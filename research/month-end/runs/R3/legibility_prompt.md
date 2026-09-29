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
RW1 RB extractor-01 re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 art=file:data/emails.md p=pay h=57499640b2f1

--- message 3: extractor to reconciler ---
RW1 HO extractor-02 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 rb=all art=file:work/invoices.json n=12 // 12 emails, 12 records: 5 invoices, void, correction, resend, credit note, statement, bank-change request, marketing. by_number gives latest versions. I raised the bank change to human (extractor-12). Approval for MD-2026-057 and the USD invoice 7731 are left to you and the scheduler.
RW1 ST extractor-03 re=extractor-02 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS // net 1240.00 VAT 248.00, due 20261002; supplier says bank details unchanged
RW1 ST extractor-04 re=extractor-02 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID // voided by supplier 20260908, nothing due (raised in error, delivery already in PO-1041 price); amount shown is as first invoiced
RW1 ST extractor-05 re=extractor-02 from=extractor to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN // credit vs MD-2026-049 (net 250.00 VAT 50.00); supplier says it refunded 300.00 by bank transfer 20260909 ref CN-012; unverified, check bank feed
RW1 ST extractor-06 re=extractor-02 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX // USD 960.00, no VAT (reverse charge) so net equals gross, due 20261012; supplier says wire to the USD account on file
RW1 ST extractor-07 re=extractor-02 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ // net 4500.00 VAT 900.00, due 20261015; sent 20260915 and again 20260922, identical (one invoice number)
RW1 ST extractor-08 re=extractor-02 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR // corrected 20260917, supersedes 20260916 version (net 310.50 gross 372.60); now net 315.50 VAT 63.10, due 20261016
RW1 ST extractor-09 re=extractor-02 from=extractor to=reconciler p=pay item=stmt:evergreen sup=evergreen flag=STMT // statement 20260924, customer 20917: balance outstanding 0.00, payment of 142.80 received 20260903 (EO-55120); not an invoice, nothing payable
RW1 ST extractor-10 re=extractor-02 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // request from accounts@northfield-print.co (5 earlier Northfield mails were .co.uk); new acct 04-00-75 88214561 not actioned, pay details on file; raised to human as extractor-12

--- message 4: extractor to human ---
RW1 DN extractor-11 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json n=12 next=RECON
RW1 AQ extractor-12 from=extractor to=human p=pay item=sup:northfield sup=northfield need=ENUM opts=KEEP+CALLBACK by=20261001 flag=BANKCHG+LOOKALIKE appr=REQ // Email from accounts@northfield-print.co (earlier Northfield mail: .co.uk) asks to move payments to sort 04-00-75 acct 88214561; urgent, wants a reply. Not actioned, details on file used. KEEP=ignore it. CALLBACK=you phone the number on file.

--- message 5: human to extractor ---
RW1 AN human-02 re=extractor-12 from=human to=extractor p=pay item=sup:northfield val=KEEP // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 6: reconciler to extractor ---
RW1 RB reconciler-01 re=extractor-02 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json p=pay h=91d4e81f3058 n=12
RW1 ST reconciler-02 re=extractor-03 from=reconciler to=extractor p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS
RW1 ST reconciler-03 re=extractor-04 from=reconciler to=extractor p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID
RW1 ST reconciler-04 re=extractor-05 from=reconciler to=extractor p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN
RW1 ST reconciler-05 re=extractor-06 from=reconciler to=extractor p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX
RW1 ST reconciler-06 re=extractor-07 from=reconciler to=extractor p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ
RW1 ST reconciler-07 re=extractor-08 from=reconciler to=extractor p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR
RW1 ST reconciler-08 re=extractor-09 from=reconciler to=extractor p=pay item=stmt:evergreen sup=evergreen flag=STMT
RW1 ST reconciler-09 re=extractor-10 from=reconciler to=extractor p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ

--- message 7: reconciler to human ---
RW1 AQ reconciler-10 from=reconciler to=human p=pay need=ENUM opts=APPROVE+DECLINE by=20261001 item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ var=0.00 // Approve paying Marlow 5400.00 (above the 2000.00 threshold)? Matches PO-1039 net 4500.00 exactly. Sent twice, paid once. CN-012 300.00 already refunded 20260910, so no offset. Supplier says phase 2 is signed off. Details on file.
RW1 AQ reconciler-11 from=reconciler to=human p=pay need=ENUM opts=PAY-USD+HOLD by=20261001 item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX appr=REQ var=0.00 // Run is GBP (policy 2), a USD invoice is not covered. PAY-USD: wire USD 960.00 to the USD account on file, bank converts at its rate. HOLD: leave it out of this run. Equals PO-1046, no VAT (reverse charge), far under 2000.00.

