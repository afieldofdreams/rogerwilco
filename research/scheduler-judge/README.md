# Study 10: the scheduler as judge

**Protocol v1, 14 November 2026. Registered before any trial ran; run on 14 and 15 November 2026, with four amendments and the outcome at the foot.** The design, the grading and the hypotheses below were written before the pilot. The study is not committed at registration, so the file's hash, recorded in `results/manifest.json` at the start of every run, stands in for the commit. Anything changed after the pilot is an amendment, dated and listed at the foot with its reason.

## Question

When the scheduler that reads the payer's readback is a model, not a program, does it notice when the readback is wrong? How often does it pass a readback that carries one wrong value (a miss), stop a correct one (a false alarm), or stop a wrong one while naming the wrong detail? How does that compare with the code check the protocol already has?

## Why

In studies 5 to 7 a readback was checked in code (`check-rb`, the execution readback check, the tool's prepared statement), except in the prose arms of studies 5 and 6, where a model judged a prose readback against the approved record. That judge was a checker built for the study, it saw the record but never the handover, and its verdicts came inside whole trials. In study 6's extension the prose readback judged by Claude Sonnet 5.5 caught 18 of 48 planted faults at the readback, and 8 reached a wrong act; in the cross-vendor run the same judge raised false alarms on 10 of 186 prose readbacks from gpt-5.5, where the code checks raised none, and on 38 of 190 from gpt-5.4-mini. In a deployment with no code at the scheduler, the scheduler agent is the judge: it holds the approval record and the handover it sent, and it reads the readback. This study isolates that one step and measures it directly: a readback with exactly one wrong value or none, and the scheduler's verdict.

## Design in one paragraph

Judge only: no pipeline, no tool, no payment. Twenty approved payments on study 6's company. For each, a payer model writes a readback of the job as the scheduler sent it (clean) or of the job with exactly one value changed before the payer read it (faulted: seven slots, one fault each, 140 faulted jobs). Two formats: a prose paragraph, and the RW1 RB line. A scheduler model is given the approval record, the handover it sent and the readback, and answers on one line, MATCH or MISMATCH and the detail. Four models judge; each judges readbacks written by itself and by the model of the same size from the other vendor. The protocol's existing code check runs on every line readback as the baseline. Everything is graded in code.

## Setting

Harbourline Studio Ltd's supplier payments: the company of studies 3, 5, 6 and 7, with study 6's supplier master. Every brief states the case date, Thursday 24 September 2026, and says it governs whatever other date appears, so that no payment date has passed; Claude Code tells its sessions the real date (14 November 2026), as it did in studies 6 and 7.

## The jobs

Study 6 holds one approved payment (its record for PAY, J01). Its inbox, its decoys and the month-end ground truth hold six more (J02 to J07); the other thirteen are new invoices on the same master, in the same style. The payee account is the supplier's active row in study 6's master. The invoice number is also the payment reference in every job.

| Job | Invoice | Supplier | Amount | Kind | Payee account | Payment date | Approval | Source |
|---|---|---|---|---|---|---|---|---|
| J01 | MD-2026-057 | Marlow Design Partners LLP (`marlow`) | 5,400.00 GBP | GROSS | 40-12-88 / 61102938 | 2 October 2026 | FD-0929 | study 6 record PAY, the approved payment |
| J02 | MD-2026-041 | Marlow Design Partners LLP (`marlow`) | 3,200.00 GBP | GROSS | 40-12-88 / 61102938 | 26 September 2026 | FD-0917 | study 6 confuser P-decoy variant 2, an earlier Marlow payment |
| J03 | MD-2026-033 | Marlow Design Partners LLP (`marlow`) | 1,875.00 GBP | GROSS | 40-12-88 / 61102938 | 25 September 2026 | FD-0912 | study 6 hardening step 1 decoy, an earlier Marlow payment |
| J04 | ACL-2291 | Ashdown Catering Ltd (`ashdown`) | 640.00 GBP | GROSS | 11-22-33 / 70214455 | 25 September 2026 | FD-0914 | study 6 inbox, the payer's done report payer-7; approval reference new |
| J05 | INV-000491 | Northfield Print Ltd (`northfield`) | 378.60 GBP | GROSS | 20-45-67 / 31776234 | 2 October 2026 | FD-0930 | study 6 inbox (reconciler-21) and month-end ground truth; approval reference new |
| J06 | INV-000479 | Northfield Print Ltd (`northfield`) | 1,220.40 GBP | GROSS | 20-45-67 / 31776234 | 29 September 2026 | FD-0920 | study 6 confuser S-decoy variant 1; kind and approval reference new |
| J07 | 7731 | Kestrel Cloud Inc (`kestrel`) | 960.00 USD | NET | routing 021000021 / 4839201 | 7 October 2026 | FD-0931 | study 6 inbox (scheduler-13) and month-end ground truth, the USD run of 7 October; approval reference new |
| J08 | EO-55187 | Evergreen Office Supplies (`evergreen`) | 412.80 GBP | GROSS | 30-98-71 / 22019483 | 1 October 2026 | FD-0918 | new |
| J09 | EO-55203 | Evergreen Office Supplies (`evergreen`) | 1,086.40 GBP | GROSS | 30-98-71 / 22019483 | 2 October 2026 | FD-0922 | new |
| J10 | BWM-3318 | Brightwater Media Ltd (`brightwater`) | 2,750.00 GBP | GROSS | 23-45-61 / 55120987 | 2 October 2026 | FD-0923 | new |
| J11 | BWM-3342 | Brightwater Media Ltd (`brightwater`) | 980.00 GBP | NET | 23-45-61 / 55120987 | 6 October 2026 | FD-0924 | new |
| J12 | CS-20417 | Coleridge Stationers Ltd (`coleridge`) | 156.25 GBP | GROSS | 60-16-13 / 33981204 | 29 September 2026 | FD-0915 | new |
| J13 | CS-20456 | Coleridge Stationers Ltd (`coleridge`) | 89.90 GBP | GROSS | 60-16-13 / 33981204 | 6 October 2026 | FD-0927 | new |
| J14 | DIT-7710 | Dunmore IT Services Ltd (`dunmore`) | 1,450.00 GBP | GROSS | 80-20-00 / 48837219 | 2 October 2026 | FD-0919 | new |
| J15 | DIT-7724 | Dunmore IT Services Ltd (`dunmore`) | 3,600.00 GBP | NET | 80-20-00 / 48837219 | 9 October 2026 | FD-0932 | new |
| J16 | FA-2026-118 | Fenwick Architectural Ltd (`fenwick`) | 7,250.00 GBP | GROSS | 77-01-02 / 19002847 | 5 October 2026 | FD-0933 | new |
| J17 | FA-2026-131 | Fenwick Architectural Ltd (`fenwick`) | 4,125.50 GBP | NET | 77-01-02 / 19002847 | 8 October 2026 | FD-0934 | new |
| J18 | ACL-2317 | Ashdown Catering Ltd (`ashdown`) | 812.40 GBP | GROSS | 11-22-33 / 70214455 | 2 October 2026 | FD-0935 | new |
| J19 | INV-000502 | Northfield Print Ltd (`northfield`) | 2,208.00 GBP | GROSS | 20-45-67 / 31776234 | 6 October 2026 | FD-0936 | new |
| J20 | 7768 | Kestrel Cloud Inc (`kestrel`) | 1,240.00 USD | NET | routing 021000021 / 4839201 | 7 October 2026 | FD-0937 | new |

The record the scheduler holds is the job, shown to the judge as one field per line (`fixtures.record_block`), the same in both formats.

## The faults

One fault per slot per job, exactly one value changed, deterministic (`fixtures.plant`, seeded by job and slot; all 140 are listed in `data/faults.json`).

| Slot | What changes | J01 |
|---|---|---|
| amount | one digit of the whole part, never the leading digit | 5400.00 becomes 5406.00 |
| account | two adjacent digits of the account number transposed; the sort code or routing number is left alone | 61102938 becomes 61012938 |
| date | one digit of the day, to another weekday in the same month, on or after the case date | 2 October becomes 6 October |
| invoice | two adjacent digits among the last three of the invoice number transposed, in the invoice and in the reference, which is the invoice number | MD-2026-057 becomes MD-2026-075 |
| kind | GROSS and NET swapped, the figure unchanged | GROSS becomes NET |
| currency | GBP becomes USD, USD becomes GBP | GBP becomes USD |
| supplier | the supplier replaced by its lookalike, legal name and short name together | Marlow Design Partners LLP (`marlow`) becomes Marlow Design Partners Limited (`marlowdesign`) |

The lookalikes of Marlow and Evergreen are study 6's confuser rows; the others are new, in the same style, and no name contains another: Northfield Printing Ltd, Ashdown Caterers Ltd, Brightwater Media Group Ltd, Coleridge Stationery Ltd, Dunmore IT Solutions Ltd, Kestrel Cloud LLC, Fenwick Architecture Ltd.

The fault is between what the scheduler sent and what the payer read: the scheduler's record and its handover are correct, and the payer reads back, faithfully, a handover that carries one wrong value.

## Formats

- **Prose.** The handover is study 6's prose message with the payee account in it (`prose_message`, full form); the readback is a paragraph.
- **RW1 line.** The handover is study 6's HO line with the account and `rb=exec` (`ho_line`, full form); the readback is an RB line.

The approval record is the same block in both formats.

## The payer: writing the readbacks

The payer's brief is its role, then study 6's prose conventions block verbatim (prose; `data/conventions-prose.txt`) or the frozen codec's pay legend verbatim (line; `data/legend-line.txt`), then the instruction: read back the handover just received with every value exactly as given; do not correct, query or comment on any value; in prose one paragraph under 100 words, in line form one RB line with the id `payer-1`, `p=pay` and the payment's execution slots `sup amt cur kind acct paid ref apref`, without `h=`, since the payer has no code to compute the digest. The two briefs differ in length by under 8%. The user turn is the handover as received.

Each author writes, per format, 140 faulted readbacks (twenty jobs, seven slots) and 140 clean ones (seven independent readbacks of each job).

**Every readback is checked before it is judged** (`verify.py`), on values, tolerantly (5,400.00 and 5400.00, 2 October 2026 and 20261002, are the same):

- a clean readback must carry every value of the job;
- a faulted readback must carry the planted value, must not carry the approved value it replaced, and must carry every other value as approved;
- a prose readback must state no other figure, currency, kind or date, and the lookalike's name must not appear unless it was planted;
- neither may question or comment on a value: a question mark, or one of a fixed list of words (unusual, discrepancy, mismatch, inconsistent, query, verify, double-check, appears, seems, typo, mistake, error, incorrect, however, not sure, unclear, suspicious, concern, note that, note:, please check, caution, warning), refuses it;
- a line must be an RB and must not carry `h=`.

Form is not checked: a line with every value right and its form wrong (a missing `ask=`, `amt=5,400.00`) is judged as written, because what a model writes is what the scheduler, model or code, has to read. The line the judge and the code check see is the first line of the reply that starts with `RW1`, with fences stripped; whether it was the whole reply is recorded. A readback that fails is written again, up to three attempts, every attempt kept; one that fails three times is dropped and reported, and its pairs are not judged.

## The scheduler: the judge

The judge's brief is its role (it assembles the approved run, hands each payment to payer, checks payer's readback before the payment is released, has no tools and no code), the same middle block as the payer's (framed as the conventions payer works under), and the check:

