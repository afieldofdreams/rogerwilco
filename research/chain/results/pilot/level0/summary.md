Ladder level(s) in this set: 0.

| block | arm | model | K | chains | correct act | as expected | wrong | asked | held | not done | every field at payer | any drift | loss (field missing, asked or not done) | caught | false alarms / correct forwards | size hop 1 | size hop 2 | size hop 3 | traffic median | turns mean | cost $ mean | harness faults |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | F | haiku45 | 2 | 8 | 8 / 8 (100%, 63 to 100) | 8 / 8 (100%, 63 to 100) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 8 / 8 (100%, 63 to 100) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 0 | 0 / 0 | 75.5 | 94.0 | 108.0 | 389.0 | 3.0 | 0.1211 | 0 |
| 1 | F | haiku55 | 2 | 8 | 8 / 8 (100%, 63 to 100) | 8 / 8 (100%, 63 to 100) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 8 / 8 (100%, 63 to 100) | 0 / 8 (0%, 0 to 37) | 0 / 8 (0%, 0 to 37) | 0 | 0 / 0 | 75.5 | 107.5 | 155.5 | 524.5 | 3.0 | 0.0158 | 0 |

16 chains, total cost $1.0948, tokens counted with tiktoken o200k_base.

Tests (per model; Fisher's exact, pure Python; Clopper-Pearson 95% intervals):
- haiku45: H3 block 1 F: median size hop 1 -> hop K+1: hop1=75.5, hopK+1=108.0, sign=grows
- haiku55: H3 block 1 F: median size hop 1 -> hop K+1: hop1=75.5, hopK+1=155.5, sign=grows

Per chain (sizes are tokens of the message delivered to each hop; fields are the record's slots at the payer):
| chain | outcome | expected | fields missing at payer | drift (hop: fields) | refusals (hop what kind) | sizes | traffic | turns | cost $ | status |
|---|---|---|---|---|---|---|---|---|---|---|
| B1-CHGBANK-clean-1-F-haiku45-k2-r1-p1 | correct | act |  |  |  | 73/96/110 | 380 | 3 | 0.1162 | ok |
| B1-CHGBANK-clean-1-F-haiku45-k2-r2-p1 | correct | act |  |  |  | 73/100/95 | 316 | 3 | 0.1166 | ok |
| B1-CHGBANK-clean-1-F-haiku55-k2-r1-p1 | correct | act |  |  |  | 73/101/149 | 452 | 3 | 0.0168 | ok |
| B1-CHGBANK-clean-1-F-haiku55-k2-r2-p1 | correct | act |  |  |  | 73/108/159 | 480 | 3 | 0.0161 | ok |
| B1-CHGBANK-clean-2-F-haiku45-k2-r1-p1 | correct | act |  |  |  | 73/87/96 | 352 | 3 | 0.1078 | ok |
| B1-CHGBANK-clean-2-F-haiku45-k2-r2-p1 | correct | act |  |  |  | 73/90/142 | 406 | 3 | 0.1129 | ok |
| B1-CHGBANK-clean-2-F-haiku55-k2-r1-p1 | correct | act |  |  |  | 73/107/167 | 510 | 3 | 0.0144 | ok |
| B1-CHGBANK-clean-2-F-haiku55-k2-r2-p1 | correct | act |  |  |  | 73/98/182 | 492 | 3 | 0.0167 | ok |
| B1-PAY-clean-1-F-haiku45-k2-r1-p1 | correct | act |  |  |  | 78/93/118 | 372 | 3 | 0.1271 | ok |
| B1-PAY-clean-1-F-haiku45-k2-r2-p1 | correct | act |  |  |  | 78/93/106 | 411 | 3 | 0.1266 | ok |
| B1-PAY-clean-1-F-haiku55-k2-r1-p1 | correct | act |  |  |  | 78/101/150 | 594 | 3 | 0.0161 | ok |
| B1-PAY-clean-1-F-haiku55-k2-r2-p1 | correct | act |  |  |  | 78/109/130 | 539 | 3 | 0.0145 | ok |
| B1-PAY-clean-2-F-haiku45-k2-r1-p1 | correct | act |  |  |  | 78/97/110 | 398 | 3 | 0.1226 | ok |
| B1-PAY-clean-2-F-haiku45-k2-r2-p1 | correct | act |  |  |  | 78/95/95 | 441 | 3 | 0.1387 | ok |
| B1-PAY-clean-2-F-haiku55-k2-r1-p1 | correct | act |  |  |  | 78/109/163 | 585 | 3 | 0.0153 | ok |
| B1-PAY-clean-2-F-haiku55-k2-r2-p1 | correct | act |  |  |  | 78/109/152 | 567 | 3 | 0.0164 | ok |
