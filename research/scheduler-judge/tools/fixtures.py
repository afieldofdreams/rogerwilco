"""Study 10, the scheduler as judge: the company, the twenty approved payment jobs, the planted faults, the renderings.

Copied from study 6 (research/plan-readback/tools/common.py at commit 82938298e) and kept here, so that nothing
outside this folder can change what this study sees: the supplier master rows (BASE_ROWS, EXTRA_ROW), the approval
record of the payment (study 6's RECORDS["PAY"], job J01 here), the lookalike rows of its confusers (P-look and C-look,
variant 1), the handover renderings (ho_line and prose_message with full=True, which carry the payee account), the
money and date formats, and the slot normalisation. Study 6 holds one approved payment; its inbox, its decoys and the
month-end ground truth hold six more, which are J02 to J07 here. J08 to J20 are new invoices on the same master, in
the same style. Every job names its source.
"""
from __future__ import annotations

import random
import re
from datetime import date
from decimal import Decimal, InvalidOperation

CASE_TODAY = "2026-09-24"                    # every payment date is on or after this day, so no date has passed
CASE_TODAY_LONG = "Thursday 24 September 2026"

# ------------------------------------------------------------------------------------- the master (study 6, copied)

def _row(short, supplier, domain, phone, cur, sort_code, account, verified, status="ACTIVE", effective=None, routing=None):
    r = {"short": short, "supplier": supplier, "email_domain": domain, "contacts": {"billing": f"billing@{domain}"},
         "phone": phone, "currency": cur, "status": status, "effective": effective or verified, "verified": verified}
    if routing:
        r["routing"] = routing; r["account"] = account
    else:
        r["sort_code"] = sort_code; r["account"] = account
    return r

BASE_ROWS = [
    _row("northfield", "Northfield Print Ltd", "northfield-print.co.uk", "+44 20 7946 0810", "GBP", "20-45-67", "31776234", "2025-11-04"),
    _row("marlow", "Marlow Design Partners LLP", "marlowdesign.co.uk", "+44 20 7946 0223", "GBP", "40-12-88", "61102938", "2026-02-11"),
    _row("kestrel", "Kestrel Cloud Inc", "kestrelcloud.com", "+1 415 555 0142", "USD", None, "4839201", "2026-01-20", routing="021000021"),
    _row("evergreen", "Evergreen Office Supplies", "evergreen-office.co.uk", "+44 117 496 0330", "GBP", "30-98-71", "22019483", "2025-09-30"),
    _row("ashdown", "Ashdown Catering Ltd", "ashdowncatering.co.uk", "+44 1273 555 0188", "GBP", "11-22-33", "70214455", "2025-06-12"),
    _row("brightwater", "Brightwater Media Ltd", "brightwatermedia.co.uk", "+44 161 496 0921", "GBP", "23-45-61", "55120987", "2026-03-02"),
    _row("coleridge", "Coleridge Stationers Ltd", "coleridge-stationers.co.uk", "+44 1392 496 0450", "GBP", "60-16-13", "33981204", "2025-12-18"),
    _row("dunmore", "Dunmore IT Services Ltd", "dunmore-it.co.uk", "+44 131 496 0666", "GBP", "80-20-00", "48837219", "2026-01-09"),
]
EXTRA_ROW = _row("fenwick", "Fenwick Architectural Ltd", "fenwick-arch.co.uk", "+44 20 7946 0999", "GBP", "77-01-02", "19002847", "2026-04-22")
MASTER = {r["short"]: r for r in BASE_ROWS + [EXTRA_ROW]}

# The lookalike a supplier fault puts in place of the approved supplier: (legal name, short name). Marlow's and
# Evergreen's are study 6's confuser rows (P-look and C-look, variant 1); the others are new, in the same style. No
# name contains another, so a readback carries one or the other and never both by accident.
LOOKALIKE = {
    "marlow": ("Marlow Design Partners Limited", "marlowdesign"),
    "evergreen": ("Evergreen Office Services", "evergreen-services"),
    "northfield": ("Northfield Printing Ltd", "northfield-printing"),
    "ashdown": ("Ashdown Caterers Ltd", "ashdown-caterers"),
    "brightwater": ("Brightwater Media Group Ltd", "brightwater-group"),
    "coleridge": ("Coleridge Stationery Ltd", "coleridge-stationery"),
    "dunmore": ("Dunmore IT Solutions Ltd", "dunmore-it-solutions"),
    "kestrel": ("Kestrel Cloud LLC", "kestrelcloud"),
    "fenwick": ("Fenwick Architecture Ltd", "fenwick-architecture"),
}

