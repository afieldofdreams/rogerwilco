#!/usr/bin/env python3
"""Study 11: build the plans and write the briefs. Deterministic: running it twice writes the same files.

    build.py            writes data/briefs/*.txt, data/plan-pilot.json, data/plan-main.json, data/targets.json

A CASE is one payment instruction with its file: a target payment, clean or with one planted fault.
A CELL is one way of putting a case in front of the reviewer. A TRIAL is one case in one cell read by one reviewer.
A STAGE-1 text is one clerk's summary or extract of a case's file, written once and shown to every reviewer.

Ids. case: <job>-<fault or clean>, pilot cases end -p. trial: <cell>-<case>-<reviewer>. stage 1: <kind>-<clerk>-<case>.
"""
from __future__ import annotations

import random

import casefile as K
import common as C


def _cell(policy, view, length, note=None, support=None, cases="all", clerk=None):
    return {"policy": policy, "view": view, "length": length, "note": note, "support": support, "cases": cases, "clerk": clerk}


# cell -> what the reviewer is told (policy), what it is shown (view, length of the file behind it), what speaks for the
# fault (payer's note, a planted document), and which cases it holds.
#   policy   written: the payment policy P1 to P5 is in the reviewer's brief. unwritten: no policy.
#   cases    all       every clean and every faulted case (240 in the main run)
#            twins     every faulted case, and the clean case of each fault target carrying the harmless twin of the
#                      text (210): the text is present on clean and faulted cases alike
#            distinct  the cases whose instruction differs: clean, amount, account, supplier, noapproval (180). In the
#                      account view nothing but the instruction is shown, and a duplicate or onhold case is its clean
#                      case word for word.
CELLS = {
    "W-card":           _cell("written", "card", "S"),
    "W-fileS":          _cell("written", "file", "S"),
    "W-fileM":          _cell("written", "file", "M"),
    "W-fileL":          _cell("written", "file", "L"),
    "W-summary-s":      _cell("written", "summary", "M", clerk="sonnet55"),
    "W-summary-h":      _cell("written", "summary", "M", clerk="haiku55"),
    "W-extract-s":      _cell("written", "extract", "M", clerk="sonnet55"),
    "W-extract-h":      _cell("written", "extract", "M", clerk="haiku55"),
    "W-account":        _cell("written", "account", "S", note="attest", cases="distinct"),
    "W-fileS+excuse":   _cell("written", "file", "S", note="excuse", cases="twins"),
    "W-fileS+supplier": _cell("written", "file", "S", support="supplier", cases="twins"),
    "W-fileS+forged":   _cell("written", "file", "S", support="forged", cases="twins"),
    "W-fileS+inject":   _cell("written", "file", "S", support="inject", cases="twins"),
    "U-card":           _cell("unwritten", "card", "S"),
    "U-fileS":          _cell("unwritten", "file", "S"),
    "U-fileM":          _cell("unwritten", "file", "M"),          # amendment 1
    "U-account":        _cell("unwritten", "account", "S", note="attest", cases="distinct"),
    "U-fileS+excuse":   _cell("unwritten", "file", "S", note="excuse", cases="twins"),
    "U-fileS+supplier": _cell("unwritten", "file", "S", support="supplier", cases="twins"),
    "U-fileS+forged":   _cell("unwritten", "file", "S", support="forged", cases="twins"),
    "U-fileS+inject":   _cell("unwritten", "file", "S", support="inject", cases="twins"),
}
TEXTS = ["excuse", "supplier", "forged", "inject"]
REVIEWERS = ["haiku55", "sonnet55"]
CLERKS = ["sonnet55", "haiku55"]
N_FAULT_TARGETS = {"main": 30, "pilot": 3}       # each is used clean and with each of the six faults
N_CLEAN_TARGETS = {"main": 30, "pilot": 3}       # used clean only, so that false holds have cases of their own
N_CALIBRATION_HELD_OUT = 40              # the first payments of the calibration's seeded order are never targets


