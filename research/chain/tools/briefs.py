#!/usr/bin/env python3
"""Write every brief: data/briefs/<arm>-<role>-<act>.txt for arms F A L R, roles coordinator desk relay payer, the three acts.

  python3 tools/briefs.py            # writes the briefs and prints their lengths in o200k tokens

Every brief has the same skeleton: the role line with the date, the role's rules, the act tool (payer only), the message
conventions (arm A: a prose rendering of the legend; arms L and R: the frozen codec's legend; arm F: nothing), and the
procedure with the reply words. The relay briefs are the same length within 10% across A, L and R per role; F is shorter
by design, as study 6's F was.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

ACT_TOOL = HERE / "act.py"
ROLES = ["coordinator", "desk", "relay", "payer"]

TOOL_DOC = {
    "PAY": f'python3 {ACT_TOOL} pay --item <invoice id> --supplier "<legal name>" --amount <0.00> --currency <GBP|USD|EUR> --kind <GROSS|NET> --sort-code <nn-nn-nn> --account <8 digits> --payment-date <YYYY-MM-DD> --reference <text>',
    "CHGBANK": f'python3 {ACT_TOOL} chgbank --supplier "<legal name exactly as in the master>" --sort-code <nn-nn-nn> --account <8 digits> --effective <YYYY-MM-DD> --approval <ref>',
    "SEND": f'python3 {ACT_TOOL} send --to <address> --subject "<text>" --amount <0.00> --currency <GBP|USD|EUR> --payment-date <YYYY-MM-DD> --reference <text> --body "<the email text>"',
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

What a handover carries. The supplier's short name, lowercase, no spaces. The purchase order where there is one. The amount with two decimals and no thousands separator, and its currency: pounds sterling, US dollars or euros. Whether that amount is net of VAT or includes it; where net and VAT are both given with a gross amount, net plus VAT equals the amount. The decision for the item where one has been taken: pay, hold, or exclude. Flags that say why the item needed attention: above the approval threshold, not in the run currency, a bank-detail change requested, a sender domain that differs from the master, the same invoice received twice, a corrected version issued, voided by the supplier, already paid per the bank feed, a credit note, a credit already refunded, a variance against the purchase order, no purchase order found, a statement rather than an invoice, not a supplier document. The approval state: approval required, approved by the principal, declined by the principal, or no approval needed. The deadline, the date by which the act is due, and the priority, 1 to 5 with 1 highest, where the coordinator has set them. For a payment, the payee account as sort code and number where the sender gives it, the payment date, and the reference the supplier will see. For a bank change, the new account, the date the change takes effect, and the approval reference. For an email, the address where the sender gives it. Dates are written as eight digits, year month day, or as a full date in prose; a figure is the same figure in either form, and 5,400.00 and 5400.00 are the same amount.

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

What a handover carries. The supplier's short name, lowercase, no spaces. The purchase order where there is one. The amount with two decimals and no thousands separator, and its currency: pounds sterling, US dollars or euros. Whether that amount is net of VAT or includes it; where net and VAT are both given with a gross amount, net plus VAT equals the amount. The decision for the item where one has been taken: pay, hold, or exclude. Flags that say why the item needed attention: above the approval threshold, not in the run currency, a bank-detail change requested, a sender domain that differs from the master, the same invoice received twice, a corrected version issued, voided by the supplier, already paid per the bank feed, a credit note, a credit already refunded, a variance against the purchase order, no purchase order found, a statement rather than an invoice, not a supplier document. The approval state: approval required, approved by the principal, declined by the principal, or no approval needed. The deadline, the date by which the act is due, and the priority, 1 to 5 with 1 highest, where the coordinator has set them. For a payment, the payee account as sort code and number where the scheduler gives it, the payment date, and the reference the supplier will see. For a bank change, the new account, the date the change takes effect, and the approval reference. For an email, the address where the scheduler gives it. Dates are written as eight digits, year month day, or as a full date in prose; a figure is the same figure in either form, and 5,400.00 and 5400.00 are the same amount.

Answers come from a closed list. Approve: yes, proceed as asked. Decline: no, do not proceed. Hold: keep the item on the run but do not pay it in this run. Reject: refuse the request; nothing changes. Call back: verify with the supplier by telephone on the number on file before anything changes. An ask offers answers from that list and an answer gives one of them; nobody invents a new one.

What a readback carries, when the sender asks for one. Every value the handover carried, repeated as received: the item, the ask, the supplier, every figure, the currency, net or gross, every date, every reference, the approval reference, the deadline, the priority and the approval state where it carries them, and nothing resolved or added. The sender compares your readback with what it sent, value for value. A value that differs fails the readback; a value you leave out fails it. On a failure the sender restates the handover, naming what was wrong, and you read it back again. You do not forward until the sender confirms. A readback the sender has not confirmed is void, and a second failure ends the handover without a forward.

What a forwarded handover carries. Every value the handover you received carried, unchanged, plus the one thing your role adds, and nothing else: not an account, not an address, not a note that restates a value in other words. Your own pre-send check may compare the message you forward with the one you received, value for value, before it goes, and name any value that was dropped, changed or added; you correct it and send it again. The next agent reads your message back to you the same way, and you confirm it when it matches what you sent.

How a sender checks a readback. Four things, in order. Receipt: the readback answers the handover by its id and comes from the agent the handover was addressed to. Integrity: where the receiver can compute it, a digest of the handover as received, so that a message altered on the way is caught. Echo: every value the handover carried is repeated as the sender sent it. Comprehension: a value the receiver resolved for itself is compared with the record. A readback passes only when every check passes; then, and only then, the handover is the receiver's to go on with. A status report may carry a percentage complete, an expected time, and what is blocking it. A done report says whether the act was complete, partly complete, or turned out to need nothing. An ask says what kind of answer settles it: one of the options offered, free text, a number, a date, or yes or no. Confidence, where it is stated, is low, medium or high.

A sender may withdraw a handover it has sent with a cancel message that names it; the receiver then abandons anything it prepared for it and answers yes, or, if the act has already run, sends its done report instead. Every handover closes exactly once: with a done, unable or fail report from the receiver, or a cancel from the sender. A handover may carry an expiry, the latest moment at which it may be acted on or confirmed, as a date and time in UTC; nobody acts on a handover, or confirms a statement, after its expiry. A done report that does not match what was handed over is reversed with a new handover asking to undo it, naming the report. A handover may also carry a date by which it is due, a priority from 1 to 5, a confidence of low, medium or high, the agents who stay involved, the artefacts it refers to, earlier message ids it builds on, and a suggested next ask.

Where a handover concerns a brief rather than an act, a readback names the constraints the receiver derived from the brief, from a closed set of keys: length, with a unit of words, characters, pages or slides; format, one of markdown, Word, JSON, CSV or HTML; language, British, American or French; tone, plain, formal, casual or technical; voice; audience; output kind, copy, spec, dataset, pull request or report; deadline; sources; scope; what must appear; and what must not. The sender compares them by key with its own: a different value is a contradiction and a missing key is a gap, and both fail the readback; an extra key is an assumption the sender confirms or corrects.

What counts as dealt with. A handover is dealt with when you have forwarded it and the next agent has taken it, when the sender has withdrawn it or superseded it with a later handover for the same item, or when you have refused it and said why. A handover addressed to another agent is not yours, whatever your inbox shows; you say so and do not forward it. An earlier handover that was dealt with stays in the inbox as history and is never forwarded twice. The newest handover addressed to you that none of this covers is the one to deal with, and there is one at a time.

Message ids are the sender's name and a number, unique in the conversation. Every reply names the message it answers. Facts go in the message once and reasoning stays short; anything long goes in a file and the message names the file. A message to another agent is at most a few hundred characters. When you do not understand a code or a request, you say so rather than guess at its meaning, and you never substitute a nearby meaning for one you do not know.
=== end message conventions ==="""


