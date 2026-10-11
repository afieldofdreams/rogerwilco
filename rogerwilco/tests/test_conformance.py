#!/usr/bin/env python3
"""Runs the rogerwilco conformance suite against scripts/rogerwilco.py.

  python3 tests/test_conformance.py                 # codec cases (parse, readback, round trip)
  python3 tests/test_conformance.py --agent FILE    # also score an agent's replies (JSONL: {"id": "a01", "reply": "<line>"})

An implementation is conformant when every parse case gives the expected verdict and JSON,
every readback, presend and done case gives the expected verdict, every valid line round-trips
through JSON, and (for agents) every reply has the expected type and slots.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import rogerwilco as fc  # noqa: E402

cases = [json.loads(l) for l in (HERE / "conformance.jsonl").read_text().splitlines() if l.strip()]
fails = []; n = 0

for c in cases:
    if c["kind"] == "parse":
        n += 1
        msg, errors, _ = fc.parse(c["line"], c.get("profile"))
        ok = (not errors) if c["expect"] == "valid" else bool(errors)
        if not ok:
            fails.append(f"{c['id']}: expected {c['expect']}, errors={errors}")
            continue
        for needle in c.get("errors_contain", []):
            if not any(needle in e for e in errors):
                fails.append(f"{c['id']}: expected an error containing {needle!r}, got {errors}")
        if "json" in c and msg != c["json"]:
            fails.append(f"{c['id']}: JSON form differs\n  got  {json.dumps(msg)}\n  want {json.dumps(c['json'])}")
        if c["expect"] == "valid":
            back = fc.encode(msg, c.get("profile"))
            msg2, e2, _ = fc.parse(back, c.get("profile"))
            if e2 or msg2 != msg:
                fails.append(f"{c['id']}: round trip failed: {back} -> {e2 or msg2}")
    elif c["kind"] == "readback":
        n += 1
        exp = c["expect_acc"].split("+") if c.get("expect_acc") else None
        problems, notes = fc.check_rb_full(c["ho"], c["rb"], c.get("profile"), expect_acc=exp)
        ok = (not problems) if c["expect"] == "match" else bool(problems)
        if not ok:
            fails.append(f"{c['id']}: expected {c['expect']}, problems={problems}")
        for needle in c.get("problems_contain", []):
            if not any(needle in p for p in problems):
                fails.append(f"{c['id']}: expected a problem containing {needle!r}, got {problems}")
        for needle in c.get("notes_contain", []):
            if not any(needle in p for p in notes):
                fails.append(f"{c['id']}: expected a note containing {needle!r}, got {notes}")

    elif c["kind"] == "presend":
        n += 1
        problems, notes = fc.check_ho(c["ho"], c["record"], c.get("profile"))
        ok = (not problems) if c["expect"] == "match" else bool(problems)
        if not ok:
            fails.append(f"{c['id']}: expected {c['expect']}, problems={problems}")
        for needle in c.get("problems_contain", []):
            if not any(needle in p for p in problems):
                fails.append(f"{c['id']}: expected a problem containing {needle!r}, got {problems}")
    elif c["kind"] == "done":
        n += 1
        problems, notes = fc.check_dn(c["ho"], c["dn"], c.get("profile"), rb_line=c.get("rb"))
        ok = (not problems) if c["expect"] == "match" else bool(problems)
        if not ok:
            fails.append(f"{c['id']}: expected {c['expect']}, problems={problems}")
        for needle in c.get("problems_contain", []):
            if not any(needle in p for p in problems):
                fails.append(f"{c['id']}: expected a problem containing {needle!r}, got {problems}")

for c in cases:
    if c["kind"] == "digest":
        n += 1
        got = fc.digest(c["line"])
        if got != c["expect"]:
            fails.append(f"{c['id']}: digest {got} != {c['expect']}")

agent_file = None
if "--agent" in sys.argv:
    agent_file = Path(sys.argv[sys.argv.index("--agent") + 1])
if agent_file:
    replies = {}
    for l in agent_file.read_text().splitlines():
        if l.strip():
            r = json.loads(l); replies[r["id"]] = r["reply"]
    for c in cases:
        if c["kind"] != "agent":
            continue
        n += 1
        reply = replies.get(c["id"])
        if reply is None:
            fails.append(f"{c['id']}: no reply"); continue
        msg, errors, _ = fc.parse(reply)
        if errors:
            fails.append(f"{c['id']}: reply invalid: {errors}\n  reply: {reply}"); continue
        allowed_types = c.get("reply_type_in") or [c["reply_type"]]
        if msg["type"] not in allowed_types:
            fails.append(f"{c['id']}: expected {'/'.join(allowed_types)}, got {msg['type']}\n  reply: {reply}"); continue
        flat = {**{k: msg[k] for k in ("re", "from", "to", "item")}, **msg["slots"]}
        for k, v in c["reply_slots"].items():
            if flat.get(k) != v:
                fails.append(f"{c['id']}: slot {k} expected {v!r}, got {flat.get(k)!r}\n  reply: {reply}")
        if "val_in" in c and msg["type"] == "AN" and flat.get("val") not in c["val_in"]:
            fails.append(f"{c['id']}: val must be one of {c['val_in']}, got {flat.get('val')!r}")
        if "why_in" in c and msg["type"] == "UN" and flat.get("why") not in c["why_in"]:
            fails.append(f"{c['id']}: why must be one of {c['why_in']}, got {flat.get('why')!r}\n  reply: {reply}")
        if msg["from"] != c["you"]:
            fails.append(f"{c['id']}: from should be {c['you']}, got {msg['from']}")
        if "acc_keys_required" in c:
            derived = {fc._split_constraint(x)[0] for x in (flat.get("acc") or [])}
            missing = [k for k in c["acc_keys_required"] if k not in derived]
            if not flat.get("acc"):
                fails.append(f"{c['id']}: rb=acc was asked for but reply has no acc=\n  reply: {reply}")
            elif missing:
                fails.append(f"{c['id']}: acc= lacks keys {missing}; sender's criteria were {c['expect_acc']}\n  reply: {reply}")

print(f"{n - len(fails)}/{n} passed")
for f in fails:
    print("FAIL", f)
sys.exit(1 if fails else 0)
