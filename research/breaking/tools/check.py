#!/usr/bin/env python3
"""The code at every hop: hop 0's message, check-ho on a relay's forwarded line (arms R and C), check-rb on a readback the
model wrote (arm R), make-rb by code and the dispute check (arm C), the AN and the re-issue, and the act block executor
(every arm). Everything loads the frozen codec.

  check.py first TRIAL                       print hop 0's message for the chain
  check.py forward TRIAL HOP                 check the line hop HOP forwarded against the HO it received (R, C)
  check.py rb TRIAL HOP [--second]           check hop HOP's readback (R: the model's; C: the code's) against the HO it received
  check.py act TRIAL                         show the payer's act block as parsed and what was executed

run.py calls the functions directly with the text in hand; the CLI reads the chain files for a look by eye.

Decisions the protocol did not spell out, recorded in results/pilot/README.md:
 - every HO in the chain asks rb=all (study 8's amendment): check-ho's demand for rb=exec is waived and noted;
 - the record for check-ho at a relay is the HO it received, flattened, re-addressed, plus the role's addition with the
   value its own context gives when read by code (study 8's forward_record);
 - in R the model writes its readback without h= (it has no codec to compute a digest), so check-rb's integrity tier is
   not applied: an h= the model writes is ignored and noted. R therefore measures the model's echo, not the digest;
 - in C the readback is make-rb from the HO as delivered, h= included; the model replies CONFIRM or DISPUTE: <slot> <value>.
   A dispute is correct (a catch) when the readback's value for that slot is not the HO's; otherwise it is a false alarm
   by the model, answered once with the HO and the readback again, and a second dispute holds the chain;
 - the act block is validated as study 8's act tool validated its arguments (the same patterns), refused once with the
   reason, and a second refusal ends the chain without an act.
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

VALUE_SLOTS = {"item", "ask", "to", "sup", "amt", "cur", "kind", "paid", "ref", "apref", "acct", "eff", "addr", "due", "pri", "appr", "prev", "x_cb"}
WAIVED = "the HO must ask rb=exec"
WHY = {
    "acct": "not the ACTIVE account on file for the supplier named in the HO", "prev": "not the account on file that this change replaces",
    "addr": "not the supplier's billing contact on file", "amt": "not the approved amount", "cur": "not the approved currency",
    "kind": "not as approved", "paid": "not the approved payment date", "eff": "not the approved effective date",
    "ref": "not the approved reference", "apref": "not the approval reference on record", "item": "not the item handed over",
    "sup": "not the supplier handed over", "supplier": "not the supplier handed over",
}


def line_from(text: str) -> str:
    """The message line in a reply: the first line starting RW1, else the first non-empty line."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines:
        if l.startswith("RW1 "):
            return l
    return lines[0] if lines else ""


def is_ask(reply: str) -> bool:
    """ASK on the first non-empty line (the reply instruction), or a first line that is an AQ or UN line."""
    lines = [l.strip() for l in (reply or "").splitlines() if l.strip()]
    if not lines:
        return False
    first = lines[0]
    if re.match(r"^\**ASK\**(\s|:|$)", first):
        return True
    return bool(re.match(r"^RW1 (AQ|UN) ", first))


def question_of(reply: str) -> str:
    lines = [l.strip() for l in (reply or "").splitlines() if l.strip()]
    if lines and re.match(r"^\**ASK\**(\s|:|$)", lines[0]):
        rest = re.sub(r"^\**ASK\**:?\s*", "", lines[0])
        return "\n".join(([rest] if rest else []) + lines[1:])
    return "\n".join(lines)


def problem_kind(problems: list[str]) -> str | None:
    """'value' when any problem names a slot whose value the chain carries; 'formal' otherwise; None when no problem."""
    if not problems:
        return None
    for p in problems:
        m = re.search(r"(?:record: |tier3 echo: |tier5 execution: |executed: |does not carry |RB does not echo )([a-z_]+)", p)
        slot = m.group(1) if m else None
        if slot in VALUE_SLOTS or p.startswith(("addition:", "added slot:", "ask instead", "dispute:")):
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
    """check-ho at a relay in arms R and C. Returns {ok, problems, notes, kind, record, reply}."""
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
        problems.append("the reply carried no line")
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
    return (f"Your pre-send check refused the line you replied with before it went: {named}. "
            f"Reply with the corrected line, one line, carrying every slot of the HO you received with the same value, plus only what your role adds, "
            f"addressed to the next agent. If the check says to ask instead, reply ASK and your question.")

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