--- message 8: reconciler to scheduler ---
RW1 HO reconciler-12 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 rb=all art=file:work/payable.json n=9 // amt on each line = what this run pays (0.00 if excluded). Only INV-000491 is PAY now. MD-2026-057 and 7731 are HOLD until the principal answers reconciler-10 and reconciler-11: do not re-ask. Pay to details on file only. Bank change is with the principal (extractor-12).
RW1 ST reconciler-13 re=reconciler-12 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 // debit 1488.00 on 20260918 ref INV-000482 in the bank feed equals the invoice gross
RW1 ST reconciler-14 re=reconciler-12 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA // voided by supplier 20260908, nothing due (114.00 as first invoiced)
RW1 ST reconciler-15 re=reconciler-12 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // pay the corrected version only, not 372.60. Net 315.50 v PO net 300.00, inside the 50.00 tolerance, recorded. Pay to details on file
RW1 ST reconciler-16 re=reconciler-12 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 // do not schedule until the principal approves (reconciler-10). Paid once, no credit offset (CN-012 refunded)
RW1 ST reconciler-17 re=reconciler-12 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 // do not schedule until the principal answers reconciler-11. Run is GBP. No rate assumed, not in the GBP total
RW1 ST reconciler-18 re=reconciler-12 from=reconciler to=scheduler p=pay item=inv:CN-012 sup=marlow amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // credit 300.00 already refunded: bank feed credit 300.00 on 20260910 ref CN-012. Nothing to offset
RW1 ST reconciler-19 re=reconciler-12 from=reconciler to=scheduler p=pay item=stmt:evergreen sup=evergreen dec=EXCL flag=STMT appr=NA // statement, balance 0.00, not an invoice. Nothing payable
RW1 ST reconciler-20 re=reconciler-12 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=REQ // dec covers the request only, not Northfield: INV-000491 stays PAY. Not actioned. Lookalike confirmed against the master. Pay to details on file. With the principal as extractor-12
RW1 ST reconciler-21 re=reconciler-12 from=reconciler to=scheduler p=pay item=mail:M12 sup=evergreen dec=EXCL flag=NOISE appr=NA // marketing email, not a supplier document

--- message 9: reconciler to extractor ---
RW1 DN reconciler-22 re=extractor-02 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json next=SCHED n=9 tot=378.60 // 12 records in 9 items: 1 PAY, 2 HOLD for the principal, 6 EXCL. Send me any answer to extractor-12 and any supplier-master question.

--- message 10: extractor to human ---
RW1 AN extractor-13 re=human-02 from=extractor to=human p=pay item=sup:northfield val=KEEP // read back: KEEP = change rejected, Northfield paid to the details on file, you phone the number on file, .co email treated as suspected fraud. (AN used as the echo: ST has no val slot)

--- message 11: extractor to reconciler ---
RW1 ST extractor-14 re=extractor-10 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO // principal answered KEEP (human-02): change rejected, pay Northfield to the details on file, principal will phone the number on file, .co email is suspected fraud

--- message 12: human to reconciler ---
RW1 AN human-03 re=reconciler-10 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-04 re=reconciler-11 from=human to=reconciler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 13: scheduler to reconciler ---
RW1 RB scheduler-01 re=reconciler-12 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json p=pay h=06ec0b06aec3 n=9
RW1 ST scheduler-02 re=reconciler-13 from=scheduler to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00
RW1 ST scheduler-03 re=reconciler-14 from=scheduler to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA
RW1 ST scheduler-04 re=reconciler-15 from=scheduler to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50
RW1 ST scheduler-05 re=reconciler-16 from=scheduler to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00
RW1 ST scheduler-06 re=reconciler-17 from=scheduler to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00
RW1 ST scheduler-07 re=reconciler-18 from=scheduler to=reconciler p=pay item=inv:CN-012 sup=marlow amt=0.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA
RW1 ST scheduler-08 re=reconciler-19 from=scheduler to=reconciler p=pay item=stmt:evergreen sup=evergreen dec=EXCL flag=STMT appr=NA
RW1 ST scheduler-09 re=reconciler-20 from=scheduler to=reconciler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=REQ
RW1 ST scheduler-10 re=reconciler-21 from=scheduler to=reconciler p=pay item=mail:M12 sup=evergreen dec=EXCL flag=NOISE appr=NA

--- message 14: scheduler to auditor ---
RW1 HO scheduler-11 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 rb=all art=file:work/payment_run.json n=9 amt=378.60 cur=GBP kind=GROSS // Built from reconciler-12: 1 PAY (INV-000491), 2 HOLD, 6 excluded. HOLD lines wait for the principal (reconciler-10, reconciler-11), not re-asked. Northfield bank change not actioned, master untouched. All lines use details on file. Per-line notes are in the artifact.

