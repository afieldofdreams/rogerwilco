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

## Amendments after the pilot, before the freeze

Recorded on 22 October 2026, after the registered pilot (block 1, F and R, PAY and CHGBANK, two clean contexts, one repeat, Haiku 5.5 then Haiku 4.5; `results/pilot/`) and before any main-run result exists. The pilot passed the R gate (8 of 8 R chains reached a correct act with no refusal, no re-issue and no harness fault) and failed the F gate (0 of 4 F chains on each model lost anything). Each entry says what was seen, what changed and why.

- **The worked example in the relay inboxes is removed.** As built, each relay's inbox carried an earlier handover that had passed through it (the Ashdown payment of 24 September, as received and as the relay forwarded it). The protocol says routine traffic only; the example was a builder's decision it never named, and in every prose chain of the pilot both relays copied the handover paragraph they received verbatim and appended one sentence, which the example invites. The inboxes now hold routine traffic only (nine messages and the live handover at level 0). This restores the design as registered and is not a ladder step; the F pilot is re-run at level 0 without it (suffix `-p1`, both models, eight F chains each: the two acts, two clean contexts, two repeats), and the ladder follows from there if the gate is still not met: step 1 (two other live handovers for other suppliers in each relay's inbox, suffix `-p2`), then step 2 (the relay's brief says the next agent is busy and asks for a short message, suffix `-p3`). R is not re-run at these levels; it runs at whatever level is chosen for the main run. The levels are `RW_HARDEN=0,1,2` in the environment when `build.py` runs, recorded in each chain's `meta.json` and `grade.json`; the level-2 relay briefs carry `-h2` in their file name.
- **Block 2's desk-cover confuser and H6.** In that cell the approvals log holds an entry for the supplier but not for the item, so the correct chain ends with the desk asking; a correct act is not possible. The grade records the expected outcome (`act`, or `ask@2`) and whether the chain ended as expected; a chain that forwards past the desk and acts, or asks elsewhere, is graded wrong. H6 is tested on chains whose outcome is as expected (the correct act, or the ask where the ask is correct), not on correct acts alone; the separate H6a the first analysis carried is dropped.
- **Agent names.** The pay profile's closed agent set did not name the chain's relays. `coordinator` and `desk` were added to the live profile (commit 15bd29ade) and the frozen copy was taken after that. The sweep's further relays use names the profile already held, in this order: hop 3 `auditor`, hop 4 `reconciler`, hop 5 `extractor`. Briefs are per role (coordinator, desk, relay, payer) and do not depend on K; a relay's own name and its neighbours are given in its first user turn.
- **Readback level and the check-ho waiver.** Every HO in the chain asks `rb=all`, as study 6's arm C did: a relay echoes every slot it received and resolves nothing, and `rb=exec` would demand the payee account from a relay that does not hold it. `check-ho` refuses every PAY, CHGBANK or SEND line that does not ask `rb=exec`; the harness waives that one problem and records it as a note on every check. Nothing else of `check-ho` is waived.
- **The record at a relay.** `check-ho` compares a relay's forwarded line with the HO it received, flattened: item, ask, rb, p and every slot with its decoded value, `from=` the relay, `to=` the next agent, plus the relay's permitted addition with the value its own context gives when read by code (the run of the act's kind on the act's date in `schedule.json`; the log entry covering the supplier and the item, under the handover's approval reference where it carries one, in `approvals.json`). A slot on the forwarded line outside that set is refused as an addition the role does not name; the tail is free. Where the context does not cover the item, any forward is refused with "ask instead of forwarding".
- **One re-issue after a failed readback.** The protocol names the re-issue only for the forwarded line. A readback that fails `check-rb` is answered as study 6 answered it: the previous hop's code sends the HO again with `re=` pointing at the bad RB and the problems in the tail, the relay reads that back to `rb2.txt`, and a second failure holds the chain. A passing readback is answered with `AN val=Y` from the previous hop's agent name, ids `<agent>-51` upward so that they cannot collide with the model's own.
- **How a refusal reaches the relay.** The pre-send refusal is appended to the relay's inbox as a message from "pre-send check" and sent as the next turn of the same session, naming every problem; the AN and the re-issue are delivered the same way. A second refusal holds the chain.
- **The desk on SEND.** The first SEND message carries no approval reference, so the desk confirms the log entry covering the supplier and the item (FD-0929 covers MD-2026-057) and adds `appr=OK`.
- **The relay contexts.** `schedule.json` holds seven runs (payment runs on 2, 9 and 16 October, master changes on 3 and 10 October, advices on 2 and 9 October) with priorities 1 to 3; the coordinator's expected addition is PAY due=20261002 pri=2, CHGBANK due=20261003 pri=1, SEND due=20261002 pri=3. `approvals.json` holds six entries (FD-0918, FD-0921, FD-0926, FD-0927, FD-0929, FD-0930) with supplier, item and what was approved. The block-2 confusers: coord-decoy, a second live HO from the scheduler for the same supplier with other figures two messages before the live one; coord-sched, a run of the same kind on the adjacent day with another priority; desk-near, FD-0928 (PAY, SEND: another Marlow invoice) or FD-0925 (CHGBANK: an Evergreen invoice) beside the right entry; desk-cover, the right reference's entry changed to another item of the same supplier.
- **Coverage in prose.** A field is carried when the record's value appears in any of its forms (the amount with or without separators; the date as ISO, eight digits, "2 October 2026" or "02/10/2026"; the account as sort code and number in any punctuation; the supplier's short or legal name; GBP, pounds sterling or the pound sign; gross or "including VAT"); it is drift when the value is absent and another value of the same kind is present; missing otherwise. Lines are graded by parse; a line that does not parse is graded as prose and flagged. The additions (due, pri, appr) are graded the same way as a secondary measure.
- **Traffic.** Every message between agents counts: the delivered messages, readbacks, ANs, re-issues, pre-send refusals, the payer's DN or done note, and any question. The smoke run's `chain.json` counted an accepted forward twice; fixed before the pilot.
- **Timestamps.** Delivered and harness messages carry synthetic stamps on the case date (09:32 for hop 1 and two minutes later per hop; 11:12 onward for later messages), not the wall clock.
- **Layout.** `sender/` beside `trials/` holds the harness's private state per chain (the record, the inboxes as built, the expected additions, the master copy, the act log), as in study 6; `results/manifest.json` is written by `tools/freeze.py`.
- **A second act attempted.** In two F PAY chains of the pilot the payer, after releasing the payment, tried to send a remittance advice as well, prompted by a routine note in study 6's payer inbox; the act tool refused it. The act is graded on what the tool executed; the attempt is recorded in `grade.json` as `second_act_attempt`.
- **Brief lengths.** The prose rendering of the legend was extended with what the v0.2 legend carries (cancel, expiry, undo, the closed constraint keys), so that arm A's briefs are within 5% of L and R per role; F is shorter by design.
- **Cost.** At the runner's rates Haiku 4.5 costs about nine times Haiku 5.5 per chain with similar token counts ($0.16 against $0.017 for an F chain, $0.43 against $0.05 for R). The main run as sized projects to about $15 on Haiku 5.5 and $120 on Haiku 4.5, not the $40 registered. The sizing is unchanged pending the ladder.

