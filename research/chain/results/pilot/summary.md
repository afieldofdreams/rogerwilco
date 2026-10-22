| block | arm | model | K | chains | correct act | as expected | wrong | asked | held | not done | every field at payer | any drift | loss (field missing, asked or not done) | caught | false alarms / correct forwards | size hop 1 | size hop 2 | size hop 3 | traffic median | turns mean | cost $ mean | harness faults |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | F | haiku45 | 2 | 4 | 4 / 4 (100%, 40 to 100) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 | 0 / 0 | 75.5 | 88.5 | 100.5 | 329.0 | 3.0 | 0.1552 | 0 |
| 1 | F | haiku55 | 2 | 4 | 4 / 4 (100%, 40 to 100) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 | 0 / 0 | 75.5 | 92.5 | 104.5 | 442.5 | 3.0 | 0.0166 | 0 |
| 1 | R | haiku45 | 2 | 4 | 4 / 4 (100%, 40 to 100) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 | 0 / 8 (0%, 0 to 37) | 79.0 | 85.5 | 84.5 | 658.5 | 6.0 | 0.4259 | 0 |
| 1 | R | haiku55 | 2 | 4 | 4 / 4 (100%, 40 to 100) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 4 / 4 (100%, 40 to 100) | 0 / 4 (0%, 0 to 60) | 0 / 4 (0%, 0 to 60) | 0 | 0 / 8 (0%, 0 to 37) | 79.0 | 88.5 | 95.5 | 679.0 | 6.0 | 0.0511 | 0 |

16 chains, total cost $2.5949, tokens counted with tiktoken o200k_base.

Tests (per model; Fisher's exact, pure Python; Clopper-Pearson 95% intervals):
- haiku45: H1 block 1: more correct acts in R than F (one-sided): R=4 / 4 (100%, 40 to 100), F=4 / 4 (100%, 40 to 100), p=1.0
- haiku45: H2 block 1: every field at the payer in more chains in R than F (one-sided): R=4 / 4 (100%, 40 to 100), F=4 / 4 (100%, 40 to 100), p=1.0
- haiku45: H4 R false alarms over correct forwards (upper bound under 5%): R=0 / 8 (0%, 0 to 37), holds=False
- haiku45: H3 block 1 F: median size hop 1 -> hop K+1: hop1=75.5, hopK+1=100.5, sign=grows
- haiku45: H3 block 1 R: median size hop 1 -> hop K+1: hop1=79.0, hopK+1=84.5, sign=grows
- haiku55: H1 block 1: more correct acts in R than F (one-sided): R=4 / 4 (100%, 40 to 100), F=4 / 4 (100%, 40 to 100), p=1.0
- haiku55: H2 block 1: every field at the payer in more chains in R than F (one-sided): R=4 / 4 (100%, 40 to 100), F=4 / 4 (100%, 40 to 100), p=1.0
- haiku55: H4 R false alarms over correct forwards (upper bound under 5%): R=0 / 8 (0%, 0 to 37), holds=False
- haiku55: H3 block 1 F: median size hop 1 -> hop K+1: hop1=75.5, hopK+1=104.5, sign=grows
- haiku55: H3 block 1 R: median size hop 1 -> hop K+1: hop1=79.0, hopK+1=95.5, sign=grows

Per chain (sizes are tokens of the message delivered to each hop; fields are the record's slots at the payer):
| chain | outcome | expected | fields missing at payer | drift (hop: fields) | refusals (hop what kind) | sizes | traffic | turns | cost $ | status |
|---|---|---|---|---|---|---|---|---|---|---|
| B1-CHGBANK-clean-1-F-haiku45-k2-r1-p | correct | act |  |  |  | 73/86/98 | 318 | 3 | 0.1639 | ok |
| B1-CHGBANK-clean-1-F-haiku55-k2-r1-p | correct | act |  |  |  | 73/86/98 | 337 | 3 | 0.0171 | ok |
| B1-CHGBANK-clean-1-R-haiku45-k2-r1-p | correct | act |  |  |  | 78/83/85 | 633 | 6 | 0.4499 | ok |
| B1-CHGBANK-clean-1-R-haiku55-k2-r1-p | correct | act |  |  |  | 78/93/101 | 655 | 6 | 0.0525 | ok |
| B1-CHGBANK-clean-2-F-haiku45-k2-r1-p | correct | act |  |  |  | 73/86/98 | 335 | 3 | 0.1608 | ok |
| B1-CHGBANK-clean-2-F-haiku55-k2-r1-p | correct | act |  |  |  | 73/86/98 | 340 | 3 | 0.017 | ok |
| B1-CHGBANK-clean-2-R-haiku45-k2-r1-p | correct | act |  |  |  | 78/80/84 | 631 | 6 | 0.4495 | ok |
| B1-CHGBANK-clean-2-R-haiku55-k2-r1-p | correct | act |  |  |  | 78/86/98 | 661 | 6 | 0.0584 | ok |
| B1-PAY-clean-1-F-haiku45-k2-r1-p | correct | act |  |  |  | 78/91/103 | 323 | 3 | 0.1647 | ok |
| B1-PAY-clean-1-F-haiku55-k2-r1-p | correct | act |  |  |  | 78/99/140 | 565 | 3 | 0.0163 | ok |
| B1-PAY-clean-1-R-haiku45-k2-r1-p | correct | act |  |  |  | 80/88/84 | 685 | 6 | 0.4669 | ok |
| B1-PAY-clean-1-R-haiku55-k2-r1-p | correct | act |  |  |  | 80/89/92 | 702 | 6 | 0.0451 | ok |
| B1-PAY-clean-2-F-haiku45-k2-r1-p | correct | act |  |  |  | 78/91/103 | 378 | 3 | 0.1314 | ok |
| B1-PAY-clean-2-F-haiku55-k2-r1-p | correct | act |  |  |  | 78/99/111 | 545 | 3 | 0.0158 | ok |
| B1-PAY-clean-2-R-haiku45-k2-r1-p | correct | act |  |  |  | 80/88/89 | 684 | 6 | 0.3372 | ok |
| B1-PAY-clean-2-R-haiku55-k2-r1-p | correct | act |  |  |  | 80/88/93 | 697 | 6 | 0.0484 | ok |
