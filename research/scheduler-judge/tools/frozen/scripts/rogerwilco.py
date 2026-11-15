#!/usr/bin/env python3
"""rogerwilco reference codec, version RW1. Standard library only.

Usage:
  rogerwilco.py validate "<line>" [--profile NAME] [--strict]
  rogerwilco.py check-rb "<HO line>" "<RB line>" [--profile NAME] [--expect-acc "len:120w+no:em-dash"]
                                                    # five-tier readback check; --expect-acc is the sender's withheld criteria
  rogerwilco.py make-rb "<HO line>" <rb-id> [--profile NAME] [--no-hash] [--acc "k:v+k:v"] [--do copy]
                                                    # build a readback; acc/do are the receiver's derived interpretation
  rogerwilco.py check-ho "<HO line>" '<record json>' [--profile NAME]
                                                    # before sending: the HO against the record it was built from; a relay
                                                    # passes the HO it received, as slot values, as the record
  rogerwilco.py check-dn "<HO line>" "<DN line>" [--profile NAME] [--rb "<RB line>"]
                                                    # after the act: the done report against the plan
  rogerwilco.py check-thread FILE [--profile NAME] [--now YYYYMMDDTHHMMZ]
                                                    # every handoff closes: DN, UN, FL or an acknowledged CX
  rogerwilco.py digest "<line>" [--profile NAME]                     # h= value for a line
  rogerwilco.py to-json "<line>" [--profile NAME]
  rogerwilco.py from-json '<json>' [--profile NAME]
  rogerwilco.py legend [--profile NAME]
  rogerwilco.py lint FILE [--profile NAME]        # one message per line, reports every problem

Exit status is 0 when valid, 1 when any error was found, 2 on usage error.
"""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

VERSION = "RW1"
HERE = Path(__file__).resolve().parent
PROFILES = HERE.parent / "profiles"

ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
DATE_RE = re.compile(r"^\d{8}$")
TIME_RE = re.compile(r"^\d{8}T\d{4}Z$")      # YYYYMMDDTHHMMZ, UTC to the minute: exp=


class FormError(ValueError):
    pass


# ---------------------------------------------------------------- profiles

def load_core() -> dict:
    return json.loads((PROFILES / "core.json").read_text())


def load_profile(name: str | None) -> dict:
    """Return the core spec merged with the named profile (if any)."""
    core = load_core()
    spec = {
        "types": {k: {"required": list(v["required"]), "optional": list(v["optional"]), "name": v["name"]}
                  for k, v in core["types"].items()},
        "slots": dict(core["slots"]),
        "enums": {k: dict(v) for k, v in core["enums"].items()},
        "tail_max": core.get("tail_max_chars", 300),
        "agents": None,
        "profile": None,
    }
    if not name:
        return spec
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", name) or name == "core":
        raise FormError(f"unknown profile {name!r} (profile names are lowercase letters, digits, - and _)")
    path = PROFILES / f"{name}.json"
    if not path.exists():
        raise FormError(f"unknown profile {name!r} (no {path.name} in profiles/)")
    p = json.loads(path.read_text())
    spec["profile"] = p.get("profile", name)
    for ename, vals in p.get("enums", {}).items():
        if ename in spec["enums"] and ename not in ("ask", "why"):
            # profiles may only add to core enums, never redefine
            clash = set(vals) & set(spec["enums"][ename])
            if clash:
                raise FormError(f"profile {name} redefines core codes {sorted(clash)} in enum {ename}")
        spec["enums"].setdefault(ename, {}).update(vals)
    for code, meaning in p.get("asks", {}).items():
        if code in spec["enums"]["ask"]:
            raise FormError(f"profile {name} redefines core ask {code}")
        spec["enums"]["ask"][code] = meaning
    for s in p.get("slots", []):
        key = s["key"]
        if key in spec["slots"]:
            raise FormError(f"profile {name} redefines core slot {key}")
        spec["slots"][key] = s["type"]
        if s.get("desc"):
            spec.setdefault("slot_desc", {})[key] = s["desc"]
        for t in s.get("on", []):
            if t not in spec["types"]:
                raise FormError(f"profile {name} slot {key} names unknown type {t}")
            bucket = "required" if s.get("required") else "optional"
            spec["types"][t][bucket].append(key)
    if p.get("agents"):
        spec["agents"] = set(p["agents"]) | {"human"}
    if p.get("item_examples"):
        spec["item_examples"] = list(p["item_examples"])
    if p.get("item_kinds"):
        spec["item_kinds"] = dict(p["item_kinds"])
    if p.get("asks_used"):
        spec["asks_used"] = list(p["asks_used"])
    if p.get("exec"):
        spec["exec"] = {k: list(v) for k, v in p["exec"].items()}
    return spec


# ---------------------------------------------------------------- values

