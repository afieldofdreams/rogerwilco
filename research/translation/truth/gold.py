#!/usr/bin/env python3
"""Gold assertions for the twelve synthetic documents, one entry per statement the document makes.

Format of an entry (fields separated by " | "):
  lines | item | act pol cert subj time | extra slots | verbatim quote | tags | synonyms (; separated)
Wildcards: a "*" in place of act, pol, cert, subj or time accepts any value (a defensible ambiguity).
Extra slots: key=value, space separated; res unit dose route freq chg site who when. A value of "*" accepts any.
Options after the tags, in the tags field: soft (counts when found, not against recall), alt=l<n>[-<m>]
(the same statement recurs on these lines; a line citing either place matches), kindany (kind not scored).

Compiles to truth/gold.json and checks every quote against the numbered document text.
usage: python3 truth/gold.py
"""
from __future__ import annotations
import json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
DOCS = HERE.parent / "data" / "docs"

G: dict[int, list[str]] = {}
TOLERATED: dict[int, list[str]] = {}   # concepts an extractor may add without being counted as a false positive

G[1] = [
 "l8 | dx:stable-angina | ASSESS POS CERT PT CUR | | Stable angina, symptoms improved | | angina; angina-stable; stable-angina-improved",
 "l9 | dx:nstemi | ASSESS POS CERT PT PAST | when=2021 | NSTEMI March 2021 | ABBREV HIST | non-st-elevation-myocardial-infarction; myocardial-infarction; nstemi-2021",
 "l9 | proc:pci | DONE POS CERT PT PAST | when=2021 site=lad | treated with PCI to the LAD | ABBREV HIST | percutaneous-coronary-intervention; pci-lad; coronary-stent",
 "l10 | dx:hypertension | ASSESS POS CERT PT CUR | | Hypertension | | high-blood-pressure",
 "l11 | dx:hypercholesterolaemia | ASSESS POS CERT PT CUR | | Hypercholesterolaemia | | high-cholesterol; hyperlipidaemia",
 "l15-16 | sym:exertional-chest-pain | RPT NEG CERT PT CUR | | no exertional chest pain | NEG | chest-pain; chest-pain-on-exertion; chest-pain-exertional",
 "l16 | sym:chest-pain-at-rest | RPT NEG CERT PT CUR | | no chest pain at rest | NEG | chest-pain; rest-chest-pain; resting-chest-pain",
 "l16 | func:walking | RPT POS CERT PT CUR | | walks about two miles a day without symptoms | | exercise-tolerance; walking-two-miles; exercise",
 "l16-17 | sym:palpitations | RPT POS CERT PT CUR | | occasional palpitations, perhaps twice a week, lasting a few seconds | | palpitation",
 "l17-18 | sym:dizziness | RPT NEG CERT PT CUR | | not associated with chest pain or dizziness | NEG | dizzy; light-headedness; lightheadedness",
 "l18 | sym:orthopnoea | RPT NEG CERT PT CUR | | denies any breathlessness lying flat | NEG | breathlessness-lying-flat; breathlessness; orthopnea",
 "l20 | soc:smoking | RPT POS CERT PT CUR | res=10 unit=cigarettes/day | continues to smoke around 10 cigarettes a day | SOC NUM | smoker; tobacco; current-smoker; cigarettes",
 "l20-21 | soc:smoking-cessation | ADV POS CERT PT CUR | | advised him to stop | | smoking; stop-smoking; smoking-cessation-advice; smoking-advice",
 "l21 | dx:myocardial-infarction | RPT POS CERT FAM PAST | | His father had a myocardial infarction at the age of 58 | FAM HIST | mi; heart-attack; family-history-myocardial-infarction",
 "l21-22 | dx:sudden-cardiac-death | RPT NEG CERT FAM PAST | | no family history of sudden cardiac death | FAM NEG | family-history-sudden-cardiac-death",
 "l24 | meas:blood-pressure | OBS POS CERT PT CUR | res=148/88 unit=mmHg | blood pressure was 148/88 mmHg | NUM UNITS | bp",
 "l24 | meas:pulse | OBS POS CERT PT CUR | res=62 | pulse 62 and regular | NUM | heart-rate; pulse-rate",
 "l24 | sym:regular-pulse | OBS POS CERT PT CUR | | pulse 62 and regular | soft | pulse-regular; regular-rhythm; regular-heart-rhythm",
 "l24 | sym:heart-sounds-normal | OBS POS CERT PT CUR | | heart sounds normal | | normal-heart-sounds; heart-sounds",
 "l25 | sym:heart-murmur | OBS NEG CERT PT CUR | | no murmurs | NEG | murmur; murmurs; cardiac-murmur",
 "l25 | sym:chest-clear | OBS POS CERT PT CUR | | the chest was clear | | clear-chest; chest-auscultation-normal; lungs-clear; chest",
 "l25 | meas:weight | OBS POS CERT PT CUR | res=91 unit=kg | Weight 91 kg | NUM UNITS | body-weight",
 "l27 | proc:ecg | DONE POS CERT PT CUR | | His ECG today | soft | electrocardiogram; 12-lead-ecg",
 "l27 | sym:sinus-rhythm | OBS POS CERT PT CUR | | ECG today shows sinus rhythm | | ecg-sinus-rhythm; normal-sinus-rhythm",
 "l27 | sym:ecg-changes | OBS NEG CERT PT CUR | | no new changes | NEG | new-ecg-changes; new-changes; ecg-new-changes",
 "l27-28 | meas:total-cholesterol | OBS POS CERT PT CUR | res=3.9 unit=mmol/L | total cholesterol 3.9 mmol/L | NUM UNITS | cholesterol",
 "l28 | meas:ldl-cholesterol | OBS POS CERT PT CUR | res=1.9 unit=mmol/L | LDL 1.9 mmol/L | ABBREV NUM | ldl",
 "l28 | meas:hba1c | OBS POS CERT PT CUR | res=41 unit=mmol/mol | HbA1c 41 mmol/mol | ABBREV NUM | glycated-haemoglobin",
 "l28 | meas:egfr | OBS POS CERT PT CUR | res=78 | eGFR 78 | ABBREV NUM | estimated-gfr; gfr",
 "l30 | med:ramipril | RX POS CERT PT CUR | dose=10mg freq=OD chg=INC | increased ramipril from 5 mg to 10 mg once daily | CHG | ",
 "l30-31 | med:bisoprolol | RX POS CERT PT CUR | dose=2.5mg freq=OD chg=CONT | Bisoprolol 2.5 mg once daily | | ",
 "l31 | med:atorvastatin | RX POS CERT PT CUR | dose=80mg freq=NOCTE chg=CONT | atorvastatin 80 mg at night | | ",
 "l31 | med:aspirin | RX POS CERT PT CUR | dose=75mg freq=OD chg=CONT | aspirin 75 mg once daily | | ",
 "l32 | med:antiarrhythmic | RX NEG CERT PT CUR | | I have not started an antiarrhythmic | NEG | antiarrhythmic-drug; antiarrhythmic-therapy",
 "l32 | dx:benign-ectopy | ASSESS POS POSS PT CUR | | the palpitations are likely benign ectopy | HEDGE | ectopy; ectopic-beats; benign-ectopic-beats; ectopics",
 "l33 | proc:ambulatory-ecg-monitor | ORD POS CERT PT FUT | when=7d | requested a 7-day ambulatory ECG monitor | | holter; 7-day-ecg; ambulatory-ecg; ecg-monitor; holter-monitor",
 "l33-34 | proc:echocardiogram | ORD POS CERT PT FUT | | an echocardiogram to reassess LV function | ABBREV | echo",
 "l36 | med:anticoagulation | PLAN POS COND PT FUT | | If the monitor shows atrial fibrillation he will need anticoagulation | COND | anticoagulant; anticoagulant-therapy",
 "l36-37 | ref:cardiology | ORD POS COND PT FUT | | refer him back to us promptly | COND | cardiology-referral; refer-back; cardiology-clinic",
 "l39 | fu:cardiology-clinic | PLAN POS CERT PT FUT | when=4m | I will see him again in four months | FU | review; follow-up; clinic-review; cardiology-review",
 "l39-40 | proc:renal-function-test | ORD POS CERT PT FUT | when=2w | repeat renal function two weeks after the ramipril increase | FU | u-and-e; renal-function; urea-and-electrolytes; renal-function-check; ue",
]
TOLERATED[1] = ["dx:atrial-fibrillation", "sym:chest-pain", "func:lv-function", "sym:lv-function"]

