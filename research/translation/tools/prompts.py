#!/usr/bin/env python3
"""Build the extractor prompt for one document in one arm.

usage: python3 tools/prompts.py --arm L --docs 1,2,3   # prints the prompt for those documents
"""
from __future__ import annotations
import argparse, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CODEC, count_tokens, doc_lines, enum_text, numbered  # noqa: E402

RULES = """You translate one clinical document into assertion lines. The lines are the record: someone who reads only your lines must know everything the document says about the patient, and be able to go back to the exact words behind each one.

Rules
1. One line per statement the document makes about the patient: each symptom, sign, examination finding, result, diagnosis, medicine, procedure, allergy, referral, social fact, functional fact, plan and piece of advice. A sentence that makes three statements ("no haemoptysis, no weight loss and no night sweats") gets three lines. Never merge two statements into one line.
2. item is <kind>:<concept>. kind is one of sym dx med proc meas alg ref soc func fu. concept is the thing itself in lowercase words joined by hyphens, generic drug names, no abbreviations (shortness-of-breath, not sob). Name the thing, not the sentence.
3. Negation and normality: "no X", "denies X", "not started X", "not arranged X" is item X with pol=NEG. A normal finding stated as normal ("chest clear", "heart sounds normal") is the finding as written with pol=POS (sym:chest-clear). An ex-smoker is soc:smoking pol=POS time=PAST; a never-smoker is soc:smoking pol=NEG. A negative test result is the test with pol=NEG.
4. act: OBS what the author examined or measured; RPT what the patient or someone else told them (add who=REL or who=OTH when it was not the patient); ASSESS the author's diagnosis or impression, including the diagnosis list at the top; ORD what they asked for (a test, a referral, a request to the GP); DONE what was carried out; RX a medicine the author prescribed, continued or changed, with chg saying how; PLAN what the author intends or has scheduled; ADV advice or information given to the patient. A medicine the patient reports taking is RPT. A medicine on a discharge list is RX with chg.
5. cert: CERT unless the words hedge. likely, probable, possible, query, cannot exclude are POSS. "if ... then" is COND, on the thing that depends on the condition. A risk that was warned about is HYPO.
6. subj: PT unless the statement is about a relative (FAM) or someone else (OTH).
7. time: PAST for history, past events, values on admission and anything now resolved; CUR for the present, including ongoing conditions and results being reported; FUT for plans, follow-up and anything that waits on a future check.
8. Values go in slots, as written, and res carries no unit: res=148/88 unit=mmHg; res=4850 (no thousands separator); dose=10mg, dose=1.2g, dose=18micrograms; route and freq from the vocabulary (freq=QDS+PRN); chg for medicines (START STOP INC DEC CONT SWITCH HOLD CHG); site for a body part or side (site=left-forehead); when for a date or interval as written (when=2021, when=6w, when=3d, when=admission, when=discharge).
9. Tables: one line per cell that is a value. The column says when: admission is time=PAST when=admission, discharge is time=CUR when=discharge. A previous value in brackets ("HbA1c 62 (previous 58)") is its own line with time=PAST. Reference ranges are not statements.
10. src=doc:<N>#l<a> or src=doc:<N>#l<a>-<b> names the numbered line or lines where the words are. Exactly one src per line. The quote is the shortest run of words from those lines that supports the statement, copied exactly: no paraphrase, no added words. A quote may run across two lines where a sentence wraps.
11. A statement made twice (a diagnosis in the header and again in the body, a medicine in the text and again in the discharge list) gets one line, at its first occurrence. A statement that corrects an earlier one gets its own line with re=<id of the line it corrects>.
12. Out of scope: headers, names, dates of birth, hospital numbers, greetings, sign-offs, and statements about the letter itself rather than the patient."""

