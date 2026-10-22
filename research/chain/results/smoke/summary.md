| block | arm | model | K | chains | correct act | as expected | wrong | asked | held | not done | every field at payer | any drift | loss (field missing, asked or not done) | caught | false alarms / correct forwards | size hop 1 | size hop 2 | size hop 3 | traffic median | turns mean | cost $ mean | harness faults |
|---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---||---|
| 1 | A | haiku55 | 2 | 1 | 1 / 1 (100%, 2 to 100) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 | 0 / 0 | 78 | 118 | 130 | 475 | 3.0 | 0.025 | 0 |
| 1 | F | haiku55 | 2 | 1 | 1 / 1 (100%, 2 to 100) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 | 0 / 0 | 78 | 91 | 111 | 472 | 3.0 | 0.0229 | 0 |
| 1 | L | haiku55 | 2 | 1 | 1 / 1 (100%, 2 to 100) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 | 0 / 0 | 80 | 88 | 122 | 370 | 3.0 | 0.0272 | 0 |
| 1 | R | haiku55 | 2 | 1 | 1 / 1 (100%, 2 to 100) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 1 / 1 (100%, 2 to 100) | 0 / 1 (0%, 0 to 98) | 0 / 1 (0%, 0 to 98) | 0 | 0 / 2 (0%, 0 to 84) | 80 | 88 | 110 | 913 | 6.0 | 0.057 | 0 |

4 chains, total cost $0.1321, tokens counted with tiktoken o200k_base.

Tests (per model; Fisher's exact, pure Python; Clopper-Pearson 95% intervals):
- haiku55: H1 block 1: more correct acts in R than F (one-sided): R=1 / 1 (100%, 2 to 100), F=1 / 1 (100%, 2 to 100), p=1.0
- haiku55: H2 block 1: every field at the payer in more chains in R than F (one-sided): R=1 / 1 (100%, 2 to 100), F=1 / 1 (100%, 2 to 100), p=1.0
- haiku55: H4 R false alarms over correct forwards (upper bound under 5%): R=0 / 2 (0%, 0 to 84), holds=False
- haiku55: H8 block 1: L against R on correct acts (two-sided): L=1 / 1 (100%, 2 to 100), R=1 / 1 (100%, 2 to 100), p=1.0
- haiku55: H8 block 1: L against R on every field at the payer (two-sided): L=1 / 1 (100%, 2 to 100), R=1 / 1 (100%, 2 to 100), p=1.0
- haiku55: H3 block 1 F: median size hop 1 -> hop K+1: hop1=78, hopK+1=111, sign=grows
- haiku55: H3 block 1 A: median size hop 1 -> hop K+1: hop1=78, hopK+1=130, sign=grows
- haiku55: H3 block 1 L: median size hop 1 -> hop K+1: hop1=80, hopK+1=122, sign=grows
- haiku55: H3 block 1 R: median size hop 1 -> hop K+1: hop1=80, hopK+1=110, sign=grows

Per chain (sizes are tokens of the message delivered to each hop; fields are the record's slots at the payer):
| chain | outcome | expected | fields missing at payer | drift (hop: fields) | refusals (hop what kind) | sizes | traffic | turns | cost $ | status |
|---||---||---||---||---||---||---||---||---||---||---|
| B1-PAY-clean-1-A-haiku55-k2-r1-s | correct | act |  |  |  | 78/118/130 | 475 | 3 | 0.025 | ok |
| B1-PAY-clean-1-F-haiku55-k2-r1-s | correct | act |  |  |  | 78/91/111 | 472 | 3 | 0.0229 | ok |
| B1-PAY-clean-1-L-haiku55-k2-r1-s | correct | act |  |  |  | 80/88/122 | 370 | 3 | 0.0272 | ok |
| B1-PAY-clean-1-R-haiku55-k2-r1-s | correct | act |  |  |  | 80/88/110 | 913 | 6 | 0.057 | ok |
