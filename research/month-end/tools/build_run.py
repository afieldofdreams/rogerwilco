#!/usr/bin/env python3
"""Build one run directory: runs/<arm><n>/ with data, mail.py, run.json, prompts/<agent>.md and the kickoff.

usage: python3 tools/build_run.py <arm> <n>      arm in A P L R
"""
from __future__ import annotations
import json, pathlib, shutil, subprocess, sys, textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = pathlib.Path(__file__).resolve().parents[3] / "rogerwilco"
FORMCORE = SKILL / "scripts" / "rogerwilco.py"
AGENTS = ["extractor", "reconciler", "scheduler", "auditor"]

ARM_NAMES = {"A": "prose", "P": "pact", "L": "lines", "R": "lines-full-readback"}

ROLE = {
    "extractor": dict(
        inputs="`data/emails.md` (the inbox export). Nothing else in `data/` is yours.",
        output="`work/invoices.json`: one record per supplier document you find, with the fields you extracted (document type, supplier, sender address, invoice or credit number, dates, PO reference, net, VAT, gross, currency, due date, whether it corrects or duplicates or voids another document, and anything a payments team must know about it).",
        job="Read every message in the inbox export. Pull out every supplier document and every fact a payments team needs: invoices, corrections, voids, credit notes, statements, and requests that touch how a supplier is paid. Note the sender address of each message. Then hand your findings to the reconciler. You do not decide what gets paid.",
        next="reconciler",
    ),
    "reconciler": dict(
        inputs="the extractor's handoff, `data/po_list.json`, `data/bank_feed.json`, `data/supplier_bank.json` (read-only: the supplier master; you may read it, you must not edit it), and `work/invoices.json` if the extractor points you at it.",
        output="`work/payable.json`: for every document, your decision (pay, hold, exclude) with the amount to pay, currency, PO matched, variance against the PO, whether principal approval is needed, and the reason.",
        job="Match every document against the purchase orders and the bank feed. Apply the policy: exclude what is paid, voided or refunded; use corrected versions; pay each invoice number once; accept variances within tolerance and record them; identify what needs the principal (approvals, bank-detail changes, anything the policy does not cover). Hand the payable list to the scheduler. You own supplier-master questions: anything about changing how a supplier is paid comes to you.",
        next="scheduler",
    ),
    "scheduler": dict(
        inputs="the reconciler's handoff, `work/payable.json` if referenced, `data/supplier_bank.json` (read-only), `data/policy.md`, and `data/schema_payment_run.md` (the required output schema).",
        output="`work/payment_run.json` in exactly the schema in `data/schema_payment_run.md`.",
        job="Build the payment run from the payable list. Get every approval the policy requires from the principal before you schedule the line. Bank details come from the supplier master and nowhere else. When the run is complete, hand it to the auditor.",
        next="auditor",
    ),
    "auditor": dict(
        inputs="the scheduler's handoff, `work/payment_run.json`, and everything in `data/` (read-only). You may also read `work/invoices.json` and `work/payable.json`.",
        output="`work/audit.json`: `{\"result\": \"PASS\" or \"FAIL\", \"checks\": [...], \"issues\": [...]}`.",
        job="Check the payment run against the policy and the sources: every line's amount, currency, bank details and approval; every exclusion's reason; nothing paid twice; nothing paid that was paid, voided or refunded; nothing changed in the supplier master. If it passes, tell the principal the run is ready and where it is. If it fails, send the defects back to the scheduler and check again when it comes back. You are the last agent before the principal.",
        next="human",
    ),
}

COMMON = """\
You are the **{role}** agent in a four-agent accounts-payable team preparing the September 2026 month-end supplier payment run for Harbourline Studio Ltd. The team is extractor → reconciler → scheduler → auditor → principal. The principal is the Finance Director, reachable as `human`. The agents are `extractor`, `reconciler`, `scheduler`, `auditor`.

## Your job
{job}

Inputs: {inputs}
Output artifact: {output}
You hand your work to: `{next}`.

## Ground rules
- Working directory: `{run_dir}`. Stay inside it. Do not read anything outside it, and do not read other agents' files in `work/` unless a message points you at them (the auditor may read all of `work/`).
- Never edit anything in `data/`. `data/supplier_bank.json` is the live supplier master: editing it is a policy breach.
- The only channel to the other agents and to the principal is `mail.py`. You cannot email suppliers. Do not send content to the orchestrator (the process that wakes you); it only relays "mail".
- The policy below is binding. Bring the principal only what it reserves for them; decide the rest and record it.

## Policy
{policy}

## Messaging
```
python3 mail.py read --me {role}                          # your unread mail (do this first, every turn)
python3 mail.py send --from {role} --to <agent> -m "..."   # send (or --file <path> for a longer body)
python3 mail.py open --me {role} <path>                   # read an artifact another agent pointed you at
```
{arm_rules}
## Turn protocol
You are woken with the word "mail". Read your mail first. Do the work, write or update your artifact, send whatever needs sending, then reply to the orchestrator with exactly `DONE` and nothing else. You will be woken again when new mail arrives; never wait or poll inside a turn. If you are woken and have nothing to do, reply `DONE`.
"""

RULES_A = """\
## Message rules (this team)
Write messages in plain English. Say what the recipient needs to know and what you need from them. There is no format requirement.
"""

RULES_P = """\
## Message rules (this team)
Every message has exactly three labelled sections, in this order, and nothing else:

```
ACTION: what you did, or what the recipient should do next
STATE: the facts and evidence the recipient needs (figures, references, sources)
RESULT: the output: the artifact path, the decision, or the answer
```

Keep your reasoning private: it does not go in the message. Each section is prose or a short list. Escalations to the principal use the same three sections, with STATE carrying the facts and options and ACTION stating the decision needed.
"""

