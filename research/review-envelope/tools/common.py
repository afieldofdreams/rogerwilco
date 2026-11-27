"""Study 11, the review envelope: paths, the models, the model call, and the cost ledger with its cap.

Copied from study 10 (research/scheduler-judge/tools/common.py) with the paths, the model table and the working
directory changed; the calls themselves are unchanged. What follows is study 10's own description of them.

Claude models run as headless Claude Code sessions (`claude -p`), the runner of studies 5 to 9, with nothing the task
does not need: no tools (`--tools ""`), no MCP servers, no CLAUDE.md, skills or hooks (`--safe-mode`), no session
saved, the brief as the whole system prompt, one fixed working directory outside the repository. Three variables of
the session that launches the run are not passed on: CLAUDE_EFFORT (it was `max` here, which every child session
would inherit), CLAUDE_CODE_USER_EMAIL and CLAUDE_CODE_REMOTE_SESSION_ID. Each model runs at its provider's default
effort, passed explicitly. OpenAI models run through research/harness/llm.py, the API harness of studies 6 and 7,
imported by path and unchanged; the key is read from OPENAI_API_KEY, or from OPEN_API_KEY where the environment names
it that way, and is never written anywhere.

Every call is written to results/ledger.jsonl with its cost: as `claude -p` reports it for Claude, and from the
token counts at the published prices for OpenAI (the harness records no cost for them). A run stops before a call
that could take its phase past the cap.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # research/review-envelope
REPO = ROOT.parents[1]
DATA = ROOT / "data"
BRIEFS = DATA / "briefs"
SUMMARIES = ROOT / "summaries"
TRIALS = ROOT / "trials"
RESULTS = ROOT / "results"
LEDGER = RESULTS / "ledger.jsonl"
HARNESS = REPO / "research" / "harness"
CWD = Path(tempfile.gettempdir()) / "rw-review-envelope-cwd"   # one fixed, empty working directory for every claude -p call

# alias -> how it is called. effort: the provider's default for the model, passed explicitly (Claude);
# the OpenAI models get no reasoning setting, which is their API default.
MODELS = {
    "haiku55": {"name": "Claude Haiku 5.5", "vendor": "anthropic", "id": "claude-haiku-5-5", "effort": "medium"},
    "sonnet55": {"name": "Claude Sonnet 5.5", "vendor": "anthropic", "id": "claude-sonnet-5-5", "effort": "high"},
    "opus55": {"name": "Claude Opus 5.5", "vendor": "anthropic", "id": "claude-opus-5-5", "effort": "high"},
    "gpt54mini": {"name": "GPT-5.4 mini", "vendor": "openai", "id": "openai:gpt-5.4-mini"},
    "gpt55": {"name": "GPT-5.5", "vendor": "openai", "id": "openai:gpt-5.5"},
}
# Published prices, US dollars per million tokens: input, cached input, output (output includes reasoning).
# gpt-5.4-mini as study 7 recorded them (amendment 13); gpt-5.5 from OpenAI's model page, read on 14 November 2026.
PRICES = {"gpt54mini": (0.75, 0.075, 4.50), "gpt55": (5.00, 0.50, 30.00)}

CLAUDE_TIMEOUT = 300
CLAUDE_BUDGET_PER_CALL = "0.50"            # a runaway guard for one call, far above any expected cost
DROP_ENV = ("CLAUDE_EFFORT", "CLAUDE_CODE_USER_EMAIL", "CLAUDE_CODE_REMOTE_SESSION_ID")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path_or_text) -> str:
    data = Path(path_or_text).read_bytes() if isinstance(path_or_text, Path) else str(path_or_text).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def read_json(p: Path):
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def brief(name: str) -> str:
    return (BRIEFS / f"{name}.txt").read_text()


def git_short() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO), capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "?"


def claude_version() -> str:
    try:
        return subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return "?"


# ------------------------------------------------------------------------------------- the ledger and the cap

class CapReached(RuntimeError):
    pass


class Ledger:
    """Every call's cost, appended as it lands. reserve() refuses a call that could take the phase's spend with that
    call's vendor past its cap: spent + the reservations of the calls in flight + this call's reservation must stay at or
    under it. Amendment 2: the cap is on OpenAI spend, the money the run costs; Claude runs on the account's plan and its
    list-price cost is recorded and held under a separate runaway guard (claude_cap), or none."""

    def __init__(self, phase: str, cap: float, claude_cap: float | None = None):
        self.phase = phase
        self.caps = {"openai": cap, "anthropic": claude_cap}
        self.lock = threading.Lock()
        self.spent = {"openai": 0.0, "anthropic": 0.0}
        self.in_flight = {"openai": 0.0, "anthropic": 0.0}
        self.per_model: dict[str, list[float]] = {}
        if LEDGER.exists():
            for line in LEDGER.read_text().splitlines():
                if line.strip():
                    e = json.loads(line)
                    if e.get("phase") == phase and e.get("model") in MODELS:
                        self.spent[MODELS[e["model"]]["vendor"]] += e.get("cost") or 0.0
                    self.per_model.setdefault(f"{e.get('model')}:{e.get('kind')}", []).append(e.get("cost") or 0.0)

    def estimate(self, model: str, kind: str) -> float:
        seen = self.per_model.get(f"{model}:{kind}") or []
        floor = {"haiku55": 0.005, "gpt54mini": 0.01, "sonnet55": 0.05, "gpt55": 0.08, "opus55": 0.25}[model]
        return max(floor, 3 * max(seen[-50:])) if seen else floor

    def describe(self) -> str:
        return (f"OpenAI ${self.spent['openai']:.4f} of the ${self.caps['openai']:.2f} cap; Claude at list price "
                f"${self.spent['anthropic']:.4f}" + (f" of the ${self.caps['anthropic']:.2f} guard" if self.caps["anthropic"] else ""))

    def reserve(self, model: str, kind: str) -> float:
        v = MODELS[model]["vendor"]
        cap = self.caps[v]
        est = self.estimate(model, kind)
        with self.lock:
            if cap is not None and self.spent[v] + self.in_flight[v] + est > cap:
                raise CapReached(f"phase {self.phase}, {v}: spent ${self.spent[v]:.4f}, in flight ${self.in_flight[v]:.4f}, "
                                 f"next call up to ${est:.4f}, cap ${cap:.2f}")
            self.in_flight[v] += est
        return est

    def settle(self, reserved: float, entry: dict) -> None:
        entry = {"ts": now(), "phase": self.phase, **entry}
        v = MODELS[entry["model"]]["vendor"]
        with self.lock:
            self.in_flight[v] -= reserved
            self.spent[v] += entry.get("cost") or 0.0
            self.per_model.setdefault(f"{entry['model']}:{entry['kind']}", []).append(entry.get("cost") or 0.0)
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")

# ------------------------------------------------------------------------------------- the model call

def _child_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in DROP_ENV}
    return env


def call_claude(alias: str, system: str, user: str) -> dict:
    m = MODELS[alias]
    CWD.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", "--model", m["id"], "--effort", m["effort"], "--output-format", "json", "--safe-mode",
           "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--max-budget-usd", CLAUDE_BUDGET_PER_CALL,
           "--session-id", str(uuid.uuid4()), "--system-prompt", system]
    t0 = time.time()
    last = {}
    spent = 0.0                                  # what failed attempts cost is still spent
    for attempt in (1, 2, 3):
        try:
            proc = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT, cwd=str(CWD), env=_child_env())
        except subprocess.TimeoutExpired:
            last = {"error": "timeout"}
            continue
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            last = {"error": "no json", "stderr": proc.stderr[-1000:]}
            time.sleep(5 * attempt)
            continue
        spent += data.get("total_cost_usd") or 0.0
        if data.get("is_error"):
            last = {"error": f"is_error: {str(data.get('result'))[:300]}"}
            time.sleep(8 * attempt)
            continue
        mu = data.get("modelUsage") or {}
        return {"text": (data.get("result") or "").strip(), "cost": round(spent, 8), "cost_by": "claude -p total_cost_usd",
                "served": sorted(mu), "usage": data.get("usage"), "model_usage": mu, "attempts": attempt,
                "seconds": round(time.time() - t0, 1), "num_turns": data.get("num_turns")}
    return {"text": None, "cost": round(spent, 8), "cost_by": "claude -p total_cost_usd", "error": last.get("error"),
            "attempts": 3, "seconds": round(time.time() - t0, 1)}


_llm = None

def _harness():
    global _llm
    if _llm is None:
        if not os.environ.get("OPENAI_API_KEY") and os.environ.get("OPEN_API_KEY"):
            os.environ["OPENAI_API_KEY"] = os.environ["OPEN_API_KEY"]   # in this process only; never written anywhere
        sys.path.insert(0, str(HARNESS))
        import llm  # noqa: E402
        _llm = llm
    return _llm


def call_openai(alias: str, system: str, user: str) -> dict:
    """One chat-completions call through the harness's own functions, as llm.chat makes it with no tools, keeping
    the model id the API says it served."""
    llm = _harness()
    name = MODELS[alias]["id"].split(":", 1)[1]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    t0 = time.time()
    try:
        url, key, host = llm._resolve_compat("openai")
        body = {"model": name, "messages": llm._oa_messages(messages, host)}
        body.update(llm._extra_body())
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        estimate = llm._estimate_tokens([body["messages"], []])
        raw = {}

        def once():
            data = llm._post_json(url, headers, body, 600.0)
            raw["data"] = data
            return llm._parse_openai(data, host, estimate)

        (assistant, _calls, usage), attempts = llm._with_retries(once, 8)
    except Exception as e:  # noqa: BLE001
        return {"text": None, "cost": 0.0, "error": llm._redact(str(e))[:500], "seconds": round(time.time() - t0, 1)}
    pin, pcached, pout = PRICES[alias]
    prompt = usage.get("prompt_tokens") or 0
    cached = usage.get("cached_tokens") or 0
    out = usage.get("completion_tokens") or 0
    cost = ((prompt - cached) * pin + cached * pcached + out * pout) / 1e6
    data = raw.get("data") or {}
    return {"text": (llm._text(assistant.get("content")) or "").strip(), "cost": round(cost, 8),
            "cost_by": f"tokens at published prices {PRICES[alias]}", "served": [data.get("model")],
            "system_fingerprint": data.get("system_fingerprint"), "usage": usage, "attempts": attempts,
            "seconds": round(time.time() - t0, 1)}


def call(alias: str, system: str, user: str, ledger: Ledger, kind: str, call_id: str) -> dict:
    reserved = ledger.reserve(alias, kind)
    try:
        r = call_claude(alias, system, user) if MODELS[alias]["vendor"] == "anthropic" else call_openai(alias, system, user)
    except Exception as e:  # noqa: BLE001
        r = {"text": None, "cost": 0.0, "error": f"{type(e).__name__}: {e}"[:500]}
    usage = r.get("usage") or {}
    ledger.settle(reserved, {"kind": kind, "id": call_id, "model": alias, "cost": r.get("cost") or 0.0, "cost_by": r.get("cost_by"),
                             "served": r.get("served"), "error": r.get("error"),
                             "tokens": {k: usage.get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
                                                                  "output_tokens", "prompt_tokens", "cached_tokens", "completion_tokens",
                                                                  "reasoning_tokens") if usage.get(k) is not None}})
    return r
