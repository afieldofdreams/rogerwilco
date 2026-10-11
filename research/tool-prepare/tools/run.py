#!/usr/bin/env python3
"""Run the trials as headless Claude Code sessions (`claude -p`), unattended.

  run.py [--only SUBSTR] [--jobs N] [--redo] [--reset] [--limit N] [--list] [--exclude SUBSTR]

Each trial is one session for the receiver: the brief is its system prompt, prompt.txt its first turn, and the sender's
replies, produced by check.py, are later turns through --resume. The receiver has Read, Write and python3, cat and ls in Bash
and nothing else. No judge: every arm in this study is checked by code. Everything the model said and every usage record goes
to <trial>/turns.json; the model ids as the API returned them, the harness commit and the brief's hash go to <trial>/manifest.json.

The reply words: READBACK (arms C, D, E and P, a readback written), PREPARED (arm Q, a transaction prepared with the tool),
DONE, ASKED. The sender's check runs after READBACK or PREPARED; its reply is the next turn. A second rejection holds the
handover without an act. In arm P the time the sender's confirmation is produced is recorded beside the tool's commit time,
so that a commit made before the confirmation is visible.
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
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import check as K  # noqa: E402

ALLOWED = "Read,Write,Bash(python3:*),Bash(cat:*),Bash(ls:*)"
TURN_TIMEOUT = 480
MAX_TURNS = 4
WAIT_WORD = {"C": "READBACK", "D": "READBACK", "E": "READBACK", "P": "READBACK", "Q": "PREPARED"}


def git_short(path: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(path), capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "?"


def claude(prompt: str, model: str, session: str, resume: bool, cwd: Path, system: str | None, tools: str = ALLOWED) -> dict:
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--allowedTools", tools,
           "--exclude-dynamic-system-prompt-sections", "--resume" if resume else "--session-id", session]
    if system is not None:
        cmd += ["--system-prompt", system]
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
                time.sleep(5); continue
            return {"error": "no json", "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:], "seconds": round(time.time() - t0)}
        if data.get("is_error") and attempt == 1:
            time.sleep(8); continue
        return {"result": (data.get("result") or "").strip(), "session": data.get("session_id"), "usage": data.get("usage"),
                "models": data.get("modelUsage"), "cost": data.get("total_cost_usd"), "seconds": round(time.time() - t0),
                "denials": data.get("permission_denials"), "is_error": data.get("is_error", False), "num_turns": data.get("num_turns")}
    return {"error": "gave up", "seconds": round(time.time() - t0)}


def word(reply: str) -> str:
    m = re.search(r"\b(READBACK|PREPARED|DONE|ASKED)\b", reply or "")
    return m.group(1) if m else "OTHER"


RECEIVER_FILES = ("rb.txt", "rb2.txt", "readback.txt", "readback2.txt", "dn.txt", "done.txt", "question.txt", "action.json", "email.json",
                  "prepared.json", "check_rb.json", "check_rb2.json", "check_dn.json", "grade.json", "turns.json", "manifest.json")
SENDER_FILES = ("actlog.json", "preplog.json", "confirm.json")


def reset_trial(trial: Path) -> None:
    """Back to the built state: receiver and sender outputs removed, the master restored, the tool's logs cleared."""
    for f in RECEIVER_FILES:
        if (trial / f).exists():
            (trial / f).unlink()
    for extra in trial.iterdir():
        if extra.is_file() and extra.name not in ("prompt.txt", "meta.json", "supplier_bank.json"):
            extra.unlink()
    master = C.SENDER / f"{trial.name}.master.json"
    if master.exists():
        (trial / "supplier_bank.json").write_text(master.read_text())
    for f in SENDER_FILES:
        p = C.SENDER / f"{trial.name}.{f}"
        if p.exists():
            p.unlink()


