"""Link: assertions from many documents become events on one timeline.

An event is one thing that happened or held true for the patient: a problem, a course of a medicine
at one dose, a measurement on a date, a procedure, a state such as smoking. Every assertion that
states it becomes a source of the event, with its document, date, act, certainty, quote and weight.
Restatements therefore collapse into one event with several sources; changes (a new dose, a stop,
a correction) start or close events and are linked to what they replace; disagreements between
sources are kept and flagged rather than resolved silently.

Rules, by kind
  meas          one event per value and date; a different value on the same date is a conflict unless
                one source is a correction letter, which then supersedes; an order is a planned event,
                fulfilled by the next value of that measurement within 180 days
  med           one event per course at a dose: START begins, STOP and SWITCH end, INC/DEC/CHG end the
                previous course and begin a new one, CONT/HOLD/RPT attach to the open course; a
                different dose with no change stated begins a new course and is flagged; a course
                length (for 12 months) or a future STOP sets the planned end without closing the course
  dx alg soc    one event per state (affirmed or negated); a later PAST statement closes an open state,
                on the date the statement gives if it gives one
  sym func      as above, but a new event after 180 days without mention
  proc ref fu   one event per date, matched by overlap so "May 2026" and "20 May 2026" are the same
                event; an order or plan followed by the thing done within 180 days is one event,
                fulfilled; an undated "previous" mention attaches to the latest earlier event
Across kinds and concepts, after grouping: a planned referral is fulfilled by the procedure or visit
of the same name; an ordered panel (renal function) by any member result (data/panels.json); a
planned clinic review or referral is evidenced by a later document from that specialty. Plans with
no evidence stay flagged. Within a document, re= supersedes the line it points at; the superseded
line stays as a source. Source weight comes from the document type (data below) reduced for patient
report and hedging.
"""
from __future__ import annotations
import datetime as dt, json, pathlib, re
from . import PKG, read_jsonl, write_jsonl
from .normalise import _shift
from .registry import load_registry

DOC_WEIGHT = {"discharge summary": 1.0, "correction": 1.0, "clinic letter": 0.9, "ward round": 0.85, "emergency": 0.85,
              "gp note": 0.75, "referral": 0.7, "medication review": 0.7, "telephone review": 0.6, "document": 0.5}
CERT_RANK = {"CERT": 3, "POSS": 2, "COND": 1, "HYPO": 0}
PREC_RANK = {"D": 5, "EVENT": 5, "REL": 4, "POINT": 3, "M": 2, "Y": 1}
DATED = set(PREC_RANK)
STATE_KINDS = {"dx", "alg", "soc", "func", "sym"}
POINT_KINDS = {"proc", "ref", "fu"}
PLAN_ACTS = {"ORD", "PLAN"}
SYM_GAP_DAYS = 180
FULFIL_DAYS = 180
TOL_DAYS = 2
GENERIC_FU = {"review", "follow-up", "clinic", "outpatients", "appointment"}   # grouped by specialty (named in the concept, else the planning document's)
SPECIALTIES = ("cardiology", "respiratory", "gastroenterology", "neurology", "oncology", "renal", "nephrology", "endocrinology", "diabetes", "rheumatology",
               "dermatology", "orthopaedics", "orthopaedic", "urology", "gynaecology", "haematology", "ophthalmology", "ent", "psychiatry", "geriatrics", "stroke",
               "general-practice", "gp", "surgical", "surgery", "physiotherapy", "dietetics", "pain", "palliative", "vascular", "hepatology", "chest")
PANELS_PATH = PKG / "data" / "panels.json"


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


def fu_key(a: dict) -> tuple[str, str | None]:
    """(canon, specialty) for a follow-up: "cardiology-clinic", "review" and "follow-up" are all the review of
    a specialty, the one named in the concept or else the one that wrote the plan."""
    if a["kind"] != "fu":
        return a["canon"], None
    words = a["concept"].split("-")
    spec = next((w for w in words if w in SPECIALTIES), None)
    if spec == "gp":
        spec = "general-practice"
    rest = [w for w in words if w not in SPECIALTIES]
    if spec and (not rest or "-".join(rest) in GENERIC_FU):
        return "fu:review", spec.replace("-", " ")
    if a["concept"] in GENERIC_FU:
        return "fu:review", a.get("doc_specialty")
    return a["canon"], None


