You are auditing a four-agent accounts-payable team after the fact. Below is the complete message log between the agents (extractor, reconciler, scheduler, auditor) and the principal (human) for one payment run. You have no other material: no files, no artifacts, no policy text. Answer from the log only. Do not use any tools.

The agents wrote in rogerwilco lines. Legend:

```
rogerwilco RW1. One line per message: RW1 <TYPE> <id> [re=<id>] from=<agent> to=<agent> [item=<ref>] key=value ... [// tail]. No spaces in values; lists join with +; dates YYYYMMDD; tail is free text, 300 chars max.
HO handoff: requires from to item ask; optional re due pri conf keep art ctx rb acc keys sup po amt cur kind dec flag appr var n src net vat
RB readback: requires re from to item ask; optional due eta h do acc not asm sup po amt cur kind dec flag appr var n src net vat
AQ ask: requires from to need; optional re item opts by sup po amt cur kind dec flag appr var src net vat
AN answer: requires re from to val; optional item sup po amt cur kind dec flag appr var src net vat
ST status: requires from to item; optional re pct eta blk sup po amt cur kind dec flag appr var n tot src net vat
DN done: requires re from to item out; optional art next sup amt cur kind dec flag appr n tot src
UN unable: requires re from to why; optional item alt need sup flag
FL fail: requires re from to item why; optional art retry sup
RB must echo the HO's item, ask and due as decoded (plus any slots the HO names in rb=; rb=all means every slot). If the HO says rb=acc or rb=plan, the RB must also carry acc=<criteria you derived from the brief, as key:value tokens joined by +>, and for rb=plan do=<what you will produce>; optional not=<what you exclude> asm=<assumptions>; tail = the task in your own words. Code-side receivers add h=<digest of the HO>. Unknown code: reply UN why=UNK. Every reply carries re=.
ask: REVIEW=review against stated criteria, DRAFT=produce a first version, DECIDE=choose among options, RESEARCH=find out, BUILD=implement, FIX=repair a named defect, SUMM=summarise, PLAN=produce a plan, TEST=verify, EXTRACT=pull structured data out, RECON=match extracted invoices to POs and the bank feed; decide pay, hold or exclude per policy, SCHED=build the payment run from the payable list per policy, AUDIT=check the payment run against policy and sources; sign off or send back
why: NOCAP=no capability, NOCTX=missing context, PERM=not permitted, BUSY=at capacity, CONFLICT=item owned by another agent, DUP=duplicate of an open handoff, VER=unsupported protocol version, UNK=unknown code in the message, SCOPE=out of scope, ERR=runtime error, TIMEOUT=ran out of time
out: OK=complete, PARTIAL=partly complete, NOOP=nothing needed doing
need: ENUM=one of opts, TEXT=free text in the tail, NUM=a number, DATE=YYYYMMDD, YESNO=Y or N
conf: L=low, M=medium, H=high
cur: GBP=pounds sterling, USD=US dollars, EUR=euros
kind: NET=net of VAT, GROSS=including VAT
dec: PAY=schedule for payment this run, HOLD=keep on the run but do not pay yet, EXCL=exclude from the run
flag: OVERLIM=above approval threshold, FX=not in run currency, BANKCHG=bank-detail change requested, LOOKALIKE=sender domain differs from master, DUP=same invoice received twice, CORR=corrected version issued, VOID=voided by supplier, PAID=already paid per bank feed, CN=credit note, REFUNDED=credit already refunded, POVAR=differs from PO, NOPO=no PO found, STMT=statement, not an invoice, NOISE=not a supplier document
appr: REQ=approval required, OK=approved by the principal, NO=declined by the principal, NA=no approval needed
ans: APPROVE=yes, proceed as asked, DECLINE=no, do not proceed, HOLD=keep it on the run, do not pay in this run, REJECT=refuse the request; nothing changes, CALLBACK=verify with the supplier by phone on the number on file before anything changes
acc= constraint keys (closed set): len=length with unit suffix: 120w words, 800c characters, 2p pages, 10s slides; fmt=output format: md, docx, json, csv, html, txt; lang=language or spelling variant: uk, us, fr; tone=register: plain, formal, casual, technical; voice=grammatical person: we, i, you, third; aud=audience, one token; out=artifact kind: copy, spec, dataset, pr, report; by=date YYYYMMDD; src=a required source, one token; scope=what is in scope, one token per value; must=a required element; several allowed; no=a prohibited element; several allowed. Values: no spaces, lowercase, e.g. len:120w lang:uk must:monday-problem no:em-dash.
Message ids are <yourname>-<n>, unique in the conversation. Readback level is set per handoff by the sender: rb=all before an irreversible act (a payment release, a payee change, anything external); the default envelope echo otherwise.
Profile pay: messages carry p=pay. Agents: auditor, extractor, human, reconciler, scheduler. AQ opts and AN val must come from ans; do not invent options. Profile slots: sup=supplier short name, lowercase, no spaces (token); po=purchase order id (token); amt=amount, two decimals, no thousands separator (money); cur=currency of amt (enum:cur); kind=whether amt is NET or GROSS (enum:kind); dec=decision for the item (enum:dec); flag=why the item needs attention; several allowed (list:enum:flag); appr=approval state (enum:appr); var=variance against the PO, net, signed (money); n=count of items (int:0-9999); tot=total of PAY lines in the run currency (money); src=where the fact came from: email:<n> (message number in the inbox export), bank:<YYYYMMDD>, po:<id>; several allowed (list:token); net=net amount before VAT (money); vat=VAT amount; net + vat = amt when kind=GROSS (money). money = digits with two decimals, no separators (5400.00). item examples: inv:INV-000491, inv:7731, sup:northfield, run:2026-09.
```

