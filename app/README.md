# rogerwilco app

A small web app for the [rogerwilco](../rogerwilco/SKILL.md) protocol (RW1): a JSON API over the reference codec, an MCP server that agents can call, and the site that explains it. Roger means received, wilco means understood and will comply, and the app lets you check both.

It has no auth and no database. Every request is answered from the codec in the skill folder.

## Layout

This folder is `app/` in the repo, next to the skill (`rogerwilco/`). The `Dockerfile` sits at the repo root.

```
Dockerfile              repo root: python:3.12-slim, copies rogerwilco/ and app/, port 8080
rogerwilco/             the skill: SKILL.md, references/SPEC.md, profiles/, scripts/rogerwilco.py
app/
  main.py               FastAPI app: routes, CORS, error handling, serves the site
  mcp.py                MCP server (official SDK), mounted at /mcp
  service.py            finds the codec, imports it by path, wraps it as JSON in, JSON out
  static/index.html     the home page: no build step
  tests/test_app.py     pytest
  requirements.txt
```

The codec is imported by path from `<skill folder>/scripts`, not as a package. The skill folder is `RW_SKILL_DIR` if set, otherwise the first of `/srv/rogerwilco` (the container), `../rogerwilco` (a repo checkout) and `/home/claude/rogerwilco-skill/rogerwilco` (local dev) that holds `scripts/rogerwilco.py`. If `RW_SKILL_DIR` is set and wrong, the app stops at startup and says so.

## Run it locally

From the repo root, where `app/` and `rogerwilco/` sit side by side:

```
pip install -r app/requirements.txt
uvicorn app.main:app --reload
```

Then open <http://localhost:8000> for the site, or <http://localhost:8000/docs> for the API reference. Pass `--port` to use another port.

## Docker

```
docker build -t rogerwilco --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) .
docker run --rm -p 8080:8080 rogerwilco
```

`GIT_COMMIT` is reported by `/healthz`. Without it the commit reads `unknown`.

| Variable | Meaning |
|---|---|
| `RW_SKILL_DIR` | The skill folder. Set to `/srv/rogerwilco` in the image. |
| `GIT_COMMIT` | Build id for `/healthz`. Set by the `GIT_COMMIT` build arg. |

## Endpoints

JSON in, JSON out, CORS open. A line that fails validation is a normal answer (`200` with `"ok": false`). Anything the codec cannot answer, such as an unknown profile or a line that cannot be converted, is `400` with `{"error": "..."}`. A malformed request body is `422` with the same shape.

| Method and path | Body or query | Answer |
|---|---|---|
| `GET /` | | the home page |
| `GET /healthz` | | `{"ok": true, "version": "RW1", "commit": "..."}` |
| `POST /validate` | `{"line", "profile"}` | `{"ok", "message", "errors", "warnings"}` |
| `POST /check-rb` | `{"ho", "rb", "profile", "expect_acc"}` | `{"ok", "problems", "notes"}` |
| `POST /check-ho` | `{"ho", "record", "profile"}` | `{"ok", "problems", "notes"}`: the HO against the record it was built from, before it is sent |
| `POST /check-dn` | `{"ho", "dn", "profile", "rb"}` | `{"ok", "problems", "notes"}`: the done report against the plan, after the act |
| `POST /make-rb` | `{"ho", "id", "profile", "acc", "do", "hash"}` | `{"rb"}` |
| `POST /to-json` | `{"line", "profile"}` | `{"message"}` |
| `POST /from-json` | `{"message", "profile"}` | `{"line"}` |
| `POST /digest` | `{"line", "profile"}` | `{"digest"}` |
| `POST /gate` | `{"lines", "profile", "document", "doc_id"}` | `{"ok", "errors", "notes", "counts", "rows", "accepted"}` |
| `GET /legend?profile=pay` | | the legend as `text/plain` |
| `GET /profiles` | | `[{"name", "description"}]`, core first |
| `GET /spec`, `GET /skill` | | `SPEC.md` and `SKILL.md` as `text/markdown` |
| `GET /docs`, `GET /openapi.json` | | OpenAPI |
| `POST /mcp` | JSON-RPC | the MCP server, below |

- `profile` is a profile name such as `pay` or `pform`. `null`, an empty string and `core` all mean the core vocabulary. A message can also name its profile itself with `p=`.
- `expect_acc` is the criteria the sender kept back, as `key:value` tokens joined by `+`, for example `len:120w+tone:plain+no:em-dash`. `acc` on `/make-rb` has the same shape. Either can also be a JSON list of tokens.
- `message` in `/validate` is the codec's best-effort parse. Trust it only when `ok` is true.
- `/gate` checks a batch of lines against the source document they state facts from, under a profile that makes the lines the record (`clin`, `pay`). Every row must be a valid line; every `ST` must carry `src=`; for `clin` the tail is a quote that must be found verbatim in the cited document line(s), the item kind must be one of the profile's, and there is one `src` per line; for `pay` an invoice line carries `amt cur kind` and net plus VAT must equal the amount. `document` is optional: without it the gate checks shape only and says so in `notes`. `rows` reports every row with its own errors; `accepted` holds the parsed `ST` messages that passed. Limits: 200k characters of document, 60k of lines, 500 rows.
- `/from-json` takes the message as an object or as a string that holds one. `/make-rb` needs an `HO` line.
- `hash` on `/make-rb` defaults to true, which adds `h=` (the digest of the HO).
- `/spec` and `/skill` answer a browser with `text/plain`, because browsers offer to save `text/markdown` instead of showing it. Any other client gets `text/markdown`.

