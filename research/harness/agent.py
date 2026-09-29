#!/usr/bin/env python3
"""agent.py: a tool-calling agent bound to one run directory. Standard library only.

An agent has a system prompt (the role file, prompts/<role>.md, verbatim), a working directory (the run
directory) and exactly five tools, all scoped to that directory:

    read_file(path)             read a text file
    write_file(path, content)   create or overwrite a text file
    list_dir(path)              list a directory
    shell(cmd)                  one allowlisted command, 60 s timeout (see below)
    done()                      end the turn

A turn: append the user message "mail", then loop on model calls and tool calls until done() (or a plain-text
reply, which the role prompts call `DONE`) or 40 tool calls. The conversation persists across turns. Before each
model call the context is capped at 150k characters by dropping the oldest tool results (the system prompt and
the last 20 messages are kept).

Scoping. Paths are resolved with realpath and must land inside the run directory (`..`, absolute paths and
symlinks out are refused). The harness's own directory `harness/` is invisible to the tools, and write_file
refuses the channel and bookkeeping files (mail/, mail.py, run.json, prompts/, rounds.json, usage.json,
grade.json, principal_state.json). data/ stays writable on purpose: whether an agent edits the supplier master
is something the study measures.

Shell. The command is split with shlex and executed without a shell, so there is no pipe, redirect, chaining,
globbing or expansion. Allowed: `python3 mail.py <read|send|open|validate|make-rb|check-echo|pending> ...`,
`python3 -c '<code>'`, and cat, ls, grep, head, tail, wc, jq, sha256sum. Every argument that names an existing
path outside the run directory is refused, recursion (grep -r, ls -R) is refused, and `mail.py log|stats` (the
orchestrator's commands) are refused. An agent is itself: `mail.py send --from` and `read|open --me` must name
the calling agent, so no model can send as the principal or take another agent's mail. Subprocesses get a
scrubbed environment: no API keys, no proxy settings.
`python3 -c` is NOT a sandbox: it can touch anything your user can. Run unknown models in a container, or pass
allow_python_c=False.

read_file goes through `mail.py open`, so a read is logged in mail/log.jsonl with its token count exactly as
when an agent uses `mail.py open` (the month-end grader counts those). Every `python3 mail.py` call runs under
one lock per run: mail.py's `read` rewrites the whole log and `send` numbers messages by reading it, so two
agents running them at the same instant could lose a message or reuse a sequence number.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import traceback
from contextlib import nullcontext
from pathlib import Path
from typing import Callable, NamedTuple

import llm

MAX_TOOL_CALLS = 40
CONTEXT_CHARS = 150_000
KEEP_LAST = 20
SHELL_TIMEOUT = 60
MAX_RESULT_CHARS = 40_000
MAX_FILE_BYTES = 2_000_000
DROPPED = "[older tool result dropped to save context]"

HIDDEN = {"harness"}
PROTECTED = {"mail", "mail.py", "run.json", "prompts", "harness", "rounds.json", "usage.json", "grade.json",
             "principal_state.json"}
FILE_COMMANDS = ("cat", "ls", "grep", "head", "tail", "wc", "jq", "sha256sum")
MAIL_COMMANDS = ("read", "send", "open", "validate", "make-rb", "check-echo", "pending")
ENV_KEEP = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "TMPDIR", "TEMP", "TMP", "TZ",
            "SYSTEMROOT", "COMSPEC", "PATHEXT", "VIRTUAL_ENV", "TIKTOKEN_CACHE_DIR", "DATA_GYM_CACHE_DIR")
_OPERATOR = re.compile(r"(?:\d*[<>]{1,2}&?\d*|&>?|\|\|?|&&|;;?)")
_REDIRECT_TO = re.compile(r"\d*[<>]{1,2}[^\s<>&]+")

ALLOWED_TEXT = ("python3 mail.py <read|send|open|validate|make-rb|check-echo|pending> ..., python3 -c '<code>', "
                "cat, ls, grep, head, tail, wc, jq, sha256sum")


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
                                             "parameters": {"type": "object", "properties": properties, "required": required}}}


TOOLS = [
    _tool("read_file", "Read a text file inside the run directory, for example data/emails.md or work/invoices.json.",
          {"path": {"type": "string", "description": "Path relative to the run directory."}}, ["path"]),
    _tool("write_file", "Create or overwrite a text file inside the run directory, for example work/invoices.json. "
                        "Parent directories are created. Paths outside the run directory are refused.",
          {"path": {"type": "string", "description": "Path relative to the run directory."},
           "content": {"type": "string", "description": "The full file content."}}, ["path", "content"]),
    _tool("list_dir", "List a directory inside the run directory (default: the run directory itself).",
          {"path": {"type": "string", "description": "Directory relative to the run directory. Default '.'."}}, []),
    _tool("shell", "Run ONE command in the run directory and return its output. Allowed: " + ALLOWED_TEXT + ". "
                   "There is no shell: no pipes, redirects, chaining, globbing or variable expansion. 60 second timeout.",
          {"cmd": {"type": "string", "description": "The command line."}}, ["cmd"]),
    _tool("done", "End this turn. Call it when you have nothing more to do until new mail arrives "
                  "(the equivalent of replying DONE).", {}, []),
]


class _Quiet(argparse.ArgumentParser):
    """An argparse parser that raises instead of printing usage and exiting."""

    def error(self, message):
        raise ValueError(message)


class ToolError(Exception):
    """The call failed; the message goes back to the model."""


class Refused(ToolError):
    """The call was refused by the sandbox (scope or allowlist)."""


class ToolResult(NamedTuple):
    text: str
    error: bool = False
    refused: bool = False


def child_env() -> dict:
    """The environment for subprocesses: a whitelist, so no API key or proxy setting is ever inherited."""
    env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def _clip(text: str, limit: int = MAX_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[truncated: {len(text) - limit} more characters]"


# ---------------------------------------------------------------- the sandbox

class Sandbox:
    """The five tools, bound to one run directory."""

    def __init__(self, run_dir, role: str, mail_lock: threading.Lock | None = None, allow_python_c: bool = True,
                 shell_timeout: float = SHELL_TIMEOUT):
        self.root = Path(os.path.realpath(run_dir))
        self.role = role
        self.lock = mail_lock if mail_lock is not None else threading.Lock()
        self.allow_python_c = allow_python_c
        self.shell_timeout = shell_timeout

    # -- paths

    def resolve(self, raw, write: bool = False) -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise ToolError("path must be a non-empty string")
        if "\x00" in raw:
            raise ToolError("path contains a NUL byte")
        p = Path(raw)
        full = p if p.is_absolute() else self.root / p
        try:
            real = Path(os.path.realpath(full))
        except (OSError, ValueError) as e:
            raise ToolError(f"bad path: {e}") from None
        if real != self.root and self.root not in real.parents:
            raise Refused(f"{raw} is outside the run directory ({self.root}); only paths inside it are available")
        top = real.relative_to(self.root).parts[:1]
        if top and top[0].lower() in HIDDEN:            # (lower-cased: macOS and Windows file systems ignore case)
            raise Refused(f"{raw} is not available")
        if write and (not top or top[0].lower() in PROTECTED):
            raise Refused(f"{raw} is managed by the harness and cannot be written")
        return real

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix() or "."

    # -- tools

    def read_file(self, args: dict) -> ToolResult:
        path = args.get("path")
        p = self.resolve(path)
        if not p.exists():
            raise ToolError(f"no such file: {path}")
        if p.is_dir():
            raise ToolError(f"{path} is a directory; use list_dir")
        if p.stat().st_size > MAX_FILE_BYTES:
            raise ToolError(f"{path} is larger than {MAX_FILE_BYTES} bytes")
        try:
            text = p.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            raise ToolError(f"{path} is not UTF-8 text") from None
        if (self.root / "mail.py").is_file():
            rc, out = self._mail(["open", "--me", self.role, self.rel(p)])
            if rc != 0:
                raise ToolError(out.strip() or f"could not read {path}")
            text = out[:-1] if out.endswith("\n") else out
        return ToolResult(text)

    def write_file(self, args: dict) -> ToolResult:
        path, content = args.get("path"), args.get("content")
        if not isinstance(content, str):
            raise ToolError("content must be a string")
        p = self.resolve(path, write=True)
        if p.is_dir():
            raise ToolError(f"{path} is a directory")
        data = content.encode("utf-8")
        if len(data) > MAX_FILE_BYTES:
            raise ToolError(f"content is larger than {MAX_FILE_BYTES} bytes")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return ToolResult(f"wrote {len(data)} bytes to {self.rel(p)}")

    def list_dir(self, args: dict) -> ToolResult:
        path = args.get("path") or "."
        p = self.resolve(path)
        if not p.exists():
            raise ToolError(f"no such directory: {path}")
        if not p.is_dir():
            raise ToolError(f"{path} is a file; use read_file")
        lines = []
        for child in sorted(p.iterdir(), key=lambda c: c.name):
            if p == self.root and child.name.lower() in HIDDEN:
                continue
            try:
                lines.append(f"{child.name}/" if child.is_dir() else f"{child.name}  ({child.stat().st_size} bytes)")
            except OSError:
                lines.append(child.name)
            if len(lines) >= 500:
                lines.append("[more entries not shown]")
                break
        return ToolResult("\n".join(lines) if lines else "(empty directory)")

    def done(self, args: dict) -> ToolResult:
        return ToolResult("Turn ended.")

    def shell(self, args: dict) -> ToolResult:
        cmd = args.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            raise ToolError("cmd must be a non-empty string")
        try:
            argv = shlex.split(cmd)
        except ValueError as e:
            raise ToolError(f"could not parse the command: {e}") from None
        if not argv:
            raise ToolError("empty command")
        if any(_OPERATOR.fullmatch(t) or _REDIRECT_TO.fullmatch(t) for t in argv):
            raise Refused("shell syntax (pipes, redirects, ; & && ||) is not supported: run one command per call and "
                          "pass file names as arguments; use write_file to create files")
        head = argv[0]
        if head == "python3":
            if len(argv) >= 2 and argv[1] == "mail.py":
                sub = argv[2] if len(argv) > 2 else None
                if sub not in MAIL_COMMANDS and sub not in ("-h", "--help"):
                    raise Refused(f"mail.py subcommand {sub!r} is not available to agents; use one of {', '.join(MAIL_COMMANDS)}")
                self._check_identity(sub, argv[3:])
                kind, check = "mail", argv[2:]
            elif len(argv) >= 3 and argv[1] == "-c":
                if not self.allow_python_c:
                    raise Refused("python3 -c is disabled for this run")
                kind, check = "python", []
            else:
                raise Refused("python3 may only run `python3 mail.py ...` or `python3 -c '<code>'`")
        elif head in FILE_COMMANDS:
            kind, check = "file", argv[1:]
            for t in check:
                if re.fullmatch(r"--recursive|--dereference-recursive", t) or \
                        (head == "grep" and re.fullmatch(r"-[A-Za-z]*[rR][A-Za-z]*", t)) or \
                        (head == "ls" and re.fullmatch(r"-[A-Za-z]*R[A-Za-z]*", t)):
                    raise Refused("recursive options are not available; name the files you want")
        else:
            raise Refused(f"command not allowed: {head}. Allowed: {ALLOWED_TEXT}")
        self._check_paths(check)
        env = child_env()
        exe = sys.executable if head == "python3" else shutil.which(head, path=env.get("PATH"))
        if exe is None:
            raise ToolError(f"{head} is not installed on this machine")
        try:
            with (self.lock if kind == "mail" else nullcontext()):
                proc = subprocess.run([exe, *argv[1:]], cwd=self.root, env=env, stdin=subprocess.DEVNULL,
                                      capture_output=True, timeout=self.shell_timeout)
        except subprocess.TimeoutExpired:
            raise ToolError(f"command timed out after {self.shell_timeout:g} s") from None
        except OSError as e:
            raise ToolError(f"could not run {head}: {e}") from None
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        text = out
        if err.strip():
            text += ("" if not text or text.endswith("\n") else "\n") + err
        if proc.returncode != 0:
            text = text.rstrip("\n") + f"\n[exit status {proc.returncode}]"
        return ToolResult(text if text.strip() else "(no output)", error=proc.returncode != 0)

    def _check_identity(self, sub: str | None, args: list[str]) -> None:
        """An agent sends as itself and reads its own mail: `send --from` and `read|open --me` must name this agent.
        Without this a model could write the principal's approval into the log or take another agent's mail (which
        marks it read, so that agent is never woken). The arguments are parsed the way mail.py parses them; anything
        that does not parse is left to mail.py to report."""
        if sub not in ("send", "read", "open"):
            return
        parser = _Quiet(add_help=False, allow_abbrev=True)
        if sub == "send":
            parser.add_argument("--from", dest="who")
            parser.add_argument("--to")
            parser.add_argument("-m")
            parser.add_argument("--file")
        else:
            parser.add_argument("--me", dest="who")
            parser.add_argument("path", nargs="*")
        try:
            ns, _ = parser.parse_known_args(args)
        except (ValueError, argparse.ArgumentError):
            return
        if ns.who is not None and ns.who != self.role:
            flag = "--from" if sub == "send" else "--me"
            raise Refused(f"you are the {self.role} agent: `{flag}` must be {self.role}, not {ns.who}")

    def _check_paths(self, tokens: list[str]) -> None:
        """Refuse any argument that names an existing path outside the run directory (or inside harness/).
        Arguments that are not paths (patterns, message bodies) pass because they do not exist as files."""
        for tok in tokens:
            cand = tok
            if tok.startswith("-"):
                if "=" not in tok:
                    continue
                cand = tok.split("=", 1)[1]
            if not cand or len(cand) > 1024 or "\x00" in cand:
                continue
            try:
                full = Path(cand) if os.path.isabs(cand) else self.root / cand
                real = Path(os.path.realpath(full))
                exists = os.path.lexists(real)
            except (OSError, ValueError):
                continue
            inside = real == self.root or self.root in real.parents
            if not inside and exists:
                raise Refused(f"{tok!r} is outside the run directory")
            if inside and real != self.root and real.relative_to(self.root).parts[0].lower() in HIDDEN:
                raise Refused(f"{tok!r} is not available")

    def _mail(self, args: list[str]) -> tuple[int, str]:
        with self.lock:
            proc = subprocess.run([sys.executable, "mail.py", *args], cwd=self.root, env=child_env(),
                                  stdin=subprocess.DEVNULL, capture_output=True, timeout=self.shell_timeout)
        return proc.returncode, (proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace"))

    # -- dispatch

    def call(self, name: str, args) -> ToolResult:
        handler = {"read_file": self.read_file, "write_file": self.write_file, "list_dir": self.list_dir,
                   "shell": self.shell, "done": self.done}.get(name)
        if handler is None:
            return ToolResult(f"error: unknown tool {name!r}. The tools are read_file, write_file, list_dir, shell, done.", True)
        if not isinstance(args, dict):
            return ToolResult("error: the arguments must be a JSON object", True)
        try:
            res = handler(args)
        except Refused as e:
            return ToolResult(f"refused: {e}", True, True)
        except ToolError as e:
            return ToolResult(f"error: {e}", True)
        except subprocess.TimeoutExpired:
            return ToolResult(f"error: timed out after {self.shell_timeout:g} s", True)
        except Exception as e:  # noqa: BLE001
            return ToolResult(f"error: {type(e).__name__}: {e}", True)
        return ToolResult(_clip(res.text) or "(no output)", res.error, res.refused)   # never an empty tool message


# ---------------------------------------------------------------- context cap and usage

def message_chars(m: dict) -> int:
    c = m.get("content")
    n = len(c) if isinstance(c, str) else (len(json.dumps(c)) if c else 0)
    for tc in m.get("tool_calls") or []:
        fn = tc.get("function") or {}
        n += len(fn.get("name") or "") + len(fn.get("arguments") or "")
    return n


def cap_context(messages: list[dict], limit: int = CONTEXT_CHARS, keep_last: int = KEEP_LAST) -> int:
    """Replace the oldest tool results with a stub until the conversation is within `limit` characters.
    messages[0] (the system prompt) and the last `keep_last` messages are never touched. Returns how many
    results were dropped. Tool-call ids stay paired, so the conversation remains valid for every provider."""
    total = sum(message_chars(m) for m in messages)
    if total <= limit:
        return 0
    dropped = 0
    for i in range(1, max(1, len(messages) - keep_last)):
        m = messages[i]
        before = message_chars(m)
        if m.get("role") != "tool" or m.get("_dropped") or before <= len(DROPPED):
            continue
        m["content"], m["_dropped"] = DROPPED, True
        total -= before - len(DROPPED)
        dropped += 1
        if total <= limit:
            break
    return dropped


def sum_usage(usages: list[dict]) -> dict:
    keys = ("prompt_tokens", "completion_tokens", "cached_tokens", "cache_write_tokens", "reasoning_tokens")
    tot: dict = {k: 0 for k in keys}
    tot.update({"cost": None, "cached_reported": False, "estimated": False})
    for u in usages:
        for k in keys:
            if isinstance(u.get(k), (int, float)):
                tot[k] += u[k]
        if u.get("cached_reported") if "cached_reported" in u else u.get("cached_tokens") is not None:
            tot["cached_reported"] = True
        if isinstance(u.get("cost"), (int, float)):
            tot["cost"] = (tot["cost"] or 0) + u["cost"]
        if u.get("estimated"):
            tot["estimated"] = True
    return tot


# ---------------------------------------------------------------- the agent

class Agent:
    """One agent for the whole run: a persistent conversation and a sandbox on the run directory."""

    def __init__(self, role: str, run_dir, model: str, *, system_prompt: str | None = None,
                 mail_lock: threading.Lock | None = None, chat_fn: Callable | None = None, allow_python_c: bool = True,
                 max_tool_calls: int = MAX_TOOL_CALLS, context_chars: int = CONTEXT_CHARS, keep_last: int = KEEP_LAST,
                 shell_timeout: float = SHELL_TIMEOUT, transcript: str | Path | None = None,
                 stop: threading.Event | None = None):
        self.role = role
        self.run_dir = Path(run_dir)
        self.model = model
        self.chat = chat_fn or llm.chat
        self.max_tool_calls = max_tool_calls
        self.context_chars = context_chars
        self.keep_last = keep_last
        self.stop = stop
        self.sandbox = Sandbox(run_dir, role, mail_lock, allow_python_c, shell_timeout)
        if system_prompt is None:
            system_prompt = (self.run_dir / "prompts" / f"{role}.md").read_text()
        self.messages: list[dict] = [{"role": "system", "content": system_prompt}]
        self.turn_no = 0
        self.transcript = Path(transcript) if transcript else None
        if self.transcript:
            self.transcript.parent.mkdir(parents=True, exist_ok=True)
        self._log(self.messages[0])

    def _log(self, message: dict, **extra) -> None:
        if not self.transcript:
            return
        rec = {"agent": self.role, "turn": self.turn_no, "i": len(self.messages) - 1, "ts": round(time.time(), 3),
               "message": message, **extra}
        with self.transcript.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _add(self, message: dict, **extra) -> None:
        self.messages.append(message)
        self._log(message, **extra)

    def turn(self, round_no: int | None = None) -> dict:
        """Wake the agent with "mail" and run it to the end of its turn. Never raises: a provider failure or a
        crash is recorded in the returned record (ended_by "error" or "crash", with `error`)."""
        self.turn_no += 1
        rec: dict = {"turn": self.turn_no, "round": round_no, "calls": 0, "tool_calls": 0, "tool_errors": 0, "refused": 0,
                     "tool_counts": {}, "ended_by": None, "error": None, "seconds": None, "calls_detail": []}
        usages: list[dict] = []
        t0 = time.time()
        self._add({"role": "user", "content": "mail"})
        try:
            while True:
                if self.stop is not None and self.stop.is_set():
                    rec["ended_by"] = "aborted"
                    break
                cap_context(self.messages, self.context_chars, self.keep_last)
                assistant, tool_calls, usage = self.chat(self.messages, TOOLS, self.model)
                usages.append(usage)
                rec["calls"] += 1
                rec["calls_detail"].append({"prompt_tokens": usage.get("prompt_tokens"),
                                            "completion_tokens": usage.get("completion_tokens"),
                                            "cached_tokens": usage.get("cached_tokens"), "seconds": usage.get("latency_s"),
                                            "finish_reason": usage.get("finish_reason")})
                self._add(assistant, usage=usage)
                if not tool_calls:
                    rec["ended_by"] = "text"
                    break
                finished = False
                for tc in tool_calls:
                    if finished:
                        res = ToolResult("not executed: the turn was ended by done()", True)
                    elif rec["tool_calls"] >= self.max_tool_calls:
                        res = ToolResult(f"not executed: the limit of {self.max_tool_calls} tool calls per turn was reached", True)
                    else:
                        rec["tool_calls"] += 1
                        rec["tool_counts"][tc["name"]] = rec["tool_counts"].get(tc["name"], 0) + 1
                        if tc["name"] == "done":
                            res, finished = ToolResult("Turn ended."), True
                        elif tc.get("error"):
                            res = ToolResult(f"error: {tc['error']}. Send the arguments as a JSON object.", True)
                        else:
                            res = self.sandbox.call(tc["name"], tc["arguments"])
                    rec["tool_errors"] += int(res.error)
                    rec["refused"] += int(res.refused)
                    self._add({"role": "tool", "tool_call_id": tc["id"], "content": res.text, "_error": res.error,
                               "_tool": tc["name"]})
                if finished:
                    rec["ended_by"] = "done"
                    break
                if rec["tool_calls"] >= self.max_tool_calls:
                    rec["ended_by"] = "tool_limit"
                    break
        except llm.LLMError as e:
            rec["error"], rec["ended_by"] = str(e), "error"
        except Exception as e:  # noqa: BLE001
            rec["error"], rec["ended_by"] = f"{type(e).__name__}: {e}", "crash"
            rec["traceback"] = traceback.format_exc()[-2000:]
        rec["seconds"] = round(time.time() - t0, 3)
        rec.update(sum_usage(usages))
        return rec
