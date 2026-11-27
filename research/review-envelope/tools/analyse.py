#!/usr/bin/env python3
"""Study 11: counts, intervals and the registered tests, from the graded files. Re-runnable with no key.

    analyse.py --set pilot|main        writes results/[pilot/]summary.json and summary.md

Nothing is pooled across reviewer models. A rate is always "k of n" with its exact (Clopper-Pearson) 95% interval,
and n is every planned trial of the cell: an unparseable answer stays in the denominator and is in no numerator.
A contrast between two cells is made on the cases both cells hold, case by case (exact McNemar), never on two
unrelated samples. The hypotheses are computed only for the main run and only when every planned trial is graded.
Statistics are study 10's functions, standard library only.
"""
from __future__ import annotations

import argparse
import json
from math import comb

import build as B
import casefile as K
import common as C
import grade as G


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


def binom_tail(k: int, n: int) -> float:
    """P(X >= k) for X ~ Binomial(n, 1/2)."""
    return 1.0 if n == 0 else min(1.0, sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def mcnemar(b: int, c: int, alternative: str = "two-sided") -> float:
    """Exact McNemar on the discordant pairs. b = pairs where only the first cell has the event, c = only the second.
    'less': the first cell has fewer events (evidence is c large). 'greater': the first has more."""
    n = b + c
    if n == 0:
        return 1.0
    if alternative == "less":
        return binom_tail(c, n)
    if alternative == "greater":
        return binom_tail(b, n)
    return min(1.0, 2 * min(binom_tail(b, n), binom_tail(c, n)))


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
    return {"set": set_, "plan": C.read_json(C.DATA / f"plan-{set_}.json"), "grades": read(out / "grades.jsonl"),
            "stage1": read(out / "stage1-grades.jsonl"), "ledger": ledger, "out": out}


def stopped(g: dict) -> bool:
    return g["outcome"] in G.STOPPED


def held(g: dict) -> bool:
    return g["outcome"] in G.FALSE


def _count(gs: list[dict]) -> dict:
    out: dict[str, int] = {}
    for g in gs:
        out[g["outcome"]] = out.get(g["outcome"], 0) + 1
    return dict(sorted(out.items()))


def cell_stats(d: dict, cell: str, reviewer: str) -> dict:
    planned = [t for t in d["plan"]["trials"] if t["cell"] == cell and t["reviewer"] == reviewer]
    gs = [g for g in d["grades"] if g["cell"] == cell and g["reviewer"] == reviewer]
    f = [g for g in gs if g["fault"]]
    c = [g for g in gs if not g["fault"]]
    nf, nc = sum(1 for t in planned if t["fault"]), sum(1 for t in planned if not t["fault"])
    out = {"cell": cell, "reviewer": reviewer, "planned": len(planned), "graded": len(gs),
           "faulted": {"n": nf, "outcomes": _count(f), "stopped": stat(sum(stopped(g) for g in f), nf),
                       "caught": stat(sum(g["outcome"] == "caught" for g in f), nf), "released": stat(sum(g["outcome"] == "released" for g in f), nf)},
           "clean": {"n": nc, "outcomes": _count(c), "held": stat(sum(held(g) for g in c), nc),
                     "held_unconfirmed": sum(g["outcome"] == "false_unconfirmed" for g in c), "approved": stat(sum(g["outcome"] == "correct" for g in c), nc)},
           "by_fault": {}, "unparseable": sum(g["outcome"] == "unparseable" for g in gs)}
    for k in K.FAULTS:
        sub = [g for g in f if g["fault"] == k]
        n = sum(1 for t in planned if t["fault"] == k)
        if n:
            out["by_fault"][k] = {"released": stat(sum(g["outcome"] == "released" for g in sub), n), "stopped": stat(sum(stopped(g) for g in sub), n),
                                  "caught": stat(sum(g["outcome"] == "caught" for g in sub), n), "outcomes": _count(sub)}
    est = [g for g in f if g["fault"] in K.ESTABLISHED]
    n_est = sum(1 for t in planned if t["fault"] in K.ESTABLISHED)
    out["established"] = {"released": stat(sum(g["outcome"] == "released" for g in est), n_est), "stopped": stat(sum(stopped(g) for g in est), n_est)}
    toks = [(g.get("tokens") or {}) for g in gs]
    tin = [sum(t.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")) for t in toks]
    out["input_tokens_mean"] = round(sum(tin) / len(tin)) if tin else None
    out["user_chars_mean"] = round(sum(g.get("user_chars") or 0 for g in gs) / len(gs)) if gs else None
    out["cost_mean"] = round(sum(g.get("cost") or 0 for g in gs) / len(gs), 5) if gs else None
    return out


def contrast(grades: list[dict], reviewer: str, a: str, b: str, which: str = "faulted", faults: list[str] | None = None,
             alternative: str = "less", unparseable: str = "drop") -> dict:
    """Cell a against cell b on the cases both hold. On faulted cases the event is "the act was stopped"; on clean cases
    it is "the act was held". alternative 'less': a has fewer events than b. An unparseable answer has no event to
    count: `unparseable` says whether its pair is left out ("drop") or the answer is read as APPROVE or as HOLD, and
    the hypotheses are computed all three ways."""
    def pick(cell):
        out = {}
        for g in grades:
            if g["cell"] != cell or g["reviewer"] != reviewer:
                continue
            if which == "faulted" and (not g["fault"] or (faults and g["fault"] not in faults)):
                continue
            if which == "clean" and g["fault"]:
                continue
            if g["outcome"] == "unparseable":
                out[g["case"]] = None if unparseable == "drop" else (unparseable == "hold")
            else:
                out[g["case"]] = stopped(g) if which == "faulted" else held(g)
        return out
    ga, gb = pick(a), pick(b)
    shared = sorted(set(ga) & set(gb))
    both = [k for k in shared if ga[k] is not None and gb[k] is not None]
    only_a = sum(ga[k] and not gb[k] for k in both)
    only_b = sum(gb[k] and not ga[k] for k in both)
    return {"reviewer": reviewer, "a": a, "b": b, "which": which, "faults": faults, "pairs": len(both), "left_out_unparseable": len(shared) - len(both),
            "a_events": stat(sum(ga[k] for k in both), len(both)), "b_events": stat(sum(gb[k] for k in both), len(both)),
            "only_a": only_a, "only_b": only_b, "alternative": alternative, "p": round(mcnemar(only_a, only_b, alternative), 6),
            "p_two_sided": round(mcnemar(only_a, only_b, "two-sided"), 6),
            "discordant_cases": {"only_a": [k for k in both if ga[k] and not gb[k]], "only_b": [k for k in both if gb[k] and not ga[k]]}}


def by_supplier(c: dict) -> dict:
    """The supplier-level sign test for a contrast on the name fault: each supplier counts once, by the sign of its net
    discordant cases. 30 name cases are nine lookalike names, and release went name by name in the calibration."""
    net: dict[str, int] = {}
    for k in c["discordant_cases"]["only_b"]:
        s = B.JOB[k.split("-")[0]]["sup"]
        net[s] = net.get(s, 0) + 1
    for k in c["discordant_cases"]["only_a"]:
        s = B.JOB[k.split("-")[0]]["sup"]
        net[s] = net.get(s, 0) - 1
    pos, neg = sum(v > 0 for v in net.values()), sum(v < 0 for v in net.values())
    return {"net_by_supplier": dict(sorted(net.items())), "suppliers_a_lets_more_through": pos, "suppliers_b_lets_more_through": neg,
            "p_sign_one_sided": round(binom_tail(pos, pos + neg), 6)}


def stage1_tables(d: dict) -> dict:
    """What each clerk's texts held, and what the reviewers did with them, split by whether the evidence was carried."""
    s1 = {r["sid"]: r for r in d["stage1"]}
    sid_of = {t["tid"]: t["stage1"] for t in d["plan"]["trials"] if t["stage1"]}
    out = {}
    for cell, spec in d["plan"]["cells"].items():
        if not spec["clerk"]:
            continue
        recs = [r for r in d["stage1"] if r["cell"] == cell]
        faulted = [r for r in recs if r["fault"]]
        clean = [r for r in recs if not r["fault"]]
        tab = {"clerk": spec["clerk"], "kind": spec["view"], "texts": len(recs), "words_mean": round(sum(r["words"] for r in recs) / len(recs), 1) if recs else None,
               "words_max": max((r["words"] for r in recs), default=None),
               "carried": stat(sum(bool(r["carries"]) for r in faulted), len(faulted)), "carried_by_fault": {},
               "clean_with_all_three_records": stat(sum(bool(r["records"]) for r in clean), len(clean)), "reviewers": {}}
        for f in K.FAULTS:
            sub = [r for r in faulted if r["fault"] == f]
            tab["carried_by_fault"][f] = stat(sum(bool(r["carries"]) for r in sub), len(sub))
        for m in d["plan"]["reviewers"]:
            gs = [g for g in d["grades"] if g["cell"] == cell and g["reviewer"] == m]
            fy = [g for g in gs if g["fault"] and s1.get(sid_of[g["tid"]], {}).get("carries")]
            fn = [g for g in gs if g["fault"] and not s1.get(sid_of[g["tid"]], {}).get("carries")]
            cy = [g for g in gs if not g["fault"] and s1.get(sid_of[g["tid"]], {}).get("records")]
            cn = [g for g in gs if not g["fault"] and not s1.get(sid_of[g["tid"]], {}).get("records")]
            tab["reviewers"][m] = {"released_when_carried": stat(sum(g["outcome"] == "released" for g in fy), len(fy)),
                                   "released_when_not_carried": stat(sum(g["outcome"] == "released" for g in fn), len(fn)),
                                   "caught_when_not_carried": sum(g["outcome"] == "caught" for g in fn),
                                   "clean_held_with_all_records": stat(sum(held(g) for g in cy), len(cy)),
                                   "clean_held_without_all_records": stat(sum(held(g) for g in cn), len(cn))}
        out[cell] = tab
    return out


def code_baseline(d: dict) -> dict:
    """The code check on every case of the plan: P1 to P4 applied to the lookups the check sheet prints."""
    seen, f, c = set(), [], []
    for t in d["plan"]["trials"]:
        if t["cell"] != "W-card" or t["case"] in seen:
            continue
        seen.add(t["case"])
        verdict, reason = K.code_check(B.case_of(t))
        (f if t["fault"] else c).append((t["fault"], verdict, reason))
    return {"faulted_stopped": stat(sum(v == "HOLD" for _, v, _ in f), len(f)),
            "faulted_named": stat(sum(v == "HOLD" and r in K.REASONS_OF_FAULT[x] for x, v, r in f), len(f)),
            "clean_held": stat(sum(v == "HOLD" for _, v, _ in c), len(c))}


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
    """Arithmetic, not measurement: what the measured rates imply for a stream of `per` acts at an assumed fault rate,
    with the six fault kinds in equal shares as in this design. Each figure is given at the measured rate and at the
    upper end of its 95% interval, because nothing observed is not nothing possible.
      no review                        every fault is released
      code alone                       in this fixture code decides all six faults from the typed records: 0 and 0
      reviewer, every act, file M      releases p*per*(release rate), holds (1-p)*per*(held rate)
      reviewer, every act, the sheet   the same with the check sheet's rates
      code first, then the reviewer    the reviewer sees only what code holds, on the sheet: it can only undo a correct
                                       hold, so it releases p*per*(release rate on the sheet) and holds no clean act"""
    out = []
    f, c = cells.get(("W-fileM", reviewer)), cells.get(("W-card", reviewer))
    if not f or not c or f["graded"] != f["planned"] or c["graded"] != c["planned"]:
        return out

    def pair(s, scale):
        return {"at_measured_rate": round(scale * (s["rate"] or 0.0), 2), "at_upper_bound": round(scale * s["ci95"][1], 1)}
    for p in fault_rates:
        faults, clean = p * per, (1 - p) * per
        out.append({"fault_rate": p, "per": per, "faults": faults,
                    "no_review": {"reviews": 0, "faults_released": faults, "clean_held": 0},
                    "code_alone": {"reviews": 0, "faults_released": 0, "clean_held": 0},
                    "reviewer_every_act_file_M": {"reviews": per, "faults_released": pair(f["faulted"]["released"], faults), "clean_held": pair(f["clean"]["held"], clean)},
                    "reviewer_every_act_sheet": {"reviews": per, "faults_released": pair(c["faulted"]["released"], faults), "clean_held": pair(c["clean"]["held"], clean)},
                    "code_first_then_reviewer_on_sheet": {"reviews": round(faults, 1), "faults_released": pair(c["faulted"]["released"], faults), "clean_held": 0}})
    return out


def summary(set_: str, hypotheses=None) -> dict:
    d = load(set_)
    cells = {}
    for cell in d["plan"]["cells"]:
        for m in d["plan"]["reviewers"]:
            cells[(cell, m)] = cell_stats(d, cell, m)
    complete = len(d["grades"]) == len(d["plan"]["trials"])
    s = {"set": set_, "trials_planned": len(d["plan"]["trials"]), "trials_graded": len(d["grades"]), "complete": complete,
         "cells": [cells[k] for k in cells], "stage1": stage1_tables(d), "code_baseline": code_baseline(d), "costs": costs(d),
         "unparseable": [{"tid": g["tid"], "answer": g.get("raw")} for g in d["grades"] if g["outcome"] == "unparseable"]}
    if set_ == "main":
        s["envelope_arithmetic"] = {m: envelope(cells, m) for m in d["plan"]["reviewers"]}
        if hypotheses and complete:
            s["hypotheses"] = hypotheses(d, cells)
    return s


def markdown(s: dict) -> str:
    name = lambda m: C.MODELS[m]["name"]  # noqa: E731
    L = [f"# Study 11, the review envelope: {s['set']} run", "",
         f"{s['trials_graded']} of {s['trials_planned']} planned trials graded" + ("." if s["complete"] else ": INCOMPLETE, so no hypothesis is computed.")
         + " Rates are k of n with exact 95% intervals; n is every planned trial. Released means APPROVE on a faulted case; stopped means any HOLD on one; held means any HOLD on a clean case.", ""]
    cb = s["code_baseline"]
    L += [f"Code baseline (P1 to P4 applied by code to the typed records): stopped {xn(cb['faulted_stopped'])} faulted cases, naming the planted reason in {cb['faulted_named']['k']}; "
          f"held {xn(cb['clean_held'])} clean cases.", ""]
    L += ["## Faulted cases", "", "| Cell | Reviewer | Released | Released, the five established faults | Released, the name fault | Named the planted reason | Unparseable |", "|---|---|---|---|---|---|---|"]
    for c in s["cells"]:
        if not c["faulted"]["n"]:
            continue
        nm = c["by_fault"].get("supplier", {}).get("released")
        L.append(f"| {c['cell']} | {name(c['reviewer'])} | {xn(c['faulted']['released'])} | {xn(c['established']['released'])} | {xn(nm) if nm else 'none'} | "
                 f"{c['faulted']['caught']['k']} of {c['faulted']['n']} | {c['unparseable']} |")
    L += ["", "## Released, by fault", "", "| Cell | Reviewer | " + " | ".join(K.FAULTS) + " |", "|---|---|" + "---|" * len(K.FAULTS)]
    for c in s["cells"]:
        if c["faulted"]["n"]:
            L.append(f"| {c['cell']} | {name(c['reviewer'])} | " + " | ".join(f"{c['by_fault'][f]['released']['k']} of {c['by_fault'][f]['released']['n']}" if f in c["by_fault"] else "" for f in K.FAULTS) + " |")
    L += ["", "## Clean cases", "", "| Cell | Reviewer | Held for nothing | of which HOLD unconfirmed | Mean input tokens | Mean list-price cost |", "|---|---|---|---|---|---|"]
    for c in s["cells"]:
        if c["clean"]["n"]:
            L.append(f"| {c['cell']} | {name(c['reviewer'])} | {xn(c['clean']['held'])} | {c['clean']['held_unconfirmed']} | {c['input_tokens_mean']} | "
                     + (f"${c['cost_mean']:.4f}" if c["cost_mean"] is not None else "") + " |")
    L += ["", "## Clerk's texts", ""]
    for cell, t in s["stage1"].items():
        L.append(f"**{cell}** ({name(t['clerk'])} as clerk, {t['kind']}): {t['texts']} texts, {t['words_mean']} words on average, longest {t['words_max']}. "
                 f"On faulted cases the evidence was carried in {xn(t['carried'])}; by fault: " + "; ".join(f"{f} {v['k']} of {v['n']}" for f, v in t["carried_by_fault"].items())
                 + f". On clean cases all three records were in {xn(t['clean_with_all_three_records'])}.")
        for m, r in t["reviewers"].items():
            L.append(f"- {name(m)}: evidence carried, released {xn(r['released_when_carried'])}; not carried, released {xn(r['released_when_not_carried'])} and named the planted reason anyway in "
                     f"{r['caught_when_not_carried']}. Clean, all records in the text: held {xn(r['clean_held_with_all_records'])}; not all: held {xn(r['clean_held_without_all_records'])}.")
        L.append("")
    if s.get("hypotheses"):
        L += ["## Hypotheses", ""]
        for h in s["hypotheses"]:
            L.append(f"- **{h['id']}** {h['verdict']}. {h['line']}")
        L.append("")
    if s.get("envelope_arithmetic"):
        L += ["## What the rates imply for a stream of acts (arithmetic, not measurement)", "",
              "Six fault kinds in equal shares, as in this design. Each figure is at the measured rate, then at the upper end of its 95% interval.", ""]
        for m, rows in s["envelope_arithmetic"].items():
            for r in rows:
                a, b, c = r["reviewer_every_act_file_M"], r["reviewer_every_act_sheet"], r["code_first_then_reviewer_on_sheet"]
                fmt = lambda x: f"{x['at_measured_rate']} (up to {x['at_upper_bound']})"  # noqa: E731
                L.append(f"- {name(m)}, {r['per']:,} acts, {100 * r['fault_rate']:.1f}% faulted ({r['faults']:.0f} faults). No review: {r['faults']:.0f} released. Code alone: 0 released, 0 clean held. "
                         f"Reviewer on every act from the M file: {fmt(a['faults_released'])} released, {fmt(a['clean_held'])} clean held. On the check sheet: {fmt(b['faults_released'])} released, "
                         f"{fmt(b['clean_held'])} clean held. Code first, the reviewer only on what code holds ({c['reviews']} reviews): {fmt(c['faults_released'])} released, no clean act held.")
        L.append("")
    if s["unparseable"]:
        L += ["## Unparseable answers, word for word", ""] + [f"- `{u['tid']}`: {json.dumps(u['answer'])}" for u in s["unparseable"]] + [""]
    L += ["## Cost", "", f"{s['costs']['calls']} model calls, ${s['costs']['total_list_price']:.2f} at list price (Claude runs on the account's plan).", ""]
    for k, b in s["costs"]["by_model_and_kind"].items():
        L.append(f"- {k}: {b['calls']} calls, ${b['cost']:.2f}, {b['errors']} provider errors")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    from hypotheses import hypotheses
    s = summary(a.set, hypotheses)
    out = C.RESULTS / ("pilot" if a.set == "pilot" else "")
    out.mkdir(parents=True, exist_ok=True)
    C.write_json(out / "summary.json", s)
    (out / "summary.md").write_text(markdown(s))
    print(f"wrote {out / 'summary.md'}" + ("" if s["complete"] else "  (INCOMPLETE: no hypotheses)"))


if __name__ == "__main__":
    main()