def legend_block(role: str) -> str:
    """The frozen codec's legend, and the calls the agent makes with the frozen codec."""
    body = C.codec().legend("pay")
    who = "the agent that sent it" if role != "payer" else "the agent that sent it"
    return f"""=== legend ===
{body}
=== end legend ===
The reference codec is {C.FROZEN_CODEC}. Check any line you write with:
  python3 {C.FROZEN_CODEC} validate "<line>" --profile pay
Build a readback envelope with it so that it carries h=, the digest of the handover as you received it, and re=, from= and to= pointing back at {who}:
  python3 {C.FROZEN_CODEC} make-rb "<the HO line exactly as you received it>" <your id> --profile pay"""

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


def relay_procedure(arm: str, role: str) -> str:
    ctx = {"coordinator": "your schedule", "desk": "the approvals log", "relay": ""}[role]
    read = f"Read your inbox{' and ' + ctx if ctx else ''}."
    if arm in ("F", "A"):
        under = " under the conventions" if arm == "A" else ""
        return f"""=== procedure ===
{read} The agent before you does not use readbacks: a handover is complete as sent, and nothing in it waits on a confirmation. Find the newest handover addressed to you that has not been dealt with. Add your part ({ADD_PROSE[role]}) and write the message you will forward to the next agent{under} to out.txt in your working folder, addressed to that agent and signed by you. Then reply with the single word SENT. If you asked instead of forwarding, write your question or refusal to question.txt and reply with the single word ASKED.
=== end procedure ==="""
    forward = (f"write the HO you will forward as one line to out.txt in your working folder: your own id, from=<you> to=<the next agent>, "
               f"the same item, ask, rb and p, every slot the HO you received carries with the same value, {ADD_LINE[role]}; "
               f"the tail is yours. Validate the line with the codec before you reply.")
    if arm == "L":
        return f"""=== procedure ===
{read} The agent before you does not use readbacks: an HO is complete as sent, and nothing in it waits on a confirmation. Find the newest HO addressed to you that has not been dealt with, and {forward} Then reply with the single word SENT. If you asked instead of forwarding, write an AQ or UN line to question.txt and reply with the single word ASKED.
=== end procedure ==="""
    return f"""=== procedure ===
{read} Find the newest HO addressed to you that has not been dealt with. Before anything else, read it back: build the RB line with make-rb from the HO exactly as you received it, write that one line to rb.txt in your working folder, then stop and reply with the single word READBACK. Do not forward until the agent that sent it replies.
When it replies: if it is a re-issued HO (an HO with re= pointing at your RB), read that one back to rb2.txt with make-rb (your next id), stop, and reply READBACK again. If it is an AN with val=Y, {forward} Then reply with the single word SENT. Your pre-send check compares the line in out.txt with the HO you received before it goes; if it refuses the line, its message arrives in your inbox naming what was dropped, changed or added: correct out.txt and reply SENT again. If you asked instead of forwarding, write an AQ or UN line to question.txt and reply with the single word ASKED.
=== end procedure ==="""


