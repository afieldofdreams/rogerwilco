"""The extraction prompt for one document, and the fix-round message."""
from __future__ import annotations
import subprocess, sys
from . import CODEC, profile
from .registry import numbered

RULES = """You translate one clinical document into assertion lines. The lines are the record: someone who reads only your lines must know everything the document says about the patient, and be able to go back to the exact words behind each one.

Rules
1. One line per statement the document makes about the patient: each symptom, sign, examination finding, result, diagnosis, medicine, procedure, allergy, referral, social fact, functional fact, plan and piece of advice. A sentence that makes three statements ("no haemoptysis, no weight loss and no night sweats") gets three lines. Never merge two statements into one line.
2. item is <kind>:<concept>. kind is one of sym dx med proc meas alg ref soc func fu. concept is the thing itself in lowercase words joined by hyphens, generic drug names, no abbreviations (shortness-of-breath, not sob). Name the thing, not the sentence. Use the same concept name every time the same thing is meant.
3. Negation and normality: "no X", "denies X", "not started X", "not arranged X" is item X with pol=NEG. A normal finding stated as normal ("chest clear", "heart sounds normal") is the finding as written with pol=POS (sym:chest-clear). An ex-smoker is soc:smoking pol=POS time=PAST; a never-smoker is soc:smoking pol=NEG. A negative test result is the test with pol=NEG.
4. act: OBS what the author examined or measured; RPT what the patient or someone else told them (add who=REL or who=OTH when it was not the patient); ASSESS the author's diagnosis or impression, including the diagnosis list at the top; ORD what they asked for (a test, a referral, a request to the GP); DONE what was carried out; RX a medicine the author prescribed, continued or changed, with chg saying how; PLAN what the author intends or has scheduled; ADV advice or information given to the patient. A medicine the patient reports taking, or listed as current medication in a referral, is RPT. A medicine on a discharge list or in a clinic plan is RX with chg. A test or procedure that "showed", "confirmed" or "revealed" something was DONE, even when the sentence also says who requested it; its findings are their own lines.
5. cert: CERT unless the words hedge. likely, probable, possible, query, cannot exclude are POSS. "if ... then" is COND, on the thing that depends on the condition. A risk that was warned about is HYPO.
6. subj: PT unless the statement is about a relative (FAM) or someone else (OTH).
7. time: PAST for history, past events, values on admission and anything now resolved; CUR for the present, including ongoing conditions and results being reported; FUT for plans, follow-up and anything that waits on a future check.
8. Values go in slots, as written, and res carries no unit: res=148/88 unit=mmHg; res=4850 (no thousands separator); dose=10mg, dose=1.2g, dose=18micrograms; route and freq from the vocabulary (freq=QDS+PRN); chg for medicines (START STOP INC DEC CONT SWITCH HOLD CHG); site for a body part or side (site=left-forehead); when for a date or interval as written (when=20260520, when=2021, when=6w, when=3d, when=admission, when=discharge). Give when= whenever the document gives a date, a month, a year or an interval for the statement. Prefer a date to an interval when the document gives both ("twelve months from 20 May 2026": when=20260520 on the start, a second line for the stop with when=20270520 if the document states it).
9. Tables: one line per cell that is a value. The column says when: admission is time=PAST when=admission, discharge is time=CUR when=discharge. A previous value in brackets ("HbA1c 62 (previous 58)") is its own line with time=PAST. Reference ranges are not statements.
10. src=doc:<N>#l<a> or src=doc:<N>#l<a>-<b> names the numbered line or lines where the words are. Exactly one src per line. The quote is the shortest run of words from those lines that supports the statement, copied exactly: no paraphrase, no added words. A quote may run across two lines where a sentence wraps.
11. A statement made twice in this document (a diagnosis in the header and again in the body, a medicine in the text and again in the discharge list) gets one line, at its first occurrence. A statement that corrects an earlier one in this document gets its own line with re=<id of the line it corrects>. A document that corrects another document states the corrected value as its own statement with when= the date the value belongs to.
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


def legend() -> str:
    return subprocess.run([sys.executable, str(CODEC), "legend", "--profile", "clin", "--lean"], capture_output=True, text=True, check=True).stdout.strip()


def build(doc: dict) -> str:
    n = doc["num"]
    parts = [RULES, "", LINES_FORM, "", "Vocabulary (the rogerwilco legend for profile clin):", "```", legend(), "```", "",
             f"Kickoff: RW1 HO human-01 from=human to=extractor p=clin item=doc:{n} ask=EXTRACT due=20261001 src=doc:{n}#l1-{doc['n_lines']} // translate every statement this document makes about the patient into assertion lines",
             "", f"Document doc:{n} (the number at the left of each line is its line number for src=). Document type: {doc.get('type')}. Document date: {doc.get('date')}.", "```", numbered(doc), "```", "",
             "Reply with the rows and nothing else: no introduction, no commentary, no code fences."]
    return "\n".join(parts)


REVIEW_MARK = "Completeness review."


def review_message(n_lines: int, next_id: int) -> str:
    """The second turn: the model reads the document again against its own lines and adds what it missed."""
    return (f"{REVIEW_MARK} Read the document again, line 1 to line {n_lines}, against the lines you wrote. For every statement about the patient "
            f"that has no line yet (a finding, a value, a medicine, a plan, a negation, a piece of advice, a second statement inside a sentence you gave "
            f"one line), write the missing line now, same rules and form, continuing the numbering from extractor-{next_id}. Do not repeat or rewrite "
            f"lines you already gave. Finish with one DN line to human with n=<number of lines added>; if nothing is missing, reply with only that DN line "
            f"with n=0. Rows only, no commentary, no code fences.")


def fix_message(errors: list[str]) -> str:
    return ("The gate rejected that output. Every row must be a valid line and every quote must be copied word for word from the numbered line(s) named in src=, in the document's order, with no words dropped or added (a sentence that wraps needs src=doc:N#l<a>-<b>). res is only for numbers; a finding without a number has no res. Problems:\n\n"
            + "\n".join("  " + e for e in errors) + "\n\nReply with the whole output again, every row, with every problem fixed and everything that was right kept. Rows only, no commentary, no code fences.")
