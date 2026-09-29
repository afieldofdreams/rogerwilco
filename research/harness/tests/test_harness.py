"""Tests for the harness. No real API is called: the agent loop is driven by the mock provider, and the two HTTP
adapters are exercised against a fake server on 127.0.0.1. Everything is built under pytest's tmp_path; the
repository's runs/ directory is never touched.

    cd research/harness && python3 -m pytest -q
"""
from __future__ import annotations

import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))

import agent  # noqa: E402
import llm  # noqa: E402
import orchestrate  # noqa: E402

REPO = HARNESS.parents[1]
MONTH_END = HARNESS.parent / "month-end"
CODEC = REPO / "rogerwilco" / "scripts" / "rogerwilco.py"
ROLES = orchestrate.AGENTS
SENTINEL = "SENTINEL-not-a-real-key-do-not-leak-0123456789"      # deliberately not key-shaped, so no scanner mistakes it for one
ENV_VARS = ("RW_API_KEY", "RW_BASE_URL", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
            "RW_MAX_TOKENS", "RW_TEMPERATURE", "RW_EXTRA_BODY", "RW_RETRIES", "RW_TIMEOUT", "RW_ANTHROPIC_CACHE", "RW_MONTH_END")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ENV_VARS:
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------- helpers

def sh(cmd: str) -> dict:
    return {"name": "shell", "arguments": {"cmd": cmd}}


def call(name: str, **arguments) -> dict:
    return {"name": name, "arguments": arguments}


def use(prompt: int, completion: int, cached: int = 0) -> dict:
    return {"prompt_tokens": prompt, "completion_tokens": completion, "cached_tokens": cached}


def total(steps: list[dict], key: str) -> int:
    return sum(s["usage"][key] for s in steps)


