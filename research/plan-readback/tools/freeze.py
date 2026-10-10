#!/usr/bin/env python3
"""Write results/manifest.json: the commit the main run is frozen at, the models as the API names them, the runner, the level.

  python3 tools/freeze.py [--level 0] [--note TEXT]
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


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--level", type=int, default=0); ap.add_argument("--note", default="")
    a = ap.parse_args(argv)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(C.ROOT), capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(C.ROOT / "tools"), str(C.ROOT / "data"), str(C.ROOT / "README.md")],
                           cwd=str(C.ROOT), capture_output=True, text=True).stdout.strip()
    cli = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    seen = set()
    for m in C.TRIALS.glob("*/manifest.json"):
        seen.update(json.loads(m.read_text()).get("models_seen") or [])
    manifest = {
        "frozen_at": commit, "tools_data_readme_clean_at_freeze": not dirty, "frozen_on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runner": f"claude -p {cli}", "receivers": {"sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"},
        "judge": "claude-sonnet-5-5", "model_ids_seen_in_pilots": sorted(seen), "harden_level": a.level,
        "tokenizer": "tiktoken o200k_base", "codec": "rogerwilco/scripts/rogerwilco.py at frozen_at", "note": a.note,
    }
    C.RESULTS.mkdir(exist_ok=True)
    C.write_json(C.RESULTS / "manifest.json", manifest)
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
