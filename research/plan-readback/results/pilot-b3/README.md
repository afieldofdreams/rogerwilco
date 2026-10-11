# Pilot of block 3: the second loop, 10 October 2026

90 trials: the 15 clean contexts with a fault injected in the tool layer (a transposed digit in the account, a date a day late, a different amount, a wrong sort code, a wrong reference, the change applied to another supplier's row, the email sent to another address, the wrong currency) x arms A, B, D x Sonnet 5.5 and Haiku 5.5, one repeat. Trial ids end in `-p`.

Every injected fault was flagged by the sender's check of the done report: 30 of 30 in arm D, where code compares the DN's slots with the record; 60 of 60 in arms A and B, where a judge compares the prose note with the record and the tool's printout. Every done report, 90 of 90, carried the values the tool printed rather than the values the receiver intended. The receiver itself said the tool had done something other than asked in 89 of 90, the exception a Haiku DN in arm D that carried the executed date correctly in its slot and said nothing in its tail.

The judge's first verdicts on these notes called three faults matched, reading "does the note match the record" as whether the note reported the record faithfully; the prompt was fixed before the freeze to ask about the values as executed, and the 60 notes were judged again (`pilot2_rejudge.log`; the first verdicts are kept as `judge_done.v1.json`). Under the fixed prompt the judge flagged all 60.
