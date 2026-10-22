#!/usr/bin/env python3
"""The speed test: wall seconds per session and per chain for each local model, measured and projected, to results/speed.md.

  python3 tools/speed.py [--tag speed]

Measured: every run chain with the -s suffix (block 1, PAY, F and C, one repeat per local model): seconds per model call,
per session (one agent's conversation) and per chain, with the prompt and completion tokens the model reported. A small
model often ends a chain at hop 1 (it asks), so the per-chain figure is also projected: the model's prompt rate and
generation rate (tokens per second, from its own calls) applied to the token budget of a chain that went the distance
(the anchor chains' prompt and completion counts per session, in the model's own tokens the counts are close enough).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

# a chain's token budget per arm when it goes the distance: sessions x (prompt tokens of the first turn, later turns, completion),
# from study 8's shapes and the pilot's anchor chains: F = 3 sessions of one turn; C = 3 sessions, the relays 2 turns and the
# payer 2 turns, the later turns re-sending the whole conversation (cached prefix in llama_cpp, so only the new tokens cost)
# The budgets are the token counts qwen7b reported on the speed chains that went the distance (F) or reached the desk's
# forward (C), the payer's C session being the coordinator's plus the master (about 1,200 tokens more).
BUDGET = {"F": {"prompt": [2146, 2557, 3383], "completion": [295, 148, 179]},
          "C": {"prompt": [4749 + 84, 4924 + 83, 6100 + 90], "completion": [2 + 104, 2 + 93, 2 + 100]}}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--suffix", default="-s"); ap.add_argument("--out", default="speed.md")
    a = ap.parse_args(argv)
    per_model: dict = {}
    for t in sorted(C.TRIALS.iterdir()):
        if not t.name.endswith(a.suffix) or not (t / "turns.json").exists():
            continue
        meta = C.read_json(t / "meta.json"); turns = C.read_json(t / "turns.json"); man = C.read_json(t / "manifest.json")
        m = per_model.setdefault(meta["model"], {"chains": [], "calls": []})
        m["chains"].append({"id": t.name, "arm": meta["arm"], "wall": man["wall_seconds"], "sessions": man["session_seconds"], "ended": man["ended"], "turns": len(turns["turns"])})
        for x in turns["turns"]:
            u = x.get("usage") or {}
            m["calls"].append({"chain": t.name, "prompt": u.get("prompt_tokens"), "completion": u.get("completion_tokens"), "seconds": x.get("seconds"), "hop": x["hop"], "turn": x["turn"]})
    lines = ["# Speed test", "", f"One PAY chain per arm (F and C), K = 2, block 1, clean context 1, on each local model, trial suffix `{a.suffix}`. Four threads, llama_cpp in-process, temperature 0, context 12288.",
             "Seconds are wall seconds of the model call. A chain that ended at hop 1 (the model asked) measures one session; the per-chain figure for a chain that goes the distance is projected from the model's token rates.", ""]
    lines += ["| model | calls fitted | prompt tok/s | gen tok/s | measured sessions (s) | measured chain F (s, hops reached) | measured chain C (s, hops reached) | projected chain F (s) | projected chain C (s) | projected chain, design mix (s) | chains in 8 h (F / C / mix) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    proj_all = {}
    for alias in C.LOCAL_MODELS:
        m = per_model.get(alias)
        if not m:
            lines.append(f"| {alias} | (no chains run) | | | | | | | | | |"); continue
        # fit seconds = new_prompt / prompt_rate + completion / gen_rate by least squares over every call of the model;
        # a later turn of a session re-uses llama_cpp's cached prefix, so its new prompt tokens are the increase since the turn before
        pts = []
        prev = {}
        for c in sorted(m["calls"], key=lambda c: (c["chain"], c["hop"], c["turn"])):
            if not (c["prompt"] and c["seconds"]):
                continue
            key = (c["chain"], c["hop"])
            new_prompt = c["prompt"] - prev.get(key, 0) if c["turn"] > 1 else c["prompt"]
            prev[key] = c["prompt"]
            pts.append((max(new_prompt, 1), c["completion"] or 0, c["seconds"]))
        sxx = sum(x * x for x, y, t in pts); sxy = sum(x * y for x, y, t in pts); syy = sum(y * y for x, y, t in pts)
        sxt = sum(x * t for x, y, t in pts); syt = sum(y * t for x, y, t in pts)
        det = sxx * syy - sxy * sxy
        prompt_rate = gen_rate = None
        if det > 0 and len(pts) >= 2:
            a1 = (sxt * syy - syt * sxy) / det      # seconds per prompt token
            b1 = (sxx * syt - sxy * sxt) / det      # seconds per generated token
            if a1 > 0 and b1 > 0:
                prompt_rate, gen_rate = 1 / a1, 1 / b1
        if prompt_rate is None and pts:            # one call, or a degenerate fit: charge everything to the prompt
            prompt_rate = sum(x for x, y, t in pts) / sum(t for x, y, t in pts); gen_rate = None
        sess = sorted(round(v) for c in m["chains"] for v in c["sessions"].values())
        def chain_of(arm):
            cs = [c for c in m["chains"] if c["arm"] == arm]
            return f"{round(cs[0]['wall'])}, {cs[0]['ended'].get('hop')}" if cs else ""
        proj = {}
        for arm in ("F", "C"):
            if prompt_rate and gen_rate:
                proj[arm] = sum(p / prompt_rate for p in BUDGET[arm]["prompt"]) + sum(c / gen_rate for c in BUDGET[arm]["completion"])
        if proj:
            proj["mix"] = 0.4 * proj["F"] + 0.6 * proj["C"]     # the design's weight over the five arms
        proj_all[alias] = {"prompt_rate": prompt_rate, "gen_rate": gen_rate, "projected": proj, "measured": m["chains"], "points": pts}
        fit = f"{int(8 * 3600 / proj['F'])} / {int(8 * 3600 / proj['C'])} / {int(8 * 3600 / proj['mix'])}" if proj else ""
        if prompt_rate and gen_rate:
            lines.append(f"| {alias} | {len(pts)} | {prompt_rate:.0f} | {gen_rate:.1f} | {', '.join(str(s) for s in sess)} | {chain_of('F')} | {chain_of('C')} | "
                         f"{proj['F']:.0f} | {proj['C']:.0f} | {proj['mix']:.0f} | {fit} |")
        else:
            lines.append(f"| {alias} | {len(pts)} | {prompt_rate:.0f} | ? | {', '.join(str(s) for s in sess)} | {chain_of('F')} | {chain_of('C')} | | | | |")
    lines += ["", "Projection: the token budget of a chain that goes the distance, per arm, in sessions of (prompt tokens, completion tokens): " + json.dumps(BUDGET) + ". The later turns of a session re-use llama_cpp's cached prefix, so only their new tokens are counted. A chain of the other arms (A, L, R) sits between F and C; the design's mix over the five arms is about 0.4 F-weight and 0.6 C-weight.", ""]
    lines += ["Every call:", "", "| model | chain | hop | turn | prompt tokens | completion tokens | seconds |", "|---|---|---|---|---|---|---|"]
    for t in sorted(C.TRIALS.iterdir()):
        if not t.name.endswith(a.suffix) or not (t / "turns.json").exists():
            continue
        meta = C.read_json(t / "meta.json")
        for x in C.read_json(t / "turns.json")["turns"]:
            u = x.get("usage") or {}
            lines.append(f"| {meta['model']} | {t.name} | {x['hop']} | {x['turn']} | {u.get('prompt_tokens')} | {u.get('completion_tokens')} | {x.get('seconds')} |")
    C.RESULTS.mkdir(exist_ok=True)
    (C.RESULTS / a.out).write_text("\n".join(lines) + "\n")
    (C.RESULTS / "speed.json").write_text(json.dumps(proj_all, indent=1, default=str))
    print("\n".join(lines[:12]))
    print(f"wrote {C.RESULTS / a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
