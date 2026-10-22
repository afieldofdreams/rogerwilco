#!/usr/bin/env python3
"""Run the chains, text only: every agent is one chat conversation with no tools, hop by hop.

  run.py [--only SUBSTR[,SUBSTR]] [--models a,b] [--jobs N] [--redo] [--reset] [--limit N] [--list] [--exclude SUFFIX[,SUFFIX]] [--server URL]

Hop 0 is code: its message is delivered into hop 1's inbox. Each agent's brief is its system prompt; its first user turn
carries its inbox with the live message, its context file inline, and the reply instruction; its reply is the message
(prose arms: the text as it stands; line arms: the first RW1 line, else the first non-empty line), or ASK and a question,
or, for the payer, the act block the harness executes. The harness's later messages (the AN, a re-issued HO, a pre-send
refusal, an act refusal) are later user turns of the same conversation and are appended to the agent's inbox.

Backends: local models load in-process through llama_cpp (tools/serve.py), one model at a time, one chain at a time, at
temperature 0; the anchors run through headless `claude -p` (text only, no tools, --session-id then --resume) from an
empty directory outside the repository, with --jobs chains in parallel; --server URL sends local chains through
research/harness/llm.py's compat: adapter to a server tools/serve.py started. Everything the models said and every usage
record goes to <trial>/turns.json with wall seconds; every message between agents to <trial>/chain.json; the model file's
sha256 or the API's model id, the harness commit, the llama_cpp version and the sampling to <trial>/manifest.json.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import gc
import hashlib
import importlib.util
import json
import os
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
import build as B  # noqa: E402

TURN_TIMEOUT = 600
MAX_TURNS = 7
CLAUDE_CWD = Path(os.environ.get("RW_CLAUDE_CWD", str(Path.home() / ".cache" / "rogerwilco-breaking" / "cwd")))
HARNESS_LLM = C.REPO / "research" / "harness" / "llm.py"
CLI_VERSION = ""
HARNESS_COMMIT = ""


def git_short(path: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(path), capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "?"

# ----------------------------------------------------------------------------------------------------- backends

class LocalBackend:
    kind = "local"

    def __init__(self, alias: str):
        import serve as S
        self.alias = alias
        self.model = S.LocalModel(alias)
        self.desc = {"backend": "llama_cpp in-process", **self.model.describe(), "load_seconds": self.model.load_seconds}

    def describe(self) -> dict:
        return self.desc

    def conversation(self, system: str, cwd: Path):
        return LocalConversation(self.model, system)

    def close(self) -> None:
        self.model.close(); self.model = None; gc.collect()


class LocalConversation:
    def __init__(self, model, system: str):
        self.model = model
        self.messages = [{"role": "system", "content": system}]

    def send(self, text: str) -> dict:
        self.messages.append({"role": "user", "content": text})
        try:
            r = self.model.chat(self.messages)
        except Exception as e:  # noqa: BLE001
            self.messages.pop()
            return {"error": f"{type(e).__name__}: {str(e)[:300]}", "seconds": 0}
        self.messages.append({"role": "assistant", "content": r["text"]})
        return {"reply": r["text"], "usage": r["usage"], "finish_reason": r["finish_reason"], "seconds": r["seconds"]}


class CompatBackend:
    """The same local model through tools/serve.py's server and research/harness/llm.py (compat:<alias>)."""
    kind = "compat"

    def __init__(self, alias: str, url: str):
        self.alias = alias
        os.environ["RW_BASE_URL"] = url
        os.environ.setdefault("RW_TEMPERATURE", "0")
        os.environ.setdefault("RW_MAX_TOKENS", "500")
        spec = importlib.util.spec_from_file_location("rw_llm", HARNESS_LLM)
        self.llm = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.llm)
        import urllib.request
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url.rstrip("/") + "/models", timeout=30) as resp:
            served = json.loads(resp.read())
        self.desc = {"backend": f"compat via research/harness/llm.py at {url}", "served": served.get("data"),
                     "temperature": float(os.environ["RW_TEMPERATURE"]), "max_tokens": int(os.environ["RW_MAX_TOKENS"])}

    def describe(self) -> dict:
        return self.desc

    def conversation(self, system: str, cwd: Path):
        return CompatConversation(self.llm, self.alias, system)

    def close(self) -> None:
        pass