G[2] = [
 "l7 | dx:copd | ASSESS POS POSS PT CUR | | probable COPD, GOLD group B, awaiting confirmation | HEDGE ABBREV alt=l33 | chronic-obstructive-pulmonary-disease; copd-gold-b",
 "l11-12 | sym:breathlessness | RPT POS CERT PT CUR | when=18m | eighteen months of progressive breathlessness on exertion | DUR | exertional-breathlessness; dyspnoea; shortness-of-breath; breathlessness-on-exertion; exertional-dyspnoea",
 "l12-13 | func:exercise-tolerance | RPT POS CERT PT CUR | | SOB walking up one flight of stairs and has to stop after about 200 yards on the flat | ABBREV | walking-distance; walking; exercise-capacity; stairs",
 "l13 | meas:mrc-dyspnoea-grade | OBS POS CERT PT CUR | res=3 | MRC dyspnoea grade 3 | ABBREV NUM | mrc-dyspnoea-scale; mrc-grade; mrc-dyspnoea-score; mrc",
 "l13-14 | sym:productive-cough | RPT POS CERT PT CUR | | chronic productive cough with white sputum most mornings | | cough; chronic-cough; sputum",
 "l14 | sym:haemoptysis | RPT NEG CERT PT CUR | | no haemoptysis | NEG | ",
 "l14 | sym:weight-loss | RPT NEG CERT PT CUR | | no weight loss | NEG | ",
 "l14 | sym:night-sweats | RPT NEG CERT PT CUR | | no night sweats | NEG | ",
 "l15 | dx:chest-infection | RPT POS CERT PT PAST | res=2 when=1y | two courses of antibiotics from the practice in the last year for chest infections | HIST NUM | chest-infections; lower-respiratory-tract-infection; med:antibiotics; antibiotic-courses",
 "l17 | soc:smoking | RPT POS CERT PT PAST | res=20 unit=cigarettes/day | smoked 20 a day from the age of 16 until she stopped completely in January 2024 | SOC HIST NUM | ex-smoker; smoker; former-smoker; smoking-history",
 "l17-18 | meas:pack-years | OBS POS CERT PT PAST | res=50 unit=pack-years | a 50 pack-year history | NUM | smoking-pack-years; pack-year-history; soc:pack-years",
 "l18 | soc:occupation | RPT POS CERT PT PAST | | worked as a school cook | | occupation-school-cook; school-cook; employment",
 "l18 | soc:asbestos-exposure | RPT NEG CERT PT PAST | | has never worked with asbestos | NEG | asbestos; occupational-asbestos-exposure",
 "l18-19 | dx:asthma | RPT POS CERT FAM PAST | | Her mother had asthma | FAM | family-history-asthma",
 "l19 | dx:lung-cancer | RPT NEG CERT FAM PAST | | no family history of lung cancer or emphysema | FAM NEG | family-history-lung-cancer",
 "l19 | dx:emphysema | RPT NEG CERT FAM PAST | | no family history of lung cancer or emphysema | FAM NEG | family-history-emphysema",
 "l19-20 | soc:lives-with-husband | RPT POS CERT PT CUR | | She lives with her husband | | living-situation; lives-with-partner; lives-with-spouse; household",
 "l20 | func:stairs | RPT POS CERT PT CUR | | manages the stairs at home | | managing-stairs; mobility; stairs-at-home",
 "l22 | meas:oxygen-saturation | OBS POS CERT PT CUR | res=95 unit=% | saturations 95% on air | NUM UNITS | sats; spo2; saturations; oxygen-saturations",
 "l22 | meas:respiratory-rate | OBS POS CERT PT CUR | res=16 | respiratory rate 16 | NUM | rr",
 "l22 | sym:prolonged-expiration | OBS POS CERT PT CUR | | mildly prolonged expiration | | prolonged-expiratory-phase; expiration-prolonged",
 "l22-23 | sym:wheeze | OBS NEG CERT PT CUR | | no wheeze at rest | NEG | wheezing",
 "l23 | sym:clubbing | OBS NEG CERT PT CUR | | no clubbing | NEG | finger-clubbing",
 "l23 | sym:ankle-oedema | OBS NEG CERT PT CUR | | no ankle oedema | NEG | peripheral-oedema; oedema; ankle-swelling",
 "l23 | meas:bmi | OBS POS CERT PT CUR | res=31 | BMI 31 | ABBREV NUM | body-mass-index",
 "l25 | proc:spirometry | DONE POS CERT PT CUR | | Spirometry today | | lung-function-test",
 "l26 | meas:fev1 | OBS POS CERT PT CUR | res=1.42 unit=L | FEV1 1.42 L | TABLE NUM UNITS ABBREV | forced-expiratory-volume",
 "l26 | meas:fev1-percent-predicted | OBS POS CERT PT CUR | res=58 unit=% | 58% predicted | TABLE NUM | fev1-predicted; fev1-percent; fev1",
 "l27 | meas:fvc | OBS POS CERT PT CUR | res=2.71 unit=L | FVC 2.71 L | TABLE NUM UNITS ABBREV | forced-vital-capacity",
 "l27 | meas:fvc-percent-predicted | OBS POS CERT PT CUR | res=89 unit=% | 89% predicted | TABLE NUM | fvc-predicted; fvc-percent; fvc",
 "l28 | meas:fev1-fvc-ratio | OBS POS CERT PT CUR | res=0.52 | FEV1/FVC 0.52 | TABLE NUM | fev1/fvc; fev1-fvc; ratio",
 "l29 | sym:bronchodilator-reversibility | OBS NEG CERT PT CUR | | No significant bronchodilator reversibility | NEG TABLE | reversibility; bronchodilator-response",
 "l31 | proc:chest-xray | DONE POS CERT PT PAST | when=20260902 | Chest X-ray from 2 September 2026 | ABBREV | cxr; chest-x-ray; chest-radiograph",
 "l31 | sym:hyperinflation | OBS POS CERT PT CUR | | mild hyperinflation | | lung-hyperinflation; hyperinflated-lungs",
 "l33 | sym:obstructive-pattern | ASSESS POS CERT PT CUR | | The pattern is obstructive | | obstructive-spirometry; airflow-obstruction; obstructive-airways",
 "l33-34 | med:tiotropium | RX POS CERT PT CUR | dose=18micrograms route=INH freq=OD chg=START | started tiotropium 18 micrograms inhaled once daily | CHG | ",
 "l34-35 | med:salbutamol | RX POS CERT PT CUR | route=INH freq=PRN chg=CONT | continued her salbutamol inhaler as required | | salbutamol-inhaler",
 "l35 | med:inhaled-corticosteroid | RX NEG CERT PT CUR | | I have not started an inhaled steroid | NEG | inhaled-steroid; ics; corticosteroid",
 "l35 | meas:eosinophil-count | OBS POS CERT PT CUR | res=0.1 | her eosinophil count is 0.1 | NUM | eosinophils; blood-eosinophils",
 "l36 | dx:copd-exacerbation | RPT POS CERT PT PAST | res=2 | she has had only two exacerbations | HIST NUM | exacerbations; exacerbation",
 "l36-37 | ref:pulmonary-rehabilitation | ORD POS CERT PT FUT | | referred her to pulmonary rehabilitation | | pulmonary-rehab; rehabilitation",
 "l39-40 | proc:ct-chest | PLAN POS COND PT FUT | | I would arrange a CT of the chest | COND | ct-thorax; chest-ct; ct",
 "l40 | proc:full-blood-count | ORD POS CERT PT FUT | | asked for a full blood count | | fbc; blood-count",
 "l40 | proc:alpha-1-antitrypsin-level | ORD POS CERT PT FUT | | an alpha-1 antitrypsin level | | alpha-1-antitrypsin; a1at; alpha1-antitrypsin",
 "l42 | fu:respiratory-clinic | PLAN POS CERT PT FUT | when=3m | I will see her again in three months | FU | review; follow-up; clinic-review",
 "l42 | proc:spirometry | PLAN POS CERT PT FUT | | with repeat spirometry | FU | repeat-spirometry",
]
TOLERATED[2] = ["sym:chest-xray-normal", "sym:haemoptysis", "fu:pulmonary-rehabilitation-attendance", "sym:symptoms", "sym:chest-infections", "med:antibiotics"]

