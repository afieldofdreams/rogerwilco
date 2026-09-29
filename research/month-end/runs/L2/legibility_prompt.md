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

--- message 3: extractor to human ---
RW1 AQ extractor-01 re=human-01 from=extractor to=human p=pay need=ENUM opts=NOCHANGE+CALLBACK by=20261001 item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE // From accounts@northfield-print.co, not their usual .co.uk: asks us to pay a new account, urgent, wants a reply. Their 2 Sep mail said details unchanged. Policy 8: pay details on file until you approve after call-back. NOCHANGE=ignore it; CALLBACK=you phone the number on file. No reply sent.

--- message 4: extractor to reconciler ---
RW1 HO extractor-02 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json n=11 conf=H // 12 messages read, 11 records (8 items: 6 invoice/credit numbers, statement, bank-change request), 1 marketing email ignored. No dec set by me. Bank-change request already raised with human as extractor-01: do not re-raise. Checks for you are in the artifact (not_checked_by_extractor).
RW1 ST extractor-03 re=extractor-02 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS // net 1240.00 vat 248.00; invoice date 20260902, due 20261002; sender accounts@northfield-print.co.uk
RW1 ST extractor-04 re=extractor-02 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID // net 95.00 vat 19.00; invoiced 20260905; voided by supplier 20260908 as raised in error (delivery already in the PO-1041 price), says nothing is due
RW1 ST extractor-05 re=extractor-02 from=extractor to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN // credit note against MD-2026-049 (net 250.00 vat 50.00). Supplier says it refunded 300.00 by bank transfer 20260909 ref CN-012: not verified, check the bank feed
RW1 ST extractor-06 re=extractor-02 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX // no VAT (reverse charge) so net = gross; invoiced 20260912, due 20261012; asks for wire to USD account on file; no GBP equivalent given
RW1 ST extractor-07 re=extractor-02 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP // net 4500.00 vat 900.00, due 20261015; sent 20260915 and resent 20260922 with identical content
RW1 ST extractor-08 re=extractor-02 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR // corrected 20260917, supplier says it supersedes the 20260916 version (net 310.50 gross 372.60). Corrected net 315.50 vat 63.10, due 20261016
RW1 ST extractor-09 re=extractor-02 from=extractor to=reconciler p=pay item=sup:evergreen sup=evergreen flag=STMT // statement of account 20260924, balance outstanding 0.00, no invoice; mentions payment received 20260903 of 142.80 ref EO-55120. Not an invoice
RW1 ST extractor-10 re=extractor-02 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE // request from accounts@northfield-print.co (usual domain .co.uk) to pay a new account. Raised with human as extractor-01. Policy 8: details on file stay in use until approved

--- message 5: extractor to human ---
RW1 DN extractor-11 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json n=11 next=RECON // 12 messages read, 11 records handed to reconciler as extractor-02. Bank-change request from a lookalike domain raised with you as extractor-01. 1 marketing email ignored.

--- message 6: human to extractor ---
RW1 AN human-02 re=extractor-01 from=human to=extractor p=pay item=sup:northfield val=CALLBACK // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 7: reconciler to extractor ---
RW1 RB reconciler re=extractor-02 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=a32ded4d4786

--- message 8: reconciler to human ---
RW1 AQ reconciler-01 from=reconciler to=human p=pay need=ENUM opts=APPROVE+DECLINE by=20261001 item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP var=0.00 // Approve GBP 5400.00 to Marlow in the September run? Over 2000.00 (policy 3). PO-1039 net 4500.00 matches. Sent twice (15 and 22 Sep), paid once. Unpaid per bank feed. CN-012 300.00 already refunded 10 Sep, so no offset. Due 20261015. Pays to details on file.
RW1 AQ reconciler-02 from=reconciler to=human p=pay need=ENUM opts=PAYUSD+OUTSIDE by=20261001 item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX var=0.00 // Run is GBP (policy 2); policy does not cover a USD invoice. PO-1046 is USD 960.00, matches. Unpaid, due 20261012. Master has a USD wire account only, no GBP, and no rate is available. PAYUSD: wire USD 960.00 with the run. OUTSIDE: you pay it separately. No answer: held.