def mock_model(tmp_path: Path, agents: dict, name: str = "script.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps({"agents": agents}))
    return f"mock:{p}"


def make_run(tmp_path: Path, arm: str = "A", name: str = "A9") -> Path:
    """A minimal run directory: the real mail.py and data, one-line role prompts, one kickoff message."""
    run = tmp_path / "runs" / name
    for d in ("work", "mail", "prompts"):
        (run / d).mkdir(parents=True)
    shutil.copytree(MONTH_END / "data", run / "data")
    shutil.copy(MONTH_END / "tools" / "mail.py", run / "mail.py")
    (run / "run.json").write_text(json.dumps({"arm": arm, "n": 9, "scenario": 1, "model": "sonnet", "profile": "pay",
                                              "rogerwilco": str(CODEC)}))
    for role in ROLES:
        (run / "prompts" / f"{role}.md").write_text(f"You are the **{role}** agent in a test team.\n")
    subprocess.run([sys.executable, "mail.py", "send", "--from", "human", "--to", "extractor", "-m", "Please prepare the run."],
                   cwd=run, check=True, capture_output=True)
    return run


def make_month_end(tmp_path: Path) -> Path:
    """A private copy of the month-end tools and data, so --build and grid tests never write into the repository."""
    root = tmp_path / "repo"
    me = root / "research" / "month-end"
    me.mkdir(parents=True)
    for d in ("tools", "data", "data2", "truth"):
        shutil.copytree(MONTH_END / d, me / d, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "rogerwilco").symlink_to(REPO / "rogerwilco")
    return me


def quiet(_msg: str) -> None:
    pass


def log_records(run: Path) -> list[dict]:
    return orchestrate.read_log(run)


def transcript(run: Path, role: str) -> list[dict]:
    return [json.loads(l) for l in (run / "harness" / "transcripts" / f"{role}.jsonl").read_text().splitlines()]


def tool_results(run: Path, role: str) -> list[str]:
    return [t["message"]["content"] for t in transcript(run, role) if t["message"]["role"] == "tool"]


# ---------------------------------------------------------------- the two-round mini-run

QUESTION = ("Northfield emailed from accounts@northfield-print.co asking us to switch to sort 04-00-75 account 88214561. "
            "Approve or reject?")
ENV_DUMP = 'python3 -c "import os,json; print(json.dumps(sorted(os.environ)))"'


def mini_script(outside: Path) -> dict:
    extractor = [
        [  # round 1: woken by the kickoff
            {"tool_calls": [sh("python3 mail.py read --me extractor")], "usage": use(1000, 20)},
            {"tool_calls": [call("read_file", path="../outside.txt"),           # refused: outside the run directory
                            call("read_file", path=str(outside)),               # refused: absolute path outside
                            sh("rm -rf work"),                                  # refused: not on the allowlist
                            sh(f"cat {outside}"),                               # refused: names a file outside
                            call("read_file", path="data/emails.md"),           # fine, and logged like mail.py open
                            call("write_file", path="work/invoices.json", content="[]")],
             "usage": use(1500, 300, 1000)},
            {"tool_calls": [sh(f'python3 mail.py send --from extractor --to human -m "{QUESTION}"'),
                            sh('python3 mail.py send --from extractor --to auditor -m "Extraction finished, facts in work/invoices.json"')],
             "usage": use(2000, 400, 1500)},
            {"tool_calls": [call("done")], "usage": use(2500, 5, 2000)},
        ],
        [  # round 2: woken by the principal's answer
            {"tool_calls": [sh(ENV_DUMP)], "usage": use(2900, 10, 2400)},
            {"tool_calls": [sh("python3 mail.py read --me extractor")], "usage": use(3000, 20, 2500)},
            {"content": "DONE", "usage": use(3100, 2, 3000)},
        ],
    ]
    auditor = [[  # round 2: woken by the extractor's message, at the same time as the extractor
        {"tool_calls": [sh("python3 mail.py read --me auditor")], "usage": use(800, 20)},
        {"tool_calls": [sh('python3 mail.py send --from auditor --to human -m "Audit passed: the run is ready in work/payment_run.json."')],
         "usage": use(1200, 60, 700)},
        {"tool_calls": [call("done")], "usage": use(1300, 5, 1200)},
    ]]
    return {"extractor": extractor, "auditor": auditor}


def test_two_round_mini_run(tmp_path, monkeypatch):
    for k in ("RW_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "HTTPS_PROXY"):   # must reach no file and no subprocess
        monkeypatch.setenv(k, SENTINEL + k)
    outside = tmp_path / "outside.txt"
    outside.write_text("not for the agents")
    run = make_run(tmp_path)
    script = mini_script(outside)
    model = mock_model(tmp_path, script)

    res = orchestrate.run_one(run, model, log=quiet)

    assert (res["stop"], res["rounds"]) == ("complete", 2)
    rounds = json.loads((run / "rounds.json").read_text())
    assert rounds["rounds"] == 2 and rounds["stop"] == "complete" and rounds["auditor_reported"] is True
    assert [r["agents"] for r in rounds["per_round"]] == [["extractor"], ["extractor", "auditor"]]
    assert rounds["per_round"][0]["principal"]["sent"] == 1          # the scripted principal answered the bank-change question
    assert rounds["per_round"][1]["principal"]["sent"] == 0          # the auditor's "ready" needs no answer

    # the channel: kickoff, question, principal answer, hand-off, final report
    msgs = [(r["from"], r["to"]) for r in log_records(run) if r["kind"] == "msg"]
    assert msgs == [("human", "extractor"), ("extractor", "human"), ("extractor", "auditor"), ("human", "extractor"),
                    ("auditor", "human")]
    answer = [r for r in log_records(run) if r["kind"] == "msg" and r["from"] == "human" and r["to"] == "extractor"][-1]
    assert answer["body"].startswith("REJECT")
    assert orchestrate.MailBus(run).pending() == {}
    opens = [r for r in log_records(run) if r["kind"] == "open"]
    assert [(o["by"], o["path"]) for o in opens] == [("extractor", "data/emails.md")]   # read_file is logged like mail.py open
    assert (run / "work" / "invoices.json").read_text() == "[]"

    # usage is recorded per agent, per turn, per call
    usage = json.loads((run / "usage.json").read_text())
    ex_turns = usage["agents"]["extractor"]["turns"]
    assert [t["turn"] for t in ex_turns] == [1, 2] and [t["round"] for t in ex_turns] == [1, 2]
    for turn, steps in zip(ex_turns, script["extractor"]):
        assert turn["prompt_tokens"] == total(steps, "prompt_tokens")
        assert turn["completion_tokens"] == total(steps, "completion_tokens")
        assert turn["cached_tokens"] == total(steps, "cached_tokens")
        assert turn["calls"] == len(steps)
        assert [c["prompt_tokens"] for c in turn["calls_detail"]] == [s["usage"]["prompt_tokens"] for s in steps]
    assert (ex_turns[0]["prompt_tokens"], ex_turns[0]["completion_tokens"], ex_turns[0]["cached_tokens"]) == (7000, 725, 4500)
    assert ex_turns[0]["ended_by"] == "done" and ex_turns[1]["ended_by"] == "text"
    au = usage["agents"]["auditor"]["total"]
    assert (au["prompt_tokens"], au["completion_tokens"], au["cached_tokens"], au["turns"]) == (3300, 85, 1900, 1)
    every = [s for steps in script["extractor"] + script["auditor"] for s in steps]
    assert usage["total"]["prompt_tokens"] == total(every, "prompt_tokens")
    assert usage["total"]["completion_tokens"] == total(every, "completion_tokens")
    assert usage["total"]["cached_tokens"] == total(every, "cached_tokens")
    assert usage["total"]["cached_reported"] is True and usage["total"]["estimated"] is False

    # the sandbox refused the four out-of-bounds calls and let the rest through
    assert ex_turns[0]["refused"] == 4 and ex_turns[0]["tool_errors"] == 4
    results = tool_results(run, "extractor")
    assert sum(r.startswith("refused:") for r in results) == 4
    assert any("outside the run directory" in r for r in results) and any("command not allowed: rm" in r for r in results)

    # graded and annotated
    assert res["grade"] is not None and (run / "grade.json").exists()
    cfg = json.loads((run / "run.json").read_text())
    assert cfg["harness"]["model"] == model and cfg["arm"] == "A"
    config = json.loads((run / "harness" / "config.json").read_text())
    assert config["model"] == model and config["endpoint_host"] == "mock" and config["limits"]["max_rounds"] == 16
    assert config["token_counter"].startswith(("tiktoken", "chars/4"))               # how mail.py counted, recorded for provenance

    # no key in any file, and none in what the agent's subprocess could see
    for f in run.rglob("*"):
        if f.is_file():
            assert SENTINEL not in f.read_text(errors="ignore"), f
    env_names = json.loads(next(r for r in results if r.startswith('["')))
    assert not [k for k in env_names if "KEY" in k or "PROXY" in k or k.startswith(("RW_", "OPENAI", "ANTHROPIC"))]


def test_the_config_record_scrubs_secrets_but_keeps_ordinary_settings():
    body = {"max_tokens": 5000, "reasoning": {"effort": "low", "max_tokens": 100}, "thinking": {"type": "enabled", "budget_tokens": 8000},
            "api_key": "k1", "provider": {"order": ["a"], "Authorization": "Bearer k2", "access_token": "k3"}, "list": [{"secret": "k4", "n": 1}]}
    out = orchestrate.scrub(body)
    assert out["max_tokens"] == 5000 and out["reasoning"] == {"effort": "low", "max_tokens": 100}
    assert out["thinking"] == {"type": "enabled", "budget_tokens": 8000} and out["provider"]["order"] == ["a"]
    assert out["api_key"] == out["provider"]["Authorization"] == out["provider"]["access_token"] == "[redacted]"
    assert out["list"] == [{"secret": "[redacted]", "n": 1}] and "k1" not in json.dumps(out) and "k4" not in json.dumps(out)


def test_a_provider_error_aborts_the_run_and_skips_grading(tmp_path):
    run = make_run(tmp_path)
    calls = []

    def flaky(messages, tools, model):
        calls.append(1)
        if len(calls) == 1:
            return llm.chat(messages, tools, model)
        raise llm.LLMError("HTTP 500 from example.invalid: boom (gave up after 8 attempts)")

    model = mock_model(tmp_path, {"extractor": [[{"tool_calls": [sh("python3 mail.py read --me extractor")], "usage": use(10, 1)}]]})
    res = orchestrate.run_one(run, model, chat_fn=flaky, log=quiet)
    assert res["stop"] == "error" and "boom" in res["error"] and res["grade"] is None
    assert not (run / "grade.json").exists()
    rounds = json.loads((run / "rounds.json").read_text())
    assert rounds["stop"] == "error" and "boom" in rounds["error"]
    assert json.loads((run / "usage.json").read_text())["agents"]["extractor"]["turns"][0]["ended_by"] == "error"


def test_a_run_directory_is_used_once(tmp_path):
    run = make_run(tmp_path)
    model = mock_model(tmp_path, {})
    orchestrate.run_one(run, model, max_rounds=1, grade=False, log=quiet)
    with pytest.raises(SystemExit, match="already been run"):
        orchestrate.run_one(run, model, grade=False, log=quiet)
    other = make_run(tmp_path / "b")
    subprocess.run([sys.executable, "mail.py", "send", "--from", "extractor", "--to", "human", "-m", "hello"], cwd=other, check=True,
                   capture_output=True)
    with pytest.raises(SystemExit, match="beyond the kickoff"):
        orchestrate.run_one(other, model, grade=False, log=quiet)


def test_a_shared_halt_flag_interrupts_a_run_cleanly(tmp_path):
    """What the grid does on Ctrl-C with --jobs: the run stops at its next model call and records why."""
    run = make_run(tmp_path)
    halt = threading.Event()

    def chat(messages, tools, model):
        halt.set()
        return llm.chat(messages, tools, model)

    model = mock_model(tmp_path, {"extractor": [[{"tool_calls": [call("list_dir")]}, {"tool_calls": [call("list_dir")]}]]})
    with pytest.raises(KeyboardInterrupt):
        orchestrate.run_one(run, model, chat_fn=chat, halt=halt, log=quiet)
    rounds = json.loads((run / "rounds.json").read_text())
    assert rounds["stop"] == "interrupted" and rounds["rounds"] == 1 and rounds["error"] is None
    turn = json.loads((run / "usage.json").read_text())["agents"]["extractor"]["turns"][0]
    assert turn["ended_by"] == "aborted" and turn["calls"] == 1                     # the second call was never made
    assert not (run / "grade.json").exists()                                        # an interrupted run is not graded


def test_max_rounds_and_token_budget(tmp_path):
    # an agent that never reads its mail is woken every round until the cap
    run = make_run(tmp_path)
    res = orchestrate.run_one(run, mock_model(tmp_path, {}), max_rounds=3, grade=False, log=quiet)
    assert (res["stop"], res["rounds"]) == ("max_rounds", 3)
    assert res["unread_at_stop"] == {"extractor": [1]}
    # the budget is checked between rounds
    run2 = make_run(tmp_path / "b")
    script = {"extractor": [[{"content": "DONE", "usage": use(5000, 1)}]] * 5}
    res = orchestrate.run_one(run2, mock_model(tmp_path / "b", script), max_prompt_tokens=8000, grade=False, log=quiet)
    assert (res["stop"], res["rounds"]) == ("budget", 2)
    # ... and after every model call, so a long turn is cut off inside the turn, not at the end of the round
    run3 = make_run(tmp_path / "c")
    script = {"extractor": [[{"tool_calls": [call("list_dir")], "usage": use(5000, 1)}] * 10]}
    res = orchestrate.run_one(run3, mock_model(tmp_path / "c", script), max_prompt_tokens=12000, grade=False, log=quiet)
    assert (res["stop"], res["rounds"], res["prompt_tokens"]) == ("budget", 1, 15000)
    turn = json.loads((run3 / "usage.json").read_text())["agents"]["extractor"]["turns"][0]
    assert turn["ended_by"] == "aborted" and turn["calls"] == 3


# ---------------------------------------------------------------- the sandbox

def test_file_tools_refuse_paths_outside_the_run_directory(tmp_path):
    run = make_run(tmp_path)
    sb = agent.Sandbox(run, "extractor")
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    (run / "escape").symlink_to(tmp_path)
    for path in ("../outside.txt", str(outside), "/etc/hostname", "data/../../outside.txt", "escape/outside.txt", "escape"):
        for r in (sb.call("read_file", {"path": path}), sb.call("list_dir", {"path": path})):
            assert r.refused and r.error and "outside the run directory" in r.text, (path, r)
    for path in ("../new.txt", str(tmp_path / "new.txt"), "/etc/rw-harness-test", "data/../../new.txt", "escape/new.txt",
                 "escape/deeper/new.txt"):
        r = sb.call("write_file", {"path": path, "content": "x"})
        assert r.refused and r.error and "outside the run directory" in r.text, (path, r)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["outside.txt", "runs"]     # nothing was created outside the run
    assert not Path("/etc/rw-harness-test").exists() and outside.read_text() == "x"
    ok = sb.call("read_file", {"path": "data/policy.md"})
    assert not ok.error and ok.text == (run / "data" / "policy.md").read_text()
    assert sb.call("read_file", {"path": str(run / "data" / "policy.md")}).text == ok.text      # absolute inside is fine
    assert sb.call("write_file", {"path": "work/x.json", "content": "{}"}).text == "wrote 2 bytes to work/x.json"
    assert sb.call("write_file", {"path": "work/sub/y.txt", "content": "y"}).error is False
    assert "x.json" in sb.call("list_dir", {"path": "work"}).text
    assert sb.call("read_file", {"path": "data/nope.md"}).text.startswith("error: no such file")
    assert sb.call("write_file", {"path": "data/note.txt", "content": "n"}).error is False       # data/ stays writable on purpose
    (run / "work" / "empty.txt").write_text("")
    assert sb.call("read_file", {"path": "work/empty.txt"}).text == "(no output)"                # never an empty tool message


def test_the_channel_and_the_harness_directory_are_protected(tmp_path):
    run = make_run(tmp_path)
    (run / "harness" / "transcripts").mkdir(parents=True)
    (run / "harness" / "transcripts" / "auditor.jsonl").write_text("secret\n")
    sb = agent.Sandbox(run, "extractor")
    for path in ("mail/log.jsonl", "mail.py", "run.json", "prompts/auditor.md", "harness/new.txt", "rounds.json", "principal_state.json", "."):
        r = sb.call("write_file", {"path": path, "content": "x"})
        assert r.refused, path
    assert sb.call("read_file", {"path": "harness/transcripts/auditor.jsonl"}).refused
    assert "harness" not in sb.call("list_dir", {"path": "."}).text
    assert sb.call("list_dir", {"path": "harness"}).refused
    assert sb.call("shell", {"cmd": "cat harness/transcripts/auditor.jsonl"}).refused
    assert sb.call("shell", {"cmd": "grep -r secret ."}).refused
    assert (run / "mail.py").read_text() == (MONTH_END / "tools" / "mail.py").read_text()


@pytest.mark.parametrize("cmd", [
    "python3 mail.py pending", "python3 mail.py --help", "python3 -c 'print(6 * 7)'", "cat data/po_list.json", "ls data",
    "grep -n Northfield data/emails.md", "head -n 3 data/emails.md", "tail -n 2 data/emails.md", "wc -l data/emails.md",
    "jq . data/po_list.json", "sha256sum data/policy.md", "grep -c /2026 data/emails.md", "ls -la",
    "python3 mail.py send --from extractor --to auditor -m x", "python3 mail.py read --me extractor",
    "python3 mail.py open --me extractor data/policy.md", "python3 mail.py send --to auditor -m x --from extractor",
])
def test_shell_allows(tmp_path, cmd):
    r = agent.Sandbox(make_run(tmp_path), "extractor").call("shell", {"cmd": cmd})
    assert not r.refused, r.text
    assert "not allowed" not in r.text and "refused" not in r.text


@pytest.mark.parametrize("cmd", [
    "rm -rf work", "curl http://example.invalid", "bash -c ls", "sh -c ls", "python3", "python3 evil.py", "python mail.py pending",
    "python3 -m http.server", "ls | wc -l", "cat data/policy.md > work/x", "ls; ls", "ls && ls", "ls || ls", "ls &", "ls 2>&1",
    "cat data/policy.md >work/x", "cat /etc/passwd", "ls ..", "cat {up}/etc/passwd", "python3 mail.py log", "python3 mail.py stats",
    "python3 mail.py send --from extractor --to auditor --file /etc/hostname", "python3 mail.py open --me extractor /etc/hostname",
    "grep -r Northfield data", "grep -rn Northfield data", "ls -R", "ls -lR data", "find . -name x", "env", "echo hi",
    "python3 mail.py", "python3 mail.py nonsense", "",
    # an agent is itself: it cannot send as the principal or another agent, or take another agent's mail
    "python3 mail.py send --from human --to extractor -m x", "python3 mail.py send --from=human --to auditor -m x",
    "python3 mail.py send --fro reconciler --to auditor -m x", "python3 mail.py read --me auditor",
    "python3 mail.py open --me reconciler data/policy.md",
])
def test_shell_refuses(tmp_path, cmd):
    run = make_run(tmp_path)
    cmd = cmd.replace("{up}", os.path.relpath("/", run))          # enough ".." to reach the real /etc/passwd from here
    r = agent.Sandbox(run, "extractor").call("shell", {"cmd": cmd})
    assert r.error, cmd
    assert r.refused or cmd == "", (cmd, r.text)


def test_shell_details(tmp_path):
    run = make_run(tmp_path)
    sb = agent.Sandbox(run, "extractor")
    assert sb.call("shell", {"cmd": "python3 -c 'print(6 * 7)'"}).text.strip() == "42"
    r = sb.call("shell", {"cmd": "python3 -c 'import sys; print(\"boom\", file=sys.stderr); sys.exit(3)'"})
    assert r.error and not r.refused and "boom" in r.text and "[exit status 3]" in r.text
    assert sb.call("shell", {"cmd": "grep -c zzzzz data/policy.md"}).error          # no match: exit 1, but not refused
    assert sb.call("shell", {"cmd": "cat"}).text == "(no output)"                    # stdin is closed, so this returns at once
    assert sb.call("shell", {"cmd": 'python3 -c "print(1)" "unterminated'}).text.startswith("error: could not parse")
    # quoted message bodies may contain shell characters: there is no shell to interpret them
    sent = sb.call("shell", {"cmd": 'python3 mail.py send --from extractor --to auditor -m "a; b | c > d && $HOME `x` \\"q\\""'})
    assert not sent.error and sent.text.startswith("SENT #2")
    assert log_records(run)[-1]["body"] == 'a; b | c > d && $HOME `x` "q"'
    slow = agent.Sandbox(run, "extractor", shell_timeout=1)
    assert "timed out after 1 s" in slow.call("shell", {"cmd": "python3 -c 'import time; time.sleep(5)'"}).text
    off = agent.Sandbox(run, "extractor", allow_python_c=False)
    assert off.call("shell", {"cmd": "python3 -c 'print(1)'"}).refused
    assert sb.call("shell", {"cmd": None}).error and sb.call("nonsense", {}).error and sb.call("shell", ["cat"]).error


def test_shell_children_never_see_keys_or_proxies(tmp_path, monkeypatch):
    for k in ("RW_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "HTTPS_PROXY", "https_proxy", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(k, SENTINEL)
    r = agent.Sandbox(make_run(tmp_path), "extractor").call("shell", {"cmd": "python3 -c 'import os,json; print(json.dumps(dict(os.environ)))'"})
    assert SENTINEL not in r.text
    env = json.loads(r.text)
    assert "PATH" in env and env["PYTHONUTF8"] == "1"
    assert orchestrate.agent_mod.child_env().keys() <= set(agent.ENV_KEEP) | {"PYTHONIOENCODING", "PYTHONUTF8", "PYTHONDONTWRITEBYTECODE"}


def test_mail_calls_are_serialised(tmp_path):
    """Eight threads hammering mail.py at once must not lose a message or reuse a sequence number. (mail.py's `read`
    rewrites the whole log and `send` numbers by reading it; without the per-run lock this test fails.)"""
    run = make_run(tmp_path)
    lock = threading.Lock()
    boxes = [agent.Sandbox(run, r, lock) for r in ("extractor", "reconciler", "scheduler", "auditor")]
    errors = []

    def worker(i):
        sb = boxes[i % 4]
        for k in range(2):
            to = "human" if sb.role != "auditor" else "extractor"
            r = sb.call("shell", {"cmd": f'python3 mail.py send --from {sb.role} --to {to} -m "m {i} {k}"'})
            r2 = sb.call("shell", {"cmd": f"python3 mail.py read --me {sb.role}"})
            if r.error or r2.error:
                errors.append((r.text, r2.text))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    bodies = sorted(r["body"] for r in log_records(run) if r["kind"] == "msg")
    assert bodies == sorted(["Please prepare the run."] + [f"m {i} {k}" for i in range(8) for k in range(2)])     # none lost
    seqs = [r["seq"] for r in log_records(run) if r["kind"] == "msg"]
    assert seqs == list(range(1, 18))                     # kickoff + 16 sends, in order, none reused


# ---------------------------------------------------------------- the agent loop

def test_the_turn_limit_answers_every_tool_call(tmp_path):
    run = make_run(tmp_path)
    one_batch = [[{"tool_calls": [call("list_dir")] * 45}]]
    a = agent.Agent("extractor", run, mock_model(tmp_path, {"extractor": one_batch}))
    rec = a.turn()
    assert rec["ended_by"] == "tool_limit" and rec["tool_calls"] == 40 and rec["calls"] == 1
    calls = a.messages[2]["tool_calls"]
    results = [m for m in a.messages if m["role"] == "tool"]
    assert len(calls) == len(results) == 45 and [r["tool_call_id"] for r in results] == [c["id"] for c in calls]
    assert sum(r["content"].startswith("not executed") for r in results) == 5

    a2 = agent.Agent("extractor", run, mock_model(tmp_path, {"extractor": [[{"tool_calls": [call("list_dir")]}] * 60]}, "s2.json"))
    rec = a2.turn()
    assert rec["ended_by"] == "tool_limit" and rec["tool_calls"] == 40 and rec["calls"] == 40


def test_done_ends_the_turn_even_mid_batch_and_the_conversation_persists(tmp_path):
    run = make_run(tmp_path)
    script = {"extractor": [[{"tool_calls": [call("list_dir"), call("done"), call("list_dir")]}],
                            [{"tool_calls": [call("list_dir", path="data")]}, {"content": "DONE"}]]}
    a = agent.Agent("extractor", run, mock_model(tmp_path, script))
    first = a.turn(round_no=1)
    assert first["ended_by"] == "done" and first["tool_calls"] == 2
    assert a.messages[-1]["content"].startswith("not executed")
    second = a.turn(round_no=2)
    assert second["ended_by"] == "text" and (second["turn"], second["round"]) == (2, 2)
    users = [m["content"] for m in a.messages if m["role"] == "user"]
    assert users == ["mail", "mail"] and a.messages[0]["role"] == "system"
    assert a.messages[0]["content"] == (run / "prompts" / "extractor.md").read_text()      # the role file, verbatim


def test_bad_tool_calls_come_back_as_errors(tmp_path):
    run = make_run(tmp_path)
    script = {"extractor": [[{"tool_calls": [{"name": "read_file", "arguments": "{not json"}, call("no_such_tool"),
                                             {"name": "read_file", "arguments": ["x"]}, call("write_file", path="work/a.txt"),
                                             call("read_file", path=3)]},
                             {"content": "DONE"}]]}
    a = agent.Agent("extractor", run, mock_model(tmp_path, script))
    rec = a.turn()
    results = [m["content"] for m in a.messages if m["role"] == "tool"]
    assert results[0].startswith("error: arguments are not valid JSON")
    assert results[1].startswith("error: unknown tool 'no_such_tool'")
    assert results[2].startswith("error: arguments must be a JSON object")
    assert results[3] == "error: content must be a string"
    assert results[4] == "error: path must be a non-empty string"
    assert rec["tool_errors"] == 5 and rec["ended_by"] == "text"


def test_context_cap_drops_the_oldest_tool_results_only():
    def turn_pair(i):
        return [{"role": "assistant", "content": None, "tool_calls": [{"id": f"c{i}", "type": "function", "function": {"name": "shell", "arguments": "{}"}}]},
                {"role": "tool", "tool_call_id": f"c{i}", "content": f"result {i} " + "x" * 9990}]
    messages = [{"role": "system", "content": "S" * 5000}, {"role": "user", "content": "mail"}]
    for i in range(20):
        messages += turn_pair(i)
    before_tail = [dict(m) for m in messages[-20:]]
    assert sum(agent.message_chars(m) for m in messages) > 150_000
    dropped = agent.cap_context(messages, 150_000, 20)
    assert dropped > 0 and sum(agent.message_chars(m) for m in messages) <= 150_000
    assert messages[0]["content"] == "S" * 5000 and messages[-20:] == before_tail       # system prompt and last 20 untouched
    tools = [m for m in messages if m["role"] == "tool"]
    gone = [m for m in tools if m["content"] == agent.DROPPED]
    assert gone == tools[:len(gone)]                                                    # the oldest ones went first
    assert [m["tool_call_id"] for m in tools] == [f"c{i}" for i in range(20)]           # ids stay paired
    assert agent.cap_context(messages, 150_000, 20) == 0                                # nothing more to do
    small = [{"role": "system", "content": "s"}, {"role": "user", "content": "mail"}]
    assert agent.cap_context(small, 150_000, 20) == 0


def test_the_cap_is_applied_before_each_model_call(tmp_path):
    run = make_run(tmp_path)
    big = "x" * 30_000
    (run / "work" / "big.txt").write_text(big)
    script = {"extractor": [[{"tool_calls": [call("read_file", path="work/big.txt")]}] * 12 + [{"content": "DONE"}]]}
    sizes = []

    def spy(messages, tools, model):                       # what the model is actually sent, call by call
        sizes.append(sum(agent.message_chars(m) for m in messages))
        return llm.chat(messages, tools, model)

    a = agent.Agent("extractor", run, mock_model(tmp_path, script), context_chars=100_000, keep_last=4, chat_fn=spy)
    rec = a.turn()
    assert rec["ended_by"] == "text" and len(sizes) == 13
    assert max(sizes) <= 100_000                            # twelve 30k results, yet no call was sent more than the cap
    assert sizes[2] > 60_000 and sizes[-1] > 60_000         # ... and the recent results are still there
    results = [m["content"] for m in a.messages if m["role"] == "tool"]
    assert results[0] == agent.DROPPED and results[-1] == big and results[-2] == big
    assert len(results) == 12 and len(a.messages) == 2 + 2 * 12 + 1                   # dropped, not deleted: the pairing is intact


def test_mock_scripts_are_per_agent_and_stateless(tmp_path):
    model = mock_model(tmp_path, {"extractor": [[{"content": "E1"}]], "auditor": [[{"content": "A1"}]], "*": [[{"content": "ANY"}]]})
    def ask(role):
        msg, _, u = llm.chat([{"role": "system", "content": f"You are the **{role}** agent"}, {"role": "user", "content": "mail"}], [], model)
        return msg["content"], u
    assert ask("extractor")[0] == "E1" and ask("auditor")[0] == "A1" and ask("scheduler")[0] == "ANY"
    _, u = ask("extractor")
    assert u["estimated"] is True and u["prompt_tokens"] > 0 and u["model"] == model


# ---------------------------------------------------------------- the providers

class FakeServer:
    """A stand-in provider on 127.0.0.1. `responses` is consumed first (status, payload, headers); then `default`."""

    def __init__(self, default):
        self.requests: list[dict] = []
        self.responses: list[tuple] = []
        self.default = default
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                outer.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                                       "body": json.loads(self.rfile.read(n) or b"{}")})
                status, payload, headers = outer.responses.pop(0) if outer.responses else (200, outer.default, {})
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


OPENAI_REPLY = {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "reasoning": "thinking",
                "tool_calls": [{"id": "call_a", "type": "function", "index": 0, "function": {"name": "shell", "arguments": "{\"cmd\": \"ls\"}"}},
                               {"id": "call_a", "type": "function", "index": 1, "function": {"name": "done", "arguments": ""}}]}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10, "prompt_tokens_details": {"cached_tokens": 64},
                          "completion_tokens_details": {"reasoning_tokens": 3}, "cost": 0.0012}}
