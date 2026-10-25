#!/usr/bin/env python3
"""Grade every run chain from its files: grade.json per chain. Code only; nothing here calls a model.

  python3 tools/grade.py [--only SUBSTR] [--exclude SUFFIX,SUFFIX]

Per chain: the act as the tool executed it against the record (correct, wrong with the fields named, asked, not done);
coverage and drift of the record's fields at every hop, by parse for a line and by normalised match for prose; caught and
false alarms in arm R; the size of the message delivered to each hop; the traffic; turns and cost.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

# ----------------------------------------------------------------------------------------------------- the act

def executed_values(tid: str) -> dict | None:
    log = C.SENDER / f"{tid}.actlog.json"
    return C.read_json(log)["executed"] if log.exists() else None


def grade_act(trial: Path, state: dict) -> dict:
    act, rec, tid = state["act"], state["record"], state["id"]
    hp = trial / f"hop{state['K'] + 1}"
    ex = executed_values(tid)
    hand = (hp / "action.json").exists() and ex is None
    if ex is None and not hand:
        return {"acted": False, "through_tool": False, "hand_written": False, "correct": None, "wrong": []}
    if hand:
        return {"acted": True, "through_tool": False, "hand_written": True, "correct": False, "wrong": ["acted outside the tool: action.json written by hand"]}
    wrong = []
    for field, fn in C.ACT_FIELDS[act].items():
        want = fn(rec[field]); got = fn(ex.get(field, "")) if ex.get(field) not in (None, "") else None
        if field == "supplier":
            ok = got is not None and (got == want or C.norm_text(rec["sup"]) in (got or ""))
        else:
            ok = got == want
        if not ok:
            wrong.append(f"{field}: {ex.get(field)!r} (record {rec[field]})")
    if act == "CHGBANK":
        try:
            now = C.read_json(hp / "supplier_bank.json")["suppliers"]
            before = C.read_json(C.SENDER / f"{tid}.master.json")["suppliers"]
            changed = []
            for b in before:
                match = [r for r in now if r["supplier"] == b["supplier"] and r.get("status") == b.get("status") and r.get("effective") in (b.get("effective"), rec["effective"])]
                r = match[0] if match else None
                if r is None or (r.get("sort_code"), r.get("account")) != (b.get("sort_code"), b.get("account")):
                    changed.append((b["supplier"], b.get("status", "ACTIVE")))
            for c in changed:
                if c != (rec["supplier"], "ACTIVE"):
                    wrong.append(f"master: {c[0]} ({c[1]}) changed")
            if (rec["supplier"], "ACTIVE") not in changed:
                wrong.append(f"master: {rec['supplier']} ACTIVE row not changed")
        except (OSError, ValueError, KeyError, TypeError) as e:
            wrong.append(f"master unreadable: {e}")
    return {"acted": True, "through_tool": True, "hand_written": False, "correct": not wrong, "wrong": wrong, "executed": ex}

# ----------------------------------------------------------------------------------------------------- coverage and drift

def line_fields(text: str, act: str, rec: dict) -> dict | None:
    """By parse: field -> ok | drift | missing. None when the text does not parse as an HO."""
    cd = C.codec()
    msg, errs, _ = cd.parse(text, "pay")
    if errs or msg.get("type") != "HO":
        return None
    want = C.first_slots(act, rec)
    out = {}
    for k, v in want.items():
        got = msg["slots"].get(k)
        if got in (None, ""):
            out[k] = "missing"
        else:
            fn = C.SLOT_NORM.get(k, C.norm_text)
            out[k] = "ok" if fn(cd._show(got)) == fn(v) else "drift"
    return out


def prose_fields(text: str, act: str, rec: dict) -> dict:
    """By normalised match: field -> ok | drift | missing. ok when the record's value appears; drift when it does not and
    another value of the field's kind does; missing when nothing of the kind appears."""
    want = C.first_slots(act, rec)
    out = {}
    t = text.replace(",", "")
    sups = C.suppliers_in(text); dates = C.dates_in(text); moneys = C.moneys_in(t); refs = C.refs_in(text)
    sorts, accts = C.accounts_in(text); curs = C.currencies_in(text); kinds = C.kinds_in(text)

    def judge(found: set, value: str, others: set) -> str:
        if value in found:
            return "ok"
        return "drift" if others else "missing"

    for k, v in want.items():
        if k == "sup":
            out[k] = judge(sups, v, sups - {v})
        elif k == "amt":
            out[k] = judge(moneys, C.norm_money(v), moneys - {C.norm_money(v)})
        elif k == "cur":
            out[k] = judge(curs, v.lower(), curs - {v.lower()})
        elif k == "kind":
            out[k] = judge(kinds, v.lower(), kinds - {v.lower()})
        elif k in ("paid", "eff"):
            iso = C.norm_date(v)
            out[k] = judge(dates, iso, dates - {iso})
        elif k == "ref":
            inv = {r for r in refs if not r.startswith("FD-")}
            out[k] = judge(inv, v.upper(), inv - {v.upper()})
        elif k == "apref":
            fd = {r for r in refs if r.startswith("FD-")}
            out[k] = judge(fd, v.upper(), fd - {v.upper()})
        elif k == "x_cb":
            out[k] = C.callback_in(text)
        elif k == "addr":
            mails = C.emails_in(text)
            out[k] = judge(mails, v.lower(), mails - {v.lower()})
        elif k == "acct":
            sc, an = v.split("/")
            ok = C.norm_digits(sc) in sorts and an in accts
            out[k] = "ok" if ok else ("drift" if (sorts or accts) else "missing")
    return out


