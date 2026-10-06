# theograph

Documents in, an episodic care timeline out. A reference pipeline built on the `clin` profile:
one assertion per statement, gated on provenance, anchored in time, linked across documents into
events with every source kept, rendered as a self-contained HTML theograph.

Work in progress: the pipeline runs end to end on the synthetic patient in `demo/patient-01`;
nothing here has been run on a real record. Runs where the data is allowed to be; model keys come
from the environment (`ANTHROPIC_API_KEY`, or `OPENAI_API_KEY` with `OPENAI_BASE_URL`); nothing is
sent anywhere but the endpoint you name. No patient data belongs in this repository.

```
python3 -m theograph run theograph/demo/patient-01 out/patient-01 --provider anthropic
python3 -m theograph run <docs> <out> --provider mock --from-files <dir of replies>   # assertions extracted elsewhere
python3 -m pytest -q theograph/tests
```

Stages (each writes a file the next reads): ingest (registry.jsonl) -> extract (assertions.jsonl,
raw/) -> normalise (dates and canonical concepts) -> link (events.jsonl, episodes.json) -> analyse
(report.md, summary.json) -> render (theograph.html).

## How the extraction works

One document per model call. The prompt carries the rules (`prompt.py`), the `clin` legend from the
codec, the numbered document and a kickoff line; the model answers with assertion lines, one per
statement, each naming the line(s) of the document it comes from and quoting the words it rests on.
The gate (`gate.py`) refuses the whole output if any line is invalid under the profile, names lines
that do not exist, quotes words that are not on those lines, or reuses an id; the errors go back to
the model and it answers again, up to `--rounds` times. What passes the gate is the record. The
model therefore cannot state something the document does not say, and every event on the timeline
can be traced to the words behind it. Whether a statement was missed, or read as the wrong kind of
statement, the gate cannot see: that is what the checks in `analyse` and a reviewer are for.

`demo/patient-01/replies/` holds the six accepted outputs the demo was built from, so the pipeline
reproduces without a model (`--provider mock --from-files`). `replies/superseded/` keeps the first
reading of the discharge summary, which read "the CT coronary angiogram requested in clinic had
shown ..." as the order rather than the test done, and gave the clopidogrel course as an interval
rather than the date the letter states. Two rules were added to the prompt (a test that showed
something was DONE; prefer a date to an interval when both are given) and the document was
extracted again; the second reading is the one in `replies/`.

## What the linker does with certainty and time

Three things are kept apart and never folded into one score: `cert` is what the document said
(hedged or not), `act` is how the author knew it (observed, reported, assessed, ordered, done),
and the document type gives the source its weight (`DOC_WEIGHT` in `link.py`). An event carries all
of its sources; its displayed certainty and authority come from its best source, and the rest are
still there to read.

Dates come from what the line says, not from the document date alone (`normalise.py`): an explicit
date, month or year; an interval read by direction (a review in six weeks is after the letter, a
symptom for three months began before it, a course of twelve months runs forward from the start);
admission and discharge dates from the registry, including for a correction letter, which resolves
them against the document it corrects. Statements with no date are current as of their document.

The linker (`link.py`) then makes one event per thing: a course of a medicine at a dose, with
changes linked to what they replace and a planned stop kept separate from an actual one; one event
per measurement per date, with a correction letter superseding the value it corrects and a genuine
disagreement between documents flagged rather than resolved; one event per problem or state, closed
by a later past-tense statement on the date it gives; plans and orders matched to the thing done,
across concept names (an ordered renal function panel is met by a creatinine result) and across
documents (a planned cardiology review is evidenced by the next cardiology letter). Plans with no
evidence stay flagged. Concept names are unified through `data/synonyms.json` until a terminology
binding replaces it; names the extractor invents beyond that table stay as separate rows, which is
the visible cost of not having the binding yet.