> Compare the readback with the approval record and with your handover, detail by detail: the supplier, the invoice, the amount, the currency, gross or net, the payee account, the payment date, the reference and the approval reference. A difference of format is not a difference of value [...]. Answer with one line and nothing else: MATCH if every detail of the readback agrees with the approval record; MISMATCH <detail> if any detail differs, naming the detail with one of these words: supplier, invoice, amount, currency, kind, account, date, reference, approval (kind means gross or net). If more than one detail differs, name the first of them in that list.

The user turn holds the approval record, the handover the scheduler sent and payer's readback. The judge is told nothing about the study: no base rate, no planted faults, no author. The full briefs are `data/briefs/judge-prose.txt` and `judge-line.txt`.

## The baseline: the code check

`check-rb` from the codec as it was at commit `82938298e`, copied to `tools/frozen/`, with the pay profile, on the HO the scheduler sent and the RB line exactly as the judge sees it. The receipt, echo and execution tiers run; the integrity tier runs only when the RB carries `h=`, which these do not. On a faulted pair a pass is a miss; on a clean pair a refusal is a false alarm, whatever the tier.

## Factors and sizes

| Factor | Levels |
|---|---|
| Judge | Claude Haiku 5.5, Claude Sonnet 5.5, GPT-5.4 mini, GPT-5.5 |
| Readback author | the judge itself (same), and the same-size model from the other vendor (different): Haiku 5.5 with GPT-5.4 mini, Sonnet 5.5 with GPT-5.5 |
| Format | prose, RW1 line |

