# Month-end harness

Runs the month-end multi-agent scenario (`../month-end`) unattended against any chat model that can call tools. Four agents (extractor, reconciler, scheduler, auditor) each get the role file from the run directory as their system prompt and five tools; a scripted principal answers the questions sent to `human`; `tools/grade.py` grades the result. Python 3.11+, standard library only (pytest for the tests).

```
harness/
  llm.py                  chat(messages, tools, model) -> (assistant_message, tool_calls, usage)
  agent.py                the five-tool agent loop, scoped to one run directory
  orchestrate.py          rounds, the principal, usage files, grading, --build and --grid
  tests/test_harness.py   mock-provider tests (python3 -m pytest -q)
```

## Read this first: what it costs

**One agent turn uses 120k to 180k prompt tokens on Sonnet.** Every tool call is a model call, and every model call re-sends the whole conversation, so a turn of a few dozen tool calls (the limit is 40) adds up quickly. A run has about 10 to 14 turns (four agents, each woken a few times; the readback arm R sits at the high end), so:

| | prompt tokens |
|---|---|
| one turn | 120k to 180k |
| one run | about 1.2M to 2.5M |
| the grid `"A,D,L" --runs 3` (9 runs) | about 11M to 23M |
| a second model | the same again |

Output and reasoning tokens come on top, and reasoning models can produce a lot of them. As an illustration only, at $3 per million uncached input tokens one run is roughly $4 to $8 and the grid $35 to $70; use your model's real prices. Prompt caching cuts the input side a great deal, but only where it is on: the Anthropic adapter puts cache breakpoints on the system prompt and the newest message (`RW_ANTHROPIC_CACHE=0` turns that off), OpenAI caches long prompts by itself, and through OpenRouter it depends on the upstream model (Anthropic models there get no breakpoints from this harness, so use `anthropic:` for them). `usage.json` records `cached_tokens` wherever the provider reports them; check that the first run shows some.

Before you launch the grid:

1. Run **one** run of **one** arm first and read its `usage.json`.
2. Set a ceiling on every run with `--max-prompt-tokens 3000000`. It counts prompt tokens (cached ones included) after every model call, so a run overshoots it by at most the calls already in flight.
3. The harness has no notion of money. It stops only for that ceiling, for 16 rounds, or for a provider error.

The context cap (150k characters, oldest tool results dropped first) limits how big each call can get, not how many calls there are.

## Run one arm on one model

From `research/month-end`, with a key in the environment (never in a file):

```
export OPENROUTER_API_KEY=...            # or RW_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, see below
python3 ../harness/orchestrate.py --build L 4 --model openrouter:openai/gpt-5.6 --max-prompt-tokens 3000000
```

`--build L 4` runs `tools/build_run.py L 4` first (it refuses to overwrite an existing run), then plays the run to the end and calls `tools/grade.py`. `--scenario 2` builds the scenario-2 variant (`L4s2`). To play a run directory you built yourself, use `--run runs/L4`; it must be fresh, holding only the kickoff message. A run directory is used once: after a provider error, build a new one.

Model strings are `provider:name`:

| model string | endpoint | key |
|---|---|---|
| `openrouter:openai/gpt-5.6` | https://openrouter.ai/api/v1 | `OPENROUTER_API_KEY` |
| `openai:gpt-5.6` | https://api.openai.com/v1 | `OPENAI_API_KEY` |
| `anthropic:claude-sonnet-4-6` | https://api.anthropic.com (Messages API) | `ANTHROPIC_API_KEY` |
| `compat:<model>` | `RW_BASE_URL`, required | `RW_API_KEY` (not needed for local servers) |
| `mock:script.json` | none, scripted answers for tests | none |

Gemini's OpenAI-compatible endpoint, Ollama and vLLM go through the OpenAI-compatible adapter: set `RW_BASE_URL` (`https://generativelanguage.googleapis.com/v1beta/openai/`, `http://localhost:11434/v1`, `http://localhost:8000/v1`) and use `openai:<model>` or `compat:<model>`.

`--principal-model MODEL` is optional; see the caveats.

## Run the whole grid

```
python3 ../harness/orchestrate.py --grid "A,D,L" --runs 3 --model anthropic:claude-sonnet-4-6 --max-prompt-tokens 3000000
```

