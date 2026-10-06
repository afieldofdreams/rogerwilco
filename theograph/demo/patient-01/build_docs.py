#!/usr/bin/env python3
"""Write the six synthetic documents of demo patient 01 to this folder, wrapped at 92 characters.

One fictional patient over ten months: a GP referral, a first cardiology clinic letter, a discharge
summary from an admission, a follow-up clinic letter, a GP medication review and a correction letter.
The facts recur (the problem list and the medicines are restated in every letter), change (ramipril
5 mg to 10 mg, bisoprolol started and later reduced, aspirin stopped for clopidogrel, smoking) and get
corrected (the discharge summary's eGFR). Everything is invented; no real person or record is
represented. usage: python3 build_docs.py
"""
from __future__ import annotations
import pathlib, re, textwrap

HERE = pathlib.Path(__file__).resolve().parent
WIDTH = 92
DOCS: dict[str, str] = {}

DOCS["d01-gp-referral"] = """\
Ridgeway Lane Surgery, referral letter
Date: 14 January 2026
From: Dr S. Iqbal, GP
To: Cardiology Outpatients, Saltmarsh District Hospital
Re: Mr Thomas ABBOTT, DOB 12/03/1961, NHS no. 943 476 5919

Dear Colleague,

I would be grateful if you would see this 64-year-old man with three months of chest tightness on
exertion. It comes on after about half a mile of brisk walking or one flight of stairs, is central,
settles within five minutes of rest, and has never occurred at rest. There is no associated
breathlessness, palpitations or syncope.

He had an NSTEMI in March 2021 treated with PCI to the LAD at your hospital and was discharged
from your clinic in 2022. He has hypertension and hypercholesterolaemia. He smokes about 15
cigarettes a day and has declined cessation support twice. His father had a myocardial
infarction at 58.

Current medication: aspirin 75 mg once daily, atorvastatin 80 mg at night, ramipril 5 mg once
daily. He is allergic to penicillin (rash as a child).

Examination: BP 152/90, pulse 72 regular, heart sounds normal, chest clear. Weight 93 kg. ECG in
the surgery today shows sinus rhythm with old anterior Q waves and no acute change.

Bloods 9 January 2026: total cholesterol 4.4 mmol/L, LDL 2.4 mmol/L, HbA1c 40 mmol/mol, eGFR 82,
creatinine 84.

I have started him on GTN spray as required and asked him to use it before exertion. I would
value your assessment of his symptoms and consideration of further investigation.

Yours sincerely,
Dr S. Iqbal
"""

DOCS["d02-cardiology-letter-1"] = """\
Saltmarsh District Hospital, Cardiology Outpatients
Clinic date: 3 March 2026
Consultant: Dr Ana Kovac, Consultant Cardiologist
To: Dr S. Iqbal, Ridgeway Lane Surgery
Re: Mr Thomas ABBOTT, DOB 12/03/1961, hospital no. SDH-204417

Diagnoses:
1. Stable angina, new since late 2025
2. NSTEMI March 2021, PCI to the LAD
3. Hypertension
4. Hypercholesterolaemia
5. Penicillin allergy

Dear Dr Iqbal,

Thank you for referring Mr Abbott. He describes exertional chest tightness for about four
months, reproducible at half a mile or one flight of stairs and relieved by rest within five
minutes. He has used the GTN spray you prescribed perhaps twice a week with good effect. There
has been no rest pain and no breathlessness. He continues to smoke 15 a day.

On examination BP 146/88, pulse 70 regular, heart sounds normal, no signs of heart failure.
Weight 92 kg. ECG today unchanged from yours: sinus rhythm, old anterior Q waves.

I think this is stable angina on the background of his previous infarct. I have started
bisoprolol 5 mg once daily and increased ramipril from 5 mg to 10 mg once daily for his blood
pressure. Aspirin 75 mg once daily and atorvastatin 80 mg at night continue unchanged. I have
requested a CT coronary angiogram and an echocardiogram. I have again advised him to stop
smoking and given him the details of the community stop smoking service.

If the CT shows significant disease beyond the stented segment we will discuss invasive
angiography. Please check his renal function and blood pressure in two weeks.

I will see him again with the results in eight weeks.

Yours sincerely,
Dr Ana Kovac
"""

