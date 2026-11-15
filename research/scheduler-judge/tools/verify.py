"""Study 10: is a payer's readback the stimulus it should be?

A clean readback must carry every value of the job as sent. A faulted readback must carry every value of the job as
the payer received it: the planted value in its slot, the approved value nowhere, every other value as approved. Both
are checked on values, tolerantly (5,400.00 and 5400.00, 2 October 2026 and 20261002, are the same), never on form: a
line with a value right and its form wrong stays in the pool, because what a model writes is what the scheduler, model
or code, has to read. A readback is also refused here if it questions or comments on a value, and a line if it carries
h= (a payer with no code cannot compute the digest). This module decides only which readbacks go to the judge.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

import fixtures as F

DOUBT = re.compile(r"\?|\b(unusual|discrepan\w*|mismatch\w*|inconsisten\w*|quer(y|ies)|verify|double[- ]check\w*|appears?|seems?|"
                   r"typo|mistake\w*|errors?|erroneous|incorrect\w*|however|not sure|unclear|suspicious|concern\w*|note that|"
                   r"please check|caution|warning)\b|\bnote:", re.I)

_MON = {m.lower()[:3]: i + 1 for i, m in enumerate(F.MONTHS)}
_MONRE = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"


def _iso(y, m, d) -> str | None:
    try:
        from datetime import date
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def dates_in(text: str) -> set[str]:
    t = text.lower()
    out = set()
    for d, mon, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MONRE + r",?\s+(\d{4})\b", t):
        out.add(_iso(y, _MON[mon[:3]], d))
    for mon, d, y in re.findall(r"\b" + _MONRE + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", t):
        out.add(_iso(y, _MON[mon[:3]], d))
    for d, mon in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MONRE + r"(?!,?\s+\d{4})", t):
        out.add(_iso(2026, _MON[mon[:3]], d))
    for y, m, d in re.findall(r"\b(20\d{2})-(\d{2})-(\d{2})\b", t):
        out.add(_iso(y, m, d))
    for y, m, d in re.findall(r"(?<!\d)(202[5-7])(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)", t):
        out.add(_iso(y, m, d))
    for d, m, y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t):
        out.add(_iso(y, m, d))
    out.discard(None)
    return out


def amounts_in(text: str) -> set[Decimal]:
    out = set()
    for m in re.finditer(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)\.(\d{2})(?![\d])", text):
        out.add(Decimal(m.group(1).replace(",", "") + "." + m.group(2)))
    for m in re.finditer(r"[£$]\s?(\d{1,3}(?:,\d{3})+|\d+)(?![\d.,])", text):
        out.add(Decimal(m.group(1).replace(",", "")))
    return out


CUR_RE = {"GBP": r"\bGBP\b|£|\bpounds?\b|\bsterling\b", "USD": r"\bUSD\b|US\$|\$|\bdollars?\b", "EUR": r"\bEUR\b|€|\beuros?\b"}


def currencies_in(text: str) -> set[str]:
    return {c for c, rx in CUR_RE.items() if re.search(rx, text, re.I)}


def kinds_in(text: str) -> set[str]:
    out = set()
    if re.search(r"\bgross\b", text, re.I):
        out.add("GROSS")
    if re.search(r"\bnet\b", text, re.I):
        out.add("NET")
    return out


def digit_runs(text: str) -> list[str]:
    return [re.sub(r"\D", "", m) for m in re.findall(r"\d+(?:[ \-]\d+)*", text)]


def _has(runs: list[str], digits: str) -> bool:
    return any(digits in r for r in runs)


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _squash(s: str) -> str:
    """Letters and digits only, lower case (amendment 4): Kestrel Cloud Inc and kestrelcloudinc are the same name."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def check_prose(text: str, got: dict, rec: dict, slot: str | None) -> list[str]:
    """Problems with a prose readback of `got` (the job as received); `rec` is the job as sent, `slot` the planted slot."""
    p = []
    t = text or ""
    tl = _norm_ws(t)
    if not t.strip():
        return ["empty"]
    ts = _squash(t)
    if _squash(got["supplier"]) not in ts:
        p.append(f"supplier {got['supplier']} missing")
    other = F.LOOKALIKE[rec["sup"]][0] if slot != "supplier" else rec["supplier"]
    if _squash(other) in ts:
        p.append(f"carries {other}")
    if got["item"].lower() not in tl:
        p.append(f"invoice {got['item']} missing")
    if slot == "invoice" and rec["item"].lower() in tl:
        p.append(f"carries the approved invoice {rec['item']}")
    amts = amounts_in(t)
    if Decimal(got["amount"]) not in amts:
        p.append(f"amount {got['amount']} missing")
    extra = amts - {Decimal(got["amount"])}
    if extra:
        p.append(f"other figures {sorted(str(a) for a in extra)}")
    curs = currencies_in(t)
    if got["currency"] not in curs:
        p.append(f"currency {got['currency']} missing")
    if curs - {got["currency"]}:
        p.append(f"other currency {sorted(curs - {got['currency']})}")
    kinds = kinds_in(t)
    if got["kind"] not in kinds:
        p.append(f"{got['kind'].lower()} missing")
    if kinds - {got["kind"]}:
        p.append(f"also says {sorted(kinds - {got['kind']})}")
    runs = digit_runs(t)
    bank = got.get("routing") or got.get("sort_code")
    if not _has(runs, F.norm_digits(bank)):
        p.append(f"sort code or routing {bank} missing")
    if not _has(runs, got["account"]):
        p.append(f"account {got['account']} missing")
    if slot == "account" and _has(runs, rec["account"]):
        p.append(f"carries the approved account {rec['account']}")
    ds = dates_in(t)
    if got["payment_date"] not in ds:
        p.append(f"date {got['payment_date']} missing")
    extra_d = ds - {got["payment_date"], F.CASE_TODAY}
    if extra_d:
        p.append(f"other dates {sorted(extra_d)}")
    if got["approval"].lower() not in tl:
        p.append(f"approval {got['approval']} missing")
    m = DOUBT.search(t)
    if m:
        p.append(f"comments or questions: {m.group(0)!r}")
    return p


