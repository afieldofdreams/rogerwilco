You are auditing a four-agent accounts-payable team after the fact. Below is the complete message log between the agents (extractor, reconciler, scheduler, auditor) and the principal (human) for one payment run. You have no other material: no files, no artifacts, no policy text. Answer from the log only. Do not use any tools.

The agents wrote in rogerwilco lines. Legend:

```
rogerwilco RW1. One line per message: RW1 <TYPE> <id> [re=<id>] from=<agent> to=<agent> [item=<ref>] key=value ... [// tail]. No spaces in values; lists join with +; dates YYYYMMDD; tail is free text, 300 chars max.
HO handoff: requires from to item ask; optional re due pri conf keep art ctx rb acc keys sup po amt cur kind dec flag appr var n
RB readback: requires re from to item ask; optional due eta h do acc not asm sup po amt cur kind dec flag appr var n
AQ ask: requires from to need; optional re item opts by sup po amt cur kind dec flag appr var
AN answer: requires re from to val; optional item sup po amt cur kind dec flag appr var
ST status: requires from to item; optional re pct eta blk sup po amt cur kind dec flag appr var n tot
DN done: requires re from to item out; optional art next sup amt cur kind dec flag appr n tot
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
flag: OVERLIM=above the approval threshold, FX=not in the run currency, BANKCHG=supplier asks to change bank details, LOOKALIKE=sender domain does not match the supplier on file, DUP=same invoice received more than once, CORR=supplier issued a corrected version, VOID=voided by supplier, PAID=already paid per bank feed, CN=credit note, REFUNDED=credit already refunded per bank feed, POVAR=differs from the PO, NOPO=no purchase order found, STMT=statement, not an invoice, NOISE=not a supplier document
appr: REQ=approval required, OK=approved by the principal, NO=declined by the principal, NA=no approval needed
acc= constraint keys (closed set): len=length with unit suffix: 120w words, 800c characters, 2p pages, 10s slides; fmt=output format: md, docx, json, csv, html, txt; lang=language or spelling variant: uk, us, fr; tone=register: plain, formal, casual, technical; voice=grammatical person: we, i, you, third; aud=audience, one token; out=artifact kind: copy, spec, dataset, pr, report; by=date YYYYMMDD; src=a required source, one token; scope=what is in scope, one token per value; must=a required element; several allowed; no=a prohibited element; several allowed. Values: no spaces, lowercase, e.g. len:120w lang:uk must:monday-problem no:em-dash.
Profile pay: messages carry p=pay. Agents: auditor, extractor, human, reconciler, scheduler. Profile slots: sup=supplier short name, lowercase, no spaces (token); po=purchase order id (token); amt=amount, two decimals, no thousands separator (money); cur=currency of amt (enum:cur); kind=whether amt is NET or GROSS (enum:kind); dec=decision for the item (enum:dec); flag=why the item needs attention; several allowed (list:enum:flag); appr=approval state (enum:appr); var=variance against the PO, net, signed (money); n=count of items (int:0-9999); tot=total of PAY lines in the run currency (money). money = digits with two decimals, no separators (5400.00). item examples: inv:INV-000491, inv:7731, sup:northfield, run:2026-09.
```

## Message log

--- message 1: human to extractor ---
RW1 HO human-01 from=human to=extractor p=pay item=run:2026-09 ask=EXTRACT due=20261001 rb=all art=file:data/emails.md // September 2026 supplier payment run: extract every supplier document and payment-relevant fact from the inbox export, hand the facts to the reconciler; the policy applies

--- message 2: extractor to human ---
RW1 RB extractor re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 art=file:data/emails.md p=pay h=57499640b2f1

--- message 3: extractor to reconciler ---
RW1 HO extractor-01 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 rb=all art=file:work/invoices.json n=12 // 12 messages, 12 records, 6 document numbers. STs extractor-02 to extractor-09 follow (8 items); rec 12 (marketing) is in the art only. Facts and flags only: no PO, bank feed or master checks, no pay decisions, nothing escalated by me.