def is_planned(a: dict) -> bool:
    return a.get("time") == "FUT" or (a.get("act") in PLAN_ACTS and a.get("time") != "PAST")


def n_res(v) -> str:
    return str(v).replace(",", "").strip() if v is not None else ""


def n_dose(v) -> str:
    v = (v or "").lower().replace(" ", "").replace("-", "")
    v = re.sub(r"micrograms?|microg|µg|ug", "mcg", v)
    return v


def overlaps(s1: dt.date | None, e1: dt.date | None, s2: dt.date | None, e2: dt.date | None, tol: int = TOL_DAYS) -> bool:
    s1, e1, s2, e2 = s1 or e1, e1 or s1, s2 or e2, e2 or s2
    if not (s1 and e1 and s2 and e2):
        return False
    t = dt.timedelta(days=tol)
    return s1 - t <= e2 and s2 - t <= e1


def source(a: dict, role: str = "states") -> dict:
    return {"assertion": f"{a['doc']}/{a['id']}", "doc": a["doc"], "doc_type": a.get("doc_type"), "doc_date": a.get("doc_date"), "lines": a.get("lines"),
            "src": a.get("src"), "quote": a.get("quote"), "act": a.get("act"), "cert": a.get("cert"), "pol": a.get("pol"), "time": a.get("time"),
            "slots": a.get("slots") or {}, "weight": weight(a), "role": role, "t_start": a.get("t_start"), "t_end": a.get("t_end"), "t_prec": a.get("t_prec"), "t_dur": a.get("t_dur")}


def doc_source(doc: dict, role: str) -> dict:
    """A document as evidence in itself (the clinic letter that shows the planned visit happened)."""
    return {"assertion": None, "doc": doc["id"], "doc_type": doc.get("type"), "doc_date": doc.get("date"), "lines": None, "src": None, "quote": None,
            "act": "DONE", "cert": "CERT", "pol": "POS", "time": "CUR", "slots": {}, "weight": DOC_WEIGHT.get(doc.get("type") or "", 0.5), "role": role,
            "t_start": doc.get("date"), "t_end": doc.get("date"), "t_prec": "D", "t_dur": None}


