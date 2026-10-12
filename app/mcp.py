"""MCP server for rogerwilco, over Streamable HTTP. Tools: validate, gate, check_rb, make_rb, check_ho, check_dn, check_thread, legend, to_json.

Built on the official SDK (pip install "mcp<2"; the 2.x line renamed FastMCP and moved the transport options). The
server is stateless and answers with plain JSON, so any client can call it with a single POST and no session.

This file is called mcp.py, like the SDK it uses. Import it as app.mcp and never put this folder itself on sys.path.
"""
import sys
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field
from starlette.routing import Route

from . import service as svc


def _import_sdk():
    """Import the SDK with this folder off sys.path, so that a bare `import mcp` cannot find this file instead
    (`cd app && python -m pytest` puts the current directory first on the path)."""
    here = Path(__file__).resolve().parent
    saved = list(sys.path)
    sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != here]
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.server.transport_security import TransportSecuritySettings
        from mcp.types import ToolAnnotations
    finally:
        sys.path[:] = saved
    return FastMCP, TransportSecuritySettings, ToolAnnotations


FastMCP, TransportSecuritySettings, ToolAnnotations = _import_sdk()

INSTRUCTIONS = (
    "rogerwilco (RW1) is a one-line typed message format for handing work between agents, with a readback the sender "
    "verifies. A fact that came from a document crosses as a line that points back at it (src=). Call legend to get "
    "the format in a few lines. Use validate on every line you send or receive, make_rb to build the readback for an "
    "HO you received, and check_rb to verify a readback before you treat a handoff as accepted. Before an irreversible "
    "act, check_ho compares the HO with the record it was built from before it is sent, and afterwards check_dn "
    "compares the done report with the plan. When lines state facts from a source document (profile clin or pay), send "
    "the document and the lines to gate and fix every error before anyone acts on them. to_json converts a line to its "
    "JSON form."
)

Line = Annotated[str, Field(description="One rogerwilco message on one line, starting RW1.")]
Profile = Annotated[str, Field(description="Profile name such as pay or pform. Leave empty for the core vocabulary.")]


def validate(line: Line, profile: Profile = "") -> dict[str, Any]:
    """Check one rogerwilco line against the protocol. Returns {ok, message, errors, warnings}. ok is true when there
    are no errors. message is the parsed JSON form (trust it only when ok is true). Each error names the rule it
    breaks. Run it on every line you send or receive."""
    return svc.validate(line, profile)


def check_rb(
    ho: Annotated[str, Field(description="The HO line the sender sent.")],
    rb: Annotated[str, Field(description="The RB line that came back.")],
    profile: Profile = "",
    expect_acc: Annotated[str, Field(description=(
        "Optional. The acceptance criteria the sender wrote down before sending and kept back, as key:value tokens "
        "joined by +, for example len:120w+tone:plain+no:em-dash. Compared with the RB's acc=."))] = "",
) -> dict[str, Any]:
    """Sender-side check of a readback. Returns {ok, problems, notes}. ok is true only when receipt (tier 1),
    integrity (tier 2, when the RB carries h=), echo (tier 3), if the HO asked for rb=acc or rb=plan comprehension
    (tier 4), and if it asked for rb=exec execution (tier 5: the profile's execution slots for the ask, with the
    values the receiver will act with) all pass. Only then does the receiver own the item; otherwise re-send the HO
    with re= pointing at the bad RB. notes lists assumptions to confirm."""
    return svc.check_rb(ho, rb, profile, expect_acc)


def check_ho(
    ho: Annotated[str, Field(description="The HO line about to be sent.")],
    record: Annotated[dict[str, Any], Field(description=(
        "The record the HO was built from: slot names (and to, item, ask) to values written as they are on the line, "
        "for example {\"to\": \"payer\", \"amt\": \"5400.00\", \"acct\": \"40-12-88/61102938\"}."))],
    profile: Profile = "",
) -> dict[str, Any]:
    """The check before sending a handoff for an irreversible act (a payment, a payee change, anything external).
    Compares the HO with the record it should have been built from: every value in the record must appear in the HO
    unchanged, and under a profile that names execution slots for the ask the HO must say rb=exec. Returns {ok,
    problems, notes}. Send the HO only when ok is true; a note names a value in the HO that the record cannot vouch
    for."""
    return svc.check_ho(ho, record, profile)


def check_dn(
    ho: Annotated[str, Field(description="The HO line the sender sent.")],
    dn: Annotated[str, Field(description="The DN line that came back after the act.")],
    profile: Profile = "",
    rb: Annotated[str, Field(description=(
        "Optional. The RB that passed check_rb, when the receiver read back values the HO did not carry (the account "
        "it found on file); those values are then part of the plan the DN is checked against."))] = "",
) -> dict[str, Any]:
    """The second loop: check a done report against the plan after an irreversible act. The DN must answer the HO,
    and under a profile that names execution slots for the ask it must carry every one of them with the value as
    executed, equal to the HO's value or to the readback's where the HO left the slot to the receiver. out=NOOP
    carries none; out=PARTIAL carries the ones that were executed. Returns {ok, problems, notes}. A problem here
    means the tool did something other than what was agreed, which no readback can catch."""
    return svc.check_dn(ho, dn, profile, rb or None)


