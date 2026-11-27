#!/usr/bin/env python3
"""Study 11: grade every reviewer answer in code, and class every first-stage text (summary, extract) by whether
it still carries what decides the case. Re-runnable from the raw files with no key.

    grade.py --set pilot|main

A reviewer answer is one line: APPROVE, or HOLD and a reason. Only the first non-blank line is read, and the reason
is looked for in what stands after HOLD up to the first bracket, colon, semicolon, comma, full stop, dash or spaced
hyphen, so that an explanation added after the reason does not change it.

  faulted case   APPROVE                    miss           the instruction would be released
                 HOLD <the planted reason>  caught
                 HOLD <another reason>      held_other     stopped, for a reason that is not the planted one
                 HOLD unconfirmed           held_unconfirmed
                 HOLD, no reason found      held_unnamed
  clean case     APPROVE                    correct
                 HOLD <a reason>            false_hold
                 HOLD unconfirmed           false_unconfirmed
                 HOLD, no reason found      false_unnamed
  either         no verdict on the line     unparseable

"Stopped" is any HOLD on a faulted case: caught, held_other, held_unconfirmed or held_unnamed. The act does not go
out in any of them. "Caught" is the stricter measure. Unparseable answers are reported and are in neither.
"""
from __future__ import annotations

import argparse
import json
import re

import casefile as K
import common as C

VERDICT = re.compile(r"^(APPROVE|HOLD)\b(.*)$", re.I)
# Longest phrases first. A reason is found only if exactly one distinct reason is named.
SYNONYMS = {
    "supplier": ["supplier name", "payee name", "supplier", "payee", "beneficiary", "vendor"],
    "invoice": ["invoice number", "invoice"],
    "amount": ["amount", "figure", "sum"],
    "currency": ["currency"],
    "kind": ["gross or net", "gross", "net", "kind", "vat"],
    "account": ["payee account", "bank account", "account number", "sort code", "routing number", "account", "bank details"],
    "date": ["payment date", "date"],
    "reference": ["payment reference", "reference"],
    "approval": ["approval reference", "approval record", "no approval", "unapproved", "not approved", "approval"],
    "duplicate": ["already paid", "paid twice", "duplicate"],
    "onhold": ["on hold", "on-hold", "onhold"],
    "unconfirmed": ["cannot confirm", "not confirmed", "unconfirmed"],
}
_PHRASES = sorted(((p, r) for r, ps in SYNONYMS.items() for p in ps), key=lambda x: -len(x[0]))
STOPPED = ("caught", "held_other", "held_unconfirmed", "held_unnamed")
FALSE = ("false_hold", "false_unconfirmed", "false_unnamed")


def reason_of(rest: str) -> tuple[str | None, list[str]]:
    text = " " + re.sub(r"[^a-z]+", " ", rest.lower().replace("on-hold", "on hold")) + " "
    found = []
    for phrase, reason in _PHRASES:
        pat = f" {phrase.replace('-', ' ')} "
        if pat in text:
            text = text.replace(pat, "  ")
            if reason not in found:
                found.append(reason)
    return (found[0] if len(found) == 1 else None), found


def parse_answer(text: str | None) -> dict:
    if text is None or not text.strip():
        return {"verdict": None, "reason": None, "first_line": "", "why": "no answer"}
    first = next(ln for ln in text.splitlines() if ln.strip())
    first = re.sub(r"[*_`#>]", "", first).strip().strip("\"'").strip()
    m = VERDICT.match(first)
    if not m:
        later = next((ln for ln in text.splitlines()[1:] if VERDICT.match(re.sub(r"[*_`#>]", "", ln).strip())), None)
        return {"verdict": None, "reason": None, "first_line": first[:300], "why": "no verdict on the first line", "verdict_later": later}
    rest = re.sub(r"^[\s:\-–—]+", "", m.group(2))
    rest = re.split(r"[(:;,.!–—]| - ", rest, maxsplit=1)[0]            # the reason is what stands before any explanation
    reason, found = reason_of(rest) if m.group(1).upper() == "HOLD" else (None, [])
    return {"verdict": m.group(1).upper(), "reason": reason, "found": found, "first_line": first[:300],
            "lines": len([ln for ln in text.splitlines() if ln.strip()])}


def grade_answer(ans: dict, fault: str | None) -> str:
    v, r = ans["verdict"], ans["reason"]
    if v is None:
        return "unparseable"
    if fault is None:
        if v == "APPROVE":
            return "correct"
        return "false_unconfirmed" if r == "unconfirmed" else ("false_hold" if r else "false_unnamed")
    if v == "APPROVE":
        return "miss"
    if r == K.REASON_OF_FAULT[fault]:
        return "caught"
    if r == "unconfirmed":
        return "held_unconfirmed"
    return "held_other" if r else "held_unnamed"

