#!/usr/bin/env python3
"""Writes the integration guide and the files machines read, from one source.

  python3 app/tools/start.py      # then run app/tools/stamp.py

Writes, under app/static:
  quickstart.html   /quickstart, the guide for a developer or the coding agent working for one
  quickstart.md     /quickstart.md, the same guide as Markdown
  llms.txt          /llms.txt, what rogerwilco is and where each thing is, for a model reading the site
  llms-full.txt     /llms-full.txt, the guide, the skill and the spec in one file, for a model integrating it
  robots.txt, sitemap.xml

Every output printed in the guide is computed here by running the code it follows, against the codec in this repo,
so the page cannot drift from the library. The full example is examples/payment.py, read from disk and run.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATIC = REPO / "app" / "static"
SITE = "https://rogerwilco.crox.io"
sys.path.insert(0, str(REPO))
import rogerwilco as rw  # noqa: E402

P = "pay"
EXAMPLE = (REPO / "examples" / "payment.py").read_text(encoding="utf-8")


def run_example(*args: str) -> str:
    r = subprocess.run([sys.executable, str(REPO / "examples" / "payment.py"), *args], capture_output=True, text=True,
                       env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"})
    return r.stdout.strip()


# ---------------------------------------------------------------- the values the guide prints, computed
RECORD = {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP",
          "kind": "GROSS", "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}
HO = rw.encode({"type": "HO", "id": "scheduler-1", "from": "scheduler", "to": "payer", "item": RECORD["item"],
                "slots": {"p": P, "rb": ["exec"], **{k: v for k, v in RECORD.items() if k not in ("to", "item")}}}, P)
HO_BAD = HO.replace("61102938", "61102983")
CHECK_HO_BAD = rw.check_ho(HO_BAD, RECORD, P)[0]
VALUES = {k: RECORD[k] for k in ("sup", "amt", "cur", "kind", "acct", "paid", "ref", "apref")}
STATEMENT = rw.encode({"type": "RB", "id": "payer-1", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                       "item": RECORD["item"], "slots": {"p": P, "ask": "PAY", "h": rw.digest(HO, P), **VALUES}}, P)
STATEMENT_BAD = STATEMENT.replace("61102938", "61102983")
CHECK_RB_BAD = rw.check_rb_full(HO, STATEMENT_BAD, P)[0]
DN = rw.encode({"type": "DN", "id": "payer-2", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                "item": RECORD["item"], "slots": {"p": P, "out": "OK", **VALUES}}, P)
DN_BAD = DN.replace("amt=5400.00", "amt=5100.00")
CHECK_DN_BAD = rw.check_dn(HO, DN_BAD, P, rb_line=STATEMENT)[0]
MAKE_RB = rw.make_rb(HO, "payer-1", P)
assert not rw.check_ho(HO, RECORD, P)[0] and not rw.check_rb_full(HO, STATEMENT, P)[0]
assert not rw.check_dn(HO, DN, P, rb_line=STATEMENT)[0] and CHECK_HO_BAD and CHECK_RB_BAD and CHECK_DN_BAD
RUN_OK, RUN_FAULT, RUN_CANCEL = run_example(), run_example("--fault"), run_example("--cancel")
assert RUN_CANCEL.startswith("cancelled:")
assert RUN_OK.startswith("roger, wilco") and RUN_FAULT.startswith("held:")
LEGEND_HEAD = "\n".join(rw.legend(P).splitlines()[:3]) + "\n..."

SNIP_HO = f'''import rogerwilco as rw

record = {json.dumps(RECORD)}   # the approved record, from your database

ho = rw.encode({{"type": "HO", "id": "scheduler-1", "from": "scheduler", "to": "payer", "item": record["item"],
                "slots": {{"p": "pay", "rb": ["exec"], **{{k: v for k, v in record.items() if k not in ("to", "item")}}}}}}, "pay")
problems, notes = rw.check_ho(ho, record, "pay")
if problems:
    raise RuntimeError(problems)      # never send it'''

SNIP_RB = '''# inside your payment tool: resolve what will actually run, freeze it under a token, state it as a line
values = resolve_payment(ho)                    # supplier, amount, account looked up on file, date, references
token = secrets.token_hex(4)
pending[token] = values
statement = rw.encode({"type": "RB", "id": "payer-1", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                       "item": "inv:MD-2026-057", "slots": {"p": "pay", "ask": "PAY", "h": rw.digest(ho, "pay"), **values}}, "pay")

# back on the sender's side: check the statement against the plan
problems, notes = rw.check_rb_full(ho, statement, "pay")'''

SNIP_DN = '''def commit(token, confirmed):
    if not confirmed or token not in pending:
        raise PermissionError("no confirmation for this token: nothing is paid")
    values = pending.pop(token)
    bank.pay(**values)                           # exactly what was stated, nothing else
    return rw.encode({"type": "DN", "id": "payer-2", "re": "scheduler-1", "from": "payer", "to": "scheduler",
                      "item": "inv:MD-2026-057", "slots": {"p": "pay", "out": "OK", **values}}, "pay")

dn = commit(token, confirmed=not problems)
problems, notes = rw.check_dn(ho, dn, "pay", rb_line=statement)'''

AGENT_PROMPT = f"""Integrate rogerwilco (pip install rogerwilco) around every irreversible action in this codebase: payments,
bank-detail changes, outbound emails, deletions, deploys. Read {SITE}/llms-full.txt first.
1. Find each place an agent hands another agent or a tool a job that cannot be undone.
2. Write that job as an RW1 HO line from the approved record with rw.encode, and refuse to send it unless
   rw.check_ho(ho, record, profile) returns no problems.