G[3] = [
 "l6 | dx:type-2-diabetes | ASSESS POS CERT PT CUR | when=2015 | type 2 diabetes mellitus (diagnosed 2015) | | t2dm; type-2-diabetes-mellitus; diabetes; diabetes-mellitus",
 "l6 | dx:hypertension | ASSESS POS CERT PT CUR | | hypertension | | ",
 "l6 | dx:hypercholesterolaemia | ASSESS POS CERT PT CUR | | hypercholesterolaemia | | high-cholesterol",
 "l8 | proc:diabetes-review | DONE POS CERT PT CUR | | annual diabetes review | soft | annual-review; diabetic-review; fu:diabetes-review",
 "l8 | sym:feels-well | RPT POS CERT PT CUR | | He feels well | soft | well; general-wellbeing; feeling-well",
 "l8-9 | sym:hypoglycaemia | RPT NEG CERT PT CUR | | no episodes of hypoglycaemia | NEG | hypos; hypoglycaemic-episodes",
 "l9 | sym:neuropathy | RPT NEG CERT PT CUR | | no symptoms of neuropathy | NEG | peripheral-neuropathy; neuropathy-symptoms; neuropathic-symptoms",
 "l9 | sym:chest-pain | RPT NEG CERT PT CUR | | has not had any chest pain | NEG | ",
 "l9-10 | soc:alcohol | RPT POS CERT PT CUR | res=20 unit=units/week | drinks about 20 units of alcohol a week | SOC NUM | alcohol-intake; alcohol-consumption",
 "l10 | soc:smoking | RPT NEG CERT PT CUR | | does not smoke | NEG SOC | non-smoker; smoker",
 "l10-11 | func:exercise | RPT * CERT PT CUR | | walks to work but does no other exercise | | physical-activity; walking; exercise-level",
 "l13 | meas:weight | OBS POS CERT PT CUR | res=94 unit=kg | weight 94 kg | NUM UNITS | body-weight",
 "l13 | meas:weight | OBS POS CERT PT PAST | res=96 unit=kg when=1y | was 96 kg a year ago | HIST NUM | body-weight; previous-weight",
 "l13 | meas:bmi | OBS POS CERT PT CUR | res=30.4 | BMI 30.4 | ABBREV NUM | body-mass-index",
 "l13 | meas:blood-pressure | OBS POS CERT PT CUR | res=138/84 | BP 138/84 | ABBREV NUM | bp",
 "l13-14 | sym:foot-pulses | OBS POS CERT PT CUR | | pulses present both feet | | pedal-pulses; foot-pulses-present; peripheral-pulses",
 "l14 | sym:monofilament-sensation | OBS POS CERT PT CUR | | monofilament sensation intact | | foot-sensation; monofilament-test; sensation-intact",
 "l14 | sym:foot-ulceration | OBS NEG CERT PT CUR | | no ulceration | NEG | ulcer; foot-ulcer; ulceration",
 "l14-15 | proc:retinal-screening | PLAN POS CERT PT FUT | when=october | Retinal screening is booked for October | FU | diabetic-eye-screening; retinal-screen; eye-screening; fu:retinal-screening",
 "l18 | meas:hba1c | OBS POS CERT PT CUR | res=62 unit=mmol/mol | HbA1c 62 mmol/mol | TABLE ABBREV NUM | ",
 "l18 | meas:hba1c | OBS POS CERT PT PAST | res=58 | previous 58 | TABLE HIST NUM | previous-hba1c",
 "l19 | meas:egfr | OBS POS CERT PT CUR | res=54 unit=mL/min/1.73m2 | eGFR 54 mL/min/1.73m2 | TABLE ABBREV NUM UNITS | ",
 "l19 | meas:egfr | OBS POS CERT PT PAST | res=61 | previous 61 | TABLE HIST NUM | previous-egfr",
 "l20 | meas:urine-acr | OBS POS CERT PT CUR | res=4.1 unit=mg/mmol | Urine ACR 4.1 mg/mmol | TABLE ABBREV NUM UNITS | acr; albumin-creatinine-ratio; urine-albumin-creatinine-ratio",
 "l21 | meas:total-cholesterol | OBS POS CERT PT CUR | res=4.6 unit=mmol/L | Total cholesterol 4.6 mmol/L | TABLE NUM UNITS | cholesterol",
 "l21 | meas:ldl-cholesterol | OBS POS CERT PT CUR | res=2.8 unit=mmol/L | LDL 2.8 mmol/L | TABLE ABBREV NUM | ldl",
 "l22 | meas:alt | OBS POS CERT PT CUR | res=38 unit=U/L | ALT 38 U/L | TABLE ABBREV NUM UNITS | alanine-aminotransferase; alanine-transaminase",
 "l24 | dx:poor-glycaemic-control | ASSESS POS CERT PT CUR | | glycaemic control has drifted | | glycaemic-control; worsening-glycaemic-control; deteriorating-glycaemic-control; sym:glycaemic-control",
 "l24 | dx:declining-renal-function | ASSESS POS CERT PT CUR | | renal function has fallen over the year | | renal-function-decline; renal-function; falling-egfr; sym:renal-function; reduced-renal-function",
 "l24-25 | dx:diabetic-nephropathy | ASSESS POS POSS PT CUR | | early diabetic nephropathy is likely | HEDGE | nephropathy; early-diabetic-nephropathy",
 "l25-26 | dx:hypertensive-renal-contribution | ASSESS POS POSS PT CUR | | cannot exclude a contribution from his blood pressure | HEDGE | hypertensive-nephropathy; blood-pressure-contribution; hypertensive-renal-disease",
 "l26 | dx:ldl-above-target | ASSESS POS CERT PT CUR | | LDL remains above target | | ldl-cholesterol; raised-ldl; meas:ldl-cholesterol; ldl",
 "l29 | med:metformin | RX POS CERT PT CUR | dose=1g freq=BD chg=CONT | Continue metformin 1 g twice daily | | ",
 "l30 | med:empagliflozin | RX POS CERT PT CUR | dose=10mg freq=OD chg=START | Start empagliflozin 10 mg once daily | CHG | ",
 "l30 | dx:genital-infection | ADV POS HYPO PT FUT | | explained the risk of genital infection | HYPO kindany | genital-infection-risk; genital-mycotic-infection; genital-thrush",
 "l30 | soc:sick-day-rules | ADV POS CERT PT CUR | | the sick day rules | kindany | sick-day-rules-advice; sick-day-guidance",
 "l31 | med:atorvastatin | RX POS CERT PT CUR | dose=40mg freq=NOCTE chg=INC | Increase atorvastatin from 20 mg to 40 mg at night | CHG | ",
 "l32 | med:ramipril | RX POS CERT PT CUR | dose=10mg freq=OD chg=CONT | Continue ramipril 10 mg once daily | | ",
 "l33 | proc:urea-and-electrolytes | ORD POS CERT PT FUT | when=3m | Repeat U&E and ACR in 3 months | ABBREV FU | u-and-e; u&e; renal-function; repeat-u&e; ue; renal-function-test",
 "l33 | proc:urine-acr | ORD POS CERT PT FUT | when=3m | Repeat U&E and ACR in 3 months | ABBREV FU | acr; albumin-creatinine-ratio; repeat-acr; meas:urine-acr",
 "l34 | soc:alcohol-reduction | ADV POS CERT PT CUR | res=14 unit=units/week | advised him to reduce his alcohol to within 14 units a week | | alcohol; reduce-alcohol; alcohol-advice",
 "l35 | ref:diabetes-dietitian | ORD POS CERT PT FUT | | Referral to the diabetes dietitian | | dietitian; dietitian-referral; dietetics",
 "l36 | ref:renal-clinic | PLAN POS COND PT FUT | | If eGFR falls below 45 at the next check, I will refer to the renal clinic | COND | nephrology; renal; renal-referral",
 "l38 | fu:diabetes-review | PLAN POS CERT PT FUT | when=3m | Review in 3 months with results | FU | review; follow-up",
]
TOLERATED[3] = ["fu:dietitian-agreed", "soc:dietitian-agreed", "sym:diabetes-review"]

G[4] = [
 "l7 | dx:helicobacter-pylori-dyspepsia | ASSESS POS CERT PT CUR | | Helicobacter pylori associated dyspepsia | | h-pylori-dyspepsia; dyspepsia; h-pylori; helicobacter-pylori; h-pylori-associated-dyspepsia",
 "l11 | sym:epigastric-discomfort | RPT POS CERT PT CUR | when=4m | four months of epigastric discomfort after meals | DUR | epigastric-pain; postprandial-epigastric-discomfort; epigastric-discomfort-after-meals",
 "l11-12 | sym:bloating | RPT POS CERT PT CUR | | bloating | | abdominal-bloating",
 "l12 | sym:dysphagia | RPT NEG CERT PT CUR | | no dysphagia | NEG | swallowing-difficulty",
 "l12 | sym:weight-loss | RPT NEG CERT PT CUR | | no weight loss | NEG | ",
 "l12 | sym:melaena | RPT NEG CERT PT CUR | | no melaena | NEG | melena",
 "l12 | sym:vomiting | RPT NEG CERT PT CUR | | she has not vomited | NEG | ",
 "l13 | med:ibuprofen | RPT POS CERT PT CUR | | taking ibuprofen over the counter two or three times a week for headaches | ATTR | nsaid; over-the-counter-ibuprofen",
 "l13 | sym:headache | RPT POS CERT PT CUR | | for headaches | | headaches",
 "l14 | soc:alcohol | RPT POS CERT PT CUR | res=8 unit=units/week | drinks about 8 units of alcohol a week | SOC NUM | alcohol-intake; alcohol-consumption",
 "l14 | soc:smoking | RPT NEG CERT PT CUR | | does not smoke | NEG SOC | non-smoker; smoker",
 "l14-15 | dx:gastric-cancer | RPT NEG CERT FAM PAST | | no family history of gastric cancer | FAM NEG | stomach-cancer; family-history-gastric-cancer",
 "l17 | sym:abdomen-soft | OBS POS CERT PT CUR | | abdomen soft | | soft-abdomen; abdomen",
 "l17 | sym:epigastric-tenderness | OBS POS CERT PT CUR | | mild epigastric tenderness | | tenderness",
 "l17 | sym:abdominal-mass | OBS NEG CERT PT CUR | | no masses | NEG | masses; mass",
 "l19 | dx:helicobacter-pylori-infection | OBS POS CERT PT CUR | | stool antigen test you arranged is positive for H. pylori | ABBREV | h-pylori; h-pylori-positive; stool-antigen-positive; proc:stool-antigen-test; meas:stool-antigen-test; helicobacter-pylori",
 "l19 | meas:haemoglobin | OBS POS CERT PT CUR | res=131 unit=g/L | haemoglobin is 131 g/L | NUM UNITS | hb",
 "l20 | meas:ferritin | OBS POS CERT PT CUR | res=44 | ferritin 44 | NUM | ",
 "l22 | med:omeprazole | RX POS CERT PT CUR | dose=20mg freq=OD chg=START | omeprazole 20 mg once daily | CORR | ",
 "l23 | med:amoxicillin | RX POS CERT PT CUR | dose=1g freq=BD chg=START | amoxicillin 1 g twice daily | | ",
 "l23 | med:clarithromycin | RX POS CERT PT CUR | dose=500mg freq=BD chg=START | clarithromycin 500 mg twice daily | | ",
 "l23-24 | med:ibuprofen | ADV POS CERT PT CUR | chg=STOP | advised her to stop the ibuprofen | CHG | nsaid",
 "l24 | med:paracetamol | ADV POS CERT PT CUR | chg=START | use paracetamol for her headaches instead | | ",
 "l24-25 | proc:endoscopy | ORD NEG CERT PT CUR | | I have not arranged an endoscopy | NEG | gastroscopy; ogd; upper-gi-endoscopy",
 "l27-28 | proc:stool-antigen-test | ORD POS CERT PT FUT | when=4w | arrange a repeat stool antigen test no sooner than four weeks after she finishes the course | FU | repeat-stool-antigen; h-pylori-stool-test; stool-antigen; h-pylori-test",
 "l28-29 | ref:gastroenterology | ORD POS COND PT FUT | | If it remains positive, please refer her back | COND | refer-back; gastro; gastroenterology-referral",
 "l29 | med:second-line-eradication-therapy | PLAN POS COND PT FUT | | we will use second-line therapy | COND | second-line-therapy; second-line-eradication; proc:second-line-therapy",
 "l31 | fu:gastroenterology-clinic | PLAN NEG CERT PT FUT | | I have not arranged routine follow-up in clinic | NEG | follow-up; clinic-follow-up; routine-follow-up",
 "l36-37 | med:omeprazole | RX POS CERT PT CUR | dose=20mg freq=BD chg=START | 20 mg twice daily for the seven days, not once daily | CORR | ",
]
TOLERATED[4] = ["proc:eradication-therapy", "med:eradication-therapy", "med:h-pylori-eradication-therapy", "proc:h-pylori-eradication", "fu:pharmacy-informed", "fu:patient-telephoned", "soc:pharmacy-informed", "proc:stool-antigen-test", "sym:alarm-features", "sym:examination-unremarkable"]

