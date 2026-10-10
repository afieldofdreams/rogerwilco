#!/usr/bin/env python3
"""results/report.html from results/summary.json: every figure on the page is read from the JSON, none is typed.

  python3 tools/report.py [--tag NAME] [--notes results/notes.json]
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

CSS = """body{font:16px/1.5 Georgia,serif;max-width:68rem;margin:2rem auto;padding:0 1rem;color:#222}
h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:2rem}table{border-collapse:collapse;font-size:0.85rem;margin:1rem 0;width:100%}
th,td{border:1px solid #ccc;padding:0.3rem 0.5rem;text-align:left;vertical-align:top}th{background:#f3f3f3}
.note{background:#fff7e0;padding:0.8rem 1rem;border-left:4px solid #e0b000}.ok{color:#1a7f37}.bad{color:#b00020}code{font-size:0.85em}"""


def pct(r: dict) -> str:
    if not r or not r.get("n"):
        return "0 / 0"
    return f"{r['k']} / {r['n']} ({100 * r['p']:.0f}%, {100 * r['lo']:.0f} to {100 * r['hi']:.0f})"


def build(tag: str | None, notes_path: Path | None) -> Path:
    d = C.RESULTS / tag if tag else C.RESULTS
    s = C.read_json(d / "summary.json")
    notes = C.read_json(notes_path) if notes_path and notes_path.exists() else {}
    cells = s["cells"]
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Study 6: the execution readback</title><style>{CSS}</style></head><body>"]
    out.append("<h1>Study 6: the execution readback</h1>")
    out.append(f"<p>{html.escape(notes.get('status', 'Results as computed from the trial files.'))}</p>")
    if notes.get("deviations"):
        out.append("<div class='note'><strong>Deviations from the pre-registered protocol</strong><ul>" +
                   "".join(f"<li>{html.escape(x)}</li>" for x in notes["deviations"]) + "</ul></div>")
    out.append("<h2>Cells</h2><table><tr><th>block</th><th>arm</th><th>model</th><th>trials</th><th>wrong acts, induced or planted</th><th>wrong acts, clean</th>"
               "<th>caught before the act</th><th>asked (induced)</th><th>false alarms (clean)</th><th>fidelity</th><th>DN honest</th>"
               "<th>DN flagged tool faults</th><th>receiver reported tool fault</th><th>mean cost $</th><th>receiver turns</th></tr>")
    for key in sorted(cells):
        c = cells[key]; b, arm, model = key.split("-", 2)
        out.append(f"<tr><td>{b[1:]}</td><td>{arm}</td><td>{model}</td><td>{c['trials']}</td><td>{pct(c['wrong_acts_induced'])}</td><td>{pct(c['wrong_acts_clean'])}</td>"
                   f"<td>{pct(c['caught_before_act'])}</td><td>{pct(c['asked_induced'])}</td><td>{pct(c['false_alarms_clean'])}</td><td>{pct(c['fidelity'])}</td>"
                   f"<td>{pct(c['dn_honest'])}</td><td>{pct(c['dn_flag_tool'])}</td><td>{pct(c['receiver_reported_tool'])}</td><td>{c['cost_usd_mean']}</td><td>{c['receiver_turns_mean']}</td></tr>")
    out.append("</table><p>Every proportion carries its 95% Clopper-Pearson interval.</p>")
    out.append("<h2>The pre-registered tests</h2><table><tr><th>model</th><th>test</th><th>cells</th><th>result</th></tr>")
    for m, t in s["tests"].items():
        for name, v in t.items():
            res = f"p = {v['p']:.4f}" if "p" in v else ("holds" if v.get("holds") else "does not hold")
            cellstr = ", ".join(f"{k}: {v[k]}" for k in v if k not in ("p", "holds"))
            out.append(f"<tr><td>{m}</td><td>{html.escape(name)}</td><td>{html.escape(cellstr)}</td><td>{res}</td></tr>")
    out.append("</table>")
    md = (d / "summary.md").read_text().split("\n")
    # the per-handover tables from summary.md, rendered as is
    out.append("<h2>Every handover in every cell</h2><pre style='font-size:0.75rem;white-space:pre-wrap'>" + html.escape("\n".join(l for l in md if l.startswith("|") or l.startswith("Block"))) + "</pre>")
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
