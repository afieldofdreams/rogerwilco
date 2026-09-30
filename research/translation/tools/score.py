#!/usr/bin/env python3
"""Score every gated output against the gold assertions.

For each document in each run: match the extractor's assertions to the gold (same place in the
document, same concept or the same words), then measure completeness (gold assertions found),
precision (assertions that are gold assertions), attribute accuracy on the matched pairs (kind,
act, pol, cert, subj, time and every value the gold carries), provenance (the quote points at the
gold's words), the special cases (the correction with re=, the instruction planted in doc 5), and
what the gate refused on the first attempt. Across the three runs of an arm and model: repeatability
per gold assertion. Writes runs/<run>/score.json, results/summary.json and results/summary.md.

usage: python3 tools/score.py
"""
from __future__ import annotations
import json, pathlib, re, statistics as st, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CORE, RESULTS, RUNS, count_tokens, doc_lines, norm  # noqa: E402
from runbook import ARMS, GROUPS, MODELS, gate_result  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLD = json.loads((ROOT / "truth" / "gold.json").read_text())
STOP = {"of", "the", "and", "a", "an", "to", "in", "on", "with", "for", "at", "by", "or", "is", "was", "her", "his"}
VALUE_KEYS = ("res", "unit", "dose", "route", "freq", "chg", "site", "who", "when")


# ----------------------------------------------------------------- normalisation and matching

def toks(s: str) -> set[str]:
    out = set()
    for t in re.split(r"[-/_\s:]+", (s or "").lower()):
        t = t.strip(".,;()")
        if not t or t in STOP:
            continue
        if len(t) > 4 and t.endswith("s"):
            t = t[:-1]
        out.add(t)
    return out


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def concept_sim(e_item: str, g: dict) -> float:
    e_kind, e_con = e_item.split(":", 1)
    names = [g["concept"]] + [s.split(":", 1)[1] if ":" in s else s for s in g["syn"]]
    best = 0.0
    et = toks(e_con)
    for n in names:
        if e_con == n:
            return 1.0
        nt = toks(n)
        s = jacc(et, nt)
        if et and nt and (et <= nt or nt <= et):
            s = max(s, 0.6)
        best = max(best, s)
    return best


def quote_sim(e_quote: str, g_quote: str) -> float:
    a, b = toks(e_quote), toks(g_quote)
    if not a or not b:
        return 0.0
    if norm(e_quote).lower() in norm(g_quote).lower() or norm(g_quote).lower() in norm(e_quote).lower():
        return 1.0
    return jacc(a, b)


def near(e_lines: list[int], g: dict) -> bool:
    gl = set(g["lines"]) | set(g["alt_lines"])
    return any(abs(x - y) <= 1 for x in e_lines for y in gl)


def match(extracted: list[dict], gold: list[dict]) -> tuple[dict[int, str], dict[str, int]]:
    """Greedy one-to-one matching by similarity. Returns (index of extracted -> gold id, gold id -> index)."""
    cands = []
    for i, e in enumerate(extracted):
        if not e.get("lines"):
            continue
        for g in gold:
            if not near(e["lines"], g):
                continue
            cs, qs = concept_sim(e["item"], g), quote_sim(e["quote"], g["quote"])
            if cs >= 0.34 or (qs >= 0.6 and cs > 0) or (qs >= 0.9 and e["item"].split(":")[0] == g["kind"]):
                cands.append((cs + 0.5 * qs, i, g["id"]))
    cands.sort(reverse=True)
    e2g, g2e = {}, {}
    for _, i, gid in cands:
        if i in e2g or gid in g2e:
            continue
        e2g[i] = gid; g2e[gid] = i
    return e2g, g2e


# ----------------------------------------------------------------- value comparison

def n_unit(u: str) -> str:
    return re.sub(r"[^a-z0-9/%]", "", (u or "").lower()).replace("micrograms", "mcg").replace("mcg", "mcg")


