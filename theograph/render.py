"""Render: the theograph as one self-contained HTML file.

Lanes by kind, one row per concept, events as bars (a state, a course of a medicine, an admission)
or points (a result, a procedure, an encounter). Every mark carries its evidence: hover or click to
see each source document, date, act, certainty and the exact words. Hollow marks are negated
statements, dashed marks are hedged, faint marks come from low-authority sources, diamonds are
plans with no evidence of completion. Nothing loads from the network; the page works offline.
"""
from __future__ import annotations
import html, json, pathlib
from . import read_jsonl
from .registry import load_registry

LANES = [("encounters", "Encounters and episodes", []), ("dx", "Problems", ["dx"]), ("med", "Medicines", ["med"]), ("sym", "Symptoms and findings", ["sym"]),
         ("meas", "Results and measurements", ["meas"]), ("proc", "Procedures and investigations", ["proc"]), ("ref", "Referrals, follow-up and plans", ["ref", "fu"]),
         ("alg", "Allergies", ["alg"]), ("soc", "Social and function", ["soc", "func"])]

CSS = """
:root{--paper:#F6F7F9;--ink:#171A1F;--muted:#5B6470;--rule:#D6DAE0;--well:#ECEFF3;--accent:#1E5A6E;
 --c-encounters:#5B6470;--c-dx:#8A3B2F;--c-med:#1E5A6E;--c-sym:#9A5B12;--c-meas:#2F6B3A;--c-proc:#5A3E8A;--c-ref:#3E7A8A;--c-alg:#B0273B;--c-soc:#6B6B2F;
 --serif:"Source Serif 4",Georgia,serif;--mono:"IBM Plex Mono","SFMono-Regular",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#14171B;--ink:#E6E8EB;--muted:#9AA3AE;--rule:#2B3138;--well:#1D2126;--accent:#63B3C7;
 --c-encounters:#9AA3AE;--c-dx:#E08A7A;--c-med:#63B3C7;--c-sym:#D9A054;--c-meas:#7CC48A;--c-proc:#B39DDB;--c-ref:#7FB8C7;--c-alg:#F07E8F;--c-soc:#C9C97A;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#14171B;--ink:#E6E8EB;--muted:#9AA3AE;--rule:#2B3138;--well:#1D2126;--accent:#63B3C7;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:15px;line-height:1.45}
header{padding:16px 16px 8px;border-bottom:1px solid var(--rule);display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline}
h1{font-size:1.25rem;margin:0;font-weight:600}.mast{font-family:var(--mono);font-size:.74rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.controls{display:flex;flex-wrap:wrap;gap:6px 14px;padding:8px 16px;font-family:var(--mono);font-size:.76rem;border-bottom:1px solid var(--rule);align-items:center}
.controls label{display:inline-flex;gap:4px;align-items:center;cursor:pointer}.controls input[type=text]{font:inherit;padding:2px 6px;border:1px solid var(--rule);background:var(--paper);color:var(--ink);width:14ch}
.wrap{display:grid;grid-template-columns:minmax(220px,300px) 1fr;min-height:60vh}
.labels{border-right:1px solid var(--rule);font-family:var(--mono);font-size:.74rem}
.chart{overflow-x:auto;position:relative}svg{display:block}
.lane-h{font-weight:500;text-transform:uppercase;letter-spacing:.05em;font-size:.68rem;padding:0 10px;display:flex;align-items:center;background:var(--well)}
.row-l{padding:0 10px 0 18px;display:flex;align-items:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-top:1px solid transparent}
.row-l small{color:var(--muted);margin-left:6px}
.grid line{stroke:var(--rule)}.grid .year{stroke:var(--muted)}.grid text{fill:var(--muted);font-family:var(--mono);font-size:10px}
.mark{cursor:pointer}.mark.neg{fill:var(--paper)!important}.mark.hedged{stroke-dasharray:4 3}.src-tick{stroke:var(--paper);stroke-width:1.5}
.today{stroke:var(--accent);stroke-dasharray:2 3}
#panel{position:fixed;right:0;top:0;height:100vh;width:min(440px,92vw);background:var(--paper);border-left:1px solid var(--rule);box-shadow:-6px 0 18px rgba(0,0,0,.12);padding:14px 16px;overflow:auto;transform:translateX(105%);transition:transform .15s;font-size:.9rem}
#panel.open{transform:none}#panel h2{font-size:1rem;margin:0 0 4px}#panel .meta{font-family:var(--mono);font-size:.72rem;color:var(--muted);margin-bottom:8px}
#panel .src{border-top:1px solid var(--rule);padding:8px 0}.src .who{font-family:var(--mono);font-size:.72rem;color:var(--muted)}.src q{display:block;margin-top:4px;font-style:italic}
#panel .flag{font-family:var(--mono);font-size:.72rem;color:#9A5B12}#panel button{float:right;font:inherit;background:none;border:1px solid var(--rule);color:var(--ink);padding:2px 8px;cursor:pointer}
.legend{padding:8px 16px 24px;font-family:var(--mono);font-size:.72rem;color:var(--muted)}
"""

