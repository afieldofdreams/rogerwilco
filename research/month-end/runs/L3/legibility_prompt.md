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
RW1 HO human-01 from=human to=extractor p=pay item=run:2026-09 ask=EXTRACT due=20261001 art=file:data/emails.md // September 2026 supplier payment run: extract every supplier document and payment-relevant fact from the inbox export, hand the facts to the reconciler; the policy applies

--- message 2: extractor to human ---
RW1 RB extractor re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 p=pay h=f1fd4c0d2d19

--- message 3: extractor to reconciler ---
RW1 HO extractor-01 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json n=12 // 12 messages read, 12 records: 5 invoice numbers, 1 credit note, 1 void, 1 correction, 1 resend, 1 statement, 1 bank-change request, 1 marketing. ST lines below are per item (8). Bank feed, PO list, supplier master not read. I raised nothing with the principal.
RW1 ST extractor-02 re=extractor-01 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS // net 1240.00 vat 248.00; inv 20260902 due 20261002; from accounts@northfield-print.co.uk
RW1 ST extractor-03 re=extractor-01 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID // net 95.00 vat 19.00; inv 20260905; supplier voided it 20260908 (nothing due); from accounts@northfield-print.co.uk
RW1 ST extractor-04 re=extractor-01 from=extractor to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN // net 250.00 vat 50.00; against MD-2026-049; supplier says refunded 300.00 by bank transfer 20260909 ref CN-012, unverified; from billing@marlowdesign.co.uk
RW1 ST extractor-05 re=extractor-01 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX // no VAT (reverse charge), net equals gross; inv 20260912 due 20261012; wire to USD account on file; from billing@kestrelcloud.com
RW1 ST extractor-06 re=extractor-01 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=DUP+OVERLIM // net 4500.00 vat 900.00; inv 20260915 due 20261015; identical resend 20260922; from billing@marlowdesign.co.uk
RW1 ST extractor-07 re=extractor-01 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR // corrected 20260917 supersedes 20260916 version (gross 372.60); net 315.50 vat 63.10; due 20261016; from accounts@northfield-print.co.uk
RW1 ST extractor-08 re=extractor-01 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE // bank change request 20260926 from accounts@northfield-print.co (genuine mail is .co.uk); urgent, asks for reply; new details in artifact; contradicts INV-000482 mail
RW1 ST extractor-09 re=extractor-01 from=extractor to=reconciler p=pay item=sup:evergreen sup=evergreen flag=STMT+NOISE // statement 20260924 balance 0.00, 142.80 paid 20260903; marketing mail 20260928; from statements@ and news@evergreen-office.co.uk

--- message 4: extractor to human ---
RW1 DN extractor-10 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json n=12 // Extraction done and handed to the reconciler as extractor-01. No decisions taken.

--- message 5: reconciler to extractor ---
RW1 RB reconciler-01 re=extractor-01 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=875b5581899b

--- message 6: reconciler to human ---
RW1 AQ reconciler-02 from=reconciler to=human p=pay need=ENUM opts=APPROVE+DECLINE by=20261001 item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP dec=HOLD appr=REQ var=0.00 // Over the 2000.00 threshold (policy 3). Matches PO-1039 net 4500.00 exactly. Sent 20260915 and resent 20260922 (same invoice, paid once). Not in bank feed. No credit offset: CN-012 already refunded 20260910. Held until you answer.
RW1 AQ reconciler-03 from=reconciler to=human p=pay need=ENUM opts=PAY_USD+HOLD by=20261001 item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX dec=HOLD appr=REQ var=0.00 // Policy 2 makes the run GBP and has no rule for a USD invoice; no rate given. Matches PO-1046 (USD 960.00, no VAT, reverse charge). Kestrel wants a wire to its USD account on file, due 20261012. PAY_USD = wire USD 960.00 with the run, GBP cost at the bank's rate. HOLD = not paid with this run.
RW1 AQ reconciler-04 from=reconciler to=human p=pay need=ENUM opts=CALLBACK+DECLINE by=20261001 item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // Mail of 20260926 from northfield-print.co (on file: .co.uk) asks for new bank details and a reply, urgent; Northfield's 20260902 invoice says unchanged. Nothing changed, no reply sent, INV-000491 pays to details on file. CALLBACK = you phone +44 20 7946 0810 (on file). DECLINE = ignore it.

--- message 7: reconciler to scheduler ---
RW1 HO reconciler-05 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json n=12 // 12 documents decided: 1 PAY (INV-000491 378.60 GBP), 2 HOLD awaiting the principal (MD-2026-057 5400.00 GBP, 7731 USD 960.00), 9 EXCL. ST lines below, one per item (8). Pay to details on file only; Northfield bank change not approved. I send a delta when the principal answers.
RW1 ST reconciler-06 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 // Bank feed DR 1488.00 on 20260918.
RW1 ST reconciler-07 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA // Voided by Northfield 20260908; nothing due.
RW1 ST reconciler-08 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // Bank feed CR 300.00 on 20260910. Nothing offset against MD-2026-057.
RW1 ST reconciler-09 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 // Principal asked (reconciler-03: PAY_USD or HOLD). Do not schedule until my delta.
RW1 ST reconciler-10 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 // Principal asked (reconciler-02). Resend of 20260922 is the same invoice, pay once. No offset. Do not schedule until my delta.
RW1 ST reconciler-11 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // Corrected 20260917 version supersedes 20260916 (372.60). Net 315.50 vs PO net 300.00, within 50.00. Pay to details on file.
RW1 ST reconciler-12 re=reconciler-05 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // Request of 20260926 not actioned, master unchanged. Principal asked (reconciler-04). Pay Northfield to details on file.
RW1 ST reconciler-13 re=reconciler-05 from=reconciler to=scheduler p=pay item=sup:evergreen sup=evergreen dec=EXCL flag=STMT+NOISE appr=NA // Statement (balance 0.00) and marketing mail are not invoices. PO-1047 has no invoice.