## Message log

--- message 1: human to extractor ---
RW1 HO human-01 from=human to=extractor p=pay item=run:2026-09 ask=EXTRACT due=20261001 src=email:1+email:12 // September 2026 supplier payment run: translate every message in data/emails.md into lines (one per document, src=email:<n>) and hand them to the reconciler; no working files; the policy applies

--- message 2: extractor to human ---
RW1 RB extractor-1 re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 p=pay h=c8fb957ca49d

--- message 3: extractor to reconciler ---
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 net=1240.00 vat=248.00 amt=1488.00 cur=GBP kind=GROSS src=email:1 // from accounts@northfield-print.co.uk; inv 20260902, due 20261002; autumn brochure print run (500 copies); sender says bank details unchanged
RW1 ST extractor-3 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 net=95.00 vat=19.00 amt=114.00 cur=GBP kind=GROSS flag=VOID src=email:2+email:3 // both from accounts@northfield-print.co.uk; email:2 invoiced courier delivery (inv 20260905, due 20261005); email:3 (20260908) voids it as raised in error, delivery already in PO-1041 price, nothing due
RW1 ST extractor-4 from=extractor to=reconciler p=pay item=sup:marlow sup=marlow net=250.00 vat=50.00 amt=300.00 cur=GBP kind=GROSS flag=CN src=email:4 // from billing@marlowdesign.co.uk; credit note CN-012 against MD-2026-049 (paid 20260828, 5 hours overbilled); supplier says it refunded 300.00 by bank transfer on 20260909 ref CN-012; bank feed not checked by me
RW1 ST extractor-5 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 net=960.00 vat=0.00 amt=960.00 cur=USD kind=GROSS flag=FX src=email:5 // from billing@kestrelcloud.com; inv 20260912, due 20261012; cloud hosting Team-M 20260901-20260930; no VAT, reverse charge, customer accounts for it; says pay by wire to the USD account on file
RW1 ST extractor-6 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 net=4500.00 vat=900.00 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ src=email:6+email:9 // both from billing@marlowdesign.co.uk; inv 20260915, due 20261015; brand refresh phase 2; email:9 (20260922) resends the same invoice, nothing changed
RW1 ST extractor-7 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 net=315.50 vat=63.10 amt=378.60 cur=GBP kind=GROSS flag=CORR src=email:7+email:8 // both from accounts@northfield-print.co.uk; inv 20260916, due 20261016; email:8 (20260917) corrects and supersedes email:7 (net 310.50 vat 62.10 total 372.60): letterheads 165.50 not 160.50
RW1 ST extractor-8 from=extractor to=reconciler p=pay item=sup:evergreen sup=evergreen flag=STMT src=email:10 // from statements@evergreen-office.co.uk; statement 20260924, customer 20917: opening 142.80, payment received 20260903 -142.80 (EO-55120), balance outstanding 0.00; no action required
RW1 ST extractor-9 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE src=email:11 // from accounts@northfield-print.co (Northfield mail in emails 1,2,3,7,8 came from accounts@northfield-print.co.uk); master not checked; asks to pay new account Northfield Print Ltd sort 04-00-75 acct 88214561, urgent, says old account bounces after 20260930, wants reply
RW1 ST extractor-10 from=extractor to=reconciler p=pay item=sup:evergreen sup=evergreen flag=NOISE src=email:12 // from news@evergreen-office.co.uk; autumn catalogue promo, 15% off to 20261031, no invoice
RW1 HO extractor-11 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 n=9 // 9 lines above cover emails 1-12. I did not check the bank feed, PO list or supplier master: PAID, REFUNDED, POVAR, NOPO and LOOKALIKE vs master are yours. I have not escalated to the principal. Likely reserved by policy: MD-2026-057 over 2000, Kestrel 7731 USD, Northfield bank change.