JS = r"""
const D = window.__theograph;
const LANES = D.lanes, EV = D.events, EPS = D.episodes, DOCS = D.docs;
const ROW = 22, LANE_H = 24, PAD_L = 8, PAD_R = 60;
const day = 86400000;
const p = s => s ? new Date(s + 'T00:00:00Z') : null;
let allDates = [];
for (const e of EV) for (const k of ['start','end','first_seen','last_seen']) if (e[k]) allDates.push(p(e[k]));
for (const e of EPS) for (const k of ['start','end']) if (e[k]) allDates.push(p(e[k]));
const today = new Date(); today.setUTCHours(0,0,0,0);
let t0 = new Date(Math.min(...allDates.map(d => +d)) - 45*day), t1 = new Date(Math.max(...allDates.map(d => +d), +today) + 45*day);
const state = {zoom: 1, lanes: new Set(LANES.map(l => l[0])), neg: true, minAuth: 0, q: '', pinned: null};
const $ = s => document.querySelector(s);
function pxPerDay(){ const w = Math.max(700, $('.chart').clientWidth - PAD_L - PAD_R); return state.zoom * w / ((t1 - t0)/day); }
function x(d){ return PAD_L + (d - t0)/day * pxPerDay(); }
function rows(){
  const out = [];
  for (const [id, label, kinds] of LANES){
    if (!state.lanes.has(id)) continue;
    out.push({lane: id, label, head: true});
    if (id === 'encounters'){
      const adm = EPS.filter(e => e.kind === 'admission'), outp = EPS.filter(e => e.kind === 'outpatient'), enc = EPS.filter(e => e.kind === 'encounter');
      if (adm.length) out.push({lane: id, label: 'admissions', items: adm.map(e => ({ep: e}))});
      for (const e of outp) out.push({lane: id, label: e.label, items: [{ep: e}]});
      out.push({lane: id, label: 'documents', items: enc.map(e => ({ep: e}))});
      continue;
    }
    const evs = EV.filter(e => kinds.includes(e.kind) && (state.neg || e.pol === 'POS') && e.authority >= state.minAuth && (!state.q || e.canon.includes(state.q)));
    const byC = new Map();
    for (const e of evs){ const k = e.canon + (e.subj === 'FAM' ? ' (family)' : ''); if (!byC.has(k)) byC.set(k, []); byC.get(k).push(e); }
    const keys = [...byC.keys()].sort((a, b) => { const fa = Math.min(...byC.get(a).map(e => +p(e.start || e.first_seen))), fb = Math.min(...byC.get(b).map(e => +p(e.start || e.first_seen))); return fa - fb; });
    for (const k of keys) out.push({lane: id, label: k, items: byC.get(k).map(e => ({ev: e}))});
  }
  return out;
}
function esc(s){ return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function fmtVal(v){ const parts = []; if (v.res) parts.push(v.res + (v.unit ? ' ' + v.unit : '')); for (const k of ['dose','route','freq','chg','site']) if (v[k]) parts.push(Array.isArray(v[k]) ? v[k].join('+') : v[k]); return parts.join(' '); }
function draw(){
  const R = rows(); const ppd = pxPerDay(); const W = PAD_L + (t1 - t0)/day * ppd + PAD_R;
  let y = 30; const labels = []; const marks = []; const grid = [];
  // months and years
  for (let d = new Date(Date.UTC(t0.getUTCFullYear(), t0.getUTCMonth(), 1)); d < t1; d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))){
    const yr = d.getUTCMonth() === 0; const X = x(d).toFixed(1);
    grid.push(`<line x1="${X}" x2="${X}" y1="22" y2="__H__" class="${yr ? 'year' : ''}"/>`);
    if (ppd * 28 > 34 || yr) grid.push(`<text x="${(+X + 3).toFixed(1)}" y="16">${yr ? d.getUTCFullYear() : d.toLocaleString('en-GB', {month: 'short', timeZone: 'UTC'})}</text>`);
  }
  if (today > t0 && today < t1) grid.push(`<line x1="${x(today).toFixed(1)}" x2="${x(today).toFixed(1)}" y1="22" y2="__H__" class="today"/>`);
  for (const r of R){
    if (r.head){ labels.push(`<div class="lane-h" style="height:${LANE_H}px;color:var(--c-${r.lane})">${esc(r.label)}</div>`); marks.push(`<rect x="0" y="${y}" width="${W}" height="${LANE_H}" fill="var(--well)"/>`); y += LANE_H; continue; }
    const n = r.items.length; const multi = r.items.filter(i => i.ev).length;
    labels.push(`<div class="row-l" style="height:${ROW}px" title="${esc(r.label)}">${esc(r.label)}${multi > 1 ? `<small>×${multi}</small>` : ''}</div>`);
    const cy = y + ROW/2; const col = `var(--c-${r.lane})`;
    for (const it of r.items){
      if (it.ep){
        const e = it.ep; const s = p(e.start), en = p(e.end || e.start);
        if (e.kind === 'encounter') marks.push(`<circle class="mark" cx="${x(s).toFixed(1)}" cy="${cy}" r="4" fill="${col}" data-ep="${esc(e.id)}"><title>${esc(e.label)} ${esc(e.start)}</title></circle>`);
        else marks.push(`<rect class="mark" x="${x(s).toFixed(1)}" y="${cy-6}" width="${Math.max(4, x(en) - x(s)).toFixed(1)}" height="12" rx="2" fill="${col}" opacity=".55" data-ep="${esc(e.id)}"><title>${esc(e.label)} ${esc(e.start)} to ${esc(e.end)}</title></rect>`);
        continue;
      }
      const e = it.ev; const op = (0.45 + 0.55 * e.authority).toFixed(2);
      const cls = 'mark' + (e.pol === 'NEG' ? ' neg' : '') + (e.cert !== 'CERT' ? ' hedged' : '');
      const s = p(e.start), en = p(e.end), fs = p(e.first_seen), ls = p(e.last_seen);
      const isPoint = ['meas', 'proc', 'ref', 'fu'].includes(e.kind) || (s && en && +s === +en && !e.open);
      const planned = e.flags.includes('planned');
      if (isPoint && !(e.open && e.kind === 'med')){
        const d = s || fs; const X = x(d).toFixed(1);
        if (planned) marks.push(`<path class="${cls}" d="M${X} ${cy-6} l6 6 l-6 6 l-6 -6 z" fill="var(--paper)" stroke="${col}" stroke-width="1.5" opacity="${op}" data-ev="${e.id}"/>`);
        else marks.push(`<circle class="${cls}" cx="${X}" cy="${cy}" r="5" fill="${col}" stroke="${col}" stroke-width="1.5" opacity="${op}" data-ev="${e.id}"/>`);
        if (e.kind === 'meas' && e.value.res) marks.push(`<text x="${(+X + 7).toFixed(1)}" y="${cy + 4}" font-size="10" font-family="var(--mono)" fill="var(--muted)">${esc(e.value.res)}</text>`);
      } else {
        const from = s || fs; const to = e.open ? t1 : (en || ls || from);
        const x1 = x(from), x2 = Math.max(x(to), x1 + 4);
        if (!s) marks.push(`<line x1="${(x1 - 14).toFixed(1)}" x2="${x1.toFixed(1)}" y1="${cy}" y2="${cy}" stroke="${col}" stroke-dasharray="2 2" opacity="${op}"/>`);
        marks.push(`<rect class="${cls}" x="${x1.toFixed(1)}" y="${cy-5}" width="${(x2 - x1).toFixed(1)}" height="10" rx="2" fill="${col}" stroke="${col}" stroke-width="1.2" opacity="${op}" data-ev="${e.id}"/>`);
        if (e.open) marks.push(`<path d="M${(x2 - 6).toFixed(1)} ${cy-5} l6 5 l-6 5" fill="var(--paper)"/>`);
      }
      for (const src of e.sources) if (src.doc_date) marks.push(`<line class="src-tick" x1="${x(p(src.doc_date)).toFixed(1)}" x2="${x(p(src.doc_date)).toFixed(1)}" y1="${cy-5}" y2="${cy+5}"/>`);
    }
    y += ROW;
  }
  const H = y + 10;
  $('.labels').innerHTML = `<div style="height:30px"></div>` + labels.join('');
  $('.chart').innerHTML = `<svg width="${W}" height="${H}"><g class="grid">${grid.join('').replaceAll('__H__', H)}</g>${marks.join('')}</svg>`;
}
function show(e){
  const P = $('#panel'); state.pinned = e.id;
  const when = e.start ? (e.end && e.end !== e.start ? `${e.start} to ${e.open ? 'ongoing' : e.end}` : e.start + (e.open ? ' onwards' : '')) : `known by ${e.first_seen}${e.open ? ', ongoing' : (e.end ? ', to ' + e.end : '')}`;
  const srcs = [...e.sources].sort((a, b) => (a.doc_date || '').localeCompare(b.doc_date || ''));
  P.innerHTML = `<button onclick="document.getElementById('panel').classList.remove('open')">close</button><h2>${esc(e.display)}${e.subj === 'FAM' ? ' (family)' : ''}</h2>
  <div class="meta">${esc(e.kind)} · ${e.pol === 'NEG' ? 'negated' : 'affirmed'} · ${esc(e.cert)} · authority ${e.authority} · ${esc(when)}${fmtVal(e.value) ? ' · ' + esc(fmtVal(e.value)) : ''}</div>
  ${e.flags.length ? `<div class="flag">${e.flags.map(esc).join('<br>')}</div>` : ''}
  ${e.relations.length ? `<div class="meta">${e.relations.map(r => esc(r.rel) + ' ' + esc(r.event)).join(', ')}</div>` : ''}
  <div class="meta">${srcs.length} source${srcs.length === 1 ? '' : 's'}</div>
  ${srcs.map(s => `<div class="src"><div class="who">${esc(s.doc_date)} · ${esc(s.doc_type)} · ${esc(s.doc)} · ${esc(s.src)} · ${esc(s.act)} ${esc(s.cert)}${s.role !== 'states' ? ' · ' + esc(s.role) : ''} · w ${s.weight}</div><q>${esc(s.quote)}</q>${fmtVal(s.slots) ? `<div class="who">${esc(fmtVal(s.slots))}${s.slots.when ? ' when=' + esc(s.slots.when) : ''}</div>` : ''}</div>`).join('')}`;
  P.classList.add('open');
}
document.addEventListener('click', ev => { const m = ev.target.closest('[data-ev]'); if (m){ show(EV.find(e => e.id === m.dataset.ev)); } });
function bind(){
  $('#zoom').oninput = e => { state.zoom = +e.target.value; draw(); };
  $('#neg').onchange = e => { state.neg = e.target.checked; draw(); };
  $('#auth').oninput = e => { state.minAuth = +e.target.value; $('#authv').textContent = e.target.value; draw(); };
  $('#q').oninput = e => { state.q = e.target.value.trim().toLowerCase(); draw(); };
  for (const cb of document.querySelectorAll('[data-lane]')) cb.onchange = e => { e.target.checked ? state.lanes.add(e.target.dataset.lane) : state.lanes.delete(e.target.dataset.lane); draw(); };
  window.addEventListener('resize', draw);
}
bind(); draw();
"""


