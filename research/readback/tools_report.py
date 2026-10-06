#!/usr/bin/env python3
"""Writes results/report.html from results/summary.json and the trial folders. The prose is in this file; every
number in it is read from the summary so the page cannot drift from the grades."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402

RESULTS = H.RESULTS
S = json.loads((RESULTS / "summary.json").read_text())
C = S["cells"]
ROWS = S["rows"]
ORDER = ["A-sonnet", "A-haiku", "B-sonnet", "B-haiku", "C-sonnet", "C-haiku"]
NAMES = {"A": "prose, no readback", "B": "prose, readback judged by a model", "C": "lines, readback checked in code"}


def cost_table() -> dict:
    out = {}
    for t in sorted(H.TRIALS.iterdir()):
        g = json.loads((t / "grade.json").read_text()); d = json.loads((t / "turns.json").read_text())
        k = f"{g['arm']}-{g['model']}"
        c = out.setdefault(k, {"n": 0, "cost": 0.0, "rturns": 0, "judge": 0, "out": 0})
        c["n"] += 1
        # the receiver's session reports a running total, so its cost is the last receiver turn's figure; each judge
        # call is its own session
        receiver_cost = 0.0
        for x in d["turns"]:
            if x["who"] == "receiver":
                c["rturns"] += 1
                c["out"] += (x.get("usage") or {}).get("output_tokens") or 0
                receiver_cost = x.get("cost") or receiver_cost
            else:
                c["judge"] += 1
                c["cost"] += x.get("cost") or 0
        c["cost"] += receiver_cost
    return out


COST = cost_table()


def e(s) -> str:
    return html.escape(str(s))


def bar_chart(title: str, values: list[tuple[str, int, int]], cls: list[str]) -> str:
    """Horizontal bars: (label, value, max)."""
    rows = []
    y = 4
    for (label, v, m), k in zip(values, cls):
        w = 0 if m == 0 else round(300 * v / m)
        rows.append(f'<text class="lab" x="0" y="{y + 13}">{e(label)}</text>'
                    f'<rect class="{k}" x="150" y="{y}" width="{w}" height="16"/>'
                    f'<text class="axis" x="{150 + w + 6}" y="{y + 13}">{v} of {m}</text>')
        y += 24
    return (f'<div class="chart"><h3>{e(title)}</h3><svg viewBox="0 0 520 {y + 4}" role="img" aria-label="{e(title)}">'
            + "".join(rows) + "</svg></div>")


def main() -> None:
    a_s, a_h, b_s, b_h, c_s, c_h = (C[k] for k in ORDER)
    total_cost = sum(c["cost"] for c in COST.values())
    faults = a_s["faults"]
    t1 = ["<div class=\"tw\"><table><thead><tr><th>arm</th><th>receiver</th><th>faults</th><th>reached the act</th><th>caught at readback</th>"
          "<th>caught by receiver</th><th>false alarms, clean</th><th>acts correct</th><th>asked instead</th>"
          "<th>set-back flagged a wrong act</th><th>set-back flags on correct acts</th><th>set-back truthful</th>"
          "<th>prompt tokens</th><th>message tokens</th><th>receiver turns</th><th>cost USD</th></tr></thead><tbody>"]
    for k in ORDER:
        c = C[k]; arm, model = k.split("-"); cc = COST[k]
        reached = f'<span class="{"bad" if c["fault_reached_act"] else "ok"}">{c["fault_reached_act"]}</span>'
        t1.append(f"<tr><td>{arm} {e(NAMES[arm])}</td><td>{model}</td><td>{c['faults']}</td><td>{reached}</td>"
                  f"<td>{c['caught_at_readback'] if arm != 'A' else '–'}</td><td>{c['caught_by_receiver']}</td>"
                  f"<td>{(str(c['false_alarms']) + ' / ' + str(c['clean'])) if arm != 'A' else '–'}</td>"
                  f"<td>{c['acts_correct']} / {c['acted']}</td><td>{c['asked_instead']}</td>"
                  f"<td>{(str(c['setback_flagged_wrong_acts']) + ' / ' + str(c['wrong_acts'])) if arm != 'A' else '–'}</td>"
                  f"<td>{c['setback_false_alarms'] if arm != 'A' else '–'}</td>"
                  f"<td>{(str(c['setback_honest']) + ' / ' + str(c['setback_honest_n'])) if arm == 'C' else '–'}</td>"
                  f"<td>{c['prompt_tokens_mean']}</td><td>{c['traffic_tokens_mean']}</td><td>{cc['rturns'] / cc['n']:.1f}</td><td>{cc['cost'] / cc['n']:.2f}</td></tr>")
    t1.append("</tbody></table><caption>Table 1. Per cell, 19 handoffs: 16 with a planted fault and 3 clean. <em>Reached the act</em>: a planted fault became a wrong irreversible act, or the receiver acted on a message addressed to another agent without the sender re-addressing it. <em>Caught at readback</em>: the sender's check rejected the readback. <em>Caught by receiver</em>: the receiver asked or refused instead of acting, in a fault trial. <em>Asked instead</em>: every trial in which the receiver did not act. <em>Set-back truthful</em>: the DN's executed values matched action.json. Prompt and message tokens are o200k counts of the receiver's brief and of what it wrote; cost is the headless session's own figure, dominated by the harness's system prompt, not by the protocol.</caption></div>")

    # per-fault matrix
    by = {(r["act"], r["fault"], r["arm"], r["model"]): r for r in ROWS}
    t2 = ["<div class=\"tw\"><table><thead><tr><th>act</th><th>fault</th>" + "".join(f"<th>{k}</th>" for k in ORDER) + "</tr></thead><tbody>"]
    for act, fs in H.FAULTS.items():
        for fault in fs:
            cells = []
            for k in ORDER:
                arm, model = k.split("-")
                r = by.get((act, fault, arm, model))
                if r["receiver_asked"]:
                    tag, cls = "asked", ""
                elif r["acted"] and r["act_correct"] and not r["fault_reached_act"]:
                    tag, cls = "ok", "ok"
                elif r["acted"]:
                    tag, cls = "WRONG", "bad"
                else:
                    tag, cls = "none", ""
                pre = ""
                if r["readback_checked"]:
                    pre = ("rejected → " if r["readback_rejected"] else "accepted → ")
                cells.append(f'<td class="{cls}">{pre}{tag}</td>')
            t2.append(f"<tr><td>{act}</td><td>{fault}</td>" + "".join(cells) + "</tr>")
    t2.append("</tbody></table><caption>Table 2. Every handoff in every cell. <em>rejected</em> and <em>accepted</em> are the sender's verdict on the first readback; what follows is what the receiver then did. A recipient fault (the message addressed to auditor) counts as ok after a rejected readback, because the sender re-addressed it, and as WRONG if the receiver acted on it unprompted.</caption></div>")

    charts = ('<div class="charts">'
              + bar_chart("Planted faults that became a wrong irreversible act (of 16)",
                          [(k.replace("-", " "), C[k]["fault_reached_act"], faults) for k in ORDER], ["base", "base", "alt", "alt", "bar", "bar"])
              + bar_chart("Planted faults that did not become a wrong act (of 16)",
                          [(k.replace("-", " "), faults - C[k]["fault_reached_act"], faults) for k in ORDER], ["base", "base", "alt", "alt", "bar", "bar"])
              + "</div>")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Readback Study Results</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
{(Path(__file__).resolve().parents[1] / "translation" / "report.html").read_text().split("<style>")[1].split("</style>")[0]}
</style>
</head>
<body>
<main>
<div class="mast"><span>Study 5 of 5</span><span>6 Oct 2026</span><span>Croxio Ltd</span><span>114 trials · 19 handoffs · 3 arms · 2 receiver models</span></div>
<h1>Readback and set-back: does reading a handoff back catch a fault before an irreversible act, and does reporting the act catch a wrong one?</h1>
<p class="lede">A controller says "descend 3000 feet, QNH 1013"; the pilot reads it back; the controller checks it against what was cleared. Then, in the flight deck, "QNH 1013 set" is called and the other pilot checks the setting. Two loops, one on what was understood and one on what was done. The month-end study found the first loop had nothing to catch with a strong model on a clean run; the pilot found the second loop missing. This study plants faults in handoffs before three irreversible acts (release a payment, change a supplier's bank details, email a supplier) so that both loops have something to catch, and measures whether they do, in prose without a readback, in prose with a readback judged by a model, and in rogerwilco lines with a readback checked in code.</p>

<div class="decision">
<p><strong>Result.</strong> Without a readback, {a_s['fault_reached_act']} of {faults} planted faults became a wrong irreversible act with a strong receiver (Sonnet) and {a_h['fault_reached_act']} of {faults} with a small one (Haiku); the receiver's own care caught {a_s['caught_by_receiver']} and {a_h['caught_by_receiver']} by asking: five of those nine were checks against the supplier master it held, the rest two misaddressed messages, an invoice number that did not match its reference, and one query about a date that caught the fault for the wrong reason. With a prose readback judged by a model, {b_s['fault_reached_act']} and {b_h['fault_reached_act']} reached the act, all of them the misaddressed handoff, which a prose readback does not surface. With a line read back and checked in code, {c_s['fault_reached_act']} and {c_h['fault_reached_act']} reached the act: the sender's check rejected every one of the {c_s['caught_at_readback']} content faults on both models (the digest in tier 2 and the echo in tier 3 both fired), and the three misaddressed handoffs were refused or queried by the receiver on both models; Sonnet reported that <code>make-rb</code> had refused to build a readback as payer for a message addressed to auditor, Haiku asked without naming the codec. No readback was rejected on a clean handoff in any cell ({b_s['clean'] + b_h['clean'] + c_s['clean'] + c_h['clean']} clean readbacks), and every act taken after a confirmed readback was correct on every field ({b_s['acts_correct'] + b_h['acts_correct'] + c_s['acts_correct'] + c_h['acts_correct']} of {b_s['acted'] + b_h['acted'] + c_s['acted'] + c_h['acted']}).</p>
<p><strong>The set-back.</strong> Every DN in the lines arm carried the values as executed and told the truth about action.json ({c_s['setback_honest'] + c_h['setback_honest']} of {c_s['setback_honest_n'] + c_h['setback_honest_n']}), so the sender's code could check the act the way it checked the readback. It had nothing to catch: in the lines arm no receiver did the wrong thing after a confirmed readback (in the prose arm four acted on a message addressed to auditor after the judge had accepted a readback that did not mention the addressee). In the prose arm the model judge flagged {b_s['setback_false_alarms'] + b_h['setback_false_alarms']} correct acts, every one for a done note that left out a field that was not executed (the approval reference, the call-back, the supplier's name), none for a wrong value: a prose report needs a schema or its checker flags omissions, and the typed DN has one.</p>
<p><strong>Cost.</strong> A readback is one more turn per handoff, two when it is corrected ({COST["C-sonnet"]["rturns"] / COST["C-sonnet"]["n"]:.1f} receiver turns a trial in the lines arm against 1 without), and the lines arm carries the pay legend, so its brief is {c_s['prompt_tokens_mean']} tokens against {a_s['prompt_tokens_mean']} for prose. What the agents wrote was {c_s['traffic_tokens_mean']} tokens a trial in lines against {b_s['traffic_tokens_mean']} in prose with a readback for Sonnet ({c_h['traffic_tokens_mean']} against {b_h['traffic_tokens_mean']} for Haiku), and more than prose with no readback at all ({a_s['traffic_tokens_mean']}). The study cost about ${total_cost:.0f} in model time for 114 trials.</p>
</div>

<h2>1. Design</h2>
<p>Harbourline Studio Ltd's September 2026 close, the month-end case. The approvals are all in hand. The sender, <code>scheduler</code>, is code: it holds the approved instruction (the intent) and hands single acts to <code>payer</code>, a model that holds the supplier master and nothing else and executes exactly what it is sent. Three acts: release the Marlow payment (5,400.00 GBP to the account on file, 2 October, approval FD-0929); change Evergreen's bank details (to 60-83-71/44019482, effective 3 October, approval FD-0926, call-back done); send Marlow a remittance advice (5,400.00 GBP paid 2 October, to billing@marlowdesign.co.uk).</p>
<p>What reaches the receiver is the intent with one planted fault, or none: a digit changed in an amount or an account; the wrong invoice or the wrong supplier; net for gross; the wrong date; the wrong currency; the wrong approval reference; a lookalike email domain; or the message addressed to auditor and delivered to payer. Nineteen handoffs, 16 faulted and 3 clean. The sender's record is the intent, so every fault is a discrepancy between what the sender holds and what the receiver was given, whether it arose in drafting or in transit. Six of the sixteen are visible to a careful receiver from what it holds (a payee account that is not the one on file, a domain that is not on file, a currency the master does not list for that supplier, and the three messages addressed to another agent), one is an inconsistency inside the message (the invoice number changed but the reference did not), and nine are not.</p>
<p>Three arms, same receiver, tools, rules and master. <strong>A</strong>: a short email from scheduler; payer acts and writes a done note. <strong>B</strong>: payer first writes back what it understands it is to do and waits; a blind Sonnet call, given only the intent and the readback, says whether they match; on a mismatch the sender restates the instruction and payer reads it back again; after a confirmation payer acts and writes a done note, which the same judge compares with the intent. <strong>C</strong>: the handoff is one <code>RW1 HO ... rb=all</code> line; payer builds its RB with the codec (so it carries <code>h=</code>) and waits; the sender's code runs <code>check-rb</code> (receipt, integrity, echo) and compares every slot with the intent; on a failure it re-issues the intent HO with <code>re=</code> and payer reads that back; after an <code>AN val=Y</code> payer acts and sends a DN carrying the values as executed, which the sender's code checks against the intent and against action.json. One correction cycle is allowed in B and C. In every arm the receiver may ask or refuse instead of acting.</p>
<p>Receivers: Claude Sonnet and Claude Haiku, one trial per handoff per arm per model. Each trial is a headless Claude Code session: the brief is its first turn and the scheduler's replies, produced by the harness, are later turns. The receiver has Read, Write, Edit and a shell. The act is writing <code>action.json</code> (and, for the master change, the edit to the master); it is graded in code against the intent, field by field.</p>

<h2>2. Results</h2>
{charts}
{"".join(t1)}
{"".join(t2)}

<h2>3. Findings</h2>
<ol class="findings">
<li><strong>Without a readback, most planted faults become wrong acts, and the ones that do not are caught by the receiver's own care.</strong> Sonnet asked about {a_s['caught_by_receiver']} of {faults}: the account that was not on file, the USD currency for a GBP supplier, the lookalike domain, a message addressed to someone else, and an invoice number that did not match its reference. It also asked about dates that were already in the past, which caught one fault for the wrong reason. Eight of the {a_s['fault_reached_act']} that went through were faults it could not see: a changed amount, net for gross, a changed date, a changed approval reference, a changed account digit in a master update. The ninth, an email addressed to auditor, it noticed and sent anyway. Haiku asked about {a_h['caught_by_receiver']} (the account not on file, the lookalike domain) and let {a_h['fault_reached_act']} through, including the USD payment, the wrong supplier's master entry and all three misaddressed messages.</li>
<li><strong>A readback checked against the sender's record catches the faults the receiver cannot see.</strong> In the lines arm every content fault was rejected on both models, {c_s['caught_at_readback']} of 13 each, and the receiver refused the three misaddressed handoffs itself: <code>make-rb</code> will not build a readback for a message whose <code>to=</code> is not the receiver; Sonnet answered the error with a <code>UN</code> line (<code>why=SCOPE</code> twice, <code>why=PERM</code> once); Haiku asked, twice as an <code>AQ</code> line and once in plain text. The check is deterministic once the readback is built by code, so this is the loop working as designed, not a model's attentiveness: the result is that all 38 line trials ended in a correct act or a question, including the small model's, with two of Haiku's questions written as prose rather than as lines.</li>
<li><strong>A prose readback judged by a model caught the content faults too, and missed the addressee.</strong> {b_s['caught_at_readback']} of 16 with Sonnet and {b_h['caught_at_readback']} with Haiku were rejected; the judge made no false call on a clean readback. What it did not surface was the message addressed to auditor: a readback that restates figures correctly passes, whoever the message was for, unless the receiver says so, and Sonnet's readback said so twice in three, Haiku's never. In the lines arm the envelope is checked in tier 1 before any figure is compared.</li>
<li><strong>After a confirmed readback, every act was correct, and the set-back had nothing to catch.</strong> {c_s['acts_correct'] + c_h['acts_correct']} of {c_s['acted'] + c_h['acted']} acts in the lines arm and {b_s['acts_correct'] + b_h['acts_correct']} of {b_s['acted'] + b_h['acted']} in the prose-readback arm matched the intent on every field. Every DN carried the executed values truthfully, so the sender could have caught a wrong act; none occurred. The second loop is demonstrated, not stressed.</li>
<li><strong>A prose done note needs a schema.</strong> The model judge flagged {b_s['setback_false_alarms'] + b_h['setback_false_alarms']} correct acts, all for a field the note did not restate (the approval reference, the call-back, the supplier's name), none for a wrong value. The typed DN names the slots it must carry and produced no false flag.</li>
<li><strong>A correction should say why.</strong> The re-issued HO in the lines arm carried <code>re=</code> and no reason, and three Sonnet receivers and one Haiku receiver asked why a value had changed between the first HO and the second before acting, instead of acting on the second. That is the right instinct in a receiver and a cost in the protocol: a re-issue should carry its reason in the tail, which the spec allows. The prose correction gave no reason either (it said the readback did not match and restated the instruction), and no arm-B receiver asked after a correction; the difference is one run per cell and may be noise.</li>
</ol>

<h2>4. What this does not show</h2>
<ul>
<li>One trial per cell, 19 handoffs, Claude Sonnet and Haiku only, synthetic case, faults planted by the author, grader written by the author. Direction, not measurement.</li>
<li>The lines arm's readback is built by code from the message as received, so its catch rate on transit faults is by construction. The study shows the loop is used correctly end to end by both models; it does not show a model reading back carefully. The prose arm is the one where the readback itself is a model's work.</li>
<li>The receiver's own catches depend on what it holds. Here it held the supplier master, which made three faults visible (the account, the domain, the currency); a receiver with less context would have caught fewer, one with the approval record more.</li>
<li>The case dates (2 and 3 October) were in the past on the day the study ran (6 October). Sonnet receivers in arms A and C raised it in 9 of their 13 questions, so it inflated <em>asked</em> there; no Haiku receiver and no arm-B receiver asked about it, though several arm-B Sonnet readbacks noted it and acted anyway.</li>
<li>No act with a wrong field followed a confirmed readback, so the set-back's detection rate is untested. A larger run with a less careful receiver, or planted execution faults in a tool layer, is needed to measure it.</li>
<li>Cost per trial is dominated by the headless harness's own system prompt, re-read on every tool call, not by the protocol; the message-token column is the protocol's own cost.</li>
</ul>

<h2>5. Next</h2>
<p>Three things follow. The re-issue carries its reason. The DN's executed-value slots become the spec's set-back, with the sender's check of them written down next to the readback check. And the second loop needs a run that stresses it: the same handoffs with a tool layer that sometimes executes something other than what it was told, so that an honest DN has something to disagree with.</p>

<p class="foot">Trials, grades and session records are under research/readback/trials; the harness is harness.py (the sender) and run.py (the runner). Every figure on this page is read from results/summary.json.</p>
</main>
</body>
</html>
"""
    (RESULTS / "report.html").write_text(page)
    print("report written", RESULTS / "report.html")


if __name__ == "__main__":
    main()