class Event:
    _n = 0

    def __init__(self, a: dict, role: str = "states"):
        Event._n += 1
        self.id = f"ev-{Event._n:04d}"
        self.patient, self.kind, self.concept, self.canon = a["patient"], a["kind"], a["concept"], a["canon"]
        self.pol, self.subj = a.get("pol"), a.get("subj")
        self.canon, self.specialty = fu_key(a)
        self.concept = self.canon.split(":", 1)[1]
        self.t_raw = a.get("t_raw")
        self.sources: list[dict] = []
        self.start = self.end = None
        self.prec_rank = 0
        self.open = False
        self.planned_end: dt.date | None = None
        self.planned_by: str | None = None
        self.value = {}
        self.flags: list[str] = []
        self.relations: list[dict] = []
        self.display = self.concept + (f" ({self.specialty})" if self.specialty else "")
        self.add(a, role)

    def add(self, a: dict, role: str = "states", anchor: bool = True) -> None:
        s = source(a, role); self.sources.append(s)
        valued = [x for x in self.sources if x["role"] in ("states", "corrects", "starts", "changes", "fulfils") and any(k != "when" for k in x["slots"])]
        if valued:
            best = max(valued, key=lambda x: (x["role"] == "corrects", "res" in x["slots"], x["weight"], x["doc_date"] or ""))
            self.value = {k: v for k, v in best["slots"].items() if k not in ("when",)}
        if not anchor or a.get("t_prec") not in DATED:
            return
        ps, pe = _d(a.get("t_start")), _d(a.get("t_end"))
        rank = PREC_RANK.get(a.get("t_prec"), 0)
        if self.kind in POINT_KINDS or self.kind == "meas":
            if rank > self.prec_rank:              # the most precise statement dates a point event
                self.start, self.end, self.prec_rank = ps, pe, rank
            return
        if ps and (self.start is None or ps < self.start):
            self.start = ps
        if self.kind == "med":                     # a course ends only by STOP, change or supersession
            return
        if pe and (self.end is None or pe > self.end):
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

    def span(self) -> tuple[dt.date | None, dt.date | None]:
        s = self.start or _d(self.first_seen())
        return s, self.end or s

    def set_planned_end(self, d: dt.date | None, a: dict, how: str) -> None:
        """A planned end wins over an earlier one when it comes from a correction or a later document."""
        if not d:
            return
        if self.planned_end is None or a.get("doc_type") == "correction" or (a.get("doc_date") or "") >= (self.planned_by or ""):
            self.planned_end, self.planned_by = d, a.get("doc_date") or ""
            self.flags = [f for f in self.flags if not f.startswith("stop planned")]
            self.flags.append(f"stop planned {d.isoformat()} ({how}, {a['doc']})")

    def to_dict(self) -> dict:
        return {"id": self.id, "patient": self.patient, "kind": self.kind, "concept": self.concept, "canon": self.canon, "display": self.display,
                "specialty": self.specialty, "pol": self.pol, "subj": self.subj, "cert": self.cert, "authority": self.authority, "value": self.value,
                "start": self.start.isoformat() if self.start else None, "end": self.end.isoformat() if self.end else None, "open": self.open,
                "planned_end": self.planned_end.isoformat() if self.planned_end else None,
                "first_seen": self.first_seen(), "last_seen": self.last_seen(), "n_sources": len(self.sources), "n_docs": len({s["doc"] for s in self.sources}),
                "doc_types": sorted({s["doc_type"] for s in self.sources if s["doc_type"]}), "flags": self.flags, "relations": self.relations, "sources": self.sources}


def _relate(a: Event, b: Event, rel: str) -> None:
    a.relations.append({"rel": rel, "event": b.id}); b.relations.append({"rel": {"supersedes": "superseded_by", "follows": "followed_by", "fulfils": "fulfilled_by"}.get(rel, rel), "event": a.id})


def _fulfil(ev: Event, a: dict, d: dt.date | None) -> None:
    ev.add(a, "fulfils")
    ev.flags = [f for f in ev.flags if f != "planned"]
    ev.flags.append(f"fulfilled by {a['doc']}")
    if d:
        ev.start = ev.end = d


def _nearest_plan(events: list[Event], d: dt.date | None, pol: str | None) -> Event | None:
    """The planned event of this group that the thing done on d most plausibly fulfils."""
    if not d:
        return None
    cands = []
    for ev in events:
        if "planned" not in ev.flags or ev.pol != pol:
            continue
        ed = ev.start or _d(ev.first_seen())
        if ed and -TOL_DAYS <= (d - ed).days <= FULFIL_DAYS:
            cands.append((abs((d - ed).days), ev))
    return min(cands, key=lambda x: x[0])[1] if cands else None


