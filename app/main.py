"""rogerwilco app: a JSON API over the RW1 reference codec, an MCP endpoint at /mcp, and the site at /.

Run from the repo root:  uvicorn app.main:app --reload
"""
import json
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import mcp as rw_mcp
from . import service as svc

DESCRIPTION = (
    "One-line typed messages for handing work between agents, with a readback the sender verifies. "
    "JSON in, JSON out. Codec errors answer 400 with {\"error\": \"...\"}. An MCP server for agents is at /mcp."
)

EXAMPLE_HO = "RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 pri=2 // hero copy, 120 words"
PROFILE_HELP = "Profile name such as pay or pform. Null or core means the core vocabulary."
ACC_HELP = "Criteria as key:value tokens joined by +, for example len:120w+tone:plain+no:em-dash."


class LineBody(BaseModel):
    line: str = Field(description="One rogerwilco message on one line.", examples=[EXAMPLE_HO])
    profile: str | None = Field(default=None, description=PROFILE_HELP)


class CheckRBBody(BaseModel):
    ho: str = Field(description="The HO line the sender sent.", examples=[EXAMPLE_HO])
    rb: str = Field(description="The RB line that came back.")
    profile: str | None = Field(default=None, description=PROFILE_HELP)
    expect_acc: str | list[str] | None = Field(
        default=None, description="The criteria the sender kept back, compared with the RB's acc=. " + ACC_HELP)


class CheckHOBody(BaseModel):
    ho: str = Field(description="The HO line about to be sent.")
    record: dict = Field(description="The record the HO was built from: slot names (and to, item, ask) to values as "
                                     "they are written on the line, for example {\"amt\": \"5400.00\"}.")
    profile: str | None = Field(default=None, description=PROFILE_HELP)


class CheckDNBody(BaseModel):
    ho: str = Field(description="The HO line the sender sent.")
    dn: str = Field(description="The DN line that came back after the act.")
    profile: str | None = Field(default=None, description=PROFILE_HELP)
    rb: str | None = Field(default=None, description="The RB that passed the sender's check, when the receiver resolved "
                                                     "values the HO did not carry; its values are then the plan.")


class MakeRBBody(BaseModel):
    ho: str = Field(description="The HO line to read back.", examples=[EXAMPLE_HO])
    id: str = Field(description="Message id for the RB, for example writer-01.")
    profile: str | None = Field(default=None, description=PROFILE_HELP)
    acc: str | list[str] | None = Field(
        default=None, description="What the receiver derived from the brief. " + ACC_HELP)
    do: str | None = Field(default=None, description="What the receiver will produce, for example copy.")
    hash: bool = Field(default=True, description="Add h=, the digest of the HO.")


class FromJSONBody(BaseModel):
    message: dict | str = Field(description="The JSON form of a message: an object, or a string that holds one.")
    profile: str | None = Field(default=None, description=PROFILE_HELP)


class GateBody(BaseModel):
    lines: str = Field(description="One rogerwilco line per row: the lines that state facts from the source document.")
    profile: str = Field(description="A profile that makes the lines the record: clin or pay.", examples=["clin"])
    document: str | None = Field(
        default=None, description="The source document as plain text. For clin, src=doc:<id>#l<n> counts its lines "
                                  "from 1 and each line's quote must be found in the lines it cites. For pay, an inbox "
                                  "export with messages separated by --- lines, so email:<n> can be checked.")
    doc_id: str | None = Field(default=None, description="The document's id, the part after doc: in src=. Optional.")


router = APIRouter()
MARKDOWN = {200: {"content": {"text/markdown": {}}}}


@router.get("/", include_in_schema=False)
def index():
    return FileResponse(svc.APP_DIR / "static" / "index.html", media_type="text/html",
                        headers={"Cache-Control": "no-cache"})


PAGES = {"quickstart": "quickstart.html", "demo": "demo.html", "lines": "lines.html", "profiles": "profiles.html", "about": "about.html"}


TEXT_FILES = {"robots.txt": "text/plain", "llms.txt": "text/plain", "llms-full.txt": "text/plain",
              "sitemap.xml": "application/xml", "quickstart.md": "text/markdown"}