### The ladder

Run on 22 October 2026, F only, both models, eight chains per model per level (PAY and CHGBANK, clean contexts 1 and 2, two repeats), K = 2; numbers and the transcripts' reading in `results/pilot/README.md`.

- **Level 0, the worked example removed** (suffix `-p1`): Haiku 5.5 8 of 8 correct, no loss; Haiku 4.5 8 of 8 correct, no loss. The relays still carried the received paragraph through verbatim, now under headers of their own making, so the message grew by more per hop than before. Gate not met.
- **Level 1, two other live handovers for other suppliers in each relay's inbox** (suffix `-p2`): Haiku 5.5 8 of 8 correct, no loss; Haiku 4.5 7 of 8 correct, 1 of 8 lost (12.5%): the desk's redraft dropped the call-back statement from a CHGBANK handover and the payer asked instead of acting. No relay picked a decoy; no value drifted. Gate met on Haiku 4.5; the ladder stops here. Level 2 (the next agent is busy and asks for a short message) is built (`RW_HARDEN=2`, relay briefs `-h2`) and was not run.
- **Decisions, 22 October 2026.** The main run is at level 1, the first level that met the gate, as the protocol says. The sizing stays as registered: both models, three repeats; Haiku 4.5 is the model that showed loss and stays. The main run at level 1 means every relay's inbox in every arm carries the two other live handovers; R runs at the same level as F.
- **The call-back becomes a graded field for CHGBANK, carried in a slot.** What was seen: the one loss on the ladder was a relay dropping "after the call-back to the number on file", a fact the payer's rules require before a bank change, and the coverage measure did not count it because hop 0's line carried it in the tail (`// call-back done on the number on file; ...`), not in a slot, so neither `check-ho` nor coverage by parse saw it. What changed: hop 0's CHGBANK line carries `x_cb=Y` (an extension key the codec accepts without a profile change, as study 6's `x_prev` was); the relay record at every hop and the readback echo therefore cover it, the legend block in the L and R briefs and the prose conventions in the A briefs name it ("that the call-back to the supplier on the number on file was done"), and coverage counts it for CHGBANK: by parse on a line, and in prose as present when a sentence says the call-back was done without a negation or a condition, drift when every mention is negated or conditional, missing when there is no mention. Why: rule 4 of the skill, a fact that has a slot goes in the slot, applied to the line; the prose arms already carried the fact in the first message and are unchanged except for the conventions' sentence. The F briefs are unchanged.

