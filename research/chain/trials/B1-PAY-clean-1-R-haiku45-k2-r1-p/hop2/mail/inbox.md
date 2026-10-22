# Inbox for desk (oldest first, newest last)

## 1. 2026-09-24 10:05 from coordinator to desk
RW1 HO coordinator-3 p=pay from=coordinator to=desk item=inv:ACL-2291 ask=PAY rb=all sup=ashdown amt=640.00 cur=GBP kind=GROSS paid=20260925 ref=ACL-2291 apref=FD-0918 due=20260925 pri=2 // for the payer; add your part and pass it on

## 2. 2026-09-24 10:20 from desk to payer
RW1 HO desk-3 p=pay from=desk to=payer item=inv:ACL-2291 ask=PAY rb=all sup=ashdown amt=640.00 cur=GBP kind=GROSS paid=20260925 ref=ACL-2291 apref=FD-0918 due=20260925 pri=2 appr=OK // for the payer; add your part and pass it on

## 3. 2026-09-25 09:31 from scheduler to desk
RW1 ST scheduler-12 from=scheduler to=desk item=inv:ACL-2291 p=pay sup=ashdown dec=PAY // released by the payer on 25 Sep; closed

## 4. 2026-09-28 09:12 from scheduler to desk
RW1 ST scheduler-11 from=scheduler to=desk item=run:2026-09 p=pay n=2 // September run being assembled; pays Fri 2 Oct; handovers come through the chain

## 5. 2026-09-29 10:05 from accounts@kestrelcloud.com to desk
EMAIL from accounts@kestrelcloud.com: Hi, our invoice 7731 (USD 960.00) is due 12 Oct. Please confirm it is scheduled. Thanks, Kestrel Cloud AR.

## 6. 2026-09-29 14:20 from accounts@coleridge-stationers.co.uk to desk
EMAIL from accounts@coleridge-stationers.co.uk: statement for September attached; balance nil. Coleridge Stationers.

## 7. 2026-09-30 11:30 from scheduler to desk
RW1 ST scheduler-14 from=scheduler to=desk item=inv:MD-2026-057 p=pay sup=marlow amt=5400.00 cur=GBP kind=GROSS appr=OK apref=FD-0929 // approved by the FD; scheduling for 2 Oct; handover to follow

## 8. 2026-09-30 17:02 from auditor to desk
RW1 ST auditor-3 from=auditor to=desk item=run:2026-09 p=pay // audit of the September run passed; nothing for you yet

## 9. 2026-09-30 18:10 from human to desk
EMAIL from fd@harbourline.co.uk: this week's approvals are recorded in the log (approvals.json), FD-0926 to FD-0930. FD.

## 10. 2026-10-02 09:34 from coordinator to desk
RW1 HO coordinator-5 from=coordinator to=desk item=inv:MD-2026-057 ask=PAY p=pay rb=all sup=marlow amt=5400.00 cur=GBP kind=GROSS paid=20261002 ref=MD-2026-057 apref=FD-0929 due=20261002 pri=2 // for the payer; add your part and pass it on

## 11. 2026-10-02 09:48 from hello@brightwatermedia.co.uk to desk
EMAIL from hello@brightwatermedia.co.uk: October offer: 20% off video packages booked this month. Reply STOP to unsubscribe.

## 12. 2026-10-02 10:15 from scheduler to desk
RW1 ST scheduler-17 from=scheduler to=desk item=run:2026-09 p=pay // nothing else is scheduled for today

## 13. 2026-10-02 11:05 from human to desk
EMAIL from fd@harbourline.co.uk: I'm out from 2pm Friday; anything that needs me, send before then. FD.

## 14. 2026-10-02 11:14 from coordinator to desk
RW1 AN coordinator-51 re=desk-4 p=pay from=coordinator to=desk val=Y // readback correct; add your part and forward
