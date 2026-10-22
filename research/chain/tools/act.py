#!/usr/bin/env python3
"""The act tool: the only way the payer executes an act. Runs with the payer's hop folder as cwd.

  python3 act.py pay --item ID --supplier NAME --amount 0.00 --currency GBP --kind GROSS --sort-code nn-nn-nn --account dddddddd --payment-date YYYY-MM-DD --reference TEXT
  python3 act.py chgbank --supplier NAME --sort-code nn-nn-nn --account dddddddd --effective YYYY-MM-DD --approval REF
  python3 act.py send --to ADDRESS --subject TEXT --amount 0.00 --currency GBP --payment-date YYYY-MM-DD --reference TEXT --body TEXT

Validates the arguments, executes once, prints what it executed as JSON. Refuses a second act, and refuses to run anywhere
but the payer's folder of a chain (a relay that tries to act is a measured fault, not a harness one). Study 6's tool, with
no fault injection.
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

RE = {"sort_code": r"\d\d-\d\d-\d\d", "account": r"\d{8}", "amount": r"\d+\.\d\d", "date": r"\d{4}-\d\d-\d\d",
      "email": r"[^@\s]+@[^@\s]+\.[^@\s]+", "currency": r"GBP|USD|EUR", "kind": r"GROSS|NET"}


def refuse(msg: str) -> None:
    print(json.dumps({"status": "REFUSED", "reason": msg}))
    sys.exit(2)


def hop_dir() -> tuple[Path, str, int]:
    cwd = Path.cwd().resolve()
    m = re.fullmatch(r"hop(\d+)", cwd.name)
    if not m or cwd.parent.parent != C.TRIALS.resolve():
        refuse("the act tool runs only from inside an agent's hop folder of a chain")
    return cwd, cwd.parent.name, int(m.group(1))


def check(field: str, value: str, pattern: str) -> None:
    if value is None or not re.fullmatch(pattern, str(value)):
        refuse(f"{field}={value!r} is not in the form the tool accepts ({pattern})")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="act.py")
    sub = ap.add_subparsers(dest="act", required=True)
    p = sub.add_parser("pay")
    for a in ("item", "supplier", "amount", "currency", "kind", "sort-code", "account", "payment-date", "reference"):
        p.add_argument("--" + a, required=True)
    p = sub.add_parser("chgbank")
    for a in ("supplier", "sort-code", "account", "effective", "approval"):
        p.add_argument("--" + a, required=True)
    p = sub.add_parser("send")
    for a in ("to", "subject", "amount", "currency", "payment-date", "reference", "body"):
        p.add_argument("--" + a, required=True)
    a = ap.parse_args(argv)
    t, tid, hop = hop_dir()
    state = C.sender_state(tid)
    if hop != state["K"] + 1:
        refuse("the act tool runs only in the payer's folder; a relay passes the handover on and does not act")
    log = C.SENDER / f"{tid}.actlog.json"
    if (t / "action.json").exists() or log.exists():
        refuse("an act has already been executed in this folder; the act is irreversible and cannot be repeated")
    expected_act = state["act"]
    requested = {k.replace("-", "_"): v for k, v in vars(a).items()}
    act = requested.pop("act").upper()
    if act != expected_act:
        refuse(f"this handover is a {expected_act} act; the tool was called for {act}")
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
    executed = dict(requested)
    master_path = t / "supplier_bank.json"
    if act == "CHGBANK":
        master = C.read_json(master_path)
        name = re.sub(r"\s+", " ", executed["supplier"]).strip().lower()
        named = [r for r in master["suppliers"] if r["supplier"].lower() == name]
        rows = [r for r in named if r.get("status", "ACTIVE") == "ACTIVE"]
        if not rows:
            refuse(f"no ACTIVE row in the master for supplier {executed['supplier']!r}; nothing changed")
        if len(rows) > 1:
            refuse(f"more than one ACTIVE row for supplier {executed['supplier']!r}; nothing changed")
        r = rows[0]
        prev = {"sort_code": r.get("sort_code"), "account": r.get("account"), "effective": r.get("effective")}
        r.setdefault("history", []).append({"replaced": prev, "on": C.TODAY, "approval": executed["approval"]})
        r["sort_code"], r["account"], r["effective"] = executed["sort_code"], executed["account"], executed["effective"]
        C.write_json(master_path, master)
        executed["previous"] = f"{prev['sort_code']}/{prev['account']}"
    out = {"act": act, **executed}
    C.write_json(t / "action.json", out)
    if act == "SEND":
        C.write_json(t / "email.json", out)
    C.SENDER.mkdir(exist_ok=True)
    C.write_json(log, {"requested": {"act": act, **requested}, "executed": out})
    shown = {k: v for k, v in out.items() if k not in ("body", "subject")}
    verb = {"PAY": "released", "CHGBANK": "master updated", "SEND": "sent"}[act]
    print(json.dumps({"status": verb, "executed": shown}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