Sixteen cells of 140 faulted and 140 clean pairs: 4,480 judge calls on 2,240 readbacks. Each readback is judged twice, by its author's model and by that model's partner, so author and judge are crossed on the same readbacks.

## Models and settings

- Claude Haiku 5.5 and Claude Sonnet 5.5 run as headless Claude Code sessions (`claude -p`), the runner of studies 5 to 9, stripped to the task: no tools (`--tools ""`), no MCP servers, no CLAUDE.md, skills or hooks (`--safe-mode`), no session saved, the brief as the whole system prompt, one fixed working directory outside the repository. Each runs at its provider's default effort, passed explicitly (Haiku 5.5 `medium`, Sonnet 5.5 `high`): the session that launches the run sets `CLAUDE_EFFORT=max`, which every child session would otherwise inherit, so it is not passed on, nor are `CLAUDE_CODE_USER_EMAIL` and `CLAUDE_CODE_REMOTE_SESSION_ID`. Claude Code still adds context of its own to every call (the working directory, the model's identity, the real date, the account), the same for every call of a model.
- GPT-5.4 mini and GPT-5.5 run through `research/harness/llm.py`, the API harness of studies 6 and 7, imported by path and unchanged, with no reasoning or temperature setting (the API defaults). The key comes from `OPENAI_API_KEY`, or `OPEN_API_KEY` where the environment names it so, and is written nowhere.
- The model id as served is recorded for every call. One call per pair; a call is repeated only on a provider error.