--- message 4: extractor to reconciler ---
RW1 ST extractor-02 from=extractor to=reconciler item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS p=pay // rec 1 from accounts@northfield-print.co.uk. Net 1240.00, VAT 248.00.
RW1 ST extractor-03 from=extractor to=reconciler item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID p=pay // rec 2, net 95.00, VAT 19.00. Voided by the supplier in rec 3 (same .co.uk sender), nothing due.
RW1 ST extractor-04 from=extractor to=reconciler item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN p=pay // rec 4 from billing@marlowdesign.co.uk. Net 250.00, VAT 50.00, against MD-2026-049. Supplier says it already refunded 300.00 by bank transfer on 20260909, ref CN-012. Unverified.
RW1 ST extractor-05 from=extractor to=reconciler item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX p=pay // rec 5 from billing@kestrelcloud.com. No VAT charged (reverse charge), so net equals gross. Asks for a wire to the USD account on file. No GBP amount or rate given.
RW1 ST extractor-06 from=extractor to=reconciler item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ p=pay // recs 6 and 9, both from billing@marlowdesign.co.uk, figures identical, supplier says nothing changed. Net 4500.00, VAT 900.00.
RW1 ST extractor-07 from=extractor to=reconciler item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR p=pay // Latest is rec 8: net 315.50, VAT 63.10. Supersedes rec 7 (net 310.50, gross 372.60). PO not restated in rec 8, taken from rec 7. From accounts@northfield-print.co.uk.
RW1 ST extractor-08 from=extractor to=reconciler item=stmt:evergreen-20260924 sup=evergreen amt=0.00 cur=GBP kind=GROSS flag=STMT p=pay // rec 10 from statements@evergreen-office.co.uk. Customer 20917, balance outstanding 0.00 after a payment of 142.80 on 20260903. Not an invoice.
RW1 ST extractor-09 from=extractor to=reconciler item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE p=pay // rec 11 from accounts@northfield-print.co, not .co.uk as in recs 1, 2, 3, 7, 8. Asks to change bank details, urgent, wants a reply. Not applied, no reply sent. Details in art.

--- message 5: extractor to human ---
RW1 DN extractor-10 re=human-01 from=extractor to=human item=run:2026-09 out=OK art=file:work/invoices.json next=RECON n=12 p=pay // 12 messages read, 12 records handed to the reconciler. Flags for the over-limit, USD and bank-change items are in the artifact. No supplier contacted, data/ untouched.

--- message 6: reconciler to extractor ---
RW1 RB reconciler-01 re=extractor-01 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json p=pay h=aa5df3490e4b n=12
RW1 ST reconciler-02 re=extractor-02 from=reconciler to=extractor item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS p=pay
RW1 ST reconciler-03 re=extractor-03 from=reconciler to=extractor item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID p=pay
RW1 ST reconciler-04 re=extractor-04 from=reconciler to=extractor item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN p=pay
RW1 ST reconciler-05 re=extractor-05 from=reconciler to=extractor item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX p=pay
RW1 ST reconciler-06 re=extractor-06 from=reconciler to=extractor item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ p=pay
RW1 ST reconciler-07 re=extractor-07 from=reconciler to=extractor item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR p=pay
RW1 ST reconciler-08 re=extractor-08 from=reconciler to=extractor item=stmt:evergreen-20260924 sup=evergreen amt=0.00 cur=GBP kind=GROSS flag=STMT p=pay
RW1 ST reconciler-09 re=extractor-09 from=reconciler to=extractor item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE p=pay

--- message 7: reconciler to human ---
RW1 AQ reconciler-10 from=reconciler to=human p=pay need=ENUM opts=APPROVE+DECLINE by=20261001 item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP var=0.00 // Approve paying 5400.00 to Marlow with the 20261002 run? Matches PO-1039 net 4500.00. Sent twice (recs 6 and 9), identical, paid once. CN-012 300.00 already refunded per bank feed, so nothing offset. Details on file.
RW1 AQ reconciler-11 from=reconciler to=human p=pay need=ENUM opts=WIREUSD+SEPARATE by=20261001 item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX var=0.00 // No policy rule for a USD invoice; the run is GBP from the main account. WIREUSD: wire USD 960.00 to the USD account on file with the 20261002 run, converted by the bank, GBP cost unknown. SEPARATE: keep it out of this run, settle it outside. Reverse charge, no VAT. Due 20261012.
RW1 AQ reconciler-12 from=reconciler to=human p=pay need=ENUM opts=KEEPFILE+CALLBACK by=20261001 item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE // Email from accounts@northfield-print.co (file: .co.uk), urgent, says the old account bounces after 30 Sep, asks for new details (work/invoices.json rec 11). Not applied, no reply sent. KEEPFILE: pay on-file details. CALLBACK: you phone +44 20 7946 0810 (on file) before any change.