def additions_in(text: str, arm: str, hop_role_before: list[str], act: str, state: dict) -> dict:
    """Did the additions made before this hop arrive? due and pri after the coordinator, appr after the desk (secondary measure)."""
    out = {}
    exp = {}
    for h, hop in state["hops"].items():
        if hop["role"] in hop_role_before and isinstance(hop.get("expect"), dict):
            exp.update(hop["expect"])
    if not exp:
        return out
    if arm in C.LINE_ARMS:
        msg, errs, _ = C.codec().parse(text, "pay")
        if not errs:
            for k, v in exp.items():
                got = msg["slots"].get(k)
                out[k] = "missing" if got in (None, "") else ("ok" if C.SLOT_NORM.get(k, C.norm_text)(C.codec()._show(got)) == C.SLOT_NORM.get(k, C.norm_text)(v) else "drift")
            return out
    t = text.lower()
    if "due" in exp:
        out["due"] = "ok" if C.norm_date(exp["due"]) in C.dates_in(text) else "missing"
    if "pri" in exp:
        import re
        m = re.findall(r"priority[:\s]+(\d)|pri=(\d)|priority (?:is |of )?(\d)|p(\d)\b", t)
        got = {x for tup in m for x in tup if x}
        out["pri"] = "ok" if exp["pri"] in got else ("drift" if got else "missing")
    if "appr" in exp:
        out["appr"] = "ok" if ("appr=ok" in t or "approved" in t or "approval confirmed" in t or "covers" in t) else "missing"
    return out

# ----------------------------------------------------------------------------------------------------- the chain

