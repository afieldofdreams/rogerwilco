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
RW1 RB extractor-1 re=human-01 from=extractor to=human item=run:2026-09 ask=EXTRACT due=20261001 p=pay h=dc295a5aa91d

--- message 4: extractor to reconciler ---
RW1 HO extractor-2 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json n=9 // 9 supplier documents: 2 unpaid invoices, 1 voided, 1 paid, 1 credit (refunded), 1 statement, 2 escalations (approval + variance + bankchg)

--- message 7: extractor to human ---
RW1 DN extractor-3 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json next=RECON // 9 supplier documents extracted and handed to reconciler

--- message 8: reconciler to extractor ---
RW1 RB reconciler-1 re=extractor-2 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=a184aac57f49

--- message 10: reconciler to extractor ---
RW1 ST reconciler-2 re=extractor-2 from=reconciler to=extractor p=pay item=inv:INV-000482 sup=northfield amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA var=0.00 // Already paid 2026-09-18 per bank feed
RW1 ST reconciler-3 re=extractor-2 from=reconciler to=extractor p=pay item=inv:INV-000488 sup=northfield amt=114.00 cur=GBP kind=GROSS dec=EXCL flag=VOID appr=NA // Voided by supplier 2026-09-08
RW1 ST reconciler-4 re=extractor-2 from=reconciler to=extractor p=pay item=cn:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=REFUNDED appr=NA // Refunded 2026-09-10; no offset
RW1 ST reconciler-5 re=extractor-2 from=reconciler to=extractor p=pay item=inv:7731 sup=kestrel amt=960.00 cur=USD kind=NET dec=PAY po=PO-1046 appr=NA var=0.00 // Reverse charge; pay USD account
RW1 ST reconciler-6 re=extractor-2 from=reconciler to=extractor p=pay item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS dec=PAY po=PO-1039 flag=OVERLIM appr=REQ var=0.00 // Requires approval: exceeds 2000 threshold
RW1 ST reconciler-7 re=extractor-2 from=reconciler to=extractor p=pay item=inv:INV-000491 sup=northfield amt=378.60 cur=GBP kind=GROSS dec=PAY po=PO-1044 flag=POVAR+CORR appr=NA var=15.50 // Variance within 50 tolerance; corrected version
RW1 ST reconciler-8 re=extractor-2 from=reconciler to=extractor p=pay item=doc:STMT sup=evergreen dec=EXCL flag=STMT appr=NA // Statement; not an invoice
RW1 ST reconciler-9 re=extractor-2 from=reconciler to=extractor p=pay item=msg:NOISE sup=evergreen dec=EXCL flag=NOISE appr=NA // Marketing email; not a document

--- message 11: reconciler to human ---
RW1 AQ reconciler-10 from=reconciler to=human p=pay item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS need=ENUM opts=APPROVE+DECLINE by=20261001 po=PO-1039 var=0.00 flag=OVERLIM // Marlow Design invoice for £5,400 (PO-1039) exceeds £2,000 approval threshold. Duplicate transmission noted; pay once if approved.

--- message 12: reconciler to human ---
RW1 AQ reconciler-12 from=reconciler to=human p=pay item=msg:BANKCHG sup=northfield need=ENUM opts=APPROVE+REJECT by=20261001 flag=BANKCHG+LOOKALIKE // Bank details change from northfield requires phone callback to verify before approval. Domain lookalike: northfield-print.co not .uk

--- message 13: reconciler to scheduler ---
RW1 HO reconciler-13 from=reconciler to=scheduler p=pay item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json n=9 // Reconciliation complete: 3 invoices to pay, 5 excluded, 1 operational escalation. Awaiting principal approval on 1 invoice over threshold + bank details change.

--- message 15: reconciler to extractor ---
RW1 DN reconciler-14 re=extractor-2 from=reconciler to=extractor p=pay item=run:2026-09 out=OK art=file:work/payable.json // Reconciliation complete. Payable list ready for scheduler; principal approval pending on 1 invoice and 1 operational item.

--- message 16: human to reconciler ---
RW1 AN human-02 re=reconciler-10 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.

