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
```

Stages (each writes a file the next reads): ingest (registry.jsonl) -> extract (assertions.jsonl,
raw/) -> normalise (dates and canonical concepts) -> link (events.jsonl, episodes.json) -> analyse
(report.md, summary.json) -> render (theograph.html).
