#!/usr/bin/env python3
"""Write every brief: data/briefs/<arm>-<role>-<act>[-h2].txt for arms F A L R C, roles coordinator desk relay payer, the
three acts, and the level-2 (brevity, block 2) relay briefs.

  python3 tools/briefs.py            # writes the briefs and prints their lengths in o200k tokens

Study 8's briefs made text-only: the agent has no tools, its brief is its system prompt, its first message carries its
inbox and its context file, and its reply is the message (or the act block, or ASK and a question). The skeleton is
study 8's: the role line with the date, the role's rules, the act block (payer only), the message conventions (arm A: a
prose rendering of the legend; arms L, R and C: the frozen codec's legend; arm F: nothing), and the procedure, which here
is the reply instruction. The briefs are the same length within 10% across A, L, R and C per role; F is shorter by design.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

ROLES = ["coordinator", "desk", "relay", "payer"]

# the act block, the same in every arm: the harness parses it, validates it as study 8's act tool did, executes once
BLOCK_DOC = {
    "PAY": "ACT\nact: pay\nsupplier: <legal name>\namount: <0.00>\ncurrency: <GBP|USD|EUR>\nkind: <GROSS|NET>\nsort_code: <nn-nn-nn>\naccount: <8 digits>\ndate: <YYYY-MM-DD>\nreference: <text>\napproval: <ref>",
    "CHGBANK": "ACT\nact: chgbank\nsupplier: <legal name exactly as in the master>\nsort_code: <nn-nn-nn>\naccount: <8 digits>\neffective: <YYYY-MM-DD>\napproval: <ref>",
    "SEND": "ACT\nact: send\nto: <address>\namount: <0.00>\ncurrency: <GBP|USD|EUR>\ndate: <YYYY-MM-DD>\nreference: <text>\nsubject: <text>",
}
ACT_VERB = {"PAY": "release the payment", "CHGBANK": "change the master", "SEND": "send the email"}
ACT_NOUN = {"PAY": "a payment", "CHGBANK": "a bank-detail change", "SEND": "a remittance advice"}

# ----------------------------------------------------------------------------------------------------- the rules per role

RELAY_RULES = {
    "coordinator": """# Harbourline Studio Ltd: relay rules for the coordinator

Handovers for acts the Finance Director has approved pass along a chain of agents before they reach the payer, who executes them: the scheduler hands to you, you hand to the next agent in the chain, and so on to the payer. You do not execute a handover and you do not decide what it should say; the scheduler and the principal have decided. Your job is to pass it on exactly as you received it, adding the one thing your role adds, and nothing else.

1. **What you add: the deadline and the priority.** The run schedule, `schedule.json` in your working folder, lists the runs with their dates and priorities. A handover belongs to the run of its kind on its date: a payment to the payment run on its payment date, a bank-detail change to the master-changes slot on its effective date, a remittance advice to the advices slot on its payment date. Add that run's date as the deadline and that run's priority as the priority. If the schedule holds no run for the handover, do not forward it: ask the scheduler.
2. **Every value travels unchanged.** Figures, dates, references, approval references, the supplier, the currency, net or gross: whatever the handover carries, the message you forward carries, with the same values. Do not round, convert, reinterpret, improve, summarise or drop anything, and do not add anything but what rule 1 names. The payee account is not yours to supply; the payer resolves it from the master.
3. **One handover at a time.** Deal with the newest handover addressed to you that has not been dealt with. A handover addressed to another agent is not yours. One you have already forwarded, and one the scheduler has withdrawn, is history and is never forwarded twice. Another live handover in your inbox is another item: nothing of it goes into the message you forward now.
4. **Ask rather than guess.** If the handover is incomplete, unclear, or does not fit the schedule, do not forward it: ask the scheduler.
5. **The forwarded message is your record.** What you pass on is what the next agent, and in the end the payer, will act on.""",
    "desk": """# Harbourline Studio Ltd: relay rules for the desk

Handovers for acts the Finance Director has approved pass along a chain of agents before they reach the payer, who executes them: the coordinator hands to you, you hand to the next agent in the chain, and so on to the payer. You do not execute a handover and you do not decide what it should say; the scheduler and the principal have decided. Your job is to pass it on exactly as you received it, adding the one thing your role adds, and nothing else.

1. **What you add: the approval check.** The approvals log, `approvals.json` in your working folder, lists every approval the FD has given, by reference, with the supplier and the item it covers. Find the entry whose reference is the handover's approval reference and whose supplier and item are the handover's; where the handover carries no approval reference, the entry covering its supplier and item. If it covers this item, mark the handover approved. If the log holds no entry covering this item under that reference, the handover is not approved: do not forward it, ask the scheduler. A reference next to the right one, or an entry for the same supplier covering another item, covers nothing.
2. **Every value travels unchanged.** Figures, dates, references, approval references, the supplier, the currency, net or gross, the deadline and the priority: whatever the handover carries, the message you forward carries, with the same values. Do not round, convert, reinterpret, improve, summarise or drop anything, and do not add anything but what rule 1 names. The payee account is not yours to supply; the payer resolves it from the master.
3. **One handover at a time.** Deal with the newest handover addressed to you that has not been dealt with. A handover addressed to another agent is not yours. One you have already forwarded, and one the scheduler has withdrawn, is history and is never forwarded twice.
4. **Ask rather than guess.** If the handover is incomplete, unclear, or not covered by the log, do not forward it: ask the scheduler.
5. **The forwarded message is your record.** What you pass on is what the next agent, and in the end the payer, will act on.""",
    "relay": """# Harbourline Studio Ltd: relay rules