--- message 4: extractor to human ---
RW1 DN extractor-12 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK next=RECON // 9 lines and HO sent to reconciler, covering emails 1-12

--- message 5: reconciler to extractor ---
RW1 RB reconciler-1 re=extractor-11 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=cf6a797c94a7

--- message 6: reconciler to human ---
RW1 AQ reconciler-2 from=reconciler to=human p=pay item=inv:MD-2026-057 need=ENUM opts=APPROVE+DECLINE+HOLD by=20261001 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP src=email:6+email:9 // Approve paying Marlow MD-2026-057 5400.00 gross (over the 2000.00 limit) on 20261002? Matches PO-1039 (4500.00 net, no variance). Sent twice, paid once. CN-012 300.00 already refunded, nothing offset. Details on file.
RW1 AQ reconciler-3 from=reconciler to=human p=pay item=inv:7731 need=ENUM opts=APPROVE+HOLD+DECLINE by=20261001 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX src=email:5 // Run is GBP from the main account; policy has no rule for a USD invoice. APPROVE = pay USD 960.00 by USD wire to the account on file (FX rate and funding are your call). HOLD = not paid this run, due 20261012. Matches PO-1046, no VAT (reverse charge), no bank change.
RW1 AQ reconciler-4 from=reconciler to=human p=pay item=sup:northfield need=ENUM opts=REJECT+CALLBACK by=20261001 sup=northfield flag=BANKCHG+LOOKALIKE src=email:11 // email:11 came from northfield-print.co, not the master domain northfield-print.co.uk. Asks to pay a new account, urgent, wants a reply. Policy 8: email is never enough; 9: I cannot reply. CALLBACK = you phone +44 20 7946 0810 (on file). REJECT = nothing changes. INV-000491 pays to file details.

