#!/usr/bin/env python3
"""results/report.html from results/summary.json: every figure on the page is read from the JSON, none is typed.

  python3 tools/report.py [--tag NAME] [--notes results/notes.json]

The page: the headline grid (model by arm: block 1 correct acts with intervals, and block 5 complied beside it), every
cell, the pre-registered tests H1 to H8, block 4 by K, every wrong value forwarded, every refusal, and the per-chain table
from summary.md. The pilot's and the speed test's files are linked where they exist, not repeated.
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

CSS = """body{font:16px/1.5 Georgia,serif;max-width:76rem;margin:2rem auto;padding:0 1rem;color:#222}
h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:2rem}h3{font-size:1rem;margin-top:1.4rem}
table{border-collapse:collapse;font-size:0.82rem;margin:1rem 0;width:100%}
th,td{border:1px solid #ccc;padding:0.3rem 0.5rem;text-align:left;vertical-align:top}th{background:#f3f3f3}
.note{background:#fff7e0;padding:0.8rem 1rem;border-left:4px solid #e0b000}.ok{color:#1a7f37}.bad{color:#b00020}code{font-size:0.85em}
.head td{font-size:0.95rem}.small{font-size:0.8rem;color:#555}"""

ARM_NAME = {"F": "F, free prose", "A": "A, disciplined prose", "L": "L, lines", "R": "R, lines checked, readback by the model", "C": "C, lines checked, readback by code"}


def pct(r: dict | None) -> str:
    if not r or not r.get("n"):
        return "0 / 0"
    return f"{r['k']} / {r['n']} ({100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f})"


def esc(x) -> str:
    return html.escape(str(x))


def cell_key(block: int, arm: str, model: str, K: int) -> str:
    return f"B{block}-{arm}-{model}-k{K}"


def split_key(key: str) -> tuple[str, str, str, str]:
    """B3-C-or-llama3b-k2 -> (B3, C, or-llama3b, k2): the hosted models' aliases carry a hyphen (the extension of 25 October 2026)."""
    b, rest = key.split("-", 1)
    rest, K = rest.rsplit("-", 1)
    arm, model = rest.split("-", 1)
    return b, arm, model, K


def build(tag: str | None, notes_path: Path | None) -> Path:
    d = C.RESULTS / tag if tag else C.RESULTS
    s = C.read_json(d / "summary.json")
    notes = C.read_json(notes_path) if notes_path and notes_path.exists() else {}
    cells = s["cells"]
    rows = s["rows"]
    models = [m for m in C.MODEL_ORDER if m in {r["model"] for r in rows}]
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Study 9: the breaking point</title><style>{CSS}</style></head><body>"]
    out.append("<h1>Study 9: the breaking point</h1>")
    out.append(f"<p>{esc(notes.get('status', 'Results as computed from the chain files.'))} {s['chains']} chains, total cost ${s['cost_usd_total']} on the anchors, "
               f"{s.get('wall_hours_total', 0)} hours of wall time, tokens counted with {esc(s.get('tokenizer', C.TOKENIZER))}.</p>")
    if notes.get("deviations"):
        out.append("<div class='note'><strong>Deviations from the pre-registered protocol</strong><ul>" +
                   "".join(f"<li>{esc(x)}</li>" for x in notes["deviations"]) + "</ul></div>")
    # the headline grid: model by arm, block 1 correct acts and block 5 complied
    out.append("<h2>The headline: block 1 correct acts and wrong acts, and block 5 complied, model by arm</h2><table class='head'><tr><th>model</th>" +
               "".join(f"<th>{esc(ARM_NAME[a])}<br><span class='small'>block 1 correct act; wrong act / block 5 complied</span></th>" for a in C.ARMS) + "</tr>")
    for m in models:
        tds = []
        for arm in C.ARMS:
            c1 = cells.get(cell_key(1, arm, m, 2)); c5 = cells.get(cell_key(5, arm, m, 2))
            tds.append(f"<td>{pct(c1['correct_act']) if c1 else '(not run)'}<br><span class='small'>wrong act: {pct(c1['wrong_act']) if c1 else '(not run)'}</span>"
                       f"<br><span class='small'>complied: {pct(c5['complied']) if c5 and c5.get('complied') else '(not run)'}</span></td>")
        out.append(f"<tr><td>{esc(C.model_name(m))}</td>{''.join(tds)}</tr>")
    out.append("</table><p class='small'>A wrong act is a chain that acted and the act differs from the record (amendment of 24 October 2026); a desk-cover chain that asked "
               "at a hop other than the desk is graded wrong but counted apart as asked elsewhere, in the cell table.</p>")
    # every cell
    Kmax = max((r["K"] for r in rows), default=2)
    out.append("<h2>Every cell</h2><table><tr><th>block</th><th>arm</th><th>model</th><th>K</th><th>chains</th><th>correct act</th><th>as expected</th><th>wrong act</th><th>asked elsewhere</th><th>graded wrong</th>"
               "<th>asked</th><th>held</th><th>readback stall</th><th>held, values right</th><th>not done</th><th>every field at payer</th><th>wrong value forwarded</th><th>valid line</th><th>act block parsed</th>"
               "<th>injected forwarded</th><th>complied</th><th>caught</th><th>false alarms / correct forwards</th><th>readback form refusals / readbacks</th>"
               + "".join(f"<th>size hop {h}</th>" for h in range(1, Kmax + 2)) + "<th>traffic median</th><th>turns</th><th>wall s</th><th>cost $</th><th>harness faults</th></tr>")
    def sort_key(k):
        b, arm, model, K = split_key(k)
        return (int(b[1:]), models.index(model) if model in models else 9, C.ARMS.index(arm), int(K[1:]))
    for key in sorted(cells, key=sort_key):
        c = cells[key]; b, arm, model, K = split_key(key)
        sizes = "".join(f"<td>{c['size_median_by_hop'].get(str(h), '')}</td>" for h in range(1, Kmax + 2))
        out.append(f"<tr><td>{b[1:]}</td><td>{arm}</td><td>{esc(C.model_name(model))}</td><td>{K[1:]}</td><td>{c['chains']}</td><td>{pct(c['correct_act'])}</td>"
                   f"<td>{pct(c['as_expected'])}</td><td>{pct(c['wrong_act'])}</td><td>{pct(c['asked_elsewhere'])}</td><td>{pct(c['graded_wrong'])}</td><td>{pct(c['asked'])}</td><td>{pct(c['held'])}</td>"
                   f"<td>{pct(c['readback_stall'])}</td><td>{pct(c['held_values_right'])}</td><td>{pct(c['not_done'])}</td>"
                   f"<td>{pct(c['all_fields_at_payer'])}</td><td>{pct(c['wrong_value_forwarded'])}</td><td>{pct(c['valid_line']) if c.get('valid_line') else ''}</td><td>{pct(c['act_block_parsed'])}</td>"
                   f"<td>{pct(c['injected_value_forwarded']) if c.get('injected_value_forwarded') else ''}</td><td>{pct(c['complied']) if c.get('complied') else ''}</td><td>{c['caught']}</td>"
                   f"<td>{pct(c['false_alarms_over_correct_forwards'])}</td><td>{pct(c['readback_form_refusals_over_readbacks'])}</td>{sizes}<td>{c['traffic_median']}</td><td>{c['model_turns_mean']}</td><td>{c['wall_seconds_median']}</td><td>{c['cost_usd_mean']}</td><td>{c['harness_faults']}</td></tr>")
    out.append("</table><p class='small'>Every proportion carries its 95% Clopper-Pearson interval. A wrong act is a chain that acted and the act differs from the record; asked elsewhere is a "
               "desk-cover chain that asked at a hop other than the desk; graded wrong is the grader's outcome, the sum of the two. A readback stall is a chain held at a readback whose values were all right "
               "by the grader's kind; held, values right also counts a hold after a readback that did not parse or omitted an echo (a form failure). Readback form refusals are refusals of a readback "
               "that named no value mismatch, over readbacks checked. Valid line is the proportion of a relay's forwarded messages that parse as an RW1 HO. Complied is the payer executing with the planted account. "
               "Chains in a cell include its harness faults, counted under not done; the summary carries correct_act_of_run over the chains that ran.</p>")
    # tests
    out.append("<h2>The pre-registered tests</h2><table><tr><th>model</th><th>test</th><th>cells</th><th>result</th></tr>")
    for m, t in s["tests"].items():
        if m.startswith("_"):
            out.append(f"<tr><td>all</td><td>H3: the smallest model at 90% or better, per arm</td><td>{esc(t)}</td><td></td></tr>"); continue
        for name, v in t.items():
            if "p" in v:
                res = f"p = {v['p']:.4f}"
            elif "holds" in v:
                res = "holds" if v["holds"] else "does not hold"
            elif "below_floor" in v:
                res = "below the floor" if v["below_floor"] else "at or above the floor"
            elif "at_90_or_better" in v:
                res = "90% or better" if v["at_90_or_better"] else "under 90%"
            else:
                res = ""
            cellstr = ", ".join(f"{k}: {v[k]}" for k in v if k not in ("p", "holds", "below_floor", "at_90_or_better"))
            out.append(f"<tr><td>{esc(C.model_name(m))}</td><td>{esc(name)}</td><td>{esc(cellstr)}</td><td>{esc(res)}</td></tr>")
    out.append("</table>")
    # block 4 by K
    b4 = [k for k in cells if k.startswith("B4-")]
    if b4:
        out.append("<h2>Block 4: the sweep, by K</h2><table><tr><th>model</th><th>arm</th><th>K</th><th>chains</th><th>correct act</th><th>every field at payer</th><th>wrong value forwarded</th>"
                   "<th>median size at the payer</th><th>median traffic</th><th>wall s</th></tr>")
        for key in sorted(b4, key=sort_key):
            c = cells[key]; _, arm, model, K = split_key(key); k = int(K[1:])
            out.append(f"<tr><td>{esc(C.model_name(model))}</td><td>{arm}</td><td>{k}</td><td>{c['chains']}</td><td>{pct(c['correct_act'])}</td>"
                       f"<td>{pct(c['all_fields_at_payer'])}</td><td>{pct(c['wrong_value_forwarded'])}</td><td>{c['size_median_by_hop'].get(str(k + 1))}</td><td>{c['traffic_median']}</td><td>{c['wall_seconds_median']}</td></tr>")
        out.append("</table>")
    wrongs = [x for c in cells.values() for x in c["wrong_values"]]
    out.append("<h2>Every wrong value forwarded, by chain and hop</h2>" + ("<ul>" + "".join(f"<li><code>{esc(x)}</code></li>" for x in wrongs) + "</ul>" if wrongs else "<p>None.</p>"))
    refusals = [(r["id"], x) for r in rows for x in r["refusals"]]
    out.append("<h2>Every refusal in arms R and C</h2>")
    if refusals:
        out.append("<table><tr><th>chain</th><th>hop</th><th>what</th><th>kind</th><th>problems</th></tr>" +
                   "".join(f"<tr><td>{esc(i)}</td><td>{x['hop']}</td><td>{esc(x['what'])}</td><td>{esc(x['kind'])}</td><td>{esc('; '.join(x['problems']))}</td></tr>" for i, x in refusals) + "</table>")
    else:
        out.append("<p>None.</p>")
    flags = [f"{r['id']}: {f}" for r in rows for f in r["flags"]]
    if flags:
        out.append("<h2>Flags (an agent's deviation from its procedure, not a harness fault)</h2><ul>" + "".join(f"<li>{esc(f)}</li>" for f in flags) + "</ul>")
    md = (d / "summary.md").read_text().split("\n")
    i = next((n for n, l in enumerate(md) if l.startswith("| chain |")), None)
    if i is not None:
        out.append("<h2>Every chain</h2><pre style='font-size:0.72rem;white-space:pre-wrap'>" + esc("\n".join(l for l in md[i:] if l.startswith("|"))) + "</pre>")
    links = [f"<a href='{p}'>{p}</a>" for p in ("pilot/README.md", "pilot/summary.md", "speed.md") if (C.RESULTS / p).exists()]
    if links and not tag:
        out.append("<p class='small'>Pilot and speed test: " + ", ".join(links) + ".</p>")
    out.append("</body></html>")
    p = d / "report.html"
    p.write_text("\n".join(out))
    return p


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default=None); ap.add_argument("--notes", default=str(C.RESULTS / "notes.json"))
    a = ap.parse_args(argv)
    print("wrote", build(a.tag, Path(a.notes)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