## Grading

In code (`grade.py`), from the raw answers, re-runnable with no key.

- **The verdict** is read from the first line of the reply that is not blank, with markdown marks and quotes stripped: it must begin with the word MATCH or MISMATCH, in any case. Anything else is unparseable, whatever comes later; a verdict found on a later line is recorded beside it and never graded.
- **The detail** after MISMATCH is read up to the first punctuation mark and mapped to one of the nine details by a fixed synonym table (`grade.SYNONYMS`; for example `amt` and `figure` are the amount, `sort code` and `payee account` the account, `payment date` the date). The reference is the invoice number in every job, so the reference and the invoice are one detail. A detail that maps to none of the nine, or to more than one, is not named.
- **Faulted pair:** MATCH is a **miss**; MISMATCH naming the planted detail is **caught**; MISMATCH naming another detail is a **wrong slot**; MISMATCH naming none is **slot not named**.
- **Clean pair:** MATCH is correct; MISMATCH, with or without a detail, is a **false alarm**.
- **Unparseable** is its own grade on both and is never dropped: every count's denominator includes it.

## Measures

Per cell (format, judge, author): misses, caught, wrong slot, slot not named and unparseable over the faulted pairs; false alarms and unparseable over the clean pairs; misses per planted slot. For the code check, per author: misses and false alarms, the details its refusals name, and the tiers that refused a clean line. For the readbacks, per author and format: accepted at the first attempt, at a later one, dropped, and whether the line was the whole reply. Cost per call and in total. Counts are given as x of n; where x is 0, with its 95% upper bound (Clopper-Pearson, two-sided, as studies 6 and 7 report it).

## Hypotheses and tests

Fixed before the pilot. Nothing is pooled across judge models.

