#!/usr/bin/env python3
"""Block 6, the routed message, then the 14B's confuser block, in one long-lived process (README, amendment of 23 October
2026: block 6 runs before the 14B's confuser block). One local model at a time on this box: block 6 on Llama 3.2 3B, Qwen
7B and Qwen 14B in that order (run.py orders the models by MODEL_ORDER), then the confuser block on Qwen 14B resumes from
where it stopped. run.py skips chains that have turns.json, so this can be started again after an interruption.

  nohup python3 tools/block6_sequence.py >> results/main_run_local.log 2>&1 &
"""
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*args):
    print(f"== block6_sequence: run.py --exclude=-s,-p {' '.join(args)}, {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}", flush=True)
    subprocess.run([sys.executable, "tools/run.py", "--exclude=-s,-p", *args], cwd=ROOT)


run("--models", "llama3b,qwen7b,qwen14b", "--only=B6-")
run("--models", "qwen14b", "--only=B3-")
print(f"== block6_sequence finished {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}", flush=True)
