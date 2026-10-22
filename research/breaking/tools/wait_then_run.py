#!/usr/bin/env python3
"""Wait for a running run.py (by pid) to exit, then run the rest of the local sequence in this one process:
every unfinished chain of the models named, in MODEL_ORDER, one chain at a time. Started so that it outlives the shell."""
import os, subprocess, sys, time
pid = int(sys.argv[1]); models = sys.argv[2]
while True:
    try:
        os.kill(pid, 0)
    except OSError:
        break
    time.sleep(30)
subprocess.run([sys.executable, "tools/run.py", "--exclude=-s,-p", "--models", models], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