def _check_value(spec: dict, key: str, typ: str, raw: str, errors: list):
    """Validate one raw slot value against its declared type. Returns the decoded value."""
    if typ.startswith("list:"):
        inner = typ[5:]
        parts = raw.split("+")
        return [_check_value(spec, key, inner, x, errors) for x in parts if x != ""]
    if typ.startswith("enum:"):
        ename = typ[5:]
        allowed = spec["enums"].get(ename, {})
        if raw not in allowed:
            errors.append(f"{key}={raw}: not a known {ename} code (rule 2: reply UN why=UNK, do not guess)")
        return raw
    if typ.startswith("int:"):
        lo, hi = typ[4:].split("-")
        if not re.fullmatch(r"-?\d+", raw):
            errors.append(f"{key}={raw}: expected an integer")
            return raw
        v = int(raw)
        if not (int(lo) <= v <= int(hi)):
            errors.append(f"{key}={raw}: out of range {lo}-{hi}")
        return v
    if typ == "date":
        if not DATE_RE.match(raw):
            errors.append(f"{key}={raw}: dates are YYYYMMDD")
        return raw
    if typ == "time":
        if not TIME_RE.match(raw):
            errors.append(f"{key}={raw}: times are YYYYMMDDTHHMMZ in UTC, e.g. 20261002T1405Z")
        return raw
    if typ == "days":
        if not re.fullmatch(r"\d+d?", raw):
            errors.append(f"{key}={raw}: expected a number of days, e.g. 14 or 14d")
            return raw
        return int(raw.rstrip("d"))
    if typ == "money":
        if not re.fullmatch(r"-?\d+\.\d{2}", raw):
            errors.append(f"{key}={raw}: money is digits with exactly two decimals, no separators, e.g. 5400.00")
        return raw
    if typ == "num":
        if not re.fullmatch(r"-?\d+(\.\d+)?(/\d+(\.\d+)?)?", raw):
            errors.append(f"{key}={raw}: num is a number as written (7.2, 148/88), no units, no separators")
        return raw
    if typ == "bool":
        if raw not in ("Y", "N"):
            errors.append(f"{key}={raw}: booleans are Y or N")
            return raw
        return raw == "Y"
    if typ in ("msgid", "agent"):
        if not ID_RE.match(raw):
            errors.append(f"{key}={raw}: must match [A-Za-z0-9._-]+")
        if typ == "agent" and spec.get("agents") and raw not in spec["agents"]:
            errors.append(f"{key}={raw}: not an agent named in profile {spec['profile']}")
        return raw
    if typ in ("ref", "token"):
        return raw
    errors.append(f"{key}: unknown slot type {typ} in spec")
    return raw


# ---------------------------------------------------------------- parse / validate

def parse(line: str, profile: str | None = None, spec: dict | None = None) -> tuple[dict, list, list]:
    """Parse one line. Returns (message, errors, warnings). message is the JSON form as a dict."""
    spec = spec or load_profile(profile)
    errors, warnings = [], []
    line = line.rstrip("\n")
    if line != line.strip():
        warnings.append("leading or trailing whitespace")
        line = line.strip()
    tail = None
    if " // " in line:
        line, tail = line.split(" // ", 1)
    elif line.endswith(" //"):
        line = line[:-3]; tail = ""
    toks = line.split(" ")
    if "" in toks:
        warnings.append("multiple consecutive spaces; separators are single spaces")
        toks = [t for t in toks if t != ""]
    msg = {"v": None, "type": None, "id": None, "re": None, "from": None, "to": None, "item": None, "slots": {}, "tail": tail}
    if len(toks) < 3:
        errors.append("a message needs at least: RW1 <TYPE> <id>")
        return msg, errors, warnings
    msg["v"], msg["type"], msg["id"] = toks[0], toks[1], toks[2]
    if msg["v"] != VERSION:
        errors.append(f"version token {msg['v']!r} is not {VERSION} (rule 2: reply UN why=VER)")
        return msg, errors, warnings
    if msg["type"] not in spec["types"]:
        errors.append(f"type {msg['type']!r} unknown; types are {' '.join(spec['types'])} (rule 2: reply UN why=UNK)")
        return msg, errors, warnings
    if not ID_RE.match(msg["id"]):
        errors.append(f"id {msg['id']!r} must match [A-Za-z0-9._-]+")
    # keyed slots
    seen = {}
    for tok in toks[3:]:
        if "=" not in tok:
            errors.append(f"{tok!r}: expected key=value (positional slots are only RW1, TYPE and id)")
            continue
        k, v = tok.split("=", 1)
        if not KEY_RE.match(k):
            errors.append(f"key {k!r} must be lowercase [a-z][a-z0-9_]*")
            continue
        if k in seen:
            errors.append(f"duplicate key {k}")
            continue
        if v == "":
            errors.append(f"{k}= has an empty value; omit the slot instead")
            continue
        seen[k] = v
    # profile switch inside the message
    if "p" in seen and seen["p"] != (spec.get("profile") or seen["p"]):
        warnings.append(f"message names profile p={seen['p']} but validation used profile {spec.get('profile') or 'core'}")
    if "p" in seen and spec.get("profile") is None:
        try:
            spec = load_profile(seen["p"])
        except FormError as e:
            errors.append(str(e))
    tdef = spec["types"][msg["type"]]
    for k, v in seen.items():
        typ = spec["slots"].get(k)
        if typ is None:
            if k.startswith("x_"):
                msg["slots"][k] = v
            else:
                warnings.append(f"unknown key {k!r} ignored (extension keys start with x_)")
            continue
        allowed = set(tdef["required"]) | set(tdef["optional"]) | {"p"}
        if msg["type"] == "RB":
            allowed |= set(spec["types"]["HO"]["required"]) | set(spec["types"]["HO"]["optional"])
        if k not in allowed:
            warnings.append(f"slot {k} is not defined for type {msg['type']}")
        val = _check_value(spec, k, typ, v, errors)
        if k in ("re", "from", "to", "item"):
            msg[k] = val
        else:
            msg["slots"][k] = val
    for k in tdef["required"]:
        if k not in seen:
            errors.append(f"{msg['type']} requires {k}")
    if msg["type"] == "AQ" and seen.get("need") == "ENUM" and "opts" not in seen:
        errors.append("AQ with need=ENUM requires opts")
    if msg["type"] == "AN" and seen.get("val") == "tail" and not tail:
        errors.append("AN with val=tail needs a tail")
    if msg["from"] and msg["to"] and msg["from"] == msg["to"]:
        warnings.append("from and to are the same agent")
    if msg["from"] and not re.fullmatch(re.escape(msg["from"]) + r"-\d+", msg["id"]):
        errors.append(f"id {msg['id']!r} must be <from>-<n>: {msg['from']}-1, {msg['from']}-2, ... unique in the conversation")
    # closed answer vocabulary: a profile may define enum ans; then AQ opts and AN val must come from it
    ans = spec["enums"].get("ans")
    if ans:
        if msg["type"] == "AQ" and seen.get("need") == "ENUM":
            for o in str(seen.get("opts", "")).split("+"):
                if o and o not in ans:
                    errors.append(f"opts={o}: not in the profile's answer vocabulary {'/'.join(ans)} (do not invent options)")
        if msg["type"] == "AN" and seen.get("val") not in (None, "tail", "Y", "N") and not re.fullmatch(r"-?\d+(\.\d+)?|\d{8}", str(seen.get("val"))):
            if seen["val"] not in ans:
                errors.append(f"val={seen['val']}: not in the profile's answer vocabulary {'/'.join(ans)}")
    if tail is not None and len(tail) > spec["tail_max"]:
        errors.append(f"tail is {len(tail)} characters; limit is {spec['tail_max']} (rule 4: move it to an artifact and reference with art=)")
    return msg, errors, warnings