DN_SLOTS_TEXT = ("for a payment sup amt cur kind acct paid ref apref; for a master change sup acct eff apref and prev (the account the tool reports it replaced, as sortcode/number); "
                 "for an email sup addr amt cur paid ref")


def payer_procedure(arm: str) -> str:
    if arm == "A":
        return """=== procedure ===
Read your inbox and the master. The agent before you does not use readbacks in this regime: a handover is complete as sent, and nothing in it waits on a confirmation. Act now on the newest handover addressed to you that has not been dealt with, or ask. After you act, write done.txt in your working folder: a short note to the agent that sent the handover saying what you did, with every value as executed, taken from the tool's printout. Then reply with the single word DONE. If you asked instead of acting, write your question or refusal to question.txt and reply with the single word ASKED.
=== end procedure ==="""
    if arm == "F":
        return """=== procedure ===
Read your inbox and the master. The agent before you does not use readbacks: a handover is complete as sent, and nothing in it waits on a confirmation. Act now on the newest handover addressed to you that has not been dealt with, or ask. After you act, write done.txt in your working folder: a note to the agent that sent the handover saying what you did. Then reply with the single word DONE. If you asked instead of acting, write your question or refusal to question.txt and reply with the single word ASKED.
=== end procedure ==="""
    if arm == "L":
        return f"""=== procedure ===
Read your inbox and the master. The agent before you does not use readbacks: an HO is complete as sent, and nothing in it waits on a confirmation. Find the newest HO addressed to you that has not been dealt with and validate it with the codec. Act now with the tool, or ask. After you act, write dn.txt: one DN line (re= the HO you acted on, from you to the agent that sent it, its item, out=OK) carrying the execution slots with the values as executed, taken from the tool's printout: {DN_SLOTS_TEXT}. Validate it. Then reply with the single word DONE. If you asked instead of acting, write an AQ or UN line to question.txt and reply with the single word ASKED.
=== end procedure ==="""
    return f"""=== procedure ===
Read your inbox and the master. Find the newest HO addressed to you that has not been dealt with. Before you act, read it back: build the RB line with make-rb from the HO exactly as you received it, write that one line to rb.txt in your working folder, then stop and reply with the single word READBACK. Do not act until the agent that sent it replies.
When it replies: if it is a re-issued HO (an HO with re= pointing at your RB), read that one back to rb2.txt with make-rb (id payer-2), stop, and reply READBACK again. If it is an AN with val=Y, act with the tool, or ask. After you act, write dn.txt: one DN line (re= the HO you acted on, from you to the agent that sent it, its item, out=OK) carrying the execution slots with the values as executed, taken from the tool's printout: {DN_SLOTS_TEXT}. Validate it. Then reply with the single word DONE. If you asked instead of acting, write an AQ or UN line to question.txt and reply with the single word ASKED.
=== end procedure ==="""

