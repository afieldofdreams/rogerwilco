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
    for path in ("/healthz", "/validate", "/check-rb", "/make-rb", "/to-json", "/from-json", "/digest", "/legend",
                 "/profiles", "/spec", "/skill"):
        assert path in paths
    assert client.get("/docs").status_code == 200


# ------------------------------------------------------------------ playground

def test_index_page(client):
    r = client.get("/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    for href in ('href="/spec"', 'href="/skill"', 'href="/legend?profile=core"'):
        assert href in r.text


def _examples() -> dict:
    html = (APP_DIR / "static" / "index.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script type="application/json" id="examples">(.*?)</script>', html, re.S).group(1))


def test_playground_line_examples_do_what_they_say(client):
    for ex in _examples()["lines"]:
        body = post(client, "/validate", line=ex["line"], profile=ex["profile"]).json()
        assert body["ok"] is ex["valid"], ex["label"]


def test_playground_readback_examples_do_what_they_say(client):
    for ex in _examples()["pairs"]:
        body = post(client, "/check-rb", ho=ex["ho"], rb=ex["rb"], profile=ex["profile"], expect_acc=ex["expect"] or None).json()
        assert body["ok"] is ex["passes"], ex["label"]


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
    assert set(tools) == {"validate", "check_rb", "make_rb", "legend", "to_json"}
    for tool in tools.values():
        assert tool["description"] and "\n" not in tool["description"] and tool["inputSchema"]["type"] == "object"
        assert all("description" in p for p in tool["inputSchema"]["properties"].values())
    assert tools["validate"]["inputSchema"]["required"] == ["line"]
    assert tools["check_rb"]["inputSchema"]["required"] == ["ho", "rb"]
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
    assert r.status_code == 200 and len(r.json()["result"]["tools"]) == 5


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