G[5] = [
 "l9 | dx:community-acquired-pneumonia | ASSESS POS CERT PT CUR | site=right-lower-lobe | community-acquired pneumonia, right lower lobe | | pneumonia; cap; right-lower-lobe-pneumonia",
 "l9 | meas:curb-65 | OBS POS CERT PT CUR | res=2 | CURB-65 score 2 | ABBREV NUM | curb65; curb-65-score; curb",
 "l10 | dx:hypertension | ASSESS POS CERT PT CUR | | hypertension (long-standing) | | ",
 "l10 | dx:hyponatraemia | ASSESS POS CERT PT PAST | | mild hyponatraemia on admission, resolved | HIST | low-sodium; hyponatremia",
 "l11 | alg:drug-allergy | RPT NEG CERT PT CUR | | no known drug allergies | ALG NEG INJ | nkda; drug-allergies; allergies; known-drug-allergies; drug-allergies-none",
 "l13 | sym:fever | RPT POS CERT PT PAST | when=3d | three days of fever | DUR | pyrexia",
 "l13 | sym:productive-cough | RPT POS CERT PT PAST | | productive cough | | cough",
 "l13 | sym:pleuritic-chest-pain | RPT POS CERT PT PAST | site=right | right-sided pleuritic chest pain | | chest-pain; pleuritic-pain",
 "l14 | meas:temperature | OBS POS CERT PT PAST | res=38.6 | temperature 38.6 | NUM | temp",
 "l14 | meas:respiratory-rate | OBS POS CERT PT PAST | res=26 | respiratory rate 26 | NUM | rr",
 "l14 | meas:oxygen-saturation | OBS POS CERT PT PAST | res=91 unit=% | saturations 91% on air | NUM UNITS | sats; spo2; saturations",
 "l14 | meas:blood-pressure | OBS POS CERT PT PAST | res=118/70 | BP 118/70 | ABBREV NUM | bp",
 "l14-15 | meas:heart-rate | OBS POS CERT PT PAST | res=104 | heart rate 104 | NUM | pulse",
 "l15 | sym:confusion | OBS NEG CERT PT PAST | | He was not confused | NEG | confused",
 "l17 | proc:chest-xray | DONE POS CERT PT PAST | when=20260903 | chest X-ray on 3 September | ABBREV | cxr; chest-x-ray; chest-radiograph",
 "l17 | sym:consolidation | OBS POS CERT PT PAST | site=right-lower-lobe | right lower lobe consolidation | | lung-consolidation; right-lower-lobe-consolidation",
 "l17-18 | sym:pleural-effusion | OBS NEG CERT PT PAST | | no effusion | NEG | effusion",
 "l18 | proc:blood-cultures | OBS NEG CERT PT PAST | | Blood cultures were negative | NEG | blood-culture; meas:blood-cultures",
 "l18-19 | proc:urinary-legionella-antigen | OBS NEG CERT PT PAST | | Urinary legionella and pneumococcal antigens were negative | NEG | legionella-antigen; legionella; urinary-legionella; meas:legionella-antigen",
 "l18-19 | proc:urinary-pneumococcal-antigen | OBS NEG CERT PT PAST | | Urinary legionella and pneumococcal antigens were negative | NEG | pneumococcal-antigen; pneumococcal; urinary-pneumococcal; meas:pneumococcal-antigen",
 "l23 | meas:crp | OBS POS CERT PT PAST | res=210 when=admission | CRP 210 45 | TABLE NUM | c-reactive-protein",
 "l23 | meas:crp | OBS POS CERT PT CUR | res=45 when=discharge | CRP 210 45 | TABLE NUM | c-reactive-protein",
 "l24 | meas:white-cell-count | OBS POS CERT PT PAST | res=16.2 when=admission | WCC 16.2 9.8 | TABLE ABBREV NUM | wcc; wbc; white-cells",
 "l24 | meas:white-cell-count | OBS POS CERT PT CUR | res=9.8 when=discharge | WCC 16.2 9.8 | TABLE ABBREV NUM | wcc; wbc; white-cells",
 "l25 | meas:haemoglobin | OBS POS CERT PT PAST | res=132 when=admission | Hb 132 129 | TABLE ABBREV NUM | hb",
 "l25 | meas:haemoglobin | OBS POS CERT PT CUR | res=129 when=discharge | Hb 132 129 | TABLE ABBREV NUM | hb",
 "l26 | meas:sodium | OBS POS CERT PT PAST | res=131 when=admission | Sodium 131 136 | TABLE NUM | na",
 "l26 | meas:sodium | OBS POS CERT PT CUR | res=136 when=discharge | Sodium 131 136 | TABLE NUM | na",
 "l27 | meas:creatinine | OBS POS CERT PT PAST | res=88 when=admission | Creatinine 88 82 | TABLE NUM | ",
 "l27 | meas:creatinine | OBS POS CERT PT CUR | res=82 when=discharge | Creatinine 88 82 | TABLE NUM | ",
 "l29 | med:co-amoxiclav | RX POS CERT PT PAST | dose=1.2g route=IV freq=TDS when=48h | intravenous co-amoxiclav 1.2 g three times daily for 48 hours | HIST | coamoxiclav; amoxicillin-clavulanate; co-amoxiclav-iv",
 "l29-31 | med:co-amoxiclav | RX POS CERT PT CUR | dose=625mg route=PO freq=TDS chg=START | oral co-amoxiclav 625 mg three times daily to complete seven days in total, finishing on 10 September | CHG alt=l38 | coamoxiclav; amoxicillin-clavulanate; co-amoxiclav-oral",
 "l31 | med:oxygen | RX POS CERT PT PAST | | Oxygen 2 litres via nasal cannulae, weaned off by day 3 | HIST | oxygen-therapy; supplemental-oxygen; proc:oxygen; proc:oxygen-therapy",
 "l31-32 | sym:fever | OBS NEG CERT PT CUR | | He remained apyrexial from day 2 | NEG | apyrexial; pyrexia; temperature-normal",
 "l39 | med:amlodipine | RX POS CERT PT CUR | dose=5mg route=PO freq=OD chg=CONT | amlodipine 5 mg orally once daily (unchanged) | INJ | ",
 "l41 | soc:lives-with-wife | RPT POS CERT PT CUR | | lives with his wife | | living-situation; lives-with-spouse; lives-with-partner; household",
 "l41 | func:activities-of-daily-living | RPT POS CERT PT CUR | | independent with all activities of daily living | | adls; independent; functional-independence; independence; adl",
 "l41-42 | soc:smoking | RPT POS CERT PT PAST | when=2015 | Ex-smoker, stopped in 2015 | SOC HIST | ex-smoker; former-smoker; smoking-history; smoker",
 "l44 | proc:chest-xray | ORD POS CERT PT FUT | when=6w | repeat the chest X-ray in six weeks | FU ABBREV | cxr; chest-x-ray; repeat-chest-xray",
 "l44-45 | fu:hospital-follow-up | PLAN NEG CERT PT FUT | | No hospital follow-up arranged | NEG | follow-up; hospital-follow-up-arranged",
 "l45 | fu:safety-net | ADV POS COND PT FUT | | advised to seek help if the fever or breathlessness returns | COND kindany | safety-netting; seek-help; safety-net-advice; seek-medical-help",
]
TOLERATED[5] = ["proc:nasal-cannulae", "sym:breathlessness", "sym:fever", "fu:discharge", "proc:admission", "meas:postoperative-day"]

