#!/usr/bin/env python3
"""Build the chains: trials/<id>/ with one hop folder per agent, plus the harness's private state in sender/<id>.json.

  python3 tools/build.py [--blocks 1,2,3,4,5] [--arms F,A,L,R,C] [--models qwen15,...] [--repeats 3] [--only SUBSTR] [--suffix -p]
  python3 tools/build.py --pilot --suffix -p        # the registered pilot: block 1, F and C, PAY, clean context 1, one repeat, every model available
  python3 tools/build.py --speed --suffix -s        # the speed test: block 1, F and C, PAY, clean-1, one repeat, the local models present

Ids: B1-PAY-clean-1-C-qwen15-k2-r1, B2-PAY-clean-2-A-llama3b-k2-r1 (block 2 is brevity: the -h2 relay briefs),
B3-CHGBANK-desk-near-R-qwen7b-k2-r1, B4-SEND-clean-1-C-haiku55-k5-r1, B5-PAY-inject-coord-F-qwen3b-k2-r1, plus the suffix.
A hop folder holds what that agent sees: inbox.md (routine traffic; run.py renders the live message into it when it is
delivered) and its context file (schedule.json, approvals.json or supplier_bank.json). The agent's first turn is composed
by run.py from those and the reply instruction. The record, the inboxes as built and the expected additions live in
sender/<id>.json, outside the folders. Existing trial folders are never overwritten.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import briefs as B  # noqa: E402

SUFFIX = ""
SWEEP_ARMS = ("F", "C")
KS = (1, 2, 3, 5)


def render_inbox(messages: list, arm: str, me: str, live: dict | None) -> str:
    """The inbox as the agent sees it. live = {"from", "text", "when"} or None (not yet delivered: the placeholder is skipped)."""
    key = "prose" if arm in C.PROSE_ARMS else "line"
    out = [f"# Inbox for {me} (oldest first, newest last)", ""]
    n = 0
    for m in messages:
        if m == "{HO}":
            if live is None:
                continue
            n += 1
            out.append(f"## {n}. {live['when']} from {live['from']} to {me}")
            out.append(live["text"])
        else:
            n += 1
            out.append(f"## {n}. {m['when']} from {m['from']} to {m['to']}")
            out.append(m[key])
        out.append("")
    return "\n".join(out)


def make_trial(tid: str, block: int, act: str, context: str, arm: str, model: str, K: int, rep: int,
               k_ctx: int | None, confuser: str | None, inject: str | None) -> bool:
    tid = tid + SUFFIX
    d = C.TRIALS / tid
    if d.exists():
        return False
    level = C.harden_for_block(block)
    cc = C.chain_contexts(act, k_ctx, confuser, K, inject)
    rec = C.RECORDS[act]
    d.mkdir(parents=True)
    C.SENDER.mkdir(exist_ok=True)
    hops_meta = {}
    briefs = {}
    for h, hop in cc["hops"].items():
        hd = d / f"hop{h}"
        hd.mkdir(parents=True)
        (hd / "inbox.md").write_text(render_inbox(hop["inbox"], arm, hop["agent"], None))
        if hop["context"] is not None:
            C.write_json(hd / hop["context_file"], hop["context"])
            if hop["role"] == "payer":
                C.write_json(C.SENDER / f"{tid}.master.json", hop["context"])
        brief = f"data/briefs/{B.brief_name(arm, hop['role'], act, level)}"
        briefs[str(h)] = brief
        hops_meta[str(h)] = {"agent": hop["agent"], "role": hop["role"], "prev": hop["prev"], "next": hop["next"], "brief": brief,
                             "context_file": hop["context_file"]}
    first = C.first_prose(act, rec, cc["agents"][1]) if arm in C.PROSE_ARMS else C.first_line(act, rec, cc["agents"][1])
    expected = "act"
    for h, hop in cc["hops"].items():
        if hop.get("expect") == "ask":
            expected = f"ask@{h}"
    C.write_json(d / "meta.json", {"id": tid, "block": block, "block_name": C.BLOCKS[block], "act": act, "context": context, "arm": arm, "model": model,
                                   "K": K, "repeat": rep, "agents": cc["agents"], "hops": hops_meta, "harden": level, "inject_hop": cc["inject_hop"]})
    shas = {h: hashlib.sha256((C.ROOT / b).read_bytes()).hexdigest()[:12] for h, b in briefs.items()}
    C.write_json(C.SENDER / f"{tid}.json", {
        "id": tid, "block": block, "act": act, "context": context, "arm": arm, "model": model, "K": K, "repeat": rep,
        "record": rec, "first_message": first, "first_slots": C.first_slots(act, rec), "agents": cc["agents"], "expected": expected,
        "hops": {str(h): {"agent": hop["agent"], "role": hop["role"], "prev": hop["prev"], "next": hop["next"], "inbox": hop["inbox"],
                          "expect": hop.get("expect"), "context_file": hop["context_file"]} for h, hop in cc["hops"].items()},
        "context_desc": cc["desc"], "confuser": confuser, "inject": inject, "inject_hop": cc["inject_hop"],
        "planted": C.PLANTED if inject else None, "brief_sha": shas, "harden": level,
    })
    return True


def build(blocks, arms, models, repeats, only, acts=None, contexts=None, ks=None, confusers=None, injects=None) -> int:
    n = 0
    acts = acts or list(C.RECORDS)
    for block in blocks:
        for arm in arms:
            if block == 4 and arm not in SWEEP_ARMS:
                continue
            for model in models:
                for rep in range(1, repeats + 1):
                    for act in acts:
                        if block in (1, 2):
                            for k in (contexts or [1, 2]):
                                tid = f"B{block}-{act}-clean-{k}-{arm}-{model}-k2-r{rep}"
                                if only in tid:
                                    n += make_trial(tid, block, act, f"clean-{k}", arm, model, 2, rep, k, None, None)
                        elif block == 3:
                            for cf in (confusers or C.CONFUSERS):
                                tid = f"B3-{act}-{cf}-{arm}-{model}-k2-r{rep}"
                                if only in tid:
                                    n += make_trial(tid, 3, act, cf, arm, model, 2, rep, 1, cf, None)
                        elif block == 4:
                            for K in (ks or KS):
                                tid = f"B4-{act}-clean-1-{arm}-{model}-k{K}-r{rep}"
                                if only in tid:
                                    n += make_trial(tid, 4, act, "clean-1", arm, model, K, rep, 1, None, None)
                        else:
                            for inj in (injects or list(C.INJECT_RELAYS)):
                                tid = f"B5-{act}-inject-{inj}-{arm}-{model}-k2-r{rep}"
                                if only in tid:
                                    n += make_trial(tid, 5, act, f"inject-{inj}", arm, model, 2, rep, 1, None, inj)
    return n


def write_injection() -> None:
    """data/injection.json: the block-5 message per act, as built, for the record."""
    out = {act: {"relay": "coordinator or desk, two messages before the live handover", "message": C.inject_message(act, "<relay>"),
                 "planted": C.PLANTED, "lookalike": C.LOOKALIKE[act]} for act in C.RECORDS}
    C.write_json(C.DATA / "injection.json", out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", default="1,2,3,4,5")
    ap.add_argument("--arms", default=",".join(C.ARMS))
    ap.add_argument("--models", default=",".join(C.MODEL_ORDER))
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--acts", default="")
    ap.add_argument("--contexts", default="")
    ap.add_argument("--ks", default="")
    ap.add_argument("--pilot", action="store_true", help="block 1, arms F and C, PAY, clean context 1, one repeat, every model available")
    ap.add_argument("--speed", action="store_true", help="the speed test: as the pilot, local models only")
    a = ap.parse_args(argv)
    global SUFFIX
    SUFFIX = a.suffix
    B.write_all()
    write_injection()
    models = [m for m in a.models.split(",") if m]
    if a.pilot or a.speed:
        models = [m for m in (models if a.models != ",".join(C.MODEL_ORDER) else C.MODEL_ORDER) if C.model_available(m) and (not a.speed or m in C.LOCAL_MODELS)]
        n = build([1], ["F", "C"], models, 1, a.only, acts=["PAY"], contexts=[1])
    else:
        n = build([int(b) for b in a.blocks.split(",")], a.arms.split(","), models, a.repeats, a.only,
                  acts=a.acts.split(",") if a.acts else None, contexts=[int(x) for x in a.contexts.split(",")] if a.contexts else None,
                  ks=[int(x) for x in a.ks.split(",")] if a.ks else None)
    print(f"built {n} chains in {C.TRIALS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
