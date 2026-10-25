#!/usr/bin/env python3
"""The site page for study 8, generated from results/summary.json so that no figure on it is typed by hand.

  python3 tools/site_page.py            # writes app/static/research/chain.html (then run app/tools/stamp.py)
  python3 tools/site_page.py --figures  # prints the named figures the page carries, as the app test recomputes them

Every number in the prose is a <span data-fig="name">value</span>; figures() is the single source of those values and
app/tests/test_research_figures.py asserts the committed page carries exactly what figures() computes from the JSON.
The pilot, the ladder, the exclusions and the blind second reading are read from their own files beside the summary.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

PAGE = C.REPO / "app" / "static" / "research" / "chain.html"
MODELS = {"haiku55": "h55", "haiku45": "h45"}   # cell key -> figure prefix


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def kn(r: dict) -> str:
    return f"{r['k']} of {r['n']}"


def ci(r: dict) -> str:
    """The proportion and its exact 95% interval as the README writes them: 82%, 68 to 92."""
    return f"{100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f}"


def pct_hi(r: dict) -> str:
    return f"{100 * r['hi']:.0f}%"


def num(x) -> str:
    """A median size or a count as the JSON holds it, without a trailing .0."""
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return f"{x:,}" if isinstance(x, int) else str(x)


def times(n: int) -> str:
    return {0: "never", 1: "once", 2: "twice"}.get(n, f"{n} times")


def pval(p: float) -> str:
    if p < 0.001:
        return "under 0.001"
    s = f"{p:.3f}".rstrip("0").rstrip(".")
    return "1.0" if s == "1" else s


def figures(results: Path = C.RESULTS) -> dict:
    """Named figures from the main run's summary, the pilot's and the ladder's, the exclusions and the validation.
    Strings, as they appear on the page."""
    s = load(results / "summary.json")
    cells, rows = s["cells"], s["rows"]
    f: dict[str, str] = {}
    f["chains"] = f"{s['chains']:,}"
    f["cost_total"] = f"${s['cost_usd_total']:,.2f}"
    for model, m in MODELS.items():
        mrows = [r for r in rows if r["model"] == model]
        f[f"chains_{m}"] = f"{len(mrows):,}"
        f[f"cost_{m}"] = f"${sum(r['cost_usd'] for r in mrows):,.2f}"
        # block 1 and block 2, every arm, K = 2
        for block in (1, 2):
            for arm in C.ARMS:
                c = cells[f"B{block}-{arm}-{model}-k2"]
                p = f"b{block}_{arm}_{m}"
                f[f"{p}_n"] = str(c["chains"])
                f[f"{p}_correct"] = kn(c["correct_act"]); f[f"{p}_correct_ci"] = ci(c["correct_act"])
                f[f"{p}_expected"] = kn(c["as_expected"]); f[f"{p}_expected_ci"] = ci(c["as_expected"])
                f[f"{p}_fields"] = kn(c["all_fields_at_payer"])
                f[f"{p}_asked"] = kn(c["asked"]); f[f"{p}_held"] = kn(c["held"])
                f[f"{p}_wrong_act"] = kn(c["wrong_act"])
                f[f"{p}_drift"] = kn(c["any_drift"])
                f[f"{p}_size1"] = num(c["size_median_by_hop"]["1"]); f[f"{p}_size2"] = num(c["size_median_by_hop"]["2"])
                f[f"{p}_size3"] = num(c["size_median_by_hop"]["3"])
                f[f"{p}_traffic"] = num(c["traffic_median"]); f[f"{p}_turns"] = f"{c['model_turns_mean']:.1f}"
                f[f"{p}_cost"] = f"${c['cost_usd_mean']:.3f}"
                if arm == "R":
                    f[f"{p}_fa"] = kn(c["false_alarms_over_correct_forwards"]); f[f"{p}_fa_hi"] = pct_hi(c["false_alarms_over_correct_forwards"])
                    f[f"{p}_rbfa"] = kn(c["readback_false_alarms_over_readbacks"]); f[f"{p}_rbfa_ci"] = ci(c["readback_false_alarms_over_readbacks"])
                    f[f"{p}_caught"] = str(c["caught"])
                sub = [r for r in rows if r["block"] == block and r["arm"] == arm and r["model"] == model]
                f[f"{p}_graded_wrong"] = str(sum(1 for r in sub if r["outcome"] == "wrong"))
                f[f"{p}_loss"] = str(c["chains"] - c["correct_act"]["k"])
                f[f"{p}_fa_chains"] = str(sum(1 for r in sub if r["false_alarms"]))
                f[f"{p}_asked_after_fa"] = str(sum(1 for r in sub if r["false_alarms"] and r["asked"]))
            f[f"b{block}_prose_n_{m}"] = str(cells[f"B{block}-F-{model}-k2"]["chains"] + cells[f"B{block}-A-{model}-k2"]["chains"])
        # the prose failures of block 1, pooled over F and A
        f[f"b1_prose_fail_{m}"] = str(cells[f"B1-F-{model}-k2"]["asked"]["k"] + cells[f"B1-A-{model}-k2"]["asked"]["k"]
                                      + cells[f"B1-F-{model}-k2"]["held"]["k"] + cells[f"B1-A-{model}-k2"]["held"]["k"]
                                      + cells[f"B1-F-{model}-k2"]["wrong_act"]["k"] + cells[f"B1-A-{model}-k2"]["wrong_act"]["k"])
        # block 2: the chains graded wrong, and where they ended
        b2wrong = [r for r in rows if r["block"] == 2 and r["model"] == model and r["outcome"] == "wrong"]
        f[f"b2_wrong_{m}"] = str(len(b2wrong))
        f[f"b2_wrong_acted_{m}"] = str(sum(1 for r in b2wrong if r["acted"]))
        f[f"b2_wrong_asked_hop1_{m}"] = str(sum(1 for r in b2wrong if r["asked"] and r["asked_at"] == 1))
        # block 3, the sweep
        for arm in ("F", "R"):
            for K in (1, 2, 3, 5):
                c = cells[f"B3-{arm}-{model}-k{K}"]
                p = f"b3_{arm}_{m}_k{K}"
                f[f"{p}_correct"] = kn(c["correct_act"]); f[f"{p}_correct_ci"] = ci(c["correct_act"])
                f[f"{p}_asked"] = kn(c["asked"]); f[f"{p}_held"] = kn(c["held"])
                f[f"{p}_size1"] = num(c["size_median_by_hop"]["1"]); f[f"{p}_size_payer"] = num(c["size_median_by_hop"][str(K + 1)])
                f[f"{p}_traffic"] = num(c["traffic_median"]); f[f"{p}_turns"] = f"{c['model_turns_mean']:.1f}"
                f[f"{p}_cost"] = f"${c['cost_usd_mean']:.3f}"
        # the registered tests
        t = s["tests"][model]
        for name, v in t.items():
            h = name.split()[0].lower()
            if "p" in v:
                key = {"h1": "h1", "h2": "h2", "h6": "h6"}.get(h)
                if key:
                    f[f"{key}_{m}_p"] = pval(v["p"])
                elif h == "h8":
                    f[f"h8_{m}_p" if "correct acts" in name else f"h8_fields_{m}_p"] = pval(v["p"])
            if h == "h4":
                f[f"h4_{m}"] = "holds" if v["holds"] else "does not hold"
    # drift, the dropped fields and the lines, over the whole run
    drift = [r for r in rows if r["any_drift"]]
    f["drift_total"] = str(len(drift)); f["drift_times"] = times(len(drift))
    for r in drift:
        fields = {x for hop in r["drift"].values() for x in hop}
        f["drift_note" if fields == {"x_cb"} else "drift_telephone"] = r["id"]
    dropped = [r for r in rows if r["reached_payer"] and r["fields_missing_at_payer"] and not r["any_drift"]]
    f["dropped_total"] = str(len(dropped)); f["dropped_times"] = times(len(dropped))
    f["dropped_ids"] = " and ".join(r["id"] for r in dropped)
    f["dropped_fields"] = ", ".join(sorted({x for r in dropped for x in r["fields_missing_at_payer"]}))
    f["dropped_correct_otherwise"] = str(sum(1 for r in dropped if r["act_correct"]))
    f["lines_short_at_payer"] = str(sum(1 for r in rows if r["arm"] in C.LINE_ARMS and r["reached_payer"] and r["fields_missing_at_payer"]))
    f["lines_reached_payer"] = str(sum(1 for r in rows if r["arm"] in C.LINE_ARMS and r["reached_payer"]))
    f["wrong_acts_total"] = str(sum(1 for r in rows if r["acted"] and not r["act_correct"]))
    f["harness_faults"] = str(sum(1 for r in rows if r["harness_fault"]))
    f["repeat4"] = str(sum(1 for r in rows if r["repeat"] == 4))
    # the readback false alarms on Haiku 4.5, and their tier
    fa45 = [x for r in rows if r["model"] == "haiku45" and r["arm"] == "R" for x in r["false_alarms"]]
    f["rbfa_h45_all"] = str(len(fa45))
    f["rbfa_h45_integrity"] = str(sum(1 for x in fa45 if "tier2 integrity" in x))
    fa55 = [x for r in rows if r["model"] == "haiku55" and r["arm"] == "R" for x in r["false_alarms"]]
    f["rbfa_h55_all"] = str(len(fa55))
    f["cost_ratio"] = f"{sum(r['cost_usd'] for r in rows if r['model'] == 'haiku45') / sum(r['cost_usd'] for r in rows if r['model'] == 'haiku55'):.0f}"
    # excluded chains, from results/excluded.json
    ex = results / "excluded.json"
    f["excluded"] = str(len(load(ex))) if ex.exists() else "0"
    # the pilot and the ladder, from their own summaries
    pilot = results / "pilot" / "summary.json"
    if pilot.exists():
        p = load(pilot)
        f["pilot_chains"] = str(p["chains"])
        R = [r for r in p["rows"] if r["arm"] == "R"]; F = [r for r in p["rows"] if r["arm"] == "F"]
        f["pilot_R_correct"] = f"{sum(1 for r in R if r['outcome'] == 'correct')} of {len(R)}"
        f["pilot_R_refusals"] = str(sum(len(r["refusals"]) for r in R))
        f["pilot_F_loss"] = f"{sum(1 for r in F if r['outcome'] != 'correct' or r['fields_missing_at_payer'])} of {len(F)}"
        cost = p["cost_usd_total"]
        for level, key in (("level0", "ladder0"), ("level1", "ladder1")):
            q = results / "pilot" / level / "summary.json"
            if not q.exists():
                continue
            q = load(q)
            cost += q["cost_usd_total"]
            for model, m in MODELS.items():
                c = q["cells"][f"B1-F-{model}-k2"]
                f[f"{key}_loss_{m}"] = kn(c["loss"])
                f[f"{key}_correct_{m}"] = kn(c["correct_act"])
        f["pilot_cost"] = f"${cost:,.2f}"
    # the blind second reading, from results/validation
    reader = results / "validation" / "reader.json"
    if reader.exists():
        rd = load(reader)
        by_id = {r["id"]: r for r in rows}
        act = fields = drift_agree = 0
        for cid, v in rd.items():
            r = by_id[cid]
            act += v["act"] == r["outcome"]
            fields += (bool(v["coverage_at_payer"]) and all(x == "ok" for x in v["coverage_at_payer"].values())) == r["all_fields_at_payer"]
            drift_agree += bool(v["drift"]) == r["any_drift"]
        f["val_n"] = str(len(rd))
        f["val_act"] = f"{act} of {len(rd)}"; f["val_fields"] = f"{fields} of {len(rd)}"; f["val_drift"] = f"{drift_agree} of {len(rd)}"
    return f


def fig(f: dict, key: str) -> str:
    return f'<span data-fig="{key}">{html.escape(f[key])}</span>'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--figures", action="store_true")
    a = ap.parse_args(argv)
    f = figures()
    if a.figures:
        print(json.dumps(f, indent=1)); return 0
    from site_text import render  # the page text lives beside this, written once the results were in
    html_text = render(f, fig)
    if "RESULTS_" in html_text:
        sys.exit("the page text still carries a RESULTS_ placeholder; fill it before writing the page")
    if "—" in html_text:
        sys.exit("the page text carries an em dash")
    PAGE.write_text(html_text)
    print("wrote", PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