ANTHROPIC_REPLY = {"type": "message", "role": "assistant", "stop_reason": "tool_use",
                   "content": [{"type": "thinking", "thinking": "hm", "signature": "sig"}, {"type": "text", "text": "listing"},
                               {"type": "tool_use", "id": "toolu_1", "name": "shell", "input": {"cmd": "ls"}}],
                   "usage": {"input_tokens": 5, "output_tokens": 7, "cache_read_input_tokens": 90, "cache_creation_input_tokens": 10}}
TOOLS = agent.TOOLS
CONVERSATION = [
    {"role": "system", "content": "You are the **extractor**."},
    {"role": "user", "content": "mail"},
    {"role": "assistant", "content": "reading", "_reasoning": "private",
     "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "shell", "arguments": "{\"cmd\": \"ls\"}"}},
                    {"id": "call_2", "type": "function", "function": {"name": "list_dir", "arguments": "{}"}}]},
    {"role": "tool", "tool_call_id": "call_1", "content": "data", "_error": False, "_tool": "shell"},
    {"role": "tool", "tool_call_id": "call_2", "content": "boom", "_error": True, "_tool": "list_dir"},
    {"role": "user", "content": "mail"},
]


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(llm, "_sleep", slept.append)
    return slept


def test_openai_compatible_adapter(monkeypatch):
    srv = FakeServer(OPENAI_REPLY)
    try:
        monkeypatch.setenv("RW_BASE_URL", f"http://127.0.0.1:{srv.port}/v1")
        monkeypatch.setenv("RW_API_KEY", SENTINEL)
        monkeypatch.setenv("RW_MAX_TOKENS", "999")
        monkeypatch.setenv("RW_EXTRA_BODY", '{"reasoning_effort": "low"}')
        msg, calls, usage = llm.chat(CONVERSATION, TOOLS, "openai:gpt-5.6")
    finally:
        srv.close()
    req = srv.requests[0]
    assert req["path"] == "/v1/chat/completions" and req["headers"]["authorization"] == f"Bearer {SENTINEL}"
    body = req["body"]
    assert body["model"] == "gpt-5.6" and body["max_tokens"] == 999 and body["reasoning_effort"] == "low"
    assert body["tools"][:4] == TOOLS[:4]
    assert body["tools"][4] == {"type": "function", "function": {"name": "done", "description": TOOLS[4]["function"]["description"]}}
    assert "parameters" in TOOLS[4]["function"]                                       # the shared definition is not altered
    assert "temperature" not in body and "tool_choice" not in body
    assert [m["role"] for m in body["messages"]] == ["system", "user", "assistant", "tool", "tool", "user"]
    assert all(set(m) <= {"role", "content", "tool_calls", "tool_call_id"} for m in body["messages"])     # no private keys
    assert body["messages"][2]["tool_calls"][1]["function"]["arguments"] == "{}"
    # response: ids made unique, empty arguments read as {}, usage normalised
    assert [(c["id"], c["name"], c["arguments"], c["error"]) for c in calls] == [
        ("call_a", "shell", {"cmd": "ls"}, None), ("call_a_2", "done", {}, None)]
    assert msg["role"] == "assistant" and msg["content"] is None and [t["id"] for t in msg["tool_calls"]] == ["call_a", "call_a_2"]
    assert msg["_reasoning"] == "thinking" and "index" not in msg["tool_calls"][0]
    assert (usage["prompt_tokens"], usage["completion_tokens"], usage["cached_tokens"], usage["reasoning_tokens"], usage["cost"]) == (100, 10, 64, 3, 0.0012)
    assert usage["estimated"] is False and usage["finish_reason"] == "tool_calls" and usage["attempts"] == 1


