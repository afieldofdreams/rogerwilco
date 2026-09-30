"""Link: assertions from many documents become events on one timeline.

An event is one thing that happened or held true for the patient: a problem, a course of a medicine
at one dose, a measurement on a date, a procedure, a state such as smoking. Every assertion that
states it becomes a source of the event, with its document, date, act, certainty, quote and weight.
Restatements therefore collapse into one event with several sources; changes (a new dose, a stop,
a correction) start or close events and are linked to what they replace; disagreements between
sources are kept and flagged rather than resolved silently.

Rules, by kind
  meas          one event per value and date; a different value on the same date is a conflict unless
                one source is a correction, which then supersedes
  med           one event per course at a dose: START begins, STOP ends, INC/DEC/SWITCH/CHG end the
                previous course and begin a new one, CONT/HOLD/RPT attach to the open course; a
                different dose with no change stated begins a new course and is flagged
  dx alg soc    one event per state (affirmed or negated); a later PAST statement closes an open state
  sym func      as above, but a new event after 180 days without mention
  proc ref fu   one event per date; an order or plan followed by the thing done within 180 days is one
                event, fulfilled; a plan with no evidence of completion is flagged in the analysis
Within a document, re= supersedes the line it points at; the superseded line stays as a source.
Source weight comes from the document type (data below) reduced for patient report and hedging.
"""
from __future__ import annotations
import datetime as dt, json, pathlib, re
from . import read_jsonl, write_jsonl
from .registry import load_registry

DOC_WEIGHT = {"discharge summary": 1.0, "correction": 1.0, "clinic letter": 0.9, "ward round": 0.85, "emergency": 0.85,
              "gp note": 0.75, "referral": 0.7, "medication review": 0.7, "telephone review": 0.6, "document": 0.5}
CERT_RANK = {"CERT": 3, "POSS": 2, "COND": 1, "HYPO": 0}
STATE_KINDS = {"dx", "alg", "soc", "func", "sym"}
POINT_KINDS = {"proc", "ref", "fu"}
SYM_GAP_DAYS = 180
FULFIL_DAYS = 180


