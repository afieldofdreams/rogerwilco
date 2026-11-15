# Study 10, the scheduler as judge: pilot

40 of 40 planned trials graded. Cost: OpenAI $0.49, the money the run spent, from tokens at published prices; Claude $0.20 at list price as `claude -p` reports it, run on the account's plan. Counts are x of n; a zero carries its 95% upper bound. Misses, wrong slot and slot not named are over faulted pairs; false alarms over clean pairs; unparseable over all pairs in the row.

## Judges

### Prose readbacks

| Judge | Readback author | Misses | Wrong slot | Slot not named | False alarms | Unparseable |
|---|---|---|---|---|---|---|
| GPT-5.5 | GPT-5.5 (same) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 10 (≤30.9%) |
| GPT-5.5 | Claude Sonnet 5.5 (different) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 10 (≤30.9%) |

### RW1 line readbacks

| Judge | Readback author | Misses | Wrong slot | Slot not named | False alarms | Unparseable |
|---|---|---|---|---|---|---|
| GPT-5.5 | GPT-5.5 (same) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 10 (≤30.9%) |
| GPT-5.5 | Claude Sonnet 5.5 (different) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 10 (≤30.9%) |
| Code check (check-rb) | Claude Haiku 5.5 | 0 of 3 (≤70.8%) | 0 of 3 (≤70.8%) | 3 of 3 | 1 of 2 | – |
| Code check (check-rb) | GPT-5.4 mini | 0 of 3 (≤70.8%) | 0 of 3 (≤70.8%) | 0 of 3 (≤70.8%) | 0 of 2 (≤84.2%) | – |
| Code check (check-rb) | Claude Sonnet 5.5 | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | – |
| Code check (check-rb) | GPT-5.5 | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | 0 of 5 (≤52.2%) | – |

### Misses by planted slot, Prose

| Planted slot | GPT-5.5 reading GPT-5.5 | GPT-5.5 reading Claude Sonnet 5.5 |
|---|---|---|
| supplier | 0 of 1 | 0 of 0 |
| invoice | 0 of 1 | 0 of 1 |
| amount | 0 of 0 | 0 of 2 |
| currency | 0 of 1 | 0 of 0 |
| kind | 0 of 0 | 0 of 1 |
| account | 0 of 1 | 0 of 1 |
| date | 0 of 1 | 0 of 0 |

### Misses by planted slot, RW1 line

| Planted slot | GPT-5.5 reading GPT-5.5 | GPT-5.5 reading Claude Sonnet 5.5 |
|---|---|---|
| supplier | 0 of 0 | 0 of 1 |
| invoice | 0 of 0 | 0 of 2 |
| amount | 0 of 0 | 0 of 1 |
| currency | 0 of 2 | 0 of 0 |
| kind | 0 of 2 | 0 of 0 |
| account | 0 of 1 | 0 of 0 |
| date | 0 of 0 | 0 of 1 |

## The code check on every line readback

| Author | Faulted | Passed (miss) | Refused, planted slot only | Refused, planted and another | Refused, another slot | Refused, no slot named | Clean | Refused (false alarm) | Tiers that refused a clean line |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | 3 | 0 of 3 (≤70.8%) | 0 | 0 | 0 | 3 | 2 | 1 of 2 | {'form': 1} |
| GPT-5.4 mini | 3 | 0 of 3 (≤70.8%) | 3 | 0 | 0 | 0 | 2 | 0 of 2 (≤84.2%) | none |
| Claude Sonnet 5.5 | 5 | 0 of 5 (≤52.2%) | 5 | 0 | 0 | 0 | 5 | 0 of 5 (≤52.2%) | none |
| GPT-5.5 | 5 | 0 of 5 (≤52.2%) | 5 | 0 | 0 | 0 | 5 | 0 of 5 (≤52.2%) | none |

## Readbacks: what the payer models wrote

| Author | Format | Readbacks | Accepted first time | Accepted on attempt 2 or 3 | Dropped | Line was the whole reply | Problems on rejected attempts |
|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | prose | 5 | 5 | 0 | 0 | – | none |
| Claude Haiku 5.5 | line | 5 | 5 | 0 | 0 | 5 of 5 | none |
| GPT-5.4 mini | prose | 5 | 5 | 0 | 0 | – | none |
| GPT-5.4 mini | line | 5 | 5 | 0 | 0 | 5 of 5 | none |
| Claude Sonnet 5.5 | prose | 10 | 10 | 0 | 0 | – | none |
| Claude Sonnet 5.5 | line | 10 | 10 | 0 | 0 | 10 of 10 | none |
| GPT-5.5 | prose | 10 | 10 | 0 | 0 | – | none |
| GPT-5.5 | line | 10 | 10 | 0 | 0 | 10 of 10 | none |

## Cost

| Model | Kind | Calls | Cost | Mean a call | Calls that failed |
|---|---|---|---|---|---|
| GPT-5.4 mini | author | 10 | $0.0104 | $0.00104 | 0 |
| GPT-5.5 | author | 20 | $0.1786 | $0.00893 | 0 |
| GPT-5.5 | judge | 40 | $0.3046 | $0.00761 | 0 |
| Claude Haiku 5.5 | author | 15 | $0.0078 | $0.00052 | 0 |
| Claude Sonnet 5.5 | author | 20 | $0.1930 | $0.00965 | 0 |
| OpenAI, spent | | | $0.4936 | | |
| Claude, at list price | | | $0.2008 | | |

## The main run's projected cost

| Model | Readbacks | Attempts a readback | Author cost | Judgments | Judge call | How | Judge cost |
|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 | 560 | 1.5 | $0.44 | 1120 | $0.00044 | estimated (author mean x 0.85) | $0.50 |
| GPT-5.4 mini | 560 | 1.0 | $0.58 | 1120 | $0.00089 | estimated (author mean x 0.85) | $1.00 |
| Claude Sonnet 5.5 | 560 | 1.0 | $5.41 | 1120 | $0.00823 | estimated (author mean x 0.85) | $9.22 |
| GPT-5.5 | 560 | 1.0 | $5.00 | 1120 | $0.00761 | measured | $8.53 |

Projected total: $30.67 against the $25 cap.