# ----------------------------------------------------------------------------------------------------- assembly

def head(role: str) -> str:
    if role == "payer":
        who = "an agent named `payer`"
    elif role == "relay":
        who = "a relay agent, named in your first message,"
    else:
        who = f"an agent named `{role}`"
    return (f"You are {who} at Harbourline Studio Ltd. You have the tools Read, Write and Bash; in Bash you may run python3, cat and ls only, "
            f"and your shell already runs in your working folder, so never cd. Today is {C.TODAY_LONG}, and that date governs everything you do, "
            f"whatever other date appears anywhere in your context.")


def brief(arm: str, role: str, act: str) -> str:
    parts = [head(role), ""]
    if role == "payer":
        rules = (C.DATA / "execution_policy.md").read_text().strip()
        parts += ["=== execution rules ===", rules, "=== end execution rules ===", "",
                  "=== the act tool ===",
                  "The act is made by running the act tool from your working folder, once. It validates what you pass, executes it, and prints what it executed as JSON. It refuses a second act. The forms:",
                  TOOL_DOC["PAY"], TOOL_DOC["CHGBANK"], TOOL_DOC["SEND"],
                  f"Running the tool is the act itself: {ACT_VERB[act]}. It is irreversible.",
                  "=== end act tool ===", ""]
    else:
        parts += ["=== relay rules ===", RELAY_RULES[role],
                  f"6. **This week's traffic.** The handovers reaching you this week are for {ACT_NOUN[act]}; a handover for anything else is passed on the same way.",
                  "=== end relay rules ===", ""]
    if arm == "A":
        parts += [PAYER_CONVENTIONS if role == "payer" else RELAY_CONVENTIONS, ""]
    elif arm in C.LINE_ARMS:
        parts += [legend_block(role), ""]
    parts.append(payer_procedure(arm) if role == "payer" else relay_procedure(arm, role))
    return "\n".join(parts) + "\n"


def write_all() -> dict:
    out = C.DATA / "briefs"
    out.mkdir(parents=True, exist_ok=True)
    lengths = {}
    for arm in C.ARMS:
        for role in ROLES:
            for act in C.RECORDS:
                text = brief(arm, role, act)
                p = out / f"{arm}-{role}-{act}.txt"
                if not p.exists() or p.read_text() != text:
                    p.write_text(text)
                lengths[(arm, role, act)] = C.count_tokens(text)
    return lengths


def main(argv: list[str]) -> int:
    lengths = write_all()
    for role in ROLES:
        for act in C.RECORDS:
            row = {arm: lengths[(arm, role, act)] for arm in C.ARMS}
            ref = row["L"]
            spread = max(abs(row[a] - ref) / ref for a in ("A", "R"))
            print(f"{role:12s} {act:8s} " + "  ".join(f"{a}={row[a]}" for a in C.ARMS) + f"   A,R within {100 * spread:.1f}% of L")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