def render(out_dir: pathlib.Path, title: str | None = None) -> pathlib.Path:
    events = read_jsonl(out_dir / "events.jsonl")
    eps = json.loads((out_dir / "episodes.json").read_text()) if (out_dir / "episodes.json").exists() else []
    docs = [{k: d.get(k) for k in ("id", "type", "date", "specialty", "author", "admitted", "discharged")} for d in load_registry(out_dir)]
    patients = sorted({e["patient"] for e in events}) or sorted({d.get("patient") for d in load_registry(out_dir)})
    title = title or f"Theograph: {', '.join(patients)}"
    data = {"lanes": LANES, "events": events, "episodes": eps, "docs": docs}
    lane_boxes = " ".join(f'<label><input type="checkbox" data-lane="{lid}" checked> {html.escape(label)}</label>' for lid, label, _ in LANES)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<header><h1>{html.escape(title)}</h1><span class="mast">{len(docs)} documents · {len(events)} events · {sum(e['n_sources'] for e in events)} sources · built by theograph</span></header>
<div class="controls">
  <label>zoom <input id="zoom" type="range" min="1" max="8" step="0.5" value="1"></label>
  <label><input id="neg" type="checkbox" checked> show negated</label>
  <label>min authority <input id="auth" type="range" min="0" max="1" step="0.05" value="0"> <span id="authv">0</span></label>
  <label>find <input id="q" type="text" placeholder="concept"></label>
  {lane_boxes}
</div>
<div class="wrap"><div class="labels"></div><div class="chart"></div></div>
<div class="legend">bar: a state or course, arrow: ongoing, dotted lead-in: start unknown · circle: a dated event · diamond: planned, no evidence of completion · hollow: negated · dashed: hedged · faint: low-authority source · white ticks: each document that states it · click a mark for its evidence</div>
<div id="panel"></div>
<script>window.__theograph = {json.dumps(data, ensure_ascii=False).replace("</", "<\\/")};</script>
<script>{JS}</script>
</body></html>"""
    out = out_dir / "theograph.html"
    out.write_text(page)
    print(f"wrote {out}")
    return out
