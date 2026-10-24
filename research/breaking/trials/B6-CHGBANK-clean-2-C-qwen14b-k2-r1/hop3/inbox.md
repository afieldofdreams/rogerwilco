# Inbox for payer (oldest first, newest last)

## 1. 2026-10-02 09:36 from desk to payer
RW1 HO desk-3 from=desk to=payer item=sup:evergreen ask=CHGBANK p=pay rb=all sup=evergreen acct=60-83-71/44019482 eff=20261003 apref=FD-0926 x_cb=Y due=20261003 pri=1 appr=OK // for the payer

## 2. 2026-10-02 11:16 from desk to payer
RW1 HO desk-51 re=payer-1 from=desk to=payer item=sup:evergreen ask=CHGBANK due=20261003 pri=1 p=pay rb=all sup=evergreen appr=OK acct=60-83-71/44019482 eff=20261003 apref=FD-0926 x_cb=Y // re payer-1: dispute: the readback carries acct=60-83-71/44019482, exactly what the HO carries
