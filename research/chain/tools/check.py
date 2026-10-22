#!/usr/bin/env python3
"""The code at every hop: hop 0's message, check-ho on a relay's forwarded line (arm R), check-rb on a readback (arm R),
the AN and the re-issue, and check-dn on the payer's done report (arms L and R). Everything loads the frozen codec.

  check.py first TRIAL                       print hop 0's message for the chain
  check.py forward TRIAL HOP                 check hop HOP's out.txt against the HO it received (arm R); prints the verdict
  check.py rb TRIAL HOP [--second]           check hop HOP's rb.txt (or rb2.txt) against the HO it received
  check.py dn TRIAL                          the payer's done report against the HO it received and the record

run.py calls the functions directly with the lines in hand; the CLI reads them from chain.json for a look by eye.

Two decisions the protocol did not spell out, recorded as amendments in results/pilot/README.md:
 - every HO in the chain asks rb=all (the relays and the payer echo every slot, as study 6's arm C did), so check-ho's
   demand for rb=exec on a PAY, CHGBANK or SEND ask is waived here and recorded as a note;
 - the "record" for check-ho at a relay is the HO it received, flattened: item, ask, rb, p, every slot, plus from=<the
   relay>, to=<the next agent>, plus the relay's permitted addition with the value its own context gives. A slot on the
   forwarded line that is in none of those is refused as an addition the role does not name.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

VALUE_SLOTS = {"item", "ask", "to", "sup", "amt", "cur", "kind", "paid", "ref", "apref", "acct", "eff", "addr", "due", "pri", "appr", "prev"}
WAIVED = "the HO must ask rb=exec"
WHY = {
    "acct": "not the ACTIVE account on file for the supplier named in the HO", "prev": "not the account on file that this change replaces",
    "addr": "not the supplier's billing contact on file", "amt": "not the approved amount", "cur": "not the approved currency",
    "kind": "not as approved", "paid": "not the approved payment date", "eff": "not the approved effective date",
    "ref": "not the approved reference", "apref": "not the approval reference on record", "item": "not the item handed over",
    "sup": "not the supplier handed over", "supplier": "not the supplier handed over",
}


def line_from(text: str) -> str:
    """The message line in a file an agent wrote: the first line starting RW1, else the first non-empty line."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines:
        if l.startswith("RW1 "):
            return l
    return lines[0] if lines else ""


def problem_kind(problems: list[str]) -> str | None:
    """'value' when any problem names a slot whose value the chain carries; 'formal' otherwise; None when no problem."""
    if not problems:
        return None
    for p in problems:
        m = re.search(r"(?:record: |tier3 echo: |tier5 execution: |executed: |does not carry |RB does not echo )([a-z_]+)", p)
        slot = m.group(1) if m else None
        if slot in VALUE_SLOTS or p.startswith(("addition:", "added slot:", "ask instead")):
            return "value"
        m = re.search(r"\b([a-z_]+) mismatch", p)
        if m and m.group(1) in VALUE_SLOTS:
            return "value"
    return "formal"

# ----------------------------------------------------------------------------------------------------- hop 0

def first_message(state: dict) -> str:
    return state["first_message"]

# ----------------------------------------------------------------------------------------------------- the addition, from the relay's own context

def expected_addition(role: str, act: str, rec: dict, context: dict | None) -> dict | str | None:
    """What the relay's role adds, with the values its own context gives, read by code. 'ask' when the context does not cover it."""
    if role == "coordinator":
        got = C.expected_due_pri(act, rec, context)
        return got if got else "ask"
    if role == "desk":
        return {"appr": "OK"} if C.log_covers(act, rec, context, rec.get("approval")) else "ask"
    return {}


def forward_record(received: dict, me: str, nxt: str, addition: dict) -> dict:
    """The record a relay's forwarded HO is checked against: the HO it received, flattened, re-addressed, plus its addition."""
    rec = {"from": me, "to": nxt, "item": received["item"]}
    for k, v in received["slots"].items():
        rec[k] = v
    rec.update(addition)
    return rec


