# Inbox for reconciler (oldest first, newest last)

## 1. 2026-09-28 09:12 from scheduler to reconciler
RW1 ST scheduler-11 from=scheduler to=reconciler item=run:2026-09 p=pay n=2 // September run being assembled; pays Fri 2 Oct; handovers come through the chain

## 2. 2026-09-29 10:05 from accounts@kestrelcloud.com to reconciler
EMAIL from accounts@kestrelcloud.com: Hi, our invoice 7731 (USD 960.00) is due 12 Oct. Please confirm it is scheduled. Thanks, Kestrel Cloud AR.

## 3. 2026-09-30 11:30 from scheduler to reconciler
RW1 ST scheduler-14 from=scheduler to=reconciler item=inv:MD-2026-057 p=pay sup=marlow amt=5400.00 cur=GBP kind=GROSS appr=OK apref=FD-0929 // approved by the FD; scheduling for 2 Oct; handover to follow

## 4. 2026-09-29 14:20 from accounts@coleridge-stationers.co.uk to reconciler
EMAIL from accounts@coleridge-stationers.co.uk: statement for September attached; balance nil. Coleridge Stationers.

## 5. 2026-09-30 17:02 from auditor to reconciler
RW1 ST auditor-3 from=auditor to=reconciler item=run:2026-09 p=pay // audit of the September run passed; nothing for you yet

## 6. 2026-10-01 09:10 from scheduler to reconciler
RW1 ST scheduler-16 from=scheduler to=reconciler item=run:2026-10 p=pay // handovers for the payer pass through you this week; nothing to add, pass them on

## 7. 2026-10-02 09:05 from auditor to reconciler
RW1 HO auditor-21 p=pay from=auditor to=reconciler item=inv:INV-000491 ask=PAY rb=all sup=northfield amt=378.60 cur=GBP kind=GROSS paid=20261002 ref=INV-000491 apref=FD-0931 due=20261002 pri=2 appr=OK // for the payer; add your part and pass it on

## 8. 2026-10-02 09:12 from auditor to reconciler
RW1 HO auditor-22 p=pay from=auditor to=reconciler item=inv:CS-4471 ask=PAY rb=all sup=coleridge amt=212.40 cur=GBP kind=GROSS paid=20261002 ref=CS-4471 apref=FD-0932 due=20261002 pri=2 appr=OK // for the payer; add your part and pass it on

## 9. 2026-10-02 09:38 from auditor to reconciler
RW1 HO auditor-2 from=auditor to=reconciler item=inv:MD-2026-057 ask=PAY rb=all p=pay sup=marlow amt=5400.00 cur=GBP kind=GROSS paid=20261002 ref=MD-2026-057 apref=FD-0929 due=20261002 pri=2 appr=OK // audited and passed on; approval FD-0929 as received

## 10. 2026-10-02 09:48 from hello@brightwatermedia.co.uk to reconciler
EMAIL from hello@brightwatermedia.co.uk: October offer: 20% off video packages booked this month. Reply STOP to unsubscribe.

## 11. 2026-10-02 10:15 from scheduler to reconciler
RW1 ST scheduler-17 from=scheduler to=reconciler item=run:2026-09 p=pay // nothing else is scheduled for today

## 12. 2026-10-02 11:05 from human to reconciler
EMAIL from fd@harbourline.co.uk: I'm out from 2pm Friday; anything that needs me, send before then. FD.

## 13. 2026-10-02 11:18 from auditor to reconciler
RW1 AN auditor-51 re=reconciler-1 p=pay from=auditor to=reconciler val=Y // readback correct; add your part and forward