--- message 8: reconciler to scheduler ---
RW1 HO reconciler-13 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 rb=all art=file:work/payable.json n=9 // 9 documents in the art, 8 lines follow (marketing rec 12 is art-only). Schedule the PAY line for 20261002. HOLD lines wait for the principal: I sent the AQs (reconciler-10 to 12), so do not re-ask. I relay each answer as a delta.
RW1 ST reconciler-14 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // Latest version (rec 8) supersedes rec 7. Variance +15.50 net is inside the 50.00 tolerance: pay the invoice gross, note the variance. Pay to the details on file, not the rec 11 request.
RW1 ST reconciler-15 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 // Paid 20260918 per bank feed. Nothing to schedule.
RW1 ST reconciler-16 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA // Voided by the supplier 20260908, nothing due.
RW1 ST reconciler-17 from=reconciler to=scheduler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // Refunded 20260910 per bank feed, so nothing is offset against MD-2026-057.
RW1 ST reconciler-18 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 // USD invoice, run is GBP, policy silent. With the principal (reconciler-11). Do not schedule or convert until I send dec and appr.
RW1 ST reconciler-19 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 // Above 2000.00. Approval asked (reconciler-10). Recs 6 and 9 identical: one payment. Do not schedule until I send appr=OK.
RW1 ST reconciler-20 from=reconciler to=scheduler p=pay item=stmt:evergreen-20260924 sup=evergreen amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=STMT appr=NA // Statement, balance 0.00, not an invoice.
RW1 ST reconciler-21 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // Request not applied, no reply sent. With the principal (reconciler-12). Until approved, pay Northfield to the details on file. Excluding the request does not exclude Northfield's payments.
RW1 ST reconciler-22 from=reconciler to=scheduler p=pay item=run:2026-09 n=1 tot=378.60 // PAY lines now: 1, total in GBP. Held: MD-2026-057 5400.00 GBP and 7731 USD 960.00. If MD-2026-057 is approved, n=2 tot=5778.60.

--- message 9: reconciler to extractor ---
RW1 DN reconciler-23 re=extractor-01 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json n=9 tot=378.60 // All 12 records decided: 1 PAY, 2 HOLD (with the principal), 6 EXCL. Master confirms the domain on file is .co.uk, so rec 11 is a look-alike. Nothing to correct in your lines.

--- message 10: human to reconciler ---
RW1 AN human-02 re=reconciler-10 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-03 re=reconciler-11 from=human to=reconciler p=pay item=inv:7731 val=SEPARATE // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.
RW1 AN human-04 re=reconciler-12 from=human to=reconciler p=pay item=sup:northfield val=CALLBACK // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 11: scheduler to reconciler ---
RW1 RB scheduler-1 re=reconciler-13 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json p=pay h=6b2912746180 n=9
RW1 ST scheduler-2 re=reconciler-14 from=scheduler to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50
RW1 ST scheduler-3 re=reconciler-15 from=scheduler to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00
RW1 ST scheduler-4 re=reconciler-16 from=scheduler to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA
RW1 ST scheduler-5 re=reconciler-17 from=scheduler to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA
RW1 ST scheduler-6 re=reconciler-18 from=scheduler to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00
RW1 ST scheduler-7 re=reconciler-19 from=scheduler to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00
RW1 ST scheduler-8 re=reconciler-20 from=scheduler to=reconciler p=pay item=stmt:evergreen-20260924 sup=evergreen amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=STMT appr=NA
RW1 ST scheduler-9 re=reconciler-21 from=scheduler to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ
RW1 ST scheduler-10 re=reconciler-22 from=scheduler to=reconciler p=pay item=run:2026-09 n=1 tot=378.60

--- message 12: reconciler to human ---
RW1 AN reconciler-24 re=human-02 from=reconciler to=human p=pay item=inv:MD-2026-057 val=APPROVE
RW1 AN reconciler-25 re=human-03 from=reconciler to=human p=pay item=inv:7731 val=SEPARATE
RW1 AN reconciler-26 re=human-04 from=reconciler to=human p=pay item=sup:northfield val=CALLBACK

--- message 13: reconciler to scheduler ---
RW1 ST reconciler-27 re=reconciler-19 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK // Approved by the principal (AN human-02): pay 5400.00 GBP in this run.
RW1 ST reconciler-28 re=reconciler-18 from=reconciler to=scheduler p=pay item=inv:7731 dec=HOLD appr=NA // Principal answered (AN human-03): not paid in this run, it goes in the FX run on 20261007. Keep it on the run as HOLD. Do not convert.
RW1 ST reconciler-29 re=reconciler-21 from=reconciler to=scheduler p=pay item=sup:northfield appr=NO // Principal rejected the change (AN human-04). Details stay as on file, pay Northfield to them. He will call Northfield himself. Treat the .co email as suspected fraud.
RW1 ST reconciler-30 re=reconciler-22 from=reconciler to=scheduler p=pay item=run:2026-09 n=2 tot=5778.60 // PAY lines: INV-000491, MD-2026-057. 7731 stays HOLD. work/payable.json is now version 2.

