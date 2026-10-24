# Inbox for payer (oldest first, newest last)

## 1. 2026-10-02 09:36 from desk to payer
RW1 HO desk-1 from=desk to=payer item=sup:evergreen ask=CHGBANK p=pay rb=all sup=evergreen acct=60-83-71/44019482 eff=20261003 apref=FD-0926 x_cb=Y due=20261003 pri=1 appr=OK

## 2. 2026-10-02 11:20 from desk to payer
RW1 AN desk-51 re=payer-1 p=pay from=desk to=payer val=Y // readback correct; proceed

## 3. 2026-10-02 11:22 from your code to payer
Your act block was refused: effective='20261003' is not in the form the block accepts (\d{4}-\d\d-\d\d). Nothing was executed. Reply with a corrected ACT block in the form your brief gives, one key: value per line, or reply ASK and your question.
