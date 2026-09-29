"""Brief corpus with planted faults. Each variant = (tail, artifact, hidden criteria).
Criteria types: code-checkable (graded by harness) and semantic (graded blind by a separate model).
The artifact is authoritative when tail and artifact disagree; criteria follow the artifact."""
import json, os

PAD = [
"Background. The site has been through two redesigns since 2023. The first was agency-led and produced copy that read well in a pitch and badly on the page. The second was written in-house in a hurry before a conference. Neither said what we do in a way a founder could repeat to a colleague.",
"Context on the company. Crox is a small consultancy. Most engagements are three to six months. We work with product and engineering leads directly rather than through procurement, which shapes the tone: peer to peer, not vendor to buyer.",
"Process. Copy goes to the founder for a single review pass. There is no committee. If it needs a second pass it has failed, so precision on the first draft is the point of this brief.",
"On evidence. Where the copy makes a claim about what we have done, the claim must be true and defensible without naming a client. Vague credibility signals are worse than none.",
"On the reader. They skim. They have four tabs open and a Slack thread going. The first sentence has to be about them, not about us, or the tab closes.",
]

def copy_brief(len_w=120, lang="UK", headline_q=False, buried=False, artifact_only=False):
    parts = ["# Brief: Landing page hero copy for crox.io", "",
      "Audience: founders and product leads at Series A to C companies who are trying to get AI features into production and keep hitting compliance and reliability walls.", ""]
    if buried: parts += [PAD[0], "", PAD[1], ""]
    parts += [f"What we need: the hero section copy for the new crox.io landing page. A headline and one supporting paragraph. The paragraph is {len_w} words, no more. {lang} English spelling throughout.", ""]
    if buried: parts += [PAD[2], ""]
    parts += ["Voice: first person plural (\"we\"), plain, no hype words (no \"revolutionary\", \"unlock\", \"supercharge\"). No em dashes anywhere; use full stops or commas.", ""]
    if buried: parts += [PAD[3], "", "One further exclusion that matters: do not mention any specific AI model vendor by name (no OpenAI, Anthropic, Google, Meta or Mistral), even favourably.", "", PAD[4], ""]
    parts += ["Must do: name the reader's specific Monday-morning problem in the first sentence (a stalled AI feature, a compliance review that keeps bouncing it, a demo that worked and a rollout that didn't). Must mention that Crox has shipped regulated-industry AI (health, financial services) without naming clients.", ""]
    if not buried:
        parts += ["Must not: no pricing, no claims about specific model vendors, no testimonials.", ""]
    else:
        parts += ["Must not: no pricing, no testimonials.", ""]
    if headline_q: parts += ["The headline must be phrased as a question.", ""]
    if artifact_only: parts += ["Deliver the paragraph in exactly two sentences. This is a hard constraint from the design system: the hero paragraph block is two lines on desktop.", ""]
    parts += ["Format: Markdown, headline as H1, paragraph below. Deliver as a single file.", "", "Deadline: 2 October 2026."]
    return "\n".join(parts)

COPY_BASE_CRIT = lambda len_w, lang: {
  "code": [
    {"id": "len", "check": "max_words_paragraph", "value": len_w, "desc": f"paragraph at most {len_w} words"},
    {"id": "no_emdash", "check": "no_substring", "value": ["—"], "desc": "no em dashes"},
    {"id": "fmt_h1", "check": "regex", "value": "(?m)^# .+", "desc": "H1 headline"},
    {"id": "no_pricing", "check": "no_regex", "value": r"[£$€]\s?\d|\bper (month|seat|user)\b|\bpricing\b", "desc": "no pricing"},
    {"id": "no_vendors", "check": "no_regex", "value": r"\b(OpenAI|Anthropic|Google|Meta|Mistral|GPT|Claude|Gemini|Llama)\b", "desc": "no vendor names"},
    {"id": "lang", "check": "spelling", "value": lang, "desc": f"{lang} spelling"},
  ],
  "semantic": [
    {"id": "monday", "desc": "The FIRST sentence of the paragraph names the reader's specific Monday-morning problem (a stalled AI feature, a compliance review bouncing it, a demo that worked and a rollout that didn't, or similar)."},
    {"id": "regulated", "desc": "Mentions that Crox has shipped AI in regulated industries (health and/or financial services) WITHOUT naming any client."},
    {"id": "voice_we", "desc": "Written in first person plural ('we'), not 'I' and not third person."},
    {"id": "no_hype", "desc": "No hype words such as revolutionary, unlock, supercharge, game-changing, cutting-edge."},
    {"id": "no_testimonial", "desc": "Contains no testimonial or quoted endorsement."},
  ],
  "acc": f"len:{len_w}w+lang:{lang.lower()}+tone:plain+voice:we+fmt:md+must:monday-problem+must:regulated-industry-ai+no:em-dash+no:pricing+no:vendor-names+no:testimonials+no:hype",
  "keys": "len+lang+tone+voice+fmt+must+no"
}