def validate(line: str, profile: str | None = None, strict: bool = False) -> list[str]:
    _, errors, warnings = parse(line, profile)
    return errors + (warnings if strict else [])


# ---------------------------------------------------------------- encode

_ORDER = ["re", "from", "to", "item"]

def encode(msg: dict, profile: str | None = None) -> str:
    """JSON form (dict) to line. Validates the result."""
    spec = load_profile(profile or msg.get("slots", {}).get("p"))
    if msg.get("v", VERSION) != VERSION:
        raise FormError(f"version must be {VERSION}")
    toks = [VERSION, msg["type"], msg["id"]]
    for k in _ORDER:
        if msg.get(k) not in (None, ""):
            toks.append(f"{k}={msg[k]}")
    slot_order = [s for s in spec["slots"] if s not in _ORDER]
    slots = msg.get("slots", {})
    for k in slot_order + [k for k in slots if k not in slot_order]:
        if k not in slots or slots[k] in (None, ""):
            continue
        v = slots[k]
        if isinstance(v, bool):
            v = "Y" if v else "N"
        elif isinstance(v, list):
            v = "+".join(str(x) for x in v)
        toks.append(f"{k}={v}")
    line = " ".join(toks)
    if msg.get("tail"):
        line += " // " + str(msg["tail"]).replace("\n", " ")
    _, errors, _ = parse(line, spec=spec)
    if errors:
        raise FormError("; ".join(errors))
    return line


def to_json(line: str, profile: str | None = None) -> str:
    msg, errors, _ = parse(line, profile)
    if errors:
        raise FormError("; ".join(errors))
    return json.dumps(msg, ensure_ascii=False)


def from_json(s: str, profile: str | None = None) -> str:
    return encode(json.loads(s), profile)


# ---------------------------------------------------------------- canonical form and digest

def canonical(msg: dict) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8. Lists keep their order. Basis for h=."""
    return json.dumps(msg, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(line_or_msg, profile: str | None = None) -> str:
    """Tier-2 integrity digest: first 12 hex chars of SHA-256 over the canonical JSON form."""
    if isinstance(line_or_msg, str):
        msg, errors, _ = parse(line_or_msg, profile)
        if errors:
            raise FormError("; ".join(errors))
    else:
        msg = line_or_msg
    return hashlib.sha256(canonical(msg).encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- readback

DEFAULT_RB = ["item", "ask", "due"]
RB_LEVELS = {"echo", "all", "acc", "plan", "exec"}


def _split_constraint(tok: str) -> tuple[str, str]:
    """'len:120w' -> ('len', '120w'); a bare token is its own key."""
    k, _, v = tok.partition(":")
    return k.strip().lower(), v.strip().lower()


def _norm(v: str, aliases: dict) -> tuple[str, frozenset]:
    """Normalise a constraint value: alias, lowercase, strip punctuation. Returns (joined, word set)."""
    v = v.lower().strip()
    for canon, alts in aliases.items():
        if v == canon or v in alts:
            v = canon; break
    words = [w for w in re.split(r"[^a-z0-9]+", v) if w]
    words = [w[:-1] if len(w) >= 5 and w.endswith("s") and not w.endswith("ss") else w for w in words]  # crude singular
    return "".join(words), frozenset(words)


STOP = {"the", "and", "with", "for", "from", "that", "this", "must", "not", "no", "of", "to", "in", "on", "a", "an"}

def _same_value(a: str, b: str, aliases: dict) -> int:
    """0 no match; 1 strict: equal after normalisation, prefix (4+ chars), or one word set contains the other;
    2 loose: the two share a distinctive word (5+ chars, not a stopword). Set-valued keys accept loose matches
    and report them; single-valued keys require strict."""
    ja, wa = _norm(a, aliases); jb, wb = _norm(b, aliases)
    if ja == jb:
        return 1
    if len(ja) >= 4 and len(jb) >= 4 and (ja.startswith(jb) or jb.startswith(ja)):
        return 1
    if wa and wb and (wa <= wb or wb <= wa):
        return 1
    shared = {w for w in wa & wb if len(w) >= 5 and w not in STOP}
    return 2 if shared else 0


def compare_acc(expected: list[str], derived: list[str], keys: list[str] | None = None,
                spec: dict | None = None, derived_not: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Tier 4. Compare the sender's criteria with the ones the receiver derived. Returns (problems, notes).

    Single-valued keys (len, fmt, lang, tone, voice, aud, out, by): same key, different value is a contradiction;
    key expected but absent is a gap. Set-valued keys (must, no, scope, src): each expected element must have a
    matching derived element, else a gap; extra elements are assumptions. Values match by normalisation, not string.
    A receiver's not= list counts as no: values. Keys the sender named in keys= but the receiver omitted are gaps
    even when the sender's own set is empty for that key. Keys outside the closed set are noted, not compared."""
    core = spec or load_core()
    aliases = core.get("value_aliases", {})
    set_keys = set(core.get("constraint_set_keys", ["must", "no", "scope", "src"]))
    known = set(core.get("constraint_keys", {}))
    problems, notes = [], []
    exp, der = {}, {}
    for t in expected:
        k, v = _split_constraint(t); exp.setdefault(k, []).append(v)
    for t in derived:
        k, v = _split_constraint(t); der.setdefault(k, []).append(v)
    for v in (derived_not or []):
        der.setdefault("no", []).append(v)
    for k in list(exp) + list(der):
        if k not in known:
            notes.append(f"key {k} is not in the closed constraint set; not compared (use one of {', '.join(sorted(known))})")
    for k, vs in exp.items():
        if k not in known:
            continue
        if k not in der:
            problems.append(f"tier4 comprehension: gap, receiver did not derive {k}:{'/'.join(vs)}")
            continue
        if k in set_keys:
            for v in vs:
                best = max((_same_value(v, d, aliases), d) for d in der[k])
                if best[0] == 0:
                    problems.append(f"tier4 comprehension: gap, receiver did not derive {k}:{v}")
                elif best[0] == 2:
                    notes.append(f"loose match: sender {k}:{v} taken as receiver {k}:{best[1]}")
            for d in der[k]:
                if not any(_same_value(v, d, aliases) for v in vs):
                    notes.append(f"assumption: receiver added {k}:{d}; confirm or correct")
        else:
            if not any(_same_value(vs[0], d, aliases) == 1 for d in der[k]):
                problems.append(f"tier4 comprehension: contradiction on {k}: sender {'/'.join(vs)} vs receiver {'/'.join(der[k])}")
    for k in (keys or []):
        k = k.lower()
        if k in known and k not in der and k not in exp:
            problems.append(f"tier4 comprehension: gap, sender asked for {k} in keys= and receiver did not report it")
    for k, vs in der.items():
        if k in known and k not in exp and k not in set_keys:
            notes.append(f"assumption: receiver added {k}:{'/'.join(vs)}; confirm or correct")
    return problems, notes