Limits: a line is at most 2000 characters and any other field at most 1000. Profile names are plain names (`[A-Za-z0-9_-]`, up to 64 characters). The reference codec builds a file path from the profile name, both from the `profile` field and from a `p=` inside a message, so the app refuses anything path-like before the codec sees it. There is no rate limiting; put the service behind your platform's limits if it is public.

## MCP server

The MCP endpoint is `POST /mcp`: Streamable HTTP, stateless, plain JSON responses, no auth. Locally that is `http://localhost:8000/mcp`. Deployed it is `https://YOUR-HOST/mcp`. `GET` and `DELETE` answer 405, since a stateless server has no event stream or session to offer. `/mcp/` with a trailing slash works too and is not redirected.

It is built on the official [`mcp`](https://pypi.org/project/mcp/) Python SDK, pinned to `<2` in `requirements.txt`: the 2.x line renamed `FastMCP` to `MCPServer` and moved the transport options, and `app/mcp.py` is written for 1.x.

| Tool | Arguments | What it does |
|---|---|---|
| `validate` | `line`, `profile` | Checks one line. Returns `ok`, `message`, `errors`, `warnings`. |
| `gate` | `lines`, `profile`, `document`, `doc_id` | Checks lines against the source document they state facts from. A failed gate is a result with `ok: false`, not a tool error. |
| `check_rb` | `ho`, `rb`, `profile`, `expect_acc` | Sender-side check of a readback across the five tiers. |
| `check_ho` | `ho`, `record`, `profile` | Before an irreversible act: the HO against the record it was built from. |
| `check_dn` | `ho`, `dn`, `profile`, `rb` | After it: the done report against the plan. |
| `make_rb` | `ho`, `id`, `profile`, `acc`, `do`, `hash` | Builds a correct readback for an HO. |
| `legend` | `profile` | The legend to paste into another agent's prompt. |
| `to_json` | `line`, `profile` | The line's JSON form. |

All six are marked read-only. A tool error, such as an unknown profile, comes back as a result with `isError: true`, so the calling model can see it and correct itself.

### Add it to Claude Code

```
claude mcp add --transport http rogerwilco https://YOUR-HOST/mcp
```

Add `--scope project` to write it to the repo's `.mcp.json` so the whole team gets it. The same thing by hand:

```json
{
  "mcpServers": {
    "rogerwilco": { "type": "http", "url": "https://YOUR-HOST/mcp" }
  }
}
```

Run `/mcp` inside Claude Code to see that it connected.

### Add it to Cursor

Put this in `.cursor/mcp.json` (one project) or `~/.cursor/mcp.json` (all projects), or add the same URL in Cursor's MCP settings:

```json
{
  "mcpServers": {
    "rogerwilco": { "url": "https://YOUR-HOST/mcp" }
  }
}
```

### Why the transport is set up this way

`stateless_http` and `json_response` are on, so a client needs one POST and nothing survives a restart or a second replica. The SDK's DNS rebinding protection is off: by default it only accepts `Host: localhost` and would answer 421 to every request behind a real domain. The server is public, keeps no state and takes no credentials, so there is nothing for such an attack to reach.

## Try it with curl

Start the server as above, then run these. They are the commands used to check the app.

<!-- smoke:begin -->
```bash
BASE=http://localhost:8000

# the app is up
curl -s $BASE/healthz

# the home page is served
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $BASE/

# a valid line, then an invalid one
curl -s -X POST $BASE/validate -H 'content-type: application/json' \
  -d '{"line":"RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT"}'
curl -s -X POST $BASE/validate -H 'content-type: application/json' \
  -d '{"line":"RW1 HO a-1 from=a to=b ask=WRITE"}'

# build a readback, then check it against the HO
curl -s -X POST $BASE/make-rb -H 'content-type: application/json' \
  -d '{"ho":"RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT","id":"b-1"}'
curl -s -X POST $BASE/check-rb -H 'content-type: application/json' \
  -d '{"ho":"RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT","rb":"RW1 RB b-1 re=a-1 from=b to=a item=x:1 ask=BUILD"}'

# the legend for the pay profile
curl -s "$BASE/legend?profile=pay" | head -c 200; echo

# MCP: list the tools, then call one
curl -s -X POST $BASE/mcp -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
curl -s -X POST $BASE/mcp -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"validate","arguments":{"line":"RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT"}}}'
```
<!-- smoke:end -->

## Tests

```
pip install pytest httpx
python -m pytest app/tests
```

The tests cover every endpoint, the five readback tiers, the checks before and after an irreversible act, the MCP handshake and tools, and how the app starts. They also run the lines shown on the home page and the quickstart through the API, so the pages cannot drift from the codec.

## The site

The site is six pages, each a self-contained HTML file under `static/` with no build step: `/` (what it is and the three-message loop), `/demo` (one handover between two scripted agents, step by step, every check a live call to the API; its script is `demo.js`), `/quickstart` (four ways to start, each with a real request and reply), `/lines` (every message type with an example, and what a program checks), `/profiles` (the same loop in four kinds of work, and how to write a profile; the same path answers a program with the JSON list of profiles) and `/research` (the five studies in plain words, each with its full report).

`/` is one self-contained page with no build step. It leads with what goes wrong in a handover, the control that catches it and the figure from the studies, then three panels. Paste a line and validate it, convert it to JSON, take its digest, or build the readback a receiver would send. The second panel is the sender's check: paste the HO and the RB, and it shows which of the four tiers passed. Roger is receipt and integrity, wilco is echo and comprehension. The third is the gate: paste a document and the lines that state facts from it, and it shows which pointers hold. All three open on a working example. The figures on the page are tested against the results tables under `research/`, so the page cannot drift from the studies.
