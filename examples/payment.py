"""A payment handed from one agent to another with rogerwilco's three checks around it.

    pip install rogerwilco
    python examples/payment.py            # roger, wilco: the payment goes out
    python examples/payment.py --fault    # the tool resolves the wrong account; the check stops it before any money moves

The scheduler hands the job over as a line; the line is checked against the approved record before it is sent.
The payment tool prepares the payment and states, as a readback line, exactly what it will execute; the scheduler
checks that statement and only then confirms. The tool commits what it stated and nothing else, and its done report
is checked against the plan afterwards.
"""
import secrets
import sys

import rogerwilco as rw

PROFILE = "pay"   # the accounts-payable profile: it names the values a payment is executed with

# The approved record: what the finance director signed off. In your system this comes from your database.
RECORD = {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP",
          "kind": "GROSS", "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}


# ---------------------------------------------------------------- the sender
def hand_over() -> str:
    """Write the job as a line, from the record, and check it before it goes (check 1)."""
    slots = {k: v for k, v in RECORD.items() if k not in ("to", "item")}
    ho = rw.encode({"type": "HO", "id": "scheduler-1", "from": "scheduler", "to": RECORD["to"], "item": RECORD["item"],
                    "slots": {"p": PROFILE, "rb": ["exec"], **slots}}, PROFILE)
    problems, _notes = rw.check_ho(ho, RECORD, PROFILE)
    if problems:
        raise SystemExit(f"not sent: {problems}")
    return ho


# ---------------------------------------------------------------- the receiver's tool: prepare, then commit
class PaymentTool:
    """Your payment tool, given two phases. prepare() resolves the payment and states it as a readback line;
    commit() executes exactly what was stated, and only with the sender's confirmation."""

    def __init__(self, fault: bool = False):
        self.pending: dict[str, dict] = {}
        self.fault = fault

    def prepare(self, ho_line: str) -> tuple[str, str]:
        ho, errors, _ = rw.parse(ho_line, PROFILE)
        if errors or ho["to"] != "payer":
            raise ValueError(f"refused: {errors or 'not addressed to the payer'}")
        values = {k: ho["slots"][k] for k in ("sup", "amt", "cur", "kind", "acct", "paid", "ref", "apref")}
        if self.fault:
            values["acct"] = "40-12-88/61102983"   # the tool resolves a lookalike account
        token = secrets.token_hex(4)
        self.pending[token] = values
        statement = rw.encode({"type": "RB", "id": "payer-1", "re": ho["id"], "from": "payer", "to": ho["from"],
                               "item": ho["item"], "slots": {"p": PROFILE, "ask": "PAY", "h": rw.digest(ho_line, PROFILE),
                                                             **values}}, PROFILE)
        return token, statement

    def commit(self, token: str, confirmed: bool) -> str:
        if not confirmed or token not in self.pending:
            raise PermissionError("no confirmation for this token: nothing is paid")
        values = self.pending.pop(token)
        # ... call your bank here with `values`, and nothing else ...
        return rw.encode({"type": "DN", "id": "payer-2", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                          "item": RECORD["item"], "slots": {"p": PROFILE, "out": "OK", **values}}, PROFILE)


# ---------------------------------------------------------------- the flow
def main(fault: bool) -> int:
    ho = hand_over()                                                  # check 1: the line against the record
    tool = PaymentTool(fault)
    token, statement = tool.prepare(ho)
    problems, _notes = rw.check_rb_full(ho, statement, PROFILE)       # check 2: the tool's statement against the plan
    if problems:
        print("held:", problems)
        return 1
    dn = tool.commit(token, confirmed=True)
    problems, _notes = rw.check_dn(ho, dn, PROFILE, rb_line=statement)  # check 3: what was done against the plan
    print("recall the payment:" if problems else "roger, wilco:", problems or dn)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main("--fault" in sys.argv))
