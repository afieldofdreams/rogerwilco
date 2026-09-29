# rogerwilco v0.1

Schema-driven typed compact messages for agent-to-agent handoffs. Domain-agnostic codec; P-Form (Pensive stance handoffs) is the first schema.

Dated 27 September 2026. Author: Adam Field, Croxio Ltd. Built with Lumos.

## Layout

- `schemas/pform.json` — enums, message types, typed slots. Edit this to define a new domain.
- `rogerwilco/codec.py` — `encode`/`decode` (keyed pipe form), `encode_tight`/`decode_tight` (positional METAR-style form with optional CRC), `validate`, `delta`, legends.
- `rogerwilco/render.py` — English, JSON and glyph renderings of the same data, for comparison only.
- `rogerwilco/synth.py` — synthetic handoff generator and the ground-truth receiver policy.
- `measure.py` — token counts (tiktoken o200k and cl100k), round trip, corruption tests, delta example. Writes `results/measure.json`.
- `parity_prep.py` — builds the five blind-receiver prompts in `data/prompt_*.txt` and `data/parity_truth.json`.
- `results/parity_raw.json`, `results/parity.json` — receiver answers and scoring (Haiku 4.5 x2, Sonnet x1).
- `report.html` — the working paper.

## Run

```
pip install tiktoken
python3 measure.py        # deterministic; regenerates data/ and results/measure.json
python3 parity_prep.py    # regenerates the prompts
```

To re-run parity, send each `data/prompt_<format>.txt` to a fresh model instance with no tools and score the JSON reply against `data/parity_truth.json` (see the scoring snippet at the bottom of `parity_prep.py` history in `results/parity.json`).

## Quick use

```python
from rogerwilco.codec import Schema, encode, decode, encode_tight, decode_tight
S = Schema.load("schemas/pform.json")
msg = {"from": "TRI", "to": "STR", "node": 4102, "stage": "OPT", "stall_days": 19,
       "confidence": "M", "ask": "SCORE4", "keep_assigned": ["ADAM"], "source_view": 121}
encode(S, "HO", msg)            # HO|TRI>STR|P4102|stg=OPT|stall=19d|conf=M|ask=SCORE4|keep=ADAM|src=121
encode_tight(S, "HO", msg, check=True)
decode(S, "HO|TRI>STR|P4102|stg=OPT|stall=19d|conf=M|ask=SCORE4|keep=ADAM|src=121")
```

## Known gaps (v0.1)

- `opstatus.WAIT` collides with a receiver decision label; rename before adoption.
- Keyed form cannot detect a dropped optional field. Tight form with CRC can.
- Token counts use OpenAI tokenizers as proxies for Claude's.
- Parity cells are n=60, one to two runs. Screening quality only.
