#!/usr/bin/env python3
"""Runs the trials as headless Claude Code sessions (`claude -p`), unattended.

  run.py [--only PATTERN] [--jobs N] [--redo]

Each trial is one session for the receiver (its prompt.txt is the first turn; the scheduler's replies, produced by
harness.py, are later turns through --resume), plus, in arm B, a fresh one-turn session per judge call. The receiver
has Read, Write and `python3 ...` in Bash, nothing else. Everything the models said and every usage record is written
to <trial>/turns.json. A trial that already has turns.json is skipped unless --redo.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402

ALLOWED = "Read,Write,Edit,Bash"
TURN_TIMEOUT = 420
MAX_TURNS = 4


def claude(prompt: str, model: str, session: str, resume: bool, cwd: Path) -> dict:
    cmd = ["claude", "-p", "--model", model, "--allowedTools", ALLOWED, "--output-format", "json",
           "--resume" if resume else "--session-id", session]
    t0 = time.time()
    for attempt in (1, 2):
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=TURN_TIMEOUT, cwd=str(cwd))
        except subprocess.TimeoutExpired:
            if attempt == 1:
                continue
            return {"error": "timeout", "seconds": round(time.time() - t0)}
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            if attempt == 1:
                time.sleep(5)
                continue
            return {"error": "no json", "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
        if data.get("is_error") and attempt == 1:
            time.sleep(5)
            continue
        return {"result": (data.get("result") or "").strip(), "session": data.get("session_id"), "usage": data.get("usage"),
                "models": data.get("modelUsage"), "cost": data.get("total_cost_usd"), "seconds": round(time.time() - t0),
                "denials": data.get("permission_denials"), "is_error": data.get("is_error", False)}
    return {"error": "gave up"}


def word(reply: str) -> str:
    m = re.search(r"\b(READBACK|DONE|JUDGED|ASKED)\b", reply or "")
    return m.group(1) if m else "OTHER"


def judge(trial: Path, kind: str, turns: list) -> bool:
    path = H.TRIALS / trial.name / f"judge_{kind}.txt"
    path.write_text(H.judge_prompt(trial, kind))
    r = claude(path.read_text(), "sonnet", str(uuid.uuid4()), False, trial)
    turns.append({"who": f"judge-{kind}", **r})
    return (trial / f"judge_{kind}.json").exists()


def run_trial(trial: Path) -> str:
    meta = json.loads((trial / "meta.json").read_text())
    arm, model = meta["arm"], meta["model"]
    turns: list = []
    sid = str(uuid.uuid4())
    r = claude((trial / "prompt.txt").read_text(), model, sid, False, trial)
    turns.append({"who": "receiver", "turn": 1, **r})
    status = "ok"
    try:
        if arm == "A":
            if word(r.get("result", "")) not in ("DONE", "ASKED"):
                status = f"receiver said {r.get('result', r.get('error'))!r}"
        else:
            n = 1
            second = False
            while n < MAX_TURNS:
                w = word(r.get("result", ""))
                if w in ("DONE", "ASKED"):
                    break
                if w != "READBACK":
                    status = f"receiver said {r.get('result', r.get('error'))!r} at turn {n}"
                    break
                kind = "rb2" if second else "rb"
                if arm == "B":
                    if not (trial / ("readback2.txt" if second else "readback.txt")).exists():
                        status = f"no {'readback2' if second else 'readback'}.txt after READBACK"
                        break
                    if not judge(trial, kind, turns):
                        status = f"judge wrote no judge_{kind}.json"
                        break
                else:
                    if not (trial / f"{kind}.txt").exists():
                        status = f"no {kind}.txt after READBACK"
                        break
                check = H.rb_check(trial, second=second)
                if not check["ok"] and second:
                    status = "rejected twice; stopped without acting"      # one correction cycle is allowed
                    break
                reply = "Message from scheduler:\n\n" + check["reply"]
                n += 1
                r = claude(reply, model, sid, True, trial)
                turns.append({"who": "receiver", "turn": n, "sent": check["reply"], **r})
                if not check["ok"]:
                    second = True
            else:
                status = "turn limit"
            if arm == "B" and (trial / "done.txt").exists():
                if not judge(trial, "done", turns):
                    status += "; judge wrote no judge_done.json"
    finally:
        (trial / "turns.json").write_text(json.dumps({"status": status, "turns": turns}, indent=1))
    return status


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring of the trial id")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args(argv)
    trials = [t for t in sorted(H.TRIALS.iterdir()) if a.only in t.name and (a.redo or not (t / "turns.json").exists())]
    print(f"{len(trials)} trials, {a.jobs} at a time", flush=True)
    bad = 0
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futures = {ex.submit(run_trial, t): t for t in trials}
        for fut in cf.as_completed(futures):
            t = futures[fut]
            try:
                status = fut.result()
            except Exception as e:  # noqa: BLE001
                status = f"crashed: {type(e).__name__}: {e}"
            if status != "ok":
                bad += 1
            print(f"{t.name:24s} {status}", flush=True)
    print(f"done; {bad} trials need attention", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
