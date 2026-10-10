#!/usr/bin/env python3
"""Aggregate grade.json files into results/summary.json and results/summary.md, with intervals and the pre-registered tests.

  python3 tools/analyse.py [--tag NAME]     # --tag writes results/<NAME>/ instead of results/
"""
from __future__ import annotations

import argparse
import json
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

# ----------------------------------------------------------------------------------------------------- statistics

def cp_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Clopper-Pearson exact interval for k of n."""
    if n == 0:
        return (0.0, 1.0)
    def cdf(p, upto):
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(upto + 1))
    def solve(target, upto, lo=0.0, hi=1.0, rising=False):
        for _ in range(60):
            mid = (lo + hi) / 2
            v = cdf(mid, upto)
            if (v > target) != rising:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(1 - alpha / 2, k - 1)
    upper = 1.0 if k == n else solve(alpha / 2, k)
    return (round(lower, 4), round(upper, 4))


def fisher(a: int, b: int, c: int, d: int, alternative: str = "two-sided") -> float:
    """Fisher's exact test on [[a, b], [c, d]]; one-sided 'less' tests that row 1's rate is lower than row 2's."""
    n = a + b + c + d; r1 = a + b; c1 = a + c
    if n == 0 or r1 == 0 or c1 == 0 or r1 == n or c1 == n:
        return 1.0
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    def pr(x):
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = pr(a)
    if alternative == "less":
        return min(1.0, sum(pr(x) for x in range(lo, a + 1)))
    if alternative == "greater":
        return min(1.0, sum(pr(x) for x in range(a, hi + 1)))
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 + 1e-12))


def rate(k: int, n: int) -> dict:
    lo, hi = cp_interval(k, n)
    return {"k": k, "n": n, "p": round(k / n, 4) if n else None, "lo": lo, "hi": hi}


def fmt(r: dict) -> str:
    if not r["n"]:
        return "0 / 0"
    return f"{r['k']} / {r['n']} ({100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f})"

# ----------------------------------------------------------------------------------------------------- cells

def cell_summary(rows: list[dict]) -> dict:
    induced = [r for r in rows if r["kind"] in ("induced", "planted")]
    clean = [r for r in rows if r["kind"] == "clean"]
    tool = [r for r in rows if r["kind"] == "tool"]
    acted = [r for r in rows if r["acted"]]
    fid = [r for r in rows if r["fidelity"] is not None and r["kind"] != "tool"]
    honest = [r for r in rows if r["dn_honest"] is not None]
    checked_rb = [r for r in rows if r["readback_checked"]]
    c = {
        "trials": len(rows), "induced": len(induced), "clean": len(clean), "tool": len(tool),
        "wrong_acts_induced": rate(sum(r["wrong_act"] for r in induced), len(induced)),
        "wrong_acts_clean": rate(sum(r["wrong_act"] for r in clean), len(clean)),
        "caught_before_act": rate(sum(r["caught_before_act"] for r in induced), len(induced)),
        "asked_induced": rate(sum(r["asked"] for r in induced), len(induced)),
        "asked_clean": rate(sum(r["asked"] for r in clean), len(clean)),
        "asked_about_date": sum(r["asked_about_date"] for r in rows),
        "false_alarms_clean": rate(sum(bool(r["false_alarm"]) for r in clean if r["readback_checked"]), len([r for r in clean if r["readback_checked"]])),
        "rejected_clean": rate(sum(r["readback_rejected"] for r in clean if r["readback_checked"]), len([r for r in clean if r["readback_checked"]])),
        "fidelity": rate(sum(r["fidelity"] for r in fid), len(fid)),
        "dn_honest": rate(sum(r["dn_honest"] for r in honest), len(honest)),
        "dn_flag_tool": rate(sum(bool(r["dn_flag"]) for r in tool), len(tool)),
        "receiver_reported_tool": rate(sum(bool(r["receiver_reported"]) for r in tool), len(tool)),
        "dn_false_flag": rate(sum(bool(r["dn_flag"]) for r in acted if r["act_correct"] and r["dn_checked"]), len([r for r in acted if r["act_correct"] and r["dn_checked"]])),
        "acted": len(acted), "held": sum(r["held"] for r in rows), "outside_tool": sum(1 for r in acted if not r["through_tool"]),
        "status_not_ok": sum(1 for r in rows if r["status"] != "ok"),
        "cost_usd_mean": round(sum(r.get("cost_usd") or 0 for r in rows) / len(rows), 4) if rows else None,
        "receiver_turns_mean": round(sum(r["receiver_turns"] for r in rows) / len(rows), 2) if rows else None,
        "brief_tokens_mean": round(sum(r["brief_tokens"] for r in rows) / len(rows)) if rows else None,
        "traffic_tokens_mean": round(sum(sum(r["traffic_tokens"].values()) for r in rows) / len(rows)) if rows else None,
        "cache_read_mean": round(sum(r["usage"]["cache_read"] for r in rows) / len(rows)) if rows else None,
        "denials": sum(r["denials"] for r in rows),
    }
    return c