# ------------------------------------------------------------------------------------- the twenty approved jobs

_JOBS = [
    # id    invoice        sup           amount     cur    kind     payment date  approval  source
    ("J01", "MD-2026-057", "marlow",     "5400.00", "GBP", "GROSS", "2026-10-02", "FD-0929", "study 6 record PAY, the approved payment"),
    ("J02", "MD-2026-041", "marlow",     "3200.00", "GBP", "GROSS", "2026-09-26", "FD-0917", "study 6 confuser P-decoy variant 2, an earlier Marlow payment"),
    ("J03", "MD-2026-033", "marlow",     "1875.00", "GBP", "GROSS", "2026-09-25", "FD-0912", "study 6 hardening step 1 decoy, an earlier Marlow payment"),
    ("J04", "ACL-2291",    "ashdown",    "640.00",  "GBP", "GROSS", "2026-09-25", "FD-0914", "study 6 inbox, the payer's done report payer-7; approval reference new"),
    ("J05", "INV-000491",  "northfield", "378.60",  "GBP", "GROSS", "2026-10-02", "FD-0930", "study 6 inbox (reconciler-21) and month-end ground truth; approval reference new"),
    ("J06", "INV-000479",  "northfield", "1220.40", "GBP", "GROSS", "2026-09-29", "FD-0920", "study 6 confuser S-decoy variant 1; kind and approval reference new"),
    ("J07", "7731",        "kestrel",    "960.00",  "USD", "NET",   "2026-10-07", "FD-0931", "study 6 inbox (scheduler-13) and month-end ground truth, the USD run of 7 Oct; approval reference new"),
    ("J08", "EO-55187",    "evergreen",  "412.80",  "GBP", "GROSS", "2026-10-01", "FD-0918", "new"),
    ("J09", "EO-55203",    "evergreen",  "1086.40", "GBP", "GROSS", "2026-10-02", "FD-0922", "new"),
    ("J10", "BWM-3318",    "brightwater", "2750.00", "GBP", "GROSS", "2026-10-02", "FD-0923", "new"),
    ("J11", "BWM-3342",    "brightwater", "980.00",  "GBP", "NET",   "2026-10-06", "FD-0924", "new"),
    ("J12", "CS-20417",    "coleridge",  "156.25",  "GBP", "GROSS", "2026-09-29", "FD-0915", "new"),
    ("J13", "CS-20456",    "coleridge",  "89.90",   "GBP", "GROSS", "2026-10-06", "FD-0927", "new"),
    ("J14", "DIT-7710",    "dunmore",    "1450.00", "GBP", "GROSS", "2026-10-02", "FD-0919", "new"),
    ("J15", "DIT-7724",    "dunmore",    "3600.00", "GBP", "NET",   "2026-10-09", "FD-0932", "new"),
    ("J16", "FA-2026-118", "fenwick",    "7250.00", "GBP", "GROSS", "2026-10-05", "FD-0933", "new"),
    ("J17", "FA-2026-131", "fenwick",    "4125.50", "GBP", "NET",   "2026-10-08", "FD-0934", "new"),
    ("J18", "ACL-2317",    "ashdown",    "812.40",  "GBP", "GROSS", "2026-10-02", "FD-0935", "new"),
    ("J19", "INV-000502",  "northfield", "2208.00", "GBP", "GROSS", "2026-10-06", "FD-0936", "new"),
    ("J20", "7768",        "kestrel",    "1240.00", "USD", "NET",   "2026-10-07", "FD-0937", "new"),
]


