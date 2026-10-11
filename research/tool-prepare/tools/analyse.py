#!/usr/bin/env python3
"""Aggregate grade.json files into results/summary.json and results/summary.md, with intervals and the pre-registered tests.

  python3 tools/analyse.py [--tag NAME] [--only SUBSTR] [--exclude SUBSTR]     # --tag writes results/<NAME>/ instead of results/
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

BLOCK_NAME = {0: "the sender's draft", 1: "the receiver and the call", 2: "the tool"}

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


def fmt(r: dict | None) -> str:
    if not r or not r["n"]:
        return "0 / 0"
    return f"{r['k']} / {r['n']} ({100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f})"


def mean(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None

# ----------------------------------------------------------------------------------------------------- cells

def cell_summary(rows: list[dict]) -> dict:
    induced = [r for r in rows if r["kind"] in ("induced", "planted")]
    clean = [r for r in rows if r["kind"] == "clean"]
    tool = [r for r in rows if r["kind"] == "tool"]
    acted = [r for r in rows if r["acted"]]
    fid = [r for r in rows if r["fidelity"] is not None and r["kind"] != "tool"]
    honest = [r for r in rows if r["dn_honest"] is not None]
    checked_rb = [r for r in rows if r["readback_checked"]]
    clean_checked = [r for r in clean if r["readback_checked"]]
    two = [r for r in rows if r.get("prepared") is not None]
    relayed = [r for r in rows if r.get("relay_mismatch") is not None]
    committed = [r for r in rows if r.get("committed")]
    c = {
        "trials": len(rows), "induced": len(induced), "clean": len(clean), "tool": len(tool),
        "wrong_acts_induced": rate(sum(r["wrong_act"] for r in induced), len(induced)),
        "wrong_acts_clean": rate(sum(r["wrong_act"] for r in clean), len(clean)),
        "wrong_acts_tool": rate(sum(r["wrong_act"] for r in tool), len(tool)),
        "wrong_acts_tool_prepare": rate(sum(r["wrong_act"] for r in tool if r.get("tool_fault_at") == "prepare"), len([r for r in tool if r.get("tool_fault_at") == "prepare"])),
        "wrong_acts_tool_commit": rate(sum(r["wrong_act"] for r in tool if r.get("tool_fault_at") == "commit"), len([r for r in tool if r.get("tool_fault_at") == "commit"])),
        "caught_before_act": rate(sum(r["caught_before_act"] for r in induced), len(induced)),
        "caught_tool_prepare": rate(sum(r["caught_before_act"] for r in tool if r.get("tool_fault_at") == "prepare"), len([r for r in tool if r.get("tool_fault_at") == "prepare"])),
        "caught_by_receiver": sum(1 for r in rows if r.get("caught_by") == "receiver"), "caught_by_sender": sum(1 for r in rows if r.get("caught_by") == "sender"),
        "asked_induced": rate(sum(r["asked"] for r in induced), len(induced)),
        "asked_clean": rate(sum(r["asked"] for r in clean), len(clean)),
        "asked_about_date": sum(r["asked_about_date"] for r in rows),
        "did_nothing": sum(1 for r in rows if not r["acted"] and not r["asked"] and not r["held"]),
        "false_alarms_clean": rate(sum(bool(r["false_alarm"]) for r in clean_checked), len(clean_checked)),
        "rejected_clean": rate(sum(r["readback_rejected"] for r in clean_checked), len(clean_checked)),
        "false_alarms_all": rate(sum(bool(r["false_alarm"]) for r in checked_rb), len(checked_rb)),
        "held_induced": rate(sum(r["held"] for r in induced), len(induced)),
        "held_clean": rate(sum(r["held"] for r in clean), len(clean)),
        "fidelity": rate(sum(r["fidelity"] for r in fid), len(fid)),
        "rb_covers_act": rate(sum(bool(r.get("rb_covers_act")) for r in rows if r.get("rb_covers_act") is not None), len([r for r in rows if r.get("rb_covers_act") is not None])),
        "dn_honest": rate(sum(r["dn_honest"] for r in honest), len(honest)),
        "dn_flag_tool": rate(sum(bool(r["dn_flag"]) for r in tool), len(tool)),
        "dn_flag_tool_commit": rate(sum(bool(r["dn_flag"]) for r in tool if r.get("tool_fault_at") == "commit" and r["acted"]), len([r for r in tool if r.get("tool_fault_at") == "commit" and r["acted"]])),
        "receiver_reported_tool": rate(sum(bool(r["receiver_reported"]) for r in tool if r["acted"]), len([r for r in tool if r["acted"]])),
        "dn_false_flag": rate(sum(bool(r["dn_flag"]) for r in acted if r["act_correct"] and r["dn_checked"]), len([r for r in acted if r["act_correct"] and r["dn_checked"]])),
        "prepared": rate(sum(bool(r.get("prepared")) for r in two), len(two)),
        "relay_mismatch": rate(sum(bool(r.get("relay_mismatch")) for r in relayed), len(relayed)),
        "relay_text_differs": rate(sum(bool(r.get("relay_text_differs")) for r in relayed), len(relayed)),
        "commit_before_confirm": rate(sum(bool(r.get("commit_before_confirm")) for r in two), len(two)),
        "commit_before_confirm_of_committed": rate(sum(bool(r.get("commit_before_confirm")) for r in committed), len(committed)),
        "abandons": sum(r.get("abandons") or 0 for r in rows), "prepares_mean": mean([r.get("prepares") for r in two]),
        "acted": len(acted), "held": sum(r["held"] for r in rows), "outside_tool": sum(1 for r in acted if not r["through_tool"]),
        "status_not_ok": sum(1 for r in rows if r["status"] != "ok"),
        "cost_usd_mean": mean([r.get("cost_usd") for r in rows]),
        "receiver_turns_mean": round(sum(r["receiver_turns"] for r in rows) / len(rows), 2) if rows else None,
        "brief_tokens_mean": round(sum(r["brief_tokens"] for r in rows) / len(rows)) if rows else None,
        "traffic_tokens_mean": round(sum(sum(r["traffic_tokens"].values()) for r in rows) / len(rows)) if rows else None,
        "output_tokens_mean": round(sum(r["usage"]["output"] for r in rows) / len(rows)) if rows else None,
        "cache_read_mean": round(sum(r["usage"]["cache_read"] for r in rows) / len(rows)) if rows else None,
        "denials": sum(r["denials"] for r in rows),
    }
    return c


def tests(cells: dict, models: list[str]) -> dict:
    out = {}
    def cell(block, arm, model):
        return cells.get((block, arm, model))
    for m in models:
        t = {}
        b1 = {x: cell(1, x, m) for x in "ACDEPQ"}
        if b1["Q"] and b1["C"]:
            q, c = b1["Q"]["wrong_acts_induced"], b1["C"]["wrong_acts_induced"]
            t["H1a Q fewer wrong acts than C, block 1 induced (one-sided)"] = {"Q": fmt(q), "C": fmt(c), "p": fisher(q["k"], q["n"] - q["k"], c["k"], c["n"] - c["k"], "less")}
        if b1["Q"] and b1["D"]:
            q, d = b1["Q"]["held_induced"], b1["D"]["held_induced"]
            t["H1b Q held less often than D, block 1 induced (one-sided)"] = {"Q": fmt(q), "D": fmt(d), "p": fisher(q["k"], q["n"] - q["k"], d["k"], d["n"] - d["k"], "less")}
        if b1["Q"] and b1["E"]:
            t["H2 Q against E, wrong acts, block 1 induced (intervals)"] = {"Q": fmt(b1["Q"]["wrong_acts_induced"]), "E": fmt(b1["E"]["wrong_acts_induced"])}
        for arm in "ADPQ":
            c2 = cell(2, arm, m)
            if c2:
                t[f"H3 block 2, arm {arm}: wrong acts by injection point"] = {"at prepare": fmt(c2["wrong_acts_tool_prepare"]), "at commit": fmt(c2["wrong_acts_tool_commit"]),
                                                                            "caught at prepare": fmt(c2["caught_tool_prepare"]), "of which by the receiver": c2["caught_by_receiver"], "DN flagged (commit faults, acted)": fmt(c2["dn_flag_tool_commit"])}
        if b1["D"]:
            for arm in "PQ":
                if b1[arm]:
                    t[f"H4 {arm} against D, block 1 (intervals; cost and turns)"] = {
                        f"{arm} wrong, induced": fmt(b1[arm]["wrong_acts_induced"]), "D wrong, induced": fmt(b1["D"]["wrong_acts_induced"]),
                        f"{arm} held, induced": fmt(b1[arm]["held_induced"]), "D held, induced": fmt(b1["D"]["held_induced"]),
                        f"{arm} cost $": b1[arm]["cost_usd_mean"], "D cost $": b1["D"]["cost_usd_mean"],
                        f"{arm} turns": b1[arm]["receiver_turns_mean"], "D turns": b1["D"]["receiver_turns_mean"]}
        for arm in "PQ":
            if b1[arm]:
                f = b1[arm]["false_alarms_clean"]
                t[f"H5 {arm} false alarms on clean, block 1 (upper bound under 5%)"] = {arm: fmt(f), "holds": f["hi"] < 0.05}
        if b1["P"]:
            t["H6 P: discipline against enforcement, block 1"] = {"commit before confirm": fmt(b1["P"]["commit_before_confirm"]), "relay mismatch": fmt(b1["P"]["relay_mismatch"]),
                                                               "relay text differs": fmt(b1["P"]["relay_text_differs"])}
        if cell(2, "P", m):
            t["H6 P: discipline against enforcement, block 2"] = {"commit before confirm": fmt(cell(2, "P", m)["commit_before_confirm"]), "relay mismatch": fmt(cell(2, "P", m)["relay_mismatch"])}
        for arm in "PQ":
            c0 = cell(0, arm, m)
            if c0:
                t[f"Block 0 regression, arm {arm}"] = {"wrong acts, planted": fmt(c0["wrong_acts_induced"]), "caught": fmt(c0["caught_before_act"]), "asked": fmt(c0["asked_induced"]),
                                                      "wrong acts, clean": fmt(c0["wrong_acts_clean"])}
        out[m] = t
    return out


def analyse(tag: str | None, only: str = "", exclude: str = "") -> None:
    rows = []
    for trial in sorted(C.TRIALS.iterdir()):
        g = trial / "grade.json"
        if g.exists() and only in trial.name and not (exclude and exclude in trial.name):
            rows.append(C.read_json(g))
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
    lines = ["| block | arm | model | trials | wrong acts, induced or planted | wrong acts, clean | wrong acts, tool faults | caught before act | held (induced) | asked (induced) | false alarms (clean) | relay mismatch | commit before confirm | DN flagged tool faults | cost $ mean | turns |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(cs):
        c = cs[key]
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {c['trials']} | {fmt(c['wrong_acts_induced'])} | {fmt(c['wrong_acts_clean'])} | {fmt(c['wrong_acts_tool'])} | "
                     f"{fmt(c['caught_before_act'])} | {fmt(c['held_induced'])} | {fmt(c['asked_induced'])} | {fmt(c['false_alarms_clean'])} | {fmt(c['relay_mismatch'])} | "
                     f"{fmt(c['commit_before_confirm'])} | {fmt(c['dn_flag_tool'])} | {c['cost_usd_mean']} | {c['receiver_turns_mean']} |")
    lines += ["", "Tests (per model; Fisher's exact where named):"]
    for m, t in summary["tests"].items():
        for name, v in t.items():
            lines.append(f"- {m}: {name}: " + ", ".join(f"{k}={v[k]}" for k in v))
    arms = sorted({r["arm"] for r in rows})
    for block in sorted({r["block"] for r in rows}):
        hs = sorted({r["handover"] for r in rows if r["block"] == block})
        cols = [(a, m) for a in arms for m in models if (block, a, m) in cs]
        lines += ["", f"Block {block}, {BLOCK_NAME[block]}, one row per handover; the cell shows repeats as outcomes (ok, WRONG, asked, held, none): rej / ok marks the first readback or prepared statement.",
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
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default=None); ap.add_argument("--only", default="")
    ap.add_argument("--exclude", default="", help="skip trials whose id contains this (the pilot's -p)")
    a = ap.parse_args(argv)
    analyse(a.tag, a.only, a.exclude)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
