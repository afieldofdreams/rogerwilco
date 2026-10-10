#!/usr/bin/env python3
"""Run the trials as headless Claude Code sessions (`claude -p`), unattended.

  run.py [--only SUBSTR] [--jobs N] [--redo] [--limit N] [--list]

Each trial is one session for the receiver: system.txt is its system prompt, prompt.txt its first turn, and the sender's
replies, produced by check.py, are later turns through --resume. The receiver has Read, Write and `python3 ...` in Bash and
nothing else. In arm B (and arm A in block 3, for the done note) a fresh one-turn session per judge call, with only the record
and the text to judge. Everything the models said and every usage record goes to <trial>/turns.json; the model ids as the API
returned them, the harness commit and the brief's hash go to <trial>/manifest.json.

Deviation from the protocol, recorded here and in the results: the runner is claude -p, not research/harness, because this
environment holds no provider API key; the judge is Claude Sonnet 5.5 for every receiver, not a second vendor.
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
    m = re.search(r"\b(READBACK|DONE|ASKED)\b", reply or "")
    return m.group(1) if m else "OTHER"


def judge(trial: Path, kind: str, turns: list) -> bool:
    prompt = K.judge_prompt(trial, kind)
    (trial / f"judge_{kind}.txt").write_text(prompt)
    r = claude(prompt, C.JUDGE_MODEL, str(uuid.uuid4()), False, trial, "You are a careful checker. You reply with one JSON object and nothing else.", tools="")
    turns.append({"who": f"judge-{kind}", **r})
    text = r.get("result", "")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return False
    try:
        verdict = json.loads(m.group(0))
    except ValueError:
        return False
    C.write_json(trial / f"judge_{kind}.json", verdict)
    return True


def run_trial(trial: Path) -> str:
    meta = C.read_json(trial / "meta.json")
    arm, model, block = meta["arm"], C.MODELS[meta["model"]], meta["block"]
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
            if block == 3 and (trial / "done.txt").exists():
                if not judge(trial, "done", turns):
                    status += "; judge gave no verdict on the done note"
            K.dn_check(trial)
        else:
            n = 1
            second = False
            while n < MAX_TURNS:
                w = word(r.get("result", ""))
                if w in ("DONE", "ASKED"):
                    break
                if w != "READBACK":
                    status = f"receiver said {r.get('result', r.get('error', ''))[:80]!r} at turn {n}"
                    break
                kind = "rb2" if second else "rb"
                if arm == "B":
                    if not (trial / ("readback2.txt" if second else "readback.txt")).exists():
                        status = f"no {'readback2' if second else 'readback'}.txt after READBACK"; break
                    if not judge(trial, kind, turns):
                        status = f"judge gave no verdict on {kind}"; break
                elif arm == "E":
                    if not (trial / ("readback2.txt" if second else "readback.txt")).exists():
                        status = f"no {'readback2' if second else 'readback'}.txt after READBACK"; break
                else:
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
            if arm == "B" and (trial / "done.txt").exists():
                if not judge(trial, "done", turns):
                    status += "; judge gave no verdict on the done note"
            K.dn_check(trial)
    finally:
        models_seen = sorted({m for t in turns if isinstance(t.get("models"), dict) for m in t["models"]})
        cost = sum(t.get("cost") or 0 for t in turns)
        C.write_json(trial / "turns.json", {"status": status, "turns": turns})
        C.write_json(trial / "manifest.json", {
            "id": meta["id"], "model_alias": meta["model"], "models_seen": models_seen, "judge_alias": C.JUDGE_MODEL,
            "runner": "claude -p " + CLI_VERSION, "harness_commit": HARNESS_COMMIT, "system_sha": C.sender_state(meta["id"])["system_sha"],
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cost_usd": round(cost, 4), "status": status,
        })
    return status


CLI_VERSION = ""
HARNESS_COMMIT = ""


def main(argv: list[str]) -> int:
    global CLI_VERSION, HARNESS_COMMIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring of the trial id")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    CLI_VERSION = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    HARNESS_COMMIT = git_short(C.ROOT)
    trials = [t for t in sorted(C.TRIALS.iterdir()) if a.only in t.name and (a.redo or not (t / "turns.json").exists())]
    if a.limit:
        trials = trials[:a.limit]
    if a.list:
        print("\n".join(t.name for t in trials)); return 0
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
            print(f"[{i}/{len(trials)} {round(time.time() - t0)}s] {t.name:34s} {status}", flush=True)
    print(f"done; {bad} trials need attention", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
