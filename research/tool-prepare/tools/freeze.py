#!/usr/bin/env python3
"""Write results/manifest.json: the commit the tools, data and protocol are frozen at, before the main run.

  python3 tools/freeze.py [--note TEXT]
"""
from __future__ import annotations

import argparse
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
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "research/tool-prepare/tools", "research/tool-prepare/data", "research/tool-prepare/README.md"],
                           cwd=str(C.REPO), capture_output=True, text=True).stdout.strip()
    cli = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip().split()[0]
    C.RESULTS.mkdir(exist_ok=True)
    C.write_json(C.RESULTS / "manifest.json", {
        "frozen_at": head, "tools_data_readme_clean_at_freeze": not dirty, "frozen_on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runner": "claude -p " + cli, "receivers": {"haiku": "claude-haiku-5-5"}, "judge": None, "tokenizer": "tiktoken o200k_base",
        "codec": "tools/frozen/scripts/rogerwilco.py, study 6's freeze at 1bf4f5f3351c827b0947138eb6d8b6fc2938ee24", "note": a.note,
    })
    print((C.RESULTS / "manifest.json").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