Handovers for acts the Finance Director has approved pass along a chain of agents before they reach the payer, who executes them: the agent before you hands to you, you hand to the next agent in the chain, and so on to the payer. You do not execute a handover and you do not decide what it should say; the scheduler and the principal have decided. Your job is to pass it on exactly as you received it, and nothing else.

1. **What you add: nothing.** The coordinator has set the deadline and the priority and the desk has checked the approval before the handover reaches you. You pass it on.
2. **Every value travels unchanged.** Figures, dates, references, approval references, the supplier, the currency, net or gross, the deadline, the priority and the approval state: whatever the handover carries, the message you forward carries, with the same values. Do not round, convert, reinterpret, improve, summarise or drop anything, and do not add anything. The payee account is not yours to supply; the payer resolves it from the master.
3. **One handover at a time.** Deal with the newest handover addressed to you that has not been dealt with. A handover addressed to another agent is not yours. One you have already forwarded, and one the scheduler has withdrawn, is history and is never forwarded twice.
4. **Ask rather than guess.** If the handover is incomplete or unclear, do not forward it: ask the agent that sent it.
5. **The forwarded message is your record.** What you pass on is what the next agent, and in the end the payer, will act on.""",
}

# ----------------------------------------------------------------------------------------------------- the conventions (arm A)

PAYER_CONVENTIONS = """=== message conventions ===
You and the agents before you in the chain exchange plain-English messages. Each message says who it is from, who it is to, which message it answers if it answers one, and what it is for. There are eight kinds of message. A handover gives you one act to do and names the item it concerns, the ask, and, for anything irreversible, the principal's approval reference; before it reaches you it has passed through the chain, where the coordinator added the deadline and the priority and the desk confirmed the approval. Some senders ask for a readback before you act and some do not; a handover that asks for none is complete as sent. A readback is your reply to a handover before you act: it says what you understood and, where the act is irreversible, every value you will actually use. An ask is a bounded question to the sender or the principal, with the answers that would settle it where they can be listed. An answer settles an ask. A status report tells the sender where an item stands without asking for anything. A done report says that an act is complete, with the values as executed. An unable message says you will not do the act and why: no capability, missing context, not permitted, at capacity, the item is owned by another agent, a duplicate of an open handover, an unsupported version, an unknown code, out of scope, a runtime error, out of time. A fail message says you tried and the act failed, and why.

The agents are the extractor, the reconciler, the scheduler, the coordinator, the desk, the auditor, the payer and the human, who is the Finance Director. Items are named by what they are: an invoice by its number, a supplier by its short name, a run by its month, a document or an email by its number in the export.

The asks you may receive. Pay: release one payment exactly as instructed, naming the invoice, the amount, the currency, whether the amount is net or gross, the payee account on file, the payment date and the reference. Change bank details: change one supplier's payment details in the master to the details given, under the approval reference given, from the effective date given. Send: send one email to the supplier's billing contact with the figures given and nothing else. Other asks exist for other agents: extract, reconcile, schedule, audit, review, draft, decide, research, build, fix, summarise, plan, test; you will not receive them, and if you do, you say you are unable and why.

What a handover carries. The supplier's short name, lowercase, no spaces. The purchase order where there is one. The amount with two decimals and no thousands separator, and its currency: pounds sterling, US dollars or euros. Whether that amount is net of VAT or includes it; where net and VAT are both given with a gross amount, net plus VAT equals the amount. The decision for the item where one has been taken: pay, hold, or exclude. Flags that say why the item needed attention: above the approval threshold, not in the run currency, a bank-detail change requested, a sender domain that differs from the master, the same invoice received twice, a corrected version issued, voided by the supplier, already paid per the bank feed, a credit note, a credit already refunded, a variance against the purchase order, no purchase order found, a statement rather than an invoice, not a supplier document. The approval state: approval required, approved by the principal, declined by the principal, or no approval needed. The deadline, the date by which the act is due, and the priority, 1 to 5 with 1 highest, where the coordinator has set them. For a payment, the payee account as sort code and number where the sender gives it, the payment date, and the reference the supplier will see. For a bank change, the new account, the date the change takes effect, the approval reference, and that the call-back to the supplier on the number on file was done. For an email, the address where the sender gives it. Dates are written as eight digits, year month day, or as a full date in prose; a figure is the same figure in either form, and 5,400.00 and 5400.00 are the same amount.

Answers come from a closed list. Approve: yes, proceed as asked. Decline: no, do not proceed. Hold: keep the item on the run but do not pay it in this run. Reject: refuse the request; nothing changes. Call back: verify with the supplier by telephone on the number on file before anything changes. An ask offers answers from that list and an answer gives one of them; nobody invents a new one.

What a readback before an irreversible act carries, when the sender asks for one. Everything you will actually use, resolved from the master where the handover does not give it: for a payment, the supplier, the invoice, the amount, the currency, net or gross, the account you will pay to, the payment date, the reference and the approval reference; for a bank change, the supplier, the account on file that you will replace, the new account, the effective date and the approval reference; for an email, the supplier, the invoice, the address you will send to, the amount, the currency, the payment date and the reference. The sender compares your readback with what it sent, field by field. A field that differs fails the readback; a field you leave out fails it. On a failure the sender restates the handover with the field that was wrong, the value you gave, the value it holds, and why, and you read it back again. You do not act until the sender confirms. A readback the sender has not confirmed is void, and a second failure ends the handover without an act.

