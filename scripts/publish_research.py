#!/usr/bin/env python3
"""Copy the research results pages into the app so rogerwilco.crox.io/research serves them.

The app never reads research/ at runtime (CLAUDE.md); this script is the one place the two meet.
Each report is an HTML fragment (title, link, style, then the page) written for a hosting skeleton,
so it is wrapped in a full document here. Run after a report changes, then commit app/static/research/.

usage: python3 scripts/publish_research.py
"""
from __future__ import annotations
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "static" / "research"
PAGES = {
    "wire-study": ROOT / "research" / "wire-study" / "report.html",
    "pilot": ROOT / "research" / "pilot" / "report.html",
    "month-end": ROOT / "research" / "month-end" / "results" / "report.html",
}
NAV = ('<nav class="rw-nav" aria-label="Site"><a href="/">rogerwilco</a> <span aria-hidden="true">/</span> '
       '<a href="/research">research</a></nav>')
NAV_CSS = ('.rw-nav{font-family:"IBM Plex Mono","SFMono-Regular",Menlo,Consolas,monospace;font-size:0.8rem;'
           'letter-spacing:0.04em;text-transform:uppercase;max-width:70ch;margin:0 auto 1.4rem}'
           '.rw-nav a{color:inherit;text-decoration:none;opacity:0.7}.rw-nav a:hover{opacity:1;text-decoration:underline}'
           '.rw-nav span{opacity:0.4;margin:0 0.3rem}')


def wrap(fragment: str) -> str:
    m = re.search(r"</style>\s*", fragment)
    if not m:
        raise SystemExit("report has no <style> block; expected the artifact fragment shape")
    head, body = fragment[:m.end()], fragment[m.end():]
    head = head.replace("</style>", NAV_CSS + "\n</style>", 1)
    body = body.replace("<main>", NAV + "\n<main>", 1)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, src in PAGES.items():
        (OUT / f"{slug}.html").write_text(wrap(src.read_text()))
        print(f"{src.relative_to(ROOT)} -> app/static/research/{slug}.html")


if __name__ == "__main__":
    main()
