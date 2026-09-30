You translate one clinical document into assertion lines. The lines are the record: someone who reads only your lines must know everything the document says about the patient, and be able to go back to the exact words behind each one.

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
12. Out of scope: headers, names, dates of birth, hospital numbers, greetings, sign-offs, and statements about the letter itself rather than the patient.

Form
Every row is one JSON object on one line (JSON Lines), one per statement, in document order:
{"id":"extractor-<n>","item":"<kind>:<concept>","act":"<act>","pol":"<pol>","cert":"<cert>","subj":"<subj>","time":"<time>","src":"doc:<N>#l<a>[-<b>]","quote":"<quote>"}
plus any of "res","unit","dose","route","freq" (an array),"chg","site","who","when","re" when they apply. No other keys, no wrapper array, no commentary.

Example (from a different document):
{"id":"extractor-1","item":"meas:blood-pressure","act":"OBS","pol":"POS","cert":"CERT","subj":"PT","time":"CUR","res":"148/88","unit":"mmHg","src":"doc:9#l24","quote":"blood pressure was 148/88 mmHg"}
{"id":"extractor-2","item":"sym:chest-pain","act":"RPT","pol":"NEG","cert":"CERT","subj":"PT","time":"CUR","src":"doc:9#l15-16","quote":"no exertional chest pain"}
{"id":"extractor-3","item":"med:ramipril","act":"RX","pol":"POS","cert":"CERT","subj":"PT","time":"CUR","dose":"10mg","freq":["OD"],"chg":"INC","src":"doc:9#l30","quote":"increased ramipril from 5 mg to 10 mg once daily"}
{"id":"extractor-4","item":"ref:cardiology","act":"ORD","pol":"POS","cert":"COND","subj":"PT","time":"FUT","src":"doc:9#l36-37","quote":"refer him back to us promptly"}

Vocabulary (closed: use these codes and no others):
```
act: OBS=observed, examined or measured by the author, RPT=reported by the patient or a third party, not verified by the author, ASSESS=the author's assessment, diagnosis or impression, ORD=ordered or requested: a test, a referral, an action asked of someone else, DONE=carried out: a procedure, treatment or action that happened, RX=a medicine prescribed, continued or changed by the author; chg says how, PLAN=the author's intention or a scheduled next step, ADV=advice or information given to the patient or carer
pol: POS=present or affirmed, NEG=absent, denied or negated
cert: CERT=stated as fact, POSS=possible, likely, suspected or queried, COND=conditional on something else happening, HYPO=hypothetical: a warning, a risk or a possibility discussed
subj: PT=the patient, FAM=a family member, OTH=someone else
time: CUR=current at the time of the document, including ongoing conditions, PAST=before the document: history, a past event, resolved, FUT=after the document: planned or expected
route: PO=by mouth, IV=intravenous, IM=intramuscular, SC=subcutaneous, TOP=topical, INH=inhaled, NEB=nebulised, PR=rectal, SL=sublingual, OTH=another route, as quoted
freq: OD=once a day, BD=twice a day, TDS=three times a day, QDS=four times a day, PRN=as required, NOCTE=at night, MANE=in the morning, WKLY=weekly, MTHLY=monthly, STAT=once, now, OTH=another frequency, as quoted
chg: START=started or newly prescribed, STOP=stopped, INC=dose increased, DEC=dose decreased, CONT=continued unchanged, SWITCH=replaced by another medicine, HOLD=withheld for now, CHG=changed in another way: route, formulation, frequency
who: CLIN=the author or another clinician, PT=the patient, REL=a relative or carer, OTH=another source: a laboratory, another service, unknown
kind (the part of item before the colon): sym=symptom, sign, examination or investigation finding, dx=diagnosis, condition or problem, med=medicine, proc=procedure, operation, investigation or intervention, meas=measurement with a value: vital sign, test result, score, alg=allergy or intolerance, ref=referral, soc=social or lifestyle fact, func=functional status, mobility, exercise tolerance, fu=follow-up, review or appointment
slots: src=where the words are: doc:<id>#l<n> or doc:<id>#l<n>-<m>, the numbered line(s) of the source; exactly one per line; res=the measured or reported value as written, no units (7.2, 148/92, 3/10); unit=unit of res as written, no spaces (mmol/L, mmHg, kg, %); dose=medicine dose as written, no spaces (500mg, 1g, 2puffs); route=medicine route; freq=medicine frequency; several join with + (QDS+PRN); chg=what happened to a medicine at this encounter; site=body site or laterality, lowercase, hyphens (left-knee, right-iliac-fossa); who=who said or did it; omit when it is the author; when=date or interval as written, no spaces (2009, 20260914, 6w, 3d, 10y)
res is a number as written, or two numbers with a slash (7.2, 148/88); units go in unit.
```

