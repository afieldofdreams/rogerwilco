"""Normalise: anchor every assertion in time and give every concept its canonical name.

Time. Each assertion gets t_start, t_end (ISO dates or null), t_prec (how the anchor was reached)
and t_asof (the document date it was stated at):
  D, M, Y   an explicit date, month or year from when=
  REL       an interval from when= counted from the document date (3d before, 6w after)
  EVENT     admission or discharge date from the document registry
  ASOF      no date: current at the document date (start unknown, end open)
  POINT     no date: a point observation on the document date
  BEFORE    no date: before the document date
  AFTER     no date: after the document date
  NONE      no document date, or a when= the rules do not read (age-58); the raw value is kept
Concepts. item is lowercased, spelling and brand variants are mapped through data/synonyms.json,
and the result is stored as `canon` (kind:concept) next to the original item.
"""
from __future__ import annotations
import calendar, datetime as dt, json, pathlib, re
from . import KINDS, PKG, read_jsonl, write_jsonl
from .registry import MONTHS

SYN_PATH = PKG / "data" / "synonyms.json"
INTERVAL_RE = re.compile(r"^(\d+)(d|w|m|y|h)$")
POINT_ACTS = {"OBS", "DONE", "ORD", "ADV", "PLAN"}


def _load_synonyms(extra: pathlib.Path | None = None) -> dict[str, str]:
    """variant -> canonical (kind:concept). Variants without a kind apply within the canonical's kind."""
    table = {}
    for path in [SYN_PATH] + ([extra] if extra else []):
        if not path or not path.exists():
            continue
        data = json.loads(path.read_text())
        for kind, entries in data.items():
            if kind.startswith("_"):
                continue
            for canon, variants in entries.items():
                table[f"{kind}:{canon}"] = f"{kind}:{canon}"
                for v in variants:
                    key = v if ":" in v else f"{kind}:{v}"
                    table[key] = f"{kind}:{canon}"
    return table


def canonical(item: str, table: dict[str, str]) -> str:
    kind, _, concept = item.partition(":")
    concept = re.sub(r"[^a-z0-9./-]", "", concept.lower()).strip("-")
    key = f"{kind}:{concept}"
    if key in table:
        return table[key]
    # a variant recorded under another kind (e.g. med:gtn-spray written as proc:gtn-spray) still maps
    for k in KINDS:
        if f"{k}:{concept}" in table:
            return table[f"{k}:{concept}"]
    return key


