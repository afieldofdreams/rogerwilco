#!/usr/bin/env python3
"""orchestrate.py: run the month-end multi-agent scenario unattended against any chat model with tool calling.

    python3 orchestrate.py --run runs/L4 --model openrouter:openai/gpt-5.6 [--principal-model MODEL]
    python3 orchestrate.py --build L 4 [--scenario 2] --model anthropic:claude-sonnet-4-6
    python3 orchestrate.py --grid "A,D,L" --runs 3 --model openai:gpt-5.6

Run it from research/month-end (so `runs/L4` resolves) or give absolute paths. See README.md.

What it does, mirroring what the Claude session did by hand. Each round: read `mail.py pending`; every agent
(extractor, reconciler, scheduler, auditor) with unread mail gets one turn, the agent being spawned on its first
mail; the four run concurrently in threads. Then the scripted principal (tools/principal.py, imported by path,
never copied) answers what was sent to `human`. The run stops when no agent has unread mail and the auditor has
written to the human ("complete"), when nothing is left to wake without the auditor having reported ("stalled"),
after 16 rounds ("max_rounds"), or on a provider error ("error"). It then writes rounds.json and usage.json and
calls tools/grade.py.

Files written into the run directory: rounds.json, usage.json, grade.json (by grade.py), harness/config.json,
harness/principal.json and harness/transcripts/<agent>.jsonl (every message of every agent's conversation).
run.json gets one added key, "harness", naming the model. Nothing else in the repository is touched, and no API
key is ever written anywhere.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent as agent_mod  # noqa: E402
import llm  # noqa: E402

VERSION = "0.1"
AGENTS = ["extractor", "reconciler", "scheduler", "auditor"]
ARMS = "APDLR"
MAX_ROUNDS = 16
NOTE_RE = re.compile(r"\s*\(no matching option[^)]*\)\s*$")

PRINCIPAL_SYSTEM = """You are the **principal**, the Finance Director of Harbourline Studio Ltd, answering questions from your accounts-payable agents during the September 2026 month-end supplier payment run. You decide only what the payments policy reserves for you; the agents decide everything else.

Policy:
{policy}

Your decisions on the matters that are known to come up (use them when a question is about the same matter):
{script}

