"""formcore: schema-driven typed compact messages for agent-to-agent handoffs.

Domain-agnostic. A schema declares enums and message types; each message type
declares typed slots. The codec encodes a dict to a single pipe-delimited line,
decodes it back, and rejects anything that does not validate.

Wire format:
    CODE|<positional 1>|<positional 2>|key=value|...|note=free text
Positional slots sharing an index are joined with '>' (e.g. TRI>STR).
Lists use '+'. Dates are YYYYMMDD. Durations are '<n>d'. note is always last.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass
from pathlib import Path


class FormError(ValueError):
    pass


@dataclass
class Schema:
    raw: dict

    @classmethod
    def load(cls, path) -> "Schema":
        return cls(json.loads(Path(path).read_text()))

    @property
    def enums(self):
        return self.raw["enums"]

    def msg(self, code):
        if code not in self.raw["messages"]:
            raise FormError(f"unknown message type {code!r}")
        return self.raw["messages"][code]

    def legend(self) -> str:
        """Compact human/LLM-readable codebook, sent once as shared context."""
        out = [f"{self.raw['name']} v{self.raw['version']} codebook"]
        for code, m in self.raw["messages"].items():
            out.append(f"Message {code} = {m['name']}. Format: {code}|FROM>TO|P<node>|key=value|...|note=text")
            for s in m["slots"]:
                req = "required" if s["required"] else "optional"
                out.append(f"  {s['key']}: {s['field']} ({s['type']}, {req})")
        for name, vals in self.enums.items():
            out.append(f"Enum {name}: " + ", ".join(f"{k}={v}" for k, v in vals.items()))
        out.append("Lists join with '+'. Dates YYYYMMDD. Durations like 19d.")
        return "\n".join(out)


# ---------- type handling ----------

def _enc_val(schema: Schema, typ: str, v):
    if typ.startswith("enum:"):
        e = schema.enums[typ[5:]]
        if v not in e:
            raise FormError(f"{v!r} not in enum {typ[5:]}")
        return v
    if typ.startswith("list:"):
        inner = typ[5:]
        inner_t = "int" if inner == "int" else f"enum:{inner}"
        return "+".join(str(_enc_val(schema, inner_t, x)) for x in v)
    if typ.startswith("int"):
        if not isinstance(v, int):
            raise FormError(f"expected int, got {v!r}")
        m = re.match(r"int\[(\d+)-(\d+)\]", typ)
        if m and not (int(m[1]) <= v <= int(m[2])):
            raise FormError(f"{v} out of range {typ}")
        return str(v)
    if typ == "days":
        return f"{int(v)}d"
    if typ == "date":
        if not re.fullmatch(r"\d{8}", v):
            raise FormError(f"bad date {v!r}")
        return v
    if typ == "text":
        return str(v).replace("|", "/").replace("\n", " ")
    raise FormError(f"unknown type {typ}")


def _dec_val(schema: Schema, typ: str, s: str):
    if typ.startswith("enum:"):
        if s not in schema.enums[typ[5:]]:
            raise FormError(f"{s!r} not in enum {typ[5:]}")
        return s
    if typ.startswith("list:"):
        inner = typ[5:]
        inner_t = "int" if inner == "int" else f"enum:{inner}"
        return [_dec_val(schema, inner_t, x) for x in s.split("+") if x]
    if typ.startswith("int"):
        if not re.fullmatch(r"-?\d+", s):
            raise FormError(f"expected int, got {s!r}")
        v = int(s)
        m = re.match(r"int\[(\d+)-(\d+)\]", typ)
        if m and not (int(m[1]) <= v <= int(m[2])):
            raise FormError(f"{v} out of range {typ}")
        return v
    if typ == "days":
        if not re.fullmatch(r"\d+d", s):
            raise FormError(f"bad duration {s!r}")
        return int(s[:-1])
    if typ == "date":
        if not re.fullmatch(r"\d{8}", s):
            raise FormError(f"bad date {s!r}")
        return s
    if typ == "text":
        return s
    raise FormError(f"unknown type {typ}")


# ---------- codec ----------

def encode(schema: Schema, code: str, data: dict) -> str:
    m = schema.msg(code)
    parts = [code]
    positional = {}
    keyed, note = [], None
    for s in m["slots"]:
        f = s["field"]
        if f not in data or data[f] is None:
            if s["required"]:
                raise FormError(f"missing required field {f}")
            continue
        v = _enc_val(schema, s["type"], data[f])
        if "positional" in s:
            positional.setdefault(s["positional"], []).append((s, v))
        elif s["type"] == "text":
            note = f"{s['key']}={v}"
        else:
            keyed.append(f"{s['key']}={v}")
    for idx in sorted(positional):
        group = positional[idx]
        if len(group) == 1:
            s, v = group[0]
            parts.append(f"{s['key']}{v}")
        else:
            parts.append(">".join(v for _, v in group))
    parts += keyed
    if note:
        parts.append(note)
    return "|".join(parts)


def decode(schema: Schema, line: str) -> tuple[str, dict]:
    line = line.strip()
    # note may contain anything after 'note=' so split it off first
    note = None
    if "|note=" in line:
        line, note = line.split("|note=", 1)
    segs = line.split("|")
    code = segs[0]
    m = schema.msg(code)
    slots = m["slots"]
    pos_idx = sorted({s["positional"] for s in slots if "positional" in s})
    if len(segs) < 1 + len(pos_idx):
        raise FormError("truncated message")
    out = {}
    for i, idx in enumerate(pos_idx):
        group = [s for s in slots if s.get("positional") == idx]
        seg = segs[1 + i]
        if len(group) == 1:
            s = group[0]
            if not seg.startswith(s["key"]):
                raise FormError(f"positional {idx} should start with {s['key']!r}")
            out[s["field"]] = _dec_val(schema, s["type"], seg[len(s["key"]):])
        else:
            vals = seg.split(">")
            if len(vals) != len(group):
                raise FormError(f"positional {idx} expects {len(group)} values")
            for s, v in zip(group, vals):
                out[s["field"]] = _dec_val(schema, s["type"], v)
    bykey = {s["key"]: s for s in slots if "positional" not in s}
    for seg in segs[1 + len(pos_idx):]:
        if "=" not in seg:
            raise FormError(f"malformed segment {seg!r}")
        k, v = seg.split("=", 1)
        if k not in bykey:
            raise FormError(f"unknown key {k!r}")
        s = bykey[k]
        if s["field"] in out:
            raise FormError(f"duplicate key {k!r}")
        out[s["field"]] = _dec_val(schema, s["type"], v)
    if note is not None:
        out["note"] = note
    for s in slots:
        if s["required"] and s["field"] not in out:
            raise FormError(f"missing required field {s['field']}")
    return code, out


def validate(schema: Schema, line: str) -> list[str]:
    try:
        decode(schema, line)
        return []
    except FormError as e:
        return [str(e)]


# ---------- delta encoding for repeated state reads ----------

def delta(schema: Schema, code: str, prev: dict, cur: dict) -> str:
    """Encode only changed fields plus identity slots. '~' marks a cleared field."""
    m = schema.msg(code)
    ident = {s["field"] for s in m["slots"] if "positional" in s}
    changed = {k: v for k, v in cur.items() if k in ident or prev.get(k) != v}
    cleared = [k for k in prev if k not in cur and k not in ident]
    line = "D" + encode_partial(schema, code, changed)
    for f in cleared:
        key = next(s["key"] for s in m["slots"] if s["field"] == f)
        line += f"|{key}=~"
    return line


def encode_partial(schema, code, data):
    m = schema.msg(code)
    patched = dict(schema.raw)
    patched = {**schema.raw, "messages": {code: {**m, "slots": [{**s, "required": s.get("positional") is not None} for s in m["slots"]]}}}
    return encode(Schema(patched), code, data)


# ---------- tight style: METAR-like, fully positional, space-separated ----------
# Every slot appears in schema order; '-' marks absent. Free text trails after ' // '.
# Dropping or inserting a field changes arity and is rejected. An optional
# checksum (' #xx') catches value corruption when the line is produced by code.
import zlib

def _crc(body: str) -> str:
    return format(zlib.crc32(body.encode()) % 1296, "x").zfill(3)

def _tight_val(schema, typ, v):
    s = _enc_val(schema, typ, v)
    return s[:-1] if typ == "days" else s

def encode_tight(schema: Schema, code: str, data: dict, check=False) -> str:
    m = schema.msg(code)
    out = [code]
    note = None
    for s in m["slots"]:
        f = s["field"]
        present = f in data and data[f] is not None
        if not present and s["required"]:
            raise FormError(f"missing required field {f}")
        if s["type"] == "text":
            note = data.get(f)
            continue
        out.append(_tight_val(schema, s["type"], data[f]) if present else "-")
    body = " ".join(out)
    if note:
        body += " // " + str(note).replace("\n", " ")
    if check:
        body += " #" + _crc(body)
    return body

def decode_tight(schema: Schema, line: str) -> tuple[str, dict]:
    line = line.strip()
    if re.search(r" #[0-9a-f]{3}$", line):
        body, c = line[:-5], line[-3:]
        if _crc(body) != c:
            raise FormError("checksum mismatch")
        line = body
    note = None
    if " // " in line:
        line, note = line.split(" // ", 1)
    toks = line.split(" ")
    code = toks[0]
    m = schema.msg(code)
    slots = [s for s in m["slots"] if s["type"] != "text"]
    if len(toks) - 1 != len(slots):
        raise FormError(f"expected {len(slots)} fields, got {len(toks) - 1}")
    out = {}
    for s, t in zip(slots, toks[1:]):
        if t == "-":
            if s["required"]:
                raise FormError(f"missing required field {s['field']}")
            continue
        out[s["field"]] = _dec_val(schema, s["type"], t + "d" if s["type"] == "days" else t)
    if note is not None:
        out["note"] = note
    return code, out

def tight_legend(schema: Schema, code="HO") -> str:
    m = schema.msg(code)
    fields = [f"{s['field']}" for s in m["slots"] if s["type"] != "text"]
    lines = [f"{schema.raw['name']} tight form. Space-separated, fixed positions, '-' = not stated.",
             f"{code} " + " ".join(fields) + " // optional note",
             "Lists join with '+'. Dates YYYYMMDD. stall_days is a number of days."]
    for name, vals in schema.enums.items():
        lines.append(f"{name}: " + ", ".join(f"{k}={v}" for k, v in vals.items()))
    return "\n".join(lines)