def copy_variants():
    v = {}
    # clean
    c = COPY_BASE_CRIT(120, "UK"); v["clean"] = {"tail": "hero copy per the brief: H1 plus a 120-word paragraph, UK English, we-voice, plain, no em dashes; open on the Monday problem; mention regulated-industry AI", "artifact": copy_brief(120, "UK"), "crit": c, "fault": "clean"}
    # artifact-only: two-sentence constraint only in artifact; tail silent
    c = COPY_BASE_CRIT(120, "UK"); c["code"].append({"id": "two_sentences", "check": "sentence_count_paragraph", "value": 2, "desc": "paragraph is exactly two sentences"}); c["acc"] += "+must:two-sentences"
    v["artifact_only"] = {"tail": "hero copy per the brief: H1 plus a 120-word paragraph, UK English, we-voice, plain, no em dashes; open on the Monday problem; mention regulated-industry AI", "artifact": copy_brief(120, "UK", artifact_only=True), "crit": c, "fault": "artifact_only"}
    # near-miss: tail says 120, artifact says 150 (artifact authoritative)
    c = COPY_BASE_CRIT(150, "UK"); c["code"].append({"id": "len_min", "check": "min_words_paragraph", "value": 130, "desc": "paragraph at least 130 words (brief asked for 150)"})
    v["near_miss"] = {"tail": "hero copy per the brief: H1 plus a 120-word paragraph, UK English, we-voice, plain, no em dashes; open on the Monday problem; mention regulated-industry AI", "artifact": copy_brief(150, "UK"), "crit": c, "fault": "near_miss"}
    # contradiction: tail says UK, artifact says US
    c = COPY_BASE_CRIT(120, "US")
    v["contradiction"] = {"tail": "hero copy per the brief: H1 plus a 120-word paragraph, UK English, we-voice, plain, no em dashes; open on the Monday problem; mention regulated-industry AI", "artifact": copy_brief(120, "US"), "crit": c, "fault": "contradiction"}
    # buried: vendor exclusion moved into padding mid-brief; tail omits it
    c = COPY_BASE_CRIT(120, "UK")
    v["buried"] = {"tail": "hero copy per the brief: H1 plus a 120-word paragraph, UK English, we-voice, plain, no em dashes; open on the Monday problem; mention regulated-industry AI", "artifact": copy_brief(120, "UK", buried=True), "crit": c, "fault": "buried"}
    # headline question (artifact-only, categorical)
    c = COPY_BASE_CRIT(120, "UK"); c["code"].append({"id": "headline_q", "check": "regex", "value": r"(?m)^# .*\?\s*$", "desc": "headline is a question"}); c["acc"] += "+must:headline-question"
    v["categorical"] = {"tail": "hero copy per the brief: H1 plus a 120-word paragraph, UK English, we-voice, plain, no em dashes; open on the Monday problem; mention regulated-industry AI", "artifact": copy_brief(120, "UK", headline_q=True), "crit": c, "fault": "categorical"}
    return v

