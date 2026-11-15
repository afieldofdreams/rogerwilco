#!/usr/bin/env python3
"""Study 10: the summary, from the graded files and the ledger. Re-runs with no key.

  analyse.py --set pilot|main        writes results/summary.{json,md} (main) or results/pilot/summary.{json,md}

Counts are "x of n"; where x is 0 the 95% upper bound is given (Clopper-Pearson, two-sided, as studies 6 and 7 report
it). Tests: Fisher's exact (study 6's implementation), and an exact McNemar test on matched pairs as a secondary.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from math import comb

import common as C
import fixtures as F

ORDER = ["haiku55", "gpt54mini", "sonnet55", "gpt55"]
OUTCOMES_F = ["caught", "miss", "wrong_slot", "slot_not_named", "unparseable"]
OUTCOMES_C = ["correct", "false_alarm", "unparseable"]


def cp_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Clopper-Pearson exact interval for k of n (study 6's analyse.py)."""
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
    """Fisher's exact test on [[a, b], [c, d]] (study 6's analyse.py); 'less' tests that row 1's rate is lower."""
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


def mcnemar_less(b: int, c: int) -> float:
    """Exact one-sided McNemar: b = pairs missed in the first condition only, c = in the second only;
    the probability of c or fewer of b + c under 0.5, i.e. evidence that the second misses less."""
    n = b + c
    return 1.0 if n == 0 else min(1.0, sum(comb(n, i) for i in range(c + 1)) / 2 ** n)


def xn(k: int, n: int) -> str:
    if n == 0:
        return "–"
    if k == 0:
        return f"0 of {n} (≤{100 * cp_interval(0, n)[1]:.1f}%)"
    return f"{k} of {n}"


def stat(k: int, n: int) -> dict:
    lo, hi = cp_interval(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [lo, hi]}


def name(alias: str) -> str:
    return C.MODELS[alias]["name"]

# ------------------------------------------------------------------------------------- loading


def load(set_: str) -> dict:
    p = C.read_json(C.DATA / f"plan-{set_}.json")
    trials, rbs = [], []
    for t in p["trials"]:
        g = C.TRIALS / set_ / t["tid"] / "grade.json"
        if g.exists():
            trials.append({**t, **C.read_json(g), "answer_text": (g.parent / "answer.txt").read_text()})
    for rb in p["readbacks"]:
        f = C.READBACKS / set_ / f"{rb['rid']}.json"
        rbs.append({**rb, **(C.read_json(f) if f.exists() else {"attempts": [], "accepted": None, "missing": True})})
    ledger = [json.loads(l) for l in C.LEDGER.read_text().splitlines() if l.strip()] if C.LEDGER.exists() else []
    return {"plan": p, "trials": trials, "readbacks": rbs, "ledger": [e for e in ledger if e.get("phase") == set_]}

# ------------------------------------------------------------------------------------- tables


def cells(trials: list[dict]) -> dict:
    out = {}
    for t in trials:
        key = (t["fmt"], t["judge"], t["author"])
        c = out.setdefault(key, {"fmt": t["fmt"], "judge": t["judge"], "author": t["author"], "relation": t["relation"],
                                 "faulted": defaultdict(int), "clean": defaultdict(int), "miss_by_slot": defaultdict(int),
                                 "n_by_slot": defaultdict(int), "false_alarm_details": defaultdict(int)})
        if t["faulted"]:
            c["faulted"][t["outcome"]] += 1
            c["n_by_slot"][t["slot"]] += 1
            if t["outcome"] == "miss":
                c["miss_by_slot"][t["slot"]] += 1
        else:
            c["clean"][t["outcome"]] += 1
            if t["outcome"] == "false_alarm":
                c["false_alarm_details"][t["answer"].get("detail") or "not named"] += 1
    return out


