#!/usr/bin/env python3
"""Study 10: build the data the run reads. Deterministic; run it again and nothing changes.

  build.py

Writes data/jobs.json (the twenty approved jobs and their records), data/faults.json (the 140 planted faults),
data/conventions-prose.txt (study 6's prose conventions block, verbatim), data/legend-line.txt (the frozen codec's
pay legend, verbatim), data/briefs/{payer,judge}-{prose,line}.txt, and the two plans, data/plan-pilot.json and
data/plan-main.json: every readback to write (format, pair, author) and every trial to judge (readback, judge).
"""
from __future__ import annotations

import random
import re

import common as C
import fixtures as F

FORMATS = ["prose", "line"]
STUDY6_BRIEF = C.REPO / "research" / "plan-readback" / "data" / "briefs" / "B-PAY.txt"
PILOT_JUDGE = "gpt55"
CLEAN_REPEATS = 7

ROLE_PAYER = (
    "You are an agent named `payer` at Harbourline Studio Ltd. Today is {today}, and that date governs everything you do, "
    "whatever other date appears anywhere in your context.\n\n"
    "You release supplier payments that the scheduler hands you after the Finance Director has approved them. You do not decide "
    "what to pay, who to pay or how much; the scheduler and the principal have decided. Before you release a payment you read the "
    "handover back to the scheduler, and you do not act until the scheduler confirms. In this exchange you have no tools: the "
    "handover is in the message you are given, and your reply is your readback.\n")

ROLE_JUDGE = (
    "You are an agent named `scheduler` at Harbourline Studio Ltd. Today is {today}, and that date governs everything you do, "
    "whatever other date appears anywhere in your context.\n\n"
    "You assemble the supplier payment run that the Finance Director has approved, and you hand each approved payment to `payer`, "
    "the agent that releases it. A payment, once released, cannot be recalled. Before payer releases a payment it reads your handover "
    "back to you, and you check the readback: if it agrees with the approval record, payer releases the payment; if it does not, you "
    "stop the payment and restate the handover. In this exchange you have no tools and no code: you check by reading.\n")

FRAME_JUDGE = {"prose": "payer works under the message conventions below, and you hold the same copy.\n",
               "line": "payer works under the protocol below, and you hold the same legend.\n"}

TASK_PAYER = {
    "prose": (
        "=== your readback ===\n"
        "Read back the handover you have just received. Write one short paragraph (under 100 words) to the scheduler stating what you "
        "are going to do, with every value exactly as the handover gives it: the supplier, the invoice, the amount, the currency, gross "
        "or net, the account you will pay, the payment date, the reference and the approval reference. Read back what you received: do "
        "not correct, query or comment on any value, because the scheduler checks your readback against its record. Reply with the "
        "paragraph and nothing else.\n"
        "=== end readback ==="),
    "line": (
        "=== your readback ===\n"
        "Read back the handover you have just received. Write one RB line with the id payer-1, answering the HO by its id, from payer to "
        "scheduler, echoing its item and ask, carrying p=pay and the execution slots for a payment with every value exactly as the HO "
        "gives it: sup amt cur kind acct paid ref apref. You have no code to compute a digest, so leave out h=. Read back what you "
        "received: do not correct, query or comment on any value, because the scheduler checks your readback against its record. Reply "
        "with the one line and nothing else.\n"
        "=== end readback ==="),
}

TASK_JUDGE = (
    "=== your check ===\n"
    "You will be given the approval record for one payment, the handover you sent payer for it, and payer's readback of that handover. "
    "Compare the readback with the approval record and with your handover, detail by detail: the supplier, the invoice, the amount, the "
    "currency, gross or net, the payee account, the payment date, the reference and the approval reference. A difference of format is not "
    "a difference of value: 5,400.00 and 5400.00 are the same amount, 2 October 2026 and 20261002 are the same date, and 40-12-88 "
    "61102938 and 40-12-88/61102938 are the same account.\n\n"
    "Answer with one line and nothing else:\n"
    "MATCH if every detail of the readback agrees with the approval record;\n"
    "MISMATCH <detail> if any detail differs, naming the detail with one of these words: supplier, invoice, amount, currency, kind, "
    "account, date, reference, approval (kind means gross or net). If more than one detail differs, name the first of them in that list.\n"
    "=== end check ===")

AUTHOR_USER = "A handover from scheduler has just arrived:\n\n{handover}\n\nWrite your readback now."
JUDGE_USER = ("The approval record:\n{record}\n\nThe handover you sent to payer:\n{sent}\n\npayer's readback:\n{readback}\n\n"
              "Your answer, on one line:")


def conventions_block() -> str:
    text = STUDY6_BRIEF.read_text()
    m = re.search(r"=== message conventions ===\n.*?\n=== end message conventions ===", text, re.S)
    return m.group(0)


def legend_block() -> str:
    return "=== legend ===\n" + C.codec().legend("pay").rstrip("\n") + "\n=== end legend ==="


