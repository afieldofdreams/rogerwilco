"""Shared pieces for the translation study: paths, document text, quote matching, profile vocabulary."""
from __future__ import annotations
import importlib.util, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DOCS = ROOT / "data" / "docs"
RUNS = ROOT / "runs"
RESULTS = ROOT / "results"
PROFILE = REPO / "rogerwilco" / "profiles" / "clin.json"
CODEC = REPO / "rogerwilco" / "scripts" / "rogerwilco.py"
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
    return json.loads(PROFILE.read_text())


def doc_lines(n: int) -> list[str]:
    return (DOCS / f"doc{n:02d}.md").read_text().splitlines()


def numbered(n: int) -> str:
    return "\n".join(f"{i:>3}  {l}" for i, l in enumerate(doc_lines(n), 1))


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


SRC_RE = re.compile(r"^doc:(\d+)#l(\d+)(?:-(\d+))?$")


def parse_src(src: str, doc: int, n_lines: int) -> tuple[list[int] | None, str | None]:
    m = SRC_RE.match(src or "")
    if not m:
        return None, f"src={src!r}: expected doc:{doc}#l<n> or doc:{doc}#l<n>-<m>"
    if int(m.group(1)) != doc:
        return None, f"src={src}: this is document doc:{doc}"
    a, b = int(m.group(2)), int(m.group(3) or m.group(2))
    if a < 1 or b > n_lines or b < a:
        return None, f"src={src}: the document has lines 1 to {n_lines}"
    return list(range(a, b + 1)), None


def quote_in_lines(quote: str, lines: list[int], text: list[str]) -> bool:
    """Verbatim up to whitespace and letter case: the words must be the document's words, in its order."""
    return bool(quote) and norm(quote).lower() in join_lines([text[i - 1] for i in lines]).lower()


def count_tokens(s: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(s))
    except Exception:  # noqa: BLE001
        return len(s.split())


def enum_text() -> str:
    """The profile's enumerations, printed the way the legend prints them, for the JSON arm."""
    p = profile()
    out = []
    for name, vals in p["enums"].items():
        out.append(f"{name}: " + ", ".join(f"{k}={v}" for k, v in vals.items()))
    out.append("kind (the part of item before the colon): " + ", ".join(f"{k}={v}" for k, v in p["item_kinds"].items()))
    out.append("slots: " + "; ".join(f"{s['key']}={s['desc']}" for s in p["slots"] if s["key"] in VALUE_SLOTS or s["key"] == "src"))
    out.append("res is a number as written, or two numbers with a slash (7.2, 148/88); units go in unit.")
    return "\n".join(out)
