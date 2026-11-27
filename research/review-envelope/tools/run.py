#!/usr/bin/env python3
"""Study 11: have clerk write the summaries and extracts, then run the reviewers. Resumable: finished work is never redone.

  run.py stage1 --set pilot|main [--jobs N] [--claude-cap DOLLARS]
  run.py review --set pilot|main [--reviewers a,b] [--cells c1,c2] [--jobs N] [--claude-cap DOLLARS] [--limit N]

stage1: for each summary or extract in the plan, a clerk model is given its brief (data/briefs/clerk-<kind>.txt) as the
system prompt and, as the user turn, the whole file of the case WITHOUT payer's instruction, then the number of the
invoice being paid. One call; the reply is kept as written in summaries/<set>/<kind>.<clerk>.jsonl. Nothing is checked
or written again: grade.py classes each text afterwards.

review: for each trial, the reviewer model is given data/briefs/reviewer-<view>.txt as the system prompt and the view of
the case as the user turn. One call; a call is repeated only on a provider error. trials/<set>/<cell>.<model>.jsonl
holds one line per trial: the answer as written, the served model, tokens, cost, and the hash and length of the user
turn. A trial id that is recorded twice stops the run and the grading. The user turn itself is not stored when it is long: it is rebuilt from the case by code (`run.py prompt <tid>`)
and its hash is checked against the stored one.

Every model call is written to results/ledger.jsonl. Claude runs through `claude -p` on the account's plan; its cost
is recorded at list price, and --claude-cap is a guard on that figure for the phase.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import sys
import threading

import build as B
import casefile as K
import common as C

print_lock = threading.Lock()
write_lock = threading.Lock()
STORE_PROMPT_UNDER = 6000          # characters; longer user turns are stored as a hash and rebuilt by code
MAX_ERRORS_IN_A_ROW = 25


def log(msg: str) -> None:
    with print_lock:
        print(msg, flush=True)


def plan(set_: str) -> dict:
    return C.read_json(C.DATA / f"plan-{set_}.json")


def read_lines(path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()] if path.exists() else []


def append(path, row: dict) -> None:
    with write_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def stage1_path(set_: str, kind: str, author: str):
    return C.SUMMARIES / set_ / f"{kind}.{author}.jsonl"


def trial_path(t: dict):
    return C.TRIALS / t["set"] / f"{t['cell']}.{t['reviewer']}.jsonl"


def keyed(rows: list[dict], key: str, where: str) -> dict:
    """One row per id. Two rows with one id would mean a trial was called twice; that is refused, not resolved."""
    out: dict = {}
    for r in rows:
        if r[key] in out:
            raise SystemExit(f"{where}: {r[key]} is recorded twice; one call per trial is the rule. Remove the later line by hand and say so in the README.")
        out[r[key]] = r
    return out


def load_stage1(set_: str) -> dict:
    rows = [r for kind in ("summary", "extract") for a in B.CLERKS for r in read_lines(stage1_path(set_, kind, a))]
    return keyed(rows, "sid", f"summaries/{set_}")


def load_answers(set_: str, p: dict) -> dict:
    rows = [r for cell in p["cells"] for m in p["reviewers"] for r in read_lines(C.TRIALS / set_ / f"{cell}.{m}.jsonl")]
    return keyed(rows, "tid", f"trials/{set_}")


def stage1_user(st: dict) -> str:
    return K.clerk_user(B.case_of(st), st["kind"])


def review_user(t: dict, s1: dict) -> str | None:
    case = B.case_of(t)
    text = None
    if t["stage1"]:
        rec = s1.get(t["stage1"])
        if rec is None:
            return None
        text = rec["text"]
    return K.render(case, t["view"], t["note"], stage1=text, support=t["support"]) + K.USER_TAIL


def write_stage1(st: dict, ledger: C.Ledger) -> str:
    user = stage1_user(st)
    r = C.call(st["author"], K.clerk_brief(st["kind"]), user, ledger, f"stage1-{st['kind']}", st["sid"])
    if r.get("text") is None:
        return "error"
    append(stage1_path(st["set"], st["kind"], st["author"]), {**st, "text": r["text"], "served": r.get("served"), "cost": r.get("cost"), "usage": r.get("usage"),
                                                 "seconds": r.get("seconds"), "attempts": r.get("attempts"), "at": C.now(),
                                                 "user_sha": C.sha(user), "user_chars": len(user), "brief_sha": C.sha(K.clerk_brief(st["kind"]))})
    return "written"


def review_trial(t: dict, s1: dict, ledger: C.Ledger) -> str:
    user = review_user(t, s1)
    if user is None:
        return "no stage-1 text"
    system = K.brief(t["view"], t["policy"])
    r = C.call(t["reviewer"], system, user, ledger, f"review-{t['cell']}", t["tid"])
    if r.get("text") is None:
        return "error"
    usage = r.get("usage") or {}
    row = {**t, "answer": r["text"], "served": r.get("served"), "cost": r.get("cost"), "seconds": r.get("seconds"), "attempts": r.get("attempts"),
           "tokens": {k: usage.get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")},
           "at": C.now(), "user_sha": C.sha(user), "user_chars": len(user), "brief": f"reviewer-{t['view']}" if t["policy"] == "written" else f"reviewer-unwritten-{t['view']}", "brief_sha": C.sha(system)}
    if len(user) < STORE_PROMPT_UNDER:
        row["user"] = user
    append(trial_path(t), row)
    return "answered"


def stamp_manifest(set_: str, cmd: str, cap) -> None:
    path = C.RESULTS / "manifest.json"
    man = C.read_json(path) if path.exists() else {"study": "11, the review envelope", "runs": []}
    man["runs"].append({
        "at": C.now(), "set": set_, "cmd": cmd, "claude_cap": cap, "repo_head": C.git_short(),
        "readme_sha": C.sha(C.ROOT / "README.md") if (C.ROOT / "README.md").exists() else None,
        "tools_sha": {f.name: C.sha(f) for f in sorted(C.HERE.glob("*.py"))},
        "briefs_sha": {f.stem: C.sha(f) for f in sorted(C.BRIEFS.glob("*.txt"))},
        "plan_sha": C.sha(C.DATA / f"plan-{set_}.json"), "claude_cli": C.claude_version(),
        "models": {k: v for k, v in C.MODELS.items() if k in set(B.REVIEWERS) | set(B.CLERKS)},
        "env_not_passed_to_claude": list(C.DROP_ENV),
    })
    C.write_json(path, man)


def run_pool(fn, items, jobs: int, label: str) -> dict:
    counts: dict[str, int] = {}
    stop = threading.Event()
    streak = [0]

    def work(x):
        if stop.is_set():
            return "skipped"
        try:
            res = fn(x)
        except C.CapReached as e:
            if not stop.is_set():
                log(f"CAP: {e}")
            stop.set()
            return "cap"
        with print_lock:
            streak[0] = streak[0] + 1 if res == "error" else 0
            if streak[0] >= MAX_ERRORS_IN_A_ROW and not stop.is_set():
                print(f"STOP: {streak[0]} provider errors in a row; resume later with the same command", flush=True)
                stop.set()
        return res

    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(work, x): x for x in items}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            res = fut.result()
            counts[res] = counts.get(res, 0) + 1
            x = futs[fut]
            if res not in ("answered", "written", "skipped"):
                log(f"[{label} {i}/{len(items)}] {x.get('tid') or x.get('sid')}: {res}")
            elif i % 200 == 0:
                log(f"[{label} {i}/{len(items)}]")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage1", "review", "prompt"])
    ap.add_argument("tid", nargs="?")
    ap.add_argument("--set", choices=["pilot", "main"])
    ap.add_argument("--reviewers", default="")
    ap.add_argument("--cells", default="")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--claude-cap", type=float, default=None, help="a guard on Claude's list-price cost for the phase")
    ap.add_argument("--limit", type=int, default=0, help="only the first N items per cell and model (a smoke test)")
    a = ap.parse_args()
    if a.cmd == "prompt":
        for set_ in ("pilot", "main"):
            p = plan(set_)
            t = next((t for t in p["trials"] if t["tid"] == a.tid), None)
            if t:
                print(review_user(t, load_stage1(set_)))
                return 0
        print("no such trial", file=sys.stderr)
        return 2
    if not a.set:
        print("--set is required", file=sys.stderr)
        return 2
    p = plan(a.set)
    ledger = C.Ledger(a.set, 0.0, a.claude_cap)
    print(f"phase {a.set} before this run: {ledger.describe()}")
    stamp_manifest(a.set, " ".join(sys.argv[1:]), a.claude_cap)
    if a.cmd == "stage1":
        done = set(load_stage1(a.set))
        items = [st for st in p["stage1"] if st["sid"] not in done]
        if a.limit:
            items = [st for cell in p["cells"] for st in [x for x in items if x["cell"] == cell][: a.limit]]
        counts = run_pool(lambda st: write_stage1(st, ledger), items, a.jobs, "stage1")
    else:
        s1 = load_stage1(a.set)
        want_r = set(filter(None, a.reviewers.split(","))) or set(p["reviewers"])
        want_c = set(filter(None, a.cells.split(","))) or set(p["cells"])
        done = set(load_answers(a.set, p))
        items = [t for t in p["trials"] if t["reviewer"] in want_r and t["cell"] in want_c and t["tid"] not in done]
        if a.limit:
            seen: dict = {}
            kept = []
            for t in items:
                k = (t["cell"], t["reviewer"])
                if seen.get(k, 0) < a.limit:
                    kept.append(t); seen[k] = seen.get(k, 0) + 1
            items = kept
        random.Random(f"order:{a.set}").shuffle(items)          # so that the long calls are spread through the run
        counts = run_pool(lambda t: review_trial(t, s1, ledger), items, a.jobs, "review")
    print(f"{a.cmd}: {counts}; phase {a.set}: {ledger.describe()}")
    return 3 if counts.get("cap") else 0


if __name__ == "__main__":
    sys.exit(main())