class CompatConversation:
    def __init__(self, llm, alias: str, system: str):
        self.llm, self.alias = llm, alias
        self.messages = [{"role": "system", "content": system}]

    def send(self, text: str) -> dict:
        self.messages.append({"role": "user", "content": text})
        try:
            assistant, _, usage = self.llm.chat(self.messages, [], f"compat:{self.alias}")
        except Exception as e:  # noqa: BLE001
            self.messages.pop()
            return {"error": f"{type(e).__name__}: {str(e)[:300]}", "seconds": 0}
        self.messages.append(assistant)
        return {"reply": (assistant.get("content") or "").strip(), "usage": usage, "finish_reason": usage.get("finish_reason"), "seconds": usage.get("latency_s")}


class ClaudeBackend:
    kind = "claude"

    def __init__(self, alias: str):
        self.alias = alias
        self.model = C.MODELS[alias]["id"]
        CLAUDE_CWD.mkdir(parents=True, exist_ok=True)

    def describe(self) -> dict:
        return {"backend": f"claude -p {CLI_VERSION}, text only, no tools, cwd outside the repository", "model_requested": self.model,
                "temperature": "provider default", "max_tokens": "provider default"}

    def conversation(self, system: str, cwd: Path):
        return ClaudeConversation(self.model, system)

    def close(self) -> None:
        pass


class ClaudeConversation:
    def __init__(self, model: str, system: str):
        self.model, self.system = model, system
        self.session = str(uuid.uuid4())
        self.started = False

    def send(self, text: str) -> dict:
        cmd = ["claude", "-p", "--model", self.model, "--output-format", "json", "--allowedTools", "", "--exclude-dynamic-system-prompt-sections",
               "--resume" if self.started else "--session-id", self.session, "--system-prompt", self.system]
        t0 = time.time()
        for attempt in (1, 2):
            try:
                proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=TURN_TIMEOUT, cwd=str(CLAUDE_CWD))
            except subprocess.TimeoutExpired:
                if attempt == 1:
                    continue
                return {"error": "timeout", "seconds": round(time.time() - t0, 1)}
            try:
                data = json.loads(proc.stdout)
            except ValueError:
                if attempt == 1:
                    time.sleep(5); continue
                return {"error": "no json", "stdout": proc.stdout[-1500:], "stderr": proc.stderr[-1500:], "seconds": round(time.time() - t0, 1)}
            if data.get("is_error") and attempt == 1:
                time.sleep(8); continue
            self.started = True
            return {"reply": (data.get("result") or "").strip(), "session": data.get("session_id"), "usage": data.get("usage"),
                    "models": data.get("modelUsage"), "cost": data.get("total_cost_usd"), "seconds": round(time.time() - t0, 1),
                    "is_error": data.get("is_error", False), "finish_reason": data.get("stop_reason")}
        return {"error": "gave up", "seconds": round(time.time() - t0, 1)}


def backend_for(alias: str, server: str | None):
    kind = C.MODELS[alias]["kind"]
    if kind == "claude":
        return ClaudeBackend(alias)
    if server:
        return CompatBackend(alias, server)
    return LocalBackend(alias)

# ----------------------------------------------------------------------------------------------------- files and inboxes

TRIAL_FILES = ("chain.json", "turns.json", "manifest.json", "grade.json")


def reset_trial(trial: Path) -> None:
    """Back to the built state: every agent's outputs removed, the inboxes re-rendered without the live message, the master restored, the act log cleared."""
    meta = C.read_json(trial / "meta.json")
    state = C.sender_state(meta["id"])
    for f in TRIAL_FILES:
        if (trial / f).exists():
            (trial / f).unlink()
    for h, hop in state["hops"].items():
        d = trial / f"hop{h}"
        for extra in d.iterdir():
            if extra.is_file() and extra.name != hop["context_file"]:
                extra.unlink()
        (d / "inbox.md").write_text(B.render_inbox(hop["inbox"], state["arm"], hop["agent"], None))
        if hop["role"] == "payer":
            master = C.SENDER / f"{meta['id']}.master.json"
            if master.exists():
                (d / "supplier_bank.json").write_text(master.read_text())
    log = C.SENDER / f"{meta['id']}.actlog.json"
    if log.exists():
        log.unlink()


