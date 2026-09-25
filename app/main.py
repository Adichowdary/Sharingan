"""
PhishGuard — Main FastAPI Application (v2)

Registers all routers including email settings, notifications, SSE.
Starts background notification workers on startup.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.database import init_db, SessionLocal
from app.routers import (
    auth_router, campaigns, url_analyzer,
    analytics, landing, email_settings,
    notifications, sse,
)

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)

# ── Create app ────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

# ── CORS (cross-origin support for API access) ───────────────────────
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security Headers Middleware ───────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from collections import defaultdict
from datetime import datetime, timezone
import time

_rate_limiter: dict[str, list[float]] = defaultdict(list)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers and enforce rate limiting on every response."""

    async def dispatch(self, request: StarletteRequest, call_next):
        # ── Rate limiting (per IP) ────────────────────────────────
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60  # 1-minute window
        max_req = settings.RATE_LIMIT_PER_MINUTE

        # Clean old entries
        _rate_limiter[client_ip] = [
            t for t in _rate_limiter[client_ip] if now - t < window
        ]

        if len(_rate_limiter[client_ip]) >= max_req:
            return StarletteResponse(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        _rate_limiter[client_ip].append(now)

        # ── Process request ───────────────────────────────────────
        response = await call_next(request)

        # ── Security headers ──────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self)"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response


app.add_middleware(SecurityHeadersMiddleware)


# ── Register routers ─────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(campaigns.router)
app.include_router(url_analyzer.router)
app.include_router(analytics.router)
app.include_router(email_settings.router)
app.include_router(notifications.router)
app.include_router(sse.router)
app.include_router(landing.router)

# ── Static files (dashboard UI) ──────────────────────────────────────
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Serve dashboard ──────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_dashboard():
    return FileResponse(str(static_dir / "index.html"))


# ── Startup ───────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    # Initialise database tables
    init_db()

    # Start background notification workers
    from app.services.notification_queue import notification_worker, batch_worker

    loop = asyncio.get_event_loop()
    loop.create_task(notification_worker(SessionLocal))
    loop.create_task(batch_worker(SessionLocal))

    logging.getLogger("phishguard").info(
        f"{settings.PROJECT_NAME} v{settings.VERSION} started "
        f"— dashboard at {settings.BASE_URL}"
    )


# ── Health check ──────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
