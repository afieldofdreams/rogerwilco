#!/usr/bin/env python3
"""Study 11: grade every reviewer answer in code, and class every clerk text by whether it holds what decides the
case. Re-runnable from the raw files with no key.

    grade.py --set pilot|main        writes results/[pilot/]grades.jsonl and stage1-grades.jsonl

A reviewer answer is one line: APPROVE, or HOLD and a reason. Only the first non-blank line is read. Markdown marks,
quotes, a leading bullet and a leading "Answer:" are taken off it; it must then begin APPROVE (or APPROVED) or HOLD.
The reason is looked for in what stands after HOLD up to the first bracket, colon, semicolon, comma, full stop, dash
or spaced hyphen, so that an explanation added after the reason does not change it.

  faulted case   APPROVE                         released          the instruction goes out
                 HOLD <a reason that names it>   caught
                 HOLD <another reason>           held_other        stopped, for a reason that is not the planted one
                 HOLD unconfirmed                held_unconfirmed
                 HOLD, no one reason found       held_unnamed
  clean case     APPROVE                         correct
                 HOLD <a reason>                 false_hold
                 HOLD unconfirmed                false_unconfirmed
                 HOLD, no one reason found       false_unnamed
  either         no verdict on the line          unparseable

"Stopped" is any HOLD on a faulted case: caught, held_other, held_unconfirmed or held_unnamed. The act does not go
out in any of them. "Held" is any HOLD on a clean case. Unparseable answers are neither; they stay in every
denominator and are listed word for word in the summary.

In the two account cells the outcome words are the same but mean less: nothing shown tells a faulted case from a
clean one there, so the only measure is how often the answer is APPROVE.
"""
from __future__ import annotations

import argparse
import json
import re

import casefile as K
import common as C

VERDICT = re.compile(r"^(APPROVED?|HOLD)\b(.*)$", re.I)
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
    "onhold": ["on hold", "onhold"],
    "unconfirmed": ["cannot confirm", "not confirmed", "unconfirmed"],
}
_PHRASES = sorted(((p, r) for r, ps in SYNONYMS.items() for p in ps), key=lambda x: -len(x[0]))
STOPPED = ("caught", "held_other", "held_unconfirmed", "held_unnamed")
FALSE = ("false_hold", "false_unconfirmed", "false_unnamed")
QUOTES = "\"'\u201c\u201d\u2018\u2019"


def reason_of(rest: str) -> tuple[str | None, list[str]]:
    text = " " + re.sub(r"[^a-z]+", " ", rest.lower().replace("on-hold", "on hold")) + " "
    found = []
    for phrase, reason in _PHRASES:
        pat = f" {phrase} "
        if pat in text:
            text = text.replace(pat, "  ")
            if reason not in found:
                found.append(reason)
    return (found[0] if len(found) == 1 else None), found


def clean_line(line: str) -> str:
    line = re.sub(r"[*`#>]", "", line).replace("_", " ")
    line = line.strip().strip(QUOTES).strip()
    line = re.sub(r"^[-\u2022]\s*", "", line)
    return re.sub(r"^answer\s*:\s*", "", line, flags=re.I).strip().strip(QUOTES).strip()


