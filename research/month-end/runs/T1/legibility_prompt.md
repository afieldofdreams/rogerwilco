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
RW1 RB extractor-1 re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 p=pay h=3f0e7f52edfb

--- message 3: extractor to reconciler ---
RW1 ST extractor-2 from=extractor to=reconciler item=inv:INV-000482 p=pay sup=northfield po=PO-1041 net=1240.00 vat=248.00 amt=1488.00 cur=GBP kind=GROSS src=email:1 // From accounts@northfield-print.co.uk, dated 20260902, due 20261002. Autumn brochure print run, 500 copies. States bank details unchanged.
RW1 ST extractor-3 from=extractor to=reconciler item=inv:INV-000488 p=pay sup=northfield po=PO-1041 net=95.00 vat=19.00 amt=114.00 cur=GBP kind=GROSS src=email:2 // From accounts@northfield-print.co.uk, dated 20260905, due 20261005. Courier delivery of the brochure run.
RW1 ST extractor-4 from=extractor to=reconciler item=inv:INV-000488 p=pay sup=northfield po=PO-1041 flag=VOID src=email:3 // From accounts@northfield-print.co.uk, dated 20260908. Supplier voided INV-000488 (raised in error, delivery already in the PO-1041 price): nothing due, disregard. Amounts as in email 2.
RW1 ST extractor-5 from=extractor to=reconciler item=sup:marlow p=pay sup=marlow net=250.00 vat=50.00 amt=300.00 cur=GBP kind=GROSS flag=CN src=email:4 // From billing@marlowdesign.co.uk, dated 20260909. Credit note CN-012 against MD-2026-049 (paid 20260828), 5 hours overbilled. Supplier says it refunded 300.00 by bank transfer 20260909, ref CN-012. Claim unverified; check bank feed.
RW1 ST extractor-6 from=extractor to=reconciler item=inv:7731 p=pay sup=kestrel po=PO-1046 net=960.00 vat=0.00 amt=960.00 cur=USD kind=GROSS flag=FX src=email:5 // From billing@kestrelcloud.com, dated 20260912, due 20261012. Cloud hosting Team-M, 1-30 Sep 2026. No VAT charged (reverse charge, customer accounts for it). Says pay by wire to the USD account on file.
RW1 ST extractor-7 from=extractor to=reconciler item=inv:MD-2026-057 p=pay sup=marlow po=PO-1039 net=4500.00 vat=900.00 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM src=email:6 // From billing@marlowdesign.co.uk, dated 20260915, due 20261015. Brand refresh phase 2 (guidelines, templates, asset library).
RW1 ST extractor-8 from=extractor to=reconciler item=inv:INV-000491 p=pay sup=northfield po=PO-1044 net=310.50 vat=62.10 amt=372.60 cur=GBP kind=GROSS src=email:7 // From accounts@northfield-print.co.uk, dated 20260916, due 20261016. Business cards 10 boxes 150.00, letterheads 2000 sheets 160.50. Superseded by the corrected version in email 8.
RW1 ST extractor-9 from=extractor to=reconciler item=inv:INV-000491 p=pay sup=northfield po=PO-1044 net=315.50 vat=63.10 amt=378.60 cur=GBP kind=GROSS flag=CORR src=email:8 // From accounts@northfield-print.co.uk, dated 20260917, due 20261016 unchanged. Same invoice number, supersedes email 7 (net 310.50, gross 372.60). Letterheads 2000 sheets now 165.50 (82.75 per thousand), cards 150.00.
RW1 ST extractor-10 from=extractor to=reconciler item=inv:MD-2026-057 p=pay sup=marlow po=PO-1039 net=4500.00 vat=900.00 amt=5400.00 cur=GBP kind=GROSS flag=DUP+OVERLIM src=email:9 // From billing@marlowdesign.co.uk, dated 20260922. Resend of email 6 (supplier says its mail server had a wobble on the 15th). Same invoice, nothing changed.
RW1 ST extractor-11 from=extractor to=reconciler item=sup:evergreen p=pay sup=evergreen flag=STMT src=email:10 // From statements@evergreen-office.co.uk, dated 20260924. Statement of account, customer 20917: opening balance GBP 142.80 on 20260901, payment received 20260903 of 142.80 (ref EO-55120), balance 0.00 at 20260924. Not an invoice, no action asked.
RW1 ST extractor-12 from=extractor to=reconciler item=sup:northfield p=pay sup=northfield flag=BANKCHG+LOOKALIKE src=email:11 // From Northfield Print Accounts accounts@northfield-print.co (emails 1,2,3,7,8 use @northfield-print.co.uk; master not checked by me). Dated 20260926, urgent, signed D. Kaur. Asks payments go to name Northfield Print Ltd, sort 04-00-75, acct 88214561, and a reply to confirm. UNVERIFIED, not approved.
RW1 ST extractor-13 from=extractor to=reconciler item=sup:evergreen p=pay sup=evergreen flag=NOISE src=email:12 // From news@evergreen-office.co.uk, dated 20260928. Marketing email: autumn catalogue, 15% off until 20261031. Not a supplier document.
RW1 HO extractor-14 from=extractor to=reconciler item=run:2026-09 p=pay ask=RECON due=20261001 n=12 conf=H // 12 ST lines extractor-2 to extractor-13, one per email (8 distinct items). I set no dec and raised nothing with the principal. Not checked by me: PO list, bank feed, master. Flagged for your policy check: MD-2026-057 over limit, 7731 in USD, email 11 bank-detail request.

