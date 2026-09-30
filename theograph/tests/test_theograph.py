"""Tests for the theograph pipeline: date anchoring, the correction registry rule, and the demo patient
end to end from the stored extractor replies (no model call).

  python3 -m pytest -q theograph/tests        or        python3 theograph/tests/test_theograph.py
"""
from __future__ import annotations
import json, pathlib, shutil, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from theograph.normalise import anchor  # noqa: E402
from theograph.registry import build_registry, corrected_document  # noqa: E402

DEMO = ROOT / "theograph" / "demo" / "patient-01"
DOC = {"id": "d", "date": "2026-05-22", "admitted": "2026-05-19", "discharged": "2026-05-22", "patient": "p"}
LETTER = {"id": "l", "date": "2026-07-07", "admitted": None, "discharged": None, "patient": "p"}


def A(item, act="OBS", time="CUR", when=None, chg=None):
    slots = {}
    if when:
        slots["when"] = when
    if chg:
        slots["chg"] = chg
    return {"item": item, "act": act, "time": time, "slots": slots}


def test_explicit_dates():
    assert anchor(A("meas:egfr", when="20260520"), LETTER)["t_start"] == "2026-05-20"
    r = anchor(A("dx:nstemi", "ASSESS", "PAST", when="202103"), LETTER)
    assert (r["t_start"], r["t_end"], r["t_prec"]) == ("2021-03-01", "2021-03-31", "M")
    r = anchor(A("dx:angina", "ASSESS", "CUR", when="2025"), LETTER)
    assert (r["t_start"], r["t_end"], r["t_prec"]) == ("2025-01-01", "2025-12-31", "Y")


def test_intervals_read_by_what_the_line_says():
    # a plan n after the document
    assert anchor(A("fu:review", "PLAN", "FUT", when="6w"), LETTER)["t_start"] == "2026-08-18"
    assert anchor(A("fu:review", "PLAN", "CUR", when="6w"), LETTER)["t_start"] == "2026-08-18"
    # a course length runs forward from the document and is kept as a duration
    r = anchor(A("med:clopidogrel", "RX", "CUR", when="12m", chg="START"), DOC)
    assert (r["t_start"], r["t_end"], r["t_dur"]) == ("2026-05-22", "2027-05-22", "12m")
    # a symptom for three months: onset before the document, still current
    r = anchor(A("sym:chest-pain", "RPT", "CUR", when="3m"), LETTER)
    assert (r["t_start"], r["t_end"]) == ("2026-04-07", None)
    # a past event n ago is a point; a past symptom n ago ran up to some time before the document
    assert anchor(A("dx:mi", "ASSESS", "PAST", when="3y"), LETTER)["t_end"] == "2023-07-07"
    assert anchor(A("sym:rash", "RPT", "PAST", when="3y"), LETTER)["t_end"] == "2026-07-07"
    # the six-week review that this letter is: a point on the letter's date
    r = anchor(A("fu:review", "DONE", "CUR", when="6w"), LETTER)
    assert (r["t_start"], r["t_prec"]) == ("2026-07-07", "POINT")
    # hours count from admission
    assert anchor(A("meas:troponin", "OBS", "PAST", when="6h"), DOC)["t_start"] == "2026-05-19"


def test_admission_and_discharge_resolve_through_a_correction():
    corr = {"id": "c", "date": "2026-06-02", "admitted": None, "discharged": None, "patient": "p", "corrects": "d"}
    docs = {"d": DOC, "c": corr}
    assert anchor(A("meas:egfr", when="discharge"), corr, docs)["t_start"] == "2026-05-22"
    assert anchor(A("meas:egfr", when="admission"), corr, docs)["t_start"] == "2026-05-19"
    r = anchor(A("sym:chest-pain", "RPT", "CUR", when="since-discharge"), LETTER, {"d": DOC, "l": LETTER})
    assert (r["t_start"], r["t_end"], r["t_prec"]) == ("2026-05-22", None, "EVENT")


def test_no_date_rules():
    assert anchor(A("dx:hypertension", "ASSESS", "CUR"), LETTER)["t_prec"] == "ASOF"
    assert anchor(A("meas:weight", "OBS", "CUR"), LETTER)["t_prec"] == "POINT"
    assert anchor(A("dx:mi", "ASSESS", "PAST"), LETTER)["t_prec"] == "BEFORE"
    assert anchor(A("fu:review", "PLAN", "FUT"), LETTER)["t_prec"] == "AFTER"