def link_group(items: list[dict]) -> list[Event]:
    """Events for one (patient, canon, subj) group, in date order."""
    items = sorted(items, key=lambda a: (point_date(a) or dt.date.min, a.get("doc_date") or "", a.get("id") or ""))
    kind = items[0]["kind"]
    events: list[Event] = []
    if kind == "meas":
        for a in items:
            d = point_date(a); v = n_res((a.get("slots") or {}).get("res"))
            if is_planned(a) and not v:
                ev = Event(a); ev.flags.append("planned"); events.append(ev); continue
            hit = _nearest_plan(events, d, a.get("pol")) if v else None
            if hit is not None:
                _fulfil(hit, a, d); continue
            for ev in events:
                if "planned" in ev.flags:
                    continue
                ed = ev.start or _d(ev.first_seen())
                same_day = d and ed and abs((d - ed).days) <= TOL_DAYS
                if not same_day or ev.pol != a.get("pol"):
                    continue
                ev_v = n_res(ev.value.get("res"))
                if ev_v == v or not v or not ev_v:
                    hit = ev; ev.add(a); break
                if ev.sources[0]["doc"] == a["doc"] or (ev.t_raw or "") != (a.get("t_raw") or ""):
                    continue                            # a series (admission, six hours) or two time points on one day: separate readings
                if a.get("doc_type") == "correction":
                    ev.add(a, "corrects"); ev.flags.append(f"corrected: {ev_v} -> {v} ({a['doc']})"); ev.value["res"] = v; hit = ev; break
                if any(s["role"] == "corrects" for s in ev.sources):
                    ev.add(a, "superseded"); hit = ev; break
                ev.add(a, "disputes"); ev.flags.append(f"conflict: {ev_v} vs {v} ({a['doc']})"); hit = ev; break
            if hit is None:
                events.append(Event(a))
        return events
    if kind == "med":
        open_ev: Event | None = None
        for a in items:
            sl = a.get("slots") or {}; chg = sl.get("chg"); d = point_date(a); dose = n_dose(sl.get("dose")); dur = a.get("t_dur")
            if a.get("pol") == "NEG":
                ev = Event(a); ev.flags.append("negated"); events.append(ev); continue
            od = n_dose(open_ev.value.get("dose")) if open_ev is not None else ""
            same_dose = (not dose) or (not od) or dose == od
            if chg in ("STOP", "SWITCH"):
                if is_planned(a):
                    target = open_ev or (events[-1] if events and "negated" not in events[-1].flags else None)
                    if target is not None:
                        target.add(a, "plans", anchor=False); target.set_planned_end(d, a, "planned")
                    else:
                        ev = Event(a, "plans"); ev.flags.append("stop planned; no course recorded"); events.append(ev)
                    continue
                if open_ev is not None:
                    open_ev.add(a, "closes", anchor=False); open_ev.end = d or open_ev.end; open_ev.open = False; open_ev = None
                else:
                    ev = Event(a, "closes"); ev.end = d; ev.start = None; ev.open = False; ev.flags.append("stopped; no earlier course recorded"); events.append(ev)
                continue
            if chg in ("INC", "DEC", "CHG") or (chg == "START" and open_ev is not None and not same_dose):
                ev = Event(a, "starts"); ev.start = ev.start or d; ev.open = True
                if dur:
                    ev.set_planned_end(_d(a.get("t_end")), a, f"course of {dur}")
                if open_ev is not None:
                    open_ev.end = d; open_ev.open = False; _relate(ev, open_ev, "supersedes")
                events.append(ev); open_ev = ev; continue
            if open_ev is None:
                ev = Event(a, "starts" if chg == "START" else "states"); ev.open = True
                if chg == "START":
                    ev.start = ev.start or d
                else:
                    ev.flags.append("course start unknown")
                if dur:
                    ev.set_planned_end(_d(a.get("t_end")), a, f"course of {dur}")
                events.append(ev); open_ev = ev; continue
            if same_dose:
                open_ev.add(a, anchor=not dur)
                if chg == "HOLD":
                    open_ev.flags.append(f"held ({a['doc']})")
                if dur and open_ev.start:
                    m = re.fullmatch(r"(\d+)([dwmy])", dur)
                    if m:
                        open_ev.set_planned_end(_shift(open_ev.start, int(m.group(1)), m.group(2), +1), a, f"course of {dur}")
                continue
            ev = Event(a); ev.open = True; ev.flags.append(f"dose differs from {open_ev.value.get('dose')} with no change stated")
            open_ev.end = d; open_ev.open = False; _relate(ev, open_ev, "follows"); events.append(ev); open_ev = ev
        return events
    if kind in POINT_KINDS:
        for a in items:
            d = point_date(a); planned = is_planned(a); doc_date = _d(a.get("doc_date"))
            undated_past = a.get("t_prec") in ("BEFORE", "ASOF", "NONE") and a.get("time") == "PAST"
            site = (a.get("slots") or {}).get("site")
            if undated_past or (a.get("act") in PLAN_ACTS and a.get("time") == "PAST"):
                # "previous PCI", "the CT requested in clinic": the latest earlier event of the same kind of statement
                cands = [ev for ev in events if ev.pol == a.get("pol") and (ev.start or _d(ev.first_seen())) and (ev.start or _d(ev.first_seen())) <= (doc_date or dt.date.max)
                         and not (site and ev.value.get("site") and ev.value.get("site") != site)]
                if cands:
                    ev = max(cands, key=lambda ev: ev.start or _d(ev.first_seen()))
                    if "planned" in ev.flags and not planned and a.get("act") == "DONE":
                        _fulfil(ev, a, None); ev.flags[-1] += " (date not stated)"
                    else:
                        ev.add(a, "states", anchor=False)
                    continue
                ev = Event(a); events.append(ev); continue
            hit = None if planned else _nearest_plan(events, d, a.get("pol"))
            if hit is not None:
                _fulfil(hit, a, d); continue
            for ev in events:
                if ev.pol != a.get("pol") or ("planned" in ev.flags) != planned:
                    continue
                if overlaps(_d(a.get("t_start")), _d(a.get("t_end")), *ev.span()) and not (site and ev.value.get("site") and ev.value.get("site") != site):
                    hit = ev; ev.add(a); break
            if hit is None:
                ev = Event(a)
                if planned:
                    ev.flags.append("planned")
                events.append(ev)
        return events
    # state kinds
    cur: dict[str, Event] = {}
    for a in items:
        pol = a.get("pol"); d = point_date(a); ev = cur.get(pol); past = a.get("time") == "PAST"
        if ev is not None and kind in ("sym", "func"):
            last = _d(ev.last_seen())
            if last and d and (d - last).days > SYM_GAP_DAYS:
                ev.open = False; ev = None
        if ev is None:
            # an examination finding is observed on a date, not a state that runs on; reported symptoms and diagnoses run on until resolved
            ev = Event(a); ev.open = not past and not (kind in ("sym", "func") and a.get("act") == "OBS"); events.append(ev); cur[pol] = ev
            continue
        if past:
            if a.get("act") == "OBS" and a.get("t_prec") in DATED:
                ev.add(a)                               # a finding observed on a past date: the state held then
            elif ev.open:
                # current earlier, past now: the state had resolved, on the date given (if it is after the start) or by this document
                ev.add(a, "closes", anchor=False)
                when = _d(a.get("t_start")) if a.get("t_prec") in ("D", "M", "REL", "EVENT") else None
                if when and ((ev.start and when <= ev.start) or (_d(ev.first_seen()) and when < _d(ev.first_seen()))):
                    when = None
                ev.end = when or _d(a.get("doc_date")) or ev.end; ev.open = False
                ev.flags.append(f"resolved by {a['doc']}" + (f" ({ev.end.isoformat()})" if when else ""))
            else:
                ev.add(a, "states", anchor=False)
            continue
        if not ev.open and ev.end and d and d > ev.end:
            if a.get("act") == "OBS" and all(s["act"] == "OBS" for s in ev.sources):
                ev.add(a)                               # the finding observed again: the series extends to this date
                continue
            # stated current again after being closed: a recurrence, so a new event
            new = Event(a); new.open = True; _relate(new, ev, "follows"); events.append(new); cur[pol] = new
            continue
        ev.add(a)
        if ev.open and kind in ("sym", "func") and a.get("act") == "OBS" and all(s["act"] == "OBS" for s in ev.sources):
            ev.open = False
    return events