def check_readback(ho_line: str, rb_line: str, act: str, rec: dict, waive_digest: bool = True) -> dict:
    """check-rb at the previous hop's code: the readback against the HO as delivered, and its carried slots against the
    record. With waive_digest (arm R, text-only) the integrity tier is noted, not applied: the model cannot compute h=."""
    cd = C.codec()
    problems, notes = cd.check_rb_full(ho_line, rb_line, "pay")
    if waive_digest:
        kept = []
        for p in problems:
            if p.startswith("tier2 integrity"):
                notes.append("waived (text-only R: the model cannot compute a digest): " + p)
            else:
                kept.append(p)
        problems = kept
    msg, errs, _ = cd.parse(rb_line, "pay") if rb_line else ({}, ["empty"], [])
    rb_id = msg.get("id") if not errs else None
    if errs:
        problems = [f"parse: {e}" for e in errs] + [p for p in problems if not p.startswith("RB:")]
    else:
        homsg, _, _ = cd.parse(ho_line, "pay")
        carried = ["item"] + [k for k in homsg["slots"] if k in C.record_slots(act, rec)]
        problems += compare_exec({"item": msg["item"], **msg["slots"]}, act, rec, carried)
    problems = list(dict.fromkeys(problems))
    return {"ok": not problems, "problems": problems, "notes": notes, "kind": problem_kind(problems), "rb": rb_line, "rb_id": rb_id, "by": "model"}


def code_readback(ho_line: str, me: str, n: int = 1) -> str:
    """Arm C: the readback composed by the relay's or the payer's code from the HO as delivered, h= included."""
    return C.codec().make_rb(ho_line, f"{me}-{n}", "pay")


NOT_ECHOED = ("rb", "acc", "exp", "tail")      # what make-rb leaves off a readback by design (the codec's tier 3 does not demand them)
CONFIRM_RE = re.compile(r"\bCONFIRM(ED)?\b", re.I)
DISPUTE_RE = re.compile(r"\bDISPUTE[DS]?\b\**\s*[:\-]?\s*`?([a-z_]+)`?\s*[=:]?\s*(\S*)", re.I)


def parse_confirm(reply: str) -> dict:
    """The relay's or payer's answer to the code-composed readback: confirm, dispute (with slot and value), ask, or other.
    Confirm: the first non-empty line carries the word CONFIRM and no line disputes (a small model writes "RW1 CONFIRM"
    and lists slots; the word is the answer). Dispute: a line carries DISPUTE followed by a slot name and a value; a
    dispute naming nothing ("DISPUTE: none") is a confirm."""
    lines = [l.strip() for l in (reply or "").splitlines() if l.strip()]
    first = lines[0] if lines else ""
    if is_ask(reply):
        return {"answer": "ask"}
    disputes = [m for l in lines for m in [DISPUTE_RE.search(l)] if m]
    if disputes:
        m = disputes[0]
        slot = m.group(1).lower()
        if slot in ("none", "nothing", "no", "nil") and CONFIRM_RE.search(first) is None:
            return {"answer": "confirm"}
        if slot in ("none", "nothing", "no", "nil"):
            return {"answer": "confirm"}
        return {"answer": "dispute", "slot": slot, "value": m.group(2).strip("`'\".,;")}
    if CONFIRM_RE.search(first):
        return {"answer": "confirm"}
    return {"answer": "other"}


