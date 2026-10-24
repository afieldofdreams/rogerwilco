## turn 1

### user

You are the agent named desk; the agent before you in the chain is coordinator and the agent after you is payer. The message you received, from coordinator:

RW1 HO coordinator-1 from=coordinator to=desk item=inv:MD-2026-057 ask=SEND p=pay rb=all sup=marlow amt=5400.00 cur=GBP paid=20261002 ref=MD-2026-057 addr=billing@marlowdesign.co.uk due=20261002 pri=3 // for the payer

# approvals.json
{
 "note": "Approvals log: every approval the FD has given, by reference, with the supplier and the item it covers. A handover is approved when the log holds an entry with its approval reference covering its item; nothing else approves it.",
 "as_of": "2026-10-02",
 "approvals": [
  {
   "ref": "FD-0926",
   "supplier": "Evergreen Office Supplies",
   "item": "bank change",
   "what": "payment details to 60-83-71/44019482 from 3 October 2026, call-back done",
   "date": "2026-09-30"
  },
  {
   "ref": "FD-0927",
   "supplier": "Kestrel Cloud Inc",
   "item": "7731",
   "what": "hold for the USD run of 9 October, 960.00 USD net",
   "date": "2026-09-30"
  },
  {
   "ref": "FD-0929",
   "supplier": "Marlow Design Partners LLP",
   "item": "MD-2026-057",
   "what": "payment, 5400.00 GBP gross, 2 October 2026",
   "date": "2026-09-30"
  },
  {
   "ref": "FD-0930",
   "supplier": "Coleridge Stationers Ltd",
   "item": "statement September",
   "what": "statement reviewed, balance nil, no payment",
   "date": "2026-10-01"
  },
  {
   "ref": "FD-0918",
   "supplier": "Ashdown Catering Ltd",
   "item": "ACL-2291",
   "what": "payment, 640.00 GBP gross, 25 September 2026",
   "date": "2026-09-24"
  },
  {
   "ref": "FD-0921",
   "supplier": "Northfield Print Ltd",
   "item": "bank change",
   "what": "payment details to 20-45-67/31776243 from 30 September 2026, call-back done",
   "date": "2026-09-29"
  }
 ]
}

# Your reply
Your code composed this readback from the message as delivered to you:
RW1 RB desk-1 re=coordinator-1 from=desk to=coordinator item=inv:MD-2026-057 ask=SEND due=20261002 pri=3 p=pay h=26ce544bdd1e sup=marlow amt=5400.00 cur=GBP paid=20261002 ref=MD-2026-057 addr=billing@marlowdesign.co.uk

Reply CONFIRM if every value in the readback is what the HO you received carries (the readback repeats neither rb= nor the tail, by design), or DISPUTE: <slot> <value> if one is not; or reply ASK on the first line and your question below it.

### assistant

CONFIRM

## turn 2

### user

Message from coordinator:
RW1 AN coordinator-51 re=desk-1 p=pay from=coordinator to=desk val=Y // readback correct; add your part and forward

Reply with the one HO line you forward to payer, and nothing else, or reply ASK on the first line and your question below it.

### assistant

RW1 HO desk-1 from=desk to=payer item=inv:MD-2026-057 ask=SEND p=pay sup=marlow amt=5400.00 cur=GBP paid=20261002 ref=MD-2026-057 addr=billing@marlowdesign.co.uk

## turn 3

### user

Message from your pre-send check:

Your pre-send check refused the line you replied with before it went: record: HO does not carry rb (record has rb=all); record: HO does not carry due (record has due=20261002); record: HO does not carry pri (record has pri=3); record: HO does not carry appr (record has appr=OK). Reply with the corrected line, one line, carrying every slot of the HO you received with the same value, plus only what your role adds, addressed to the next agent. If the check says to ask instead, reply ASK and your question.

### assistant

RW1 HO desk-1 from=desk to=payer item=inv:MD-2026-057 ask=SEND p=pay rb=all sup=marlow amt=5400.00 cur=GBP paid=20261002 ref=MD-2026-057 addr=billing@marlowdesign.co.uk appr=OK

