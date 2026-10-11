/* rogerwilco: the demo at /demo. Two scripted agents hand a payment over in RW1 lines; every check is a live call to
   this service's own API (/check-ho, /check-rb, /digest, /check-dn). The page parses lines only to put them into plain
   English and to write the scripted replies; nothing here decides a verdict. With the window switch on, the payment tool
   prepares the payment first and prints the readback line itself (study 7): the checker checks the tool's statement, the
   confirmation names its token, and commit runs exactly what was stated. */
(function () {
  "use strict";

  // ------------------------------------------------------------------ the case
  var RECORD = {to: "payer", item: "inv:MD-2026-057", ask: "PAY", sup: "marlow", amt: "5400.00", cur: "GBP", kind: "GROSS",
                acct: "40-12-88/61102938", paid: "20261002", ref: "MD-2026-057", apref: "FD-0929"};
  var RECORD_NO_ACCT = {}; Object.keys(RECORD).forEach(function (k) { if (k !== "acct") RECORD_NO_ACCT[k] = RECORD[k]; });
  var RECORD_LABELS = [["Supplier", "Marlow Design Partners LLP (marlow)"], ["Invoice", "MD-2026-057"], ["Amount", "5,400.00 GBP, gross"],
                       ["Account on file", "40-12-88 / 61102938"], ["Payment date", "2 October 2026"], ["Reference", "MD-2026-057"], ["Approval", "FD-0929, the FD"]];
  var MASTER = [
    {sup: "marlow", name: "Marlow Design Partners LLP", sort_code: "40-12-88", account: "61102938", status: "ACTIVE", since: "2025-03-01"},
    {sup: "northfield", name: "Northfield Print Ltd", sort_code: "20-45-67", account: "31776243", status: "ACTIVE", since: "2024-11-12"},
    {sup: "evergreen", name: "Evergreen Office Supplies", sort_code: "30-98-71", account: "22019483", status: "ACTIVE", since: "2025-09-30"}
  ];
  var LOOKALIKE = {sup: "marlow-design", name: "Marlow Design Studio Ltd", sort_code: "40-12-88", account: "61102983", status: "ACTIVE", since: "2026-09-28"};
  var EXEC_PAY = ["sup", "amt", "cur", "kind", "acct", "paid", "ref", "apref"];

  // ------------------------------------------------------------------ reading a line, enough for the gloss
  var ENVELOPE = {re: 1, from: 1, to: 1, item: 1};
  function parse(line) {
    var tail = null, body = line.trim(), cut = body.indexOf(" // ");
    if (cut >= 0) { tail = body.slice(cut + 4).trim(); body = body.slice(0, cut); }
    var toks = body.split(/\s+/);
    var msg = {type: toks[1], id: toks[2], re: null, from: null, to: null, item: null, slots: {}, tail: tail};
    toks.slice(3).forEach(function (t) {
      var eq = t.indexOf("="); if (eq < 1) return;
      var k = t.slice(0, eq), v = t.slice(eq + 1);
      if (ENVELOPE[k]) msg[k] = v; else msg.slots[k] = v;
    });
    return msg;
  }
  function encode(msg) {
    var parts = ["RW1", msg.type, msg.id];
    ["re", "from", "to", "item"].forEach(function (k) { if (msg[k]) parts.push(k + "=" + msg[k]); });
    Object.keys(msg.slots).forEach(function (k) { parts.push(k + "=" + msg.slots[k]); });
    return parts.join(" ") + (msg.tail ? " // " + msg.tail : "");
  }
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function dateWords(d) { return d && /^\d{8}$/.test(d) ? parseInt(d.slice(6), 10) + " " + MONTHS[parseInt(d.slice(4, 6), 10) - 1] + " " + d.slice(0, 4) : d; }
  function money(a) { var n = Number(a); return isNaN(n) ? a : n.toLocaleString("en-GB", {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
  function acctWords(a) { return a ? a.replace("/", " / ") : "no account given"; }
  function gloss(m) {
    var s = m.slots, who = m.from + " to " + m.to;
    if (m.type === "HO") return who + ": pay " + (s.sup || "?") + " invoice " + String(m.item || "").replace("inv:", "") + ", " + money(s.amt) + " " + (s.cur || "") + (s.kind === "GROSS" ? " gross" : s.kind === "NET" ? " net" : "") + (s.acct ? ", to " + acctWords(s.acct) : ", to the account on file") + ", on " + dateWords(s.paid) + ", approval " + (s.apref || "none") + ". Read back what you will do before you act.";
    if (m.type === "RB" && s.x_tok) return "the payment tool, via " + m.from + ": I will pay " + money(s.amt) + " " + (s.cur || "") + (s.kind === "GROSS" ? " gross" : "") + " to " + acctWords(s.acct) + " on " + dateWords(s.paid) + ", reference " + s.ref + ". Frozen under token " + s.x_tok + "; commit runs exactly this and nothing else.";
    if (m.type === "RB") return who + ": I will pay " + money(s.amt) + " " + (s.cur || "") + (s.kind === "GROSS" ? " gross" : "") + " to " + acctWords(s.acct) + " on " + dateWords(s.paid) + ", reference " + s.ref + (s.h ? ", and here is my fingerprint of what I received." : ".");
    if (m.type === "DN") return who + ": paid " + money(s.amt) + " " + (s.cur || "") + " to " + acctWords(s.acct) + " on " + dateWords(s.paid) + ", reference " + s.ref + ". These are the values the tool reported.";
    if (m.type === "AN") return who + ": " + (s.val === "Y" ? (s.x_tok ? "confirmed; commit " + s.x_tok + "." : "confirmed, go ahead.") : "no.");
    if (m.type === "UN") return who + ": I will not take this (" + s.why + ").";
    return who;
  }
  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]; }); }
  function highlight(line) { return esc(line).replace(/(^|\s)([a-z][a-z0-9_]*)=/g, '$1<b>$2=</b>'); }

  // ------------------------------------------------------------------ the scripted agents
  function scriptedHO(n) {
    return "RW1 HO scheduler-" + n + " p=pay from=scheduler to=payer item=" + RECORD.item + " ask=PAY rb=exec sup=" + RECORD.sup + " amt=" + RECORD.amt + " cur=" + RECORD.cur + " kind=" + RECORD.kind + " acct=" + RECORD.acct + " paid=" + RECORD.paid + " ref=" + RECORD.ref + " apref=" + RECORD.apref + " // approved run, 2 October";
  }
  function scriptedRB(ho, master, n) {
    if (ho.to !== "payer") return "RW1 UN payer-" + n + " re=" + ho.id + " p=pay from=payer to=" + ho.from + " item=" + ho.item + " why=SCOPE // this handover is addressed to " + ho.to + ", not to me";
    var row = null; master.forEach(function (r) { if (!row && r.sup === ho.slots.sup && r.status === "ACTIVE") row = r; });
    var onFile = row ? row.sort_code + "/" + row.account : "unknown", s = ho.slots, tail = "";
    if (s.acct && s.acct !== onFile) tail = " // the handover names " + s.acct + "; the account on file is " + onFile;
    return "RW1 RB payer-" + n + " re=" + ho.id + " from=payer to=scheduler item=" + ho.item + " ask=PAY p=pay sup=" + s.sup + " amt=" + s.amt + " cur=" + s.cur + " kind=" + s.kind + " acct=" + onFile + " paid=" + s.paid + " ref=" + s.ref + " apref=" + s.apref + tail;
  }
  function scriptedDN(hoId, ex) {
    return "RW1 DN payer-3 re=" + hoId + " p=pay from=payer to=scheduler item=" + RECORD.item + " out=OK sup=" + ex.sup + " amt=" + ex.amount + " cur=" + ex.currency + " kind=" + ex.kind + " acct=" + ex.sort_code + "/" + ex.account + " paid=" + ex.payment_date.replace(/-/g, "") + " ref=" + ex.reference + " apref=" + ex.approval + " // as executed, from the payment tool";
  }
  function payTool(args, fault) {
    if (!/^\d{2}-\d{2}-\d{2}\/\d{8}$/.test(args.acct || "")) return {error: "acct must be sortcode/number, e.g. 40-12-88/61102938"};
    if (!/^\d+\.\d{2}$/.test(args.amt || "")) return {error: "amt must have two decimals"};
    var sc = args.acct.split("/");
    var executed = {act: "PAY", item: args.item, sup: args.sup, amount: args.amt, currency: args.cur, kind: args.kind, sort_code: sc[0], account: sc[1],
                    payment_date: args.paid.slice(0, 4) + "-" + args.paid.slice(4, 6) + "-" + args.paid.slice(6, 8), reference: args.ref, approval: args.apref};
    if (fault === "tool") executed.amount = "5100.00";
    if (fault === "prepare") executed.account = "61102983";      // the one-step tool resolves the wrong account as it executes
    return {status: "payment released", executed: executed};
  }
  // the two-phase tool: prepare states and freezes exactly what will run, and prints the readback line itself; commit runs that and nothing else
  function prepareTool(args, fault, ho, hoDigest, n) {
    if (!/^\d{2}-\d{2}-\d{2}\/\d{8}$/.test(args.acct || "")) return {error: "acct must be sortcode/number, e.g. 40-12-88/61102938"};
    if (!/^\d+\.\d{2}$/.test(args.amt || "")) return {error: "amt must have two decimals"};
    var prepared = {}; Object.keys(args).forEach(function (k) { prepared[k] = args[k]; });
    if (fault === "prepare") prepared.acct = "40-12-88/61102983";   // the tool resolves the wrong account as it prepares, and its statement says so
    var token = Math.floor(Math.random() * 0xffffffff).toString(16); while (token.length < 8) token = "0" + token;
    var line = "RW1 RB payer-" + n + " re=" + ho.id + " from=payer to=scheduler item=" + ho.item + " ask=PAY p=pay h=" + hoDigest + " sup=" + prepared.sup + " amt=" + prepared.amt + " cur=" + prepared.cur + " kind=" + prepared.kind + " acct=" + prepared.acct + " paid=" + prepared.paid + " ref=" + prepared.ref + " apref=" + prepared.apref + " x_tok=" + token + " // prepared by the tool; commit executes exactly this";
    return {token: token, prepared: prepared, line: line};
  }
  function commitTool(prep, fault) {
    var p = prep.prepared, sc = p.acct.split("/");
    var executed = {act: "PAY", item: p.item, sup: p.sup, amount: p.amt, currency: p.cur, kind: p.kind, sort_code: sc[0], account: sc[1],
                    payment_date: p.paid.slice(0, 4) + "-" + p.paid.slice(4, 6) + "-" + p.paid.slice(6, 8), reference: p.ref, approval: p.apref};
    if (fault === "tool") executed.amount = "5100.00";             // a fault at the moment of paying: the statement was right, the act is not
    return {status: "payment released", token: prep.token, executed: executed};
  }
  function plant(hoLine, mistake) {
    var edits = {
      digit: [function (l) { return l.replace("61102938", "61102983"); }, "Mistake planted: the scheduler mistyped the last two digits of the account."],
      amount: [function (l) { return l.replace("amt=5400.00", "amt=5100.00"); }, "Mistake planted: the scheduler wrote 5,100.00 instead of 5,400.00."],
      recipient: [function (l) { return l.replace("to=payer", "to=auditor"); }, "Mistake planted: the handover is addressed to the auditor, not the payer."],
      lookalike: [function (l) { return l.replace(/ acct=[^ ]+/, ""); }, "The scheduler leaves the account to the payer, and the payer's master holds a lookalike supplier with a near-identical account."]
    };
    if (mistake === "prepare") return {line: hoLine, note: "Mistake planted in the tool: when it prepares the payment it will resolve the account to 61102983, not the one it was given."};
    if (mistake === "tool") return {line: hoLine, note: "Mistake planted in the tool: at the moment of paying it will pay 5,100.00, whatever it said it would do."};
    if (!edits[mistake]) return {line: hoLine, note: null};
    return {line: edits[mistake][0](hoLine), note: edits[mistake][1]};
  }

  // ------------------------------------------------------------------ the live checks
  function api(path, body) {
    return fetch(path, {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(body)})
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || ("HTTP " + r.status)); return j; }); });
  }
  function recordCheck(rb) {   // the sender's own record: the values the receiver resolved for itself, against the approval
    var problems = [];
    EXEC_PAY.forEach(function (k) { if (k in RECORD && k in rb.slots && rb.slots[k] !== RECORD[k]) problems.push("record: " + k + " mismatch: the readback says " + rb.slots[k] + ", the approval record says " + RECORD[k]); });
    return problems;
  }

  // ------------------------------------------------------------------ the log
  var el = function (id) { return document.getElementById(id); };
  var state = {running: false, stepping: false, n: 0, resolveNext: null, sched: 1};
  function nextSched() { return ++state.sched; }

  function card(o) {
    el("empty").hidden = true;
    state.n += 1;
    var c = document.createElement("article");
    c.className = "tx " + (o.kind || "");
    var h = '<div class="tx-head"><span class="callsign ' + (o.agent ? "agent" : "") + '">' + esc(o.callsign) + '</span><span class="tx-who">' + esc(o.who || "") + '</span><span class="tx-n">' + state.n + '</span></div>';
    if (o.planted) h += '<p class="planted">' + esc(o.planted) + '</p>';
    if (o.waiting) h += '<p class="tx-who">' + esc(o.waiting) + '</p>';
    if (o.line) h += '<pre class="line">' + highlight(o.line) + '</pre>';
    if (o.gloss) h += '<p class="tx-gloss">' + esc(o.gloss) + '</p>';
    if (o.verdict) h += '<p class="verdict ' + (o.kind || "") + '">' + esc(o.verdict) + '</p>';
    if (o.problems && o.problems.length) h += '<ul>' + o.problems.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join("") + '</ul>';
    if (o.notes && o.notes.length) h += '<ul class="notes">' + o.notes.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join("") + '</ul>';
    if (o.inputs) h += '<details><summary>What this agent had in front of it</summary><pre>' + esc(o.inputs) + '</pre></details>';
    c.innerHTML = h;
    el("log").appendChild(c);
    c.scrollIntoView({block: "nearest", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});
    return c;
  }
  function pause() {
    return new Promise(function (resolve) {
      if (!state.stepping) return setTimeout(resolve, 400);
      state.resolveNext = resolve; el("next").disabled = false;
    });
  }
  function finish(fired, summary) {
    var box = document.createElement("div"); box.className = "demo-summary";
    box.innerHTML = "<h2>What happened</h2><p>" + esc(summary) + "</p>" + (fired.length ? "<ul>" + fired.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ul>" : '<p class="hint">No check fired. Nothing was wrong.</p>');
    el("log").appendChild(box);
    box.scrollIntoView({block: "nearest"});
    state.running = false; state.stepping = false; el("run").disabled = false; el("next").disabled = false;
  }
  function failed(e) {
    card({callsign: "page", who: "the service did not answer: " + (e && e.message ? e.message : e), kind: "fail"});
    finish([], "The demo could not reach the checking service. Try again in a moment.");
  }

  // ------------------------------------------------------------------ the run
  function run() {
    if (state.running) return;
    state.running = true; state.n = 0; state.sched = 1;
    Array.prototype.forEach.call(el("log").querySelectorAll(".tx, .demo-summary"), function (x) { x.remove(); });
    el("run").disabled = true;
    var instruction = el("instruction").value.trim();
    var mistake = el("mistake").value;
    var presend = el("presend").checked;
    var windowOn = el("window").checked;
    var prep = null, checkedLine, checked;
    var master = mistake === "lookalike" ? [LOOKALIKE].concat(MASTER) : MASTER;
    var presendRecord = mistake === "lookalike" ? RECORD_NO_ACCT : RECORD;
    var fired = [];
    var hoLine, ho, hoDigest, rbLine, rb, attempt = 0;

    card({callsign: "human", who: "the finance director's instruction, in plain words", gloss: instruction});
    Promise.resolve().then(pause).then(function () {
      // 1. the scheduler drafts the handover
      hoLine = scriptedHO(1);
      var planted = plant(hoLine, mistake); hoLine = planted.line; ho = parse(hoLine);
      card({callsign: "scheduler", who: "agent: the handover, drafted from the record", agent: true, kind: "agent", line: hoLine, gloss: gloss(ho), planted: planted.note,
            inputs: "The instruction: " + instruction + "\n\nThe approval record: " + JSON.stringify(RECORD, null, 1)});
      return pause();
    }).then(function () {
      // 2. the check before sending
      if (!presend) return;
      return api("/check-ho", {ho: hoLine, record: presendRecord, profile: "pay"}).then(function (r) {
        if (r.ok) {
          card({callsign: "checker", who: "code: POST /check-ho, the handover against the approval record, before it goes", kind: "pass",
                verdict: mistake === "lookalike" ? "Checked against the record: sent. The account is left to the payer to resolve, as the record allows." : "Checked against the record: sent.", notes: r.notes});
          return pause();
        }
        fired.push("the check before sending refused the handover");
        card({callsign: "checker", who: "code: POST /check-ho, the handover against the approval record, before it goes", kind: "fail", verdict: "Refused. The line does not match the record, so it is not sent.", problems: r.problems});
        return pause().then(function () {
          hoLine = scriptedHO(nextSched()); if (mistake === "lookalike") hoLine = hoLine.replace(/ acct=[^ ]+/, ""); ho = parse(hoLine);
          return api("/check-ho", {ho: hoLine, record: presendRecord, profile: "pay"});
        }).then(function (r2) {
          card({callsign: "scheduler", who: "agent: the handover, redrafted from the record", agent: true, kind: r2.ok ? "pass" : "fail", line: hoLine, gloss: gloss(ho), verdict: r2.ok ? "Checked against the record: sent." : "Still refused.", problems: r2.ok ? [] : r2.problems});
          if (!r2.ok) throw {stop: "The scheduler could not produce a handover that matches the record. Nothing was sent."};
          return pause();
        });
      });
    }).then(function () {
      return api("/digest", {line: hoLine, profile: "pay"}).then(function (d) { hoDigest = d.digest; });
    }).then(function readback() {
      // 3. the payer reads back; the checker checks; at most two attempts
      attempt += 1;
      rbLine = scriptedRB(ho, master, attempt); rb = parse(rbLine);
      if (rb.type === "UN") {
        fired.push("the payer refused: the handover was not addressed to it");
        card({callsign: "payer", who: "agent: will not act on this", agent: true, kind: "note", line: rbLine, gloss: gloss(rb), inputs: "The handover: " + hoLine + "\n\nThe supplier master: " + JSON.stringify(master, null, 1)});
        throw {stop: "The payer refused the handover, so nothing was paid. A message addressed to someone else is not acted on."};
      }
      rb.slots.h = hoDigest; rbLine = encode(rb); rb = parse(rbLine);
      if (windowOn) {
        // the payer does not send its own readback: it hands the values to the tool, and the tool's statement is the readback
        var s0 = rb.slots;
        var pr = prepareTool({item: rb.item, sup: s0.sup, amt: s0.amt, cur: s0.cur, kind: s0.kind, acct: s0.acct, paid: s0.paid, ref: s0.ref, apref: s0.apref}, mistake, ho, hoDigest, attempt);
        if (pr.error) { card({callsign: "tool", who: "code: the payment tool refused to prepare the call", kind: "fail", verdict: pr.error}); throw {stop: "The payment tool refused the call, so nothing was prepared and nothing was paid."}; }
        prep = pr; checkedLine = pr.line; checked = parse(checkedLine);
        card({callsign: "tool", who: attempt === 1 ? "code: prepare. The tool freezes what it will do under a token and prints the readback line itself; the payer passes it on" : "code: prepare again, from the re-issued handover", kind: "agent", line: checkedLine, gloss: gloss(checked),
              planted: mistake === "prepare" ? "The fault shows in the statement: the tool says it will pay 61102983." : null,
              inputs: "The payer called: prepare pay --account " + s0.acct + " --amount " + s0.amt + " ... (the values from its own reading of the handover and the master)\n\nThe tool answered: " + JSON.stringify({status: "prepared", token: pr.token, prepared: pr.prepared}, null, 1)});
      } else {
        checkedLine = rbLine; checked = rb;
        card({callsign: "payer", who: attempt === 1 ? "agent: the readback, with the account it looked up and the fingerprint its codec adds" : "agent: the second readback", agent: true, kind: "agent", line: rbLine, gloss: gloss(rb),
              inputs: "The handover: " + hoLine + "\n\nThe supplier master: " + JSON.stringify(master, null, 1)});
      }
      return pause().then(function () {
        return api("/check-rb", {ho: hoLine, rb: checkedLine, profile: "pay"});
      }).then(function (r) {
        var recordProblems = recordCheck(checked);
        var problems = r.problems.concat(recordProblems);
        var what = windowOn ? "the tool's statement" : "the readback";
        if (!problems.length) {
          card({callsign: "checker", who: "code: POST /check-rb, " + what + " against the handover, then against the record", kind: "pass", verdict: windowOn ? "Roger, wilco. Every value the tool will run with matches the record." : "Roger, wilco. Every value the payer will act with matches the record.", notes: r.notes});
          return pause().then(function () {
            var an = "RW1 AN scheduler-" + nextSched() + " re=" + checked.id + " p=pay from=scheduler to=payer val=Y" + (windowOn ? " x_tok=" + prep.token + " // statement matches the approved run; commit " + prep.token : " // readback matches the approved run; proceed");
            card({callsign: "scheduler", who: windowOn ? "code: the confirmation, naming the token the tool may commit" : "code: the confirmation that clears the act", line: an, gloss: gloss(parse(an))});
            return pause();
          });
        }
        fired.push(windowOn ? (attempt === 1 ? "the check of the tool's statement caught a mismatch before the act" : "the tool's second statement was refused too")
                            : (attempt === 1 ? "the readback check caught a mismatch before the act" : "the second readback was refused too"));
        var verdict = (r.problems.length && !recordProblems.length) ? "Refused. " + (windowOn ? "The statement" : "The readback") + " differs from the handover but matches the record, so the handover was wrong. The payment waits." : "Refused. The payment waits.";
        card({callsign: "checker", who: "code: POST /check-rb, " + what + " against the handover, then against the record", kind: "fail", verdict: verdict, problems: problems});
        if (attempt === 2) throw {stop: windowOn ? "The tool's statement was refused twice, so nothing was ever committed. The payment is held for a human, and the fault is in the tool, not the agent." : "Two readbacks were refused, so the payer never acted. The payment is held for a human."};
        return pause().then(function () {
          var n2 = nextSched();
          hoLine = scriptedHO(n2).replace("scheduler-" + n2, "scheduler-" + n2 + " re=" + checked.id).replace("// approved run, 2 October", "// re " + checked.id + ": " + problems[0].slice(0, 120));
          ho = parse(hoLine);
          card({callsign: "scheduler", who: "code: re-issues the handover from the record, pointing at the refused " + (windowOn ? "statement" : "readback"), line: hoLine, gloss: gloss(ho)});
          if (windowOn) card({callsign: "tool", who: "code: abandon " + prep.token + ". The prepared payment is discarded; nothing ran", kind: "note", verdict: "Abandoned. The payer will prepare again from the re-issued handover."});
          return api("/digest", {line: hoLine, profile: "pay"}).then(function (d) { hoDigest = d.digest; }).then(pause).then(readback);
        });
      });
    }).then(function () {
      // 4. the act, through the tool
      var s = rb.slots, result;
      if (windowOn) {
        result = commitTool(prep, mistake);
      } else {
        result = payTool({item: rb.item, sup: s.sup, amt: s.amt, cur: s.cur, kind: s.kind, acct: s.acct, paid: s.paid, ref: s.ref, apref: s.apref}, mistake);
      }
      if (result.error) { card({callsign: "tool", who: "code: the payment tool refused the call", kind: "fail", verdict: result.error}); throw {stop: "The payment tool refused the call, so nothing was paid."}; }
      var ex = result.executed;
      card({callsign: "tool", who: windowOn ? "code: commit " + prep.token + ". The tool executes the statement it froze, and prints what it did" : "code: the payment tool executes the confirmed values and prints what it did", line: JSON.stringify(ex), gloss: "Released " + money(ex.amount) + " " + ex.currency + " to " + ex.sort_code + " / " + ex.account + ", reference " + ex.reference + ".",
            planted: mistake === "tool" ? "Mistake planted: the tool paid 5,100.00 instead of the 5,400.00 it said it would." : mistake === "prepare" && !windowOn ? "Mistake planted: the tool paid account 61102983 instead of the one it was told. With no statement to check, nothing could see this before the money moved." : null});
      return pause().then(function () {
        // 5. the done report, from the tool's printout, and the second loop
        var dnLine = scriptedDN(ho.id, ex), dn = parse(dnLine);
        card({callsign: "payer", who: "agent: the done report, from what the tool printed, not what it meant", agent: true, kind: "agent", line: dnLine, gloss: gloss(dn), inputs: "The tool printed: " + JSON.stringify(ex, null, 1)});
        return pause().then(function () { return api("/check-dn", {ho: hoLine, dn: dnLine, rb: checkedLine, profile: "pay"}); });
      }).then(function (r) {
        if (r.ok) {
          card({callsign: "checker", who: "code: POST /check-dn, the done report against the plan", kind: "pass", verdict: "The payment went out exactly as agreed.", notes: r.notes});
          finish(fired, fired.length ? "A mistake was caught before the money moved, the handover was corrected from the record, and the payment then went out as agreed."
                        : windowOn && mistake === "none" ? "Everything matched at every step. The tool said what it would do, the checker agreed, and the tool did exactly that."
                        : mistake === "lookalike" ? "The payer picked the right account despite the lookalike, so there was nothing to catch, and the payment went out as agreed."
                        : "Everything matched at every step.");
        } else {
          fired.push("the done check flagged a difference between the plan and what the tool did");
          card({callsign: "checker", who: "code: POST /check-dn, the done report against the plan", kind: "fail", verdict: "Flagged. The tool did something other than what was agreed. Recall the payment.", problems: r.problems});
          finish(fired, windowOn ? "The money has already moved. The tool's statement was right and the tool did something else at the last moment; nothing before the act can see that, and the done check saw it within one message."
                        : mistake === "prepare" ? "The money has already moved to the wrong account. With the window on, the tool's statement would have shown this account before anything was paid; run it again with the second switch on."
                        : "The money has already moved. The done check is the only check that can see a tool fault, and it sees it within one message.");
        }
      });
    }).catch(function (e) {
      if (e && e.stop) return finish(fired, e.stop);
      failed(e);
    });
  }

  el("record").innerHTML = RECORD_LABELS.map(function (kv) { return "<dt>" + esc(kv[0]) + "</dt><dd>" + esc(kv[1]) + "</dd>"; }).join("");
  el("run").addEventListener("click", function () { state.stepping = false; run(); });
  el("next").addEventListener("click", function () {
    if (!state.running) { state.stepping = true; run(); return; }
    el("next").disabled = true;
    var r = state.resolveNext; state.resolveNext = null; if (r) r();
  });
  el("reset").addEventListener("click", function () {
    if (state.running) return;
    Array.prototype.forEach.call(el("log").querySelectorAll(".tx, .demo-summary"), function (x) { x.remove(); });
    el("empty").hidden = false; state.n = 0;
  });
})();
