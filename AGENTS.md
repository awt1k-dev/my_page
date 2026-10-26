# AGENTS.md

## What this repo is

One-page RU/EN portfolio for **awtik** (`awtik.ru`), served by FastAPI + Jinja2. There is no form, database or outbound API: the only dynamic work is per-IP rate limiting. Contact happens through a direct Telegram link.

All copy lives in `app/i18n.py`; templates only render structure. RU is `/`, EN is `/en/`; both are server-rendered.

## Commands

```bash
uv sync --all-groups
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8001
uv run pytest
uv run ruff check .
uv run mypy app
PORT=8001 docker compose up --build
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build  # prod: app + Caddy
```

Port **8000** is usually occupied by `cloth_site-api` on this machine. Use `8001` locally, or stop that container before mapping 8000.

## Rate limiting / privacy

- Every request except `/healthz` is limited per IP via `app/ratelimit.py` (`RATE_LIMIT_REQUESTS`, default 120 per `RATE_LIMIT_WINDOW`, 60 s). A normal page load is roughly 15–20 requests.
- The site stores no form data and has no bot. Only IP addresses may appear in server logs, for spam protection; the privacy pages say so. Keep both language versions in sync.
- Set `TRUST_PROXY_HEADERS=true` only behind a trusted Nginx/Caddy. The in-process limiter assumes one worker; don't scale workers without replacing it.
- Security work that remains: strict CSP/security headers, static path handling, and the per-IP limiter.

## Gotchas

- In `app/i18n.py`, never name dict keys `items` or `values` — Jinja resolves them as `dict.items` / `dict.values` and rendering breaks. Current keys are `entries`, `cases`, and `tools`.
- All user-facing strings (including privacy text) must be added to both `ru` and `en` in `app/i18n.py`.
- Keep first-level copy client-facing: technical terms belong in case dialogs and the collapsed “technical details” disclosure, not in the hero, services, work cards, process or contact section.
- Templates: `app/templates/index.html`, `base.html`, `privacy.html`, `404.html`. CSS/JS are served directly from `app/static/`.
- `app/static/favicon/` is a copy of root `favicon/`; keep both in sync if icons change.
- `sitemap.xml` and `robots.txt` are generated in `app/main.py`, not static files. Canonicals/hreflang use `PUBLIC_BASE_URL`.
- The contact section is a two-column layout: copy and direct links on the left, a dark Telegram card on the right. All CTAs scroll to `#contact`; only that card opens `https://t.me/valerarsdj`. Keep the button visible and keyboard-accessible, and do not reintroduce `/contact-fallback` or a JSON endpoint.
- The hero fits with `white-space: nowrap`; English uses smaller clamp sizes in CSS (`html[lang="en"]`) because its headline is longer. Check both languages after editing the hero.
- Do not reintroduce `-webkit-text-stroke`, transparent display text, giant watermark words or hover states that change padding: the current direction is solid, readable type and stable layout.
- The header theme is driven by `data-header="dark|light"` on sections **and the footer** and `app/static/js/main.js`. New sections need that attribute or the header color will be wrong while scrolling over them.
- CSS/JS are served with `no-cache` (their URLs are not fingerprinted). Do not add a long `max-age` back without adding hashes.
- Tests create the app via `create_app()` and clear `get_settings` cache; env overrides are in `tests/conftest.py`. The fixture also disables `.env` loading so tests always use their own rate-limit settings — keep that isolation.
- No build/codegen/migrations. Editing CSS/JS/templates only needs a server restart (or `--reload`).

## Checks before finishing

Run `uv run ruff check .`, `uv run mypy app`, `uv run pytest`. For visual changes, verify `/` and `/en/` at desktop and mobile widths, plus the case dialog and the Telegram card.
