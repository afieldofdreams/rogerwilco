#!/usr/bin/env python3
"""The site page for study 7, generated from results/summary.json so that no figure on it is typed by hand.

  python3 tools/site_page.py            # writes app/static/research/tool-prepare.html (then run app/tools/stamp.py)
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

PAGE = C.REPO / "app" / "static" / "research" / "tool-prepare.html"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def cell(s: dict, block: int, arm: str, model: str) -> dict | None:
    return s["cells"].get(f"B{block}-{arm}-{model}")


def figures(results: Path = C.RESULTS) -> dict:
    """Named figures from the main run's summary and the pilot's. Strings, as they appear on the page."""
    s = load(results / "summary.json")
    f = {}
    def r(c, key):
        v = c[key]; return v["k"], v["n"], v["hi"]
    def pct(x):
        return f"{100 * x:.1f}%"
    rows = s["rows"]
    for model, prefix in (("haiku", ""), ("gpt54mini", "g_")):
        for block, arms in ((1, "ACDEPQ"), (2, "ADPQ"), (0, "PQ")):
          for arm in arms:
              c = cell(s, block, arm, model)
              if not c:
                  continue
              p = f"{prefix}b{block}_{arm}"
              k, n, hi = r(c, "wrong_acts_induced"); f[f"{p}_wrong"] = f"{k} of {n}"; f[f"{p}_wrong_hi"] = pct(hi)
              k, n, hi = r(c, "wrong_acts_clean"); f[f"{p}_wrong_clean"] = f"{k} of {n}"
              k, n, hi = r(c, "caught_before_act"); f[f"{p}_caught"] = f"{k} of {n}"
              k, n, hi = r(c, "asked_induced"); f[f"{p}_asked"] = f"{k} of {n}"
              k, n, hi = r(c, "held_induced"); f[f"{p}_held"] = f"{k} of {n}"
              f[f"{p}_cost"] = f"${c['cost_usd_mean']:.3f}" if c["cost_usd_mean"] is not None else "not priced by the runner"
              f[f"{p}_turns"] = f"{c['receiver_turns_mean']:.1f}"
              f[f"{p}_traffic"] = f"{c['traffic_tokens_mean']:,}"
              f[f"{p}_output"] = f"{c['output_tokens_mean']:,}"
              f[f"{p}_n"] = str(c["trials"])
              if arm != "A":
                  k, n, hi = r(c, "false_alarms_clean"); f[f"{p}_fa"] = f"{k} of {n}"; f[f"{p}_fa_hi"] = pct(hi)
                  k, n, hi = r(c, "rejected_clean"); f[f"{p}_rej_clean"] = f"{k} of {n}"
                  k, n, hi = r(c, "false_alarms_all"); f[f"{p}_fa_all"] = f"{k} of {n}"
                  k, n, hi = r(c, "fidelity"); f[f"{p}_fid"] = f"{k} of {n}"
                  k, n, hi = r(c, "dn_honest"); f[f"{p}_honest"] = f"{k} of {n}"
              k, n, hi = r(c, "form_rejections"); f[f"{p}_form"] = f"{k} of {n}"
              k, n, hi = r(c, "caught_registered_rule"); f[f"{p}_caught_reg"] = f"{k} of {n}"
              if arm == "P":
                  sub = [x for x in rows if x["block"] == block and x["arm"] == "P" and x["model"] == model]
                  f[f"{p}_noprep"] = str(sum(1 for x in sub if not x.get("prepared")))
              if arm in "PQ":
                  k, n, hi = r(c, "prepared"); f[f"{p}_prepared"] = f"{k} of {n}"
                  k, n, hi = r(c, "commit_before_confirm"); f[f"{p}_early"] = f"{k} of {n}"; f[f"{p}_early_hi"] = pct(hi)
                  f[f"{p}_abandons"] = str(c["abandons"])
                  f[f"{p}_caught_receiver"] = str(c["caught_by_receiver"]); f[f"{p}_caught_sender"] = str(c["caught_by_sender"])
              if arm == "P":
                  k, n, hi = r(c, "relay_mismatch"); f[f"{p}_relay"] = f"{k} of {n}"; f[f"{p}_relay_hi"] = pct(hi)
                  k, n, hi = r(c, "relay_text_differs"); f[f"{p}_relay_text"] = f"{k} of {n}"
              if block == 2:
                  k, n, hi = r(c, "wrong_acts_tool"); f[f"{p}_wrong_tool"] = f"{k} of {n}"
                  k, n, hi = r(c, "wrong_acts_tool_prepare"); f[f"{p}_wrong_prepare"] = f"{k} of {n}"; f[f"{p}_wrong_prepare_hi"] = pct(hi)
                  k, n, hi = r(c, "wrong_acts_tool_commit"); f[f"{p}_wrong_commit"] = f"{k} of {n}"
                  k, n, hi = r(c, "caught_tool_prepare"); f[f"{p}_caught_prepare"] = f"{k} of {n}"
                  k, n, hi = r(c, "dn_flag_tool_commit"); f[f"{p}_flag_commit"] = f"{k} of {n}"
                  k, n, hi = r(c, "dn_flag_tool"); f[f"{p}_flag"] = f"{k} of {n}"
                  k, n, hi = r(c, "receiver_reported_tool"); f[f"{p}_reported"] = f"{k} of {n}"
                  sub = [x for x in rows if x["block"] == 2 and x["arm"] == arm and x["model"] == model]
                  f[f"{p}_none"] = str(sum(1 for x in sub if not x["acted"] and not x["asked"] and not x["held"]))
                  f[f"{p}_asked_tool"] = f"{sum(1 for x in sub if x['asked'])} of {len(sub)}"
                  f[f"{p}_asked_prepare"] = f"{sum(1 for x in sub if x['asked'] and x.get('tool_fault_at') == 'prepare')} of {len([x for x in sub if x.get('tool_fault_at') == 'prepare'])}"
                  f[f"{p}_asked_commit"] = f"{sum(1 for x in sub if x['asked'] and x.get('tool_fault_at') == 'commit')} of {len([x for x in sub if x.get('tool_fault_at') == 'commit'])}"
    for model, prefix in (("haiku", ""), ("gpt54mini", "g_")):
        mrows = [x for x in rows if x["model"] == model]
        if not mrows:
            continue
        f[f"{prefix}model_trials"] = f"{len(mrows):,}"
        f[f"{prefix}model_status_not_ok"] = str(sum(1 for x in mrows if x["status"] != "ok"))
        f[f"{prefix}model_held"] = str(sum(1 for x in mrows if x["held"]))
        if model == "gpt54mini":
            # the API runner records tokens and no price; the published rates for gpt-5.4-mini are $0.75 per million uncached
            # input tokens, $0.075 cached and $4.50 output (October 2026)
            usd = sum((x["usage"]["input"] * 0.75 + x["usage"]["cache_read"] * 0.075 + x["usage"]["output"] * 4.5) / 1e6 for x in mrows)
            f["g_cost_note"] = f"${usd:,.0f}"
    f["trials"] = f"{len(rows):,}"
    f["cost_total"] = f"${sum(x.get('cost_usd') or 0 for x in rows):,.0f}"
    f["status_not_ok"] = str(sum(1 for x in rows if x["status"] != "ok"))
    f["held_total"] = str(sum(1 for x in rows if x["held"]))
    f["wrong_total"] = str(sum(1 for x in rows if x["wrong_act"]))
    f["outside_tool"] = str(sum(1 for x in rows if x["acted"] and not x["through_tool"]))
    # tests
    for m, t in s.get("tests", {}).items():
        for name, v in t.items():
            key = name.split()[0].lower()
            if "p" in v:
                f[f"{key}_{m}_p"] = f"{v['p']:.2f}" if v["p"] >= 0.01 else "under 0.01"
            if "holds" in v:
                f[f"{key}_{name.split()[1]}_{m}_holds"] = "holds" if v["holds"] else "does not hold"
    # the pilots, from their own summaries
    for name, prefix in (("pilot", "pilot_"), ("pilot-gpt54mini", "gpilot_"), ("pilot-gpt54mini-first", "gpilot1_"), ("pilot-haiku45", "h45_")):
        p = results / name / "summary.json"
        if not p.exists():
            continue
        prow = load(p)["rows"]
        f[f"{prefix}trials"] = str(len(prow))
        f[f"{prefix}not_ok"] = str(sum(1 for x in prow if x["status"] != "ok"))
        f[f"{prefix}reached"] = str(sum(1 for x in prow if x["status"] == "ok" and (x["acted"] or x["held"] or x["asked"])))
        f[f"{prefix}wrong"] = str(sum(1 for x in prow if x["wrong_act"]))
        f[f"{prefix}cost"] = f"${sum(x.get('cost_usd') or 0 for x in prow):,.2f}"
        for arm in "CDQ":
            ind = [x for x in prow if x["arm"] == arm and x["kind"] == "induced"]
            allr = [x for x in prow if x["arm"] == arm]
            if allr:
                f[f"{prefix}{arm}_wrong"] = f"{sum(x['wrong_act'] for x in ind)} of {len(ind)}"
                f[f"{prefix}{arm}_held"] = f"{sum(x['held'] for x in allr)} of {len(allr)}"
                f[f"{prefix}{arm}_reached"] = f"{sum(1 for x in allr if x['status'] == 'ok' and (x['acted'] or x['held'] or x['asked']))} of {len(allr)}"
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
    html_text = render(f, fig)
    if "RESULTS_" in html_text:
        sys.exit("the page text still carries a RESULTS_ placeholder; fill it before writing the page")
    PAGE.write_text(html_text)
    print("wrote", PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