For every arm it builds `--runs` fresh runs, numbered from the first free numbers (the Claude runs `A1` to `A3` stay untouched, so a new grid starts at `A4`; `--start N` overrides), plays them one after another, prints a table (stop reason, rounds, core checks, recall, precision, prompt and completion tokens, minutes) and writes `results/harness-grid-<time>.json` (or `--summary PATH`). `--jobs 3` plays three runs at once, which is faster and hits provider rate limits sooner (the adapters retry with backoff). `--scenario 2` grids the scenario-2 variant. Ctrl-C stops the runs in flight at their next model call and leaves them recorded as `interrupted`.

Other options: `--max-rounds N` (default 16), `--no-grade`, `--no-python-c`, `--month-end DIR`.

Exit status: 0 when every run completed, 1 when a run ended without the auditor reporting (`stalled`, `max_rounds`, `budget`), 2 when any run hit a provider error or the setup was bad, 130 when interrupted.

## Environment variables

| variable | default | meaning |
|---|---|---|
| `RW_BASE_URL` | per provider | base URL for the OpenAI-compatible adapters (overrides the OpenRouter and OpenAI defaults too) |
| `RW_API_KEY` | | key for the OpenAI-compatible adapters; wins over the two below |
| `OPENROUTER_API_KEY` | | used only when the endpoint is openrouter.ai |
| `OPENAI_API_KEY` | | used only when the endpoint is api.openai.com |
| `ANTHROPIC_API_KEY` | | key for `anthropic:` |
| `ANTHROPIC_BASE_URL` | https://api.anthropic.com | override for `anthropic:` |
| `RW_TIMEOUT` | 600 | seconds per HTTP request |
| `RW_RETRIES` | 8 | attempts per call on 408, 409, 425, 429, 5xx and network errors (exponential backoff, `Retry-After` honoured) |
| `RW_MAX_TOKENS` | unset (16000 for Anthropic) | maximum output tokens |
| `RW_TEMPERATURE` | unset | sent only when set (reasoning models reject it) |
| `RW_EXTRA_BODY` | | JSON object merged into every request, for example `{"reasoning_effort": "low"}`, `{"thinking": {"type": "enabled", "budget_tokens": 8000}}` or, on OpenRouter, `{"usage": {"include": true}}` to get costs |
| `RW_ANTHROPIC_CACHE` | 1 | `0` removes the Anthropic cache breakpoints |
| `RW_MONTH_END` | `../month-end` | where `tools/`, `data/`, `truth/` and `runs/` live (same as `--month-end`) |

Keys are read from the environment only, are never written to a file, and are redacted from error messages. A key is sent only to the host it belongs to: with `RW_API_KEY` unset, `OPENROUTER_API_KEY` goes to openrouter.ai and nowhere else, and a third-party `RW_BASE_URL` without `RW_API_KEY` is refused before anything is built. The agents' subprocesses run with a scrubbed environment (no keys, no proxy settings).

## What a run leaves behind

In the run directory, next to what the scenario already writes (`mail/log.jsonl`, `work/`, `grade.json`):

| file | content |
|---|---|
| `rounds.json` | rounds played, why it stopped (`complete`, `stalled`, `max_rounds`, `budget`, `error`, `interrupted`), per-round agents and principal activity, unanswered principal questions |
| `usage.json` | per agent, per turn, per model call: prompt, completion, cached and reasoning tokens, cost where the provider reports it, tool calls, refusals, how the turn ended; plus totals |
| `harness/config.json` | model, endpoint host, limits, harness commit, and how `mail.py` counted tokens |
| `harness/principal.json` | every question the principal read and exactly what was sent back |
| `harness/transcripts/<agent>.jsonl` | every message of every conversation, with usage and any reasoning text |
| `run.json` | one added key, `harness`, naming the model and principal model (`build_run.py` labels every run `sonnet` unless given `--model`; `--build` and `--grid` pass yours) |

The agents cannot see or write `harness/`. The transcripts are written as the run goes, so `tail -f runs/L4/harness/transcripts/extractor.jsonl` shows an agent working; the console line for a turn appears when the turn ends. `complete` means no agent has unread mail and the auditor has written to the human; it says nothing about whether the run was right, which is what `grade.json` is for.

## How a run goes

Each round: `mail.py pending`; every agent with unread mail gets one turn (spawned on its first mail), the four in parallel threads; then the scripted principal (`../month-end/tools/principal.py`, imported by path, never copied) reads what was sent to `human` and its replies are sent. The run stops when nothing is unread and the auditor has reported, when nothing is unread and it has not (`stalled`), after 16 rounds, over the token ceiling, or on a provider error.

