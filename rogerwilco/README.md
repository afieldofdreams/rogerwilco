# rogerwilco

One-line, typed, closed-vocabulary messages for handing work between AI agents, with a readback the sender can verify.

```
RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 pri=2 // hero copy, 120 words
RW1 RB writer-01 re=research-01 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 h=f209197fa615
RW1 DN writer-03 re=research-01 from=writer to=research item=gh:crox/site#42 out=OK art=sha256:9f3e1c // v1, 118 words
```

Agents hand work to each other in prose today. Prose hides state, can't be validated, and gets misread silently. Most of the cost is fixed by discipline (facts once, files by reference, deltas only, closed options for the human), which the skill states in English first; the syntax exists so that code can check the discipline is being kept. rogerwilco puts the facts in slots, keeps reasoning in a bounded tail, and makes the receiver read the handoff back before it owns the work. The sender checks the readback in code across five tiers: receipt, integrity, echo, comprehension, where the receiver derives the acceptance criteria from the brief and the sender compares them with the ones it kept to itself, and execution, where before an irreversible act the receiver reads back the values it will act with and, afterwards, reports the values the tool executed. ATC phraseology for the envelope, teach-back for the instruction.

The name is the radio call. *Roger*: received. *Wilco*: understood, and will comply. Those are two different claims, and the protocol makes the receiver prove both before the sender lets go of the work: the receipt tier is roger, the comprehension tier is wilco. A handoff whose readback passes is said to be wilco.

It is content, not transport. It rides inside an MCP tool result, an A2A message part, a chat turn, a queue message or a log line. The receiving agent needs nothing installed: a 400-token legend in its prompt is enough to read and reply.

## Install and integrate

```
pip install rogerwilco
```

Python 3.10+, standard library only. Three checks go around anything an agent does that cannot be undone:

```python
import rogerwilco as rw

problems, notes = rw.check_ho(ho, record, "pay")                    # 1. the job's line against the approved record, before sending
problems, notes = rw.check_rb_full(ho, statement, "pay")            # 2. the tool's statement of what it will do, before it acts
problems, notes = rw.check_dn(ho, dn, "pay", rb_line=statement)     # 3. what it did, against the plan, afterwards
```

Empty `problems` means go; anything else means stop. The integration guide, with a runnable two-phase payment tool and a
brief to hand your coding agent, is at **https://rogerwilco.crox.io/quickstart**. For a model doing the integration:
https://rogerwilco.crox.io/llms-full.txt. The evidence, seven pre-registered studies: https://rogerwilco.crox.io/research.

## Use it with Claude

This repo is an [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview). Install it and Claude will use rogerwilco whenever it delegates to a subagent or receives a line that starts with `RW1`.

- **Claude Code**: copy the `rogerwilco/` folder into `.claude/skills/` in your project (or `~/.claude/skills/` for all projects).
- **Claude.ai and the Claude apps**: zip the `rogerwilco/` folder and upload it under Settings, Capabilities, Skills.
- **Any other agent**: put the output of `python3 scripts/rogerwilco.py legend` in its system prompt.

## What's in the folder

| Path | What |
|---|---|
| `SKILL.md` | The instructions Claude follows. Short by design. |
| `references/SPEC.md` | The protocol, version RW1 v0.1: grammar, eight message types, slots, codes, five rules, the five-tier readback, the checks before and after an irreversible act, JSON form, profiles. |
| `scripts/rogerwilco.py` | Reference codec, standard library only: validate, encode, JSON twin, `make-rb`, `check-rb`, `check-ho`, `check-dn`, digest, legend, lint. |
| `profiles/core.json` | The core vocabulary. |
| `profiles/pform.json` | An example domain profile (a knowledge-graph workflow). Copy it to make your own. `pay.json` (accounts payable, with execution slots) and `clin.json` (clinical assertions) are the profiles the studies used. |
| `tests/conformance.jsonl` | 80 codec cases (parse, readback, presend, done, digest) plus 6 agent-behaviour cases. |
| `tests/test_conformance.py` | Runner. An implementation is conformant when it passes. |

## The eight types

`HO` handoff · `RB` readback · `AQ` ask · `AN` answer · `ST` status · `DN` done · `UN` unable · `FL` fail

## The five rules

1. No handover without readback.
2. Never guess: unknown code, reply `UN why=UNK`.
3. Every reply carries `re=`.
4. Facts in slots, reasoning in the tail.
5. The line and its JSON form are the same message.

## Why these choices

They come from a 240-message study of five wire formats and from reading real agent logs (September 2026). Keyed form beat positional because a small model miscounted positional columns in one run of two. Three-letter codes beat glyphs because glyph savings were tokenizer-dependent and the legend cost 1.7x more. Readback exists because every error observed was a misread of a neighbouring field, which an echo catches at the boundary. The execution level and the done check exist because the execution readback study found faults in the sender's draft and in the tool, and none in the receiver's reading on current models. The tail is bounded because real agent logs were 50% process narration and 26% narrated field changes. Details in `references/SPEC.md` section 10.

## Conformance

```
python3 tests/test_conformance.py
python3 tests/test_conformance.py --agent replies.jsonl   # score an agent's replies to the five agent cases
```

## Status

v0.1, draft. The core vocabulary is small on purpose; extend it through a profile, not by editing the core. Issues and profiles welcome.

MIT licence. Adam Field, Croxio Ltd. Lineage: M-Form (medical-record compression, 2025) to P-Form (knowledge-graph handoffs, April 2026) to rogerwilco (September 2026).