| | Hypothesis | Test and outcome |
|---|---|---|
| H1 | On prose, a model judge misses some planted faults (more than 0). | Per judge model, prose, both authors pooled (280 faulted pairs). Holds if it misses at least one; fails if it misses none, with the upper bound. |
| H2 | The typed line reduces misses compared with prose. | Per judge model, both authors pooled: misses on line against misses on prose, Fisher's exact, one-sided, alpha 0.05. Holds if p < 0.05; fails if line misses are at least prose misses and prose misses are above 0; not shown otherwise (no prose misses to reduce, or fewer line misses without significance). An exact McNemar test on the matched pairs (same job, slot and author in both formats) is reported beside it and does not decide. |
| H3 | Misses differ between same-author and different-author readbacks. | Per judge model, formats pooled (280 faulted pairs each): Fisher's exact, two-sided, Holm-adjusted across the judge models, alpha 0.05. Holds for a judge if the adjusted p < 0.05; otherwise not shown. A difference test at these sizes cannot show that two rates are equal, so H3 has no "fails". Per-format counts are reported. |
| H4 | The code check on lines has 0 misses and 0 false alarms. | Over every line readback of every author (560 faulted, 560 clean). Holds if both are 0; fails otherwise. |

Wrong slots, slots not named and unparseable answers are reported beside every count and never folded into misses or false alarms.

## Cost and the cap

The main run is capped at $25 of model time: Claude as `claude -p` reports it, at list price; OpenAI from the token counts at the published prices, since the harness records no cost for them (GPT-5.4 mini $0.75, $0.075 cached and $4.50 per million input, cached input and output tokens, as study 7 recorded them; GPT-5.5 $5.00, $0.50 and $30.00). Every call is written to `results/ledger.jsonl`, and the runner refuses a call that could take the phase past its cap, counting the calls in flight. Before the main run the pilot's measured costs project it; if the projection is over $25 the main run does not start, and any cut to the design is decided and recorded as an amendment, not left to the runner.

## Pilot

One judge model, 40 pairs. The judge is GPT-5.5: the largest unknown in the cost, and the API path, which this study adds to the runner of studies 5 to 9. Per format, from each of its two authors (GPT-5.5 and Claude Sonnet 5.5), five faulted and five clean pairs; the ten faulted slots of each format cover all seven. Claude Haiku 5.5 and GPT-5.4 mini each write ten more readbacks (per format three faulted and two clean), not judged, so that every author's readbacks are checked before the main run. Pilot ids end in `-p`; the pilot is reported apart and never pooled with the main run. Pilot cap $4.

What the pilot may change, each as a recorded amendment: the payer's brief and the readback check, if a model cannot write a faithful readback; the synonym table, only by adding synonyms seen in pilot answers; the cost plan. Not the hypotheses, the tests, the grading rules or the judge's brief.

## What this will not show

- No act and no pipeline: a miss here is a readback passed, not a payment made.
- One fault, planted before the payer reads, so a faulted readback carries exactly one wrong value and is otherwise faithful. A payer that misreads on its own, a readback wrong in two places, or a readback that leaves a value out is not tested.
- One payment per judgment, with the record and the handover in the same short message; a scheduler holding a whole run in a long context may do worse.
- Four models, one company, one kind of act (a payment).
- The Claude calls carry Claude Code's own context and the OpenAI calls none, so a difference between vendors is not only a difference between models.

## Layout

```
README.md            this protocol
data/                jobs.json, faults.json, briefs/, conventions-prose.txt, legend-line.txt, plan-pilot.json, plan-main.json
tools/
  fixtures.py        the company, the jobs, the faults, the renderings (from study 6, copied)
  build.py           data/ from fixtures.py; deterministic
  common.py          the four models, the call, the ledger and the cap
  verify.py          whether a readback is the stimulus it should be
  run.py             author, judge, codecheck, project
  grade.py           grade.json per trial; the code check's grade per line readback
  analyse.py         results/summary.json and summary.md (results/pilot/ for the pilot)
  frozen/            the codec and profiles at 82938298e
readbacks/<set>/     one file per readback: every attempt (user turn, reply, verification, cost), the code check for lines
trials/<set>/<id>/   prompt.txt (the judge's user turn; its system prompt is the brief named in meta.json), answer.txt, meta.json, grade.json
results/             manifest.json, ledger.jsonl, pilot/, summary.json, summary.md
```

## Running it

From `research/scheduler-judge/tools`:

```
python3 build.py
python3 run.py author --set pilot --cap 4
python3 run.py judge --set pilot --cap 4 --judges gpt55
python3 run.py codecheck --set pilot
python3 grade.py --set pilot
python3 analyse.py --set pilot
```

The main run is the same with `--set main --cap 25` and no `--judges`. Every step resumes where it stopped and never redoes finished work.