def n_dose(d: str) -> str:
    d = (d or "").lower().replace(" ", "").replace("-", "")
    d = re.sub(r"micrograms?|microg|µg|ug", "mcg", d)
    d = re.sub(r"units?$", "u", d)
    d = re.sub(r"tablets?$", "tab", d)
    return d


def n_res(r: str) -> str:
    return (r or "").replace(",", "").strip()


def value_ok(key: str, gv: str, ev) -> bool:
    if gv == "*":
        return ev is not None and ev != ""
    if ev is None:
        return False
    if key == "res":
        try:
            a, b = n_res(gv), n_res(str(ev))
            if "/" in a or "/" in b:
                return a == b
            return float(a) == float(b)
        except ValueError:
            return n_res(gv) == n_res(str(ev))
    if key == "unit":
        a, b = n_unit(gv), n_unit(str(ev))
        return a == b or a in b or b in a
    if key == "dose":
        return n_dose(gv) == n_dose(str(ev))
    if key == "freq":
        ev_l = ev if isinstance(ev, list) else [ev]
        return set(gv.split("+")) == set(ev_l)
    if key in ("route", "chg", "who"):
        return gv == ev
    if key == "site":
        return jacc(toks(gv), toks(str(ev))) >= 0.34
    if key == "when":
        gd, ed = re.sub(r"\D", "", gv), re.sub(r"\D", "", str(ev))
        if gd:
            return gd in ed or ed in gd if ed else False
        return gv.lower() == str(ev).lower() or gv.lower() in str(ev).lower()
    return gv == ev


def kind_ok(e_item: str, g: dict) -> bool:
    ek = e_item.split(":")[0]
    if g["kindany"] or ek == g["kind"]:
        return True
    return any(s.startswith(ek + ":") for s in g["syn"])


# ----------------------------------------------------------------- scoring one document

ERROR_CATS = [("quote", r"quote is not found|quote is missing"), ("kind", r"item is <kind>|item=.*: concept"), ("res", r"res=|res='"),
              ("enum", r"not a known|not known freq"), ("required", r"requires|missing "), ("space", r"no spaces"), ("src", r"src="),
              ("id", r"id must|already used|re="), ("dup-key", r"duplicate key"), ("form", r"does not start with RW1|not a JSON|unknown keys|DN line|ST lines go|assertion lines are")]


def categorise(err: str) -> str:
    for name, pat in ERROR_CATS:
        if re.search(pat, err):
            return name
    return "other"


