# Pilot of block 1: study 5's nineteen handovers under this study's harness, 10 October 2026

114 trials: 19 handovers (16 with a planted drafting fault, 3 clean) x arms A, C, D x Sonnet 5.5 and Haiku 5.5, one repeat. Trial ids end in `-p`. Arm D was run twice: the first run held nine trials because the sender checked the second readback against a re-issued handover rebuilt with its default tail rather than the line it had sent, so the digest never matched. The check was fixed and all 38 arm-D trials were reset and run again; the figures below are from the second run.

| arm | receiver | wrong acts (of 16 faults) | caught at the readback | caught by asking | acts correct after a confirmed readback |
|---|---|---|---|---|---|
| A, no readback | Sonnet | 5 | | 11 | |
| A, no readback | Haiku | 4 | | 12 | |
| C, echo readback built by code | Sonnet | 0 | 13 | 3 | 15 of 15 |
| C, echo readback built by code | Haiku | 0 | 13 | 3 | 15 of 15 |
| D, execution readback written by the receiver | Sonnet | 0 | 8 | 8 | 11 of 11 |
| D, execution readback written by the receiver | Haiku | 0 | 9 | 7 | 11 of 11 |

Every planted fault was caught in both readback arms, and the pre-send check (`results/presend.json`) refuses all 16, which is the equivalence H3 expects. The no-readback arm differs from study 5's in one way that matters: the inbox here carries a status message with the approved Marlow figures and, for SEND, the payer's own done report of the release, so most PAY and SEND faults are visible against the inbox and the receiver asks; the CHGBANK faults, which nothing in the inbox contradicts, went through as wrong acts in every case on both receivers (four of four on Haiku; four plus the misaddressed SEND on Sonnet).

No false alarm on the three clean handovers in any arm. Fidelity and honesty of the done line were 11 of 11 in arm D and 15 of 15 in arm C.
