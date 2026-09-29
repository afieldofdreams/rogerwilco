#!/usr/bin/env python3
"""formcore effectiveness pilot harness.

  harness.py build                 # trials/ with one folder per trial: prompt.txt + meta.json
  harness.py check-c TRIAL         # run check-rb on a C-arm readback (rb.txt) -> check.json; prints correction text if failed
  harness.py d-batch               # build blind judge prompts for D-arm readbacks (understanding.txt)
  harness.py grade                 # code-check every out.md/out2.md -> grade.json; build blind semantic grader batches
  harness.py analyse               # merge grades -> results/summary.json + table

Arms:
  A  prose handoff, no readback
  C  formcore HO with rb=acc keys=..., receiver emits RB first; sender checks in code; one correction cycle
  D  prose handoff + prose readback paragraph; a blind model judges it against hidden criteria; one correction cycle
"""
import json, os, re, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
TRIALS = ROOT / "trials"
RESULTS = ROOT / "results"
SKILL = Path("/home/claude/formcore-skill/formcore/SKILL.md").read_text()
FC = "/home/claude/formcore-skill/formcore/scripts/formcore.py"
DOMAINS = ["copy", "extract"]
VARIANTS = ["clean", "artifact_only", "near_miss", "contradiction", "buried", "categorical"]
ARMS = ["A", "C", "D"]
SEEDS = [1, 2]

ROLE = {"copy": "You are an agent named `writer`, a copywriter.", "extract": "You are an agent named `extractor`, a data-extraction agent."}
ITEM = {"copy": "gh:crox/site#42", "extract": "fin:aug-2026-invoices"}
DELIV = {"copy": "the hero copy as Markdown", "extract": "the JSON array"}


def prompt_for(arm, dom, var, seed):
    meta = json.load(open(CORPUS / dom / f"{var}.meta.json"))
    art = (CORPUS / dom / f"{var}.artifact.md").read_text()
    agent = "writer" if dom == "copy" else "extractor"
    out_path = f"{{TRIAL}}/out.md"
    common = f"""{ROLE[dom]} You have no tools except Read and Write. Do not run code.

You will receive a task from an agent named `lead`. The brief is the artifact file:brief.md, reproduced in full below.

=== brief.md ===
{art}
=== END brief.md ===
"""
    if arm == "A":
        task = f"""Message from lead:

Please handle this: {meta['tail']}. Full details in the attached brief. Due 2 October 2026.

Produce {DELIV[dom]}. Use the Write tool to save it to {out_path} and then reply with the single word DONE."""
    elif arm == "D":
        task = f"""Message from lead:

Please handle this: {meta['tail']}. Full details in the attached brief. Due 2 October 2026.

Before you start, write a short paragraph (under 120 words) stating what you understand the requirements and acceptance criteria to be, based on the brief. Save that paragraph to {{TRIAL}}/understanding.txt with the Write tool. Then produce {DELIV[dom]} and save it to {out_path}. Reply with the single word DONE.

If lead later sends you a correction, revise and save the revised deliverable to {{TRIAL}}/out2.md."""
    else:  # C
        ho = (f"FC1 HO lead-01 from=lead to={agent} item={ITEM[dom]} ask={'DRAFT' if dom == 'copy' else 'EXTRACT'} due=20261002 "
              f"rb=acc keys={meta['crit']['keys']} art=file:brief.md // {meta['tail']}")
        task = f"""The file below is a skill you have been given for communicating with other agents. Follow it.

=== SKILL.md ===
{SKILL}
=== END SKILL ===

Message from lead:

{ho}

First, write your readback as exactly one formcore line and save it to {{TRIAL}}/rb.txt with the Write tool. Then produce {DELIV[dom]} and save it to {out_path}. Reply with the single word DONE.

If lead later sends you a re-issued HO with a correction, send a fresh readback to {{TRIAL}}/rb2.txt, then revise and save the revised deliverable to {{TRIAL}}/out2.md."""
        meta["ho"] = ho
    return common + "\n" + task, meta


def build():
    TRIALS.mkdir(exist_ok=True)
    manifest = []
    for dom in DOMAINS:
        for var in VARIANTS:
            for arm in ARMS:
                for seed in SEEDS:
                    tid = f"{dom}-{var}-{arm}{seed}"
                    d = TRIALS / tid; d.mkdir(exist_ok=True)
                    p, meta = prompt_for(arm, dom, var, seed)
                    p = p.replace("{TRIAL}", str(d))
                    (d / "prompt.txt").write_text(p)
                    m = {"id": tid, "domain": dom, "variant": var, "fault": meta["fault"], "arm": arm, "seed": seed,
                         "crit": meta["crit"], "tail": meta["tail"], "ho": meta.get("ho")}
                    json.dump(m, open(d / "meta.json", "w"), indent=1)
                    manifest.append(tid)
    json.dump(manifest, open(TRIALS / "manifest.json", "w"), indent=1)
    print(len(manifest), "trials")


