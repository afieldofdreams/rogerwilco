#!/usr/bin/env python3
"""Study 11: counts, intervals and the registered tests, from the graded files. Re-runnable with no key.

    analyse.py --set pilot|main        writes results/[pilot/]summary.json and summary.md

Nothing is pooled across reviewer models. A rate is always "k of n" with its exact (Clopper-Pearson) 95% interval.
A contrast between two cells is made on the cases both cells hold, case by case (exact McNemar), never on two
unrelated samples. Statistics are study 10's functions, standard library only.
"""
from __future__ import annotations

import argparse
import json
from math import comb

import common as C
import grade as G

FAULT_CLASSES = ["literal", "record"]


def cp_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Clopper-Pearson exact interval for k of n (study 6's analyse.py)."""
    if n == 0:
        return (0.0, 1.0)

    def cdf(p, upto):
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(upto + 1))

    def solve(target, upto, lo=0.0, hi=1.0):
        for _ in range(60):
            mid = (lo + hi) / 2
            if cdf(mid, upto) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(1 - alpha / 2, k - 1)
    upper = 1.0 if k == n else solve(alpha / 2, k)
    return (round(lower, 4), round(upper, 4))


def mcnemar(b: int, c: int, alternative: str = "two-sided") -> float:
    """Exact McNemar on the discordant pairs. b = pairs where only the first cell stopped the act, c = only the second.
    'less': the first cell stops fewer (evidence is c large). 'greater': the first stops more."""
    n = b + c
    if n == 0:
        return 1.0
    tail_c = sum(comb(n, i) for i in range(c, n + 1)) / 2 ** n         # P(X >= c)
    tail_b = sum(comb(n, i) for i in range(b, n + 1)) / 2 ** n         # P(X >= b)
    if alternative == "less":
        return min(1.0, tail_c)
    if alternative == "greater":
        return min(1.0, tail_b)
    return min(1.0, 2 * min(tail_b, tail_c))


def holm(ps: dict) -> dict:
    """Holm step-down adjusted p values for a family {key: p}."""
    order = sorted(ps, key=lambda k: ps[k])
    m, out, running = len(order), {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * ps[k]))
        out[k] = running
    return out


def stat(k: int, n: int) -> dict:
    lo, hi = cp_interval(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [lo, hi]}


def xn(s: dict) -> str:
    if not s["n"]:
        return "none"
    if s["k"] == 0:
        return f"0 of {s['n']} (at most {100 * s['ci95'][1]:.1f}%)"
    if s["k"] == s["n"]:
        return f"{s['k']} of {s['n']} (at least {100 * s['ci95'][0]:.1f}%)"
    return f"{s['k']} of {s['n']} ({100 * s['rate']:.1f}%, {100 * s['ci95'][0]:.1f} to {100 * s['ci95'][1]:.1f})"