--- message 15: scheduler to reconciler ---
RW1 DN scheduler-12 re=reconciler-12 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK art=file:work/payment_run.json next=AUDIT n=9 tot=378.60 // Run built and handed to the auditor: 1 PAY, 2 HOLD, 6 excluded. To flip MD-2026-057 or 7731, send me the principal's answer to reconciler-10 or reconciler-11 as a delta ST (dec, appr).

--- message 16: reconciler to extractor ---
RW1 ST reconciler-23 re=extractor-14 from=reconciler to=extractor p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO

--- message 17: reconciler to human ---
RW1 AN reconciler-24 re=human-03 from=reconciler to=human p=pay item=inv:MD-2026-057 val=APPROVE // read back as AN, ST has no val slot
RW1 AN reconciler-25 re=human-04 from=reconciler to=human p=pay item=inv:7731 val=HOLD // read back as AN, ST has no val slot

--- message 18: reconciler to scheduler ---
RW1 ST reconciler-26 re=scheduler-12 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 // principal approved in human-03. Pay once at 5400.00, no credit offset. GBP PAY total is now 5778.60. Pay to details on file
RW1 ST reconciler-27 re=scheduler-12 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NO var=0.00 // principal chose HOLD in human-04: not paid in this run, goes in the FX run on 20261007. Keep on the run as HOLD, not in the GBP total
RW1 ST reconciler-28 re=scheduler-12 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO // principal answered KEEP (human-02 via extractor-14): change rejected. Pay Northfield to the details on file. dec covers the request only, INV-000491 stays PAY

--- message 19: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-11 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json p=pay h=f975cbd950c2 amt=378.60 cur=GBP kind=GROSS n=9

--- message 20: auditor to scheduler ---
RW1 HO auditor-2 re=scheduler-11 from=auditor to=scheduler p=pay item=run:2026-09 ask=FIX due=20261001 rb=all art=file:work/audit.json amt=5778.60 cur=GBP kind=GROSS n=9 // Audit FAIL: 2 blocking, 1 minor, see art. The principal has already answered all three open points (payable.json rev 2, deltas reconciler-26 to -28). Apply them, refresh the notes, expected total 5778.60, then re-send AUDIT.

--- message 21: scheduler to auditor ---
RW1 RB scheduler-13 re=auditor-2 from=scheduler to=auditor item=run:2026-09 ask=FIX due=20261001 art=file:work/audit.json p=pay h=62b175353b7a amt=5778.60 cur=GBP kind=GROSS n=9

--- message 22: scheduler to reconciler ---
RW1 ST scheduler-14 re=reconciler-26 from=scheduler to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00
RW1 ST scheduler-15 re=reconciler-27 from=scheduler to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NO var=0.00
RW1 ST scheduler-16 re=reconciler-28 from=scheduler to=reconciler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO

--- message 23: scheduler to auditor ---
RW1 DN scheduler-17 re=auditor-2 from=scheduler to=auditor p=pay item=run:2026-09 out=OK art=file:work/payment_run.json next=AUDIT n=9 tot=5778.60 // I1 to I3 applied. My earlier 7731 note saying move to excluded was wrong (a held invoice stays in lines) and is removed. Deltas reconciler-26 to -28 echoed before I acted. Re-sent as AUDIT.
RW1 HO scheduler-18 re=auditor-2 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 rb=all art=file:work/payment_run.json n=9 amt=5778.60 cur=GBP kind=GROSS // Fixes applied. 2 PAY: INV-000491 378.60, MD-2026-057 5400.00 (approved human-03). 1 HOLD: 7731 USD 960.00, FX run 20261007 (human-04). 6 excluded. Northfield change rejected (human-02). Details on file throughout.

--- message 24: auditor to scheduler ---
RW1 RB auditor-3 re=scheduler-18 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json p=pay h=6992c6f24002 amt=5778.60 cur=GBP kind=GROSS n=9

--- message 25: auditor to human ---
RW1 HO auditor-4 from=auditor to=human p=pay item=run:2026-09 ask=REVIEW due=20261001 rb=all art=file:work/payment_run.json+file:work/audit.json n=9 amt=5778.60 cur=GBP kind=GROSS // Audit PASS. Run ready for payment 20261002: 2 PAY (INV-000491 378.60, MD-2026-057 5400.00 on your approval human-03), 1 HOLD (7731 USD 960.00, FX run 20261007, human-04), 6 excluded. No decision needed from you.

--- message 26: auditor to scheduler ---
RW1 DN auditor-5 re=scheduler-18 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json next=REVIEW n=9 tot=5778.60 // Audit PASS. I1 to I3 verified fixed. Run handed to the principal in auditor-4.

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/R3/legibility_answers.json. Then reply DONE.