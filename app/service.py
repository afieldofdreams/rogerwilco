"""Shared core of the rogerwilco app.

Finds the skill folder, imports the reference codec from its scripts/ directory by path, and wraps the codec as plain
functions that take and return JSON-friendly values. The REST routes (main.py) and the MCP tools (mcp.py) both call
these, so the two front doors behave the same. Codec errors surface as FormError.
"""
import json
import os
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

# Longest input accepted, in characters. A message line is meant to be short (the tail alone is capped at 300), and the
# acc comparison grows with the square of the number of criteria, so a small cap keeps one request from burning CPU.
MAX_LINE = 2000
MAX_FIELD = 1000


def _find_skill_dir() -> Path:
    """RW_SKILL_DIR when it is set (and then it has to be right), else the first usual place that holds the codec."""
    env = os.environ.get("RW_SKILL_DIR")
    candidates = [Path(env)] if env else [
        Path("/srv/rogerwilco"),                              # the container
        APP_DIR.parent / "rogerwilco",                        # a repo checkout: app/ next to rogerwilco/
        Path("/home/claude/rogerwilco-skill/rogerwilco"),     # local dev
    ]
    for candidate in candidates:
        if (candidate / "scripts" / "rogerwilco.py").is_file():
            return candidate.resolve()
    raise RuntimeError(
        "rogerwilco codec not found. Set RW_SKILL_DIR to the folder that holds scripts/rogerwilco.py. Looked in: "
        + ", ".join(str(c) for c in candidates)
    )


SKILL_DIR = _find_skill_dir()
_scripts = str(SKILL_DIR / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)
import rogerwilco as rw  # noqa: E402  the reference codec, standard library only

FormError = rw.FormError
VERSION = rw.VERSION


# ------------------------------------------------------------------ profile names

# The codec turns a profile name into a file path (profiles/<name>.json). Names reach it from the network, both as the
# profile argument and as p= tokens inside messages, so a name such as ../../tmp/x would make it load any .json file
# on disk as a profile. Refuse anything that is not a plain name before the codec sees it.
_SAFE_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _guard_profile_loading() -> None:
    if getattr(rw.load_profile, "_rw_guarded", False):
        return
    original = rw.load_profile

    def load_profile(name):
        if name and not _SAFE_NAME.fullmatch(name):
            raise FormError(f"invalid profile name {name!r}")
        return original(name)

    load_profile._rw_guarded = True
    rw.load_profile = load_profile


_guard_profile_loading()


def profile_arg(profile) -> str | None:
    """The API's profile argument as the codec wants it. Empty and 'core' both mean no profile: the codec treats core
    as the base every profile extends, and refuses to load it as a profile."""
    name = _text("profile", profile or "", MAX_FIELD).strip()
    return None if name in ("", "core") else name


# ------------------------------------------------------------------ inputs

def _text(name: str, value, limit: int) -> str:
    if not isinstance(value, str):
        raise FormError(f"{name} must be a string")
    if len(value) > limit:
        raise FormError(f"{name} is {len(value)} characters; the limit is {limit}")
    return value