LINES_FORM = """Form
Every line is an ST from you to the record, then one DN to human at the end:
RW1 ST extractor-<n> from=extractor to=record p=clin item=<kind>:<concept> act=<act> pol=<pol> cert=<cert> subj=<subj> time=<time> [res= unit= dose= route= freq= chg= site= who= when=] src=doc:<N>#l<a>[-<b>] // <quote>
RW1 DN extractor-<n> re=human-01 from=extractor to=human p=clin item=doc:<N> out=OK n=<number of ST lines>
Number the ids extractor-1, extractor-2, ... in document order. No other lines, no blank lines, no commentary.

Example (from a different document):
RW1 ST extractor-1 from=extractor to=record p=clin item=meas:blood-pressure act=OBS pol=POS cert=CERT subj=PT time=CUR res=148/88 unit=mmHg src=doc:9#l24 // blood pressure was 148/88 mmHg
RW1 ST extractor-2 from=extractor to=record p=clin item=sym:chest-pain act=RPT pol=NEG cert=CERT subj=PT time=CUR src=doc:9#l15-16 // no exertional chest pain
RW1 ST extractor-3 from=extractor to=record p=clin item=med:ramipril act=RX pol=POS cert=CERT subj=PT time=CUR dose=10mg freq=OD chg=INC src=doc:9#l30 // increased ramipril from 5 mg to 10 mg once daily
RW1 ST extractor-4 from=extractor to=record p=clin item=ref:cardiology act=ORD pol=POS cert=COND subj=PT time=FUT src=doc:9#l36-37 // refer him back to us promptly
RW1 DN extractor-5 re=human-01 from=extractor to=human p=clin item=doc:9 out=OK n=4"""

JSON_FORM = """Form
Every row is one JSON object on one line (JSON Lines), one per statement, in document order:
{"id":"extractor-<n>","item":"<kind>:<concept>","act":"<act>","pol":"<pol>","cert":"<cert>","subj":"<subj>","time":"<time>","src":"doc:<N>#l<a>[-<b>]","quote":"<quote>"}
plus any of "res","unit","dose","route","freq" (an array),"chg","site","who","when","re" when they apply. No other keys, no wrapper array, no commentary.

Example (from a different document):
{"id":"extractor-1","item":"meas:blood-pressure","act":"OBS","pol":"POS","cert":"CERT","subj":"PT","time":"CUR","res":"148/88","unit":"mmHg","src":"doc:9#l24","quote":"blood pressure was 148/88 mmHg"}
{"id":"extractor-2","item":"sym:chest-pain","act":"RPT","pol":"NEG","cert":"CERT","subj":"PT","time":"CUR","src":"doc:9#l15-16","quote":"no exertional chest pain"}
{"id":"extractor-3","item":"med:ramipril","act":"RX","pol":"POS","cert":"CERT","subj":"PT","time":"CUR","dose":"10mg","freq":["OD"],"chg":"INC","src":"doc:9#l30","quote":"increased ramipril from 5 mg to 10 mg once daily"}
{"id":"extractor-4","item":"ref:cardiology","act":"ORD","pol":"POS","cert":"COND","subj":"PT","time":"FUT","src":"doc:9#l36-37","quote":"refer him back to us promptly"}"""


def legend() -> str:
    return subprocess.run([sys.executable, str(CODEC), "legend", "--profile", "clin", "--lean"], capture_output=True, text=True, check=True).stdout.strip()


def build(arm: str, docs: list[int], out: str, per_doc: dict[int, str] | None = None) -> str:
    parts = [RULES, ""]
    if arm == "L":
        parts += [LINES_FORM, "", "Vocabulary (the rogerwilco legend for profile clin):", "```", legend(), "```"]
    else:
        parts += [JSON_FORM, "", "Vocabulary (closed: use these codes and no others):", "```", enum_text(), "```"]
    parts += ["", f"There are {len(docs)} documents below, each with its own kickoff. Translate each one on its own: number its ids from extractor-1 again, and start its block with a header row of exactly `# doc:<N>`.",
              "The rows are the whole output: no introduction, no commentary, no code fences."]
    for d in docs:
        n = len(doc_lines(d))
        parts += ["", f"Kickoff: RW1 HO human-01 from=human to=extractor p=clin item=doc:{d} ask=EXTRACT due=20261001 src=doc:{d}#l1-{n} // translate every statement this document makes about the patient into assertion lines",
                  "", f"Document doc:{d} (the number at the left of each line is its line number for src=):", "```", numbered(d), "```"]
    if per_doc:
        files = "; ".join(f"doc:{d} to {per_doc[d]}" for d in docs)
        parts += ["", f"Write each document's rows, and nothing else, to its own file with the Write tool, one Write call per document: {files}. Then reply DONE and nothing else. Use no other tool and read no other file."]
    else:
        parts += ["", f"Write the rows for all {len(docs)} documents, and nothing else, to the file {out} with the Write tool, then reply DONE and nothing else. Use no other tool and read no other file."]
    return "\n".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["L", "J"])
    ap.add_argument("--docs", required=True, help="comma-separated document numbers")
    ap.add_argument("--out", default="OUTPUT")
    a = ap.parse_args()
    p = build(a.arm, [int(x) for x in a.docs.split(",")], a.out)
    print(p)
    print(f"\n[{count_tokens(p)} tokens]", file=sys.stderr)
