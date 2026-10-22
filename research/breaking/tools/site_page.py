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
MODELS = {"qwen15": "q15", "qwen3b": "q3", "llama3b": "l3", "qwen7b": "q7", "haiku45": "h45", "haiku55": "h55"}   # alias -> figure prefix


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def kn(r: dict) -> str:
    return f"{r['k']} of {r['n']}"


def ci(r: dict) -> str:
    """The proportion and its exact 95% interval as the README writes them: 82%, 68 to 92."""
    return f"{100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f}"


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
    cells, rows = s["cells"], s["rows"]
    f: dict[str, str] = {}
    f["chains"] = f"{s['chains']:,}"
    f["cost_total"] = f"${s['cost_usd_total']:,.2f}"
    f["wall_hours"] = f"{s.get('wall_hours_total', 0):,.1f}"
    for model, m in MODELS.items():
        mrows = [r for r in rows if r["model"] == model]
        if not mrows:
            continue
        f[f"chains_{m}"] = f"{len(mrows):,}"
        for block in (1, 2, 3, 5):
            for arm in C.ARMS:
                c = cells.get(f"B{block}-{arm}-{model}-k2")
                if not c:
                    continue
                p = f"b{block}_{arm}_{m}"
                f[f"{p}_n"] = str(c["chains"])
                f[f"{p}_correct"] = kn(c["correct_act"]); f[f"{p}_correct_ci"] = ci(c["correct_act"])
                f[f"{p}_expected"] = kn(c["as_expected"])
                f[f"{p}_fields"] = kn(c["all_fields_at_payer"])
                f[f"{p}_asked"] = kn(c["asked"]); f[f"{p}_held"] = kn(c["held"]); f[f"{p}_stall"] = kn(c["readback_stall"])
                f[f"{p}_wrong_act"] = kn(c["wrong_act"]); f[f"{p}_wrong_value"] = kn(c["wrong_value_forwarded"])
                f[f"{p}_size_payer"] = num(c["size_median_by_hop"].get("3")); f[f"{p}_traffic"] = num(c["traffic_median"])
                f[f"{p}_turns"] = f"{c['model_turns_mean']:.1f}"
                if c.get("valid_line"):
                    f[f"{p}_valid"] = kn(c["valid_line"]); f[f"{p}_valid_ci"] = ci(c["valid_line"])
                if c.get("complied"):
                    f[f"{p}_complied"] = kn(c["complied"]); f[f"{p}_complied_ci"] = ci(c["complied"])
                    f[f"{p}_injected"] = kn(c["injected_value_forwarded"])
                if arm in C.CHECKED_ARMS:
                    f[f"{p}_caught"] = str(c["caught"]); f[f"{p}_fa"] = kn(c["false_alarms_over_correct_forwards"])
        for arm in ("F", "C"):
            for K in (1, 2, 3, 5):
                c = cells.get(f"B4-{arm}-{model}-k{K}")
                if c:
                    p = f"b4_{arm}_{m}_k{K}"
                    f[f"{p}_correct"] = kn(c["correct_act"]); f[f"{p}_size_payer"] = num(c["size_median_by_hop"].get(str(K + 1)))
        t = s["tests"].get(model, {})
        for name, v in t.items():
            h = name.split()[0].lower().rstrip(":")
            if "p" in v and h in ("h1", "h4", "h5", "h8"):
                f[f"{h}_{m}_p"] = pval(v["p"])
            if h == "h2" and "holds" in v:
                f[f"h2_{name.split()[3]}_{m}"] = "holds" if v["holds"] else f"misses {len(v['misses'])}"
            if h == "h6":
                f[f"h6_{name.split()[1].rstrip(':')}_{m}"] = "below the floor" if v["below_floor"] else "at or above the floor"
    floor = s["tests"].get("_H3_smallest_model_at_90_per_arm", {})
    for arm, model in floor.items():
        f[f"h3_floor_{arm}"] = C.model_name(model) if model else "none"
    f["harness_faults"] = str(sum(1 for r in rows if r["harness_fault"]))
    pilot = results / "pilot" / "summary.json"
    if pilot.exists():
        p = load(pilot)
        f["pilot_chains"] = str(p["chains"])
        f["pilot_cost"] = f"${p['cost_usd_total']:,.2f}"
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