def check_dispute(ho_line: str, rb_line: str, slot: str, value: str) -> dict:
    """A dispute names a slot and the value the HO carries. It is a catch when the readback's value for the slot differs
    from the HO's; it is a false alarm when the readback carries exactly what the HO carries."""
    cd = C.codec()
    ho, e1, _ = cd.parse(ho_line, "pay")
    rb, e2, _ = cd.parse(rb_line, "pay")
    if e1 or e2:
        return {"ok": False, "problems": [f"parse: {e}" for e in e1 + e2], "kind": "formal", "rb": rb_line, "rb_id": None, "by": "code", "dispute": {"slot": slot, "value": value}}
    hflat = {"item": ho["item"], "from": ho["from"], "to": ho["to"], "id": ho["id"], **ho["slots"]}
    rflat = {"item": rb["item"], **rb["slots"]}
    hv = cd._show(hflat[slot]) if slot in hflat else None
    rv = cd._show(rflat[slot]) if slot in rflat else None
    if slot in ("h", "re", "from", "to", "id"):
        problems = [f"dispute: {slot} is the readback's own envelope, not a value of the HO"]
        catch = False
    elif slot in NOT_ECHOED:
        problems = [f"dispute: the readback does not repeat {slot}= by design (it echoes the HO's item, ask, p and every value slot, with h=); every value the HO carries is in it"]
        catch = False
    elif hv is None and rv is None:
        problems = [f"dispute: neither the HO nor the readback carries a slot {slot}"]
        catch = False
    elif hv == rv:
        problems = [f"dispute: the readback carries {slot}={rv}, exactly what the HO carries"]
        catch = False
    else:
        problems = []
        catch = True
    # a dispute is never 'ok' as a readback: a catch holds the chain at a readback that did not match, a false alarm is answered once
    return {"ok": False, "catch": catch, "problems": problems or [f"dispute: {slot}: readback {rv} is not the HO's {hv}"], "kind": "value" if catch else "false-dispute",
            "rb": rb_line, "rb_id": rb["id"], "by": "code", "dispute": {"slot": slot, "value": value, "ho_value": hv, "rb_value": rv}}


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

# ----------------------------------------------------------------------------------------------------- the act block

RE = {"sort_code": r"\d\d-\d\d-\d\d", "account": r"\d{8}", "amount": r"\d+\.\d\d", "date": r"\d{4}-\d\d-\d\d",
      "email": r"[^@\s]+@[^@\s]+\.[^@\s]+", "currency": r"GBP|USD|EUR", "kind": r"GROSS|NET"}
PATTERN_OF = {"PAY": {"amount": "amount", "currency": "currency", "kind": "kind", "sort_code": "sort_code", "account": "account", "date": "date"},
              "CHGBANK": {"sort_code": "sort_code", "account": "account", "effective": "date"},
              "SEND": {"to": "email", "amount": "amount", "currency": "currency", "date": "date"}}


def parse_act_block(reply: str) -> dict | None:
    """ACT on a line, then key: value lines. None when there is no ACT line. Returns {"values": {...}, "extra": [...], "second": bool}."""
    lines = [l.strip() for l in (reply or "").splitlines()]
    starts = [i for i, l in enumerate(lines) if re.match(r"^\**\s*ACT\s*\**\s*:?\s*$", l)]
    if not starts:
        return None
    values: dict = {}
    extra: list[str] = []
    for l in lines[starts[0] + 1:]:
        if not l or l.startswith("```"):
            continue
        if re.match(r"^\**\s*ACT\s*\**\s*:?\s*$", l):
            break
        m = re.match(r"^[-*\s]*`?([A-Za-z_ ]+?)`?\s*[:=]\s*(.*?)\s*$", l)
        if m and m.group(1).strip().lower().replace(" ", "_") in {k for keys in C.ACT_KEYS.values() for k in keys} | {"body", "item"}:
            key = m.group(1).strip().lower().replace(" ", "_")
            if key not in values:
                values[key] = m.group(2).strip().strip("`'\"")
        else:
            extra.append(l)
    return {"values": values, "extra": extra, "second": len(starts) > 1}


