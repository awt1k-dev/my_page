from __future__ import annotations

import json
import logging
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.i18n import EMAIL, GITHUB, TELEGRAM, get_content
from app.ratelimit import SlidingWindowLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _base_url() -> str:
    return get_settings().public_base_url.rstrip("/")


def _page_context(request: Request, lang: str, page: str) -> dict[str, Any]:
    t = get_content(lang)
    base = _base_url()
    is_en = lang == "en"

    if page == "privacy":
        ru_path, en_path = "/privacy", "/en/privacy"
    else:
        ru_path, en_path = "/", "/en/"

    canonical = base + (en_path if is_en else ru_path)
    schema = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": "awtik",
        "url": base + "/",
        "image": base + "/static/img/og.png",
        "description": t["meta"]["description"],
        "email": EMAIL,
        "sameAs": [GITHUB, f"https://t.me/{TELEGRAM}"],
        "serviceType": [
            "Web development",
            "Telegram bots",
            "Automation",
            "Launch and support",
        ],
        "founder": {
            "@type": "Person",
            "name": "awtik",
            "url": GITHUB,
            "sameAs": [GITHUB, f"https://t.me/{TELEGRAM}"],
        },
        "areaServed": "Worldwide",
        "availableLanguage": ["ru", "en"],
        "knowsAbout": [
            "Python",
            "FastAPI",
            "SQLAlchemy",
            "PostgreSQL",
            "Telegram bots",
            "Docker",
            "Nginx",
            "Linux",
        ],
    }

    return {
        "request": request,
        "t": t,
        "lang": lang,
        "page": page,
        "site_url": base,
        "canonical": canonical,
        "alternate_ru": base + ru_path,
        "alternate_en": base + en_path,
        "home_path": "/en/" if is_en else "/",
        "privacy_path": "/en/privacy" if is_en else "/privacy",
        "email": EMAIL,
        "telegram": TELEGRAM,
        "github": GITHUB,
        "telegram_url": f"https://t.me/{TELEGRAM}",
        "year": datetime.now(UTC).year,
        "og_image": base + ("/static/img/og-en.png" if is_en else "/static/img/og.png"),
        "og_image_width": 1200 if is_en else 2400,
        "og_image_height": 630 if is_en else 1260,
        "schema_json": json.dumps(
            schema, ensure_ascii=False, separators=(",", ":")
        ).replace("</", "<\\/"),
        "csp_nonce": getattr(request.state, "csp_nonce", ""),
    }


def create_app() -> FastAPI:
    settings = get_settings()
    limiter = SlidingWindowLimiter(settings.rate_limit_requests, settings.rate_limit_window)

    app = FastAPI(
        title="awtik landing",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.limiter = limiter
    app.state.proxy_warning_logged = False
    app.add_middleware(GZipMiddleware, minimum_size=800)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        nonce = secrets.token_urlsafe(18)
        request.state.csp_nonce = nonce

        if (
            not settings.trust_proxy_headers
            and request.headers.get("x-forwarded-for")
            and not app.state.proxy_warning_logged
        ):
            app.state.proxy_warning_logged = True
            logger.warning(
                "X-Forwarded-For detected but TRUST_PROXY_HEADERS is false; "
                "rate limiting will use the proxy IP. Set TRUST_PROXY_HEADERS=true "
                "only behind a trusted proxy."
            )

        ip = _client_ip(request, settings.trust_proxy_headers)
        if request.url.path != "/healthz" and not limiter.allow(ip):
            response: Response = PlainTextResponse(
                "Too many requests",
                status_code=429,
                headers={"Retry-After": str(settings.rate_limit_window)},
            )
        else:
            response = await call_next(request)

        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if settings.public_base_url.startswith("https://"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        path = request.url.path
        if (
            path == "/favicon.ico"
            or path.startswith(("/static/css/", "/static/js/"))
            or path.startswith("/favicon/")
        ):
            # These URLs are not fingerprinted, so a long cache would leave
            # users on stale CSS/JS after a deploy.
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=2592000"
        elif response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    app.mount(
        "/favicon",
        StaticFiles(directory=str(BASE_DIR / "static" / "favicon")),
        name="favicon",
    )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_page_context(request, "ru", "index"),
        )

    @app.get("/en", include_in_schema=False)
    async def en_without_slash() -> RedirectResponse:
        return RedirectResponse("/en/", status_code=308)

    @app.get("/en/", response_class=HTMLResponse)
    async def index_en(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_page_context(request, "en", "index"),
        )

    @app.get("/privacy", response_class=HTMLResponse)
    async def privacy(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="privacy.html",
            context=_page_context(request, "ru", "privacy"),
        )

    @app.get("/en/privacy", response_class=HTMLResponse)
    async def privacy_en(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="privacy.html",
            context=_page_context(request, "en", "privacy"),
        )

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/robots.txt", include_in_schema=False)
    async def robots() -> PlainTextResponse:
        return PlainTextResponse(
            "User-agent: *\n"
            "Allow: /\n"
            f"Sitemap: {_base_url()}/sitemap.xml\n"
        )

    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap() -> Response:
        base = _base_url()
        last_modified = datetime.now(UTC).date().isoformat()
        urls = [base + "/", base + "/en/", base + "/privacy", base + "/en/privacy"]
        body = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for url in urls:
            priority = "1.0" if url in (base + "/", base + "/en/") else "0.4"
            body.append("<url>")
            body.append(f"<loc>{url}</loc>")
            body.append(f"<lastmod>{last_modified}</lastmod>")
            body.append("<changefreq>monthly</changefreq>")
            body.append(f"<priority>{priority}</priority>")
            body.append("</url>")
        body.append("</urlset>")
        return Response("\n".join(body), media_type="application/xml")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(BASE_DIR / "static" / "favicon" / "favicon.ico")

    @app.exception_handler(404)
    async def not_found(request: Request, _exc: Exception) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "not_found"}, status_code=404)
        lang = "en" if request.url.path.startswith("/en") else "ru"
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context=_page_context(request, lang, "404"),
            status_code=404,
        )

    return app


app = create_app()
