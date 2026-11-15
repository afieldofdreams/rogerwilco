"""The text of the study 10 site page. render(f, fig, misses) returns the whole HTML; every number is fig(f, key)."""
from __future__ import annotations

import html

NAME = {"haiku55": "Claude Haiku 5.5", "gpt54mini": "GPT-5.4 mini", "sonnet55": "Claude Sonnet 5.5", "gpt55": "GPT-5.5"}
SHORT = {"haiku55": "h55", "gpt54mini": "mini", "sonnet55": "s55", "gpt55": "g55"}
PARTNER = {"haiku55": "gpt54mini", "gpt54mini": "haiku55", "sonnet55": "gpt55", "gpt55": "sonnet55"}
JUDGES = ["haiku55", "gpt54mini", "sonnet55", "gpt55"]


def render(f: dict, fig, misses: list[dict]) -> str:
    g = lambda k: fig(f, k)  # noqa: E731

    def cell_rows(fmt: str) -> str:
        out = []
        for j in JUDGES:
            for a in (j, PARTNER[j]):
                p = f"{fmt}_{SHORT[j]}_{SHORT[a]}"
                rel = "itself" if a == j else NAME[a]
                out.append(f"<tr><td>{NAME[j]}</td><td>{rel}</td><td>{g(p + '_miss')}</td><td>{g(p + '_wrong')}</td>"
                           f"<td>{g(p + '_fa')}</td><td>{g(p + '_unp')}</td></tr>")
        return "\n".join(out)

    def code_rows() -> str:
        return "\n".join(f"<tr><td>The code check, <code>check-rb</code></td><td>{NAME[a]}'s lines</td><td>{g('code_' + SHORT[a] + '_miss')}</td>"
                         f"<td>{g('code_' + SHORT[a] + '_unnamed')}</td><td>{g('code_' + SHORT[a] + '_fa')}</td><td></td></tr>"
                         for a in JUDGES)

    def miss_block(m: dict) -> str:
        j = m["job"]
        lead = (f"Job {j['id']}: invoice {html.escape(j['item'])}, approved for {html.escape(j['supplier'])} "
                f"(<code>{j['sup']}</code>). The payer was handed {html.escape(m['planted']['supplier'])} "
                f"(<code>{m['planted']['sup']}</code>) instead. Readback written by {NAME[m['author']]}, "
                f"{'a paragraph' if m['format'] == 'prose' else 'an RB line'}; judged by {NAME[m['judge']]}, which answered "
                f"<code>{html.escape(m['answer'])}</code>.")
        return f"<p>{lead}</p>\n<pre>{html.escape(m['readback'])}</pre>"

    HEAD = ("<thead><tr><th>Judge</th><th>Readbacks written by</th><th>Misses</th><th>Wrong slot</th><th>False alarms</th>"
            "<th>Unparseable</th></tr></thead>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>The scheduler as judge</title>
<meta name="description" content="When the scheduler that checks a payer's readback is a model, not a program, does it notice a wrong value? {f['trials']} judgments by four models from two vendors on {f['readbacks']} readbacks, in prose and as lines, against the protocol's code check. Pre-registered.">
<!-- site:head -->
<!-- /site:head -->
</head>
<body>
<!-- site:header -->
<!-- /site:header -->
<main class="report">
<p class="mast"><span>Study 10</span><span>15 November 2026</span><span>Croxio Ltd</span><span>{g('trials')} judgments on {g('readbacks')} readbacks, four models from two vendors, pre-registered, after a pilot of {g('pilot_trials')}</span></p>
<h1>When the scheduler is a model, does it notice a wrong readback?</h1>
<div class="answer">
<p>Three of the four models did, every time. Claude Haiku 5.5, Claude Sonnet 5.5 and GPT-5.5 passed none of the readbacks that carried one wrong value: {g('strong_miss')}, in prose and on lines alike. GPT-5.4 mini passed {g('all_miss_k')}, and every one was a lookalike supplier: it let {g('mini_supplier_miss')} lookalike payees through, {g('mini_prose_miss')} in prose and {g('mini_line_miss')} on lines, so the typed line did not help it. No judge passed any fault of the other six kinds, a changed amount, account, date, invoice, currency or gross for net: {g('other_miss')}.</p>
<p>The cost of a model as the check showed on the other side. Claude Haiku 5.5 never passed a wrong value, but it stopped {g('h55_prose_fa')} correct readbacks in prose and {g('h55_line_fa')} on lines, most of them naming a date or an approval that was right. In a deployment each of those is a payment held for nothing. Of the same clean readbacks Claude Sonnet 5.5 stopped {g('s55_fa')}, GPT-5.5 {g('g55_fa')} and GPT-5.4 mini {g('mini_fa')}.</p>
<p>The protocol's code check, <code>check-rb</code> on the same lines, passed no wrong value: {g('code_miss')}. It refused {g('code_fa')} correct lines, every one at parsing, because the model that typed the line had left out its version token or added free text after the slots. That is study 9's finding again, and it is why the protocol has the readback composed by code from the message as delivered.</p>
</div>
<dl class="glance">
<dt>The question</dt><dd>In studies 5 to 9 a readback was checked by code, or, in the prose arms of studies 5 and 6, by a model set up as a checker for the study. A team with no code at the scheduler has the scheduler agent itself as the check. Whether that agent notices one wrong value, and how often it stops a correct one, had not been measured on its own.</dd>
<dt>The material</dt><dd>Study 6's fictional company and supplier master: {g('jobs')} approved payments, one from study 6's record, six from its inbox, its decoys and the month-end ground truth, thirteen new invoices on the same master.</dd>
<dt>The faults</dt><dd>Before the payer reads the job, one value is changed: one digit of the amount, two digits of the account transposed, the payment date, two digits of the invoice number transposed, gross for net, the currency, or the supplier swapped for a lookalike. One fault of each kind for each job, {g('faulted_jobs')} faulted jobs, and seven clean readbacks of each job.</dd>
<dt>The readbacks</dt><dd>Written by a payer model, as a paragraph or as an RW1 RB line, and checked in code to carry exactly the values it was given, the planted one included, before any judge saw them.</dd>
<dt>The judges</dt><dd>A scheduler model given the approval record, the handover it sent and the payer's readback, answering on one line: MATCH, or MISMATCH and the detail. Four models: Claude Haiku 5.5 and Claude Sonnet 5.5 as headless Claude Code sessions, GPT-5.4 mini and GPT-5.5 through the API. Each read readbacks it had written itself and readbacks from the same-size model of the other vendor.</dd>
<dt>Graded by</dt><dd>Code. A miss is MATCH on a faulted pair; a wrong slot is MISMATCH naming a detail other than the planted one; a false alarm is MISMATCH on a clean pair; an answer that does not begin with MATCH or MISMATCH is unparseable, counted and never dropped. The baseline is the codec's own <code>check-rb</code> on every line. The protocol, its four amendments and every trial's prompt, answer and grade are in the repository.</dd>
</dl>

<h2>Why we did it</h2>
<p>Study 6 found that strong receivers read their own context without error, and that the work of a readback before an irreversible act is done by whatever checks it. Its prose arm used a model as that check, and the model raised false alarms where code raised none: on 38 of 190 readbacks from gpt-5.4-mini. In study 6's extension the same judge passed 8 jobs addressed to the wrong agent, because the numbers matched. Those judges were checkers set up for the study, shown the record and never the handover, inside whole trials with everything else going on. This study takes the one step out and measures it: a readback that is right or carries exactly one wrong value, and a scheduler model that holds the record and the handover it sent, asked whether they agree.</p>

<h2>What we tested</h2>
<div class="tw"><table><thead><tr><th>Planted fault</th><th>What changes</th><th>Job J01</th></tr></thead><tbody>
<tr><td>amount</td><td>one digit of the whole part</td><td>5400.00 becomes 5406.00</td></tr>
<tr><td>account</td><td>two adjacent digits swapped, sort code kept</td><td>61102938 becomes 61012938</td></tr>
<tr><td>date</td><td>one digit of the day, still a weekday</td><td>2 October becomes 6 October</td></tr>
<tr><td>invoice</td><td>two adjacent digits swapped, reference too</td><td>MD-2026-057 becomes MD-2026-075</td></tr>
<tr><td>gross or net</td><td>swapped, the figure unchanged</td><td>GROSS becomes NET</td></tr>
<tr><td>currency</td><td>pounds and dollars swapped</td><td>GBP becomes USD</td></tr>
<tr><td>supplier</td><td>replaced by its lookalike</td><td>Marlow Design Partners LLP becomes Marlow Design Partners Limited</td></tr>
</tbody></table></div>
<p class="cap">The seven planted faults. One of each for every job, chosen by a seeded rule: never the amount's leading digit; the date moved to another weekday in the same month, on or after the case date; the invoice number's reference changed with it, since the reference is the invoice number; the lookalike replacing the legal name and the short name together. All {g('faulted_jobs')} are listed in the repository.</p>
<p>The fault sits between what the scheduler sent and what the payer read: the scheduler's record and its handover are right, and the payer reads back, faithfully, a handover with one wrong value in it. In prose the handover is study 6's message with the payee account in it and the readback is a paragraph. As lines the handover is study 6's HO with <code>rb=exec</code> and the readback is an RB line, written by the model, without the digest it has no code to compute. The judge sees the approval record as one field a line, the same in both forms, then the handover and the readback. It is told nothing about the study: no base rate, no planted faults, no author.</p>
<p>Every readback was checked in code before any judge saw it. A clean one had to carry every value of the job; a faulted one the planted value, not the value it replaced, and every other value as approved; neither might question or comment on a value. Form was not checked: a line with every value right and its form wrong went to the judge as written, because what a model writes is what the scheduler, model or code, has to read. Each author wrote 140 faulted and 140 clean readbacks in each form, and each readback was judged twice, by its author's model and by the same-size model of the other vendor, so that authors and judges cross on the same readbacks.</p>

<h2>How we ran it</h2>
<ol class="steps">
<li>Wrote the protocol before building: the jobs, the faults, the forms, the grading, four hypotheses and their tests, the sizes and a cost cap. It is <code>research/scheduler-judge/README.md</code>, with every amendment dated under its own heading.</li>
<li>Built the jobs and the briefs from study 6's fixtures, copied into the study folder, with the codec frozen at the commit the run started from. The briefs carry study 6's prose conventions block or the codec's pay legend, word for word, and are within 8% of one length.</li>
<li>Piloted {g('pilot_trials')} trials, GPT-5.5 judging readbacks from itself and from Claude Sonnet 5.5: {g('pilot_caught')} faults caught with the planted detail named and {g('pilot_fa')} false alarms. Every author wrote readbacks in the pilot, {g('pilot_readbacks')} in all, so that each was checked before the main run.</li>
<li>Amended four things before any judgment of the main run: a line without its version token is judged as written, because Claude Haiku 5.5 left it out and the check had been writing those readbacks again; the cost cap counts OpenAI spend, since the Claude sessions run on the account's plan; a provider error is not one of a readback's three attempts; a supplier's name is compared without case or spaces, because GPT-5.4 mini wrote some names as one lowercase run.</li>
<li>Ran {g('readbacks')} readbacks and {g('trials')} judgments with nothing dropped and no provider error, for {g('cost_openai')} of OpenAI credit; the Claude sessions ran on the account's plan, {g('cost_claude')} at list price.</li>
<li>Graded everything in code. Every figure on this page is read from <code>results/summary.json</code> by the script that writes the page, and a test in the app asserts they match.</li>
</ol>

<h2>What happened</h2>
<h3>The judges, in prose and on lines</h3>
<div class="tw"><table>{HEAD}<tbody>
{cell_rows('prose')}
</tbody></table></div>
<p class="cap">Table 1. Prose. Each row is 140 faulted and 140 clean pairs. Misses and wrong slots are over the faulted pairs (a wrong slot is MISMATCH naming another detail, or none); false alarms over the clean ones; unparseable over both. A zero of 140 has a 95% upper bound of {g('ub140')}.</p>
<div class="tw"><table>{HEAD}<tbody>
{cell_rows('line')}
{code_rows()}
</tbody></table></div>
<p class="cap">Table 2. RW1 lines, the same judges and readbacks, and the code check on every line each author wrote. For the code check, a wrong slot is a refusal that does not name the planted detail.</p>
<p class="inwords">In words: across both forms Claude Haiku 5.5 missed {g('h55_miss')}, Claude Sonnet 5.5 {g('s55_miss')} and GPT-5.5 {g('g55_miss')}, a zero with an upper bound of {g('ub560')} each. GPT-5.4 mini missed {g('mini_miss')}, all of them the lookalike supplier, {g('mini_supplier_cell')} supplier faults in each of its four cells: on its own readbacks and on Claude Haiku 5.5's, in prose and on lines alike. The other three judges named the planted detail in all but {g('strong_unnamed')} of the faults they stopped, every one of those Claude Haiku 5.5 naming another detail. On false alarms one judge stood apart: Claude Haiku 5.5 stopped {g('h55_fa')} correct readbacks, against {g('s55_fa')} for Claude Sonnet 5.5, {g('g55_fa')} for GPT-5.5 and {g('mini_fa')} for GPT-5.4 mini.</p>

<h3>The misses</h3>
<p>Every miss was the same fault: the payee replaced by a lookalike, read back faithfully, and passed. These three are verbatim, the readback as the judge saw it and its whole answer.</p>
{chr(10).join(miss_block(m) for m in misses)}
<p>The line carries the supplier as a short name, so on a line the lookalike is <code>sup=northfield-printing</code> against the record's <code>northfield</code>: the same comparison as the names in prose, and the same answer. The record the judge held showed both the legal name and the short name.</p>

<h3>The false alarms</h3>
<p>Claude Haiku 5.5 stopped {g('h55_prose_fa_k')} correct prose readbacks, {g('h55_prose_fa_date')} of them naming the date. The dates were right, and the flags fell on {g('h55_fa_date_days')} of the {g('payment_days')} payment dates in the set, so they do not follow any one date. On lines it stopped {g('h55_line_fa_k')}, {g('h55_line_fa_appr')} of them naming the approval; all {g('h55_line_fa_appr_noecho')} were lines that do not repeat the handover's <code>appr=OK</code>, as {g('h55_line_noecho_passed')} lines it passed do not either. Its answers are one line, so they do not say why.</p>
<p>The OpenAI judges stopped {g('openai_fa_k')} correct readbacks between them, every one naming the supplier, and {g('openai_fa_not_as_given')} of the {g('openai_fa_k')} were readbacks that did not write the supplier's name as it was given: run together as one lowercase word, or in lower case. The readback check counts those as the right name, so the grading counts the judge's stop as a false alarm; a stricter reader might call it fair. GPT-5.4 mini also answered {g('unp_k')} faulted line pairs with the detail alone and no verdict; {g('unp_named_planted')} of them named the planted detail, and all are unparseable under the rule written before the run.</p>

<h3>The code check</h3>
<p>The code check refused every wrong line and named the planted detail in every refusal of a line whose form was right. Its {g('code_fa_form')} false alarms are all one thing, a refusal at parsing: Claude Haiku 5.5 left the version token <code>RW1</code> off {g('h55_no_version')} of its lines, and GPT-5.4 mini put free text after the slots without the <code>//</code> that marks a tail. The same faults made it refuse {g('code_unnamed')} faulted lines without naming the planted detail. On Claude Sonnet 5.5's and GPT-5.5's lines it passed every right one and refused every wrong one.</p>

<h3>The readbacks</h3>
<p>{g('rb_first')} readbacks were accepted at the first attempt and {g('rb_dropped')} were dropped. The {g('rb_later')} written again were six prose readbacks that named the supplier without its legal suffix, which is the part that tells an approved supplier from a lookalike such as Marlow Design Partners Limited, and one line that copied part of its brief into the line. {g('rb_recheck')} more were accepted at the first attempt when the name check was amended to ignore case and spaces.</p>

<h2>The hypotheses</h2>
<p>Registered before the pilot and tested per judge, with nothing pooled across judges. H1: on prose, a model judge misses some planted faults. H2: the typed line reduces misses compared with prose. H3: misses differ between readbacks the judge's own model wrote and readbacks from the other vendor's model. H4: the code check on lines has no miss and no false alarm.</p>
<div class="tw"><table><thead><tr><th></th><th>Claude Haiku 5.5</th><th>GPT-5.4 mini</th><th>Claude Sonnet 5.5</th><th>GPT-5.5</th></tr></thead><tbody>
<tr><td>H1, prose misses</td><td>{g('h1_h55')}, {g('h55_prose_miss')}</td><td>{g('h1_mini')}, {g('mini_prose_miss')}</td><td>{g('h1_s55')}, {g('s55_prose_miss')}</td><td>{g('h1_g55')}, {g('g55_prose_miss')}</td></tr>
<tr><td>H2, line against prose</td><td>{g('h2_h55')}</td><td>{g('h2_mini')}, {g('mini_line_miss_k')} and {g('mini_prose_miss_k')}</td><td>{g('h2_s55')}</td><td>{g('h2_g55')}</td></tr>
<tr><td>H3, own against other</td><td>{g('h3_h55')}, {g('h3_h55_same_k')} and {g('h3_h55_diff_k')}</td><td>{g('h3_mini')}, {g('h3_mini_same_k')} and {g('h3_mini_diff_k')}</td><td>{g('h3_s55')}, {g('h3_s55_same_k')} and {g('h3_s55_diff_k')}</td><td>{g('h3_g55')}, {g('h3_g55_same_k')} and {g('h3_g55_diff_k')}</td></tr>
<tr><td>H4, the code check</td><td colspan="4">{g('h4')}: {g('code_miss')} missed, {g('code_fa')} refused for form</td></tr>
</tbody></table></div>
<p class="cap">Table 3. The four hypotheses. H2 by Fisher's exact test, one-sided: GPT-5.4 mini missed {g('mini_line_miss')} on lines and {g('mini_prose_miss')} in prose, p {g('h2_mini_p')}; on the matched pairs {g('h2_mini_prose_only')} were missed only in prose and {g('h2_mini_line_only')} only on the line. The other three had no prose miss for the line to reduce, so H2 is not shown for them. H3 by Fisher's exact test, two-sided, Holm-adjusted across the judges, over 280 faulted pairs a side; a difference test at these sizes cannot show two rates equal, so H3 has no "fails".</p>

<h2>What it cost</h2>
<p>{g('cost_openai')} of OpenAI credit for the main run and {g('pilot_cost_openai')} for the pilot, costed from the tokens at the published prices; the Claude sessions ran on the account's plan, {g('cost_claude')} at list price. One judgment cost {g('cost_g55_judge')} on GPT-5.5, {g('cost_mini_judge')} on GPT-5.4 mini, and at list price {g('cost_s55_judge')} on Claude Sonnet 5.5 and {g('cost_h55_judge')} on Claude Haiku 5.5. The code check costs nothing per readback and takes no turn.</p>

<h2>What it means</h2>
<p>One wrong value in an otherwise faithful readback is something three of these four models catch as reliably as code, in prose as well as on a line. The failure that did appear is the lookalike payee, the bank-detail fraud the earlier studies were built around: the smallest OpenAI model passed it once in about seven, and the line did not help, because a lookalike short name is no easier to see than a lookalike legal name.</p>
<p>The price of a model as the check is its false alarms, and they are not small for every model: Claude Haiku 5.5 held about one correct payment in six in prose and one in eleven on lines. On this evidence a judge chosen for cost does one or the other: GPT-5.4 mini passed the lookalike, Claude Haiku 5.5 held good payments. The two larger models did neither, on this task.</p>
<p>The task is the easy version: one wrong value, one short message, a fluent readback, and nothing else in the judge's context. A scheduler holding a whole payment run in a long context will do worse, so the zeros here are the best case, not a guarantee. The code check's result does not depend on the context, and its only false alarms came from lines a model typed by hand, which a readback composed by code cannot produce.</p>

<h2>What we decided</h2>
<dl class="decided">
<dt>Nothing in the spec changes; two rules it already has gain evidence.</dt><dd>The study was registered to measure, not to choose between forms, and its results fit the protocol as it stands.</dd>
<dt>Before an irreversible act, the scheduler's check is code.</dt><dd>No model judge caught more than the code check, which passed no wrong value ({g('code_miss')}), and the two smaller judges failed in the two ways that cost: one let the lookalike payee through, the other held good payments.</dd>
<dt>The readback is composed by code from the message as delivered.</dt><dd>Every one of the code check's {g('code_fa_form')} false alarms was a line a model had typed with its form wrong; a readback composed by code could not have drawn them. Rule 1 of the skill already says so, on study 9's evidence; this is the same finding in a judge-only setting.</dd>
</dl>

<h2>The amendments, in short</h2>
<ul>
<li>A line without its version token is judged and checked as written; the stored pilot attempts were checked again in code, no call repeated.</li>
<li>The $25 cost cap counts OpenAI spend, the money the run cost; the Claude sessions run on the account's plan and their list price is reported.</li>
<li>A provider error is not one of a readback's three attempts; none occurred in the run.</li>
<li>A supplier's name is compared without case or spaces; applied to the stored attempts in code once the readbacks were written, before any judgment.</li>
</ul>

<h2>What this does not show</h2>
<ul>
<li>No act and no pipeline: a miss here is a readback passed, not a payment made.</li>
<li>One fault, planted before the payer reads, so a faulted readback carries exactly one wrong value; a payer that misreads on its own, a readback wrong in two places, or one that leaves a value out is not tested.</li>
<li>One payment a judgment, in one short message; a scheduler holding a whole run in a long context is not tested.</li>
<li>Four models, one company, one kind of act.</li>
<li>The Claude sessions carry Claude Code's own context, the OpenAI calls none, so a difference between vendors is not only a difference between models.</li>
<li>The judges answer in one line; why Claude Haiku 5.5 stopped correct dates is not recorded.</li>
</ul>

<h2>Where everything is</h2>
<p>The protocol with its amendments, the jobs and the planted faults, every readback with every attempt, every judgment's prompt, answer and grade, the cost ledger and <code>results/summary.json</code>: <code>research/scheduler-judge</code> in the rogerwilco repository. The page you are reading is written from that JSON by <code>tools/site_page.py</code>, and <code>app/tests/test_research_figures.py</code> fails if any figure here differs from it.</p>
<p class="foot">Study 10 · 15 November 2026 · {g('trials')} judgments on {g('readbacks')} readbacks · Claude Haiku 5.5 and Claude Sonnet 5.5 as headless Claude Code sessions, GPT-5.4 mini and GPT-5.5 through the API harness · pre-registered · a pilot of {g('pilot_trials')} trials · graded in code</p>
</main>
<!-- site:footer -->
<!-- /site:footer -->
</body>
</html>
"""