A turn appends the user message `mail` and loops on tool calls until `done()`, a plain-text reply (the role prompts ask for `DONE`) or 40 tool calls. The conversation persists across turns. Before each call the context is capped at 150k characters by replacing the oldest tool results with a stub, keeping the system prompt and the last 20 messages. Only tool results are dropped: the agent's own messages, including large `write_file` contents, are never trimmed.

The five tools, all scoped to the run directory:

- `read_file(path)`, `write_file(path, content)`, `list_dir(path)`: paths are resolved through symlinks and must stay inside the run directory. `read_file` goes through `mail.py open`, so reads are logged and counted exactly as the study counts them. `mail/`, `mail.py`, `run.json`, `prompts/` and the harness files cannot be written; `data/` can, on purpose, because whether an agent edits the supplier master is something the study measures.
- `shell(cmd)`: one command, no shell (so no pipes, redirects, chaining or expansion), 60 second timeout. Allowed: `python3 mail.py read|send|open|validate|make-rb|check-echo|pending`, `python3 -c`, `cat ls grep head tail wc jq sha256sum`. Everything else returns an error string. Arguments naming an existing path outside the run directory, and recursion (`grep -r`, `ls -R`), are refused. `send --from` and `read|open --me` must name the calling agent, so no model can answer as the principal.
- `done()`: ends the turn.

`python3 mail.py` calls from all agents and the orchestrator run under one lock per run, because `mail.py` rewrites its log on `read` and numbers messages by reading it; the model calls themselves stay concurrent.

## Caveats

- **The principal is scripted, and the same for every model.** `principal.py` recognises the planted events by keyword and answers with fixed text, whatever the agent wrote and whichever model wrote it. It was written for the Claude runs. A model that words a question differently may get a reply that fits less well, or none: in arms L and R the script flags questions it cannot map to the offered options (`no matching option: check by hand`). Those are not sent. They are listed under `principal_unanswered` in `rounds.json` and `harness/principal.json`, and the run usually ends `stalled` with the agent still waiting. With `--principal-model MODEL` such a question is put to that model instead, which is shown the policy and the script's decisions and must pick one of the offered options; everything else still comes from the script. That changes the experiment, so a run that used it is marked in `run.json` and `harness/config.json`. Compare models only with the same principal setting.
- **Only the mock provider and local fake servers have been used.** The adapters were written to the published OpenAI-compatible and Anthropic request and response shapes and are tested against local stand-ins, but the build environment had no API keys, so no real provider has been called. Do the first real run small (one run, a token ceiling) and read `harness/transcripts/`. Reasoning text is replayed only where the API requires it (Anthropic thinking blocks, OpenRouter `reasoning_details`, Gemini thought signatures); other providers' reasoning text is recorded and not sent back.
- **`python3 -c` is not a sandbox.** It can touch anything your user can. Run unknown models in a container, or pass `--no-python-c`. The agents can also read `mail/log.jsonl` and `prompts/`, as the Claude agents could.
- **Token counts.** `mail.py` counts with tiktoken's `o200k_base` when it loads, else characters divided by four, and the harness's subprocesses have no proxy settings, so an encoding that is not cached cannot be downloaded there. The harness records which counter was used and warns when it is the fallback. Cache it once first: `python3 -c "import tiktoken; tiktoken.get_encoding('o200k_base')"`.
- **`tools/summarise.py` pools everything.** It averages every `runs/*[0-9]` directory by arm with no model column, so runs from different models mix, and it stops at a run without `grade.json` (the harness does not grade runs that ended in `error` or `interrupted`). To keep a model apart, run the harness against a copy of `research/month-end` placed at `<root>/research/<name>` with the codec at `<root>/rogerwilco` and pass `--month-end`, and move or grade failed runs before summarising.
- **Different runs are not identical runs.** The models are not deterministic and providers change under a model name. `harness/config.json` records the model string, the endpoint host, the limits and the harness commit; keep them with the results.

## Tests

```
cd research/harness
pip install --break-system-packages pytest     # if needed
python3 -m pytest -q
```

They use the mock provider (a scripted two-round mini-run: the loop, tool scoping, the shell allowlist, usage records) and stand-in HTTP servers on 127.0.0.1 for the adapters, and build their runs in temporary directories, so nothing in the repository is written. They take a minute or two because every `mail.py` call is a subprocess.
