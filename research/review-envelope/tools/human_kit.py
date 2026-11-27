#!/usr/bin/env python3
"""A paper-free way to put the same cases in front of a person: writes ../human/index.html, one self-contained page.

NOT part of the registered study, and no result from it is reported there. The study's reviewers are models, and it
says nothing about people. This page exists so that a person can try the two views on themselves, or on a team, with
the policy in front of them: eight payment instructions, four on the check sheet and four with the file, half of them
faulted. It records the answer and the time for each, shows the score at the end, and offers the results as a JSON
file. Nothing leaves the browser.

Two forms, A and B, swap which cases are shown which way, so that across people every case is seen in both views.
The cases are payments held out of the pilot and the main run. The file is the shortest one that still holds a near
neighbour of every value: the target and two other payments of the same supplier, about 1,000 words.

    python3 human_kit.py
"""
from __future__ import annotations

import html
import json
import random

import casefile as K
import common as C

OUT = C.ROOT / "human"
FAULTS = [None, None, "amount", "duplicate", None, None, "account", "onhold"]      # cases 1-8; 1-4 and 5-8 swap views between forms


def cases() -> list[dict]:
    pool = list(K.POOL)
    random.Random("calibration-targets").shuffle(pool)
    held = pool[20:28]                                   # inside the 40 held out of the registered runs, not used by the calibration
    K.LENGTHS["XS"], K.LEDGER_ROWS["XS"] = 2, 1
    out = []
    for i, (t, f) in enumerate(zip(held, FAULTS)):
        c = K.make_case(t, f, "XS", f"human:{t['id']}")
        out.append({"n": i + 1, "fault": f, "reason": K.REASON_OF_FAULT.get(f) if f else None,
                    "sheet": K.view_card(c), "file": K.view_file(c), "words_file": len(K.view_file(c).split())})
    order = list(range(8))
    random.Random("human-order").shuffle(order)
    return [out[i] for i in order]


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>The review envelope: try it yourself</title>
<style>
:root { --bg:#fbfaf7; --fg:#1c1b19; --mut:#6b665e; --line:#d9d4ca; --ok:#1f6f4a; --bad:#a3312b; --card:#ffffff; }
@media (prefers-color-scheme: dark) { :root { --bg:#161513; --fg:#ece8e0; --mut:#a39d92; --line:#3a3731; --ok:#6fcf9b; --bad:#f08a82; --card:#1f1e1b; } }
body { background:var(--bg); color:var(--fg); font:16px/1.5 system-ui, sans-serif; margin:0; }
main { max-width:60rem; margin:0 auto; padding:1.25rem 1rem 4rem; }
h1 { font-size:1.5rem; margin:.5rem 0; } h2 { font-size:1.1rem; margin:1.5rem 0 .5rem; }
p, li { max-width:44rem; } .mut { color:var(--mut); }
pre { background:var(--card); border:1px solid var(--line); border-radius:6px; padding:.9rem; white-space:pre-wrap; word-break:break-word; font:13.5px/1.45 ui-monospace, Menlo, Consolas, monospace; overflow-x:auto; }
details { border:1px solid var(--line); border-radius:6px; padding:.5rem .9rem; background:var(--card); }
button, select { font:inherit; padding:.55rem 1rem; border-radius:6px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }
button.go { border-color:var(--ok); color:var(--ok); } button.stop { border-color:var(--bad); color:var(--bad); }
.bar { position:sticky; bottom:0; background:var(--bg); border-top:1px solid var(--line); padding:.75rem 0; display:flex; gap:.6rem; flex-wrap:wrap; align-items:center; }
table { border-collapse:collapse; width:100%; } th, td { border-bottom:1px solid var(--line); padding:.4rem .5rem; text-align:left; font-variant-numeric:tabular-nums; }
.tablewrap { overflow-x:auto; } .ok { color:var(--ok); } .bad { color:var(--bad); }
</style></head><body><main>
<h1>The review envelope: try it yourself</h1>
<div id="intro">
<p>You are the reviewer at Harbourline Studio Ltd. Today is Thursday 24 September 2026. An agent called payer has prepared eight supplier payments. A payment, once released, cannot be recalled. For each one, decide: approve it, or hold it.</p>
<p>Four payments come with a check sheet composed by code from the records. Four come with the file: the approval register, the supplier master, the paid ledger and the run's paperwork, about a thousand words each time. Some of the eight are wrong. The page times each decision.</p>
<p class="mut">This is not part of the study and proves nothing on its own. Nothing you do here leaves your browser. At the end you can save your results as a file.</p>
<details open><summary>The payment policy (it stays available on every case)</summary><pre id="policy"></pre></details>
<p><button class="go" id="start">Start</button> <span class="mut">Form <span id="form"></span></span></p>
</div>
<div id="case" hidden>
<h2 id="head"></h2>
<details><summary>The payment policy</summary><pre id="policy2"></pre></details>
<pre id="text"></pre>
<div class="bar">
<button class="go" id="approve">Approve</button>
<select id="reason" aria-label="Reason for holding"><option value="">Hold because...</option></select>
<button class="stop" id="hold">Hold</button>
<span class="mut" id="count"></span>
</div></div>
<div id="done" hidden>
<h2>Your results</h2>
<div class="tablewrap"><table id="summary"></table></div>
<h2>Case by case</h2>
<div class="tablewrap"><table id="rows"></table></div>
<p><button id="save">Save results as a file</button></p>
<p class="mut">Four cases a view is far too few to conclude anything about one person. Collected across a team, with half on form A and half on form B, every case is seen both ways.</p>
</div>
</main>
<script>
const CASES = __CASES__;
const POLICY = __POLICY__;
const REASONS = ["supplier","invoice","amount","currency","kind","account","date","reference","approval","duplicate","onhold","unconfirmed"];
const form = (location.hash === "#B") ? "B" : (location.hash === "#A" ? "A" : (Math.random() < 0.5 ? "A" : "B"));
document.getElementById("form").textContent = form;
document.getElementById("policy").textContent = POLICY; document.getElementById("policy2").textContent = POLICY;
const sel = document.getElementById("reason"); REASONS.forEach(r => { const o = document.createElement("option"); o.value = r; o.textContent = r; sel.appendChild(o); });
const viewOf = c => ((c.n <= 4) === (form === "A")) ? "sheet" : "file";
let i = -1, t0 = 0; const results = [];
function show() {
  i += 1;
  if (i >= CASES.length) return finish();
  const c = CASES[i], v = viewOf(c);
  document.getElementById("head").textContent = "Payment " + (i + 1) + " of " + CASES.length + (v === "sheet" ? ": the check sheet" : ": the file");
  document.getElementById("text").textContent = c[v];
  document.getElementById("count").textContent = "";
  sel.value = ""; window.scrollTo(0, 0); t0 = performance.now();
}
function answer(verdict) {
  const c = CASES[i];
  if (verdict === "HOLD" && !sel.value) { document.getElementById("count").textContent = "Choose a reason to hold."; return; }
  results.push({ n: c.n, view: viewOf(c), fault: c.fault, verdict: verdict, reason: verdict === "HOLD" ? sel.value : null, seconds: Math.round((performance.now() - t0) / 100) / 10 });
  show();
}
function cell(tr, text, cls) { const td = document.createElement("td"); td.textContent = text; if (cls) td.className = cls; tr.appendChild(td); }
function finish() {
  document.getElementById("case").hidden = true; document.getElementById("done").hidden = false;
  const sum = document.getElementById("summary");
  sum.innerHTML = "<tr><th>View</th><th>Wrong payments stopped</th><th>Right payments approved</th><th>Median seconds a case</th></tr>";
  ["sheet", "file"].forEach(v => {
    const r = results.filter(x => x.view === v), f = r.filter(x => x.fault), c = r.filter(x => !x.fault);
    const secs = r.map(x => x.seconds).sort((a, b) => a - b), med = secs.length ? secs[Math.floor((secs.length - 1) / 2)] : 0;
    const tr = document.createElement("tr");
    cell(tr, v === "sheet" ? "check sheet" : "file"); cell(tr, f.filter(x => x.verdict === "HOLD").length + " of " + f.length);
    cell(tr, c.filter(x => x.verdict === "APPROVE").length + " of " + c.length); cell(tr, String(med)); sum.appendChild(tr);
  });
  const rows = document.getElementById("rows");
  rows.innerHTML = "<tr><th>Payment</th><th>View</th><th>It was</th><th>You said</th><th>Seconds</th></tr>";
  results.forEach((x, k) => {
    const right = x.fault ? x.verdict === "HOLD" : x.verdict === "APPROVE";
    const tr = document.createElement("tr");
    cell(tr, String(k + 1)); cell(tr, x.view === "sheet" ? "check sheet" : "file"); cell(tr, x.fault ? "wrong: " + x.fault : "right");
    cell(tr, x.verdict === "HOLD" ? "hold: " + x.reason : "approve", right ? "ok" : "bad"); cell(tr, String(x.seconds)); rows.appendChild(tr);
  });
}
document.getElementById("start").onclick = () => { document.getElementById("intro").hidden = true; document.getElementById("case").hidden = false; show(); };
document.getElementById("approve").onclick = () => answer("APPROVE");
document.getElementById("hold").onclick = () => answer("HOLD");
document.getElementById("save").onclick = () => {
  const blob = new Blob([JSON.stringify({ kit: "review-envelope human kit v1", form: form, results: results }, null, 1)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "review-envelope-results-" + form + ".json"; a.click();
};
</script></body></html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cs = cases()
    page = PAGE.replace("__CASES__", json.dumps(cs).replace("</", "<\\/")).replace("__POLICY__", json.dumps(K.POLICY).replace("</", "<\\/"))
    (OUT / "index.html").write_text(page)
    print(f"wrote {OUT / 'index.html'}: {len(cs)} cases, file views of {min(c['words_file'] for c in cs)} to {max(c['words_file'] for c in cs)} words; faults {[c['fault'] for c in cs]}")


if __name__ == "__main__":
    main()