def validate_act(values: dict, expected_act: str) -> str | None:
    """None when the block is acceptable; else the reason, as study 8's act tool gave it."""
    act = (values.get("act") or "").strip().lower()
    if not act:
        return "the block carries no act: line"
    if act.upper() != expected_act:
        return f"this handover is a {expected_act} act; the block says act: {act}"
    missing = [k for k in C.ACT_KEYS[expected_act] if not values.get(k)]
    if missing:
        return "missing: " + ", ".join(f"{k}:" for k in missing)
    for k, pat in PATTERN_OF[expected_act].items():
        if not re.fullmatch(RE[pat], str(values[k])):
            return f"{k}={values[k]!r} is not in the form the block accepts ({RE[pat]})"
    return None


def execute_act(trial: Path, state: dict, values: dict) -> dict:
    """Execute once against the master in the payer's folder; record what was executed. Refuses a second act."""
    tid, act = state["id"], state["act"]
    hp = trial / f"hop{state['K'] + 1}"
    log = C.SENDER / f"{tid}.actlog.json"
    if log.exists() or (hp / "action.json").exists():
        return {"status": "REFUSED", "reason": "an act has already been executed for this handover; the act is irreversible and cannot be repeated"}
    executed = {k: values[k] for k in C.ACT_KEYS[act]}
    for k in ("body", "item"):
        if values.get(k):
            executed[k] = values[k]
    if act == "CHGBANK":
        master_path = hp / "supplier_bank.json"
        master = C.read_json(master_path)
        name = re.sub(r"\s+", " ", executed["supplier"]).strip().lower()
        named = [r for r in master["suppliers"] if r["supplier"].lower() == name]
        rows = [r for r in named if r.get("status", "ACTIVE") == "ACTIVE"]
        if not rows:
            return {"status": "REFUSED", "reason": f"no ACTIVE row in the master for supplier {executed['supplier']!r}; nothing changed"}
        if len(rows) > 1:
            return {"status": "REFUSED", "reason": f"more than one ACTIVE row for supplier {executed['supplier']!r}; nothing changed"}
        r = rows[0]
        prev = {"sort_code": r.get("sort_code"), "account": r.get("account"), "effective": r.get("effective")}
        r.setdefault("history", []).append({"replaced": prev, "on": C.TODAY, "approval": executed["approval"]})
        r["sort_code"], r["account"], r["effective"] = executed["sort_code"], executed["account"], executed["effective"]
        C.write_json(master_path, master)
        executed["previous"] = f"{prev['sort_code']}/{prev['account']}"
    out = {"act": act, **{k: v for k, v in executed.items() if k != "act"}}
    C.write_json(hp / "action.json", out)
    if act == "SEND":
        C.write_json(hp / "email.json", out)
    C.SENDER.mkdir(exist_ok=True)
    C.write_json(log, {"requested": {"act": act, **values}, "executed": out})
    verb = {"PAY": "released", "CHGBANK": "master updated", "SEND": "sent"}[act]
    return {"status": verb, "executed": out}


def act_refusal_text(reason: str) -> str:
    return (f"Your act block was refused: {reason}. Nothing was executed. Reply with a corrected ACT block in the form your brief gives, "
            f"one key: value per line, or reply ASK and your question.")

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
    p = sub.add_parser("act"); p.add_argument("trial")
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
        received = chain["delivered"][str(h)]["final"]
        ctx_file = hop["context_file"]
        ctx = C.read_json(trial / f"hop{h}" / ctx_file) if ctx_file else None
        out = line_from(C.text_of(trial / f"hop{h}" / "out.txt"))
        print(json.dumps(check_forward(received, out, hop["role"], hop["agent"], hop["next"], act, rec, ctx), indent=1)); return 0
    if a.cmd == "rb":
        h = a.hop
        ho = chain["delivered"][str(h)]["reissued"] if a.second else chain["delivered"][str(h)]["text"]
        rb = line_from(C.text_of(trial / f"hop{h}" / ("rb2.txt" if a.second else "rb.txt")))
        print(json.dumps(check_readback(ho, rb, act, rec), indent=1)); return 0
    log = C.SENDER / f"{meta['id']}.actlog.json"
    print(json.dumps(C.read_json(log) if log.exists() else {"executed": None}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
