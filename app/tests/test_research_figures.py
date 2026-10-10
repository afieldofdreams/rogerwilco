"""Every figure on the study 6 research page is read from the study's results JSON, never typed.

The page carries each number as <span data-fig="name">value</span>; this test recomputes the figures from
research/plan-readback/results/summary.json with the study's own generator and asserts the committed page matches.
Skipped when the research folder or the page is not in the checkout.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
STUDY = REPO / "research" / "plan-readback"
PAGE = REPO / "app" / "static" / "research" / "plan-readback.html"


@pytest.mark.skipif(not (STUDY / "results" / "summary.json").exists() or not PAGE.exists(), reason="study 6 results or page not in this checkout")
def test_page_figures_match_results():
    sys.path.insert(0, str(STUDY / "tools"))
    spec = importlib.util.spec_from_file_location("site_page", STUDY / "tools" / "site_page.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    want = mod.figures()
    page = PAGE.read_text()
    got = dict(re.findall(r'<span data-fig="([^"]+)">([^<]*)</span>', page))
    assert got, "the page carries no data-fig spans"
    wrong = {k: (v, want.get(k)) for k, v in got.items() if want.get(k) != v}
    assert not wrong, f"figures on the page differ from the results JSON: {wrong}"
