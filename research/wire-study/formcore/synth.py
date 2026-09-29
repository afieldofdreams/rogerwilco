"""Synthetic P-Form handoffs plus a ground-truth receiver policy."""
import random

STANCES = ["TRI", "STR", "ARC", "BLD", "QAR", "CPY", "GRD", "DAT", "MKT", "SCT", "IDE"]
NOTES = [
    "Last touched during the Q3 review.",
    "Related thread in Claude Questions.",
    "Adam mentioned this on the call, no decision yet.",
    "Two stale edges to archived nodes.",
    "Description field is thin.",
    "Linked to the partner pipeline.",
    "Came in via the Inbox Queue last week.",
]

TODAY = "20260927"
EXPEDITE_BEFORE = "20261004"  # due within 7 days

POLICY = """Receiver policy. Apply rules in order; the first rule that matches decides.
1. WAIT if the node is blocked by any other node.
2. BOUNCE if confidence is low AND the ask is DECIDE (make a decision) or BUILD (build it).
3. EXPEDITE if there is a due date earlier than 4 October 2026 (20261004).
4. ESCALATE if it has been stalled 14 days or more AND importance is 7 or higher.
5. CLOSE if the pipeline stage is done.
6. ACCEPT otherwise.
Stall days or importance that are not stated do not satisfy rule 4."""


def decide(d: dict) -> str:
    if d.get("blocked_by"):
        return "WAIT"
    if d["confidence"] == "L" and d["ask"] in ("DECIDE", "BUILD"):
        return "BOUNCE"
    if d.get("due") and d["due"] < EXPEDITE_BEFORE:
        return "EXPEDITE"
    if (d.get("stall_days") or 0) >= 14 and (d.get("importance") or 0) >= 7:
        return "ESCALATE"
    if d["stage"] == "DONE":
        return "CLOSE"
    return "ACCEPT"


def make(n=200, seed=7):
    rng = random.Random(seed)
    out = []
    target = ["WAIT", "BOUNCE", "EXPEDITE", "ESCALATE", "CLOSE", "ACCEPT"]
    tries = 0
    counts = {t: 0 for t in target}
    per = n // len(target)
    while len(out) < n and tries < 100000:
        tries += 1
        frm, to = rng.sample(STANCES, 2)
        d = {"from": frm, "to": to, "node": rng.randint(1000, 4999),
             "stage": rng.choice(["DIA", "REV", "OPT", "DEC", "ACT", "DONE"]),
             "confidence": rng.choice(["L", "M", "H"]),
             "ask": rng.choice(["SCORE4", "SPEC", "BUILD", "REVIEW", "ENRICH", "PRUNE", "DECIDE", "RESEARCH", "DRAFT"])}
        if rng.random() < 0.6: d["opstatus"] = rng.choice(["NOW", "WAIT", "SCH", "NONE"])
        if rng.random() < 0.8: d["importance"] = rng.randint(1, 10)
        if rng.random() < 0.5: d["heat"] = rng.choice(["COLD", "WARM", "HOT"])
        if rng.random() < 0.7: d["stall_days"] = rng.choice([2, 5, 7, 9, 12, 13, 14, 15, 19, 21, 28, 40])
        if rng.random() < 0.35:
            d["due"] = f"2026{rng.choice(['09', '10', '10', '11'])}{rng.randint(1, 28):02d}"
            if d["due"] < TODAY: d["due"] = "20261003"
        if rng.random() < 0.6: d["keep_assigned"] = rng.sample(["ADAM"] + STANCES, rng.choice([1, 1, 2]))
        if rng.random() < 0.5: d["source_view"] = rng.choice([119, 120, 121, 94, 95, 97, 74])
        if rng.random() < 0.18: d["blocked_by"] = [rng.randint(1000, 4999) for _ in range(rng.choice([1, 2]))]
        if rng.random() < 0.5: d["note"] = rng.choice(NOTES)
        # canonical order so encode/decode compare cleanly
        label = decide(d)
        if counts[label] >= per and len(out) < per * len(target):
            continue
        counts[label] += 1
        d["_id"] = len(out)
        d["_truth"] = label
        out.append(d)
    return out