def parse_answer(text: str | None) -> dict:
    if text is None or not text.strip():
        return {"verdict": None, "reason": None, "first_line": "", "why": "no answer"}
    first = clean_line(next(ln for ln in text.splitlines() if ln.strip()))
    m = VERDICT.match(first)
    if not m:
        later = next((ln for ln in text.splitlines()[1:] if VERDICT.match(clean_line(ln))), None)
        return {"verdict": None, "reason": None, "first_line": first[:300], "why": "no verdict on the first line", "verdict_later": later}
    verdict = "HOLD" if m.group(1).upper() == "HOLD" else "APPROVE"
    reason, found = None, []
    if verdict == "HOLD":
        rest = re.sub(r"^[\s:\-\u2013\u2014(,.]+", "", m.group(2))
        rest = re.split(r"[(:;,.!\u2013\u2014]| - ", rest, maxsplit=1)[0]            # the reason is what stands before any explanation
        reason, found = reason_of(rest)
    return {"verdict": verdict, "reason": reason, "found": found, "first_line": first[:300],
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
        return "released"
    if r in K.REASONS_OF_FAULT[fault]:
        return "caught"
    if r == "unconfirmed":
        return "held_unconfirmed"
    return "held_other" if r else "held_unnamed"

# ------------------------------------------------------------------------------------- the evidence check on clerk's texts


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*`_\"\u201c\u201d\u2018\u2019]", "", text).replace("'", " ")).lower()


def _sentences(text: str) -> list[str]:
    """Sentences and lines: a clerk: line or a copied record line is one unit."""
    out = []
    for line in text.splitlines():
        out += [s for s in re.split(r"(?<=[.!?;])\s+", _plain(line)) if s.strip()]
    return out


NEG = r"\b(no|not|none|nothing|never|without|neither|absent|missing|isn t|doesn t|cannot|unable)\b"


def carries(text: str, case: dict) -> dict:
    """Does a clerk text hold what a reader needs to see the planted fault? clerk is not shown the instruction, and the
    reviewer is, so the question is whether the text holds the record's side of the comparison:
      amount      the approved amount, pence and all
      account     the approved account number
      supplier    the approved supplier's legal name in full, or a word of it that the lookalike's name lacks
      duplicate   the date of the earlier release, or the words released under <the approval>, or already or
                  previously paid or released
      onhold      a sentence or line with "on hold" that is not about Pennine Couriers
      noapproval  a sentence or line that names the register or an approval, holds a negative, and does not name the
                  ledger
    On every case it also reports whether the text holds all three records for the invoice (`records`: the approval
    reference, an ACTIVE or ON HOLD status, and a statement about the paid ledger), which is what a reviewer needs
    before it can confirm anything. Fixed rules, applied with quotes and markdown taken off. They are a secondary
    measure: a text that holds the evidence in words they do not know is classed as not carrying it, and that shows
    wherever a reviewer then names the planted reason."""
    fault, t = case["fault"], case["target"]
    plain = _plain(text)
    sents = _sentences(text)
    held = {"approval": t["approval"].lower() in plain or any(re.search(r"register|approval", s) and re.search(NEG, s) for s in sents),
            "master": bool(re.search(r"\bactive\b|\bon[ -]hold\b", plain)), "ledger": "ledger" in plain}
    out = {"records": all(held.values()), "records_held": held}
    if fault is None:
        return {"carries": None, **out}
    if fault == "amount":
        whole, pence = t["amount"].split(".")
        forms = "|".join(re.escape(x) for x in sorted({whole, f"{int(whole):,}"}))
        ok = bool(re.search(rf"(?<![\d,.])(?:{forms})(?:\.{pence})?(?![\d,]\d|\.\d|\d)", plain))
        rule = "the approved amount is in the text"
    elif fault == "account":
        ok = bool(re.search(rf"(?<!\d){t['account']}(?!\d)", plain))
        rule = "the approved account number is in the text"
    elif fault == "supplier":
        own = re.findall(r"[a-z0-9]+", t["supplier"].lower())
        other = set(re.findall(r"[a-z0-9]+", case["instr"]["supplier"].lower()))
        telling = [w for w in own if w not in other]
        ok = " ".join(own) in " ".join(re.findall(r"[a-z0-9]+", plain)) or any(re.search(rf"\b{re.escape(w)}\b", plain) for w in telling)
        rule = "the approved supplier's legal name is in the text in full, or a word of it that the lookalike's name lacks"
    elif fault == "duplicate":
        iso = case["truth"]["ledger"]["released"]
        day = str(int(iso.split("-")[2]))
        ok = (iso in plain or bool(re.search(rf"\b{day}(st|nd|rd|th)? (of )?september\b|\bseptember {day}\b", plain))
              or f"released under {t['approval'].lower()}" in plain or bool(re.search(r"\b(already|previously) (been )?(paid|released)\b", plain)))
        rule = "the date of the earlier release, or released under the approval, or already or previously paid or released"
    elif fault == "onhold":
        ok = any(re.search(r"\bon[ -]hold\b", s) and "pennine" not in s for s in sents)
        rule = "a sentence or line holds ON HOLD and is not about Pennine Couriers"
    elif fault == "noapproval":
        ok = any(re.search(r"register|approval", s) and re.search(NEG, s) and "ledger" not in s for s in sents)
        rule = "a sentence or line names the register or an approval, holds a negative, and does not name the ledger"
    else:
        raise ValueError(fault)
    return {"carries": bool(ok), "rule": rule, **out}

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
    with (out / "stage1-grades.jsonl").open("w") as fh:
        for st in p["stage1"]:
            rec = s1.get(st["sid"])
            if rec is None:
                continue
            ev = carries(rec["text"], B.case_of(st))
            fh.write(json.dumps({"sid": st["sid"], "cell": st["cell"], "kind": st["kind"], "author": st["author"], "case": st["case"], "job": st["job"],
                                 "fault": st["fault"], "words": len(rec["text"].split()),
                                 "lines": len([ln for ln in rec["text"].splitlines() if ln.strip()]), "chars": len(rec["text"]), **ev}) + "\n")
            k = f"stage1 {st['cell']} carries={ev['carries']}"
            counts[k] = counts.get(k, 0) + 1
    answers = R.load_answers(a.set, p)
    with (out / "grades.jsonl").open("w") as fh:
        for t in p["trials"]:
            r = answers.get(t["tid"])
            if r is None:
                continue
            ans = parse_answer(r["answer"])
            o = grade_answer(ans, t["fault"])
            fh.write(json.dumps({"tid": t["tid"], "cell": t["cell"], "reviewer": t["reviewer"], "case": t["case"], "job": t["job"], "fault": t["fault"],
                                 "fault_class": t["fault_class"], "fault_target": t["fault_target"], "answer": ans, "outcome": o,
                                 "raw": r["answer"] if o == "unparseable" else None,
                                 "user_chars": r.get("user_chars"), "tokens": r.get("tokens"), "cost": r.get("cost"), "seconds": r.get("seconds")}) + "\n")
            counts[o] = counts.get(o, 0) + 1
    print(f"graded {a.set}: {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