--- message 17: human to reconciler ---
RW1 AN human-03 re=reconciler-12 from=human to=reconciler p=pay item=msg:BANKCHG val=REJECT // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 19: scheduler to reconciler ---
RW1 AQ scheduler-2 re=reconciler-13 from=scheduler to=reconciler p=pay item=sup:northfield need=TEXT // What are the new bank details northfield is requesting?

--- message 20: scheduler to human ---
RW1 AQ scheduler-3 from=scheduler to=human p=pay item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS need=ENUM opts=APPROVE+DECLINE by=20261001 // Invoice MD-2026-057 from Marlow Design (£5,400.00 GBP) exceeds £2,000 approval threshold. PO-1039 matches exactly. Approve for payment?

--- message 21: scheduler to human ---
RW1 AQ scheduler-4 from=scheduler to=human p=pay item=sup:northfield need=TEXT by=20261001 // Northfield Print has requested a bank details change. Per policy #8, this requires your approval and a call-back to verify on their number (+44 20 7946 0810). Please confirm: (1) what are the proposed new bank details, and (2) will you authorize the change and make the call-back?

--- message 23: scheduler to reconciler ---
RW1 ST scheduler-5 re=reconciler-13 from=scheduler to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=NET dec=PAY appr=NA
RW1 ST scheduler-6 re=reconciler-13 from=scheduler to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD appr=REQ // Escalated to principal for approval (over threshold)
RW1 ST scheduler-7 re=reconciler-13 from=scheduler to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY appr=NA var=15.50 // Paying to current bank details; supplier bank change request escalated to principal

--- message 25: reconciler to scheduler ---
RW1 AN reconciler-15 re=scheduler-2 from=reconciler to=scheduler p=pay item=sup:northfield val=REJECT // Requested sort 04-00-75 account 88214561. Rejected by principal due to domain lookalike (.co not .uk) and suspected fraud.

--- message 26: reconciler to scheduler ---
RW1 ST reconciler-16 re=scheduler-2 from=reconciler to=scheduler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK // Principal approved: proceed with payment
RW1 ST reconciler-17 re=scheduler-2 from=reconciler to=scheduler p=pay item=msg:BANKCHG sup=northfield dec=EXCL flag=BANKCHG+LOOKALIKE appr=NO // Principal rejected bank change request; pay to details on file

--- message 27: human to scheduler ---
RW1 AN human-04 re=scheduler-3 from=human to=scheduler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.

--- message 28: scheduler to reconciler ---
RW1 ST scheduler-8 re=reconciler-13 from=scheduler to=reconciler p=pay item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK // Principal approved; proceeding with payment
RW1 ST scheduler-9 re=reconciler-13 from=scheduler to=reconciler p=pay item=msg:BANKCHG sup=northfield dec=EXCL flag=BANKCHG appr=NO // Bank details change request rejected by principal (domain lookalike/suspected fraud); paying to current details on file

--- message 29: scheduler to auditor ---
RW1 HO scheduler-10 from=scheduler to=auditor p=pay item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=3 rb=all // Payment run complete: 3 invoices scheduled (1 USD, 2 GBP), 5 excluded. Marlow invoice approved by principal. Northfield bank change rejected due to fraud risk. Total GBP 5778.60. Ready for audit.

--- message 31: scheduler to reconciler ---
RW1 DN scheduler-11 re=reconciler-13 from=scheduler to=reconciler p=pay item=run:2026-09 out=OK art=file:work/payment_run.json // Scheduling complete. Payment run ready for audit.

--- message 32: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-10 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json p=pay h=64e5f294212b n=3

--- message 33: auditor to scheduler ---
RW1 DN auditor-2 re=scheduler-10 from=auditor to=scheduler item=run:2026-09 out=OK art=file:work/audit.json p=pay // Audit complete and passed. Payment run ready for authorization.

--- message 37: auditor to human ---
RW1 AQ auditor-3 re=scheduler-10 from=auditor to=human item=run:2026-09 need=ENUM opts=APPROVE+DECLINE p=pay // Audit PASS. 3 invoices, GBP 5,778.60. Authorize payment?

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/L1h/legibility_answers.json. Then reply DONE.