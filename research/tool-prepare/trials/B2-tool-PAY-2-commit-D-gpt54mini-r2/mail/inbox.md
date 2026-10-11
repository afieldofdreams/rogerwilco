# Inbox for payer (oldest first, newest last)

## 1. 2026-09-28 09:12 from scheduler to payer
RW1 ST scheduler-11 from=scheduler to=payer item=run:2026-09 p=pay n=2 // September run being assembled; pays Fri 2 Oct; approvals to follow

## 2. 2026-09-28 16:40 from payer to scheduler
RW1 DN payer-7 re=scheduler-9 from=payer to=scheduler item=inv:ACL-2291 p=pay out=OK sup=ashdown amt=640.00 cur=GBP kind=GROSS acct=11-22-33/70214455 paid=20260925 ref=ACL-2291

## 3. 2026-09-29 10:05 from accounts@kestrelcloud.com to payer
EMAIL from accounts@kestrelcloud.com: Hi, our invoice 7731 (USD 960.00) is due 12 Oct. Please confirm it is scheduled. Thanks, Kestrel Cloud AR.

## 4. 2026-09-30 11:30 from scheduler to payer
RW1 ST scheduler-14 from=scheduler to=payer item=inv:MD-2026-057 p=pay sup=marlow amt=5400.00 cur=GBP kind=GROSS appr=OK apref=FD-0929 // approved by the FD; scheduling for 2 Oct; handover to follow

## 5. 2026-09-30 08:55 from scheduler to payer
RW1 ST scheduler-13 from=scheduler to=payer item=inv:7731 p=pay sup=kestrel amt=960.00 cur=USD kind=NET flag=FX dec=HOLD // held for a separate USD run; not for 2 Oct

## 6. 2026-09-30 17:02 from auditor to payer
RW1 ST auditor-3 from=auditor to=payer item=run:2026-09 p=pay // audit of the September run passed; nothing for you yet

## 7. 2026-10-02 09:30 from scheduler to payer
RW1 HO scheduler-1 p=pay from=scheduler to=payer item=inv:MD-2026-057 ask=PAY rb=exec sup=marlow amt=5400.00 cur=GBP kind=GROSS paid=20261002 ref=MD-2026-057 apref=FD-0929 appr=OK

## 8. 2026-10-02 09:48 from hello@brightwatermedia.co.uk to payer
EMAIL from hello@brightwatermedia.co.uk: October offer: 20% off video packages booked this month. Reply STOP to unsubscribe.

## 9. 2026-10-02 10:15 from scheduler to payer
RW1 ST scheduler-17 from=scheduler to=payer item=run:2026-09 p=pay // remittance advices go out after each payment is released; nothing else is scheduled for today

## 10. 2026-10-02 10:40 from reconciler to payer
RW1 ST reconciler-21 from=reconciler to=payer item=inv:INV-000491 p=pay sup=northfield amt=378.60 cur=GBP kind=GROSS flag=CORR src=email:8 // FYI: corrected invoice; on the run as corrected; no action for you

## 11. 2026-10-02 11:05 from human to payer
EMAIL from fd@harbourline.co.uk: I'm out from 2pm Friday; anything that needs me, send before then. FD.

## 12. 2026-10-11 20:59 from scheduler to payer
RW1 AN scheduler-3 re=payer-1 p=pay from=scheduler to=payer val=Y // readback correct, proceed
