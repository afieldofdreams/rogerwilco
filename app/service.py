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


CORE_DESCRIPTION = (
    "The core vocabulary: eight message types, the ask, why, out, need and conf codes, and the acc constraint keys. "
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