def _d(s: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat(s) if s else None
    except ValueError:
        return None


def weight(a: dict) -> float:
    w = DOC_WEIGHT.get(a.get("doc_type") or "", 0.5)
    if a.get("act") == "RPT":
        w *= 0.85
    w *= {"CERT": 1.0, "POSS": 0.5, "COND": 0.3, "HYPO": 0.2}.get(a.get("cert"), 1.0)
    return round(w, 3)


def point_date(a: dict) -> dt.date | None:
    """The date to sort and compare an assertion by."""
    for k in ("t_start", "t_end", "t_asof", "doc_date"):
        d = _d(a.get(k))
        if d:
            return d
    return None


def n_res(v) -> str:
    return str(v).replace(",", "").strip() if v is not None else ""


def n_dose(v) -> str:
    v = (v or "").lower().replace(" ", "").replace("-", "")
    v = re.sub(r"micrograms?|microg|µg|ug", "mcg", v)
    return v


def source(a: dict, role: str = "states") -> dict:
    return {"assertion": f"{a['doc']}/{a['id']}", "doc": a["doc"], "doc_type": a.get("doc_type"), "doc_date": a.get("doc_date"), "lines": a.get("lines"),
            "src": a.get("src"), "quote": a.get("quote"), "act": a.get("act"), "cert": a.get("cert"), "pol": a.get("pol"), "time": a.get("time"),
            "slots": a.get("slots") or {}, "weight": weight(a), "role": role, "t_start": a.get("t_start"), "t_end": a.get("t_end"), "t_prec": a.get("t_prec")}


class Event:
    _n = 0

    def __init__(self, a: dict, role: str = "states"):
        Event._n += 1
        self.id = f"ev-{Event._n:04d}"
        self.patient, self.kind, self.concept, self.canon = a["patient"], a["kind"], a["concept"], a["canon"]
        self.pol, self.subj = a.get("pol"), a.get("subj")
        self.sources: list[dict] = []
        self.start = self.end = None
        self.open = False
        self.value = {}
        self.flags: list[str] = []
        self.relations: list[dict] = []
        self.display = a["item"].split(":", 1)[1]
        self.add(a, role)

    def add(self, a: dict, role: str = "states") -> None:
        s = source(a, role); self.sources.append(s)
        if role in ("states", "corrects", "starts", "changes") and a.get("slots"):
            best = max((x for x in self.sources if x["role"] in ("states", "corrects", "starts", "changes")), key=lambda x: (x["role"] == "corrects", x["weight"], x["doc_date"] or ""))
            self.value = {k: v for k, v in best["slots"].items() if k not in ("when",)}
        ps, pe = _d(a.get("t_start")), _d(a.get("t_end"))
        if a.get("t_prec") in ("D", "M", "Y", "REL", "EVENT", "POINT"):
            if ps and (self.start is None or ps < self.start):
                self.start = ps
            if pe and (self.end is None or pe > self.end) and role != "closes":
                self.end = pe

    @property
    def authority(self) -> float:
        return max((s["weight"] for s in self.sources if s["role"] != "superseded"), default=0.0)

    @property
    def cert(self) -> str:
        live = [s for s in self.sources if s["role"] != "superseded"]
        best = max(live, key=lambda s: (s["weight"], CERT_RANK.get(s["cert"], 0)))
        return best["cert"]

    def first_seen(self) -> str | None:
        return min((s["doc_date"] for s in self.sources if s["doc_date"]), default=None)

    def last_seen(self) -> str | None:
        return max((s["doc_date"] for s in self.sources if s["doc_date"]), default=None)

    def to_dict(self) -> dict:
        return {"id": self.id, "patient": self.patient, "kind": self.kind, "concept": self.concept, "canon": self.canon, "display": self.display,
                "pol": self.pol, "subj": self.subj, "cert": self.cert, "authority": self.authority, "value": self.value,
                "start": self.start.isoformat() if self.start else None, "end": self.end.isoformat() if self.end else None, "open": self.open,
                "first_seen": self.first_seen(), "last_seen": self.last_seen(), "n_sources": len(self.sources), "n_docs": len({s["doc"] for s in self.sources}),
                "doc_types": sorted({s["doc_type"] for s in self.sources if s["doc_type"]}), "flags": self.flags, "relations": self.relations, "sources": self.sources}


def _relate(a: Event, b: Event, rel: str) -> None:
    a.relations.append({"rel": rel, "event": b.id}); b.relations.append({"rel": {"supersedes": "superseded_by", "follows": "followed_by", "fulfils": "fulfilled_by"}.get(rel, rel), "event": a.id})


def link_group(items: list[dict]) -> list[Event]:
    """Events for one (patient, canon, subj) group, in date order."""
    items = sorted(items, key=lambda a: (point_date(a) or dt.date.min, a.get("doc_date") or "", a.get("id") or ""))
    kind = items[0]["kind"]
    events: list[Event] = []
    if kind == "meas":
        for a in items:
            d = point_date(a); v = n_res((a.get("slots") or {}).get("res"))
            hit = None
            for ev in events:
                ed = ev.start or _d(ev.first_seen())
                same_day = d and ed and abs((d - ed).days) <= 2
                if same_day and n_res(ev.value.get("res")) == v:
                    hit = ev; break
                if same_day and v and n_res(ev.value.get("res")) and n_res(ev.value.get("res")) != v:
                    if a.get("doc_type") == "correction":
                        ev.add(a, "corrects"); ev.flags.append("corrected")
                        ev.value["res"] = v; hit = ev; break
                    ev.add(a, "disputes"); ev.flags.append(f"conflict: {n_res(ev.value.get('res'))} vs {v} ({a['doc']})"); hit = ev; break
            if hit is None:
                events.append(Event(a))
        return events
    if kind == "med":
        open_ev: Event | None = None
        for a in items:
            sl = a.get("slots") or {}; chg = sl.get("chg"); d = point_date(a); dose = n_dose(sl.get("dose"))
            if a.get("pol") == "NEG":
                ev = Event(a); ev.flags.append("negated"); events.append(ev); continue
            od = n_dose(open_ev.value.get("dose")) if open_ev is not None else ""
            same_dose = (not dose) or (not od) or dose == od
            if chg == "STOP":
                if open_ev is not None:
                    open_ev.add(a, "closes"); open_ev.end = d or open_ev.end; open_ev.open = False; open_ev = None
                else:
                    ev = Event(a, "closes"); ev.end = d; ev.open = False; ev.flags.append("stopped; no earlier course recorded"); events.append(ev)
                continue
            if chg in ("INC", "DEC", "SWITCH", "CHG") or (chg == "START" and open_ev is not None and not same_dose):
                ev = Event(a, "starts"); ev.start = ev.start or d; ev.open = True
                if open_ev is not None:
                    open_ev.end = d; open_ev.open = False; _relate(ev, open_ev, "supersedes")
                events.append(ev); open_ev = ev; continue
            if open_ev is None:
                ev = Event(a, "starts" if chg == "START" else "states"); ev.open = True
                if chg == "START":
                    ev.start = ev.start or d
                else:
                    ev.flags.append("course start unknown")
                events.append(ev); open_ev = ev; continue
            if same_dose:
                open_ev.add(a)
                if chg == "HOLD":
                    open_ev.flags.append(f"held ({a['doc']})")
                continue
            ev = Event(a); ev.open = True; ev.flags.append(f"dose differs from {open_ev.value.get('dose')} with no change stated")
            open_ev.end = d; open_ev.open = False; _relate(ev, open_ev, "follows"); events.append(ev); open_ev = ev
        return events
    if kind in POINT_KINDS:
        for a in items:
            d = point_date(a); planned = a.get("act") in ("ORD", "PLAN") or a.get("time") == "FUT"
            hit = None
            for ev in events:
                ed = ev.start or _d(ev.first_seen())
                if d and ed and abs((d - ed).days) <= 2 and ev.pol == a.get("pol"):
                    hit = ev; break
                if ev.flags and "planned" in ev.flags and not planned and d and ed and 0 <= (d - ed).days <= FULFIL_DAYS and a.get("pol") == "POS":
                    ev.add(a, "fulfils"); ev.flags.remove("planned"); ev.flags.append("fulfilled"); ev.start = d; ev.end = d; hit = ev; break
            if hit is None:
                ev = Event(a)
                if planned:
                    ev.flags.append("planned")
                events.append(ev)
            elif hit.sources[-1]["assertion"] != f"{a['doc']}/{a['id']}":
                hit.add(a)
        return events
    # state kinds
    cur: dict[str, Event] = {}
    for a in items:
        pol = a.get("pol"); d = point_date(a); ev = cur.get(pol)
        if ev is not None and kind in ("sym", "func"):
            last = _d(ev.last_seen())
            if last and d and (d - last).days > SYM_GAP_DAYS:
                ev.open = False; ev = None
        if ev is None:
            ev = Event(a); ev.open = a.get("time") != "PAST"; events.append(ev); cur[pol] = ev
            continue
        if a.get("time") != "PAST" and not ev.open and ev.end and d and d > ev.end:
            # stated current again after being closed: a recurrence, so a new event
            new = Event(a); new.open = True; _relate(new, ev, "follows"); events.append(new); cur[pol] = new
            continue
        was_open = ev.open
        ev.add(a)
        if a.get("time") == "PAST" and was_open:
            # current earlier, past now: the state had resolved by this document
            ev.end = _d(a.get("doc_date")) or ev.end; ev.open = False; ev.flags.append(f"resolved by {a['doc']}")
    return events


def apply_re(rows: list[dict]) -> None:
    by_doc: dict[str, dict[str, dict]] = {}
    for a in rows:
        by_doc.setdefault(a["doc"], {})[a["id"]] = a
    for a in rows:
        if a.get("re") and a["re"] in by_doc.get(a["doc"], {}):
            target = by_doc[a["doc"]][a["re"]]
            target["superseded_by"] = a["id"]; a["corrects"] = a["re"]


def episodes_for(docs: list[dict], events: list[dict]) -> list[dict]:
    eps = []
    for d in docs:
        if d.get("admitted") and d.get("discharged"):
            eps.append({"id": f"ep-adm-{d['id']}", "kind": "admission", "label": f"Admission ({d.get('specialty') or 'inpatient'})", "start": d["admitted"], "end": d["discharged"], "docs": [d["id"]], "specialty": d.get("specialty")})
    # outpatient: runs of clinic letters and referrals per specialty, in date order, broken by a gap of a year
    letters = sorted([d for d in docs if d["type"] in ("clinic letter", "referral", "correction") and d.get("date")], key=lambda d: d["date"])
    runs: dict[str, list[dict]] = {}
    for d in letters:
        spec = d.get("specialty") or "outpatient"
        if d["type"] == "referral":
            m = re.search(r"to:\s*([a-z ]+?)(?: outpatients| clinic|,|\n)", "\n".join(d["lines"][:6]).lower())
            spec = (m.group(1).strip() if m else spec)
        runs.setdefault(spec, []).append(d)
    for spec, ds in runs.items():
        if spec in ("general practice",):
            continue
        cur = [ds[0]]
        for d in ds[1:]:
            if (_d(d["date"]) - _d(cur[-1]["date"])).days > 365:
                eps.append(_out_ep(spec, cur)); cur = [d]
            else:
                cur.append(d)
        eps.append(_out_ep(spec, cur))
    for d in docs:
        eps.append({"id": f"enc-{d['id']}", "kind": "encounter", "label": f"{d['type']} ({d.get('specialty') or 'unknown'})", "start": d.get("date"), "end": d.get("date"), "docs": [d["id"]], "specialty": d.get("specialty")})
    return eps


def _out_ep(spec: str, ds: list[dict]) -> dict:
    return {"id": f"ep-out-{spec.replace(' ', '-')}-{ds[0]['date']}", "kind": "outpatient", "label": f"{spec} episode", "start": ds[0]["date"], "end": ds[-1]["date"], "docs": [d["id"] for d in ds], "specialty": spec}


def link(out_dir: pathlib.Path) -> tuple[list[dict], list[dict]]:
    rows = read_jsonl(out_dir / "assertions.jsonl")
    docs = load_registry(out_dir)
    if not rows or "canon" not in rows[0]:
        raise SystemExit("run normalise first")
    apply_re(rows)
    Event._n = 0
    groups: dict[tuple, list[dict]] = {}
    superseded = []
    for a in rows:
        if a.get("superseded_by"):
            superseded.append(a); continue
        groups.setdefault((a["patient"], a["canon"], a.get("subj")), []).append(a)
    events: list[Event] = []
    for key, items in groups.items():
        events.extend(link_group(items))
    # superseded lines attach to the event their corrector joined
    by_assertion = {s["assertion"]: ev for ev in events for s in ev.sources}
    for a in superseded:
        ev = by_assertion.get(f"{a['doc']}/{a['superseded_by']}")
        if ev:
            ev.add(a, "superseded"); ev.flags.append(f"corrected within {a['doc']}")
    out = [ev.to_dict() for ev in events]
    out.sort(key=lambda e: (e["kind"], e["canon"], e["start"] or e["first_seen"] or ""))
    write_jsonl(out_dir / "events.jsonl", out)
    eps = episodes_for(docs, out)
    (out_dir / "episodes.json").write_text(json.dumps(eps, indent=1))
    n_multi = sum(1 for e in out if e["n_docs"] > 1)
    print(f"{len(rows)} assertions -> {len(out)} events ({n_multi} stated in more than one document); {sum(1 for e in out if any(f.startswith('conflict') for f in e['flags']))} conflicts, "
          f"{sum(1 for e in out if 'corrected' in ' '.join(e['flags']))} corrected, {sum(1 for e in out if 'planned' in e['flags'])} plans without evidence of completion; {len(eps)} episodes and encounters")
    return out, eps