def rows(trials: list[dict], rbs: list[dict]) -> list[dict]:
    """One row per graded trial, with what the readback looked like: whether a prose readback wrote the supplier's name
    exactly as it was given, whether a line echoed the handover's appr=, whether it carried its version token."""
    by_rid = {r["rid"]: r for r in rbs if r.get("accepted") is not None}
    out = []
    for t in sorted(trials, key=lambda x: x["tid"]):
        rb = by_rid.get(t["rid"], {})
        text = rb.get("readback") or ""
        got = F.plant(F.JOB[t["job"]], t["slot"]) if t["slot"] else F.JOB[t["job"]]
        first = next((l.strip() for l in (t.get("answer_text") or "").splitlines() if l.strip()), "")
        out.append({"id": t["tid"], "format": t["fmt"], "judge": t["judge"], "author": t["author"], "relation": t["relation"],
                    "job": t["job"], "slot": t["slot"], "outcome": t["outcome"], "detail": t["answer"].get("detail"),
                    "first_line": first[:120], "payment_date": got["payment_date"],
                    "supplier_as_given": (got["supplier"] in text) if t["fmt"] == "prose" else None,
                    "echoes_appr": ("appr=" in text) if t["fmt"] == "line" else None,
                    "version_token": text.startswith("RW1 ") if t["fmt"] == "line" else None})
    return out


def cell_json(c: dict) -> dict:
    nf = sum(c["faulted"].values()); nc = sum(c["clean"].values())
    return {"format": c["fmt"], "judge": c["judge"], "author": c["author"], "relation": c["relation"],
            "faulted": {"n": nf, **{o: stat(c["faulted"].get(o, 0), nf) for o in OUTCOMES_F}},
            "clean": {"n": nc, **{o: stat(c["clean"].get(o, 0), nc) for o in OUTCOMES_C}},
            "false_alarm_details": dict(c["false_alarm_details"]),
            "misses_by_slot": {s: stat(c["miss_by_slot"].get(s, 0), c["n_by_slot"].get(s, 0)) for s in F.FAULT_SLOTS}}


def code_table(rbs: list[dict]) -> dict:
    out = {}
    for r in rbs:
        g = r.get("code_grade")
        if not g:
            continue
        c = out.setdefault(r["author"], {"faulted": defaultdict(int), "clean": defaultdict(int), "tiers_clean": defaultdict(int),
                                         "miss_by_slot": defaultdict(int)})
        if g["faulted"]:
            c["faulted"][g["outcome"]] += 1
            if g["outcome"] == "miss":
                c["miss_by_slot"][g["planted"]] += 1
        else:
            c["clean"][g["outcome"]] += 1
            if g["outcome"] == "false_alarm":
                for tier in g["tiers"]:
                    c["tiers_clean"][tier] += 1
    js = {}
    for a, c in out.items():
        nf = sum(c["faulted"].values()); nc = sum(c["clean"].values())
        js[a] = {"faulted": {"n": nf, "miss": stat(c["faulted"].get("miss", 0), nf),
                             "caught_planted_only": stat(c["faulted"].get("caught", 0), nf),
                             "caught_planted_and_other": stat(c["faulted"].get("caught_and_other", 0), nf),
                             "wrong_slot": stat(c["faulted"].get("wrong_slot", 0), nf),
                             "slot_not_named": stat(c["faulted"].get("slot_not_named", 0), nf)},
                 "clean": {"n": nc, "false_alarm": stat(c["clean"].get("false_alarm", 0), nc), "false_alarm_tiers": dict(c["tiers_clean"])},
                 "misses_by_slot": dict(c["miss_by_slot"])}
    return js


def fidelity(rbs: list[dict]) -> dict:
    out = {}
    for r in rbs:
        if r.get("missing"):
            continue
        c = out.setdefault(f"{r['author']}|{r['fmt']}", {"author": r["author"], "format": r["fmt"], "n": 0, "first": 0, "later": 0,
                                                          "dropped": 0, "attempts": 0, "line_alone": 0, "problems": defaultdict(int),
                                                          "version_token_missing": 0, "accepted_on_recheck": 0})
        c["n"] += 1
        c["attempts"] += len(r["attempts"])
        if r["accepted"] is not None and r["attempts"][r["accepted"]].get("version_token_missing"):
            c["version_token_missing"] += 1
        if "accepted_registered" in r and r["accepted_registered"] != r["accepted"]:
            c["accepted_on_recheck"] += 1
        if r["accepted"] == 0:
            c["first"] += 1
        elif r["accepted"] is not None:
            c["later"] += 1
        else:
            c["dropped"] += 1
        if r["accepted"] is not None and r["fmt"] == "line" and r["attempts"][r["accepted"]].get("reply_was_line_alone"):
            c["line_alone"] += 1
        for att in r["attempts"]:
            for prob in att["problems"]:
                c["problems"][prob.split(" ")[0] if not prob.startswith("comments") else "comments"] += 1
    return {k: {**v, "problems": dict(v["problems"])} for k, v in out.items()}


