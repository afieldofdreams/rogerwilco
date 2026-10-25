#!/usr/bin/env python3
"""Run the chains as sequences of headless Claude Code sessions (`claude -p`), one session per agent, unattended.

  run.py [--only SUBSTR[,SUBSTR]] [--jobs N] [--redo] [--reset] [--limit N] [--list] [--exclude SUFFIX[,SUFFIX]]

A chain runs hop by hop. Hop 0 is code: its message is delivered into hop 1's inbox. Each relay is one session with its
brief as system prompt and prompt.txt as its first turn; the harness's replies (the AN, a re-issued HO, a pre-send refusal)
are later turns through --resume, and are also appended to the agent's inbox. The relay's out.txt is the message delivered
into the next hop's inbox; in arm R it is first checked against the HO the relay received (check-ho) and returned once on
a failure, a second failure holding the chain. The payer is the last session. Everything the models said and every usage
record goes to <trial>/turns.json; every message between agents to <trial>/chain.json; the model ids as the API returned
them, the harness commit, the briefs' hashes and the cost to <trial>/manifest.json. Chains run in parallel with --jobs;
every chain is sequential inside.
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
import build as B  # noqa: E402

ALLOWED = "Read,Write,Bash(python3:*),Bash(cat:*),Bash(ls:*)"
TURN_TIMEOUT = 480
MAX_TURNS = 5
WORDS = r"\b(READBACK|SENT|DONE|ASKED)\b"


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
    found = re.findall(WORDS, reply or "")
    return found[-1] if found else "OTHER"

# ----------------------------------------------------------------------------------------------------- files and inboxes

AGENT_FILES = ("out.txt", "rb.txt", "rb2.txt", "dn.txt", "done.txt", "question.txt", "action.json", "email.json")
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
            if extra.is_file() and extra.name not in ("prompt.txt", hop["context_file"]):
                extra.unlink()
        (d / "mail" / "inbox.md").write_text(B.render_inbox(hop["inbox"], state["arm"], hop["agent"], None))
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
    (trial / f"hop{h}" / "mail" / "inbox.md").write_text(B.render_inbox(hop["inbox"], state["arm"], hop["agent"], live))
    chain["delivered"][str(h)] = {"from": frm, "to": hop["agent"], "text": text, "tokens": C.count_tokens(text), "when": when, "reissued": None, "final": text}
    chain["traffic"].append({"hop": h, "from": frm, "to": hop["agent"], "kind": "deliver", "text": text, "tokens": C.count_tokens(text)})


def append_inbox(trial: Path, chain: dict, h: int, frm: str, to: str, text: str) -> None:
    """A later message for hop h (an AN, a re-issue, a refusal) is appended to its inbox as it arrives."""
    inbox = trial / f"hop{h}" / "mail" / "inbox.md"
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

# ----------------------------------------------------------------------------------------------------- one chain

def run_chain(trial: Path) -> str:
    meta = C.read_json(trial / "meta.json")
    state = C.sender_state(meta["id"])
    arm, model, Kn, act, rec = state["arm"], C.MODELS[state["model"]], state["K"], state["act"], state["record"]
    agents = state["agents"]
    turns: list = []
    chain = {"id": meta["id"], "arm": arm, "K": Kn, "agents": agents, "delivered": {}, "traffic": [], "checks": {}, "counters": {},
             "ended": None, "status": "ok", "flags": []}
    status = "ok"
    ended = None

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
            sid = str(uuid.uuid4())
            checks = chain["checks"].setdefault(str(h), {"rb": None, "rb2": None, "forward": []})
            r = claude((d / "prompt.txt").read_text(), model, sid, False, d, system)
            turns.append({"hop": h, "agent": me, "turn": 1, **r})
            if "error" in r:
                status = f"{me} error at hop {h}: {r['error']}"; end(h, "error", r["error"]); break
            n = 1
            second = False
            refused_once = False
            outcome = None          # "forwarded" | "done" | "asked" | "held" | "stalled"
            while n <= MAX_TURNS:
                w = word(r.get("result", ""))
                if w == "ASKED":
                    record_traffic(chain, h, me, prev, "question", C.text_of(d / "question.txt"))
                    outcome = "asked"; break
                if role == "payer" and w == "DONE":
                    if arm == "R" and checks["rb"] is None:
                        chain["flags"].append(f"hop {h}: payer acted without a readback")
                    outcome = "done"; break
                if role != "payer" and w == "SENT":
                    out_text = C.text_of(d / "out.txt")
                    out_line = K.line_from(out_text) if arm in C.LINE_ARMS else out_text.strip()
                    if not out_line:
                        status = f"{me} said SENT with no out.txt at hop {h}"; outcome = "stalled"; break
                    if arm == "R":
                        if checks["rb"] is None:
                            chain["flags"].append(f"hop {h}: {me} forwarded without a readback")
                        ctx = C.read_json(d / hop["context_file"]) if hop["context_file"] else None
                        received = chain["delivered"][str(h)]["final"]
                        fc = K.check_forward(received, out_line, role, me, nxt, act, rec, ctx)
                        fc["out"] = out_line
                        checks["forward"].append(fc)
                        if not fc["ok"]:
                            record_traffic(chain, h, me, nxt, "forward-refused", out_line)
                            if refused_once:
                                outcome = "held"; status = f"held: hop {h} ({me}): forwarded line refused twice"; break
                            refused_once = True
                            append_inbox(trial, chain, h, "pre-send check", me, fc["reply"])
                            record_traffic(chain, h, "pre-send check", me, "refusal", fc["reply"])
                            n += 1
                            r = claude("Message from your pre-send check:\n\n" + fc["reply"], model, sid, True, d, system)
                            turns.append({"hop": h, "agent": me, "turn": n, "sent": fc["reply"], **r})
                            if "error" in r:
                                status = f"{me} error at hop {h} turn {n}: {r['error']}"; end(h, "error", r["error"]); outcome = "error"; break
                            continue
                    outcome = "forwarded"
                    deliver(trial, state, chain, h + 1, me, out_line)
                    break
                if w == "READBACK" and arm == "R":
                    kind = "rb2" if second else "rb"
                    rb_line = K.line_from(C.text_of(d / f"{kind}.txt"))
                    ho = chain["delivered"][str(h)]["final"]
                    rc = K.check_readback(ho, rb_line, act, rec)
                    checks[kind] = rc
                    record_traffic(chain, h, me, prev, kind, rb_line)
                    if not rc["ok"] and second:
                        outcome = "held"; status = f"held: hop {h} ({me}): readback rejected twice"; break
                    if rc["ok"]:
                        reply = K.an_line(prev, me, next_id(chain, prev), rc["rb_id"] or f"{me}-1", role)
                        record_traffic(chain, h, prev, me, "an", reply)
                    else:
                        reply = K.reissue_line(ho, next_id(chain, prev), rc["rb_id"], rc["problems"])
                        chain["delivered"][str(h)]["reissued"] = reply
                        chain["delivered"][str(h)]["final"] = reply
                        record_traffic(chain, h, prev, me, "reissue", reply)
                        second = True
                    append_inbox(trial, chain, h, prev, me, reply)
                    n += 1
                    r = claude(f"Message from {prev}:\n\n" + reply, model, sid, True, d, system)
                    turns.append({"hop": h, "agent": me, "turn": n, "sent": reply, **r})
                    if "error" in r:
                        status = f"{me} error at hop {h} turn {n}: {r['error']}"; end(h, "error", r["error"]); outcome = "error"; break
                    continue
                status = f"{me} said {r.get('result', '')[:80]!r} at hop {h} turn {n}"
                outcome = "stalled"; break
            else:
                status = f"turn limit at hop {h}"; outcome = "stalled"
            if outcome == "forwarded":
                continue
            if outcome == "done":
                end(h, "done")
            elif outcome in ("asked", "held", "stalled"):
                end(h, outcome, status if outcome != "asked" else "")
            break
        # the payer's done report, in every arm
        hp = Kn + 1
        dp = trial / f"hop{hp}"
        if ended and ended["how"] == "done":
            log = C.SENDER / f"{meta['id']}.actlog.json"
            executed = C.read_json(log)["executed"] if log.exists() else None
            ho = chain["delivered"].get(str(hp), {}).get("final")
            dn = K.dn_check(ho, C.text_of(dp / "dn.txt"), act, rec, executed, arm, (dp / "done.txt").exists())
            chain["checks"]["dn"] = dn
            text = C.text_of(dp / "dn.txt") or C.text_of(dp / "done.txt")
            record_traffic(chain, hp, "payer", state["hops"][str(hp)]["prev"], "dn", K.line_from(text) if arm in C.LINE_ARMS else text)
    finally:
        chain["status"] = status
        chain["ended"] = ended or {"hop": None, "how": "error", "detail": status}
        models_seen = sorted({m for t in turns if isinstance(t.get("models"), dict) for m in t["models"]})
        cost = sum(t.get("cost") or 0 for t in turns)
        C.write_json(trial / "chain.json", chain)
        C.write_json(trial / "turns.json", {"status": status, "ended": chain["ended"], "turns": turns})
        C.write_json(trial / "manifest.json", {
            "id": meta["id"], "model_alias": state["model"], "model_requested": model, "models_seen": models_seen,
            "runner": "claude -p " + CLI_VERSION, "harness_commit": HARNESS_COMMIT, "brief_sha": state["brief_sha"], "tokenizer": C.TOKENIZER,
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cost_usd": round(cost, 4), "sessions": len({t["hop"] for t in turns}),
            "model_turns": len(turns), "status": status, "ended": chain["ended"],
        })
    return status


CLI_VERSION = ""
HARNESS_COMMIT = ""


def main(argv: list[str]) -> int:
    global CLI_VERSION, HARNESS_COMMIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring of the chain id; several, comma-separated, must all match")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--reset", action="store_true", help="with --redo: return the selected chains to their built state first")
    ap.add_argument("--exclude", default="", help="skip chains whose id ends with any of these, comma-separated (the smoke's -s, the pilot's -p)")
    a = ap.parse_args(argv)
    CLI_VERSION = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    HARNESS_COMMIT = git_short(C.ROOT)
    needles = [x for x in a.only.split(",") if x]
    skip = [x for x in a.exclude.split(",") if x]
    trials = [t for t in sorted(C.TRIALS.iterdir()) if t.is_dir() and all(n in t.name for n in needles) and not any(t.name.endswith(x) for x in skip)
              and (a.redo or not (t / "turns.json").exists())]
    if a.limit:
        trials = trials[:a.limit]
    if a.list:
        print("\n".join(t.name for t in trials)); return 0
    if a.reset:
        for t in trials:
            reset_trial(t)
        print(f"reset {len(trials)} chains", flush=True)
    print(f"{len(trials)} chains, {a.jobs} at a time, cli {CLI_VERSION}, commit {HARNESS_COMMIT}", flush=True)
    bad = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futures = {ex.submit(run_chain, t): t for t in trials}
        for i, fut in enumerate(cf.as_completed(futures), 1):
            t = futures[fut]
            try:
                status = fut.result()
            except Exception as e:  # noqa: BLE001
                status = f"crashed: {type(e).__name__}: {e}"
            if status != "ok":
                bad += 1
            print(f"[{i}/{len(trials)} {round(time.time() - t0)}s] {t.name:44s} {status}", flush=True)
    print(f"done; {bad} chains ended other than in an act", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
