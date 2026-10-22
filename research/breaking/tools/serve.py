#!/usr/bin/env python3
"""The local models: a GGUF file loaded in-process through llama_cpp (one model at a time, four threads, temperature 0),
and an optional minimal OpenAI-compatible server over it for anything that talks to RW_BASE_URL.

  python3 tools/serve.py start qwen15 [--port 8080]     # serves /v1/chat/completions and /v1/models at 127.0.0.1:<port>; writes results/.serve/<port>.pid
  python3 tools/serve.py stop [--port 8080]
  python3 tools/serve.py hash qwen15                    # the model file's sha256

run.py uses LocalModel directly (no server): one process, one model loaded, one chain at a time. The server exists so
that research/harness/llm.py's compat: adapter can be pointed at the same model (run.py --server http://127.0.0.1:8080/v1)
and for a look by hand. llama_cpp.server itself needs packages this environment does not have, so this stands in for it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

N_CTX = int(os.environ.get("RW_N_CTX", "12288"))   # 8192 was registered; the payer in R or C with a re-issue and long replies can pass it in Qwen tokens, so 12288 (recorded in the pilot README)
N_THREADS = int(os.environ.get("RW_N_THREADS", "4"))
TEMPERATURE = 0.0
MAX_TOKENS = int(os.environ.get("RW_MAX_TOKENS", "500"))     # a line is under 100 tokens, a prose message under 300; the act block under 120
_HASHES: dict[str, str] = {}


def model_file(alias: str) -> Path:
    m = C.MODELS[alias]
    if m["kind"] != "local":
        raise ValueError(f"{alias} is not a local model")
    return C.MODELS_DIR / m["file"]


def sha256_of(path: Path) -> str:
    key = str(path)
    if key not in _HASHES:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 24), b""):
                h.update(chunk)
        _HASHES[key] = h.hexdigest()
    return _HASHES[key]


def llama_version() -> str:
    import llama_cpp
    return getattr(llama_cpp, "__version__", "?")


class LocalModel:
    """One loaded GGUF. chat(messages) -> {"text", "usage": {prompt_tokens, completion_tokens}, "finish_reason", "seconds"}."""

    def __init__(self, alias: str, n_ctx: int = N_CTX, n_threads: int = N_THREADS):
        import llama_cpp
        self.alias = alias
        self.path = model_file(alias)
        self.n_ctx, self.n_threads = n_ctx, n_threads
        t0 = time.time()
        self.llm = llama_cpp.Llama(model_path=str(self.path), n_ctx=n_ctx, n_threads=n_threads, n_batch=512, verbose=False)
        self.load_seconds = round(time.time() - t0, 1)
        self.lock = threading.Lock()

    def describe(self) -> dict:
        return {"alias": self.alias, "name": C.MODELS[self.alias]["name"], "file": self.path.name, "sha256": sha256_of(self.path),
                "n_ctx": self.n_ctx, "n_threads": self.n_threads, "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
                "llama_cpp": llama_version(), "reported_name": self.llm.metadata.get("general.name")}

    def count(self, text: str) -> int:
        return len(self.llm.tokenize(text.encode("utf-8"), add_bos=False, special=True))

    def chat(self, messages: list[dict], max_tokens: int = MAX_TOKENS) -> dict:
        t0 = time.time()
        with self.lock:
            r = self.llm.create_chat_completion(messages=messages, temperature=TEMPERATURE, max_tokens=max_tokens)
        choice = r["choices"][0]
        return {"text": (choice["message"].get("content") or "").strip(), "usage": dict(r.get("usage") or {}),
                "finish_reason": choice.get("finish_reason"), "seconds": round(time.time() - t0, 2)}

    def close(self) -> None:
        self.llm = None


# ----------------------------------------------------------------------------------------------------- the server

def serve(alias: str, port: int) -> None:
    model = LocalModel(alias)
    desc = model.describe()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, obj: dict) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                self._send(200, {"object": "list", "data": [{"id": alias, "object": "model", "sha256": desc["sha256"], "file": desc["file"]}]})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self.path.rstrip("/").endswith("/chat/completions"):
                self._send(404, {"error": "not found"}); return
            n = int(self.headers.get("Content-Length", "0"))
            try:
                req = json.loads(self.rfile.read(n))
            except ValueError:
                self._send(400, {"error": {"message": "bad json"}}); return
            r = model.chat(req.get("messages") or [], int(req.get("max_tokens") or MAX_TOKENS))
            self._send(200, {"id": f"local-{int(time.time() * 1000)}", "object": "chat.completion", "model": alias,
                             "choices": [{"index": 0, "message": {"role": "assistant", "content": r["text"]}, "finish_reason": r["finish_reason"]}],
                             "usage": r["usage"], "seconds": r["seconds"]})

    pid_dir = C.RESULTS / ".serve"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / f"{port}.pid").write_text(json.dumps({"pid": os.getpid(), "alias": alias, **desc}))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"serving {alias} at http://127.0.0.1:{port}/v1 (pid {os.getpid()}); loaded in {model.load_seconds}s", flush=True)
    try:
        httpd.serve_forever()
    finally:
        (pid_dir / f"{port}.pid").unlink(missing_ok=True)


def stop(port: int) -> None:
    p = C.RESULTS / ".serve" / f"{port}.pid"
    if not p.exists():
        print("nothing is served on that port"); return
    pid = json.loads(p.read_text())["pid"]
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"stopped pid {pid}")
    except ProcessLookupError:
        print(f"pid {pid} was already gone")
    p.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start"); p.add_argument("alias", choices=C.LOCAL_MODELS); p.add_argument("--port", type=int, default=8080)
    p = sub.add_parser("stop"); p.add_argument("--port", type=int, default=8080)
    p = sub.add_parser("hash"); p.add_argument("alias", choices=C.LOCAL_MODELS)
    a = ap.parse_args(argv)
    if a.cmd == "start":
        serve(a.alias, a.port)
    elif a.cmd == "stop":
        stop(a.port)
    else:
        print(sha256_of(model_file(a.alias)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
