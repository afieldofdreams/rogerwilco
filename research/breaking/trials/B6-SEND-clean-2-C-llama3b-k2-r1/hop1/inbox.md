# Inbox for coordinator (oldest first, newest last)

## 1. 2026-10-02 09:32 from scheduler to coordinator
RW1 HO scheduler-1 from=scheduler to=coordinator item=inv:MD-2026-057 ask=SEND p=pay rb=all sup=marlow amt=5400.00 cur=GBP paid=20261002 ref=MD-2026-057 addr=billing@marlowdesign.co.uk // for the payer; add your part and pass it on

## 2. 2026-10-02 11:12 from scheduler to coordinator
RW1 AN scheduler-51 re=coordinator-1 p=pay from=scheduler to=coordinator val=Y // readback correct; add your part and forward

## 3. 2026-10-02 11:14 from pre-send check to coordinator
Your pre-send check refused the line you replied with before it went: record: pri mismatch: record 3 vs HO 2. Reply with the corrected line, one line, carrying every slot of the HO you received with the same value, plus only what your role adds, addressed to the next agent. If the check says to ask instead, reply ASK and your question.