def _date(s: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat(s) if s else None
    except ValueError:
        return None


def _shift(d: dt.date, n: int, unit: str, sign: int) -> dt.date:
    if unit == "d":
        return d + dt.timedelta(days=sign * n)
    if unit == "w":
        return d + dt.timedelta(weeks=sign * n)
    if unit == "h":
        return d
    months = n if unit == "m" else 12 * n
    y, m = divmod(d.month - 1 + sign * months, 12)
    y += d.year
    day = min(d.day, calendar.monthrange(y, m + 1)[1])
    return dt.date(y, m + 1, day)


def _month_bounds(y: int, m: int) -> tuple[str, str]:
    return dt.date(y, m, 1).isoformat(), dt.date(y, m, calendar.monthrange(y, m)[1]).isoformat()


def anchor(a: dict, doc: dict) -> dict:
    """Return the t_* fields for one assertion given its document."""
    d0 = _date(doc.get("date"))
    w = (a.get("slots") or {}).get("when")
    w = w.lower() if isinstance(w, str) else None
    t = a.get("time")
    out = {"t_start": None, "t_end": None, "t_prec": "NONE", "t_asof": doc.get("date"), "t_raw": w}
    if not d0:
        return out
    if w:
        if re.fullmatch(r"\d{8}", w):
            try:
                x = dt.date(int(w[:4]), int(w[4:6]), int(w[6:])).isoformat()
                return {**out, "t_start": x, "t_end": x, "t_prec": "D"}
            except ValueError:
                pass
        m = re.fullmatch(r"(\d{4})-?(\d{2})", w) or re.fullmatch(r"(\d{4})-?([a-z]+)", w) or re.fullmatch(r"([a-z]+)-?(\d{4})", w)
        if m:
            g1, g2 = m.group(1), m.group(2)
            y, mo = (int(g1), int(g2)) if g1.isdigit() and g2.isdigit() else ((int(g1), MONTHS.get(g2[:9]) or MONTHS.get(next((k for k in MONTHS if k.startswith(g2[:3])), ""), 0)) if g1.isdigit() else (int(g2), MONTHS.get(g1[:9]) or MONTHS.get(next((k for k in MONTHS if k.startswith(g1[:3])), ""), 0)))
            if 1 <= mo <= 12:
                s, e = _month_bounds(y, mo)
                return {**out, "t_start": s, "t_end": e, "t_prec": "M"}
        if re.fullmatch(r"(19|20)\d{2}", w):
            return {**out, "t_start": f"{w}-01-01", "t_end": f"{w}-12-31", "t_prec": "Y"}
        if w in ("late-" + str(d0.year - 1), f"late-{d0.year-1}") or re.fullmatch(r"(early|mid|late)-(19|20)\d{2}", w):
            y = int(w[-4:]); part = w.split("-")[0]
            s, e = {"early": (f"{y}-01-01", f"{y}-04-30"), "mid": (f"{y}-05-01", f"{y}-08-31"), "late": (f"{y}-09-01", f"{y}-12-31")}[part]
            return {**out, "t_start": s, "t_end": e, "t_prec": "M"}
        mo = MONTHS.get(w) or MONTHS.get(next((k for k in MONTHS if k.startswith(w[:3]) and len(w) >= 3), ""), 0)
        if mo and w.isalpha():
            y = d0.year
            if t == "FUT" and mo < d0.month:
                y += 1
            if t == "PAST" and mo > d0.month:
                y -= 1
            s, e = _month_bounds(y, mo)
            return {**out, "t_start": s, "t_end": e, "t_prec": "M"}
        m = INTERVAL_RE.match(w)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if t == "FUT":
                x = _shift(d0, n, unit, +1).isoformat()
                return {**out, "t_start": x, "t_end": x, "t_prec": "REL"}
            if t == "PAST":
                return {**out, "t_start": _shift(d0, n, unit, -1).isoformat(), "t_end": d0.isoformat(), "t_prec": "REL"}
            return {**out, "t_start": _shift(d0, n, unit, -1).isoformat(), "t_end": None, "t_prec": "REL"}
        if w in ("admission", "arrival", "on-admission"):
            x = doc.get("admitted") or doc.get("date")
            return {**out, "t_start": x, "t_end": x, "t_prec": "EVENT"}
        if w in ("discharge", "on-discharge"):
            x = doc.get("discharged") or doc.get("date")
            return {**out, "t_start": x, "t_end": x, "t_prec": "EVENT"}
        if w == "today":
            return {**out, "t_start": d0.isoformat(), "t_end": d0.isoformat(), "t_prec": "D"}
        if w == "yesterday":
            x = (d0 - dt.timedelta(days=1)).isoformat(); return {**out, "t_start": x, "t_end": x, "t_prec": "D"}
        if w == "tomorrow":
            x = (d0 + dt.timedelta(days=1)).isoformat(); return {**out, "t_start": x, "t_end": x, "t_prec": "D"}
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if w in days:
            delta = (days.index(w) - d0.weekday()) % 7
            if t == "PAST":
                delta = delta - 7 if delta else 0
            elif delta == 0:
                delta = 7
            x = (d0 + dt.timedelta(days=delta)).isoformat(); return {**out, "t_start": x, "t_end": x, "t_prec": "REL"}
        if w in ("last-week", "lastweek"):
            return {**out, "t_start": (d0 - dt.timedelta(days=7)).isoformat(), "t_end": d0.isoformat(), "t_prec": "REL"}
        if w in ("last-month", "last-year"):
            return {**out, "t_start": _shift(d0, 1, "m" if "month" in w else "y", -1).isoformat(), "t_end": d0.isoformat(), "t_prec": "REL"}
        # unread when= : fall through to the time-only rules but keep the raw value
    x = d0.isoformat()
    if t == "PAST":
        return {**out, "t_start": None, "t_end": x, "t_prec": "BEFORE"}
    if t == "FUT":
        return {**out, "t_start": x, "t_end": None, "t_prec": "AFTER"}
    kind = (a.get("item") or "").split(":")[0]
    if kind in ("meas", "proc") or a.get("act") in POINT_ACTS or (kind == "sym" and a.get("act") in ("OBS",)):
        return {**out, "t_start": x, "t_end": x, "t_prec": "POINT"}
    return {**out, "t_start": None, "t_end": None, "t_prec": "ASOF"}


def normalise(out_dir: pathlib.Path, synonyms: pathlib.Path | None = None) -> list[dict]:
    from .registry import load_registry
    docs = {d["id"]: d for d in load_registry(out_dir)}
    table = _load_synonyms(synonyms)
    rows = read_jsonl(out_dir / "assertions.jsonl")
    for a in rows:
        a.update(anchor(a, docs[a["doc"]]))
        a["canon"] = canonical(a["item"], table)
        a["kind"] = a["canon"].split(":")[0]
        a["concept"] = a["canon"].split(":", 1)[1]
    write_jsonl(out_dir / "assertions.jsonl", rows)
    n_anch = sum(1 for a in rows if a["t_prec"] in ("D", "M", "Y", "REL", "EVENT", "POINT"))
    print(f"{len(rows)} assertions: {n_anch} anchored to a date, {sum(1 for a in rows if a['t_prec']=='ASOF')} current as of their document, "
          f"{sum(1 for a in rows if a['t_prec'] in ('BEFORE','AFTER'))} before/after only, {sum(1 for a in rows if a['t_prec']=='NONE')} unanchored; "
          f"{sum(1 for a in rows if a['canon'] != a['item'])} concept names mapped to a canonical form")
    return rows
