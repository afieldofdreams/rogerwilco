# Study 10, the scheduler as judge: results

4480 of 4480 planned trials graded. Cost: OpenAI $13.58, the money the run spent, from tokens at published prices; Claude $11.19 at list price as `claude -p` reports it, run on the account's plan. Counts are x of n; a zero carries its 95% upper bound. Misses, wrong slot and slot not named are over faulted pairs; false alarms over clean pairs; unparseable over all pairs in the row.

## Judges

### Prose readbacks

| Judge | Readback author | Misses | Wrong slot | Slot not named | False alarms | Unparseable |
|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | Claude Haiku 5.5 (same) | 0 of 140 (≤2.6%) | 2 of 140 | 0 of 140 (≤2.6%) | 23 of 140 | 0 of 280 (≤1.3%) |
| Claude Haiku 5.5 | GPT-5.4 mini (different) | 0 of 140 (≤2.6%) | 1 of 140 | 0 of 140 (≤2.6%) | 21 of 140 | 0 of 280 (≤1.3%) |
| GPT-5.4 mini | GPT-5.4 mini (same) | 3 of 140 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 2 of 140 | 0 of 280 (≤1.3%) |
| GPT-5.4 mini | Claude Haiku 5.5 (different) | 3 of 140 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 1 of 140 | 0 of 280 (≤1.3%) |
| Claude Sonnet 5.5 | Claude Sonnet 5.5 (same) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |
| Claude Sonnet 5.5 | GPT-5.5 (different) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |
| GPT-5.5 | GPT-5.5 (same) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 1 of 140 | 0 of 280 (≤1.3%) |
| GPT-5.5 | Claude Sonnet 5.5 (different) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |

### RW1 line readbacks

| Judge | Readback author | Misses | Wrong slot | Slot not named | False alarms | Unparseable |
|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | Claude Haiku 5.5 (same) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 11 of 140 | 0 of 280 (≤1.3%) |
| Claude Haiku 5.5 | GPT-5.4 mini (different) | 0 of 140 (≤2.6%) | 1 of 140 | 0 of 140 (≤2.6%) | 15 of 140 | 0 of 280 (≤1.3%) |
| GPT-5.4 mini | GPT-5.4 mini (same) | 3 of 140 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 2 of 280 |
| GPT-5.4 mini | Claude Haiku 5.5 (different) | 3 of 140 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 1 of 280 |
| Claude Sonnet 5.5 | Claude Sonnet 5.5 (same) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |
| Claude Sonnet 5.5 | GPT-5.5 (different) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |
| GPT-5.5 | GPT-5.5 (same) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |
| GPT-5.5 | Claude Sonnet 5.5 (different) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 280 (≤1.3%) |
| Code check (check-rb) | Claude Haiku 5.5 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 19 of 140 | 21 of 140 | – |
| Code check (check-rb) | GPT-5.4 mini | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 2 of 140 | 3 of 140 | – |
| Code check (check-rb) | Claude Sonnet 5.5 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | – |
| Code check (check-rb) | GPT-5.5 | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | 0 of 140 (≤2.6%) | – |

### Misses by planted slot, Prose

| Planted slot | Claude Haiku 5.5 reading Claude Haiku 5.5 | Claude Haiku 5.5 reading GPT-5.4 mini | GPT-5.4 mini reading GPT-5.4 mini | GPT-5.4 mini reading Claude Haiku 5.5 | Claude Sonnet 5.5 reading Claude Sonnet 5.5 | Claude Sonnet 5.5 reading GPT-5.5 | GPT-5.5 reading GPT-5.5 | GPT-5.5 reading Claude Sonnet 5.5 |
|---|---|---|---|---|---|---|---|---|
| supplier | 0 of 20 | 0 of 20 | 3 of 20 | 3 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| invoice | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| amount | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| currency | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| kind | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| account | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| date | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |

### Misses by planted slot, RW1 line

| Planted slot | Claude Haiku 5.5 reading Claude Haiku 5.5 | Claude Haiku 5.5 reading GPT-5.4 mini | GPT-5.4 mini reading GPT-5.4 mini | GPT-5.4 mini reading Claude Haiku 5.5 | Claude Sonnet 5.5 reading Claude Sonnet 5.5 | Claude Sonnet 5.5 reading GPT-5.5 | GPT-5.5 reading GPT-5.5 | GPT-5.5 reading Claude Sonnet 5.5 |
|---|---|---|---|---|---|---|---|---|
| supplier | 0 of 20 | 0 of 20 | 3 of 20 | 3 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| invoice | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| amount | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| currency | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| kind | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| account | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |
| date | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | 0 of 20 |

## Hypotheses

