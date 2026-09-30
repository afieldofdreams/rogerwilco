"""theograph: documents in, an episodic care timeline out.

Pipeline: ingest (document registry) -> extract (one assertion line per statement, gated on provenance)
-> normalise (dates and concepts) -> link (events: dedup, supersession, conflicts, episodes)
-> analyse (report) -> render (self-contained HTML theograph).

Runs where the data is allowed to be. Model keys come from the environment; nothing is sent
anywhere but the endpoint you name. The codec and the clin profile are read from the rogerwilco
skill folder next to this package (or RW_SKILL_DIR).
"""
from __future__ import annotations
import importlib.util, json, os, pathlib

PKG = pathlib.Path(__file__).resolve().parent
SKILL_DIR = pathlib.Path(os.environ.get("RW_SKILL_DIR", PKG.parent / "rogerwilco"))
CODEC = SKILL_DIR / "scripts" / "rogerwilco.py"
PROFILE_NAME = "clin"
KINDS = ("sym", "dx", "med", "proc", "meas", "alg", "ref", "soc", "func", "fu")
CORE = ("act", "pol", "cert", "subj", "time")
VALUE_SLOTS = ("res", "unit", "dose", "route", "freq", "chg", "site", "who", "when")

_codec = None


def codec():
    global _codec
    if _codec is None:
        spec = importlib.util.spec_from_file_location("rogerwilco", CODEC)
        _codec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_codec)
    return _codec


def profile() -> dict:
    return json.loads((SKILL_DIR / "profiles" / f"{PROFILE_NAME}.json").read_text())


def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def write_jsonl(path: pathlib.Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