# ---------------------------------------------------------------- C-arm check

def check_c(tid):
    d = TRIALS / tid; m = json.load(open(d / "meta.json"))
    rbfile = d / ("rb2.txt" if (d / "rb2.txt").exists() else "rb.txt")
    rb = rbfile.read_text().strip().splitlines()[0] if rbfile.exists() and rbfile.read_text().strip() else ""
    ho = m["ho"]
    prev0 = json.load(open(d / "check.json")) if (d / "check.json").exists() else None
    if rbfile.name == "rb2.txt" and prev0 and (prev0.get("first") or {}).get("correction"):
        ho = prev0["first"]["correction"]  # second readback answers the re-issued HO
    exp = m["crit"]["acc"]
    r = subprocess.run(["python3", FC, "check-rb", ho, rb, "--expect-acc", exp], capture_output=True, text=True)
    out = r.stdout.strip().splitlines()
    problems = [l[10:] for l in out if l.startswith("MISMATCH:")]
    notes = [l[6:] for l in out if l.startswith("NOTE:")]
    res = {"rb": rb, "passed": r.returncode == 0, "problems": problems, "notes": notes, "rb_file": rbfile.name}
    prev = json.load(open(d / "check.json")) if (d / "check.json").exists() else None
    if prev and rbfile.name == "rb2.txt":
        res = {"first": prev.get("first", prev), "second": res}
    else:
        res = {"first": res}
    json.dump(res, open(d / "check.json", "w"), indent=1)
    cur = res.get("second") or res["first"]
    print(json.dumps(cur, indent=1))
    if not cur["passed"]:
        # correction: re-issue HO with re= and the corrected criteria named in the tail (controller restates the clearance)
        fixes = []
        for p in cur["problems"]:
            mm = re.search(r"contradiction on (\w+): sender ([^ ]+) vs", p)
            if mm: fixes.append(f"{mm.group(1)} is {mm.group(2)} per the brief")
            mm = re.search(r"gap, receiver did not derive (\w+):([^ ]+)", p)
            if mm: fixes.append(f"{mm.group(1)}:{mm.group(2)} is required per the brief")
            mm = re.search(r"sender asked for (\w+) in keys=", p)
            if mm: fixes.append(f"report {mm.group(1)}")
            if "carries no acc=" in p: fixes.append("readback must carry acc= derived from the brief")
        tail = "readback mismatch: " + "; ".join(fixes)
        tail = tail[:290]
        ho2 = m["ho"].replace("FC1 HO lead-01", "FC1 HO lead-02 re=" + cur["rb"].split(" ")[2] if cur["rb"] else "FC1 HO lead-02")
        ho2 = re.sub(r" // .*$", " // " + tail, ho2)
        if "second" not in res:
            res["first"]["correction"] = ho2
            json.dump(res, open(d / "check.json", "w"), indent=1)
        print("CORRECTION:\n" + ho2)


# ---------------------------------------------------------------- D-arm judge batch

def d_batch():
    items = []
    for tid in json.load(open(TRIALS / "manifest.json")):
        d = TRIALS / tid; m = json.load(open(d / "meta.json"))
        if m["arm"] != "D" or not (d / "understanding.txt").exists(): continue
        if (d / "djudge.json").exists(): continue
        crit = [c["desc"] for c in m["crit"]["code"]] + [c["desc"] for c in m["crit"]["semantic"]]
        items.append({"id": tid, "understanding": (d / "understanding.txt").read_text().strip(), "criteria": crit})
    RESULTS.mkdir(exist_ok=True)
    batches = [items[i:i + 6] for i in range(0, len(items), 6)]
    for n, b in enumerate(batches):
        p = ["You are a strict judge. For each item, an agent has stated its understanding of a task before starting. You are given the hidden acceptance criteria the sender holds. Decide, per item, whether the stated understanding CONTRADICTS any criterion (states a different value) or OMITS a criterion that a competent worker would need to state to show they understood the brief. Ignore criteria that are generic hygiene (e.g. 'parses as JSON array', 'H1 headline') unless the understanding contradicts them.",
             "Reply with only a JSON array of objects: {\"id\": ..., \"pass\": true|false, \"contradictions\": [..], \"omissions\": [..]} where pass is false if there is at least one contradiction or one material omission.", ""]
        for it in b:
            p.append(f"### {it['id']}\nUNDERSTANDING: {it['understanding']}\nCRITERIA:\n- " + "\n- ".join(it["criteria"]) + "\n")
        (RESULTS / f"djudge_batch{n}.txt").write_text("\n".join(p))
    print(len(items), "D readbacks in", len(batches), "batches")