def costs(ledger: list[dict]) -> dict:
    by = defaultdict(lambda: {"calls": 0, "cost": 0.0, "errors": 0})
    vendor = {"openai": 0.0, "anthropic": 0.0}
    for e in ledger:
        b = by[f"{e['model']}|{e['kind']}"]
        b["calls"] += 1; b["cost"] += e.get("cost") or 0.0; b["errors"] += 1 if e.get("error") else 0
        vendor[C.MODELS[e["model"]]["vendor"]] += e.get("cost") or 0.0
    return {"total": round(sum(v["cost"] for v in by.values()), 4), "openai": round(vendor["openai"], 4),
            "claude_list": round(vendor["anthropic"], 4),
            "by": {k: {**v, "cost": round(v["cost"], 4), "mean": round(v["cost"] / v["calls"], 6) if v["calls"] else None} for k, v in by.items()}}

# ------------------------------------------------------------------------------------- hypotheses (main run)


def pooled(trials, **kw) -> tuple[int, int]:
    sel = [t for t in trials if t["faulted"] and all(t[k] == v for k, v in kw.items())]
    return sum(t["outcome"] == "miss" for t in sel), len(sel)


def hypotheses(trials: list[dict], code: dict) -> dict:
    judges = [j for j in ORDER if any(t["judge"] == j for t in trials)]
    h = {"H1": {}, "H2": {}, "H3": {}, "H4": {}}
    for j in judges:
        k, n = pooled(trials, judge=j, fmt="prose")
        h["H1"][j] = {"prose_misses": stat(k, n), "outcome": "holds" if k > 0 else ("fails" if n else "not shown")}
        kl, nl = pooled(trials, judge=j, fmt="line")
        p = fisher(kl, nl - kl, k, n - k, "less")
        # matched pairs: the same job, slot and author read back in both formats
        pm ={(t["job"], t["slot"], t["author"]): t["outcome"] == "miss" for t in trials if t["faulted"] and t["judge"] == j and t["fmt"] == "prose"}
        lm = {(t["job"], t["slot"], t["author"]): t["outcome"] == "miss" for t in trials if t["faulted"] and t["judge"] == j and t["fmt"] == "line"}
        both = set(pm) & set(lm)
        b = sum(pm[x] and not lm[x] for x in both); c = sum(lm[x] and not pm[x] for x in both)
        if k == 0:
            out = "not shown"
        elif p < 0.05:
            out = "holds"
        elif kl >= k:
            out = "fails"
        else:
            out = "not shown"
        h["H2"][j] = {"line_misses": stat(kl, nl), "prose_misses": stat(k, n), "fisher_one_sided_p": round(p, 5),
                      "mcnemar_one_sided_p": round(mcnemar_less(b, c), 5), "discordant_prose_only": b, "discordant_line_only": c,
                      "outcome": out}
    raw = {}
    for j in judges:
        ks, ns = pooled(trials, judge=j, relation="same")
        kd, nd = pooled(trials, judge=j, relation="different")
        raw[j] = (ks, ns, kd, nd, fisher(ks, ns - ks, kd, nd - kd, "two-sided"))
    order = sorted(raw, key=lambda j: raw[j][4])
    m = len(order); running = 0.0
    for i, j in enumerate(order):
        ks, ns, kd, nd, p = raw[j]
        adj = min(1.0, max(running, (m - i) * p)); running = adj
        per_fmt = {}
        for fmt in ("prose", "line"):
            a1, n1 = pooled(trials, judge=j, relation="same", fmt=fmt)
            a2, n2 = pooled(trials, judge=j, relation="different", fmt=fmt)
            per_fmt[fmt] = {"same": stat(a1, n1), "different": stat(a2, n2), "fisher_two_sided_p": round(fisher(a1, n1 - a1, a2, n2 - a2), 5)}
        h["H3"][j] = {"same_author_misses": stat(ks, ns), "different_author_misses": stat(kd, nd), "fisher_two_sided_p": round(p, 5),
                      "holm_p": round(adj, 5), "outcome": "holds" if adj < 0.05 else "not shown", "by_format": per_fmt}
    fm = sum(v["faulted"]["miss"]["k"] for v in code.values()); fn = sum(v["faulted"]["n"] for v in code.values())
    cf_ = sum(v["clean"]["false_alarm"]["k"] for v in code.values()); cn = sum(v["clean"]["n"] for v in code.values())
    h["H4"] = {"code_misses": stat(fm, fn), "code_false_alarms": stat(cf_, cn),
               "outcome": ("holds" if fm == 0 and cf_ == 0 else "fails") if fn and cn else "not shown"}
    return h

