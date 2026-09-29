#!/usr/bin/env python3
"""llm.py: one chat-with-tools interface for the harness. Standard library only (urllib).

    assistant_message, tool_calls, usage = chat(messages, tools, model)

Inside the harness everything uses the OpenAI chat-completions shapes ("canonical" form):

    {"role": "system" | "user", "content": str}
    {"role": "assistant", "content": str | None,
     "tool_calls": [{"id", "type": "function", "function": {"name", "arguments": "<json string>"}}]}
    {"role": "tool", "tool_call_id": str, "content": str}
    tools = [{"type": "function", "function": {"name", "description", "parameters": {<json schema>}}}]

`assistant_message` is appendable to `messages` as it is. `tool_calls` is the same information parsed:
[{"id", "name", "arguments": dict | None, "error": str | None}] (`error` is set when the model's arguments were
not a JSON object). `usage` always has the same keys: prompt_tokens (input including cached), completion_tokens,
cached_tokens (None when the provider does not report it), cache_write_tokens, reasoning_tokens, cost,
estimated (True when the provider reported nothing and the numbers are chars/4), finish_reason, latency_s,
attempts, model.

Model strings (provider:name):

    openrouter:openai/gpt-5.6      OpenAI-compatible, https://openrouter.ai/api/v1
    openai:gpt-5.6                 OpenAI-compatible, https://api.openai.com/v1
    compat:qwen3-coder             OpenAI-compatible at RW_BASE_URL (Gemini, Ollama, vLLM, LiteLLM, ...)
    anthropic:claude-sonnet-4-6    Anthropic Messages API
    mock:path.json                 scripted responses for tests (format below)

Environment (keys are read from the environment only, never from files, and are never written anywhere):

    RW_BASE_URL, RW_API_KEY   base URL and key for the OpenAI-compatible adapters. Without RW_API_KEY the key is
                              taken from OPENROUTER_API_KEY (host openrouter.ai) or OPENAI_API_KEY (host
                              api.openai.com); a key is never sent to a host it does not belong to.
    ANTHROPIC_API_KEY         key for anthropic: (ANTHROPIC_BASE_URL optionally overrides https://api.anthropic.com)
    RW_TIMEOUT                seconds per HTTP request (default 600)
    RW_RETRIES                attempts per call on 408/409/425/429/5xx and network errors (default 8)
    RW_MAX_TOKENS             max output tokens (default: unset for OpenAI-compatible, 16000 for Anthropic)
    RW_TEMPERATURE            sent only when set (reasoning models reject it, so it is off by default)
    RW_EXTRA_BODY             JSON object merged into every request body (reasoning effort, provider routing, extended
                              thinking, ...). Anthropic thinking blocks and OpenRouter reasoning_details are sent back
                              with the conversation, as those APIs require during tool use; other providers' reasoning
                              text is recorded in the transcripts and not replayed.
    RW_ANTHROPIC_CACHE        1 (default) puts prompt-cache breakpoints on the system prompt and the last message

Mock script (mock:path.json). Agents are told apart by the `**role**` in their system prompt; a wake-up is a user
message and each assistant message after it is one step:

    {"agents": {"extractor": [ [ {"content": "...", "tool_calls": [{"name": "shell", "arguments": {"cmd": "..."}}],
                                  "usage": {"prompt_tokens": 1000, "completion_tokens": 40, "cached_tokens": 0}},
                                 ... ],                     # turn 1: one entry per model call
                               [ ... ] ]},                  # turn 2
     "default": {"content": "DONE"}}                        # used when a turn or step is not scripted
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import os
import random
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "rogerwilco-harness/0.1"
DEFAULT_BASES = {"openrouter": "https://openrouter.ai/api/v1", "openai": "https://api.openai.com/v1"}
OPENAI_COMPAT = ("openrouter", "openai", "compat")
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529}
BACKOFF_BASE = 2.0
BACKOFF_CAP = 60.0
_sleep = time.sleep  # tests replace this


class LLMError(RuntimeError):
    """A provider call failed for good (or, with retryable=True, it is worth another attempt)."""

    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.retry_after = retry_after


# ---------------------------------------------------------------- small helpers

def _env(name: str) -> str | None:
    v = os.environ.get(name)
    return v.strip() if v and v.strip() else None


def _env_num(name: str, cast, default=None):
    v = _env(name)
    if v is None:
        return default
    try:
        return cast(v)
    except ValueError:
        raise LLMError(f"{name}={v!r} is not a valid {cast.__name__}") from None


def _extra_body() -> dict:
    raw = _env("RW_EXTRA_BODY")
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except ValueError as e:
        raise LLMError(f"RW_EXTRA_BODY is not valid JSON: {e}") from None
    if not isinstance(obj, dict):
        raise LLMError("RW_EXTRA_BODY must be a JSON object")
    return obj


def _text(content) -> str:
    """Message content as a string (providers sometimes return a list of parts)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and isinstance(p.get("text"), str):
                parts.append(p["text"])
        return "".join(parts)
    return str(content)