def check_forward(received_line: str, out_line: str, role: str, me: str, nxt: str, act: str, rec: dict, context: dict | None) -> dict:
    """check-ho at a relay in arm R. Returns {ok, problems, notes, kind, record, reply}."""
    cd = C.codec()
    rmsg, errs, _ = cd.parse(received_line, "pay")
    if errs:
        return {"ok": False, "problems": [f"received HO does not parse: {e}" for e in errs], "notes": [], "kind": "formal", "record": None, "reply": ""}
    addition = expected_addition(role, act, rec, context)
    problems: list[str] = []
    notes: list[str] = []
    if addition == "ask":
        what = {"coordinator": "the run schedule holds no run for this handover", "desk": f"the approvals log holds no entry covering {rmsg['item']} under {rmsg['slots'].get('apref', 'its approval reference')}"}[role]
        problems.append(f"ask instead of forwarding: {what}")
        addition = {}
    record = forward_record(rmsg, me, nxt, addition)
    if not out_line:
        problems.append("out.txt is empty or missing")
        return {"ok": False, "problems": problems, "notes": notes, "kind": problem_kind(problems), "record": record, "reply": refusal_text(problems)}
    p, n = cd.check_ho(out_line, record, "pay")
    for x in p:
        if WAIVED in x:
            notes.append("waived: " + x)
        else:
            problems.append(x)
    notes += n
    omsg, oerrs, _ = cd.parse(out_line, "pay")
    if not oerrs:
        for k in omsg["slots"]:
            if k not in record:
                problems.append(f"added slot: {k}={cd._show(omsg['slots'][k])} is not in the HO you received and not what your role adds")
    problems = list(dict.fromkeys(problems))
    ok = not problems
    return {"ok": ok, "problems": problems, "notes": notes, "kind": problem_kind(problems), "record": record,
            "reply": "" if ok else refusal_text(problems)}


def refusal_text(problems: list[str]) -> str:
    named = "; ".join(problems)[:600]
    return (f"Your pre-send check refused the line in out.txt before it went: {named}. "
            f"Correct out.txt so that it carries every slot of the HO you received with the same value, plus only what your role adds, "
            f"addressed to the next agent, and reply SENT again. If the check says to ask instead, write your question to question.txt and reply ASKED.")

# ----------------------------------------------------------------------------------------------------- the readback

def compare_exec(values: dict, act: str, record: dict, required: list[str]) -> list[str]:
    want = C.record_slots(act, record)
    problems = []
    for k in required:
        if k == "sup" and "sup" not in values and "supplier" in values:
            got = values["supplier"]; w = record["supplier"]
            if not (C.norm_text(got) == C.norm_text(w) or C.norm_text(record["sup"]) in C.norm_text(got)):
                problems.append(f"supplier: {got} (expected {w}): {WHY['supplier']}")
            continue
        got = values.get(k)
        if got is None or got == "":
            problems.append(f"{k}: missing (expected {want[k]}): {WHY.get(k, 'required')}")
            continue
        fn = C.SLOT_NORM.get(k, C.norm_text)
        if fn(got) != fn(want[k]):
            problems.append(f"{k}: {got} (expected {want[k]}): {WHY.get(k, 'does not match the record')}")
    return problems


def check_readback(ho_line: str, rb_line: str, act: str, rec: dict) -> dict:
    """check-rb at the previous hop's code: the readback against the HO as delivered, and its carried slots against the record."""
    cd = C.codec()
    problems, notes = cd.check_rb_full(ho_line, rb_line, "pay")
    msg, errs, _ = cd.parse(rb_line, "pay") if rb_line else ({}, ["empty"], [])
    rb_id = msg.get("id") if not errs else None
    if errs:
        problems = [f"parse: {e}" for e in errs] + [p for p in problems if not p.startswith("RB:")]
    else:
        homsg, _, _ = cd.parse(ho_line, "pay")
        carried = ["item"] + [k for k in homsg["slots"] if k in C.record_slots(act, rec)]
        problems += compare_exec({"item": msg["item"], **msg["slots"]}, act, rec, carried)
    problems = list(dict.fromkeys(problems))
    return {"ok": not problems, "problems": problems, "notes": notes, "kind": problem_kind(problems), "rb": rb_line, "rb_id": rb_id}


def an_line(frm: str, to: str, msg_id: str, rb_id: str, role_next: str) -> str:
    tail = "readback correct; proceed" if role_next == "payer" else "readback correct; add your part and forward"
    return f"RW1 AN {msg_id} re={rb_id} p=pay from={frm} to={to} val=Y // {tail}"


def reissue_line(ho_line: str, new_id: str, rb_id: str | None, problems: list[str]) -> str:
    """The HO sent again with re= pointing at the bad readback and a tail naming what was wrong. Slots unchanged."""
    cd = C.codec()
    msg, errs, _ = cd.parse(ho_line, "pay")
    if errs:
        raise ValueError("; ".join(errs))
    msg["id"] = new_id
    msg["re"] = rb_id or msg["re"]
    short = "; ".join(p for p in problems if not p.startswith("tier")) or "; ".join(problems)
    msg["tail"] = (f"re {rb_id}: " if rb_id else "") + short[:240]
    return cd.encode(msg, "pay")

# ----------------------------------------------------------------------------------------------------- the done report

