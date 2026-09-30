"""The document registry: what each document is, when, whose, and its numbered text.

Documents are text or Markdown files in a folder (one patient per folder, or a manifest that says
which patient each file belongs to). A manifest `docs.csv` with columns file, patient, type, date,
specialty, author (and optionally corrects, the file stem a correction letter refers to) overrides
anything parsed from the header. Without one, the type is guessed from the first lines, the date is
the first labelled date in the header, and the patient is the folder name. PDF and Word files are
converted on the way in when pdftotext or python-docx is available.
"""
from __future__ import annotations
import csv, datetime as dt, pathlib, re, shutil, subprocess
from . import read_jsonl, write_jsonl

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
DATE_RES = [
    re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b"),          # 14 January 2026
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),                        # 2026-01-14
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),                    # 14/01/2026 (UK order)
]
TYPE_RULES = [
    ("discharge summary", r"discharge summary"),
    ("correction", r"\bcorrection\b"),
    ("referral", r"referral"),
    ("medication review", r"medication review"),
    ("ward round", r"ward round"),
    ("emergency", r"emergency department|\bED\b"),
    ("telephone review", r"by telephone|telephone review"),
    ("clinic letter", r"clinic date|outpatients|clinic\b"),
    ("gp note", r"surgery, consultation|consultation note|\bGP\b"),
]
DATE_LABELS = ("date:", "clinic date:", "discharged:", "dictated:", "seen on:")


def parse_date(s: str) -> str | None:
    """First date in s as YYYY-MM-DD, or None."""
    for rx in DATE_RES:
        m = rx.search(s)
        if not m:
            continue
        try:
            if rx is DATE_RES[0]:
                mon = MONTHS.get(m.group(2).lower()[:9]) or MONTHS.get(next((k for k in MONTHS if k.startswith(m.group(2).lower()[:3])), ""), None)
                if not mon:
                    continue
                d = dt.date(int(m.group(3)), mon, int(m.group(1)))
            elif rx is DATE_RES[1]:
                d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            else:
                d = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d.isoformat()
        except ValueError:
            continue
    return None


def labelled_date(lines: list[str], labels: tuple[str, ...]) -> str | None:
    for line in lines[:15]:
        low = line.lower()
        for lab in labels:
            if lab in low:
                d = parse_date(line[low.index(lab) + len(lab):])
                if d:
                    return d
    return None


def guess_type(lines: list[str]) -> str:
    head = "\n".join(lines[:6])
    for name, pat in TYPE_RULES:
        if re.search(pat, head, re.I):
            return name
    return "document"


def guess_specialty(lines: list[str]) -> str | None:
    head = "\n".join(lines[:4])
    m = re.search(r"(cardiology|respiratory|gastroenterology|diabetes|orthopaedics|trauma|neurology|oncology|renal|stroke|tia|acute medicine|surgical|surgery|emergency)", head, re.I)
    return m.group(1).lower() if m else None


def load_text(path: pathlib.Path) -> list[str] | None:
    suf = path.suffix.lower()
    if suf in (".md", ".txt"):
        return path.read_text(errors="replace").splitlines()
    if suf == ".pdf" and shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        return out.stdout.splitlines() if out.returncode == 0 else None
    if suf == ".docx":
        try:
            import docx  # type: ignore
            return [p.text for p in docx.Document(str(path)).paragraphs]
        except Exception:  # noqa: BLE001
            return None
    return None


def build_registry(input_dir: pathlib.Path, out_dir: pathlib.Path, patient: str | None = None) -> list[dict]:
    manifest = {}
    mp = input_dir / "docs.csv"
    if mp.exists():
        with mp.open(newline="") as f:
            for row in csv.DictReader(f):
                manifest[row["file"]] = row
    docs = []
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in (".md", ".txt", ".pdf", ".docx") and p.name != "build_docs.py")
    for n, path in enumerate(files, 1):
        lines = load_text(path)
        if lines is None:
            print(f"skipped {path.name}: no converter for {path.suffix}")
            continue
        m = manifest.get(path.name, {})
        d = {
            "id": path.stem, "num": n, "file": path.name,
            "patient": m.get("patient") or patient or input_dir.name,
            "type": (m.get("type") or guess_type(lines)).lower(),
            "date": m.get("date") or labelled_date(lines, DATE_LABELS) or parse_date("\n".join(lines[:8])),
            "specialty": (m.get("specialty") or guess_specialty(lines) or "").lower() or None,
            "author": m.get("author") or None,
            "admitted": labelled_date(lines, ("admitted:",)), "discharged": labelled_date(lines, ("discharged:",)),
            "n_lines": len(lines), "lines": lines,
        }
        if d["type"] == "discharge summary" and d["discharged"]:
            d["date"] = d["date"] or d["discharged"]
        if not d["date"]:
            print(f"warning: no date found for {path.name}; put one in docs.csv")
        docs.append(d)
    for d in docs:
        d["corrects"] = m.get("corrects") if (m := manifest.get(d["file"], {})).get("corrects") else (corrected_document(d, docs) if d["type"] == "correction" else None)
    write_jsonl(out_dir / "registry.jsonl", docs)
    return docs


def corrected_document(d: dict, docs: list[dict]) -> str | None:
    """The id of the document a correction letter corrects: the same patient's document on the date the
    letter names ("correction to the discharge summary of 22 May 2026"), else the latest earlier discharge
    summary. Admission and discharge dates in the letter then resolve against that document."""
    head = "\n".join(d["lines"][:15])
    mine = [x for x in docs if x["patient"] == d["patient"] and x["id"] != d["id"] and x.get("date")]
    for m in re.finditer(r"(?:summary|letter|note|report)\s+(?:of|dated|from)\s+([^\n.;,]+)", head, re.I):
        date = parse_date(m.group(1))
        if date:
            hits = [x for x in mine if x["date"] == date]
            if hits:
                return max(hits, key=lambda x: x["type"] == "discharge summary")["id"]
    earlier = [x for x in mine if x["type"] == "discharge summary" and d.get("date") and x["date"] <= d["date"]]
    return max(earlier, key=lambda x: x["date"])["id"] if earlier else None


def load_registry(out_dir: pathlib.Path) -> list[dict]:
    return read_jsonl(out_dir / "registry.jsonl")


def numbered(doc: dict) -> str:
    return "\n".join(f"{i:>3}  {l}" for i, l in enumerate(doc["lines"], 1))