DOCS["d03-discharge-summary"] = """\
Saltmarsh District Hospital, Cardiology
Discharge summary
Patient: Mr Thomas ABBOTT, DOB 12/03/1961, hospital no. SDH-204417
Admitted: 19 May 2026
Discharged: 22 May 2026
Consultant: Dr Ana Kovac
GP: Dr S. Iqbal, Ridgeway Lane Surgery

Principal diagnosis: unstable angina; no myocardial infarction (troponin negative)
Procedure: coronary angiography 20 May 2026 with drug-eluting stent to the circumflex artery
Other diagnoses: hypertension; hypercholesterolaemia; stable angina since late 2025; NSTEMI
March 2021 with PCI to the LAD
Allergies: penicillin (rash)

Presentation: two episodes of chest pain at rest on 18 May lasting twenty minutes, relieved by
GTN. On arrival pain free, BP 138/82, heart rate 64, saturations 97% on air. ECG sinus rhythm
with old anterior Q waves and no new changes. Troponin 8 ng/L on arrival and 9 ng/L at six
hours, both within the normal range.

Investigations: the CT coronary angiogram requested in clinic had shown a tight proximal
circumflex stenosis. Angiography on 20 May confirmed a 90% proximal circumflex stenosis, patent
LAD stent, and minor irregularities elsewhere. A drug-eluting stent was placed to the circumflex
with a good result. Echocardiogram on 21 May: ejection fraction 52%, mild anterior hypokinesis,
no significant valve disease.

Bloods:
              Admission   Discharge
  Hb          141         138
  Creatinine  86          92
  eGFR        81          75
  Potassium   4.4         4.6

Medication changes:
  clopidogrel 75 mg once daily started, for twelve months after the stent
  aspirin stopped; clopidogrel replaces it as his single antiplatelet
  bisoprolol reduced from 5 mg to 2.5 mg once daily because of a resting heart rate of 52
  ramipril 10 mg once daily continues unchanged
  atorvastatin 80 mg at night continues unchanged
  GTN spray as required continues

He was seen by the smoking cessation nurse on the ward and has accepted a referral. He has been
advised not to drive for one week after the stent.

Follow-up: cardiology clinic in six weeks. Cardiac rehabilitation referral made. GP please
repeat renal function and potassium in two weeks.
"""

DOCS["d04-cardiology-letter-2"] = """\
Saltmarsh District Hospital, Cardiology Outpatients
Clinic date: 7 July 2026
Consultant: Dr Ana Kovac, Consultant Cardiologist
To: Dr S. Iqbal, Ridgeway Lane Surgery
Re: Mr Thomas ABBOTT, DOB 12/03/1961, hospital no. SDH-204417

Diagnoses:
1. Unstable angina May 2026, drug-eluting stent to the circumflex 20 May 2026
2. Stable angina since late 2025, now resolved
3. NSTEMI March 2021, PCI to the LAD
4. Hypertension
5. Hypercholesterolaemia
6. Penicillin allergy

Dear Dr Iqbal,

I reviewed Mr Abbott six weeks after his stent. He has had no chest pain since discharge, at
rest or on exertion, and has not needed his GTN spray. He is walking three miles a day and has
started cardiac rehabilitation. He stopped smoking on 1 June 2026 with the community service
and is using nicotine patches.

On examination BP 132/80, pulse 58 regular, heart sounds normal, chest clear. Weight 90 kg.

Bloods from your surgery on 5 June: creatinine 88, eGFR 79, potassium 4.5.

Clopidogrel 75 mg once daily continues until May 2027, then stops. Bisoprolol 2.5 mg once daily,
ramipril 10 mg once daily and atorvastatin 80 mg at night continue unchanged. I have told him
he may drive.

No further investigation is planned. I will see him once more in six months and then discharge
him to your care if he remains well.

Yours sincerely,
Dr Ana Kovac
"""