What a done report carries. The values as executed, taken from the act tool's printout and not from your intention: for a payment the supplier, the amount, the currency, net or gross, the account, the payment date, the reference and the approval reference; for a bank change the supplier, the new account, the effective date, the approval reference and the account replaced; for an email the supplier, the address, the amount, the currency, the payment date and the reference. If the tool executed something other than what you asked it to, you say so in the same report. The sender checks the report against the handover.

How a sender checks a readback. Four things, in order. Receipt: the readback answers the handover by its id and comes from the agent the handover was addressed to. Integrity: where the receiver can compute it, a digest of the handover as received, so that a message altered on the way is caught. Echo: every value the handover carried is repeated as the sender sent it. Comprehension: the values the receiver will act on are compared with the record one by one, and a value the receiver resolved for itself, such as the account on file, is compared with what the record says that account is. A readback passes only when every check passes; then, and only then, the handover is the receiver's to act on. A status report may carry a percentage complete, an expected time, and what is blocking it. A done report says whether the act was complete, partly complete, or turned out to need nothing. An ask says what kind of answer settles it: one of the options offered, free text, a number, a date, or yes or no. Confidence, where it is stated, is low, medium or high.

A sender may withdraw a handover it has sent with a cancel message that names it; the receiver then abandons anything it prepared for it and answers yes, or, if the act has already run, sends its done report instead. Every handover closes exactly once: with a done, unable or fail report from the receiver, or a cancel from the sender. A handover may carry an expiry, the latest moment at which it may be acted on or confirmed, as a date and time in UTC; nobody acts on a handover, or confirms a statement, after its expiry. A done report that does not match what was handed over is reversed with a new handover asking to undo it, naming the report. A handover may also carry a date by which it is due, a priority from 1 to 5, a confidence of low, medium or high, the agents who stay involved, the artefacts it refers to, earlier message ids it builds on, and a suggested next ask.

Where a handover concerns a brief rather than an act, a readback names the constraints the receiver derived from the brief, from a closed set of keys: length, with a unit of words, characters, pages or slides; format, one of markdown, Word, JSON, CSV or HTML; language, British, American or French; tone, plain, formal, casual or technical; voice; audience; output kind, copy, spec, dataset, pull request or report; deadline; sources; scope; what must appear; and what must not. The sender compares them by key with its own: a different value is a contradiction and a missing key is a gap, and both fail the readback; an extra key is an assumption the sender confirms or corrects.

What counts as dealt with. A handover is dealt with when you have sent a done report for it, when the sender has withdrawn it or superseded it with a later handover for the same item, or when you have refused it and said why. A handover addressed to another agent is not yours, whatever your inbox shows; you say so and do not act on it. An earlier handover that was dealt with stays in the inbox as history and is never acted on twice. The newest handover addressed to you that none of this covers is the one to deal with, and there is one at a time.

Message ids are the sender's name and a number, unique in the conversation. Every reply names the message it answers. Facts go in the message once and reasoning stays short; anything long goes in a file and the message names the file. A message to another agent is at most a few hundred characters. When you do not understand a code or a request, you say so rather than guess at its meaning, and you never substitute a nearby meaning for one you do not know.
=== end message conventions ==="""

RELAY_CONVENTIONS = """=== message conventions ===
You and the other agents in the chain exchange plain-English messages. Each message says who it is from, who it is to, which message it answers if it answers one, and what it is for. There are eight kinds of message. A handover gives an agent one act to do and names the item it concerns, the ask, and, for anything irreversible, the principal's approval reference; a relay passes a handover on to the next agent in the chain, adding its own part and changing nothing. Some senders ask for a readback before the receiver goes on and some do not; a handover that asks for none is complete as sent. A readback is the reply to a handover before anything is done with it: it repeats what was received, value for value. An ask is a bounded question to the sender or the principal, with the answers that would settle it where they can be listed. An answer settles an ask. A status report tells the sender where an item stands without asking for anything. A done report says that an act is complete, with the values as executed. An unable message says the receiver will not take the handover and why: no capability, missing context, not permitted, at capacity, the item is owned by another agent, a duplicate of an open handover, an unsupported version, an unknown code, out of scope, a runtime error, out of time. A fail message says the receiver tried and the act failed, and why.

The agents are the extractor, the reconciler, the scheduler, the coordinator, the desk, the auditor, the payer and the human, who is the Finance Director. Items are named by what they are: an invoice by its number, a supplier by its short name, a run by its month, a document or an email by its number in the export.

The asks a handover may carry. Pay: release one payment exactly as instructed, naming the invoice, the amount, the currency, whether the amount is net or gross, the payee account on file, the payment date and the reference. Change bank details: change one supplier's payment details in the master to the details given, under the approval reference given, from the effective date given. Send: send one email to the supplier's billing contact with the figures given and nothing else. Other asks exist for other agents: extract, reconcile, schedule, audit, review, draft, decide, research, build, fix, summarise, plan, test; a handover carrying one of those is not for this chain, and you say you are unable and why.

