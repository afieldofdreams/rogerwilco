"""theograph command line.

  python3 -m theograph ingest   <docs dir> <out dir> [--patient ID]
  python3 -m theograph extract  <out dir> --provider anthropic|openai|mock [--model M] [--from-files DIR] [--rounds 2] [--form lines|json] [--only DOC ...] [--redo] [--review]
  python3 -m theograph normalise <out dir> [--synonyms extra.json]
  python3 -m theograph link     <out dir>
  python3 -m theograph analyse  <out dir>
  python3 -m theograph render   <out dir> [--title T]
  python3 -m theograph run      <docs dir> <out dir> --provider ... (all of the above in order)
"""
from __future__ import annotations
import argparse, pathlib, sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="theograph", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest"); s.add_argument("docs"); s.add_argument("out"); s.add_argument("--patient")
    s = sub.add_parser("extract"); s.add_argument("out"); s.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "mock"]); s.add_argument("--model")
    s.add_argument("--from-files"); s.add_argument("--rounds", type=int, default=2); s.add_argument("--form", default="lines", choices=["lines", "json"]); s.add_argument("--only", nargs="*"); s.add_argument("--redo", action="store_true"); s.add_argument("--review", action="store_true")
    s = sub.add_parser("normalise"); s.add_argument("out"); s.add_argument("--synonyms")
    s = sub.add_parser("link"); s.add_argument("out")
    s = sub.add_parser("analyse"); s.add_argument("out")
    s = sub.add_parser("render"); s.add_argument("out"); s.add_argument("--title")
    s = sub.add_parser("run"); s.add_argument("docs"); s.add_argument("out"); s.add_argument("--patient"); s.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "mock"]); s.add_argument("--model")
    s.add_argument("--from-files"); s.add_argument("--rounds", type=int, default=2); s.add_argument("--form", default="lines", choices=["lines", "json"]); s.add_argument("--review", action="store_true"); s.add_argument("--synonyms"); s.add_argument("--title")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out).resolve()
    if a.cmd in ("ingest", "run"):
        from .registry import build_registry
        docs = build_registry(pathlib.Path(a.docs).resolve(), out, a.patient)
        print(f"{len(docs)} documents registered in {out / 'registry.jsonl'}")
        for d in docs:
            print(f"  {d['num']:>2} {d['id']}: {d['type']}, {d.get('date')}, {d.get('specialty') or ''}, {d['n_lines']} lines")
    if a.cmd in ("extract", "run"):
        from .extract import extract
        extract(out, a.provider, a.model, a.from_files, a.rounds, a.form, getattr(a, "only", None), getattr(a, "redo", False), a.review)
    if a.cmd in ("normalise", "run"):
        from .normalise import normalise
        normalise(out, pathlib.Path(a.synonyms) if a.synonyms else None)
    if a.cmd in ("link", "run"):
        from .link import link
        link(out)
    if a.cmd in ("analyse", "run"):
        from .analyse import analyse
        analyse(out)
    if a.cmd in ("render", "run"):
        from .render import render
        render(out, a.title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