# ------------------------------------------------------------------------------------- the evidence check


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def carries(text: str, case: dict) -> dict:
    """Does a first-stage text (a summary or an extract) still hold what a reader needs to see the planted fault?
    The reviewer is always shown the instruction itself beside it, so for a literal fault the question is whether
    the text holds the APPROVED value of the changed detail. For a record fault it is whether the text holds the
    record that decides the case. Decided by fixed string rules; a text that holds the evidence in words these rules
    do not know is classed as not carrying it, and that is visible wherever a reviewer then catches the fault."""
    fault, t, low = case["fault"], case["target"], text.lower()
    flat = re.sub(r"\s+", " ", low)
    if fault is None:
        return {"carries": None}
    if fault == "amount":
        whole = t["amount"].split(".")[0]
        with_comma = f"{int(whole):,}"
        ok = bool(re.search(rf"(?<![\d,.]){re.escape(with_comma)}(?:\.\d\d)?(?![\d])", text) or re.search(rf"(?<![\d,.]){whole}(?:\.\d\d)?(?![\d])", text))
        return {"carries": ok, "rule": "the approved amount is in the text"}
    if fault == "account":
        ok = t["account"] in _digits(text) and bool(re.search(rf"(?<!\d){t['account']}(?!\d)", text))
        return {"carries": ok, "rule": "the approved account number is in the text"}
    if fault == "supplier":
        return {"carries": t["supplier"].lower() in flat, "rule": "the approved supplier's legal name is in the text"}
    if fault == "duplicate":
        iso = case["truth"]["ledger"]["released"]
        y, m, d = iso.split("-")
        long_ = f"{int(d)} september"
        sents = re.split(r"(?<=[.!?\n])\s+", flat)
        ok = any((t["item"].lower() in s) and re.search(r"ledger|already|released on|previously|duplicate|twice", s) and
                 not re.search(r"no entry|not in the paid ledger|does not appear|no record of|not been (paid|released)|is not in", s) for s in sents)
        ok = ok or iso in text or (long_ in flat and "ledger" in flat and t["item"].lower() in flat)
        return {"carries": bool(ok), "rule": "a sentence or line holds the invoice with the paid ledger, a release or the word duplicate"}
    if fault == "onhold":
        name = t["supplier"].split()[0].lower()
        ok = any(("on hold" in s) and (name in s or f"{t['sup']} |" in s) for s in re.split(r"(?<=[.!?\n])\s+|\n", low))
        return {"carries": bool(ok), "rule": "a sentence or line holds ON HOLD with the supplier's name"}
    if fault == "noapproval":
        other = case["truth"]["covers"].lower()
        ok = other in flat or bool(re.search(r"no (approval )?record|not (covered|in the (approval )?register|listed|found)|does not (cover|appear)|"
                                             r"no approval|different invoice|another invoice|unapproved", flat))
        return {"carries": bool(ok), "rule": "the text holds the invoice the cited approval really covers, or says no record covers this one"}
    raise ValueError(fault)

# ------------------------------------------------------------------------------------- main


def main() -> None:
    import build as B
    import run as R
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    p = C.read_json(C.DATA / f"plan-{a.set}.json")
    out = C.RESULTS / ("pilot" if a.set == "pilot" else "")
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    s1 = R.load_stage1(a.set)
    rows1 = []
    for st in p["stage1"]:
        rec = s1.get(st["sid"])
        if rec is None:
            continue
        ev = carries(rec["text"], B.case_of(st))
        rows1.append({"sid": st["sid"], "kind": st["kind"], "job": st["job"], "fault": st["fault"], "words": len(rec["text"].split()),
                      "lines": len([ln for ln in rec["text"].splitlines() if ln.strip()]), "chars": len(rec["text"]), **ev})
        k = f"stage1 {st['kind']} carries={ev['carries']}"
        counts[k] = counts.get(k, 0) + 1
    with (out / "stage1-grades.jsonl").open("w") as fh:
        for r in rows1:
            fh.write(json.dumps(r) + "\n")
    grades = []
    answers = {}
    for cell in p["cells"]:
        for m in p["reviewers"]:
            for r in R.read_lines(C.TRIALS / a.set / f"{cell}.{m}.jsonl"):
                answers[r["tid"]] = r
    for t in p["trials"]:
        r = answers.get(t["tid"])
        if r is None:
            continue
        ans = parse_answer(r["answer"])
        o = grade_answer(ans, t["fault"])
        grades.append({"tid": t["tid"], "cell": t["cell"], "reviewer": t["reviewer"], "case": t["case"], "job": t["job"], "fault": t["fault"],
                       "fault_class": t["fault_class"], "paired_target": t["paired_target"], "answer": ans, "outcome": o,
                       "user_chars": r.get("user_chars"), "tokens": r.get("tokens"), "cost": r.get("cost"), "seconds": r.get("seconds")})
        counts[o] = counts.get(o, 0) + 1
    with (out / "grades.jsonl").open("w") as fh:
        for g in grades:
            fh.write(json.dumps(g) + "\n")
    print(f"graded {a.set}: {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
