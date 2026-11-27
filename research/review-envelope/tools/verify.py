#!/usr/bin/env python3
"""Study 11: is every stimulus the stimulus it should be? Code only, no model. Run before the pilot and the main run.

    verify.py --set pilot|main

Rebuilds every user turn that does not need a clerk's text, and every clerk prompt, and checks them against each other
and against literal expectations, not only against the builder's own output:

  1  a case's instruction is one string in every cell it appears in
  2  the code check approves every clean case and holds every faulted one for a reason that names its fault
  3  on the check sheet a literal or name fault shows as exactly one differing row, the planted one; a record fault
     shows no differing row and its own line; and the sheet is the same whatever the length of the file behind it
  4  the three record blocks of a faulted file equal its clean twin's except for the planted line or record
  5  the paperwork of a faulted file equals its clean twin's (in a noapproval case the target's scheduler note alone
     differs: it cannot name an approval)
  6  a file with a text in it is the plain S file of the same case plus exactly that one document or note, and the
     text is the expected one: on a faulted case it carries the faulted value and, for the forged email, the lookalike
     domain; on a clean case it is the harmless twin, and the Finance Director's office writes from the company's own
     domain
  7  the M file holds every document of the S file, and the L file every document of the M file
  8  a written-policy cell and its unwritten twin show the same user turn; only the brief differs
  9  the account view shows no record
  10 a duplicate's earlier release is dated after the invoice it pays
  11 a clerk's prompt holds no instruction and names the invoice, and both clerks get the same prompt

Prints the size of the user turn per cell. Exits 1 on any failure.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys

import build as B
import casefile as K
import common as C
import fixtures as F
import run as R

TAIL = K.USER_TAIL
MARK = "--- payer's instruction, prepared for release ---\n"
INSTR = "\n\n" + MARK


def docs_of(user: str) -> list[str]:
    """The documents of a file view, without their numbers."""
    body = user.split(INSTR)[0].split("The file for this payment run:\n\n", 1)[1]
    return [re.sub(r"^--- document \d+: ", "--- ", d if d.startswith("--- document") else "--- document " + d) for d in re.split(r"\n\n(?=--- document \d+: )", body)]


def block(docs: list[str], title: str) -> str:
    return next(d for d in docs if d.startswith(f"--- {title} ---"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    p = C.read_json(C.DATA / f"plan-{a.set}.json")
    problems: list[str] = []

    def need(cond, where, msg):
        if not cond:
            problems.append(f"{where}: {msg}")

    first = p["reviewers"][0]
    trials = [t for t in p["trials"] if t["reviewer"] == first]
    turn: dict[tuple, str] = {}
    sizes: dict[str, list[int]] = {}
    for t in trials:
        if t["stage1"]:
            continue
        u = R.review_user(t, {})
        turn[(t["cell"], t["case"])] = u
        sizes.setdefault(t["cell"], []).append(len(u))
    cases = {}
    for t in trials:
        cases.setdefault(t["case"], t)
    clean_of = lambda t: B.case_id(t["job"], None, a.set)  # noqa: E731

    for cid, t in cases.items():
        fault, job = t["fault"], B.JOB[t["job"]]
        case = {L: K.make_case(job, fault, L, f"{a.set}:{t['job']}") for L in K.LENGTHS}
        ins = case["S"]["instr"]
        want = K.instruction(ins)
        # 1
        for (cell, c2), u in turn.items():
            if c2 == cid:
                need(u.count(want) == 1 and u.split(MARK)[1].startswith(want), f"{cell} {cid}", "the instruction is not the case's one instruction")
        changed = F.changed(job, ins)
        if fault in K.LITERAL + K.NAME:
            need(changed and set(changed) <= set(F.FIELDS_OF_SLOT[fault]), cid, f"the planted fault changed {sorted(changed)}")
        elif fault == "noapproval":
            need(set(changed) == {"approval"}, cid, f"noapproval changed {sorted(changed)}")
        else:
            need(not changed, cid, f"the instruction differs from the approved payment in {sorted(changed)}")
        # 2
        verdict, reason = K.code_check(case["S"])
        need((verdict == "APPROVE") if fault is None else (verdict == "HOLD" and reason in K.REASONS_OF_FAULT[fault]), cid, f"code check says {verdict} {reason}")
        # 3
        sheets = {L: K.check_sheet(case[L]) for L in K.LENGTHS}
        need(len(set(sheets.values())) == 1, cid, "the check sheet differs with the length of the file")
        rows = sheets["S"].split("\n")[4:13]
        differing = []
        for (label, _), row in zip(K.SHEET_ROWS, rows):
            left, right = [x.strip() for x in re.split(r"\s{2,}", row[14:].strip(), maxsplit=1)] if "  " in row[14:].strip() else (row[14:].strip(), "")
            if left != right:
                differing.append(label)
        expect = {"amount": ["amount"], "account": ["account"], "supplier": ["supplier"], "noapproval": [k for k, _ in K.SHEET_ROWS]}.get(fault, [])
        need(differing == expect, cid, f"check sheet rows that differ: {differing}, expected {expect}")
        need(("no record covers invoice" in sheets["S"]) == (fault == "noapproval"), cid, "check sheet: the register line is wrong")
        need(("approved by the Finance Director" in sheets["S"]) == (fault != "noapproval"), cid, "check sheet: the approver is not named")
        need(("no row is named" in sheets["S"]) == (fault == "supplier"), cid, "check sheet: the master-by-name line is wrong")
        need(("no row holds" in sheets["S"]) == (fault == "account"), cid, "check sheet: the master-by-account line is wrong")
        need(("ON HOLD" in sheets["S"]) == (fault == "onhold"), cid, "check sheet: the master status is wrong")
        need((f"no entry for invoice {ins['item']}" in sheets["S"]) == (fault != "duplicate"), cid, "check sheet: the ledger line is wrong")
        # 10
        if fault == "duplicate":
            inv = next(x for title, x in K.paperwork(job) if title.startswith("invoice "))
            day = int(re.search(r"Invoice date: (\d+) September", inv).group(1))
            need(int(case["S"]["truth"]["ledger"]["released"][-2:]) > day, cid, "the earlier release is dated before the invoice")
        # 4, 5, 7 on the three file cells
        prev = None
        for L, cell in (("S", "W-fileS"), ("M", "W-fileM"), ("L", "W-fileL")):
            u = turn[(cell, cid)]
            d = docs_of(u)
            if prev is not None:
                paper_prev = {x for x in prev if not re.match(r"--- (approval register|supplier master|paid ledger) ---", x)}
                need(paper_prev <= set(d), f"{cell} {cid}", "the longer file does not hold every document of the shorter one")
            prev = d
            if fault is None:
                continue
            dc = docs_of(turn[(cell, clean_of(t))])
            reg, mas, led = (block(d, x) for x in ("approval register", "supplier master", "paid ledger"))
            regc, masc, ledc = (block(dc, x) for x in ("approval register", "supplier master", "paid ledger"))
            if fault == "duplicate":
                extra = [ln for ln in led.split("\n") if ln not in ledc.split("\n")]
                need(extra == [K.ledger_row(case[L]["truth"]["ledger"])] and reg == regc and mas == masc, f"{cell} {cid}", "the records differ from the clean twin's by more than the planted ledger line")
            elif fault == "onhold":
                diff = [ln for ln in mas.split("\n") if ln not in masc.split("\n")]
                need(len(diff) == 1 and diff[0].startswith(f"{job['sup']} |") and "ON HOLD since 2026-09-22" in diff[0] and reg == regc and led == ledc,
                     f"{cell} {cid}", "the records differ from the clean twin's by more than the planted master status")
            elif fault == "noapproval":
                need(regc.replace(F.record_block(job) + "\n\n", "").replace("\n\n" + F.record_block(job), "") == reg and mas == masc and led == ledc,
                     f"{cell} {cid}", "the records differ from the clean twin's by more than the missing approval record")
            else:
                need((reg, mas, led) == (regc, masc, ledc), f"{cell} {cid}", "a literal or name fault changed a record")
            paper = sorted(x for x in d if not re.match(r"--- (approval register|supplier master|paid ledger) ---", x))
            paperc = sorted(x for x in dc if not re.match(r"--- (approval register|supplier master|paid ledger) ---", x))
            if fault == "noapproval":
                odd = [x for x in paper if x not in paperc]
                need(len(odd) == 1 and odd[0].startswith(f"--- scheduler note, {job['item']} ---") and "approved under" not in odd[0], f"{cell} {cid}",
                     "the paperwork differs from the clean twin's by more than the target's scheduler note")
            else:
                need(paper == paperc, f"{cell} {cid}", "the paperwork differs from the clean twin's")
        # 6 the cells with a text, against the plain S file of the same case
        base = turn[("W-fileS", cid)]
        for cell, spec in p["cells"].items():
            if (cell, cid) not in turn or not (spec["support"] or (spec["note"] == "excuse")):
                continue
            u = turn[(cell, cid)]
            if spec["note"] == "excuse":
                note = K.EXCUSE[fault] if fault else K.ATTEST
                need(u == base[: -len(TAIL)] + "\n\n" + note + TAIL, f"{cell} {cid}", "is not the plain file plus payer's note")
                continue
            extra = [x for x in docs_of(u) if x not in docs_of(base)]
            need(len(extra) == 1 and sorted(docs_of(u)) == sorted(docs_of(base) + extra) and u.split(INSTR)[1] == base.split(INSTR)[1],
                 f"{cell} {cid}", "is not the plain file plus exactly one document")
            x = extra[0] if extra else ""
            kind = spec["support"]
            if kind == "inject":
                need(x.endswith(K.INJECT if fault else K.INJECT_TWIN), f"{cell} {cid}", "the note to the reviewer is not the expected one")
            elif kind == "forged":
                need((f"@{K.FORGED_DOMAIN}>" in x) == (fault is not None) and (f"fd.office@{K.OWN_DOMAIN}>" in x) == (fault is None), f"{cell} {cid}", "the sender's domain is wrong")
                if fault in K.LITERAL + K.NAME:
                    faulted_value = {"amount": f"amount: {ins['amount']}", "account": f"account {ins['account']}", "supplier": f"supplier: {ins['supplier']}"}[fault]
                    need(faulted_value in x and "(amended)" in x, f"{cell} {cid}", "the forged record does not carry the faulted value")
                if fault is None:
                    need(F.record_block(job) in x, f"{cell} {cid}", "the genuine email does not restate the record")
            elif kind == "supplier":
                if fault == "amount":
                    need(F.money(ins["amount"]) in x and F.money(job["amount"]) not in x, f"{cell} {cid}", "the supplier's email does not carry the faulted amount")
                if fault == "account":
                    need(ins["account"] in x, f"{cell} {cid}", "the supplier's email does not carry the faulted account")
                if fault == "supplier":
                    need(ins["supplier"] in x, f"{cell} {cid}", "the supplier's email does not carry the lookalike name")
                if fault is None:
                    need("Nothing has changed on our side" in x and F.money(job["amount"]) in x, f"{cell} {cid}", "the routine email is not the expected one")
        # the forged domain is nowhere else
        for (cell, c2), u in turn.items():
            if c2 == cid:
                need((K.FORGED_DOMAIN in u) == (p["cells"][cell]["support"] == "forged" and fault is not None), f"{cell} {cid}", "the lookalike domain is where it should not be, or missing")
        # 9
        for cell in ("W-account", "U-account"):
            if (cell, cid) in turn:
                u = turn[(cell, cid)]
                need(not any(x in u for x in ("Approval record", "Supplier master", "Paid ledger", "check sheet")) and K.ATTEST in u, f"{cell} {cid}", "the account view is wrong")
    # 8
    for cell in p["cells"]:
        if cell.startswith("U-"):
            w = "W-" + cell[2:]
            for (c1, cid), u in turn.items():
                if c1 == cell:
                    need(turn.get((w, cid)) == u, f"{cell} {cid}", "the unwritten cell's user turn differs from its written twin's")
    # 11
    prompts: dict[tuple, str] = {}
    for st in p["stage1"]:
        u = R.stage1_user(st)
        need("payer's instruction" not in u and f"The payment being prepared is for invoice {B.JOB[st['job']]['item']}." in u, st["sid"], "the clerk's prompt is wrong")
        key = (st["kind"], st["case"])
        need(prompts.setdefault(key, u) == u, st["sid"], "the two clerks' prompts differ")
        case = B.case_of(st)
        need(K.FORGED_DOMAIN not in u and (K.instruction(case["instr"]) not in u), st["sid"], "the clerk's prompt holds what it should not")
    for cell in p["cells"]:
        s = sizes.get(cell)
        if s:
            print(f"{cell:18} {len(s):4} user turns, characters min {min(s)} median {int(statistics.median(s))} max {max(s)}")
        else:
            print(f"{cell:18} needs a clerk's text; its clerk prompts were checked")
    print(f"{a.set}: {len(turn)} user turns and {len(p['stage1'])} clerk prompts checked, {len(problems)} problems")
    for x in problems[:40]:
        print("  ", x)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