def now_utc() -> str:
    """The current time as an exp= value, YYYYMMDDTHHMMZ."""
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%MZ")


def _expired(exp, now: str) -> bool:
    """True when an exp= time has passed. Both are YYYYMMDDTHHMMZ, so they compare as strings."""
    return bool(exp) and TIME_RE.match(str(exp)) is not None and str(now) >= str(exp)


def check_rb_full(ho_line: str, rb_line: str, profile: str | None = None,
                  expect_acc: list[str] | None = None, now: str | None = None) -> tuple[list[str], list[str]]:
    """Rule 1, five tiers. Returns (problems, notes); no problems means the readback passes and ownership transfers.

    Tier 1 receipt:        RB.re == HO.id, and RB travels from HO.to back to HO.from.
    Tier 2 integrity:      if RB carries h=, it must equal digest(HO). Only code can produce it.
    Tier 3 echo:           RB echoes item ask due as decoded values, plus slots the HO named in rb=; rb=all means every slot.
    Tier 4 comprehension:  when the HO asked rb=acc or rb=plan, the RB must carry acc= derived from the brief, and it is
                           compared by key with the sender's criteria (expect_acc, withheld, or acc= on the HO if sent).
                           rb=plan additionally requires do=.
    Tier 5 execution:      when the HO asked rb=exec, the RB must carry every execution slot the profile names for the
                           HO's ask, with the values the receiver will use; a slot the HO carries must match it, a slot the
                           receiver resolved for itself (the account on file) is present here and compared with the
                           sender's record by the sender's own code, which holds that record.
    """
    ho, e1, _ = parse(ho_line, profile)
    rb, e2, _ = parse(rb_line, profile)
    problems = [f"HO: {e}" for e in e1] + [f"RB: {e}" for e in e2]
    notes = []
    if problems:
        return problems, notes
    if ho["type"] != "HO":
        problems.append(f"first line is {ho['type']}, expected HO")
    if rb["type"] != "RB":
        problems.append(f"second line is {rb['type']}, expected RB")
    if problems:
        return problems, notes
    # tier 1
    if rb["re"] != ho["id"]:
        problems.append(f"tier1 receipt: RB re={rb['re']} does not point at HO id {ho['id']}")
    if rb["from"] != ho["to"] or rb["to"] != ho["from"]:
        problems.append(f"tier1 receipt: RB must come from {ho['to']} to {ho['from']}; got from={rb['from']} to={rb['to']}")
    # expiry: a handoff or a prepared statement past its exp= cannot be confirmed; prepare again from the record
    clock = now or now_utc()
    if _expired(ho["slots"].get("exp"), clock):
        problems.append(f"expired: the HO expired at {ho['slots']['exp']} (now {clock}); send a new HO from the record")
    if _expired(rb["slots"].get("exp"), clock):
        problems.append(f"expired: the statement expired at {rb['slots']['exp']} (now {clock}); prepare again")
    if ho["slots"].get("exp") and rb["slots"].get("exp") and str(rb["slots"]["exp"]) > str(ho["slots"]["exp"]):
        problems.append(f"expired: the statement's exp={rb['slots']['exp']} outlives the HO's exp={ho['slots']['exp']}")
    # tier 2
    if "h" in rb["slots"]:
        want = digest(ho)
        if rb["slots"]["h"] != want:
            problems.append(f"tier2 integrity: h={rb['slots']['h']} but digest of the HO is {want}")
    # tier 3
    rbset = [x.lower() for x in (ho["slots"].get("rb") or [])]
    levels = {x for x in rbset if x in RB_LEVELS}
    named = [x for x in rbset if x not in RB_LEVELS]
    ho_flat = {"item": ho["item"], **ho["slots"]}
    rb_flat = {"item": rb["item"], **rb["slots"]}
    if "all" in levels:
        keys = [k for k in ho_flat if k not in ("rb", "p", "acc", "exp")]
    else:
        keys = list(DEFAULT_RB) + [k for k in named if k not in DEFAULT_RB]
    for k in keys:
        if k not in ho_flat:
            continue
        if k not in rb_flat:
            problems.append(f"tier3 echo: RB does not echo {k} (HO has {k}={_show(ho_flat[k])})")
        elif rb_flat[k] != ho_flat[k]:
            problems.append(f"tier3 echo: {k} mismatch: HO {_show(ho_flat[k])} vs RB {_show(rb_flat[k])}")
    # tier 4
    if "acc" in levels or "plan" in levels:
        derived = rb["slots"].get("acc")
        if not derived:
            problems.append("tier4 comprehension: HO asked for rb=" + ("plan" if "plan" in levels else "acc") + " but RB carries no acc=")
        else:
            expected = expect_acc if expect_acc is not None else ho["slots"].get("acc")
            if expected is None:
                notes.append("tier4: no expected criteria supplied (withheld set missing and HO sent none); acc= recorded but not compared")
            else:
                p4, n4 = compare_acc(expected, derived, keys=ho["slots"].get("keys"), derived_not=rb["slots"].get("not"))
                problems += p4; notes += n4
        if "plan" in levels and not rb["slots"].get("do"):
            problems.append("tier4 comprehension: rb=plan requires do= on the RB")
        aliases = load_core().get("value_aliases", {})
        exp_must = [v for t in (expect_acc or ho["slots"].get("acc") or []) for k, v in [_split_constraint(t)] if k == "must"]
        for t in rb["slots"].get("not") or []:
            if any(_same_value(t, v, aliases) == 1 for v in exp_must):
                problems.append(f"tier4 comprehension: receiver excludes {t} which the sender requires")
    # tier 5
    if "exec" in levels:
        spec = load_profile(profile)
        ask = str(ho["slots"].get("ask") or "")
        exec_slots = (spec.get("exec") or {}).get(ask)
        if not exec_slots:
            notes.append(f"tier5 execution: the profile names no execution slots for ask {ask or '?'}; nothing checked beyond the echo")
        else:
            for k in exec_slots:
                if k not in rb_flat:
                    problems.append(f"tier5 execution: RB does not carry {k}, which the act needs")
                elif k in ho_flat and rb_flat[k] != ho_flat[k]:
                    problems.append(f"tier5 execution: {k} mismatch: HO {_show(ho_flat[k])} vs RB {_show(rb_flat[k])}")
    return problems, notes


