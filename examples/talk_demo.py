#!/usr/bin/env python3
"""A payment handoff played as a radio exchange, for a 15-minute talk.

    python3 examples/talk_demo.py --clean            # readback passes, the payment goes out
    python3 examples/talk_demo.py --draft-fault      # a transposed digit is refused before the line is sent
    python3 examples/talk_demo.py --tool-fault       # the tool resolves the wrong account; its statement is refused
    python3 examples/talk_demo.py --relay            # scheduler -> coordinator -> desk -> payer, each hop checked
    python3 examples/talk_demo.py --relay --drop     # the desk drops apref=; the check at that hop names it
    python3 examples/talk_demo.py --prose            # the same instruction as three paragraphs, for contrast
    python3 examples/talk_demo.py --all              # every scene in order, with a heading each

    --pace SECONDS   pause between lines (default 1.2; 0 for tests)
    --step           advance on Enter instead of the pause
    --no-color       plain text (colour is used only on a tty anyway)

Standard library only. The codec is imported by path from rogerwilco/scripts; nothing is installed.
Every digest on screen is computed by the codec as the scene runs. The script checks its own expectations:
a check that should pass and does not, or one that should refuse and does not, stops the run with DEMO FAULT.
"""
import argparse
import os
import secrets
import sys
import textwrap
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "rogerwilco", "scripts"))
import rogerwilco as rw  # noqa: E402

PROFILE = "pay"
WIDTH = 100

# The approved record: what the finance director signed off. In a real system this comes from the database.
RECORD = {"to": "payer", "item": "inv:MD-2026-057", "ask": "PAY", "sup": "marlow", "amt": "5400.00", "cur": "GBP",
          "kind": "GROSS", "acct": "40-12-88/61102938", "paid": "20261002", "ref": "MD-2026-057", "apref": "FD-0929"}
EXEC = ("sup", "amt", "cur", "kind", "acct", "paid", "ref", "apref")   # the pay profile's execution slots for PAY

ROLE = {"scheduler": "scheduler", "payer": "payer", "coordinator": "coordinator", "desk": "desk",
        "paytool": "payment tool"}


# ---------------------------------------------------------------- output
class Style:
    def __init__(self, enabled: bool):
        self.bold = "\033[1m" if enabled else ""
        self.dim = "\033[2m" if enabled else ""
        self.cyan = "\033[36m" if enabled else ""
        self.green = "\033[32m" if enabled else ""
        self.red = "\033[31m" if enabled else ""
        self.yellow = "\033[33m" if enabled else ""
        self.off = "\033[0m" if enabled else ""


class Stage:
    def __init__(self, pace: float, step: bool, color: bool):
        self.pace, self.step, self.s = pace, step, Style(color)

    def pause(self):
        if self.step:
            try:
                input()
            except EOFError:
                pass
        elif self.pace > 0:
            time.sleep(self.pace)

    def heading(self, title: str):
        print()
        print(f"{self.s.bold}{title}{self.s.off}")
        print("=" * min(WIDTH, len(title)))
        print()
        self.pause()

    def note(self, text: str):
        """A context line: not a message, not a check."""
        for row in textwrap.wrap(text, WIDTH - 4, subsequent_indent="  "):
            print(f"    {self.s.dim}{row}{self.s.off}")
        print()
        self.pause()

    def caption(self, text: str):
        assert len(text.split()) <= 12, f"caption over 12 words: {text!r}"
        print(f"    {self.s.dim}> {text}{self.s.off}")
        print()

    def line(self, speaker: str, to: str | None, msg: str, caption: str):
        """One radio call: who is speaking, the RW1 line in full, and what it meant."""
        route = f"{ROLE.get(speaker, speaker)} -> {ROLE.get(to, to)}" if to else ROLE.get(speaker, speaker)
        print(f"{self.s.cyan}{self.s.bold}{route}{self.s.off}")
        for row in textwrap.wrap(msg, WIDTH - 4, subsequent_indent="      ",
                                 break_long_words=False, break_on_hyphens=False):
            print(f"    {row}")
        self.caption(caption)
        self.pause()

    def check(self, who: str, name: str, problems: list, notes: list, expect_pass: bool, caption: str):
        """A check, printed with the codec's own words. The script stops if the outcome is not the expected one."""
        passed = not problems
        if passed != expect_pass:
            print(f"{self.s.red}{self.s.bold}DEMO FAULT: {name} was expected to "
                  f"{'pass' if expect_pass else 'refuse'} and did not: {problems}{self.s.off}")
            sys.exit(2)
        ok_text = {"check-ho": "OK the HO matches the record; send it",
                   "check-rb": "OK readback passes; ownership transfers",
                   "check-dn": "OK the done report matches the plan",
                   "check-thread": "OK every handoff is closed or open in time"}[name]
        print(f"{self.s.yellow}{ROLE.get(who, who)} runs {name}{self.s.off}")
        if passed:
            print(f"    {self.s.green}{ok_text}{self.s.off}")
        else:
            for p in problems:
                for row in textwrap.wrap(f"REFUSED: {p}", WIDTH - 4, subsequent_indent="      "):
                    print(f"    {self.s.red}{row}{self.s.off}")
        for n in notes:
            print(f"    {self.s.dim}note: {n}{self.s.off}")
        self.caption(caption)
        self.pause()

    def closing(self, text: str):
        print(f"{self.s.bold}{text}{self.s.off}")
        print()
        self.pause()