def deliver(trial: Path, state: dict, chain: dict, h: int, frm: str, text: str) -> None:
    """The message for hop h arrives: the inbox is rendered with it in the live slot (never last)."""
    hop = state["hops"][str(h)]
    when = f"{C.TODAY} 09:{30 + 2 * h:02d}"
    live = {"from": frm, "text": text, "when": when}
    (trial / f"hop{h}" / "inbox.md").write_text(B.render_inbox(hop["inbox"], state["arm"], hop["agent"], live))
    chain["delivered"][str(h)] = {"from": frm, "to": hop["agent"], "text": text, "tokens": C.count_tokens(text), "when": when, "reissued": None, "final": text}
    chain["traffic"].append({"hop": h, "from": frm, "to": hop["agent"], "kind": "deliver", "text": text, "tokens": C.count_tokens(text)})


def append_inbox(trial: Path, chain: dict, h: int, frm: str, to: str, text: str) -> None:
    inbox = trial / f"hop{h}" / "inbox.md"
    body = inbox.read_text()
    n = body.count("\n## ") + 1
    chain["clock"] = chain.get("clock", 0) + 1
    stamp = f"{C.TODAY} 11:{10 + 2 * chain['clock']:02d}"
    inbox.write_text(body.rstrip("\n") + f"\n\n## {n}. {stamp} from {frm} to {to}\n{text}\n")


def next_id(chain: dict, agent: str) -> str:
    n = chain["counters"].get(agent, 50) + 1
    chain["counters"][agent] = n
    return f"{agent}-{n}"


def record_traffic(chain: dict, h: int, frm: str, to: str, kind: str, text: str) -> None:
    chain["traffic"].append({"hop": h, "from": frm, "to": to, "kind": kind, "text": text, "tokens": C.count_tokens(text or "")})

# ----------------------------------------------------------------------------------------------------- the turns

CONTEXT_NAME = {"coordinator": "your run schedule (schedule.json)", "desk": "the approvals log (approvals.json)", "relay": None,
                "payer": "the supplier master (supplier_bank.json)"}


def instruction(arm: str, role: str, nxt: str | None, step: str) -> str:
    """The reply instruction, repeated from the brief's procedure. step: first | forward | act."""
    ask_prose = "or reply ASK on the first line and your question below it"
    ask_line = "or reply ASK on the first line and one AQ or UN line below it"
    if role == "payer":
        act = f"Reply with the act block (ACT on the first line, then one key: value per line) and nothing else, {ask_prose if arm in C.PROSE_ARMS else ask_line}."
        if step == "act" or arm not in C.CHECKED_ARMS:
            return act
    else:
        if arm in C.PROSE_ARMS:
            fwd = f"Reply with the message you forward to {nxt}, and nothing else, {ask_prose}."
        else:
            fwd = f"Reply with the one HO line you forward to {nxt}, and nothing else, {ask_line}."
        if step == "forward" or arm not in C.CHECKED_ARMS:
            return fwd
    if arm == "R":
        return f"Reply with your readback of the HO, one RB line, and nothing else, and wait for the reply; {ask_line}."
    return f"Reply CONFIRM if every value in the readback is what the HO in your inbox carries (the readback repeats neither rb= nor the tail, by design), or DISPUTE: <slot> <value> if one is not; {ask_line}."


def first_turn(trial: Path, state: dict, h: int, rb_line: str | None) -> str:
    hop = state["hops"][str(h)]
    me, prev, nxt, role, arm = hop["agent"], hop["prev"], hop["next"], hop["role"], state["arm"]
    d = trial / f"hop{h}"
    who = f"You are the agent named {me}; the agent before you in the chain is {prev}" + (f" and the agent after you is {nxt}." if nxt else ".")
    ctx_name = CONTEXT_NAME[role]
    parts = [f"{who} You have been woken because new mail arrived. Your inbox follows" + (f", then {ctx_name}." if ctx_name else ".") +
             " Deal with the newest handover addressed to you that has not been dealt with, following your procedure.", "",
             (d / "inbox.md").read_text().rstrip()]
    if hop["context_file"]:
        parts += ["", f"# {hop['context_file']}", json.dumps(C.read_json(d / hop["context_file"]), indent=1)]
    parts += ["", "# Your reply"]
    if rb_line:
        parts += ["Your code composed this readback from the newest handover as delivered to you:", rb_line, ""]
    parts.append(instruction(arm, role, nxt, "first"))
    return "\n".join(parts) + "\n"