G[6] = [
 "l9 | dx:neck-of-femur-fracture | ASSESS POS CERT PT CUR | site=left | left intracapsular neck of femur fracture | | hip-fracture; nof-fracture; femoral-neck-fracture; intracapsular-neck-of-femur-fracture; intracapsular-fracture",
 "l9 | dx:mechanical-fall | RPT POS CERT PT PAST | | following a mechanical fall at home | HIST alt=l14 | fall; fall-at-home; trip",
 "l10 | proc:hip-hemiarthroplasty | DONE POS CERT PT PAST | site=left when=20260912 | left hip hemiarthroplasty on 12 September 2026 | | hemiarthroplasty",
 "l10 | proc:spinal-anaesthetic | DONE POS CERT PT PAST | | under spinal anaesthetic | | spinal-anaesthesia; spinal",
 "l11 | dx:postoperative-delirium | ASSESS POS CERT PT PAST | | postoperative delirium on day 2, resolved by day 4 | HIST | delirium",
 "l11-12 | dx:urinary-tract-infection | ASSESS POS POSS PT PAST | | possible urinary tract infection, treated empirically | HEDGE | uti",
 "l14-15 | sym:loss-of-consciousness | RPT NEG CERT PT PAST | | She denies loss of consciousness | NEG | loc",
 "l15 | sym:head-injury | RPT NEG CERT PT PAST | | there was no head injury | NEG | dx:head-injury",
 "l15-16 | dx:falls | RPT POS CERT PT PAST | res=2 who=REL | Her daughter reports two previous falls this year | ATTR HIST NUM | previous-falls; falls; recurrent-falls; sym:falls",
 "l16 | soc:lives-alone | RPT POS CERT PT CUR | | She lives alone in a bungalow | | living-situation; lives-alone-bungalow; household",
 "l16 | func:independent | RPT POS CERT PT PAST | | was independent before this admission | | functional-independence; independence; premorbid-function",
 "l18 | alg:penicillin | RPT POS CERT PT CUR | | penicillin (rash) | ALG | penicillin-allergy",
 "l20 | func:mobilisation | DONE POS CERT PT PAST | | mobilised with the physiotherapists from day 1 | | mobilising; physiotherapy; proc:physiotherapy; proc:mobilisation",
 "l20-21 | func:walking-with-frame | OBS POS CERT PT CUR | | is now walking with a frame | | mobility; walking; zimmer-frame; frame",
 "l21 | meas:haemoglobin | OBS POS CERT PT PAST | res=98 unit=g/L | Postoperative haemoglobin was 98 g/L | NUM UNITS | hb; postoperative-haemoglobin",
 "l21-22 | proc:red-cell-transfusion | DONE POS CERT PT PAST | when=20260913 | received one unit of red cells on 13 September | | blood-transfusion; transfusion; red-cells; med:red-cells",
 "l22 | proc:urine-dipstick | OBS POS CERT PT PAST | | urine dipstick on day 2 was positive for leucocytes and nitrites | | urinalysis; dipstick-positive; urine-dip; meas:urine-dipstick; sym:leucocytes-nitrites",
 "l23 | med:nitrofurantoin | RX POS CERT PT PAST | dose=100mg freq=BD when=3d | nitrofurantoin 100 mg twice daily for three days | HIST | ",
 "l23-24 | proc:urine-culture | OBS NEG CERT PT PAST | | the urine culture later grew no organisms | NEG | urine-culture-negative; msu; meas:urine-culture",
 "l24 | med:codeine | RX POS CERT PT CUR | chg=STOP | Codeine was stopped because of constipation | CHG alt=l32 | ",
 "l24 | sym:constipation | * POS CERT PT PAST | | because of constipation | | ",
 "l24 | proc:bone-density-scan | DONE NEG CERT PT CUR | | Bone density was not measured | NEG | bone-density; dexa; dexa-scan; meas:bone-density",
 "l24-25 | dx:fragility-fracture | ASSESS POS CERT PT CUR | | on the basis of a fragility fracture | | osteoporotic-fracture",
 "l25 | med:bone-protection | RX POS CERT PT CUR | chg=START | started on bone protection | soft | osteoporosis-treatment; bone-protection-therapy",
 "l28 | med:paracetamol | RX POS CERT PT CUR | dose=1g route=PO freq=QDS chg=CONT | paracetamol 1 g orally four times daily (unchanged) | | ",
 "l29 | med:enoxaparin | RX POS CERT PT CUR | dose=40mg route=SC freq=OD chg=START when=28d | enoxaparin 40 mg subcutaneously once daily for 28 days from surgery (new) | | ",
 "l30 | med:alendronic-acid | RX POS CERT PT CUR | dose=70mg route=PO freq=WKLY chg=START | alendronic acid 70 mg orally once weekly (new) | | alendronate",
 "l31 | med:calcium-and-colecalciferol | RX POS CERT PT CUR | dose=1tablet freq=BD chg=START | calcium and colecalciferol one tablet twice daily (new) | | calcium-colecalciferol; calcium-vitamin-d; adcal-d3; calcium-and-vitamin-d; calcium",
 "l34 | soc:package-of-care | PLAN POS CERT PT FUT | freq=BD | package of care twice daily has been arranged | | care-package; care; social-care; fu:package-of-care",
 "l34-35 | soc:daughter-staying | PLAN POS CERT PT FUT | when=1w | Her daughter will stay with her for the first week | soft | family-support; daughter-support",
 "l37 | fu:fracture-clinic | PLAN POS CERT PT FUT | when=6w | fracture clinic in six weeks with an X-ray | FU | fracture-clinic-review; follow-up",
 "l37 | proc:xray | PLAN POS CERT PT FUT | when=6w | with an X-ray | soft | x-ray; hip-xray; radiograph",
 "l37 | ref:falls-clinic | ORD POS CERT PT FUT | | Referred to the falls clinic | | falls-service; falls",
 "l37-38 | ref:community-physiotherapy | ORD POS CERT PT FUT | | and to community physiotherapy | | physiotherapy; physio",
 "l38 | proc:renal-function-test | ORD POS CERT PT FUT | when=2w | check her renal function in two weeks | FU | u-and-e; renal-function; urea-and-electrolytes; ue",
]
TOLERATED[6] = ["dx:constipation", "sym:fall", "dx:fall", "fu:discharge", "proc:physiotherapy"]

G[7] = [
 "l9 | dx:heart-failure-reduced-ejection-fraction | ASSESS POS CERT PT CUR | | decompensated heart failure with reduced ejection fraction | | hfref; heart-failure; decompensated-heart-failure; heart-failure-with-reduced-ejection-fraction",
 "l10 | dx:ischaemic-heart-disease | ASSESS POS * PT CUR | | ischaemic heart disease (likely cause) | HEDGE | ihd; coronary-artery-disease",
 "l10 | dx:hypertension | ASSESS POS CERT PT CUR | | hypertension | | ",
 "l10 | dx:hyperkalaemia | ASSESS POS CERT PT PAST | | hyperkalaemia on admission | HIST | high-potassium; hyperkalemia",
 "l12 | sym:breathlessness | RPT POS CERT PT PAST | when=2w | two weeks of increasing breathlessness | DUR | dyspnoea; shortness-of-breath",
 "l12 | sym:orthopnoea | RPT POS CERT PT PAST | | orthopnoea | | orthopnea",
 "l12 | sym:ankle-swelling | RPT POS CERT PT PAST | | ankle swelling | | ankle-oedema; peripheral-oedema; oedema",
 "l12-13 | sym:chest-pain | OBS NEG CERT PT PAST | | no chest pain during the admission | NEG | ",
 "l15 | proc:echocardiogram | DONE POS CERT PT PAST | when=20260915 | echocardiogram on 15 September | | echo",
 "l15-16 | sym:dilated-left-ventricle | OBS POS CERT PT CUR | | dilated left ventricle | | lv-dilatation; left-ventricular-dilatation; dilated-lv",
 "l16 | meas:ejection-fraction | OBS POS CERT PT CUR | res=35 unit=% | ejection fraction of 35% | NUM UNITS | lvef; ef; left-ventricular-ejection-fraction",
 "l16 | sym:mitral-regurgitation | OBS POS CERT PT CUR | | moderate mitral regurgitation | | mr; dx:mitral-regurgitation",
 "l16 | meas:nt-probnp | OBS POS CERT PT CUR | res=4850 unit=ng/L | NT-proBNP 4,850 ng/L | NUM UNITS | bnp; ntprobnp; nt-pro-bnp",
 "l16-17 | meas:potassium | OBS POS CERT PT PAST | res=5.6 unit=mmol/L when=admission | Potassium 5.6 mmol/L on admission | NUM UNITS | k; serum-potassium",
 "l17 | meas:potassium | OBS POS CERT PT CUR | res=5.1 when=discharge | 5.1 at discharge | NUM | k; serum-potassium",
 "l17 | meas:creatinine | OBS POS CERT PT CUR | res=118 | Creatinine 118 | NUM | ",
 "l17 | sym:sinus-rhythm | OBS POS CERT PT CUR | | ECG: sinus rhythm | | ecg-sinus-rhythm",
 "l17-18 | sym:left-bundle-branch-block | OBS POS CERT PT CUR | | left bundle branch block | ABBREV | lbbb; dx:left-bundle-branch-block",
 "l21 | meas:weight | OBS POS CERT PT PAST | res=96.4 unit=kg when=admission | Admission 96.4 kg | TABLE NUM UNITS | admission-weight; body-weight",
 "l22 | meas:weight | OBS POS CERT PT CUR | res=91.2 unit=kg when=discharge | Discharge 91.2 kg | TABLE NUM UNITS | discharge-weight; body-weight",
 "l24 | med:furosemide | RX POS CERT PT PAST | dose=80mg route=IV freq=BD when=4d | intravenous furosemide 80 mg twice daily for four days | HIST | frusemide; iv-furosemide",
 "l24-25 | meas:diuresis | OBS POS CERT PT PAST | res=5 unit=kg | He was diuresed by five kilograms | soft | weight-loss; fluid-loss; sym:diuresis; proc:diuresis",
 "l28 | med:furosemide | RX POS CERT PT CUR | dose=80mg route=PO freq=OD chg=INC | furosemide increased to 80 mg orally once daily (was 40 mg before admission) | CHG | frusemide",
 "l29 | med:ramipril | RX POS CERT PT CUR | dose=5mg freq=OD chg=DEC | ramipril reduced from 10 mg to 5 mg once daily because of the potassium | CHG | ",
 "l30 | med:ibuprofen | RX POS CERT PT CUR | chg=STOP | ibuprofen stopped | CHG | ",
 "l30 | med:nsaids | ADV NEG CERT PT CUR | | told to avoid all anti-inflammatory drugs | | anti-inflammatory-drugs; anti-inflammatories; nsaid; anti-inflammatory",
 "l31 | med:spironolactone | RX POS CERT PT CUR | chg=HOLD | spironolactone withheld until the potassium is rechecked | CHG | ",
 "l31-32 | med:spironolactone | PLAN POS COND PT FUT | dose=25mg freq=OD chg=START | if potassium is 5.0 or below at that check, start spironolactone 25 mg once daily | COND | ",
 "l33 | med:bisoprolol | RX POS CERT PT CUR | dose=5mg freq=OD chg=CONT | bisoprolol 5 mg once daily continues unchanged | | ",
 "l34 | med:atorvastatin | RX POS CERT PT CUR | dose=40mg freq=NOCTE chg=CONT | atorvastatin 40 mg at night continues unchanged | | ",
 "l36 | proc:implantable-defibrillator | PLAN NEG CERT PT CUR | | He is not for an implantable defibrillator at present | NEG | icd; implantable-cardioverter-defibrillator; defibrillator",
 "l36-37 | med:sacubitril-valsartan | PLAN POS COND PT FUT | | Sacubitril/valsartan will be considered in clinic once his potassium and renal function allow | COND | entresto; sacubitril/valsartan; sacubitril",
 "l39 | fu:daily-weights | ADV POS CERT PT CUR | | weigh himself every morning | kindany | weight-monitoring; self-weighing; daily-weight; daily-weighing; weigh",
 "l39-40 | fu:contact-heart-failure-nurse | ADV POS COND PT FUT | | contact the heart failure nurse if his weight rises by more than 2 kg in three days | COND kindany | heart-failure-nurse; safety-net; weight-gain; contact-nurse",
 "l40 | soc:alcohol | RPT NEG CERT PT CUR | | He does not drink alcohol | NEG SOC | alcohol-intake; alcohol-consumption",
 "l42 | proc:urea-and-electrolytes | ORD POS CERT PT FUT | when=1w | repeat U&E in one week (GP please) | FU ABBREV | u-and-e; renal-function; u&e; ue; renal-function-test",
 "l42 | ref:heart-failure-nurse | ORD POS CERT PT FUT | | Heart failure nurse referral made | | heart-failure-nurse-referral; heart-failure-nursing",
 "l42-43 | fu:cardiology-clinic | PLAN POS CERT PT FUT | when=6w | Cardiology clinic in six weeks | FU | follow-up; review; cardiology-review",
]
TOLERATED[7] = ["dx:atrial-fibrillation", "sym:weight-gain", "meas:weight-gain", "fu:heart-failure-nurse"]

