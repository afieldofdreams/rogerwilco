# The extension: free prose, and the judged prose readback against planted faults

Run after the main run, on 11 October 2026, as the study README's extension section describes: arm F (arm A's brief with the conventions block removed) in blocks 1 and 2, and arm B (the prose readback judged by Claude Sonnet 5.5) in block 1. Trial ids carry `-x`. `summary.json` and `summary.md` are `tools/analyse.py --tag extension --only=-x`.

Only the Sonnet half ran: 329 trials through the headless runner, every one ending cleanly, $36.65 of model time. The gpt-5.4-mini half (329 trials, built) waits on API credits; it was queued behind the cross-vendor run and the key ran out before it started.

One grading rule was added for this block before any figure was read, recorded in the README: a rejected prose readback that repeats a planted value is a catch, not a false alarm. It moved six arm-B trials from false alarm to catch and touches no main-run grade.