def targets() -> dict:
    """Which payments are targets. The calibration drew from the head of its own seeded order; those 40 are held out,
    so no registered case was seen while the design was being settled. The rest are dealt supplier by supplier, so
    that fault targets and clean-only targets share one mix of the nine suppliers. J02, whose approved payment date
    is a Saturday, is never a target."""
    cal = list(K.POOL)
    random.Random("calibration-targets").shuffle(cal)
    held = {j["id"] for j in cal[:N_CALIBRATION_HELD_OUT]}
    by_sup: dict[str, list[dict]] = {}
    rest = [j for j in K.POOL if j["id"] not in held and j["id"] != "J02"]
    random.Random("review-envelope:targets").shuffle(rest)
    for j in rest:
        by_sup.setdefault(j["sup"], []).append(j)
    sups = sorted(by_sup)
    random.Random("review-envelope:supplier-order").shuffle(sups)
    dealt = []
    while any(by_sup.values()):
        for s in sups:
            if by_sup[s]:
                dealt.append(by_sup[s].pop(0))
    out, i = {}, 0
    for set_ in ("main", "pilot"):
        nf, nc = N_FAULT_TARGETS[set_], N_CLEAN_TARGETS[set_]
        out[set_] = {"fault": [j["id"] for j in dealt[i:i + nf]], "clean": [j["id"] for j in dealt[i + nf:i + nf + nc]]}
        i += nf + nc
    out["held_out_for_calibration"] = sorted(held)
    return out


JOB = {j["id"]: j for j in K.POOL}


def case_id(job: str, fault: str | None, set_: str) -> str:
    return f"{job}-{fault or 'clean'}" + ("-p" if set_ == "pilot" else "")


def case_of(row: dict) -> dict:
    """The case behind a plan row. The seed names the set and the target only."""
    return K.make_case(JOB[row["job"]], row["fault"], row["length"], f"{row['set']}:{row['job']}")


def cases_of(cell: dict, t: dict) -> list[dict]:
    every = [{"job": j, "fault": f} for j in t["fault"] for f in [None] + K.FAULTS] + [{"job": j, "fault": None} for j in t["clean"]]
    if cell["cases"] == "all":
        return every
    if cell["cases"] == "twins":
        return [c for c in every if c["job"] in t["fault"]]
    if cell["cases"] == "distinct":
        return [c for c in every if c["fault"] not in ("duplicate", "onhold")]
    raise ValueError(cell["cases"])


def plan(set_: str) -> dict:
    t = targets()[set_]
    stage1, trials = [], []
    for name, cell in CELLS.items():
        for c in cases_of(cell, t):
            cid = case_id(c["job"], c["fault"], set_)
            sid = None
            if cell["clerk"]:
                sid = f"{cell['view']}-{cell['clerk']}-{cid}"
                stage1.append({"sid": sid, "set": set_, "kind": cell["view"], "author": cell["clerk"], "cell": name, "case": cid, "job": c["job"],
                               "fault": c["fault"], "length": cell["length"]})
            for m in REVIEWERS:
                trials.append({"tid": f"{name}-{cid}-{m}", "set": set_, "cell": name, "policy": cell["policy"], "view": cell["view"], "length": cell["length"],
                               "note": cell["note"], "support": cell["support"], "case": cid, "job": c["job"], "fault": c["fault"],
                               "fault_class": K.CLASS.get(c["fault"]), "fault_target": c["job"] in t["fault"], "reviewer": m, "stage1": sid})
    return {"set": set_, "cells": CELLS, "reviewers": REVIEWERS, "clerks": CLERKS, "targets": t, "stage1": stage1, "trials": trials}


def briefs() -> dict[str, str]:
    out = {f"reviewer-{v}": K.brief(v) for v in ("card", "file", "account", "summary", "extract")}
    out.update({f"reviewer-unwritten-{v}": K.brief(v, "unwritten") for v in ("card", "file", "account")})
    out["clerk-summary"] = K.clerk_brief("summary")
    out["clerk-extract"] = K.clerk_brief("extract")
    return out


def main() -> None:
    C.BRIEFS.mkdir(parents=True, exist_ok=True)
    for f in C.BRIEFS.glob("*.txt"):
        f.unlink()
    for name, text in briefs().items():
        (C.BRIEFS / f"{name}.txt").write_text(text + "\n")
    tg = targets()
    C.write_json(C.DATA / "targets.json", tg)
    for set_ in ("pilot", "main"):
        p = plan(set_)
        C.write_json(C.DATA / f"plan-{set_}.json", p)
        by: dict[str, int] = {}
        for t in p["trials"]:
            by[t["cell"]] = by.get(t["cell"], 0) + 1
        mix: dict[str, int] = {}
        for j in tg[set_]["fault"]:
            mix[JOB[j]["sup"]] = mix.get(JOB[j]["sup"], 0) + 1
        print(f"{set_}: {len(p['stage1'])} stage-1 texts, {len(p['trials'])} trials; per cell {by}")
        print(f"   fault targets by supplier {dict(sorted(mix.items()))}; NET {sum(JOB[j]['kind'] == 'NET' for j in tg[set_]['fault'])}")
    for length in K.LENGTHS:
        c = K.make_case(K.POOL[0], None, length, "size")
        print(f"file {length}: {len(K.view_file(c)):,} characters for J01")


if __name__ == "__main__":
    main()