def check_rb(ho_line: str, rb_line: str, profile: str | None = None, expect_acc: list[str] | None = None) -> list[str]:
    """Rule 1. Returns mismatches; empty means the readback passes and ownership transfers. See check_rb_full."""
    problems, _ = check_rb_full(ho_line, rb_line, profile, expect_acc)
    return problems


def _show(v):
    if isinstance(v, list):
        return "+".join(str(x) for x in v)
    if isinstance(v, bool):
        return "Y" if v else "N"
    return str(v)


def make_rb(ho_line: str, rb_id: str, profile: str | None = None, with_hash: bool = True, eta: str | None = None,
            acc: list[str] | None = None, do: str | None = None) -> str:
    """Build a correct readback for an HO. What a code-side receiver should send. Under rb=exec the envelope and the
    execution slots the HO carries are copied; the slots the receiver must resolve for itself (an account on file) are
    not in the HO and the receiver adds them before sending."""
    ho, errors, _ = parse(ho_line, profile)
    if errors:
        raise FormError("; ".join(errors))
    rbset = [x.lower() for x in (ho["slots"].get("rb") or [])]
    ho_flat = {"item": ho["item"], **ho["slots"]}
    if "all" in rbset:
        keys = [k for k in ho_flat if k not in ("rb", "acc")]
    elif "exec" in rbset:
        spec = load_profile(profile)
        exec_slots = (spec.get("exec") or {}).get(str(ho["slots"].get("ask") or ""), [])
        keys = list(DEFAULT_RB) + [k for k in exec_slots if k in ho_flat and k not in DEFAULT_RB] + [k for k in rbset if k not in DEFAULT_RB and k not in RB_LEVELS]
    else:
        keys = list(DEFAULT_RB) + [k for k in rbset if k not in DEFAULT_RB and k not in RB_LEVELS]
    slots = {k: ho_flat[k] for k in keys if k in ho_flat and k != "item"}
    if acc:
        slots["acc"] = acc
    if do:
        slots["do"] = do
    if "p" in ho["slots"]:
        slots["p"] = ho["slots"]["p"]
    if with_hash:
        slots["h"] = digest(ho)
    if eta:
        slots["eta"] = eta
    msg = {"v": VERSION, "type": "RB", "id": rb_id, "re": ho["id"], "from": ho["to"], "to": ho["from"],
           "item": ho["item"], "slots": slots, "tail": None}
    return encode(msg, profile)


def _exec_slots(spec: dict, ask) -> list[str]:
    """The execution slots a profile names for an ask: the values an irreversible act is done with."""
    return list((spec.get("exec") or {}).get(str(ask or "")) or [])


_RB_OWN = ("h", "eta", "acc", "do", "not", "asm", "p", "exp")   # what an RB adds for itself; never part of the plan