def transcript_add(d: Path, n: int, sent: str, reply: str) -> None:
    with open(d / "transcript.md", "a") as f:
        f.write(f"## turn {n}\n\n### user\n\n{sent.rstrip()}\n\n### assistant\n\n{(reply or '').rstrip()}\n\n")

# ----------------------------------------------------------------------------------------------------- one chain

def run_chain(trial: Path, backend) -> str:
    meta = C.read_json(trial / "meta.json")
    state = C.sender_state(meta["id"])
    arm, Kn, act, rec = state["arm"], state["K"], state["act"], state["record"]
    agents = state["agents"]
    turns: list = []
    chain = {"id": meta["id"], "arm": arm, "K": Kn, "agents": agents, "delivered": {}, "traffic": [], "checks": {}, "counters": {},
             "ended": None, "status": "ok", "flags": []}
    status = "ok"
    ended = None
    t_chain = time.time()
    session_seconds: dict = {}
    brief_sha_run: dict = {}

    def end(h: int, how: str, detail: str = "") -> None:
        nonlocal ended
        ended = {"hop": h, "how": how, "detail": detail}

    try:
        deliver(trial, state, chain, 1, "scheduler", K.first_message(state))
        for h in range(1, Kn + 2):
            hop = state["hops"][str(h)]
            me, prev, nxt, role = hop["agent"], hop["prev"], hop["next"], hop["role"]
            d = trial / f"hop{h}"
            system = (C.ROOT / meta["hops"][str(h)]["brief"]).read_text()
            brief_sha_run[str(h)] = hashlib.sha256(system.encode()).hexdigest()[:12]
            conv = backend.conversation(system, d)
            checks = chain["checks"].setdefault(str(h), {"rb": None, "rb2": None, "confirm": [], "forward": []})
            n = 0
            outcome = None          # forwarded | done | asked | held | stalled | error

            def say(text: str) -> dict:
                nonlocal n
                n += 1
                r = conv.send(text)
                turns.append({"hop": h, "agent": me, "turn": n, "sent": text, **r})
                transcript_add(d, n, text, r.get("reply", f"[error: {r.get('error')}]"))
                session_seconds[str(h)] = round(session_seconds.get(str(h), 0) + (r.get("seconds") or 0), 1)
                return r

            # the readback, before anything else, in the checked arms
            rb_line = None
            if arm == "C":
                try:
                    rb_line = K.code_readback(chain["delivered"][str(h)]["final"], me, 1)
                except Exception as e:  # noqa: BLE001
                    status = f"harness: make-rb failed at hop {h}: {e}"; end(h, "error", status); break
                (d / "rb.txt").write_text(rb_line + "\n")
                record_traffic(chain, h, me, prev, "rb", rb_line)
            first = first_turn(trial, state, h, rb_line)
            (d / "prompt.txt").write_text(first)
            r = say(first)
            if "error" in r:
                status = f"{me} error at hop {h}: {r['error']}"; end(h, "error", r["error"]); break
            stage = "readback" if arm in C.CHECKED_ARMS else ("act" if role == "payer" else "forward")
            nudged = False
            rb_second = False
            forward_refused = False
            act_refused = False
            while n <= MAX_TURNS and outcome is None:
                reply = r.get("reply", "")
                if K.is_ask(reply):
                    (d / "question.txt").write_text(K.question_of(reply) + "\n")
                    record_traffic(chain, h, me, prev, "question", K.question_of(reply))
                    outcome = "asked"; break
                # ---- the readback stage (R: the model's RB line; C: CONFIRM or DISPUTE on the code's RB)
                if stage == "readback":
                    ho = chain["delivered"][str(h)]["final"]
                    if arm == "R":
                        kind = "rb2" if rb_second else "rb"
                        rbl = K.line_from(reply)
                        (d / f"{kind}.txt").write_text(rbl + "\n")
                        rc = K.check_readback(ho, rbl, act, rec, waive_digest=True)
                        checks[kind] = rc
                        record_traffic(chain, h, me, prev, kind, rbl)
                        if not rc["ok"] and rb_second:
                            outcome = "held"; status = f"held: hop {h} ({me}): readback rejected twice"; break
                        if rc["ok"]:
                            an = K.an_line(prev, me, next_id(chain, prev), rc["rb_id"] or f"{me}-1", role)
                            record_traffic(chain, h, prev, me, "an", an)
                            append_inbox(trial, chain, h, prev, me, an)
                            stage = "act" if role == "payer" else "forward"
                            r = say(f"Message from {prev}:\n{an}\n\n{instruction(arm, role, nxt, stage)}")
                        else:
                            re_ho = K.reissue_line(ho, next_id(chain, prev), rc["rb_id"], rc["problems"])
                            chain["delivered"][str(h)]["reissued"] = re_ho; chain["delivered"][str(h)]["final"] = re_ho
                            record_traffic(chain, h, prev, me, "reissue", re_ho)
                            append_inbox(trial, chain, h, prev, me, re_ho)
                            rb_second = True
                            r = say(f"Message from {prev}:\n{re_ho}\n\nThis is the HO again, re-issued because your readback did not match it: "
                                    f"reply with your readback of this HO, one RB line (id {me}-2), and nothing else.")
                    else:  # C
                        pc = K.parse_confirm(reply)
                        rbl = (d / ("rb2.txt" if rb_second else "rb.txt")).read_text().strip()
                        if pc["answer"] == "other":
                            if nudged:
                                outcome = "stalled"; status = f"{me} replied neither CONFIRM nor DISPUTE twice at hop {h}: {reply[:80]!r}"; break
                            nudged = True
                            r = say("Your reply was not what your procedure asks for at this step. " + instruction(arm, role, nxt, "first"))
                            continue
                        if pc["answer"] == "confirm":
                            rc = {"ok": True, "problems": [], "notes": [], "kind": None, "rb": rbl, "rb_id": f"{me}-{2 if rb_second else 1}", "by": "code", "answer": "confirm"}
                            checks["rb2" if rb_second else "rb"] = rc
                            checks["confirm"].append({"answer": "confirm"})
                            an = K.an_line(prev, me, next_id(chain, prev), rc["rb_id"], role)
                            record_traffic(chain, h, prev, me, "an", an)
                            append_inbox(trial, chain, h, prev, me, an)
                            stage = "act" if role == "payer" else "forward"
                            r = say(f"Message from {prev}:\n{an}\n\n{instruction(arm, role, nxt, stage)}")
                        else:  # dispute
                            dc = K.check_dispute(ho, rbl, pc["slot"], pc["value"])
                            dc["answer"] = "dispute"
                            checks["rb2" if rb_second else "rb"] = dc
                            checks["confirm"].append({"answer": "dispute", "catch": dc["catch"], **dc["dispute"]})
                            if dc["catch"]:
                                outcome = "held"; status = f"held: hop {h} ({me}): disputed the readback on {pc['slot']} and the readback did not match the HO"; break
                            if rb_second:
                                outcome = "held"; status = f"held: hop {h} ({me}): disputed the readback twice with every value right"; break
                            re_ho = K.reissue_line(ho, next_id(chain, prev), dc["rb_id"], dc["problems"])
                            chain["delivered"][str(h)]["reissued"] = re_ho; chain["delivered"][str(h)]["final"] = re_ho
                            rb2 = K.code_readback(re_ho, me, 2)
                            (d / "rb2.txt").write_text(rb2 + "\n")
                            record_traffic(chain, h, prev, me, "reissue", re_ho)
                            record_traffic(chain, h, me, prev, "rb2", rb2)
                            append_inbox(trial, chain, h, prev, me, re_ho)
                            rb_second = True
                            r = say(f"Message from {prev}:\n{re_ho}\n\nThe HO again: your dispute named a value the readback carries exactly as the HO carries it. "
                                    f"Your code composed this readback from it:\n{rb2}\n\n{instruction(arm, role, nxt, 'first')}")
                    if "error" in r:
                        status = f"{me} error at hop {h} turn {n}: {r['error']}"; end(h, "error", r["error"]); outcome = "error"
                    continue
                # ---- the forward (relays)
                if stage == "forward":
                    out_text = K.line_from(reply) if arm in C.LINE_ARMS else reply.strip()
                    if not out_text:
                        outcome = "stalled"; status = f"{me} replied nothing at hop {h}"; break
                    (d / "out.txt").write_text(out_text + "\n")
                    if arm in C.CHECKED_ARMS:
                        ctx = C.read_json(d / hop["context_file"]) if hop["context_file"] else None
                        fc = K.check_forward(chain["delivered"][str(h)]["final"], out_text, role, me, nxt, act, rec, ctx)
                        fc["out"] = out_text
                        checks["forward"].append(fc)
                        if not fc["ok"]:
                            record_traffic(chain, h, me, nxt, "forward-refused", out_text)
                            if forward_refused:
                                outcome = "held"; status = f"held: hop {h} ({me}): forwarded line refused twice"; break
                            forward_refused = True
                            append_inbox(trial, chain, h, "pre-send check", me, fc["reply"])
                            record_traffic(chain, h, "pre-send check", me, "refusal", fc["reply"])
                            r = say("Message from your pre-send check:\n\n" + fc["reply"])
                            if "error" in r:
                                status = f"{me} error at hop {h} turn {n}: {r['error']}"; end(h, "error", r["error"]); outcome = "error"
                            continue
                    elif arm == "L":
                        msg, errs, _ = C.codec().parse(out_text, "pay")
                        checks["forward"].append({"ok": not errs, "problems": [f"syntax: {e}" for e in errs], "notes": [], "kind": "formal" if errs else None, "out": out_text, "delivered_as_written": True})
                        if errs:
                            chain["flags"].append(f"hop {h}: {me} forwarded a line that does not parse; delivered as written")
                    outcome = "forwarded"
                    deliver(trial, state, chain, h + 1, me, out_text)
                    break
                # ---- the act (payer)
                blk = K.parse_act_block(reply)
                if blk is None:
                    if nudged:
                        outcome = "stalled"; status = f"payer replied neither ACT nor ASK twice: {reply[:80]!r}"; break
                    nudged = True
                    r = say("Your reply was not what your procedure asks for. " + instruction(arm, role, nxt, "act"))
                    if "error" in r:
                        status = f"{me} error at hop {h} turn {n}: {r['error']}"; end(h, "error", r["error"]); outcome = "error"
                    continue
                (d / "act.txt").write_text(reply.strip() + "\n")
                if blk["second"]:
                    chain["flags"].append(f"hop {h}: the payer's reply carried a second ACT block; only the first was read")
                reason = K.validate_act(blk["values"], act)
                result = K.execute_act(trial, state, blk["values"]) if reason is None else {"status": "REFUSED", "reason": reason}
                checks.setdefault("act", []).append({"values": blk["values"], "result": result})
                record_traffic(chain, h, me, prev, "act", reply.strip())
                if result["status"] == "REFUSED":
                    if act_refused:
                        outcome = "stalled"; status = f"act block refused twice: {result['reason'][:100]}"; break
                    act_refused = True
                    text = K.act_refusal_text(result["reason"])
                    append_inbox(trial, chain, h, "your code", me, text)
                    record_traffic(chain, h, "code", me, "act-refusal", text)
                    r = say("Message from your code:\n\n" + text)
                    if "error" in r:
                        status = f"{me} error at hop {h} turn {n}: {r['error']}"; end(h, "error", r["error"]); outcome = "error"
                    continue
                outcome = "done"
                break
            if outcome is None:
                status = f"turn limit at hop {h}"; outcome = "stalled"
            if outcome == "forwarded":
                continue
            if outcome == "done":
                end(h, "done")
            elif outcome in ("asked", "held", "stalled"):
                end(h, outcome, status if outcome != "asked" else "")
            break
    finally:
        chain["status"] = status
        chain["ended"] = ended or {"hop": None, "how": "error", "detail": status}
        models_seen = sorted({m for t in turns if isinstance(t.get("models"), dict) for m in t["models"]})
        cost = sum(t.get("cost") or 0 for t in turns)
        C.write_json(trial / "chain.json", chain)
        C.write_json(trial / "turns.json", {"status": status, "ended": chain["ended"], "turns": turns})
        C.write_json(trial / "manifest.json", {
            "id": meta["id"], "model_alias": state["model"], "model": backend.describe(), "models_seen": models_seen,
            "harness_commit": HARNESS_COMMIT, "brief_sha": state["brief_sha"], "brief_sha_run": brief_sha_run, "tokenizer": C.TOKENIZER,
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cost_usd": round(cost, 4),
            "wall_seconds": round(time.time() - t_chain, 1), "session_seconds": session_seconds,
            "sessions": len({t["hop"] for t in turns}), "model_turns": len(turns), "status": status, "ended": chain["ended"],
        })
    return status

