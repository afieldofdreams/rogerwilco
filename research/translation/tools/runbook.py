#!/usr/bin/env python3
"""Plan, ingest, gate and track the extraction jobs.

A job is one (arm, model, run k, group of three documents). Arms: L (rogerwilco lines) and J (JSON
objects with the same vocabulary). Models: sonnet, haiku. Three runs per arm and model; each run
partitions the twelve documents into four groups of three, differently in each run, and one agent
translates one group in a single reply. The orchestrating session spawns the agent with the prompt
file, saves the reply, splits it by its `# doc:<n>` headers into one output file per document, and
gates each. Rejections go back to the same agent for one or two fix rounds. Everything is on disk:
prompt, every raw reply, every version of every output, every gate verdict.

usage: python3 tools/runbook.py plan                                   # write the prompt files, list the jobs
       python3 tools/runbook.py ingest <run_id> [group ...]             # split the agents' output files into doc files and gate them
       python3 tools/runbook.py status                                  # one line per run
       python3 tools/runbook.py errors <run_id> [doc ...]               # the gate's problems, for the fix message
"""
from __future__ import annotations
import json, pathlib, re, shutil, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import RUNS  # noqa: E402
from prompts import build  # noqa: E402
import gate as gate_mod  # noqa: E402

ARMS = {"L": "rw", "J": "jsonl"}
MODELS = ("sonnet", "haiku")
GROUPS = {
    1: [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]],
    2: [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]],
    3: [[1, 8, 10], [2, 4, 12], [3, 5, 11], [6, 7, 9]],
}


def jobs() -> list[dict]:
    out = []
    for arm, ext in ARMS.items():
        for model in MODELS:
            for k, groups in GROUPS.items():
                rid = f"{arm}-{model}-{k}"
                for gi, docs in enumerate(groups, 1):
                    out.append({"run": rid, "arm": arm, "model": model, "k": k, "group": gi, "docs": docs, "ext": ext,
                                "prompt": RUNS / rid / "prompts" / f"g{gi}.md", "reply": RUNS / rid / "raw" / f"g{gi}.txt",
                                # Sonnet loops past the output limit on a single 100-line write, so it writes one file per document
                                "per_doc": {d: str(RUNS / rid / "raw" / f"doc{d:02d}.txt") for d in docs} if model == "sonnet" else None})
    return out


def out_path(rid: str, doc: int, ext: str) -> pathlib.Path:
    return RUNS / rid / f"doc{doc:02d}.{ext}"


def plan() -> None:
    for j in jobs():
        j["prompt"].parent.mkdir(parents=True, exist_ok=True)
        j["reply"].parent.mkdir(parents=True, exist_ok=True)
        j["prompt"].write_text(build(j["arm"], j["docs"], str(j["reply"]), j["per_doc"]))
    print(f"{len(jobs())} jobs planned under {RUNS}")
    for j in jobs():
        print(f"{j['run']} g{j['group']} docs {j['docs']} -> {j['prompt']}")


HDR_RE = re.compile(r"^\s*#\s*doc:(\d+)\s*$")


def split_reply(text: str) -> dict[int, str]:
    """Split a reply into per-document blocks on `# doc:<n>` headers. Lines are dedented (the harness indents replies)."""
    blocks, cur = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        m = HDR_RE.match(line)
        if m:
            cur = int(m.group(1)); blocks[cur] = []
            continue
        if not line or line.startswith("```"):
            continue
        if cur is None:
            # a row before any header: assign by the src it carries
            ms = re.search(r"doc:(\d+)#l", line)
            if ms:
                cur = int(ms.group(1)); blocks.setdefault(cur, [])
            else:
                continue
        blocks[cur].append(line)
    return {d: "\n".join(rows) + "\n" for d, rows in blocks.items()}


def ingest(rid: str, group: int, reply_file: pathlib.Path | None = None) -> None:
    j = next(x for x in jobs() if x["run"] == rid and x["group"] == group)
    raw_dir = RUNS / rid / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(raw_dir.glob(f"g{group}.v*.txt")))
    if j["per_doc"] and not reply_file:
        # one raw file per document; keep a versioned copy of each, and a joined copy as the group's raw reply
        parts = []
        for d in j["docs"]:
            f = pathlib.Path(j["per_doc"][d])
            if f.exists():
                parts.append(f"# doc:{d}\n" + f.read_text().strip() + "\n")
        if not parts:
            print(f"{rid} g{group}: no output files yet"); return
        text = "\n".join(parts)
        (raw_dir / f"g{group}.v{n + 1}.txt").write_text(text)
    else:
        reply_file = reply_file or j["reply"]
        if not reply_file.exists():
            print(f"{rid} g{group}: no reply file at {reply_file}"); return
        text = reply_file.read_text()
        shutil.copy(reply_file, raw_dir / f"g{group}.v{n + 1}.txt")
    blocks = split_reply(text)
    for d in j["docs"]:
        if d not in blocks:
            print(f"{rid} doc{d:02d}: MISSING from the reply")
            continue
        p = out_path(rid, d, j["ext"])
        p.write_text(blocks[d])
        r = gate_mod.run(p, j["arm"], d)
        hist = p.parent / "history"; hist.mkdir(exist_ok=True)
        v = len(list(hist.glob(f"doc{d:02d}.v*.{j['ext']}"))) + 1
        shutil.copy(p, hist / f"doc{d:02d}.v{v}.{j['ext']}")
        (hist / f"doc{d:02d}.v{v}.gate.json").write_text(json.dumps(r, indent=1))
        print(f"{rid} doc{d:02d}: " + (f"OK {r['counts']['st']} ({r['tokens']} tokens)" if r["ok"] else f"REJECTED {len(r['errors'])}"))
    extra = set(blocks) - set(j["docs"])
    if extra:
        print(f"{rid} g{group}: reply carried blocks for documents not in this group: {sorted(extra)} (ignored)")