def check_ho(ho_line: str, record: dict, profile: str | None = None) -> tuple[list[str], list[str]]:
    """The check before sending. Before an irreversible act the HO is built from the record by code or, where it was
    drafted, compared with the record before it goes: every value the record holds appears in the HO unchanged, and
    the HO asks rb=exec where the profile names execution slots for its ask. record maps slot names (and to, item,
    ask) to values written as they are on the line. A relay forwarding a handover it received passes that HO's slots,
    with to= the next agent, as the record. Returns (problems, notes); no problems means the HO may be sent."""
    ho, errors, _ = parse(ho_line, profile)
    problems = [f"HO: {e}" for e in errors]
    notes: list[str] = []
    if problems:
        return problems, notes
    if ho["type"] != "HO":
        return [f"first line is {ho['type']}, expected HO"], notes
    flat = {"from": ho["from"], "to": ho["to"], "item": ho["item"], **ho["slots"]}
    for k, v in record.items():
        want = "+".join(str(x) for x in v) if isinstance(v, list) else _show(v)
        if k not in flat:
            problems.append(f"record: HO does not carry {k} (record has {k}={want})")
        elif _show(flat[k]) != want:
            problems.append(f"record: {k} mismatch: record {want} vs HO {_show(flat[k])}")
    spec = load_profile(profile)
    exec_slots = _exec_slots(spec, ho["slots"].get("ask"))
    if exec_slots:
        levels = {str(x).lower() for x in (ho["slots"].get("rb") or [])} & RB_LEVELS
        if "exec" not in levels:
            problems.append(f"ask {ho['slots']['ask']} is an irreversible act under profile {spec.get('profile')}: "
                            "the HO must ask rb=exec")
        for k in exec_slots:
            if k in flat and k not in record:
                notes.append(f"{k}={_show(flat[k])} has no value in the record to check against")
            elif k not in flat and k not in record:
                notes.append(f"{k} is in neither the HO nor the record; the receiver resolves it and the readback carries it")
    return problems, notes


def check_dn(ho_line: str, dn_line: str, profile: str | None = None,
             rb_line: str | None = None) -> tuple[list[str], list[str]]:
    """The second loop: the done report checked against the plan. The DN answers the HO (receipt), and for an ask the
    profile names execution slots for, it carries every one of them with the value as executed. Each must equal the
    value the plan held: the HO's, or the readback's where the HO left the slot to the receiver and the readback
    passed. out=NOOP carries no execution slots, since nothing was executed; out=PARTIAL carries the ones that were,
    and a missing one is noted rather than refused. Returns (problems, notes)."""
    ho, e1, _ = parse(ho_line, profile)
    dn, e2, _ = parse(dn_line, profile)
    problems = [f"HO: {e}" for e in e1] + [f"DN: {e}" for e in e2]
    notes: list[str] = []
    if problems:
        return problems, notes
    if ho["type"] != "HO":
        problems.append(f"first line is {ho['type']}, expected HO")
    if dn["type"] != "DN":
        problems.append(f"second line is {dn['type']}, expected DN")
    if problems:
        return problems, notes
    if dn["re"] != ho["id"]:
        problems.append(f"receipt: DN re={dn['re']} does not point at HO id {ho['id']}")
    if dn["from"] != ho["to"] or dn["to"] != ho["from"]:
        problems.append(f"receipt: DN must come from {ho['to']} to {ho['from']}; got from={dn['from']} to={dn['to']}")
    if dn["item"] != ho["item"]:
        problems.append(f"receipt: DN item {dn['item']} is not the HO's {ho['item']}")
    plan = {k: v for k, v in ho["slots"].items() if k not in ("rb", "acc", "keys", "p")}
    if rb_line:
        rb, e3, _ = parse(rb_line, profile)
        if e3:
            return problems + [f"RB: {e}" for e in e3], notes
        if rb["type"] != "RB":
            return problems + [f"third line is {rb['type']}, expected RB"], notes
        failed, _ = check_rb_full(ho_line, rb_line, profile)
        if failed:
            problems.append("the readback did not pass the sender's check, so it is not the plan: " + failed[0])
            return problems, notes
        plan.update({k: v for k, v in rb["slots"].items() if k not in _RB_OWN})
    spec = load_profile(profile)
    exec_slots = _exec_slots(spec, ho["slots"].get("ask"))
    done = dn["slots"]
    out = done.get("out")
    if not exec_slots:
        notes.append(f"the profile names no execution slots for ask {ho['slots'].get('ask') or '?'}; "
                     "only the slots the DN carries are compared")
        keys = [k for k in done if k in plan]
    else:
        keys = exec_slots
    for k in keys:
        if k not in done:
            if out == "OK":
                problems.append(f"executed: DN does not carry {k}, which the act used")
            elif out == "PARTIAL":
                notes.append(f"executed: DN does not carry {k}")
        elif k in plan:
            if plan[k] != done[k]:
                problems.append(f"executed: {k} mismatch: plan {_show(plan[k])} vs DN {_show(done[k])}")
        else:
            notes.append(f"executed: {k}={_show(done[k])} was resolved by the receiver and is not in the plan; "
                         "check it against the record")
    if out == "NOOP" and any(k in done for k in exec_slots):
        notes.append("out=NOOP but the DN carries execution values")
    return problems, notes


# ---------------------------------------------------------------- the thread: every handoff closes

CLOSERS = ("DN", "UN", "FL")