# ---------------------------------------------------------------- grading

UK_WORDS = ["organis", "realis", "optimis", "colour", "behaviour", "programme", "centre", "licence", "analyse", "favour", "labour", "defence"]
US_WORDS = ["organiz", "realiz", "optimiz", "color", "behavior", "program ", "center", "license", "analyze", "favor", "labor", "defense"]

def _paragraph(text):
    lines = [l.strip() for l in text.splitlines()]
    body = [l for l in lines if l and not l.startswith("#")]
    return max(body, key=len) if body else ""

def code_check(c, text):
    k, v = c["check"], c["value"]
    try:
        if k == "max_words_paragraph": return len(_paragraph(text).split()) <= v
        if k == "min_words_paragraph": return len(_paragraph(text).split()) >= v
        if k == "sentence_count_paragraph":
            p = _paragraph(text); n = len([s for s in re.split(r"(?<=[.!?])\s+", p.strip()) if s]); return n == v
        if k == "no_substring": return not any(s in text for s in v)
        if k == "regex": return re.search(v, text) is not None
        if k == "no_regex": return re.search(v, text, re.I) is None
        if k == "spelling":
            low = text.lower(); uk = sum(w in low for w in UK_WORDS); us = sum(w in low for w in US_WORDS)
            if uk == 0 and us == 0: return None  # no evidence
            return (uk >= us) if v == "UK" else (us >= uk)
        arr = None
        if k in ("json_array", "invoice_set", "amounts", "dates_iso", "currencies", "invoice_absent", "field_true", "due_dates", "amounts_are_2dp_strings"):
            t = text.strip()
            t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
            arr = json.loads(t)
            if not isinstance(arr, list): return False
            by = {str(o.get("invoice_number")): o for o in arr if isinstance(o, dict)}
        if k == "json_array": return True
        if k == "invoice_set": return sorted(by) == sorted(v)
        if k == "amounts": return all(inv in by and abs(float(str(by[inv].get("amount")).replace(",", "")) - amt) < 0.01 for inv, amt in v.items())
        if k == "dates_iso": return all(inv in by and by[inv].get("date") == dt for inv, dt in v.items())
        if k == "currencies": return all(inv in by and by[inv].get("currency") == cur for inv, cur in v.items())
        if k == "invoice_absent": return not any(inv in by for inv in v)
        if k == "field_true": return all(inv in by and by[inv].get(f) is True for inv, f in v.items())
        if k == "due_dates": return all(inv in by and by[inv].get("due_date") == dd for inv, dd in v.items())
        if k == "amounts_are_2dp_strings": return all(isinstance(o.get("amount"), str) and re.fullmatch(r"\d+\.\d{2}", o["amount"]) for o in arr if isinstance(o, dict))
    except Exception as e:
        return False
    return None

def grade():
    sem_items = []
    for tid in json.load(open(TRIALS / "manifest.json")):
        d = TRIALS / tid; m = json.load(open(d / "meta.json"))
        g = {}
        for name in ("out.md", "out2.md"):
            f = d / name
            if not f.exists(): continue
            text = f.read_text()
            g[name] = {"code": {c["id"]: code_check(c, text) for c in m["crit"]["code"]}, "words": len(text.split())}
            if m["crit"]["semantic"] and not (d / f"sem_{name}.json").exists():
                sem_items.append({"id": f"{tid}::{name}", "text": text, "criteria": [(c["id"], c["desc"]) for c in m["crit"]["semantic"]]})
        json.dump(g, open(d / "grade.json", "w"), indent=1)
    RESULTS.mkdir(exist_ok=True)
    batches = [sem_items[i:i + 5] for i in range(0, len(sem_items), 5)]
    for n, b in enumerate(batches):
        p = ["You are a strict, literal grader. For each item you get a piece of copy and a list of criteria with ids. Decide pass or fail per criterion, quoting the evidence briefly. Be literal: if a criterion says the FIRST sentence must do X, check the first sentence only.",
             "Reply with only a JSON array: [{\"id\": <item id>, \"results\": {<criterion id>: {\"pass\": true|false, \"evidence\": \"...\"}}}]", ""]
        for it in b:
            p.append(f"### {it['id']}\n" + "\n".join(f"- {cid}: {desc}" for cid, desc in it["criteria"]) + "\nTEXT:\n" + it["text"] + "\n")
        (RESULTS / f"sem_batch{n}.txt").write_text("\n".join(p))
    print(len(sem_items), "semantic items in", len(batches), "batches")


