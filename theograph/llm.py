"""Model providers. Keys come from the environment and nothing else.

anthropic: ANTHROPIC_API_KEY, model default claude-sonnet-5
openai:    OPENAI_API_KEY, OPENAI_BASE_URL (default https://api.openai.com/v1; any OpenAI-compatible endpoint), model required
mock:      replies from files: --from-files <dir> holding <doc id>.txt, <doc id>.fix<k>.txt for fix rounds and <doc id>.review.txt
           for the completeness review (used for tests and for assertions extracted elsewhere)
"""
from __future__ import annotations
import json, os, pathlib, time, urllib.error, urllib.request


class Provider:
    name = "base"

    def chat(self, messages: list[dict], max_tokens: int = 16000) -> tuple[str, dict]:
        raise NotImplementedError


def _post(url: str, headers: dict, payload: dict, retries: int = 4, timeout: int = 300) -> dict:
    data = json.dumps(payload).encode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers={"content-type": "application/json", **headers}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            last = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(2 ** attempt * 3); continue
            raise RuntimeError(last)
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e); time.sleep(2 ** attempt * 3)
    raise RuntimeError(f"request failed after {retries} attempts: {last}")


class Anthropic(Provider):
    name = "anthropic"

    def __init__(self, model: str | None = None):
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise SystemExit("ANTHROPIC_API_KEY is not set")
        self.model = model or "claude-sonnet-5"
        self.url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com") + "/v1/messages"

    def chat(self, messages, max_tokens=16000):
        r = _post(self.url, {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                  {"model": self.model, "max_tokens": max_tokens, "messages": messages})
        text = "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
        return text, {"model": r.get("model"), "in": r.get("usage", {}).get("input_tokens"), "out": r.get("usage", {}).get("output_tokens"), "stop": r.get("stop_reason")}


class OpenAICompatible(Provider):
    name = "openai"

    def __init__(self, model: str | None = None):
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise SystemExit("OPENAI_API_KEY is not set")
        if not model:
            raise SystemExit("--model is required for the openai provider")
        self.model = model
        self.url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"

    def chat(self, messages, max_tokens=16000):
        r = _post(self.url, {"authorization": f"Bearer {self.key}"}, {"model": self.model, "max_tokens": max_tokens, "messages": messages, "temperature": 0})
        ch = r["choices"][0]
        return ch["message"]["content"] or "", {"model": r.get("model"), "in": r.get("usage", {}).get("prompt_tokens"), "out": r.get("usage", {}).get("completion_tokens"), "stop": ch.get("finish_reason")}


class FromFiles(Provider):
    """Replies read from files: <dir>/<doc id>.txt for the first turn, <doc id>.fix<k>.txt for fix rounds."""
    name = "mock"

    def __init__(self, directory: pathlib.Path):
        self.dir = pathlib.Path(directory)
        self.doc_id = None

    def chat(self, messages, max_tokens=16000):
        from .prompt import REVIEW_MARK
        users = [m["content"] for m in messages if m["role"] == "user"]
        rev = next((i for i, c in enumerate(users) if c.startswith(REVIEW_MARK)), None)
        if rev is None:
            k = len(users) - 1
            p = self.dir / (f"{self.doc_id}.txt" if k == 0 else f"{self.doc_id}.fix{k}.txt")
        else:
            k = len(users) - 1 - rev
            p = self.dir / (f"{self.doc_id}.review.txt" if k == 0 else f"{self.doc_id}.review.fix{k}.txt")
        if not p.exists():
            raise FileNotFoundError(f"no reply file {p}")
        return p.read_text(), {"model": "files", "in": None, "out": None, "stop": "file"}


def make(provider: str, model: str | None = None, from_files: str | None = None) -> Provider:
    if provider == "anthropic":
        return Anthropic(model)
    if provider == "openai":
        return OpenAICompatible(model)
    if provider == "mock":
        if not from_files:
            raise SystemExit("--from-files <dir> is required for the mock provider")
        return FromFiles(pathlib.Path(from_files))
    raise SystemExit(f"unknown provider {provider}")