def tests(cells: dict, models: list[str]) -> dict:
    out = {}
    def wa(block, arm, model):
        c = cells.get((block, arm, model))
        return c["wrong_acts_induced"] if c else None
    def fa(block, arm, model):
        c = cells.get((block, arm, model))
        return c["false_alarms_clean"] if c else None
    for m in models:
        t = {}
        a, d, c2, b, e = (wa(2, x, m) for x in "ADCBE")
        if a and d:
            t["H1 D fewer wrong acts than A (one-sided)"] = {"A": fmt(a), "D": fmt(d), "p": fisher(d["k"], d["n"] - d["k"], a["k"], a["n"] - a["k"], "less")}
        if a and c2:
            t["H2 C against A (two-sided)"] = {"A": fmt(a), "C": fmt(c2), "p": fisher(c2["k"], c2["n"] - c2["k"], a["k"], a["n"] - a["k"])}
        if b and d:
            t["H7 B against D (two-sided)"] = {"B": fmt(b), "D": fmt(d), "p": fisher(b["k"], b["n"] - b["k"], d["k"], d["n"] - d["k"])}
        if e and d:
            t["H8 E against D (two-sided)"] = {"E": fmt(e), "D": fmt(d), "p": fisher(e["k"], e["n"] - e["k"], d["k"], d["n"] - d["k"])}
        f = fa(2, "D", m)
        if f:
            t["H4 D false alarms on clean (upper bound under 5%)"] = {"D": fmt(f), "holds": f["hi"] < 0.05}
        out[m] = t
    return out


def analyse(tag: str | None, only: str = "", level: int | None = None) -> None:
    rows = []
    for trial in sorted(C.TRIALS.iterdir()):
        g = trial / "grade.json"
        if g.exists() and only in trial.name:
            r = C.read_json(g)
            if level is None or r.get("harden", 0) == level:
                rows.append(r)
    out_dir = C.RESULTS / tag if tag else C.RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = {}
    for r in rows:
        cells.setdefault((r["block"], r["arm"], r["model"]), []).append(r)
    models = sorted({r["model"] for r in rows})
    summary = {"rows": rows, "cells": {}, "tests": {}}
    cs = {}
    for key, rs in cells.items():
        cs[key] = cell_summary(rs)
        summary["cells"][f"B{key[0]}-{key[1]}-{key[2]}"] = cs[key]
    summary["tests"] = tests(cs, models)
    lines = ["| block | arm | model | trials | wrong acts, induced | wrong acts, clean | caught before act | asked (induced) | false alarms (clean) | fidelity | DN honest | DN flagged tool faults | receiver reported tool fault | cost $ mean | turns |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(cs):
        c = cs[key]
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {c['trials']} | {fmt(c['wrong_acts_induced'])} | {fmt(c['wrong_acts_clean'])} | {fmt(c['caught_before_act'])} | "
                     f"{fmt(c['asked_induced'])} | {fmt(c['false_alarms_clean'])} | {fmt(c['fidelity'])} | {fmt(c['dn_honest'])} | {fmt(c['dn_flag_tool'])} | "
                     f"{fmt(c['receiver_reported_tool'])} | {c['cost_usd_mean']} | {c['receiver_turns_mean']} |")
    lines += ["", "Tests (per model; Fisher's exact):"]
    for m, t in summary["tests"].items():
        for name, v in t.items():
            lines.append(f"- {m}: {name}: " + ", ".join(f"{k}={v[k]}" for k in v))
    # per handover: the tag per cell, block 2
    arms = sorted({r["arm"] for r in rows}); 
    for block in sorted({r["block"] for r in rows}):
        hs = sorted({r["handover"] for r in rows if r["block"] == block})
        cols = [(a, m) for a in arms for m in models if (block, a, m) in cs]
        lines += ["", f"Block {block}, one row per handover; the cell shows repeats as outcomes (ok, WRONG, asked, held): rb-rej / rb-ok marks the first readback.",
                  "| handover | " + " | ".join(f"{a}-{m[:2]}" for a, m in cols) + " |", "|---|" + "---|" * len(cols)]
        for h in hs:
            cells_txt = []
            for a, m in cols:
                rs = [r for r in rows if r["block"] == block and r["handover"] == h and r["arm"] == a and r["model"] == m]
                tags = []
                for r in sorted(rs, key=lambda r: r["repeat"]):
                    tag_ = "held" if r["held"] else "asked" if r["asked"] else ("WRONG" if r["wrong_act"] else "ok" if r["acted"] else "none")
                    if r["readback_checked"]:
                        tag_ = ("rej " if r["readback_rejected"] else "ok ") + tag_
                    tags.append(tag_)
                cells_txt.append(", ".join(tags))
            lines.append(f"| {h} | " + " | ".join(cells_txt) + " |")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:len(cs) + 2]))
    for m, t in summary["tests"].items():
        for name, v in t.items():
            print(f"- {m}: {name}: " + ", ".join(f"{k}={v[k]}" for k in v))
    print(f"wrote {out_dir}/summary.json and summary.md ({len(rows)} trials)")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default=None); ap.add_argument("--only", default=""); ap.add_argument("--level", type=int, default=None)
    a = ap.parse_args(argv)
    analyse(a.tag, a.only, a.level)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