def test_openai_max_completion_tokens_and_temperature_for_openai_itself(monkeypatch):
    monkeypatch.setenv("RW_MAX_TOKENS", "50")
    monkeypatch.setenv("RW_TEMPERATURE", "0.2")
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL)
    seen = {}
    monkeypatch.setattr(llm, "_post_json", lambda url, headers, payload, timeout: seen.update(url=url, headers=headers, payload=payload) or OPENAI_REPLY)
    llm.chat(CONVERSATION[:2], [], "openai:gpt-5.6")
    assert seen["url"] == "https://api.openai.com/v1/chat/completions" and seen["headers"] == {"Authorization": f"Bearer {SENTINEL}"}
    assert seen["payload"]["max_completion_tokens"] == 50 and "max_tokens" not in seen["payload"] and seen["payload"]["temperature"] == 0.2
    assert "tools" not in seen["payload"]                                             # none offered, none sent


def test_key_and_endpoint_resolution(monkeypatch):
    def resolve(provider):
        return llm._resolve_compat(provider)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    assert resolve("openrouter") == ("https://openrouter.ai/api/v1/chat/completions", "or-key", "openrouter.ai")
    with pytest.raises(llm.LLMError, match="no API key for api.openai.com"):
        resolve("openai")                                                             # an OpenRouter key is never sent to OpenAI
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    assert resolve("openai")[1:] == ("oa-key", "api.openai.com")
    assert resolve("openrouter")[1] == "or-key"
    monkeypatch.setenv("RW_API_KEY", "rw-key")
    assert resolve("openai")[1] == "rw-key" and resolve("openrouter")[1] == "rw-key"
    monkeypatch.setenv("RW_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    assert resolve("compat") == ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "rw-key", "generativelanguage.googleapis.com")
    monkeypatch.delenv("RW_API_KEY")
    with pytest.raises(llm.LLMError, match="set RW_API_KEY"):
        resolve("compat")                                                             # no other provider's key goes to a third host
    monkeypatch.setenv("RW_BASE_URL", "http://localhost:11434/v1")
    assert resolve("compat") == ("http://localhost:11434/v1/chat/completions", None, "localhost")   # Ollama needs none
    monkeypatch.delenv("RW_BASE_URL")
    with pytest.raises(llm.LLMError, match="needs RW_BASE_URL"):
        resolve("compat")
    monkeypatch.setenv("RW_BASE_URL", "ftp://x")
    with pytest.raises(llm.LLMError, match="not a valid http"):
        resolve("openai")
    monkeypatch.setenv("RW_BASE_URL", "https://user:pw@example.com/v1")
    assert "pw" not in llm._safe_url("https://user:pw@example.com/v1")


def test_retries_honour_retry_after_and_give_up(monkeypatch, no_sleep):
    srv = FakeServer(OPENAI_REPLY)
    try:
        monkeypatch.setenv("RW_BASE_URL", f"http://127.0.0.1:{srv.port}/v1")
        monkeypatch.setenv("RW_API_KEY", SENTINEL)
        srv.responses = [(429, {"error": {"message": "slow down"}}, {"Retry-After": "7"}),
                         (503, b"<html>upstream</html>", {}), (200, {"error": {"message": "x", "code": 502}}, {})]
        _, _, usage = llm.chat(CONVERSATION[:2], [], "openai:m")
        assert usage["attempts"] == 4 and len(srv.requests) == 4
        assert no_sleep[0] >= 7 and len(no_sleep) == 3
        no_sleep.clear()
        monkeypatch.setenv("RW_RETRIES", "3")
        srv.responses = [(500, {"error": {"message": "down"}}, {})] * 5
        with pytest.raises(llm.LLMError, match=r"HTTP 500.*down.*gave up after 3 attempts"):
            llm.chat(CONVERSATION[:2], [], "openai:m")
        assert len(no_sleep) == 2 and no_sleep[1] > no_sleep[0] * 0.9                 # backing off
    finally:
        srv.close()


def test_a_client_error_is_not_retried_and_the_key_is_redacted(monkeypatch, no_sleep):
    srv = FakeServer(OPENAI_REPLY)
    try:
        monkeypatch.setenv("RW_BASE_URL", f"http://127.0.0.1:{srv.port}/v1")
        monkeypatch.setenv("RW_API_KEY", SENTINEL)
        srv.responses = [(401, {"error": {"message": f"Incorrect API key provided: {SENTINEL}. Bearer abcdefghijkl"}}, {})]
        with pytest.raises(llm.LLMError) as e:
            llm.chat(CONVERSATION[:2], [], "openai:m")
    finally:
        srv.close()
    assert len(srv.requests) == 1 and not no_sleep and e.value.status == 401 and e.value.retryable is False
    assert SENTINEL not in str(e.value) and "abcdefghijkl" not in str(e.value) and "***" in str(e.value)
    # key-shaped strings that are not in the environment are masked too
    shaped = "rejected " + "sk-" + "proj0123456789abcdef and " + "Bear" + "er 0123456789abcdefghij"      # built here, so no scanner sees a key
    assert "0123456789abcdef" not in llm._redact(shaped) and "rejected" in llm._redact(shaped)


def test_a_dead_endpoint_is_retried_then_reported(monkeypatch, no_sleep):
    srv = FakeServer(OPENAI_REPLY)
    port = srv.port
    srv.close()
    monkeypatch.setenv("RW_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setenv("RW_RETRIES", "3")
    with pytest.raises(llm.LLMError, match="network error.*gave up after 3 attempts"):
        llm.chat(CONVERSATION[:2], [], "compat:m")
    assert len(no_sleep) == 2


def test_missing_usage_is_estimated_and_bad_arguments_are_flagged(monkeypatch):
    reply = {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}],
                                                               "tool_calls": [{"id": "", "type": "function",
                                                                               "function": {"name": "shell", "arguments": "{oops"}}]}}]}
    srv = FakeServer(reply)
    try:
        monkeypatch.setenv("RW_BASE_URL", f"http://127.0.0.1:{srv.port}/v1")
        monkeypatch.setenv("RW_API_KEY", "k")
        msg, calls, usage = llm.chat(CONVERSATION, TOOLS, "openrouter:x/y")
    finally:
        srv.close()
    assert usage["estimated"] is True and usage["prompt_tokens"] > 0 and usage["cached_tokens"] is None
    assert msg["content"] == "hi" and calls[0]["id"] == "call_1" and calls[0]["arguments"] is None
    assert "not valid JSON" in calls[0]["error"] and msg["tool_calls"][0]["function"]["arguments"] == "{oops"