def acc_list(name: str, value) -> list[str] | None:
    """'len:120w+no:em-dash' (or a list of such strings) as the codec's token list. Empty means not supplied."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = "+".join(str(v) for v in value)
    tokens = [t.strip() for t in _text(name, value, MAX_FIELD).split("+") if t.strip()]
    return tokens or None


# ------------------------------------------------------------------ operations

def health() -> dict:
    return {"ok": True, "version": VERSION, "commit": os.environ.get("GIT_COMMIT") or "unknown"}


def validate(line, profile=None) -> dict:
    msg, errors, warnings = rw.parse(_text("line", line, MAX_LINE), profile_arg(profile))
    return {"ok": not errors, "message": msg, "errors": errors, "warnings": warnings}


def check_rb(ho, rb, profile=None, expect_acc=None) -> dict:
    problems, notes = rw.check_rb_full(
        _text("ho", ho, MAX_LINE), _text("rb", rb, MAX_LINE), profile_arg(profile), acc_list("expect_acc", expect_acc)
    )
    return {"ok": not problems, "problems": problems, "notes": notes}


def check_ho(ho, record, profile=None) -> dict:
    if not isinstance(record, dict):
        raise FormError("record must be a JSON object of slot values as they are written on the line")
    if len(record) > 64:
        raise FormError(f"record has {len(record)} keys; the limit is 64")
    for k, v in record.items():
        if not isinstance(k, str) or not k:
            raise FormError("record keys are slot names")
        if isinstance(v, list):
            if len(v) > 64 or not all(isinstance(x, (str, int, float, bool)) for x in v):
                raise FormError(f"record value for {k} must be a list of simple values")
        elif not isinstance(v, (str, int, float, bool)):
            raise FormError(f"record value for {k} must be a string, number, boolean or list")
        _text(k, "+".join(str(x) for x in v) if isinstance(v, list) else str(v), MAX_FIELD)
    problems, notes = rw.check_ho(_text("ho", ho, MAX_LINE), record, profile_arg(profile))
    return {"ok": not problems, "problems": problems, "notes": notes}


def check_dn(ho, dn, profile=None, rb=None) -> dict:
    problems, notes = rw.check_dn(
        _text("ho", ho, MAX_LINE), _text("dn", dn, MAX_LINE), profile_arg(profile),
        rb_line=_text("rb", rb, MAX_LINE) if rb else None,
    )
    return {"ok": not problems, "problems": problems, "notes": notes}


def check_thread(lines, profile=None, now=None) -> dict:
    """Every handoff in a conversation closes: DN, UN, FL or an acknowledged CX. lines is the conversation, one
    message per row, in the order sent (a string, or a list of strings). now is YYYYMMDDTHHMMZ; default the clock."""
    if isinstance(lines, list):
        if not all(isinstance(x, str) for x in lines):
            raise FormError("lines must be strings")
        lines = "\n".join(lines)
    rows = _text("lines", lines, MAX_BATCH).splitlines()
    if len([r for r in rows if r.strip()]) > MAX_ROWS:
        raise FormError(f"lines has more than {MAX_ROWS} rows")
    for r in rows:
        if len(r) > MAX_LINE:
            raise FormError(f"a line is {len(r)} characters; the limit is {MAX_LINE}")
    clock = None
    if now:
        clock = _text("now", now, 32).strip()
        if not rw.TIME_RE.match(clock):
            raise FormError("now is YYYYMMDDTHHMMZ in UTC, e.g. 20261012T1405Z")
    problems, notes = rw.check_thread(rows, profile_arg(profile), clock)
    return {"ok": not problems, "problems": problems, "notes": notes}


def make_rb(ho, id, profile=None, acc=None, do=None, hash=True) -> dict:  # noqa: A002  names match the REST body
    prof = profile_arg(profile)
    msg, errors, _ = rw.parse(_text("ho", ho, MAX_LINE), prof)
    if errors:
        raise FormError("; ".join(errors))
    if msg["type"] != "HO":
        raise FormError(f"make-rb needs an HO line, got {msg['type']}")
    rb = rw.make_rb(
        ho, _text("id", id, MAX_FIELD), prof, with_hash=bool(hash),
        acc=acc_list("acc", acc), do=_text("do", do or "", MAX_FIELD).strip() or None,
    )
    return {"rb": rb}


def digest(line, profile=None) -> dict:
    return {"digest": rw.digest(_text("line", line, MAX_LINE), profile_arg(profile))}


def to_json(line, profile=None) -> dict:
    return {"message": json.loads(rw.to_json(_text("line", line, MAX_LINE), profile_arg(profile)))}


def from_json(message, profile=None) -> dict:
    if isinstance(message, str):
        try:
            message = json.loads(_text("message", message, MAX_LINE))
        except json.JSONDecodeError as e:
            raise FormError(f"message is not valid JSON: {e}") from None
    if not isinstance(message, dict):
        raise FormError("message must be a JSON object")
    for key in ("type", "id"):
        if not isinstance(message.get(key), str) or not message[key]:
            raise FormError(f"message needs {key!r} as a non-empty string")
    if message.get("slots") is None:
        message = {**message, "slots": {}}
    elif not isinstance(message["slots"], dict):
        raise FormError("slots must be a JSON object")
    text = json.dumps(message, ensure_ascii=False)
    if len(text) > MAX_LINE:
        raise FormError(f"message is {len(text)} characters as JSON; the limit is {MAX_LINE}")
    try:
        return {"line": rw.from_json(text, profile_arg(profile))}
    except FormError:
        raise
    except (KeyError, TypeError, AttributeError, ValueError) as e:  # a JSON shape the codec did not expect
        raise FormError(f"message could not be encoded: {type(e).__name__}: {e}") from None


def legend(profile=None) -> str:
    return rw.legend(profile_arg(profile))


# ------------------------------------------------------------------ the gate: lines as the record

# When lines state facts that came from a document, the gate is what the batch must pass before anyone acts on them
# or they become the record: every line valid under the profile, every statement pointing at the evidence, and the
# evidence saying what the line says. The rules come from the profile's own `translation` note (clin, pay); the checks
# are the ones the research harnesses enforced (research/translation/tools/gate.py, research/month-end/tools/mail.py).
MAX_DOCUMENT = 200_000   # characters of source document
MAX_BATCH = 60_000       # characters of lines
MAX_ROWS = 500
# One src range is the few lines a statement stands on (the translation corpus cites at most 45). Without a bound a
# batch of rows each citing the whole document makes the gate join and search the document once per row.
MAX_SRC_LINES = 100
MAX_SRC_CHARS = 20_000

_CONCEPT_RE = re.compile(r"[a-z0-9][a-z0-9./-]*")
_DOC_SRC_RE = re.compile(r"^doc:([A-Za-z0-9._-]+)#l(\d+)(?:-(\d+))?$")
_EMAIL_SRC_RE = re.compile(r"^email:(\d+)$")


def _norm_words(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _join_doc_lines(parts: list[str]) -> str:
    """Consecutive document lines as one string: a line ending in a hyphen continues its word on the next line."""
    out = ""
    for seg in parts:
        seg = seg.strip()
        if out and out.endswith("-"):
            out += seg
        elif out:
            out += " " + seg
        else:
            out = seg
    return _norm_words(out)


def _inbox_messages(document: str) -> int:
    """How many messages an inbox export holds: segments between lines that are exactly ---, not counting a header
    segment (one with no From: line). This is the export shape the month-end study used."""
    segments = re.split(r"(?m)^---\s*$", document)
    return sum(1 for seg in segments if seg.strip() and re.search(r"(?mi)^\**from:", seg))


class _Gate:
    def __init__(self, profile_name: str, document: str | None, doc_id: str | None):
        self.profile = profile_name
        self.spec = rw.load_profile(profile_name)
        # The codec's merged spec keeps what it validates; the translation note is read from the profile file.
        try:
            raw = json.loads((rw.PROFILES / f"{profile_name}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        self.rule = raw.get("translation") if isinstance(raw.get("translation"), dict) else None
        if self.rule is None:
            raise FormError(f"profile {profile_name!r} has no translation rule; the gate applies to profiles that "
                            "make the lines the record (clin, pay)")
        self.doc_lines = document.splitlines() if document else None
        self.doc_id = doc_id
        self.messages = _inbox_messages(document) if document and profile_name == "pay" else None
        self.errors: list[str] = []
        self.notes: list[str] = []
        self.rows: list[dict] = []
        self.seen: set[str] = set()

    # -- per-row checks -------------------------------------------------------------------------------------------
    def row(self, i: int, line: str) -> None:
        errs: list[str] = []
        if not line.startswith(VERSION + " "):
            self._finish(i, line, None, [f"does not start with {VERSION} (every row is a rogerwilco line)"])
            return
        msg, perrs, _warn = rw.parse(line, spec=self.spec)
        if perrs:
            self._finish(i, line, msg, perrs)
            return
        if msg["slots"].get("p") != self.profile:
            errs.append(f"missing p={self.profile}")
        if msg["id"] in self.seen:
            errs.append(f"id {msg['id']} already used in this batch")
        if msg["type"] == "ST":
            if msg.get("re") and msg["re"] not in self.seen:
                errs.append(f"re={msg['re']} does not name an earlier line in this batch")
            check = self._clin if self.profile == "clin" else self._pay
            check(msg, errs)
        self.seen.add(msg["id"])
        self._finish(i, line, msg, errs)

    def _finish(self, i: int, line: str, msg, errs: list[str]) -> None:
        for e in errs:
            self.errors.append(f"row {i}: {e}")
        self.rows.append({"row": i, "line": line, "type": (msg or {}).get("type"), "ok": not errs, "errors": errs,
                          "message": msg if msg and not errs else None})

    def _clin(self, msg: dict, errs: list[str]) -> None:
        item = msg.get("item") or ""
        kinds = self.spec.get("item_kinds") or {}
        if ":" not in item or item.split(":", 1)[0] not in kinds:
            errs.append(f"item={item!r}: item is <kind>:<concept> with kind one of {' '.join(kinds)}")
        elif not _CONCEPT_RE.fullmatch(item.split(":", 1)[1]):
            errs.append(f"item={item!r}: concept is lowercase words joined by hyphens")
        src = msg["slots"].get("src")
        if isinstance(src, list):
            errs.append(f"exactly one src per line (got {len(src)}); a statement has one place in the document")
            src = src[0] if src else None
        quote = msg.get("tail") or ""
        if not src:
            errs.append("src= is missing: doc:<id>#l<n> or doc:<id>#l<n>-<m>, the numbered line(s) the words are on")
            if not quote:
                errs.append("the quote is missing: the tail is the shortest verbatim quote that supports the statement")
            return
        m = _DOC_SRC_RE.match(str(src))
        if not m:
            errs.append(f"src={src}: expected doc:<id>#l<n> or doc:<id>#l<n>-<m>")
            return
        if self.doc_id is not None and m.group(1) != str(self.doc_id):
            errs.append(f"src={src}: this is document doc:{self.doc_id}")
        a, b = int(m.group(2)), int(m.group(3) or m.group(2))
        if not quote:
            errs.append(f"the quote is missing: copy the words from line(s) {src} that support the statement")
        if self.doc_lines is None:
            return
        if a < 1 or b > len(self.doc_lines) or b < a:
            errs.append(f"src={src}: the document has lines 1 to {len(self.doc_lines)}")
            return
        if b - a + 1 > MAX_SRC_LINES or sum(len(x) for x in self.doc_lines[a - 1:b]) > MAX_SRC_CHARS:
            errs.append(f"src={src}: a source range is at most {MAX_SRC_LINES} lines and {MAX_SRC_CHARS:,} characters; "
                        "cite the lines the quote is on")
            return
        if quote and _norm_words(quote) not in _join_doc_lines(self.doc_lines[a - 1:b]):
            errs.append(f"the quote is not found verbatim in {src}: {quote[:80]!r}")

    def _pay(self, msg: dict, errs: list[str]) -> None:
        sl = msg["slots"]
        item = msg.get("item") or ""
        srcs = sl.get("src")
        if isinstance(srcs, str):
            srcs = [srcs]
        if item.startswith(("inv:", "sup:", "doc:")) and not srcs:
            errs.append("a line that states a source document carries src=email:<n> (the message number in the "
                        "inbox export), bank:<YYYYMMDD> or po:<id>")
        if self.messages is not None:
            for s in srcs or []:
                m = _EMAIL_SRC_RE.match(str(s))
                if m and not 1 <= int(m.group(1)) <= self.messages:
                    errs.append(f"src={s}: the inbox export has messages 1 to {self.messages}")
        flags = set(sl.get("flag") or [])
        if item.startswith("inv:") and not ({"VOID", "STMT", "NOISE"} & flags):
            for k in ("amt", "cur", "kind"):
                if k not in sl:
                    errs.append(f"an invoice line needs {k}=")
        if all(k in sl for k in ("net", "vat", "amt")) and sl.get("kind") == "GROSS":
            from decimal import Decimal, InvalidOperation
            try:
                if Decimal(str(sl["net"])) + Decimal(str(sl["vat"])) != Decimal(str(sl["amt"])):
                    errs.append(f"net {sl['net']} + vat {sl['vat']} is not amt {sl['amt']}")
            except InvalidOperation:
                errs.append("net, vat and amt must be numbers")

    # -- the batch ------------------------------------------------------------------------------------------------
    def run(self, lines: str) -> dict:
        rows = [l.strip() for l in lines.splitlines() if l.strip()]
        if not rows:
            raise FormError("lines is empty: paste the translation, one rogerwilco line per row")
        if len(rows) > MAX_ROWS:
            raise FormError(f"lines has {len(rows)} rows; the limit is {MAX_ROWS}")
        for i, line in enumerate(rows, 1):
            if len(line) > MAX_LINE:
                self._finish(i, line, None, [f"{len(line)} characters; a line is at most {MAX_LINE}"])
                continue
            self.row(i, line)
        if self.profile == "clin" and self.doc_lines is None:
            self.notes.append("no document given: src ranges and quotes were not checked against the source")
        if self.profile == "pay" and self.messages == 0:
            self.notes.append("the document holds no messages separated by --- lines, so email:<n> pointers were not "
                              "checked against it")
        counts = {"rows": len(rows), "st": sum(1 for r in self.rows if r["type"] == "ST"),
                  "ok": sum(1 for r in self.rows if r["ok"])}
        return {"ok": not self.errors, "errors": self.errors, "notes": self.notes, "counts": counts,
                "rows": self.rows,
                "accepted": [r["message"] for r in self.rows if r["ok"] and r["type"] == "ST"]}


def gate(lines, profile, document=None, doc_id=None) -> dict:
    """Check a batch of lines against the source document they state facts from, under the profile's rule for lines
    as the record. Returns {ok, errors, notes, counts, rows, accepted}."""
    name = profile_arg(profile)
    if not name:
        raise FormError("profile is required: the gate applies to a profile that makes the lines the record (clin, pay)")
    doc = _text("document", document, MAX_DOCUMENT) if document else None
    ident = _text("doc_id", str(doc_id), MAX_FIELD).strip() if doc_id not in (None, "") else None
    return _Gate(name, doc, ident).run(_text("lines", lines, MAX_BATCH))


CORE_DESCRIPTION = (
    "The core vocabulary: nine message types, the ask, why, out, need and conf codes, and the acc constraint keys. "
    "No domain codes."
)


def profiles() -> list[dict]:
    out = [{"name": "core", "description": CORE_DESCRIPTION}]
    for path in sorted(rw.PROFILES.glob("*.json")):
        if path.stem == "core":
            continue
        try:
            description = json.loads(path.read_text(encoding="utf-8")).get("description", "")
        except (OSError, ValueError, AttributeError):
            description = ""
        out.append({"name": path.stem, "description": description})
    return out


_DOCS = {"spec": Path("references") / "SPEC.md", "skill": Path("SKILL.md")}


def document(which: str) -> str:
    """The protocol spec ('spec') or the skill file ('skill') as shipped in the skill folder."""
    return (SKILL_DIR / _DOCS[which]).read_text(encoding="utf-8")
