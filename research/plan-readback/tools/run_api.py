#!/usr/bin/env python3
"""Run trials against an API model through research/harness (llm.py): the protocol's intended runner, for receivers
that are not Claude. The key comes from the environment (OPENAI_API_KEY for openai:, see harness/llm.py) and is never
written anywhere; the receiver's subprocesses get a scrubbed environment.

  run_api.py --only SUBSTR[,SUBSTR] [--jobs N] [--redo] [--reset] [--limit N] [--list]

Selects trials whose meta.json model alias maps to a provider:name string (common.MODELS). The receiver has four
tools: read_file, write_file, shell (python3, cat, ls; one command, no shell) and done. Its brief is the system
prompt, prompt.txt the first user turn, and the sender's replies (check.py) later user turns in the same
conversation. The judge, where an arm needs one, is Claude Sonnet 5.5 through claude -p (run.judge), a different
vendor from these receivers. turns.json, manifest.json and transcript.json are written per trial.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import check as K  # noqa: E402
import run as R  # noqa: E402

HARNESS = C.REPO / "research" / "harness"
sys.path.insert(0, str(HARNESS))
import llm  # noqa: E402
import agent as H  # noqa: E402

MAX_TOOL_CALLS = 40
MAX_TURNS = 4
SHELL_TIMEOUT = 90
ALLOWED_HEADS = ("python3", "cat", "ls")

TOOLS = [
    H._tool("read_file", "Read a text file in your working folder, by absolute or relative path.", {"path": {"type": "string"}}, ["path"]),
    H._tool("write_file", "Create or overwrite a text file in your working folder, by absolute or relative path.",
            {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    H._tool("shell", "Run ONE command in your working folder and return its output. Allowed: python3 ..., cat <file>, ls [dir]. "
                     "No pipes, redirects, chaining or cd; the shell already runs in your working folder. 90 second timeout.",
            {"cmd": {"type": "string"}}, ["cmd"]),
    H._tool("done", "End your turn when you have written what your procedure asks and have nothing more to do until the scheduler replies.", {}, []),
]


class Sandbox:
    def __init__(self, trial: Path):
        self.trial = trial.resolve()
        self.denials: list = []

    def resolve(self, raw: str) -> Path:
        p = Path(raw)
        p = (p if p.is_absolute() else self.trial / p).resolve()
        if p != self.trial and self.trial not in p.parents:
            raise H.Refused(f"{raw} is outside your working folder")
        return p

    def read_file(self, a: dict) -> str:
        p = self.resolve(a.get("path", ""))
        if not p.exists():
            raise H.ToolError(f"{a.get('path')}: no such file")
        return H._clip(p.read_text(errors="replace"))

    def write_file(self, a: dict) -> str:
        p = self.resolve(a.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a.get("content", ""))
        return f"wrote {p.relative_to(self.trial)} ({len(a.get('content', ''))} chars)"

    def shell(self, a: dict) -> str:
        cmd = (a.get("cmd") or "").strip()
        if H._OPERATOR.search(cmd):
            raise H.Refused("no pipes, redirects or chaining: one command")
        try:
            argv = shlex.split(cmd)
        except ValueError as e:
            raise H.ToolError(f"cannot parse the command: {e}")
        if not argv or argv[0] not in ALLOWED_HEADS:
            raise H.Refused(f"command not allowed: {argv[0] if argv else ''}. Allowed: python3, cat, ls")
        if argv[0] in ("cat", "ls"):
            for t in argv[1:]:
                if not t.startswith("-"):
                    self.resolve(t)
        try:
            proc = subprocess.run(argv, cwd=str(self.trial), env=H.child_env(), capture_output=True, text=True, timeout=SHELL_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise H.ToolError(f"timed out after {SHELL_TIMEOUT}s")
        out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
        if proc.returncode:
            out += f"\n[exit {proc.returncode}]"
        return H._clip(out) or "(no output)"

    def call(self, name: str, args) -> tuple[str, bool]:
        fn = {"read_file": self.read_file, "write_file": self.write_file, "shell": self.shell}.get(name)
        if name == "done":
            return "ok", False
        if fn is None:
            return f"error: unknown tool {name!r}", True
        try:
            return fn(args or {}), False
        except H.Refused as e:
            self.denials.append({"tool_name": name, "tool_input": args, "reason": str(e)})
            return f"refused: {e}", True
        except H.ToolError as e:
            return f"error: {e}", True
        except Exception as e:  # noqa: BLE001
            return f"error: {type(e).__name__}: {e}", True


def usage_claude_shape(usages: list[dict]) -> dict:
    tot = H.sum_usage(usages)
    cached = tot["cached_tokens"] or 0
    return {"input_tokens": max(0, (tot["prompt_tokens"] or 0) - cached), "cache_read_input_tokens": cached,
            "cache_creation_input_tokens": tot.get("cache_write_tokens") or 0, "output_tokens": tot["completion_tokens"] or 0,
            "reasoning_tokens": tot.get("reasoning_tokens") or 0, "estimated": tot.get("estimated", False)}


def receiver_turn(messages: list[dict], model: str, box: Sandbox, prompt: str) -> dict:
    """One turn: a user message, then model calls and tool calls until the model replies with text or calls done."""
    messages.append({"role": "user", "content": prompt})
    usages = []; calls = 0; text = ""; t0 = time.time(); ended = "text"
    while True:
        H.cap_context(messages)
        try:
            assistant, tool_calls, usage = llm.chat(messages, TOOLS, model)
        except llm.LLMError as e:
            return {"error": f"model error: {e}", "usage": usage_claude_shape(usages), "calls": calls, "seconds": round(time.time() - t0)}
        usages.append(usage)
        messages.append(assistant)
        if assistant.get("content"):
            text = assistant["content"] if isinstance(assistant["content"], str) else llm._text(assistant["content"])
        if not tool_calls:
            break
        stop = False
        for tc in tool_calls:
            calls += 1
            if tc.get("error"):
                result = f"error: {tc['error']}"
            else:
                result, _ = box.call(tc["name"], tc.get("arguments"))
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            if tc.get("name") == "done":
                stop = True
        if stop:
            ended = "done"
            break
        if calls >= MAX_TOOL_CALLS:
            ended = "tool limit"
            break
    inferred = None
    if not text.strip():
        # the model ended its turn through the done tool without the reply word: infer it from what it wrote
        t = box.trial
        if (t / "question.txt").exists():
            inferred = "ASKED"
        elif (t / "action.json").exists() or (t / "dn.txt").exists() or (t / "done.txt").exists():
            inferred = "DONE"
        elif any((t / f).exists() for f in ("rb.txt", "rb2.txt", "readback.txt", "readback2.txt")):
            inferred = "READBACK"
        if inferred:
            text = inferred
    models = {}
    for u in usages:
        mid = u.get("response_model") or u.get("model")
        m = models.setdefault(mid, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
        m["calls"] += 1; m["prompt_tokens"] += u.get("prompt_tokens") or 0; m["completion_tokens"] += u.get("completion_tokens") or 0
    return {"result": text.strip(), "inferred_reply": inferred, "usage": usage_claude_shape(usages), "models": models, "cost": None, "calls": calls,
            "ended": ended, "seconds": round(time.time() - t0), "denials": list(box.denials), "is_error": False}


def run_trial(trial: Path) -> str:
    meta = C.read_json(trial / "meta.json")
    arm, block = meta["arm"], meta["block"]
    model = C.MODELS[meta["model"]]
    system = (C.ROOT / meta["brief"]).read_text()
    box = Sandbox(trial)
    messages = [{"role": "system", "content": system}]
    turns: list = []
    status = "ok"
    r = receiver_turn(messages, model, box, (trial / "prompt.txt").read_text())
    turns.append({"who": "receiver", "turn": 1, **r})
    try:
        if "error" in r:
            status = f"receiver error: {r['error'][:120]}"
        elif arm in ("A", "F"):
            if R.word(r.get("result", "")) not in ("DONE", "ASKED"):
                status = f"receiver said {r.get('result', '')[:80]!r}"
            if block == 3 and (trial / "done.txt").exists():
                if not R.judge(trial, "done", turns):
                    status += "; judge gave no verdict on the done note"
            K.dn_check(trial)
        else:
            n = 1; second = False
            while n < MAX_TURNS:
                w = R.word(r.get("result", ""))
                if w in ("DONE", "ASKED"):
                    break
                if w != "READBACK":
                    status = f"receiver said {r.get('result', r.get('error', ''))[:80]!r} at turn {n}"
                    break
                kind = "rb2" if second else "rb"
                if arm in ("B", "E"):
                    if not (trial / ("readback2.txt" if second else "readback.txt")).exists():
                        status = f"no {'readback2' if second else 'readback'}.txt after READBACK"; break
                    if arm == "B" and not R.judge(trial, kind, turns):
                        status = f"judge gave no verdict on {kind}"; break
                else:
                    if not (trial / f"{kind}.txt").exists():
                        status = f"no {kind}.txt after READBACK"; break
                check = K.rb_check(trial, second=second)
                if not check["ok"] and second:
                    status = "held: rejected twice; stopped without acting"; break
                n += 1
                r = receiver_turn(messages, model, box, "Message from scheduler:\n\n" + check["reply"])
                turns.append({"who": "receiver", "turn": n, "sent": check["reply"], **r})
                if "error" in r:
                    status = f"receiver error at turn {n}: {r['error'][:120]}"; break
                if not check["ok"]:
                    second = True
            else:
                status = "turn limit"
            if arm == "B" and (trial / "done.txt").exists():
                if not R.judge(trial, "done", turns):
                    status += "; judge gave no verdict on the done note"
            K.dn_check(trial)
    finally:
        models_seen = sorted({m for t in turns if isinstance(t.get("models"), dict) for m in t["models"]})
        C.write_json(trial / "turns.json", {"status": status, "turns": turns})
        C.write_json(trial / "transcript.json", messages)
        C.write_json(trial / "manifest.json", {
            "id": meta["id"], "model_alias": meta["model"], "model": model, "endpoint": llm.endpoint_host(model), "models_seen": models_seen,
            "judge_alias": C.JUDGE_MODEL, "runner": "research/harness llm.py via run_api.py", "harness_commit": R.git_short(C.ROOT),
            "system_sha": C.sender_state(meta["id"])["system_sha"], "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cost_usd": None, "status": status,
        })
    return status


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=""); ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--redo", action="store_true")
    ap.add_argument("--reset", action="store_true"); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    needles = [x for x in a.only.split(",") if x]
    trials = []
    for t in sorted(C.TRIALS.iterdir()):
        if not all(n in t.name for n in needles):
            continue
        meta = C.read_json(t / "meta.json")
        if ":" not in C.MODELS.get(meta["model"], ""):
            continue
        if a.redo or not (t / "turns.json").exists():
            trials.append(t)
    if a.limit:
        trials = trials[:a.limit]
    if a.list:
        print("\n".join(t.name for t in trials)); return 0
    if a.reset:
        for t in trials:
            R.reset_trial(t)
        print(f"reset {len(trials)} trials", flush=True)
    for m in sorted({C.MODELS[C.read_json(t / "meta.json")["model"]] for t in trials}):
        llm.preflight(m)
    print(f"{len(trials)} trials, {a.jobs} at a time", flush=True)
    bad = 0; t0 = time.time()
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
            print(f"[{i}/{len(trials)} {round(time.time() - t0)}s] {t.name:36s} {status}", flush=True)
    print(f"done; {bad} trials need attention", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