def _redact(text: str) -> str:
    """Strip anything key-shaped from text that is about to be shown or logged."""
    for name in ("RW_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        v = _env(name)
        if v and len(v) >= 6:
            text = text.replace(v, "***")
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=\-]{8,}", r"\1***", text)
    return re.sub(r"\b(sk-[A-Za-z0-9_\-]{0,4})[A-Za-z0-9_*\-]{6,}", r"\1***", text)


def _safe_url(url: str) -> str:
    p = urllib.parse.urlparse(url)
    host = p.hostname or ""
    if p.port:
        host += f":{p.port}"
    return urllib.parse.urlunparse(p._replace(netloc=host))


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_local(host: str) -> bool:
    """Hosts where an unauthenticated endpoint (Ollama, vLLM) is normal."""
    if _is_loopback(host) or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_unspecified
    except ValueError:
        return False


def _opener_for(url: str) -> urllib.request.OpenerDirector:
    """The default opener (which honours HTTP(S)_PROXY and NO_PROXY), except that loopback never uses a proxy."""
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if _is_loopback(host):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def _estimate_tokens(obj) -> int:
    return max(1, len(json.dumps(obj, ensure_ascii=False)) // 4)


def _usage(prompt=None, completion=None, cached=None, cache_write=None, reasoning=None, cost=None,
           estimated=False, finish=None) -> dict:
    return {
        "prompt_tokens": prompt, "completion_tokens": completion, "cached_tokens": cached,
        "cache_write_tokens": cache_write, "reasoning_tokens": reasoning, "cost": cost,
        "estimated": estimated, "finish_reason": finish,
    }


def _int_or_none(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _parse_args(raw) -> tuple[str, dict | None, str | None]:
    """Tool-call arguments as (json string to keep in the conversation, parsed dict, error)."""
    if isinstance(raw, dict):
        return json.dumps(raw), raw, None
    if raw is None:
        s = "{}"
    elif isinstance(raw, str):
        s = raw
    else:
        s = json.dumps(raw)          # a list or scalar: keep it as JSON text so the "not an object" error is the right one
    if not s.strip():
        return "{}", {}, None
    try:
        obj = json.loads(s)
    except ValueError as e:
        return s, None, f"arguments are not valid JSON ({e})"
    if not isinstance(obj, dict):
        return s, None, "arguments must be a JSON object"
    return s, obj, None


def _unique_id(raw_id, seen: set, n: int) -> str:
    tid = raw_id if isinstance(raw_id, str) and raw_id.strip() else f"call_{n}"
    base, k = tid, 1
    while tid in seen:
        k += 1
        tid = f"{base}_{k}"
    seen.add(tid)
    return tid


# ---------------------------------------------------------------- HTTP with retries

def _error_text(raw: bytes) -> str:
    try:
        obj = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return raw.decode("utf-8", "replace")[:500]
    err = obj.get("error") if isinstance(obj, dict) else None
    if isinstance(err, dict):
        return str(err.get("message") or err)[:500]
    if isinstance(err, str):
        return err[:500]
    return json.dumps(obj)[:500]


def _post_json(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    """One POST. Raises LLMError (retryable or not); returns the decoded JSON object."""
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT, **headers}
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with _opener_for(url).open(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:  # noqa: BLE001
            body = b""
        status = e.code
        retry_after = None
        ra = e.headers.get("Retry-After") if e.headers else None
        if ra:
            try:
                retry_after = float(ra)
            except ValueError:
                pass
        raise LLMError(f"HTTP {status} from {_safe_url(url)}: {_redact(_error_text(body))}", status=status,
                       retryable=status in RETRY_STATUS, retry_after=retry_after) from None
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, http.client.HTTPException, OSError) as e:
        reason = getattr(e, "reason", e)
        raise LLMError(f"network error calling {_safe_url(url)}: {_redact(str(reason))}", retryable=True) from None
    try:
        obj = json.loads(raw.decode("utf-8"))
    except ValueError:
        raise LLMError(f"{_safe_url(url)} returned a body that is not JSON: {_redact(raw[:200].decode('utf-8', 'replace'))}",
                       retryable=True) from None
    if not isinstance(obj, dict):
        raise LLMError(f"{_safe_url(url)} returned JSON that is not an object", retryable=True)
    return obj


def _with_retries(fn, retries: int):
    """Run fn() until it returns; retry retryable LLMErrors with exponential backoff and jitter."""
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn(), attempt
        except LLMError as e:
            if not e.retryable or attempt >= retries:
                if e.retryable:
                    raise LLMError(f"{e} (gave up after {attempt} attempts)", status=e.status) from None
                raise
            delay = min(BACKOFF_CAP, BACKOFF_BASE * 2 ** (attempt - 1)) * random.uniform(0.5, 1.0)
            if e.retry_after:
                delay = max(delay, min(e.retry_after, 300.0))
            _sleep(delay)


# ---------------------------------------------------------------- OpenAI-compatible adapter

def _resolve_compat(provider: str) -> tuple[str, str | None, str]:
    base = _env("RW_BASE_URL") or DEFAULT_BASES.get(provider)
    if not base:
        raise LLMError("provider 'compat' needs RW_BASE_URL, for example http://localhost:11434/v1 for Ollama")
    base = base.rstrip("/")
    p = urllib.parse.urlparse(base)
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or not host:
        raise LLMError(f"RW_BASE_URL {_safe_url(base)!r} is not a valid http(s) URL")
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    key = _env("RW_API_KEY")
    if not key:
        if host == "openrouter.ai" or host.endswith(".openrouter.ai"):
            key = _env("OPENROUTER_API_KEY")
        elif host == "api.openai.com":
            key = _env("OPENAI_API_KEY")
    if not key and not _is_local(host):
        raise LLMError(f"no API key for {host}: set RW_API_KEY (or OPENROUTER_API_KEY for openrouter.ai, "
                       f"OPENAI_API_KEY for api.openai.com)")
    return url, key, host


def _oa_tool_call(tc: dict) -> dict:
    fn = tc.get("function") or {}
    args = fn.get("arguments")
    out = {"id": tc.get("id"), "type": "function",
           "function": {"name": fn.get("name"), "arguments": args if isinstance(args, str) else json.dumps(args or {})}}
    if tc.get("extra_content"):  # Gemini thought signatures must come back untouched
        out["extra_content"] = tc["extra_content"]
    return out


def _oa_messages(messages: list[dict], host: str) -> list[dict]:
    """Canonical messages to an OpenAI request: a whitelist of keys, so private bookkeeping never leaves the process."""
    out = []
    for m in messages:
        role = m.get("role")
        if role in ("system", "user"):
            out.append({"role": role, "content": _text(m.get("content"))})
        elif role == "assistant":
            item: dict = {"role": "assistant"}
            tcs = m.get("tool_calls")
            if tcs:
                item["content"] = m.get("content") or None
                item["tool_calls"] = [_oa_tool_call(tc) for tc in tcs]
            else:
                item["content"] = _text(m.get("content"))
            if m.get("reasoning_details") and host.endswith("openrouter.ai"):
                item["reasoning_details"] = m["reasoning_details"]
            out.append(item)
        elif role == "tool":
            out.append({"role": "tool", "tool_call_id": m.get("tool_call_id"), "content": _text(m.get("content"))})
        else:
            raise LLMError(f"unknown message role {role!r}")
    return out


def _parse_openai(data: dict, host: str, request_estimate: int) -> tuple[dict, list[dict], dict]:
    choices = data.get("choices")
    err = data.get("error")
    if not choices:
        if err:
            code = err.get("code") if isinstance(err, dict) else None
            code = int(code) if isinstance(code, (int, str)) and str(code).isdigit() else None
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise LLMError(f"provider error: {_redact(str(msg))[:500]}", status=code, retryable=code in RETRY_STATUS)
        raise LLMError("the response had no choices", retryable=True)
    choice = choices[0]
    msg = choice.get("message") or {}
    finish = choice.get("finish_reason")
    if finish == "error":
        raise LLMError("the provider ended the response with finish_reason=error", retryable=True)

    text = _text(msg.get("content"))
    seen: set = set()
    stored, calls = [], []
    for n, tc in enumerate(msg.get("tool_calls") or [], 1):
        fn = tc.get("function") or {}
        tid = _unique_id(tc.get("id"), seen, n)
        arg_str, args, error = _parse_args(fn.get("arguments"))
        stored.append(_oa_tool_call({"id": tid, "function": {"name": fn.get("name") or "", "arguments": arg_str},
                                     "extra_content": tc.get("extra_content")}))
        calls.append({"id": tid, "name": fn.get("name") or "", "arguments": args, "error": error})
    assistant: dict = {"role": "assistant", "content": text or None}
    if stored:
        assistant["tool_calls"] = stored
    rd = msg.get("reasoning_details")
    if rd and host.endswith("openrouter.ai"):
        assistant["reasoning_details"] = rd
    reasoning = msg.get("reasoning") or msg.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning:
        assistant["_reasoning"] = reasoning  # kept for transcripts only; never sent back

    u = data.get("usage") or {}
    details = u.get("prompt_tokens_details") or {}
    cdetails = u.get("completion_tokens_details") or {}
    prompt = _int_or_none(u.get("prompt_tokens"))
    completion = _int_or_none(u.get("completion_tokens"))
    cached = _int_or_none(details.get("cached_tokens"))
    if cached is None:
        cached = _int_or_none(u.get("prompt_cache_hit_tokens"))  # DeepSeek
    cost = u.get("cost") if isinstance(u.get("cost"), (int, float)) and not isinstance(u.get("cost"), bool) else None
    usage = _usage(prompt, completion, cached, _int_or_none(details.get("cache_write_tokens")),
                   _int_or_none(cdetails.get("reasoning_tokens")), cost, False, finish)
    if prompt is None or completion is None:
        usage["prompt_tokens"] = prompt if prompt is not None else request_estimate
        usage["completion_tokens"] = completion if completion is not None else _estimate_tokens([text, stored])
        usage["estimated"] = True
    return assistant, calls, usage


def _wire_tool(tool: dict) -> dict:
    """A function that takes no arguments goes out without a `parameters` object. OpenAI treats that as an empty
    parameter list, while an empty `properties` is rejected by some endpoints (Gemini's, notably)."""
    fn = tool.get("function") or {}
    params = fn.get("parameters")
    if isinstance(params, dict) and not params.get("properties"):
        return {**tool, "function": {k: v for k, v in fn.items() if k != "parameters"}}
    return tool


def _chat_openai_compat(provider: str, name: str, messages: list[dict], tools: list[dict]):
    url, key, host = _resolve_compat(provider)
    body: dict = {"model": name, "messages": _oa_messages(messages, host)}
    if tools:
        body["tools"] = [_wire_tool(t) for t in tools]
    max_tokens = _env_num("RW_MAX_TOKENS", int)
    if max_tokens:
        body["max_completion_tokens" if host == "api.openai.com" else "max_tokens"] = max_tokens
    temperature = _env_num("RW_TEMPERATURE", float)
    if temperature is not None:
        body["temperature"] = temperature
    body.update(_extra_body())
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    timeout = _env_num("RW_TIMEOUT", float, 600.0)
    retries = _env_num("RW_RETRIES", int, 8)
    estimate = _estimate_tokens([body["messages"], tools])

    def once():
        return _parse_openai(_post_json(url, headers, body, timeout), host, estimate)

    (assistant, calls, usage), attempts = _with_retries(once, retries)
    usage["attempts"] = attempts
    return assistant, calls, usage


# ---------------------------------------------------------------- Anthropic adapter

def _to_anthropic(messages: list[dict], cache: bool = True) -> tuple[list[dict], list[dict]]:
    """Canonical messages to (system blocks, Anthropic messages). Tool results are merged into one user turn and
    come before any text in it; the last block gets a cache breakpoint."""
    system_parts: list[str] = []
    out: list[dict] = []

    def push(role: str, blocks: list[dict]) -> None:
        if out and out[-1]["role"] == role:
            out[-1]["content"].extend(blocks)
        else:
            out.append({"role": role, "content": list(blocks)})

    for m in messages:
        role = m.get("role")
        if role == "system":
            system_parts.append(_text(m.get("content")))
        elif role == "user":
            text = _text(m.get("content"))
            push("user", [{"type": "text", "text": text if text.strip() else "(empty)"}])
        elif role == "assistant":
            # extended thinking: the model's own thinking blocks go back first and untouched, or tool use is refused
            blocks: list[dict] = [dict(b) for b in m.get("_thinking_blocks") or [] if isinstance(b, dict)]
            text = _text(m.get("content"))
            if text.strip():
                blocks.append({"type": "text", "text": text})
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                _, args, _ = _parse_args(fn.get("arguments"))
                if args is None:
                    args = {"_raw_arguments": str(fn.get("arguments"))}
                blocks.append({"type": "tool_use", "id": tc.get("id"), "name": fn.get("name"), "input": args})
            push("assistant", blocks or [{"type": "text", "text": "(empty response)"}])
        elif role == "tool":
            block = {"type": "tool_result", "tool_use_id": m.get("tool_call_id"),
                     "content": _text(m.get("content")) or "(no output)"}
            if m.get("_error"):
                block["is_error"] = True
            push("user", [block])
        else:
            raise LLMError(f"unknown message role {role!r}")
    if out and out[0]["role"] != "user":
        out.insert(0, {"role": "user", "content": [{"type": "text", "text": "(start)"}]})
    system: list[dict] = []
    if any(p.strip() for p in system_parts):
        system = [{"type": "text", "text": "\n\n".join(system_parts)}]
        if cache:
            system[0]["cache_control"] = {"type": "ephemeral"}
    if cache and out:
        out[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
    return system, out


def _parse_anthropic(data: dict) -> tuple[dict, list[dict], dict]:
    if data.get("type") == "error" or ("content" not in data and data.get("error")):
        err = data.get("error") or {}
        kind = err.get("type") if isinstance(err, dict) else None
        raise LLMError(f"Anthropic error: {_redact(str(err.get('message') if isinstance(err, dict) else err))[:500]}",
                       retryable=kind in ("overloaded_error", "api_error", "rate_limit_error"))
    blocks = data.get("content")
    if not isinstance(blocks, list):
        raise LLMError("the response had no content list", retryable=True)
    text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    seen: set = set()
    stored, calls = [], []
    for n, b in enumerate((b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"), 1):
        tid = _unique_id(b.get("id"), seen, n)
        args = b.get("input") if isinstance(b.get("input"), dict) else {}
        stored.append({"id": tid, "type": "function", "function": {"name": b.get("name") or "", "arguments": json.dumps(args)}})
        calls.append({"id": tid, "name": b.get("name") or "", "arguments": args, "error": None})
    assistant: dict = {"role": "assistant", "content": text or None}
    if stored:
        assistant["tool_calls"] = stored
    thinking = [dict(b) for b in blocks if isinstance(b, dict) and b.get("type") in ("thinking", "redacted_thinking")]
    if thinking:
        assistant["_thinking_blocks"] = thinking  # replayed by _to_anthropic; not part of any other provider's request
    u = data.get("usage") or {}
    inp = _int_or_none(u.get("input_tokens")) or 0
    read = _int_or_none(u.get("cache_read_input_tokens")) or 0
    write = _int_or_none(u.get("cache_creation_input_tokens")) or 0
    # Anthropic reports uncached input separately; the harness reports prompt tokens the way OpenAI does (all input).
    usage = _usage(inp + read + write, _int_or_none(u.get("output_tokens")) or 0, read, write, None, None, False,
                   data.get("stop_reason"))
    return assistant, calls, usage


def _chat_anthropic(name: str, messages: list[dict], tools: list[dict]):
    key = _env("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("ANTHROPIC_API_KEY is not set")
    base = (_env("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
    url = base + "/messages" if base.endswith("/v1") else base + "/v1/messages"
    system, msgs = _to_anthropic(messages, cache=(_env("RW_ANTHROPIC_CACHE") or "1") != "0")
    body: dict = {"model": name, "max_tokens": _env_num("RW_MAX_TOKENS", int, 16000), "messages": msgs}
    if system:
        body["system"] = system
    if tools:
        body["tools"] = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                          "input_schema": t["function"].get("parameters") or {"type": "object", "properties": {}}}
                         for t in tools]
    temperature = _env_num("RW_TEMPERATURE", float)
    if temperature is not None:
        body["temperature"] = temperature
    body.update(_extra_body())
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    timeout = _env_num("RW_TIMEOUT", float, 600.0)
    retries = _env_num("RW_RETRIES", int, 8)

    def once():
        return _parse_anthropic(_post_json(url, headers, body, timeout))

    (assistant, calls, usage), attempts = _with_retries(once, retries)
    usage["attempts"] = attempts
    return assistant, calls, usage


# ---------------------------------------------------------------- mock adapter

_MOCK_CACHE: dict = {}
_MOCK_LOCK = threading.Lock()
_ROLE_RE = re.compile(r"\*\*(extractor|reconciler|scheduler|auditor|principal)\*\*|\[mock-role:\s*([\w-]+)\]")


def _load_mock(path: str) -> dict:
    p = Path(path)
    try:
        stamp = (str(p.resolve()), p.stat().st_mtime_ns)
    except OSError as e:
        raise LLMError(f"mock script {path!r} not readable: {e}") from None
    with _MOCK_LOCK:
        hit = _MOCK_CACHE.get(stamp[0])
        if hit and hit[0] == stamp[1]:
            return hit[1]
        try:
            script = json.loads(p.read_text())
        except ValueError as e:
            raise LLMError(f"mock script {path!r} is not valid JSON: {e}") from None
        _MOCK_CACHE[stamp[0]] = (stamp[1], script)
        return script


def _chat_mock(path: str, messages: list[dict], tools: list[dict]):
    script = _load_mock(path)
    role = "*"
    for m in messages:
        if m.get("role") == "system":
            mo = _ROLE_RE.search(_text(m.get("content")))
            role = (mo.group(1) or mo.group(2)) if mo else "*"
            break
    turn, step = -1, 0
    for m in messages:
        if m.get("role") == "user":
            turn, step = turn + 1, 0
        elif m.get("role") == "assistant":
            step += 1
    turn = max(turn, 0)
    agents = script.get("agents", {})
    turns = agents.get(role) or agents.get("*") or []
    try:
        entry = turns[turn]
        entry = [entry] if isinstance(entry, dict) else entry
        resp = entry[step]
    except IndexError:
        resp = script.get("default", {"content": "DONE"})
    text = resp.get("content")
    stored, calls = [], []
    for i, c in enumerate(resp.get("tool_calls") or []):
        tid = c.get("id") or f"mock_{turn}_{step}_{i}"
        arg_str, args, error = _parse_args(c.get("arguments", {}))
        stored.append({"id": tid, "type": "function", "function": {"name": c.get("name", ""), "arguments": arg_str}})
        calls.append({"id": tid, "name": c.get("name", ""), "arguments": args, "error": error})
    assistant: dict = {"role": "assistant", "content": text or None}
    if stored:
        assistant["tool_calls"] = stored
    su = resp.get("usage")
    if su:
        usage = _usage(su.get("prompt_tokens", 0), su.get("completion_tokens", 0), su.get("cached_tokens"),
                       su.get("cache_write_tokens"), su.get("reasoning_tokens"), su.get("cost"), False,
                       "tool_calls" if stored else "stop")
    else:
        usage = _usage(_estimate_tokens([messages, tools]), _estimate_tokens([text, stored]), None, None, None, None, True,
                       "tool_calls" if stored else "stop")
    return assistant, calls, usage


# ---------------------------------------------------------------- public entry point

def parse_model(model: str) -> tuple[str, str]:
    provider, sep, name = (model or "").partition(":")
    provider, name = provider.strip().lower(), name.strip()
    if not sep or not name:
        raise LLMError(f"model {model!r} must look like provider:name, for example openrouter:openai/gpt-5.6, "
                       f"openai:gpt-5.6, compat:qwen3 (with RW_BASE_URL), anthropic:claude-sonnet-4-6 or mock:script.json")
    return provider, name


def preflight(model: str) -> None:
    """Fail before any money is spent: the model string, the key and the endpoint are checked without a request."""
    provider, name = parse_model(model)
    if provider == "mock":
        _load_mock(name)
    elif provider in OPENAI_COMPAT:
        _resolve_compat(provider)
        _extra_body()
    elif provider == "anthropic":
        if not _env("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY is not set")
        _extra_body()
    else:
        raise LLMError(f"unknown provider {provider!r} in {model!r}; use openrouter, openai, compat, anthropic or mock")


def endpoint_host(model: str) -> str:
    """Host name the model string will talk to (for provenance records; never includes credentials)."""
    provider, _ = parse_model(model)
    if provider == "mock":
        return "mock"
    if provider == "anthropic":
        return urllib.parse.urlparse(_env("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").hostname or "unknown"
    base = _env("RW_BASE_URL") or DEFAULT_BASES.get(provider) or ""
    return urllib.parse.urlparse(base).hostname or "unknown"


def chat(messages: list[dict], tools: list[dict], model: str) -> tuple[dict, list[dict], dict]:
    """One model call. Returns (assistant_message, tool_calls, usage); see the module docstring."""
    provider, name = parse_model(model)
    t0 = time.time()
    if provider == "mock":
        assistant, calls, usage = _chat_mock(name, messages, tools)
    elif provider in OPENAI_COMPAT:
        assistant, calls, usage = _chat_openai_compat(provider, name, messages, tools)
    elif provider == "anthropic":
        assistant, calls, usage = _chat_anthropic(name, messages, tools)
    else:
        raise LLMError(f"unknown provider {provider!r} in {model!r}; use openrouter, openai, compat, anthropic or mock")
    usage["latency_s"] = round(time.time() - t0, 3)
    usage["model"] = model
    usage.setdefault("attempts", 1)
    return assistant, calls, usage
