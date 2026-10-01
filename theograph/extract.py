"""Extraction: one document at a time, gated, with automatic fix rounds.

For each document in the registry: build the prompt, ask the model, gate the reply; if refused,
send the gate's errors back and ask for the whole output again, up to --rounds times. Every reply
is kept under raw/<doc id>.v<k>.txt with its verdict. Accepted assertions go to assertions.jsonl,
one row each, carrying the document's id, number, patient, type and date.

With --review, an accepted output gets a second turn in the same conversation: the model reads the
document again against its own lines and adds the statements it missed, which go through the same
gate (with the first lines, so ids stay unique) and are marked pass=review. The gate makes invention
impossible; the review is the check for omission.

Assertions extracted elsewhere can be brought in with --provider mock --from-files <dir>, where
<dir> holds one reply per document (<doc id>.txt) in line or JSON form; they go through the same gate.
"""
from __future__ import annotations
import json, pathlib, re, time
from . import read_jsonl, write_jsonl
from .gate import gate
from .llm import FromFiles, make
from .prompt import build, fix_message, review_message
from .registry import load_registry

FENCE_RE = re.compile(r"^```[a-z]*\n|\n```\s*$", re.M)


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = FENCE_RE.sub("", text)
    return text.strip() + "\n"


def extract(out_dir: pathlib.Path, provider: str, model: str | None, from_files: str | None, rounds: int = 2, form: str = "lines", only: list[str] | None = None, redo: bool = False, review: bool = False) -> None:
    docs = load_registry(out_dir)
    if not docs:
        raise SystemExit(f"no registry in {out_dir}; run ingest first")
    prov = make(provider, model, from_files)
    raw = out_dir / "raw"; raw.mkdir(parents=True, exist_ok=True)
    existing = {a["doc"]: True for a in read_jsonl(out_dir / "assertions.jsonl")}
    rows = [a for a in read_jsonl(out_dir / "assertions.jsonl")]
    log = read_jsonl(out_dir / "extract_log.jsonl")
    for doc in docs:
        if only and doc["id"] not in only:
            continue
        if doc["id"] in existing and not redo:
            print(f"{doc['id']}: already extracted (use --redo to replace)"); continue
        if isinstance(prov, FromFiles):
            prov.doc_id = doc["id"]
        messages = [{"role": "user", "content": build(doc)}]
        accepted, errors, parsed, usage = [], ["not run"], [], []
        t0 = time.time()
        for k in range(rounds + 1):
            text, u = prov.chat(messages)
            usage.append(u)
            body = strip_fences(text)
            (raw / f"{doc['id']}.v{k + 1}.txt").write_text(body)
            accepted, errors, parsed = gate(body, doc["num"], doc["lines"], form)
            (raw / f"{doc['id']}.v{k + 1}.gate.json").write_text(json.dumps({"ok": not errors, "errors": errors, "n": len(parsed)}, indent=1))
            if not errors:
                break
            print(f"{doc['id']}: attempt {k + 1} refused ({len(errors)} problems)")
            messages += [{"role": "assistant", "content": text}, {"role": "user", "content": fix_message(errors)}]
        status = "ok" if not errors else "rejected"
        added, review_attempts = 0, 0
        if not errors and review and form == "lines":
            first = [a["line"] for a in accepted]
            messages += [{"role": "assistant", "content": text}, {"role": "user", "content": review_message(doc["n_lines"], len(accepted) + 1)}]
            r_errors = ["not run"]
            for k in range(rounds + 1):
                r_text, u = prov.chat(messages); usage.append(u); review_attempts += 1
                r_body = strip_fences(r_text)
                (raw / f"{doc['id']}.review.v{k + 1}.txt").write_text(r_body)
                # gate the additions together with the first lines (minus their DN) so ids stay unique
                joined = "\n".join(first) + "\n" + r_body
                r_accepted, r_errors, _ = gate(joined, doc["num"], doc["lines"], form)
                (raw / f"{doc['id']}.review.v{k + 1}.gate.json").write_text(json.dumps({"ok": not r_errors, "errors": r_errors, "n_added": max(0, len(r_accepted) - len(accepted))}, indent=1))
                if not r_errors:
                    for a in r_accepted[len(accepted):]:
                        a["pass"] = "review"
                    accepted = r_accepted; added = len(r_accepted) - len(first)
                    break
                print(f"{doc['id']}: review attempt {k + 1} refused ({len(r_errors)} problems)")
                messages += [{"role": "assistant", "content": r_text}, {"role": "user", "content": fix_message(r_errors)}]
            if r_errors:
                print(f"{doc['id']}: review REJECTED after {review_attempts} attempts; first lines kept")
        if not errors:
            rows = [r for r in rows if r["doc"] != doc["id"]]
            for a in accepted:
                rows.append({"doc": doc["id"], "doc_num": doc["num"], "patient": doc["patient"], "doc_type": doc["type"], "doc_date": doc["date"],
                             "doc_specialty": doc.get("specialty"), "pass": a.get("pass", "first"), **{k: v for k, v in a.items() if k not in ("line", "pass")}, "raw": a["line"]})
            print(f"{doc['id']}: OK {len(accepted)} assertions" + (f" after {len(usage) - review_attempts} attempts" if len(usage) - review_attempts > 1 else "") + (f", {added} added by review" if review else ""))
        else:
            print(f"{doc['id']}: REJECTED after {len(usage)} attempts; see raw/{doc['id']}.v{len(usage)}.gate.json")
        log.append({"doc": doc["id"], "status": status, "attempts": len(usage) - review_attempts, "review_attempts": review_attempts, "added_by_review": added, "errors_final": len(errors), "usage": usage, "seconds": round(time.time() - t0, 1), "provider": provider, "model": model})
    write_jsonl(out_dir / "assertions.jsonl", rows)
    write_jsonl(out_dir / "extract_log.jsonl", log)
    print(f"{len(rows)} assertions in {out_dir / 'assertions.jsonl'}")