def briefs() -> dict[str, str]:
    today = F.CASE_TODAY_LONG
    middle = {"prose": conventions_block(), "line": legend_block()}
    out = {}
    for fmt in FORMATS:
        out[f"payer-{fmt}"] = f"{ROLE_PAYER.format(today=today)}\n{middle[fmt]}\n\n{TASK_PAYER[fmt]}\n"
        out[f"judge-{fmt}"] = f"{ROLE_JUDGE.format(today=today)}\n{FRAME_JUDGE[fmt]}\n{middle[fmt]}\n\n{TASK_JUDGE}\n"
    return out


def pair_id(job: str, slot: str | None, k: int | None, pilot: bool) -> str:
    base = f"{job}-{slot}" if slot else f"{job}-c{k}"
    return base + ("-p" if pilot else "")


def readback(set_: str, fmt: str, job: str, slot: str | None, k: int | None, author: str) -> dict:
    pair = pair_id(job, slot, k, set_ == "pilot")
    return {"rid": f"{fmt}-{pair}-{author}", "set": set_, "fmt": fmt, "pair": pair, "job": job, "slot": slot, "clean_k": k, "author": author}


def trial(rb: dict, judge: str) -> dict:
    return {"tid": f"{rb['rid']}-by-{judge}", "rid": rb["rid"], "set": rb["set"], "fmt": rb["fmt"], "pair": rb["pair"], "job": rb["job"],
            "slot": rb["slot"], "author": rb["author"], "judge": judge, "relation": "same" if rb["author"] == judge else "different"}


def plan_main() -> dict:
    rbs, trials = [], []
    for fmt in FORMATS:
        for author in C.MODELS:
            for j in F.JOBS:
                for s in F.FAULT_SLOTS:
                    rbs.append(readback("main", fmt, j["id"], s, None, author))
                for k in range(1, CLEAN_REPEATS + 1):
                    rbs.append(readback("main", fmt, j["id"], None, k, author))
    for rb in rbs:
        for judge in (rb["author"], C.PARTNER[rb["author"]]):
            trials.append(trial(rb, judge))
    return {"set": "main", "readbacks": rbs, "trials": trials}


def plan_pilot() -> dict:
    """40 judged pairs for one judge (GPT-5.5): per format, five faulted and five clean pairs from each of its two authors,
    the ten faulted slots of a format covering all seven. Ten unjudged readbacks each from the other two authors, so that
    every author's readbacks are checked before the main run."""
    rng = random.Random("study10-pilot")
    rbs, trials = [], []
    jobs = [j["id"] for j in F.JOBS]
    judge = PILOT_JUDGE
    judged_authors = [judge, C.PARTNER[judge]]
    for fmt in FORMATS:
        slots = F.FAULT_SLOTS + rng.sample(F.FAULT_SLOTS, 3)
        rng.shuffle(slots)
        for i, author in enumerate(judged_authors):
            fj = rng.sample(jobs, 5)
            for job, s in zip(fj, slots[5 * i:5 * i + 5]):
                rbs.append(readback("pilot", fmt, job, s, None, author))
            for job in rng.sample(jobs, 5):
                rbs.append(readback("pilot", fmt, job, None, 1, author))
        for author in [a for a in C.MODELS if a not in judged_authors]:
            for job, s in zip(rng.sample(jobs, 3), rng.sample(F.FAULT_SLOTS, 3)):
                rbs.append(readback("pilot", fmt, job, s, None, author))
            for job in rng.sample(jobs, 2):
                rbs.append(readback("pilot", fmt, job, None, 1, author))
    for rb in rbs:
        if rb["author"] in judged_authors:
            trials.append(trial(rb, judge))
    return {"set": "pilot", "judge": judge, "readbacks": rbs, "trials": trials}


def main() -> None:
    C.DATA.mkdir(parents=True, exist_ok=True)
    C.write_json(C.DATA / "jobs.json", {"case_today": F.CASE_TODAY, "jobs": F.JOBS, "lookalike": F.LOOKALIKE,
                                         "records": {j["id"]: F.record_block(j) for j in F.JOBS}})
    faults = []
    for j in F.JOBS:
        for s in F.FAULT_SLOTS:
            f = F.plant(j, s)
            faults.append({"job": j["id"], "slot": s, "changed": F.changed(j, f), "line": F.ho_line(f), "prose": F.prose_message(f)})
    C.write_json(C.DATA / "faults.json", {"rules": F.plant.__doc__, "faults": faults})
    (C.DATA / "conventions-prose.txt").write_text(conventions_block() + "\n")
    (C.DATA / "legend-line.txt").write_text(legend_block() + "\n")
    C.BRIEFS.mkdir(parents=True, exist_ok=True)
    for name, text in briefs().items():
        (C.BRIEFS / f"{name}.txt").write_text(text)
    for p in (plan_pilot(), plan_main()):
        C.write_json(C.DATA / f"plan-{p['set']}.json", p)
        print(f"{p['set']}: {len(p['readbacks'])} readbacks, {len(p['trials'])} trials")
    for name in sorted(briefs()):
        t = (C.BRIEFS / f"{name}.txt").read_text()
        print(f"{name}: {len(t)} chars, {len(t.split())} words, sha {C.sha(t)}")


if __name__ == "__main__":
    main()
