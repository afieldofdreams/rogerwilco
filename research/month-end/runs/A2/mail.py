#!/usr/bin/env python3
"""mail.py: the only channel between agents in a rogerwilco-mas run.

Agent commands (run from the run directory):
  python3 mail.py read --me <agent>                        print your unread mail, mark it read
  python3 mail.py send --from <agent> --to <agent> -m "<text>"     send a message
  python3 mail.py send --from <agent> --to <agent> --file <path>   send a message read from a file
  python3 mail.py open --me <agent> <path>                 print an artifact (counts as reading it)
  python3 mail.py check-echo "<original line>" "<echo line>"       (arms L/R) verify an echo/readback
  python3 mail.py validate "<line>"                        (arms L/R) check a line before sending
  python3 mail.py make-rb "<HO line>" <your-id>            (arms L/R) build a readback with h= digest

Orchestrator commands:
  python3 mail.py pending        who has unread mail
  python3 mail.py log            dump the log
  python3 mail.py stats          token accounting

Every send, delivery, rejection and open is appended to mail/log.jsonl with an o200k token count.
"""
from __future__ import annotations
import argparse, json, os, sys, time, subprocess, pathlib, hashlib

RUN = pathlib.Path(__file__).resolve().parent
LOG = RUN / "mail" / "log.jsonl"
CFG = json.loads((RUN / "run.json").read_text())
AGENTS = {"extractor", "reconciler", "scheduler", "auditor", "human"}
FORMCORE = pathlib.Path(CFG.get("rogerwilco") or (RUN.parents[3] / "rogerwilco" / "scripts" / "rogerwilco.py"))

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("o200k_base")
    def ntok(s: str) -> int: return len(_ENC.encode(s))