There are 1 documents below, each with its own kickoff. Translate each one on its own: number its ids from extractor-1 again, and start its block with a header row of exactly `# doc:<N>`.
The rows are the whole output: no introduction, no commentary, no code fences.

Kickoff: RW1 HO human-01 from=human to=extractor p=clin item=doc:7 ask=EXTRACT due=20261001 src=doc:7#l1-43 // translate every statement this document makes about the patient into assertion lines

Document doc:7 (the number at the left of each line is its line number for src=):
```
  1  Saltmarsh District Hospital, Cardiology
  2  Discharge summary
  3  Patient: Mr Gordon PRICE, DOB 23/04/1950, hospital no. SDH-226001
  4  Admitted: 14 September 2026
  5  Discharged: 20 September 2026
  6  Consultant: Dr Ana Kovac
  7  GP: Dr H. Adeyemi, Ridgeway Lane Surgery
  8  
  9  Diagnosis: decompensated heart failure with reduced ejection fraction
 10  Other: ischaemic heart disease (likely cause), hypertension, hyperkalaemia on admission
 11  
 12  Presentation: two weeks of increasing breathlessness, orthopnoea and ankle swelling. He had
 13  no chest pain during the admission.
 14  
 15  Investigations: echocardiogram on 15 September showed a dilated left ventricle with an
 16  ejection fraction of 35% and moderate mitral regurgitation. NT-proBNP 4,850 ng/L. Potassium
 17  5.6 mmol/L on admission, 5.1 at discharge. Creatinine 118. ECG: sinus rhythm, left bundle
 18  branch block.
 19  
 20  Weights:
 21    Admission   96.4 kg
 22    Discharge   91.2 kg
 23  
 24  Treatment: intravenous furosemide 80 mg twice daily for four days, then oral. He was
 25  diuresed by five kilograms.
 26  
 27  Medication changes:
 28    furosemide increased to 80 mg orally once daily (was 40 mg before admission)
 29    ramipril reduced from 10 mg to 5 mg once daily because of the potassium
 30    ibuprofen stopped; he has been told to avoid all anti-inflammatory drugs
 31    spironolactone withheld until the potassium is rechecked; if potassium is 5.0 or below at
 32      that check, start spironolactone 25 mg once daily
 33    bisoprolol 5 mg once daily continues unchanged
 34    atorvastatin 40 mg at night continues unchanged
 35  
 36  He is not for an implantable defibrillator at present. Sacubitril/valsartan will be
 37  considered in clinic once his potassium and renal function allow.
 38  
 39  Advice given: weigh himself every morning and contact the heart failure nurse if his weight
 40  rises by more than 2 kg in three days. He does not drink alcohol.
 41  
 42  Follow-up: repeat U&E in one week (GP please). Heart failure nurse referral made. Cardiology
 43  clinic in six weeks.
```

Write each document's rows, and nothing else, to its own file with the Write tool, one Write call per document: doc:7 to /home/claude/rogerwilco/research/translation/runs/J-sonnet-2/raw/doc07.txt. Then reply DONE and nothing else. Use no other tool and read no other file.