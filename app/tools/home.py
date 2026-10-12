#!/usr/bin/env python3
"""Writes app/static/index.html, the home page: the story one test at a time, with its flow diagrams.

  python3 app/tools/home.py       # rewrites the page; then run app/tools/stamp.py

Prose first, then the line. What we were testing, the two ways a job can be said, six tests each with a picture of who
says what to whom and where a planted mistake was or was not caught, the scorecard, the flow that works with its three
messages, how to use it, what not to do. The diagrams are inline SVG laid out from small specs below, so every test's
picture shares one geometry and the colours come from site.css tokens (style attributes take var()). The figures are
the ones on the research pages, studies 6 and 7, both receivers; when a study is re-run, change them here and
regenerate. The three lines are real: the app's tests validate them and check the readback against the hand-over.
"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"

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

# the three messages; the app's tests validate these lines and check the readback against the hand-over
HO = ("RW1 <b>HO</b> scheduler-1 p=pay from=scheduler to=payer item=inv:MD-2026-057 ask=<b>PAY</b> rb=exec sup=marlow amt=<b>5400.00</b> "
      "cur=GBP kind=GROSS acct=<b>40-12-88/61102938</b> paid=<b>20261002</b> ref=MD-2026-057 apref=FD-0929")
RB = ("RW1 <b>RB</b> payer-1 re=scheduler-1 from=payer to=scheduler item=inv:MD-2026-057 ask=PAY p=pay <b>h=a7a82de76607</b> sup=marlow amt=5400.00 "
      "cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929")
DN = ("RW1 <b>DN</b> payer-2 re=scheduler-1 p=pay from=payer to=scheduler item=inv:MD-2026-057 out=OK sup=marlow amt=5400.00 "
      "cur=GBP kind=GROSS acct=40-12-88/61102938 paid=20261002 ref=MD-2026-057 apref=FD-0929")

# ---------------------------------------------------------------- the page
HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>rogerwilco</title>
<meta name="description" content="Aviation learned how to hand an instruction from one person to another so that it cannot be misheard. rogerwilco gives that discipline to AI agents: a job as one typed line, read back and checked by a program before anything happens. The last minute at Tenerife, the five layers that keep flying safe, their twins for agents, and seven studies told one test at a time, with a picture of each flow and the mistakes it caught.">
<!-- site:head -->
<!-- /site:head -->
</head>
<body>
<!-- site:header -->
<!-- /site:header -->
<main class="story">
  <header class="hero">
    <p class="lede">Aviation learned, at great cost, how to hand an instruction from one person to another so that it cannot be misheard. rogerwilco gives that discipline to AI agents, and tests whether it works.</p>
    <div class="exchange" role="group" aria-label="A clearance read back on the radio">
      <div class="rt tower"><span class="who">Tower</span><p>"Speedbird one two three, descend flight level nine zero, QNH one zero one three."</p><span class="tag">fixed words</span></div>
      <div class="rt pilot"><span class="who">Pilot</span><p>"Descend flight level nine zero, QNH one zero one three, Speedbird one two three."</p><span class="tag">read back</span></div>
      <div class="rt tower"><span class="who">Tower</span><p class="hb">listens, and corrects anything that differs. Then the pilot sets 9,000 in the window, and the other pilot checks the window.</p><span class="tag">heard back, then checked</span></div>
    </div>
    <p>Thousands of times a day, a controller says what to do, the pilot says it back, and the controller listens for the mistake. The words are fixed, so each means one thing. What gets set is checked against what was said. It is dull, and it is a large part of why flying is the safest way to travel.</p>
    <p>AI agents now hand each other jobs that cannot be undone: paying invoices, changing the account a supplier is paid into, sending emails to customers. They do it in paragraphs that nothing checks. rogerwilco is built at Crox by Adam Field, who flew the Boeing 737 for an airline before he built software, to give agents the radio's discipline and to find out, test by test, what it catches.</p>
  </header>

  <section>
    <h2>Tenerife, 27 March 1977</h2>
    <p>Two Boeing 747s on a fog-bound runway, and the deadliest accident in aviation. The KLM crew began its take-off on a clearance it had not been given and struck the Pan Am 747 still taxiing on the runway. 583 people died. Here is the last minute on the tower frequency and in the KLM cockpit.</p>
    <div class="radio" role="group" aria-label="The last minute of radio and cockpit recordings before the collision">
      <div class="rx klm"><span class="t">17:05:44</span><span class="who">KLM 4805</span><p>"The KLM four eight zero five is now ready for take-off, and we're waiting for our ATC clearance."</p></div>
      <div class="rx tower"><span class="t">17:05:53</span><span class="who">Tower</span><p>"KLM eight seven zero five, you are cleared to the Papa beacon, climb to and maintain flight level nine zero, right turn after take-off, proceed with heading zero four zero until intercepting the three two five radial from Las Palmas VOR."</p><p class="why">A route clearance: where to fly after take-off. Not a clearance to take off. The callsign is wrong, too.</p></div>
      <div class="rx klm"><span class="t">17:06:09</span><span class="who">KLM 4805</span><p>"Ah, roger sir, we're cleared to the Papa beacon, flight level nine zero, right turn out zero four zero until intercepting the three two five. <mark>We are now at take-off.</mark>"</p><p class="why">A correct readback, then four words that were in nobody's book. The tower heard "at the take-off point". The crew meant "taking off".</p></div>
      <div class="rx klm"><span class="t">17:06:11</span><span class="who">KLM captain</span><p>"We gaan." <i>(We're going.)</i></p><p class="why">The brakes were already off.</p></div>
      <div class="rx tower"><span class="t">17:06:18</span><span class="who">Tower</span><p>"OK." <i>(a pause)</i> "Stand by for take-off, I will call you."</p></div>
      <div class="rx panam"><span class="t">17:06:20</span><span class="who">Pan Am 1736</span><p>"No. And we're still taxiing down the runway, the Clipper one seven three six."</p><p class="why">Both transmitted at once. In the KLM cockpit the two became a squeal lasting almost four seconds. "OK" was heard. The warning was not.</p></div>
      <div class="rx tower"><span class="t">17:06:25</span><span class="who">Tower</span><p>"Papa Alpha one seven three six, report the runway clear."</p></div>
      <div class="rx panam"><span class="t">17:06:29</span><span class="who">Pan Am 1736</span><p>"OK, we'll report when we're clear."</p></div>
      <div class="rx klm"><span class="t">17:06:32</span><span class="who">KLM flight engineer</span><p>"Is hij er niet af dan? Is hij er niet af, die Pan American?" <i>(Is he not clear then? Is he not clear, that Pan American?)</i></p></div>
      <div class="rx klm"><span class="t">17:06:35</span><span class="who">KLM captain</span><p>"Jawel." <i>(Oh, yes.)</i></p><p class="why">The one person who doubted was overruled, and the aircraft kept accelerating.</p></div>
      <div class="rx end"><span class="t">17:06:50</span><span class="who">Runway 30</span><p>The KLM 747 struck the Pan Am 747.</p></div>
    </div>
    <p class="cap">From the cockpit voice recorder and the tower tape as published in the investigation reports; Dutch lines translated; times local.</p>
    <p>Nothing here was a technical failure. Every word was ordinary English, and that was the problem. One phrase meant two things. Two people spoke at once and the warning never arrived. The person who doubted was overruled. Aviation's answer was not a better pilot. It was a protocol, and it changed three things.</p>
    <div class="tiles">
      <div class="tile"><b>one word</b><span>"Take-off" is now said only in the clearance to take off, or to cancel it. Everything else is "departure".</span></div>
      <div class="tile"><b>read back</b><span>A take-off clearance, a runway crossing, an altitude: the pilot must say it back, and the controller must listen.</span></div>
      <div class="tile"><b>the doubt wins</b><span>Crew training was rebuilt so that the most junior voice in the cockpit is heard, and a doubt stops the aircraft.</span></div>
    </div>
  </section>

  <section>
    <h2>Five layers, and their twins for agents</h2>
    <p>The readback is the famous part. It is one layer of five, and the layers that catch the most are the ones that check the machine rather than the person. Each has a twin in the way agents can hand each other a job, and the tests further down say how much each twin caught.</p>
    <div class="layers" role="table" aria-label="The five layers of aviation safety and their twins for agents">
      <div class="layer head" role="row"><span role="columnheader">Layer</span><span role="columnheader">In the cockpit</span><span role="columnheader">Between agents</span></div>
      <div class="layer" role="row"><h3 role="cell"><span class="n">1</span>Fixed words</h3><p role="cell">A closed vocabulary, so a word means one thing and nothing is said in two ways.</p><p role="cell">The job is one typed line, every fact in a labelled slot, so a program can read it like a form.</p></div>
      <div class="layer" role="row"><h3 role="cell"><span class="n">2</span>Read back, listened to</h3><p role="cell">The pilot says the clearance back; the controller listens for the mistake.</p><p role="cell">The payer reads the job back as a line and a program compares it with the record. <b>Caught every typed mistake.</b></p></div>
      <div class="layer" role="row"><h3 role="cell"><span class="n">3</span>Set it, check the window</h3><p role="cell">The new altitude goes in the window; the other pilot checks the window, not their memory.</p><p role="cell">The payment tool states exactly what it will do, and a program checks that before it does it. <b>Caught every tool mistake before the money moved.</b></p></div>
      <div class="layer" role="row"><h3 role="cell"><span class="n">4</span>Watch the radar</h3><p role="cell">The tower sees what the aircraft actually does, so a mistake is seen early.</p><p role="cell">The tool reports what it actually did and a program compares it with the plan. <b>Caught every fault, after the money moved.</b></p></div>
      <div class="layer" role="row"><h3 role="cell"><span class="n">5</span>The aircraft says no</h3><p role="cell">The flight computer will not fly the aircraft into the ground, whatever anyone says.</p><p role="cell">The tool will not pay until the program says yes, whatever any agent says. <b>Never paid early, in 378 tries.</b></p></div>
    </div>
    <p>rogerwilco is those layers written down for agents: three one-line messages, the checks a program runs on them, hosted here for any agent to call, and seven studies that planted mistakes to find out what each layer catches. The rest of this page is those studies, one test at a time. <em>Roger</em> means "I received it"; <em>wilco</em> means "I understood it and I will do it".</p>
  </section>

  <section>
    <h2>What we were testing</h2>
    <p>Three agents and a tool. The boss says what to pay. The scheduler agent writes the job. The payer agent reads it and looks up the bank account. The payment tool moves the money. A mistake can enter at three places, and once the money has moved it cannot be undone.</p>
    {D["places"]}
    <p>The setting was a made-up company with a made-up month of bills, so no real money was ever at risk. We used four AI models from two companies: three strong ones and one weaker, cheaper one. Every log and every grade is in the open.</p>
  </section>

  <section>
    <h2>Two ways to say a job</h2>
    <p>Everything turns on this. A job can be a sentence, or it can be a <b>line</b>: the same facts in fixed slots, each with a label. A person can read both. Only the line can be checked by a program, because a program can find <code>amt=</code> and compare it with the record, and it cannot find "five thousand four hundred" in a sentence reliably.</p>
    <div class="vs">
      <div><span class="lbl">A sentence (prose)</span><p class="said">"Pay invoice MD-2026-057: 5,400.00 pounds, gross, to account 40-12-88 / 61102938, on 2 October, under approval FD-0929. Read back what you will do before you do anything."</p></div>
      <div><span class="lbl">The same job as a line</span><pre class="line">{HO}</pre></div>
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
    <p>Three checks, three places, all done by a program on typed lines. The agents still do the thinking and the talking. The checks are what stop the money. This is rogerwilco: three messages, each one line, said here first in words and then as the line a program checks.</p>
    <div class="loop">
      <div class="step">
        <h2>1. Hand over <span>scheduler to payer</span></h2>
        <p class="says">"Pay invoice MD-2026-057: 5,400.00 pounds, gross, to account 40-12-88 / 61102938, on 2 October, under approval FD-0929. Read back what you will do before you do anything."</p>
        <p class="check"><span class="badge">check 1</span><span>The line is the one above. Before it is sent, a program compares it with the approved record, label by label: <code>check-ho</code>. A wrong digit, date or account stops here, with no round trip.</span></p>
      </div>
      <div class="step">
        <h2>2. Read back <span>the tool's statement, payer to scheduler</span></h2>
        <p class="says">"Paying invoice MD-2026-057, 5,400.00 pounds, gross, to 40-12-88 / 61102938, the account on file for Marlow, on 2 October, under FD-0929."</p>
        <pre class="line">{RB}</pre>
        <p class="check"><span class="badge">check 2</span><span>The values are the ones that will actually be used, the account read from the payer's own master, so an instruction that named the wrong account shows up here. <code>h=</code> is a fingerprint of the message as it arrived, so a digit changed on the way shows up too. Where the payment tool can prepare before it commits, this line is the tool's own statement of what it will run, frozen under a ticket: test 6. If anything differs, the payment waits and the scheduler sends the job again. If it all matches: roger, wilco, and the tool gets its yes.</span></p>
      </div>
      <div class="step">
        <h2>3. Done <span>payer to scheduler</span></h2>
        <p class="says">"Paid 5,400.00 pounds to 40-12-88 / 61102938 on 2 October, reference MD-2026-057, under FD-0929."</p>
        <pre class="line">{DN}</pre>
        <p class="check"><span class="badge">check 3</span><span>The done message carries the values as they were actually used, printed by the tool, not as they were asked for, so a program can compare them with the plan: <code>check-dn</code>. That is the second loop, not just "I understood" but "here is what I did", and in tests 5 and 6 it was the one check that caught a tool doing something other than what it was told.</span></p>
      </div>
    </div>
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
    <h3 class="section-h">Start in two minutes</h3>
    <div class="starts">
      <a class="start-card" href="/quickstart#api"><b>API</b><span>One POST, no key, no sign-up.</span><code>POST /check-rb</code></a>
      <a class="start-card" href="/quickstart#python"><b>Python</b><span>One package, no dependencies.</span><code>pip install rogerwilco</code></a>
      <a class="start-card" href="/quickstart#agent"><b>Your agent</b><span>Add the tools to Claude Code in one line, or give any agent the legend.</span><code>claude mcp add ...</code></a>
      <a class="start-card" href="/demo"><b>The demo</b><span>Watch two agents hand a payment over, step by step, and plant a mistake.</span><code>/demo</code></a>
    </div>
    <p class="hint">Want the words first? <a href="/lines">What a line is</a> explains every message type with one example each, <a href="/profiles">profiles</a> show the same line doing four kinds of work, and the <a href="/spec">spec</a> and the <a href="/skill">skill</a> say exactly what each check compares.</p>
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

  <p class="foot">Every study, log and grade is public in the <a href="https://github.com/afieldofdreams/rogerwilco">rogerwilco repository</a>, and <a href="/research">the research pages</a> tell each of the seven studies with every figure and its interval. Numbers above are from studies 6 and 7; the strong models were Claude Sonnet 5.5, Claude Haiku 5.5 and gpt-5.5, the weak one gpt-5.4-mini.</p>
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
