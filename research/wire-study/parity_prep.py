"""Build blind parity batches: same 60 messages, five formats."""
import json, random
from formcore.codec import Schema, encode, encode_tight, tight_legend
from formcore.render import english, as_json, glyph, glyph_legend
from formcore import synth

S = Schema.load("schemas/pform.json")
data = json.load(open("data/handoffs.json"))
rng = random.Random(42)
by = {}
for d in data: by.setdefault(d["_truth"], []).append(d)
sample = [d for lab in sorted(by) for d in rng.sample(by[lab], 10)]
rng.shuffle(sample)
clean = lambda d: {k: v for k, v in d.items() if not k.startswith("_")}

fmts = {
  "english": (None, lambda d, i: english(S, clean(d), seed=d["_id"])),
  "json": ("Messages are JSON handoff objects.", lambda d, i: as_json(S, clean(d))),
  "keyed": (S.legend(), lambda d, i: encode(S, "HO", clean(d))),
  "tight": (tight_legend(S), lambda d, i: encode_tight(S, "HO", clean(d))),
  "glyph": (S.legend() + "\n\n" + glyph_legend(), lambda d, i: glyph(S, clean(d))),
}
truth = {f"m{i+1:02d}": d["_truth"] for i, d in enumerate(sample)}
json.dump({"truth": truth, "src_ids": {f"m{i+1:02d}": d["_id"] for i, d in enumerate(sample)}}, open("data/parity_truth.json", "w"), indent=1)

for name, (legend, fn) in fmts.items():
    msgs = "\n".join(f"{mid}: {fn(d, i)}" for i, (mid, d) in enumerate(zip(truth, sample)))
    prompt = f"""You are a receiving agent in a multi-agent system. Other agents send you handoff messages about nodes in a knowledge graph. For each message, decide what to do by applying the policy below exactly. Today is 27 September 2026.

Do not run code, write scripts, or use any tools. Read each message yourself and decide. This tests reading comprehension.

{synth.POLICY}
""" + (f"\nMessage format reference:\n{legend}\n" if legend else "") + f"""
Messages:
{msgs}

Reply with only a JSON object mapping each message id to one of WAIT, BOUNCE, EXPEDITE, ESCALATE, CLOSE, ACCEPT. Example: {{"m01": "ACCEPT", "m02": "WAIT"}}. Include all 60 ids. No other text."""
    open(f"data/prompt_{name}.txt", "w").write(prompt)
    print(name, len(prompt))