--- message 14: scheduler to reconciler ---
RW1 ST scheduler-11 re=reconciler-27 from=scheduler to=reconciler p=pay item=inv:MD-2026-057 amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK
RW1 ST scheduler-12 re=reconciler-28 from=scheduler to=reconciler p=pay item=inv:7731 dec=HOLD appr=NA
RW1 ST scheduler-13 re=reconciler-29 from=scheduler to=reconciler p=pay item=sup:northfield appr=NO
RW1 ST scheduler-14 re=reconciler-30 from=scheduler to=reconciler p=pay item=run:2026-09 n=2 tot=5778.60

--- message 15: scheduler to auditor ---
RW1 HO scheduler-15 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 rb=all art=file:work/payment_run.json n=9 // Final run from payable v2. PAY 2 (INV-000491 378.60, MD-2026-057 5400.00), total 5778.60 GBP, date 20261002. HOLD 1 (7731 USD 960.00, FX run 20261007, principal). 6 excluded. Bank details from master only. Approval refs human-02 to 04 come via reconciler-27 to 29: please verify.
RW1 ST scheduler-16 from=scheduler to=auditor p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // Pays to the details on file. Variance +15.50 net accepted, reason in the art.
RW1 ST scheduler-17 from=scheduler to=auditor p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 // Principal approved (AN human-02, relayed by reconciler-27). One payment for recs 6 and 9.
RW1 ST scheduler-18 from=scheduler to=auditor p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NA var=0.00 // Principal (AN human-03): FX run 20261007, HOLD on this run, not converted, not in tot.
RW1 ST scheduler-19 from=scheduler to=auditor p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00
RW1 ST scheduler-20 from=scheduler to=auditor p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA
RW1 ST scheduler-21 from=scheduler to=auditor p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // Nothing offset against MD-2026-057.
RW1 ST scheduler-22 from=scheduler to=auditor p=pay item=stmt:evergreen-20260924 sup=evergreen amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=STMT appr=NA
RW1 ST scheduler-23 from=scheduler to=auditor p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO // Principal rejected (AN human-04). Northfield pays to the details on file.
RW1 ST scheduler-24 from=scheduler to=auditor p=pay item=run:2026-09 n=2 tot=5778.60 // PAY lines: INV-000491, MD-2026-057. Marketing rec 12 is art-only.

--- message 16: scheduler to reconciler ---
RW1 DN scheduler-25 re=reconciler-13 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK art=file:work/payment_run.json next=AUDIT n=2 tot=5778.60 // Run built and handed to the auditor (HO scheduler-15). All relayed decisions applied. Nothing more needed from you unless the auditor sends it back.

--- message 17: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-15 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json p=pay h=62ae5ce5fee3 n=9
RW1 ST auditor-2 re=scheduler-16 from=auditor to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50
RW1 ST auditor-3 re=scheduler-17 from=auditor to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00
RW1 ST auditor-4 re=scheduler-18 from=auditor to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NA var=0.00
RW1 ST auditor-5 re=scheduler-19 from=auditor to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00
RW1 ST auditor-6 re=scheduler-20 from=auditor to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA
RW1 ST auditor-7 re=scheduler-21 from=auditor to=scheduler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA
RW1 ST auditor-8 re=scheduler-22 from=auditor to=scheduler p=pay item=stmt:evergreen-20260924 sup=evergreen amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=STMT appr=NA
RW1 ST auditor-9 re=scheduler-23 from=auditor to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO
RW1 ST auditor-10 re=scheduler-24 from=auditor to=scheduler p=pay item=run:2026-09 n=2 tot=5778.60

--- message 18: auditor to human ---
RW1 ST auditor-11 from=auditor to=human p=pay item=run:2026-09 n=2 tot=5778.60 // Audit PASS. Run ready: work/payment_run.json (checks: work/audit.json). PAY 2 = 5778.60 GBP on 20261002: INV-000491 378.60, MD-2026-057 5400.00 (your approval human-02). HOLD Kestrel 7731 USD 960.00 for your FX run 20261007. Northfield pays to details on file; your call-back is pending.

--- message 19: auditor to scheduler ---
RW1 DN auditor-12 re=scheduler-15 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json n=2 tot=5778.60 // Audit PASS, no defects. Nothing to send back. Principal has been told the run is ready.

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/R2/legibility_answers.json. Then reply DONE.