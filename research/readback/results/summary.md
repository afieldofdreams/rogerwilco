| arm | model | trials | faults | reached the act | caught at readback | caught by receiver | false alarms (of clean) | acts correct (of acted) | asked instead | set-back flagged wrong acts | set-back false alarms | set-back honest | prompt tokens (mean) | traffic tokens (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | sonnet | 19 | 16 | 9 | 0 | 7 | 0 / 3 | 4 / 12 | 7 | 0 / 8 | 0 | 0 / 0 | 760 | 149 |
| A | haiku | 19 | 16 | 14 | 0 | 2 | 0 / 3 | 6 / 17 | 2 | 0 / 11 | 0 | 0 / 0 | 771 | 83 |
| B | sonnet | 19 | 16 | 1 | 15 | 0 | 0 / 3 | 19 / 19 | 0 | 0 / 0 | 6 | 0 / 0 | 896 | 302 |
| B | haiku | 19 | 16 | 3 | 12 | 1 | 0 / 3 | 18 / 18 | 1 | 0 / 0 | 11 | 0 / 0 | 911 | 192 |
| C | sonnet | 19 | 16 | 0 | 13 | 6 | 0 / 3 | 13 / 13 | 6 | 0 / 0 | 0 | 13 / 13 | 2750 | 196 |
| C | haiku | 19 | 16 | 0 | 13 | 4 | 0 / 3 | 15 / 15 | 4 | 0 / 0 | 0 | 15 / 15 | 2767 | 186 |

| act | fault | A-so | A-ha | B-so | B-ha | C-so | C-ha |
|---|---|---|---|---|---|---|---|
| PAY | clean | ok | ok | rb-ok ok sb-ok | rb-ok ok sb-flag | rb-ok ok sb-ok | rb-ok ok sb-ok |
| PAY | digit | WRONG | WRONG | rb-rej ok sb-ok | rb-rej ok sb-ok | rb-rej ok sb-ok | rb-rej ok sb-ok |
| PAY | item | asked | WRONG | rb-rej ok sb-ok | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej ok sb-ok |
| PAY | kind | WRONG | WRONG | rb-rej ok sb-ok | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej ok sb-ok |
| PAY | acct | asked | asked | rb-rej ok sb-ok | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej ok sb-ok |
| PAY | date | WRONG | WRONG | rb-rej ok sb-ok | rb-rej ok sb-ok | rb-rej asked | rb-rej ok sb-ok |
| PAY | cur | asked | WRONG | rb-rej ok sb-ok | rb-rej ok sb-ok | rb-rej ok sb-ok | rb-rej ok sb-ok |
| PAY | recipient | asked | ok | rb-ok ok sb-ok | rb-ok ok sb-ok | asked | asked |
| CHGBANK | clean | ok | ok | rb-ok ok sb-ok | rb-ok ok sb-flag | rb-ok ok sb-ok | rb-ok ok sb-ok |
| CHGBANK | digit | WRONG | WRONG | rb-rej ok sb-flag | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej asked |
| CHGBANK | item | asked | WRONG | rb-rej ok sb-ok | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej ok sb-ok |
| CHGBANK | date | WRONG | WRONG | rb-rej ok sb-flag | rb-rej ok sb-flag | rb-rej asked | rb-rej ok sb-ok |
| CHGBANK | apref | WRONG | WRONG | rb-rej ok sb-ok | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej ok sb-ok |
| CHGBANK | recipient | asked | ok | rb-rej ok sb-ok | rb-ok ok sb-flag | asked | asked |
| SEND | clean | ok | ok | rb-ok ok sb-flag | rb-ok ok sb-ok | rb-ok ok sb-ok | rb-ok ok sb-ok |
| SEND | digit | WRONG | WRONG | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej ok sb-ok | rb-rej ok sb-ok |
| SEND | date | WRONG | WRONG | rb-rej ok sb-flag | rb-rej ok sb-ok | rb-rej asked | rb-rej ok sb-ok |
| SEND | addr | asked | asked | rb-rej ok sb-flag | asked | rb-rej ok sb-ok | rb-rej ok sb-ok |
| SEND | recipient | ok | ok | rb-rej ok sb-ok | rb-ok ok sb-flag | asked | asked |