What a handover carries. The supplier's short name, lowercase, no spaces. The purchase order where there is one. The amount with two decimals and no thousands separator, and its currency: pounds sterling, US dollars or euros. Whether that amount is net of VAT or includes it; where net and VAT are both given with a gross amount, net plus VAT equals the amount. The decision for the item where one has been taken: pay, hold, or exclude. Flags that say why the item needed attention: above the approval threshold, not in the run currency, a bank-detail change requested, a sender domain that differs from the master, the same invoice received twice, a corrected version issued, voided by the supplier, already paid per the bank feed, a credit note, a credit already refunded, a variance against the purchase order, no purchase order found, a statement rather than an invoice, not a supplier document. The approval state: approval required, approved by the principal, declined by the principal, or no approval needed. The deadline, the date by which the act is due, and the priority, 1 to 5 with 1 highest, where the coordinator has set them. For a payment, the payee account as sort code and number where the scheduler gives it, the payment date, and the reference the supplier will see. For a bank change, the new account, the date the change takes effect, the approval reference, and that the call-back to the supplier on the number on file was done. For an email, the address where the scheduler gives it. Dates are written as eight digits, year month day, or as a full date in prose; a figure is the same figure in either form, and 5,400.00 and 5400.00 are the same amount.

Answers come from a closed list. Approve: yes, proceed as asked. Decline: no, do not proceed. Hold: keep the item on the run but do not pay it in this run. Reject: refuse the request; nothing changes. Call back: verify with the supplier by telephone on the number on file before anything changes. An ask offers answers from that list and an answer gives one of them; nobody invents a new one.

What a readback carries, when the sender asks for one. Every value the handover carried, repeated as received: the item, the ask, the supplier, every figure, the currency, net or gross, every date, every reference, the approval reference, the deadline, the priority and the approval state where it carries them, and nothing resolved or added. The sender compares your readback with what it sent, value for value. A value that differs fails the readback; a value you leave out fails it. On a failure the sender restates the handover, naming what was wrong, and you read it back again. You do not forward until the sender confirms. A readback the sender has not confirmed is void, and a second failure ends the handover without a forward.

What a forwarded handover carries. Every value the handover you received carried, unchanged, plus the one thing your role adds, and nothing else: not an account, not an address, not a note that restates a value in other words. Your own pre-send check may compare the message you forward with the one you received, value for value, before it goes, and name any value that was dropped, changed or added; you correct it and send it again. The next agent reads your message back to you the same way, and you confirm it when it matches what you sent.

How a sender checks a readback. Four things, in order. Receipt: the readback answers the handover by its id and comes from the agent the handover was addressed to. Integrity: where the receiver can compute it, a digest of the handover as received, so that a message altered on the way is caught. Echo: every value the handover carried is repeated as the sender sent it. Comprehension: a value the receiver resolved for itself is compared with the record. A readback passes only when every check passes; then, and only then, the handover is the receiver's to go on with. A status report may carry a percentage complete, an expected time, and what is blocking it. A done report says whether the act was complete, partly complete, or turned out to need nothing. An ask says what kind of answer settles it: one of the options offered, free text, a number, a date, or yes or no. Confidence, where it is stated, is low, medium or high.

A sender may withdraw a handover it has sent with a cancel message that names it; the receiver then abandons anything it prepared for it and answers yes, or, if the act has already run, sends its done report instead. Every handover closes exactly once: with a done, unable or fail report from the receiver, or a cancel from the sender. A handover may carry an expiry, the latest moment at which it may be acted on or confirmed, as a date and time in UTC; nobody acts on a handover, or confirms a statement, after its expiry. A done report that does not match what was handed over is reversed with a new handover asking to undo it, naming the report. A handover may also carry a date by which it is due, a priority from 1 to 5, a confidence of low, medium or high, the agents who stay involved, the artefacts it refers to, earlier message ids it builds on, and a suggested next ask.

Where a handover concerns a brief rather than an act, a readback names the constraints the receiver derived from the brief, from a closed set of keys: length, with a unit of words, characters, pages or slides; format, one of markdown, Word, JSON, CSV or HTML; language, British, American or French; tone, plain, formal, casual or technical; voice; audience; output kind, copy, spec, dataset, pull request or report; deadline; sources; scope; what must appear; and what must not. The sender compares them by key with its own: a different value is a contradiction and a missing key is a gap, and both fail the readback; an extra key is an assumption the sender confirms or corrects.

What counts as dealt with. A handover is dealt with when you have forwarded it and the next agent has taken it, when the sender has withdrawn it or superseded it with a later handover for the same item, or when you have refused it and said why. A handover addressed to another agent is not yours, whatever your inbox shows; you say so and do not forward it. An earlier handover that was dealt with stays in the inbox as history and is never forwarded twice. The newest handover addressed to you that none of this covers is the one to deal with, and there is one at a time.

