#!/usr/bin/env python3
"""Study 11: is every stimulus the stimulus it should be? Code only, no model. Run before the pilot and the main run.

    verify.py --set pilot|main

Rebuilds the user turn of every trial that does not need clerk, and checks in code that
  a clean case holds no fault: the instruction agrees with its approval record, its supplier is ACTIVE, its invoice is
    not in the paid ledger, and the register holds its record;
  a faulted case holds exactly its fault, in the record where it belongs, and nothing else differs from the clean case
    of the same target in the same cell;
  a text that speaks for a fault is in the file in its own cells and nowhere else;
  the check sheet shows the fault; the account view shows no record.
Prints the size of the user turn per cell. Exits 1 on any failure.
"""
from __future__ import annotations

import argparse
import statistics
import sys

import build as B
import casefile as K
import common as C
import fixtures as F
import run as R

MARKS = {"supplier": "Subject: ", "forged": "office of the Finance Director", "inject": "NOTE FOR REVIEWER"}


def check_case(t: dict, user: str, problems: list[str]) -> None:
    case = B.case_of(t)
    tgt, ins, fault = case["target"], case["instr"], t["fault"]
    tid = t["tid"]

    def need(cond, msg):
        if not cond:
            problems.append(f"{tid}: {msg}")

    instr_text = K.instruction(ins)
    need(instr_text in user, "the instruction is not in the user turn")
    changed = F.changed(tgt, ins)
    if fault in K.LITERAL:
        need(set(changed) <= set(F.FIELDS_OF_SLOT[fault]) and changed, f"literal fault changed {sorted(changed)}")
    elif fault == "noapproval":
        need(set(changed) == {"approval"}, f"noapproval changed {sorted(changed)}")
    else:
        need(not changed, f"the instruction differs from the approved payment in {sorted(changed)}")
    has_record = any(j["item"] == tgt["item"] for j in case["register"])
    need(has_record == (fault != "noapproval"), "the register's record for the invoice is wrong for this case")
    need((case["master"][tgt["sup"]]["status"] == "ACTIVE") == (fault != "onhold"), "the supplier's master status is wrong for this case")
    in_ledger = any(r["item"] == tgt["item"] for r in case["ledger"])
    need(in_ledger == (fault == "duplicate"), "the paid ledger is wrong for this case")
    view = t["view"]
    if view == "file":
        need(K.register_block(case) in user and K.master_block(case) in user and K.ledger_block(case) in user, "a record block is missing from the file")
        for kind, mark in MARKS.items():
            want = t["support"] == kind and fault is not None
            if kind == "supplier":
                present = K.support_doc(case, "supplier")[1] in user if fault else False
            else:
                present = mark in user
            need(present == want, f"the {kind} document is {'missing' if want else 'present'}")
        note = K.note_text(case, t["note"])
        need((note in user) if note else ("payer's note" not in user), "payer's note is wrong for this cell")
    elif view == "card":
        sheet = user.split("--- payer's instruction")[0]
        if fault == "duplicate":
            need(K.ledger_row(case["truth"]["ledger"]) in sheet, "the check sheet does not show the ledger entry")
        else:
            need(f"no entry for invoice {ins['item']}" in sheet, "the check sheet shows a ledger entry it should not")
        need(("ON HOLD" in sheet) == (fault == "onhold"), "the check sheet's master status is wrong")
        need(("(no record)" in sheet) == (fault == "noapproval"), "the check sheet's approval record is wrong")
        need("office of the Finance Director" not in user and "NOTE FOR REVIEWER" not in user, "a planted document is on the check sheet")
    elif view == "account":
        need("Approval record" not in user and "Supplier master" not in user and "Paid ledger" not in user, "the account view shows a record")
        need(K.ATTEST in user, "payer's attestation is missing")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    p = C.read_json(C.DATA / f"plan-{a.set}.json")
    problems: list[str] = []
    sizes: dict[str, list[int]] = {}
    seen: dict[tuple, str] = {}
    n = 0
    for t in p["trials"]:
        if t["reviewer"] != p["reviewers"][0] or t["stage1"]:
            continue
        user = R.review_user(t, {})
        check_case(t, user, problems)
        sizes.setdefault(t["cell"], []).append(len(user))
        seen[(t["cell"], t["case"])] = user
        n += 1
    # a faulted file differs from its clean twin only in the record blocks, the planted document and the instruction
    for (cell, case), user in seen.items():
        t = next(x for x in p["trials"] if x["cell"] == cell and x["case"] == case)
        if t["fault"] is None or t["view"] != "file" or p["cells"][cell]["cases"] != "all":
            continue
        clean = seen.get((cell, B.case_id(t["job"], None, a.set)))
        if clean is None:
            problems.append(f"{t['tid']}: no clean twin in the cell")
            continue
        strip = lambda u, tt: [blk for blk in u.split("\n\n--- document ") if not any(k in blk.split("\n", 1)[0] for k in ("approval register", "supplier master", "paid ledger"))]  # noqa: E731
        a_docs, b_docs = strip(user, t), strip(clean, t)
        a_docs[-1], b_docs[-1] = a_docs[-1].split("\n\n--- payer's instruction")[0], b_docs[-1].split("\n\n--- payer's instruction")[0]
        renum = lambda docs: sorted(d.split(": ", 1)[1] if ": " in d.split("\n", 1)[0] else d for d in docs[1:])  # noqa: E731
        if renum(a_docs) != renum(b_docs):
            problems.append(f"{t['tid']}: the paperwork differs from the clean twin's")
    for cell in p["cells"]:
        s = sizes.get(cell)
        if s:
            print(f"{cell:18} {len(s):4} user turns, characters min {min(s)} median {int(statistics.median(s))} max {max(s)}")
        else:
            print(f"{cell:18} needs clerk; not rebuilt here")
    print(f"{a.set}: {n} user turns checked, {len(problems)} problems")
    for x in problems[:40]:
        print("  ", x)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