# ------------------------------------------------------------------------------------- markdown


def md_tables(cj: list[dict], code: dict, set_: str) -> list[str]:
    out = []
    for fmt, title in (("prose", "Prose readbacks"), ("line", "RW1 line readbacks")):
        out += [f"### {title}", "",
                "| Judge | Readback author | Misses | Wrong slot | Slot not named | False alarms | Unparseable |",
                "|---|---|---|---|---|---|---|"]
        rows = sorted([c for c in cj if c["format"] == fmt], key=lambda c: (ORDER.index(c["judge"]), c["relation"] != "same"))
        for c in rows:
            nf, nc = c["faulted"]["n"], c["clean"]["n"]
            un = c["faulted"]["unparseable"]["k"] + c["clean"]["unparseable"]["k"]
            out.append(f"| {name(c['judge'])} | {name(c['author'])} ({c['relation']}) | {xn(c['faulted']['miss']['k'], nf)} | "
                       f"{xn(c['faulted']['wrong_slot']['k'], nf)} | {xn(c['faulted']['slot_not_named']['k'], nf)} | "
                       f"{xn(c['clean']['false_alarm']['k'], nc)} | {xn(un, nf + nc)} |")
        if fmt == "line" and code:
            for a in ORDER:
                if a in code:
                    v = code[a]
                    out.append(f"| Code check (check-rb) | {name(a)} | {xn(v['faulted']['miss']['k'], v['faulted']['n'])} | "
                               f"{xn(v['faulted']['wrong_slot']['k'], v['faulted']['n'])} | "
                               f"{xn(v['faulted']['slot_not_named']['k'], v['faulted']['n'])} | "
                               f"{xn(v['clean']['false_alarm']['k'], v['clean']['n'])} | – |")
        out.append("")
    return out


def md_slots(cj: list[dict]) -> list[str]:
    out = []
    for fmt, title in (("prose", "Prose"), ("line", "RW1 line")):
        rows = sorted([c for c in cj if c["format"] == fmt], key=lambda c: (ORDER.index(c["judge"]), c["relation"] != "same"))
        if not rows:
            continue
        head = "| Planted slot | " + " | ".join(f"{name(c['judge'])} reading {name(c['author'])}" for c in rows) + " |"
        out += [f"### Misses by planted slot, {title}", "", head, "|---|" + "---|" * len(rows)]
        for s in F.FAULT_SLOTS:
            out.append(f"| {s} | " + " | ".join(f"{c['misses_by_slot'][s]['k']} of {c['misses_by_slot'][s]['n']}" for c in rows) + " |")
        out.append("")
    return out


def md_fidelity(fid: dict) -> list[str]:
    out = ["| Author | Format | Readbacks | Accepted first time | Accepted on attempt 2 or 3 | Dropped | Line was the whole reply | Problems on rejected attempts |",
           "|---|---|---|---|---|---|---|---|"]
    for a in ORDER:
        for fmt in ("prose", "line"):
            v = fid.get(f"{a}|{fmt}")
            if not v:
                continue
            probs = ", ".join(f"{k} {n}" for k, n in sorted(v["problems"].items(), key=lambda x: -x[1])) or "none"
            alone = f"{v['line_alone']} of {v['first'] + v['later']}" if fmt == "line" else "–"
            out.append(f"| {name(a)} | {fmt} | {v['n']} | {v['first']} | {v['later']} | {v['dropped']} | {alone} | {probs} |")
    return out