Each message shows you one question, a rogerwilco AQ line. Answer with a single JSON object and nothing else:
{{"val": "<exactly one of the options after opts=>", "tail": "<one or two sentences for the agent, 250 characters at most>"}}
If the policy leaves the matter to the agents, pick the most conservative listed option (HOLD or DECLINE if present) and say in the tail that the agents decide it under the policy.
"""


class RunError(SystemExit):
    """A problem with how the run was set up; the message is shown and nothing more."""


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def month_end_dir(arg: str | None = None) -> Path:
    return Path(arg or os.environ.get("RW_MONTH_END") or HERE.parent / "month-end").resolve()


def write_json(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def read_log(run_dir: Path) -> list[dict]:
    p = run_dir / "mail" / "log.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def fmt_tokens(n) -> str:
    if n is None:
        return "-"
    return f"{n / 1000:.1f}k" if n >= 1000 else str(int(n))


_PRINCIPAL_MODULES: dict = {}


def load_principal(tools_dir: Path):
    """tools/principal.py imported by path (not copied), once per tools directory."""
    path = str((tools_dir / "principal.py").resolve())
    if path not in _PRINCIPAL_MODULES:
        if not Path(path).is_file():
            raise RunError(f"{path} not found: run from research/month-end or set --month-end / RW_MONTH_END")
        spec = importlib.util.spec_from_file_location("rw_month_end_principal", path)
        mod = importlib.util.module_from_spec(spec)
        keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # do not write __pycache__ next to the tool
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.dont_write_bytecode = keep
        _PRINCIPAL_MODULES[path] = mod
    return _PRINCIPAL_MODULES[path]


# ---------------------------------------------------------------- the mail channel

class MailBus:
    """The orchestrator's side of mail.py. One lock per run, shared with every agent's shell tool: mail.py's `read`
    rewrites the whole log and `send` numbers messages by reading it, so calls must not overlap."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.lock = threading.Lock()
        self._n = 0

    def _run(self, args: list[str], timeout: float = 120) -> tuple[int, str]:
        with self.lock:
            p = subprocess.run([sys.executable, "mail.py", *args], cwd=self.run_dir, env=agent_mod.child_env(),
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")

    def pending(self) -> dict:
        rc, out = self._run(["pending"])
        if rc != 0:
            raise RunError(f"mail.py pending failed: {out.strip()[:300]}")
        try:
            return json.loads(out.strip() or "{}")
        except ValueError:
            raise RunError(f"mail.py pending printed something unexpected: {out.strip()[:300]}") from None

    def send(self, frm: str, to: str, text: str) -> tuple[int, str]:
        if text.startswith("-"):  # argparse would take the body for an option; a file carries it exactly
            self._n += 1
            outbox = self.run_dir / "harness" / "outbox"
            outbox.mkdir(parents=True, exist_ok=True)
            f = outbox / f"{self._n:03d}.txt"
            f.write_text(text)
            return self._run(["send", "--from", frm, "--to", to, "--file", str(f)])
        return self._run(["send", "--from", frm, "--to", to, "-m", text])

    def mark_read(self, me: str) -> None:
        self._run(["read", "--me", me])


# ---------------------------------------------------------------- the principal

class LLMPrincipal:
    """Only for questions the scripted principal cannot answer (arms L and R, off-script AQ lines): a model picks
    one of the offered options. The script's own decisions and the policy are in its prompt."""

    def __init__(self, model: str, run_dir: Path, principal_mod, chat_fn=None):
        script = principal_mod.truth_for(run_dir)["principal_script"]
        policy = (run_dir / "data" / "policy.md").read_text().strip()
        self.model = model
        self.principal = principal_mod
        self.chat = chat_fn or llm.chat
        self.messages: list[dict] = [{"role": "system", "content": PRINCIPAL_SYSTEM.format(
            policy=policy, script=json.dumps(script, indent=1))}]
        self.usages: list[dict] = []

    @staticmethod
    def _parse(text: str, opts: list[str]) -> tuple[str | None, str]:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None, ""
        try:
            obj = json.loads(m.group(0))
        except ValueError:
            return None, ""
        val = str(obj.get("val", "")).strip().upper()
        by_upper = {o.upper(): o for o in opts}
        tail = " ".join(str(obj.get("tail", "")).split())[:280]
        return by_upper.get(val), tail

    def answer(self, an_line: str, body: str, sender: str) -> str | None:
        """an_line is the scripted principal's flagged reply; it supplies the line id (human-<n>, already unique in
        this batch) and the id of the question being answered."""
        m = re.search(r"\bre=(\S+)", an_line)
        parts = an_line.split()
        if not m or len(parts) < 3 or not re.fullmatch(r"human-\d+", parts[2]):
            return None
        an_id, aq_id = parts[2], m.group(1)
        aq = next((l for l in body.splitlines() if l.startswith("RW1 AQ") and l.split()[2:3] == [aq_id]), None)
        opts = self.principal.opts_of(aq) if aq else []
        if not opts:
            return None
        item = re.search(r"\bitem=(\S+)", aq)
        self.messages.append({"role": "user", "content": f"Question from {sender}:\n{aq}\n\nOptions: {', '.join(opts)}"})
        for _ in range(2):
            assistant, _calls, usage = self.chat(self.messages, [], self.model)
            self.usages.append(usage)
            self.messages.append({"role": "assistant", "content": assistant.get("content") or ""})
            val, tail = self._parse(assistant.get("content") or "", opts)
            if val:
                return (f"RW1 AN {an_id} re={aq_id} from=human to={sender} p=pay"
                        + (f" item={item.group(1)}" if item else "") + f" val={val} // {tail or 'Decided under the policy.'}")
            self.messages.append({"role": "user", "content": "That was not valid. Answer with JSON whose val is exactly "
                                                             f"one of: {', '.join(opts)}."})
        return None


def principal_step(run: "Run", rnd: int) -> dict:
    """Answer everything addressed to `human`. propose() is called exactly once per batch (the scenario-2
    principal keeps state), then human's mail is marked read."""
    props = run.principal.propose(run.run_dir)
    info = {"read": len(props), "sent": 0, "rejected": 0, "unanswered": 0, "llm_answered": 0}
    for p in props:
        entry = {"round": rnd, "seq": p["seq"], "from": p["from"], "events": p["events"],
                 "asks_decision": p["asks_decision"], "sent": None, "unanswered": []}
        text = p.get("proposed")
        if text:
            out = text
            if run.arm in ("L", "R"):
                answers, flagged = [], []
                for line in text.split("\n"):
                    (flagged if NOTE_RE.search(line) else answers).append(NOTE_RE.sub("", line))
                for line in flagged:
                    ans = run.llm_principal.answer(line, p["body"], p["from"]) if run.llm_principal else None
                    if ans:
                        answers.append(ans)
                        info["llm_answered"] += 1
                    else:
                        entry["unanswered"].append(line[:300])
                        info["unanswered"] += 1
                out = "\n".join(answers)
            if out.strip():
                rc, msg = run.bus.send("human", p["from"], out)
                if rc == 0:
                    info["sent"] += 1
                    entry["sent"] = out
                else:
                    info["rejected"] += 1
                    entry["rejected"] = msg.strip()[:500]
                    run.log(f"principal reply to {p['from']} was rejected by mail.py: {msg.strip()[:200]}")
        run.principal_log.append(entry)
    run.bus.mark_read("human")
    return info


# ---------------------------------------------------------------- one run

class Run:
    """Everything one run needs, so the helpers stay small."""

    def __init__(self, run_dir: Path, model: str, principal_model: str | None, month_end: Path, chat_fn, log):
        self.run_dir = run_dir
        self.name = run_dir.name
        self.model = model
        self.principal_model = principal_model
        self.month_end = month_end
        self.tools_dir = month_end / "tools"
        self.chat_fn = chat_fn
        self.log = log
        self.cfg = json.loads((run_dir / "run.json").read_text())
        self.arm = self.cfg["arm"]
        self.bus = MailBus(run_dir)
        self.principal = load_principal(self.tools_dir)
        self.llm_principal: LLMPrincipal | None = None
        self.principal_log: list[dict] = []
        self.agents: dict[str, agent_mod.Agent] = {}
        self.turns: dict[str, list[dict]] = {a: [] for a in AGENTS}
        self.per_round: list[dict] = []


class _StopFlag:
    """A run's own stop flag, which also reads the grid's shared `halt` flag (Ctrl-C while --jobs runs are in flight)."""

    def __init__(self, halt: threading.Event | None = None):
        self._own = threading.Event()
        self._halt = halt

    def set(self) -> None:
        self._own.set()

    def is_set(self) -> bool:
        return self._own.is_set() or (self._halt is not None and self._halt.is_set())


class Budget:
    """A ceiling on prompt tokens (cached ones included), checked after every model call, the principal model's too.
    Passing it raises the run's stop flag: calls already in flight finish (at most one per agent), no new one starts."""

    def __init__(self, limit: int | None, flag: _StopFlag):
        self.limit = limit
        self.flag = flag
        self.used = 0
        self.hit = False
        self._lock = threading.Lock()

    def wrap(self, fn):
        def counted(messages, tools, model):
            out = fn(messages, tools, model)
            with self._lock:
                self.used += out[2].get("prompt_tokens") or 0
                if self.limit and self.used > self.limit and not self.hit:
                    self.hit = True
                    self.flag.set()
            return out
        return counted


def check_fresh(run_dir: Path) -> None:
    if (run_dir / "rounds.json").exists() or (run_dir / "harness").exists():
        raise RunError(f"{run_dir} has already been run by the harness; build a fresh run directory (--build)")
    recs = read_log(run_dir)
    if len(recs) != 1 or recs[0].get("kind") != "msg" or recs[0].get("from") != "human":
        raise RunError(f"{run_dir} has mail activity beyond the kickoff message; the harness needs a freshly built run directory")


def auditor_reported(run_dir: Path) -> bool:
    return any(r.get("kind") == "msg" and r.get("from") == "auditor" and r.get("to") == "human" for r in read_log(run_dir))


def _totals(turns: list[dict]) -> dict:
    t = agent_mod.sum_usage(turns)
    t.update({"turns": len(turns), "calls": sum(x.get("calls", 0) for x in turns),
              "tool_calls": sum(x.get("tool_calls", 0) for x in turns), "tool_errors": sum(x.get("tool_errors", 0) for x in turns),
              "refused": sum(x.get("refused", 0) for x in turns), "seconds": round(sum(x.get("seconds") or 0 for x in turns), 1)})
    return t


def usage_doc(run: Run) -> dict:
    agents = {}
    for role in AGENTS:
        turns = [{k: v for k, v in t.items() if k != "traceback"} for t in run.turns[role]]
        if turns:
            agents[role] = {"turns": turns, "total": _totals(turns)}
    principal = None
    if run.llm_principal:
        principal = agent_mod.sum_usage(run.llm_principal.usages)
        principal["calls"] = len(run.llm_principal.usages)
    every = [t for role in AGENTS for t in run.turns[role]] + (run.llm_principal.usages if run.llm_principal else [])
    total = agent_mod.sum_usage(every)
    total["calls"] = sum(t.get("calls", 1) for t in every)
    return {"model": run.model, "principal_model": run.principal_model, "agents": agents, "principal": principal, "total": total}


def write_state(run: Run, state: dict) -> None:
    write_json(run.run_dir / "rounds.json", state)
    write_json(run.run_dir / "usage.json", usage_doc(run))
    write_json(run.run_dir / "harness" / "principal.json", run.principal_log)


_TOKEN_COUNTER: list[str] = []


def token_counter() -> str:
    """How mail.py counts the tokens it logs (the study's headline numbers) inside the agents' scrubbed environment:
    o200k via tiktoken when the encoding loads there, else characters / 4. The scrubbed environment has no proxy
    settings, so an encoding that is not already cached cannot be downloaded there."""
    if not _TOKEN_COUNTER:
        try:
            p = subprocess.run([sys.executable, "-c", "import tiktoken; tiktoken.get_encoding('o200k_base')"],
                               capture_output=True, env=agent_mod.child_env(), stdin=subprocess.DEVNULL, timeout=60)
            _TOKEN_COUNTER.append("tiktoken o200k_base" if p.returncode == 0
                                  else "chars/4 (tiktoken or its o200k_base encoding is not usable in the agents' environment)")
        except (OSError, subprocess.SubprocessError):
            _TOKEN_COUNTER.append("unknown (the check timed out)")
    return _TOKEN_COUNTER[0]


_SECRETISH = re.compile(r"key|secret|auth|password|bearer|credential|(?<![a-z])token(?!s)", re.I)


def scrub(obj):
    """A copy of a JSON value with every secret-looking key's value replaced, at any depth (max_tokens is not one)."""
    if isinstance(obj, dict):
        return {k: ("[redacted]" if _SECRETISH.search(str(k)) else scrub(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


def _config(run: Run, max_rounds: int, allow_python_c: bool, max_prompt_tokens: int | None) -> dict:
    extra = {}
    try:
        extra = scrub(json.loads(os.environ.get("RW_EXTRA_BODY") or "{}"))
    except ValueError:
        pass
    commit = "unknown"
    try:
        p = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10)
        commit = p.stdout.strip() or commit
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "harness_version": VERSION, "harness_commit": commit, "python": sys.version.split()[0],
        "model": run.model, "principal_model": run.principal_model, "endpoint_host": llm.endpoint_host(run.model),
        "token_counter": token_counter(),
        "env": {k: os.environ.get(k) for k in ("RW_TIMEOUT", "RW_RETRIES", "RW_MAX_TOKENS", "RW_TEMPERATURE", "RW_ANTHROPIC_CACHE")
                if os.environ.get(k)},
        "extra_body": extra,
        "limits": {"max_rounds": max_rounds, "max_tool_calls": agent_mod.MAX_TOOL_CALLS, "context_chars": agent_mod.CONTEXT_CHARS,
                   "keep_last": agent_mod.KEEP_LAST, "shell_timeout_s": agent_mod.SHELL_TIMEOUT,
                   "max_prompt_tokens": max_prompt_tokens},
        "allow_python_c": allow_python_c,
    }


def run_one(run_dir, model: str, *, principal_model: str | None = None, max_rounds: int = MAX_ROUNDS,
            max_prompt_tokens: int | None = None, grade: bool = True, allow_python_c: bool = True,
            month_end: str | None = None, chat_fn=None, log=None, halt: threading.Event | None = None) -> dict:
    """Run one prepared run directory to the end. Returns a summary dict (also what the grid prints). If `halt` is
    set (by the grid, on Ctrl-C) the run stops at its next model call, is recorded as "interrupted" and raises
    KeyboardInterrupt, exactly as if it had been interrupted itself."""
    run_dir = Path(run_dir).resolve()
    if not (run_dir / "run.json").is_file():
        raise RunError(f"{run_dir} is not a run directory (no run.json)")
    name = run_dir.name
    log = log or (lambda m: print(f"[{name}] {m}", flush=True))
    check_fresh(run_dir)
    if chat_fn is None:
        try:
            llm.preflight(model)
            if principal_model:
                llm.preflight(principal_model)
        except llm.LLMError as e:
            raise RunError(f"cannot use {model}: {e}") from None
    stop_event = _StopFlag(halt)
    budget = Budget(max_prompt_tokens, stop_event)
    counted = budget.wrap(chat_fn or llm.chat)
    run = Run(run_dir, model, principal_model, month_end_dir(month_end), counted, log)
    if principal_model:
        run.llm_principal = LLMPrincipal(principal_model, run_dir, run.principal, counted)

    (run_dir / "harness").mkdir()
    config = _config(run, max_rounds, allow_python_c, max_prompt_tokens)
    write_json(run_dir / "harness" / "config.json", config)
    if not config["token_counter"].startswith("tiktoken"):
        log(f"WARNING: token counts in mail/log.jsonl will be {config['token_counter']}; cache the encoding first "
            f"(python3 -c \"import tiktoken; tiktoken.get_encoding('o200k_base')\") if you compare with runs that used tiktoken")
    cfg = dict(run.cfg)
    cfg["harness"] = {"model": model, "principal_model": principal_model, "version": VERSION, "started": utc_now()}
    write_json(run_dir / "run.json", cfg)

    t_start = time.time()
    started = utc_now()
    state = {"rounds": 0, "stop": "running", "model": model, "principal_model": principal_model, "arm": run.arm,
             "max_rounds": max_rounds, "started": started, "finished": None, "seconds": None,
             "auditor_reported": False, "unread_at_stop": {}, "principal_unanswered": [], "error": None, "per_round": run.per_round}
    log(f"arm {run.arm} model {model}" + (f" principal {principal_model}" if principal_model else "") + f" up to {max_rounds} rounds")
    stop = None
    error = None
    rounds = 0
    try:
        while True:
            pending = run.bus.pending()
            ready = [a for a in AGENTS if pending.get(a)]
            human_waiting = bool(pending.get("human"))
            if not ready and not human_waiting:
                stop = "complete" if auditor_reported(run_dir) else "stalled"
                break
            if stop_event.is_set():
                stop = "budget" if budget.hit else "interrupted"
                break
            if rounds >= max_rounds:
                stop = "max_rounds"
                break
            rounds += 1
            t_round = time.time()
            rec = {"round": rounds, "agents": ready, "turns": {}, "principal": None, "seconds": None}
            for role in ready:
                if role not in run.agents:
                    log(f"spawn {role}")
                    run.agents[role] = agent_mod.Agent(
                        role, run_dir, model, mail_lock=run.bus.lock, chat_fn=counted, allow_python_c=allow_python_c,
                        transcript=run_dir / "harness" / "transcripts" / f"{role}.jsonl", stop=stop_event)
            errors = []
            if ready:
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(ready)) as pool:
                    futs = {pool.submit(run.agents[r].turn, rounds): r for r in ready}
                    try:
                        for fut in concurrent.futures.as_completed(futs):
                            role, turn = futs[fut], fut.result()
                            run.turns[role].append(turn)
                            rec["turns"][role] = {k: turn.get(k) for k in ("turn", "calls", "tool_calls", "ended_by", "seconds")}
                            log(f"round {rounds} {role}: {turn['calls']} calls, {fmt_tokens(turn['prompt_tokens'])} in, "
                                f"{fmt_tokens(turn['completion_tokens'])} out, {turn['tool_calls']} tool calls, "
                                f"ended by {turn['ended_by']}, {turn['seconds']:.0f}s")
                            if turn["error"]:
                                errors.append(f"{role} turn {turn['turn']}: {turn['error']}")
                    except KeyboardInterrupt:
                        stop_event.set()
                        raise
            if errors:
                error = "; ".join(errors)
                stop = "error"
                rec["seconds"] = round(time.time() - t_round, 1)
                run.per_round.append(rec)
                break
            try:
                rec["principal"] = principal_step(run, rounds)
            except llm.LLMError as e:
                error, stop = f"principal model: {e}", "error"
                run.per_round.append(rec)
                break
            pi = rec["principal"]
            if pi["read"]:
                log(f"round {rounds} principal: read {pi['read']}, sent {pi['sent']}"
                    + (f", model answered {pi['llm_answered']}" if pi["llm_answered"] else "")
                    + (f", UNANSWERED {pi['unanswered']}" if pi["unanswered"] else "")
                    + (f", REJECTED {pi['rejected']}" if pi["rejected"] else ""))
            rec["seconds"] = round(time.time() - t_round, 1)
            run.per_round.append(rec)
            state.update({"rounds": rounds, "auditor_reported": auditor_reported(run_dir)})
            write_state(run, state)
    except KeyboardInterrupt:
        stop_event.set()
        stop = "interrupted"
    except (Exception, SystemExit) as e:  # noqa: BLE001  (RunError is a SystemExit)
        stop, error = "error", f"{type(e).__name__}: {e}"
    finally:
        stop_event.set()
        try:
            unread = run.bus.pending()
        except (SystemExit, Exception):  # noqa: BLE001
            unread = {}
        unanswered = [{"round": e["round"], "seq": e["seq"], "from": e["from"], "lines": e["unanswered"]}
                      for e in run.principal_log if e["unanswered"]]
        state.update({"rounds": rounds, "stop": stop or "error", "finished": utc_now(), "seconds": round(time.time() - t_start, 1),
                      "auditor_reported": auditor_reported(run_dir), "unread_at_stop": unread,
                      "principal_unanswered": unanswered, "error": error})
        write_state(run, state)

    total = usage_doc(run)["total"]
    result = {"run": name, "path": str(run_dir), "arm": run.arm, "model": model, "stop": state["stop"], "rounds": rounds,
              "seconds": state["seconds"], "prompt_tokens": total["prompt_tokens"], "completion_tokens": total["completion_tokens"],
              "cached_tokens": total["cached_tokens"] if total["cached_reported"] else None, "cost": total["cost"],
              "error": error, "unread_at_stop": state["unread_at_stop"], "principal_unanswered": len(unanswered), "grade": None}
    log(f"stopped: {state['stop']} after {rounds} rounds, {state['seconds']}s, {fmt_tokens(total['prompt_tokens'])} prompt tokens, "
        f"{fmt_tokens(total['completion_tokens'])} completion tokens" + (f" ({error})" if error else ""))
    if state["stop"] == "stalled":
        log(f"nobody has unread mail and the auditor never reported; unanswered principal questions: {len(unanswered)}")
    if grade and state["stop"] not in ("error", "interrupted"):
        result["grade"] = grade_run(run, log)
    elif grade:
        log("not graded (the run did not end normally)")
    if state["stop"] == "interrupted":
        raise KeyboardInterrupt
    return result


def grade_run(run: Run, log) -> dict | None:
    """tools/grade.py on the run: it prints the summary and writes grade.json."""
    p = subprocess.run([sys.executable, str(run.tools_dir / "grade.py"), str(run.run_dir)], capture_output=True, text=True,
                       env=agent_mod.child_env())
    for line in p.stdout.splitlines():
        log(line)
    if p.returncode != 0:
        log(f"grade.py failed: {p.stderr.strip()[-500:]}")
        return None
    try:
        g = json.loads((run.run_dir / "grade.json").read_text())
    except (OSError, ValueError):
        return None
    try:
        o, e = g["outcome"], g["escalation"]
        return {"core": f"{o['_core_passed']}/{o['_core_total']}", "audit_pass": o.get("P11_audit_pass"),
                "recall": e["recall"], "precision": e["precision"], "false_alarms": e["false_alarms"],
                "redundant": e["redundant"], "missed": e["missed"]}
    except (KeyError, TypeError):
        log("grade.json is not in the expected shape; see the file itself")
        return None


# ---------------------------------------------------------------- build and grid

def build_run(month_end: Path, arm: str, n: int, scenario: int, model: str | None = None) -> Path:
    """tools/build_run.py, which refuses to overwrite a run directory that exists. `model` goes into run.json's
    "model" field (build_run.py would otherwise label every run "sonnet")."""
    cmd = [sys.executable, str(month_end / "tools" / "build_run.py"), arm, str(n)] + (["--scenario", "2"] if scenario == 2 else [])
    if model:
        cmd += ["--model", model]
    p = subprocess.run(cmd, capture_output=True, text=True, env=agent_mod.child_env())
    if p.returncode != 0:
        raise RunError(f"build_run.py {arm} {n} failed: {(p.stderr or p.stdout).strip()[-400:]}")
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    if not lines:
        raise RunError("build_run.py printed no run directory")
    return Path(lines[-1].strip())


def free_numbers(runs_dir: Path, arm: str, scenario: int, count: int, start: int | None) -> list[int]:
    suffix = "s2" if scenario == 2 else ""
    if start is not None:
        return list(range(start, start + count))
    out, n = [], 1
    while len(out) < count:
        if not (runs_dir / f"{arm}{n}{suffix}").exists():
            out.append(n)
        n += 1
    return out


def format_table(rows: list[dict]) -> str:
    def cell(r, key, fmt=str):
        v = r.get(key)
        return "-" if v is None else fmt(v)
    header = ["run", "arm", "stop", "rounds", "core", "audit", "recall", "prec", "prompt", "cached", "compl", "cost", "min"]
    body = []
    for r in rows:
        g = r.get("grade") or {}
        body.append([r["run"], r["arm"], r["stop"], str(r["rounds"]), g.get("core", "-"),
                     "-" if g.get("audit_pass") is None else ("PASS" if g["audit_pass"] else "no"),
                     "-" if g.get("recall") is None else f"{g['recall']:.2f}",
                     "-" if g.get("precision") is None else f"{g['precision']:.2f}",
                     fmt_tokens(r["prompt_tokens"]), fmt_tokens(r["cached_tokens"]), fmt_tokens(r["completion_tokens"]),
                     "-" if r["cost"] is None else f"{r['cost']:.3f}", "-" if r["seconds"] is None else f"{r['seconds'] / 60:.1f}"])
    widths = [max(len(header[i]), *(len(row[i]) for row in body)) if body else len(header[i]) for i in range(len(header))]
    lines = ["  ".join(h.ljust(w) for h, w in zip(header, widths)), "  ".join("-" * w for w in widths)]
    lines += ["  ".join(c.ljust(w) for c, w in zip(row, widths)) for row in body]
    return "\n".join(lines)


def run_grid(arms: list[str], runs: int, model: str, *, scenario: int = 1, start: int | None = None, jobs: int = 1,
             summary: str | None = None, month_end: str | None = None, **run_kwargs) -> list[dict]:
    me = month_end_dir(month_end)
    try:
        llm.preflight(model)
        if run_kwargs.get("principal_model"):
            llm.preflight(run_kwargs["principal_model"])
    except llm.LLMError as e:
        raise RunError(f"cannot use {model}: {e}") from None
    dirs = []
    for arm in arms:
        for n in free_numbers(me / "runs", arm, scenario, runs, start):
            dirs.append(build_run(me, arm, n, scenario, model))
            print(f"built {dirs[-1]}", flush=True)
    results: list[dict] = []
    halt = threading.Event()

    def one(d: Path) -> dict:
        try:
            return run_one(d, model, month_end=month_end, halt=halt, **run_kwargs)
        except (Exception, RunError) as e:  # noqa: BLE001  (one broken run must not end the grid)
            return {"run": d.name, "path": str(d), "arm": json.loads((d / "run.json").read_text())["arm"], "model": model,
                    "stop": "error", "rounds": 0, "seconds": None, "prompt_tokens": 0, "completion_tokens": 0,
                    "cached_tokens": None, "cost": None,
                    "error": str(e) if isinstance(e, RunError) else f"{type(e).__name__}: {e}", "grade": None}

    if jobs > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(one, d) for d in dirs]
            try:
                results = [f.result() for f in futures]
            except KeyboardInterrupt:
                halt.set()              # runs in flight stop at their next model call and write their state
                for f in futures:
                    f.cancel()          # runs not started stay built and unrun
                raise
    else:
        results = [one(d) for d in dirs]
    print("\n" + format_table(results), flush=True)
    out = Path(summary) if summary else me / "results" / f"harness-grid-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, {"model": model, "arms": arms, "runs_per_arm": runs, "scenario": scenario, "results": results})
    print(f"summary written to {out}", flush=True)
    return results