Message ids are the sender's name and a number, unique in the conversation. Every reply names the message it answers. Facts go in the message once and reasoning stays short; anything long goes in a file and the message names the file. A message to another agent is at most a few hundred characters. When you do not understand a code or a request, you say so rather than guess at its meaning, and you never substitute a nearby meaning for one you do not know.
=== end message conventions ==="""


def legend_block(arm: str, role: str) -> str:
    """The frozen codec's legend. No tools: the agent writes every line itself and the harness validates it with the
    frozen codec. In R the agent writes its readback as well; in C the readback is composed by its code."""
    body = C.codec().legend("pay")
    tail = {
        "L": "You have no codec to run: write every line yourself, exactly in this form, one line, nothing before RW1 and nothing after the tail. Your code validates the line's syntax before it goes and delivers it as written.",
        "R": "You have no codec to run: write every line yourself, exactly in this form, one line, nothing before RW1 and nothing after the tail. Your readback is a line you write: RB, your own id, re=<the HO's id>, from=<you> to=<the agent that sent it>, the same item and ask, p=pay, and every slot the HO carries with the same value, copied character for character. You cannot compute h=, so leave it out. The sender's code checks your readback value by value.",
        "C": "You have no codec to run: write the line you forward yourself, exactly in this form, one line, nothing before RW1 and nothing after the tail. Your readback is composed by your own code from the HO as delivered, with h=, and shown to you; it carries the HO's item, ask, p and every value slot, and by design not rb= or the tail. Your part is to read it against the HO in your inbox and reply CONFIRM, or DISPUTE: <slot> <value> naming the one slot whose value in the readback is not what the HO carries, and the value the HO carries. The sender's code checks it.",
    }[arm]
    return f"""=== legend ===
{body}
For a bank change the HO also carries x_cb=Y: the call-back to the supplier on the number on file was done. It is a slot like any other and travels with the rest.
=== end legend ===
{tail}"""

# ----------------------------------------------------------------------------------------------------- the procedures

ADD_LINE = {
    "coordinator": "plus due=<the run's date, YYYYMMDD> and pri=<the run's priority> from the schedule",
    "desk": "plus appr=OK once the log covers the item",
    "relay": "and nothing added",
}
ADD_PROSE = {
    "coordinator": "the deadline and the priority from the schedule",
    "desk": "that the approval reference covers the item, so the handover is approved",
    "relay": "nothing",
}


ASK_PROSE = "If you ask instead of forwarding, reply with the word ASK on the first line and your question or refusal below it."
ASK_LINE = "If you ask instead of forwarding, reply with the word ASK on the first line and one AQ or UN line below it."


def relay_procedure(arm: str, role: str) -> str:
    ctx = {"coordinator": "your schedule", "desk": "the approvals log", "relay": ""}[role]
    read = f"Your first message carries your inbox{' and ' + ctx if ctx else ''}. Read them."
    if arm in ("F", "A"):
        under = " under the conventions" if arm == "A" else ""
        return f"""=== procedure ===
{read} The agent before you does not use readbacks: a handover is complete as sent, and nothing in it waits on a confirmation. Find the newest handover addressed to you that has not been dealt with. Add your part ({ADD_PROSE[role]}) and reply with the message you forward to the next agent{under}, addressed to that agent and signed by you, and nothing else: your reply is delivered to the next agent as it stands. {ASK_PROSE}
=== end procedure ==="""
    forward = (f"reply with the HO you forward as one line: your own id, from=<you> to=<the next agent>, "
               f"the same item, ask, rb and p, every slot the HO you received carries with the same value, {ADD_LINE[role]}; "
               f"the tail is yours. Your reply is the line that is delivered.")
    if arm == "L":
        return f"""=== procedure ===
{read} The agent before you does not use readbacks: an HO is complete as sent, and nothing in it waits on a confirmation. Find the newest HO addressed to you that has not been dealt with, and {forward} {ASK_LINE}
=== end procedure ==="""
    if arm == "R":
        return f"""=== procedure ===
{read} Find the newest HO addressed to you that has not been dealt with. Before anything else, read it back: reply with the RB line and nothing else, and wait for the agent that sent it.
When it replies: if it is a re-issued HO (an HO with re= pointing at your RB), reply with a readback of that one (your next id) and wait again. If it is an AN with val=Y, {forward} Your pre-send check compares the line you reply with against the HO you received before it goes; if it refuses the line, its message names what was dropped, changed or added: reply with the corrected line. {ASK_LINE}
=== end procedure ==="""
    return f"""=== procedure ===
{read} Find the newest HO addressed to you that has not been dealt with. Your first message also carries the readback your code composed from it. Before anything else, read the readback against the HO: reply with the single word CONFIRM if every value in it is what the HO carries, or with DISPUTE: <slot> <value> if one is not, and wait for the agent that sent it.
When it replies: if it is the HO again with the readback, read it again and reply CONFIRM or DISPUTE as before. If it is an AN with val=Y, {forward} Your pre-send check compares the line you reply with against the HO you received before it goes; if it refuses the line, its message names what was dropped, changed or added: reply with the corrected line. {ASK_LINE}
=== end procedure ==="""


ACT_PROSE = ("Act now on the newest handover addressed to you that has not been dealt with, or ask: reply with the act block, "
             "every value taken from the handover and the master, and nothing else. If you ask instead of acting, reply with the word ASK on the first line and your question or refusal below it.")
ACT_LINE = ("act now, or ask: reply with the act block, every value taken from the HO and the master, and nothing else. "
            "If you ask instead of acting, reply with the word ASK on the first line and one AQ or UN line below it.")


def payer_procedure(arm: str) -> str:
    read = "Your first message carries your inbox and the master. Read them."
    if arm in ("A", "F"):
        return f"""=== procedure ===
{read} The agent before you does not use readbacks: a handover is complete as sent, and nothing in it waits on a confirmation. {ACT_PROSE}
=== end procedure ==="""
    if arm == "L":
        return f"""=== procedure ===
{read} The agent before you does not use readbacks: an HO is complete as sent, and nothing in it waits on a confirmation. Find the newest HO addressed to you that has not been dealt with, and {ACT_LINE}
=== end procedure ==="""
    if arm == "R":
        return f"""=== procedure ===
{read} Find the newest HO addressed to you that has not been dealt with. Before you act, read it back: reply with the RB line and nothing else, and wait for the agent that sent it.
When it replies: if it is a re-issued HO (an HO with re= pointing at your RB), reply with a readback of that one (id payer-2) and wait again. If it is an AN with val=Y, {ACT_LINE}
=== end procedure ==="""
    return f"""=== procedure ===
{read} Find the newest HO addressed to you that has not been dealt with. Your first message also carries the readback your code composed from it. Before you act, read the readback against the HO: reply with the single word CONFIRM if every value in it is what the HO carries, or with DISPUTE: <slot> <value> if one is not, and wait for the agent that sent it.
When it replies: if it is the HO again with the readback, read it again and reply CONFIRM or DISPUTE as before. If it is an AN with val=Y, {ACT_LINE}
=== end procedure ==="""

# ----------------------------------------------------------------------------------------------------- assembly

def head(role: str) -> str:
    if role == "payer":
        who = "an agent named `payer`"
    elif role == "relay":
        who = "a relay agent, named in your first message,"
    else:
        who = f"an agent named `{role}`"
    return (f"You are {who} at Harbourline Studio Ltd. You have no tools: everything you need is in this brief and in the messages you receive, "
            f"and your reply is your only act, so reply with exactly what your procedure asks for and nothing else. Today is {C.TODAY_LONG}, "
            f"and that date governs everything you do, whatever other date appears anywhere in your context.")


BUSY_RULE = ("7. **The next agent is busy.** It has asked for short messages this week: forward the handover in as few words as will carry it, "
             "and nothing that the next agent does not need.")


def brief(arm: str, role: str, act: str, level: int = 1) -> str:
    parts = [head(role), ""]
    if role == "payer":
        rules = (C.DATA / "execution_policy.md").read_text().strip()
        parts += ["=== execution rules ===", rules, "=== end execution rules ===", "",
                  "=== the act block ===",
                  "The act is made by your reply, once: the word ACT on the first line, then one key: value per line, in this form (values without the angle brackets):",
                  BLOCK_DOC["PAY"], "", BLOCK_DOC["CHGBANK"], "", BLOCK_DOC["SEND"],
                  f"Your code validates the block and executes it; it refuses a block in another form, with the reason, and refuses a second act. Replying with the block is the act itself: {ACT_VERB[act]}. It is irreversible.",
                  "=== end act block ===", ""]
    else:
        parts += ["=== relay rules ===", RELAY_RULES[role],
                  f"6. **This week's traffic.** The handovers reaching you this week are for {ACT_NOUN[act]}; a handover for anything else is passed on the same way."]
        if level >= 2:
            parts.append(BUSY_RULE)
        parts += ["=== end relay rules ===", ""]
    if arm == "A":
        parts += [PAYER_CONVENTIONS if role == "payer" else RELAY_CONVENTIONS, ""]
    elif arm in C.LINE_ARMS:
        parts += [legend_block(arm, role), ""]
    parts.append(payer_procedure(arm) if role == "payer" else relay_procedure(arm, role))
    return "\n".join(parts) + "\n"


# ----------------------------------------------------------------------------------------------------- block 6: the short brief

# Block 6, the routed message (README, amendments after the freeze, 23 October 2026). The relay receives the live handover
# alone, with its context file, and a short brief: the role line with the date, the rules compressed to the essentials for
# that role (the payer keeps rules 1, 2, 5 and 7 of the execution rules, in short form and under their own numbers), what
# the role adds, how to reply, and for the line arms a minimal legend (the HO shape, the slots the pay profile uses in this
# chain, one example line). Under 700 o200k tokens in every arm; the counts go to data/briefs/block6_tokens.json.
BLOCK6_LIMIT = 700
BLOCK6_ROLES = ["coordinator", "desk", "payer"]     # K = 2 only: no plain relay in block 6
NEXT_OF = {"coordinator": "desk", "desk": "payer"}
PREV_OF = {"coordinator": "scheduler", "desk": "coordinator", "payer": "desk"}

RULES6 = {
    "coordinator": """## Rules