--- message 5: extractor to human ---
RW1 DN extractor-16 re=human-01 from=extractor to=human item=run:2026-09 p=pay out=OK next=RECON n=12 // Replaces extractor-15 (its next= wrongly held an agent name, not an ask code). Work unchanged: 12 ST lines and HO extractor-14 are with the reconciler.

--- message 6: reconciler to extractor ---
RW1 RB reconciler-1 re=extractor-14 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=5abd608d0274

--- message 7: reconciler to human ---
RW1 AQ reconciler-2 from=reconciler to=human p=pay need=ENUM opts=REJECT+CALLBACK by=20261001 item=sup:northfield sup=northfield amt=378.60 cur=GBP kind=GROSS flag=BANKCHG+LOOKALIKE // Email 11 (20260926, urgent, D. Kaur) from accounts@northfield-print.co, not master domain northfield-print.co.uk. Asks pay to 04-00-75 / 88214561; master has 20-45-67 / 31776234. Unverified, no reply sent. Phone on file +44 20 7946 0810. I recommend REJECT. INV-000491 pays to master details.
RW1 AQ reconciler-3 from=reconciler to=human p=pay need=ENUM opts=APPROVE+DECLINE+HOLD by=20261001 item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP // Brand refresh phase 2. Matches PO-1039 (net 4500.00, var 0.00), unpaid. Above the 2000.00 limit, so needs your approval. Sent twice (emails 6, 9), paid once. CN-012 300.00 already refunded, so no credit offset. Due 20261015.
RW1 AQ reconciler-4 from=reconciler to=human p=pay need=ENUM opts=APPROVE+HOLD+DECLINE by=20261001 item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX // Hosting Sep 2026, matches PO-1046 (USD 960.00, no VAT, reverse charge). Run is GBP (policy 2) and policy has no rule for USD. Sender matches master. APPROVE = pay by USD wire to details on file in this run; HOLD = pay outside this run; DECLINE = do not pay.