DOCS["d05-gp-medication-review"] = """\
Ridgeway Lane Surgery, medication review
Date: 12 October 2026. Seen by: Priya Shah, Clinical Pharmacist
Patient: Mr Thomas ABBOTT, DOB 12/03/1961, practice ref P-0412

Annual medication review following his stent in May. He feels well, no chest pain, no
breathlessness, no bleeding or bruising on clopidogrel. He remains an ex-smoker since June, off
the patches since September. Walking daily.

Repeat medication confirmed: clopidogrel 75 mg once daily (review May 2027), bisoprolol 2.5 mg
once daily, ramipril 10 mg once daily, atorvastatin 80 mg at night, GTN spray as required (not
used since May). Penicillin allergy recorded.

BP today 128/78, pulse 60. Weight 89 kg.

Bloods 6 October 2026: total cholesterol 3.6 mmol/L, LDL 1.7 mmol/L, eGFR 80, creatinine 87,
potassium 4.4, HbA1c 41 mmol/mol.

He reports some muscle aches in his thighs over the last month, worse after walking, which he
wonders are from the atorvastatin. CK 180 U/L, within range. Discussed; he would like to
continue the statin for now and see if it settles. Review in three months if the aches persist.

Flu vaccination given today.
"""

DOCS["d06-correction-letter"] = """\
Saltmarsh District Hospital, Cardiology
Correction to discharge summary
Date: 2 June 2026
Patient: Mr Thomas ABBOTT, DOB 12/03/1961, hospital no. SDH-204417
To: Dr S. Iqbal, Ridgeway Lane Surgery

Dear Dr Iqbal,

Please note a correction to the discharge summary of 22 May 2026. The eGFR at discharge was
recorded as 75; the laboratory result was 79 (creatinine 88). The admission values were
correct. No change to management follows.

I would also add that the clopidogrel duration is twelve months from 20 May 2026, so the stop
date is 20 May 2027, not the May 2027 review date implied by the summary.

Yours sincerely,
Dr Ana Kovac
"""

MANIFEST = """\
file,patient,type,date,specialty,author
d01-gp-referral.md,patient-01,referral,2026-01-14,general practice,Dr S. Iqbal
d02-cardiology-letter-1.md,patient-01,clinic letter,2026-03-03,cardiology,Dr Ana Kovac
d03-discharge-summary.md,patient-01,discharge summary,2026-05-22,cardiology,Dr Ana Kovac
d04-cardiology-letter-2.md,patient-01,clinic letter,2026-07-07,cardiology,Dr Ana Kovac
d05-gp-medication-review.md,patient-01,medication review,2026-10-12,general practice,Priya Shah
d06-correction-letter.md,patient-01,correction,2026-06-02,cardiology,Dr Ana Kovac
"""


HEADER_RE = re.compile(r"^[A-Z][A-Za-z ./-]{1,40}:")
LIST_RE = re.compile(r"^(\d+\.|-)\s")


def is_prose(line: str) -> bool:
    """A line that belongs to a prose paragraph: not blank, not indented (tables), not a list item, not a short header."""
    return bool(line) and not line.startswith("  ") and not LIST_RE.match(line) and not line.endswith(":") \
        and not (HEADER_RE.match(line) and len(line) <= 60)


def unwrap(text: str) -> list[str]:
    """Join the lines of a prose paragraph into one line; keep headers, lists, tables and blank lines as they are."""
    out, buf = [], []
    for line in text.split("\n"):
        if is_prose(line):
            buf.append(line); continue
        if buf:
            out.append(" ".join(buf)); buf.clear()
        out.append(line)
    if buf:
        out.append(" ".join(buf))
    return out


def wrap(text: str) -> str:
    out = []
    for para in unwrap(text):
        if not para.strip() or para.startswith("  ") or len(para) <= WIDTH:
            out.append(para)
        else:
            out.extend(textwrap.wrap(para, WIDTH, break_long_words=False, break_on_hyphens=False))
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for name, text in DOCS.items():
        (HERE / f"{name}.md").write_text(wrap(text))
    (HERE / "docs.csv").write_text(MANIFEST)
    print(f"wrote {len(DOCS)} documents and docs.csv to {HERE}")