## Amendments after the freeze

Recorded on 22 October 2026 during the main run, after 342 of the 396 Haiku 5.5 chains had run and before any Haiku 4.5 chain had. Under the exclusions rule a defect found during the run stops it, the fix is committed, the freeze moves and every block it could have touched is re-run; the aborted trials stay under `results/aborted/`.

- **The SEND handover carries the address.** What was seen: in the lines arm without checks every SEND chain ended at the first hop, 15 of 15, with the coordinator asking the scheduler for the supplier's address instead of forwarding; the prose arms asked in 3 of 15 each and the checked lines arm in 2 of 15, and the one chain the runner recorded as stalled was a desk asking the same question. The legend defines a SEND as an email "to the supplier address given", the first message gave none (study 6's design, where the payer resolves the address from its master), and a relay holds no master, so it could neither forward a handover it read as incomplete nor resolve it. That is a defect in the case, not a relay losing anything: the chain was built so that a relay could not pass the message on in good faith. What changed: hop 0's SEND line carries `addr=billing@marlowdesign.co.uk`, the billing contact on file, as study 6's block-1 SEND handover did; the prose first message names the same address; `addr` is a graded field for SEND at every hop, by parse on a line and by normalised match in prose; the payer still checks it against the master under its rule 4. Every SEND chain of every block, arm and model is reset and re-run from the new freeze; the SEND trials of the aborted pass, with their grades and the partial Haiku 5.5 summary, are kept under `results/aborted/send-no-addr/`. PAY and CHGBANK chains are not touched by the change and are not re-run; their results stand from the first pass and the manifest names both commits.
- **The runner was interrupted once by the environment.** The container running the study restarted after chain 342 of the Haiku 5.5 pass; the eight chains in flight were reset to their built state and run again under the same ids with the rest of the pass. No chain ran twice to completion; `results/main_run.log` and `main_run2.log` hold the two passes and `main_run3.log` the resumption after this amendment.

## Amendments in the analysis

Recorded on 22 October 2026 after the main run, before the outcome below was written. None changes a hypothesis, a test or a trial.