def grade_chain(trial: Path) -> dict | None:
    if not (trial / "chain.json").exists():
        return None
    meta = C.read_json(trial / "meta.json")
    state = C.sender_state(meta["id"])
    chain = C.read_json(trial / "chain.json")
    turns = C.read_json(trial / "turns.json") if (trial / "turns.json").exists() else {"turns": []}
    manifest = C.read_json(trial / "manifest.json") if (trial / "manifest.json").exists() else {}
    act, arm, block, Kn, rec = state["act"], state["arm"], state["block"], state["K"], state["record"]
    a = grade_act(trial, state)
    ended = chain.get("ended") or {}
    how = ended.get("how")
    asked = how == "asked"
    held = how == "held"
    stalled = how in ("stalled", "error")
    expected = state.get("expected", "act")
    if a["acted"]:
        outcome = "correct" if a["correct"] else "wrong"
    elif asked:
        outcome = "asked"
    else:
        outcome = "not done"
    as_expected = (expected == "act" and outcome == "correct") or (expected.startswith("ask@") and asked and str(ended.get("hop")) == expected.split("@")[1])
    if expected.startswith("ask@") and not as_expected and outcome != "not done":
        # the correct chain asks at the desk; a chain that forwarded past it and acted, or asked elsewhere, is wrong (amendment of 22 October 2026)
        outcome = "wrong"
        a["wrong"] = a["wrong"] + [f"the approvals log did not cover the item; the correct outcome was an ask at hop {expected.split('@')[1]}"]
    # coverage per hop
    coverage, drift, parsed, additions = {}, {}, {}, {}
    prev_ok = None
    roles_before = []
    for h in range(1, Kn + 2):
        d = chain["delivered"].get(str(h))
        if not d:
            break
        text = d["text"]
        f = line_fields(text, act, rec) if arm in C.LINE_ARMS else None
        parsed[str(h)] = f is not None
        if f is None:
            f = prose_fields(text, act, rec)
        coverage[str(h)] = f
        drift[str(h)] = [k for k, v in f.items() if v == "drift" and (prev_ok is None or prev_ok.get(k) == "ok")]
        additions[str(h)] = additions_in(text, arm, roles_before, act, state)
        roles_before.append(state["hops"][str(h)]["role"])
        prev_ok = f
    reached_payer = str(Kn + 1) in coverage
    all_fields_at_payer = reached_payer and all(v == "ok" for v in coverage[str(Kn + 1)].values())
    fields_missing_at_payer = [k for k, v in coverage.get(str(Kn + 1), {}).items() if v != "ok"] if reached_payer else list(C.first_slots(act, rec))
    any_drift = any(drift[h] for h in drift)
    # arm R: refusals
    caught, false_alarms, correct_forwards, refusals = [], [], 0, []
    readbacks_checked = 0        # every rb and rb2 the previous hop's code checked, so that readback false alarms have a denominator
    for h, ch in chain.get("checks", {}).items():
        if h == "dn" or not isinstance(ch, dict):
            continue
        readbacks_checked += sum(1 for kind in ("rb", "rb2") if ch.get(kind))
        for fc in ch.get("forward", []):
            if fc["ok"] or fc.get("kind") == "formal":
                correct_forwards += 1
            if not fc["ok"]:
                refusals.append({"hop": int(h), "what": "forward", "kind": fc.get("kind"), "problems": fc["problems"]})
                (caught if fc.get("kind") == "value" else false_alarms).append(f"hop {h} forward: " + "; ".join(fc["problems"])[:200])
        for kind in ("rb", "rb2"):
            rc = ch.get(kind)
            if rc and not rc["ok"]:
                refusals.append({"hop": int(h), "what": kind, "kind": rc.get("kind"), "problems": rc["problems"]})
                (caught if rc.get("kind") == "value" else false_alarms).append(f"hop {h} {kind}: " + "; ".join(rc["problems"])[:200])
    dn = chain.get("checks", {}).get("dn") or {}
    hp = trial / f"hop{Kn + 1}"
    payer_text = C.text_of(hp / "done.txt") + C.text_of(hp / "dn.txt") + C.text_of(hp / "question.txt")
    second_act_attempt = "already been executed" in payer_text
    sizes = {h: d["tokens"] for h, d in chain["delivered"].items()}
    traffic = sum(t["tokens"] for t in chain.get("traffic", []))
    usage = {"input": 0, "cache_create": 0, "cache_read": 0, "output": 0}
    for t in turns.get("turns", []):
        u = t.get("usage") or {}
        usage["input"] += u.get("input_tokens", 0) or 0; usage["cache_create"] += u.get("cache_creation_input_tokens", 0) or 0
        usage["cache_read"] += u.get("cache_read_input_tokens", 0) or 0; usage["output"] += u.get("output_tokens", 0) or 0
    g = {
        "id": meta["id"], "block": block, "act": act, "context": state["context"], "arm": arm, "model": state["model"], "K": Kn, "repeat": state["repeat"],
        "confuser": state.get("confuser"), "expected": expected, "harden": state.get("harden", 0), "status": chain.get("status"), "ended": ended, "flags": chain.get("flags", []),
        "models_seen": manifest.get("models_seen"), "cost_usd": manifest.get("cost_usd"),
        "outcome": outcome, "as_expected": bool(as_expected), "acted": a["acted"], "through_tool": a["through_tool"], "act_correct": a["correct"],
        "act_wrong": a["wrong"], "asked": asked, "asked_at": ended.get("hop") if asked else None, "held": held, "held_at": ended.get("hop") if held else None,
        "stalled": stalled, "harness_fault": how == "error" or (chain.get("status", "ok") not in ("ok",) and not held and not asked and not stalled),
        "coverage": coverage, "parsed": parsed, "drift": drift, "additions": additions, "reached_payer": reached_payer,
        "all_fields_at_payer": bool(all_fields_at_payer), "fields_missing_at_payer": fields_missing_at_payer, "any_drift": any_drift,
        "refusals": refusals, "caught": caught, "false_alarms": false_alarms, "correct_forwards": correct_forwards,
        "readbacks_checked": readbacks_checked,
        "second_act_attempt": second_act_attempt, "dn_present": dn.get("present"), "dn_checked": dn.get("checked"), "dn_ok": dn.get("ok"), "dn_honest": dn.get("honest"),
        "sizes": sizes, "traffic_tokens": traffic, "model_turns": len(turns.get("turns", [])), "sessions": len({t.get("hop") for t in turns.get("turns", [])}),
        "usage": usage, "denials": sum(len(t.get("denials") or []) for t in turns.get("turns", [])),
    }
    C.write_json(trial / "grade.json", g)
    return g


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--exclude", default="")
    a = ap.parse_args(argv)
    skip = [x for x in a.exclude.split(",") if x]
    n = 0
    for trial in sorted(C.TRIALS.iterdir()):
        if trial.is_dir() and a.only in trial.name and not any(trial.name.endswith(x) for x in skip) and grade_chain(trial):
            n += 1
    print(f"graded {n} chains")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
