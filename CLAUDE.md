# rogerwilco

Protocol, hosted validator and research for typed agent-to-agent handoffs with verified readback.

## Layout

- `rogerwilco/` is the skill and the reference implementation. `SKILL.md` is what Claude reads; `references/SPEC.md` is the protocol; `scripts/rogerwilco.py` is the codec (standard library only, keep it that way); `profiles/` holds the core vocabulary and domain profiles; `tests/conformance.jsonl` is the conformance suite. An implementation is conformant when `python3 rogerwilco/tests/test_conformance.py` passes.
- `app/` is the FastAPI service deployed at rogerwilco.crox.io: REST, MCP at `/mcp`, playground at `/`. It imports the codec by path (`RW_SKILL_DIR`), never by copying it.
- `research/` holds the studies. It is never read by the app. Raw logs are kept as they were produced, including the working name `formcore` and prefix `FC1` used before the rename on 2026-09-29; only the version token changed.
- `Dockerfile` at the root builds the app. Coolify builds it from `main`.

## Rules

- **Merge is deploy.** Coolify auto-deploys every push to `main`. Anything that should not go live does not go on `main`: research runs and results land on a `research` branch and merge through a PR.
- **No secrets in the repo.** Keys live in Coolify's environment and in the shell. `secrets` of any kind are inventory only.
- **No private data in `research/`.** Corpora are synthetic. Nothing from a client or from a personal knowledge graph is committed.
- **Core vocabulary is closed.** New codes go in a profile under `rogerwilco/profiles/`, never into `core.json`. A profile may add codes and slots; it may not redefine core ones (the codec refuses).
- **Change the spec, change the tests.** Any behaviour change in the codec comes with a conformance case, and `SKILL.md`, `SPEC.md` and the legend stay consistent with each other.
- **Worked examples carry real digests.** If an example HO line changes, recompute its `h=` with `rogerwilco.py digest` and update every copy (SKILL.md, README.md, SPEC.md).
- No em dashes in prose.

## Commands

```
python3 rogerwilco/tests/test_conformance.py
cd app && python3 -m pytest -q
uvicorn app.main:app --reload            # from the repo root
docker build -t rogerwilco --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) .
```
