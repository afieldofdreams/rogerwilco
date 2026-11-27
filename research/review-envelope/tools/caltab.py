#!/usr/bin/env python3
"""Tabulate calibration files: caltab.py <name> [<name> ...]"""
import collections, json, sys
import common as C
rows = [json.loads(l) for n in sys.argv[1:] for l in (C.ROOT / "calibration" / f"{n}.jsonl").read_text().splitlines() if l.strip()]
LIT = {"amount", "account", "supplier"}
cells = collections.defaultdict(collections.Counter)
size = collections.defaultdict(list)
for r in rows:
    kind = "clean" if r["fault"] is None else ("literal" if r["fault"] in LIT else "record")
    k = (r["model"], r["view"], r["length"], r["note"] or "-", kind)
    cells[k][r["outcome"]] += 1
    size[k].append((r["chars"], r["seconds"] or 0, r["cost"] or 0))
for k in sorted(cells):
    s = size[k]; n = len(s)
    print(f"{k[0]:9} {k[1]:8} {k[2]} {k[3]:7} {k[4]:8} n={n:<3} {dict(sorted(cells[k].items()))}  ~{sum(x[0] for x in s)//n} chars {sum(x[1] for x in s)/n:.0f}s ${sum(x[2] for x in s)/n:.4f}")
print(len(rows), "rows")
if "-v" in sys.argv[0:1] or True:
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["fault"] and r["outcome"] != "caught":
            by[(r["model"], r["view"], r["length"], r["note"] or "-")][f"{r['fault']}:{r['outcome']}"] += 1
    for k in sorted(by):
        print("  not caught", k, dict(by[k]))