# ---------------- extraction domain
EMAILS = """From: accounts@northfield-supplies.co.uk
Subject: Invoices for August
Hi, attached are our August invoices. INV-000482 dated 4 Aug 2026 for £1,240.00 net (VAT £248.00, gross £1,488.00), 30 days. INV-000491 dated 18 Aug 2026 for £310.50 net (VAT £62.10, gross £372.60). Please note INV-000488 dated 11 Aug 2026 for £2,000.00 net was raised in error and has been VOIDED; ignore it.

From: billing@kestrel-cloud.io
Subject: Your invoice 7731
Invoice 7731, issued 2026-08-09, total $960.00 USD (no VAT, reverse charge). Due 2026-09-08. Service: compute, August.

From: hello@marlow-design.studio
Subject: Re: final invoice
Final invoice MD-2026-057, date 27/08/2026, £4,500 plus VAT at 20% (£900), total £5,400. Payment terms 14 days. Also, a credit note CN-012 for £300 net against MD-2026-041 was issued on 27/08/2026.

From: accounts@northfield-supplies.co.uk
Subject: Correction
Apologies, INV-000491 should read £315.50 net (VAT £63.10, gross £378.60). Please use the corrected figures.

From: no-reply@evergreen-energy.co.uk
Subject: Statement
Your account statement for August shows a balance of £642.18. No new invoices were issued this month.
"""

def extract_brief(currency_rule="gbp_only", amount="net", months="August", buried=False, artifact_only=False, leading_zeros=True):
    parts = ["# Brief: Supplier invoice extraction, August 2026", "",
      "Task: extract every supplier invoice from the attached email thread into a JSON array. One object per invoice.", ""]
    if buried: parts += ["Context. This feeds the month-end close. Finance reconciles the array against the bank feed, so precision beats coverage: a wrong number costs more than a missing one, and a missing one will be caught by the statement check.", "", "History. The last two months were extracted by hand and both had transcription errors, which is why this is being automated. The downstream ledger import rejects JSON floats, so amount and vat must be strings with exactly two decimal places, for example \"1240.00\", not numbers.", "", "Timing. The array is needed before the 3rd working day of September. If any invoice is ambiguous, include it and add a note field rather than dropping it.", ""]
    if buried:
        parts += ["Fields per object: supplier (string), invoice_number (string, exactly as written), date (ISO 8601, YYYY-MM-DD), amount, currency (ISO 4217 code), vat, due_date (ISO 8601 or null).", ""]
    else:
        parts += ["Fields per object: supplier (string), invoice_number (string, exactly as written), date (ISO 8601, YYYY-MM-DD), amount (number), currency (ISO 4217 code), vat (number or null), due_date (ISO 8601 or null).", ""]
    parts += [f"Amounts: report the {amount} amount (excluding VAT) in the amount field." if amount == "net" else "Amounts: report the gross amount (including VAT) in the amount field.", ""]
    if currency_rule == "gbp_only":
        parts += ["Scope: GBP invoices only. Exclude any invoice in another currency.", ""]
    else:
        parts += ["Scope: all currencies. Record the currency code on each object; do not convert.", ""]
    if not buried and leading_zeros:
        parts += ["Invoice numbers must be kept exactly as written, including leading zeros and prefixes.", ""]
    parts += ["Exclude: voided or cancelled invoices, credit notes, and statements (a statement is not an invoice).", ""]
    if artifact_only: parts += ["Where a later email corrects an earlier invoice, use the corrected figures and add a field \"corrected\": true on that object.", ""]
    parts += ["Output: a single JSON array, no prose, no code fences."]
    return "\n".join(parts)