- **False alarms at the readback are reported apart from false alarms at the forward.** H4 was registered over correct forwards: `check-ho` refusing a forwarded line that carried every received slot with the right values. The first analysis put `check-rb` refusals of a readback whose values were all right into the same numerator, so a cell could show more false alarms than forwards. The grader now records the number of readbacks checked, and the analysis reports H4 as registered and, beside it, readback false alarms over readbacks checked. By study 6's rule a rejected readback whose values were all right is a false alarm whatever the cause, and in this run every one was the integrity tier: a digest that did not match because the relay had retyped the handover into `make-rb` without its tail.
- **Three chains excluded and run again.** `B1-CHGBANK-clean-4-L-haiku45-k2-r1`, `B1-SEND-clean-2-A-haiku45-k2-r3` and `B2-CHGBANK-coord-decoy-F-haiku45-k2-r1` ended with a relay replying SENT and no `out.txt` in its folder. The relay had written the file: to a path with the model name misspelt (`hauki45`, `haikus45`), outside its working folder. Fifteen such stray folders appeared during the Haiku 4.5 pass, three of them the whole of a hop's output; they are kept under `results/aborted/mistyped-paths/`. Under the exclusions rule the three chains are named in `results/excluded.json` with the reason, kept on disk, left out of the analysis, and run again as repeat 4.
- **The reading of the questions.** Why a chain ended in a question is not a registered measure. For the outcome below the questions were read and sorted by keyword into four kinds: addressing (the payer says the handover is addressed to another agent), provenance (the payer or a relay wants the approval or the call-back shown), the email's subject and body (a SEND payer asking what to write), and other. The counts are a reading, not a grade, and every question file is in its chain's folder.
- **The ladder gate was thin.** Level 1 met the registered gate on one model with 1 chain in 8, and the main run then found the F arm on that model losing 1 chain in 45 in block 1. The gate did what it was for, choosing a level before the run; the loss it detected did not generalise, and the outcome says so rather than restating the gate.

## Outcome

792 chains on 22 October 2026, 396 per model, at ladder level 1: $10.66 of model time on Haiku 5.5 and $82.90 on Haiku 4.5, the pilots and the ladder $5 more. PAY and CHGBANK chains ran at the freeze of commit `5b58ccd`; SEND chains at the re-freeze of `a61d79e` after the address amendment. Three chains were run again under repeat 4 as above. A blind second reading of 40 chains (5%, seed 7) agreed with the code grader on 40 of 40 acts, 40 of 40 on every field at the payer and 40 of 40 on drift (`results/validation/`). Every figure is in `results/summary.json` and `summary.md`; `results/report.html` is written from the JSON.

**No relay changed a value.** Across 792 chains, both models, four forms and up to five relays, a record field reached a hop with a different value twice. One is the grader's, not a relay's: a coordinator's forwarded message read "Call-back: done, to the number on file, before approval", and the prose call-back finder, which treats "before" as a condition, graded the statement conditional (`B2-CHGBANK-desk-cover-A-haiku55-k2-r1`); the call-back was stated as done, the grade stands under the no-overrides rule, and the dispute is in `results/disputes.json`. The other is the telephone game once: a Haiku 4.5 prose relay at hop 3 of a three-relay chain forwarded a different handover altogether, the decoy Coleridge payment in place of the Evergreen bank change, and the payer asked rather than paid (`B3-CHGBANK-clean-1-F-haiku45-k3-r1`). On a line, `check-ho` at that hop refuses it on `item` alone. Nothing else drifted. A field was dropped twice, both times the call-back statement of a bank change, both by Haiku 4.5 prose relays (`B2-CHGBANK-desk-near-F-haiku45-k2-r2`, `B3-CHGBANK-clean-1-F-haiku45-k2-r3`), and in both the payer changed the master without it, correctly on every other field: the fact the pilot saw a relay lose is the one the prose arms lost, and the payer did not insist on it. No line arrived at the payer short of a slot. Elsewhere, where a cell shows fewer chains with every field at the payer than correct acts, the difference is chains that stopped at a relay with a question.

