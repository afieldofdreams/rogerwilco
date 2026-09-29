"""MCP server for rogerwilco, over Streamable HTTP. Tools: validate, check_rb, make_rb, legend, to_json.

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
    "verifies. Call legend to get the format in a few lines. Use validate on every line you send or receive, make_rb "
    "to build the readback for an HO you received, and check_rb to verify a readback before you treat a handoff as "
    "accepted. to_json converts a line to its JSON form."
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
    integrity (tier 2, when the RB carries h=), echo (tier 3) and, if the HO asked for rb=acc or rb=plan,
    comprehension (tier 4) all pass. Only then does the receiver own the item; otherwise re-send the HO with re=
    pointing at the bad RB. notes lists assumptions to confirm."""
    return svc.check_rb(ho, rb, profile, expect_acc)


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


TOOLS = (
    (validate, "Validate a rogerwilco line", None),
    (check_rb, "Check a readback", None),
    (make_rb, "Make a readback", None),
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
