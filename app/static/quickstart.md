# Integrate rogerwilco

rogerwilco puts three checks, run by a program, around anything an AI agent does that cannot be undone: a payment, a change of bank details, an email to a customer, a deploy. The job travels as one typed line. The line is checked against the approved record before it is sent. The tool that acts states exactly what it will do, and that statement is checked before it runs. What it actually did is checked afterwards. This page is for the developer wiring it in, and for the coding agent doing it on their behalf.

> **If you are a coding agent**, read [/llms-full.txt](https://rogerwilco.crox.io/llms-full.txt): this guide, the skill and the full protocol in one file. The prompt under [Hand it to your coding agent](#agent) is a complete brief.

## Install

```sh
pip install rogerwilco
```

Python 3.10 or later, standard library only, no dependencies. Until the first release is on PyPI: `pip install git+https://github.com/afieldofdreams/rogerwilco`. The same package gives you a command line, `rogerwilco`, and every function is also a hosted [HTTP endpoint](#http) for other languages.

## Where the checks go

| Check | Runs | Catches | Function |
|---|---|---|---|
| 1. The line against the record | before the job is sent | a wrong digit, date, account or addressee typed by the sender | `check_ho` |
| 2. The tool's statement against the plan | after the tool prepares, before it acts | a wrong account or value the receiver or the tool resolved | `check_rb_full` |
| 3. What was done against the plan | after the act | a tool that did something other than it stated | `check_dn` |

In our studies check 1 caught every mistake planted in the sender's line; check 2, on a tool that states what it will do, took wrong payments caused by the tool from 59 in 60 to none; check 3 flagged every fault injected at the moment of execution, after the fact. The [home page](https://rogerwilco.crox.io/) tells those tests one at a time.

## 1. Write the job as a line, and check it before it goes

Build the line from the approved record with `rw.encode`, then compare the two with `rw.check_ho`. Under a profile that names execution slots for the ask, `PAY` here, the check also insists the line asks for an execution readback, `rb=exec`.

```python
import rogerwilco as rw

record = {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP", "kind": "GROSS", "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}   # the approved record, from your database

ho = rw.encode({"type": "HO", "id": "scheduler-1", "from": "scheduler", "to": "payer", "item": record["item"],
                "slots": {"p": "pay", "rb": ["exec"], **{k: v for k, v in record.items() if k not in ("to", "item")}}}, "pay")
problems, notes = rw.check_ho(ho, record, "pay")
if problems:
    raise RuntimeError(problems)      # never send it
```

The line it builds:

```
RW1 HO scheduler-1 from=scheduler to=payer item=inv:MD-2026-057 ask=PAY p=pay rb=exec sup=marlow amt=5400.00 cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929
```

If a line was drafted by a model rather than built from the record, this is where a typo stops. With two digits swapped in the account:

```
['record: acct mismatch: record 40-12-88/61102938 vs HO 40-12-88/61102983']
```

## 2. Make the tool prepare, and check what it says it will do

Give the tool that acts two phases. `prepare` resolves every value it will execute, including anything it looks up, such as the account on file, freezes them under a token and returns them as a readback line, `RB`. Nothing has happened yet. The sender checks that statement against the plan with `rw.check_rb_full`.

```python
# inside your payment tool: resolve what will actually run, freeze it under a token, state it as a line
values = resolve_payment(ho)                    # supplier, amount, account looked up on file, date, references
token = secrets.token_hex(4)
pending[token] = values
statement = rw.encode({"type": "RB", "id": "payer-1", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                       "item": "inv:MD-2026-057", "slots": {"p": "pay", "ask": "PAY", "h": rw.digest(ho, "pay"), **values}}, "pay")

# back on the sender's side: check the statement against the plan
problems, notes = rw.check_rb_full(ho, statement, "pay")
```

The tool's statement, carrying `h=`, a fingerprint of the line it received:

```
RW1 RB payer-1 re=scheduler-1 from=payer to=scheduler item=inv:MD-2026-057 ask=PAY p=pay h=a7a82de76607 sup=marlow amt=5400.00 cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929
```

If the tool resolved a lookalike account, the check refuses it and nothing is paid:

```
['tier5 execution: acct mismatch: HO 40-12-88/61102938 vs RB 40-12-88/61102983']
```

Read the statement from the tool itself. Do not have a model copy it across: a small model in our study altered the tool's line in 51 of 129 relays.

## 3. Commit only on a yes, then check what was done

`commit` executes the frozen values and nothing else, and refuses without the sender's confirmation of that token. Its done report, `DN`, carries the values as executed, and `rw.check_dn` compares them with the plan.

```python
def commit(token, confirmed):
    if not confirmed or token not in pending:
        raise PermissionError("no confirmation for this token: nothing is paid")
    values = pending.pop(token)
    bank.pay(**values)                           # exactly what was stated, nothing else
    return rw.encode({"type": "DN", "id": "payer-2", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                      "item": "inv:MD-2026-057", "slots": {"p": "pay", "out": "OK", **values}}, "pay")

dn = commit(token, confirmed=not problems)
problems, notes = rw.check_dn(ho, dn, "pay", rb_line=statement)
```

A tool that states one thing and does another at the last moment is caught here, after the fact, so this is where you alert and reverse:

```
['executed: amt mismatch: plan 5400.00 vs DN 5100.00']
```

## The whole flow, runnable

[examples/payment.py](https://github.com/afieldofdreams/rogerwilco/blob/main/examples/payment.py) puts the three steps together with a toy two-phase payment tool. Run it, then run it with the tool resolving the wrong account.

```python
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

```

```sh
python examples/payment.py
python examples/payment.py --fault
```

```
roger, wilco: RW1 DN payer-2 re=scheduler-1 from=payer to=scheduler item=inv:MD-2026-057 out=OK p=pay sup=marlow amt=5400.00 cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929
held: ['tier5 execution: acct mismatch: HO 40-12-88/61102938 vs RB 40-12-88/61102983']
```

## Teach the receiving model the format

A model that has to read or write lines needs about 400 tokens of legend in its prompt and nothing installed. Pass the profile so it gets the domain's codes.

```python
system_prompt += rw.legend("pay")
```

```
rogerwilco RW1. One line per message: RW1 <TYPE> <id> [re=<id>] from=<agent> to=<agent> [item=<ref>] key=value ... [// tail]. No spaces in values; lists join with +; dates YYYYMMDD; tail is free text, 300 chars max.
HO handoff: requires from to item ask; optional re due pri conf keep art ctx rb acc keys sup po amt cur kind dec flag appr var n src net vat acct paid ref eff apref addr
RB readback: requires re from to item ask; optional due eta h do acc not asm sup po amt cur kind dec flag appr var n src net vat acct paid ref eff apref addr prev
...
```

Where the receiver is a model that cannot run your two-phase tool, it can still read back the values it will act with: `rw.make_rb(ho, "payer-1", "pay")` builds a correct readback for a receiver that runs code, and the sender checks it the same way. On strong models this caught little, because they read well; on a weak model, the tool's statement did better than any readback the model wrote.

## Your own domain: profiles

A profile adds the codes and slots for one kind of work and names, for each irreversible ask, the values it is executed with. That list is what checks 1 to 3 compare. Four ship with the package: `pay` (accounts payable), `clin` (clinical statements), `deploy` and `pform` (a knowledge-graph workflow). To make your own, copy `rogerwilco/profiles/pform.json`, list your asks and slots, and put the irreversible ones under `exec`. A profile may add codes; it may not redefine the core ones. [Profiles](https://rogerwilco.crox.io/profiles) shows the same line doing four kinds of work.

## Hand it to your coding agent

Paste this into Claude Code, Cursor or any coding agent working in your repository. It is the whole brief.

```text
Integrate rogerwilco (pip install rogerwilco) around every irreversible action in this codebase: payments,
bank-detail changes, outbound emails, deletions, deploys. Read https://rogerwilco.crox.io/llms-full.txt first.
1. Find each place an agent hands another agent or a tool a job that cannot be undone.
2. Write that job as an RW1 HO line from the approved record with rw.encode, and refuse to send it unless
   rw.check_ho(ho, record, profile) returns no problems.
3. Split the tool that acts into prepare and commit. prepare resolves every value it will execute, freezes them under
   a token and returns them as an RB line; commit executes the frozen values only, and only after the sender's check.
4. The sender runs rw.check_rb_full(ho, statement, profile) on that statement and confirms the token only when it
   returns no problems. Read the statement from the tool, not from a model's retelling of it.
5. After commit, build a DN line from what the tool actually did and run rw.check_dn(ho, dn, profile, rb_line=statement);
   any problem means alert and reverse.
6. If the domain is not payments, copy rogerwilco/profiles/pform.json to a new profile and list the execution slots
   for each irreversible ask under "exec".
Add tests that plant a wrong value at each of the three checks and assert it is caught.
```

## Not Python: the HTTP API

Every function is a JSON endpoint at this site, no key and no sign-up, for any language: `POST /check-ho`, `/check-rb`, `/check-dn`, `/make-rb`, `/validate`, `/digest`, `/to-json`, `/from-json`, `/gate`, and `GET /legend`. Check 1 with the swapped digits:

```sh
curl -s https://rogerwilco.crox.io/check-ho -H 'content-type: application/json' -d '{
  "profile": "pay",
  "ho": "RW1 HO scheduler-1 from=scheduler to=payer item=inv:MD-2026-057 ask=PAY p=pay rb=exec sup=marlow amt=5400.00 cur=GBP kind=GROSS acct=40-12-88/61102983 paid=20261002 ref=MD-2026-057 apref=FD-0929",
  "record": {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP", "kind": "GROSS", "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}
}'
```

```
{"ok": false, "problems": ["record: acct mismatch: record 40-12-88/61102938 vs HO 40-12-88/61102983"], "notes": []}
```

The full reference, with every input and output, is at [/docs](https://rogerwilco.crox.io/docs). For production, run the checks in your own process with the library, or host this service yourself: it is one container, `docker build .` from the repository.

## Trying it inside a chat client

The same checks are exposed as MCP tools, so you can try the format from Claude or another MCP client without writing code: `claude mcp add --transport http rogerwilco https://rogerwilco.crox.io/mcp`. This is for exploring, not for integration: checks that guard money belong in your own code path, where a model cannot skip them.

## The functions

| Function | Does | Returns |
|---|---|---|
| `encode(msg, profile)` | JSON form to a line, validated | the line |
| `parse(line, profile)` | a line to its JSON form | `(message, errors, warnings)` |
| `check_ho(ho, record, profile)` | check 1: the line against the record | `(problems, notes)` |
| `check_rb_full(ho, rb, profile)` | check 2: a readback or a tool's statement against the line | `(problems, notes)` |
| `check_dn(ho, dn, profile, rb_line=)` | check 3: what was done against the plan | `(problems, notes)` |
| `make_rb(ho, id, profile)` | a correct readback, for a receiver that runs code | the RB line |
| `digest(line, profile)` | the fingerprint `h=` of a line | 12 hex characters |
| `legend(profile)` | the prompt text another model needs | text |

No problems means go. Anything in problems means stop: re-send the job from the record, or, after the act, reverse it. Notes are assumptions worth logging. [What a line is](https://rogerwilco.crox.io/lines) explains every message type; the [spec](https://rogerwilco.crox.io/spec) is the rulebook; the [skill](https://rogerwilco.crox.io/skill) is the file an agent reads.