**Haiku 5.5: the checked line wins, and so does the unchecked one.** Block 1: R 45 of 45 chains ended in a correct act and L 45 of 45; free prose 37 of 45 (82%, 68 to 92) and disciplined prose 35 of 45. H1 holds (p = 0.003). H2 does not separate R from F (45 against 43, p = 0.25): prose carried the facts to the payer; what failed was the envelope. Of the 18 prose failures, 5 were the payer refusing a handover the relay had forwarded inside a wrapper still headed to the relay ("To: desk, Hi desk"), under its rule that a handover addressed to another agent is not its own; 9 were the payer or a relay wanting the approval record or the call-back shown rather than reported; 4 other. A line cannot fail the first way, because `from=` and `to=` are required slots the validator makes the relay rewrite, and in this run it did not fail the second, because `apref=`, `x_cb=Y` and the desk's `appr=OK` are the provenance in a checkable shape. H4 holds: 0 false alarms in 90 correct forwards (upper bound 4%), and 0 in 135 readbacks checked. Block 2: R 36 of 36 chains ended as expected, L 35, A 34, F 31; H6 holds (p = 0.027). The two chains graded wrong in the run are both here and neither is a wrong act: in each a prose coordinator asked the scheduler at hop 1 about an approval reference the SEND message does not carry, so the chain never reached the desk whose ask was the expected outcome; under the desk-cover amendment that is "asked elsewhere". No chain in the run executed a wrong act: 0 in every cell. Block 3, the sweep: R 9 of 9 at every length, K = 1, 2, 3 and 5; F 8, 9, 8 and 5 of 9. At five relays the prose message delivered to the payer was 197 tokens against 73 at hop 1, the line 104 against 77, and 4 of 9 prose chains ended with the payer or a relay asking, 3 of them on addressing or provenance, where every line chain acted.

**Haiku 4.5: the relays carry prose, and the integrity tier holds the line.** Block 1: free prose 44 of 45, unchecked lines 44 of 45, disciplined prose 40 of 45, checked lines 37 of 45 (82%, 68 to 92). H1 fails and the direction is reversed (p = 0.999); H8 separates L from R the opposite way to the one registered (p = 0.03). Seven of R's eight losses are the same event (the eighth is a desk answering UN NOCTX because the approval reference was not in its log): the relay composed its readback by retyping the handover into `make-rb`, dropped the tail, `h=` did not match the line as delivered, the re-issued handover was read back the same way, and the chain was held with every value right. H4 as registered holds, 0 false alarms in 77 correct forwards; at the readback it is 13 in 128 (10%, 6 to 17). Block 2: F and A 36 of 36 as expected, L 34, R 27, with 7 holds of the same kind. Block 3: F 9, 9, 8 and 9 of 9; R 8, 7, 6 and 8, every shortfall a hold. The three chains run again were the model writing its forwarded message to a misspelt path, a weak-receiver fault of the same family: the hands, not the reading.

**Cost.** A block-1 chain on Haiku 5.5: free prose 2.9 model turns, 515 tokens of traffic, $0.016; checked lines 6.0 turns, 684 tokens, $0.048. At five relays the line's readbacks make it the heavier wire: 1,370 tokens of traffic against 971, 12 turns against 5.4, $0.094 against $0.028. Haiku 4.5 costs about eight times as much per chain through this runner at similar token counts.

**Hypotheses.** H1 holds on Haiku 5.5 and fails on Haiku 4.5. H2 is not decided on either (p = 0.25 and 0.997): the fields arrived in prose. H3 holds in sign on both: prose grows per hop (73 to 156 and to 175 on Haiku 5.5 over two relays; to 197 over five), lines are near flat (77 to 100, and 104 at five relays). H4 holds on both over forwards; the readback figure beside it fails the same bound on Haiku 4.5. H5 holds: drift is 2 in 792, both named. H6 holds on Haiku 5.5 and fails on Haiku 4.5. H7: on Haiku 5.5 F falls at K = 5 and R does not; on Haiku 4.5 neither falls and R's holds do not grow with K. H8: L and R are not separable on Haiku 5.5, as registered; on Haiku 4.5 L beats R, the reverse of what was registered.

**What follows for the protocol**, by the table decided in advance. H1 and H4 held on Haiku 5.5, so the skill and the spec say that a relay checks the handover it forwards against the one it received, with `check-ho` taking the received HO as the record; the check caught nothing on these models and refused nothing it should not have, and the line's claim on a chain is that the envelope cannot be forwarded unaddressed and the facts cannot be forwarded in fewer slots. H8 held on Haiku 5.5 and reversed on Haiku 4.5, so the check at every hop is for mixed fleets in a form the weak relay can complete: the readback is composed by code from the message as delivered, by id, never retyped by the model, which is study 7's amendment 10 brought to the relay; without it the integrity tier holds one chain in eight on the weak model with every value right. H3 held and the value loss the study was built to find did not occur, so the site says that on these models a relay carries an instruction's facts intact in prose, and that what prose loses across hops is the address and the provenance, and size.
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
