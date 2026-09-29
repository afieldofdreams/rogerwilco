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
RW1 AQ extractor-01 re=human-01 from=extractor to=human p=pay need=ENUM opts=DECLINE+CALLBACK by=20261001 item=sup:northfield sup=northfield amt=1866.60 cur=GBP kind=GROSS flag=BANKCHG+LOOKALIKE // Email 26 Sep from accounts@northfield-print.co (all other Northfield mail is .co.uk) asks us to switch to sort 04-00-75 acct 88214561. Paying to details on file (policy 8), no reply sent. CALLBACK = you phone the number on file. amt = Northfield invoices extracted, before bank-feed check.

--- message 4: extractor to reconciler ---
RW1 HO extractor-02 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json n=12 // 12 messages, 12 records, 6 invoice/credit numbers. Yours, not escalated by me: 7731 USD (policy silent), MD-2026-057 approval. Bank-detail change is with human; Northfield is paid to details on file (policy 8).
RW1 ST extractor-03 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS
RW1 ST extractor-04 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID // supplier voided it 20260908, raised in error; nothing due
RW1 ST extractor-05 from=extractor to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN // credit against MD-2026-049; supplier says refunded 300.00 by bank transfer 20260909 ref CN-012; bank feed unchecked by me
RW1 ST extractor-06 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX // no VAT (reverse charge); due 20261012; run is GBP, policy silent on USD
RW1 ST extractor-07 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=DUP+OVERLIM appr=REQ // same invoice sent 20260915 and 20260922; count once
RW1 ST extractor-08 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR // corrected 20260917, supersedes 372.60 gross of 20260916; net now 315.50
RW1 ST extractor-09 from=extractor to=reconciler p=pay item=sup:evergreen sup=evergreen flag=STMT // statement 20260924, balance 0.00, nothing due; catalogue mail of 20260928 is NOISE
RW1 ST extractor-10 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // 20260926 email from accounts@northfield-print.co (real mail is .co.uk); with human as extractor-01; pay details on file, do not re-escalate

--- message 5: extractor to human ---
RW1 DN extractor-11 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json next=RECON n=12 // extraction complete; one escalation sent (extractor-01); rest handed to reconciler

--- message 6: human to extractor ---
RW1 AN human-02 re=extractor-01 from=human to=extractor p=pay item=sup:northfield val=DECLINE // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 7: reconciler to extractor ---
RW1 RB reconciler re=extractor-02 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=77e8b5381e01

--- message 8: reconciler to human ---
RW1 AQ reconciler-02 from=reconciler to=human p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ var=0.00 need=ENUM opts=APPROVE+DECLINE by=20261001 // Brand refresh phase 2. Net 4500.00 matches PO-1039, no variance. Sent twice, counted once. CN-012 300.00 already refunded (bank feed 20260910), so no offset: full 5400.00 payable 20261002 if approved.
RW1 AQ reconciler-03 from=reconciler to=human p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX appr=REQ var=0.00 need=ENUM opts=PAYFX+OFFRUN by=20261001 // Kestrel bills USD 960.00, no VAT (reverse charge), due 20261012, matches PO-1046. Policy 2 sets a GBP run and is silent on USD; no FX rate on hand. Below GBP 2000 at any plausible rate. PAYFX: USD wire to account on file in this run, bank converts. OFFRUN: leave out, you pay it separately.

--- message 9: reconciler to scheduler ---
RW1 HO reconciler-04 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json n=8 // Pay now: INV-000491 378.60 GBP only. Held: MD-2026-057 5400.00 (approval asked) and 7731 USD 960.00 (policy silent, asked). Five excluded; EXCL lines show the document amount, nothing is paid. Pay Northfield to details on file: bank-change email is a lookalike, not actioned.
RW1 ST reconciler-05 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // Corrected version stands (372.60 superseded). Net 315.50 vs PO 300.00: 15.50 over, within 50.00, accepted. Unpaid per bank feed.
RW1 ST reconciler-06 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=DUP+OVERLIM appr=REQ var=0.00 // Approval asked of human (reconciler-02). Counted once. CN-012 refunded, no offset. Do not schedule until appr=OK.
RW1 ST reconciler-07 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 // Policy silent on USD in a GBP run; asked of human (reconciler-03). No FX rate applied. Not for a GBP total. Do not schedule until answered.
RW1 ST reconciler-08 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 // Paid 20260918, bank feed DR 1488.00 ref INV-000482.
RW1 ST reconciler-09 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA // Voided by supplier 20260908, nothing due.
RW1 ST reconciler-10 from=reconciler to=scheduler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // Refunded 20260910, bank feed CR 300.00 ref CN-012 REFUND. Nothing offset.
RW1 ST reconciler-11 from=reconciler to=scheduler p=pay item=sup:evergreen sup=evergreen dec=EXCL flag=STMT+NOISE appr=NA // Statement balance 0.00, 142.80 paid 20260903 per bank feed. Catalogue mail is noise. Nothing due.
RW1 ST reconciler-12 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // Lookalike email, not actioned; with human as extractor-01. Master not edited. Pay Northfield to details on file only. No dec: not a payable, and it does not exclude INV-000491.