def check_thread(lines: list[str], profile: str | None = None, now: str | None = None) -> tuple[list[str], list[str]]:
    """Every handoff ends. Given the lines of a conversation in the order they were sent, each HO must close with
    exactly one DN, UN or FL from its receiver, or with a CX from its sender that the receiver acknowledged with
    AN val=Y. A DN after a CX means the act ran although it was cancelled, or before the cancel arrived: it needs a
    decision, usually an UNDO. An HO still open after its exp= (or after its due= date) is orphaned. A CX must come
    from the HO's sender to its receiver. Returns (problems, notes); notes list handoffs that are open and in time."""
    clock = now or now_utc()
    problems: list[str] = []
    notes: list[str] = []
    msgs = []
    for n, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        msg, errors, _ = parse(line, profile)
        if errors:
            problems.append(f"line {n}: " + "; ".join(errors))
            continue
        msgs.append((n, msg))
    by_id = {m["id"]: m for _, m in msgs}
    for n, ho in msgs:
        if ho["type"] != "HO":
            continue
        hid = ho["id"]
        after = [(k, m) for k, m in msgs if k > n and m.get("re") == hid]
        closes = [(k, m) for k, m in after if m["type"] in CLOSERS and m["from"] == ho["to"]]
        cancels = [(k, m) for k, m in after if m["type"] == "CX"]
        for k, cx in cancels:
            if cx["from"] != ho["from"] or cx["to"] != ho["to"]:
                problems.append(f"line {k}: CX {cx['id']} must come from {ho['from']} to {ho['to']}, the HO's sender and receiver")
        acked = [(k, cx) for k, cx in cancels
                 if any(m["type"] == "AN" and m.get("re") == cx["id"] and str(m["slots"].get("val")) == "Y" and m["from"] == ho["to"]
                        for j, m in msgs if j > k)]
        if len(closes) > 1:
            problems.append(f"{hid}: closed {len(closes)} times ({', '.join(m['type'] + ' ' + m['id'] for _, m in closes)}); a handoff closes once")
        if cancels:
            first_cx = cancels[0][0]
            ran = [m for k, m in closes if m["type"] == "DN" and k > first_cx and str(m["slots"].get("out")) != "NOOP"]
            if ran:
                problems.append(f"{hid}: {ran[0]['id']} reports the act done after CX {cancels[0][1]['id']} cancelled it; decide whether to UNDO it")
            elif not closes and not acked:
                notes.append(f"{hid}: CX {cancels[0][1]['id']} sent, not yet acknowledged; the receiver must abandon any prepared statement and answer AN val=Y")
        if closes or acked:
            continue
        exp, due = ho["slots"].get("exp"), ho["slots"].get("due")
        if _expired(exp, clock) or (due and str(clock)[:8] > str(due)):
            limit = f"exp={exp}" if _expired(exp, clock) else f"due={due}"
            problems.append(f"{hid}: orphaned, open past {limit} with no DN, UN, FL or acknowledged CX; close it or cancel it")
        else:
            notes.append(f"{hid}: open")
    for k, m in msgs:
        if m["type"] == "CX" and (m.get("re") not in by_id or by_id[m["re"]]["type"] != "HO"):
            problems.append(f"line {k}: CX {m['id']} re={m.get('re')} does not name an HO in this thread")
    return problems, notes


# ---------------------------------------------------------------- legend

def legend(profile: str | None = None, lean: bool = False) -> str:
    """The legend another agent needs in its prompt. lean=True drops the comprehension-readback constraint keys,
    for teams that use envelope echo only."""
    spec = load_profile(profile)
    out = [f"rogerwilco {VERSION}. One line per message: RW1 <TYPE> <id> [re=<id>] from=<agent> to=<agent> [item=<ref>] key=value ... [// tail]. "
           "No spaces in values; lists join with +; dates YYYYMMDD; tail is free text, 300 chars max."]
    prof_slots = set(spec.get("slot_desc", {}))
    acc_slots = {"acc", "keys", "do", "not", "asm"}
    for t, d in spec["types"].items():
        optional = [k for k in d["optional"] if not (lean and (k in prof_slots or k in acc_slots))]
        opt = " ".join(optional)
        out.append(f"{t} {d['name']}: requires {' '.join(d['required'])}" + (f"; optional {opt}" if opt else ""))
    if lean and prof_slots:
        out.append("Profile slots may appear on any type where they carry a fact.")
    if lean:
        out.append("RB echoes the HO's item, ask and due as decoded, plus any slots the HO names in rb= (rb=all: every slot). "
                   "Code-side receivers add h=<digest of the HO>. Unknown code: reply UN why=UNK. Every reply carries re=.")
    else:
        out.append("RB must echo the HO's item, ask and due as decoded (plus any slots the HO names in rb=; rb=all means every slot). "
                   "If the HO says rb=acc or rb=plan, the RB must also carry acc=<criteria you derived from the brief, as key:value tokens joined by +>, "
                   "and for rb=plan do=<what you will produce>; optional not=<what you exclude> asm=<assumptions>; tail = the task in your own words. "
                   "Code-side receivers add h=<digest of the HO>. Unknown code: reply UN why=UNK. Every reply carries re=.")
    hide_asks = set()
    if lean and spec.get("asks_used"):
        hide_asks = set(load_core()["enums"]["ask"]) - set(spec["asks_used"])
    for ename, vals in spec["enums"].items():
        shown = {k: v for k, v in vals.items() if not (ename == "ask" and k in hide_asks)}
        out.append(f"{ename}: " + ", ".join(f"{k}={v}" for k, v in shown.items()))
    core = load_core()
    if not lean:
        out.append("acc= constraint keys (closed set): " + "; ".join(f"{k}={v}" for k, v in core["constraint_keys"].items()) + ". Values: no spaces, lowercase, e.g. len:120w lang:uk must:monday-problem no:em-dash.")
    out.append("Every HO closes exactly once: DN, UN or FL from the receiver, or CX from the sender. On a CX, abandon anything prepared and answer AN val=Y; if the act already ran, send its DN instead. exp=YYYYMMDDTHHMMZ (UTC) is the latest moment to act or confirm: never act on an HO, and never confirm a statement, past its exp. A DN that does not match the plan is reversed with a new HO ask=UNDO ctx=<that DN id>.")
    out.append("Message ids are <yourname>-<n>, unique in the conversation. Readback level is set per handoff by the sender: rb=exec before an irreversible act (a payment release, a payee change, anything external) where the profile names execution slots, rb=all where it does not; the default envelope echo otherwise.")
    if spec.get("exec"):
        out.append("rb=exec: the RB carries the execution slots for the ask with the values you will actually use, resolved from your own records where the HO does not give them (" +
                   "; ".join(f"{k}: {' '.join(v)}" for k, v in spec["exec"].items()) +
                   "). The sender checks them against its record and only an AN val=Y clears the act. After the act, the DN carries the same slots with the values as executed, taken from the tool's result, not from your intention; the sender checks that too.")
    if spec.get("profile"):
        line = f"Profile {spec['profile']}: messages carry p={spec['profile']}."
        if spec.get("agents"):
            line += f" Agents: {', '.join(sorted(spec['agents']))}."
        if spec["enums"].get("ans"):
            line += " AQ opts and AN val must come from ans; do not invent options."
        if spec.get("slot_desc"):
            line += " Profile slots: " + "; ".join(f"{k}={v} ({spec['slots'][k]})" for k, v in spec["slot_desc"].items()) + "."
        if any(t == "money" for t in spec["slots"].values()):
            line += " money = digits with two decimals, no separators (5400.00)."
        if any(t == "num" for t in spec["slots"].values()):
            line += " num = a number as written, or two numbers with a slash (7.2, 148/88); units go in their own slot."
        if spec.get("item_kinds"):
            line += " item is <kind>:<concept>; kinds: " + ", ".join(f"{k}={v}" for k, v in spec["item_kinds"].items()) + "."
        if spec.get("item_examples"):
            line += " item examples: " + ", ".join(spec["item_examples"]) + "."
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------- cli

