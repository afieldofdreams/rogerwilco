"""Tests for the rogerwilco app. From the repo root:  python -m pytest app/tests

This folder is app/ in the repo. It is loaded here as the package `app` whatever it is called on disk, so the tests
also run from a checkout under another name.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP_DIR = Path(__file__).resolve().parents[1]


def _package_source(dir_path: Path) -> str:
    """Python source that registers dir_path as the package `app`."""
    return (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('app', {str(dir_path / '__init__.py')!r}, "
        f"submodule_search_locations=[{str(dir_path)!r}])\n"
        "pkg = importlib.util.module_from_spec(spec)\n"
        "sys.modules['app'] = pkg\n"
        "spec.loader.exec_module(pkg)\n"
    )


if "app" not in sys.modules:
    exec(_package_source(APP_DIR), {})

from app import service  # noqa: E402
from app.main import create_app  # noqa: E402

# The worked exchange from SKILL.md and SPEC.md.
HO = ("RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 pri=2 conf=M keep=research "
      "// hero copy, 120 words, no em dashes")
RB = "RW1 RB writer-01 re=research-01 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 h=c40bba4360dc"
HO_ACC = ("RW1 HO research-03 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 rb=acc keys=len+tone+must+no "
          "art=url:https://example.com/brief // hero copy, 120 words, plain tone, no em dashes, must name the reader's Monday problem")
RB_ACC = ("RW1 RB writer-05 re=research-03 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 "
          "acc=len:120w+tone:plain+must:monday-problem+no:em-dash+fmt:md do=copy // landing hero, 120 words, plain")
EXPECT = "len:120w+tone:plain+no:em-dash+must:monday-problem"
PAY_HO = "RW1 HO extractor-01 p=pay from=extractor to=reconciler item=inv:INV-000491 ask=RECON amt=5400.00 cur=GBP"

MCP_HEADERS = {"Accept": "application/json, text/event-stream"}


@pytest.fixture(scope="module")
def client():
    # The with block runs the app's lifespan, which the MCP endpoint needs.
    with TestClient(create_app()) as c:
        yield c


def post(client, path, **body):
    return client.post(path, json=body)


# ------------------------------------------------------------------ healthz

def test_healthz(client, monkeypatch):
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "version": "RW1", "commit": "unknown"}
    monkeypatch.setenv("GIT_COMMIT", "abc1234")
    assert client.get("/healthz").json()["commit"] == "abc1234"
    monkeypatch.setenv("GIT_COMMIT", "")          # an empty build arg must not show as an empty commit
    assert client.get("/healthz").json()["commit"] == "unknown"


# ------------------------------------------------------------------ validate

def test_validate_ok(client):
    r = post(client, "/validate", line=HO, profile=None)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["errors"] == [] and body["warnings"] == []
    msg = body["message"]
    assert (msg["v"], msg["type"], msg["id"], msg["re"]) == ("RW1", "HO", "research-01", None)
    assert (msg["from"], msg["to"], msg["item"]) == ("research", "writer", "gh:crox/site#42")
    assert msg["slots"] == {"ask": "DRAFT", "due": "20261002", "pri": 2, "conf": "M", "keep": ["research"]}
    assert msg["tail"] == "hero copy, 120 words, no em dashes"


def test_validate_error(client):
    r = post(client, "/validate", line="RW1 HO research-01 from=research to=writer ask=WRITE")
    assert r.status_code == 200                       # an invalid line is a normal answer, not an HTTP error
    body = r.json()
    assert body["ok"] is False
    assert any("HO requires item" in e for e in body["errors"])
    assert any("ask=WRITE" in e and "not a known ask code" in e for e in body["errors"])


def test_validate_warnings(client):
    body = post(client, "/validate", line="RW1 HO a-1 from=a to=a item=x:1 ask=DRAFT foo=1").json()
    assert body["ok"] is True
    assert any("same agent" in w for w in body["warnings"])
    assert any("unknown key 'foo'" in w for w in body["warnings"])


def test_validate_profiles(client):
    assert post(client, "/validate", line=PAY_HO).json()["ok"] is True                    # p= in the line picks it
    assert post(client, "/validate", line=PAY_HO, profile="pay").json()["ok"] is True
    core_only = post(client, "/validate", line=PAY_HO.replace(" p=pay", ""), profile="core").json()
    assert core_only["ok"] is False and any("RECON" in e for e in core_only["errors"])   # RECON is a pay code
    for empty in (None, "", "  ", "core"):
        assert post(client, "/validate", line=HO, profile=empty).json()["ok"] is True    # all mean the core vocabulary


@pytest.mark.parametrize("profile", ["nope", "../profiles/pay", "..", "pay.json", "/etc/passwd", "a" * 100])
def test_bad_profile_names_are_400(client, profile):
    r = post(client, "/validate", line=HO, profile=profile)
    assert r.status_code == 400
    assert list(r.json()) == ["error"]


def test_p_token_cannot_reach_outside_profiles(client, tmp_path):
    # The codec builds profiles/<name>.json from a p= token. A name that climbs out of profiles/ would load any .json
    # file as a profile, so the app must refuse it, in a line and in JSON.
    (tmp_path / "outside.json").write_text(json.dumps({"enums": {"x": {"A": "b"}}}))
    name = os.path.relpath(tmp_path / "outside", service.rw.PROFILES)
    body = post(client, "/validate", line=f"RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT p={name}").json()
    assert body["ok"] is False and any("invalid profile name" in e for e in body["errors"])
    slots = {"ask": "DRAFT", "p": name}
    r = post(client, "/from-json", message={"type": "HO", "id": "a-1", "from": "a", "to": "b", "item": "x:1", "slots": slots})
    assert r.status_code == 400 and "invalid profile name" in r.json()["error"]


# ------------------------------------------------------------------ check-rb

def test_check_rb_pass(client):
    r = post(client, "/check-rb", ho=HO, rb=RB)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "problems": [], "notes": []}


def test_check_rb_mismatch(client):
    ho = "RW1 HO ops-03 from=ops to=builder item=jira:OPS-77 ask=FIX due=20261001"
    rb = "RW1 RB builder-05 re=ops-03 from=builder to=ops item=jira:OPS-77 ask=BUILD due=20261001"
    body = post(client, "/check-rb", ho=ho, rb=rb).json()
    assert body["ok"] is False
    assert body["problems"] == ["tier3 echo: ask mismatch: HO FIX vs RB BUILD"]


@pytest.mark.parametrize("rb, tier", [
    (RB.replace("re=research-01", "re=research-09"), "tier1 receipt"),
    (RB.replace("RB writer-01 re=research-01 from=writer to=research", "RB someone-01 re=research-01 from=someone to=research"), "tier1 receipt"),
    (RB.replace("h=c40bba4360dc", "h=000000000000"), "tier2 integrity"),
    (RB.replace(" due=20261002", ""), "tier3 echo"),
])
def test_check_rb_names_the_failing_tier(client, rb, tier):
    body = post(client, "/check-rb", ho=HO, rb=rb).json()
    assert body["ok"] is False
    assert any(p.startswith(tier) for p in body["problems"]), body


def test_check_rb_unparseable_lines(client):
    body = post(client, "/check-rb", ho="RW1 HO a-1 from=a to=b", rb=RB).json()
    assert body["ok"] is False and body["problems"][0].startswith("HO: ")
    body = post(client, "/check-rb", ho=HO, rb=HO).json()          # the second line has to be an RB
    assert body["ok"] is False and "expected RB" in body["problems"][0]


def test_check_rb_comprehension(client):
    body = post(client, "/check-rb", ho=HO_ACC, rb=RB_ACC, expect_acc=EXPECT).json()
    assert body["ok"] is True
    assert body["notes"] == ["assumption: receiver added fmt:md; confirm or correct"]
    as_list = post(client, "/check-rb", ho=HO_ACC, rb=RB_ACC, expect_acc=EXPECT.split("+")).json()
    assert as_list == body                                          # a list of tokens works as well as a string
    wrong = post(client, "/check-rb", ho=HO_ACC, rb=RB_ACC.replace("len:120w", "len:150w"), expect_acc=EXPECT).json()
    assert wrong["ok"] is False and "contradiction on len" in wrong["problems"][0]
    gap = post(client, "/check-rb", ho=HO_ACC, rb=RB_ACC, expect_acc=EXPECT + "+src:brief").json()
    assert gap["ok"] is False and "did not derive src:brief" in gap["problems"][0]
    no_acc = post(client, "/check-rb", ho=HO_ACC, rb=RB_ACC.replace("acc=", "x_acc=")).json()
    assert no_acc["ok"] is False and "carries no acc=" in no_acc["problems"][0]
    unchecked = post(client, "/check-rb", ho=HO_ACC, rb=RB_ACC).json()
    assert unchecked["ok"] is True and "not compared" in unchecked["notes"][0]


# ------------------------------------------------------------------ check-ho and check-dn: before and after an irreversible act

PAY_EXEC_HO = ("RW1 HO scheduler-1 p=pay from=scheduler to=payer item=inv:MD-2026-057 ask=PAY rb=exec sup=marlow amt=5400.00 "
               "cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929")
PAY_RECORD = {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP",
              "kind": "GROSS", "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}
PAY_DN = ("RW1 DN payer-2 re=scheduler-1 p=pay from=payer to=scheduler item=inv:MD-2026-057 out=OK sup=marlow amt=5400.00 "
          "cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929 // as executed, from the payment tool")


def test_check_ho(client):
    assert post(client, "/check-ho", ho=PAY_EXEC_HO, record=PAY_RECORD, profile="pay").json() == {"ok": True, "problems": [], "notes": []}
    digit = post(client, "/check-ho", ho=PAY_EXEC_HO.replace("61102938", "61102983"), record=PAY_RECORD, profile="pay").json()
    assert digit["ok"] is False and digit["problems"] == ["record: acct mismatch: record 40-12-88/61102938 vs HO 40-12-88/61102983"]
    level = post(client, "/check-ho", ho=PAY_EXEC_HO.replace("rb=exec", "rb=all"), record=PAY_RECORD, profile="pay").json()
    assert level["problems"] == ["ask PAY is an irreversible act under profile pay: the HO must ask rb=exec"]
    missing = post(client, "/check-ho", ho=PAY_EXEC_HO.replace(" apref=FD-0929", ""), record=PAY_RECORD, profile="pay").json()
    assert missing["problems"] == ["record: HO does not carry apref (record has apref=FD-0929)"]
    partial = post(client, "/check-ho", ho=PAY_EXEC_HO, record={"amt": "5400.00"}, profile="pay").json()
    assert partial["ok"] is True and any(n.startswith("acct=") for n in partial["notes"])


@pytest.mark.parametrize("body, needle", [
    ({"ho": PAY_EXEC_HO, "record": "amt=5400.00", "profile": "pay"}, "record"),
    ({"ho": PAY_EXEC_HO, "record": {"amt": {"x": 1}}, "profile": "pay"}, "record value"),
])
def test_check_ho_refuses_bad_requests(client, body, needle):
    r = client.post("/check-ho", json=body)
    assert r.status_code in (400, 422), r.text
    assert needle in r.text
    # an HO that does not parse is a result, not a request error, as it is for check-rb
    body = post(client, "/check-ho", ho="RW1 HO a-1 from=a to=b", record={}, profile="pay").json()
    assert body["ok"] is False and body["problems"][0].startswith("HO:")


def test_check_dn(client):
    assert post(client, "/check-dn", ho=PAY_EXEC_HO, dn=PAY_DN, profile="pay").json() == {"ok": True, "problems": [], "notes": []}
    wrong = post(client, "/check-dn", ho=PAY_EXEC_HO, dn=PAY_DN.replace("amt=5400.00", "amt=5100.00"), profile="pay").json()
    assert wrong["problems"] == ["executed: amt mismatch: plan 5400.00 vs DN 5100.00"]
    gone = post(client, "/check-dn", ho=PAY_EXEC_HO, dn=PAY_DN.replace(" acct=40-12-88/61102938", ""), profile="pay").json()
    assert gone["problems"] == ["executed: DN does not carry acct, which the act used"]
    noop = post(client, "/check-dn", ho=PAY_EXEC_HO, profile="pay",
                dn="RW1 DN payer-2 re=scheduler-1 p=pay from=payer to=scheduler item=inv:MD-2026-057 out=NOOP // already paid").json()
    assert noop == {"ok": True, "problems": [], "notes": []}
    # a bank change: the account being replaced is resolved by the receiver, read back, and then reported as executed
    ho = ("RW1 HO scheduler-1 p=pay from=scheduler to=payer item=sup:evergreen ask=CHGBANK rb=exec sup=evergreen "
          "acct=60-83-71/44019482 eff=20261003 apref=FD-0926")
    rb = post(client, "/make-rb", ho=ho, id="payer-1", profile="pay").json()["rb"] + " prev=30-98-71/22019483"
    assert post(client, "/check-rb", ho=ho, rb=rb, profile="pay").json()["ok"] is True
    dn = ("RW1 DN payer-2 re=scheduler-1 p=pay from=payer to=scheduler item=sup:evergreen out=OK sup=evergreen "
          "acct=60-83-71/44019482 eff=20261003 apref=FD-0926 prev=30-98-71/22019483")
    assert post(client, "/check-dn", ho=ho, dn=dn, rb=rb, profile="pay").json() == {"ok": True, "problems": [], "notes": []}
    other = post(client, "/check-dn", ho=ho, dn=dn.replace("22019483", "22019484"), rb=rb, profile="pay").json()
    assert other["problems"] == ["executed: prev mismatch: plan 30-98-71/22019483 vs DN 30-98-71/22019484"]
    without = post(client, "/check-dn", ho=ho, dn=dn, profile="pay").json()
    assert without["ok"] is True and without["notes"] and "prev=" in without["notes"][0]
    unparsed = post(client, "/check-dn", ho=ho, dn=dn, rb=rb.replace("h=", "h=0"), profile="pay").json()
    assert unparsed["ok"] is False and "did not pass" in unparsed["problems"][0]


def test_check_ho_and_dn_via_mcp(client):
    assert call_tool(client, "check_ho", {"ho": PAY_EXEC_HO, "record": PAY_RECORD, "profile": "pay"})["structuredContent"]["ok"] is True
    res = call_tool(client, "check_dn", {"ho": PAY_EXEC_HO, "dn": PAY_DN.replace("amt=5400.00", "amt=5100.00"), "profile": "pay"})
    assert res["structuredContent"]["problems"] == ["executed: amt mismatch: plan 5400.00 vs DN 5100.00"]


# ------------------------------------------------------------------ make-rb, digest, JSON

def test_make_rb(client):
    r = post(client, "/make-rb", ho=HO, id="writer-01")
    assert r.status_code == 200
    assert r.json() == {"rb": RB}                                   # the readback printed in the spec, digest included
    assert post(client, "/check-rb", ho=HO, rb=r.json()["rb"]).json()["ok"] is True


def test_make_rb_options(client):
    rb = post(client, "/make-rb", ho=HO_ACC, id="writer-05", acc="len:120w+tone:plain", do="copy", hash=False).json()["rb"]
    assert "acc=len:120w+tone:plain" in rb and "do=copy" in rb and " h=" not in rb
    rb = post(client, "/make-rb", ho=PAY_HO, id="reconciler-01", profile="pay").json()["rb"]
    assert rb.startswith("RW1 RB reconciler-01 re=extractor-01 from=reconciler to=extractor") and "p=pay" in rb


@pytest.mark.parametrize("body, needle", [
    ({"ho": RB, "id": "writer-02"}, "needs an HO"),
    ({"ho": "RW1 HO a-1 from=a to=b ask=DRAFT", "id": "b-1"}, "HO requires item"),
    ({"ho": HO, "id": "not an id"}, "expected key=value"),
])
def test_make_rb_errors(client, body, needle):
    r = client.post("/make-rb", json=body)
    assert r.status_code == 400 and needle in r.json()["error"]


def test_digest(client):
    assert post(client, "/digest", line=HO).json() == {"digest": "c40bba4360dc"}
    r = post(client, "/digest", line="RW1 HO a-1 from=a to=b ask=DRAFT")
    assert r.status_code == 400 and "HO requires item" in r.json()["error"]


def test_json_round_trip(client):
    msg = post(client, "/to-json", line=HO).json()["message"]
    assert msg["slots"]["pri"] == 2 and msg["slots"]["keep"] == ["research"]
    assert post(client, "/from-json", message=msg).json() == {"line": HO}
    assert post(client, "/from-json", message=json.dumps(msg)).json() == {"line": HO}      # a JSON string works too
    assert post(client, "/from-json", message={k: v for k, v in msg.items() if k != "v"}).json() == {"line": HO}


def test_json_errors(client):
    r = post(client, "/to-json", line="RW1 HO a-1 from=a to=b ask=DRAFT")
    assert r.status_code == 400 and "HO requires item" in r.json()["error"]
    for message, needle in [
        ({"id": "a-1"}, "needs 'type'"),
        ({"type": "HO"}, "needs 'id'"),
        ("[1, 2]", "must be a JSON object"),
        ("{not json", "not valid JSON"),
        ({"type": 5, "id": "a-1"}, "needs 'type'"),
        ({"type": "HO", "id": "a-1", "slots": []}, "slots must be a JSON object"),
        ({"type": "HO", "id": "a-1", "slots": None}, "HO requires from"),          # null slots read as no slots
    ]:
        r = post(client, "/from-json", message=message)
        assert r.status_code == 400 and needle in r.json()["error"], (message, r.text)


def test_oversized_input_is_refused(client):
    r = post(client, "/validate", line="RW1 HO " + "a" * 5000)
    assert r.status_code == 400 and "limit" in r.json()["error"]
    assert post(client, "/check-rb", ho=HO, rb=RB, expect_acc="x:" * 600).status_code == 400


# ------------------------------------------------------------------ legend, profiles, docs

def test_legend(client):
    r = client.get("/legend", params={"profile": "pay"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert r.text.startswith("rogerwilco RW1.") and "Profile pay:" in r.text and "RECON" in r.text
    core = client.get("/legend", params={"profile": "core"})
    assert core.status_code == 200 and core.text == client.get("/legend").text and "RECON" not in core.text
    bad = client.get("/legend", params={"profile": "nope"})
    assert bad.status_code == 400 and "unknown profile" in bad.json()["error"]


def test_profiles(client):
    body = client.get("/profiles").json()
    assert body[0]["name"] == "core"
    assert {"core", "pform", "pay"} <= {p["name"] for p in body}
    assert all(p["description"] for p in body)


def test_spec_and_skill(client):
    spec = client.get("/spec")
    assert spec.status_code == 200 and spec.headers["content-type"].startswith("text/markdown")
    assert spec.text.startswith("# rogerwilco protocol")
    skill = client.get("/skill")
    assert skill.headers["content-type"].startswith("text/markdown") and "name: rogerwilco" in skill.text
    # A browser is offered text/plain, because it would save text/markdown instead of showing it.
    page = client.get("/spec", headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    assert page.headers["content-type"].startswith("text/plain") and page.text == spec.text
    assert "accept" in page.headers["vary"].lower()


def test_openapi_and_docs(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/healthz", "/validate", "/check-rb", "/check-ho", "/check-dn", "/make-rb", "/to-json", "/from-json",
                 "/digest", "/legend", "/profiles", "/spec", "/skill"):
        assert path in paths
    assert client.get("/docs").status_code == 200


# ------------------------------------------------------------------ the site

def test_index_page(client):
    r = client.get("/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    for href in ('href="/spec"', 'href="/skill"', 'href="/quickstart"', 'href="/lines"', 'href="/profiles"', 'href="/research"', 'href="/about"', 'href="https://crox.io"'):
        assert href in r.text
    assert 'class="site-head"' in r.text and '/static/site.css' in r.text


def test_home_page_lines_are_real(client):
    """The three lines on the home page validate under the pay profile, and the readback passes the sender's check."""
    html = (APP_DIR / "static" / "index.html").read_text(encoding="utf-8")
    lines = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r'<pre class="line">(.*?)</pre>', html, re.S)]
    assert len(lines) == 3 and [l.split()[1] for l in lines] == ["HO", "RB", "DN"]
    for line in lines:
        assert post(client, "/validate", line=line, profile="pay").json()["ok"] is True, line
    assert post(client, "/check-rb", ho=lines[0], rb=lines[1], profile="pay").json()["ok"] is True
    assert "Tenerife" in html and "1977" in html