def redo(rid: str, docs: list[int]) -> None:
    """A single-document prompt for a document whose group agent died (Sonnet's output loop): same rules, one document."""
    arm, model = rid.split("-")[0], rid.split("-")[1]
    for d in docs:
        out = RUNS / rid / "raw" / f"doc{d:02d}.txt"
        pf = RUNS / rid / "prompts" / f"doc{d:02d}.md"
        pf.write_text(build(arm, [d], str(out), {d: str(out)}))
        print(f"{rid} doc{d:02d}: prompt {pf}")


def ingest_doc(rid: str, doc: int) -> None:
    """Gate one document written by a single-document (redo) agent."""
    arm = rid.split("-")[0]; ext = ARMS[arm]
    f = RUNS / rid / "raw" / f"doc{doc:02d}.txt"
    if not f.exists():
        print(f"{rid} doc{doc:02d}: no output"); return
    blocks = split_reply(f"# doc:{doc}\n" + f.read_text())
    p = out_path(rid, doc, ext)
    p.write_text(blocks.get(doc, ""))
    r = gate_mod.run(p, arm, doc)
    hist = p.parent / "history"; hist.mkdir(exist_ok=True)
    v = len(list(hist.glob(f"doc{doc:02d}.v*.{ext}"))) + 1
    shutil.copy(p, hist / f"doc{doc:02d}.v{v}.{ext}")
    (hist / f"doc{doc:02d}.v{v}.gate.json").write_text(json.dumps(r, indent=1))
    print(f"{rid} doc{doc:02d}: " + (f"OK {r['counts']['st']} ({r['tokens']} tokens)" if r["ok"] else f"REJECTED {len(r['errors'])}"))


def regate() -> None:
    """Re-run the gate on every current output (after a gate change); rewrites the latest history verdict too."""
    for j in jobs():
        for d in j["docs"]:
            p = out_path(j["run"], d, j["ext"])
            if not p.exists():
                continue
            r = gate_mod.run(p, j["arm"], d)
            hist = sorted((p.parent / "history").glob(f"doc{d:02d}.v*.gate.json"))
            if hist:
                hist[-1].write_text(json.dumps(r, indent=1))
            print(f"{j['run']} doc{d:02d}: " + (f"OK {r['counts']['st']}" if r["ok"] else f"REJECTED {len(r['errors'])}"))


def gate_result(rid: str, doc: int) -> dict | None:
    ext = ARMS[rid[0]]
    g = out_path(rid, doc, ext).with_suffix(f".{ext}.gate.json")
    return json.loads(g.read_text()) if g.exists() else None


def status() -> None:
    for arm in ARMS:
        for model in MODELS:
            for k in GROUPS:
                rid = f"{arm}-{model}-{k}"
                cells = []
                for d in range(1, 13):
                    r = gate_result(rid, d)
                    cells.append(f"{d:02d}:" + ("-" if r is None else (f"ok{r['counts']['st']}" if r["ok"] else f"REJ{len(r['errors'])}")))
                print(rid, " ".join(cells))


def errors(rid: str, docs: list[int]) -> None:
    for d in docs or range(1, 13):
        r = gate_result(rid, d)
        if r and not r["ok"]:
            print(f"doc:{d} was rejected ({len(r['errors'])} problems):")
            for e in r["errors"]:
                print("  " + e)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "plan":
        plan()
    elif cmd == "ingest":
        for g in sys.argv[3:] or ["1", "2", "3", "4"]:
            ingest(sys.argv[2], int(g))
    elif cmd == "redo":
        redo(sys.argv[2], [int(x) for x in sys.argv[3:]])
    elif cmd == "ingest-doc":
        for d in sys.argv[3:]:
            ingest_doc(sys.argv[2], int(d))
    elif cmd == "regate":
        regate()
    elif cmd == "errors":
        errors(sys.argv[2], [int(x) for x in sys.argv[3:]])
    else:
        status()