def record_note(st: Stage):
    r = RECORD
    st.note(f"approved record {r['apref']} (signed off by the finance director): pay {r['sup']} {r['amt']} {r['cur']} "
            f"{r['kind']} to {r['acct']} on {r['paid']}, reference {r['ref']}, for {r['item']}")


# ---------------------------------------------------------------- the agents
def build_ho(sender: str, to: str, msg_id: str, extra: dict | None = None, drop: str | None = None,
             source: dict | None = None) -> str:
    """Write an HO from a record by code. source defaults to the approved record; a relay hop passes what it heard."""
    src = source or RECORD
    slots = {k: v for k, v in src.items() if k not in ("to", "item", "from") and k != drop}
    slots.update(extra or {})
    return rw.encode({"type": "HO", "id": msg_id, "from": sender, "to": to, "item": src["item"],
                      "slots": {"p": PROFILE, "rb": ["exec"], **slots}}, PROFILE)


class PaymentTool:
    """The payer's payment tool in two phases: prepare() resolves the payment and states it as a readback line;
    commit() executes exactly what was stated, and only with the token the sender confirmed."""

    def __init__(self, lookalike: bool = False):
        self.pending: dict[str, dict] = {}
        self.lookalike = lookalike

    def prepare(self, ho_line: str) -> tuple[str, str]:
        ho, errors, _ = rw.parse(ho_line, PROFILE)
        if errors or ho["to"] != "payer":
            raise ValueError(f"refused: {errors or 'not addressed to the payer'}")
        values = {k: ho["slots"][k] for k in EXEC}
        if self.lookalike:
            values["acct"] = "40-12-88/61102983"   # the account the tool resolved: a lookalike, two digits swapped
        token = secrets.token_hex(4)
        self.pending[token] = values
        statement = rw.encode({"type": "RB", "id": "payer-1", "re": ho["id"], "from": "payer", "to": ho["from"],
                               "item": ho["item"], "slots": {"p": PROFILE, "ask": "PAY",
                                                             "h": rw.digest(ho_line, PROFILE), "x_tok": token,
                                                             **values}}, PROFILE)
        return token, statement

    def abandon(self, token: str):
        self.pending.pop(token, None)

    def commit(self, token: str, confirmed: bool, ho_line: str) -> str:
        if not confirmed or token not in self.pending:
            raise PermissionError("no confirmation for this token: nothing is paid")
        values = self.pending.pop(token)
        ho, _, _ = rw.parse(ho_line, PROFILE)
        # ... the bank is called here with `values`, and nothing else ...
        return rw.encode({"type": "DN", "id": "payer-2", "re": ho["id"], "from": "payer", "to": ho["from"],
                          "item": ho["item"], "slots": {"p": PROFILE, "out": "OK", **values}}, PROFILE)