def check_thread(
    lines: Annotated[str, Field(description="The conversation, one rogerwilco message per row, in the order sent.")],
    profile: Profile = "",
    now: Annotated[str, Field(description="Optional. The time to judge expiry at, YYYYMMDDTHHMMZ in UTC.")] = "",
) -> dict[str, Any]:
    """Check that every handoff closed. Each HO must end exactly once: DN, UN or FL from its receiver, or a CX from
    its sender that the receiver acknowledged with AN val=Y. Flags a handoff still open past its exp= or due=
    (orphaned), a DN after a CX (the act ran although cancelled), a handoff closed twice, and a CX from the wrong
    agent. Returns {ok, problems, notes}; notes list handoffs still open and in time."""
    return svc.check_thread(lines, profile, now or None)


def make_rb(
    ho: Annotated[str, Field(description="The HO line you received.")],
    id: Annotated[str, Field(description="Your message id for the RB, for example writer-01.")],
    profile: Profile = "",
    acc: Annotated[str, Field(description=(
        "Optional. The acceptance criteria you derived from the brief, as key:value tokens joined by +. "
        "Required when the HO says rb=acc or rb=plan."))] = "",
    do: Annotated[str, Field(description=(
        "Optional. What you will produce, for example copy, spec, dataset or pr. Required when the HO says "
        "rb=plan."))] = "",
    hash: Annotated[bool, Field(description="Add h=, the digest of the HO. Default true.")] = True,
) -> dict[str, Any]:
    """Build a correct readback for an HO line, as a receiver that can run code should. It echoes item, ask and due
    (and anything the HO names in rb=), adds h= unless hash is false, and carries acc and do when you supply them.
    Returns {rb}."""
    return svc.make_rb(ho, id, profile, acc, do, hash)


def legend(profile: Profile = "") -> str:
    """Return the short legend that lets another agent read and write rogerwilco lines. Paste it into that agent's
    system prompt. Pass a profile such as pay or pform to include that profile's codes."""
    return svc.legend(profile)


def to_json(line: Line, profile: Profile = "") -> dict[str, Any]:
    """Convert one rogerwilco line to its JSON twin. Returns {message}. Fails with an error when the line is
    invalid."""
    return svc.to_json(line, profile)


def gate(
    lines: Annotated[str, Field(description=(
        "The translation: one rogerwilco line per row, the lines that stand in for the source document."))],
    profile: Annotated[str, Field(description="A profile that makes the lines the record: clin or pay.")],
    document: Annotated[str, Field(description=(
        "Optional but what the gate is for. The source document as plain text. For clin, src=doc:<id>#l<n> counts "
        "its lines from 1 and each line's quote (the tail) must be found verbatim in the lines it cites. For pay, an "
        "inbox export with messages separated by --- lines, so email:<n> can be checked."))] = "",
    doc_id: Annotated[str, Field(description="The document's id, the part after doc: in src=. Optional.")] = "",
) -> dict[str, Any]:
    """Check a batch of lines against the source they came from, before anyone acts on them or they become the
    record. Every row must be a valid line under the profile, every statement (ST) must point at its evidence with
    src=, and the evidence must say what the line says: for clin the quote in the tail is found verbatim in the cited
    document line(s), the item kind is one of the profile's, there is exactly one src per line and ids are unique;
    for pay a line about a source document carries src=, an invoice line carries amt cur kind, and net plus vat
    equals amt. Returns {ok, errors, notes, counts, rows, accepted}. ok is false if any row fails; fix every error
    and send the whole batch again."""
    return svc.gate(lines, profile, document or None, doc_id or None)


TOOLS = (
    (validate, "Validate a rogerwilco line", None),
    (gate, "Check lines against their source", None),
    (check_rb, "Check a readback", None),
    (make_rb, "Make a readback", None),
    (check_ho, "Check a handoff against the record", None),
    (check_dn, "Check a done report", None),
    (check_thread, "Check that every handoff closed", None),
    (legend, "Get the legend", False),     # plain text, not a JSON object
    (to_json, "Convert a line to JSON", None),
)


def build_server():
    server = FastMCP(
        "rogerwilco",
        instructions=INSTRUCTIONS,
        stateless_http=True,       # every request stands alone; no session to lose on restart or scale-out
        json_response=True,        # answer with JSON, not an event stream
        streamable_http_path="/mcp",
        log_level="WARNING",
        # The SDK turns on DNS rebinding protection for a localhost bind and then only accepts Host: localhost, which
        # would refuse every request behind a real domain. This server is public, holds no state and takes no
        # credentials, so there is nothing for a rebinding attack to reach.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    hints = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    for fn, title, structured in TOOLS:
        server.add_tool(fn, title=title, description=" ".join(fn.__doc__.split()), annotations=hints,
                        structured_output=structured)
    return server


def create():
    """Return (routes, run): the Route objects to add to the main app, and the lifespan context manager factory that
    has to be running while they serve. Each call builds a fresh server, so an app can be started more than once."""
    server = build_server()
    endpoint = server.streamable_http_app().routes[0].endpoint   # also creates server.session_manager
    # POST only: a stateless server has no event stream to offer, so GET and DELETE answer 405, as the spec asks.
    # Both spellings are served so that no client is redirected (a redirect can lose the scheme behind a proxy).
    routes = [Route(path, endpoint=endpoint, methods=["POST"]) for path in ("/mcp", "/mcp/")]
    return routes, server.session_manager.run