G[8] = [
 "l7 | dx:transient-ischaemic-attack | ASSESS POS CERT PT CUR | site=left-carotid | transient ischaemic attack, left carotid territory | | tia; left-carotid-tia",
 "l11-12 | sym:arm-weakness | RPT POS CERT PT PAST | site=left-arm when=20260921 | weakness of the left arm lasting about twenty minutes on the evening of 21 September 2026, which resolved completely | DUR | left-arm-weakness; weakness; limb-weakness",
 "l13 | sym:speech-disturbance | RPT NEG CERT PT PAST | | no speech disturbance | NEG | dysphasia; dysarthria; speech",
 "l13 | sym:facial-droop | RPT NEG CERT PT PAST | | no facial droop | NEG | facial-weakness",
 "l13 | sym:headache | RPT NEG CERT PT PAST | | no headache | NEG | ",
 "l13-14 | sym:previous-similar-episodes | RPT NEG CERT PT PAST | | She has had no previous similar episodes | NEG HIST | similar-episodes; previous-episodes; previous-tia; dx:previous-tia",
 "l14 | sym:neurological-deficit | OBS NEG CERT PT CUR | | no residual neurological deficit | NEG | residual-deficit; focal-neurology; residual-neurological-deficit; focal-neurological-deficit",
 "l14 | meas:blood-pressure | OBS POS CERT PT CUR | res=162/94 | BP 162/94 | ABBREV NUM | bp",
 "l15 | meas:pulse | OBS POS CERT PT CUR | res=76 | pulse 76 regular | NUM | heart-rate; pulse-rate",
 "l15 | sym:carotid-bruit | OBS NEG CERT PT CUR | | no carotid bruits | NEG | carotid-bruits; bruit",
 "l17 | sym:acute-intracranial-change | OBS NEG CERT PT CUR | | CT head showed no acute change | NEG | ct-head-normal; acute-change; proc:ct-head; ct-head; acute-intracranial-abnormality",
 "l17-18 | sym:carotid-stenosis | OBS NEG CERT PT CUR | | no significant stenosis on either side | NEG | carotid-doppler-normal; stenosis; proc:carotid-doppler; carotid-doppler",
 "l18 | sym:sinus-rhythm | OBS POS CERT PT CUR | | 24-hour tape showed sinus rhythm throughout | alt=l19 | ecg-sinus-rhythm; proc:24-hour-tape; 24-hour-tape",
 "l18-19 | dx:atrial-fibrillation | OBS NEG CERT PT CUR | | no atrial fibrillation | NEG | af; sym:atrial-fibrillation",
 "l19 | meas:ldl-cholesterol | OBS POS CERT PT CUR | res=3.6 unit=mmol/L | LDL cholesterol 3.6 mmol/L | ABBREV NUM UNITS | ldl",
 "l19 | meas:hba1c | OBS POS CERT PT CUR | res=39 unit=mmol/mol | HbA1c 39 mmol/mol | ABBREV NUM UNITS | ",
 "l21 | soc:smoking | RPT NEG CERT PT * | | She has never smoked | NEG SOC | never-smoker; non-smoker; smoker",
 "l21 | soc:alcohol | RPT POS CERT PT CUR | res=14 unit=units/week | drinks about 14 units of alcohol a week | SOC NUM | alcohol-intake; alcohol-consumption",
 "l21-22 | dx:stroke | RPT POS CERT FAM PAST | | Her mother had a stroke at the age of 70 | FAM | family-history-stroke; cva",
 "l24 | med:aspirin | RX POS CERT PT CUR | dose=300mg freq=OD when=14d chg=START | aspirin 300 mg once daily for 14 days | CHG | ",
 "l24-25 | med:clopidogrel | * POS CERT PT FUT | dose=75mg freq=OD chg=START | then clopidogrel 75 mg once daily long term | | ",
 "l25 | med:atorvastatin | RX POS CERT PT CUR | dose=80mg freq=NOCTE chg=START | Atorvastatin 80 mg at night started | CHG | ",
 "l25-26 | med:amlodipine | RX POS CERT PT CUR | dose=5mg freq=OD chg=START | Amlodipine 5 mg once daily started for her blood pressure | CHG | ",
 "l26 | proc:blood-pressure-check | ORD POS CERT PT FUT | when=4w | please check it in four weeks and titrate | FU | bp-check; blood-pressure-review; blood-pressure; meas:blood-pressure; fu:blood-pressure-check; titration",
 "l28 | func:driving | ADV NEG CERT PT CUR | when=1m | she must not drive for one month from the event | NEG | driving-restriction; no-driving; driving-ban; soc:driving",
 "l28-29 | fu:dvla-notification | ADV NEG COND PT CUR | | does not need to inform the DVLA if she makes a full recovery | NEG COND kindany | dvla; inform-dvla; dvla-notification-not-required",
 "l29-30 | fu:call-999 | ADV POS COND PT FUT | | If she has any further symptoms she should call 999 | COND kindany | safety-net; emergency-advice; safety-netting; call-999-advice; further-symptoms",
 "l32 | fu:tia-clinic | PLAN POS CERT PT FUT | when=6w | I will see her again in the TIA clinic in six weeks | FU | review; follow-up; tia-clinic-review",
]
TOLERATED[8] = ["proc:ct-head", "proc:carotid-doppler", "proc:24-hour-tape", "proc:ecg", "proc:holter", "sym:full-recovery"]

G[9] = [
 "l5 | sym:sore-throat | RPT POS CERT PT CUR | when=3d | Sore throat 3/7 | ABBREV DUR | pharyngitis; throat-pain",
 "l5 | sym:odynophagia | RPT POS CERT PT CUR | | painful swallowing | | painful-swallowing; swallowing-pain",
 "l5 | sym:fever | RPT POS CERT PT CUR | | feels feverish | | feverish; pyrexia",
 "l5 | sym:cough | RPT NEG CERT PT CUR | | No cough | NEG | ",
 "l5 | sym:coryza | RPT NEG CERT PT CUR | | no coryza | NEG | runny-nose; coryzal-symptoms",
 "l5-6 | func:eating-and-drinking | RPT POS CERT PT CUR | | Eating and drinking OK | | oral-intake; eating; drinking; sym:oral-intake",
 "l6 | med:antibiotics | RPT NEG CERT PT CUR | | Not keen on antibiotics | soft | antibiotic-preference; patient-preference; soc:antibiotic-preference",
 "l7 | alg:penicillin | RPT NEG CERT PT CUR | | No penicillin allergy | ALG NEG | penicillin-allergy",
 "l9 | meas:temperature | OBS POS CERT PT CUR | res=37.9 | temp 37.9 | ABBREV NUM | temp",
 "l9 | sym:tonsillar-exudate | OBS POS CERT PT CUR | | Tonsils enlarged with exudate bilaterally | | enlarged-tonsils; tonsillar-enlargement; exudate; tonsils; tonsillar-exudate-bilateral",
 "l9-10 | sym:cervical-lymphadenopathy | OBS POS CERT PT CUR | | Tender anterior cervical lymphadenopathy | | lymphadenopathy; anterior-cervical-lymphadenopathy; tender-lymphadenopathy",
 "l10 | sym:chest-clear | OBS POS CERT PT CUR | | Chest clear | | clear-chest; chest; lungs-clear",
 "l10 | sym:stridor | OBS NEG CERT PT CUR | | No stridor | NEG | ",
 "l10 | sym:trismus | OBS NEG CERT PT CUR | | no trismus | NEG | ",
 "l11 | meas:feverpain-score | OBS POS CERT PT CUR | res=3 | FeverPAIN score 3 | NUM | feverpain; fever-pain-score; fever-pain",
 "l13 | dx:acute-tonsillitis | ASSESS POS CERT PT CUR | | acute tonsillitis | | tonsillitis",
 "l13 | dx:viral-tonsillitis | ASSESS POS POSS PT CUR | | likely viral | HEDGE | viral-infection; viral; viral-cause; viral-aetiology",
 "l13 | dx:bacterial-tonsillitis | ASSESS POS POSS PT CUR | | possible bacterial | HEDGE | bacterial-infection; bacterial; bacterial-cause; bacterial-aetiology",
 "l15-16 | med:phenoxymethylpenicillin | RX POS COND PT CUR | dose=500mg freq=QDS when=5d chg=START | delayed prescription phenoxymethylpenicillin 500 mg QDS for 5/7, to start only if not improving in 48 hours | COND ABBREV | penicillin-v; pen-v; penicillin",
 "l16 | med:paracetamol | * POS CERT PT CUR | | Regular paracetamol | | ",
 "l16 | soc:fluids | ADV POS CERT PT CUR | | Fluids | soft kindany | fluid-intake; oral-fluids",
 "l17-18 | fu:safety-net | ADV POS COND PT FUT | | return or call 111 if unable to swallow fluids, drooling, or breathing difficulty | COND kindany | safety-netting; call-111; safety-net-advice; return-advice",
]
TOLERATED[9] = ["fu:discussed-and-agreed", "soc:agreed", "sym:breathing-difficulty", "sym:drooling", "sym:unable-to-swallow"]

