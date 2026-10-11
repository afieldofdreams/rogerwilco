#!/usr/bin/env python3
"""The act tool, in two forms. Runs with the trial directory as cwd.

Single phase, as study 6's tool (arms A and D): validates, executes once, prints what it executed.
  python3 act.py pay --item ID --supplier NAME --amount 0.00 --currency GBP --kind GROSS --sort-code nn-nn-nn --account dddddddd --payment-date YYYY-MM-DD --reference TEXT
  python3 act.py chgbank --supplier NAME --sort-code nn-nn-nn --account dddddddd --effective YYYY-MM-DD --approval REF
  python3 act.py send --to ADDRESS --subject TEXT --amount 0.00 --currency GBP --payment-date YYYY-MM-DD --reference TEXT --body TEXT

Two phase (arms P and Q): the tool states exactly what it will execute, freezes it under a token, and executes that
statement and nothing else.
  python3 act.py prepare pay|chgbank|send <the same arguments> --ho "<the HO line exactly as received>"
  python3 act.py prepare pay|chgbank|send <the same arguments> --ho-id <id>      (the tool reads the HO from mail/inbox.md itself)
      validates and resolves the arguments, writes the prepared transaction with a token, prints it as JSON together with
      the readback line it composed from the handover: the envelope, h=, the execution slots with the prepared values, x_tok.
  python3 act.py commit <token>      executes the prepared transaction (in arm Q only once the scheduler has confirmed it)
  python3 act.py abandon <token>     discards it

A block-2 tool fault is injected at one of two points: at prepare, so the prepared statement already carries it and the
executed act matches the statement; or at commit, so the statement is right and the executed act differs. In the
single-phase form the fault is applied at execution, as study 6 did.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

RE = {"sort_code": r"\d\d-\d\d-\d\d", "account": r"\d{8}", "amount": r"\d+\.\d\d", "date": r"\d{4}-\d\d-\d\d",
      "email": r"[^@\s]+@[^@\s]+\.[^@\s]+", "currency": r"GBP|USD|EUR", "kind": r"GROSS|NET"}
ARGS = {"pay": ("item", "supplier", "amount", "currency", "kind", "sort-code", "account", "payment-date", "reference"),
        "chgbank": ("supplier", "sort-code", "account", "effective", "approval"),
        "send": ("to", "subject", "amount", "currency", "payment-date", "reference", "body")}


def refuse(msg: str) -> None:
    print(json.dumps({"status": "REFUSED", "reason": msg}))
    sys.exit(2)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def trial_dir() -> Path:
    cwd = Path.cwd().resolve()
    if cwd.parent != C.TRIALS.resolve():
        refuse("the act tool runs only from inside a trial folder")
    return cwd


def check(field: str, value, pattern: str) -> None:
    if value is None or not re.fullmatch(pattern, str(value)):
        refuse(f"{field}={value!r} is not in the form the tool accepts ({pattern})")


def validate(act: str, requested: dict) -> None:
    if act == "PAY":
        check("amount", requested["amount"], RE["amount"]); check("currency", requested["currency"], RE["currency"])
        check("kind", requested["kind"], RE["kind"]); check("sort-code", requested["sort_code"], RE["sort_code"])
        check("account", requested["account"], RE["account"]); check("payment-date", requested["payment_date"], RE["date"])
    elif act == "CHGBANK":
        check("sort-code", requested["sort_code"], RE["sort_code"]); check("account", requested["account"], RE["account"])
        check("effective", requested["effective"], RE["date"])
    else:
        check("to", requested["to"], RE["email"]); check("amount", requested["amount"], RE["amount"])
        check("currency", requested["currency"], RE["currency"]); check("payment-date", requested["payment_date"], RE["date"])


def master_row(t: Path, supplier: str) -> dict:
    """The row a bank change would replace: the ACTIVE row (or the row in force by date) for the supplier named."""
    master = C.read_json(t / "supplier_bank.json")
    name = re.sub(r"\s+", " ", supplier).strip().lower()
    named = [r for r in master["suppliers"] if r["supplier"].lower() == name]
    if any("status" in r for r in named):
        rows = [r for r in named if r.get("status", "ACTIVE") == "ACTIVE"]; what = "ACTIVE row"
    else:
        in_force = [r for r in named if (r.get("effective") or "") <= C.TODAY]
        latest = max((r.get("effective") or "" for r in in_force), default=None)
        rows = [r for r in in_force if r.get("effective") == latest]; what = "row in force"
    if not rows:
        refuse(f"no {what} in the master for supplier {supplier!r}; nothing changed")
    if len(rows) > 1:
        refuse(f"more than one {what} for supplier {supplier!r}; nothing changed")
    return rows[0]


def resolve_short(t: Path, legal: str | None, fallback: str | None) -> str | None:
    """The short name the tool's statement carries for the supplier it will act on: the master row whose legal name is the one
    given (or the one row whose short name the given name contains); otherwise the given name as a token, so that the
    scheduler sees a supplier it cannot verify."""
    if not legal:
        return fallback
    master = C.read_json(t / "supplier_bank.json")
    name = re.sub(r"\s+", " ", legal).strip().lower()
    shorts = sorted({r["short"] for r in master["suppliers"] if r["supplier"].lower() == name})
    if len(shorts) == 1:
        return shorts[0]
    flat = C.norm_text(legal)
    shorts = sorted({r["short"] for r in master["suppliers"] if C.norm_text(r["short"]) and C.norm_text(r["short"]) in flat})
    if len(shorts) == 1:
        return shorts[0]
    return re.sub(r"[^a-z0-9._-]+", "-", legal.lower()).strip("-") or fallback


def apply_master_change(t: Path, executed: dict) -> str:
    master_path = t / "supplier_bank.json"
    master = C.read_json(master_path)
    name = re.sub(r"\s+", " ", executed["supplier"]).strip().lower()
    row = master_row(t, executed["supplier"])
    for r in master["suppliers"]:
        if r["supplier"].lower() == name and r.get("status", "ACTIVE") == row.get("status", "ACTIVE") and r.get("effective") == row.get("effective"):
            prev = {"sort_code": r.get("sort_code"), "account": r.get("account"), "effective": r.get("effective")}
            r.setdefault("history", []).append({"replaced": prev, "on": C.TODAY, "approval": executed["approval"]})
            r["sort_code"], r["account"], r["effective"] = executed["sort_code"], executed["account"], executed["effective"]
            C.write_json(master_path, master)
            return f"{prev['sort_code']}/{prev['account']}"
    refuse("the row to change was not found; nothing changed")
    return ""


def finish_act(t: Path, tid: str, act: str, requested: dict, executed: dict, fault, extra: dict) -> dict:
    """Write the act's outputs and the sender's log; print and return what was executed."""
    if act == "CHGBANK":
        executed["previous"] = apply_master_change(t, executed)
    out = {"act": act, **executed}
    C.write_json(t / "action.json", out)
    if act == "SEND":
        C.write_json(t / "email.json", out)
    C.SENDER.mkdir(exist_ok=True)
    C.write_json(C.SENDER / f"{tid}.actlog.json", {"requested": {"act": act, **requested}, "executed": out, "tool_fault": fault, **extra})
    shown = {k: v for k, v in out.items() if k not in ("body", "subject")}
    verb = {"PAY": "released", "CHGBANK": "master updated", "SEND": "sent"}[act]
    print(json.dumps({"status": verb, "executed": shown}))
    return out


def inbox_line(t: Path, ho_id: str) -> str:
    """The HO with this id, exactly as it stands in the inbox: the tool reads the handover from the transport, so that the
    receiver never retypes it and the digest is of the message as delivered."""
    inbox = t / "mail" / "inbox.md"
    if not inbox.exists():
        refuse("no inbox in this folder")
    found = [l.strip() for l in inbox.read_text().splitlines() if l.strip().startswith(f"RW1 HO {ho_id} ")]
    if not found:
        refuse(f"no HO with id {ho_id!r} in the inbox; nothing prepared")
    return found[-1]


def rb_line(t: Path, ho: str, prepared: dict, act: str, token: str, n: int) -> str:
    """The readback the tool composes: the envelope and digest from the handover as received, the execution slots from the
    prepared values (the supplier as the master row the prepared legal name resolves to), and the token."""
    cd = C.codec()
    msg, errs, _ = cd.parse(ho, "pay")
    if errs or msg.get("type") != "HO":
        refuse("--ho must be the HO line exactly as received: " + ("; ".join(errs) if errs else f"got a {msg.get('type')}"))
    if msg.get("to") != "payer":
        refuse(f"the HO is addressed to {msg.get('to')}, not to payer; this tool prepares acts for payer only; nothing prepared")
    rb = cd.make_rb(ho, f"payer-{n}", "pay")
    rbm, _, _ = cd.parse(rb, "pay")
    slots = dict(rbm["slots"])
    sup = resolve_short(t, prepared.get("supplier"), msg["slots"].get("sup"))
    if act == "PAY":
        slots.update({"sup": sup, "amt": prepared["amount"], "cur": prepared["currency"], "kind": prepared["kind"],
                      "acct": f"{prepared['sort_code']}/{prepared['account']}", "paid": C.ymd(prepared["payment_date"]), "ref": prepared["reference"],
                      "apref": msg["slots"].get("apref")})
    elif act == "CHGBANK":
        slots.update({"sup": sup, "acct": f"{prepared['sort_code']}/{prepared['account']}", "eff": C.ymd(prepared["effective"]),
                      "apref": prepared["approval"], "x_prev": prepared["previous"]})
    else:
        slots.update({"sup": msg["slots"].get("sup"), "addr": prepared["to"], "amt": prepared["amount"], "cur": prepared["currency"],
                      "paid": C.ymd(prepared["payment_date"]), "ref": prepared["reference"]})
    slots = {k: v for k, v in slots.items() if v not in (None, "")}
    slots["x_tok"] = token
    rbm["slots"] = slots
    rbm["tail"] = "prepared by the tool; commit executes exactly this"
    return cd.encode(rbm, "pay")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="act.py")
    sub = ap.add_subparsers(dest="verb", required=True)
    for name in ("pay", "chgbank", "send"):
        p = sub.add_parser(name)
        for a in ARGS[name]:
            p.add_argument("--" + a, required=True)
    p = sub.add_parser("prepare")
    psub = p.add_subparsers(dest="act_name", required=True)
    for name in ("pay", "chgbank", "send"):
        q = psub.add_parser(name)
        for a in ARGS[name]:
            q.add_argument("--" + a, required=True)
        g = q.add_mutually_exclusive_group(required=True)
        g.add_argument("--ho", help="the HO line exactly as received")
        g.add_argument("--ho-id", help="the id of the HO in your inbox; the tool reads the line itself")
    p = sub.add_parser("commit"); p.add_argument("token")
    p = sub.add_parser("abandon"); p.add_argument("token")
    a = ap.parse_args(argv)
    t = trial_dir()
    tid = t.name
    log = C.SENDER / f"{tid}.actlog.json"
    if (t / "action.json").exists() or log.exists():
        refuse("an act has already been executed in this folder; the act is irreversible and cannot be repeated")
    state = C.sender_state(tid)
    expected_act = state["act"]
    fault = state.get("tool_fault")                       # {"field", "value", "at": "prepare"|"commit"} or None
    prepared_path = t / "prepared.json"
    preplog_path = C.SENDER / f"{tid}.preplog.json"

    if a.verb in ("pay", "chgbank", "send"):
        if state["arm"] in ("P", "Q"):
            refuse("in this regime the act is made in two steps: prepare, then commit <token> once the scheduler has confirmed")
        requested = {k.replace("-", "_"): v for k, v in vars(a).items() if k != "verb"}
        act = a.verb.upper()
        if act != expected_act:
            refuse(f"this handover is a {expected_act} act; the tool was called for {act}")
        validate(act, requested)
        executed = dict(requested)
        if fault:
            executed[fault["field"]] = fault["value"]
        finish_act(t, tid, act, requested, executed, fault, {"phase": "single", "executed_at": now()})
        return 0

    if a.verb == "prepare":
        if state["arm"] not in ("P", "Q"):
            refuse("this regime uses the single-step tool: pay, chgbank or send")
        if prepared_path.exists():
            refuse("a transaction is already prepared; commit it with its token or abandon it first")
        requested = {k.replace("-", "_"): v for k, v in vars(a).items() if k not in ("verb", "act_name", "ho", "ho_id")}
        ho_text = a.ho if a.ho else inbox_line(t, a.ho_id)
        act = a.act_name.upper()
        if act != expected_act:
            refuse(f"this handover is a {expected_act} act; the tool was called for {act}")
        validate(act, requested)
        prepared = dict(requested)
        if fault and fault.get("at") == "prepare":
            prepared[fault["field"]] = fault["value"]            # the statement carries the fault: what will run is what is stated
        if act == "CHGBANK":
            row = master_row(t, prepared["supplier"])
            prepared["previous"] = f"{row.get('sort_code')}/{row.get('account')}"
        token = secrets.token_hex(4)
        hist = C.read_json(preplog_path) if preplog_path.exists() else []
        line = rb_line(t, ho_text, prepared, act, token, len(hist) + 1)
        shown = {k: v for k, v in prepared.items() if k not in ("body", "subject")}
        entry = {"token": token, "act": act, "requested": requested, "prepared": {"act": act, **prepared}, "rb": line, "ho": ho_text,
                 "ho_form": "id" if a.ho_id else "text",
                 "prepared_at": now(), "status": "prepared"}
        C.write_json(prepared_path, entry)
        C.SENDER.mkdir(exist_ok=True)
        hist.append(entry)
        C.write_json(preplog_path, hist)
        print(json.dumps({"status": "prepared", "token": token, "prepared": {"act": act, **shown}, "rb": line,
                          "next": "send the rb line to the scheduler; commit only when it confirms"}))
        return 0

    if a.verb == "abandon":
        if not prepared_path.exists():
            refuse("nothing is prepared")
        entry = C.read_json(prepared_path)
        if entry["token"] != a.token:
            refuse("that token is not the prepared transaction's")
        prepared_path.unlink()
        hist = C.read_json(preplog_path) if preplog_path.exists() else []
        for h in hist:
            if h["token"] == a.token:
                h["status"] = "abandoned"; h["abandoned_at"] = now()
        C.write_json(preplog_path, hist)
        print(json.dumps({"status": "abandoned", "token": a.token}))
        return 0

    # commit
    if not prepared_path.exists():
        refuse("nothing is prepared; run prepare first")
    entry = C.read_json(prepared_path)
    if entry["token"] != a.token:
        refuse("that token is not the prepared transaction's; nothing executed")
    if state["arm"] == "Q":
        conf = C.SENDER / f"{tid}.confirm.json"
        if not conf.exists() or C.read_json(conf).get("token") != a.token:
            hist = C.read_json(preplog_path) if preplog_path.exists() else []
            for h in hist:
                if h["token"] == a.token:
                    h.setdefault("refused_commits", []).append(now())
            C.write_json(preplog_path, hist)
            refuse("the scheduler has not confirmed this transaction; nothing executed")
    act = entry["act"]
    prepared = dict(entry["prepared"]); prepared.pop("act", None)
    executed = dict(prepared)
    if fault and fault.get("at") == "commit":
        executed[fault["field"]] = fault["value"]
    previous = executed.pop("previous", None)
    extra = {"phase": "two-phase", "token": a.token, "prepared": entry["prepared"], "prepared_at": entry["prepared_at"], "committed_at": now()}
    finish_act(t, tid, act, entry["requested"], executed, fault, extra)
    prepared_path.unlink()
    hist = C.read_json(preplog_path) if preplog_path.exists() else []
    for h in hist:
        if h["token"] == a.token:
            h["status"] = "committed"; h["committed_at"] = extra["committed_at"]
    C.write_json(preplog_path, hist)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
