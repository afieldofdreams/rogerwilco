#!/usr/bin/env python3
"""Aggregate grade.json files into results/summary.json and results/summary.md: cells, proportions with Clopper-Pearson
95% intervals, medians, and the pre-registered tests (Fisher's exact, pure Python).

  python3 tools/analyse.py [--tag NAME] [--only SUBSTR] [--suffix -p] [--exclude -s,-p]     # --tag writes results/<NAME>/

Cells are block x arm x model x K. Tests are per model; nothing is pooled across models.
"""
from __future__ import annotations

import argparse
import json
import sys
from math import comb
from pathlib import Path
from statistics import median

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
    def solve(target, upto, rising=False):
        lo, hi = 0.0, 1.0
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
    """Fisher's exact test on [[a, b], [c, d]]. 'greater' tests that row 1's rate (a/(a+b)) is higher than row 2's; 'less' that it is lower."""
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
    if not r or not r["n"]:
        return "0 / 0"
    return f"{r['k']} / {r['n']} ({100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f})"


def med(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(median(xs), 1) if xs else None

# ----------------------------------------------------------------------------------------------------- cells

def cell_summary(rows: list[dict]) -> dict:
    n = len(rows)
    Kmax = max(r["K"] for r in rows)
    sizes = {str(h): med([r["sizes"].get(str(h)) for r in rows]) for h in range(1, Kmax + 2)}
    correct_forwards = sum(r["correct_forwards"] for r in rows)
    false_alarms = sum(len(r["false_alarms"]) for r in rows)
    return {
        "chains": n,
        "correct_act": rate(sum(r["outcome"] == "correct" for r in rows), n),
        "as_expected": rate(sum(r["as_expected"] for r in rows), n),
        "wrong_act": rate(sum(r["outcome"] == "wrong" for r in rows), n),
        "asked": rate(sum(r["asked"] for r in rows), n),
        "asked_at": sorted({f"hop {r['asked_at']}" for r in rows if r["asked"]}),
        "held": rate(sum(r["held"] for r in rows), n),
        "not_done": rate(sum(r["outcome"] == "not done" for r in rows), n),
        "stalled": sum(r["stalled"] for r in rows),
        "harness_faults": sum(bool(r["harness_fault"]) for r in rows),
        "all_fields_at_payer": rate(sum(r["all_fields_at_payer"] for r in rows), n),
        "any_drift": rate(sum(r["any_drift"] for r in rows), n),
        "drifts": [f"{r['id']}: " + "; ".join(f"hop {h}: {','.join(v)}" for h, v in r["drift"].items() if v) for r in rows if r["any_drift"]],
        "loss": rate(sum((not r["all_fields_at_payer"]) or r["asked"] or r["outcome"] == "not done" for r in rows), n),
        "caught": sum(len(r["caught"]) for r in rows),
        "false_alarms_over_correct_forwards": rate(false_alarms, correct_forwards),
        "refusals": sum(len(r["refusals"]) for r in rows),
        "size_median_by_hop": sizes,
        "traffic_median": med([r["traffic_tokens"] for r in rows]),
        "model_turns_mean": round(sum(r["model_turns"] for r in rows) / n, 2),
        "sessions_mean": round(sum(r["sessions"] for r in rows) / n, 2),
        "cost_usd_mean": round(sum(r.get("cost_usd") or 0 for r in rows) / n, 4),
        "cost_usd_total": round(sum(r.get("cost_usd") or 0 for r in rows), 4),
        "dn_ok": rate(sum(bool(r["dn_ok"]) for r in rows if r["dn_checked"]), sum(bool(r["dn_checked"]) for r in rows)),
        "flags": [f for r in rows for f in r["flags"]],
    }


def tests(cells: dict, models: list[str]) -> dict:
    out = {}
    def get(block, arm, model, K=2):
        return cells.get((block, arm, model, K))
    for m in models:
        t = {}
        f, r, l = get(1, "F", m), get(1, "R", m), get(1, "L", m)
        if f and r:
            a, b = r["correct_act"], f["correct_act"]
            t["H1 block 1: more correct acts in R than F (one-sided)"] = {"R": fmt(a), "F": fmt(b), "p": round(fisher(a["k"], a["n"] - a["k"], b["k"], b["n"] - b["k"], "greater"), 4)}
            a, b = r["all_fields_at_payer"], f["all_fields_at_payer"]
            t["H2 block 1: every field at the payer in more chains in R than F (one-sided)"] = {"R": fmt(a), "F": fmt(b), "p": round(fisher(a["k"], a["n"] - a["k"], b["k"], b["n"] - b["k"], "greater"), 4)}
        if r:
            fa = r["false_alarms_over_correct_forwards"]
            t["H4 R false alarms over correct forwards (upper bound under 5%)"] = {"R": fmt(fa), "holds": fa["n"] > 0 and fa["hi"] < 0.05}
        f2, r2 = get(2, "F", m), get(2, "R", m)
        if f2 and r2:
            a, b = r2["as_expected"], f2["as_expected"]
            t["H6 block 2: more chains end as expected (the correct act, or the ask where the log does not cover the item) in R than F (one-sided)"] = {"R": fmt(a), "F": fmt(b), "p": round(fisher(a["k"], a["n"] - a["k"], b["k"], b["n"] - b["k"], "greater"), 4)}
        if l and r:
            a, b = l["correct_act"], r["correct_act"]
            t["H8 block 1: L against R on correct acts (two-sided)"] = {"L": fmt(a), "R": fmt(b), "p": round(fisher(a["k"], a["n"] - a["k"], b["k"], b["n"] - b["k"]), 4)}
            a, b = l["all_fields_at_payer"], r["all_fields_at_payer"]
            t["H8 block 1: L against R on every field at the payer (two-sided)"] = {"L": fmt(a), "R": fmt(b), "p": round(fisher(a["k"], a["n"] - a["k"], b["k"], b["n"] - b["k"]), 4)}
        for arm in ("F", "A", "L", "R"):
            c = get(1, arm, m)
            if c:
                s = c["size_median_by_hop"]
                first, last = s.get("1"), s.get(str(c and 3))
                if first is not None and last is not None:
                    t[f"H3 block 1 {arm}: median size hop 1 -> hop K+1"] = {"hop1": first, "hopK+1": last, "sign": "grows" if last > first else "flat" if last == first else "shrinks"}
        for arm in ("F", "R"):
            byK = {K: cells[(3, arm, m, K)]["correct_act"] for K in (1, 2, 3, 5) if (3, arm, m, K) in cells}
            if byK:
                t[f"H7 block 3 {arm}: correct acts by K"] = {str(K): fmt(v) for K, v in byK.items()}
        out[m] = t
    return out

# ----------------------------------------------------------------------------------------------------- output

def analyse(tag: str | None, only: str = "", suffix: str = "", exclude: str = "") -> None:
    rows = []
    skip = [x for x in exclude.split(",") if x]
    for trial in sorted(C.TRIALS.iterdir()):
        g = trial / "grade.json"
        if g.exists() and only in trial.name and (not suffix or trial.name.endswith(suffix)) and not any(trial.name.endswith(x) for x in skip):
            rows.append(C.read_json(g))
    out_dir = C.RESULTS / tag if tag else C.RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = {}
    for r in rows:
        cells.setdefault((r["block"], r["arm"], r["model"], r["K"]), []).append(r)
    models = sorted({r["model"] for r in rows})
    cs = {key: cell_summary(rs) for key, rs in cells.items()}
    summary = {"rows": rows, "cells": {f"B{k[0]}-{k[1]}-{k[2]}-k{k[3]}": v for k, v in sorted(cs.items())}, "tests": tests(cs, models),
               "tokenizer": C.TOKENIZER, "chains": len(rows), "cost_usd_total": round(sum(r.get("cost_usd") or 0 for r in rows), 4)}
    Kmax = max((r["K"] for r in rows), default=2)
    hop_cols = " | ".join(f"size hop {h}" for h in range(1, Kmax + 2))
    levels = sorted({r.get("harden", 0) for r in rows})
    lines = [f"Ladder level(s) in this set: {', '.join(str(x) for x in levels)}.", "", f"| block | arm | model | K | chains | correct act | as expected | wrong | asked | held | not done | every field at payer | any drift | loss (field missing, asked or not done) | caught | false alarms / correct forwards | {hop_cols} | traffic median | turns mean | cost $ mean | harness faults |",
             "|" + "---|" * (20 + Kmax + 1)]
    for key in sorted(cs):
        c = cs[key]
        sizes = " | ".join(str(c["size_median_by_hop"].get(str(h), "")) for h in range(1, Kmax + 2))
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {c['chains']} | {fmt(c['correct_act'])} | {fmt(c['as_expected'])} | {fmt(c['wrong_act'])} | {fmt(c['asked'])} | "
                     f"{fmt(c['held'])} | {fmt(c['not_done'])} | {fmt(c['all_fields_at_payer'])} | {fmt(c['any_drift'])} | {fmt(c['loss'])} | {c['caught']} | "
                     f"{fmt(c['false_alarms_over_correct_forwards'])} | {sizes} | {c['traffic_median']} | {c['model_turns_mean']} | {c['cost_usd_mean']} | {c['harness_faults']} |")
    lines += ["", f"{len(rows)} chains, total cost ${summary['cost_usd_total']}, tokens counted with {C.TOKENIZER}.", "", "Tests (per model; Fisher's exact, pure Python; Clopper-Pearson 95% intervals):"]
    for m, t in summary["tests"].items():
        for name, v in t.items():
            lines.append(f"- {m}: {name}: " + ", ".join(f"{k}={v[k]}" for k in v))
    lines += ["", "Per chain (sizes are tokens of the message delivered to each hop; fields are the record's slots at the payer):",
              "| chain | outcome | expected | fields missing at payer | drift (hop: fields) | refusals (hop what kind) | sizes | traffic | turns | cost $ | status |", "|" + "---|" * 11]
    for r in sorted(rows, key=lambda r: r["id"]):
        drift = "; ".join(f"{h}: {','.join(v)}" for h, v in r["drift"].items() if v) or ""
        refs = "; ".join(f"{x['hop']} {x['what']} {x['kind']}" for x in r["refusals"]) or ""
        sizes = "/".join(str(r["sizes"].get(str(h), "")) for h in range(1, r["K"] + 2))
        lines.append(f"| {r['id']} | {r['outcome']} | {r['expected']} | {','.join(r['fields_missing_at_payer'])} | {drift} | {refs} | {sizes} | {r['traffic_tokens']} | {r['model_turns']} | {r['cost_usd']} | {r['status']} |")
    drifts = [d for c in cs.values() for d in c["drifts"]]
    if drifts:
        lines += ["", "Every drift, by chain and hop:"] + [f"- {d}" for d in drifts]
    flags = [f"{c_key}: {f}" for c_key, c in cs.items() for f in c["flags"]]
    if flags:
        lines += ["", "Flags (protocol deviations by an agent, not harness faults):"] + [f"- {f}" for f in flags]
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:len(cs) + 2]))
    for m, t in summary["tests"].items():
        for name, v in t.items():
            print(f"- {m}: {name}: " + ", ".join(f"{k}={v[k]}" for k in v))
    print(f"wrote {out_dir}/summary.json and summary.md ({len(rows)} chains)")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default=None); ap.add_argument("--only", default="")
    ap.add_argument("--suffix", default="", help="keep only chains whose id ends with this (the pilot's -p)")
    ap.add_argument("--exclude", default="", help="skip chains whose id ends with any of these, comma-separated")
    a = ap.parse_args(argv)
    analyse(a.tag, a.only, a.suffix, a.exclude)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
