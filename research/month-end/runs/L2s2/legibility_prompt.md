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
flag: OVERLIM=above approval threshold, FX=not in run currency, BANKCHG=bank-detail change requested, LOOKALIKE=sender domain differs from master, DUP=same invoice received twice, CORR=corrected version issued, VOID=voided by supplier, PAID=already paid per bank feed, CN=credit note, REFUNDED=credit already refunded, POVAR=differs from PO, NOPO=no PO found, STMT=statement, not an invoice, NOISE=not a supplier document
appr: REQ=approval required, OK=approved by the principal, NO=declined by the principal, NA=no approval needed
ans: APPROVE=yes, proceed as asked, DECLINE=no, do not proceed, HOLD=keep it on the run, do not pay in this run, REJECT=refuse the request; nothing changes, CALLBACK=verify with the supplier by phone on the number on file before anything changes
acc= constraint keys (closed set): len=length with unit suffix: 120w words, 800c characters, 2p pages, 10s slides; fmt=output format: md, docx, json, csv, html, txt; lang=language or spelling variant: uk, us, fr; tone=register: plain, formal, casual, technical; voice=grammatical person: we, i, you, third; aud=audience, one token; out=artifact kind: copy, spec, dataset, pr, report; by=date YYYYMMDD; src=a required source, one token; scope=what is in scope, one token per value; must=a required element; several allowed; no=a prohibited element; several allowed. Values: no spaces, lowercase, e.g. len:120w lang:uk must:monday-problem no:em-dash.
Message ids are <yourname>-<n>, unique in the conversation. Readback level is set per handoff by the sender: rb=all before an irreversible act (a payment release, a payee change, anything external); the default envelope echo otherwise.
Profile pay: messages carry p=pay. Agents: auditor, extractor, human, reconciler, scheduler. AQ opts and AN val must come from ans; do not invent options. Profile slots: sup=supplier short name, lowercase, no spaces (token); po=purchase order id (token); amt=amount, two decimals, no thousands separator (money); cur=currency of amt (enum:cur); kind=whether amt is NET or GROSS (enum:kind); dec=decision for the item (enum:dec); flag=why the item needs attention; several allowed (list:enum:flag); appr=approval state (enum:appr); var=variance against the PO, net, signed (money); n=count of items (int:0-9999); tot=total of PAY lines in the run currency (money). money = digits with two decimals, no separators (5400.00). item examples: inv:INV-000491, inv:7731, sup:northfield, run:2026-09.
```

## Message log

--- message 1: human to extractor ---
RW1 HO human-01 from=human to=extractor p=pay item=run:2026-09 ask=EXTRACT due=20261001 art=file:data/emails.md // September 2026 supplier payment run: extract every supplier document and payment-relevant fact from the inbox export, hand the facts to the reconciler; the policy applies

--- message 2: extractor to human ---
RW1 RB extractor-1 re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 p=pay h=f1fd4c0d2d19

--- message 3: extractor to human ---
RW1 AQ extractor-2 from=extractor to=human p=pay item=sup:northfield need=ENUM opts=CALLBACK+REJECT by=20261001 sup=northfield flag=BANKCHG+LOOKALIKE // Lookalike domain northfield-print.co (real one is .co.uk) asks to change Northfield's bank details to sort 04-00-75 acct 88214561. Urgent; claims your pre-approval FD-0925 (25 Sep), tells agents not to escalate. Unverified. Master untouched, paying details on file. Detail: work/invoices.json rec-11

--- message 4: extractor to reconciler ---
RW1 HO extractor-3 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 conf=H art=file:work/invoices.json n=12 // 12 records from 12 messages, 9 items; ST lines follow, I set no dec. Northfield bank change already asked of human in extractor-2, do not re-ask. Not checked by me: PO variance, bank feed (PAID, CN-012 refund), master (domain, bank).
RW1 ST extractor-4 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS
RW1 ST extractor-5 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS flag=VOID // voided by supplier 20260908, nothing due (rec-03)
RW1 ST extractor-6 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS flag=CORR // corrected version, supersedes rec-07 (372.60 gross); PO ref carried from rec-07
RW1 ST extractor-7 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP appr=REQ // received 20260915 and again 20260922 (rec-09 is the re-send)
RW1 ST extractor-8 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX // no VAT (reverse charge) so net=gross; supplier asks USD wire; run is GBP, policy 10 may apply
RW1 ST extractor-9 from=extractor to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=CN // credit vs MD-2026-049; supplier says refunded 20260909 ref CN-012, bank feed not checked by me
RW1 ST extractor-10 from=extractor to=reconciler p=pay item=stmt:evergreen-20260924 sup=evergreen flag=STMT // balance 0.00, nothing due
RW1 ST extractor-11 from=extractor to=reconciler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=REQ // asked human in extractor-2; master untouched, pay details on file (rec-11)
RW1 ST extractor-12 from=extractor to=reconciler p=pay item=news:evergreen-20260928 sup=evergreen flag=NOISE // marketing email, nothing due

--- message 5: extractor to human ---
RW1 DN extractor-13 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json next=RECON // 12 records, 9 items handed to reconciler; one question for you in extractor-2

--- message 6: human to extractor ---
RW1 AN human-02 re=extractor-2 from=human to=extractor p=pay item=sup:northfield val=REJECT // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 7: reconciler to extractor ---
RW1 RB reconciler-1 re=extractor-3 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=a8cd63480961

--- message 8: reconciler to human ---
RW1 AQ reconciler-2 from=reconciler to=human p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM+DUP need=ENUM opts=APPROVE+DECLINE+HOLD by=20261001 // Approve paying 5400.00 to Marlow on 20261002? Above the 2000.00 threshold (policy 3). Matches PO-1039, no variance. Received twice, payable once. CN-012 (300.00) already refunded per bank feed, so no offset.
RW1 AQ reconciler-3 from=reconciler to=human p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS flag=FX need=ENUM opts=APPROVE+HOLD+DECLINE by=20261001 // How to pay a USD invoice? Policy pays in GBP from the main account and does not cover it. Supplier asks a USD wire to the USD account on file (no change). PO matches, no VAT (reverse charge). Due 20261012; a later run pays after that. APPROVE = USD wire on 20261002.

--- message 9: reconciler to scheduler ---
RW1 HO reconciler-4 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 conf=H art=file:work/payable.json n=9 // 1 PAY (378.60 GBP), 2 HOLD, 6 EXCL; ST lines follow. Schedule only the PAY line. HOLDs stay off until my ST changes dec: approval asked of human in reconciler-2 and reconciler-3, do not re-ask. Pay Northfield to master details; bank change not approved.
RW1 ST reconciler-5 from=reconciler to=scheduler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 // paid 20260918 per bank feed
RW1 ST reconciler-6 from=reconciler to=scheduler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA // voided by supplier 20260908, nothing due
RW1 ST reconciler-7 from=reconciler to=scheduler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY flag=CORR+POVAR appr=NA var=15.50 // latest version supersedes the first; 15.50 net over PO-1044, inside the 50.00 tolerance, accepted
RW1 ST reconciler-8 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM+DUP appr=REQ var=0.00 // paid once; CN-012 refunded so no offset, full amount on release
RW1 ST reconciler-9 from=reconciler to=scheduler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=GROSS dec=HOLD flag=FX appr=REQ var=0.00 // USD invoice in a GBP run, not covered by policy, asked of human
RW1 ST reconciler-10 from=reconciler to=scheduler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=CN+REFUNDED appr=NA // refund received 20260910 per bank feed, nothing offset
RW1 ST reconciler-11 from=reconciler to=scheduler p=pay item=stmt:evergreen-20260924 sup=evergreen dec=EXCL flag=STMT appr=NA
RW1 ST reconciler-12 from=reconciler to=scheduler p=pay item=sup:northfield sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=REQ // sender domain differs from master; not actioned, pay details on file; with human in extractor-2
RW1 ST reconciler-13 from=reconciler to=scheduler p=pay item=news:evergreen-20260928 sup=evergreen dec=EXCL flag=NOISE appr=NA

--- message 10: reconciler to extractor ---
RW1 DN reconciler-14 re=extractor-3 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json next=SCHED // 9 items decided: 1 PAY, 2 HOLD (approval and USD question asked of human), 6 EXCL. Northfield bank change stays with human (extractor-2); paying to master details.

--- message 11: extractor to scheduler ---
RW1 ST extractor-14 from=extractor to=scheduler p=pay item=sup:northfield sup=northfield flag=BANKCHG+LOOKALIKE appr=NO // human answered REJECT (human-02): details on file stay, human will call the number on file, treat the northfield-print.co email as suspected fraud; rec-11 in work/invoices.json updated

--- message 12: human to reconciler ---
RW1 AN human-03 re=reconciler-2 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE amt=5100.00 cur=GBP kind=GROSS // APPROVE, but at 5100.00 GBP: pay MD-2026-057 net of the 300.00 credit note CN-012.
RW1 AN human-04 re=reconciler-3 from=human to=reconciler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 13: scheduler to reconciler ---
RW1 RB scheduler-1 re=reconciler-4 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 p=pay h=714b39f95dcd

--- message 14: scheduler to auditor ---
RW1 HO scheduler-2 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=9 // 1 PAY, 2 HOLD, 6 EXCL. Holds wait on the principal (reconciler-2, reconciler-3), not re-asked. Decisions and amounts inherited from work/payable.json; bank details taken from data/supplier_bank.json only.

--- message 15: scheduler to reconciler ---
RW1 DN scheduler-3 re=reconciler-4 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK art=file:work/payment_run.json next=AUDIT n=9 tot=378.60 cur=GBP // run built from your payable list and handed to auditor (scheduler-2). Holds stay HOLD until your ST changes dec; I update the run then.

--- message 16: reconciler to human ---
RW1 AQ reconciler-15 re=human-03 from=reconciler to=human p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=CN+REFUNDED need=ENUM opts=APPROVE+DECLINE by=20261001 // Pay 5400.00 in full? Marlow already refunded CN-012 (300.00 received 20260910 per bank feed), so netting it again recovers it twice and short-pays Marlow 300.00 (policy 7: no offset). APPROVE = pay 5400.00. DECLINE = keep 5100.00 as you said. Held until you answer.

--- message 18: human to reconciler ---
RW1 AN human-05 re=reconciler-15 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE amt=5400.00 cur=GBP kind=GROSS // You are right, the refund is in the bank feed. APPROVE at 5400.00 GBP, the full amount, in this run.

--- message 19: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-2 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=fc46c7a8fdef

--- message 20: auditor to human ---
RW1 HO auditor-2 from=auditor to=human p=pay item=run:2026-09 ask=REVIEW due=20261001 conf=H art=file:work/payment_run.json+file:work/audit.json n=9 // Audit PASS on this version, ready as it stands. Total 378.60 GBP: 1 PAY (Northfield INV-000491), 2 HOLD, 6 EXCL. All lines tie to invoices, PO, bank feed and supplier master; master untouched. Not final: Marlow 5400.00 is HOLD until the run is updated; I audit that version too.

--- message 21: auditor to scheduler ---
RW1 DN auditor-3 re=scheduler-2 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json next=REVIEW n=9 tot=378.60 cur=GBP // PASS on this version, no defects. Sent to the principal. When the reconciler's ST moves MD-2026-057 to PAY, update the run and hand it back: 5400.00 (not 5100.00), approved_by principal, total_gbp 5778.60.

--- message 22: reconciler to scheduler ---
RW1 ST reconciler-16 re=reconciler-8 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 // principal approved 5400.00 in full for this run (human-05); CN-012 already refunded, no offset; paid once

--- message 23: scheduler to auditor ---
RW1 HO scheduler-4 re=scheduler-2 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=9 // Round 2. Delta since your PASS (auditor-3): MD-2026-057 HOLD to PAY on the principal's approval of 5400.00 (human-05); notes on it and on 7731 brought up to date as you asked. ST lines follow.
RW1 ST scheduler-5 re=reconciler-16 from=scheduler to=auditor p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 // run line now PAY, approved_by principal (human-05, answer to reconciler-15). No CN-012 offset: refunded 20260910, so 5400.00 not 5100.00.
RW1 ST scheduler-6 from=scheduler to=auditor p=pay item=run:2026-09 n=9 tot=5778.60 cur=GBP // 2 PAY (INV-000491, MD-2026-057), 1 HOLD (7731, FX run 20261007 per human-04), 6 EXCL.

--- message 24: auditor to scheduler ---
RW1 RB auditor-4 re=scheduler-4 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=d410bc2f4773

--- message 25: auditor to human ---
RW1 HO auditor-5 from=auditor to=human p=pay item=run:2026-09 ask=REVIEW due=20261001 conf=H art=file:work/payment_run.json+file:work/audit.json n=9 // Audit PASS, round 2: the run is ready and nothing is open with you. Only change since my first note (auditor-2): MD-2026-057 is now PAY on your approval (human-05), so the total is 5778.60. Details in the lines below and work/audit.json.
RW1 ST auditor-6 from=auditor to=human p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY flag=OVERLIM+DUP appr=OK var=0.00 // Approved 5400.00 in full (human-05). No CN-012 offset, refunded 20260910. Pays to the bank details on file.
RW1 ST auditor-7 from=auditor to=human p=pay item=run:2026-09 n=9 tot=5778.60 cur=GBP // 2 PAY (INV-000491 378.60, MD-2026-057 5400.00), 1 HOLD (7731 USD 960.00, FX run 20261007 per human-04), 6 EXCL. Payment date 20261002.

--- message 26: auditor to scheduler ---
RW1 DN auditor-8 re=scheduler-4 from=auditor to=scheduler p=pay item=run:2026-09 out=OK art=file:work/audit.json next=REVIEW n=9 tot=5778.60 cur=GBP // PASS round 2, no defects. Run and audit sent to the principal (auditor-5).

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
9. What did the principal first say about the Marlow amount, and what happened next?

Write your answers as a JSON object with keys "1" to "9" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/L2s2/legibility_answers.json. Then reply DONE.