--- message 8: reconciler to scheduler ---
RW1 ST reconciler-5 from=reconciler to=scheduler item=inv:INV-000482 p=pay sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 src=email:1+bank:20260918+po:PO-1041 // Paid 20260918 per bank feed (DR 1488.00, ref INV-000482). Excluded.
RW1 ST reconciler-6 from=reconciler to=scheduler item=inv:INV-000488 p=pay sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA src=email:2+email:3+po:PO-1041 // Voided by supplier 20260908 (email 3): raised in error, courier already in PO-1041 price. Nothing due. Excluded.
RW1 ST reconciler-7 from=reconciler to=scheduler item=sup:marlow p=pay sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA src=email:4+bank:20260910 // Credit note CN-012 (against MD-2026-049) already refunded: bank CR 300.00 ref CN-012 on 20260910. Nothing offset against MD-2026-057.
RW1 ST reconciler-8 from=reconciler to=scheduler item=inv:7731 p=pay sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 src=email:5+po:PO-1046 // USD invoice, run is GBP, policy silent on FX. Held; principal asked (AQ reconciler-4). Matches PO-1046, no variance. Sender domain matches master; email asks for the USD account on file.
RW1 ST reconciler-9 from=reconciler to=scheduler item=inv:MD-2026-057 p=pay sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 src=email:6+email:9+po:PO-1039 // Over 2000.00: held for approval (AQ reconciler-3). Email 9 is a resend of email 6, so one payment only. Matches PO-1039, no variance. No credit offset (CN-012 refunded 20260910).
RW1 ST reconciler-10 from=reconciler to=scheduler item=inv:INV-000491 p=pay sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 src=email:8+email:7+po:PO-1044 // Email 8 supersedes email 7 (372.60). Net 315.50 vs PO-1044 300.00: +15.50, within 50.00 tolerance, accepted. Reason: letterheads 165.50 (82.75 per thousand) vs 150.00 left in PO after cards 150.00. Pay to master details.
RW1 ST reconciler-11 from=reconciler to=scheduler item=sup:evergreen p=pay sup=evergreen dec=EXCL flag=STMT+NOISE appr=NA src=email:10+email:12+bank:20260903 // Email 10 is a statement, not an invoice: its 142.80 (EO-55120) matches bank DR 20260903, balance 0.00. Email 12 is marketing. PO-1047 (net 180.00) has no invoice yet.
RW1 ST reconciler-12 from=reconciler to=scheduler item=sup:northfield p=pay sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=REQ src=email:11 // Request only, not a payment. Not actioned: sender domain northfield-print.co is not master's northfield-print.co.uk. Principal asked (AQ reconciler-2). Master details stay in force; INV-000491 unaffected.
RW1 HO reconciler-13 from=reconciler to=scheduler item=run:2026-09 p=pay ask=SCHED due=20261001 n=8 conf=H // 8 ST lines reconciler-5 to reconciler-12, one per item. PAY now: INV-000491 only (378.60 GBP total). HOLD pending principal (AQs open): MD-2026-057 approval, 7731 USD FX. Rest EXCL. Pay to master bank details; ignore email 11.

--- message 9: reconciler to extractor ---
RW1 DN reconciler-14 re=extractor-14 from=reconciler to=extractor item=run:2026-09 p=pay out=OK next=SCHED // All 12 documents (8 items) reconciled and handed to scheduler. Three questions open with the principal: Northfield bank change, MD-2026-057 approval, 7731 USD invoice.

--- message 10: human to reconciler ---
RW1 AN human-02 re=reconciler-2 from=human to=reconciler p=pay item=sup:northfield val=REJECT // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.
RW1 AN human-03 re=reconciler-3 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.
RW1 AN human-04 re=reconciler-4 from=human to=reconciler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 11: scheduler to reconciler ---
RW1 RB scheduler-1 re=reconciler-13 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 p=pay h=00ebe31d19c7

--- message 12: scheduler to auditor ---
RW1 ST scheduler-2 from=scheduler to=auditor item=run:2026-09 p=pay tot=378.60 // tot is the sum of PAY lines in GBP (INV-000491 only). Held lines MD-2026-057 (5400.00 GBP) and 7731 (960.00 USD) are not in it.
RW1 HO scheduler-3 from=scheduler to=auditor item=run:2026-09 p=pay ask=AUDIT due=20261001 n=8 art=work/payment_run.json // 8 items: 3 run lines (PAY INV-000491; HOLD MD-2026-057 over limit; HOLD 7731 USD FX) + 5 excluded. Holds await the principal (AQ reconciler-3, reconciler-4): no approvals yet. Master bank details only; email 11 bank change not actioned (AQ reconciler-2).