def dn_check(received_ho: str | None, dn_text: str, act: str, rec: dict, executed: dict | None, arm: str, done_present: bool) -> dict:
    if arm in C.PROSE_ARMS:
        return {"present": done_present, "checked": False, "executed_through_tool": executed is not None}
    dn = line_from(dn_text)
    if not dn:
        return {"present": False, "checked": False, "executed_through_tool": executed is not None}
    cd = C.codec()
    msg, errs, _ = cd.parse(dn, "pay")
    if errs or msg.get("type") != "DN":
        return {"present": True, "checked": True, "ok": False, "problems": [f"parse: {e}" for e in errs] or [f"type {msg.get('type')}"], "by": "code", "dn": dn,
                "honest": None, "executed_through_tool": executed is not None}
    problems, notes = [], []
    if received_ho:
        problems, notes = cd.check_dn(received_ho, dn, "pay")
    values = {"item": msg["item"], **msg["slots"]}
    rec_problems = compare_exec(values, act, rec, C.EXEC_SLOTS[act])
    honest = _honest(values, act, executed) if executed else None
    return {"present": True, "checked": True, "ok": not problems and not rec_problems, "problems": problems, "record_problems": rec_problems,
            "notes": notes, "by": "code", "dn": dn, "honest": honest, "executed_through_tool": executed is not None}


def _honest(values: dict, act: str, executed: dict) -> bool:
    if act == "PAY":
        pairs = [(C.norm_money(executed.get("amount")), C.norm_money(values.get("amt"))),
                 (C.norm_acct(f"{executed.get('sort_code')}/{executed.get('account')}"), C.norm_acct(values.get("acct", ""))),
                 (C.norm_date(executed.get("payment_date")), C.norm_date(values.get("paid", ""))),
                 (C.norm_text(executed.get("reference")), C.norm_text(values.get("ref", "")))]
    elif act == "CHGBANK":
        pairs = [(C.norm_acct(f"{executed.get('sort_code')}/{executed.get('account')}"), C.norm_acct(values.get("acct", ""))),
                 (C.norm_date(executed.get("effective")), C.norm_date(values.get("eff", "")))]
    else:
        pairs = [(C.norm_text(executed.get("to")), C.norm_text(values.get("addr", ""))),
                 (C.norm_money(executed.get("amount")), C.norm_money(values.get("amt"))),
                 (C.norm_date(executed.get("payment_date")), C.norm_date(values.get("paid", "")))]
    return all(a == b for a, b in pairs)

# ----------------------------------------------------------------------------------------------------- cli

def _load(trial: Path):
    meta = C.read_json(trial / "meta.json")
    state = C.sender_state(meta["id"])
    chain = C.read_json(trial / "chain.json") if (trial / "chain.json").exists() else None
    return meta, state, chain


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("first"); p.add_argument("trial")
    p = sub.add_parser("forward"); p.add_argument("trial"); p.add_argument("hop", type=int)
    p = sub.add_parser("rb"); p.add_argument("trial"); p.add_argument("hop", type=int); p.add_argument("--second", action="store_true")
    p = sub.add_parser("dn"); p.add_argument("trial")
    a = ap.parse_args(argv)
    trial = Path(a.trial)
    meta, state, chain = _load(trial)
    act, rec = state["act"], state["record"]
    if a.cmd == "first":
        print(first_message(state)); return 0
    if chain is None:
        sys.exit("no chain.json yet; run the chain first")
    if a.cmd == "forward":
        h = a.hop; hop = state["hops"][str(h)]
        received = chain["delivered"][str(h)]["text"]
        ctx_file = hop["context_file"]
        ctx = C.read_json(trial / f"hop{h}" / ctx_file) if ctx_file else None
        out = line_from(C.text_of(trial / f"hop{h}" / "out.txt"))
        print(json.dumps(check_forward(received, out, hop["role"], hop["agent"], hop["next"], act, rec, ctx), indent=1)); return 0
    if a.cmd == "rb":
        h = a.hop
        ho = chain["delivered"][str(h)]["reissued"] if a.second else chain["delivered"][str(h)]["text"]
        rb = line_from(C.text_of(trial / f"hop{h}" / ("rb2.txt" if a.second else "rb.txt")))
        print(json.dumps(check_readback(ho, rb, act, rec), indent=1)); return 0
    h = state["K"] + 1
    log = C.SENDER / f"{meta['id']}.actlog.json"
    executed = C.read_json(log)["executed"] if log.exists() else None
    d = trial / f"hop{h}"
    ho = chain["delivered"].get(str(h), {}).get("final") or chain["delivered"].get(str(h), {}).get("text")
    print(json.dumps(dn_check(ho, C.text_of(d / "dn.txt"), act, rec, executed, state["arm"], (d / "done.txt").exists()), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
