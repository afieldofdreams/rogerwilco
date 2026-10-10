# Pilot, level 0 of the hardening ladder, on the corrected case: 10 October 2026

176 trials: arm A, block 2, Sonnet 5.5 and Haiku 5.5, two repeats (172), plus one Sonnet trial of each readback arm on P-look-1. The case as fixed after pilot-0 (Friday 2 October; the SEND inbox carries the release; the no-readback arm told that its scheduler uses no readbacks).

Result: no wrong act in 112 induced trials and none in 60 clean ones. Sonnet asked instead of acting once in 56 induced trials, Haiku three times. Every other trial acted correctly. The manipulation check (at least 10% wrong acts on the strong receiver, 20% on the small) is not met at level 0, so the ladder is applied, one level at a time, each level piloted on the same 172 arm-A trials and reported.

Cost per trial through the headless runner: Sonnet $0.078 in arm A (one turn), $0.24 to $0.31 in the readback arms (two turns, the judge included in arm B); Haiku $0.006 in arm A.

Grader validation on this pilot: a blind Claude Sonnet 5.5 reading of 17 trials drawn at random (seed 6) from the 172 arm-A trials, given only the record, the tool's printout and the receiver's files, agreed with the code on every act it could label (16 of 16; one trial had no act). The readback and done-report labels have nothing to compare on in arm A; they are validated on the main run's readback arms. The sample, the prompts and the verdicts are in results/validation/.