def test_anthropic_adapter(monkeypatch):
    srv = FakeServer(ANTHROPIC_REPLY)
    try:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{srv.port}")
        monkeypatch.setenv("ANTHROPIC_API_KEY", SENTINEL)
        msg, calls, usage = llm.chat(CONVERSATION, TOOLS, "anthropic:claude-sonnet-4-6")
        monkeypatch.setenv("RW_ANTHROPIC_CACHE", "0")
        llm.chat(CONVERSATION, TOOLS, "anthropic:claude-sonnet-4-6")
    finally:
        srv.close()
    req = srv.requests[0]
    assert req["path"] == "/v1/messages" and req["headers"]["x-api-key"] == SENTINEL and req["headers"]["anthropic-version"] == "2023-06-01"
    body = req["body"]
    assert body["model"] == "claude-sonnet-4-6" and body["max_tokens"] == 16000
    assert body["system"] == [{"type": "text", "text": "You are the **extractor**.", "cache_control": {"type": "ephemeral"}}]
    assert body["tools"][0] == {"name": "read_file", "description": TOOLS[0]["function"]["description"],
                                "input_schema": TOOLS[0]["function"]["parameters"]}
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant", "user"]                                     # alternating; results merged into one turn
    assistant = body["messages"][1]["content"]
    assert [b["type"] for b in assistant] == ["text", "tool_use", "tool_use"] and assistant[1]["input"] == {"cmd": "ls"}
    last = body["messages"][2]["content"]
    assert [b["type"] for b in last] == ["tool_result", "tool_result", "text"]        # tool results first, then the new mail
    assert last[0] == {"type": "tool_result", "tool_use_id": "call_1", "content": "data"}
    assert last[1]["is_error"] is True and last[2]["text"] == "mail" and last[2]["cache_control"] == {"type": "ephemeral"}
    assert not any(f'"{k}"' in json.dumps(body) for k in ("_error", "_tool", "_dropped", "_reasoning", "tool_call_id"))   # bookkeeping stays home
    assert "cache_control" not in json.dumps(srv.requests[1]["body"])                 # RW_ANTHROPIC_CACHE=0
    assert [(c["id"], c["name"], c["arguments"]) for c in calls] == [("toolu_1", "shell", {"cmd": "ls"})]
    assert msg == {"role": "assistant", "content": "listing", "tool_calls": [
        {"id": "toolu_1", "type": "function", "function": {"name": "shell", "arguments": "{\"cmd\": \"ls\"}"}}],
        "_thinking_blocks": [{"type": "thinking", "thinking": "hm", "signature": "sig"}]}
    # Anthropic reports uncached input separately; the harness reports all input like OpenAI does
    assert (usage["prompt_tokens"], usage["completion_tokens"], usage["cached_tokens"], usage["cache_write_tokens"]) == (105, 7, 90, 10)
    assert usage["finish_reason"] == "tool_use"


