#!/usr/bin/env python3
"""Study 10: write the readbacks, run the judge, run the code check. Resumable: finished work is never redone.

  run.py author    --set pilot|main [--authors a,b] [--jobs N] [--cap DOLLARS]
  run.py judge     --set pilot|main [--judges a,b] [--jobs N] [--cap DOLLARS]
  run.py codecheck --set pilot|main
  run.py project   --set pilot            # the main run's projected cost from the pilot's measured calls

author: for each readback in the plan, the payer model is given its brief (data/briefs/payer-<fmt>.txt) as the system
prompt and the handover as received (the job with its planted fault, or as sent) as the user turn. The reply is checked
on values by verify.py; a readback that fails is written again, up to three attempts, and every attempt is kept in
readbacks/<set>/<rid>.json. A readback that fails three times is dropped and never judged.

judge: for each trial, the judge model is given data/briefs/judge-<fmt>.txt and a user turn holding the approval record,
the handover as sent and the accepted readback. trials/<set>/<tid>/ keeps prompt.txt (the user turn; the system prompt is
the brief named in meta.json with its hash), answer.txt and meta.json; grade.py adds grade.json.

codecheck: the existing code check, the frozen codec's check-rb with the pay profile, on every accepted line readback
against the HO the scheduler sent. No model is called.

The cap is per phase (the set): the run stops before a call that could take the phase's ledger past it.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import sys
import threading

import build as B
import common as C
import fixtures as F
import verify as V

MAX_ATTEMPTS = 3
print_lock = threading.Lock()


def log(msg: str) -> None:
    with print_lock:
        print(msg, flush=True)


def plan(set_: str) -> dict:
    return C.read_json(C.DATA / f"plan-{set_}.json")


def jobs_for(rb: dict) -> tuple[dict, dict]:
    """(the job as sent, the job as the payer received it)"""
    sent = {k: v for k, v in F.JOB[rb["job"]].items() if k != "source"}
    got = F.plant(F.JOB[rb["job"]], rb["slot"]) if rb["slot"] else dict(sent)
    return sent, got


def rb_path(rb: dict):
    return C.READBACKS / rb["set"] / f"{rb['rid']}.json"


def accepted(rb: dict) -> dict | None:
    p = rb_path(rb)
    if not p.exists():
        return None
    d = C.read_json(p)
    return d if d.get("accepted") is not None else None


def write_readback(rb: dict, ledger: C.Ledger) -> str:
    p = rb_path(rb)
    rec = C.read_json(p) if p.exists() else {**rb, "attempts": [], "accepted": None}
    if rec.get("accepted") is not None:
        return "done"
    if len(rec["attempts"]) >= MAX_ATTEMPTS:
        return "dropped"
    sent, got = jobs_for(rb)
    system = C.brief(f"payer-{rb['fmt']}")
    user = B.AUTHOR_USER.format(handover=F.handover(got, rb["fmt"]))
    rec.update({"brief": f"data/briefs/payer-{rb['fmt']}.txt", "brief_sha": C.sha(system), "user": user,
                "changed": F.changed(sent, got)})
    while len(rec["attempts"]) < MAX_ATTEMPTS:
        r = C.call(rb["author"], system, user, ledger, "author", f"{rb['rid']}#{len(rec['attempts']) + 1}")
        text = r.get("text")
        if text is None:
            # a provider error is not an attempt: it is kept apart and the readback is tried again on a later run
            rec.setdefault("provider_errors", []).append({"error": r.get("error"), "cost": r.get("cost"), "at": C.now()})
            C.write_json(p, rec)
            return "error"
        problems, line, alone = verify_attempt(rb, text, sent, got)
        rec["attempts"].append({"reply": text, "problems": problems, "line": line, "reply_was_line_alone": alone,
                                "version_token_missing": bool(line) and not line.startswith("RW1 "),
                                "served": r.get("served"), "cost": r.get("cost"), "usage": r.get("usage"), "error": r.get("error"),
                                "seconds": r.get("seconds"), "at": C.now()})
        if not problems:
            rec["accepted"] = len(rec["attempts"]) - 1
            rec["readback"] = text.strip() if rb["fmt"] == "prose" else line
            break
        C.write_json(p, rec)
    C.write_json(p, rec)
    return "accepted" if rec["accepted"] is not None else "dropped"


def judge_trial(t: dict, ledger: C.Ledger) -> str:
    d = C.TRIALS / t["set"] / t["tid"]
    if (d / "answer.txt").exists():
        return "done"
    rbrec = accepted({"set": t["set"], "rid": t["rid"]})
    if rbrec is None:
        return "no readback"
    sent, _got = jobs_for(rbrec)
    system = C.brief(f"judge-{t['fmt']}")
    user = B.JUDGE_USER.format(record=F.record_block(sent), sent=F.handover(sent, t["fmt"]), readback=rbrec["readback"])
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.txt").write_text(user)
    r = C.call(t["judge"], system, user, ledger, "judge", t["tid"])
    meta = {**t, "brief": f"data/briefs/judge-{t['fmt']}.txt", "brief_sha": C.sha(system), "model": C.MODELS[t["judge"]],
            "served": r.get("served"), "cost": r.get("cost"), "cost_by": r.get("cost_by"), "usage": r.get("usage"),
            "attempts": r.get("attempts"), "seconds": r.get("seconds"), "error": r.get("error"), "at": C.now()}
    C.write_json(d / "meta.json", meta)
    if r.get("text") is None:
        return "error"          # no answer.txt: a later run tries again
    (d / "answer.txt").write_text(r["text"] + "\n")
    return "answered"


def code_check(rbrec: dict) -> dict:
    sent, _ = jobs_for(rbrec)
    ho = F.ho_line(sent)
    problems, notes = C.codec().check_rb_full(ho, rbrec["readback"], "pay", now="20260924T0900Z")
    return {"ho_sent": ho, "rb": rbrec["readback"], "verdict": "MATCH" if not problems else "MISMATCH", "problems": problems, "notes": notes}


def verify_attempt(rb: dict, text: str | None, sent: dict, got: dict) -> tuple[list[str], str | None, bool]:
    if text is None:
        return ["call failed"], None, False
    if rb["fmt"] == "prose":
        return V.check_prose(text, got, sent, rb["slot"]), None, True
    return V.check_line(text, got, sent, rb["slot"])


def reverify(set_: str) -> dict:
    """Amendment 1: check every stored attempt again with the current verify.py and accept the first that passes, as
    the amended rule would have from the start. No model is called. The registered verdicts are kept beside them."""
    counts: dict[str, int] = {}
    for rb in plan(set_)["readbacks"]:
        p = rb_path(rb)
        if not p.exists():
            continue
        rec = C.read_json(p)
        sent, got = jobs_for(rec)
        rec.setdefault("accepted_registered", rec.get("accepted"))
        new = None
        for i, att in enumerate(rec["attempts"]):
            att.setdefault("problems_registered", att["problems"])
            probs, line, alone = verify_attempt(rec, att.get("reply"), sent, got)
            att.update({"problems": probs, "line": line, "reply_was_line_alone": alone,
                        "version_token_missing": bool(line) and not line.startswith("RW1 ")})
            if new is None and not probs:
                new = i
        if new is not None and new != rec.get("accepted"):
            counts["changed"] = counts.get("changed", 0) + 1
        rec["accepted"] = new
        if new is not None:
            rec["readback"] = rec["attempts"][new]["reply"].strip() if rec["fmt"] == "prose" else rec["attempts"][new]["line"]
        else:
            rec.pop("readback", None)
        rec.pop("code_check", None); rec.pop("code_grade", None)
        C.write_json(p, rec)
        counts["accepted" if new is not None else "dropped"] = counts.get("accepted" if new is not None else "dropped", 0) + 1
    return counts


def stamp_manifest(set_: str, cmd: str, cap: float) -> None:
    """Every run appends what it ran with: the protocol's and the tools' hashes, the briefs, the codec, the models."""
    import os
    path = C.RESULTS / "manifest.json"
    man = C.read_json(path) if path.exists() else {"study": "10, the scheduler as judge", "runs": []}
    man["runs"].append({
        "at": C.now(), "set": set_, "cmd": cmd, "cap": cap, "repo_head": C.git_short(),
        "readme_sha": C.sha(C.ROOT / "README.md") if (C.ROOT / "README.md").exists() else None,
        "tools_sha": {f.name: C.sha(f) for f in sorted(C.HERE.glob("*.py"))},
        "briefs_sha": {f.stem: C.sha(f) for f in sorted(C.BRIEFS.glob("*.txt"))},
        "frozen_codec_sha": C.sha(C.FROZEN_CODEC), "codec_copied_from_commit": "82938298e",
        "harness_llm_sha": C.sha(C.HARNESS / "llm.py"), "claude_cli": C.claude_version(),
        "models": C.MODELS, "partner": C.PARTNER, "prices": C.PRICES,
        "openai_key_env": "OPENAI_API_KEY" if os.environ.get("OPENAI_API_KEY") else ("OPEN_API_KEY" if os.environ.get("OPEN_API_KEY") else None),
        "env_not_passed_to_claude": list(C.DROP_ENV),
    })
    C.write_json(path, man)


MAX_ERRORS_IN_A_ROW = 25


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
            if res not in ("done", "skipped"):
                log(f"[{label} {i}/{len(items)}] {x.get('tid') or x.get('rid')}: {res}")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["author", "judge", "codecheck", "project", "reverify"])
    ap.add_argument("--set", required=True, choices=["pilot", "main"])
    ap.add_argument("--authors", default="")
    ap.add_argument("--judges", default="")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--cap", type=float, default=None, help="dollars of OpenAI spend for the phase (amendment 2)")
    ap.add_argument("--claude-cap", type=float, default=None, help="a runaway guard on Claude's list-price cost for the phase")
    ap.add_argument("--limit", type=int, default=0, help="only the first N items per model (a smoke test)")
    a = ap.parse_args()
    p = plan(a.set)
    if a.cmd == "codecheck":
        n = 0
        for rb in p["readbacks"]:
            if rb["fmt"] != "line":
                continue
            rec = accepted(rb)
            if rec is None:
                continue
            rec["code_check"] = code_check(rec)
            C.write_json(rb_path(rb), rec)
            n += 1
        print(f"code check: {n} line readbacks")
        return 0
    if a.cmd == "project":
        import analyse
        analyse.print_projection(a.set)
        return 0
    if a.cmd == "reverify":
        print(f"reverify {a.set}: {reverify(a.set)}")
        return 0
    if a.cap is None:
        print("--cap is required for author and judge", file=sys.stderr)
        return 2
    ledger = C.Ledger(a.set, a.cap, a.claude_cap)
    print(f"phase {a.set} before this run: {ledger.describe()}")
    stamp_manifest(a.set, " ".join(sys.argv[1:]), a.cap)
    def limited(items, key):
        if not a.limit:
            return items
        seen: dict[str, int] = {}
        out = []
        for x in items:
            if seen.get(x[key], 0) < a.limit:
                out.append(x); seen[x[key]] = seen.get(x[key], 0) + 1
        return out

    if a.cmd == "author":
        want = set(filter(None, a.authors.split(","))) or set(C.MODELS)
        items = limited([rb for rb in p["readbacks"] if rb["author"] in want], "author")
        counts = run_pool(lambda rb: write_readback(rb, ledger), items, a.jobs, "author")
    else:
        want = set(filter(None, a.judges.split(","))) or set(C.MODELS)
        items = limited([t for t in p["trials"] if t["judge"] in want], "judge")
        counts = run_pool(lambda t: judge_trial(t, ledger), items, a.jobs, "judge")
    print(f"{a.cmd}: {counts}; phase {a.set}: {ledger.describe()}")
    return 3 if counts.get("cap") else 0


if __name__ == "__main__":
    sys.exit(main())
