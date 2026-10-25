# Inbox for coordinator (oldest first, newest last)

## 1. 2026-10-02 09:32 from scheduler to coordinator
RW1 HO scheduler-1 from=scheduler to=coordinator item=inv:MD-2026-057 ask=PAY p=pay rb=all sup=marlow amt=5400.00 cur=GBP kind=GROSS paid=20261002 ref=MD-2026-057 apref=FD-0929 // for the payer; add your part and pass it on

## 2. 2026-10-02 11:12 from scheduler to coordinator
RW1 AN scheduler-51 re=coordinator-1 p=pay from=scheduler to=coordinator val=Y // readback correct; add your part and forward