def test_every_page_carries_the_same_header(client):
    pages = ["/", "/quickstart", "/demo", "/lines", "/about", "/research", "/research/readback"]
    heads = []
    for path in pages:
        text = client.get(path, headers={"Accept": "text/html"}).text
        start, end = text.index('<header class="site-head">'), text.index("</header>")
        heads.append(re.sub(r' aria-current="page"', "", text[start:end]))
        assert '<footer class="site-foot">' in text, path
    assert len(set(heads)) == 1
    assert client.get("/about").status_code == 200 and client.get("/static/site.css").headers["content-type"].startswith("text/css")


def test_demo_page_and_its_lines(client):
    """The demo page is served with its script, and the scripted exchange it plays passes the service's checks."""
    r = client.get("/demo")
    assert r.status_code == 200 and "Say it back" in r.text and '/static/demo.js' in r.text
    assert client.get("/static/demo.js").status_code == 200
    ho = ("RW1 HO scheduler-1 p=pay from=scheduler to=payer item=inv:MD-2026-057 ask=PAY rb=exec sup=marlow amt=5400.00 cur=GBP "
          "kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929 // approved run, 2 October")
    record = {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP", "kind": "GROSS",
              "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}
    assert post(client, "/check-ho", ho=ho, record=record, profile="pay").json()["ok"] is True
    assert post(client, "/check-ho", ho=ho.replace("61102938", "61102983"), record=record, profile="pay").json()["ok"] is False
    h = post(client, "/digest", line=ho, profile="pay").json()["digest"]
    rb = ("RW1 RB payer-1 re=scheduler-1 from=payer to=scheduler item=inv:MD-2026-057 ask=PAY p=pay sup=marlow amt=5400.00 cur=GBP "
          f"kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929 h={h}")
    assert post(client, "/check-rb", ho=ho, rb=rb, profile="pay").json()["ok"] is True
    dn = ("RW1 DN payer-3 re=scheduler-1 p=pay from=payer to=scheduler item=inv:MD-2026-057 out=OK sup=marlow amt=5400.00 cur=GBP "
          "kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929 // as executed, from the payment tool")
    assert post(client, "/check-dn", ho=ho, dn=dn, rb=rb, profile="pay").json()["ok"] is True
    bad = post(client, "/check-dn", ho=ho, dn=dn.replace("amt=5400.00", "amt=5100.00"), rb=rb, profile="pay").json()
    assert bad["ok"] is False and bad["problems"] == ["executed: amt mismatch: plan 5400.00 vs DN 5100.00"]


def test_home_page_tells_the_tests(client):
    """The home page tells the six tests in order, each with its flow diagram, and says what we were testing first."""
    text = client.get("/").text
    assert text.count('<figure class="flow">') == 8 and text.count('role="img"') == 8
    order = [text.index(needle) for needle in ("What we were testing", "Two ways to say a job", "Test 1</p>", "Test 2</p>", "Test 3</p>",
                                                "Test 4</p>", "Test 5</p>", "Test 6</p>", "The scorecard", "The flow that works", "How to use this", "What not to do")]
    assert order == sorted(order)
    assert "\u2014" not in text


def test_quickstart_and_lines_pages(client):
    for path, needle in (("/quickstart", "Start in two minutes"), ("/lines", "What a line is")):
        r = client.get(path)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/html") and needle in r.text


def test_profiles_page_and_list_share_a_path(client):
    page = client.get("/profiles", headers={"Accept": "text/html,application/xhtml+xml"})
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html") and "Same line, four kinds of work" in page.text
    listing = client.get("/profiles", headers={"Accept": "application/json"})
    assert listing.headers["content-type"].startswith("application/json")
    assert {p["name"] for p in listing.json()} >= {"core", "pay", "clin", "pform", "deploy"}
    # every line shown on the profiles page validates under the profile it names
    for line in re.findall(r"<pre>(RW1 .*?)</pre>", page.text, re.S):
        line = re.sub(r"</?b>", "", line).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").strip()
        profile = re.search(r"p=([a-z]+)", line).group(1)
        body = post(client, "/validate", line=line, profile=profile).json()
        assert body["ok"], (line, body["errors"])


def test_quickstart_replies_are_real(client):
    """The requests on the quickstart page answer exactly what the page shows."""
    ho = ("RW1 HO scheduler-1 p=pay from=scheduler to=payer item=inv:MD-2026-057 ask=PAY rb=exec sup=marlow amt=5400.00 cur=GBP "
          "kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929")
    rb = post(client, "/make-rb", ho=ho, id="payer-1", profile="pay").json()["rb"]
    assert "h=a7a82de76607" in rb                                                      # the fingerprint printed on the page
    assert post(client, "/check-rb", ho=ho, rb=rb, profile="pay").json() == {"ok": True, "problems": [], "notes": []}
    bad = post(client, "/check-rb", ho=ho, rb=rb.replace("amt=5400.00", "amt=5100.00"), profile="pay").json()
    assert bad == {"ok": False, "problems": ["tier5 execution: amt mismatch: HO 5400.00 vs RB 5100.00"], "notes": []}
    page = client.get("/quickstart").text
    assert "tier5 execution: amt mismatch: HO 5400.00 vs RB 5100.00" in page and rb in page
    body = post(client, "/validate", line=ho, profile="pay").json()
    assert body["message"]["slots"]["rb"] == ["exec"] and body["message"]["slots"]["apref"] == "FD-0929"


# ------------------------------------------------------------------ the gate: lines as the record

# A short synthetic clinical note, numbered from 1 as src=doc:7#l<n> counts them.
NOTE = """Ridgeway Lane Surgery, Asthma Review
Date: 14 September 2026
Patient: Ms Dana FOLEY, DOB 02/04/1988

Ms Foley attended for her asthma review. She reports using her salbutamol inhaler about twice a
week, mostly after running. No night-time waking. She has never smoked. Her mother has asthma.
Peak flow today 420 L/min. Continue beclometasone 200 micrograms two puffs twice daily.
Review in 12 months, sooner if symptoms worsen."""

GOOD = """RW1 ST extractor-1 from=extractor to=record p=clin item=med:salbutamol act=RPT pol=POS cert=CERT subj=PT time=CUR freq=PRN src=doc:7#l5-6 // using her salbutamol inhaler about twice a week
RW1 ST extractor-2 from=extractor to=record p=clin item=sym:night-time-waking act=RPT pol=NEG cert=CERT subj=PT time=CUR src=doc:7#l6 // No night-time waking
RW1 ST extractor-3 from=extractor to=record p=clin item=soc:smoking act=RPT pol=NEG cert=CERT subj=PT time=PAST src=doc:7#l6 // never smoked
RW1 ST extractor-4 from=extractor to=record p=clin item=dx:asthma act=RPT pol=POS cert=CERT subj=FAM time=CUR src=doc:7#l6 // Her mother has asthma
RW1 ST extractor-5 from=extractor to=record p=clin item=meas:peak-flow act=OBS pol=POS cert=CERT subj=PT time=CUR res=420 unit=L/min src=doc:7#l7 // Peak flow today 420 L/min
RW1 ST extractor-6 from=extractor to=record p=clin item=med:beclometasone act=RX pol=POS cert=CERT subj=PT time=CUR dose=200micrograms freq=BD chg=CONT src=doc:7#l7 // Continue beclometasone 200 micrograms two puffs twice daily
RW1 ST extractor-7 from=extractor to=record p=clin item=fu:review act=ORD pol=POS cert=CERT subj=PT time=FUT when=12m src=doc:7#l8 // Review in 12 months"""


def test_gate_accepts_a_faithful_translation(client):
    body = post(client, "/gate", lines=GOOD, profile="clin", document=NOTE, doc_id="7").json()
    assert body["ok"] is True and body["errors"] == [] and body["notes"] == []
    assert body["counts"] == {"rows": 7, "st": 7, "ok": 7}
    assert [m["item"] for m in body["accepted"]][:2] == ["med:salbutamol", "sym:night-time-waking"]
    assert all(r["ok"] and r["message"]["slots"]["src"].startswith("doc:7#l") for r in body["rows"])


@pytest.mark.parametrize("edit, needle", [
    (("// never smoked", "// has never smoked a cigarette"), "not found verbatim in doc:7#l6"),   # paraphrase
    (("src=doc:7#l7 // Peak", "src=doc:7#l5 // Peak"), "not found verbatim in doc:7#l5"),          # wrong line
    (("src=doc:7#l8 // Review", "src=doc:7#l80 // Review"), "the document has lines 1 to 8"),        # beyond the end
    ((" src=doc:7#l6 // No night", " // No night"), "src= is missing"),                               # no pointer
    (("item=soc:smoking", "item=habit:smoking"), "kind one of sym dx med proc"),                     # invented kind
    (("extractor-2 from", "extractor-1 from"), "id extractor-1 already used"),                       # duplicate id
    (("RW1 ST extractor-4 from", "RW1 ST extractor-4 re=extractor-9 from"), "re=extractor-9 does not name"),
    (("src=doc:7#l6 // never", "src=doc:9#l6 // never"), "this is document doc:7"),                  # other document
    (("p=clin item=fu:review", "item=fu:review"), "missing p=clin"),
    (("act=OBS pol=POS", "act=SEEN pol=POS"), "not a known act code"),                                # the codec's own check
])
def test_gate_refuses_a_planted_fault(client, edit, needle):
    lines = GOOD.replace(*edit)
    assert lines != GOOD
    body = post(client, "/gate", lines=lines, profile="clin", document=NOTE, doc_id="7").json()
    assert body["ok"] is False and any(needle in e for e in body["errors"]), body["errors"]
    assert sum(1 for r in body["rows"] if not r["ok"]) >= 1


def test_gate_without_a_document_checks_shape_only(client):
    body = post(client, "/gate", lines=GOOD, profile="clin").json()
    assert body["ok"] is True and body["notes"] == ["no document given: src ranges and quotes were not checked against the source"]


INBOX = """# Inbox export, two messages, oldest first.

---
**From:** Northfield Print Ltd <accounts@northfield-print.co.uk>
**Subject:** Invoice INV-000491 (PO-1044)

Net 315.50, VAT 63.10, total 378.60 GBP.
---
**From:** Marlow Design <billing@marlowdesign.co.uk>
**Subject:** Invoice MD-2026-057

Net 4500.00, VAT 900.00, total 5400.00 GBP.
"""

PAY_LINES = """RW1 ST extractor-1 from=extractor to=reconciler p=pay item=inv:INV-000491 sup=northfield po=PO-1044 net=315.50 vat=63.10 amt=378.60 cur=GBP kind=GROSS src=email:1
RW1 ST extractor-2 from=extractor to=reconciler p=pay item=inv:MD-2026-057 sup=marlow net=4500.00 vat=900.00 amt=5400.00 cur=GBP kind=GROSS src=email:2
RW1 HO extractor-3 from=extractor to=reconciler p=pay item=run:2026-09 ask=RECON due=20261001"""


def test_gate_pay_profile(client):
    ok = post(client, "/gate", lines=PAY_LINES, profile="pay", document=INBOX).json()
    assert ok["ok"] is True and ok["counts"] == {"rows": 3, "st": 2, "ok": 3} and len(ok["accepted"]) == 2
    arithmetic = post(client, "/gate", lines=PAY_LINES.replace("amt=5400.00", "amt=5100.00"), profile="pay").json()
    assert arithmetic["errors"] == ["row 2: net 4500.00 + vat 900.00 is not amt 5100.00"]
    no_src = post(client, "/gate", lines=PAY_LINES.replace(" src=email:1", ""), profile="pay").json()
    assert any("carries src=email:<n>" in e for e in no_src["errors"])
    missing = post(client, "/gate", lines=PAY_LINES.replace(" cur=GBP kind=GROSS src=email:2", " src=email:2"), profile="pay").json()
    assert "row 2: an invoice line needs cur=" in missing["errors"] and "row 2: an invoice line needs kind=" in missing["errors"]
    beyond = post(client, "/gate", lines=PAY_LINES.replace("src=email:2", "src=email:9"), profile="pay", document=INBOX).json()
    assert beyond["errors"] == ["row 2: src=email:9: the inbox export has messages 1 to 2"]


@pytest.mark.parametrize("body, needle", [
    ({"lines": GOOD, "profile": "core"}, "profile is required"),
    ({"lines": GOOD, "profile": "pform"}, "has no translation rule"),
    ({"lines": "   \n", "profile": "clin"}, "lines is empty"),
    ({"lines": GOOD, "profile": "clin", "document": "x" * (service.MAX_DOCUMENT + 1)}, "the limit is"),
])
def test_gate_refuses_bad_requests(client, body, needle):
    r = client.post("/gate", json=body)
    assert r.status_code == 400 and needle in r.json()["error"], r.json()


def test_gate_via_mcp(client):
    res = call_tool(client, "gate", {"lines": GOOD, "profile": "clin", "document": NOTE, "doc_id": "7"})
    assert res["isError"] is False and res["structuredContent"]["ok"] is True
    res = call_tool(client, "gate", {"lines": GOOD.replace("// never smoked", "// smokes"), "profile": "clin", "document": NOTE})
    assert res["isError"] is False and res["structuredContent"]["ok"] is False      # a failed gate is a result, not an error
    assert any("not found verbatim" in e for e in res["structuredContent"]["errors"])
    res = call_tool(client, "gate", {"lines": GOOD, "profile": "pform"})
    assert res["isError"] is True and "no translation rule" in res["content"][0]["text"]


RESEARCH = APP_DIR.parent / "research" / "translation"


@pytest.mark.skipif(not (RESEARCH / "runs").is_dir(), reason="research corpus not checked out")
def test_gate_matches_the_translation_study(client):
    """Every line-arm output the study accepted passes the hosted gate too (research/translation/tools/gate.py is
    the reference; this is the same check served over HTTP)."""
    files = sorted((RESEARCH / "runs").glob("L-*/doc*.rw"))
    assert files, "no study outputs found"
    for path in files:
        n = int(path.stem[3:])
        doc = (RESEARCH / "data" / "docs" / f"doc{n:02d}.md").read_text(encoding="utf-8")
        body = post(client, "/gate", lines=path.read_text(encoding="utf-8"), profile="clin", document=doc, doc_id=str(n)).json()
        assert body["ok"] is True, (str(path), body["errors"][:3])


def test_index_page_numbers_match_the_studies():
    """The figures on the landing page are the studies' own. Re-derived here from the results tables so the page
    cannot drift from them."""
    root = APP_DIR.parent / "research"
    if not (root / "month-end" / "results" / "summary.md").is_file():
        pytest.skip("research corpus not checked out")
    html = (APP_DIR / "static" / "index.html").read_text(encoding="utf-8")
    research = (APP_DIR / "static" / "research" / "index.html").read_text(encoding="utf-8")
    rows = {}
    for line in (root / "month-end" / "results" / "summary.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 8 and cells[1].isdigit():
            rows[cells[0]] = (int(re.match(r"\d+", cells[5]).group()), int(re.match(r"\d+", cells[7]).group()))
    a, d = rows["A prose"], rows["D disciplined prose"]
    assert round(d[0] / a[0], 2) == 0.33 and "to a third" in research        # traffic between agents
    assert round(d[1] / a[1], 2) == 0.40 and "reading to 40%" in research     # the person's reading
    cells = {}
    for line in (root / "month-end" / "results" / "summary.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) > 9 and c[1].isdigit():
            cells[c[0]] = c
    assert cells["A prose"][8] == "1333" and cells["D disciplined prose"][8] == "520"
    assert cells["D-haiku disciplined prose, Haiku agents"][3].startswith("0.67") and cells["L-haiku lines, Haiku agents"][3].startswith("0.83")
    assert all(cells[k][3] == "1.0 / 1.0" for k in cells if "haiku" not in k) and "three reserved decisions" in research
    rb = root / "readback" / "results" / "summary.json"
    if rb.is_file():
        cells = json.loads(rb.read_text(encoding="utf-8"))["cells"]
        assert cells["A-sonnet"]["fault_reached_act"] == 9 and cells["A-haiku"]["fault_reached_act"] == 14
        assert cells["C-sonnet"]["fault_reached_act"] == 0 and cells["C-haiku"]["fault_reached_act"] == 0
        assert all(cells[k]["false_alarms"] == 0 for k in cells)
    assert "9 and 14 of 16" in research
    tp = root / "tool-prepare" / "results" / "summary.json"
    if tp.is_file():   # the landing page's headline: tool faults at prepare on Haiku 5.5, one-step tool against two-phase
        rows = json.loads(tp.read_text(encoding="utf-8"))["rows"]
        prep = [r for r in rows if r["model"] == "haiku" and r["block"] == 2 and r.get("tool_fault_at") == "prepare"]
        one_step = [r for r in prep if r["arm"] in "AD"]
        two_phase = [r for r in prep if r["arm"] in "PQ"]
        assert len(one_step) == 60 and sum(r["wrong_act"] for r in one_step) == 59 and sum(r["wrong_act"] for r in two_phase) == 0
    assert "59 to 0" in html and "of 60 wrong accounts and dates" in html and "14 to 0" in html and "0 of 378" in html
    tr = (root / "translation" / "results" / "summary.md").read_text(encoding="utf-8")
    sonnet = [c.strip() for c in [l for l in tr.splitlines() if l.startswith("| L-sonnet")][0].strip("|").split("|")]
    assert sonnet[2].startswith("0.997") and "99.7%" in research              # recall
    assert sonnet[13].startswith("0.99") and "right words 99%" in research     # quote ok


def test_study_pages_figures_match_results():
    """The headline figures on each study page are re-derived from that study's results files."""
    root = APP_DIR.parent / "research"
    pages = APP_DIR / "static" / "research"
    rb = root / "readback" / "results" / "summary.json"
    if not rb.is_file():
        pytest.skip("research corpus not checked out")
    cells = json.loads(rb.read_text(encoding="utf-8"))["cells"]
    page = (pages / "readback.html").read_text(encoding="utf-8")
    for cell in ("A-sonnet", "A-haiku", "B-sonnet", "B-haiku", "C-sonnet", "C-haiku"):
        assert f"{cells[cell]['fault_reached_act']} of 16" in page, cell
    acts = sum(cells[c]["acts_correct"] for c in ("B-sonnet", "B-haiku", "C-sonnet", "C-haiku"))
    assert acts == 65 and "65 of 65" in page
    honest = sum(cells[c]["setback_honest"] for c in ("C-sonnet", "C-haiku"))
    assert honest == 28 and "28 of 28" in page
    tr = (root / "translation" / "results" / "summary.md").read_text(encoding="utf-8").splitlines()
    row = lambda name: [c.strip() for c in [l for l in tr if l.startswith(f"| {name}")][0].strip("|").split("|")]
    page = (pages / "translation.html").read_text(encoding="utf-8")
    assert row("L-sonnet")[2].startswith("0.997") and "99.7%" in page
    refused = round((1 - float(row("L-haiku")[18])) * 36) + round((1 - float(row("J-haiku")[18])) * 36)
    assert refused == 70 and "70 of 72" in page
    me = {}
    for line in (root / "month-end" / "results" / "summary.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) > 8 and c[1].isdigit():
            me[c[0]] = (int(re.match(r"\d+", c[5]).group()), int(re.match(r"\d+", c[7]).group()))
    page = (pages / "month-end.html").read_text(encoding="utf-8")
    a, d = me["A prose"], me["D disciplined prose"]
    assert round(d[0] / a[0], 2) == 0.33 and "to a third" in page
    assert round(d[1] / a[1], 2) == 0.40 and "to 40%" in page
    assert me["L-haiku lines, Haiku agents"][0] == 1590 and "1,590" in page


# ------------------------------------------------------------------ HTTP behaviour

def test_cors_is_open(client):
    r = client.get("/healthz", headers={"Origin": "https://example.org"})
    assert r.headers["access-control-allow-origin"] == "*"
    for path in ("/validate", "/mcp"):
        pre = client.options(path, headers={
            "Origin": "https://example.org", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, mcp-protocol-version"})
        assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == "*", path


def test_errors_are_json(client):
    r = client.post("/validate", json={})
    assert r.status_code == 422 and r.json() == {"error": "line: Field required"}
    r = client.post("/validate", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and r.json() == {"error": "request body is not valid JSON"}
    r = client.post("/make-rb", json={"ho": HO, "id": "a-1", "hash": "maybe"})
    assert r.status_code == 422 and r.json()["error"].startswith("hash: ")
    r = client.get("/nope")
    assert r.status_code == 404 and r.json() == {"error": "Not Found"}
    r = client.get("/validate")
    assert r.status_code == 405 and r.json() == {"error": "Method Not Allowed"} and "POST" in r.headers["allow"]


# ------------------------------------------------------------------ MCP

def rpc(client, method, params=None, **kw):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    r = client.post("/mcp", json=body, headers={**MCP_HEADERS, **kw.get("headers", {})})
    assert r.status_code == 200, r.text
    return r.json()


def call_tool(client, name, arguments):
    return rpc(client, "tools/call", {"name": name, "arguments": arguments})["result"]


def test_mcp_tools_list(client):
    tools = {t["name"]: t for t in rpc(client, "tools/list")["result"]["tools"]}
    assert set(tools) == {"validate", "gate", "check_rb", "make_rb", "check_ho", "check_dn", "legend", "to_json"}
    assert tools["check_ho"]["inputSchema"]["required"] == ["ho", "record"]
    assert tools["check_dn"]["inputSchema"]["required"] == ["ho", "dn"]
    for tool in tools.values():
        assert tool["description"] and "\n" not in tool["description"] and tool["inputSchema"]["type"] == "object"
        assert all("description" in p for p in tool["inputSchema"]["properties"].values())
    assert tools["validate"]["inputSchema"]["required"] == ["line"]
    assert tools["check_rb"]["inputSchema"]["required"] == ["ho", "rb"]
    assert tools["gate"]["inputSchema"]["required"] == ["lines", "profile"]
    assert tools["make_rb"]["inputSchema"]["required"] == ["ho", "id"]
    assert set(tools["make_rb"]["inputSchema"]["properties"]) == {"ho", "id", "profile", "acc", "do", "hash"}
    assert tools["make_rb"]["inputSchema"]["properties"]["hash"]["type"] == "boolean"


def test_mcp_initialize_and_transport(client):
    init = rpc(client, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "test", "version": "0"}})["result"]
    assert init["serverInfo"]["name"] == "rogerwilco"
    assert "tools" in init["capabilities"] and "legend" in init["instructions"]
    note = client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=MCP_HEADERS)
    assert note.status_code == 202
    # Stateless and POST only: there is no event stream to offer and no session to close.
    assert client.get("/mcp", headers={"Accept": "text/event-stream"}).status_code == 405
    assert client.delete("/mcp").status_code == 405
    # The trailing-slash spelling is served in place, not redirected.
    r = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=MCP_HEADERS,
                    follow_redirects=False)
    assert r.status_code == 200 and "tools" in r.json()["result"]


def test_mcp_works_behind_a_real_domain(client):
    # The SDK's default would answer 421 to any Host other than localhost.
    headers = {**MCP_HEADERS, "Host": "rogerwilco.example.com", "Origin": "https://claude.ai"}
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers)
    assert r.status_code == 200 and len(r.json()["result"]["tools"]) == 8


def test_mcp_tools_call(client):
    res = call_tool(client, "validate", {"line": HO})
    assert res["isError"] is False and res["structuredContent"]["ok"] is True
    assert json.loads(res["content"][0]["text"])["message"]["type"] == "HO"       # the text block carries the same JSON
    assert call_tool(client, "validate", {"line": PAY_HO, "profile": "pay"})["structuredContent"]["ok"] is True
    assert call_tool(client, "make_rb", {"ho": HO, "id": "writer-01"})["structuredContent"] == {"rb": RB}
    assert call_tool(client, "check_rb", {"ho": HO, "rb": RB})["structuredContent"] == {"ok": True, "problems": [], "notes": []}
    bad = call_tool(client, "check_rb", {"ho": HO_ACC, "rb": RB_ACC.replace("len:120w", "len:150w"), "expect_acc": EXPECT})
    assert bad["structuredContent"]["ok"] is False
    legend = call_tool(client, "legend", {"profile": "pay"})
    assert legend["content"][0]["text"].startswith("rogerwilco RW1.") and "RECON" in legend["content"][0]["text"]
    assert call_tool(client, "to_json", {"line": HO})["structuredContent"]["message"]["slots"]["pri"] == 2


def test_mcp_tool_errors_are_reported_as_results(client):
    res = call_tool(client, "legend", {"profile": "nope"})
    assert res["isError"] is True and "unknown profile" in res["content"][0]["text"]
    res = call_tool(client, "to_json", {"line": "RW1 HO a-1 from=a to=b ask=DRAFT"})
    assert res["isError"] is True and "HO requires item" in res["content"][0]["text"]
    res = call_tool(client, "make_rb", {"ho": HO, "id": "writer-01", "profile": "../profiles/pay"})
    assert res["isError"] is True and "invalid profile name" in res["content"][0]["text"]


# ------------------------------------------------------------------ how the app starts

def _python(code: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, env=env)


def test_mcp_module_survives_its_own_folder_on_sys_path():
    # app/mcp.py shares its name with the SDK. `cd app && python -m pytest` puts this folder first on sys.path, where a
    # bare `import mcp` would find the wrong file.
    code = f"import sys; sys.path.insert(0, {str(APP_DIR)!r})\n" + _package_source(APP_DIR) + (
        "import app.mcp\nprint(app.mcp.FastMCP.__module__)\n")
    out = _python(code)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "mcp.server.fastmcp.server"


def test_skill_dir_comes_from_the_environment():
    code = _package_source(APP_DIR) + "import app.service as s\nprint(s.SKILL_DIR)\n"
    out = _python(code, {**os.environ, "RW_SKILL_DIR": str(service.SKILL_DIR)})
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == str(service.SKILL_DIR)


def test_missing_codec_stops_startup_with_a_clear_message():
    code = _package_source(APP_DIR) + "import app.service\n"
    out = _python(code, {**os.environ, "RW_SKILL_DIR": "/nonexistent/skill"})
    assert out.returncode != 0 and "RW_SKILL_DIR" in out.stderr


def test_research_index_and_pages(client):
    r = client.get("/research")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Month-end close" in r.text and "/research/month-end" in r.text
    for slug in ("wire-study", "pilot", "month-end", "translation", "readback"):
        page = client.get(f"/research/{slug}")
        assert page.status_code == 200, slug
        assert page.text.lstrip().startswith("<!doctype html>"), slug
        assert '<meta charset="utf-8">' in page.text and '<main class="report">' in page.text, slug
        assert 'class="site-head"' in page.text and '/static/site.css' in page.text, slug   # the shared chrome
    assert client.get("/research/nope").status_code == 404


def test_every_research_page_is_served(client):
    """Every study page under static/research is routed: a page the index links to must not 404."""
    from app import main as m
    pages = sorted(f.stem for f in m.RESEARCH_DIR.glob("*.html") if f.stem != "index")
    assert set(pages) == m.RESEARCH_PAGES, f"pages on disk {pages} differ from the routed set {sorted(m.RESEARCH_PAGES)}"
    assert client.get("/research").status_code == 200
    for slug in pages:
        r = client.get(f"/research/{slug}")
        assert r.status_code == 200, slug
        assert "<main" in r.text
    assert client.get("/research/no-such-study").status_code == 404