def test_anthropic_thinking_blocks_go_back_first_and_only_to_anthropic(monkeypatch):
    thinking = [{"type": "thinking", "thinking": "hm", "signature": "sig"}, {"type": "redacted_thinking", "data": "abc"}]
    convo = [CONVERSATION[0], CONVERSATION[1],
             {"role": "assistant", "content": "reading", "_thinking_blocks": thinking,
              "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "shell", "arguments": "{\"cmd\": \"ls\"}"}}]},
             {"role": "tool", "tool_call_id": "call_1", "content": "data"}]
    _, msgs = llm._to_anthropic(convo)
    blocks = msgs[1]["content"]
    assert [b["type"] for b in blocks] == ["thinking", "redacted_thinking", "text", "tool_use"] and blocks[:2] == thinking
    assert blocks[:2] is not thinking and "cache_control" not in json.dumps(blocks)      # copied, so the stored message stays clean
    assert all("_thinking_blocks" not in m for m in llm._oa_messages(convo, "openrouter.ai"))
    srv = FakeServer(ANTHROPIC_REPLY)
    try:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{srv.port}")
        monkeypatch.setenv("ANTHROPIC_API_KEY", SENTINEL)
        llm.chat(convo, TOOLS, "anthropic:claude-sonnet-4-6")
    finally:
        srv.close()
    assert srv.requests[0]["body"]["messages"][1]["content"][:2] == thinking


