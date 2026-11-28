#!/usr/bin/env python3
"""Study 12: run the reviewers. Every case, both reviewers, three repeats; one claude -p call per trial.

    run.py --set pilot --claude-cap 5 [--jobs 8]

Answers are appended to trials/<set>.jsonl as they land; a rerun skips trials already answered.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import brief as B
import cases as K
import common as C

REVIEWERS = ["haiku55", "sonnet55"]
REPEATS = 3


def plan() -> list[dict]:
    return [{"tid": f"{c['case']}.{m}.r{r}", "case": c["case"], "reviewer": m, "repeat": r}
            for c in K.all_cases() for m in REVIEWERS for r in range(1, REPEATS + 1)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="pilot", choices=["pilot"])
    ap.add_argument("--claude-cap", type=float, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    cases = {c["case"]: c for c in K.all_cases()}
    out = C.TRIALS / f"{a.set}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(ln)["tid"] for ln in out.read_text().splitlines() if ln.strip()}
    todo = [t for t in plan() if t["tid"] not in done]
    ledger = C.Ledger(a.set, cap=0.0, claude_cap=a.claude_cap)
    print(f"{len(todo)} to run, {len(done)} already answered")

    def one(t):
        user = K.render(cases[t["case"]])
        r = C.call(t["reviewer"], B.REVIEWER, user, ledger, "review", t["tid"])
        return {**t, "answer": r.get("text"), "error": r.get("error"), "cost": r.get("cost"), "seconds": r.get("seconds"),
                "tokens": r.get("usage"), "user_chars": len(user)}

    n = 0
    with ThreadPoolExecutor(a.jobs) as ex, out.open("a") as fh:
        futs = [ex.submit(one, t) for t in todo]
        for f in as_completed(futs):
            try:
                rec = f.result()
            except C.CapReached as e:
                print("cap reached:", e)
                continue
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            n += 1
            if n % 100 == 0:
                print(f"[{n}/{len(todo)}] {ledger.describe()}", flush=True)
    print(f"done {n}; {ledger.describe()}")


if __name__ == "__main__":
    main()