# ---------------------------------------------------------------- command line

def resolve_run(arg: str, month_end: Path) -> Path:
    p = Path(arg)
    for cand in ([p] if p.is_absolute() else [Path.cwd() / p, month_end / p]):
        if (cand / "run.json").is_file():
            return cand.resolve()
    raise RunError(f"no run directory at {arg} (looked in the current directory and in {month_end})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the month-end scenario unattended against a chat model with tool calling.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", metavar="DIR", help="a prepared run directory, e.g. runs/L4")
    mode.add_argument("--build", nargs=2, metavar=("ARM", "N"), help="build runs/<arm><n> with build_run.py, then run it")
    mode.add_argument("--grid", metavar="ARMS", help='comma-separated arms, e.g. "A,D,L": build and run --runs fresh runs of each')
    ap.add_argument("--model", required=True, help="provider:name, e.g. openrouter:openai/gpt-5.6, openai:gpt-5.6, anthropic:claude-sonnet-4-6, mock:script.json")
    ap.add_argument("--principal-model", metavar="MODEL", help="a model that answers the questions the scripted principal cannot (arms L and R)")
    ap.add_argument("--scenario", type=int, choices=(1, 2), default=1, help="scenario for --build and --grid (default 1)")
    ap.add_argument("--runs", type=int, default=1, help="runs per arm for --grid (default 1)")
    ap.add_argument("--start", type=int, help="first run number for --grid (default: the first free numbers)")
    ap.add_argument("--jobs", type=int, default=1, help="runs in parallel for --grid (default 1)")
    ap.add_argument("--summary", metavar="PATH", help="where --grid writes its summary JSON (default month-end/results/)")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS, help=f"default {MAX_ROUNDS}")
    ap.add_argument("--max-prompt-tokens", type=int, metavar="N", help="stop a run once its prompt tokens (cached ones included) pass N; checked after every model call")
    ap.add_argument("--no-grade", action="store_true", help="do not call grade.py at the end")
    ap.add_argument("--no-python-c", action="store_true", help="refuse `python3 -c` in the agents' shell tool")
    ap.add_argument("--month-end", metavar="DIR", help="the month-end directory (default ../month-end, or RW_MONTH_END)")
    a = ap.parse_args(argv)
    if a.grid is None and (a.runs != 1 or a.start is not None or a.jobs != 1 or a.summary):
        ap.error("--runs, --start, --jobs and --summary belong to --grid")
    if a.run and a.scenario != 1:
        ap.error("--scenario belongs to --build and --grid (a prepared run directory already has its scenario)")
    me = month_end_dir(a.month_end)
    common = dict(principal_model=a.principal_model, max_rounds=a.max_rounds, max_prompt_tokens=a.max_prompt_tokens,
                  grade=not a.no_grade, allow_python_c=not a.no_python_c)
    try:
        if a.grid is not None:
            arms = [x.strip().upper() for x in re.split(r"[,\s]+", a.grid) if x.strip()]
            bad = [x for x in arms if x not in list(ARMS)]
            if not arms or bad:
                ap.error(f"--grid takes arms from {', '.join(ARMS)}; got {a.grid!r}")
            if a.runs < 1 or a.jobs < 1:
                ap.error("--runs and --jobs must be at least 1")
            results = run_grid(arms, a.runs, a.model, scenario=a.scenario, start=a.start, jobs=a.jobs, summary=a.summary,
                               month_end=a.month_end, **common)
            stops = [r["stop"] for r in results]
            return 2 if "error" in stops else (0 if all(s == "complete" for s in stops) else 1)
        if a.build:
            arm, n = a.build[0].upper(), a.build[1]
            if arm not in list(ARMS) or not n.isdigit():
                ap.error(f"--build takes an arm from {', '.join(ARMS)} and a number, for example --build L 4")
            try:
                llm.preflight(a.model)
            except llm.LLMError as e:
                raise RunError(f"cannot use {a.model}: {e}") from None
            run_dir = build_run(me, arm, int(n), a.scenario, a.model)
        else:
            run_dir = resolve_run(a.run, me)
        result = run_one(run_dir, a.model, month_end=a.month_end, **common)
    except KeyboardInterrupt:
        print("interrupted; every run that had started has rounds.json and usage.json (stop: interrupted)", file=sys.stderr)
        return 130
    if result["stop"] == "error":
        return 2
    return 0 if result["stop"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
