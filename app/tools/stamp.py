#!/usr/bin/env python3
"""Stamps the shared head, header and footer onto every page under app/static.

  python3 app/tools/stamp.py          # rewrite every page in place; idempotent

Each page keeps its own content between the markers; the head links (fonts, site.css), the header with the nav
(the current page marked) and the footer are the same everywhere and come from this file. There is still no build
step at deploy time: the stamped HTML is what is committed and served.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"

HEAD = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=DM+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/static/site.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23B8402A'/%3E%3Cpath d='M8 17l5 5 11-12' fill='none' stroke='%23fff' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">'''

NAV = [("/quickstart", "start"), ("/lines", "what a line is"), ("/profiles", "profiles"), ("/research", "research"),
       ("/about", "about"), ("/docs", "api")]


def header(current: str) -> str:
    links = []
    for href, text in NAV:
        cur = ' aria-current="page"' if current == href or (href == "/research" and current.startswith("/research")) else ""
        links.append(f'<a href="{href}"{cur}>{text}</a>')
    links.append('<a class="lab" href="https://crox.io">Crox</a>')
    return ('<header class="site-head">\n'
            '  <p class="mark"><a href="/"><span class="roger">roger</span><span class="wilco">wilco</span></a><span class="ver">RW1</span></p>\n'
            '  <nav class="site-nav" aria-label="Site">' + " ".join(links) + '</nav>\n'
            '</header>')


FOOTER = ('<footer class="site-foot">\n'
          '  <span>Protocol RW1</span>\n'
          '  <span>Tools for agents: <code id="mcp-url">https://rogerwilco.crox.io/mcp</code></span>\n'
          '  <span><a href="https://github.com/afieldofdreams/rogerwilco">Source</a></span>\n'
          '  <span>A <a href="https://crox.io">Crox</a> lab. London.</span>\n'
          '</footer>')

HEAD_MARK = ("<!-- site:head -->", "<!-- /site:head -->")
HEADER_MARK = ("<!-- site:header -->", "<!-- /site:header -->")
FOOTER_MARK = ("<!-- site:footer -->", "<!-- /site:footer -->")


def between(s: str, marks: tuple[str, str], content: str) -> str:
    a, b = marks
    if a in s and b in s:
        return s[: s.index(a) + len(a)] + "\n" + content + "\n" + s[s.index(b):]
    return s


def page_path(file: Path) -> str:
    rel = file.relative_to(STATIC).as_posix()
    if rel == "index.html":
        return "/"
    if rel == "research/index.html":
        return "/research"
    return "/" + rel.removesuffix(".html")


def stamp(file: Path) -> bool:
    s = file.read_text(encoding="utf-8")
    if HEAD_MARK[0] not in s or HEADER_MARK[0] not in s or FOOTER_MARK[0] not in s:
        return False
    out = between(s, HEAD_MARK, HEAD)
    out = between(out, HEADER_MARK, header(page_path(file)))
    out = between(out, FOOTER_MARK, FOOTER)
    if out != s:
        file.write_text(out, encoding="utf-8")
    return True


def main() -> int:
    done = []
    for f in sorted(STATIC.rglob("*.html")):
        if stamp(f):
            done.append(f.relative_to(STATIC).as_posix())
    print("stamped:", ", ".join(done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
