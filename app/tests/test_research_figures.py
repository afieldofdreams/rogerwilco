"""Every figure on a generated research page is read from the study's results JSON, never typed.

A page carries each number as <span data-fig="name">value</span>; this test recomputes the figures from the study's
results/summary.json with the study's own generator and asserts the committed page matches. Studies 6, 7, 8 and 9 generate their
pages this way. Skipped for a study whose results or page are not in the checkout. A second test asserts that each results JSON
holds exactly the graded trials of the run it names, so a page cannot carry figures from the wrong trials and still match.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
STUDIES = [("plan-readback", "plan-readback.html"), ("tool-prepare", "tool-prepare.html"), ("chain", "chain.html"), ("breaking", "breaking.html")]


@pytest.mark.parametrize("folder,page_name", STUDIES)
def test_page_figures_match_results(folder, page_name):
    study = REPO / "research" / folder
    page_path = REPO / "app" / "static" / "research" / page_name
    if not (study / "results" / "summary.json").exists() or not page_path.exists():
        pytest.skip(f"{folder}: results or page not in this checkout")
    sys.path.insert(0, str(study / "tools"))
    try:
        spec = importlib.util.spec_from_file_location(f"site_page_{folder.replace('-', '_')}", study / "tools" / "site_page.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        want = mod.figures()
    finally:
        sys.path.remove(str(study / "tools"))
        for name in ("common", "analyse", "site_text"):
            sys.modules.pop(name, None)
    page = page_path.read_text()
    got = dict(re.findall(r'<span data-fig="([^"]+)">([^<]*)</span>', page))
    assert got, "the page carries no data-fig spans"
    wrong = {k: (v, want.get(k)) for k, v in got.items() if want.get(k) != v}
    assert not wrong, f"figures on the page differ from the results JSON: {wrong}"


# ---------------------------------------------------------------- the JSON holds the trials of the run it names
# A results JSON is built by a study's analyse.py from the grade files under trials/, selected by the id's suffix: the main run's
# ids end in the repeat number, a pilot's in its tag. A substring filter once swept 454 other trials into study 7's pilot summary
# and the page then carried a 520-trial pilot that never ran; the figure test above passed, because the page matched the JSON.
# So: every row id matches the run's pattern, and the ids are exactly the graded trials with that pattern, less any excluded by name.
RUNS = [
    ("plan-readback", "results/summary.json", r"-(sonnet|haiku)-r\d+$"),
    ("plan-readback", "results/api/summary.json", r"-(gpt55|gpt54mini)-r\d+$"),
    ("plan-readback", "results/extension/summary.json", r"-x$"),
    ("tool-prepare", "results/summary.json", r"-(haiku|gpt54mini)-r\d+$"),
    ("tool-prepare", "results/pilot/summary.json", r"-p$"),
    ("tool-prepare", "results/pilot-gpt54mini/summary.json", r"-pg$"),
    ("tool-prepare", "results/pilot-haiku45/summary.json", r"-w$"),
    ("chain", "results/summary.json", r"-k\d-r\d+$"),
    ("breaking", "results/summary.json", r"-k\d-r\d+$"),
]


@pytest.mark.parametrize("folder,results,pattern", RUNS)
def test_results_hold_the_trials_of_their_run(folder, results, pattern):
    study = REPO / "research" / folder
    path = study / results
    if not path.exists():
        pytest.skip(f"{folder}: {results} not in this checkout")
    ids = [r["id"] for r in json.loads(path.read_text())["rows"]]
    assert ids, f"{results} carries no rows"
    pat = re.compile(pattern)
    strays = [i for i in ids if not pat.search(i)]
    assert not strays, f"{folder}/{results}: {len(strays)} ids outside the run, e.g. {strays[:3]}"
    trials = study / "trials"
    if not trials.is_dir():
        pytest.skip(f"{folder}: trials/ not in this checkout")
    excluded = set()
    ex = study / "results" / "excluded.json"
    if ex.exists():
        excluded = set(json.loads(ex.read_text()))
    graded = {d.name for d in trials.iterdir() if pat.search(d.name) and (d / "grade.json").exists()} - excluded
    assert set(ids) == graded, (f"{folder}/{results}: {len(set(ids) - graded)} rows without a graded trial, "
                                f"{len(graded - set(ids))} graded trials missing, e.g. {sorted(graded - set(ids))[:3]}")
