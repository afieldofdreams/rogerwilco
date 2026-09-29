#!/usr/bin/env python3
"""Scripted principal: show unread mail to `human` in a run, classify it against the planted events,
and propose the policy answer in the arm's format. The orchestrator sends the reply (after a glance).

usage: python3 tools/principal.py runs/L1            # propose
       python3 tools/principal.py runs/L1 --send     # propose and send
"""
from __future__ import annotations
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRUTH = json.loads((ROOT / "truth" / "ground_truth.json").read_text())
EVENTS = TRUTH["events"]
SCRIPT = TRUTH["principal_script"]

# option words the principal will accept for each expected answer
PREFER = {
    "REJECT": ["REJECT", "DECLINE", "REFUSE", "NO", "KEEP", "RETAIN", "IGNORE", "DONOTUPDATE", "DO_NOT_UPDATE", "NOUPDATE", "NO_UPDATE", "EXISTING", "OLD", "DISREGARD", "HOLD", "VERIFY", "CALLBACK", "N"],
    "APPROVE": ["APPROVE", "APPROVED", "YES", "Y", "OK", "PAY", "ACCEPT", "PROCEED", "GO"],
    "HOLD": ["HOLD", "DEFER", "WAIT", "POSTPONE", "FX", "FXRUN", "FX_RUN", "OFFRUN", "OFF_RUN", "OUTSIDE_RUN", "OUTSIDE", "LATER", "NEXT", "EXCLUDE", "EXCL", "SKIP", "SEPARATE", "MANUAL"],
}


def classify(body: str) -> list[str]:
    b = body.lower()
    hits = []
    for ev, spec in EVENTS.items():
        kws = [k.lower() for k in spec["keywords"]]
        score = sum(1 for k in kws if k in b)
        if ev == "E_BANK" and ("04-00-75" in b or "88214561" in b or re.search(r"northfield-print\.co\b(?!\.uk)", b) or "bankchg" in b or "lookalike" in b
                               or re.search(r"bank[- ]detail\w*\W+(?:change|request|update|switch)|(?:change|update|switch)\W+(?:\w+\W+){0,4}bank[- ]detail|new bank", b)):
            hits.append(ev); continue
        if ev == "E_APPR" and ("md-2026-057" in b and ("5400" in b or "5,400" in b or "approv" in b or "overlim" in b)):
            hits.append(ev); continue
        if ev == "E_FX" and ("7731" in b or ("usd" in b and "kestrel" in b) or "flag=fx" in b or "fx" in b.split()):
            hits.append(ev); continue
        if ev in ("E_BANK", "E_APPR", "E_FX"):
            continue
        if score >= 2:
            hits.append(ev)
    return hits


def asks_decision(body: str) -> bool:
    b = body.lower()
    if b.startswith("rw1 aq") or "\nrw1 aq" in b:
        return True
    if b.startswith("rw1 dn") or b.startswith("rw1 st") or b.startswith("rw1 rb"):
        return False
    return any(w in b for w in ["?", "approve", "approval", "decision", "confirm", "please advise", "your call", "options", "should we", "do you want", "need you", "requires your", "require your"])


def opts_of(body: str) -> list[str]:
    m = re.search(r"opts=([A-Za-z0-9_+\-]+)", body)
    return m.group(1).split("+") if m else []


def pick(expected: str, opts: list[str]) -> str | None:
    up = [o.upper() for o in opts]
    for cand in PREFER[expected]:
        if cand in up:
            return opts[up.index(cand)]
    return None


def propose(run_dir: pathlib.Path) -> list[dict]:
    cfg = json.loads((run_dir / "run.json").read_text())
    arm = cfg["arm"]
    log = [json.loads(l) for l in (run_dir / "mail" / "log.jsonl").read_text().splitlines() if l.strip()]
    unread = [r for r in log if r.get("kind") == "msg" and r["to"] == "human" and not r.get("read")]
    n_from_human = sum(1 for r in log if r.get("kind") == "msg" and r["from"] == "human")
    out = []
    for r in unread:
        evs = classify(r["body"])
        decision = asks_decision(r["body"])
        expected = [e for e in evs if EVENTS[e]["escalate"]]
        prop = None
        if decision:
            if expected:
                ev = expected[0]
                ans = EVENTS[ev]["principal_answer"]
                text = SCRIPT[ev]
            else:
                ev, ans, text = "OTHER", None, SCRIPT["OTHER"]
            if arm in ("L", "R"):
                # answer each AQ line in the message
                lines = [l for l in r["body"].splitlines() if l.startswith("RW1 AQ")]
                replies = []
                for l in lines:
                    mid = l.split()[2]
                    item = re.search(r"item=(\S+)", l)
                    opts = opts_of(l)
                    lev = [e for e in classify(l) if EVENTS[e]["escalate"]]
                    if lev:
                        a = EVENTS[lev[0]]["principal_answer"]; t = SCRIPT[lev[0]]
                    else:
                        a = None; t = SCRIPT["OTHER"]
                    val = pick(a, opts) if a else None
                    if val is None:
                        val = (opts[0] if opts else "NONE")
                        note = " (no matching option: check by hand)"
                    else:
                        note = ""
                    n_from_human += 1
                    tail = t[:280]
                    line = f"RW1 AN human-{n_from_human:02d} re={mid} from=human to={r['from']} p=pay" + (f" item={item.group(1)}" if item else "") + f" val={val} // {tail}"
                    replies.append(line + note)
                prop = "\n".join(replies) if replies else None
            else:
                n_from_human += 1
                if arm == "P":
                    prop = f"ACTION: {text.split('.')[0]}.\nSTATE: {text}\nRESULT: decision given above."
                else:
                    prop = text
        out.append({"seq": r["seq"], "from": r["from"], "tokens": r["tokens"], "events": evs, "asks_decision": decision, "expected": expected, "proposed": prop, "body": r["body"]})
    return out


def main() -> int:
    run_dir = pathlib.Path(sys.argv[1]).resolve()
    send = "--send" in sys.argv
    props = propose(run_dir)
    if not props:
        print("(no unread mail for human)"); return 0
    for p in props:
        print(f"=== #{p['seq']} from {p['from']} [{p['tokens']}t] events={p['events']} decision={p['asks_decision']}")
        print(p["body"]); print("--- proposed reply:"); print(p["proposed"] or "(none: informational)")
        if send and p["proposed"] and "(no matching option" not in p["proposed"]:
            subprocess.run([sys.executable, str(run_dir / "mail.py"), "send", "--from", "human", "--to", p["from"], "-m", p["proposed"]], check=False)
    if send:  # mark human mail read once answered
        subprocess.run([sys.executable, str(run_dir / "mail.py"), "read", "--me", "human"], check=False, capture_output=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
