#!/usr/bin/env python3
"""The site page for study 6, generated from results/summary.json so that no figure on it is typed by hand.

  python3 tools/site_page.py            # writes app/static/research/plan-readback.html (then run app/tools/stamp.py)
  python3 tools/site_page.py --figures  # prints the named figures the page carries, as the app test recomputes them

Every number in the prose is a <span data-fig="name">value</span>; figures() is the single source of those values and
app/tests/test_research_figures.py asserts the committed page carries exactly what figures() computes from the JSON.
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

PAGE = C.REPO / "app" / "static" / "research" / "plan-readback.html"
PILOTS = {"pilot-0b": "pilot-0b", "ladder-h1": "ladder/pilot-h1", "ladder-h2": "ladder/pilot-h2", "ladder-h3": "ladder/pilot-h3", "haiku45": "pilot-haiku45"}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def cell(s: dict, block: int, arm: str, model: str) -> dict | None:
    return s["cells"].get(f"B{block}-{arm}-{model}")


def figures(results: Path = C.RESULTS) -> dict:
    """Named figures from the main run's summary and the pilots' summaries. Strings, as they appear on the page."""
    s = load(results / "summary.json")
    f = {}
    def r(c, key):
        v = c[key]; return v["k"], v["n"], v["hi"]
    # block 2 bounds, no readback and execution readback, per receiver
    for model in ("sonnet", "haiku"):
        for arm in "ABCDE":
            c = cell(s, 2, arm, model)
            if not c:
                continue
            k, n, hi = r(c, "wrong_acts_induced"); f[f"b2_{arm}_{model}_wrong"] = f"{k} of {n}"; f[f"b2_{arm}_{model}_wrong_hi"] = f"{100 * hi:.1f}%"
            k, n, hi = r(c, "asked_induced"); f[f"b2_{arm}_{model}_asked"] = f"{k} of {n}"
            if arm != "A":
                k, n, hi = r(c, "false_alarms_clean"); f[f"b2_{arm}_{model}_fa"] = f"{k} of {n}"; f[f"b2_{arm}_{model}_fa_hi"] = f"{100 * hi:.1f}%"
                k, n, hi = r(c, "rejected_clean"); f[f"b2_{arm}_{model}_rej_clean"] = f"{k} of {n}"
                k, n, hi = r(c, "false_alarms_all"); f[f"b2_{arm}_{model}_fa_all"] = f"{k} of {n}"
                k, n, hi = r(c, "rb_covers_act"); f[f"b2_{arm}_{model}_cov"] = f"{k} of {n}"
                k, n, hi = r(c, "fidelity"); f[f"b2_{arm}_{model}_fid"] = f"{k} of {n}"
                k, n, hi = r(c, "dn_honest"); f[f"b2_{arm}_{model}_honest"] = f"{k} of {n}"
            f[f"b2_{arm}_{model}_cost"] = f"${c['cost_usd_mean']:.2f}"
            f[f"b2_{arm}_{model}_turns"] = f"{c['receiver_turns_mean']:.1f}"
            f[f"b2_{arm}_{model}_traffic"] = f"{c['traffic_tokens_mean']:,}"
    # block 1
    for model in ("sonnet", "haiku"):
        for arm in "ACD":
            c = cell(s, 1, arm, model)
            if not c:
                continue
            k, n, hi = r(c, "wrong_acts_induced"); f[f"b1_{arm}_{model}_wrong"] = f"{k} of {n}"
            k, n, hi = r(c, "caught_before_act"); f[f"b1_{arm}_{model}_caught"] = f"{k} of {n}"
            k, n, hi = r(c, "asked_induced"); f[f"b1_{arm}_{model}_asked"] = f"{k} of {n}"
            if arm != "A":
                k, n, hi = r(c, "fidelity"); f[f"b1_{arm}_{model}_fid"] = f"{k} of {n}"
                k, n, hi = r(c, "false_alarms_clean"); f[f"b1_{arm}_{model}_fa"] = f"{k} of {n}"
    # block 3
    for model in ("sonnet", "haiku"):
        for arm in "ABD":
            c = cell(s, 3, arm, model)
            if not c:
                continue
            k, n, hi = r(c, "dn_flag_tool"); f[f"b3_{arm}_{model}_flag"] = f"{k} of {n}"
            k, n, hi = r(c, "dn_honest"); f[f"b3_{arm}_{model}_honest"] = f"{k} of {n}"
            k, n, hi = r(c, "receiver_reported_tool"); f[f"b3_{arm}_{model}_reported"] = f"{k} of {n}"
    # totals
    rows = s["rows"]
    f["trials"] = f"{len(rows):,}"
    f["cost_total"] = f"${sum(x.get('cost_usd') or 0 for x in rows):,.0f}"
    f["status_not_ok"] = str(sum(1 for x in rows if x["status"] != "ok"))
    for model in ("sonnet", "haiku"):
        b2 = [x for x in rows if x["block"] == 2 and x["arm"] == "A" and x["model"] == model and x["kind"] == "induced"]
        f[f"b2_A_{model}_n"] = str(len(b2))
    # the pilots: the ladder and the probe, from their own summaries
    pooled = {"sonnet": [0, 0], "haiku": [0, 0]}
    for name, rel in PILOTS.items():
        p = results / rel / "summary.json"
        if not p.exists():
            continue
        ps = load(p)
        for model in ("sonnet", "haiku", "haiku45"):
            c = cell(ps, 2, "A", model)
            if c:
                k, n, hi = r(c, "wrong_acts_induced"); f[f"{name}_{model}_wrong"] = f"{k} of {n}"
                k2, n2, _ = r(c, "asked_induced"); f[f"{name}_{model}_asked"] = f"{k2} of {n2}"
                if model in pooled and name != "haiku45":
                    pooled[model][0] += k; pooled[model][1] += n
    for model, (k, n) in pooled.items():
        if n:
            from analyse import cp_interval
            f[f"ladder_{model}_pooled"] = f"{k} of {n}"; f[f"ladder_{model}_pooled_hi"] = f"{100 * cp_interval(k, n)[1]:.1f}%"
    # the cross-vendor run: the same design on receivers outside Anthropic, through the API harness
    api = results / "api" / "summary.json"
    if api.exists():
        a = load(api)
        arows = a["rows"]
        f["api_trials"] = f"{len(arows):,}"
        f["api_status_not_ok"] = str(sum(1 for x in arows if x["status"] != "ok"))
        for model in ("gpt55", "gpt54mini"):
            for block, arms in ((2, "ABCDE"), (1, "ACD"), (3, "ABD")):
                for arm in arms:
                    c = cell(a, block, arm, model)
                    if not c:
                        continue
                    k, n, hi = r(c, "wrong_acts_induced"); f[f"api_b{block}_{arm}_{model}_wrong"] = f"{k} of {n}"; f[f"api_b{block}_{arm}_{model}_wrong_hi"] = f"{100 * hi:.1f}%"
                    k, n, hi = r(c, "asked_induced"); f[f"api_b{block}_{arm}_{model}_asked"] = f"{k} of {n}"
                    k, n, hi = r(c, "caught_before_act"); f[f"api_b{block}_{arm}_{model}_caught"] = f"{k} of {n}"
                    held = [x for x in arows if x["block"] == block and x["arm"] == arm and x["model"] == model]
                    f[f"api_b{block}_{arm}_{model}_held"] = f"{sum(1 for x in held if x['held'])} of {len(held)}"
                    f[f"api_b{block}_{arm}_{model}_turns"] = f"{c['receiver_turns_mean']:.1f}"
                    if arm != "A":
                        k, n, hi = r(c, "false_alarms_clean"); f[f"api_b{block}_{arm}_{model}_fa"] = f"{k} of {n}"
                        k, n, hi = r(c, "false_alarms_all"); f[f"api_b{block}_{arm}_{model}_fa_all"] = f"{k} of {n}"
                        k, n, hi = r(c, "rb_covers_act"); f[f"api_b{block}_{arm}_{model}_cov"] = f"{k} of {n}"
                        k, n, hi = r(c, "fidelity"); f[f"api_b{block}_{arm}_{model}_fid"] = f"{k} of {n}"
                    if block == 3:
                        k, n, hi = r(c, "dn_flag_tool"); f[f"api_b3_{arm}_{model}_flag"] = f"{k} of {n}"
                        k, n, hi = r(c, "dn_honest"); f[f"api_b3_{arm}_{model}_honest"] = f"{k} of {n}"
                        k, n, hi = r(c, "receiver_reported_tool"); f[f"api_b3_{arm}_{model}_reported"] = f"{k} of {n}"
        for model, t in a.get("tests", {}).items():
            for name, v in t.items():
                key = name.split()[0].lower()
                if "p" in v:
                    f[f"api_{key}_{model}_p"] = f"{v['p']:.2f}" if v["p"] >= 0.01 else "under 0.01"
                if "holds" in v:
                    f[f"api_{key}_{model}_holds"] = "holds" if v["holds"] else "does not hold"
    # tests
    for model, t in s.get("tests", {}).items():
        for name, v in t.items():
            key = name.split()[0].lower()
            if "p" in v:
                f[f"{key}_{model}_p"] = f"{v['p']:.2f}" if v["p"] >= 0.01 else "under 0.01"
            if "holds" in v:
                f[f"{key}_{model}_holds"] = "holds" if v["holds"] else "does not hold"
    return f


def fig(f: dict, key: str) -> str:
    return f'<span data-fig="{key}">{html.escape(f[key])}</span>'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--figures", action="store_true")
    a = ap.parse_args(argv)
    f = figures()
    if a.figures:
        print(json.dumps(f, indent=1)); return 0
    from site_text import render  # the page text lives beside this, written once the results are in
    PAGE.write_text(render(f, fig))
    print("wrote", PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