def ingest_sem(path):
    """Ingest a grader reply file (JSON array) into per-trial sem_<out>.json."""
    arr = json.loads(Path(path).read_text())
    for r in arr:
        tid, name = r["id"].split("::")
        json.dump(r["results"], open(TRIALS / tid / f"sem_{name}.json", "w"), indent=1)
    print("ingested", len(arr))


def ingest_djudge(path):
    arr = json.loads(Path(path).read_text())
    for r in arr:
        json.dump(r, open(TRIALS / r["id"] / "djudge.json", "w"), indent=1)
    print("ingested", len(arr))


# ---------------------------------------------------------------- analysis

def analyse():
    rows = []
    for tid in json.load(open(TRIALS / "manifest.json")):
        d = TRIALS / tid; m = json.load(open(d / "meta.json"))
        if not (d / "grade.json").exists(): continue
        g = json.load(open(d / "grade.json"))
        def verdict(name):
            if name not in g: return None
            code = g[name]["code"]
            sem = json.load(open(d / f"sem_{name}.json")) if (d / f"sem_{name}.json").exists() else {}
            fails = [k for k, v in code.items() if v is False] + [k for k, v in sem.items() if not v.get("pass")]
            return {"defect": bool(fails), "fails": fails}
        first = verdict("out.md"); final = verdict("out2.md") or first
        row = {"id": tid, "domain": m["domain"], "fault": m["fault"], "arm": m["arm"], "seed": m["seed"],
               "first": first, "final": final, "corrected": (d / "out2.md").exists()}
        if m["arm"] == "C" and (d / "check.json").exists():
            ck = json.load(open(d / "check.json")); row["check"] = ck["first"]["passed"]; row["check_problems"] = ck["first"]["problems"]
        if m["arm"] == "D" and (d / "djudge.json").exists():
            dj = json.load(open(d / "djudge.json")); row["check"] = dj["pass"]; row["check_problems"] = dj.get("contradictions", []) + dj.get("omissions", [])
        rows.append(row)
    json.dump(rows, open(RESULTS / "rows.json", "w"), indent=1)
    # summary
    def rate(rs, key):
        rs = [r for r in rs if r.get(key) is not None]
        return (sum(1 for r in rs if r[key]) / len(rs), len(rs)) if rs else (None, 0)
    summary = {}
    for arm in ARMS:
        ra = [r for r in rows if r["arm"] == arm]
        s = {"n": len(ra),
             "defect_first": rate([{"x": r["first"]["defect"]} for r in ra if r["first"]], "x"),
             "defect_final": rate([{"x": r["final"]["defect"]} for r in ra if r["final"]], "x")}
        if arm in ("C", "D"):
            faulty = [r for r in ra if r["fault"] != "clean" and "check" in r]
            clean = [r for r in ra if r["fault"] == "clean" and "check" in r]
            # detection: check flagged AND the first output actually had a defect (a real misunderstanding)
            real = [r for r in faulty if r["first"] and r["first"]["defect"]]
            s["detection_of_real_misreads"] = rate([{"x": not r["check"]} for r in real], "x")
            s["flag_rate_faulty"] = rate([{"x": not r["check"]} for r in faulty], "x")
            s["false_alarm_clean"] = rate([{"x": not r["check"]} for r in clean], "x")
            # false alarm broader: flagged but first output had no defect
            fine = [r for r in ra if r["first"] and not r["first"]["defect"] and "check" in r]
            s["flagged_when_output_fine"] = rate([{"x": not r["check"]} for r in fine], "x")
        summary[arm] = s
    by_fault = {}
    for f in ["clean", "artifact_only", "near_miss", "contradiction", "buried", "categorical"]:
        by_fault[f] = {arm: rate([{"x": r["final"]["defect"]} for r in rows if r["arm"] == arm and r["fault"] == f and r["final"]], "x") for arm in ARMS}
    json.dump({"summary": summary, "defect_final_by_fault": by_fault}, open(RESULTS / "summary.json", "w"), indent=1)
    print(json.dumps({"summary": summary, "defect_final_by_fault": by_fault}, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"build": build, "d-batch": d_batch, "grade": grade, "analyse": analyse}.get(cmd, lambda: None)()
    if cmd == "check-c": check_c(sys.argv[2])
    if cmd == "ingest-sem": ingest_sem(sys.argv[2])
    if cmd == "ingest-djudge": ingest_djudge(sys.argv[2])
