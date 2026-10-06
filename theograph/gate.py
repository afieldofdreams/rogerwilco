"""The gate: what an extraction must pass before it is the record.

Every row is an RW1 line valid under profile clin, from extractor, ST lines to record and one DN to
human; or, in JSON form, one object per assertion with the same fields and codes. Both: item is
<kind>:<concept> with a known kind; exactly one src naming lines that exist in the document; the
quote (the ST tail, or "quote" in JSON) is found in those lines, verbatim up to whitespace and case;
ids are unique; re= points at an earlier id in the same output.
"""
from __future__ import annotations
import json, re
from . import CORE, KINDS, VALUE_SLOTS, codec, profile

NUM_RE = re.compile(r"-?\d+(\.\d+)?(/\d+(\.\d+)?)?")
ID_RE = re.compile(r"^extractor-\d+$")
SRC_RE = re.compile(r"^doc:(\d+)#l(\d+)(?:-(\d+))?$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def join_lines(parts: list[str]) -> str:
    out = ""
    for seg in parts:
        seg = seg.strip()
        if out and out.endswith("-"):
            out += seg
        elif out:
            out += " " + seg
        else:
            out = seg
    return norm(out)


def parse_src(src: str, doc_num: int, n_lines: int):
    m = SRC_RE.match(src or "")
    if not m:
        return None, f"src={src!r}: expected doc:{doc_num}#l<n> or doc:{doc_num}#l<n>-<m>"
    if int(m.group(1)) != doc_num:
        return None, f"src={src}: this is document doc:{doc_num}"
    a, b = int(m.group(2)), int(m.group(3) or m.group(2))
    if a < 1 or b > n_lines or b < a:
        return None, f"src={src}: the document has lines 1 to {n_lines}"
    return list(range(a, b + 1)), None


def quote_in_lines(quote: str, lines: list[int], text: list[str]) -> bool:
    return bool(quote) and norm(quote).lower() in join_lines([text[i - 1] for i in lines]).lower()


def _common(a: dict, doc_num: int, text: list[str], seen: set, errors: list, i: int) -> None:
    if not ID_RE.match(a.get("id") or ""):
        errors.append(f"row {i}: id must be extractor-<n>")
    if a.get("id") in seen:
        errors.append(f"row {i}: id {a['id']} already used")
    seen.add(a.get("id"))
    item = a.get("item") or ""
    if ":" not in item or item.split(":", 1)[0] not in KINDS:
        errors.append(f"row {i}: item={item!r}: item is <kind>:<concept> with kind one of {' '.join(KINDS)}")
    elif not re.fullmatch(r"[a-z0-9][a-z0-9./-]*", item.split(":", 1)[1]):
        errors.append(f"row {i}: item={item!r}: concept is lowercase words joined by hyphens")
    if a.get("re") and a["re"] not in seen - {a.get("id")}:
        errors.append(f"row {i}: re={a['re']} does not name an earlier line in this output")
    lines, err = parse_src(a.get("src") or "", doc_num, len(text))
    if err:
        errors.append(f"row {i}: {err}"); a["lines"] = []
    else:
        a["lines"] = lines
        if not a.get("quote"):
            errors.append(f"row {i}: the quote is missing: copy the words from line(s) {a['src']} that support the statement")
        elif not quote_in_lines(a["quote"], lines, text):
            errors.append(f"row {i}: the quote is not found verbatim in {a['src']}: {a['quote'][:80]!r}")


def gate_lines(body: str, doc_num: int, text: list[str]):
    cd = codec(); spec = cd.load_profile("clin")
    rows = [l for l in body.splitlines() if l.strip()]
    accepted, errors, seen = [], [], set()
    n_dn = 0
    for i, line in enumerate(rows, 1):
        if line.startswith("#"):
            continue
        if not line.startswith("RW1 "):
            errors.append(f"row {i}: does not start with RW1 (every row is a rogerwilco line)"); continue
        msg, errs, _w = cd.parse(line, spec=spec)
        if errs:
            errors.append(f"row {i}: " + " | ".join(errs)); continue
        if msg["from"] != "extractor":
            errors.append(f"row {i}: from={msg['from']}: you are extractor")
        if msg["slots"].get("p") != "clin":
            errors.append(f"row {i}: missing p=clin")
        if msg["type"] == "DN":
            n_dn += 1; continue
        if msg["type"] != "ST":
            errors.append(f"row {i}: {msg['type']}: assertion lines are ST (one DN at the end)"); continue
        if msg["to"] != "record":
            errors.append(f"row {i}: ST lines go to=record")
        s = msg["slots"]
        srcs = s.get("src")
        if isinstance(srcs, list):
            errors.append(f"row {i}: exactly one src per line (got {len(srcs)})"); srcs = srcs[0] if srcs else None
        a = {"id": msg["id"], "item": msg["item"], "re": msg.get("re"), "src": srcs, "quote": msg.get("tail") or "",
             **{k: s.get(k) for k in CORE}, "slots": {k: s[k] for k in VALUE_SLOTS if k in s}, "line": line}
        _common(a, doc_num, text, seen, errors, i)
        accepted.append(a)
    if n_dn != 1:
        errors.append(f"finish with exactly one DN line to human (found {n_dn})")
    return accepted, errors


def gate_json(body: str, doc_num: int, text: list[str]):
    enums = profile()["enums"]
    rows = [l for l in body.splitlines() if l.strip() and not l.startswith("#")]
    accepted, errors, seen = [], [], set()
    for i, row in enumerate(rows, 1):
        try:
            o = json.loads(row)
        except json.JSONDecodeError as e:
            errors.append(f"row {i}: not a JSON object on one line ({e.msg})"); continue
        if not isinstance(o, dict):
            errors.append(f"row {i}: not a JSON object"); continue
        for k in ("id", "item", "act", "pol", "cert", "subj", "time", "src", "quote"):
            if k not in o:
                errors.append(f"row {i}: missing {k}")
        for k in ("act", "pol", "cert", "subj", "time", "route", "chg", "who"):
            if k in o and o[k] not in enums.get(k, {}):
                errors.append(f"row {i}: {k}={o[k]!r}: not a known {k} code")
        if "freq" in o:
            fr = o["freq"] if isinstance(o["freq"], list) else [o["freq"]]
            bad = [f for f in fr if f not in enums["freq"]]
            if bad:
                errors.append(f"row {i}: freq {bad}: not known freq codes")
            o["freq"] = fr
        if "res" in o and not NUM_RE.fullmatch(str(o["res"])):
            errors.append(f"row {i}: res={o['res']!r}: a number as written, or two numbers with a slash, no units")
        for k in ("unit", "dose", "site", "when"):
            if k in o and (not isinstance(o[k], str) or " " in o[k]):
                errors.append(f"row {i}: {k} is a string with no spaces")
        a = {"id": o.get("id"), "item": o.get("item"), "re": o.get("re"), "src": o.get("src"), "quote": o.get("quote") or "",
             **{k: o.get(k) for k in CORE}, "slots": {k: (str(o[k]) if k != "freq" else o[k]) for k in VALUE_SLOTS if k in o}, "line": row}
        _common(a, doc_num, text, seen, errors, i)
        accepted.append(a)
    return accepted, errors


def gate(body: str, doc_num: int, text: list[str], form: str = "lines"):
    """Returns (accepted assertions, errors). Accepted is empty when there are errors."""
    acc, errs = (gate_lines if form == "lines" else gate_json)(body, doc_num, text)
    return (acc if not errs else []), errs, acc
