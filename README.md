# rogerwilco

Roger: received. Wilco: understood, and will comply.

One-line, typed, closed-vocabulary messages for handing work between AI agents, with a readback the sender verifies in code before it lets go of the work.

```
RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 pri=2 // hero copy, 120 words
RW1 RB writer-01 re=research-01 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 h=f209197fa615
RW1 DN writer-03 re=research-01 from=writer to=research item=gh:crox/site#42 out=OK art=sha256:9f3e1c // v1, 118 words
```

Agents hand work to each other in prose today. Prose hides state, cannot be validated, and gets misread silently. rogerwilco puts the facts in slots, keeps reasoning in a bounded tail or an artifact, and makes the receiver read the handoff back before it owns it. The readback is checked in four tiers: receipt and integrity (roger), echo and comprehension (wilco). It is content, not transport: it rides inside an MCP tool result, an A2A part, a chat turn, a queue message or a log line.

## Three things in this repo

| Folder | What | Start here |
|---|---|---|
| [`rogerwilco/`](rogerwilco/) | The protocol as a Claude Agent Skill: `SKILL.md`, the spec, the reference codec (standard library only), profiles, conformance tests. Copy the folder into `.claude/skills/` or upload it as a skill. | [`rogerwilco/README.md`](rogerwilco/README.md) |
| [`app/`](app/) | The hosted validator: REST endpoints, a remote MCP server, the playground and the docs. Runs at [rogerwilco.crox.io](https://rogerwilco.crox.io). Add the MCP server by URL to any agent that has no shell. | [`app/README.md`](app/README.md) |
| [`research/`](research/) | The evidence: a five-format wire study, a readback pilot with planted faults, and a multi-agent month-end close with human-in-the-loop escalation. Corpora, harnesses, raw logs and results pages. | [`research/README.md`](research/README.md) |

## Quick start

```
# validate a line
python3 rogerwilco/scripts/rogerwilco.py validate "RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT"

# sender side: check a readback across the four tiers
python3 rogerwilco/scripts/rogerwilco.py check-rb "<HO line>" "<RB line>"

# legend for another agent's system prompt (about 400 tokens for core, more with a profile)
python3 rogerwilco/scripts/rogerwilco.py legend --profile pay

# conformance
python3 rogerwilco/tests/test_conformance.py

# the hosted app, locally
pip install -r app/requirements.txt && uvicorn app.main:app --reload
```

## Status

v0.1, draft. The core vocabulary is small on purpose; extend it through a profile, not by editing the core. Issues and profiles welcome.

MIT licence. Adam Field, Croxio Ltd. Lineage: M-Form (medical-record compression, 2025) to P-Form (knowledge-graph handoffs, April 2026) to rogerwilco (September 2026).
