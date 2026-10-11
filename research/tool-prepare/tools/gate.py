#!/usr/bin/env python3
"""The pilot gate for a weak receiver, from its pilot summary: prints the two registered conditions and exits 0 only if both hold.

  python3 tools/gate.py results/pilot-gpt54mini/summary.json

Condition 1: arm C makes wrong acts in at least 5% of induced contexts (the contexts still produce the failure the study is about).
Condition 2: arm Q reaches a commit or a refusal (acted, held or asked, with the receiver's own last word) in at least 90% of trials.
"""
from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    s = json.load(open(argv[0]))
    rows = s["rows"]
    c = [r for r in rows if r["arm"] == "C" and r["kind"] == "induced"]
    q = [r for r in rows if r["arm"] == "Q"]
    wrong = sum(r["wrong_act"] for r in c)
    reached = sum(1 for r in q if r["status"] == "ok" and (r["acted"] or r["held"] or r["asked"]))
    c_ok = bool(c) and wrong / len(c) >= 0.05
    q_ok = bool(q) and reached / len(q) >= 0.90
    print(f"condition 1, C wrong acts in induced contexts: {wrong} of {len(c)} ({100 * wrong / len(c):.1f}%): {'met' if c_ok else 'NOT met'}" if c else "condition 1: no C trials")
    print(f"condition 2, Q reached a commit or a refusal: {reached} of {len(q)} ({100 * reached / len(q):.1f}%): {'met' if q_ok else 'NOT met'}" if q else "condition 2: no Q trials")
    harness = [r["id"] for r in rows if r["status"] != "ok" and not r["status"].startswith("held")]
    if harness:
        print(f"trials ending in a harness fault or an unexpected reply ({len(harness)}): " + ", ".join(harness[:10]))
    return 0 if c_ok and q_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