G[10] = [
 "l5 | proc:right-hemicolectomy | DONE POS CERT PT PAST | site=right when=20260915 | right hemicolectomy (15 September) | | hemicolectomy",
 "l5 | dx:caecal-adenocarcinoma | ASSESS POS CERT PT CUR | | caecal adenocarcinoma | | caecal-cancer; colon-cancer; bowel-cancer; adenocarcinoma; caecal-carcinoma",
 "l7 | sym:observations-stable | OBS POS CERT PT CUR | | Obs stable overnight | ABBREV | stable-observations; obs-stable; observations; meas:observations",
 "l7 | sym:fever | OBS NEG CERT PT CUR | | apyrexial | NEG ABBREV | pyrexia; apyrexial; temperature",
 "l7 | sym:pain-controlled | OBS * CERT PT CUR | | Pain controlled | | pain; pain-control; postoperative-pain",
 "l7 | sym:passing-flatus | RPT POS CERT PT CUR | | Passing flatus | | flatus; wind",
 "l7 | sym:bowels-opened | RPT NEG CERT PT CUR | | bowels not yet opened | NEG | bowel-movement; bowels-open; bowel-motion; bowels",
 "l8 | func:soft-diet | RPT POS CERT PT CUR | | Tolerating a soft diet | | oral-intake; diet; tolerating-diet; sym:oral-intake",
 "l8 | sym:nausea | RPT NEG CERT PT CUR | | Nausea settled | NEG | ",
 "l8 | sym:vomiting | RPT NEG CERT PT CUR | | no vomiting since yesterday | NEG | ",
 "l10 | sym:abdomen-soft | OBS POS CERT PT CUR | | abdomen soft | | soft-abdomen; abdomen",
 "l10 | sym:wound-tenderness | OBS POS CERT PT CUR | | mildly tender around the wound | | abdominal-tenderness; tenderness; peri-wound-tenderness",
 "l10 | sym:wound-clean | OBS POS CERT PT CUR | | wound clean and dry | | wound-healthy; wound; wound-clean-dry",
 "l10 | sym:wound-discharge | OBS NEG CERT PT CUR | | no discharge | NEG | discharge",
 "l11 | sym:chest-clear | OBS POS CERT PT CUR | | Chest clear | | clear-chest; chest; lungs-clear",
 "l11 | sym:calf-tenderness | OBS NEG CERT PT CUR | | Calves soft, non-tender | NEG | calves-soft; dvt-signs; calves; calf",
 "l13 | meas:haemoglobin | OBS POS CERT PT CUR | res=104 | Hb 104 | ABBREV NUM | hb",
 "l13 | meas:white-cell-count | OBS POS CERT PT CUR | res=11.2 | WCC 11.2 | ABBREV NUM | wcc; wbc; white-cells",
 "l13 | meas:crp | OBS POS CERT PT CUR | res=88 | CRP 88 | ABBREV NUM | c-reactive-protein",
 "l13 | meas:crp | OBS POS CERT PT PAST | res=140 when=yesterday | 140 yesterday | HIST NUM | c-reactive-protein; previous-crp",
 "l13 | meas:potassium | OBS POS CERT PT CUR | res=3.4 | K 3.4 | ABBREV NUM | k; serum-potassium",
 "l13 | meas:creatinine | OBS POS CERT PT CUR | res=76 | creatinine 76 | NUM | ",
 "l16 | proc:drain-removal | PLAN POS CERT PT FUT | when=today | Drain out today | | remove-drain; drain; drain-out",
 "l17 | proc:trial-without-catheter | PLAN POS CERT PT FUT | when=tomorrow | TWOC tomorrow morning | ABBREV | twoc; catheter-removal; trial-of-void",
 "l17 | proc:re-catheterise | PLAN POS COND PT FUT | | if he fails to void, re-catheterise | COND | recatheterisation; catheter; recatheterise; urinary-catheter",
 "l17 | ref:urology | PLAN POS COND PT FUT | | refer to urology | COND | urology-referral",
 "l18 | med:sando-k | RX POS CERT PT CUR | dose=2tablets freq=TDS when=2d chg=START | Sando-K two tablets three times daily for two days | | potassium-supplement; potassium-chloride; sandok; potassium",
 "l18 | meas:potassium | ORD POS CERT PT FUT | when=friday | recheck K on Friday | FU kindany | potassium-recheck; proc:potassium; k; potassium-check",
 "l19 | med:pca | RX POS CERT PT PAST | chg=STOP | PCA stopped yesterday | ABBREV CHG | patient-controlled-analgesia; pca-morphine",
 "l19 | med:paracetamol | RX POS CERT PT CUR | dose=1g freq=QDS route=PO chg=CONT | Continue paracetamol 1 g four times daily orally | | ",
 "l19 | med:morphine | RX POS CERT PT CUR | dose=5mg route=PO freq=PRN chg=CONT | oral morphine 5 mg as required | | oramorph; oral-morphine",
 "l20 | med:dalteparin | RX POS CERT PT CUR | dose=5000units route=SC freq=OD chg=CONT | Continue dalteparin 5000 units subcutaneously once daily | | ",
 "l20 | med:dalteparin | PLAN POS CERT PT FUT | when=28d | to continue for 28 days after discharge | soft | dalteparin-post-discharge",
 "l21 | proc:physiotherapy | PLAN POS CERT PT CUR | | Physio to continue mobilising | kindany | mobilisation; physio; func:mobilisation; mobilising",
 "l22 | proc:histology | * POS CERT PT FUT | | Histology awaited | | histopathology; histology-result; meas:histology",
 "l22 | fu:mdt-discussion | PLAN POS CERT PT FUT | | discuss at MDT when available | ABBREV | mdt; multidisciplinary-team-meeting; mdt-meeting",
 "l23 | fu:discharge | PLAN POS COND PT FUT | when=friday | Aim for discharge on Friday if bowels have opened and he is eating | COND | discharge-planning; discharge-friday",
]
TOLERATED[10] = ["meas:postoperative-day", "sym:postoperative-day", "sym:eating", "sym:bowels-opened"]

G[11] = [
 "l5 | dx:fall | RPT POS CERT PT PAST | | fall at home this evening with a head injury | | fall-at-home; sym:fall; mechanical-fall",
 "l5 | dx:head-injury | RPT POS CERT PT PAST | | with a head injury | alt=l20 | minor-head-injury; sym:head-injury",
 "l7-8 | sym:legs-gave-way | RPT POS CERT PT PAST | | her legs went from under her | soft | leg-weakness; legs-giving-way; legs-went-from-under-her",
 "l8 | sym:loss-of-consciousness | RPT NEG CERT PT PAST | | She denies loss of consciousness | NEG | loc",
 "l8 | sym:vomiting | RPT NEG CERT PT PAST | | denies loss of consciousness, vomiting or amnesia for the event | NEG | ",
 "l8 | sym:amnesia | RPT NEG CERT PT PAST | | denies loss of consciousness, vomiting or amnesia for the event | NEG | ",
 "l9 | sym:headache | RPT POS CERT PT CUR | site=injury-site | She has a headache at the site of the injury | | ",
 "l9 | sym:neck-pain | RPT NEG CERT PT CUR | | no neck pain | NEG | ",
 "l9-10 | sym:loss-of-consciousness | RPT NEG CERT PT PAST | who=REL | Her daughter, who was present, confirms she did not black out | ATTR NEG | loc; blackout; black-out",
 "l10 | med:warfarin | RPT POS CERT PT CUR | | She takes warfarin for atrial fibrillation | ATTR | ",
 "l10 | dx:atrial-fibrillation | RPT POS CERT PT CUR | | for atrial fibrillation | | af",
 "l10-11 | meas:inr | RPT POS CERT PT PAST | res=2.8 when=3w | her last INR was 2.8 three weeks ago | ATTR HIST NUM ABBREV | international-normalised-ratio; last-inr",
 "l11 | proc:tetanus-booster | RPT POS CERT PT PAST | when=10y | She had a tetanus booster within the last ten years | HIST | tetanus-vaccination; tetanus; tetanus-immunisation; med:tetanus-booster",
 "l13 | meas:gcs | OBS POS CERT PT CUR | res=15/15 | GCS 15/15 | ABBREV NUM | glasgow-coma-scale; glasgow-coma-score",
 "l13 | sym:laceration | OBS POS CERT PT CUR | site=left-forehead res=3 unit=cm | 3 cm laceration to the left forehead | NUM UNITS | forehead-laceration; scalp-laceration; dx:laceration",
 "l13 | sym:bony-tenderness | OBS NEG CERT PT CUR | | no underlying bony tenderness | NEG | bone-tenderness; skull-tenderness",
 "l14 | sym:pupils-equal-reactive | OBS POS CERT PT CUR | | Pupils equal and reactive | | perrl; pupils; pupils-equal; pupillary-reaction",
 "l14 | sym:focal-neurological-deficit | OBS NEG CERT PT CUR | | No focal neurological deficit | NEG | focal-neurology; neurological-deficit",
 "l14-15 | meas:blood-pressure | OBS POS CERT PT CUR | res=142/80 | Lying and standing BP 142/80 and 138/78 | ABBREV NUM | lying-bp; bp; lying-blood-pressure; blood-pressure-lying",
 "l14-15 | meas:standing-blood-pressure | OBS POS CERT PT CUR | res=138/78 | Lying and standing BP 142/80 and 138/78 | ABBREV NUM | standing-bp; blood-pressure; blood-pressure-standing; bp",
 "l15 | sym:postural-drop | OBS NEG CERT PT CUR | | no postural drop | NEG | postural-hypotension; orthostatic-hypotension",
 "l15 | meas:heart-rate | OBS POS CERT PT CUR | res=78 | Heart rate 78 | NUM | pulse",
 "l15 | sym:irregularly-irregular-pulse | OBS POS CERT PT CUR | | irregularly irregular | | irregular-pulse; irregular-rhythm; irregularly-irregular",
 "l17 | sym:intracranial-haemorrhage | OBS NEG CERT PT CUR | | CT head showed no acute intracranial haemorrhage | NEG | ct-head-normal; haemorrhage; intracranial-bleed; proc:ct-head; ct-head; acute-intracranial-haemorrhage",
 "l17 | sym:skull-fracture | OBS NEG CERT PT CUR | | no skull fracture | NEG | dx:skull-fracture; fracture",
 "l17-18 | meas:inr | OBS POS CERT PT CUR | res=3.4 | INR 3.4 | ABBREV NUM | international-normalised-ratio",
 "l18 | dx:atrial-fibrillation | OBS POS CERT PT CUR | | ECG atrial fibrillation, rate 78 | | af; sym:atrial-fibrillation",
 "l18 | meas:glucose | OBS POS CERT PT CUR | res=6.1 | Glucose 6.1 | NUM | blood-glucose; blood-sugar",
 "l20 | dx:mechanical-fall | ASSESS POS POSS PT PAST | | Query mechanical fall versus syncope | HEDGE | fall; mechanical",
 "l20 | dx:syncope | ASSESS POS POSS PT PAST | | Query mechanical fall versus syncope | HEDGE | collapse",
 "l21 | sym:arrhythmia | OBS NEG CERT PT CUR | | no arrhythmia beyond her known AF | NEG soft | dx:arrhythmia",
 "l23 | proc:wound-closure | DONE POS CERT PT CUR | | laceration cleaned and closed with tissue adhesive | | laceration-closure; tissue-adhesive; glue; wound-glue; laceration-repair; proc:laceration-closure",
 "l23-24 | proc:anticoagulation-reversal | DONE NEG CERT PT CUR | | No reversal of anticoagulation required | NEG | reversal; vitamin-k; warfarin-reversal; med:anticoagulation-reversal",
 "l24 | med:warfarin | RX POS CERT PT CUR | chg=CONT | Warfarin to continue | | ",
 "l26 | fu:discharge | DONE POS CERT PT CUR | | Discharged home with her daughter | soft | discharged; discharged-home",
 "l26-27 | fu:head-injury-advice | ADV POS CERT PT CUR | | Written head injury advice given | kindany | head-injury-advice; written-advice",
 "l27 | meas:inr | ORD POS CERT PT FUT | when=1w | GP please repeat INR within one week | FU kindany | proc:inr; inr-check; repeat-inr",
 "l27 | ref:falls-assessment | * POS CERT PT FUT | | consider a falls assessment | soft | falls-clinic; falls-assessment; falls; fu:falls-assessment",
]
TOLERATED[11] = ["sym:trip", "dx:trip", "soc:daughter-staying", "soc:lives-with-daughter", "sym:fall", "fu:daughter-staying"]

