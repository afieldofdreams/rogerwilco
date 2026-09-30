"""Analyse: what the record says about itself, as a Markdown report and a JSON summary.

Counts and rates: documents, assertions, events, how many assertions collapsed into each event,
restatement by document type, anchoring precision, conflicts and corrections, plans with no evidence
of completion, hedged-only events, medicine courses, the problem list, results over time.
"""
from __future__ import annotations
import collections, json, pathlib
from . import read_jsonl
from .registry import load_registry

KIND_NAMES = {"dx": "problems", "sym": "symptoms and findings", "med": "medicines", "proc": "procedures and investigations", "meas": "results and measurements",
              "alg": "allergies", "ref": "referrals", "soc": "social", "func": "function", "fu": "follow-up and plans"}


def fmt_value(v: dict) -> str:
    parts = []
    if "res" in v:
        parts.append(v["res"] + (" " + v["unit"] if v.get("unit") else ""))
    for k in ("dose", "route", "freq", "chg", "site"):
        if k in v:
            x = v[k]
            parts.append("+".join(x) if isinstance(x, list) else str(x))
    return " ".join(parts)


def analyse(out_dir: pathlib.Path) -> dict:
    docs = load_registry(out_dir)
    rows = read_jsonl(out_dir / "assertions.jsonl")
    events = read_jsonl(out_dir / "events.jsonl")
    log = read_jsonl(out_dir / "extract_log.jsonl")
    eps = json.loads((out_dir / "episodes.json").read_text()) if (out_dir / "episodes.json").exists() else []
    patients = sorted({d["patient"] for d in docs})
    by_kind = collections.Counter(e["kind"] for e in events)
    a_by_kind = collections.Counter(a["kind"] for a in rows)
    # restatement: assertions whose event has an earlier source from another document
    restated = 0
    restated_by_type = collections.Counter(); total_by_type = collections.Counter()
    for e in events:
        srcs = sorted(e["sources"], key=lambda s: (s["doc_date"] or "", s["assertion"]))
        seen_docs = set()
        for s in srcs:
            total_by_type[s["doc_type"]] += 1
            if seen_docs and s["doc"] not in seen_docs:
                restated += 1; restated_by_type[s["doc_type"]] += 1
            seen_docs.add(s["doc"])
    prec = collections.Counter(a.get("t_prec") for a in rows)
    conflicts = [e for e in events if any(f.startswith("conflict") for f in e["flags"])]
    corrected = [e for e in events if any("corrected" in f for f in e["flags"])]
    planned = [e for e in events if "planned" in e["flags"]]
    met = [e for e in events if any(f.startswith(("fulfilled", "evidenced")) for f in e["flags"])]
    hedged = [e for e in events if e["cert"] in ("POSS", "COND", "HYPO") and e["pol"] == "POS"]
    unanchored = [e for e in events if not e["start"] and not e["end"]]
    meds = sorted([e for e in events if e["kind"] == "med"], key=lambda e: (e["concept"], e["start"] or e["first_seen"] or ""))
    problems = sorted([e for e in events if e["kind"] == "dx" and e["pol"] == "POS"], key=lambda e: (e["start"] or e["first_seen"] or ""))
    results = collections.defaultdict(list)
    for e in events:
        if e["kind"] == "meas" and e["pol"] == "POS" and e["value"].get("res"):
            results[e["concept"]].append(e)
    summary = {
        "patients": patients, "documents": len(docs), "assertions": len(rows), "events": len(events),
        "assertions_per_event": round(len(rows) / len(events), 2) if events else None,
        "events_multi_doc": sum(1 for e in events if e["n_docs"] > 1),
        "restated_sources": restated, "restatement_by_doc_type": {t: f"{restated_by_type[t]}/{total_by_type[t]}" for t in total_by_type},
        "events_by_kind": dict(by_kind), "assertions_by_kind": dict(a_by_kind), "anchoring": dict(prec),
        "conflicts": len(conflicts), "corrected": len(corrected), "plans_without_evidence": len(planned), "plans_with_evidence": len(met), "hedged_only": len(hedged), "unanchored_events": len(unanchored),
        "extraction": {"documents": len(log), "ok": sum(1 for l in log if l["status"] == "ok"), "attempts_mean": round(sum(l["attempts"] for l in log) / len(log), 2) if log else None,
                       "tokens_in": sum((u.get("in") or 0) for l in log for u in l["usage"]), "tokens_out": sum((u.get("out") or 0) for l in log for u in l["usage"])},
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    L = []
    L.append(f"# Theograph analysis: {', '.join(patients)}\n")
    L.append(f"{len(docs)} documents, {len(rows)} assertions, {len(events)} events ({summary['assertions_per_event']} assertions per event); {summary['events_multi_doc']} events stated in more than one document; {len(eps)} episodes and encounters.\n")
    L.append("## Documents\n")
    L.append("| id | type | date | specialty | lines | assertions | attempts |")
    L.append("|---|---|---|---|---|---|---|")
    lg = {l["doc"]: l for l in log}
    for d in sorted(docs, key=lambda d: d.get("date") or ""):
        L.append(f"| {d['id']} | {d['type']} | {d.get('date')} | {d.get('specialty') or ''} | {d['n_lines']} | {sum(1 for a in rows if a['doc'] == d['id'])} | {lg.get(d['id'], {}).get('attempts', '')} |")
    L.append("\n## Deduplication\n")
    L.append(f"{restated} of {len(rows)} assertions restate something an earlier document already said. By document type (restated / all sources from that type):\n")
    for t, v in summary["restatement_by_doc_type"].items():
        L.append(f"- {t}: {v}")
    L.append("\nEvents by kind: " + ", ".join(f"{KIND_NAMES.get(k, k)} {v}" for k, v in sorted(by_kind.items())) + ".")
    L.append("\n## Time\n")
    L.append("Anchoring of assertions: " + ", ".join(f"{k} {v}" for k, v in sorted(prec.items(), key=lambda x: -x[1])) + ".")
    L.append(f"\nEvents with no date at all: {len(unanchored)}" + (" (" + ", ".join(e["canon"] for e in unanchored[:12]) + ")" if unanchored else "") + ".")
    L.append("\n## Things to look at\n")
    if conflicts:
        L.append(f"Conflicts ({len(conflicts)}):")
        for e in conflicts:
            L.append(f"- {e['canon']} on {e['start']}: " + "; ".join(f for f in e["flags"] if f.startswith("conflict")))
    if corrected:
        L.append(f"\nCorrected values ({len(corrected)}):")
        for e in corrected:
            L.append(f"- {e['canon']} on {e['start']}: now {fmt_value(e['value'])}; " + "; ".join(f for f in e["flags"] if "corrected" in f))
    if planned:
        L.append(f"\nPlanned or ordered with no evidence of completion in the record ({len(planned)}):")
        for e in planned:
            L.append(f"- {e['display']} planned {e['start'] or e['first_seen']} ({e['sources'][0]['doc']})")
    if met:
        L.append(f"\nPlanned or ordered, and then evidenced ({len(met)}):")
        for e in met:
            L.append(f"- {e['display']} planned {e['sources'][0]['t_start'] or e['sources'][0]['doc_date']} ({e['sources'][0]['doc']}): " + "; ".join(f for f in e["flags"] if f.startswith(("fulfilled", "evidenced"))))
    if hedged:
        L.append(f"\nStated only with hedging ({len(hedged)}):")
        for e in hedged:
            L.append(f"- {e['canon']} ({e['cert']}, {e['sources'][0]['doc']})")
    flagged = [e for e in events if any("dose differs" in f or "start unknown" in f or "no earlier course" in f or "no course recorded" in f for f in e["flags"])]
    if flagged:
        L.append(f"\nMedicine courses to check ({len(flagged)}):")
        for e in flagged:
            L.append(f"- {e['concept']} {fmt_value(e['value'])}: " + "; ".join(e["flags"]))
    L.append("\n## Problem list\n")
    L.append("| problem | from | to | certainty | sources | documents |")
    L.append("|---|---|---|---|---|---|")
    for e in problems:
        L.append(f"| {e['concept']}{' (family)' if e['subj']=='FAM' else ''} | {e['start'] or ('by ' + (e['first_seen'] or '?'))} | {'ongoing' if e['open'] else (e['end'] or '')} | {e['cert']} | {e['n_sources']} | {', '.join(e['doc_types'])} |")
    L.append("\n## Medicines\n")
    L.append("| medicine | regimen | from | to | sources | notes |")
    L.append("|---|---|---|---|---|---|")
    for e in meds:
        to = ("ongoing" + (f", stop planned {e['planned_end']}" if e.get("planned_end") else "")) if e["open"] else (e["end"] or "")
        L.append(f"| {e['concept']}{' (not given)' if e['pol']=='NEG' else ''} | {fmt_value({k: v for k, v in e['value'].items() if k != 'chg'})} | {e['start'] or ('by ' + (e['first_seen'] or '?'))} | {to} | {e['n_sources']} | {'; '.join(f for f in e['flags'] if not f.startswith('stop planned'))} |")
    L.append("\n## Results over time\n")
    for name, es in sorted(results.items()):
        es = sorted(es, key=lambda e: e["start"] or e["first_seen"] or "")
        L.append(f"- {name}: " + ", ".join(f"{fmt_value(e['value'])} ({e['start'] or e['first_seen']})" + (" *" if e["flags"] else "") for e in es))
    L.append("\n(* flagged: see events.jsonl)\n")
    (out_dir / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:3]))
    return summary