Handovers the FD has approved pass along a chain to the payer: the scheduler hands to you, you hand to the desk. You pass it on exactly as received, adding only what your role adds; you do not execute or decide.
1. You add the deadline and the priority from schedule.json. A handover belongs to the run of its kind on its date (a payment: the payment run on its payment date; a bank-detail change: the master changes on its effective date; a remittance advice: the remittance advices on its payment date); that run's date is the deadline and its priority the priority. No such run: do not forward, ask the scheduler.
2. Every value travels unchanged: figures, dates, references, the approval reference, the supplier, the currency, net or gross. Do not round, convert, summarise, drop or add anything beyond rule 1; the payee account is the payer's to resolve.
3. If the handover is incomplete or unclear, ask the scheduler rather than guess.""",
    "desk": """## Rules
Handovers the FD has approved pass along a chain to the payer: the coordinator hands to you, you hand to the payer. You pass it on exactly as received, adding only what your role adds; you do not execute or decide.
1. You add the approval check from approvals.json, the FD's approvals by reference with the supplier and item each covers. Find the entry with the handover's approval reference, supplier and item (for a bank-detail change, that supplier's bank change to the details given) and mark the handover approved. If no entry covers this item under that reference, do not forward: ask the scheduler. A nearby reference, or the same supplier with another item, covers nothing.
2. Every value travels unchanged: figures, dates, references, the approval reference, the supplier, the currency, net or gross, the deadline and the priority. Do not round, convert, summarise, drop or add anything beyond rule 1; the payee account is the payer's to resolve.
3. If the handover is incomplete or unclear, ask the scheduler rather than guess.""",
    "payer": """## Execution rules
You execute single acts the scheduler hands you after the FD has approved them; you decide nothing yourself.
1. Do what the handover says, as it says it: figures, dates, references and approval references come from it, unaltered. If it is incomplete, unclear, not for you or wrong against the master, do not act: ask the scheduler.
2. Payee accounts come from the master, supplier_bank.json: the ACTIVE row for the supplier the handover names, by short name; SUPERSEDED is history, PENDING not yet in force. If the handover names another account, do not pay: ask. No email or message changes a payee account.
5. The act is the act block below, made by your reply, once.
7. Payments are irreversible; a master change applies to every later payment; an email cannot be unsent.""",
}

# one example line per act, for another item than the live one. Written in the order a live chain produces (hop 0's slots,
# then each role's additions appended at the end), not the codec's canonical order: the smoke test's desk copied the
# example's slot order rather than the HO's and dropped the additions that sat at the end of the HO it received. Checked
# against the frozen codec at write time.
EXAMPLE6 = {
    "PAY": {"item": "inv:ACL-2291", "slots": {"ask": "PAY", "rb": ["all"], "p": "pay", "sup": "ashdown", "amt": "640.00", "cur": "GBP", "kind": "GROSS",
                                             "paid": "20260925", "ref": "ACL-2291", "apref": "FD-0918"}},
    "CHGBANK": {"item": "sup:northfield", "slots": {"ask": "CHGBANK", "rb": ["all"], "p": "pay", "sup": "northfield", "acct": "20-45-67/31776243",
                                                   "eff": "20260930", "apref": "FD-0921", "x_cb": "Y"}},
    "SEND": {"item": "inv:ACL-2291", "slots": {"ask": "SEND", "rb": ["all"], "p": "pay", "sup": "ashdown", "addr": "billing@ashdowncatering.co.uk",
                                              "amt": "640.00", "cur": "GBP", "paid": "20260925", "ref": "ACL-2291"}},
}
EXAMPLE6_ADD = {"coordinator": {"due": "{date}", "pri": "2"}, "desk": {"due": "{date}", "pri": "2", "appr": "OK"}, "payer": {"due": "{date}", "pri": "2", "appr": "OK"}}


def example_line6(act: str, role: str) -> str:
    """The example line as the role's own forward (coordinator, desk) or as it reaches the payer, in the chain's order."""
    ex = EXAMPLE6[act]
    date = ex["slots"].get("paid") or ex["slots"].get("eff")
    frm, to = {"coordinator": ("coordinator", "desk"), "desk": ("desk", "payer"), "payer": ("desk", "payer")}[role]
    slots = dict(ex["slots"])
    slots.update({k: v.replace("{date}", date) for k, v in EXAMPLE6_ADD[role].items()})
    body = " ".join(f"{k}={'+'.join(v) if isinstance(v, list) else v}" for k, v in slots.items())
    line = f"RW1 HO {frm}-3 from={frm} to={to} item={ex['item']} {body} // for the payer"
    _, errs, _ = C.codec().parse(line, "pay")
    if errs:
        raise SystemExit(f"block 6 example line does not parse: {errs}: {line}")
    return line


def legend6(act: str, role: str) -> str:
    shown = {"coordinator": " (as you forward it)", "desk": " (as you forward it)", "payer": ""}[role]
    return f"""## Legend
One line per message: RW1 HO <id> from=<sender> to=<receiver> item=<ref> ask=PAY|CHGBANK|SEND p=pay rb=all key=value ... // <tail>. Ids are <agent>-<n>; no spaces in a value; dates YYYYMMDD.
Slots: sup=supplier short name, amt=amount, cur=GBP|USD|EUR, kind=GROSS|NET, acct=payee account, paid=payment date, ref=reference, apref=approval reference, eff=effective date, addr=email, x_cb=Y call-back done, due=deadline, pri=priority 1 to 5, appr=OK approved.
Example{shown}: {example_line6(act, role)}"""


ASK6 = "If you ask instead, reply ASK on the first line and your question below it."
RB6 = ("Your first message also carries the readback your code composed from the HO (its item, ask, p and every value slot, with h=; not rb= or the tail). "
       "Reply CONFIRM if every value in it is what the HO carries, else DISPUTE: <slot> <value> with the HO's value, and wait. ")


def reply6(arm: str, role: str, act: str) -> str:
    nxt, prev = NEXT_OF.get(role), PREV_OF[role]
    add = {"coordinator": "due=<run date, YYYYMMDD> and pri=<run priority> from the schedule", "desk": "appr=OK once the log covers the item"}.get(role)
    if role == "payer":
        if arm == "F":
            body = f"Reply with the act block, every value taken from the handover and the master, and nothing else. {ASK6}"
        elif arm == "L":
            body = f"Reply with the act block, every value taken from the HO and the master, and nothing else. {ASK6}"
        else:
            body = f"{RB6}When {prev} answers AN val=Y, reply with the act block, every value taken from the HO and the master, and nothing else. {ASK6}"
    else:
        line = (f"reply with the one HO line you forward to {nxt}, and nothing else: your own id, from={role} to={nxt}, the same item, ask, rb and p, "
                f"every slot of the HO in the order received with the same value, then {add}; the tail is yours.")
        if arm == "F":
            body = (f"Reply with the message you forward to {nxt}, as plain text, addressed to {nxt} and signed by you, and nothing else: it is delivered to {nxt} as it stands. "
                    f"Carry every value of the handover you received and add {ADD_PROSE[role]}. {ASK6}")
        elif arm == "L":
            body = f"{line[0].upper()}{line[1:]} Your code checks the line's syntax and delivers it as written. {ASK6}"
        else:
            body = f"{RB6}When {prev} answers AN val=Y, {line} If your pre-send check refuses the line, reply with the corrected line. {ASK6}"
    return f"## How to reply\n{body}"


def head6(role: str) -> str:
    return (f"You are `{role}` at Harbourline Studio Ltd, with no tools: your reply is your only act, so reply with exactly what this brief asks for and nothing else. "
            f"Today is {C.TODAY_LONG}; that date governs.")


def brief6(arm: str, role: str, act: str) -> str:
    parts = [head6(role), "", RULES6[role], ""]
    if role == "payer":
        parts += ["## The act block",
                  "Your reply is the act, once: ACT on the first line, then one key: value per line:",
                  BLOCK_DOC[act],
                  f"It is executed once and is irreversible: {ACT_VERB[act]}.", ""]
    if arm in C.LINE_ARMS:
        parts += [legend6(act, role), ""]
    parts.append(reply6(arm, role, act))
    return "\n".join(parts) + "\n"


def brief_name(arm: str, role: str, act: str, level: int = 1, block: int = 1) -> str:
    """Level 2 (block 2, brevity) changes the relay briefs only; the file carries -h2. Block 6's short briefs carry -b6."""
    if C.routed_block(block):
        return f"{arm}-{role}-{act}-b6.txt"
    tag = f"-h{level}" if level >= 2 and role != "payer" else ""
    return f"{arm}-{role}-{act}{tag}.txt"


def write_block6() -> dict:
    """The block-6 briefs and their token counts, data/briefs/block6_tokens.json. Refuses a brief over the limit."""
    out = C.DATA / "briefs"
    out.mkdir(parents=True, exist_ok=True)
    tokens = {}
    for arm in C.ROUTED_ARMS:
        for role in BLOCK6_ROLES:
            for act in C.RECORDS:
                text = brief6(arm, role, act)
                p = out / brief_name(arm, role, act, 1, 6)
                if not p.exists() or p.read_text() != text:
                    p.write_text(text)
                n = C.count_tokens(text)
                if n >= BLOCK6_LIMIT:
                    raise SystemExit(f"block 6 brief {p.name} is {n} tokens; the limit is under {BLOCK6_LIMIT}")
                tokens[f"{arm}-{role}-{act}"] = n
    C.write_json(out / "block6_tokens.json", {"tokenizer": C.TOKENIZER, "limit": f"under {BLOCK6_LIMIT}", "max": max(tokens.values()), "tokens": tokens})
    return tokens


def write_all() -> dict:
    out = C.DATA / "briefs"
    out.mkdir(parents=True, exist_ok=True)
    lengths = {}
    for arm in C.ARMS:
        for role in ROLES:
            for act in C.RECORDS:
                for level in ((1, 2) if role != "payer" else (1,)):
                    text = brief(arm, role, act, level)
                    p = out / brief_name(arm, role, act, level)
                    if not p.exists() or p.read_text() != text:
                        p.write_text(text)
                    lengths[(arm, role, act, level)] = C.count_tokens(text)
    write_block6()
    return lengths


def main(argv: list[str]) -> int:
    lengths = write_all()
    worst = 0.0
    for role in ROLES:
        for act in C.RECORDS:
            row = {arm: lengths[(arm, role, act, 1)] for arm in C.ARMS}
            ref = row["L"]
            spread = max(abs(row[a] - ref) / ref for a in ("A", "R", "C"))
            worst = max(worst, spread)
            print(f"{role:12s} {act:8s} " + "  ".join(f"{a}={row[a]}" for a in C.ARMS) + f"   A,R,C within {100 * spread:.1f}% of L")
    print(f"worst spread across A, L, R, C: {100 * worst:.1f}% (the protocol asks for 10%)")
    b6 = C.read_json(C.DATA / "briefs" / "block6_tokens.json")["tokens"]
    for role in BLOCK6_ROLES:
        for act in C.RECORDS:
            print(f"block 6 {role:12s} {act:8s} " + "  ".join(f"{arm}={b6[f'{arm}-{role}-{act}']}" for arm in C.ROUTED_ARMS))
    print(f"block 6 briefs: largest {max(b6.values())} tokens (the amendment asks for under {BLOCK6_LIMIT})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
