# Study 8: the relay

Protocol, written before anything was built, 22 October 2026. Status: not yet run. This file is the pre-registration; it is frozen at the commit recorded in `results/manifest.json` when the main run starts.

## The question

When a handover passes through agents that do not act on it before it reaches the one that does, how much of it arrives, where it is lost, and does a typed line checked at every hop stop the loss, at what cost in tokens and turns?

## Why an eighth study

Every study so far is one edge: a sender, a receiver, an act. Agent systems are graphs. A planner hands to a coordinator, the coordinator to a desk, the desk to the agent that holds the tool, and each agent restates the instruction for the next. Studies 6 and 7 placed the faults on a single edge: the sender's draft and the tool, with the receiver's own reading null on strong models. A relay is a receiver that becomes a sender, so every hop is another draft. If the drafting locus is where faults enter, a chain of N hops has N drafting loci, and the question is whether anything carries the instruction intact across them without a check at each one.

The protocol's answer is already in the spec: an HO before an irreversible act is built from the record by code or checked against it before it goes (`check-ho`), and every receiver reads back what it received. For a relay the record is the handover it received. This study measures what that costs and what it prevents, against agents passing the same instruction on in prose.

## Setting

Harbourline Studio Ltd, the same company, acts, approval record, supplier master and execution rules as study 6 (`research/plan-readback`). Today is Friday 2 October 2026. Three acts: PAY (Marlow, 5400.00 GBP gross, account on file, 2 Oct, ref MD-2026-057, approval FD-0929), CHGBANK (Evergreen to 60-83-71/44019482 from 3 Oct, approval FD-0926), SEND (the remittance advice for MD-2026-057 to Marlow's billing contact).

**The chain.** Hop 0 is the scheduler, which is code: it writes the first message from the record, as study 6's sender did. Then K relay agents, each a model, and last the payer, a model that executes through the act tool. The main design has K = 2: `coordinator`, then `desk`, then `payer`. A length sweep runs K = 1, 2, 3 and 5.

Each relay has a reason to touch the message, so that a relay is a draft and not a copy:

| relay | its own context | what it adds |
|---|---|---|
| coordinator | the run schedule: a list of payment runs with dates and priorities | the deadline (`due`) and priority (`pri`) for the act, read from the schedule |
| desk | the approvals log: the FD's approval references with the item each covers | confirms the approval reference covers this item and marks the handover approved (`appr=OK`); where the log does not cover it, asks instead of forwarding |
| any further relay in the sweep | routine traffic only | passes the handover on with nothing to add |

Every relay has an inbox with eight to twelve messages of routine traffic as study 6's base inbox, with the live handover never last. The payer has study 6's clean master and inbox for the act.

**What the first message carries.** The record's business content and nothing the payer should resolve for itself, as in study 6 block 2: for PAY `sup amt cur kind paid ref apref`, no account; for CHGBANK `sup acct eff apref`; for SEND `sup amt cur paid ref`, no address. The payee account and the address come from the payer's master. The coordinator adds `due` and `pri`; the desk adds `appr=OK`.

## Arms

Every arm has the same agents, inboxes, master, execution rules and act tool. The briefs differ only in the message form and in what a relay does before it forwards. Each relay's brief is the same length within 10% across arms (the prose arms carry a prose rendering of the legend, as study 6's did).

| arm | message form | what a relay does | what the payer does |
|---|---|---|---|
| F, free prose | plain English, no instruction about shape | reads, adds its part, writes the next message in its own words | acts, done note in prose |
| A, disciplined prose | plain English under the seven conventions (facts once, state by delta, no preamble) | as F, under the conventions | as F |
| L, lines | RW1 lines, pay profile, validated with the codec | writes the forwarded HO, validates it, sends it | acts, DN with the executed values |
| R, lines checked at every hop | RW1 lines | reads back the HO it received (`make-rb`, checked by the previous hop's code with `check-rb`); writes the forwarded HO; the harness checks it against the HO received (`check-ho`, the received HO's slots as the record) before it is delivered; a failure returns it to the relay once with the slot named; a second failure holds the chain | reads back the HO (`make-rb`), checked by code; acts after `AN val=Y`; DN checked against the first message with `check-dn` |

L separates the form from the checks: if L matches R, the line alone carries the instruction; if R beats L, the checks do the work. F against A separates the discipline from the form, as study 6's extension did on one edge.

In R the forwarded HO must carry every slot the received HO carried, with the same decoded values, plus the relay's addition; `check-ho` refuses a dropped slot, a changed value, or a slot added that the relay's role does not name. The relay's addition is checked against the relay's own context (the schedule, the log) by the same code.

