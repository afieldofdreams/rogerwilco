"""Every figure on a generated research page is read from the study's results JSON, never typed.

A page carries each number as <span data-fig="name">value</span>; this test recomputes the figures from the study's
results/summary.json with the study's own generator and asserts the committed page matches. Studies 6, 7, 8 and 9 generate their
pages this way. Skipped for a study whose results or page are not in the checkout.
"""
import importlib.util
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