3. Split the tool that acts into prepare and commit. prepare resolves every value it will execute, freezes them under
   a token and returns them as an RB line; commit executes the frozen values only, and only after the sender's check.
4. The sender runs rw.check_rb_full(ho, statement, profile) on that statement and confirms the token only when it
   returns no problems. Read the statement from the tool, not from a model's retelling of it.
5. After commit, build a DN line from what the tool actually did and run rw.check_dn(ho, dn, profile, rb_line=statement);
   any problem means alert and reverse.
6. If the domain is not payments, copy rogerwilco/profiles/pform.json to a new profile and list the execution slots
   for each irreversible ask under "exec".
Add tests that plant a wrong value at each of the three checks and assert it is caught."""

CURL_HO = f'''curl -s {SITE}/check-ho -H 'content-type: application/json' -d '{{
  "profile": "pay",
  "ho": "{HO_BAD}",
  "record": {json.dumps(RECORD)}
}}\''''

# ---------------------------------------------------------------- the guide, as blocks
# ("h1"|"h2"|"h3", text) ("p", inline) ("code", lang, text) ("out", text) ("ul", [inline]) ("table", [[cells]]) ("note", inline)
# inline text takes `code` and [label](url).
G: list[tuple] = [
    ("h1", "Integrate rogerwilco"),
    ("p", "rogerwilco puts three checks, run by a program, around anything an AI agent does that cannot be undone: a payment, a "
          "change of bank details, an email to a customer, a deploy. The job travels as one typed line. The line is checked "
          "against the approved record before it is sent. The tool that acts states exactly what it will do, and that "
          "statement is checked before it runs. What it actually did is checked afterwards. This page is for the developer "
          "wiring it in, and for the coding agent doing it on their behalf."),
    ("note", "**If you are a coding agent**, read [/llms-full.txt](/llms-full.txt): this guide, the skill and the full "
             "protocol in one file. The prompt under [Hand it to your coding agent](#agent) is a complete brief."),
    ("h2", "Install", "install"),
    ("code", "sh", "pip install rogerwilco"),
    ("p", "Python 3.10 or later, standard library only, no dependencies. The package is [rogerwilco on PyPI](https://pypi.org/project/rogerwilco/); the source is on [GitHub](https://github.com/afieldofdreams/rogerwilco). The same package gives you a command line, "
          "`rogerwilco`, and every function is also a hosted [HTTP endpoint](#http) for other languages."),
    ("h2", "Where the checks go", "where"),
    ("table", [["Check", "Runs", "Catches", "Function"],
               ["1. The line against the record", "before the job is sent", "a wrong digit, date, account or addressee typed by the sender", "`check_ho`"],
               ["2. The tool's statement against the plan", "after the tool prepares, before it acts", "a wrong account or value the receiver or the tool resolved", "`check_rb_full`"],
               ["3. What was done against the plan", "after the act", "a tool that did something other than it stated", "`check_dn`"]]),
    ("p", "In our studies check 1 caught every mistake planted in the sender's line; check 2, on a tool that states what it "
          "will do, took wrong payments caused by the tool from 59 in 60 to none; check 3 flagged every fault injected at the "
          "moment of execution, after the fact. The [home page](/) tells those tests one at a time."),
    ("h2", "1. Write the job as a line, and check it before it goes", "check-ho"),
    ("p", "Build the line from the approved record with `rw.encode`, then compare the two with `rw.check_ho`. Under a profile "
          "that names execution slots for the ask, `PAY` here, the check also insists the line asks for an execution readback, `rb=exec`."),
    ("code", "python", SNIP_HO),
    ("p", "The line it builds:"),
    ("out", HO),
    ("p", "If a line was drafted by a model rather than built from the record, this is where a typo stops. With two digits swapped in the account:"),
    ("out", repr(CHECK_HO_BAD)),
    ("h2", "2. Make the tool prepare, and check what it says it will do", "prepare"),
    ("p", "Give the tool that acts two phases. `prepare` resolves every value it will execute, including anything it looks up, "
          "such as the account on file, freezes them under a token and returns them as a readback line, `RB`. Nothing has "
          "happened yet. The sender checks that statement against the plan with `rw.check_rb_full`."),
    ("code", "python", SNIP_RB),
    ("p", "The tool's statement, carrying `h=`, a fingerprint of the line it received:"),
    ("out", STATEMENT),
    ("p", "If the tool resolved a lookalike account, the check refuses it and nothing is paid:"),
    ("out", repr(CHECK_RB_BAD)),
    ("p", "Read the statement from the tool itself. Do not have a model copy it across: a small model in our study altered "
          "the tool's line in 51 of 129 relays."),
    ("h2", "3. Commit only on a yes, then check what was done", "check-dn"),
    ("p", "`commit` executes the frozen values and nothing else, and refuses without the sender's confirmation of that token. "
          "Its done report, `DN`, carries the values as executed, and `rw.check_dn` compares them with the plan."),
    ("code", "python", SNIP_DN),
    ("p", "A tool that states one thing and does another at the last moment is caught here, after the fact, so this is where you alert and reverse:"),
    ("out", repr(CHECK_DN_BAD)),
    ("h2", "The whole flow, runnable", "example"),
    ("p", "[examples/payment.py](https://github.com/afieldofdreams/rogerwilco/blob/main/examples/payment.py) puts the three steps "
          "together with a toy two-phase payment tool. Run it, then run it with the tool resolving the wrong account."),
    ("code", "python", EXAMPLE),
    ("code", "sh", "python examples/payment.py\npython examples/payment.py --fault"),
    ("out", RUN_OK + "\n" + RUN_FAULT),
    ("h2", "Cancel, expiry, and nothing left open", "cancel"),
    ("p", "A handoff must end. Every job closes exactly once: done, unable or failed from the receiver, or a cancel, `CX`, "
          "from the sender. If the approval is withdrawn before the tool commits, send a `CX`; the tool abandons what it prepared "
          "and acknowledges. If the act already ran, the receiver answers with the done report instead, and a mismatch is "
          "reversed with a new job, `ask=UNDO`. The tool's statement also carries `exp=`, the end of its window, and `commit` "
          "refuses after it, so a confirmation that arrives late cannot pay against a world that has moved. "
          "`rw.check_thread(lines, profile)` takes a conversation and reports any job left open past its time, closed twice, "
          "or acted on after a cancel."),
    ("code", "sh", "python examples/payment.py --cancel"),
    ("out", RUN_CANCEL),
    ("h2", "Teach the receiving model the format", "legend"),
    ("p", "A model that has to read or write lines needs about 400 tokens of legend in its prompt and nothing installed. "
          "Pass the profile so it gets the domain's codes."),
    ("code", "python", 'system_prompt += rw.legend("pay")'),
    ("out", LEGEND_HEAD),
    ("p", "Where the receiver is a model that cannot run your two-phase tool, it can still read back the values it will act "
          "with: `rw.make_rb(ho, \"payer-1\", \"pay\")` builds a correct readback for a receiver that runs code, and the "
          "sender checks it the same way. On strong models this caught little, because they read well; on a weak model, "
          "the tool's statement did better than any readback the model wrote."),
    ("h2", "Your own domain: profiles", "profiles"),
    ("p", "A profile adds the codes and slots for one kind of work and names, for each irreversible ask, the values it is "
          "executed with. That list is what checks 1 to 3 compare. Four ship with the package: `pay` (accounts payable), "
          "`clin` (clinical statements), `deploy` and `pform` (a knowledge-graph workflow). To make your own, copy "
          "`rogerwilco/profiles/pform.json`, list your asks and slots, and put the irreversible ones under `exec`. A profile "
          "may add codes; it may not redefine the core ones. [Profiles](/profiles) shows the same line doing four kinds of work."),
    ("h2", "Hand it to your coding agent", "agent"),
    ("p", "Paste this into Claude Code, Cursor or any coding agent working in your repository. It is the whole brief."),
    ("code", "text", AGENT_PROMPT),
    ("h2", "Not Python: the HTTP API", "http"),
    ("p", "Every function is a JSON endpoint at this site, no key and no sign-up, for any language: `POST /check-ho`, "
          "`/check-rb`, `/check-dn`, `/make-rb`, `/validate`, `/digest`, `/to-json`, `/from-json`, `/gate`, and "
          "`GET /legend`. Check 1 with the swapped digits:"),
    ("code", "sh", CURL_HO),
    ("out", json.dumps({"ok": False, "problems": CHECK_HO_BAD, "notes": []})),
    ("p", "The full reference, with every input and output, is at [/docs](/docs). For production, run the checks in your own "
          "process with the library, or host this service yourself: it is one container, `docker build .` from the repository."),
    ("h2", "Trying it inside a chat client", "mcp"),
    ("p", "The same checks are exposed as MCP tools, so you can try the format from Claude or another MCP client without writing code: "
          "`claude mcp add --transport http rogerwilco https://rogerwilco.crox.io/mcp`. This is for exploring, not for "
          "integration: checks that guard money belong in your own code path, where a model cannot skip them."),
    ("h2", "The functions", "reference"),
    ("table", [["Function", "Does", "Returns"],
               ["`encode(msg, profile)`", "JSON form to a line, validated", "the line"],
               ["`parse(line, profile)`", "a line to its JSON form", "`(message, errors, warnings)`"],
               ["`check_ho(ho, record, profile)`", "check 1: the line against the record", "`(problems, notes)`"],
               ["`check_rb_full(ho, rb, profile)`", "check 2: a readback or a tool's statement against the line", "`(problems, notes)`"],
               ["`check_dn(ho, dn, profile, rb_line=)`", "check 3: what was done against the plan", "`(problems, notes)`"],
               ["`make_rb(ho, id, profile)`", "a correct readback, for a receiver that runs code", "the RB line"],
               ["`digest(line, profile)`", "the fingerprint `h=` of a line", "12 hex characters"],
               ["`check_thread(lines, profile)`", "every job closed: done, unable, failed or cancelled; none open past its time", "`(problems, notes)`"],
               ["`legend(profile)`", "the prompt text another model needs", "text"]]),
    ("p", "No problems means go. Anything in problems means stop: re-send the job from the record, or, after the act, reverse it. "
          "Notes are assumptions worth logging. [What a line is](/lines) explains every message type; the [spec](/spec) is the "
          "rulebook; the [skill](/skill) is the file an agent reads."),
]


# ---------------------------------------------------------------- renderers
def inline_html(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)


def inline_md(t: str) -> str:
    return re.sub(r"\]\((/[^)]*)\)", lambda m: f"]({SITE}{m.group(1)})", t)


def render_html() -> str:
    out = []
    for b in G:
        k = b[0]
        if k == "h1":
            out.append(f"<h1>{html.escape(b[1])}</h1>")
        elif k in ("h2", "h3"):
            anchor = f' id="{b[2]}"' if len(b) > 2 else ""
            out.append(f"<{k}{anchor}>{html.escape(b[1])}</{k}>")
        elif k == "p":
            out.append(f"<p>{inline_html(b[1])}</p>")
        elif k == "note":
            out.append(f'<p class="callout">{inline_html(b[1])}</p>')
        elif k == "code":
            out.append(f'<pre class="code" data-lang="{b[1]}"><code>{html.escape(b[2])}</code></pre>')
        elif k == "out":
            out.append(f'<pre class="reply">{html.escape(b[1])}</pre>')
        elif k == "table":
            head, *rows = b[1]
            t = ['<div class="tw"><table><thead><tr>' + "".join(f"<th>{inline_html(c)}</th>" for c in head) + "</tr></thead><tbody>"]
            t += ["<tr>" + "".join(f"<td>{inline_html(c)}</td>" for c in r) + "</tr>" for r in rows]
            out.append("".join(t) + "</tbody></table></div>")
    return "\n".join(out)


def render_md() -> str:
    out = []
    for b in G:
        k = b[0]
        if k == "h1":
            out.append(f"# {b[1]}")
        elif k == "h2":
            out.append(f"## {b[1]}")
        elif k in ("p", "note"):
            out.append(("> " if k == "note" else "") + inline_md(b[1]))
        elif k == "code":
            out.append(f"```{b[1]}\n{b[2]}\n```")
        elif k == "out":
            out.append(f"```\n{b[1]}\n```")
        elif k == "table":
            head, *rows = b[1]
            out.append("\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in rows]))
    return "\n\n".join(out) + "\n"


DESCRIPTION = ("How to integrate rogerwilco: pip install rogerwilco, then three checks a program runs around an AI agent's "
               "irreversible actions. Check the job against the record before sending, check the tool's statement before it "
               "acts, check what it did afterwards. Python, HTTP and a brief for your coding agent.")

PAGE = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Integrate rogerwilco: checks around an agent's irreversible actions</title>
<meta name="description" content="{html.escape(DESCRIPTION)}">
<link rel="alternate" type="text/markdown" href="/quickstart.md" title="This guide as Markdown">
<!-- site:head -->
<!-- /site:head -->
</head>
<body>
<!-- site:header -->
<!-- /site:header -->
<div class="wrap">
<main class="doc guide">
{render_html()}
<p class="muted">This page as Markdown: <a href="/quickstart.md">/quickstart.md</a>. For a model: <a href="/llms.txt">/llms.txt</a>, <a href="/llms-full.txt">/llms-full.txt</a>.</p>
</main>
</div>
<!-- site:footer -->
<!-- /site:footer -->
</body>
</html>
"""