def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 2
    cmd, rest = argv[0], argv[1:]
    profile = None; strict = False
    if "--profile" in rest:
        i = rest.index("--profile"); profile = rest[i + 1]; del rest[i:i + 2]
    if "--strict" in rest:
        strict = True; rest.remove("--strict")
    expect_acc = acc = do = None
    if "--expect-acc" in rest:
        i = rest.index("--expect-acc"); expect_acc = rest[i + 1].split("+"); del rest[i:i + 2]
    if "--acc" in rest:
        i = rest.index("--acc"); acc = rest[i + 1].split("+"); del rest[i:i + 2]
    if "--do" in rest:
        i = rest.index("--do"); do = rest[i + 1]; del rest[i:i + 2]
    rb_given = None
    if "--rb" in rest:
        i = rest.index("--rb"); rb_given = rest[i + 1]; del rest[i:i + 2]
    try:
        if cmd == "validate":
            msg, errors, warnings = parse(rest[0], profile)
            for e in errors: print("ERROR:", e)
            for w in warnings: print("WARN:", w)
            if not errors: print("OK", json.dumps(msg, ensure_ascii=False))
            return 1 if errors or (strict and warnings) else 0
        if cmd == "check-rb":
            problems, notes = check_rb_full(rest[0], rest[1], profile, expect_acc)
            for p in problems: print("MISMATCH:", p)
            for n_ in notes: print("NOTE:", n_)
            if not problems: print("OK readback passes; ownership transfers")
            return 1 if problems else 0
        if cmd == "check-ho":
            record = json.loads(rest[1])
            if not isinstance(record, dict):
                raise FormError("the record is a JSON object of slot values as written on the line")
            problems, notes = check_ho(rest[0], record, profile)
            for p in problems: print("MISMATCH:", p)
            for n_ in notes: print("NOTE:", n_)
            if not problems: print("OK the HO matches the record; send it")
            return 1 if problems else 0
        if cmd == "check-dn":
            problems, notes = check_dn(rest[0], rest[1], profile, rb_line=rb_given)
            for p in problems: print("MISMATCH:", p)
            for n_ in notes: print("NOTE:", n_)
            if not problems: print("OK the done report matches the plan")
            return 1 if problems else 0
        if cmd == "check-thread":
            lines = Path(rest[0]).read_text().splitlines()
            now = None
            if "--now" in rest:
                now = rest[rest.index("--now") + 1]
            problems, notes = check_thread(lines, profile, now)
            for p in problems: print("PROBLEM:", p)
            for n_ in notes: print("NOTE:", n_)
            if not problems: print("OK every handoff is closed or open in time")
            return 1 if problems else 0
        if cmd == "digest":
            print(digest(rest[0], profile)); return 0
        if cmd == "make-rb":
            print(make_rb(rest[0], rest[1], profile, with_hash="--no-hash" not in rest, acc=acc, do=do)); return 0
        if cmd == "to-json":
            print(to_json(rest[0], profile)); return 0
        if cmd == "from-json":
            print(from_json(rest[0], profile)); return 0
        if cmd == "legend":
            if "--lean" in rest:
                print(legend(profile, lean=True)); return 0
            print(legend(profile)); return 0
        if cmd == "lint":
            bad = 0
            for n, line in enumerate(Path(rest[0]).read_text().splitlines(), 1):
                if not line.strip() or line.lstrip().startswith("#"): continue
                _, errors, warnings = parse(line, profile)
                for e in errors: print(f"{rest[0]}:{n}: ERROR: {e}"); bad += 1
                for w in warnings: print(f"{rest[0]}:{n}: WARN: {w}")
            print(f"{bad} error(s)"); return 1 if bad else 0
        print(__doc__); return 2
    except (FormError, IndexError, json.JSONDecodeError) as e:
        print("ERROR:", e); return 1


def main() -> int:
    """Console entry point (`rogerwilco validate ...` after pip install)."""
    return _main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
