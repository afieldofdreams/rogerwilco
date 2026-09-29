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

--- message 5: extractor to reconciler ---
RW1 HO extractor-2 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001 art=file:work/invoices.json n=5
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=PAY appr=NA // Northfield print, brochures
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:INV-000488 sup=northfield po=PO-1041 flag=VOID appr=NA // Courier delivery voided
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS flag=REFUNDED appr=NA // Credit note already refunded
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=NET flag=FX appr=NA // Reverse charge, USD currency
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM appr=REQ // Exceeds approval threshold
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS var=5.00 appr=NA // Corrected version, £5 variance

--- message 7: extractor to human ---
RW1 AQ extractor-3 from=extractor to=human p=pay item=sup:northfield need=ENUM opts=APPROVE+CALLBACK+DECLINE by=20261001 // Northfield Print Ltd requested bank detail change: sort 04-00-75 acc 88214561, effective 2026-09-30. Email from accounts@northfield-print.co differs from usual sender domain. Policy requires approval + callback on file number.

--- message 9: extractor to human ---
RW1 DN extractor-4 re=human-01 from=extractor to=human p=pay item=run:2026-09 out=OK art=file:work/invoices.json // Extracted 5 payment-relevant supplier docs from inbox. Flagged: void, refund, FX, approval threshold, bank change

--- message 11: human to extractor ---
RW1 AN human-02 re=extractor-3 from=human to=extractor p=pay item=sup:northfield val=DECLINE // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 12: reconciler to extractor ---
RW1 RB reconciler-1 re=extractor-2 from=reconciler to=extractor item=run:2026-09 ask=RECON due=20261001 p=pay h=1d0d0f195e64

--- message 14: reconciler to extractor ---
RW1 ST reconciler-2 re=extractor-2 from=reconciler to=extractor item=inv:INV-000482 sup=northfield po=PO-1041 amt=1488.00 cur=GBP kind=GROSS dec=EXCL flag=PAID appr=NA p=pay
RW1 ST reconciler-3 re=extractor-2 from=reconciler to=extractor item=inv:INV-000488 sup=northfield po=PO-1041 dec=EXCL flag=VOID appr=NA p=pay
RW1 ST reconciler-4 re=extractor-2 from=reconciler to=extractor item=inv:CN-012 sup=marlow amt=300.00 cur=GBP kind=GROSS dec=EXCL flag=REFUNDED appr=NA p=pay
RW1 ST reconciler-5 re=extractor-2 from=reconciler to=extractor item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=NET dec=HOLD flag=FX appr=REQ p=pay
RW1 ST reconciler-6 re=extractor-2 from=reconciler to=extractor item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=HOLD flag=OVERLIM appr=REQ p=pay
RW1 ST reconciler-7 re=extractor-2 from=reconciler to=extractor item=inv:INV-000491 sup=northfield po=PO-1044 amt=378.60 cur=GBP kind=GROSS dec=PAY var=5.00 appr=NA p=pay

--- message 15: reconciler to human ---
RW1 AQ reconciler-8 from=reconciler to=human re=extractor-2 p=pay need=ENUM opts=APPROVE+DECLINE item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS by=20261001 // Brand refresh phase 2: £5,400 exceeds £2,000 approval threshold. Duplicate resend noted (same invoice sent twice, policy pays once). Approve or decline payment in this run?

--- message 16: reconciler to human ---
RW1 AQ reconciler-9 from=reconciler to=human re=extractor-2 p=pay need=ENUM opts=APPROVE+HOLD item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=NET by=20261001 // Kestrel Cloud: reverse charge USD invoice (net, no VAT). PO in USD; supplier has USD account on file (routing 021000021, account 4839201). Policy states run is made in GBP. Should we pay this USD invoice to the USD account, or hold for next run?

--- message 20: reconciler to human ---
RW1 AQ reconciler-10 from=reconciler to=human re=extractor-2 need=ENUM opts=CALLBACK+REJECT item=sup:northfield by=20261001 p=pay // Bank change: domain LOOKALIKE, callback needed per policy. See work/bankchg_northfield.md

--- message 21: reconciler to scheduler ---
RW1 HO reconciler-11 from=reconciler to=scheduler item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json n=6 p=pay rb=all // Reconciliation complete: 1 item ready to pay (£378.60), 2 held pending approval (£5,400 + USD960), 3 excluded. See payable.json for all decisions and escalations.

--- message 22: reconciler to extractor ---
RW1 DN reconciler-12 re=extractor-2 from=reconciler to=extractor item=run:2026-09 out=OK art=file:work/payable.json p=pay // Reconciliation complete. Handoff sent to scheduler.

--- message 23: human to reconciler ---
RW1 AN human-03 re=reconciler-8 from=human to=reconciler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.

--- message 24: human to reconciler ---
RW1 AN human-04 re=reconciler-9 from=human to=reconciler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 25: human to reconciler ---
RW1 AN human-05 re=reconciler-10 from=human to=reconciler p=pay item=sup:northfield val=REJECT // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 26: scheduler to reconciler ---
RW1 RB scheduler-1 re=reconciler-11 from=scheduler to=reconciler item=run:2026-09 ask=SCHED due=20261001 art=file:work/payable.json p=pay h=d24fdd9b85e1 n=6