def test_provider_errors_are_clear(monkeypatch):
    with pytest.raises(llm.LLMError, match="must look like provider:name"):
        llm.chat([], [], "gpt-5.6")
    with pytest.raises(llm.LLMError, match="unknown provider 'bedrock'"):
        llm.chat([], [], "bedrock:x")
    with pytest.raises(llm.LLMError, match="ANTHROPIC_API_KEY is not set"):
        llm.chat([{"role": "user", "content": "x"}], [], "anthropic:claude-sonnet-4-6")
    with pytest.raises(llm.LLMError, match="not readable"):
        llm.chat([], [], "mock:/nonexistent.json")
    for bad in ("openrouter:openai/gpt-5.6", "anthropic:claude-sonnet-4-6", "compat:x"):
        with pytest.raises(llm.LLMError):
            llm.preflight(bad)                                                        # no key: fails before a run is built
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    llm.preflight("openrouter:openai/gpt-5.6")
    assert llm.endpoint_host("openrouter:openai/gpt-5.6") == "openrouter.ai" and llm.endpoint_host("anthropic:x") == "api.anthropic.com"
    assert llm.endpoint_host("mock:x.json") == "mock"


# ---------------------------------------------------------------- build, principal, grid (in a private copy of month-end)

L_QUESTION = ("RW1 AQ extractor-01 from=extractor to=human p=pay need=ENUM opts=APPROVE+DECLINE by=20261001 item=inv:INV-000491 "
              "sup=northfield amt=378.60 cur=GBP kind=GROSS // Pay the corrected invoice?")


def l_script(extra_principal=None) -> dict:
    agents = {"extractor": [[{"tool_calls": [sh("python3 mail.py read --me extractor")], "usage": use(10, 1)},
                             {"tool_calls": [sh(f"python3 mail.py send --from extractor --to human -m '{L_QUESTION}'")], "usage": use(20, 2)},
                             {"tool_calls": [call("done")], "usage": use(30, 1)}],
                            [{"tool_calls": [sh("python3 mail.py read --me extractor")], "usage": use(40, 1)},
                             {"tool_calls": [call("done")], "usage": use(50, 1)}]]}
    if extra_principal:
        agents["principal"] = extra_principal
    return {"agents": agents}