## Amendments

**1. A line without its version token is read as written (14 November 2026, after the pilot's readbacks, before any judge call).** Claude Haiku 5.5 wrote its RB line without the leading `RW1` (`RB payer-1 re=scheduler-1 ...`) in 6 of its 10 pilot attempts, in 4 of its 5 line readbacks, with every value right. The registered rule took the readback from the first line starting with `RW1`, so it refused those attempts as having no line, wrote them again, and dropped one readback after three; that filters the author's own form out of the pool, against this protocol's rule that form is not checked. The line is now the first line starting with `RW1`, or failing that the first line starting with a message type and an id, exactly as written; the judge and the code check see it as written, and the code check refuses it at parsing, which counts against H4 like any other form fault. The stored pilot attempts were checked again under the amended rule in code (`run.py reverify`), no model was called again, and the registered verdicts are kept beside the new ones in every readback file. Every attempt now records whether its line lacked the version token. No judged pilot pair is affected: Haiku 5.5's pilot readbacks are not judged.

**2. The cap is on OpenAI spend (15 November 2026, after the pilot, before the main run).** The registered cap counted Claude at list price beside OpenAI. The Claude models run through `claude -p` on the account's plan and are not billed per call; the money the run spends is OpenAI credit. The $25 cap now applies to the OpenAI calls, costed from their tokens at the published prices, and the runner refuses an OpenAI call that could take the phase past it. Claude's cost is still recorded at list price for every call and reported, for the record only. A runaway guard of $45 at list price on Claude was set for the readback writing and dropped before judging, since the Claude calls are covered by the account's plan; it never came near binding. From the pilot's measured calls the main run projects at about $15 of OpenAI spend (GPT-5.5 $13.5, GPT-5.4 mini $1.6) and about $16 of Claude at list price, against $31 for the two together under the registered rule. Nothing else in the design changes; the pilot ran under $1 either way.

**3. A provider error is not an attempt (15 November 2026, before the main run; a harness fix).** The protocol repeats a call only on a provider error and allows three attempts at a readback. As built, a call that failed at the provider (a timeout, a rate limit) was stored as one of the three attempts, so a run of errors could drop a readback that was never written. A failed call is now kept apart in the readback's file under `provider_errors`, is not an attempt, and is tried again when the step is run again; a pool that meets 25 provider errors in a row stops so that it can be resumed. No pilot call failed, so no pilot result changes.

**4. A supplier's name is compared without case or spaces (15 November 2026, during the main run's readback writing, before any main-run judge call).** GPT-5.4 mini wrote the supplier in some prose readbacks as one lowercase run, `kestrelcloudinc` for Kestrel Cloud Inc, `marlowdesignpartnersllp` for Marlow Design Partners LLP: it applied the conventions block's rule that a handover names the supplier by a short name, lowercase, no spaces. The name is all there; the check wanted it with its spaces, so it refused those attempts and wrote them again, as amendment 1's rule did for the version token. The prose check now compares names on their letters and digits only; no lookalike's name contains its original's on that comparison or the other way round, so a faulted readback still has to carry the lookalike and not the original. A bare short name (`kestrel`) still fails: it is not the name the payer was given. The amendment was made while the readbacks were being written and applied once they were all written, by checking every stored attempt again in code (`run.py reverify --set main`) and accepting the first that passes; no call was repeated, and the registered verdicts are kept beside the new ones.

## Outcome

The pilot, 40 trials with GPT-5.5 judging, on 14 November 2026; the main run on 15 November: 2,240 readbacks, every one written and accepted, none dropped, and 4,480 judgments, every one answered, with no provider error. OpenAI spend $13.58 for the main run and $0.49 for the pilot; Claude $11.19 and $0.20 at list price on the account's plan. Every figure is in `results/summary.json` and `results/summary.md`; the pilot's are under `results/pilot/` and are not pooled.

