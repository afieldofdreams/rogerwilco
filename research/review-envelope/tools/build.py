#!/usr/bin/env python3
"""Study 11: build the plans and write the briefs. Deterministic: running it twice writes the same files.

    build.py            writes data/briefs/*.txt, data/plan-pilot.json, data/plan-main.json, data/targets.json

A CASE is one payment instruction with its file: a target payment, clean or with one planted fault.
A CELL is one way of showing a case to the reviewer. A TRIAL is one case in one cell read by one reviewer model.
A STAGE-1 text is clerk's summary or extract of a case's file, written once and shown to every reviewer.

Ids. case: <job>-<fault or clean>, pilot cases end -p. trial: <cell>-<case>-<model>. stage 1: <kind>-<case>.
"""
from __future__ import annotations

import random

import casefile as K
import common as C

# cell -> what the reviewer is told (policy), what it is shown (view, length of the file behind it), what speaks for the
# fault (payer's note, a planted document), and which cases it holds.
#   policy   W: the payment policy P1 to P5 is in the reviewer's brief. U: no policy is written down.
#   cases    "all": every clean and every faulted case. "faulted": faulted cases only, because what speaks for a fault
#            exists only where there is one.
def _cell(policy, view, length, note=None, support=None, cases="all"):
    return {"policy": policy, "view": view, "length": length, "note": note, "support": support, "cases": cases}


CELLS = {
    "W-card":           _cell("written", "card", "S"),
    "W-fileS":          _cell("written", "file", "S"),
    "W-fileM":          _cell("written", "file", "M"),
    "W-fileL":          _cell("written", "file", "L"),
    "W-account":        _cell("written", "account", "S", note="attest"),
    "W-summary":        _cell("written", "summary", "M"),
    "W-extract":        _cell("written", "extract", "M"),
    "W-fileS+excuse":   _cell("written", "file", "S", note="excuse", cases="faulted"),
    "W-fileS+supplier": _cell("written", "file", "S", support="supplier", cases="faulted"),
    "W-fileS+forged":   _cell("written", "file", "S", support="forged", cases="faulted"),
    "W-fileS+inject":   _cell("written", "file", "S", support="inject", cases="faulted"),
    "U-card":           _cell("unwritten", "card", "S"),
    "U-fileS":          _cell("unwritten", "file", "S"),
    "U-fileS+excuse":   _cell("unwritten", "file", "S", note="excuse", cases="faulted"),
    "U-fileS+supplier": _cell("unwritten", "file", "S", support="supplier", cases="faulted"),
    "U-fileS+forged":   _cell("unwritten", "file", "S", support="forged", cases="faulted"),
    "U-fileS+inject":   _cell("unwritten", "file", "S", support="inject", cases="faulted"),
}
STAGE1 = {"summary": "W-summary", "extract": "W-extract"}        # clerk's two kinds of text and the cell each feeds
REVIEWERS = ["haiku55", "sonnet55"]
CLERK = "sonnet55"                       # one clerk writes every summary and extract
N_FAULT_TARGETS = {"main": 30, "pilot": 3}       # each is used clean and with each of the six faults
N_CLEAN_TARGETS = {"main": 30, "pilot": 3}       # used clean only, so that false holds have their own cases
N_CALIBRATION_HELD_OUT = 40              # the first payments of the calibration order are never used in pilot or main


def targets() -> dict:
    """Which payments are targets. The exploratory calibration drew from the head of its own seeded order; those are
    held out here, so no registered case was seen while the design was being settled."""
    cal = list(K.POOL)
    random.Random("calibration-targets").shuffle(cal)
    held = {j["id"] for j in cal[:N_CALIBRATION_HELD_OUT]}
    rest = [j for j in K.POOL if j["id"] not in held]
    random.Random("review-envelope:targets").shuffle(rest)
    out, i = {}, 0
    for set_ in ("main", "pilot"):
        nf, nc = N_FAULT_TARGETS[set_], N_CLEAN_TARGETS[set_]
        out[set_] = {"fault": [j["id"] for j in rest[i:i + nf]], "clean": [j["id"] for j in rest[i + nf:i + nf + nc]]}
        i += nf + nc
    out["held_out_for_calibration"] = sorted(held)
    return out


JOB = {j["id"]: j for j in K.POOL}


def case_id(job: str, fault: str | None, set_: str) -> str:
    return f"{job}-{fault or 'clean'}" + ("-p" if set_ == "pilot" else "")


def case_of(row: dict) -> dict:
    """The case behind a plan row. The seed leaves the fault out, so a target's clean and faulted cases share one file
    at each length and differ only in the planted fault."""
    return K.make_case(JOB[row["job"]], row["fault"], row["length"], f"{row['set']}:{row['job']}:{row['length']}")


def plan(set_: str) -> dict:
    t = targets()[set_]
    cases = [{"job": j, "fault": f} for j in t["fault"] for f in [None] + K.FAULTS] + [{"job": j, "fault": None} for j in t["clean"]]
    stage1, trials = [], []
    for kind, cname in STAGE1.items():
        cell = CELLS[cname]
        for c in cases:
            stage1.append({"sid": f"{kind}-{case_id(c['job'], c['fault'], set_)}", "set": set_, "kind": kind, "job": c["job"], "fault": c["fault"],
                           "length": cell["length"], "author": CLERK})
    for name, cell in CELLS.items():
        for c in cases:
            if cell["cases"] == "faulted" and c["fault"] is None:
                continue
            cid = case_id(c["job"], c["fault"], set_)
            for m in REVIEWERS:
                trials.append({"tid": f"{name}-{cid}-{m}", "set": set_, "cell": name, "policy": cell["policy"], "view": cell["view"], "length": cell["length"],
                               "note": cell["note"], "support": cell["support"], "case": cid, "job": c["job"], "fault": c["fault"],
                               "fault_class": None if c["fault"] is None else ("literal" if c["fault"] in K.LITERAL else "record"),
                               "paired_target": c["job"] in t["fault"], "reviewer": m,
                               "stage1": f"{cell['view']}-{cid}" if cell["view"] in ("summary", "extract") else None})
    return {"set": set_, "cells": CELLS, "reviewers": REVIEWERS, "clerk": CLERK, "targets": t, "stage1": stage1, "trials": trials}


def briefs() -> dict[str, str]:
    out = {f"reviewer-{v}": K.brief(v) for v in ("card", "file", "account", "summary", "extract")}
    out.update({f"reviewer-unwritten-{v}": K.brief(v, "unwritten") for v in ("card", "file")})
    out["clerk-summary"] = K.clerk_brief("summary")
    out["clerk-extract"] = K.clerk_brief("extract")
    return out


def main() -> None:
    C.BRIEFS.mkdir(parents=True, exist_ok=True)
    for name, text in briefs().items():
        (C.BRIEFS / f"{name}.txt").write_text(text + "\n")
    C.write_json(C.DATA / "targets.json", targets())
    for set_ in ("pilot", "main"):
        p = plan(set_)
        C.write_json(C.DATA / f"plan-{set_}.json", p)
        by = {}
        for t in p["trials"]:
            by[t["cell"]] = by.get(t["cell"], 0) + 1
        print(f"{set_}: {len(p['stage1'])} stage-1 texts, {len(p['trials'])} trials; per cell {by}")
    sizes = {}
    for length in K.LENGTHS:
        c = K.make_case(K.POOL[0], None, length, f"size:{length}")
        sizes[length] = len(K.view_file(c))
    print("file sizes in characters for J01:", sizes)


if __name__ == "__main__":
    main()
