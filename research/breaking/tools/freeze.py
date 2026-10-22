#!/usr/bin/env python3
"""Write results/manifest.json: the commit the main run is frozen at, the models as they run (file hashes for the local
ones, the API's ids for the anchors), the runner, the sampling, the tokenizer.

  python3 tools/freeze.py [--note TEXT]

Run it at the commit the main run starts from, after the pilot's amendments are recorded in README.md. The codec and the
profiles in tools/frozen/ are the copies every check loads; this records which commit they were taken at.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import serve as S  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--note", default="")
    a = ap.parse_args(argv)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(C.REPO), capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "research/breaking/tools", "research/breaking/data", "research/breaking/README.md"],
                           cwd=str(C.REPO), capture_output=True, text=True).stdout.strip()
    try:
        cli = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    except Exception:  # noqa: BLE001
        cli = "?"
    seen = set()
    for m in C.TRIALS.glob("*/manifest.json"):
        seen.update(json.loads(m.read_text()).get("models_seen") or [])
    local = {}
    for alias in C.LOCAL_MODELS:
        if C.model_available(alias):
            f = S.model_file(alias)
            local[alias] = {"name": C.MODELS[alias]["name"], "file": f.name, "sha256": S.sha256_of(f), "bytes": f.stat().st_size}
    C.RESULTS.mkdir(exist_ok=True)
    C.write_json(C.RESULTS / "manifest.json", {
        "frozen_at": head, "tools_data_readme_clean_at_freeze": not dirty, "frozen_on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runner": {"local": f"llama_cpp {S.llama_version()} in-process, n_ctx {S.N_CTX}, n_threads {S.N_THREADS}, temperature {S.TEMPERATURE}, max_tokens {S.MAX_TOKENS}",
                   "anchors": f"claude -p {cli}, text only, no tools, provider defaults"},
        "local_models": local, "anchors": {a: C.MODELS[a]["id"] for a in C.ANCHORS}, "model_ids_seen_in_pilots": sorted(seen), "judge": None,
        "tokenizer": C.TOKENIZER, "codec": "tools/frozen/scripts/rogerwilco.py and tools/frozen/profiles/, see tools/frozen/README.md", "note": a.note,
    })
    print((C.RESULTS / "manifest.json").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