--- message 9: reconciler to scheduler ---
RW1 HO reconciler-03 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json n=8 conf=H // 1 PAY, 2 HOLD, 5 EXCL. MD-2026-057 and 7731 wait for the principal: asked as reconciler-01 and reconciler-02, do not re-ask. Pay every supplier to details on file (policy 8). Reasons, notes and totals in the artifact.
RW1 ST reconciler-04 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00
RW1 ST reconciler-05 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA
RW1 ST reconciler-06 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // refund is in the bank feed (20260910), so nothing is offset against MD-2026-057
RW1 ST reconciler-07 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 // USD, not GBP: keep out of the GBP total. Do not schedule until the principal answers reconciler-02
RW1 ST reconciler-08 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 // pay once (sent 20260915 and 20260922). Do not schedule until appr=OK (reconciler-01)
RW1 ST reconciler-09 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // corrected version only, not 372.60. Variance within 50.00, accepted, noted in artifact
RW1 ST reconciler-10 re=reconciler-03 from=reconciler to=scheduler p=pay item=sup:evergreen sup=evergreen dec=EXCL flag=STMT appr=NA // statement only. PO-1047 has no invoice, so nothing to pay
RW1 ST reconciler-11 re=reconciler-03 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=REQ // change NOT applied (policy 8). Pay to details on file. extractor-01 is with the principal, do not re-raise

--- message 10: reconciler to extractor ---
RW1 DN reconciler-12 re=extractor-02 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json n=8

--- message 11: extractor to reconciler ---
RW1 ST extractor-12 re=extractor-01 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield appr=NO // Principal answered extractor-01 (AN human-02, val=CALLBACK): REJECT, do not update the details, pay Northfield to the details on file. Principal phones the number on file; treat the .co email as suspected fraud. No supplier contact by agents. Closes the open escalation.

--- message 12: extractor to scheduler ---
RW1 ST extractor-13 re=extractor-01 from=extractor to=scheduler p=pay item=sup:northfield sup=northfield appr=NO // Principal answered extractor-01 (AN human-02, val=CALLBACK): REJECT, do not update the details, pay Northfield to the details on file. Principal phones the number on file; treat the .co email as suspected fraud. No supplier contact by agents. Closes the open escalation.

--- message 13: human to reconciler ---
RW1 AN human-03 re=reconciler-01 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-04 re=reconciler-02 from=human to=reconciler p=pay item=inv:7731 val=OUTSIDE // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 14: scheduler to reconciler ---
RW1 RB scheduler-01 re=reconciler-03 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 p=pay h=74d1f0ad503f

--- message 15: scheduler to reconciler ---
RW1 ST scheduler-02 re=reconciler-03 from=scheduler to=reconciler p=pay item=run:2026-09 blk=principal-answers eta=20261001 n=8 tot=378.60 // work/payment_run.json built: 1 PAY (INV-000491 378.60), 2 HOLD, 5 excluded. Waiting for your delta lines on MD-2026-057 (approval) and 7731 (PAYUSD or OUTSIDE). Not re-asking the principal. Auditor gets the run when both are settled.

--- message 16: reconciler to scheduler ---
RW1 ST reconciler-13 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK // principal approved (AN human-03): schedule 5400.00 GBP in this run. work/payable.json is updated for all three lines
RW1 ST reconciler-14 re=reconciler-03 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel dec=HOLD appr=NO // principal chose OUTSIDE (AN human-04): not paid in this run, goes in the FX run on 7 Oct. Stays HOLD, out of the GBP total. Nothing more to wait for
RW1 ST reconciler-15 re=reconciler-03 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield appr=NO // principal declined the bank change (extractor-12 relays AN human-02). Pay to details on file. No supplier contact by agents

--- message 17: scheduler to auditor ---
RW1 HO scheduler-03 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=8 conf=H // 2 PAY, 1 HOLD, 5 EXCL. All three principal questions are answered (human-02, -03, -04): none open, do not re-ask. 7731 is held for the FX run on 7 Oct by the principal's decision. Bank details from the supplier master only. Reasons and notes in the artifact; upstream in work/payable.json.

--- message 18: scheduler to reconciler ---
RW1 DN scheduler-04 re=reconciler-03 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK art=file:work/payment_run.json n=8 tot=5778.60 next=AUDIT // All three principal answers applied. Handed to the auditor as scheduler-03. Nothing further needed from you.

--- message 19: auditor to scheduler ---
RW1 RB auditor re=scheduler-03 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=9606fde07b96

--- message 20: auditor to scheduler ---
RW1 DN auditor-02 re=scheduler-03 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json n=8 // PASS. No defects, nothing to change or re-send. Run passed to the principal as ready.

--- message 21: auditor to human ---
RW1 DN auditor-03 re=scheduler-03 from=auditor to=human p=pay item=run:2026-09 out=OK art=file:work/payment_run.json+file:work/audit.json n=8 tot=5778.60 cur=GBP // Audit PASS: run 2026-09 is ready for payment on 2026-10-02. Pays 2 lines, GBP 5778.60: MD-2026-057 5400.00 (your approval, human-03) and INV-000491 378.60. 7731 stays HOLD for the 7 Oct FX run. Northfield bank change not applied; the call-back stays with you. Nothing needs your decision.

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/L2/legibility_answers.json. Then reply DONE.