# ---------------------------------------------------------------- scenes
def scene_clean(st: Stage):
    st.heading("Scene 1: cleared to pay (a clean handoff)")
    record_note(st)
    ho = build_ho("scheduler", "payer", "scheduler-1")
    st.line("scheduler", "payer", ho, "The job, built from the approved record by code, not typed.")
    problems, notes = rw.check_ho(ho, RECORD, PROFILE)
    st.check("scheduler", "check-ho", problems, notes, True,
             "Checked against the record before it leaves the scheduler.")

    tool = PaymentTool()
    token, statement = tool.prepare(ho)
    st.line("paytool", None, statement, "The tool states what it will execute, before it executes.")
    st.line("payer", "scheduler", statement, "Payer relays the statement unchanged; h= is the codec's digest.")
    problems, notes = rw.check_rb_full(ho, statement, PROFILE)
    st.check("scheduler", "check-rb", problems, notes, True,
             "Every execution value matches the plan; the digest proves it arrived.")

    an = rw.encode({"type": "AN", "id": "scheduler-2", "re": "payer-1", "from": "scheduler", "to": "payer",
                    "slots": {"p": PROFILE, "val": "Y"}, "tail": "readback matches the approved run; proceed"}, PROFILE)
    st.line("scheduler", "payer", an, "Cleared. Only now may the tool commit the token.")
    dn = tool.commit(token, confirmed=True, ho_line=ho)
    st.line("payer", "scheduler", dn, "What the tool did, from its result, not what was meant.")
    problems, notes = rw.check_dn(ho, dn, PROFILE, rb_line=statement)
    st.check("scheduler", "check-dn", problems, notes, True, "Done report matches the plan.")
    problems, notes = rw.check_thread([ho, statement, an, dn], PROFILE)
    st.check("scheduler", "check-thread", problems, notes, True, "The handoff opened once and closed once.")
    st.closing("Roger. Wilco.")


def scene_draft_fault(st: Stage):
    st.heading("Scene 2: a transposed digit in the draft (refused before it is sent)")
    record_note(st)
    good = build_ho("scheduler", "payer", "scheduler-1")
    draft = good.replace("61102938", "61102398")   # the draft was typed, and two digits swapped places
    assert draft != good
    st.line("scheduler", None, draft, "Drafted by hand. One account digit transposed: 2938 became 2398.")
    problems, notes = rw.check_ho(draft, RECORD, PROFILE)
    st.check("scheduler", "check-ho", problems, notes, False, "Refused at the boundary. Nothing leaves the scheduler.")
    st.closing("Not sent. The error lived at the boundary, and the boundary is where it was caught.")


def scene_tool_fault(st: Stage):
    st.heading("Scene 3: the tool resolves a lookalike account (refused before anything is paid)")
    record_note(st)
    ho = build_ho("scheduler", "payer", "scheduler-1")
    st.line("scheduler", "payer", ho, "The HO is right: built from the record and checked.")
    problems, notes = rw.check_ho(ho, RECORD, PROFILE)
    st.check("scheduler", "check-ho", problems, notes, True, "Checked against the record before it leaves the scheduler.")

    tool = PaymentTool(lookalike=True)
    token, statement = tool.prepare(ho)
    st.line("paytool", None, statement, "The tool resolved a lookalike account. Its statement says so.")
    st.line("payer", "scheduler", statement, "Payer relays it unchanged. The payer does not check; the sender does.")
    problems, notes = rw.check_rb_full(ho, statement, PROFILE)
    st.check("scheduler", "check-rb", problems, notes, False,
             "Set the altitude in the window; the other pilot checks the window.")
    an = rw.encode({"type": "AN", "id": "scheduler-2", "re": "payer-1", "from": "scheduler", "to": "payer",
                    "slots": {"p": PROFILE, "val": "N"}, "tail": "acct differs from the approved record; do not commit"},
                   PROFILE)
    st.line("scheduler", "payer", an, "Not cleared. The tool abandons the token; nothing is paid.")
    tool.abandon(token)
    try:
        tool.commit(token, confirmed=False, ho_line=ho)
    except PermissionError as e:
        st.note(f"payment tool: {e}")
    st.closing("Nothing paid. A human looks at the account before anyone tries again.")