- H1, Claude Haiku 5.5: fails. Prose misses 0 of 280 (≤1.3%).
- H1, GPT-5.4 mini: holds. Prose misses 6 of 280.
- H1, Claude Sonnet 5.5: fails. Prose misses 0 of 280 (≤1.3%).
- H1, GPT-5.5: fails. Prose misses 0 of 280 (≤1.3%).
- H2, Claude Haiku 5.5: not shown. Line misses 0 of 280 (≤1.3%) against prose 0 of 280 (≤1.3%); Fisher one-sided p 1.0, McNemar one-sided p 1.0 (0 pairs missed in prose only, 0 in the line only).
- H2, GPT-5.4 mini: fails. Line misses 6 of 280 against prose 6 of 280; Fisher one-sided p 0.61402, McNemar one-sided p 0.62305 (5 pairs missed in prose only, 5 in the line only).
- H2, Claude Sonnet 5.5: not shown. Line misses 0 of 280 (≤1.3%) against prose 0 of 280 (≤1.3%); Fisher one-sided p 1.0, McNemar one-sided p 1.0 (0 pairs missed in prose only, 0 in the line only).
- H2, GPT-5.5: not shown. Line misses 0 of 280 (≤1.3%) against prose 0 of 280 (≤1.3%); Fisher one-sided p 1.0, McNemar one-sided p 1.0 (0 pairs missed in prose only, 0 in the line only).
- H3, Claude Haiku 5.5: not shown. Same-author misses 0 of 280 (≤1.3%), different-author 0 of 280 (≤1.3%); Fisher two-sided p 1.0, Holm 1.0.
- H3, GPT-5.4 mini: not shown. Same-author misses 6 of 280, different-author 6 of 280; Fisher two-sided p 1.0, Holm 1.0.
- H3, Claude Sonnet 5.5: not shown. Same-author misses 0 of 280 (≤1.3%), different-author 0 of 280 (≤1.3%); Fisher two-sided p 1.0, Holm 1.0.
- H3, GPT-5.5: not shown. Same-author misses 0 of 280 (≤1.3%), different-author 0 of 280 (≤1.3%); Fisher two-sided p 1.0, Holm 1.0.
- H4: fails. Code check misses 0 of 560 (≤0.7%), false alarms 24 of 560.

## The code check on every line readback

| Author | Faulted | Passed (miss) | Refused, planted slot only | Refused, planted and another | Refused, another slot | Refused, no slot named | Clean | Refused (false alarm) | Tiers that refused a clean line |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | 140 | 0 of 140 (≤2.6%) | 121 | 0 | 0 | 19 | 140 | 21 of 140 | {'form': 21} |
| GPT-5.4 mini | 140 | 0 of 140 (≤2.6%) | 138 | 0 | 0 | 2 | 140 | 3 of 140 | {'form': 3} |
| Claude Sonnet 5.5 | 140 | 0 of 140 (≤2.6%) | 140 | 0 | 0 | 0 | 140 | 0 of 140 (≤2.6%) | none |
| GPT-5.5 | 140 | 0 of 140 (≤2.6%) | 140 | 0 | 0 | 0 | 140 | 0 of 140 (≤2.6%) | none |

## Readbacks: what the payer models wrote

| Author | Format | Readbacks | Accepted first time | Accepted on attempt 2 or 3 | Dropped | Line was the whole reply | Problems on rejected attempts |
|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | prose | 280 | 280 | 0 | 0 | – | none |
| Claude Haiku 5.5 | line | 280 | 280 | 0 | 0 | 280 of 280 | none |
| GPT-5.4 mini | prose | 280 | 279 | 1 | 0 | – | supplier 1 |
| GPT-5.4 mini | line | 280 | 279 | 1 | 0 | 280 of 280 | comments 1 |
| Claude Sonnet 5.5 | prose | 280 | 280 | 0 | 0 | – | none |
| Claude Sonnet 5.5 | line | 280 | 280 | 0 | 0 | 280 of 280 | none |
| GPT-5.5 | prose | 280 | 275 | 5 | 0 | – | supplier 5 |
| GPT-5.5 | line | 280 | 280 | 0 | 0 | 280 of 280 | none |

## Cost

| Model | Kind | Calls | Cost | Mean a call | Calls that failed |
|---|---|---|---|---|---|
| GPT-5.4 mini | author | 575 | $0.5815 | $0.00101 | 0 |
| GPT-5.4 mini | judge | 1120 | $1.1627 | $0.00104 | 0 |
| GPT-5.5 | author | 566 | $4.7722 | $0.00843 | 0 |
| GPT-5.5 | judge | 1120 | $7.0651 | $0.00631 | 0 |
| Claude Haiku 5.5 | author | 560 | $0.2626 | $0.00047 | 0 |
| Claude Haiku 5.5 | judge | 1120 | $0.4007 | $0.00036 | 0 |
| Claude Sonnet 5.5 | author | 560 | $4.0790 | $0.00728 | 0 |
| Claude Sonnet 5.5 | judge | 1120 | $6.4501 | $0.00576 | 0 |
| OpenAI, spent | | | $13.5815 | | |
| Claude, at list price | | | $11.1924 | | |
