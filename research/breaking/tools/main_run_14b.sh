#!/usr/bin/env bash
# Qwen2.5-14B, added after the freeze (README, amendments after the freeze): blocks 1 and 5 at one repeat, then blocks 3, 2
# and 4 at one repeat. Started after tools/main_run.sh has finished, since the box runs one local model at a time.
# run.py skips chains that already have turns.json, so the script can be started again after an interruption.
set -u
cd "$(dirname "$0")/.."
LOG=results/main_run_local.log
if [ ! -f /home/user/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf ]; then
  echo "== qwen14b: model file not present, $(date -u +%FT%TZ)" >> "$LOG"; exit 1
fi
echo "== blocks 1 and 5: qwen14b, $(date -u +%FT%TZ)" >> "$LOG"
python3 tools/run.py --exclude=-s,-p --models qwen14b >> "$LOG" 2>&1
echo "== building blocks 3, 2 and 4 at one repeat for qwen14b, $(date -u +%FT%TZ)" >> "$LOG"
python3 tools/build.py --blocks 3,2,4 --repeats 1 --models qwen14b >> "$LOG" 2>&1
echo "== blocks 3, 2 and 4: qwen14b, $(date -u +%FT%TZ)" >> "$LOG"
python3 tools/run.py --exclude=-s,-p --models qwen14b >> "$LOG" 2>&1
echo "== qwen14b finished $(date -u +%FT%TZ)" >> "$LOG"