TYPES = ("HO", "RB", "AQ", "AN", "ST", "DN", "UN", "FL", "CX")
NO_VERSION = re.compile(r"^(" + "|".join(TYPES) + r") \S+ ")


def extract_line(text: str) -> tuple[str | None, bool]:
    """The RB line in a reply: the first line that starts with RW1 once fences and quotes are stripped; failing that
    (amendment 1), the first line that starts with a message type and an id, as the model wrote it, without the version
    token. Returns (line, alone): alone is True when the reply was that line and nothing else."""
    if not text:
        return None, False
    lines = [l for l in text.strip().splitlines() if l.strip()]
    clean = [l.strip().strip("`").strip().strip('"').strip() for l in lines]
    for s in clean:
        if s.startswith("RW1 "):
            return s, (len(lines) == 1 and s == text.strip())
    m = re.search(r"RW1 [A-Z]{2}\b[^\n`]*", text)
    if m:
        return m.group(0).strip(), False
    for s in clean:
        if NO_VERSION.match(s):
            return s, (len(lines) == 1 and s == text.strip())
    return None, False


def tolerant_slots(line: str) -> tuple[str | None, dict, str]:
    """(type, key=value pairs, tail) read without the codec, so that a form fault does not hide a value. A line without
    its version token is read from its type."""
    head, _, tail = line.partition(" // ")
    toks = head.split()
    if toks and toks[0] != "RW1":
        toks = ["RW1"] + toks
    typ = toks[1] if len(toks) > 1 else None
    kv = {}
    for t in toks[3:]:
        if "=" in t:
            k, v = t.split("=", 1)
            kv.setdefault(k.strip().lower(), v.strip())
    return typ, kv, tail


def check_line(text: str, got: dict, rec: dict, slot: str | None) -> tuple[list[str], str | None, bool]:
    """Problems with an RB line readback of `got`; returns (problems, the line, whether the reply was the line alone)."""
    line, alone = extract_line(text)
    if not line:
        return ["no line"], None, False
    typ, kv, tail = tolerant_slots(line)
    p = []
    if typ != "RB":
        p.append(f"type {typ}, not RB")
    want = F.line_slots(got)
    for k, v in want.items():
        if k not in kv:
            p.append(f"{k} missing")
            continue
        norm = F.SLOT_NORM[k]
        if norm(kv[k]) != norm(v):
            p.append(f"{k}={kv[k]}, received {v}")
    if "h" in kv:
        p.append("carries h=")
    m = DOUBT.search(line)
    if m:
        p.append(f"comments or questions: {m.group(0)!r}")
    return p, line, alone
