#!/usr/bin/env python3
"""Exploratory calibration for the review envelope. Run BEFORE the protocol was registered, to find where the
effects could be seen at all. Nothing here is part of the registered pilot or main run, and none of it is pooled.

    python3 calibrate.py <name> --models haiku55,sonnet55 --cells "card::12,file:S:12,file:M:12,file:M:12:attest" [--jobs 8]

A cell is view:length:targets[:note][:faults][:support][:policy]; policy is written (the default) or unwritten; targets is how many target payments, each used once clean and
once per fault kind; faults is a plus-joined subset of the fault kinds, or "none" for clean cases only; support is one
of supplier, forged, inject (a document in the file that speaks for the fault). For the summary and extract views clerk
(Sonnet 5.5) is called first and its text is kept in ../calibration/<name>.stage1.jsonl.
Writes ../calibration/<name>.jsonl, one line per call, resumable.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import casefile as K
import common as C

OUT = C.ROOT / "calibration"
VERDICT = re.compile(r"^(APPROVE|HOLD)\b(.*)$", re.I)
WORDS = ["supplier", "invoice", "amount", "currency", "kind", "account", "date", "reference", "approval", "duplicate", "onhold", "unconfirmed"]


def parse(text: str | None) -> dict:
    if not text:
        return {"verdict": None, "reason": None, "first": ""}
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    first = re.sub(r"[*_`#>]", "", first).strip().strip("\"'")
    m = VERDICT.match(first)
    if not m:
        return {"verdict": None, "reason": None, "first": first[:200]}
    rest = re.sub(r"[^a-z]+", " ", m.group(2).lower().replace("on hold", "onhold").replace("on-hold", "onhold")).split()
    reason = next((w for w in rest if w in WORDS), None)
    return {"verdict": m.group(1).upper(), "reason": reason, "first": first[:200]}


def grade(ans: dict, fault: str | None) -> str:
    v, r = ans["verdict"], ans["reason"]
    if v is None:
        return "unparseable"
    if fault is None:
        return "correct" if v == "APPROVE" else ("false_unconfirmed" if r == "unconfirmed" else "false_alarm")
    if v == "APPROVE":
        return "miss"
    if r == K.REASON_OF_FAULT[fault]:
        return "caught"
    return "held_unconfirmed" if r == "unconfirmed" else "held_other"


def targets(n: int) -> list[dict]:
    rng = random.Random("calibration-targets")
    pool = list(K.POOL)
    rng.shuffle(pool)
    return pool[:n]


def build(cells: list[str], models: list[str]) -> list[dict]:
    out = []
    for cell in cells:
        parts = cell.split(":")
        view, length, n = parts[0], (parts[1] or "S"), int(parts[2])
        note = parts[3] if len(parts) > 3 and parts[3] else None
        faults = parts[4].split("+") if len(parts) > 4 and parts[4] else ["none"] + K.FAULTS
        support = parts[5] if len(parts) > 5 and parts[5] else None
        policy = parts[6] if len(parts) > 6 and parts[6] else "written"
        for t in targets(n):
            for f in faults:
                fault = None if f == "none" else f
                case = K.make_case(t, fault, length, f"cal:{t['id']}:{length}")
                if support and fault is None:
                    continue
                user = None if view in ("summary", "extract") else K.render(case, view, note, support=support) + K.USER_TAIL
                for m in models:
                    out.append({"tid": f"{view}-{length}-{note or 'nonote'}-{support or 'nosup'}-{policy}-{t['id']}-{f}-{m}", "view": view, "length": length, "note": note,
                                "support": support, "policy": policy, "job": t["id"], "fault": fault, "model": m, "system": K.brief(view, policy), "user": user, "_case": case})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--models", default="haiku55,sonnet55")
    ap.add_argument("--cells", required=True)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.name}.jsonl"
    done = {json.loads(ln)["tid"] for ln in path.read_text().splitlines() if ln.strip()} if path.exists() else set()
    plan = [t for t in build(a.cells.split(","), a.models.split(",")) if t["tid"] not in done]
    lock = threading.Lock()

    s1path = OUT / f"{a.name}.stage1.jsonl"
    s1 = {json.loads(ln)["key"]: json.loads(ln) for ln in s1path.read_text().splitlines() if ln.strip()} if s1path.exists() else {}
    s1lock = threading.Lock()
    s1locks: dict = {}

    def stage1(t):
        import grade as G
        key = f"{t['view']}:{t['job']}:{t['fault']}:{t['length']}"
        with s1lock:
            lk = s1locks.setdefault(key, threading.Lock())
        with lk:
            if key in s1:
                return s1[key]["text"]
            r = C.call_claude("sonnet55", K.clerk_brief(t["view"]), K.view_file(t["_case"]) + K.CLERK_TAIL[t["view"]])
            if r.get("text") is None:
                return None
            rec = {"key": key, "view": t["view"], "job": t["job"], "fault": t["fault"], "text": r["text"], "cost": r.get("cost"),
                   "evidence": G.carries(r["text"], t["_case"]), "words": len(r["text"].split())}
            with lock:
                with s1path.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")
            s1[key] = rec
            return rec["text"]

    def one(t):
        if t["user"] is None:
            text = stage1(t)
            if text is None:
                return "error"
            t["user"] = K.render(t["_case"], t["view"], stage1=text) + K.USER_TAIL
            t["carries"] = s1[f"{t['view']}:{t['job']}:{t['fault']}:{t['length']}"]["evidence"].get("carries")
        r = C.call_claude(t["model"], t["system"], t["user"])
        if r.get("text") is None:
            return "error"
        ans = parse(r.get("text"))
        row = {k: v for k, v in t.items() if k not in ("system", "user", "_case")}
        row.update({"chars": len(t["user"]), "answer": r.get("text"), **ans, "outcome": grade(ans, t["fault"]), "cost": r.get("cost"),
                    "seconds": r.get("seconds"), "served": r.get("served"),
                    "tokens": {k: (r.get("usage") or {}).get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")}})
        with lock:
            with path.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
        return row["outcome"]

    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(one, plan))
    print(len(res), "calls;", {o: res.count(o) for o in sorted(set(res))})


if __name__ == "__main__":
    main()
