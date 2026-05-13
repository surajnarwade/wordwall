import asyncio
import json
import logging
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

logger = logging.getLogger("wordwall")

UPSTREAM_URL = os.getenv("UPSTREAM_URL", "").rstrip("/")


def _current_hostname() -> str:
    return os.getenv("HOSTNAME") or socket.gethostname() or "unknown"

# Load templates from files
_DIR = os.path.join(os.path.dirname(__file__), "templates")
with open(os.path.join(_DIR, "submit.html")) as f:
    SUBMIT_TEMPLATE = f.read()
with open(os.path.join(_DIR, "admin.html")) as f:
    ADMIN_TEMPLATE = f.read()

# In-memory store
words: list[dict] = []
_subscribers: set[asyncio.Queue] = set()
_http: httpx.AsyncClient | None = None


async def _broadcast(entry: dict):
    words.append(entry)
    msg = json.dumps(entry)
    for q in _subscribers:
        await q.put(msg)


async def _clear_all():
    words.clear()
    for q in _subscribers:
        await q.put("__RESET__")


async def _forward_upstream(entry: dict, upstream_url: str | None = None):
    url = upstream_url or UPSTREAM_URL
    if not url or _http is None:
        return
    target = f"{url}/forward"
    try:
        r = await _http.post(target, json=entry)
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text.strip()
        if len(body) > 200:
            body = f"{body[:200]}..."
        logger.warning(
            "upstream forward failed url=%s status=%s body=%r",
            target,
            exc.response.status_code,
            body,
        )
        raise RuntimeError(f"{target} returned {exc.response.status_code}") from exc
    except Exception as exc:
        logger.warning("upstream forward failed url=%s error=%s", target, exc)
        raise RuntimeError(f"request to {target} failed") from exc


# --- App ---

@asynccontextmanager
async def lifespan(_: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=5.0)
    if UPSTREAM_URL:
        logger.info("forwarding words upstream to %s", UPSTREAM_URL)
    yield
    words.clear()
    _subscribers.clear()
    await _http.aclose()
    _http = None


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index(mode: str = "submit"):
    if mode == "admin":
        return HTMLResponse(ADMIN_TEMPLATE, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(SUBMIT_TEMPLATE)


@app.get("/_hostname")
async def hostname(request: Request):
    return {"hostname": _current_hostname()}


@app.post("/submit")
async def submit(request: Request):
    body = await request.json()
    w = body.get("word", "").strip()
    if not w:
        return JSONResponse({"error": "empty"}, status_code=400)
    name = body.get("name", "anon").strip() or "anon"
    req_upstream = body.get("upstream_url", "").strip().rstrip("/") or None

    hostname = _current_hostname()

    entry = {"id": str(uuid.uuid4())[:8], "word": w, "name": name, "hostname": hostname, "time": time.time()}
    target_url = req_upstream or UPSTREAM_URL
    if target_url:
        try:
            await _forward_upstream(entry, target_url)
        except RuntimeError as exc:
            return JSONResponse(
                {
                    "error": "upstream_forward_failed",
                    "message": str(exc),
                },
                status_code=502,
            )
    await _broadcast(entry)
    return {"ok": True, "word": w, "forwarded": bool(target_url)}


@app.post("/forward")
async def receive_forward(request: Request):
    entry = await request.json()
    if not {"id", "word", "name", "hostname", "time"}.issubset(entry.keys()):
        return JSONResponse({"error": "invalid"}, status_code=400)
    await _broadcast(entry)
    return {"ok": True}


@app.post("/clear")
async def clear():
    await _clear_all()
    return {"ok": True}


@app.get("/words")
async def list_words():
    """Debug endpoint to verify words are actually stored."""
    return {"count": len(words), "words": words}


@app.get("/events")
async def events():
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)

    async def stream():
        try:
            yield "retry: 3000\nevent: heartbeat\ndata: ping\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15)
                    if data == "__RESET__":
                        yield "event: reset\ndata: \n\n"
                    else:
                        yield f"event: word\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: ping\n\n"
                except (asyncio.CancelledError, GeneratorExit):
                    break
        finally:
            _subscribers.discard(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