## Blocks

**Block 1, clean.** The record is correct, every context clean. Three acts, five clean contexts per act (study 6's, with the relay contexts generated to match in size), three repeats. What it measures is loss from relaying alone: a field dropped, a value changed, a payer that acts, asks or stalls, and the size of each message.

**Block 2, a confuser at a relay.** The record is correct. One relay's own context holds something built to make a careless relay forward the wrong thing: for the coordinator, a second live handover for the same supplier with other figures in its inbox, or a run schedule with two runs close in date; for the desk, an approvals log that holds a near reference (FD-0928 covering another Marlow invoice) beside the right one, or an entry that covers the supplier but not this item. Four confusers per act, each at one relay, three repeats. The correct chain forwards the record's values; a desk whose log does not cover the item asks.

**Block 3, the sweep.** Clean context 1 for each act, K = 1, 2, 3 and 5 relays, arms F and R, three repeats. The relays beyond the desk pass the message on with nothing to add. What it measures is loss and size against hop count.

## Receivers

Claude Haiku 5.5 and Claude Haiku 4.5, through the headless runner. Haiku 5.5 is the receiver studies 6 and 7 showed null at the receiver's locus; Haiku 4.5 is the weakest receiver to hand and stands for a mixed fleet where relays are smaller models than the one that acts. Every agent in a chain runs on the same model. Claude Sonnet 5.5 is an extension on block 1, one repeat, if budget allows, and is reported apart.

## Measures

Per chain, graded in code from the messages as sent and the act as executed:

| measure | definition |
|---|---|
| act | correct (matches the record on every field), wrong (the fields named), asked (the payer asked instead), not done (the chain stalled or was held) |
| coverage at hop k | which of the record's fields the message delivered to hop k carries. For a line, by parse. For prose, by normalised match: the amount's digits, the account's digits, the date in any of its forms, the reference, the approval reference, the supplier's short or legal name, the currency, the kind. A field is carried when its value appears; a field whose value appears altered counts as drift, not coverage |
| drift at hop k | a record field present in the message at hop k with a value that differs from the record, where the message at hop k-1 carried it correctly |
| caught at hop k | arm R only: `check-ho` refused the forwarded line, or `check-rb` refused the readback, at hop k, and the chain went on correctly or was held |
| false alarm | arm R only: a refusal where the forwarded line carried every received slot with the record's values and a correct addition |
| size at hop k | tokens (tiktoken o200k_base, as study 6 counted) of the message delivered to hop k |
| traffic | tokens of every message between agents in the chain, readbacks and re-issues included |
| turns, cost | model turns per chain, cost as the runner reports it |

Per cell (block, arm, model, and K in block 3): the proportion of chains with a correct act, with every record field carried to the payer, with any drift; false alarms over correct forwards; median size at each hop; median traffic. Every proportion with its 95% Clopper-Pearson interval.

## Hypotheses and tests

Fixed before the pilot. Tests are per model; nothing is pooled across models.

| | hypothesis | test |
|---|---|---|
| H1, primary | In block 1, more chains end in a correct act in R than in F | Fisher's exact, one-sided, per model, alpha 0.05 |
| H2 | In block 1, every record field reaches the payer in more chains in R than in F | Fisher's exact, one-sided, per model |
| H3 | Message size at hop k is flat in L and R and grows with k in F and A | median size per hop reported; the sign of the difference between hop 1 and hop K+1 per arm |
| H4 | R's checks raise no false alarm: the upper bound on false alarms over correct forwards is under 5% per model | needs 0 of 60 or more; Clopper-Pearson |
| H5 | Drift (a value changed at a relay from a clean source) is rare on both models in every arm; where it occurs in R it is caught | counts with intervals; every drift named by chain and hop |
| H6 | In block 2, more chains end in a correct act in R than in F | Fisher's exact, one-sided, per model |
| H7 | In block 3, the correct-act proportion falls with K in F and not in R | proportions per K with intervals; no test |
| H8, secondary | L is not separable from R on H1 and H2 on Haiku 5.5, and R beats L on Haiku 4.5 | Fisher's exact, two-sided |

A result that does not reach significance is reported as such with its interval. The headline on the results page is the block-1 correct-act proportion per arm per model with its interval, and the size per hop beside it.

## Sizing

| block | chains per model | sessions per chain | arms | models | chains |
|---|---|---|---|---|---|
| 1 | 3 acts x 5 contexts x 3 repeats = 45 per arm | 3 (R: 3 plus re-issues) | 4 | 2 | 360 |
| 2 | 3 acts x 4 confusers x 3 repeats = 36 per arm | 3 | 4 | 2 | 288 |
| 3 | 3 acts x 4 lengths x 3 repeats = 36 per arm | 2 to 6 | 2 | 2 | 144 |

792 chains, about 2,700 model sessions. At study 7's Haiku rates ($0.006 to $0.02 a session) about $40 in all. At eight sessions in parallel, one night. The minimum version, if it has to shrink: block 1 and block 3 on Haiku 5.5 only, about 250 chains.

## Pilot and manipulation check

Before the main run: block 1, arms F and R, PAY and CHGBANK, two clean contexts, one repeat, on Haiku 5.5 (8 chains), then the same on Haiku 4.5. Gates: every R chain reaches the act or a named hold without a harness fault; and arm F shows loss, a field missing at the payer or a payer that asks or stalls, in at least 10% of its chains on at least one model. If it does not, the hardening ladder is applied one step at a time and the pilot re-run, every step reported: (1) each relay's inbox carries two other live handovers for other suppliers, so the relay must pick; (2) each relay's brief says the next agent is busy and asks for a short message. The ladder is the whole list. If F shows no loss at the top of the ladder, the study runs as built and reports bounds, as study 6's block 2 did.

## Freeze

The codec and the pay profile are copied into `tools/frozen/` from the commit the manifest names; every check loads the copy and every brief names the copy's path. The tools, data and this protocol are frozen at one commit before the main run.

## Exclusions and amendments

A chain that ends in a runner error (timeout, no JSON, provider error) is re-run once under a new repeat id; both are kept and the first excluded with the reason. A harness bug found during the main run stops the run; the fix is committed, the freeze moves, and every block the bug could have touched is re-run. No hand overrides of grades; a dispute goes in `results/disputes.json` and the code's grade stands. Amendments before the freeze, after the freeze and in the analysis are recorded here under their own headings, dated, as studies 6 and 7 recorded theirs.

## Validity

- The graders are validated before any result is read: a blind second reading of 5% of chains on act, coverage at the payer and drift. Agreement is reported.
- Every relay sees routine traffic, so a relay cannot find the handover by its being alone.
- Dates are stated in every brief.
- Every figure on the results page is read from `results/summary.json` by `tools/report.py` and `app/tests` asserts the page matches.
- Nothing in the data is real.

## What this will not show

- One company, three acts, relays that add one thing each. A relay that must translate between vocabularies, or summarise, is not tested.
- Two Claude models. The relay is the place a mixed fleet puts its smallest models, and the cross-vendor run waits on a key as study 6's did.
- The check at each hop needs a sender with code. A relay without a shell cannot run `check-ho`; the study measures the control where it can run.

## What follows for the protocol

Decided now:

- If H1 and H4 hold: the skill and the spec say a relay checks the handover it forwards against the one it received, as the sender checks against the record, and `check-ho` documents the received HO as a record.
- If H3 holds and H1 does not: the line's claim on a chain is cost, not correctness, and the site says so.
- If H8 holds on Haiku 5.5 and fails on Haiku 4.5: the check at every hop is for mixed fleets, and the spec says where it is required.
- If H1 fails: a relay on these models carries an instruction intact in prose, and the study is reported as a bound.

## Layout

```
README.md                 this protocol
data/
  briefs/                 <arm>-<role>-<act>.txt, written by tools/briefs.py
  execution_policy.md     the payer's rules, study 6's
tools/
  common.py               records, contexts, normalisation, token counts (copied from study 6, not imported)
  briefs.py               writes the briefs
  build.py                trials/<id>/ for every block x act x context x arm x model x K x repeat
  act.py                  the act tool: pay, chgbank, send; executes once, prints what it executed
  check.py                hop 0's message; check-ho at each hop in R; check-rb; check-dn; the re-issue
  run.py                  drives each chain as a sequence of headless sessions, one per agent
  grade.py                grade.json per chain
  analyse.py              results/summary.json and summary.md, intervals included
  report.py               results/report.html and the site page from summary.json
trials/<block>-<act>-<context>-<arm>-<model>-k<K>-r<n>/
  hop<k>/                 one folder per agent: inbox, its context, what it wrote
results/                  manifest.json, summary.json, summary.md, report.html, pilot/
```

Trial id example: `B1-PAY-clean-2-R-haiku55-k2-r1`.
