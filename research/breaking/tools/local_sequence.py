#!/usr/bin/env python3
"""The local models' run order, in one long-lived process: blocks 1 and 5 for every model from the 3B up, largest
effect first, then the remaining blocks per model. run.py skips finished chains, so this can be started again."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run(*args):
    subprocess.run([sys.executable, "tools/run.py", "--exclude=-s,-p", *args], cwd=ROOT)
for m in ("qwen3b", "llama3b", "qwen7b", "qwen14b"):
    run("--models", m, "--only=B1-")
    run("--models", m, "--only=B5-")
for m in ("qwen15", "qwen3b", "llama3b", "qwen7b", "qwen14b"):
    run("--models", m)
