#!/usr/bin/env python3
"""Stamps the shared head, header and footer onto every page under app/static.

  python3 app/tools/stamp.py          # rewrite every page in place; idempotent

Each page keeps its own content between the markers; the head links (fonts, site.css, site.js, each with a version
query from its content), the header with the nav (the current page marked, behind a menu button on a narrow screen) and
the footer are the same everywhere and come from this file. There is still no build
step at deploy time: the stamped HTML is what is committed and served.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"


def version() -> str:
    """A short digest of the stylesheet and the script, appended to their URLs so a deploy is never served stale
    styles from a cache between the server and the browser."""
    h = hashlib.sha256()
    for name in ("site.css", "site.js"):
        h.update((STATIC / name).read_bytes())
    return h.hexdigest()[:8]


SITE = "https://rogerwilco.crox.io"


def meta(page: str, path: str) -> str:
    """Canonical URL, Open Graph and Twitter tags from the page's own title and description; JSON-LD on the home page."""
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)">', page, re.S)
    t = title.group(1).strip() if title else "rogerwilco"
    d = desc.group(1).strip() if desc else ""
    url = SITE + path
    out = [f'<link rel="canonical" href="{url}">',
           '<meta property="og:type" content="website">', '<meta property="og:site_name" content="rogerwilco">',
           f'<meta property="og:title" content="{t}">', f'<meta property="og:description" content="{d}">',
           f'<meta property="og:url" content="{url}">', '<meta name="twitter:card" content="summary">',
           '<link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">']
    if path == "/":
        ld = {"@context": "https://schema.org", "@type": "SoftwareSourceCode", "name": "rogerwilco",
              "description": html.unescape(d), "url": SITE, "codeRepository": "https://github.com/afieldofdreams/rogerwilco",
              "programmingLanguage": "Python", "license": "https://www.apache.org/licenses/LICENSE-2.0",
              "author": {"@type": "Organization", "name": "Croxio Ltd", "url": "https://crox.io"},
              "runtimePlatform": "Python 3.10+", "keywords": "AI agents, agent handoff, readback, MCP, payments, guardrails"}
        out.append('<script type="application/ld+json">' + json.dumps(ld) + "</script>")
    return "\n".join(out)


def head(page: str = "", path: str = "/") -> str:
    v = version()
    return meta(page, path) + "\n" + ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=DM+Mono:wght@400;500&display=swap">\n'
            f'<link rel="stylesheet" href="/static/site.css?v={v}">\n'
            f'<script src="/static/site.js?v={v}" defer></script>\n'
            '<noscript><style>.site-nav{display:flex!important}.nav-toggle{display:none!important}</style></noscript>\n'
            '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'6\' fill=\'%23B8402A\'/%3E%3Cpath d=\'M8 17l5 5 11-12\' fill=\'none\' stroke=\'%23fff\' stroke-width=\'3.5\' stroke-linecap=\'round\' stroke-linejoin=\'round\'/%3E%3C/svg%3E">')


NAV = [("/quickstart", "start"), ("/demo", "demo"), ("/lines", "what a line is"), ("/profiles", "profiles"), ("/research", "research"),
       ("/about", "about"), ("/docs", "api")]


def header(current: str) -> str:
    links = []
    for href, text in NAV:
        cur = ' aria-current="page"' if current == href or (href == "/research" and current.startswith("/research")) else ""
        links.append(f'<a href="{href}"{cur}>{text}</a>')
    links.append('<a class="lab" href="https://crox.io">Crox</a>')
    return ('<header class="site-head">\n'
            '  <p class="mark"><a href="/"><span class="roger">roger</span><span class="wilco">wilco</span></a><span class="ver">RW1</span></p>\n'
            '  <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Menu">'
            '<svg viewBox="0 0 24 24" aria-hidden="true"><line class="l1" x1="4" y1="6" x2="20" y2="6"/><line class="l2" x1="4" y1="12" x2="20" y2="12"/><line class="l3" x1="4" y1="18" x2="20" y2="18"/></svg></button>\n'
            '  <nav class="site-nav" id="site-nav" aria-label="Site">' + " ".join(links) + '</nav>\n'
            '</header>')


FOOTER = ('<footer class="site-foot">\n'
          '  <span>Protocol RW1</span>\n'
          '  <span><code>pip install rogerwilco</code></span>\n'
          '  <span><a href="/quickstart">Integrate</a> · <a href="/llms.txt">llms.txt</a></span>\n'
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
    out = between(s, HEAD_MARK, head(s, page_path(file)))
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
