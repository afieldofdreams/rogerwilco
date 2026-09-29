"""Alternative renderings of the same message, for comparison.

english(): varied, faithful prose of the kind stances write today.
as_json(): compact JSON with full field names and full enum values.
glyph(): the 'hieroglyph' variant. Same structure, but keys and enum codes
         replaced by single Unicode symbols. Tests the dense-glyph hypothesis.
"""
import json, random
from .codec import Schema, encode

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
NUMWORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
            8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 14: "fourteen",
            21: "twenty-one", 28: "twenty-eight"}


def _date(d):
    return f"{int(d[6:])} {MONTHS[int(d[4:6]) - 1]}"


def _days(n, rng):
    if n % 7 == 0 and n >= 14 and rng.random() < 0.4:
        return f"{NUMWORDS.get(n // 7, n // 7)} weeks"
    if n in NUMWORDS and rng.random() < 0.3:
        return f"{NUMWORDS[n]} days"
    return f"{n} days"


def english(schema: Schema, d: dict, seed=0) -> str:
    rng = random.Random(seed)
    E = schema.enums
    frm, to = E["stance"][d["from"]], E["stance"][d["to"]]
    stage = E["stage"][d["stage"]]
    conf = E["conf"][d["confidence"]]
    ask = E["ask"][d["ask"]]
    opener = rng.choice([
        f"{frm} here.", f"Handing this over from {frm}.", f"Quick handoff from {frm} to {to}.",
        f"{frm} passing something to {to}."])
    src = f" while scanning view {d['source_view']}" if d.get("source_view") else ""
    s = [opener]
    s.append(rng.choice([
        f"I picked up node {d['node']}{src}. It's sitting in the {stage} stage",
        f"Node {d['node']} came up{src}; it's currently at {stage}",
        f"Flagging node {d['node']}{src}, pipeline stage {stage}"]))
    bits = []
    if d.get("opstatus"):
        bits.append(f"operational status {E['opstatus'][d['opstatus']]}")
    if d.get("importance") is not None:
        bits.append(f"importance {d['importance']} out of 10")
    if d.get("heat"):
        bits.append(f"running {E['heat'][d['heat']]}")
    s[-1] += (", " + ", ".join(bits) if bits else "") + "."
    if d.get("stall_days") is not None:
        s.append(rng.choice([
            f"It hasn't moved in {_days(d['stall_days'], rng)}.",
            f"Nothing has changed on it for {_days(d['stall_days'], rng)}.",
            f"It's been stalled for {_days(d['stall_days'], rng)}."]))
    if d.get("blocked_by"):
        ids = ", ".join(str(x) for x in d["blocked_by"])
        s.append(f"It's blocked by node{'s' if len(d['blocked_by']) > 1 else ''} {ids}.")
    if d.get("due"):
        s.append(rng.choice([f"It's due on {_date(d['due'])}.", f"Due date is {_date(d['due'])}."]))
    s.append(rng.choice([
        f"My confidence in the current read is {conf}.",
        f"Confidence: {conf}.",
        f"I'd put confidence at {conf}."]))
    s.append(rng.choice([
        f"I need {to} to {ask}.",
        f"Could {to} please {ask}?",
        f"The ask for {to}: {ask}."]))
    if d.get("keep_assigned"):
        names = " and ".join(E["stance"][x] for x in d["keep_assigned"])
        s.append(f"Keep {names} on the assignment.")
    if d.get("note"):
        s.append(f"Note: {d['note']}")
    return " ".join(s)


def as_json(schema: Schema, d: dict) -> str:
    E = schema.enums
    enum_of = {"from": "stance", "to": "stance", "stage": "stage", "opstatus": "opstatus",
               "confidence": "conf", "heat": "heat", "ask": "ask"}
    out = {"type": "handoff"}
    for k, v in d.items():
        if k in enum_of:
            out[k] = E[enum_of[k]][v]
        elif k == "keep_assigned":
            out[k] = [E["stance"][x] for x in v]
        else:
            out[k] = v
    return json.dumps(out, separators=(",", ":"), ensure_ascii=False)


# Glyph variant: every key and enum code becomes a single symbol.
GLYPH_KEYS = {"HO": "⇄", "P": "◉", "stg": "▲", "os": "◐", "imp": "★", "heat": "♨",
              "stall": "⧗", "conf": "✓", "ask": "➤", "keep": "⚓", "due": "⌛",
              "src": "⌖", "blk": "⛔", "note": "✎"}
GLYPH_ENUM = {
    "TRI": "⚕", "STR": "♟", "ARC": "⌂", "BLD": "⚒", "QAR": "⚖", "CPY": "✒", "GRD": "❀",
    "DAT": "∑", "MKT": "⚲", "SCT": "⚑", "IDE": "✦", "ADAM": "☺",
    "DIA": "α", "REV": "β", "OPT": "γ", "DEC": "δ", "ACT": "ε", "DONE": "ω",
    "NOW": "●", "WAIT": "○", "SCH": "◷", "NONE": "∅",
    "L": "▁", "M": "▄", "H": "█", "COLD": "❄", "WARM": "☼", "HOT": "🔥",
    "SCORE4": "④", "SPEC": "§", "BUILD": "⚙", "REVIEW": "⌕", "ENRICH": "✚", "PRUNE": "✂",
    "DECIDE": "⚡", "RESEARCH": "⚗", "DRAFT": "✍"}


def glyph(schema: Schema, d: dict) -> str:
    line = encode(schema, "HO", d)
    out = []
    for seg in line.split("|"):
        if seg.startswith("note="):
            out.append(GLYPH_KEYS["note"] + seg[5:])
            continue
        if seg == "HO":
            out.append(GLYPH_KEYS["HO"]); continue
        if ">" in seg and "=" not in seg:
            a, b = seg.split(">"); out.append(GLYPH_ENUM[a] + "→" + GLYPH_ENUM[b]); continue
        if seg.startswith("P") and "=" not in seg:
            out.append(GLYPH_KEYS["P"] + seg[1:]); continue
        k, v = seg.split("=", 1)
        v = "+".join(GLYPH_ENUM.get(x, x) for x in v.split("+"))
        out.append(GLYPH_KEYS[k] + v)
    return "".join(out) if False else " ".join(out)


def glyph_legend() -> str:
    rev = {"stance": [], "other": []}
    keys = ", ".join(f"{g}={k}" for k, g in GLYPH_KEYS.items())
    vals = ", ".join(f"{g}={k}" for k, g in GLYPH_ENUM.items())
    return ("Glyph form. Segments separated by spaces. First glyph is message type, then FROM→TO, "
            "then ◉node. Each other segment is a key glyph followed by its value.\n"
            f"Key glyphs: {keys}\nValue glyphs (map to the codebook codes): {vals}")
