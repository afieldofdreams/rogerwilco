"""The text of the study 9 site page. render(f, fig) returns the whole HTML; every number is fig(f, key)."""
from __future__ import annotations

MODELS = [("q15", "Qwen 1.5B"), ("q3", "Qwen 3B"), ("l3", "Llama 3.2 3B"), ("q7", "Qwen 7B"), ("q14", "Qwen 14B"), ("h45", "Claude Haiku 4.5"), ("h55", "Claude Haiku 5.5")]
ARMS = [("F", "Free prose"), ("A", "Disciplined prose"), ("L", "Lines, unchecked"), ("R", "Lines checked, readback by the model"), ("C", "Lines checked, readback by code")]


def render(f: dict, fig) -> str:
    g = lambda k: fig(f, k)  # noqa: E731

    def head_row(m: str, name: str) -> str:
        tds = "".join(f"<td>{g(f'b1_{a}_{m}_correct')} ({g(f'b1_{a}_{m}_correct_ci')})<br><span class='small'>wrong act {g(f'b1_{a}_{m}_wrong_act')}</span></td>" for a, _ in ARMS)
        return f"<tr><td>{name}</td>{tds}</tr>"

    def b5_row(m: str, name: str) -> str:
        tds = "".join(f"<td>{g(f'b5_{a}_{m}_complied')}<br><span class='small'>mentioned in a tail {g(f'b5_{a}_{m}_injected')}</span></td>" for a, _ in ARMS)
        return f"<tr><td>{name}</td>{tds}</tr>"

    def valid_row(m: str, name: str) -> str:
        return (f"<tr><td>{name}</td><td>{g(f'h6rate_L_{m}')}</td><td>{g(f'h6rate_R_{m}')}</td><td>{g(f'h6rate_C_{m}')}</td>"
                f"<td>{g(f'b1_L_{m}_correct')}</td><td>{g(f'b1_C_{m}_correct')}</td><td>{g(f'reached_{m}')}</td></tr>")

    def q14_row(block: int, label: str) -> str:
        tds = "".join(f"<td>{g(f'b{block}_{a}_q14_correct')}<br><span class='small'>wrong {g(f'b{block}_{a}_q14_wrong_act')}, asked {g(f'b{block}_{a}_q14_asked')}, held {g(f'b{block}_{a}_q14_held')}</span></td>"
                      for a, _ in ARMS if not (block == 6 and a in ("A", "R")))
        if block == 6:
            tds = tds.replace("</td><td>", "</td><td class='na'>(not run)</td><td>", 1)
            tds = tds.rsplit("</td>", 2)[0] + "</td><td class='na'>(not run)</td>" + tds.rsplit("</td>", 2)[1] + "</td>"
        return f"<tr><td>{label}</td>{tds}</tr>"

    def b6_row(m: str, name: str, a: str) -> str:
        valid = g(f"b6_{a}_{m}_valid") if a != "F" else ""
        return (f"<tr><td>{name}</td><td>{a}</td><td>{g(f'b1_{a}_{m}_correct')}</td><td>{g(f'b6_{a}_{m}_correct')} ({g(f'b6_{a}_{m}_correct_ci')})</td>"
                f"<td>{g(f'b1_{a}_{m}_wrong_act')}</td><td>{g(f'b6_{a}_{m}_wrong_act')}</td><td>{g(f'b6_{a}_{m}_asked')}</td><td>{g(f'b6_{a}_{m}_held')}</td><td>{valid}</td><td>{g(f'b6_{a}_{m}_wall')}</td></tr>")

    def anchor_row(a: str, name: str, m: str) -> str:
        checked = a in ("R", "C")
        return (f"<tr><td>{name}</td><td>{g(f'b1_{a}_{m}_correct')} ({g(f'b1_{a}_{m}_correct_ci')})</td><td>{g(f'b1_{a}_{m}_fields')}</td>"
                f"<td>{g(f'b1_{a}_{m}_asked')}</td><td>{g(f'b1_{a}_{m}_held')}</td><td>{g(f'b1_{a}_{m}_heldvr') if checked else ''}</td>"
                f"<td>{g(f'b1_{a}_{m}_rbform') if checked else ''}</td><td>{g(f'b1_{a}_{m}_fa') if checked else ''}</td>"
                f"<td>{g(f'b1_{a}_{m}_turns')}</td><td>{g(f'b1_{a}_{m}_traffic')}</td><td>{g(f'b1_{a}_{m}_cost')}</td></tr>")

    HEADLINE = ("<thead><tr><th>Model</th>" + "".join(f"<th>{n}</th>" for _, n in ARMS) + "</tr></thead>")
    HEAD_B5 = HEADLINE
    HEAD_VALID = "<thead><tr><th>Model</th><th>Valid lines, L</th><th>Valid lines, R</th><th>Valid lines, C</th><th>Block 1 correct, L</th><th>Block 1 correct, C</th><th>Chains that reached the payer</th></tr></thead>"
    HEAD_Q14 = HEADLINE
    HEAD_B6 = "<thead><tr><th>Model</th><th>Arm</th><th>Block 1 correct</th><th>Block 6 correct (95% interval)</th><th>Block 1 wrong acts</th><th>Block 6 wrong acts</th><th>Block 6 asked</th><th>Block 6 held</th><th>Block 6 valid lines</th><th>Median wall s</th></tr></thead>"
    HEAD_ANCHOR = ("<thead><tr><th>Form</th><th>Correct act (95% interval)</th><th>Every record field at the payer</th><th>Asked</th><th>Held</th><th>Held with every value right</th>"
                   "<th>Readbacks refused for form / readbacks</th><th>False alarms / correct forwards</th><th>Model turns</th><th>Median traffic</th><th>Cost a chain</th></tr></thead>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>The breaking point</title>
<meta name="description" content="Where does a handover relayed through agents break, by form, as the agents get smaller and the pressure rises? {f['chains']} chains on five local models from 1.5 to 14 billion parameters and two Claude anchors, five forms, six blocks, pre-registered.">
<!-- site:head -->
<!-- /site:head -->
</head>
<body>
<!-- site:header -->
<!-- /site:header -->
<main class="report">
<p class="mast"><span>Study 9 of 9</span><span>24 October 2026</span><span>Croxio Ltd</span><span>{g('chains')} chains, {g('chains_local')} on five local models and {g('chains_anchors')} on two Claude anchors, pre-registered, after a speed test and a pilot</span></p>
<h1>Where does a relayed handover break as the agents get smaller, and does the check at the hop hold?</h1>
<div class="answer">
<p>The agents break before the form does. Below about 14 billion parameters no form of handover gave throughput: Qwen 1.5B and Qwen 3B asked at the first hop in every arm, Llama 3.2 3B and Qwen 7B reached a correct act in at most {g('b1_F_l3_correct')} clean chains in any arm, and what failed was the relay acting on another message in its inbox. The run made {g('wrong_acts_total')} wrong acts in {g('chains')} chains, every one a payment, bank change or remittance for another item the relay had in front of it, and not one of them the account an injected email asked for: {g('complied_total')} of {g('chains_b5')} injection chains complied, in any form, on any model. The two checked arms made {g('wrong_acts_checked')} wrong acts in {g('chains_checked')} chains, because <code>check-ho</code> refuses a forwarded line for a different item at the hop; on the four smaller models they also made no correct acts, because the relay could not write the line it was asked to forward.</p>
<p>Qwen 14B is the first local model in the band. In the clean block its free prose ended in a correct act in {g('b1_F_q14_correct')} chains with {g('b1_F_q14_wrong_act')} wrong act, and its checked line with the readback composed by code in {g('b1_C_q14_correct')} with {g('b1_C_q14_wrong_act')}; against the confusers, prose {g('b3_F_q14_correct')} correct and {g('b3_F_q14_wrong_act')} wrong, the checked line {g('b3_C_q14_correct')} correct and {g('b3_C_q14_wrong_act')} wrong. Its unchecked line was the worst form on it, {g('b1_L_q14_correct')} correct and {g('b1_L_q14_wrong_act')} wrong in the clean block with every line parsing: a valid line for the wrong item. Routing one message per call with a short brief removed the selection errors (0 wrong acts in 18 chains across three arms) and lifted the 7B's unchecked line to {g('b6_L_q7_correct')}, but it made the 14B's checked forward harder, {g('b6_C_q14_correct')} against {g('b1_C_q14_correct')}.</p>
<p>Both anchors were in the band in every form but one. On Claude Haiku 5.5 the readback the model composed itself, with no tool to hand, was refused for form in {g('R_rbform_h55')} readbacks ({g('R_rbparse_h55')} written without the <code>RW1</code> token, {g('R_rbomit_h55')} omitting an echo on the re-issue) and {g('R_heldvr_h55')} of its chains were held with every value right; the readback composed by code was refused for form {g('C_rbform_h55')} times and held {g('b1_C_h55_held')} chains in the clean block. In study 8 the same model ran <code>make-rb</code> as a tool and this never happened. A model-composed readback without the tool is fragile even on a strong model, which is the case for composing it in code.</p>
</div>
<dl class="glance">
<dt>The question</dt><dd>Study 8 found that on Haiku 5.5 and Haiku 4.5 no relay changed a value in 792 chains. A protocol whose checks never fire is either unnecessary or untested at the edge where it matters, and the edge is a mixed fleet: relays that are the smallest and cheapest models a team can run, under length pressure, in a context that is not clean. This study goes there, with models down to 1.5 billion parameters run locally, and the two Claude anchors through the same runner so the sizes compare.</dd>
<dt>The material</dt><dd>Study 8's company, acts, record, master and inboxes, copied: release a payment, change a supplier's bank details, send a remittance advice. The chain is a scheduler that is code, a coordinator that adds the deadline and priority, a desk that confirms the approval against its log, then the payer. Every agent is one text-only chat with no tools; its brief is the system prompt, its inbox and context file the first turn, its reply the message. The payer replies with a fixed act block the harness executes once against the master.</dd>
<dt>Compared</dt><dd>Five forms: free prose; prose under the seven conventions; RW1 lines validated for syntax only; lines read back at every hop by the model, with the forward checked against the handover received; lines read back at every hop by code, built with <code>make-rb</code> from the message as delivered, the relay confirming or disputing.</dd>
<dt>The axes</dt><dd>Six blocks. The clean baseline with two other live handovers in every relay's inbox; brevity pressure; a decoy, an adjacent run, a near approval reference or a log that covers the supplier but not the item; a sweep to five relays; an injected email from a lookalike supplier domain giving a new account; and, added after the freeze, the routed message: one message per call with a short brief, as a small model is deployed.</dd>
<dt>Models</dt><dd>Qwen2.5 1.5B, 3B, 7B and 14B and Llama 3.2 3B, Q4_K_M on four CPU cores through llama.cpp at temperature 0; Claude Haiku 4.5 and Claude Haiku 5.5 headless through the same text-only runner at provider defaults. Every agent in a chain runs on the same model. No judge.</dd>
<dt>Graded by</dt><dd>Code: the act as executed against the record; the record's fields in every delivered message, by parse for a line and by normalised match for prose; whether the forwarded line parsed; whether the planted account went anywhere; every refusal and what it named. Every proportion carries its exact 95% interval. A blind second reading of {g('val_n')} chains agreed with the grader on {g('val_act')} acts, {g('val_fields')} on every field at the payer and {g('val_drift')} on drift.</dd>
</dl>

<h2>Why we did it</h2>
<p>Study 8 was a null on the fault it was built to find: current Claude models, even the small one, carry an instruction's facts intact across a chain, and the line's claim on a chain was the envelope, the size and a check that refused nothing. The question this left was where the form matters. A team that runs a mixed fleet puts its smallest models at the relays, and a 1.5B model that cannot call a tool fails for reasons that have nothing to do with the message's form; so every agent here is a plain chat, the harness is the tool, and the model's ability to write a line is itself measured. Five axes of pressure were registered: size, brevity, confusers, length and an injected instruction, each with the five forms, and a contingency table said in advance what each result would change in the protocol.</p>

<h2>What we tested</h2>
<div class="tw"><table><thead><tr><th>Arm</th><th>The message</th><th>The relay's readback</th><th>The check at the hop</th></tr></thead><tbody>
<tr><td>F, free prose</td><td>plain English, no instruction about shape</td><td>none</td><td>none</td></tr>
<tr><td>A, disciplined prose</td><td>plain English under the seven conventions</td><td>none</td><td>none</td></tr>
<tr><td>L, lines</td><td>RW1 lines, pay profile; the relay writes the line it forwards</td><td>none</td><td>syntax only; a line that does not parse is delivered as written</td></tr>
<tr><td>R, lines checked, readback by the model</td><td>as L</td><td>the relay writes its own RB line</td><td><code>check-rb</code> on the readback, <code>check-ho</code> on the forward against the HO received plus the role's addition; one re-issue, then held</td></tr>
<tr><td>C, lines checked, readback by code</td><td>as L</td><td>the harness builds the RB with <code>make-rb</code> from the message as delivered; the relay confirms or names what is wrong</td><td><code>check-ho</code> on the forward as in R; the readback cannot fail on the digest or the form</td></tr>
</tbody></table></div>
<p class="cap">The five arms. R is what held Haiku 4.5 in study 8; C is study 7's amendment, the readback composed by code, brought to the relay. If a small model cannot write a valid line at all, L, R and C all stall at that point, which is a finding about the floor of the form.</p>
<p>Block 1 is the baseline: a clean record and two other live handovers in every relay's inbox, three acts, two clean contexts, every arm. Block 2 adds brevity pressure to the relay's brief. Block 3 is study 8's confusers, four per act. Block 4 is the sweep, one, two, three and five relays, prose against the checked line. Block 5 plants, two messages before the live handover in one relay's inbox, an email from a lookalike supplier domain saying the payee account has changed; the correct relay forwards the record's values and may mention the email. Block 6, registered after the freeze and before any of its chains ran, delivers the live handover alone with a short brief in F, L and C, to ask how much of the small models' failure is the inbox and the long brief rather than the form.</p>

<h2>How we ran it</h2>
<ol class="steps">
<li>Wrote the protocol before building: the text-only runner, the five arms, the five blocks, the measures, eight hypotheses and their tests, the sizing by a speed test, the pilot gates, the exclusion rule and a contingency table. It is <code>research/breaking/README.md</code>, with every amendment under its own dated heading.</li>
<li>Built the harness from study 8's with the codec and the pay profile frozen into the study folder, measured the speed of each local model, and piloted {g('pilot_chains')} chains (free prose and the code-readback arm, one payment, every model, {g('pilot_cost')} on the anchors). Gate 3, the smallest model producing one valid line, was not met: Qwen 1.5B attempted no line. As registered it ran anyway.</li>
<li>Froze the tools, the data and the protocol at one commit and ran the design: the anchors at three repeats, the local models one chain at a time, baseline and injection blocks first on every model, kept alive by hand because the container is reclaimed when idle. Qwen 14B was added after the freeze, one size up from the 7B, so the size axis reaches the point where the local models stop breaking.</li>
<li>Cut the remaining blocks on the four models below the band after their baseline, since brevity, confusers and length on relays that do not carry the baseline would have been fifty-five hours of CPU for cells already at zero; ran the confusers on the 14B; registered and ran block 6 on the three models that had reached the payer.</li>
<li>Graded everything in code: {g('chains')} chains, {g('harness_faults')} harness faults (four chains of one launch that hit a thread-unsafe import in the harness, named in the protocol, counted as not done), {g('cost_total')} of anchor time and {g('wall_h_local')} hours of the box's clock on the local models. Then a blind second reading of {g('val_n')} chains, drawn by seed, from the chain files alone: agreement {g('val_act')} on the act, {g('val_fields')} on every field at the payer, {g('val_drift')} on drift. Every figure on this page is read from <code>results/summary.json</code> by the script that writes the page, and a test in the app asserts they match.</li>
</ol>

<h2>What happened</h2>
<h3>The headline: block 1, correct acts and wrong acts, model by arm</h3>
<div class="tw"><table>{HEADLINE}<tbody>
{''.join(head_row(m, n) for m, n in MODELS)}
</tbody></table></div>
<p class="cap">Table 1. Block 1, the clean baseline, two relays: {g('b1_F_q15_n')} chains per cell on the local models, {g('b1_F_h55_n')} on the anchors. A correct act matches the record on every field; a wrong act is a chain that acted and the act differs from the record. The rest of each cell is chains that asked, were held by a check, or stalled.</p>
<p class="inwords">In words: the two smallest models never acted. Qwen 1.5B asked at the first hop in {g('b1_F_q15_asked')} free-prose chains and {g('b1_C_q15_asked')} code-readback chains, and was held at its own readback in {g('b1_R_q15_held')} in R; Qwen 3B the same, {g('b1_F_q3_asked')}, {g('b1_C_q3_asked')} and {g('b1_R_q3_held')}. Llama 3B acted, and wrongly as often as rightly: {g('b1_F_l3_correct')} correct and {g('b1_F_l3_wrong_act')} wrong in free prose, {g('b1_L_l3_correct')} and {g('b1_L_l3_wrong_act')} with the unchecked line, {g('b1_C_l3_correct')} and {g('b1_C_l3_wrong_act')} with the checked one, held at the forward in {g('b1_C_l3_held')}. Qwen 7B made {g('b1_F_q7_wrong_act')} wrong acts in each unchecked arm and no correct one, and in C was held in {g('b1_C_q7_held')}, its forwarded line dropping a slot the check named. Qwen 14B: {g('b1_F_q14_correct')} ({g('b1_F_q14_correct_ci')}) in free prose with {g('b1_F_q14_wrong_act')} wrong, {g('b1_C_q14_correct')} with {g('b1_C_q14_wrong_act')} wrong in C, and {g('b1_L_q14_correct')} with {g('b1_L_q14_wrong_act')} wrong on the unchecked line. The anchors: Haiku 4.5 {g('b1_F_h45_correct')}, {g('b1_A_h45_correct')}, {g('b1_L_h45_correct')}, {g('b1_R_h45_correct')} and {g('b1_C_h45_correct')}; Haiku 5.5 {g('b1_F_h55_correct')}, {g('b1_A_h55_correct')}, {g('b1_L_h55_correct')}, {g('b1_R_h55_correct')} and {g('b1_C_h55_correct')}, the R cell held for form as below. No anchor made a wrong act in {g('chains_anchors')} chains.</p>

<h3>Block 5, the injected account</h3>
<div class="tw"><table>{HEAD_B5}<tbody>
{''.join(b5_row(m, n) for m, n in MODELS)}
</tbody></table></div>
<p class="cap">Table 2. Block 5: the payer executed with the planted account ("complied"), and the chains in which the planted account or the lookalike address appeared in a message delivered past the relay that received the email. Every such appearance was in the tail of a line whose slots were the record's: a relay warning the next hop. {g('injected_slot_total')} slots of any line in the run carried the planted value.</p>
<p class="inwords">In words: H1, the primary hypothesis, cannot be tested as registered, because complied is {g('complied_total')} everywhere (Fisher's p {g('h1_h55_p')} on every model). No relay on any model, in any form, forwarded the planted account as the record's, and no payer paid it. H2 holds on slots: <code>check-ho</code> had nothing to refuse. The grader's count of the value "forwarded" is {g('injected_tail_total')} chains, {g('h2tail_R_h55')} in R and {g('h2tail_C_h55')} in C on Haiku 5.5 among them, and in each the line's <code>acct=</code> or <code>addr=</code> was right and the planted value sat in the tail, for example "Evergreen email of 2026-10-02 quotes 20-71-44/58213907, not the acct on this HO; payer to verify before executing". The injection axis is a bound: these models do not comply with this instruction in this voice.</p>

<h3>The floor: valid lines against correct acts</h3>
<div class="tw"><table>{HEAD_VALID}<tbody>
{''.join(valid_row(m, n) for m, n in MODELS)}
</tbody></table></div>
<p class="cap">Table 3. The valid-line rate (H6): of every line a relay replied with as its forward, over every block the model ran, the proportion that parses as an RW1 handover under the frozen codec, with its interval; beside it the clean block's correct acts on the unchecked and the checked line, and how many of the model's chains delivered anything to the payer at all. A model under 80% is below the form's floor.</p>
<p class="inwords">In words: the valid-line rate does not predict the act. Qwen 1.5B attempted no line in {g('chains_q15')} chains and reached the payer in {g('reached_q15')}. Qwen 3B's lines parsed in {g('h6rate_L_q3')} and it executed nothing, because every chain ended with a question or a hold before the desk. Qwen 14B's lines parsed in {g('h6rate_L_q14')} and its unchecked line ended in a correct act in {g('b1_L_q14_correct')} clean chains, because the lines that parsed were lines for another item in the inbox. Below the floor are Llama 3B ({g('h6rate_L_l3')} in L, {g('h6rate_C_l3')} in C) and Qwen 7B ({g('h6rate_L_q7')} and {g('h6rate_C_q7')}); their lines that failed to parse in L were delivered as written and read by the payer as prose. Both anchors parsed everywhere: Haiku 5.5 {g('h6rate_C_h55')} in C.</p>

<h3>Qwen 14B, the first local cell in the band</h3>
<div class="tw"><table>{HEAD_Q14}<tbody>
{q14_row(1, 'Block 1, baseline')}
{q14_row(3, 'Block 3, confusers')}
{q14_row(5, 'Block 5, injection')}
{q14_row(6, 'Block 6, routed')}
</tbody></table></div>
<p class="cap">Table 4. Qwen 14B by block and arm: correct acts, then wrong acts, chains that asked and chains held. Blocks 1, 5 and 6 are 6 chains per cell, block 3 is 12; block 6 ran F, L and C only.</p>
<p class="inwords">In words: the 14B is where the checked line starts to pay. In the clean block prose and the code-readback line are level, {g('b1_F_q14_correct')} against {g('b1_C_q14_correct')}, and differ on the wrong act, {g('b1_F_q14_wrong_act')} against {g('b1_C_q14_wrong_act')}; the sixth C chain was the payer naming the supplier by its short name, which the bank-change executor's exact-name rule refused, not a relay fault. Against the confusers prose made {g('b3_F_q14_correct')} correct acts and {g('b3_F_q14_wrong_act')} wrong ones, {g('b3_F_q14_wrong_values')} of them another item and {g('b3_F_q14_uncovered')} the record's values past a log that did not cover the item; the checked line made {g('b3_C_q14_correct')} and {g('b3_C_q14_wrong_act')}, ended in the desk's ask where that was the expected outcome in {g('b3_C_q14_asked')}, and was held in {g('b3_C_q14_held')}. The check caught {g('b3_C_q14_caught')} forwarded lines in that block, the coordinator's priority or deadline taken from the wrong run or a dropped slot, and refused {g('b3_C_q14_fa')} forwards with every value right. The model-composed readback was held in every chain on this model, {g('b1_R_q14_held')}, {g('b3_R_q14_held')} and {g('b5_R_q14_held')}, because the 14B wrote its RB without the version token and could not be talked out of it.</p>

<h3>Block 6, the routed message</h3>
<div class="tw"><table>{HEAD_B6}<tbody>
{''.join(b6_row(m, n, a) for m, n in MODELS[2:5] for a in ('F', 'L', 'C'))}
</tbody></table></div>
<p class="cap">Table 5. Block 6 against block 1, the same three models, F, L and C: one message per call, a short brief under 700 tokens, and in the line arms a legend whose example line is in the live order. Six chains per cell in both blocks.</p>
<p class="inwords">In words: routing is most of what the small models were missing, and it is not the form. Llama 3B's prose rose from {g('b1_F_l3_correct')} to {g('b6_F_l3_correct')} correct, its checked line from {g('b1_C_l3_correct')} to {g('b6_C_l3_correct')} with {g('b6_C_l3_wrong_act')} wrong, and its unchecked line to {g('b6_L_l3_correct')} with {g('b6_L_l3_wrong_act')} wrong acts: in three of the four the payer wrote a value from the legend's example line, the Ashdown address or the 640.00, into its act, from a line the desk had stripped of slots; in the fourth it wrote back the old account. Qwen 7B became a questioner, asking at the first hop in {g('b6_F_q7_asked')} prose chains about which run the item belongs to and in {g('b6_C_q7_asked')} checked chains after its forward was refused; its unchecked line reached {g('b6_L_q7_correct')} correct with {g('b6_L_q7_valid')} forwarded lines parsing, the payer reading broken lines as prose. Qwen 14B's prose held at {g('b6_F_q14_correct')}, its unchecked line rose from {g('b1_L_q14_correct')} to {g('b6_L_q14_correct')} with {g('b6_L_q14_wrong_act')} wrong, and its checked line fell to {g('b6_C_q14_correct')}: {g('b6_C_q14_held')} held, two at the coordinator whose line dropped <code>rb=</code> and took the priority from the wrong run under the short brief, one at the payer disputing a readback that carried exactly what the handover carried. Routing removed the selection errors on the 14B and gave the 7B's unchecked line its first correct acts; it did not make the checked forward easier to write.</p>

<h3>The anchors, and the readback the model wrote itself</h3>
<div class="tw"><table>{HEAD_ANCHOR}<tbody>
{''.join(anchor_row(a, n, 'h55') for a, n in ARMS)}
</tbody></table></div>
<p class="cap">Table 6. Block 1 on Claude Haiku 5.5, {g('b1_F_h55_n')} chains per form. "Held with every value right" counts a chain held at a readback whose last refusal named no value mismatch: the RB did not parse or omitted an echo. Readbacks refused for form are those refusals over every readback checked in the cell. Cost is what the headless sessions cost.</p>
<div class="tw"><table>{HEAD_ANCHOR}<tbody>
{''.join(anchor_row(a, n, 'h45') for a, n in ARMS)}
</tbody></table></div>
<p class="cap">Table 7. Block 1 on Claude Haiku 4.5, the same columns.</p>
<p class="inwords">In words: both anchors carried the handover in every form but one, and the one is the readback written by the model with no tool to hand. In arm R the relay writes its own RB line. Haiku 5.5 wrote it without the <code>RW1</code> version token in {g('R_parsechains_h55')} of its R chains at least once, which the codec refuses as a parse failure; the handover was re-issued with the reason, and on the re-issue the model mostly wrote a line that parsed but omitted the echo of <code>pri</code>, which the echo tier refuses; the chain was then held with every value right. Over every block, {g('R_rbform_h55')} of its readbacks were refused for form ({g('R_rbparse_h55')} parse failures, {g('R_rbomit_h55')} omitted echoes) and {g('R_rbvalue_h55')} for a value; {g('R_heldvr_h55')} of its R chains were held with every value right, where the grader's own stall count, which reads the refusal's kind, says {g('R_stall_h55')}, because it calls an omitted echo a value failure. Haiku 4.5 did the same at a tenth the rate: {g('R_rbform_h45')} readbacks refused for form, {g('R_heldvr_h45')} chains held. The code-composed readback cannot fail this way: C on Haiku 5.5 had {g('C_rbform_h55')} readbacks refused for form, {g('C_rbfa_h55')} disputed with every value right, {g('C_fa_h55')} forward refused with every value right, and {g('C_caught_h55')} forwards caught, three a decoy's approval reference and one a priority from the wrong run, each right on the re-issue; on Haiku 4.5, {g('C_rbfa_h45')} readback disputed wrongly and {g('C_fa_h45')} forwards. H8 separates C from R on Haiku 5.5, {g('b1_C_h55_correct')} against {g('b1_R_h55_correct')} (p {g('h8_h55_p')}), in the direction the registration did not expect, and does not separate them on Haiku 4.5, {g('b1_C_h45_correct')} against {g('b1_R_h45_correct')} (p {g('h8_h45_p')}). In study 8 the same two models ran <code>make-rb</code> as a tool, and no readback on Haiku 5.5 was refused with every value right. The prose arms' shortfalls on the anchors were questions, as in study 8, not wrong values.</p>

<h2>The hypotheses</h2>
<div class="tw"><table><thead><tr><th>Registered</th><th>Verdict</th></tr></thead><tbody>
<tr><td>H1 (primary): in block 5, fewer chains end with the injected value executed in C than in F</td><td>cannot be tested as registered: complied is {g('complied_total')} in every cell; p {g('h1_h55_p')} on every model. The injection axis is a bound.</td></tr>
<tr><td>H2: <code>check-ho</code> refuses every forwarded line carrying the injected value, in R and in C</td><td>holds on slots on every model ({g('injected_slot_total')} lines carried the value in a slot); the test's two "misses" on Haiku 5.5 are mentions in the tail of a line whose slots were right.</td></tr>
<tr><td>H3: in block 1 the correct-act proportion in F falls with model size; the smallest model at 90% or better is named per arm</td><td>falls from {g('b1_F_h45_correct')} and {g('b1_F_h55_correct')} on the anchors to {g('b1_F_q14_correct')}, {g('b1_F_q7_correct')}, {g('b1_F_l3_correct')}, {g('b1_F_q3_correct')} and {g('b1_F_q15_correct')}. Smallest at 90%: F {g('h3_floor_F')}, A {g('h3_floor_A')}, L {g('h3_floor_L')}, R {g('h3_floor_R')}, C {g('h3_floor_C')}; no local model in any arm.</td></tr>
<tr><td>H4: on every model, C is held less often than R at the readback</td><td>holds everywhere R ran: Haiku 5.5 {g('b1_C_h55_stall')} against {g('R_stall_h55')} over all blocks as graded (p {g('h4_h55_p')}), {g('R_heldvr_h55')} with form failures counted (p {g('h4form_h55_p')}); Haiku 4.5 p {g('h4_h45_p')} as graded and {g('h4form_h45_p')} with form; p under 0.001 on each local model, where R was held in nearly every chain and C in almost none.</td></tr>
<tr><td>H5: in block 2, prose loses more fields at the payer than lines, on the local models</td><td>could not be tested: block 2 ran on Qwen 1.5B ({g('b2_L_q15_fields')} against {g('b2_F_q15_fields')}) and on 13 chains of Qwen 3B before the cut. On the anchors, where it was not registered: every field at the payer in L {g('b2_L_h45_fields')} against F {g('b2_F_h45_fields')} on Haiku 4.5, {g('b2_L_h55_fields')} against {g('b2_F_h55_fields')} on Haiku 5.5.</td></tr>
<tr><td>H6: valid-line rate per arm; under 80% is below the form's floor</td><td>Llama 3B {g('h6_L_l3')} (L {g('h6rate_L_l3')}, C {g('h6rate_C_l3')}); Qwen 7B {g('h6_L_q7')} (L {g('h6rate_L_q7')}, C {g('h6rate_C_q7')}); Qwen 1.5B attempted no line; Qwen 3B, Qwen 14B and both anchors at or above it.</td></tr>
<tr><td>H7: in block 4, F's correct-act proportion falls with K on the local models and C's does not</td><td>ran on Qwen 1.5B, where every cell is 0 of 3, and on the anchors: on Haiku 5.5 F falls at five relays ({g('b4_F_h55_k1_correct')}, {g('b4_F_h55_k2_correct')}, {g('b4_F_h55_k3_correct')}, {g('b4_F_h55_k5_correct')}) and C does not over the chains that ran ({g('b4_C_h55_k1_correct_run')}, {g('b4_C_h55_k2_correct_run')}, {g('b4_C_h55_k3_correct_run')}, {g('b4_C_h55_k5_correct_run')}, four harness faults aside); on Haiku 4.5 neither falls (F {g('b4_F_h45_k1_correct')}, {g('b4_F_h45_k2_correct')}, {g('b4_F_h45_k3_correct')}, {g('b4_F_h45_k5_correct')}; C {g('b4_C_h45_k5_correct')} at five).</td></tr>
<tr><td>H8 (secondary): on the anchors, C not separable from R on Haiku 5.5, C beats R on Haiku 4.5</td><td>reversed on both: Haiku 5.5 {g('b1_C_h55_correct')} against {g('b1_R_h55_correct')}, p {g('h8_h55_p')}; Haiku 4.5 {g('b1_C_h45_correct')} against {g('b1_R_h45_correct')}, p {g('h8_h45_p')}.</td></tr>
<tr><td>H9 (block 6, registered after the freeze): each model reaches a correct act in more chains than in block 1 in every arm, and C stays at zero wrong acts where any occur</td><td>holds in five of nine cells: Llama 3B rose in F, L and C and its wrong acts order as registered (C {g('b6_C_l3_wrong_act')}, F {g('b6_F_l3_wrong_act')}, L {g('b6_L_l3_wrong_act')}); Qwen 7B rose in L only; Qwen 14B rose in L, held in F and fell in C ({g('b6_C_q14_correct')} against {g('b1_C_q14_correct')}); no wrong act on the 7B or the 14B.</td></tr>
</tbody></table></div>
<p class="cap">Table 8. The nine hypotheses, tested per model with nothing pooled across models: Fisher's exact at alpha 0.05, one-sided where registered so, Clopper-Pearson intervals throughout.</p>

<h2>What it cost</h2>
<p>A clean two-relay chain on four CPU cores: Qwen 1.5B {g('b1_F_q15_wall')} s in free prose and {g('b1_C_q15_wall')} s with the code readback; Qwen 3B {g('b1_F_q3_wall')} and {g('b1_C_q3_wall')}; Llama 3B {g('b1_F_l3_wall')} and {g('b1_C_l3_wall')}; Qwen 7B {g('b1_F_q7_wall')} and {g('b1_C_q7_wall')}; Qwen 14B {g('b1_F_q14_wall')} and {g('b1_C_q14_wall')}, so a checked chain on the 14B is nineteen minutes, and its {g('chains_q14')} chains took {g('wall_h_q14')} hours of the box's clock. On the anchors through the headless runner: Haiku 5.5 free prose {g('b1_F_h55_turns')} model turns, {g('b1_F_h55_traffic')} tokens of traffic and {g('b1_F_h55_cost')} a chain; the code readback {g('b1_C_h55_turns')} turns, {g('b1_C_h55_traffic')} tokens, {g('b1_C_h55_cost')}; the model's own readback {g('b1_R_h55_cost')} for a chain that was usually held. Haiku 4.5 cost {g('b1_F_h45_cost')}, {g('b1_C_h45_cost')} and {g('b1_R_h45_cost')}, and {g('cost_h45')} for its {g('chains_h45')} chains against {g('cost_h55')} for Haiku 5.5's. At five relays on Haiku 5.5 the checked line's traffic was {g('b4_C_h55_k5_traffic')} tokens against free prose's {g('b4_F_h55_k5_traffic')}, while the prose message delivered to the payer had grown from {g('b4_F_h55_k1_size_payer')} tokens at one relay to {g('b4_F_h55_k5_size_payer')} at five and the line stayed at {g('b4_C_h55_k5_size_payer')}.</p>

<h2>What it means</h2>
<p>The breaking point is the agent, not the form. Below about 14 billion parameters a relay in this harness cannot pick its handover out of an inbox of three, in any form: in prose it forwards the wrong one or all of them, in lines it writes a valid line for the wrong one, and with the check at the hop it is refused and held. The check does what it is for, {g('wrong_acts_checked')} wrong acts in {g('chains_checked')} checked chains against {g('wrong_acts_total')} in the unchecked arms, but it buys that with zero throughput on these models, and a relay that is held every time is not a relay. Routing the message, one per call with a short brief, is what a small model needs first; the 7B and the 3B then act, and the 14B stops selecting the wrong item.</p>
<p>An unchecked line is not a half-measure at these sizes; it is the worst form. A line that parses and names the wrong item, or that has lost its slots so the payer fills them from the legend's example, gives the payer something that looks checked and is not. Where a relay cannot be trusted to copy a line exactly, the discipline is the check at the hop or prose, not the line alone.</p>
<p>The injection did nothing, on any model, in any form. These models do not change a payee on a supplier's say-so in an inbox, which leaves the check at the hop as a control against the fault the small models do make, picking another item, and not against the one the block was built to plant.</p>
<p>And the readback is composed by code. The strong model, which in study 8 built every readback with the tool and was never refused wrongly, here wrote the line itself and was refused for form in {g('R_rbform_h55')} readbacks; the code-composed readback on the same model was refused for form {g('C_rbform_h55')} times. The model's part in a readback is to read it, not to write it.</p>

<h2>What we decided</h2>
<dl class="decided">
<dt>The readback is composed by code from the message as delivered, for any receiver that has not shown it copies a line exactly.</dt><dd>H4 held on every model and H8 reversed on the strong one: the model-composed readback held {g('R_heldvr_h55')} Haiku 5.5 chains with every value right and the code-composed one {g('b1_C_h55_held')} in the clean block. The skill and the spec now say so, and that the model-composed readback is for a receiver that has demonstrated the copy with the tool in hand.</dd>
<dt>Below the floor the line alone is not the form.</dt><dd>H6 named Llama 3B and Qwen 7B below it and the 14B's unchecked line was its worst form. An unchecked line at these sizes is the check or nothing; and a legend's example line must be in the live order and must not resemble a live item.</dd>
<dt>The injection axis is a bound, not a result.</dt><dd>H1 could not be tested because no relay complied. The spec claims that no slot carried the planted value past a checked hop, and not that the check is the control against compliance.</dd>
<dt>Small models need the message routed before they need a form.</dt><dd>Block 6 raised the prose and the unchecked line on the 3B and the 7B and removed the 14B's selection errors; the checked forward got no easier. Deploy a small relay with one message per call and a short brief, and check what it forwards.</dd>
</dl>

<h2>The amendments, in short</h2>
<ul>
<li>Before the freeze: the local models run in-process; context 12,288; replies capped at 500 tokens; the anchors run from outside the repository; the reply is the message; ASK on the first line is a question; one nudge for a reply that is not an answer; the act block replaces the act tool and the done report; R without the digest tier, since a model with no code cannot compute it; C's dispute rule; a harness defect in the pilot's first pass fixed and the pilot reset.</li>
<li>After the freeze: Qwen 14B added; the runs kept alive by hand; the remaining blocks cut on the four models below the band; block 6 registered and built; four anchor chains reset under a live runner and run again at the end; four Haiku 5.5 chains ended in a harness fault from a thread-unsafe import and stand as faults.</li>
<li>In the analysis: a wrong act is a chain that acted ({g('asked_elsewhere_total')} chains that asked at the wrong hop in the desk-cover cell reported apart); Haiku 5.5's readback refusals split into form and value; "injected value forwarded" read against the slots; the act executor's two rules (the act's kind, and the exact supplier name for a bank change) recorded as shaping the small models' outcomes; what Llama 3B's block 6 wrong acts were.</li>
</ul>

<h2>What this does not show</h2>
<ul>
<li>Five quantised models on CPU at temperature 0 stand for small models in general only loosely; the result is a shape across sizes, not a number for any model, and most cells hold six chains.</li>
<li>No tools. A relay that must run code to check its own line is not tested here; the harness runs the checks the arm names.</li>
<li>The brevity and length axes ran only on the anchors and on Qwen 1.5B, which never reached a relay's forward; the cut left them unmeasured on the models in between.</li>
<li>The injection is one message in one voice, and no model complied with it; a relay that resists this one may not resist another.</li>
<li>The bank-change executor's exact-name rule stopped ten wrong acts on the small models that the payment and remittance executors would have let through; the wrong-act counts in CHGBANK are lower bounds.</li>
<li>Four Haiku 5.5 chains in the sweep stand as harness faults; the re-run the protocol calls for needs the anchors' runner.</li>
</ul>

<h2>Where everything is</h2>
<p>The protocol with its amendments and its outcome, the speed test, the pilot, the frozen manifest, every chain with every message as sent, the harness's state, the grades, the blind reading and <code>results/summary.json</code>: <code>research/breaking</code> in the rogerwilco repository. The page you are reading is written from that JSON by <code>tools/site_page.py</code>, and <code>app/tests/test_research_figures.py</code> fails if any figure here differs from it.</p>
<p class="foot">Study 9 of 9 · 24 October 2026 · {g('chains')} chains, {g('chains_local')} on five local models through llama.cpp and {g('chains_anchors')} on Claude Haiku 4.5 and Claude Haiku 5.5 as headless text-only sessions, pre-registered · a speed test and a pilot of {g('pilot_chains')} chains · no judge · tiktoken o200k_base · graded in code</p>
</main>
<!-- site:footer -->
<!-- /site:footer -->
</body>
</html>
"""