def _job(row: tuple) -> dict:
    jid, item, sup, amount, cur, kind, paid, appr, source = row
    m = MASTER[sup]
    j = {"id": jid, "item": item, "sup": sup, "supplier": m["supplier"], "amount": amount, "currency": cur, "kind": kind,
         "account": m["account"], "payment_date": paid, "reference": item, "approval": appr, "source": source}
    if m.get("routing"):
        j["routing"] = m["routing"]
    else:
        j["sort_code"] = m["sort_code"]
    return j

JOBS = [_job(r) for r in _JOBS]
JOB = {j["id"]: j for j in JOBS}

# ------------------------------------------------------------------------------------- the planted faults

FAULT_SLOTS = ["supplier", "invoice", "amount", "currency", "kind", "account", "date"]
ANSWER_SLOTS = ["supplier", "invoice", "amount", "currency", "kind", "account", "date", "reference", "approval"]
FIELDS_OF_SLOT = {"supplier": ["supplier", "sup"], "invoice": ["item", "reference"], "amount": ["amount"],
                  "currency": ["currency"], "kind": ["kind"], "account": ["account"], "date": ["payment_date"]}


def _weekday_on_or_after_today(y: int, m: int, d: int) -> bool:
    try:
        dt = date(y, m, d)
    except ValueError:
        return False
    return dt.weekday() < 5 and dt.isoformat() >= CASE_TODAY


def plant(job: dict, slot: str) -> dict:
    """The job with exactly one value changed. Deterministic: the choice is seeded by job id and slot.

    amount   one digit of the whole part changed, never the leading digit
    account  two adjacent digits of the account number transposed (the sort code or routing number is left alone)
    date     one digit of the day changed, to another weekday in the same month, on or after the case date
    invoice  two adjacent digits among the last three of the invoice number transposed; the reference is the
             invoice number, so it carries the same changed value
    kind     GROSS and NET swapped, the figure unchanged
    currency GBP becomes USD, USD becomes GBP
    supplier the approved supplier replaced by its lookalike, legal name and short name together
    """
    rng = random.Random(f"{job['id']}:{slot}")
    f = {k: v for k, v in job.items() if k != "source"}
    if slot == "amount":
        whole, frac = job["amount"].split(".")
        pos = rng.choice(range(1, len(whole)))
        new = rng.choice([d for d in "0123456789" if d != whole[pos]])
        f["amount"] = f"{whole[:pos]}{new}{whole[pos + 1:]}.{frac}"
    elif slot == "account":
        a = job["account"]
        i = rng.choice([i for i in range(len(a) - 1) if a[i] != a[i + 1]])
        f["account"] = a[:i] + a[i + 1] + a[i] + a[i + 2:]
    elif slot == "date":
        y, m, d = job["payment_date"].split("-")
        opts = sorted({d[:p] + c + d[p + 1:] for p in (0, 1) for c in "0123456789"
                       if d[:p] + c + d[p + 1:] != d and _weekday_on_or_after_today(int(y), int(m), int(d[:p] + c + d[p + 1:]))})
        f["payment_date"] = f"{y}-{m}-{rng.choice(opts)}"
    elif slot == "invoice":
        mo = re.search(r"(\d+)$", job["item"])
        digits, start = mo.group(1), mo.start(1)
        lo = max(0, len(digits) - 3)
        i = rng.choice([i for i in range(lo, len(digits) - 1) if digits[i] != digits[i + 1]])
        f["item"] = job["item"][:start] + digits[:i] + digits[i + 1] + digits[i] + digits[i + 2:]
        f["reference"] = f["item"]
    elif slot == "kind":
        f["kind"] = "NET" if job["kind"] == "GROSS" else "GROSS"
    elif slot == "currency":
        f["currency"] = "USD" if job["currency"] == "GBP" else "GBP"
    elif slot == "supplier":
        f["supplier"], f["sup"] = LOOKALIKE[job["sup"]]
    else:
        raise ValueError(slot)
    return f


def changed(job: dict, faulted: dict) -> dict:
    """The fields that differ between the job as sent and the job as received: {field: [sent, received]}."""
    return {k: [job[k], faulted[k]] for k in faulted if k in job and job[k] != faulted[k]}