--- message 10: reconciler to extractor ---
RW1 DN reconciler-13 re=extractor-02 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json next=SCHED n=8 tot=378.60 // 1 pay, 2 held for human (MD-2026-057 approval, 7731 USD), 5 excluded. Your extractor-01 figure 1866.60 counted INV-000482, already paid 20260918: Northfield payable is 378.60 only. Send me the answer to extractor-01: I own the supplier master.

--- message 11: extractor to reconciler ---
RW1 AN extractor-12 re=reconciler-13 from=extractor to=reconciler p=pay item=sup:northfield val=DECLINE sup=northfield flag=BANKCHG+LOOKALIKE appr=NO // human-02 answers extractor-01: REJECT. Do not update the details. Pay Northfield to the details on file. Principal will call the number on file; treat the .co email as suspected fraud.

--- message 12: human to reconciler ---
RW1 AN human-03 re=reconciler-02 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-04 re=reconciler-03 from=human to=reconciler p=pay item=inv:7731 val=OFFRUN // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 13: scheduler to reconciler ---
RW1 RB scheduler-01 re=reconciler-04 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 p=pay h=baa3ef803058

--- message 14: reconciler to scheduler ---
RW1 ST reconciler-14 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=DUP+OVERLIM appr=OK var=0.00 // Approved by the principal (human-03). Schedule 5400.00 GBP for 20261002.
RW1 ST reconciler-15 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NA var=0.00 // Principal decided (human-04): not paid in this run, goes in the FX run on 7 October. Keep as HOLD, not EXCL. Not for a GBP total. NA: nothing awaits approval.
RW1 ST reconciler-16 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO // Bank-detail change declined by the principal (human-02, via extractor-12). Master not edited. Pay Northfield to the details on file.
RW1 ST reconciler-17 from=reconciler to=scheduler p=pay item=run:2026-09 cur=GBP n=2 tot=5778.60 // PAY lines: INV-000491 378.60 + MD-2026-057 5400.00. 7731 (USD, HOLD) is not in the total. payable.json is updated to match (revision 2). Nothing is open with the principal.

--- message 15: scheduler to auditor ---
RW1 HO scheduler-02 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=8 // Run complete: 2 PAY, 1 HOLD, 5 excluded. MD-2026-057 approved by the principal (human-03). 7731 USD HOLD per human-04, FX run 7 Oct, outside total_gbp. Northfield bank change declined (human-02), paid to details on file. Built from work/payable.json rev 2.
RW1 ST scheduler-03 from=scheduler to=auditor p=pay item=run:2026-09 cur=GBP n=2 tot=5778.60 // PAY lines: INV-000491 378.60 + MD-2026-057 5400.00. 7731 (USD, HOLD) is not in the total. Payment date 20261002.
RW1 ST scheduler-04 from=scheduler to=auditor p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // Corrected version stands, 372.60 superseded. Variance within 50.00, accepted. Bank details as on file.
RW1 ST scheduler-05 from=scheduler to=auditor p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=DUP+OVERLIM appr=OK var=0.00 // Approved by the principal (human-03). Duplicate counted once. CN-012 already refunded, nothing offset.
RW1 ST scheduler-06 from=scheduler to=auditor p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NA var=0.00 // Principal decided (human-04): not paid in this run, FX run on 7 October. Not in the GBP total.

--- message 16: scheduler to reconciler ---
RW1 DN scheduler-07 from=scheduler to=reconciler p=pay re=reconciler-04 item=run:2026-09 out=OK art=file:work/payment_run.json next=AUDIT cur=GBP tot=5778.60 // Run built from payable.json rev 2 and handed to the auditor (scheduler-02). 2 PAY, 1 HOLD, 5 excluded.

--- message 17: auditor to scheduler ---
RW1 RB auditor re=scheduler-02 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=6afd8b366dc9

--- message 18: auditor to human ---
RW1 HO auditor-02 from=auditor to=human p=pay item=run:2026-09 ask=REVIEW due=20261001 art=file:work/payment_run.json+file:work/audit.json n=8 // Audit PASS, no defects. Run ready for payment on 2 Oct: 2 PAY 5778.60 GBP, 7731 USD 960.00 HOLD for the FX run on 7 Oct, 5 excluded. Nothing open for you.
RW1 ST auditor-03 from=auditor to=human p=pay item=run:2026-09 cur=GBP n=2 tot=5778.60 // INV-000491 378.60 + MD-2026-057 5400.00, both to the details on file.

--- message 19: auditor to scheduler ---
RW1 DN auditor-04 re=scheduler-02 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json n=8 // Audit PASS, no defects. Run handed to the principal.

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/L1/legibility_answers.json. Then reply DONE.