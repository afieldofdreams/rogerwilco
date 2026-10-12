#!/usr/bin/env python3
"""Writes app/static/explained.html, the plain-language walk through the studies, with its flow diagrams.

  python3 app/tools/explained.py       # rewrites the page; then run app/tools/stamp.py

The diagrams are inline SVG laid out from small specs below, so every test's picture shares one geometry and the
colours come from site.css tokens (the SVG uses style attributes, which take var()). The figures in the text are the
ones on the research pages: studies 6 and 7, both receivers; when a study is re-run, change them here and regenerate.
"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "static" / "explained.html"

# ---------------------------------------------------------------- the diagrams
BOX_W, BOX_H, GAP, Y = 146, 46, 46, 64
KIND = {  # fill, stroke, text
    "human": ("var(--surface)", "var(--ink)", "var(--ink)"),
    "agent": ("var(--well)", "var(--muted)", "var(--ink)"),
    "check": ("var(--good)", "var(--good)", "var(--paper)"),
    "tool": ("var(--ink)", "var(--ink)", "var(--paper)"),
}
MARK = {"ok": ("var(--good)", "✓"), "bad": ("var(--bad)", "✗"), "warn": ("var(--warn)", "!")}


def flow(nodes, marks=(), edges=None, title=""):
    """nodes: (kind, label[, sublabel]) left to right; edges: a label under each arrow; marks: (index, ok|bad|warn, text)
    above a node. One figure, one claim: the title is the SVG's accessible name."""
    n = len(nodes)
    w = n * BOX_W + (n - 1) * GAP + 24
    h = 150
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}" style="width:{w}px;max-width:100%;min-width:{min(w, 640)}px;height:auto">',
           '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           '<path d="M0,0 L10,5 L0,10 z" style="fill:currentColor"/></marker></defs>']
    xs = []
    for i, nd in enumerate(nodes):
        kind, label = nd[0], nd[1]
        sub = nd[2] if len(nd) > 2 else None
        x = 12 + i * (BOX_W + GAP)
        xs.append(x)
        fill, stroke, color = KIND[kind]
        rx = 23 if kind == "check" else 8
        out.append(f'<rect x="{x}" y="{Y}" width="{BOX_W}" height="{BOX_H}" rx="{rx}" style="fill:{fill};stroke:{stroke};stroke-width:1.5"/>')
        ty = Y + BOX_H / 2 + (5 if not sub else 1)
        out.append(f'<text x="{x + BOX_W / 2}" y="{ty}" text-anchor="middle" font-size="12.5" font-weight="600" style="fill:{color}">{escape(label)}</text>')
        if sub:
            out.append(f'<text x="{x + BOX_W / 2}" y="{ty + 14}" text-anchor="middle" font-size="11" style="fill:{color};opacity:.85">{escape(sub)}</text>')
        if i < n - 1:
            x1, x2 = x + BOX_W + 3, x + BOX_W + GAP - 4
            out.append(f'<line x1="{x1}" y1="{Y + BOX_H / 2}" x2="{x2}" y2="{Y + BOX_H / 2}" style="stroke:currentColor;stroke-width:1.5" marker-end="url(#ah)"/>')
            if edges and edges[i]:
                out.append(f'<text x="{(x1 + x2) / 2}" y="{Y + BOX_H + 18}" text-anchor="middle" font-size="10.5" style="fill:var(--muted)">{escape(edges[i])}</text>')
    for idx, kind, text in marks:
        cx = xs[idx] + BOX_W / 2
        cy = 26
        col, glyph = MARK[kind]
        out.append(f'<circle cx="{cx}" cy="{cy}" r="11" style="fill:{col}"/>')
        out.append(f'<text x="{cx}" y="{cy + 4.5}" text-anchor="middle" font-size="13" font-weight="700" style="fill:var(--paper)">{glyph}</text>')
        out.append(f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" font-size="10.5" font-weight="600" style="fill:{col}">{escape(text)}</text>')
        out.append(f'<line x1="{cx}" y1="{cy + 28}" x2="{cx}" y2="{Y - 3}" style="stroke:{col};stroke-width:1;stroke-dasharray:2 3"/>')
    out.append("</svg>")
    return "\n".join(out)


def fig(svg: str, caption: str) -> str:
    return f'<figure class="flow"><div class="scroll">{svg}</div><figcaption>{caption}</figcaption></figure>'


D = {}
D["places"] = fig(flow([("human", "The boss", "says what to pay"), ("agent", "Scheduler agent", "writes the job"), ("agent", "Payer agent", "reads it, looks up account"), ("tool", "The payment tool", "moves the money")],
                       marks=[(1, "bad", "1. typed it wrong"), (2, "bad", "2. read it wrong"), (3, "bad", "3. did the wrong thing")],
                       edges=["the job", "the job", "pay"], title="The three places a mistake can come from"),
                  "The three places a mistake can come from. We planted mistakes in each one, thousands of times, and counted which got caught.")
D["prose"] = fig(flow([("human", "The boss"), ("agent", "Scheduler", "writes a paragraph"), ("agent", "Payer", "reads it"), ("tool", "Tool", "pays")],
                      marks=[(2, "bad", "nothing checks")], edges=["", "a paragraph", "pay"], title="Test 1: prose, nothing checks"),
                 "Test 1. The agents talk in ordinary sentences and nobody checks anything. A typed mistake sails straight through.")
D["judge"] = fig(flow([("agent", "Scheduler", "writes a paragraph"), ("agent", "Payer", "says it back in words"), ("agent", "A second AI", "judges the words"), ("tool", "Tool", "pays")],
                      marks=[(2, "warn", "it checks what it is asked")], edges=["a paragraph", "the readback", "yes, go"], title="Test 2: prose, read back, judged by another AI"),
                 "Test 2. The payer says the job back in words and a second AI judges whether it matches the record. Better, but the judge waved through jobs addressed to the wrong agent because the numbers matched.")
D["echo"] = fig(flow([("agent", "Scheduler", "writes a line"), ("agent", "Payer", "echoes the line back"), ("check", "Program compares", "line with line"), ("tool", "Tool", "pays")],
                     marks=[(2, "ok", "typed mistakes: caught"), (1, "bad", "its own mistake: invisible")], edges=["the line", "the echo", "yes, go"], title="Test 3: lines, echoed back, a program compares"),
                "Test 3. The job is a typed line and the payer echoes it back word for word. A program compares the two. Every typed mistake was caught. But the echo does not carry the account the payer looked up, so when the payer itself picked the wrong account, nothing saw it.")
D["values"] = fig(flow([("agent", "Scheduler", "writes a line"), ("agent", "Payer", "reads back its values"), ("check", "Program compares", "with the record"), ("tool", "Tool", "pays")],
                       marks=[(2, "ok", "strong models: nothing to catch"), (1, "warn", "weak model: stalls")], edges=["the line", "the readback", "yes, go"], title="Test 4: lines, the payer reads back the values it will use"),
                  "Test 4. The payer reads back the actual values it will use, the account it looked up included, and a program compares them with the approved record. Strong models never needed it. The weak model could not write the line and stalled, until we let it fill in a short English form instead.")
D["report"] = fig(flow([("check", "Program says yes"), ("tool", "Tool", "pays"), ("agent", "Payer", "reports what the tool did"), ("check", "Program compares", "with the plan")],
                       marks=[(3, "ok", "tool faults flagged"), (1, "bad", "but the money has moved")], edges=["go", "what it did", "the report"], title="Test 5: the report afterwards"),
                  "Test 5. After paying, the tool prints what it actually did and the payer reports that, not what it meant. A program compares the report with the plan. It flagged every tool fault on the Claude models, and 25 of 27 on the weak one, but only after the money had moved.")
D["window"] = fig(flow([("agent", "Payer", "hands over the values"), ("tool", "Tool prepares", "states what it will do"), ("check", "Program compares", "statement vs record"), ("tool", "Tool commits", "pays exactly as stated"), ("check", "Program checks", "the report")],
                       marks=[(2, "ok", "tool mistakes: caught before paying"), (3, "ok", "will not pay without a yes")], edges=["prepare", "the statement", "yes + ticket", "the report"], title="Test 6: the window"),
                  "Test 6, the window. The tool states exactly what it is about to do and freezes it under a ticket number. A program checks that statement against the record. Only then does the tool get a yes, and it will not pay without one. The report afterwards still runs.")
D["works"] = fig(flow([("agent", "Scheduler", "writes the line"), ("check", "Check 1", "line vs record"), ("tool", "Tool prepares", "its statement"), ("check", "Check 2", "statement vs record"), ("tool", "Tool commits", "on a yes"), ("check", "Check 3", "report vs plan")],
                      marks=[(1, "ok", "typed mistakes"), (3, "ok", "wrong account, wrong date"), (5, "ok", "a tool that lies at the end")], edges=["before sending", "the values", "yes + ticket", "the report", ""], title="The flow that works: three program checks"),
                 "The flow that works. Three program checks, at the three places mistakes come from. The agents still talk; the checks are what stop the money.")

# ---------------------------------------------------------------- the page
HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Say it back, explained</title>
<meta name="description" content="What we tested, test by test: prose with nothing checking, prose judged by an AI, lines echoed back, lines with the values the payer will use, the report afterwards, and the tool's own statement before it acts. With a diagram of each flow and the mistakes it caught.">
<!-- site:head -->
<!-- /site:head -->
</head>
<body>
<!-- site:header -->
<!-- /site:header -->
<main class="explained">
  <header>
    <p class="eyebrow">Seven studies · October 2026</p>
    <h1>Say it back, explained</h1>
    <p class="lede">AI agents hand jobs to each other, like "pay this bill". We tested six ways of doing that, planted mistakes on purpose, and counted which mistakes got caught before the money moved. This page tells the story one test at a time: what we were testing, the two ways a job can be said, then each test with a picture of who said what to whom and where the mistake was or was not caught.</p>
  </header>

  <section>
    <h2>What we were testing</h2>
    <p>Three agents and a tool. The boss says what to pay. The scheduler agent writes the job. The payer agent reads it and looks up the bank account. The payment tool moves the money. A mistake can enter at three places, and once the money has moved it cannot be undone.</p>
    {D["places"]}
    <p>The setting was a made-up company with a made-up month of bills, so no real money was ever at risk. We used four AI models from two companies: three strong ones and one weaker, cheaper one.</p>
  </section>

  <section>
    <h2>Two ways to say a job</h2>
    <p>Everything turns on this. A job can be a sentence, or it can be a <b>line</b>: the same facts in fixed slots, each with a label. A person can read both. Only the line can be checked by a program, because a program can find <code>amt=</code> and compare it with the record, and it cannot find "five thousand four hundred" in a sentence reliably.</p>
    <div class="vs">
      <div><span class="lbl">A sentence (prose)</span><p class="said">"Hi payer, please release the payment for Marlow Design Partners, invoice MD-2026-057: 5,400.00 GBP gross, to the account on file, on 2 October. Approved by the FD under FD-0929."</p></div>
      <div><span class="lbl">A line</span><pre class="line">RW1 <b>HO</b> scheduler-1 p=pay from=scheduler to=payer item=inv:MD-2026-057 ask=<b>PAY</b> rb=exec sup=marlow <b>amt=5400.00</b> cur=GBP kind=GROSS <b>acct=40-12-88/61102938</b> paid=20261002 ref=MD-2026-057 apref=FD-0929</pre></div>
    </div>
    <p>"Say it back" means the payer repeats the job before acting, the way a pilot repeats a clearance before flying it. The question we kept asking: who does the repeating, what do they repeat, and who checks it? <a href="/lines">What a line is</a> explains every message type with one example each.</p>
  </section>

  <section>
    <p class="eyebrow">Test 1</p>
    <h2>Just prose, nothing checks</h2>
    <p>The agents talk in ordinary sentences and act on them. This is how most agent systems work today.</p>
    {D["prose"]}
    <div class="tiles">
      <div class="tile"><b>15 of 48</b><span>typed mistakes became wrong payments on Sonnet, 14 of 48 on Haiku and 29 of 48 on each OpenAI model.</span></div>
      <div class="tile"><b>0 of 140</b><span>wrong payments on strong models when the job was right but the payer's files were full of traps. They did not fall for them.</span></div>
    </div>
    <p class="outcome is-bad"><span class="dot"></span>Did not work. Between a third and two thirds of typed mistakes went out as money. Strong models read well, so the danger is the sender's typing and the tool, not the reading.</p>
  </section>

  <section>
    <p class="eyebrow">Test 2</p>
    <h2>Prose, said back, judged by another AI</h2>
    <p>The payer writes back, in words, what it is about to do. A second AI reads that and the approved record and says whether they match.</p>
    {D["judge"]}
    <div class="tiles">
      <div class="tile"><b>8 of 48</b><span>typed mistakes still went out. Every one was a job addressed to the wrong agent; the numbers matched, so the judge said yes.</span></div>
      <div class="tile"><b>38 of 190</b><span>correct readbacks the judge wrongly refused on the weak model, over details the record did not mention; 10 of 186 on gpt-5.5 and 1 of 215 on each Claude model.</span></div>
    </div>
    <p class="outcome is-warn"><span class="dot"></span>Partly worked. An AI judge checks what it is asked to check, and it gets tired of details a program never misses.</p>
  </section>

  <section>
    <p class="eyebrow">Test 3</p>
    <h2>Lines, echoed back, a program compares</h2>
    <p>Now the job is a line. The payer echoes it back word for word, adds a fingerprint of what it received, and a program compares the echo with the original.</p>
    {D["echo"]}
    <div class="tiles">
      <div class="tile"><b>0 of 48</b><span>typed mistakes got through on the strong models, and 1 of 48 on the weak one. A changed digit or a wrong address shows up in the comparison.</span></div>
      <div class="tile"><b>14 of 129</b><span>wrong payments on the weak model, because it picked the wrong account itself. The echo does not carry the account it looked up, so the check could not see it.</span></div>
    </div>
    <p class="outcome is-warn"><span class="dot"></span>Worked for the sender's typing. Blind to the payer's own mistakes, and on the weak model the extra round made it worse than nothing.</p>
  </section>

  <section>
    <p class="eyebrow">Test 4</p>
    <h2>Lines, with the values the payer will actually use</h2>
    <p>Instead of an echo, the payer reads back the real values it will use, including the account it looked up in its own files. The program compares those with the approved record.</p>
    {D["values"]}
    <div class="tiles">
      <div class="tile"><b>0 of 129</b><span>wrong payments on both models. On the strong models there was nothing to catch; they had already looked up the right account.</span></div>
      <div class="tile"><b>52 of 129</b><span>times the weak model got stuck: it could not write the line properly, so the program kept refusing it and nothing got paid.</span></div>
    </div>
    <p class="outcome is-warn"><span class="dot"></span>Safe but awkward. Letting the weak model fill in a short English form instead of a line fixed the stalling: 0 wrong payments and 0 stalls in 129 trials.</p>
  </section>

  <section>
    <p class="eyebrow">Test 5</p>
    <h2>The report afterwards</h2>
    <p>After paying, the tool prints what it actually did. The payer reports that, not what it meant to do, and a program compares the report with the plan.</p>
    {D["report"]}
    <div class="tiles">
      <div class="tile"><b>45 of 45</b><span>tool faults flagged on Sonnet and on Haiku: a transposed digit, a date a day late, another supplier's account. The weak model's report flagged 25 of 27 in the later test.</span></div>
      <div class="tile"><b>after</b><span>the money had moved. This check can only recall a payment, not stop one.</span></div>
    </div>
    <p class="outcome is-good"><span class="dot"></span>Worked, late. The only check that sees a tool doing something other than it was told.</p>
  </section>

  <section>
    <p class="eyebrow">Test 6</p>
    <h2>The window: the tool states what it will do first</h2>
    <p>In a cockpit the pilot sets the new altitude in a little window, and the other pilot checks the window, not their memory. We gave the payment tool a window. It prepares the payment, freezes exactly what it will do under a ticket number, and prints that as the readback itself. A program checks the statement against the record. Only then does the tool get a yes, and it refuses to pay without one.</p>
    {D["window"]}
    <div class="tiles">
      <div class="tile"><b>59 to 0</b><span>of 60 wrong accounts and dates the tool picked that became wrong payments on Haiku: 59 with the old tool, readback or not, and 0 with the window. On the weak model, 32 of 60 fell to 0 of 60.</span></div>
      <div class="tile"><b>14 to 0</b><span>of 129 wrong payments on the weak model: 14 with the echo, 0 with the window, which caught the old account and a fake address.</span></div>
      <div class="tile"><b>52 to 7</b><span>stalls on the weak model, because the tool writes the line and the model only hands it the values.</span></div>
      <div class="tile"><b>0 of 378</b><span>payments made before the program said yes. But the weak model garbled the tool's words 51 times in 129 when passing them on, so the program reads the tool directly.</span></div>
    </div>
    <p class="outcome is-good"><span class="dot"></span>Worked best of all. A tool that lies at the very last moment still gets through, and the report afterwards still catches that: 30 of 30 on Haiku, 25 of 27 on the weak model.</p>
  </section>

  <section>
    <h2>The scorecard</h2>
    <div class="tw"><table>
      <thead><tr><th>How the agents worked</th><th>The sender typed it wrong</th><th>The payer read it wrong (weak model)</th><th>The tool picked the wrong account</th><th>The tool lied at the last moment</th></tr></thead>
      <tbody>
        <tr><td>1. Prose, nothing checks</td><td class="no">15 of 48 paid wrong</td><td class="no">not caught</td><td class="no">not caught</td><td class="no">not caught</td></tr>
        <tr><td>2. Prose, judged by an AI</td><td class="part">8 of 48 paid wrong</td><td class="part">4 of 140 paid wrong</td><td class="no">not caught</td><td class="no">not caught</td></tr>
        <tr><td>3. Lines, echoed back</td><td class="yes">0 of 48 (weak model 1 of 48)</td><td class="no">14 of 129 paid wrong</td><td class="no">not caught</td><td class="no">not caught</td></tr>
        <tr><td>4. Lines, values read back</td><td class="yes">0 of 48</td><td class="part">0 wrong, 52 stalls</td><td class="no">not caught</td><td class="no">not caught</td></tr>
        <tr><td>5. The report afterwards</td><td></td><td></td><td class="part">caught after paying</td><td class="part">caught after paying</td></tr>
        <tr><td>6. The window, plus the report</td><td class="yes">0 of 19</td><td class="yes">0 of 129, 7 stalls</td><td class="yes">0 of 60 paid wrong</td><td class="part">caught after paying</td></tr>
      </tbody>
    </table></div>
    <p class="note">The check before sending, a program comparing the line with the record before it goes, catches the sender's typing on its own, with no round trip. It sits in front of every row from 3 down.</p>
  </section>

  <section>
    <h2>The flow that works</h2>
    {D["works"]}
    <p>Three checks, three places, all done by a program on typed lines. The agents still do the thinking and the talking. The checks are what stop the money.</p>
  </section>

  <section>
    <h2>How to use this</h2>
    <ol>
      <li><b>Write the job as a line.</b> Every fact in its own slot: amount, currency, account, date, reference, approval. The line is what makes everything else possible.</li>
      <li><b>Check the line against the approved record before sending it.</b> A program does this in a millisecond. A wrong digit stops here.</li>
      <li><b>Make the tool prepare first.</b> It states exactly what it will do and freezes it under a ticket number. It reads the job itself, by its id, so no agent retypes it.</li>
      <li><b>Check that statement against the record.</b> If anything differs, send the job again from the record and let the tool prepare again.</li>
      <li><b>Say yes, naming the ticket.</b> The tool pays exactly what it stated, and refuses to pay without the yes.</li>
      <li><b>Check the report afterwards.</b> The tool prints what it did; the program compares that with the plan. A difference means recall the payment.</li>
      <li><b>With a small or cheap model, let the program read the tool directly.</b> Do not have the model carry the tool's statement to the checker; the weak one changed it 51 times out of 129.</li>
    </ol>
    <p>All of it is live here: the checks are <a href="/quickstart">web calls any agent can make</a>, the <a href="/demo">demo</a> walks through one payment with a mistake of your choosing, and the <a href="/spec">spec</a> says exactly what each check compares.</p>
  </section>

  <section>
    <h2>What not to do</h2>
    <ul>
      <li><b>Do not treat "the agent said it back" as the safety net.</b> On strong models it caught almost nothing, because they read well. On the weak model the echo was worse than nothing.</li>
      <li><b>Do not use another AI to judge a prose readback before a payment.</b> It passed jobs addressed to the wrong agent because the numbers matched, and raised alarms over details that did not matter.</li>
      <li><b>Do not let an agent retype or hand-copy what the tool said.</b> Give the tool the job by its id, and let the program read the tool.</li>
      <li><b>Do not skip the report afterwards.</b> It is the only thing that catches a tool that says one thing and does another at the last moment.</li>
      <li><b>Do not switch to lines to save money.</b> They save little. Switch because a program can check them.</li>
      <li><b>Do not call this proof.</b> One made-up company, three strong models and one weak one, one person writing both the traps and the marking, a few hundred dollars of model time. It tells you where to put the checks. A month of real payments with the checks on and off would tell you what they are worth.</li>
    </ul>
  </section>

  <p class="foot">Every study, log and grade is public in the <a href="https://github.com/afieldofdreams/rogerwilco">rogerwilco repository</a>, and <a href="/research">the research pages</a> carry every figure with its interval. Numbers above are from studies 6 and 7; the strong models were Claude Sonnet 5.5, Claude Haiku 5.5 and gpt-5.5, the weak one gpt-5.4-mini.</p>
</main>
<!-- site:footer -->
<!-- /site:footer -->
</body>
</html>
"""


def main() -> int:
    if "—" in HTML:
        sys.exit("no em dashes in prose")
    PAGE.write_text(HTML, encoding="utf-8")
    print("wrote", PAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