def scene_relay(st: Stage, drop: bool):
    title = "Scene 4: the same handoff relayed through two more agents, each hop checked"
    if drop:
        title = "Scene 4b: the desk drops apref= when it forwards"
    st.heading(title)

    # hop 1: scheduler -> coordinator, built from the approved record
    ho1 = build_ho("scheduler", "coordinator", "scheduler-1")
    st.line("scheduler", "coordinator", ho1, "Hop one: scheduler to the coordinator, built from the record.")
    facts = {k: v for k, v in RECORD.items() if k != "to"}   # the route changes at each hop; the facts do not
    problems, notes = rw.check_ho(ho1, facts, PROFILE)
    st.check("scheduler", "check-ho", problems, notes, True, "Checked against the approved record before it goes.")

    # hop 2: the coordinator forwards what it heard, adds due= and pri=, and checks its line against the one received
    heard1 = rw.parse(ho1, PROFILE)[0]
    received1 = {"item": heard1["item"], **heard1["slots"]}
    ho2 = build_ho("coordinator", "desk", "coordinator-1", extra={"due": "20261002", "pri": 2}, source=received1)
    st.line("coordinator", "desk", ho2, "Coordinator adds due= and pri=, checks its line against what it heard.")
    problems, notes = rw.check_ho(ho2, received1, PROFILE)
    st.check("coordinator", "check-ho", problems, notes, True, "Every value it heard is still on the line it sends.")

    # hop 3: the desk forwards, adds appr=OK, and checks; with --drop it loses apref= on the way
    heard2 = rw.parse(ho2, PROFILE)[0]
    received2 = {"item": heard2["item"], **heard2["slots"]}
    ho3 = build_ho("desk", "payer", "desk-1", extra={"appr": "OK"}, source=received2,
                   drop="apref" if drop else None)
    if drop:
        st.line("desk", "payer", ho3, "Desk adds appr=OK and forwards without apref=. Watch the check.")
        problems, notes = rw.check_ho(ho3, received2, PROFILE)
        st.check("desk", "check-ho", problems, notes, False,
                 "Refused at hop three, naming the slot. Nothing reaches the payer.")
        st.closing("The graph's edges, each one checked. One edge failed, and only that edge.")
        return
    st.line("desk", "payer", ho3, "Desk adds appr=OK and checks again. The graph's edges, each one checked.")
    problems, notes = rw.check_ho(ho3, received2, PROFILE)
    st.check("desk", "check-ho", problems, notes, True, "Three hops, three checks, one record.")

    # the payer reads back to the hop it heard from
    rb = rw.make_rb(ho3, "payer-1", PROFILE)
    st.line("payer", "desk", rb, "Payer reads back to the desk; the digest proves it arrived intact.")
    problems, notes = rw.check_rb_full(ho3, rb, PROFILE)
    st.check("desk", "check-rb", problems, notes, True, "The payer now owns the job. Every edge was checked.")
    st.closing("The graph's edges, each one checked.")


PROSE = [
    ("scheduler", "coordinator",
     "Hi, could you pass this on to the payments desk for me? We've had sign-off from the finance director "
     "(approval ref FD-0929) to pay Marlow's invoice MD-2026-057. The amount is £5,400.00 gross, including VAT, "
     "to their usual account, sort code 40-12-88, account number 61102938, going out on 2 October 2026, and "
     "please make sure the payment reference is MD-2026-057 so their accounts team can match it. It isn't urgent "
     "but I'd like it confirmed back once it's with the desk. Let me know if anything looks off or you need the PO."),
    ("coordinator", "desk",
     "Forwarding a payment request from the scheduler. Marlow have an invoice outstanding, MD-2026-057, which the "
     "FD has approved under FD-0929. Please arrange payment of £5,400 (that's the gross figure, VAT included) to "
     "Marlow's account on file, 40-12-88 / 61102938, with reference MD-2026-057. The scheduler would like it to go "
     "on the 2nd of October, so I've set the due date to 2 October and marked it priority 2 since it's not urgent "
     "but shouldn't slip. Could you confirm back to me when it's with the payer, and flag anything that doesn't "
     "match what you have on file for Marlow?"),
    ("desk", "payer",
     "Please release the following payment. Supplier: Marlow. Invoice: MD-2026-057. Amount: £5,400.00 gross "
     "(inclusive of VAT), currency GBP. Pay to the account held in the supplier master, sort code 40-12-88, account "
     "61102938. Payment date 2 October 2026, priority 2. Use MD-2026-057 as the remittance reference. This has been "
     "approved by the principal, so it's cleared to go; the approval came through the scheduler via the coordinator "
     "earlier today. Once the payment is made, send back the confirmation with the amount and account actually "
     "used so I can close it off on our side. Thanks."),
]
PROSE_CAPTIONS = ["The same instruction as agents actually write it: hop one.",
                  "Hop two restates and rewords. Which copy is the record?",
                  "Hop three lost the approval reference. No check can say so."]