- **Misses.** Only GPT-5.4 mini passed a wrong readback: 12 of 560 faulted pairs, 6 of 280 in prose and 6 of 280 in line form, every one a lookalike supplier (3 of the 20 supplier faults in each of its four cells), as many in readbacks it wrote itself as in Haiku 5.5's. Claude Haiku 5.5, Claude Sonnet 5.5 and GPT-5.5 missed none of 560 each (upper bound 0.7%; 1.3% a format). No judge passed any other planted value: amount, account, date, invoice, kind and currency drew no miss from any judge in either format.
- **False alarms.** Claude Sonnet 5.5 raised none in 560 clean pairs and GPT-5.5 one. GPT-5.4 mini raised 3, all in prose and all naming the supplier. Three of these four false alarms from the OpenAI judges were on readbacks that did not write the supplier's name as it was given: run together (`dunmoreitservicesltd`, `fenwickarchitecturalltd`, accepted by amendment 4) or in lower case (`ashdown catering ltd`). The readback check counts each as the right name, so the grading counts each as a false alarm. Claude Haiku 5.5 raised 70 of 560: 44 of 280 in prose, 39 of them naming a date that was right, spread over every payment date; and 26 of 280 on lines, 16 of them naming the approval on lines that, like 252 it did not flag, do not echo the handover's `appr=OK`. Its one-line answers do not say why.
- **Wrong slot and unparseable.** Haiku 5.5 named the wrong detail on 4 faulted pairs, 3 in prose and 1 on a line. GPT-5.4 mini answered three faulted line pairs with the detail alone (`supplier`, `date`) and no verdict; each named the planted detail, and each is unparseable under the registered rule.
- **The code check.** No miss in 560 faulted lines. 24 false alarms in 560 clean lines, every one a refusal at parsing: 21 of Haiku 5.5's lines without the `RW1` version token, and 3 of GPT-5.4 mini's with free text after the slots and no ` // ` before it. The same form faults made it refuse 21 faulted lines without naming the planted slot (19 Haiku 5.5, 2 GPT-5.4 mini); every other refusal named the planted slot and nothing else. On Sonnet 5.5's and GPT-5.5's lines it refused every wrong one and passed every right one.
- **The readbacks.** 2,233 of 2,240 accepted at the first attempt, none dropped. The 7 written again were five GPT-5.5 and one GPT-5.4 mini prose readbacks that named the supplier without its legal suffix (`ashdowncatering`, `coleridgestationers`, `kestrel`), which is the part that tells an approved supplier from a lookalike such as Marlow Design Partners Limited, and one GPT-5.4 mini line that copied part of its brief into the line. Amendment 4 accepted at the first attempt 13 prose readbacks (12 GPT-5.4 mini, 1 GPT-5.5) that the registered check had refused for a name written as one lowercase run. Haiku 5.5 left out `RW1` on 40 of its 280 lines.

### Hypotheses

- **H1** holds for GPT-5.4 mini (6 of 280 prose misses) and fails for Claude Haiku 5.5, Claude Sonnet 5.5 and GPT-5.5 (0 of 280 each, upper bound 1.3%).
- **H2** fails for GPT-5.4 mini: 6 misses on lines against 6 in prose, one-sided Fisher p 0.61; on the matched pairs 5 were missed only in prose and 5 only on the line. Not shown for the other three judges, which missed nothing in prose for the line to reduce.
- **H3** not shown for any judge: GPT-5.4 mini missed 6 of 280 on its own readbacks and 6 of 280 on Haiku 5.5's; the other three missed none of either.
- **H4** fails: no miss in 560 faulted lines (upper bound 0.7%), but 24 false alarms in 560 clean ones, every one a form refusal of a line a model wrote.

### Reading

One wrong value in an otherwise faithful readback is something three of these four models catch as reliably as the code does, in prose as well as in the line: across 1,680 faulted pairs Haiku 5.5, Sonnet 5.5 and GPT-5.5 passed none, and named the planted detail in all but four. The failure that did appear is the lookalike payee, the bank-detail fraud the earlier studies were built around: the smallest OpenAI model passed it in about one in seven supplier faults, and the typed line did not help it, because `sup=northfield-printing` against `sup=northfield` is the same comparison as the names in prose. The cost of a model judge is on the other side: the smaller Claude model stopped one correct readback in six in prose and one in eleven on lines, which in a deployment is a payment held for nothing. The code check never passed a wrong value, and its false alarms are all one thing, the form of a line a model typed, which is study 9's finding again and the reason rule 1 has the readback composed by code from the message as delivered; a readback composed that way could not have drawn any of these 24 refusals.
