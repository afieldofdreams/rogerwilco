#!/usr/bin/env python3
"""results/report.html from results/summary.json: every figure on the page is read from the JSON, none is typed.

  python3 tools/report.py [--tag NAME] [--notes results/notes.json]

The page: the headline per model (block 1, correct acts per arm with intervals, and the median size per hop beside it),
the cells table, the pre-registered tests, block 3 by K, every drift and every refusal named, and the per-chain table from
summary.md. The pilot's and the ladder's summaries are linked where they exist, not repeated. The site page and the
app test that binds it come later (tools/site_page.py), as studies 6 and 7 did.
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

CSS = """body{font:16px/1.5 Georgia,serif;max-width:72rem;margin:2rem auto;padding:0 1rem;color:#222}
h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:2rem}h3{font-size:1rem;margin-top:1.4rem}
table{border-collapse:collapse;font-size:0.82rem;margin:1rem 0;width:100%}
th,td{border:1px solid #ccc;padding:0.3rem 0.5rem;text-align:left;vertical-align:top}th{background:#f3f3f3}
.note{background:#fff7e0;padding:0.8rem 1rem;border-left:4px solid #e0b000}.ok{color:#1a7f37}.bad{color:#b00020}code{font-size:0.85em}
.head td{font-size:1rem}.small{font-size:0.8rem;color:#555}"""

MODEL_NAME = {"haiku55": "Claude Haiku 5.5", "haiku45": "Claude Haiku 4.5", "sonnet55": "Claude Sonnet 5.5"}
ARM_NAME = {"F": "F, free prose", "A": "A, disciplined prose", "L": "L, lines", "R": "R, lines checked at every hop"}


def pct(r: dict | None) -> str:
    if not r or not r.get("n"):
        return "0 / 0"
    return f"{r['k']} / {r['n']} ({100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f})"


def esc(x) -> str:
    return html.escape(str(x))


def cell_key(block: int, arm: str, model: str, K: int) -> str:
    return f"B{block}-{arm}-{model}-k{K}"


def build(tag: str | None, notes_path: Path | None) -> Path:
    d = C.RESULTS / tag if tag else C.RESULTS
    s = C.read_json(d / "summary.json")
    notes = C.read_json(notes_path) if notes_path and notes_path.exists() else {}
    cells = s["cells"]
    rows = s["rows"]
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_NAME).index(m) if m in MODEL_NAME else 9)
    levels = sorted({r.get("harden", 0) for r in rows})
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Study 8: the relay</title><style>{CSS}</style></head><body>"]
    out.append("<h1>Study 8: the relay</h1>")
    out.append(f"<p>{esc(notes.get('status', 'Results as computed from the chain files.'))} {s['chains']} chains, total cost ${s['cost_usd_total']}, "
               f"tokens counted with {esc(s.get('tokenizer', C.TOKENIZER))}, hardening level {', '.join(str(x) for x in levels)}.</p>")
    if notes.get("deviations"):
        out.append("<div class='note'><strong>Deviations from the pre-registered protocol</strong><ul>" +
                   "".join(f"<li>{esc(x)}</li>" for x in notes["deviations"]) + "</ul></div>")
    # the headline: block 1, correct acts per arm per model, size per hop beside it
    out.append("<h2>The headline: block 1, a correct act per arm, and the size of the message at each hop</h2>")
    for m in models:
        out.append(f"<h3>{esc(MODEL_NAME.get(m, m))}</h3><table class='head'><tr><th>arm</th><th>chains</th><th>correct act</th><th>every record field at the payer</th>"
                   "<th>any drift</th><th>asked</th><th>held</th><th>median size hop 1 / 2 / 3 (tokens)</th><th>median traffic</th><th>turns</th><th>cost $</th></tr>")
        for arm in C.ARMS:
            c = cells.get(cell_key(1, arm, m, 2))
            if not c:
                continue
            sz = c["size_median_by_hop"]
            out.append(f"<tr><td>{esc(ARM_NAME[arm])}</td><td>{c['chains']}</td><td>{pct(c['correct_act'])}</td><td>{pct(c['all_fields_at_payer'])}</td>"
                       f"<td>{pct(c['any_drift'])}</td><td>{pct(c['asked'])}</td><td>{pct(c['held'])}</td>"
                       f"<td>{sz.get('1')} / {sz.get('2')} / {sz.get('3')}</td><td>{c['traffic_median']}</td><td>{c['model_turns_mean']}</td><td>{c['cost_usd_mean']}</td></tr>")
        out.append("</table>")
    # every cell
    Kmax = max((r["K"] for r in rows), default=2)
    out.append("<h2>Every cell</h2><table><tr><th>block</th><th>arm</th><th>model</th><th>K</th><th>chains</th><th>correct act</th><th>as expected</th><th>wrong</th>"
               "<th>asked</th><th>held</th><th>not done</th><th>every field at payer</th><th>any drift</th><th>loss</th><th>caught</th><th>false alarms / correct forwards</th>"
               + "".join(f"<th>size hop {h}</th>" for h in range(1, Kmax + 2)) + "<th>traffic median</th><th>turns</th><th>cost $</th><th>harness faults</th></tr>")
    def sort_key(k):
        b, arm, model, K = k.split("-")
        return (int(b[1:]), models.index(model) if model in models else 9, C.ARMS.index(arm), int(K[1:]))
    for key in sorted(cells, key=sort_key):
        c = cells[key]; b, arm, model, K = key.split("-")
        sizes = "".join(f"<td>{c['size_median_by_hop'].get(str(h), '')}</td>" for h in range(1, Kmax + 2))
        out.append(f"<tr><td>{b[1:]}</td><td>{arm}</td><td>{esc(MODEL_NAME.get(model, model))}</td><td>{K[1:]}</td><td>{c['chains']}</td><td>{pct(c['correct_act'])}</td>"
                   f"<td>{pct(c['as_expected'])}</td><td>{pct(c['wrong_act'])}</td><td>{pct(c['asked'])}</td><td>{pct(c['held'])}</td><td>{pct(c['not_done'])}</td>"
                   f"<td>{pct(c['all_fields_at_payer'])}</td><td>{pct(c['any_drift'])}</td><td>{pct(c['loss'])}</td><td>{c['caught']}</td>"
                   f"<td>{pct(c['false_alarms_over_correct_forwards'])}</td>{sizes}<td>{c['traffic_median']}</td><td>{c['model_turns_mean']}</td><td>{c['cost_usd_mean']}</td><td>{c['harness_faults']}</td></tr>")
    out.append("</table><p class='small'>Every proportion carries its 95% Clopper-Pearson interval. Loss is a field missing at the payer, a payer that asked, or a chain not done. "
               "Caught is a refusal by check-ho or check-rb that named a dropped or changed value or a wrong addition; a false alarm is a refusal with every value right.</p>")
    # tests
    out.append("<h2>The pre-registered tests</h2><table><tr><th>model</th><th>test</th><th>cells</th><th>result</th></tr>")
    for m, t in s["tests"].items():
        for name, v in t.items():
            if "p" in v:
                res = f"p = {v['p']:.4f}"
            elif "holds" in v:
                res = "holds" if v["holds"] else "does not hold"
            elif "sign" in v:
                res = v["sign"]
            else:
                res = ""
            cellstr = ", ".join(f"{k}: {v[k]}" for k in v if k not in ("p", "holds", "sign"))
            out.append(f"<tr><td>{esc(MODEL_NAME.get(m, m))}</td><td>{esc(name)}</td><td>{esc(cellstr)}</td><td>{esc(res)}</td></tr>")
    out.append("</table>")
    # block 3 by K
    b3 = [k for k in cells if k.startswith("B3-")]
    if b3:
        out.append("<h2>Block 3: the sweep, by K</h2><table><tr><th>model</th><th>arm</th><th>K</th><th>chains</th><th>correct act</th><th>every field at payer</th><th>any drift</th>"
                   "<th>median size at the payer</th><th>median traffic</th><th>cost $</th></tr>")
        for key in sorted(b3, key=sort_key):
            c = cells[key]; _, arm, model, K = key.split("-"); k = int(K[1:])
            out.append(f"<tr><td>{esc(MODEL_NAME.get(model, model))}</td><td>{arm}</td><td>{k}</td><td>{c['chains']}</td><td>{pct(c['correct_act'])}</td>"
                       f"<td>{pct(c['all_fields_at_payer'])}</td><td>{pct(c['any_drift'])}</td><td>{c['size_median_by_hop'].get(str(k + 1))}</td><td>{c['traffic_median']}</td><td>{c['cost_usd_mean']}</td></tr>")
        out.append("</table>")
    # drifts, refusals, flags
    drifts = [x for c in cells.values() for x in c["drifts"]]
    out.append("<h2>Every drift, by chain and hop</h2>" + ("<ul>" + "".join(f"<li><code>{esc(x)}</code></li>" for x in drifts) + "</ul>" if drifts else "<p>None.</p>"))
    refusals = [(r["id"], x) for r in rows for x in r["refusals"]]
    out.append("<h2>Every refusal in arm R</h2>")
    if refusals:
        out.append("<table><tr><th>chain</th><th>hop</th><th>what</th><th>kind</th><th>problems</th></tr>" +
                   "".join(f"<tr><td>{esc(i)}</td><td>{x['hop']}</td><td>{esc(x['what'])}</td><td>{esc(x['kind'])}</td><td>{esc('; '.join(x['problems']))}</td></tr>" for i, x in refusals) + "</table>")
    else:
        out.append("<p>None.</p>")
    flags = [f"{r['id']}: {f}" for r in rows for f in r["flags"]]
    if flags:
        out.append("<h2>Flags (an agent's deviation from its procedure, not a harness fault)</h2><ul>" + "".join(f"<li>{esc(f)}</li>" for f in flags) + "</ul>")
    second = [r["id"] for r in rows if r.get("second_act_attempt")]
    if second:
        out.append(f"<p class='small'>Payers that attempted a second act after acting (refused by the tool): {len(second)}: {esc(', '.join(second))}.</p>")
    # per chain, from summary.md
    md = (d / "summary.md").read_text().split("\n")
    i = next((n for n, l in enumerate(md) if l.startswith("| chain |")), None)
    if i is not None:
        out.append("<h2>Every chain</h2><pre style='font-size:0.72rem;white-space:pre-wrap'>" + esc("\n".join(l for l in md[i:] if l.startswith("|"))) + "</pre>")
    links = [f"<a href='{p}/summary.md'>{p}</a>" for p in ("pilot", "pilot/level0", "pilot/level1", "smoke") if (C.RESULTS / p / "summary.md").exists()]
    if links and not tag:
        out.append("<p class='small'>Pilot and ladder summaries: " + ", ".join(links) + ".</p>")
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
