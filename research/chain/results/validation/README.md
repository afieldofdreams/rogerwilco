# Blind second reading, study 8

A second reader graded a 5% sample of chains by hand, without seeing `grade.json` or any summary, on the three measures the protocol names in Validity: the act, coverage at the payer, and drift. The reader's verdicts were written to `reader.json` before any `grade.json` was opened; `sample.json` was written before any trial was read.

## Sample

- Population: every directory under `trials/` with a `manifest.json` whose name does not end in `-s`, `-p`, `-p1` or `-p2`: 787 chains.
- Sample: `random.Random(7).sample(ids, 40)` over the sorted ids. 5% of 787 is 39.35, so the floor of 40 applies. Ids are in `sample.json`.
- Composition: 22 block 1, 17 block 2, 1 block 3 (K=3); 12 CHGBANK, 7 PAY, 3 SEND in block 1 and 7 CHGBANK, 2 PAY, 8 SEND in block 2; arms F 7, A 8, L 11, R 14; haiku45 23, haiku55 17.

## What the reader looked at

For each chain: the record and the first message in `sender/<id>.json`; the live message delivered at every hop, read from `trials/<id>/hop<k>/mail/inbox.md` at the position the sender file reserves for it; each relay's `rb.txt`, `out.txt` and `question.txt`; the payer's `done.txt` or `dn.txt`, `action.json` and `email.json`; and `sender/<id>.actlog.json` for what the act tool executed. Verdicts follow the Measures table: act compared field by field against the record (sort code and account by digits, dates and amounts by value); coverage at the payer per record field (PAY: sup amt cur kind paid ref apref; CHGBANK: sup acct eff apref and the call-back statement; SEND: sup addr amt cur paid ref), a value in another format counting as ok; drift as a record field at a hop whose value differs from the record where the previous hop had it right. Where the chain stopped before the payer, every field at the payer was marked missing.

## Agreement

| measure | agreed / total |
|---|---|
| act (correct / wrong / asked / not done) | 40 / 40 |
| all record fields at the payer | 40 / 40 |
| any drift | 40 / 40 |

Per-field coverage at the payer also agreed on every field of every chain (the reader's `cb` is the grader's `x_cb`). The reader found 35 correct acts and 5 asked; no wrong act, no not-done chain and no drift at any hop in the sample. The grader's `asked_at` hop matches the reader's on all five asked chains (hop 2, 2, 2, 3, 1).

## Disagreements

None on the three measures.

## Notes from the reading

These are not disagreements; they record judgement calls and one observation outside the validated measures, so a later reader can check them.

- `B1-PAY-clean-1-L-haiku55-k2-r2`, `B1-PAY-clean-5-L-haiku45-k2-r1`, `B2-PAY-desk-near-R-haiku45-k2-r3`: the act tool's `item` field reads `inv:MD-2026-057`, the typed form of the record's `MD-2026-057`. The reader counted the act correct, since `item` is not among the fields the record names for PAY and the invoice is the same; every named field matched. The grader agrees.
- `B2-SEND-coord-decoy-L-haiku45-k2-r1`: the full record reached the payer intact, and the payer then asked for an email subject and body instead of sending. Both readings: act asked, all fields at the payer, no drift. The question is the payer's, not a relay's.
- `B2-SEND-desk-near-R-haiku45-k2-r1`: the coordinator's readback carried every slot correctly but a wrong digest (`h=3c0ae160e5e8` against `3fd22e2f3ef9`); after the refusal it asked the scheduler which handover was correct instead of re-issuing, and the chain stopped at hop 1. Both readings: asked, nothing at the payer, no drift. The grader lists this refusal under `false_alarms`. The README defines a false alarm as a refusal of a forwarded line that carried every received slot with the record's values; this refusal was of a readback whose digest did not match the line it read back, which is the check doing its job. Whether a readback refused on digest alone belongs under false alarms is a question for the analysis, not for these three measures, and the reader flags it rather than rules on it.
- `B2-SEND-desk-near-R-haiku55-k2-r1`: the coordinator's counters (`coordinator-12`, `coordinator-13`) suggest earlier drafts inside its session, but the delivered readback and HO are correct and the grader records no refusal. Correct in both readings.
- `B1-CHGBANK-clean-3-F-haiku55-k2-r3`: the payer wrote that it could not open `approvals.json` and acted on the approval reference and call-back statement in the handover. The act matches the record; the note does not bear on the three measures.
- `B1-SEND-clean-3-F-haiku45-k2-r3`: the payer's done note is dated 2026-10-22 (the wall clock) rather than the scenario date; cosmetic, the executed values are the record's.

No `grade.json` was changed.