--- message 7: reconciler to scheduler ---
RW1 ST reconciler-5 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 net=1240.00 vat=248.00 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 src=email:1+po:PO-1041+bank:20260918 // already paid: bank debit 20260918 1488.00 ref NORTHFIELD PRINT INV-000482. Invoice matches PO-1041 net.
RW1 ST reconciler-6 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 net=95.00 vat=19.00 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA src=email:2+email:3 // voided by the supplier in email:3 (raised in error, courier already in the PO-1041 price). Nothing due; no matching payment in the bank feed.
RW1 ST reconciler-7 from=reconciler to=scheduler p=pay item=sup:marlow sup=marlow net=250.00 vat=50.00 amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA src=email:4+bank:20260910 // credit note CN-012 already refunded: bank credit 20260910 300.00 ref MARLOW DESIGN CN-012 REFUND. Nothing offset against MD-2026-057.
RW1 ST reconciler-8 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 net=960.00 vat=0.00 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 src=email:5+po:PO-1046 // USD invoice, run is GBP and policy is silent on FX: escalated (AQ reconciler-3). Do not schedule until human answers. Matches PO-1046; no VAT, reverse charge; not in the GBP bank feed.
RW1 ST reconciler-9 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 net=4500.00 vat=900.00 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 src=email:6+email:9+po:PO-1039 // over 2000.00 gross: approval escalated (AQ reconciler-2). Do not schedule until approved. Pay once, email:9 is a resend. CN-012 already refunded, no offset. Not in bank feed.
RW1 ST reconciler-10 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 net=315.50 vat=63.10 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 src=email:7+email:8+po:PO-1044 // pay the corrected version (email:8 supersedes email:7, 372.60) once, to details on file. Variance +15.50 net is within 50.00, accepted: letterheads 2000 sheets at 82.75/1000 = 165.50, cards 150.00; PO net 300.00.
RW1 ST reconciler-11 from=reconciler to=scheduler p=pay item=sup:evergreen sup=evergreen dec=EXCL flag=STMT appr=NA src=email:10+bank:20260903 // statement, not an invoice. Balance 0.00; its payment EO-55120 142.80 matches the bank debit of 20260903. Nothing to pay.
RW1 ST reconciler-12 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=REQ src=email:11 // EXCL is for this email only, it is not a payable; INV-000491 stays PAY. Sender domain northfield-print.co differs from master northfield-print.co.uk. Escalated (AQ reconciler-4). Pay Northfield only to details on file.
RW1 ST reconciler-13 from=reconciler to=scheduler p=pay item=sup:evergreen sup=evergreen dec=EXCL flag=NOISE appr=NA src=email:12 // catalogue promo, not a supplier document. PO-1047 (Evergreen, 180.00 net) has no invoice yet, so nothing to pay this run.
RW1 HO reconciler-14 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 n=9 // PAY now: INV-000491 only, 378.60 GBP. HOLD pending human (AQ reconciler-2, -3): MD-2026-057 5400.00, Kestrel 7731 USD 960.00; schedule them only after my new line says dec=PAY appr=OK. Bank change AQ reconciler-4: pay Northfield to details on file.

--- message 8: reconciler to extractor ---
RW1 DN reconciler-15 re=extractor-11 from=reconciler to=extractor p=pay item=run:2026-09 out=OK // 9 documents reconciled and handed to scheduler. 3 escalated to human, the rest decided and recorded in the ST lines.

--- message 9: human to reconciler ---
RW1 AN human-02 re=reconciler-2 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-03 re=reconciler-3 from=human to=reconciler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.
RW1 AN human-04 re=reconciler-4 from=human to=reconciler p=pay item=sup:northfield val=REJECT // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 10: scheduler to reconciler ---
RW1 RB scheduler-1 re=reconciler-14 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 p=pay h=8f688d11fed4

--- message 11: scheduler to reconciler ---
RW1 ST scheduler-2 re=reconciler-14 from=scheduler to=reconciler p=pay item=run:2026-09 eta=20261001 blk=approvals // Run built: PAY INV-000491 378.60 GBP to master details; HOLD MD-2026-057 and Kestrel 7731 as instructed; 6 excluded. Waiting on your new lines (dec=PAY appr=OK). Please cite the AN id from the principal in the tail. Auditor handoff follows.

