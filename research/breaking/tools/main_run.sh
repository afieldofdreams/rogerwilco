#!/usr/bin/env bash
# The main run's local driver: blocks 1 and 5 at one repeat on every local model in order, then blocks 3, 2 and 4 at one
# repeat in the same order (the sizing amendment of 22 October 2026). run.py skips chains that already have turns.json,
# so the script can be started again after an interruption and carries on where it stopped.
#   setsid nohup bash tools/main_run.sh > results/main_run_local.out 2>&1 &
set -u
cd "$(dirname "$0")/.."
LOG=results/main_run_local.log
MODELS="qwen15 qwen3b llama3b qwen7b"
echo "== main run, local models, started $(date -u +%FT%TZ)" >> "$LOG"
for m in $MODELS; do
  echo "== blocks 1 and 5: $m, $(date -u +%FT%TZ)" >> "$LOG"
  python3 tools/run.py --exclude=-s,-p --models "$m" >> "$LOG" 2>&1
done
echo "== building blocks 3, 2 and 4 at one repeat for the local models, $(date -u +%FT%TZ)" >> "$LOG"
python3 tools/build.py --blocks 3,2,4 --repeats 1 --models qwen15,qwen3b,llama3b,qwen7b >> "$LOG" 2>&1
for m in $MODELS; do
  echo "== blocks 3, 2 and 4: $m, $(date -u +%FT%TZ)" >> "$LOG"
  python3 tools/run.py --exclude=-s,-p --models "$m" >> "$LOG" 2>&1
done
echo "== main run, local models, finished $(date -u +%FT%TZ)" >> "$LOG"