PAGES = ["/", "/quickstart", "/demo", "/lines", "/profiles", "/research", "/about"] + \
        [f"/research/{p.stem}" for p in sorted((STATIC / "research").glob("*.html")) if p.stem != "index"]

LLMS = f"""# rogerwilco

> rogerwilco is a Python library and protocol (RW1) that puts three program-run checks around an AI agent's irreversible actions, after aviation's readback: a job travels as one typed line; the line is checked against the approved record before it is sent; the tool that acts states exactly what it will do, and that statement is checked before it runs; what it did is checked afterwards. `pip install rogerwilco`. Standard library only. Apache 2.0 licence.

Use it when an agent pays, changes bank details, sends an external email, deletes or deploys: anything that cannot be undone. The receiving model needs only a short legend in its prompt.

## Integrate

- [Integration guide]({SITE}/quickstart.md): install, the three checks with runnable code, the two-phase tool, profiles, the HTTP API, a brief for a coding agent
- [Everything in one file]({SITE}/llms-full.txt): the guide, the skill and the full protocol, for a model doing the integration
- [Runnable example](https://github.com/afieldofdreams/rogerwilco/blob/main/examples/payment.py): a payment with all three checks

## Reference

- [Protocol spec]({SITE}/spec): grammar, the nine message types, cancel and expiry, slots, the five-tier readback, checks before and after an irreversible act, profiles
- [Skill]({SITE}/skill): the instructions an agent follows to use rogerwilco
- [Legend]({SITE}/legend?profile=pay): the text to put in a receiving model's prompt
- [HTTP API]({SITE}/openapi.json): OpenAPI for the hosted checks, no key

## Evidence

- [The tests, one at a time]({SITE}/): what was tested and what each check caught
- [Research]({SITE}/research): seven pre-registered studies, every figure with its interval

## Optional

- [What a line is]({SITE}/lines)
- [Profiles]({SITE}/profiles)
- [Demo]({SITE}/demo)
"""


def main() -> int:
    md = render_md()
    for name, text in {"quickstart.html": PAGE, "quickstart.md": md, "llms.txt": LLMS,
                       "llms-full.txt": "\n\n".join([md, "---\n\n" + (REPO / "rogerwilco" / "SKILL.md").read_text(encoding="utf-8"),
                                                     "---\n\n" + (REPO / "rogerwilco" / "references" / "SPEC.md").read_text(encoding="utf-8")]),
                       "robots.txt": f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n",
                       "sitemap.xml": '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"  <url><loc>{SITE}{p}</loc></url>\n" for p in PAGES + ["/quickstart.md", "/llms.txt", "/llms-full.txt", "/spec", "/skill"])
                                      + "</urlset>\n"}.items():
        if "—" in text and name != "llms-full.txt":
            sys.exit(f"em dash in {name}")
        (STATIC / name).write_text(text, encoding="utf-8")
        print("wrote", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