def load(set_: str) -> dict:
    out = C.RESULTS / ("pilot" if set_ == "pilot" else "")
    read = lambda p: [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.exists() else []  # noqa: E731
    ledger = [e for e in read(C.RESULTS / "ledger.jsonl") if e.get("phase") == set_]
    return {"plan": C.read_json(C.DATA / f"plan-{set_}.json"), "grades": read(out / "grades.jsonl"), "stage1": read(out / "stage1-grades.jsonl"),
            "ledger": ledger, "out": out}


def stopped(g: dict) -> bool:
    return g["outcome"] in G.STOPPED


def cell_stats(grades: list[dict], cell: str, reviewer: str) -> dict:
    gs = [g for g in grades if g["cell"] == cell and g["reviewer"] == reviewer]
    f = [g for g in gs if g["fault"]]
    c = [g for g in gs if not g["fault"]]
    out = {"cell": cell, "reviewer": reviewer, "n": len(gs),
           "faulted": {"n": len(f), "outcomes": _count(f), "stopped": stat(sum(stopped(g) for g in f), len(f)),
                       "caught": stat(sum(g["outcome"] == "caught" for g in f), len(f)), "released": stat(sum(g["outcome"] == "miss" for g in f), len(f))},
           "clean": {"n": len(c), "outcomes": _count(c), "false_holds": stat(sum(g["outcome"] in G.FALSE for g in c), len(c)),
                     "false_unconfirmed": stat(sum(g["outcome"] == "false_unconfirmed" for g in c), len(c))},
           "by_class": {}, "by_fault": {}}
    for k in FAULT_CLASSES:
        sub = [g for g in f if g["fault_class"] == k]
        out["by_class"][k] = {"stopped": stat(sum(stopped(g) for g in sub), len(sub)), "caught": stat(sum(g["outcome"] == "caught" for g in sub), len(sub)),
                              "released": stat(sum(g["outcome"] == "miss" for g in sub), len(sub))}
    for k in sorted({g["fault"] for g in f}):
        sub = [g for g in f if g["fault"] == k]
        out["by_fault"][k] = {"stopped": stat(sum(stopped(g) for g in sub), len(sub)), "outcomes": _count(sub)}
    toks = [(g.get("tokens") or {}) for g in gs]
    tin = [sum(t.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")) for t in toks]
    out["input_tokens_mean"] = round(sum(tin) / len(tin)) if tin else None
    out["user_chars_mean"] = round(sum(g.get("user_chars") or 0 for g in gs) / len(gs)) if gs else None
    out["cost_mean"] = round(sum(g.get("cost") or 0 for g in gs) / len(gs), 5) if gs else None
    out["unparseable"] = sum(g["outcome"] == "unparseable" for g in gs)
    return out


def _count(gs: list[dict]) -> dict:
    out: dict[str, int] = {}
    for g in gs:
        out[g["outcome"]] = out.get(g["outcome"], 0) + 1
    return dict(sorted(out.items()))


def contrast(grades: list[dict], reviewer: str, a: str, b: str, which: str = "faulted", klass: str | None = None,
             alternative: str = "less") -> dict:
    """Cell a against cell b on the cases both hold. For faulted cases the event is 'the act was stopped'; for clean
    cases it is 'the act was held' (a false hold). alternative 'less': a has fewer events than b."""
    def pick(cell):
        out = {}
        for g in grades:
            if g["cell"] != cell or g["reviewer"] != reviewer or g["outcome"] == "unparseable":
                continue
            if which == "faulted" and (not g["fault"] or (klass and g["fault_class"] != klass)):
                continue
            if which == "clean" and g["fault"]:
                continue
            out[g["case"]] = stopped(g) if which == "faulted" else (g["outcome"] in G.FALSE)
        return out
    ga, gb = pick(a), pick(b)
    both = sorted(set(ga) & set(gb))
    only_a = sum(ga[k] and not gb[k] for k in both)
    only_b = sum(gb[k] and not ga[k] for k in both)
    return {"reviewer": reviewer, "a": a, "b": b, "which": which, "class": klass, "pairs": len(both),
            "a_events": stat(sum(ga[k] for k in both), len(both)), "b_events": stat(sum(gb[k] for k in both), len(both)),
            "only_a": only_a, "only_b": only_b, "alternative": alternative, "p": round(mcnemar(only_a, only_b, alternative), 6)}


def stage1_tables(d: dict) -> dict:
    """What clerk's texts carried, and what the reviewers did with them, split by whether the evidence was carried."""
    s1 = {r["sid"]: r for r in d["stage1"]}
    out = {}
    for kind in ("summary", "extract"):
        recs = [r for r in d["stage1"] if r["kind"] == kind]
        faulted = [r for r in recs if r["fault"]]
        tab = {"texts": len(recs), "words_mean": round(sum(r["words"] for r in recs) / len(recs), 1) if recs else None,
               "carried": stat(sum(bool(r["carries"]) for r in faulted), len(faulted)), "carried_by_fault": {}, "reviewers": {}}
        for f in sorted({r["fault"] for r in faulted}):
            sub = [r for r in faulted if r["fault"] == f]
            tab["carried_by_fault"][f] = stat(sum(bool(r["carries"]) for r in sub), len(sub))
        for m in d["plan"]["reviewers"]:
            gs = [g for g in d["grades"] if g["cell"] == f"W-{kind}" and g["reviewer"] == m and g["fault"]]
            yes = [g for g in gs if s1.get(f"{kind}-{g['case']}", {}).get("carries")]
            no = [g for g in gs if not s1.get(f"{kind}-{g['case']}", {}).get("carries")]
            tab["reviewers"][m] = {"stopped_when_carried": stat(sum(stopped(g) for g in yes), len(yes)), "released_when_carried": stat(sum(g["outcome"] == "miss" for g in yes), len(yes)),
                                   "stopped_when_not_carried": stat(sum(stopped(g) for g in no), len(no)), "released_when_not_carried": stat(sum(g["outcome"] == "miss" for g in no), len(no)),
                                   "caught_when_not_carried": sum(g["outcome"] == "caught" for g in no)}
        out[kind] = tab
    return out


def costs(d: dict) -> dict:
    by: dict[str, dict] = {}
    for e in d["ledger"]:
        k = f"{e.get('model')}:{e.get('kind')}"
        b = by.setdefault(k, {"calls": 0, "cost": 0.0, "errors": 0})
        b["calls"] += 1
        b["cost"] += e.get("cost") or 0.0
        b["errors"] += 1 if e.get("error") else 0
    for b in by.values():
        b["cost"] = round(b["cost"], 4)
    return {"by_model_and_kind": dict(sorted(by.items())), "total_list_price": round(sum(b["cost"] for b in by.values()), 2),
            "calls": sum(b["calls"] for b in by.values())}


def envelope(cells: dict, reviewer: str, per: int = 10000, fault_rates=(0.001, 0.01, 0.05)) -> list[dict]:
    """Arithmetic, not measurement: what the measured rates imply for a stream of `per` acts at an assumed fault rate.
      review every act from the file         releases p*per*(1 - stop rate on the file), holds (1-p)*per*(false-hold rate on the file)
      code clears what agrees with the typed records; the reviewer sees only what code holds, on the check sheet
                                              releases p*per*(1 - stop rate on the check sheet), holds no clean act, reads p*per acts
    The second line rests on the fixture: here code decides all six fault kinds from the typed records exactly."""
    out = []
    f, c = cells.get(("W-fileM", reviewer)), cells.get(("W-card", reviewer))
    if not f or not c or not f["faulted"]["n"] or not c["faulted"]["n"]:
        return out
    sf, hf = f["faulted"]["stopped"]["rate"], f["clean"]["false_holds"]["rate"] or 0.0
    sc, hc = c["faulted"]["stopped"]["rate"], c["clean"]["false_holds"]["rate"] or 0.0
    for p in fault_rates:
        out.append({"fault_rate": p, "per": per,
                    "review_all_from_file": {"reviews": per, "faults_released": round(p * per * (1 - sf), 2), "clean_acts_held": round((1 - p) * per * hf, 1)},
                    "review_all_on_check_sheet": {"reviews": per, "faults_released": round(p * per * (1 - sc), 2), "clean_acts_held": round((1 - p) * per * hc, 1)},
                    "code_first_then_check_sheet": {"reviews": round(p * per, 1), "faults_released": round(p * per * (1 - sc), 2), "clean_acts_held": 0.0}})
    return out

# The registered hypotheses are added by hypotheses() below, written with the protocol.


def summary(set_: str, hypotheses=None) -> dict:
    d = load(set_)
    cells = {}
    for cell in d["plan"]["cells"]:
        for m in d["plan"]["reviewers"]:
            cells[(cell, m)] = cell_stats(d["grades"], cell, m)
    s = {"set": set_, "trials_planned": len(d["plan"]["trials"]), "trials_graded": len(d["grades"]),
         "cells": [cells[k] for k in sorted(cells)], "stage1": stage1_tables(d), "costs": costs(d),
         "envelope_arithmetic": {m: envelope(cells, m) for m in d["plan"]["reviewers"]}}
    if hypotheses and set_ == "main":
        s["hypotheses"] = hypotheses(d["grades"], d)
    return s


def markdown(s: dict) -> str:
    L = [f"# Study 11, the review envelope: {s['set']} run", "",
         f"{s['trials_graded']} of {s['trials_planned']} planned trials graded. Rates are k of n with exact 95% intervals. "
         "Stopped means any HOLD on a faulted case; released means APPROVE on a faulted case.", ""]
    L += ["## Faulted cases: stopped, by cell and reviewer", "", "| Cell | Reviewer | Stopped | Named the planted reason | Released | Literal faults stopped | Record faults stopped |",
          "|---|---|---|---|---|---|---|"]
    for c in s["cells"]:
        if not c["faulted"]["n"]:
            continue
        L.append(f"| {c['cell']} | {C.MODELS[c['reviewer']]['name']} | {xn(c['faulted']['stopped'])} | {xn(c['faulted']['caught'])} | {xn(c['faulted']['released'])} | "
                 f"{xn(c['by_class']['literal']['stopped'])} | {xn(c['by_class']['record']['stopped'])} |")
    L += ["", "## Clean cases: held for nothing, by cell and reviewer", "", "| Cell | Reviewer | Held | of which HOLD unconfirmed | Mean input tokens | Mean list-price cost |", "|---|---|---|---|---|---|"]
    for c in s["cells"]:
        if not c["clean"]["n"]:
            continue
        L.append(f"| {c['cell']} | {C.MODELS[c['reviewer']]['name']} | {xn(c['clean']['false_holds'])} | {c['clean']['false_unconfirmed']['k']} | {c['input_tokens_mean']} | ${c['cost_mean']:.4f} |")
    L += ["", "## Outcomes by fault kind", "", "| Cell | Reviewer | Fault | Outcomes |", "|---|---|---|---|"]
    for c in s["cells"]:
        for f, v in c["by_fault"].items():
            if v["stopped"]["k"] != v["stopped"]["n"] or any(k != "caught" for k in v["outcomes"]):
                L.append(f"| {c['cell']} | {C.MODELS[c['reviewer']]['name']} | {f} | {v['outcomes']} |")
    L += ["", "Rows where every case was caught with the planted reason are left out.", ""]
    L += ["## Clerk's texts", ""]
    for kind, t in s["stage1"].items():
        L.append(f"**{kind}**: {t['texts']} texts, {t['words_mean']} words on average. Carried the evidence on faulted cases: {xn(t['carried'])}; by fault: "
                 + "; ".join(f"{f} {v['k']} of {v['n']}" for f, v in t["carried_by_fault"].items()) + ".")
        for m, r in t["reviewers"].items():
            L.append(f"- {C.MODELS[m]['name']}: evidence carried, stopped {xn(r['stopped_when_carried'])}; evidence not carried, stopped {xn(r['stopped_when_not_carried'])}, "
                     f"released {xn(r['released_when_not_carried'])}, named the planted reason anyway in {r['caught_when_not_carried']}.")
        L.append("")
    if s.get("hypotheses"):
        L += ["## Hypotheses", ""]
        for h in s["hypotheses"]:
            L.append(f"- **{h['id']}** {h['verdict']}: {h['line']}")
        L.append("")
    L += ["## What the rates imply for a stream of acts (arithmetic, not measurement)", ""]
    for m, rows in s["envelope_arithmetic"].items():
        for r in rows:
            a, b, c = r["review_all_from_file"], r["review_all_on_check_sheet"], r["code_first_then_check_sheet"]
            L.append(f"- {C.MODELS[m]['name']}, {r['per']:,} acts, {100 * r['fault_rate']:.1f}% faulted: reviewing every act from the file releases {a['faults_released']} faults and holds "
                     f"{a['clean_acts_held']} clean acts; every act on the check sheet releases {b['faults_released']} and holds {b['clean_acts_held']}; code first, then the check sheet "
                     f"for what code holds, means {c['reviews']} reviews, {c['faults_released']} released, no clean act held.")
    L += ["", "## Cost", "", f"{s['costs']['calls']} model calls, ${s['costs']['total_list_price']:.2f} at list price (Claude runs on the account's plan).", ""]
    for k, b in s["costs"]["by_model_and_kind"].items():
        L.append(f"- {k}: {b['calls']} calls, ${b['cost']:.2f}, {b['errors']} provider errors")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    try:
        from hypotheses import hypotheses
    except ImportError:
        hypotheses = None
    s = summary(a.set, hypotheses)
    out = C.RESULTS / ("pilot" if a.set == "pilot" else "")
    out.mkdir(parents=True, exist_ok=True)
    C.write_json(out / "summary.json", s)
    (out / "summary.md").write_text(markdown(s))
    print(f"wrote {out / 'summary.md'}")


if __name__ == "__main__":
    main()
