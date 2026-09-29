# Research

Three studies behind the protocol, each with its corpus, harness, raw logs and a results page. Everything here is synthetic; nothing comes from a client or a private knowledge graph.

| Study | Question | Folder | Results page |
|---|---|---|---|
| Wire study | Does a closed-vocabulary line beat English, JSON, glyphs or a positional form on tokens, round trip and decision parity? 240 synthetic handoffs, five formats, two models. | `wire-study/` | `wire-study/report.html` |
| Readback pilot | Does a comprehension readback catch misread briefs before the work is done, and at what cost in tokens and false alarms? 36 trials, planted faults, blind grading. | `pilot/` | `pilot/report.html` |
| Month-end close | Do typed lines cut inter-agent traffic, keep the human's read load down and bring the human in exactly when policy says, in a four-agent accounts-payable run with planted events? 23 runs: prose, PACT-style prose, disciplined prose (the same rules without the syntax), lines, lines with full readback, lines on Haiku, and an adversarial scenario with an injected instruction and a wrong answer from the principal. | `month-end/` | `month-end/results/report.html` |

## Naming

The first two studies ran under the working name **formcore** with the line prefix `FC1`. The protocol was renamed **rogerwilco** with prefix `RW1` on 2026-09-29. The results pages use the new name; the raw logs, prompts and trial folders keep what the agents actually saw. Only the version token changed; no other part of the grammar did.

## Reproducing

Each folder has its own README or a docstring at the top of its harness. The wire study and the pilot were run with Claude subagents driven from a Claude session; the month-end study's harness (`month-end/tools/`) is file-based so any model that can run shell commands can play an agent. `harness/` is a model-agnostic runner that drives the same scenarios over an OpenAI-compatible or Anthropic API, unattended, with keys from the environment; see its README.
