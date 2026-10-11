#!/usr/bin/env bash
# The weak receiver's run on gpt-5.4-mini, as registered: the pilot, its gate, then the design. Needs OPENAI_API_KEY in the
# environment; writes the key nowhere. Run from research/tool-prepare. Each step is skipped once its trials have run, so the
# script can be restarted. Grading and the summaries follow; the write-up is by hand.
set -euo pipefail
JOBS="${JOBS:-4}"
cd "$(dirname "$0")/.."
: "${OPENAI_API_KEY:?OPENAI_API_KEY is not set; add it to the environment (never to a file in the repository)}"
mkdir -p results
echo "== pilot: block 1, arms C and Q, one repeat (86 trials, ids -pg)"
python3 tools/run_api.py --only=-pg --jobs "$JOBS" | tee -a results/pilot_gpt54mini.log
python3 tools/grade.py --only=-pg
python3 tools/analyse.py --tag pilot-gpt54mini --only=-pg > /dev/null
if ! python3 tools/gate.py results/pilot-gpt54mini/summary.json; then
  echo "the pilot gate is not met; the design does not run. Report the pilot as it stands."; exit 2
fi
echo "== the design: 1,014 trials on gpt-5.4-mini"
python3 tools/run_api.py --only gpt54mini --exclude=-pg,-p,-w --jobs "$JOBS" | tee -a results/main_run_gpt54mini.log
python3 tools/grade.py --only gpt54mini
python3 tools/analyse.py --exclude=-p,-w,-pg
echo "done: results/summary.json carries both receivers; write up, regenerate the page (tools/site_page.py, app/tools/stamp.py), run the app tests"