def run_trial(trial: Path) -> str:
    meta = C.read_json(trial / "meta.json")
    arm, model = meta["arm"], C.MODELS[meta["model"]]
    system = (C.ROOT / meta["brief"]).read_text()
    turns: list = []
    sid = str(uuid.uuid4())
    r = claude((trial / "prompt.txt").read_text(), model, sid, False, trial, system)
    turns.append({"who": "receiver", "turn": 1, **r})
    status = "ok"
    try:
        if "error" in r:
            status = f"receiver error: {r['error']}"
        elif arm == "A":
            if word(r.get("result", "")) not in ("DONE", "ASKED"):
                status = f"receiver said {r.get('result', '')[:80]!r}"
            K.dn_check(trial)
        else:
            wait = WAIT_WORD[arm]
            n = 1
            second = False
            while n < MAX_TURNS:
                w = word(r.get("result", ""))
                if w in ("DONE", "ASKED"):
                    break
                if w != wait:
                    status = f"receiver said {r.get('result', r.get('error', ''))[:80]!r} at turn {n}"
                    break
                kind = "rb2" if second else "rb"
                if arm == "E":
                    if not (trial / ("readback2.txt" if second else "readback.txt")).exists():
                        status = f"no {'readback2' if second else 'readback'}.txt after READBACK"; break
                elif arm in ("C", "D", "P"):
                    if not (trial / f"{kind}.txt").exists():
                        status = f"no {kind}.txt after READBACK"; break
                check = K.rb_check(trial, second=second)
                if not check["ok"] and second:
                    status = "held: rejected twice; stopped without acting"
                    break
                reply = "Message from scheduler:\n\n" + check["reply"]
                n += 1
                r = claude(reply, model, sid, True, trial, system)
                turns.append({"who": "receiver", "turn": n, "sent": check["reply"], **r})
                if "error" in r:
                    status = f"receiver error at turn {n}: {r['error']}"; break
                if not check["ok"]:
                    second = True
            else:
                status = "turn limit"
            K.dn_check(trial)
    finally:
        models_seen = sorted({m for t in turns if isinstance(t.get("models"), dict) for m in t["models"]})
        cost = sum(t.get("cost") or 0 for t in turns)
        C.write_json(trial / "turns.json", {"status": status, "turns": turns})
        C.write_json(trial / "manifest.json", {
            "id": meta["id"], "model_alias": meta["model"], "models_seen": models_seen,
            "runner": "claude -p " + CLI_VERSION, "harness_commit": HARNESS_COMMIT, "system_sha": C.sender_state(meta["id"])["system_sha"],
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cost_usd": round(cost, 4), "status": status,
        })
    return status


CLI_VERSION = ""
HARNESS_COMMIT = ""


def main(argv: list[str]) -> int:
    global CLI_VERSION, HARNESS_COMMIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring of the trial id; several, comma-separated, must all match")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--reset", action="store_true", help="with --redo: return the selected trials to their built state first")
    ap.add_argument("--exclude", default="", help="skip trials whose id ends with any of these, comma-separated (the pilot's -p, the Haiku 4.5 check's -w)")
    a = ap.parse_args(argv)
    CLI_VERSION = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    HARNESS_COMMIT = git_short(C.ROOT)
    needles = [x for x in a.only.split(",") if x]
    skip = [x for x in a.exclude.split(",") if x]
    trials = [t for t in sorted(C.TRIALS.iterdir()) if all(n in t.name for n in needles) and not any(t.name.endswith(x) for x in skip)
              and (a.redo or not (t / "turns.json").exists())]
    if a.limit:
        trials = trials[:a.limit]
    if a.list:
        print("\n".join(t.name for t in trials)); return 0
    if a.reset:
        for t in trials:
            reset_trial(t)
        print(f"reset {len(trials)} trials", flush=True)
    print(f"{len(trials)} trials, {a.jobs} at a time, cli {CLI_VERSION}, commit {HARNESS_COMMIT}", flush=True)
    bad = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futures = {ex.submit(run_trial, t): t for t in trials}
        for i, fut in enumerate(cf.as_completed(futures), 1):
            t = futures[fut]
            try:
                status = fut.result()
            except Exception as e:  # noqa: BLE001
                status = f"crashed: {type(e).__name__}: {e}"
            if status != "ok":
                bad += 1
            print(f"[{i}/{len(trials)} {round(time.time() - t0)}s] {t.name:40s} {status}", flush=True)
    print(f"done; {bad} trials need attention", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