def summary(set_: str) -> dict:
    d = load(set_)
    cj = [cell_json(c) for c in cells(d["trials"]).values()]
    code = code_table(d["readbacks"])
    s = {"set": set_, "trials_graded": len(d["trials"]), "trials_planned": len(d["plan"]["trials"]),
         "readbacks_planned": len(d["plan"]["readbacks"]), "cells": cj, "code_check": code, "fidelity": fidelity(d["readbacks"]),
         "cost": costs(d["ledger"]), "rows": rows(d["trials"], d["readbacks"])}
    if set_ == "main":
        s["hypotheses"] = hypotheses(d["trials"], code)
    return s


def markdown(s: dict) -> str:
    out = [f"# Study 10, the scheduler as judge: {'pilot' if s['set'] == 'pilot' else 'results'}", "",
           f"{s['trials_graded']} of {s['trials_planned']} planned trials graded. Cost: OpenAI ${s['cost']['openai']:.2f}, the money "
           f"the run spent, from tokens at published prices; Claude ${s['cost']['claude_list']:.2f} at list price as `claude -p` reports "
           "it, run on the account's plan. Counts are x of n; a zero carries its "
           "95% upper bound. Misses, wrong slot and slot not named are over faulted pairs; false alarms over clean pairs; "
           "unparseable over all pairs in the row.", "", "## Judges", ""]
    out += md_tables(s["cells"], s["code_check"], s["set"])
    out += md_slots(s["cells"])
    if s.get("hypotheses"):
        h = s["hypotheses"]
        out += ["## Hypotheses", ""]
        for j, v in h["H1"].items():
            out.append(f"- H1, {name(j)}: {v['outcome']}. Prose misses {xn(v['prose_misses']['k'], v['prose_misses']['n'])}.")
        for j, v in h["H2"].items():
            out.append(f"- H2, {name(j)}: {v['outcome']}. Line misses {xn(v['line_misses']['k'], v['line_misses']['n'])} against prose "
                       f"{xn(v['prose_misses']['k'], v['prose_misses']['n'])}; Fisher one-sided p {v['fisher_one_sided_p']}, McNemar one-sided p "
                       f"{v['mcnemar_one_sided_p']} ({v['discordant_prose_only']} pairs missed in prose only, {v['discordant_line_only']} in the line only).")
        for j, v in h["H3"].items():
            out.append(f"- H3, {name(j)}: {v['outcome']}. Same-author misses {xn(v['same_author_misses']['k'], v['same_author_misses']['n'])}, "
                       f"different-author {xn(v['different_author_misses']['k'], v['different_author_misses']['n'])}; Fisher two-sided p "
                       f"{v['fisher_two_sided_p']}, Holm {v['holm_p']}.")
        v = h["H4"]
        out.append(f"- H4: {v['outcome']}. Code check misses {xn(v['code_misses']['k'], v['code_misses']['n'])}, false alarms "
                   f"{xn(v['code_false_alarms']['k'], v['code_false_alarms']['n'])}.")
        out.append("")
    out += ["## The code check on every line readback", "",
            "| Author | Faulted | Passed (miss) | Refused, planted slot only | Refused, planted and another | Refused, another slot | Refused, no slot named | Clean | Refused (false alarm) | Tiers that refused a clean line |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for a in ORDER:
        v = s["code_check"].get(a)
        if v:
            f_, c_ = v["faulted"], v["clean"]
            out.append(f"| {name(a)} | {f_['n']} | {xn(f_['miss']['k'], f_['n'])} | {f_['caught_planted_only']['k']} | {f_['caught_planted_and_other']['k']} | "
                       f"{f_['wrong_slot']['k']} | {f_['slot_not_named']['k']} | {c_['n']} | {xn(c_['false_alarm']['k'], c_['n'])} | "
                       f"{c_['false_alarm_tiers'] or 'none'} |")
    out += ["", "## Readbacks: what the payer models wrote", ""] + md_fidelity(s["fidelity"])
    out += ["", "## Cost", "", "| Model | Kind | Calls | Cost | Mean a call | Calls that failed |", "|---|---|---|---|---|---|"]
    for k, v in sorted(s["cost"]["by"].items()):
        a, kind = k.split("|")
        out.append(f"| {name(a)} | {kind} | {v['calls']} | ${v['cost']:.4f} | ${v['mean']:.5f} | {v['errors']} |")
    out.append(f"| OpenAI, spent | | | ${s['cost']['openai']:.4f} | | |")
    out.append(f"| Claude, at list price | | | ${s['cost']['claude_list']:.4f} | | |")
    return "\n".join(out) + "\n"

# ------------------------------------------------------------------------------------- projection


def projection(set_: str = "pilot") -> dict:
    """The main run's cost from the pilot's measured calls. Judge calls are measured for the pilot judge only; for the
    other models a judge call is estimated as that model's mean author call times the pilot judge's judge/author ratio."""
    s = summary(set_)
    by = s["cost"]["by"]
    fid = s["fidelity"]
    main = C.read_json(C.DATA / "plan-main.json")
    n_author = defaultdict(int); n_judge = defaultdict(int)
    for rb in main["readbacks"]:
        n_author[rb["author"]] += 1
    for t in main["trials"]:
        n_judge[t["judge"]] += 1
    pj = C.read_json(C.DATA / "plan-pilot.json")["judge"]
    ratio = None
    if by.get(f"{pj}|judge") and by.get(f"{pj}|author"):
        ratio = by[f"{pj}|judge"]["mean"] / by[f"{pj}|author"]["mean"]
    rows = []
    total = 0.0
    for a in ORDER:
        au = by.get(f"{a}|author")
        att = [v for k, v in fid.items() if k.startswith(a + "|")]
        per_rb = (sum(v["attempts"] for v in att) / sum(v["n"] for v in att)) if att and sum(v["n"] for v in att) else 1.0
        ca = (au["mean"] * per_rb * n_author[a]) if au else None
        if by.get(f"{a}|judge"):
            jm, how = by[f"{a}|judge"]["mean"], "measured"
        elif au and ratio:
            jm, how = au["mean"] * ratio, f"estimated (author mean x {ratio:.2f})"
        else:
            jm, how = None, "unknown"
        cj = jm * n_judge[a] if jm is not None else None
        total += (ca or 0) + (cj or 0)
        rows.append({"model": a, "author_calls": n_author[a], "attempts_per_readback": round(per_rb, 3), "author_mean": au and au["mean"],
                     "author_cost": ca and round(ca, 2), "judge_calls": n_judge[a], "judge_mean": jm and round(jm, 6), "judge_mean_how": how,
                     "judge_cost": cj and round(cj, 2)})
    return {"rows": rows, "total": round(total, 2), "judge_author_ratio": ratio and round(ratio, 3), "pilot_judge": pj}


def print_projection(set_: str = "pilot") -> None:
    pr = projection(set_)
    print(f"{'model':10} {'readbacks':>9} {'att/rb':>6} {'$/author':>9} {'author $':>9} {'judgments':>9} {'$/judge':>9} {'judge $':>9}  how")
    for r in pr["rows"]:
        print(f"{r['model']:10} {r['author_calls']:>9} {r['attempts_per_readback']:>6} {r['author_mean'] or 0:>9.5f} {r['author_cost'] or 0:>9.2f} "
              f"{r['judge_calls']:>9} {r['judge_mean'] or 0:>9.5f} {r['judge_cost'] or 0:>9.2f}  {r['judge_mean_how']}")
    print(f"projected main run: ${pr['total']:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    a = ap.parse_args()
    s = summary(a.set)
    out = C.RESULTS if a.set == "main" else C.RESULTS / "pilot"
    if a.set == "pilot":
        s["projection_main"] = projection("pilot")
    C.write_json(out / "summary.json", s)
    md = markdown(s)
    if a.set == "pilot":
        pr = s["projection_main"]
        md += ("\n## The main run's projected cost\n\n| Model | Readbacks | Attempts a readback | Author cost | Judgments | Judge call | How | Judge cost |\n"
               "|---|---|---|---|---|---|---|---|\n")
        for r in pr["rows"]:
            md += (f"| {name(r['model'])} | {r['author_calls']} | {r['attempts_per_readback']} | ${r['author_cost'] or 0:.2f} | {r['judge_calls']} | "
                   f"${r['judge_mean'] or 0:.5f} | {r['judge_mean_how']} | ${r['judge_cost'] or 0:.2f} |\n")
        md += f"\nProjected total: ${pr['total']:.2f} against the $25 cap.\n"
    (out / "summary.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