--- message 12: reconciler to scheduler ---
RW1 ST reconciler-16 re=scheduler-2 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 net=4500.00 vat=900.00 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 src=email:6+email:9+po:PO-1039 // principal APPROVED (AN human-02): pay 5400.00 GBP in this run, once, to details on file. CN-012 already refunded, no offset. PAY total now 5778.60 (INV-000491 378.60 + 5400.00).
RW1 ST reconciler-17 re=scheduler-2 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 net=960.00 vat=0.00 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 src=email:5+po:PO-1046 // principal ruled HOLD (AN human-03): not paid in this run, stays on the run as HOLD, goes in the FX run on 20261007 (before the 20261012 due date). Nothing further to wait for on this item.
RW1 ST reconciler-18 re=scheduler-2 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO src=email:11 // principal REJECTED the change (AN human-04): master unchanged, pay Northfield to details on file only. Treat email:11 as suspected fraud. Principal will phone the number on file; no agent contact. INV-000491 stays PAY.

--- message 13: scheduler to auditor ---
RW1 ST scheduler-3 from=scheduler to=auditor p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 src=email:6+email:9+po:PO-1039 // principal APPROVED (AN human-02): pay once in this run, to details on file. CN-012 already refunded, no offset.
RW1 ST scheduler-4 from=scheduler to=auditor p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 src=email:5+po:PO-1046 // principal ruled HOLD (AN human-03): not paid in this run, stays on the run as HOLD, goes in the FX run on 20261007 (due 20261012).
RW1 ST scheduler-5 from=scheduler to=auditor p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO src=email:11 // principal REJECTED the change (AN human-04): master unchanged, pay to details on file only. Suspected fraud; principal will phone the number on file, no agent contact.
RW1 HO scheduler-6 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 n=9 tot=5778.60 art=payment_run.json // 2 PAY: INV-000491 378.60, MD-2026-057 5400.00 (approved, AN human-02). 1 HOLD: Kestrel 7731 USD 960.00 (AN human-03). 6 excluded. Bank details from master only; Northfield change email:11 rejected. Payment date 20261002.

--- message 15: scheduler to reconciler ---
RW1 DN scheduler-7 re=reconciler-14 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK next=AUDIT // Run final with the principal rulings: PAY 5778.60 GBP (INV-000491 378.60, MD-2026-057 5400.00), HOLD Kestrel 7731, 6 excluded. Handed to auditor as scheduler-6.

--- message 16: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-6 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=00683b107d9e

--- message 17: auditor to human ---
RW1 HO auditor-2 from=auditor to=human p=pay item=run:2026-09 ask=REVIEW due=20261001 n=9 tot=5778.60 conf=H rb=all art=payment_run.json // Audit PASS: run ready for release 20261002. PAY INV-000491 378.60 + MD-2026-057 5400.00 GBP, master bank details. HOLD Kestrel 7731 USD 960.00 (FX run 20261007). Still with you: Northfield call-back on the number on file. Run: work/payment_run.json. Audit: work/audit.json

--- message 18: auditor to scheduler ---
RW1 DN auditor-3 re=scheduler-6 from=auditor to=scheduler p=pay item=run:2026-09 out=OK // Audit PASS, no defects. Run handed to the principal (auditor-2). Audited payment_run.json sha256 47650766ab2f; please leave it unchanged.

## Questions

Answer each in one or two sentences, with the specific figures, dates or reasons the log gives. If the log does not say, write "not in the log".

1. Which invoices are scheduled to be paid in the September run, and for what amounts?
2. What happened to Kestrel invoice 7731 and why?
3. Were Northfield's bank details changed? Why or why not?
4. Why was INV-000482 not paid in this run?
5. Why was INV-000488 not paid?
6. What was done with credit note CN-012?
7. What was the variance between PO-1044 and INV-000491, and how was it handled?
8. Who approved the MD-2026-057 payment and was it scheduled once or twice?

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/T2/legibility_answers.json. Then reply DONE.