def test_correction_letter_finds_its_document():
    docs = [
        {"id": "d03", "patient": "p", "type": "discharge summary", "date": "2026-05-22", "lines": []},
        {"id": "d04", "patient": "p", "type": "clinic letter", "date": "2026-07-07", "lines": []},
        {"id": "d06", "patient": "p", "type": "correction", "date": "2026-06-02", "lines": ["Dear Dr", "Please note a correction to the discharge summary of 22 May 2026."]},
    ]
    assert corrected_document(docs[2], docs) == "d03"
    docs[2]["lines"] = ["a correction"]
    assert corrected_document(docs[2], docs) == "d03"   # the latest earlier discharge summary


def run_demo(tmp: pathlib.Path) -> tuple[list[dict], list[dict], dict]:
    from theograph.__main__ import main
    out = tmp / "p01"
    main(["run", str(DEMO), str(out), "--provider", "mock", "--from-files", str(DEMO / "replies"), "--title", "Demo"])
    events = [json.loads(l) for l in (out / "events.jsonl").read_text().splitlines()]
    rows = [json.loads(l) for l in (out / "assertions.jsonl").read_text().splitlines()]
    return rows, events, json.loads((out / "summary.json").read_text())


def test_demo_patient_end_to_end():
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        rows, events, summary = run_demo(tmp)
        by = lambda k, c: [e for e in events if e["kind"] == k and e["concept"] == c]  # noqa: E731
        assert summary["documents"] == 6 and summary["extraction"]["ok"] == 6
        assert len(rows) == 204 and summary["conflicts"] == 0
        # the correction letter supersedes the discharge eGFR and creatinine on the discharge date
        egfr = {e["start"]: e for e in by("meas", "egfr")}
        assert egfr["2026-05-22"]["value"]["res"] == "79" and any(f.startswith("corrected: 75 -> 79") for f in egfr["2026-05-22"]["flags"])
        assert [egfr[d]["value"]["res"] for d in sorted(egfr)] == ["82", "81", "79", "79", "80"]
        # serial troponins on the admission day are two readings, not a conflict
        trop = [e for e in by("meas", "troponin") if e["pol"] == "POS"]
        assert sorted(e["value"]["res"] for e in trop) == ["8", "9"] and all(e["start"] == "2026-05-19" for e in trop)
        # one clopidogrel course from the stent, planned stop from the correction letter, stated in four documents
        clop = [e for e in by("med", "clopidogrel") if e["pol"] == "POS"]
        assert len(clop) == 1 and clop[0]["start"] == "2026-05-20" and clop[0]["open"] and clop[0]["planned_end"] == "2027-05-20" and clop[0]["n_docs"] == 4
        # aspirin stopped at discharge; ramipril and bisoprolol as two courses each with the change linked
        asp = [e for e in by("med", "aspirin") if e["pol"] == "POS"]
        assert len(asp) == 1 and asp[0]["end"] == "2026-05-22" and not asp[0]["open"]
        ram = sorted(by("med", "ramipril"), key=lambda e: e["value"]["dose"])
        assert [e["value"]["dose"] for e in ram] == ["10mg", "5mg"] and ram[1]["end"] == "2026-03-03" and ram[0]["start"] == "2026-03-03"
        assert any(r["rel"] == "supersedes" for r in ram[0]["relations"])
        # smoking: stated by four documents, ended on the date the patient gave
        smk = [e for e in by("soc", "smoking") if e["pol"] == "POS"]
        assert len(smk) == 1 and smk[0]["end"] == "2026-06-01" and smk[0]["n_docs"] == 4
        # the stent: "drug-eluting stent", "stent" and "PCI" on or in May 2026 are one event in three documents; 2021 is another
        pci = sorted(by("proc", "percutaneous-coronary-intervention"), key=lambda e: e["start"])
        assert [e["start"] for e in pci] == ["2021-03-01", "2026-05-20"] and pci[1]["n_docs"] == 3
        # plans and their evidence
        flags = {(e["kind"], e["concept"], e["start"] or e["first_seen"]): e["flags"] for e in events}
        assert any(f.startswith("fulfilled by d04") for f in flags[("proc", "renal-function-test", "2026-06-05")])
        assert any(f.startswith("fulfilled by d03") for f in flags[("proc", "ct-coronary-angiogram", "2026-03-03")])
        assert any(f.startswith("fulfilled by d04") for f in flags[("ref", "cardiac-rehabilitation", "2026-05-22")])
        assert any(f.startswith("evidenced by d02") for f in flags[("ref", "cardiology", "2026-01-14")])
        rev = [e for e in events if e["kind"] == "fu" and e["concept"] == "review"]
        assert {e["specialty"] for e in rev} == {"cardiology", "general practice"}
        assert summary["plans_without_evidence"] == 7 and summary["plans_with_evidence"] == 11
        assert (tmp / "p01" / "theograph.html").stat().st_size > 50_000
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