# ----------------------------------------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    global CLI_VERSION, HARNESS_COMMIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring of the chain id; several, comma-separated, must all match")
    ap.add_argument("--models", default="", help="model aliases to run, comma-separated (default: every model with built chains)")
    ap.add_argument("--jobs", type=int, default=4, help="chains in parallel for the anchors; local models run one at a time")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--reset", action="store_true", help="with --redo: return the selected chains to their built state first")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--exclude", default="", help="skip chains whose id ends with any of these, comma-separated (the speed test's -s, the pilot's -p)")
    ap.add_argument("--server", default="", help="send local chains to a tools/serve.py server at this base URL instead of loading in-process")
    a = ap.parse_args(argv)
    try:
        CLI_VERSION = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30).stdout.strip().split()[0]
    except Exception:  # noqa: BLE001
        CLI_VERSION = "?"
    HARNESS_COMMIT = git_short(C.ROOT)
    needles = [x for x in a.only.split(",") if x]
    skip = [x for x in a.exclude.split(",") if x]
    want = [m for m in a.models.split(",") if m]
    trials = [t for t in sorted(C.TRIALS.iterdir()) if t.is_dir() and all(n in t.name for n in needles) and not any(t.name.endswith(x) for x in skip)
              and (a.redo or not (t / "turns.json").exists())]
    trials = [t for t in trials if not want or C.read_json(t / "meta.json")["model"] in want]
    if a.limit:
        trials = trials[:a.limit]
    if a.list:
        print("\n".join(t.name for t in trials)); return 0
    if a.reset:
        for t in trials:
            reset_trial(t)
        print(f"reset {len(trials)} chains", flush=True)
    by_model: dict[str, list] = {}
    for t in trials:
        by_model.setdefault(C.read_json(t / "meta.json")["model"], []).append(t)
    order = [m for m in C.MODEL_ORDER if m in by_model]
    print(f"{len(trials)} chains over {len(order)} models ({', '.join(order)}); anchors {a.jobs} at a time, local models one at a time; cli {CLI_VERSION}, commit {HARNESS_COMMIT}", flush=True)
    bad = 0
    done = 0
    t0 = time.time()

    def report(t: Path, status: str) -> None:
        nonlocal bad, done
        done += 1
        if status != "ok":
            bad += 1
        ended = C.read_json(t / "chain.json").get("ended") or {} if (t / "chain.json").exists() else {}
        how = f"{ended.get('how')} at hop {ended.get('hop')}" if ended else "?"
        print(f"[{done}/{len(trials)} {round(time.time() - t0)}s] {t.name:48s} {how}; {status}", flush=True)

    for alias in sorted(order, key=lambda m: (C.MODELS[m]["kind"] != "claude", C.MODEL_ORDER.index(m))):   # anchors first
        ts = by_model[alias]
        try:
            backend = backend_for(alias, a.server or None)
        except Exception as e:  # noqa: BLE001
            for t in ts:
                report(t, f"backend for {alias} failed: {type(e).__name__}: {str(e)[:200]}")
            continue
        print(f"-- {alias}: {len(ts)} chains; {json.dumps(backend.describe())[:300]}", flush=True)
        if backend.kind == "claude":
            with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
                futures = {ex.submit(run_chain, t, backend): t for t in ts}
                for fut in cf.as_completed(futures):
                    t = futures[fut]
                    try:
                        status = fut.result()
                    except Exception as e:  # noqa: BLE001
                        status = f"crashed: {type(e).__name__}: {e}"
                    report(t, status)
        else:
            for t in ts:
                try:
                    status = run_chain(t, backend)
                except Exception as e:  # noqa: BLE001
                    status = f"crashed: {type(e).__name__}: {e}"
                report(t, status)
        backend.close()
    print(f"done; {bad} chains with a status other than ok (held, stalled or error; a chain that asked is ok)", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
