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

# cell -> view, length of the file behind it, payer's note, which cases
#   cases "all": every clean and every faulted case. "faulted": faulted cases only (the note differs from the attest
#   cell only on faulted cases, so the clean cases of fileM+attest stand for both).
CELLS = {
    "card":         {"view": "card",     "length": "M", "note": None,     "cases": "all"},
    "fileS":        {"view": "file",     "length": "S", "note": None,     "cases": "all"},
    "fileM":        {"view": "file",     "length": "M", "note": None,     "cases": "all"},
    "fileL":        {"view": "file",     "length": "L", "note": None,     "cases": "all"},
    "cardfileM":    {"view": "cardfile", "length": "M", "note": None,     "cases": "all"},
    "fileM+attest": {"view": "file",     "length": "M", "note": "attest", "cases": "all"},
    "fileM+excuse": {"view": "file",     "length": "M", "note": "excuse", "cases": "faulted"},
    "card+excuse":  {"view": "card",     "length": "M", "note": "excuse", "cases": "faulted"},
    "account":      {"view": "account",  "length": "M", "note": "attest", "cases": "all"},
    "summaryM":     {"view": "summary",  "length": "M", "note": None,     "cases": "all"},
    "extractM":     {"view": "extract",  "length": "M", "note": None,     "cases": "all"},
}
REVIEWERS = ["haiku55", "sonnet55"]
CLERK = "sonnet55"                       # one clerk writes every summary and extract
N_FAULT_TARGETS = {"main": 40, "pilot": 6}       # each is used clean and with each of the six faults
N_CLEAN_TARGETS = {"main": 40, "pilot": 6}       # used clean only, so that false holds have their own cases
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
    for kind in ("summary", "extract"):
        cell = CELLS[f"{kind}M"]
        for c in cases:
            stage1.append({"sid": f"{kind}-{case_id(c['job'], c['fault'], set_)}", "set": set_, "kind": kind, "job": c["job"], "fault": c["fault"],
                           "length": cell["length"], "author": CLERK})
    for name, cell in CELLS.items():
        for c in cases:
            if cell["cases"] == "faulted" and c["fault"] is None:
                continue
            cid = case_id(c["job"], c["fault"], set_)
            for m in REVIEWERS:
                trials.append({"tid": f"{name}-{cid}-{m}", "set": set_, "cell": name, "view": cell["view"], "length": cell["length"],
                               "note": cell["note"], "case": cid, "job": c["job"], "fault": c["fault"],
                               "fault_class": None if c["fault"] is None else ("literal" if c["fault"] in K.LITERAL else "record"),
                               "paired_target": c["job"] in t["fault"], "reviewer": m,
                               "stage1": f"{cell['view']}-{cid}" if cell["view"] in ("summary", "extract") else None})
    return {"set": set_, "cells": CELLS, "reviewers": REVIEWERS, "clerk": CLERK, "targets": t, "stage1": stage1, "trials": trials}


def briefs() -> dict[str, str]:
    out = {f"reviewer-{v}": K.brief(v) for v in sorted(K.SHOWN)}
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
