#!/usr/bin/env python3
"""Write results/manifest.json: the commit the main run is frozen at, the models as the API names them, the runner, the tokenizer.

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


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--note", default="")
    a = ap.parse_args(argv)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(C.REPO), capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "research/chain/tools", "research/chain/data", "research/chain/README.md"],
                           cwd=str(C.REPO), capture_output=True, text=True).stdout.strip()
    cli = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    seen = set()
    for m in C.TRIALS.glob("*/manifest.json"):
        seen.update(json.loads(m.read_text()).get("models_seen") or [])
    C.RESULTS.mkdir(exist_ok=True)
    C.write_json(C.RESULTS / "manifest.json", {
        "frozen_at": head, "tools_data_readme_clean_at_freeze": not dirty, "frozen_on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runner": f"claude -p {cli}", "receivers": dict(C.MODELS), "model_ids_seen_in_pilots": sorted(seen), "judge": None,
        "tokenizer": C.TOKENIZER, "codec": "tools/frozen/scripts/rogerwilco.py and tools/frozen/profiles/, see tools/frozen/README.md", "note": a.note,
    })
    print((C.RESULTS / "manifest.json").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