def tokens(text: str) -> int:
    return round(len(text) / 4)


def scene_prose(st: Stage):
    st.heading("Scene 5: the same instruction as prose (for contrast)")
    for (speaker, to, text), cap in zip(PROSE, PROSE_CAPTIONS):
        print(f"{st.s.cyan}{st.s.bold}{ROLE[speaker]} -> {ROLE[to]}{st.s.off}")
        for row in textwrap.wrap(text, WIDTH - 4):
            print(f"    {row}")
        st.caption(cap)
        st.pause()
    line = build_ho("scheduler", "payer", "scheduler-1")
    st.line("scheduler", "payer", line, "The line again. Every fact in a slot, checkable at every hop.")
    short = {"scheduler": "scheduler", "coordinator": "coordinator", "desk": "desk", "payer": "payer"}
    rows = [(f"prose, hop {i + 1} ({short[sp]} -> {short[to]})", len(t), tokens(t))
            for i, (sp, to, t) in enumerate(PROSE)]
    total_chars = sum(len(t) for _, _, t in PROSE)
    rows.append(("prose, three hops", total_chars, tokens("".join(t for _, _, t in PROSE))))
    rows.append(("the line, any hop", len(line), tokens(line)))
    print(f"    {'':<46}{'chars':>8}{'tokens':>9}")
    for label, chars, toks in rows:
        print(f"    {label:<46}{chars:>8}{toks:>9}")
    print()
    st.caption("Tokens approximated as characters divided by four.")
    st.caption("No check is possible on prose: nothing has a slot.")
    st.pause()
    st.closing("Three paragraphs, three paraphrases, no readback. One line, one digest, checked at every edge.")


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="rogerwilco talk demo: a payment handoff as a radio exchange")
    ap.add_argument("--clean", action="store_true", help="scene 1: readback passes, the payment goes out")
    ap.add_argument("--draft-fault", action="store_true", help="scene 2: a transposed digit refused before sending")
    ap.add_argument("--tool-fault", action="store_true", help="scene 3: the tool resolves the wrong account")
    ap.add_argument("--relay", action="store_true", help="scene 4: scheduler -> coordinator -> desk -> payer")
    ap.add_argument("--drop", action="store_true", help="with --relay: the desk drops apref= and is refused")
    ap.add_argument("--prose", action="store_true", help="scene 5: the same instruction as prose, with token counts")
    ap.add_argument("--all", action="store_true", help="every scene in order")
    ap.add_argument("--pace", type=float, default=1.2, help="seconds between lines (default 1.2; 0 for tests)")
    ap.add_argument("--step", action="store_true", help="advance on Enter")
    ap.add_argument("--no-color", action="store_true", help="plain text")
    a = ap.parse_args(argv)

    color = sys.stdout.isatty() and not a.no_color and not os.environ.get("NO_COLOR")
    st = Stage(a.pace, a.step, color)
    chosen = a.all or any([a.clean, a.draft_fault, a.tool_fault, a.relay, a.drop, a.prose])
    if not chosen:
        ap.print_help()
        return 2
    if a.all or a.clean:
        scene_clean(st)
    if a.all or a.draft_fault:
        scene_draft_fault(st)
    if a.all or a.tool_fault:
        scene_tool_fault(st)
    if a.all:
        scene_relay(st, drop=False)
        scene_relay(st, drop=True)
    elif a.relay or a.drop:
        scene_relay(st, drop=a.drop)
    if a.all or a.prose:
        scene_prose(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