# ------------------------------------------------------------------------------------- formats (study 6, copied)

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def ymd(iso: str) -> str:
    return iso.replace("-", "")

def long_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"

def money(amount: str) -> str:
    whole, frac = amount.split(".")
    return f"{int(whole):,}.{frac}"


def acct_token(f: dict) -> str:
    return f"{f['routing']}/{f['account']}" if f.get("routing") else f"{f['sort_code']}/{f['account']}"


def ho_line(f: dict) -> str:
    """Study 6's ho_line for PAY with full=True and rb=exec: the HO carries the payee account."""
    return (f"RW1 HO scheduler-1 p=pay from=scheduler to=payer item=inv:{f['item']} ask=PAY rb=exec sup={f['sup']} "
            f"amt={f['amount']} cur={f['currency']} kind={f['kind']} acct={acct_token(f)} paid={ymd(f['payment_date'])} "
            f"ref={f['reference']} apref={f['approval']} appr=OK")


def prose_message(f: dict) -> str:
    """Study 6's prose_message for PAY with full=True; a routing number where the payee has one instead of a sort code."""
    where = (f", to routing number {f['routing']} account {f['account']}" if f.get("routing")
             else f", to sort code {f['sort_code']} account {f['account']}")
    body = (f"Please release the payment for {f['supplier']} invoice {f['item']}: {money(f['amount'])} {f['currency']} "
            f"{f['kind'].lower()}{where}, payment date {long_date(f['payment_date'])}, reference {f['reference']}. "
            f"Approved by the FD under {f['approval']}.")
    return f"Hi payer,\n\n{body}\n\nThanks,\nscheduler"


def handover(f: dict, fmt: str) -> str:
    return ho_line(f) if fmt == "line" else prose_message(f)


def record_block(j: dict) -> str:
    """The approval record as the scheduler holds it: study 6's record fields, one per line, the same in both formats."""
    acct = (f"routing number {j['routing']}, account {j['account']}" if j.get("routing")
            else f"sort code {j['sort_code']}, account {j['account']}")
    return "\n".join([
        f"Approval record {j['approval']}, approved by the Finance Director",
        "act: pay",
        f"invoice: {j['item']}",
        f"supplier: {j['supplier']} (short name {j['sup']})",
        f"amount: {j['amount']}",
        f"currency: {j['currency']}",
        f"gross or net: {j['kind']}",
        f"payee account: {acct}",
        f"payment date: {j['payment_date']}",
        f"reference: {j['reference']}",
        f"approval: {j['approval']}",
    ])

# ------------------------------------------------------------------------------------- normalisation (study 6, copied)

def norm_money(v) -> str | None:
    try:
        return str(Decimal(str(v).replace(",", "").replace("£", "").replace("$", "").strip()).quantize(Decimal("0.00")))
    except (InvalidOperation, ValueError):
        return None

def norm_date(v) -> str | None:
    s = str(v).strip()
    m = re.fullmatch(r"(\d{4})-?(\d{2})-?(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

def norm_text(v) -> str:
    return re.sub(r"[^a-z0-9@./-]", "", str(v).lower())

def norm_digits(v) -> str:
    return re.sub(r"\D", "", str(v))

def norm_item(v) -> str:
    return norm_text(re.sub(r"^\s*(inv|sup|run|doc|email):", "", str(v), flags=re.I))

SLOT_NORM = {"amt": norm_money, "paid": norm_date, "acct": norm_digits, "item": norm_item, "sup": norm_text, "cur": norm_text,
             "kind": norm_text, "ref": norm_text, "apref": norm_text}


def line_slots(f: dict) -> dict:
    """The execution slots a faithful RB line carries for this job (as received), unnormalised."""
    return {"item": f"inv:{f['item']}", "sup": f["sup"], "amt": f["amount"], "cur": f["currency"], "kind": f["kind"],
            "acct": acct_token(f), "paid": ymd(f["payment_date"]), "ref": f["reference"], "apref": f["approval"]}

SLOT_OF_KEY = {"sup": "supplier", "item": "invoice", "ref": "invoice", "amt": "amount", "cur": "currency", "kind": "kind",
               "acct": "account", "paid": "date", "apref": "approval"}