def _text_file(name: str):
    return FileResponse(svc.APP_DIR / "static" / name, media_type=f"{TEXT_FILES[name]}; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


@router.get("/robots.txt", include_in_schema=False)
def robots():
    return _text_file("robots.txt")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return _text_file("sitemap.xml")


@router.get("/llms.txt", include_in_schema=False)
def llms():
    return _text_file("llms.txt")


@router.get("/llms-full.txt", include_in_schema=False)
def llms_full():
    return _text_file("llms-full.txt")


@router.get("/quickstart.md", include_in_schema=False)
def quickstart_md():
    return _text_file("quickstart.md")


@router.get("/quickstart", include_in_schema=False)
def quickstart():
    return FileResponse(svc.APP_DIR / "static" / PAGES["quickstart"], media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/demo", include_in_schema=False)
def demo():
    return FileResponse(svc.APP_DIR / "static" / PAGES["demo"], media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/lines", include_in_schema=False)
def lines():
    return FileResponse(svc.APP_DIR / "static" / PAGES["lines"], media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/about", include_in_schema=False)
def about():
    return FileResponse(svc.APP_DIR / "static" / PAGES["about"], media_type="text/html", headers={"Cache-Control": "no-cache"})



RESEARCH_DIR = svc.APP_DIR / "static" / "research"
RESEARCH_PAGES = {"wire-study", "pilot", "month-end", "translation", "readback", "plan-readback", "tool-prepare"}


@router.get("/research", include_in_schema=False)
def research_index():
    return FileResponse(RESEARCH_DIR / "index.html", media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/research/{slug}", include_in_schema=False)
def research_page(slug: str):
    if slug not in RESEARCH_PAGES:
        raise HTTPException(status_code=404, detail="no such study")
    return FileResponse(RESEARCH_DIR / f"{slug}.html", media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/healthz", summary="Liveness, protocol version and build")
def healthz():
    return svc.health()


@router.post("/validate", summary="Validate one line")
def validate(body: LineBody):
    return svc.validate(body.line, body.profile)


@router.post("/check-rb", summary="Check a readback against the HO it answers")
def check_rb(body: CheckRBBody):
    return svc.check_rb(body.ho, body.rb, body.profile, body.expect_acc)


@router.post("/check-ho", summary="Check an HO against the record before it is sent")
def check_ho(body: CheckHOBody):
    return svc.check_ho(body.ho, body.record, body.profile)


@router.post("/check-dn", summary="Check a done report against the plan")
def check_dn(body: CheckDNBody):
    return svc.check_dn(body.ho, body.dn, body.profile, body.rb)


@router.post("/make-rb", summary="Build a readback for an HO")
def make_rb(body: MakeRBBody):
    return svc.make_rb(body.ho, body.id, body.profile, body.acc, body.do, body.hash)


@router.post("/to-json", summary="Line to its JSON form")
def to_json(body: LineBody):
    return svc.to_json(body.line, body.profile)


@router.post("/from-json", summary="JSON form to a line")
def from_json(body: FromJSONBody):
    return svc.from_json(body.message, body.profile)


@router.post("/digest", summary="The h= digest of a line")
def digest(body: LineBody):
    return svc.digest(body.line, body.profile)


@router.post("/gate", summary="Check lines against the source they came from")
def gate(body: GateBody):
    return svc.gate(body.lines, body.profile, body.document, body.doc_id)


@router.get("/legend", response_class=PlainTextResponse, summary="Legend to paste into an agent's prompt")
def legend(profile: str | None = Query(default=None, description=PROFILE_HELP)):
    return PlainTextResponse(svc.legend(profile))


@router.get("/profiles", summary="Available profiles")
def profiles(request: Request):
    # A browser gets the page about profiles; a program (Accept: */* or application/json) gets the list.
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse(svc.APP_DIR / "static" / PAGES["profiles"], media_type="text/html", headers={"Cache-Control": "no-cache", "Vary": "Accept"})
    return JSONResponse(svc.profiles(), headers={"Vary": "Accept"})


def _markdown(request: Request, which: str) -> Response:
    try:
        text = svc.document(which)
    except OSError:
        raise HTTPException(status_code=404, detail=f"{which} not found in the skill folder") from None
    # Browsers offer to save text/markdown instead of showing it, so a page navigation gets text/plain.
    media = "text/plain" if "text/html" in request.headers.get("accept", "") else "text/markdown"
    return PlainTextResponse(text, media_type=media, headers={"Vary": "Accept"})


@router.get("/spec", summary="The protocol spec (SPEC.md)", responses=MARKDOWN)
def spec(request: Request):
    return _markdown(request, "spec")


@router.get("/skill", summary="The skill file (SKILL.md)", responses=MARKDOWN)
def skill(request: Request):
    return _markdown(request, "skill")


# The largest request the API needs is the gate's: 200,000 characters of document and 60,000 of lines, which JSON
# escaping can grow. Anything bigger is refused before it is read into memory, so one request cannot exhaust the box.
MAX_BODY = 1_000_000

# The site loads its own script and stylesheet and Google Fonts, and uses inline styles; it has no inline script. The
# interactive API docs at /docs load Swagger UI from a CDN with an inline script, so they are left without the policy.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
SECURITY_HEADERS = [(b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-frame-options", b"DENY"), (b"permissions-policy", b"camera=(), microphone=(), geolocation=()")]


class Guard:
    """ASGI middleware: refuses a request body over MAX_BODY with 413 (by its Content-Length, or as it streams in
    when it has none), and adds security headers to every response, with the content policy on the site's pages."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > MAX_BODY):
            return await _too_large(send)
        seen = 0
        refused = False

        async def capped_receive():
            # FastAPI turns an exception raised while it reads a body into a 400, so an oversized stream is answered
            # here with the 413, and the app is told the client went away; whatever it sends after is dropped.
            nonlocal seen, refused
            if refused:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > MAX_BODY:
                    refused = True
                    await _too_large(send)
                    return {"type": "http.disconnect"}
            return message

        async def send_with_headers(message):
            if refused:
                return
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += SECURITY_HEADERS
                ctype = dict(headers).get(b"content-type", b"")
                if ctype.startswith(b"text/html") and not path.startswith("/docs"):
                    headers.append((b"content-security-policy", CSP.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, capped_receive, send_with_headers)
        except Exception:
            if not refused:
                raise


async def _too_large(send):
    body = json.dumps({"error": f"request body is larger than {MAX_BODY:,} bytes"}).encode()
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())] + SECURITY_HEADERS})
    await send({"type": "http.response.body", "body": body})


def _error(status: int, message: str, headers=None) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status, headers=headers)


def create_app() -> FastAPI:
    """A new app with its own MCP server. Build one per test run; the MCP session manager starts once per app."""
    mcp_routes, mcp_run = rw_mcp.create()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp_run():
            yield

    app = FastAPI(title="rogerwilco", version="0.1.0", description=DESCRIPTION, lifespan=lifespan, redoc_url=None)
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
        expose_headers=["Mcp-Session-Id", "Mcp-Protocol-Version"],
    )

    @app.exception_handler(svc.FormError)
    async def form_error(_request: Request, exc: svc.FormError):
        return _error(400, str(exc))

    @app.exception_handler(RequestValidationError)
    async def bad_request(_request: Request, exc: RequestValidationError):
        first = exc.errors()[0]
        if first.get("type") == "json_invalid":
            return _error(422, "request body is not valid JSON")
        where = ".".join(str(part) for part in first["loc"] if part != "body")
        return _error(422, f"{where}: {first['msg']}" if where else first["msg"])

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, str(exc.detail), getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def unexpected(_request: Request, _exc: Exception):
        return _error(500, "internal error")

    app.add_middleware(Guard)   # added last, so it runs first: the cap applies before CORS or any route reads
    app.include_router(router)
    app.router.routes.extend(mcp_routes)
    app.mount("/static", StaticFiles(directory=str(svc.APP_DIR / "static")), name="static")   # site.css
    return app


app = create_app()