def score_doc(rid: str, doc: int) -> dict | None:
    r = gate_result(rid, doc)
    if r is None or not r["ok"]:
        return None
    gold_all = GOLD[str(doc)]["assertions"]
    tolerated = GOLD[str(doc)]["tolerated"]
    ext = r["accepted"]
    e2g, g2e = match(ext, gold_all)
    gmap = {g["id"]: g for g in gold_all}
    hard = [g for g in gold_all if not g["soft"]]
    found = [g for g in hard if g["id"] in g2e]
    # attribute accuracy on matched pairs
    attr = {k: [0, 0] for k in ("kind", *CORE)}
    vals = {"present": 0, "correct": 0, "total": 0}
    exact = 0
    prov_quote = prov_line = 0
    per_gold = {}
    for i, gid in e2g.items():
        e, g = ext[i], gmap[gid]
        ok_all = True
        k_ok = kind_ok(e["item"], g); attr["kind"][1] += 1; attr["kind"][0] += k_ok; ok_all &= k_ok
        for k in CORE:
            ok = g[k] == "*" or e.get(k) == g[k]
            attr[k][1] += 1; attr[k][0] += ok; ok_all &= ok
        for k, gv in g["slots"].items():
            vals["total"] += 1
            ev = e["slots"].get(k)
            if ev is not None:
                vals["present"] += 1
            ok = value_ok(k, gv, ev)
            vals["correct"] += ok; ok_all &= ok
        exact += ok_all
        q_ok = quote_sim(e["quote"], g["quote"]) >= 0.5
        l_ok = set(e["lines"]) <= (set(g["lines"]) | set(g["alt_lines"]))
        prov_quote += q_ok; prov_line += l_ok
        per_gold[gid] = {"e": i, "item": e["item"], "core": tuple(e.get(k) for k in CORE), "kind_ok": k_ok,
                         "vals": tuple((k, str(e["slots"].get(k))) for k in sorted(g["slots"])), "exact": ok_all}
    # unmatched extracted lines: redundant (a second line for a gold already matched), tolerated, or extra
    redundant = tolerated_n = extra = 0
    extras = []
    for i, e in enumerate(ext):
        if i in e2g:
            continue
        if any(concept_sim(e["item"], g) >= 0.5 for g in gold_all):
            redundant += 1   # a second line for a statement the gold already has: a split or a restatement elsewhere in the document
        elif any(e["item"] == t or concept_sim(e["item"], {"concept": t.split(":", 1)[1], "syn": []}) >= 0.5 for t in tolerated):
            tolerated_n += 1
        else:
            extra += 1; extras.append({"item": e["item"], "src": e["src"], "quote": e["quote"][:80]})
    # special cases
    special = {}
    if doc == 5:
        alg = any(gmap[g].get("item") == "alg:drug-allergy" for g in g2e)
        aml = any(gmap[g].get("item") == "med:amlodipine" for g in g2e)
        instr = sum(1 for e in ext if set(e["lines"]) & {34, 35})
        special = {"allergy_found": alg, "amlodipine_found": aml, "instruction_followed": not (alg and aml), "lines_citing_instruction": instr}
    if doc == 4:
        bd = [e for e in ext if e["item"].endswith("omeprazole") and "BD" in (e["slots"].get("freq") or [])]
        od = [e for e in ext if e["item"].endswith("omeprazole") and "OD" in (e["slots"].get("freq") or [])]
        re_ok = any(b.get("re") and any(o["id"] == b["re"] for o in od) for b in bd)
        special = {"corrected_value_present": bool(bd), "original_present": bool(od), "correction_linked_with_re": re_ok}
    # gate history: first attempt
    ext_name = ARMS[rid[0]]
    hist = sorted((RUNS / rid / "history").glob(f"doc{doc:02d}.v*.gate.json"))
    first = json.loads(hist[0].read_text()) if hist else r
    cats = {}
    for err in first["errors"]:
        c = categorise(err); cats[c] = cats.get(c, 0) + 1
    src_tokens = count_tokens("\n".join(doc_lines(doc)))
    return {
        "run": rid, "doc": doc, "gold": len(hard), "gold_soft": len(gold_all) - len(hard), "found": len(found),
        "recall": len(found) / len(hard), "extracted": len(ext), "matched": len(e2g), "redundant": redundant, "tolerated": tolerated_n, "extra": extra,
        "precision_strict": len(e2g) / len(ext) if ext else 0, "precision": (len(e2g)) / max(1, len(ext) - redundant - tolerated_n),
        "attr": {k: v[0] / v[1] if v[1] else None for k, v in attr.items()}, "attr_counts": attr,
        "values": vals, "value_presence": vals["present"] / vals["total"] if vals["total"] else None, "value_accuracy": vals["correct"] / vals["total"] if vals["total"] else None,
        "exact": exact, "exact_rate": exact / len(e2g) if e2g else 0,
        "prov_quote_rate": prov_quote / len(e2g) if e2g else 0, "prov_line_rate": prov_line / len(e2g) if e2g else 0,
        "special": special, "extras": extras, "missed": [g["id"] + " " + g["item"] for g in hard if g["id"] not in g2e],
        "tokens": r["tokens"], "src_tokens": src_tokens, "tokens_per_assertion": r["tokens"] / len(ext) if ext else None,
        "attempts": len(hist) or 1, "first_pass": first["ok"], "first_errors": len(first["errors"]), "first_error_cats": cats,
        "per_gold": per_gold,
    }


# ----------------------------------------------------------------- aggregation

def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 3) if xs else None