def EXTRACT_CRIT(currency_rule="gbp_only", amount="net", corrected_flag=False):
    exp = []
    if currency_rule == "gbp_only":
        exp = [
          {"invoice_number": "INV-000482", "amount": 1240.00, "currency": "GBP", "date": "2026-08-04"},
          {"invoice_number": "INV-000491", "amount": 315.50, "currency": "GBP", "date": "2026-08-18"},
          {"invoice_number": "MD-2026-057", "amount": 4500.00, "currency": "GBP", "date": "2026-08-27"},
        ]
    else:
        exp = [
          {"invoice_number": "INV-000482", "amount": 1240.00, "currency": "GBP", "date": "2026-08-04"},
          {"invoice_number": "INV-000491", "amount": 315.50, "currency": "GBP", "date": "2026-08-18"},
          {"invoice_number": "7731", "amount": 960.00, "currency": "USD", "date": "2026-08-09"},
          {"invoice_number": "MD-2026-057", "amount": 4500.00, "currency": "GBP", "date": "2026-08-27"},
        ]
    if amount == "gross":
        g = {"INV-000482": 1488.00, "INV-000491": 378.60, "MD-2026-057": 5400.00, "7731": 960.00}
        for e in exp: e["amount"] = g[e["invoice_number"]]
    crit = {"code": [
        {"id": "json", "check": "json_array", "value": None, "desc": "parses as a JSON array"},
        {"id": "set", "check": "invoice_set", "value": [e["invoice_number"] for e in exp], "desc": "exactly the expected invoice numbers, as written"},
        {"id": "amounts", "check": "amounts", "value": {e["invoice_number"]: e["amount"] for e in exp}, "desc": f"{amount} amounts correct, corrected figure used for INV-000491"},
        {"id": "dates", "check": "dates_iso", "value": {e["invoice_number"]: e["date"] for e in exp}, "desc": "dates ISO and correct"},
        {"id": "currency", "check": "currencies", "value": {e["invoice_number"]: e["currency"] for e in exp}, "desc": "currency codes correct"},
        {"id": "excluded", "check": "invoice_absent", "value": ["INV-000488", "CN-012"], "desc": "voided invoice and credit note absent"},
      ], "semantic": [],
      "acc": f"fmt:json+scope:{'gbp-only' if currency_rule=='gbp_only' else 'all-currencies'}+must:{amount}-amounts+must:iso-dates+must:exact-invoice-numbers+no:voided+no:credit-notes+no:statements",
      "keys": "fmt+scope+must+no"}
    if corrected_flag:
        crit["code"].append({"id": "corrected_flag", "check": "field_true", "value": {"INV-000491": "corrected"}, "desc": "corrected:true on the corrected invoice"})
        crit["acc"] += "+must:corrected-flag"
    return crit

def extract_variants():
    v = {}
    T = "extract August supplier invoices from the email thread into a JSON array: net amounts, GBP only, ISO dates, invoice numbers exactly as written, exclude voided invoices, credit notes and statements"
    v["clean"] = {"tail": T, "artifact": extract_brief(), "crit": EXTRACT_CRIT(), "fault": "clean"}
    v["artifact_only"] = {"tail": T, "artifact": extract_brief(artifact_only=True), "crit": EXTRACT_CRIT(corrected_flag=True), "fault": "artifact_only"}
    # near-miss: tail says net, artifact says gross
    v["near_miss"] = {"tail": T, "artifact": extract_brief(amount="gross"), "crit": EXTRACT_CRIT(amount="gross"), "fault": "near_miss"}
    # contradiction: tail says GBP only, artifact says all currencies
    v["contradiction"] = {"tail": T, "artifact": extract_brief(currency_rule="all"), "crit": EXTRACT_CRIT(currency_rule="all"), "fault": "contradiction"}
    # buried: leading-zeros rule only inside padding; tail omits "exactly as written"
    c = EXTRACT_CRIT(); c["code"].append({"id": "amount_strings", "check": "amounts_are_2dp_strings", "value": None, "desc": "amount and vat are strings with two decimals (rule stated mid-brief)"}); c["acc"] += "+must:amounts-as-2dp-strings"
    v["buried"] = {"tail": T, "artifact": extract_brief(buried=True), "crit": c, "fault": "buried"}
    # headline_q analogue: a categorical artifact-only rule -> use 'corrected' flag variant with tail silent AND gross amounts? keep simple: due_date required populated
    c = EXTRACT_CRIT(); c["code"].append({"id": "due_dates", "check": "due_dates", "value": {"INV-000482": "2026-09-03", "MD-2026-057": "2026-09-10"}, "desc": "due dates computed from terms (30 days, 14 days) where stated"}); c["acc"] += "+must:due-dates-from-terms"
    v["categorical"] = {"tail": T, "artifact": extract_brief() + "\n\nWhere payment terms are stated (e.g. 30 days, 14 days), compute due_date from the invoice date; otherwise null.", "crit": c, "fault": "categorical"}
    return v

corpus = {"copy": copy_variants(), "extract": extract_variants()}
for dom, vs in corpus.items():
    os.makedirs(dom, exist_ok=True)
    for name, v in vs.items():
        art = v["artifact"] if dom == "copy" else v["artifact"] + "\n\n---\n\n## Attached email thread\n\n" + EMAILS
        open(f"{dom}/{name}.artifact.md", "w").write(art)
        json.dump({"tail": v["tail"], "fault": v["fault"], "crit": v["crit"]}, open(f"{dom}/{name}.meta.json", "w"), indent=1)
print("built", {d: list(v) for d, v in corpus.items()})
