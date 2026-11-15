#!/usr/bin/env python3
"""The site page for study 10, generated from results/summary.json so that no figure on it is typed by hand.

  python3 tools/site_page.py            # writes app/static/research/scheduler-judge.html (then run app/tools/stamp.py)
  python3 tools/site_page.py --figures  # prints the named figures the page carries, as the app test recomputes them

Every number in the prose is a <span data-fig="name">value</span>; figures() is the single source of those values and
app/tests/test_research_figures.py asserts the committed page carries exactly what figures() computes from the JSON.
The pilot's figures are read from results/pilot/summary.json; the three missed pairs the page quotes are read from their
trial files, verbatim.
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
import fixtures as F  # noqa: E402
from grade import map_detail  # noqa: E402

PAGE = C.REPO / "app" / "static" / "research" / "scheduler-judge.html"
JUDGES = ["haiku55", "gpt54mini", "sonnet55", "gpt55"]
SHORT = {"haiku55": "h55", "gpt54mini": "mini", "sonnet55": "s55", "gpt55": "g55"}
FORMATS = ["prose", "line"]
# The three misses the page quotes: the lookalike payee passed, one in prose and two on lines.
QUOTED_MISSES = ["prose-J11-supplier-haiku55-by-gpt54mini", "line-J05-supplier-gpt54mini-by-gpt54mini",
                 "line-J17-supplier-gpt54mini-by-gpt54mini"]


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def kn(k: int, n: int) -> str:
    return f"{k:,} of {n:,}"


def bound(n: int) -> str:
    """The 95% upper bound of 0 of n, as studies 6 and 7 report it."""
    import analyse
    return f"{100 * analyse.cp_interval(0, n)[1]:.1f}%"


def pval(p: float) -> str:
    if p < 0.001:
        return "under 0.001"
    return f"{p:.2f}"


def figures(results: Path = C.RESULTS) -> dict:
    s = load(results / "summary.json")
    rows = s["rows"]
    f: dict[str, str] = {}
    f["trials"] = f"{s['trials_graded']:,}"
    f["readbacks"] = f"{s['readbacks_planned']:,}"
    f["jobs"] = str(len(F.JOBS))
    f["faulted_jobs"] = str(len(F.JOBS) * len(F.FAULT_SLOTS))
    f["cost_openai"] = f"${s['cost']['openai']:,.2f}"
    f["cost_claude"] = f"${s['cost']['claude_list']:,.2f}"
    for n in (140, 280, 560):
        f[f"ub{n}"] = bound(n)

    faulted = [r for r in rows if r["slot"]]
    clean = [r for r in rows if not r["slot"]]
    count = lambda rs, o: sum(1 for r in rs if r["outcome"] == o)  # noqa: E731

    # per cell: format x judge x author
    for r_fmt in FORMATS:
        for j in JUDGES:
            for a in (j, C.PARTNER[j]):
                fr = [r for r in faulted if r["format"] == r_fmt and r["judge"] == j and r["author"] == a]
                cr = [r for r in clean if r["format"] == r_fmt and r["judge"] == j and r["author"] == a]
                p = f"{r_fmt}_{SHORT[j]}_{SHORT[a]}"
                f[f"{p}_miss"] = kn(count(fr, "miss"), len(fr))
                f[f"{p}_wrong"] = kn(count(fr, "wrong_slot") + count(fr, "slot_not_named"), len(fr))
                f[f"{p}_fa"] = kn(count(cr, "false_alarm"), len(cr))
                f[f"{p}_unp"] = kn(count(fr + cr, "unparseable"), len(fr) + len(cr))
    # per judge, pooled
    for j in JUDGES:
        m = SHORT[j]
        fr = [r for r in faulted if r["judge"] == j]; cr = [r for r in clean if r["judge"] == j]
        f[f"{m}_miss"] = kn(count(fr, "miss"), len(fr))
        f[f"{m}_fa"] = kn(count(cr, "false_alarm"), len(cr))
        f[f"{m}_fa_k"] = str(count(cr, "false_alarm"))
        f[f"{m}_wrong_k"] = str(count(fr, "wrong_slot"))
        for r_fmt in FORMATS:
            frf = [r for r in fr if r["format"] == r_fmt]; crf = [r for r in cr if r["format"] == r_fmt]
            f[f"{m}_{r_fmt}_miss"] = kn(count(frf, "miss"), len(frf))
            f[f"{m}_{r_fmt}_fa"] = kn(count(crf, "false_alarm"), len(crf))
            f[f"{m}_{r_fmt}_wrong_k"] = str(count(frf, "wrong_slot"))
    strong = [r for r in faulted if r["judge"] in ("haiku55", "sonnet55", "gpt55")]
    f["strong_miss"] = kn(count(strong, "miss"), len(strong))
    f["strong_unnamed"] = str(sum(1 for r in strong if r["outcome"] != "caught"))
    sup = [r for r in faulted if r["judge"] == "gpt54mini" and r["slot"] == "supplier"]
    f["mini_supplier_miss"] = kn(count(sup, "miss"), len(sup))
    per_cell = [count([r for r in sup if r["format"] == fm and r["author"] == au], "miss") for fm in FORMATS for au in ("gpt54mini", "haiku55")]
    lo, hi = min(per_cell), max(per_cell)
    f["mini_supplier_cell"] = f"{lo} of 20" if lo == hi else f"{lo} to {hi} of 20"
    other = [r for r in faulted if r["slot"] != "supplier"]
    f["other_miss"] = kn(count(other, "miss"), len(other))
    f["all_miss_k"] = str(count(faulted, "miss"))
    f["all_faulted"] = f"{len(faulted):,}"
    # the false alarms
    hp = [r for r in clean if r["judge"] == "haiku55" and r["format"] == "prose" and r["outcome"] == "false_alarm"]
    hl = [r for r in clean if r["judge"] == "haiku55" and r["format"] == "line" and r["outcome"] == "false_alarm"]
    f["h55_prose_fa_date"] = str(sum(1 for r in hp if r["detail"] == "date"))
    f["h55_prose_fa_k"] = str(len(hp))
    f["h55_fa_date_days"] = str(len({r["payment_date"] for r in hp if r["detail"] == "date"}))
    f["payment_days"] = str(len({j["payment_date"] for j in F.JOBS}))
    f["h55_line_fa_appr"] = str(sum(1 for r in hl if r["detail"] == "approval"))
    f["h55_line_fa_appr_noecho"] = str(sum(1 for r in hl if r["detail"] == "approval" and not r["echoes_appr"]))
    f["h55_line_noecho_passed"] = str(sum(1 for r in clean if r["judge"] == "haiku55" and r["format"] == "line"
                                          and r["outcome"] == "correct" and not r["echoes_appr"]))
    f["h55_line_fa_k"] = str(len(hl))
    oa = [r for r in clean if r["judge"] in ("gpt54mini", "gpt55") and r["outcome"] == "false_alarm"]
    f["openai_fa_k"] = str(len(oa))
    f["openai_fa_not_as_given"] = str(sum(1 for r in oa if r["supplier_as_given"] is False))
    unp = [r for r in rows if r["outcome"] == "unparseable"]
    f["unp_k"] = str(len(unp))
    f["unp_named_planted"] = str(sum(1 for r in unp if r["slot"] and map_detail(r["first_line"])[0] == r["slot"]))
    # the code check
    cc = s["code_check"]
    f["code_miss"] = kn(sum(v["faulted"]["miss"]["k"] for v in cc.values()), sum(v["faulted"]["n"] for v in cc.values()))
    f["code_fa"] = kn(sum(v["clean"]["false_alarm"]["k"] for v in cc.values()), sum(v["clean"]["n"] for v in cc.values()))
    f["code_fa_form"] = str(sum(v["clean"]["false_alarm_tiers"].get("form", 0) for v in cc.values()))
    f["code_unnamed"] = str(sum(v["faulted"]["slot_not_named"]["k"] for v in cc.values()))
    for a in JUDGES:
        v = cc[a]
        f[f"code_{SHORT[a]}_miss"] = kn(v["faulted"]["miss"]["k"], v["faulted"]["n"])
        f[f"code_{SHORT[a]}_fa"] = kn(v["clean"]["false_alarm"]["k"], v["clean"]["n"])
        f[f"code_{SHORT[a]}_unnamed"] = kn(v["faulted"]["slot_not_named"]["k"] + v["faulted"]["wrong_slot"]["k"], v["faulted"]["n"])
    # the readbacks
    fid = s["fidelity"]
    n_rb = sum(v["n"] for v in fid.values())
    f["rb_first"] = kn(sum(v["first"] for v in fid.values()), n_rb)
    f["rb_later"] = str(sum(v["later"] for v in fid.values()))
    f["rb_dropped"] = str(sum(v["dropped"] for v in fid.values()))
    f["rb_recheck"] = str(sum(v["accepted_on_recheck"] for v in fid.values()))
    f["h55_no_version"] = kn(fid["haiku55|line"]["version_token_missing"], fid["haiku55|line"]["n"])
    # the hypotheses
    h = s["hypotheses"]
    for j in JUDGES:
        m = SHORT[j]
        f[f"h1_{m}"] = h["H1"][j]["outcome"]
        f[f"h2_{m}"] = h["H2"][j]["outcome"]
        f[f"h3_{m}"] = h["H3"][j]["outcome"]
        f[f"h3_{m}_same_k"] = str(h["H3"][j]["same_author_misses"]["k"])
        f[f"h3_{m}_diff_k"] = str(h["H3"][j]["different_author_misses"]["k"])
        f[f"{m}_line_miss_k"] = str(h["H2"][j]["line_misses"]["k"])
        f[f"{m}_prose_miss_k"] = str(h["H2"][j]["prose_misses"]["k"])
    f["h2_mini_p"] = pval(h["H2"]["gpt54mini"]["fisher_one_sided_p"])
    f["h2_mini_prose_only"] = str(h["H2"]["gpt54mini"]["discordant_prose_only"])
    f["h2_mini_line_only"] = str(h["H2"]["gpt54mini"]["discordant_line_only"])
    f["h4"] = h["H4"]["outcome"]
    # cost a judgment
    by = s["cost"]["by"]
    for a in JUDGES:
        f[f"cost_{SHORT[a]}_judge"] = f"${by[f'{a}|judge']['mean']:.4f}"
    # the pilot
    pil = results / "pilot" / "summary.json"
    if pil.exists():
        p = load(pil)
        pf = [r for r in p["rows"] if r["slot"]]; pc = [r for r in p["rows"] if not r["slot"]]
        f["pilot_trials"] = str(p["trials_graded"])
        f["pilot_caught"] = kn(count(pf, "caught"), len(pf))
        f["pilot_fa"] = kn(count(pc, "false_alarm"), len(pc))
        f["pilot_cost_openai"] = f"${p['cost']['openai']:,.2f}"
        f["pilot_readbacks"] = str(p["readbacks_planned"])
    return f


def quoted_misses() -> list[dict]:
    out = []
    for tid in QUOTED_MISSES:
        d = C.TRIALS / "main" / tid
        meta = C.read_json(d / "meta.json")
        prompt = (d / "prompt.txt").read_text()
        readback = prompt.split("payer's readback:\n", 1)[1].split("\n\nYour answer", 1)[0]
        job = F.JOB[meta["job"]]
        planted = F.plant(job, meta["slot"])
        out.append({"tid": tid, "job": job, "planted": planted, "format": meta["fmt"], "author": meta["author"],
                    "judge": meta["judge"], "readback": readback, "answer": (d / "answer.txt").read_text().strip()})
    return out


def fig(f: dict, key: str) -> str:
    return f'<span data-fig="{key}">{html.escape(f[key])}</span>'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--figures", action="store_true")
    a = ap.parse_args(argv)
    f = figures()
    if a.figures:
        print(json.dumps(f, indent=1)); return 0
    from site_text import render  # the page text lives beside this, written once the results were in
    html_text = render(f, fig, quoted_misses())
    if "—" in html_text:
        sys.exit("the page text carries an em dash")
    PAGE.write_text(html_text)
    print("wrote", PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