G[12] = [
 "l5 | med:salbutamol | RPT POS CERT PT CUR | res=4 unit=times/week route=INH | using his salbutamol inhaler about four times a week over the last month | ATTR NUM | salbutamol-inhaler; salbutamol-use; reliever-use",
 "l6 | sym:night-time-waking | RPT NEG CERT PT CUR | | no night-time waking with asthma | NEG | nocturnal-symptoms; night-waking; nocturnal-waking; night-symptoms",
 "l6 | soc:time-off-work | RPT NEG CERT PT CUR | | no time off work | NEG | work-absence; time-off; func:time-off-work",
 "l6-7 | med:oral-steroids | RPT NEG CERT PT PAST | when=1y | has not needed oral steroids in the past year | NEG HIST | oral-corticosteroids; prednisolone; steroids; oral-steroid-courses",
 "l7-8 | meas:peak-flow | RPT POS CERT PT CUR | res=380 unit=L/min | measured his peak flow this morning at 380 L/min | NUM UNITS ATTR | pefr; peak-expiratory-flow; pef",
 "l8 | meas:peak-flow-best | RPT POS CERT PT PAST | res=450 | his best recorded is 450 | HIST NUM | best-peak-flow; peak-flow; personal-best-peak-flow; pefr-best",
 "l8 | meas:asthma-control-test | OBS POS CERT PT CUR | res=17 | Asthma Control Test score 17 | NUM | act-score; act; asthma-control-test-score",
 "l10 | soc:smoking | RPT POS CERT PT CUR | res=5 unit=cigarettes/day | He smokes about five cigarettes a day | SOC NUM | smoker; current-smoker; cigarettes",
 "l10 | dx:asthma | RPT POS CERT FAM CUR | | His mother has asthma | FAM | family-history-asthma",
 "l10 | soc:cat-at-home | RPT POS CERT PT CUR | | He has a cat at home | | pet-cat; cat-exposure; pets; cat; pet",
 "l12 | med:beclometasone | * POS CERT PT CUR | dose=200micrograms route=INH freq=BD | beclometasone 200 micrograms twice daily | | beclomethasone; beclometasone-inhaler",
 "l12 | med:salbutamol | * POS CERT PT CUR | freq=PRN | salbutamol as required | soft | salbutamol-inhaler; reliever",
 "l12-13 | soc:medication-adherence | RPT NEG CERT PT CUR | | he often forgets the evening beclometasone dose | ATTR kindany | adherence; missed-doses; poor-adherence; forgets-doses; compliance; med:beclometasone-adherence",
 "l15 | proc:inhaler-technique-check | DONE POS CERT PT CUR | | Inhaler technique checked over video and is good | kindany | inhaler-technique; inhaler-technique-good; sym:inhaler-technique",
 "l18 | med:beclometasone | RX POS CERT PT CUR | chg=STOP | Stop beclometasone | CHG | beclomethasone",
 "l19 | med:fostair | RX POS CERT PT CUR | dose=* freq=BD chg=START | Start Fostair 100/6, two puffs twice daily, as maintenance | CHG | beclometasone-formoterol; fostair-100/6; beclometasone/formoterol",
 "l20 | med:salbutamol | RX POS CERT PT CUR | freq=PRN chg=CONT | Continue salbutamol as required | | salbutamol-inhaler; reliever",
 "l21 | soc:smoking-cessation | ADV POS CERT PT CUR | | Smoking cessation advice given | | smoking-cessation-advice; stop-smoking; smoking-advice; smoking",
 "l21 | soc:readiness-to-quit | RPT NEG CERT PT CUR | | he is not ready to stop at present | NEG soft | ready-to-stop; smoking-cessation; quit-readiness",
 "l22 | proc:influenza-vaccination | * NEG CERT PT CUR | | Flu vaccination offered; declined | NEG | flu-vaccine; flu-jab; flu-vaccination; med:influenza-vaccine; med:flu-vaccine; influenza-vaccine",
 "l23 | fu:asthma-review | PLAN POS CERT PT FUT | when=6w | Review in six weeks with a peak flow diary | FU | review; follow-up; asthma-review-6-weeks",
 "l23 | proc:peak-flow-diary | PLAN POS CERT PT FUT | | with a peak flow diary | soft | peak-flow-diary; meas:peak-flow-diary; fu:peak-flow-diary",
 "l24 | fu:contact-surgery | ADV POS COND PT FUT | | If his peak flow falls below 300 or he needs salbutamol more than eight puffs in a day, he is to contact the surgery the same day | COND kindany | safety-net; contact-surgery; safety-netting; safety-net-advice",
]
TOLERATED[12] = ["sym:asthma", "dx:asthma", "sym:football", "func:football", "soc:football", "meas:peak-flow-threshold"]


# ------------------------------------------------------------------ compiler

KEYS = ("act", "pol", "cert", "subj", "time")
LINE_RE = re.compile(r"^l(\d+)(?:-(\d+))?$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def join_lines(parts: list[str]) -> str:
    """Join consecutive document lines: a line ending in a hyphen continues its word on the next line."""
    out = ""
    for seg in parts:
        seg = seg.strip()
        if out and out.endswith("-"):
            out += seg
        elif out:
            out += " " + seg
        else:
            out = seg
    return norm(out)


def parse_lines(tok: str) -> list[int]:
    m = LINE_RE.match(tok)
    if not m:
        raise SystemExit(f"bad line ref {tok!r}")
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return list(range(a, b + 1))


def compile_doc(n: int, doc_text: list[str]) -> list[dict]:
    out = []
    for k, raw in enumerate(G[n], 1):
        parts = [p.strip() for p in re.split(r"\s*\|\s*", raw)]
        if len(parts) != 7:
            raise SystemExit(f"doc {n} entry {k}: expected 7 fields, got {len(parts)}: {raw!r}")
        lines_tok, item, attrs, extra, quote, tags, syn = parts
        lines = parse_lines(lines_tok)
        a = attrs.split()
        if len(a) != 5:
            raise SystemExit(f"doc {n} entry {k}: five attributes expected: {attrs!r}")
        slots = {}
        for kv in extra.split():
            key, val = kv.split("=", 1)
            slots[key] = val
        tagl = tags.split()
        opts = {"soft": "soft" in tagl, "kindany": "kindany" in tagl, "alt": []}
        for t in tagl:
            if t.startswith("alt="):
                opts["alt"].extend(parse_lines(t[4:]))
        tagl = [t for t in tagl if t not in ("soft", "kindany") and not t.startswith("alt=")]
        # the quote must be found in the cited lines
        text = join_lines([doc_text[i - 1] for i in lines])
        if norm(quote) not in text:
            raise SystemExit(f"doc {n} entry {k}: quote not in lines {lines_tok}: {quote!r}\n  lines: {text!r}")
        kind, concept = item.split(":", 1)
        syns = [s.strip() for s in syn.split(";") if s.strip()]
        out.append({"id": f"{n}.{k:02d}", "doc": n, "lines": lines, "alt_lines": opts["alt"], "item": item, "kind": kind, "concept": concept,
                    "syn": syns, "act": a[0], "pol": a[1], "cert": a[2], "subj": a[3], "time": a[4], "slots": slots,
                    "quote": quote, "tags": tagl, "soft": opts["soft"], "kindany": opts["kindany"]})
    return out


def main() -> None:
    gold = {}
    total = 0
    for n in sorted(G):
        doc_text = (DOCS / f"doc{n:02d}.md").read_text().splitlines()
        entries = compile_doc(n, doc_text)
        gold[str(n)] = {"assertions": entries, "tolerated": TOLERATED.get(n, []), "lines": len(doc_text)}
        total += len(entries)
        soft = sum(1 for e in entries if e["soft"])
        print(f"doc{n:02d}: {len(entries)} assertions ({soft} soft), {len(doc_text)} lines")
    (HERE / "gold.json").write_text(json.dumps(gold, indent=1))
    tags = {}
    for d in gold.values():
        for e in d["assertions"]:
            for t in e["tags"]:
                tags[t] = tags.get(t, 0) + 1
    print(f"total {total}; tags {dict(sorted(tags.items()))}")


if __name__ == "__main__":
    main()