except Exception:  # pragma: no cover
    def ntok(s: str) -> int: return max(1, len(s) // 4)


def _append(rec: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec.setdefault("ts", time.time())
    with LOG.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _records() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def _next_seq() -> int:
    return 1 + max([r.get("seq", 0) for r in _records()] or [0])


# ---------------------------------------------------------------- rogerwilco bridge

def _fc(*args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(FORMCORE), *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def _validate_lines(body: str, frm: str, to: str) -> tuple[list[dict], list[str]]:
    """Arms L/R: every non-empty line must be a valid RW1 line from `frm` to `to` carrying p=<profile>."""
    profile = CFG.get("profile", "pay")
    msgs, errors = [], []
    lines = [l for l in body.splitlines() if l.strip()]
    if not lines:
        return [], ["empty message"]
    for i, line in enumerate(lines, 1):
        if not line.startswith("RW1 "):
            errors.append(f"line {i}: does not start with RW1 (this run's messages are rogerwilco lines only; put prose in the // tail or in an artifact)")
            continue
        rc, out = _fc("validate", "--profile", profile, line)
        if rc != 0:
            errors.append(f"line {i}: " + out.replace("\n", " | "))
            continue
        msg = json.loads(out[3:]) if out.startswith("OK ") else None
        if msg is None:
            errors.append(f"line {i}: could not parse validator output")
            continue
        if msg["from"] != frm:
            errors.append(f"line {i}: from={msg['from']} but you are {frm}")
        if msg["to"] != to:
            errors.append(f"line {i}: to={msg['to']} but --to is {to}")
        if msg["slots"].get("p") != profile:
            errors.append(f"line {i}: missing p={profile}")
        msgs.append(msg)
    return msgs, errors


# ---------------------------------------------------------------- commands

def cmd_send(a: argparse.Namespace) -> int:
    frm, to = a.frm, a.to
    if frm not in AGENTS or to not in AGENTS:
        print(f"REJECTED: agents are {sorted(AGENTS)}"); return 2
    if frm == to:
        print("REJECTED: cannot message yourself"); return 2
    body = a.m if a.m is not None else pathlib.Path(a.file).read_text()
    body = body.strip("\n")
    if not body.strip():
        print("REJECTED: empty message"); return 2
    rec = {"kind": "msg", "seq": _next_seq(), "from": frm, "to": to, "body": body, "tokens": ntok(body),
           "chars": len(body), "read": False}
    if CFG["arm"] in ("L", "R"):
        msgs, errors = _validate_lines(body, frm, to)
        if errors:
            rec.update({"kind": "rejected", "errors": errors})
            _append(rec)
            print("REJECTED, nothing sent. Fix and resend:")
            for e in errors: print("  " + e)
            return 1
        rec["lines"] = msgs
        rec["ids"] = [m["id"] for m in msgs]
        # echo verification in arm R is the receiver's job; here we only record
    _append(rec)
    print(f"SENT #{rec['seq']} {frm} -> {to} ({rec['tokens']} tokens)")
    return 0


def cmd_read(a: argparse.Namespace) -> int:
    me = a.me
    recs = _records()
    unread = [r for r in recs if r.get("kind") == "msg" and r["to"] == me and not r.get("read")]
    if not unread:
        print("(no new mail)"); return 0
    seqs = {r["seq"] for r in unread}
    # rewrite log marking read (small file; fine)
    out_lines = []
    for r in recs:
        if r.get("kind") == "msg" and r["seq"] in seqs:
            r["read"] = True; r["read_ts"] = time.time()
        out_lines.append(json.dumps(r, ensure_ascii=False))
    LOG.write_text("\n".join(out_lines) + "\n")
    for r in unread:
        print(f"--- #{r['seq']} from {r['from']} ---")
        print(r["body"])
    print(f"--- {len(unread)} message(s) ---")
    return 0


def cmd_open(a: argparse.Namespace) -> int:
    p = (RUN / a.path).resolve()
    if RUN not in p.parents and p != RUN:
        print("REJECTED: outside the run directory"); return 2
    if not p.exists():
        print(f"no such file: {a.path}"); return 1
    text = p.read_text()
    _append({"kind": "open", "by": a.me, "path": str(p.relative_to(RUN)), "tokens": ntok(text), "chars": len(text),
             "sha256": hashlib.sha256(text.encode()).hexdigest()[:12]})
    print(text)
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    rc, out = _fc("validate", "--profile", CFG.get("profile", "pay"), a.line)
    print(out); return rc


def _slots_for_echo(msg: dict) -> dict:
    d = dict(msg["slots"]); d.pop("p", None); d.pop("h", None)
    d["item"] = msg.get("item")
    return d


def cmd_check_echo(a: argparse.Namespace) -> int:
    """Verify that `echo` reads back `orig`: HO/RB via rogerwilco check-rb (rb=all), else slot-by-slot equality."""
    profile = CFG.get("profile", "pay")
    rc1, o1 = _fc("validate", "--profile", profile, a.orig)
    rc2, o2 = _fc("validate", "--profile", profile, a.echo)
    if rc1 or rc2:
        print("INVALID:", o1 if rc1 else o2); return 2
    m1, m2 = json.loads(o1[3:]), json.loads(o2[3:])
    if m2.get("re") != m1["id"]:
        print(f"MISMATCH: echo re={m2.get('re')} does not point at {m1['id']}"); return 1
    if m1["type"] == "HO":
        rc, out = _fc("check-rb", "--profile", profile, a.orig, a.echo)
        print(out); return rc
    s1, s2 = _slots_for_echo(m1), _slots_for_echo(m2)
    problems = []
    for k, v in s1.items():
        if k in ("need", "opts", "by"):  # question envelope need not be echoed
            continue
        if s2.get(k) != v:
            problems.append(f"{k}: sent {v!r}, echoed {s2.get(k)!r}")
    if problems:
        for p in problems: print("MISMATCH:", p)
        return 1
    print("OK echo matches; act on it"); return 0


def cmd_make_rb(a: argparse.Namespace) -> int:
    rc, out = _fc("make-rb", "--profile", CFG.get("profile", "pay"), a.ho, a.id)
    print(out); return rc


def cmd_pending(a: argparse.Namespace) -> int:
    recs = _records()
    unread = {}
    for r in recs:
        if r.get("kind") == "msg" and not r.get("read"):
            unread.setdefault(r["to"], []).append(r["seq"])
    print(json.dumps(unread)); return 0


def cmd_log(a: argparse.Namespace) -> int:
    for r in _records():
        if r.get("kind") == "msg":
            print(f"#{r['seq']} {r['from']}->{r['to']} [{r['tokens']}t]\n{r['body']}\n")
        elif r.get("kind") == "rejected":
            print(f"#{r['seq']} REJECTED {r['from']}->{r['to']} [{r['tokens']}t]: {r['errors']}\n")
        elif r.get("kind") == "open":
            print(f"open {r['by']} {r['path']} [{r['tokens']}t]")
    return 0


def cmd_stats(a: argparse.Namespace) -> int:
    recs = _records()
    msgs = [r for r in recs if r.get("kind") == "msg"]
    rej = [r for r in recs if r.get("kind") == "rejected"]
    opens = [r for r in recs if r.get("kind") == "open"]
    inter = [r for r in msgs if r["from"] != "human" and r["to"] != "human"]
    to_h = [r for r in msgs if r["to"] == "human"]
    from_h = [r for r in msgs if r["from"] == "human"]
    st = {
        "messages": len(msgs), "rejected": len(rej), "opens": len(opens),
        "inter_agent_msgs": len(inter), "inter_agent_tokens": sum(r["tokens"] for r in inter),
        "to_human_msgs": len(to_h), "to_human_tokens": sum(r["tokens"] for r in to_h),
        "from_human_msgs": len(from_h), "from_human_tokens": sum(r["tokens"] for r in from_h),
        "artifact_open_tokens": sum(r["tokens"] for r in opens),
        "artifact_opens_by": {},
    }
    for r in opens:
        st["artifact_opens_by"].setdefault(r["by"], 0); st["artifact_opens_by"][r["by"]] += r["tokens"]
    print(json.dumps(st, indent=1)); return 0


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send"); s.add_argument("--from", dest="frm", required=True); s.add_argument("--to", required=True)
    s.add_argument("-m"); s.add_argument("--file"); s.set_defaults(fn=cmd_send)
    s = sub.add_parser("read"); s.add_argument("--me", required=True); s.set_defaults(fn=cmd_read)
    s = sub.add_parser("open"); s.add_argument("--me", required=True); s.add_argument("path"); s.set_defaults(fn=cmd_open)
    s = sub.add_parser("validate"); s.add_argument("line"); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("check-echo"); s.add_argument("orig"); s.add_argument("echo"); s.set_defaults(fn=cmd_check_echo)
    s = sub.add_parser("make-rb"); s.add_argument("ho"); s.add_argument("id"); s.set_defaults(fn=cmd_make_rb)
    s = sub.add_parser("pending"); s.set_defaults(fn=cmd_pending)
    s = sub.add_parser("log"); s.set_defaults(fn=cmd_log)
    s = sub.add_parser("stats"); s.set_defaults(fn=cmd_stats)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