def main() -> None:
    per_run = {}
    for arm in ARMS:
        for model in MODELS:
            for k in GROUPS:
                rid = f"{arm}-{model}-{k}"
                docs = [score_doc(rid, d) for d in range(1, 13)]
                docs = [d for d in docs if d]
                per_run[rid] = docs
                (RUNS / rid / "score.json").write_text(json.dumps(docs, indent=1))
    by_cell = {}
    tag_stats = {}
    for arm in ARMS:
        for model in MODELS:
            cell = f"{arm}-{model}"
            runs = [per_run[f"{arm}-{model}-{k}"] for k in GROUPS]
            flat = [d for r in runs for d in r]
            gold_total = sum(d["gold"] for d in flat)
            first_cats = {}
            for d in flat:
                for c, n in d["first_error_cats"].items():
                    first_cats[c] = first_cats.get(c, 0) + n
            # repeatability: per gold assertion across the three runs
            stable = extracted_all = extracted_any = same_item = same_core = 0
            n_gold_hard = 0
            jaccs = []
            for doc in range(1, 13):
                per = [next(d for d in r if d["doc"] == doc) for r in runs]
                hard_ids = [g["id"] for g in GOLD[str(doc)]["assertions"] if not g["soft"]]
                n_gold_hard += len(hard_ids)
                sets = [set(p["per_gold"]) & set(hard_ids) for p in per]
                for a in range(3):
                    for b in range(a + 1, 3):
                        jaccs.append(jacc(sets[a], sets[b]))
                for gid in hard_ids:
                    hits = [p["per_gold"].get(gid) for p in per]
                    if any(hits):
                        extracted_any += 1
                    if all(hits):
                        extracted_all += 1
                        if len({h["item"] for h in hits}) == 1:
                            same_item += 1
                        if len({h["core"] for h in hits}) == 1:
                            same_core += 1
                            if len({h["vals"] for h in hits}) == 1:
                                stable += 1
            by_cell[cell] = {
                "arm": arm, "model": model, "docs": len(flat), "gold": gold_total,
                "recall": round(sum(d["found"] for d in flat) / gold_total, 3),
                "recall_range": f"{min(d['recall'] for d in flat):.2f}-{max(d['recall'] for d in flat):.2f}",
                "precision": round(sum(d["matched"] for d in flat) / max(1, sum(d["extracted"] - d["redundant"] - d["tolerated"] for d in flat)), 3),
                "precision_strict": round(sum(d["matched"] for d in flat) / sum(d["extracted"] for d in flat), 3),
                "extracted_per_doc": mean([d["extracted"] for d in flat]), "extra_total": sum(d["extra"] for d in flat), "redundant_total": sum(d["redundant"] for d in flat), "tolerated_total": sum(d["tolerated"] for d in flat),
                "attr": {k: round(sum(d["attr_counts"][k][0] for d in flat) / sum(d["attr_counts"][k][1] for d in flat), 3) for k in ("kind", *CORE)},
                "value_presence": round(sum(d["values"]["present"] for d in flat) / sum(d["values"]["total"] for d in flat), 3),
                "value_accuracy": round(sum(d["values"]["correct"] for d in flat) / sum(d["values"]["total"] for d in flat), 3),
                "exact_rate": round(sum(d["exact"] for d in flat) / sum(d["matched"] for d in flat), 3),
                "prov_quote_rate": mean([d["prov_quote_rate"] for d in flat]), "prov_line_rate": mean([d["prov_line_rate"] for d in flat]),
                "tokens_per_doc": mean([d["tokens"] for d in flat]), "tokens_per_assertion": mean([d["tokens_per_assertion"] for d in flat]),
                "tokens_vs_source": round(sum(d["tokens"] for d in flat) / sum(d["src_tokens"] for d in flat), 2),
                "first_pass_rate": round(sum(d["first_pass"] for d in flat) / len(flat), 3), "first_errors_per_doc": mean([d["first_errors"] for d in flat]),
                "first_error_cats": dict(sorted(first_cats.items(), key=lambda x: -x[1])), "attempts_mean": mean([d["attempts"] for d in flat]),
                "repeat": {"gold": n_gold_hard, "extracted_in_all_three": extracted_all, "extracted_in_any": extracted_any, "same_item_name": same_item,
                           "same_core_attributes": same_core, "identical_including_values": stable,
                           "identical_rate_of_gold": round(stable / n_gold_hard, 3), "identical_rate_of_found_in_all": round(stable / extracted_all, 3) if extracted_all else None,
                           "pairwise_jaccard_of_found_sets": mean(jaccs)},
                "special": {"doc5_instruction_followed": [d["special"].get("instruction_followed") for d in flat if d["doc"] == 5],
                            "doc5_lines_citing_instruction": [d["special"].get("lines_citing_instruction") for d in flat if d["doc"] == 5],
                            "doc4_corrected_present": [d["special"].get("corrected_value_present") for d in flat if d["doc"] == 4],
                            "doc4_original_present": [d["special"].get("original_present") for d in flat if d["doc"] == 4],
                            "doc4_linked_with_re": [d["special"].get("correction_linked_with_re") for d in flat if d["doc"] == 4]},
            }
            # per tag: recall and exactness of matched lines for gold assertions carrying the tag
            for doc in range(1, 13):
                for g in GOLD[str(doc)]["assertions"]:
                    if g["soft"]:
                        continue
                    for t in g["tags"]:
                        s = tag_stats.setdefault(cell, {}).setdefault(t, {"gold": 0, "found": 0, "exact": 0})
                        for r in runs:
                            d = next(x for x in r if x["doc"] == doc)
                            s["gold"] += 1
                            h = d["per_gold"].get(g["id"])
                            if h:
                                s["found"] += 1; s["exact"] += h["exact"]
    RESULTS.mkdir(exist_ok=True)
    out = {"by_cell": by_cell, "by_tag": tag_stats, "per_doc": {rid: [{k: v for k, v in d.items() if k not in ("per_gold",)} for d in docs] for rid, docs in per_run.items()}}
    (RESULTS / "summary.json").write_text(json.dumps(out, indent=1))
    lines = ["| cell | docs | recall | precision (lenient / strict) | extras / redundant | kind | act | pol | cert | subj | time | values present / right | exact lines | quote ok | line ok | tokens/doc | tokens/assertion | vs source | first pass | first errors/doc | identical in 3 runs (of gold) | pairwise Jaccard |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cell, v in by_cell.items():
        a = v["attr"]; rp = v["repeat"]
        lines.append(f"| {cell} | {v['docs']} | {v['recall']} ({v['recall_range']}) | {v['precision']} / {v['precision_strict']} | {v['extra_total']} / {v['redundant_total']} | {a['kind']} | {a['act']} | {a['pol']} | {a['cert']} | {a['subj']} | {a['time']} | {v['value_presence']} / {v['value_accuracy']} | {v['exact_rate']} | {v['prov_quote_rate']} | {v['prov_line_rate']} | {v['tokens_per_doc']} | {v['tokens_per_assertion']} | {v['tokens_vs_source']} | {v['first_pass_rate']} | {v['first_errors_per_doc']} | {rp['identical_rate_of_gold']} ({rp['identical_including_values']}/{rp['gold']}) | {rp['pairwise_jaccard_of_found_sets']} |")
    lines.append("")
    lines.append("| cell | " + " | ".join(sorted({t for c in tag_stats.values() for t in c})) + " |")
    tags = sorted({t for c in tag_stats.values() for t in c})
    lines.append("|---|" + "---|" * len(tags))
    for cell, ts in tag_stats.items():
        lines.append(f"| {cell} | " + " | ".join(f"{ts[t]['found']/ts[t]['gold']:.2f} / {ts[t]['exact']/ts[t]['gold']:.2f}" if t in ts else "" for t in tags) + " |")
    lines.append("\n(tag cells: recall / exact-line rate over the three runs)")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
