#!/usr/bin/env python3
"""The gate: what an extractor's output must pass before it is the record.

Arm L (lines): every row is an RW1 line valid under profile clin, from extractor, ST lines to record and
one DN to human. Arm J (JSON): every row is a JSON object with the same fields and the same closed
vocabularies. Both arms: item is <kind>:<concept> with a known kind; exactly one src naming lines that
exist in this document; the quote (the ST tail, or "quote" in JSON) is found verbatim in those lines;
ids are unique; re= points at an earlier id in the same output.

usage: python3 tools/gate.py --arm L --doc 3 runs/L-sonnet-1/doc03.rw     # prints a verdict, writes <file>.gate.json
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CORE, KINDS, VALUE_SLOTS, codec, count_tokens, doc_lines, parse_src, profile, quote_in_lines  # noqa: E402

NUM_RE = re.compile(r"-?\d+(\.\d+)?(/\d+(\.\d+)?)?")
ID_RE = re.compile(r"^extractor-\d+$")


def _common_checks(a: dict, doc: int, text: list[str], seen: set, errors: list, i: int) -> None:
    if not ID_RE.match(a.get("id") or ""):
        errors.append(f"row {i}: id must be extractor-<n>")
    if a.get("id") in seen:
        errors.append(f"row {i}: id {a['id']} already used")
    seen.add(a.get("id"))
    item = a.get("item") or ""
    if ":" not in item or item.split(":", 1)[0] not in KINDS:
        errors.append(f"row {i}: item={item!r}: item is <kind>:<concept> with kind one of {' '.join(KINDS)}")
    else:
        concept = item.split(":", 1)[1]
        if not re.fullmatch(r"[a-z0-9][a-z0-9./-]*", concept):
            errors.append(f"row {i}: item={item!r}: concept is lowercase words joined by hyphens")
    if a.get("re") and a["re"] not in seen - {a.get("id")}:
        errors.append(f"row {i}: re={a['re']} does not name an earlier line in this output")
    lines, err = parse_src(a.get("src") or "", doc, len(text))
    if err:
        errors.append(f"row {i}: {err}")
        a["lines"] = []
    else:
        a["lines"] = lines
        if not a.get("quote"):
            errors.append(f"row {i}: the quote is missing: copy the words from line(s) {a['src']} that support the statement")
        elif not quote_in_lines(a["quote"], lines, text):
            errors.append(f"row {i}: the quote is not found verbatim in {a['src']}: {a['quote'][:80]!r}")


def gate_lines(body: str, doc: int) -> tuple[list[dict], list[str], dict]:
    text = doc_lines(doc)
    cd = codec()
    spec = cd.load_profile("clin")
    rows = [l for l in body.splitlines() if l.strip()]
    accepted, errors, seen = [], [], set()
    n_st = n_dn = 0
    for i, line in enumerate(rows, 1):
        if not line.startswith("RW1 "):
            errors.append(f"row {i}: does not start with RW1 (every row is a rogerwilco line)")
            continue
        msg, errs, _warn = cd.parse(line, spec=spec)
        if errs:
            errors.append(f"row {i}: " + " | ".join(errs))
            continue
        if msg["from"] != "extractor":
            errors.append(f"row {i}: from={msg['from']}: you are extractor")
        if msg["slots"].get("p") != "clin":
            errors.append(f"row {i}: missing p=clin")
        if msg["type"] == "DN":
            n_dn += 1
            if msg["to"] != "human":
                errors.append(f"row {i}: DN goes to=human")
            continue
        if msg["type"] != "ST":
            errors.append(f"row {i}: {msg['type']}: assertion lines are ST (one DN at the end)")
            continue
        if msg["to"] != "record":
            errors.append(f"row {i}: ST lines go to=record")
        n_st += 1
        s = msg["slots"]
        srcs = s.get("src")
        if isinstance(srcs, list):
            errors.append(f"row {i}: exactly one src per line (got {len(srcs)}); a statement has one place in the document")
            srcs = srcs[0] if srcs else None
        a = {"id": msg["id"], "item": msg["item"], "re": msg.get("re"), "src": srcs, "quote": msg.get("tail") or "",
             **{k: s.get(k) for k in CORE}, "slots": {k: s[k] for k in VALUE_SLOTS if k in s}}
        _common_checks(a, doc, text, seen, errors, i)
        accepted.append(a)
    if n_dn != 1:
        errors.append(f"finish with exactly one DN line to human (found {n_dn})")
    return accepted, errors, {"st": n_st, "dn": n_dn}


def gate_json(body: str, doc: int) -> tuple[list[dict], list[str], dict]:
    text = doc_lines(doc)
    enums = profile()["enums"]
    rows = [l for l in body.splitlines() if l.strip()]
    accepted, errors, seen = [], [], set()
    for i, row in enumerate(rows, 1):
        try:
            o = json.loads(row)
        except json.JSONDecodeError as e:
            errors.append(f"row {i}: not a JSON object on one line ({e.msg})")
            continue
        if not isinstance(o, dict):
            errors.append(f"row {i}: not a JSON object")
            continue
        unknown = set(o) - {"id", "item", "act", "pol", "cert", "subj", "time", "src", "quote", "re", *VALUE_SLOTS}
        if unknown:
            errors.append(f"row {i}: unknown keys {sorted(unknown)}")
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
             **{k: o.get(k) for k in CORE}, "slots": {k: (str(o[k]) if k != "freq" else o[k]) for k in VALUE_SLOTS if k in o}}
        _common_checks(a, doc, text, seen, errors, i)
        accepted.append(a)
    return accepted, errors, {"st": len(rows), "dn": 0}


def run(path: pathlib.Path, arm: str, doc: int) -> dict:
    body = path.read_text()
    accepted, errors, counts = (gate_lines if arm == "L" else gate_json)(body, doc)
    res = {"file": str(path), "arm": arm, "doc": doc, "ok": not errors, "errors": errors, "counts": counts,
           "tokens": count_tokens(body), "chars": len(body), "accepted": accepted if not errors else [],
           "parsed": accepted}
    path.with_suffix(path.suffix + ".gate.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["L", "J"])
    ap.add_argument("--doc", required=True, type=int)
    ap.add_argument("file")
    a = ap.parse_args()
    r = run(pathlib.Path(a.file), a.arm, a.doc)
    if r["ok"]:
        print(f"OK: {r['counts']['st']} assertions, {r['tokens']} tokens")
    else:
        print(f"REJECTED ({len(r['errors'])} problems); fix every one and write the whole file again:")
        for e in r["errors"]:
            print("  " + e)
        sys.exit(1)