def test_build_run_principal_gap_and_model_answer(tmp_path):
    me = make_month_end(tmp_path)
    real_runs = sorted(p.name for p in (MONTH_END / "runs").iterdir())
    script = tmp_path / "l.json"
    script.write_text(json.dumps(l_script([[{"content": '{"val": "HOLD", "tail": "not an option"}'}],
                                            [{"content": 'Sure: {"val": "decline", "tail": "Decide it yourselves under the policy."}'}]])))
    model = f"mock:{script}"

    # 1. no principal model: the off-script question is flagged, not sent, and the run stalls with it on record
    code = orchestrate.main(["--build", "L", "1", "--model", model, "--month-end", str(me), "--no-grade"])
    run = me / "runs" / "L1"
    assert code == 1 and (run / "harness" / "config.json").exists()
    rounds = json.loads((run / "rounds.json").read_text())
    assert rounds["stop"] == "stalled" and rounds["rounds"] == 1 and rounds["auditor_reported"] is False
    assert rounds["principal_unanswered"][0]["from"] == "extractor" and "no matching option" not in rounds["principal_unanswered"][0]["lines"][0]
    assert not [r for r in log_records(run) if r["kind"] == "msg" and r["from"] == "human" and r["body"].startswith("RW1 AN")]
    assert [r["seq"] for r in log_records(run) if r["kind"] == "msg"] == [1, 2]      # the kickoff and the question, no answer
    cfg = json.loads((run / "run.json").read_text())
    assert cfg["harness"]["model"] == model and cfg["model"] == model and (run / "grade.json").exists() is False   # built with --model

    # 2. with a principal model: it picks one of the offered options (the first attempt was not one), and the agent gets it
    code = orchestrate.main(["--build", "L", "2", "--model", model, "--principal-model", model, "--month-end", str(me)])
    run = me / "runs" / "L2"
    rounds = json.loads((run / "rounds.json").read_text())
    assert code == 1 and rounds["stop"] == "stalled" and rounds["rounds"] == 2 and rounds["principal_unanswered"] == []
    answers = [r for r in log_records(run) if r["kind"] == "msg" and r["from"] == "human" and r["to"] == "extractor" and r["body"].startswith("RW1 AN")]
    assert len(answers) == 1 and answers[0]["kind"] == "msg" and "rejected" not in answers[0]
    line = answers[0]["body"]
    assert line.startswith("RW1 AN human-") and " re=extractor-01 " in line and " val=DECLINE " in line and " item=inv:INV-000491 " in line
    usage = json.loads((run / "usage.json").read_text())
    assert usage["principal"]["calls"] == 2 and usage["total"]["calls"] == usage["agents"]["extractor"]["total"]["calls"] + 2
    assert [t["ended_by"] for t in usage["agents"]["extractor"]["turns"]] == ["done", "done"]
    assert json.loads((run / "grade.json").read_text())["run"] == "L2"                # grade.py was called

    # nothing outside the private copy was touched
    assert sorted(p.name for p in (MONTH_END / "runs").iterdir()) == real_runs


def test_scenario_two_runs_against_the_stateful_scripted_principal(tmp_path):
    """--build A 1 --scenario 2: the principal first approves the wrong amount and corrects it when pushed back."""
    me = make_month_end(tmp_path)
    ask = "Marlow Design invoice MD-2026-057 is 5400.00 GBP, over the approval threshold. Do you approve paying it in this run?"
    push = "MD-2026-057: the refund is in the bank feed, so the full amount 5400.00 GBP is payable. Please confirm you approve it."
    read = sh("python3 mail.py read --me extractor")
    model = mock_model(tmp_path, {"extractor": [
        [{"tool_calls": [read]}, {"tool_calls": [sh(f'python3 mail.py send --from extractor --to human -m "{ask}"')]}, {"tool_calls": [call("done")]}],
        [{"tool_calls": [read]}, {"tool_calls": [sh(f'python3 mail.py send --from extractor --to human -m "{push}"')]}, {"tool_calls": [call("done")]}],
        [{"tool_calls": [read]}, {"tool_calls": [call("done")]}]]})
    code = orchestrate.main(["--build", "A", "1", "--scenario", "2", "--model", model, "--month-end", str(me), "--no-grade"])
    run = me / "runs" / "A1s2"
    assert code == 1                                                                  # the auditor never reported
    rounds = json.loads((run / "rounds.json").read_text())
    assert rounds["stop"] == "stalled" and rounds["rounds"] == 3 and rounds["error"] is None
    replies = [r["body"] for r in log_records(run) if r["kind"] == "msg" and r["from"] == "human" and r["seq"] > 1]
    assert len(replies) == 2 and "5100.00" in replies[0] and "full amount" in replies[1]
    assert json.loads((run / "principal_state.json").read_text()) == {"appr_wrong_sent": True, "appr_corrected": True}
    assert json.loads((run / "run.json").read_text())["scenario"] == 2
    assert [t["round"] for t in json.loads((run / "usage.json").read_text())["agents"]["extractor"]["turns"]] == [1, 2, 3]


def test_grid_builds_fresh_runs_and_numbers_them_after_existing_ones(tmp_path, capsys):
    me = make_month_end(tmp_path)
    (me / "runs").mkdir()
    (me / "runs" / "A1").mkdir()                                                      # an earlier (Claude) run is never reused
    (me / "runs" / "D2s2").mkdir()
    assert orchestrate.free_numbers(me / "runs", "A", 1, 2, None) == [2, 3]
    assert orchestrate.free_numbers(me / "runs", "D", 2, 2, None) == [1, 3]
    assert orchestrate.free_numbers(me / "runs", "L", 1, 2, 5) == [5, 6]
    model = mock_model(tmp_path, {})
    summary = tmp_path / "grid.json"
    code = orchestrate.main(["--grid", "A, d", "--runs", "2", "--model", model, "--month-end", str(me), "--summary", str(summary),
                             "--max-rounds", "1", "--no-grade", "--jobs", "2"])
    out = capsys.readouterr().out
    assert code == 1                                                                  # nothing completed: agents never read mail
    assert sorted(p.name for p in (me / "runs").iterdir()) == ["A1", "A2", "A3", "D1", "D2", "D2s2"]
    doc = json.loads(summary.read_text())
    assert [r["run"] for r in doc["results"]] == ["A2", "A3", "D1", "D2"] and doc["arms"] == ["A", "D"] and doc["runs_per_arm"] == 2
    assert all(r["stop"] == "max_rounds" and r["rounds"] == 1 for r in doc["results"]) and "run  arm  stop" in out
    assert (me / "runs" / "A2" / "harness" / "transcripts" / "extractor.jsonl").exists()


def test_command_line_checks(tmp_path, capsys):
    me = make_month_end(tmp_path)
    for argv in (["--grid", "A,X", "--model", "mock:x"], ["--grid", "A", "--model", "mock:x", "--runs", "0"],
                 ["--run", "x", "--model", "mock:x", "--runs", "2"], ["--run", "x", "--model", "mock:x", "--scenario", "2"],
                 ["--build", "Z", "1", "--model", "mock:x"], ["--model", "mock:x"], ["--run", "x", "--build", "A", "1", "--model", "m"]):
        with pytest.raises(SystemExit) as e:
            orchestrate.main(argv + ["--month-end", str(me)])
        assert e.value.code == 2, argv
    with pytest.raises(SystemExit, match="no run directory at nowhere"):
        orchestrate.main(["--run", "nowhere", "--model", "mock:x", "--month-end", str(me)])
    with pytest.raises(SystemExit, match="cannot use openai:gpt-5.6: no API key"):
        orchestrate.main(["--grid", "A", "--model", "openai:gpt-5.6", "--month-end", str(me)])
    assert not (me / "runs").exists()                                                # failed before anything was built