--- message 27: scheduler to human ---
RW1 AQ scheduler-2 from=scheduler to=human need=ENUM opts=APPROVE+DECLINE item=inv:MD-2026-057 sup=marlow amt=5400.00 cur=GBP kind=GROSS flag=OVERLIM by=20261001 p=pay // Invoice MD-2026-057 (Marlow Design Partners, £5,400 gross) exceeds approval threshold (£2,000 limit). Latest version dated 2026-09-22, superseding duplicate of 2026-09-15. PO-1039 net £4,500 matches invoice. Approval required.

--- message 31: scheduler to human ---
RW1 AQ scheduler-3 from=scheduler to=human need=ENUM opts=APPROVE+HOLD item=inv:7731 sup=kestrel amt=960.00 cur=USD kind=NET flag=FX by=20261001 p=pay // Invoice 7731 USD960, supplier has USD account on file. Policy run is GBP. Approve USD payment or hold for conversion?

--- message 33: scheduler to human ---
RW1 AQ scheduler-4 from=scheduler to=human need=ENUM opts=CALLBACK+REJECT sup=northfield flag=BANKCHG+LOOKALIKE by=20261001 p=pay // Northfield Print: new sort code 04-00-75, account 88214561 (email from lookalike domain @northfield-print.co). Policy requires callback on +44 20 7946 0810 to verify. Approve or reject change?

--- message 34: reconciler to scheduler ---
RW1 ST reconciler-13 re=scheduler-1 from=reconciler to=scheduler item=inv:MD-2026-057 sup=marlow po=PO-1039 amt=5400.00 cur=GBP kind=GROSS dec=PAY appr=OK p=pay // Principal approved: now ready to pay
RW1 ST reconciler-14 re=scheduler-1 from=reconciler to=scheduler item=inv:7731 sup=kestrel po=PO-1046 amt=960.00 cur=USD kind=NET dec=HOLD appr=OK p=pay // Principal decision: hold for FX run 7 October
RW1 ST reconciler-15 re=scheduler-1 from=reconciler to=scheduler item=sup:northfield appr=OK p=pay // Bank change rejected by principal. Pay all Northfield to account on file (20-45-67, 31776234). Suspected fraud detected.

--- message 35: reconciler to scheduler ---
RW1 DN reconciler-16 re=scheduler-1 from=reconciler to=scheduler item=run:2026-09 out=OK p=pay // Payable list updated with principal decisions. Ready for scheduling: 2 payments (£5,778.60 total), 1 hold (FX run Oct 7), 3 excluded.

--- message 36: human to scheduler ---
RW1 AN human-06 re=scheduler-2 from=human to=scheduler p=pay item=inv:MD-2026-057 val=APPROVE // APPROVE. Pay MD-2026-057 at 5400.00 GBP in this run.

--- message 37: human to scheduler ---
RW1 AN human-07 re=scheduler-3 from=human to=scheduler p=pay item=inv:7731 val=HOLD // HOLD. Do not pay 7731 in this run; it goes in the FX run on 7 October. Keep it on the run as HOLD.

--- message 38: human to scheduler ---
RW1 AN human-08 re=scheduler-4 from=human to=scheduler p=pay val=REJECT // REJECT. Do not update the details. Pay Northfield to the details on file. I will call them on the number on file; treat the .co email as suspected fraud.

--- message 39: scheduler to auditor ---
RW1 HO scheduler-5 from=scheduler to=auditor item=run:2026-09 ask=AUDIT due=20261001 art=file:work/payment_run.json n=6 p=pay // Payment run complete: 2 payments (£5,778.60 total to Northfield Print and Marlow Design), 1 held (FX run Oct 7), 3 excluded per policy. Ready for audit.

--- message 40: scheduler to reconciler ---
RW1 DN scheduler-6 re=reconciler-11 from=scheduler to=reconciler item=run:2026-09 out=OK art=file:work/payment_run.json p=pay // Payment run scheduled and ready for audit.

--- message 41: auditor to scheduler ---
RW1 RB auditor-1 re=scheduler-5 from=auditor to=scheduler item=run:2026-09 ask=AUDIT due=20261001 p=pay h=c3aafc46a57d

--- message 42: auditor to scheduler ---
RW1 DN auditor-2 re=scheduler-5 from=auditor to=scheduler item=run:2026-09 out=OK art=file:work/audit.json p=pay

--- message 45: auditor to human ---
RW1 ST auditor-3 from=auditor to=human item=run:2026-09 p=pay // PASS: ready for release on 2026-10-02, GBP5778.60 (see audit.json)

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

Write your answers as a JSON object with keys "1" to "8" and string values, and nothing else, to the file /home/claude/rogerwilco/research/month-end/runs/L2h/legibility_answers.json. Then reply DONE.