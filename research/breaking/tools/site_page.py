#!/usr/bin/env python3
"""The site page for study 9, generated from results/summary.json so that no figure on it is typed by hand.

  python3 tools/site_page.py --figures  # prints the named figures the page will carry, as the app test recomputes them
  python3 tools/site_page.py            # writes app/static/research/breaking.html from tools/site_text.py (then run app/tools/stamp.py)

As study 8: every number in the prose is a <span data-fig="name">value</span>; figures() is the single source of those
values and app/tests/test_research_figures.py asserts the committed page carries exactly what figures() computes from the
JSON. The page text (site_text.py) is written once the main run's results are in; until then this tool only prints the
figures. The headline is the grid the protocol names: model by arm, block 1 correct-act proportion with its interval, and
the block 5 complied proportion beside it.
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

PAGE = C.REPO / "app" / "static" / "research" / "breaking.html"
MODELS = {"qwen15": "q15", "qwen3b": "q3", "llama3b": "l3", "qwen7b": "q7", "qwen14b": "q14", "haiku45": "h45", "haiku55": "h55",   # alias -> figure prefix
          # the cross-vendor extension, 25 October 2026
          "or-llama3b": "ol3", "or-llama8b": "ol8", "or-ministral8b": "om8", "or-gemma12b": "og12", "or-ministral14b": "om14", "or-gemma27b": "og27",
          "or-llama70b": "ol70", "or-gpt54mini": "ogpt", "or-geminilite": "ogem", "or-deepseekflash": "odsf"}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def kn(r: dict) -> str:
    return f"{r['k']} of {r['n']}"


def ci(r: dict) -> str:
    """The proportion and its exact 95% interval as the README writes them: 82%, 68 to 92; 'none attempted' for 0 of 0."""
    if not r.get("n"):
        return "none attempted"
    return f"{100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f}"


def med_of(xs: list):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 1)


def num(x) -> str:
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return f"{x:,}" if isinstance(x, int) else str(x)


def pval(p: float) -> str:
    if p < 0.001:
        return "under 0.001"
    s = f"{p:.3f}".rstrip("0").rstrip(".")
    return "1.0" if s == "1" else s


def figures(results: Path = C.RESULTS) -> dict:
    """Named figures from the main run's summary and the pilot's. Strings, as they appear on the page."""
    s = load(results / "summary.json")
    cells, all_rows = s["cells"], s["rows"]
    # study 9's own run is the local models and the anchors; the hosted models of the extension (25 October 2026) are read
    # apart, under x_ keys below, so that no figure of the original write-up moves
    rows = [r for r in all_rows if r["model"] in C.STUDY_MODELS]
    xrows = [r for r in all_rows if r["model"] in C.API_MODELS]
    f: dict[str, str] = {}
    f["chains"] = f"{len(rows):,}"
    f["cost_total"] = f"${sum(r['cost_usd'] or 0 for r in rows):,.2f}"
    f["wall_hours"] = f"{sum(r['wall_seconds'] or 0 for r in rows) / 3600:,.1f}"
    def form(x: dict) -> bool:
        return not any("mismatch" in q for q in x.get("problems", []))

    for model, m in MODELS.items():
        mrows = [r for r in all_rows if r["model"] == model]
        if not mrows:
            continue
        f[f"chains_{m}"] = f"{len(mrows):,}"
        f[f"cost_{m}"] = f"${sum(r['cost_usd'] or 0 for r in mrows):,.2f}"
        f[f"costchain_{m}"] = f"${sum(r['cost_usd'] or 0 for r in mrows) / len(mrows):,.4f}"
        f[f"wall_h_{m}"] = f"{sum(r['wall_seconds'] or 0 for r in mrows) / 3600:.1f}"
        f[f"wall_med_{m}"] = num(med_of([r.get("wall_seconds") for r in mrows]))
        f[f"wrong_acts_{m}"] = str(sum(1 for r in mrows if r["acted"] and r["outcome"] == "wrong"))
        f[f"wrong_acts_C_{m}"] = str(sum(1 for r in mrows if r["acted"] and r["outcome"] == "wrong" and r["arm"] == "C"))
        f[f"reached_{m}"] = f"{sum(1 for r in mrows if r['reached_payer'])} of {len(mrows)}"
        f[f"served_{m}"] = ", ".join(sorted({x for r in mrows for x in (r.get("models_seen") or [])})) or "not recorded"
        f[f"complied_{m}"] = str(sum(1 for r in mrows if r["complied"]))
        f[f"b5n_{m}"] = str(sum(1 for r in mrows if r["block"] == 5))
        # arm R and arm C over every block: readbacks checked, form refusals, held with values right, chains with an RB that did not parse
        for arm in C.CHECKED_ARMS:
            ar = [r for r in mrows if r["arm"] == arm]
            if not ar:
                continue
            rbs = sum(r["readbacks_checked"] for r in ar)
            refs = [x for r in ar for x in r["refusals"] if x["what"] in ("rb", "rb2")]
            fr = [x for x in refs if form(x)]
            f[f"{arm}_rb_{m}"] = f"{rbs:,}"
            f[f"{arm}_rbform_{m}"] = f"{len(fr)} of {rbs:,}"
            f[f"{arm}_rbparse_{m}"] = str(sum(1 for x in fr if any(q.startswith('parse:') for q in x['problems'])))
            f[f"{arm}_rbomit_{m}"] = str(sum(1 for x in fr if any('does not echo' in q for q in x['problems']) and not any(q.startswith('parse:') for q in x['problems'])))
            f[f"{arm}_rbvalue_{m}"] = str(len(refs) - len(fr))
            f[f"{arm}_held_{m}"] = f"{sum(r['held'] for r in ar)} of {len(ar)}"
            f[f"{arm}_heldvr_{m}"] = f"{sum(1 for r in ar if r['held'] and r['refusals'] and r['refusals'][-1]['what'] in ('rb', 'rb2') and form(r['refusals'][-1]))} of {len(ar)}"
            f[f"{arm}_stall_{m}"] = f"{sum(bool(r['readback_stall']) for r in ar)} of {len(ar)}"
            f[f"{arm}_parsechains_{m}"] = f"{sum(1 for r in ar if any(x['what'] in ('rb', 'rb2') and any(q.startswith('parse:') for q in x['problems']) for x in r['refusals']))} of {len(ar)}"
            cf = sum(r["correct_forwards"] for r in ar)
            f[f"{arm}_fa_{m}"] = f"{sum(sum(1 for x in r['false_alarms'] if ' forward:' in x) for r in ar)} of {cf:,}"
            f[f"{arm}_rbfa_{m}"] = f"{sum(sum(1 for x in r['false_alarms'] if ' forward:' not in x) for r in ar)} of {rbs:,}"
            f[f"{arm}_caught_{m}"] = str(sum(len(r["caught"]) for r in ar))
            f[f"{arm}_correct_{m}"] = f"{sum(r['outcome'] == 'correct' for r in ar)} of {len(ar)}"
        for block in (1, 2, 3, 5, 6):
            for arm in C.ARMS:
                c = cells.get(f"B{block}-{arm}-{model}-k2")
                if not c:
                    continue
                p = f"b{block}_{arm}_{m}"
                f[f"{p}_n"] = str(c["chains"])
                f[f"{p}_correct"] = kn(c["correct_act"]); f[f"{p}_correct_ci"] = ci(c["correct_act"])
                f[f"{p}_correct_run"] = kn(c["correct_act_of_run"])
                f[f"{p}_expected"] = kn(c["as_expected"])
                f[f"{p}_fields"] = kn(c["all_fields_at_payer"])
                f[f"{p}_asked"] = kn(c["asked"]); f[f"{p}_held"] = kn(c["held"]); f[f"{p}_stall"] = kn(c["readback_stall"])
                f[f"{p}_heldvr"] = kn(c["held_values_right"]); f[f"{p}_notdone"] = kn(c["not_done"])
                f[f"{p}_wrong_act"] = kn(c["wrong_act"]); f[f"{p}_wrong_act_ci"] = ci(c["wrong_act"])
                f[f"{p}_wrong_values"] = kn(c["wrong_values_act"]); f[f"{p}_uncovered"] = kn(c["acted_uncovered"])
                f[f"{p}_elsewhere"] = kn(c["asked_elsewhere"]); f[f"{p}_graded_wrong"] = kn(c["graded_wrong"])
                f[f"{p}_wrong_value"] = kn(c["wrong_value_forwarded"])
                f[f"{p}_size1"] = num(c["size_median_by_hop"].get("1")); f[f"{p}_size_payer"] = num(c["size_median_by_hop"].get("3")); f[f"{p}_traffic"] = num(c["traffic_median"])
                f[f"{p}_turns"] = f"{c['model_turns_mean']:.1f}"; f[f"{p}_wall"] = num(c["wall_seconds_median"]); f[f"{p}_cost"] = f"${c['cost_usd_mean']:.3f}"
                if c.get("valid_line"):
                    f[f"{p}_valid"] = kn(c["valid_line"]); f[f"{p}_valid_ci"] = ci(c["valid_line"])
                if c.get("complied"):
                    f[f"{p}_complied"] = kn(c["complied"]); f[f"{p}_complied_ci"] = ci(c["complied"])
                    f[f"{p}_injected"] = kn(c["injected_value_forwarded"])
                if arm in C.CHECKED_ARMS:
                    f[f"{p}_caught"] = str(c["caught"]); f[f"{p}_fa"] = kn(c["false_alarms_over_correct_forwards"])
                    f[f"{p}_rbfa"] = kn(c["readback_false_alarms_over_readbacks"]); f[f"{p}_rbform"] = kn(c["readback_form_refusals_over_readbacks"])
        for arm in ("F", "C"):
            for K in (1, 2, 3, 5):
                c = cells.get(f"B4-{arm}-{model}-k{K}")
                if c:
                    p = f"b4_{arm}_{m}_k{K}"
                    f[f"{p}_correct"] = kn(c["correct_act"]); f[f"{p}_correct_run"] = kn(c["correct_act_of_run"])
                    f[f"{p}_size_payer"] = num(c["size_median_by_hop"].get(str(K + 1))); f[f"{p}_traffic"] = num(c["traffic_median"])
        t = s["tests"].get(model, {})
        for name, v in t.items():
            h = name.split()[0].lower().rstrip(":")
            if "p" in v and h in ("h1", "h5", "h8"):
                f[f"{h}_{m}_p"] = pval(v["p"])
            if "p" in v and h == "h4":
                f[("h4form" if "form failures" in name else "h4") + f"_{m}_p"] = pval(v["p"])
            if h == "h2" and "holds" in v:
                arm2 = name.split()[3].rstrip(":")
                f[f"h2_{arm2}_{m}"] = "holds" if v["holds"] else f"misses {len(v['misses'])}"
                f[f"h2slots_{arm2}_{m}"] = "holds" if v.get("holds_on_slots") else f"misses {len(v.get('misses_in_a_slot', []))}"
                f[f"h2tail_{arm2}_{m}"] = str(len(v.get("misses_in_the_tail_only", [])))
            if h == "h6":
                arm6 = name.split()[1].rstrip(":")
                f[f"h6_{arm6}_{m}"] = "below the floor" if v["below_floor"] else "at or above the floor"
                f[f"h6rate_{arm6}_{m}"] = v["valid"].replace(" / ", " of ") if not v["valid"].startswith("0 / 0") else "none attempted"
    floor = s["tests"].get("_H3_smallest_model_at_90_per_arm", {})
    for arm, model in floor.items():
        f[f"h3_floor_{arm}"] = C.model_name(model) if model else "none"
    f["harness_faults"] = str(sum(1 for r in rows if r["harness_fault"]))
    f["wrong_acts_total"] = str(sum(1 for r in rows if r["acted"] and r["outcome"] == "wrong"))
    f["wrong_acts_anchors"] = str(sum(1 for r in rows if r["acted"] and r["outcome"] == "wrong" and r["model"].startswith("haiku")))
    f["wrong_acts_checked"] = str(sum(1 for r in rows if r["acted"] and r["outcome"] == "wrong" and r["arm"] in C.CHECKED_ARMS))
    f["chains_checked"] = f"{sum(1 for r in rows if r['arm'] in C.CHECKED_ARMS):,}"
    f["asked_elsewhere_total"] = str(sum(1 for r in rows if (not r["acted"]) and r["outcome"] == "wrong"))
    f["complied_total"] = str(sum(1 for r in rows if r["complied"]))
    f["chains_b5"] = str(sum(1 for r in rows if r["block"] == 5))
    f["injected_tail_total"] = str(sum(1 for r in rows if any(isinstance(x, int) for x in r["injected_value_forwarded"])))
    def slot_total(models: list[str]) -> int:
        return sum(len(v.get("misses_in_a_slot", [])) for mm, mt in s["tests"].items() if mm in models and isinstance(mt, dict) for k, v in mt.items() if k.startswith("H2") and isinstance(v, dict))
    f["injected_slot_total"] = str(slot_total(C.STUDY_MODELS))
    f["wall_h_local"] = f"{sum(r['wall_seconds'] or 0 for r in rows if r['model'] in C.LOCAL_MODELS) / 3600:.1f}"
    f["chains_local"] = f"{sum(1 for r in rows if r['model'] in C.LOCAL_MODELS):,}"
    f["chains_anchors"] = f"{sum(1 for r in rows if r['model'] in C.ANCHORS):,}"
    # the extension's own totals, over the hosted models
    if xrows:
        f["x_chains"] = f"{len(xrows):,}"
        f["x_models"] = str(len({r["model"] for r in xrows}))
        f["x_cost"] = f"${sum(r['cost_usd'] or 0 for r in xrows):,.2f}"
        f["x_wall_h"] = f"{sum(r['wall_seconds'] or 0 for r in xrows) / 3600:,.1f}"
        f["x_harness_faults"] = str(sum(1 for r in xrows if r["harness_fault"]))
        f["x_wrong_acts_total"] = str(sum(1 for r in xrows if r["acted"] and r["outcome"] == "wrong"))
        f["x_wrong_acts_checked"] = str(sum(1 for r in xrows if r["acted"] and r["outcome"] == "wrong" and r["arm"] == "C"))
        f["x_chains_checked"] = f"{sum(1 for r in xrows if r['arm'] == 'C'):,}"
        f["x_wrong_acts_unchecked"] = str(sum(1 for r in xrows if r["acted"] and r["outcome"] == "wrong" and r["arm"] != "C"))
        f["x_chains_unchecked"] = f"{sum(1 for r in xrows if r['arm'] != 'C'):,}"
        f["x_complied_total"] = str(sum(1 for r in xrows if r["complied"]))
        f["x_chains_b5"] = str(sum(1 for r in xrows if r["block"] == 5))
        f["x_injected_tail_total"] = str(sum(1 for r in xrows if any(isinstance(x, int) for x in r["injected_value_forwarded"])))
        f["x_injected_slot_total"] = str(slot_total(C.API_MODELS))
        f["x_asked_elsewhere_total"] = str(sum(1 for r in xrows if (not r["acted"]) and r["outcome"] == "wrong"))
        for arm, model in s["tests"].get("_H3_smallest_hosted_model_at_90_per_arm", {}).items():
            f[f"h3_floor_hosted_{arm}"] = C.model_name(model) if model else "none"
        t10 = s["tests"].get("or-llama3b", {})
        for name, v in t10.items():
            if not name.startswith("H10"):
                continue
            key = "all" if "together" in name else name.split()[3].rstrip(":")
            if "wrong acts" in name:
                key = "wrong"
            f[f"h10_{key}_p"] = pval(v["p"])
            f[f"h10_{key}_hosted"] = v["hosted"].split(" (")[0].replace(" / ", " of ")
            f[f"h10_{key}_local"] = v["local"].split(" (")[0].replace(" / ", " of ")
        xpilot = results / "extension_pilot" / "summary.json"
        if xpilot.exists():
            xp = load(xpilot)
            f["x_pilot_chains"] = str(xp["chains"]); f["x_pilot_cost"] = f"${xp['cost_usd_total']:,.2f}"
    pilot = results / "pilot" / "summary.json"
    if pilot.exists():
        p = load(pilot)
        f["pilot_chains"] = str(p["chains"])
        f["pilot_cost"] = f"${p['cost_usd_total']:,.2f}"
    agreement = results / "validation" / "agreement.json"
    if agreement.exists():
        a = load(agreement)
        f["val_n"] = str(a["sample"]); f["val_act"] = f"{a['act']} of {a['sample']}"
        f["val_fields"] = f"{a['fields_at_payer']} of {a['sample']}"; f["val_drift"] = f"{a['drift']} of {a['sample']}"
    return f


def fig(f: dict, key: str) -> str:
    return f'<span data-fig="{key}">{html.escape(f[key])}</span>'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--figures", action="store_true"); ap.add_argument("--results", default=str(C.RESULTS))
    a = ap.parse_args(argv)
    f = figures(Path(a.results))
    if a.figures:
        print(json.dumps(f, indent=1)); return 0
    try:
        from site_text import render  # the page text lives beside this, written once the results are in
    except ImportError:
        sys.exit("tools/site_text.py does not exist yet: the page text is written after the main run; use --figures for now")
    html_text = render(f, fig)
    if "RESULTS_" in html_text:
        sys.exit("the page text still carries a RESULTS_ placeholder; fill it before writing the page")
    if chr(0x2014) in html_text:
        sys.exit("the page text carries an em dash")
    PAGE.write_text(html_text)
    print("wrote", PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
