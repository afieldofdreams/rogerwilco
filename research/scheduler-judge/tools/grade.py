#!/usr/bin/env python3
"""Study 10: grade every judged trial and every code check, in code. Re-runs from the raw files with no key.

  grade.py --set pilot|main

The answer. Markdown marks, quotes and surrounding spaces are stripped from the first line of the reply that is not
blank. If that line begins with the word MATCH or MISMATCH (any case), that is the verdict; otherwise the answer is
unparseable, whatever comes later (a verdict found on a later line is recorded beside it, never graded). After
MISMATCH the detail is read from the text up to the first punctuation mark and mapped to one of the nine details by
the synonym table below, longest phrase first; the reference is the invoice number in every job, so "reference" and
"invoice" are the same detail. A detail that maps to none, or to more than one, is "not named".

The grade. Faulted pair: MATCH is a miss; MISMATCH naming the planted detail is caught; MISMATCH naming another detail
is a wrong slot; MISMATCH naming none is slot not named. Clean pair: MATCH is correct; MISMATCH with or without a detail
is a false alarm. Unparseable is its own grade in both and is never dropped.

The code check. check-rb with the pay profile refuses or passes the RB line against the HO sent. On a faulted pair a
pass is a miss and a refusal a catch, with the details its problems name; on a clean pair a refusal is a false alarm,
with the tier that refused it.
"""
from __future__ import annotations

import argparse
import re

import common as C
import fixtures as F

SYNONYMS = {
    "supplier": ["supplier name", "payee name", "beneficiary", "supplier", "payee", "vendor", "sup", "name"],
    "invoice": ["invoice number", "invoice id", "invoice no", "invoice", "item", "inv", "payment reference", "reference", "ref"],
    "amount": ["amount", "amt", "figure", "sum", "value"],
    "currency": ["currency", "cur", "ccy"],
    "kind": ["gross or net", "gross net", "net or gross", "gross", "net", "kind", "vat"],
    "account": ["payee account", "bank account", "account number", "sort code", "sortcode", "routing number", "routing",
                "account", "acct", "bank details"],
    "date": ["payment date", "date", "paid", "value date"],
    "approval": ["approval reference", "approval ref", "approval", "apref"],
}
_PHRASES = sorted(((p, s) for s, ps in SYNONYMS.items() for p in ps), key=lambda x: -len(x[0]))
VERDICT = re.compile(r"^(MISMATCH|MATCH)\b(.*)$", re.I)


def map_detail(text: str) -> tuple[str | None, list[str]]:
    t = " " + re.sub(r"[^a-z]+", " ", (text or "").lower()) + " "
    found = []
    for phrase, slot in _PHRASES:
        pat = " " + phrase + " "
        while pat in t:
            found.append(slot)
            t = t.replace(pat, " ", 1)
    uniq = sorted(set(found))
    return (uniq[0] if len(uniq) == 1 else None), uniq


def parse_answer(text: str | None) -> dict:
    lines = [l for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return {"verdict": None, "detail": None, "why": "empty"}
    first = re.sub(r"[*_`#>]", "", lines[0]).strip().strip("\"'").strip()
    m = VERDICT.match(first)
    if not m:
        later = next((re.sub(r"[*_`#>]", "", l).strip() for l in lines[1:] if VERDICT.match(re.sub(r"[*_`#>]", "", l).strip())), None)
        return {"verdict": None, "detail": None, "why": "no verdict on the first line", "verdict_later": later}
    verdict = m.group(1).upper()
    if verdict == "MATCH":
        return {"verdict": "MATCH", "detail": None, "rest": m.group(2).strip()}
    rest = m.group(2).strip().lstrip(":-–— \t")
    detail_text = re.split(r"[(:;,.!–—]| - ", rest, maxsplit=1)[0].strip()
    slot, found = map_detail(detail_text)
    return {"verdict": "MISMATCH", "detail": slot, "detail_text": detail_text, "details_found": found, "rest": rest}


def grade_trial(t: dict, answer: str | None) -> dict:
    a = parse_answer(answer)
    planted = t["slot"]
    if a["verdict"] is None:
        outcome = "unparseable"
    elif planted:
        if a["verdict"] == "MATCH":
            outcome = "miss"
        elif a["detail"] is None:
            outcome = "slot_not_named"
        elif a["detail"] == planted:
            outcome = "caught"
        else:
            outcome = "wrong_slot"
    else:
        outcome = "correct" if a["verdict"] == "MATCH" else "false_alarm"
    return {"tid": t["tid"], "faulted": bool(planted), "planted": planted, "answer": a, "outcome": outcome}


KEY_RE = re.compile(r"\b(?:tier\d \w+: )?(\w+) mismatch|does not (?:carry|echo) (\w+)")


def grade_code(rbrec: dict) -> dict:
    cc = rbrec["code_check"]
    planted = rbrec["slot"]
    keys = set()
    tiers = set()
    for prob in cc["problems"]:
        mt = re.match(r"(tier\d)", prob)
        tiers.add(mt.group(1) if mt else ("form" if prob.startswith(("RB:", "HO:")) else "other"))
        for k1, k2 in KEY_RE.findall(prob):
            k = k1 or k2
            if k in F.SLOT_OF_KEY:
                keys.add(F.SLOT_OF_KEY[k])
    if planted:
        if cc["verdict"] == "MATCH":
            outcome = "miss"
        elif planted in keys:
            outcome = "caught" if keys == {planted} else "caught_and_other"
        else:
            outcome = "wrong_slot" if keys else "slot_not_named"
    else:
        outcome = "correct" if cc["verdict"] == "MATCH" else "false_alarm"
    return {"rid": rbrec["rid"], "faulted": bool(planted), "planted": planted, "verdict": cc["verdict"], "details": sorted(keys),
            "tiers": sorted(tiers), "outcome": outcome}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    p = C.read_json(C.DATA / f"plan-{a.set}.json")
    n = m = 0
    for t in p["trials"]:
        d = C.TRIALS / a.set / t["tid"]
        if not (d / "answer.txt").exists():
            continue
        C.write_json(d / "grade.json", grade_trial(t, (d / "answer.txt").read_text()))
        n += 1
    for rb in p["readbacks"]:
        f = C.READBACKS / a.set / f"{rb['rid']}.json"
        if rb["fmt"] != "line" or not f.exists():
            continue
        rec = C.read_json(f)
        if rec.get("accepted") is None or "code_check" not in rec:
            continue
        rec["code_grade"] = grade_code(rec)
        C.write_json(f, rec)
        m += 1
    print(f"graded {n} trials and {m} code checks")


if __name__ == "__main__":
    main()