def fulfil_across(events: list[Event], docs: list[dict]) -> None:
    """Plans met by something recorded under another concept, kind or document."""
    panels = {k: list(v) for k, v in json.loads(PANELS_PATH.read_text()).items() if not k.startswith("_")}

    def value_doc(o: Event) -> str:
        """The document that gave the event its value (an order fulfilled by a later result names the result's document)."""
        with_res = [s for s in o.sources if s["slots"].get("res")]
        return (max(with_res, key=lambda s: (s["role"] == "corrects", s["weight"]))["doc"] if with_res else o.sources[0]["doc"])
    by_concept: dict[str, list[Event]] = {}
    for ev in events:
        by_concept.setdefault(ev.concept, []).append(ev)
    for ev in events:
        if "planned" not in ev.flags or ev.pol != "POS":
            continue
        pd = ev.start or _d(ev.first_seen())
        if not pd:
            continue
        window = lambda x: x and -TOL_DAYS <= (x - pd).days <= FULFIL_DAYS  # noqa: E731
        # the same name under another kind: ref:cardiac-rehabilitation -> proc:cardiac-rehabilitation
        done = [o for o in by_concept.get(ev.concept, []) if o is not ev and o.kind != ev.kind and o.pol == "POS" and "planned" not in o.flags and window(o.start or _d(o.first_seen()))]
        if done:
            o = min(done, key=lambda o: ((o.start or _d(o.first_seen())) - pd, o.canon))
            ev.flags.remove("planned"); ev.flags.append(f"fulfilled by {o.sources[0]['doc']} ({o.canon})"); _relate(o, ev, "fulfils"); continue
        # an ordered panel: any member result
        members = panels.get(ev.concept)
        if members:
            hits = [o for c in members for o in by_concept.get(c, []) if o.kind == "meas" and o.value.get("res") and window(o.start)]
            if hits:
                o = min(hits, key=lambda o: (o.start - pd, o.concept))
                ev.flags.remove("planned"); ev.flags.append(f"fulfilled by {value_doc(o)} ({', '.join(sorted({h.concept for h in hits if h.start == o.start}))} on {o.start.isoformat()})")
                _relate(o, ev, "fulfils"); continue
        # a planned visit or referral: a later document from that specialty is evidence in itself
        if ev.kind in ("fu", "ref"):
            words = set(ev.concept.split("-"))
            spec_ok = (lambda d: d["specialty"] == ev.specialty) if ev.specialty else (lambda d: d["specialty"] in ev.concept or bool(words & set(d["specialty"].split())))
            later = [d for d in docs if d.get("date") and d.get("specialty") and d["patient"] == ev.patient and window(_d(d["date"]))
                     and d["type"] not in ("correction",) and spec_ok(d) and all(s["doc"] != d["id"] for s in ev.sources)]
            if later:
                d = min(later, key=lambda d: d["date"])
                ev.sources.append(doc_source(d, "evidences")); ev.flags.remove("planned"); ev.flags.append(f"evidenced by {d['id']} ({d['type']}, {d['date']})")


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
        groups.setdefault((a["patient"], *fu_key(a), a.get("subj")), []).append(a)
    events: list[Event] = []
    for key, items in groups.items():
        events.extend(link_group(items))
    fulfil_across(events, docs)
    # superseded lines attach to the event their corrector joined
    by_assertion = {s["assertion"]: ev for ev in events for s in ev.sources if s["assertion"]}
    for a in superseded:
        ev = by_assertion.get(f"{a['doc']}/{a['superseded_by']}")
        if ev:
            ev.add(a, "superseded", anchor=False); ev.flags.append(f"corrected within {a['doc']}")
    out = [ev.to_dict() for ev in events]
    out.sort(key=lambda e: (e["kind"], e["canon"], e["start"] or e["first_seen"] or ""))
    write_jsonl(out_dir / "events.jsonl", out)
    eps = episodes_for(docs, out)
    (out_dir / "episodes.json").write_text(json.dumps(eps, indent=1))
    n_multi = sum(1 for e in out if e["n_docs"] > 1)
    print(f"{len(rows)} assertions -> {len(out)} events ({n_multi} stated in more than one document); {sum(1 for e in out if any(f.startswith('conflict') for f in e['flags']))} conflicts, "
          f"{sum(1 for e in out if any(f.startswith('corrected') for f in e['flags']))} corrected, {sum(1 for e in out if 'planned' in e['flags'])} plans without evidence of completion, "
          f"{sum(1 for e in out if any(f.startswith(('fulfilled', 'evidenced')) for f in e['flags']))} plans with evidence; {len(eps)} episodes and encounters")
    return out, eps
