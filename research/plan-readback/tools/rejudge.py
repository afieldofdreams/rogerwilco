#!/usr/bin/env python3
"""Judge done notes again under the current judge prompt, keeping the earlier verdict beside the new one.

  python3 tools/rejudge.py --only B3-,-B- [--only ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import check as K  # noqa: E402
import run as R  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--only", action="append", default=[]); ap.add_argument("--missing", action="store_true", help="only done notes with no verdict yet")
    a = ap.parse_args(argv)
    n = 0
    for trial in sorted(C.TRIALS.iterdir()):
        if not any(all(x in trial.name for x in o.split(",")) for o in a.only):
            continue
        if not (trial / "done.txt").exists() or not (trial / "turns.json").exists():
            continue
        meta = C.read_json(trial / "meta.json")
        if meta["arm"] not in ("A", "B") or (meta["arm"] == "A" and meta["block"] != 3):
            continue
        old = trial / "judge_done.json"
        if a.missing and old.exists():
            continue
        if old.exists():
            k = 1
            while (trial / f"judge_done.v{k}.json").exists():
                k += 1
            old.rename(trial / f"judge_done.v{k}.json")
        turns = C.read_json(trial / "turns.json")
        ok = R.judge(trial, "done", turns["turns"])
        C.write_json(trial / "turns.json", turns)
        K.dn_check(trial)
        n += 1
        print(f"{trial.name:36s} {'judged' if ok else 'NO VERDICT'} {json.dumps(C.read_json(trial / 'judge_done.json')) if ok else ''}", flush=True)
    print(f"re-judged {n} done notes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
