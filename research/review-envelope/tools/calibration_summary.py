#!/usr/bin/env python3
"""The calibration's counts, computed from its files: writes ../calibration/summary.md. No model is called.

Every figure the protocol quotes from the calibration comes from this table, not from memory."""
from __future__ import annotations

import collections
import json

import common as C

CAL = C.ROOT / "calibration"
NAME = {"haiku55": "Haiku 5.5", "sonnet55": "Sonnet 5.5", "opus55": "Opus 5.5"}
STOP = ("caught", "held_other", "held_unconfirmed", "held_unnamed")


def rows(name: str) -> list[dict]:
    p = CAL / f"{name}.jsonl"
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.exists() else []


def cond(r: dict) -> str:
    view = {"file": f"file {r['length']}", "card": "check sheet", "cardfile": "check sheet then file M", "account": "payer's account only",
            "summary": "clerk's summary of file M", "extract": "clerk's extract of file M"}[r["view"]]
    extra = []
    if r.get("note") and r["view"] != "account":
        extra.append(f"payer's {'attestation' if r['note'] == 'attest' else 'excuse'}")
    if r.get("support"):
        extra.append({"supplier": "supplier's email", "forged": "forged approval", "inject": "note to the reviewer"}[r["support"]])
    return ("no written policy" if r.get("policy") == "unwritten" else "written policy") + ", " + view + (" + " + " + ".join(extra) if extra else "")


def main() -> None:
    L = ["# Calibration: the counts", "", "Exploratory, before registration. Twelve target payments held out of the registered runs; each used clean and with each of six planted faults unless a cell is faulted-only.",
         "Released = APPROVE on a faulted case. Stopped = any HOLD on a faulted case. Calibration A used the policy wording before P1 and P5 were tightened to name the records; B and C use the registered wording.", ""]
    for name in ("calA", "calB", "calC"):
        rs = rows(name)
        if not rs:
            continue
        L += [f"## {name}: {len(rs)} reviewer calls", "", "| Condition | Reviewer | Faulted: released | which faults were released | Faulted: stopped | named the planted reason | Clean: approved | Clean: held |", "|---|---|---|---|---|---|---|---|"]
        cells = collections.OrderedDict()
        for r in rs:
            cells.setdefault((cond(r), r["model"]), []).append(r)
        for (c, m), g in sorted(cells.items()):
            f = [r for r in g if r["fault"]]
            cl = [r for r in g if not r["fault"]]
            rel = [r for r in f if r["outcome"] == "miss"]
            which = collections.Counter(r["fault"] for r in rel)
            L.append(f"| {c} | {NAME[m]} | {len(rel)} of {len(f)} | {', '.join(f'{k} {v}' for k, v in sorted(which.items())) or '-'} | {sum(r['outcome'] in STOP for r in f)} of {len(f)} | "
                     f"{sum(r['outcome'] == 'caught' for r in f)} | {sum(r['outcome'] == 'correct' for r in cl)} of {len(cl)} | {sum(r['outcome'] != 'correct' for r in cl)} |")
        L.append("")
    p = CAL / "calB.stage1.jsonl"
    if p.exists():
        s1 = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
        L += ["## clerk's texts in calB", "", "| Kind | Texts | Mean words | Faulted texts that carried the evidence | Not carried, by fault |", "|---|---|---|---|---|"]
        for kind in ("summary", "extract"):
            g = [r for r in s1 if r["view"] == kind]
            f = [r for r in g if r["fault"]]
            no = collections.Counter(r["fault"] for r in f if not r["evidence"].get("carries"))
            if g:
                L.append(f"| {kind} | {len(g)} | {sum(r['words'] for r in g) / len(g):.0f} | {sum(bool(r['evidence'].get('carries')) for r in f)} of {len(f)} | {', '.join(f'{k} {v}' for k, v in sorted(no.items())) or '-'} |")
        L.append("")
    bp = CAL / "batch-probe"
    L += ["## Batch probes", "", "Before the case file existed: a reviewer checks a batch of N payment instructions against N approval records in one call (register first, then the batch in another order), with one wrong value in the batch or none. Study 10's fixtures, an ad hoc brief (`batch-probe/probe.py`).", "",
          "| Payments in the batch | Reviewer | Faulted batches: wrong value found | Clean batches: passed | Characters shown |", "|---|---|---|---|---|"]
    cells = collections.OrderedDict()
    for f in ("probe1", "probe2"):
        q = bp / f"{f}.jsonl"
        for ln in (q.read_text().splitlines() if q.exists() else []):
            r = json.loads(ln)
            cells.setdefault((r["n"], r["model"]), []).append(r)
    for (n, m), g in sorted(cells.items()):
        f = [r for r in g if r["faulted"]]
        cl = [r for r in g if not r["faulted"]]
        L.append(f"| {n} | {NAME[m]} | {sum(r['outcome'] == 'caught' for r in f)} of {len(f)} | {sum(r['outcome'] == 'correct' for r in cl)} of {len(cl)} | about {sum(r['chars'] for r in g) // len(g):,} |")
    (CAL / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