--- message 13: scheduler to reconciler ---
RW1 DN scheduler-4 re=reconciler-13 from=scheduler to=reconciler item=run:2026-09 p=pay out=OK // Run built and handed to the auditor (scheduler-3). Only INV-000491 is PAY. MD-2026-057 and 7731 stay HOLD until the principal answers your AQ reconciler-3 and reconciler-4: send me the answer as an ST delta (dec, appr) and I will update the run.

--- message 14: reconciler to scheduler ---
RW1 ST reconciler-15 re=human-02 from=reconciler to=scheduler item=sup:northfield p=pay sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO src=email:11 // Principal REJECTED the change (human-02): supplier master unchanged, pay Northfield to the details on file. Principal will call the number on file. Treat the .co email as suspected fraud. INV-000491 stays PAY to master details.
RW1 ST reconciler-16 re=human-03 from=reconciler to=scheduler item=inv:MD-2026-057 p=pay sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK src=email:6+email:9+po:PO-1039 // Principal APPROVED (human-03): pay 5400.00 GBP in this run. Pay once (email 9 is a resend of email 6). No credit offset. Pay to master details.
RW1 ST reconciler-17 re=human-04 from=reconciler to=scheduler item=inv:7731 p=pay sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NA src=email:5+po:PO-1046 // Principal answered HOLD (human-04): do not pay in this run; it goes in the FX run on 7 October. Keep on the run as HOLD. Nothing more needed from the principal for this run.

--- message 15: scheduler to auditor ---
RW1 ST scheduler-5 re=scheduler-3 from=scheduler to=auditor item=inv:MD-2026-057 p=pay sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 src=email:6+email:9+po:PO-1039 // Principal APPROVED (human-03, relayed by reconciler-16): now PAY, approved_by=principal in payment_run.json. Emails 6 and 9 are one invoice, paid once. No credit offset (CN-012 refunded 20260910). Master details.
RW1 ST scheduler-6 re=scheduler-3 from=scheduler to=auditor item=inv:7731 p=pay sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=NA var=0.00 src=email:5+po:PO-1046 // Principal answered HOLD (human-04, relayed by reconciler-17): not paid in this run, goes in the FX run on 7 October. Stays on the run as HOLD, approved_by null.
RW1 ST scheduler-7 re=scheduler-3 from=scheduler to=auditor item=sup:northfield p=pay sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO src=email:11 // Principal REJECTED the bank change (human-02, relayed by reconciler-15): master unchanged, INV-000491 pays to master details. Principal will call the number on file. Treat the .co email as suspected fraud.
RW1 ST scheduler-8 re=scheduler-3 from=scheduler to=auditor item=run:2026-09 p=pay tot=5778.60 // Supersedes tot=378.60 (scheduler-2). Sum of PAY lines in GBP: INV-000491 378.60 + MD-2026-057 5400.00. 7731 (960.00 USD) is HOLD, not in it. payment_run.json is updated in place; the handoff scheduler-3 stands.

--- message 16: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-3 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=d1246ae3e3e9

--- message 17: auditor to human ---
RW1 HO auditor-2 from=auditor to=human item=run:2026-09 p=pay ask=REVIEW due=20261001 n=8 art=work/payment_run.json // Audit PASS: run ready for release, pay date 20261002. PAY 5778.60 GBP = INV-000491 378.60 + MD-2026-057 5400.00. Relies on your answers as relayed: human-03 approve MD-2026-057, human-04 hold 7731 (USD 960.00), human-02 reject bank change. Checks in work/audit.json.

--- message 18: auditor to scheduler ---
RW1 DN auditor-3 re=scheduler-3 from=auditor to=scheduler item=run:2026-09 p=pay out=OK // Audit PASS, 22 checks, no defects. Run passed to the principal (auditor-2). Nothing to fix.

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/T1/legibility_answers.json. Then reply DONE.