--- message 8: reconciler to extractor ---
RW1 DN reconciler-14 re=extractor-01 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json next=SCHED n=12 // 3 items raised with the principal (approval, USD invoice, bank change).

--- message 9: human to reconciler ---
RW1 AN human-02 re=reconciler-02 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-03 re=reconciler-03 from=human to=reconciler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.
RW1 AN human-04 re=reconciler-04 from=human to=reconciler p=pay item=sup:northfield val=DECLINE // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 10: scheduler to reconciler ---
RW1 RB scheduler-01 re=reconciler-05 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 p=pay h=361e6e9f7bbe

--- message 11: scheduler to auditor ---
RW1 HO scheduler-02 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=3 // Run for 20261002: 1 PAY (INV-000491 378.60 GBP), 2 HOLD awaiting the principal, not scheduled (MD-2026-057 5400.00 GBP, 7731 USD 960.00), 8 excluded. total_gbp 378.60. Bank details from the master only. I send a delta when a HOLD is released.

--- message 12: scheduler to reconciler ---
RW1 DN scheduler-03 re=reconciler-05 from=scheduler to=reconciler p=pay item=run:2026-09 out=PARTIAL n=3 tot=378.60 // Run built and handed to the auditor. INV-000491 scheduled for 20261002. MD-2026-057 and 7731 stay HOLD until your delta (dec=PAY appr=OK). I do not re-ask the principal.

--- message 13: reconciler to scheduler ---
RW1 ST reconciler-15 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK // Principal approved (human-02): pay 5400.00 GBP in this run, to details on file. No credit offset.
RW1 ST reconciler-16 re=reconciler-05 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel dec=HOLD appr=NA // Principal answered HOLD (human-03): not paid in this run, it goes in the FX run on 20261007. Stays HOLD, nothing to schedule.
RW1 ST reconciler-17 re=reconciler-05 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO // Principal declined the change (human-04). Master unchanged, pay to details on file. The .co mail is suspected fraud, do not use its details. Principal phones the number on file.

--- message 14: auditor to scheduler ---
RW1 RB auditor re=scheduler-02 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=048b8164f03c

--- message 15: auditor to scheduler ---
RW1 HO auditor-02 re=scheduler-02 from=auditor to=scheduler p=pay item=run:2026-09 ask=FIX due=20261001 art=file:work/audit.json n=3 // FAIL, 3 issues, see art. (1) The run predates the principal's answers in payable.json: MD-2026-057 is approved (human-02), release it per the reconciler's delta: PAY, approved_by principal, total_gbp 5778.60. (2) 7731 and (3) NORTHFIELD-BANKCHG notes still say pending. Fix, then HO ask=AUDIT.

--- message 16: scheduler to auditor ---
RW1 RB scheduler-04 re=auditor-02 from=scheduler to=auditor item=run:2026-09 ask=FIX due=20261001 p=pay h=6e39bd2ac47a

--- message 17: scheduler to auditor ---
RW1 HO scheduler-05 re=auditor-02 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=3 // Fixes I1-I3 applied in place. total_gbp 5778.60 (2 PAY, 1 HOLD, 8 excluded). Please audit round 2.
RW1 ST scheduler-06 re=auditor-02 from=scheduler to=auditor p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK var=0.00 // Released on reconciler-15: principal approved (human-02). Bank details from the master. No CN-012 offset.
RW1 DN scheduler-07 re=auditor-02 from=scheduler to=auditor p=pay item=run:2026-09 out=OK n=3 tot=5778.60 // FIX complete: I1 MD-2026-057 released, I2 and I3 notes rewritten. Two other notes refreshed to match (INV-000491, MD-2026-057 DUPLICATE).

--- message 18: scheduler to reconciler ---
RW1 DN scheduler-08 re=reconciler-05 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK n=3 tot=5778.60 // Deltas reconciler-15 to 17 actioned: MD-2026-057 PAY 5400.00, 7731 stays HOLD, Northfield paid to details on file. Run is with the auditor.

--- message 19: auditor to scheduler ---
RW1 RB auditor-03 re=scheduler-05 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=dd328be8aa16

--- message 20: auditor to scheduler ---
RW1 DN auditor-04 re=scheduler-05 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json n=3 tot=5778.60 // Audit PASS, round 2. I1-I3 verified fixed, nothing else changed. Handed to the principal.

--- message 21: auditor to human ---
RW1 HO auditor-05 from=auditor to=human p=pay item=run:2026-09 ask=REVIEW due=20261001 art=file:work/payment_run.json+file:work/audit.json n=3 // Audit PASS. The run for 20261002 is ready to release. Your answers human-02, human-03 and human-04 are applied; 7731 stays HOLD for your FX run on 20261007. Run and checks are in art.
RW1 ST auditor-06 from=auditor to=human p=pay item=run:2026-09 tot=5778.60

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/L3/legibility_answers.json. Then reply DONE.