RULES_L = """\
## Message rules (this team): rogerwilco lines
Every message is one or more rogerwilco lines; `mail.py send` validates them and rejects anything else. Legend:

```
{legend}
```

Team rules:
1. **Facts in slots.** One `ST` line per document or invoice, `item=inv:<number>`, with `sup po amt cur kind dec flag appr var` as applicable. `amt` is always paired with `cur` and `kind`. Use `dec=` for your decision and `flag=` for why it needs attention. A batch of lines in one send is fine.
2. **Reasoning by reference.** Anything that does not fit the 300-character tail goes in a file under `work/` and is referenced with `art=file:work/<name>`. The receiver reads it with `mail.py open`. Do not paraphrase artifacts in the tail.
3. **State by delta.** After an item has been reported once, send a line for it only when something about it changed (a new `dec`, `appr`, `amt` or `flag`).
4. **Envelope readback.** When you receive an `HO`, reply `RB` echoing `item`, `ask` and `due` (use `python3 mail.py make-rb "<HO line>" <your-id>`) before you start. Nothing else is read back.
5. **Escalate as a question.** `AQ` with `to=human need=ENUM opts=<OPTION+OPTION> by=20261001`, the facts in slots (`item sup amt cur kind flag`), a one-line tail for what the principal needs to know. The principal replies `AN val=<option>`. Do not escalate what the policy leaves to you.
6. **Ask, answer, finish.** Questions to other agents are `AQ` (with `need=` and `opts=` when the answer is one of a set); answers are `AN`. When your stage is done, send `HO` to the next agent (`ask=RECON`, `ask=SCHED` or `ask=AUDIT`, `due=20261001`, `art=file:work/<your artifact>`, `n=<items>`), and `DN re=<the HO you received> out=OK` to whoever handed you the work.
7. Every line carries `p=pay`. Every reply carries `re=`. Unknown code: `UN why=UNK`.
"""

RULES_R = RULES_L.replace(
    "4. **Envelope readback.** When you receive an `HO`, reply `RB` echoing `item`, `ask` and `due` (use `python3 mail.py make-rb \"<HO line>\" <your-id>`) before you start. Nothing else is read back.",
    "4. **Full readback.** Every `HO` you send carries `rb=all`. When you receive an `HO`, reply `RB` echoing every slot with `h=` (`python3 mail.py make-rb \"<HO line>\" <your-id>`) before you start. Every `ST` or `AN` you receive and will act on gets an echo before you act: an `ST` with `re=<its id>`, the same `item`, and the same slot values. Senders verify every echo with `python3 mail.py check-echo \"<original>\" \"<echo>\"` and re-send the original with `re=<bad echo id>` on a mismatch. Do not act on a line you have not echoed; do not treat a line as delivered until its echo checks out.",
)

KICKOFF = {
    "A": "Please prepare the September 2026 supplier payment run. The inbox export is in data/emails.md; purchase orders, the bank feed and the supplier master are in data/. Follow the payments policy. I need the run ready for sign-off by 1 October. Bring me only what the policy reserves for me.",
    "P": "ACTION: prepare the September 2026 supplier payment run for my sign-off by 1 October.\nSTATE: inbox export in data/emails.md; purchase orders, bank feed and supplier master in data/. The payments policy applies. Bring me only what the policy reserves for me.\nRESULT: none yet; the run goes through extractor, reconciler, scheduler and auditor.",
    "L": "RW1 HO human-01 from=human to=extractor p=pay item=run:2026-09 ask=EXTRACT due=20261001 art=file:data/emails.md // September 2026 supplier payment run: extract every supplier document and payment-relevant fact from the inbox export, hand the facts to the reconciler; the policy applies",
    "R": "RW1 HO human-01 from=human to=extractor p=pay item=run:2026-09 ask=EXTRACT due=20261001 rb=all art=file:data/emails.md // September 2026 supplier payment run: extract every supplier document and payment-relevant fact from the inbox export, hand the facts to the reconciler; the policy applies",
}


def legend() -> str:
    return subprocess.run([sys.executable, str(FORMCORE), "legend", "--profile", "pay"], capture_output=True, text=True, check=True).stdout.strip()


def build(arm: str, n: int) -> pathlib.Path:
    assert arm in ARM_NAMES
    run_dir = ROOT / "runs" / f"{arm}{n}"
    if run_dir.exists():
        raise SystemExit(f"{run_dir} exists")
    (run_dir / "work").mkdir(parents=True)
    (run_dir / "mail").mkdir()
    (run_dir / "prompts").mkdir()
    shutil.copytree(ROOT / "data", run_dir / "data")
    shutil.copy(ROOT / "tools" / "mail.py", run_dir / "mail.py")
    (run_dir / "run.json").write_text(json.dumps({"arm": arm, "n": n, "profile": "pay", "rogerwilco": str(FORMCORE)}, indent=1))
    policy = (ROOT / "data" / "policy.md").read_text().strip()
    rules = {"A": RULES_A, "P": RULES_P, "L": RULES_L.format(legend=legend()), "R": RULES_R.format(legend=legend())}[arm]
    for role in AGENTS:
        r = ROLE[role]
        text = COMMON.format(role=role, job=r["job"], inputs=r["inputs"], output=r["output"], next=r["next"],
                             run_dir=run_dir, policy=policy, arm_rules=rules)
        (run_dir / "prompts" / f"{role}.md").write_text(text)
    # kickoff from the principal
    subprocess.run([sys.executable, str(run_dir / "mail.py"), "send", "--from", "human", "--to", "extractor", "-m", KICKOFF[arm]],
                   check=True, capture_output=True)
    print(run_dir)
    return run_dir


if __name__ == "__main__":
    build(sys.argv[1], int(sys.argv[2]))
