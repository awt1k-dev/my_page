# awtik — landing

Monochrome one-page portfolio for **awtik** with a RU/EN switch, a direct Telegram contact card and per-IP rate limiting.

**Stack:** FastAPI, Jinja2, vanilla CSS/JS, pydantic-settings. No database, no frontend build step, no outbound API calls.

## Quick start

```bash
cp .env.example .env          # already present locally
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8001
```

Open <http://127.0.0.1:8001/>. Port **8000** is often taken by `cloth_site-api` on this machine; use `8001` for local work or stop that container.

## Commands

```bash
uv run uvicorn app.main:app --reload --port 8001   # dev server
uv run pytest                                      # tests
uv run ruff check .                                # lint
uv run mypy app                                    # types
PORT=8001 docker compose up --build                # container
```

## Project layout

```text
app/
  main.py          routes, security headers, rate limiting, sitemap/robots
  config.py        pydantic-settings; reads .env
  i18n.py          ALL Russian/English copy and case data
  ratelimit.py     in-process sliding-window limiter
  templates/       base, index, privacy, 404
  static/          css, js, fonts, images, favicon copy
tests/             page, security, rate-limit tests
```

## Content and i18n

- **All user-facing copy lives in `app/i18n.py`.** Templates only render structure, so RU and EN stay in sync.
- Do not use `items` or `values` as dict keys in `app/i18n.py`: Jinja resolves them as `dict.items` / `dict.values`. The current keys are `entries`, `cases`, and `tools`.
- Main visual system: `app/static/css/main.css`; interactions: `app/static/js/main.js`.
- Fonts are self-hosted in `app/static/fonts/` (Unbounded, Manrope, JetBrains Mono). No Google Fonts request at runtime.
- There are no stock photos. Case previews are CSS/SVG mockups; the OG images are `app/static/img/og.png` (RU) and `og-en.png` (EN).
- RU is served at `/`, EN at `/en/` — both are server-rendered for SEO, with hreflang and canonical URLs based on `PUBLIC_BASE_URL`.

## Contact and rate limiting

- There is no contact form and no bot. The contact section links straight to [@valerarsdj](https://t.me/valerarsdj); every other CTA scrolls to that section.
- The site stores no form data. Privacy copy lives on `/privacy` and `/en/privacy` and explains that only IP addresses may appear in server logs, for spam protection.
- Every request except `/healthz` is rate-limited per IP (`RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW`, default 120 requests per 60 seconds). A normal page load uses roughly 15–20 requests.
- Rate limiting is in-memory and per process. Keep one worker (the Docker command does) or replace it with Redis before scaling out.
- `TRUST_PROXY_HEADERS=true` only when running behind a trusted reverse proxy, otherwise `X-Forwarded-For` can be spoofed and every visitor will share the proxy IP. The app logs a warning if the header arrives while the flag is off.
- Tests ignore the real `.env` and use their own settings.

## Deploy notes

Production is one VPS: Caddy terminates TLS and proxies to the app container. Both are started from `deploy/docker-compose.prod.yml`, and `deploy/deploy.sh` does fetch → rebuild → restart → `/healthz` check.

The server has no git, so the script pulls the `main` tarball from GitHub. It keeps `.env` and the `caddy_data` volume, and replaces everything else.

```bash
mkdir -p ~/awtik_landing && cd ~/awtik_landing
curl -fsSL https://github.com/awt1k-dev/my_page/archive/refs/heads/main.tar.gz | tar xz --strip-components=1
cp .env.example .env   # PUBLIC_BASE_URL, TRUST_PROXY_HEADERS=true, PORT=8001
./deploy/deploy.sh
```

Updates are the same `./deploy/deploy.sh`; it is safe to re-run.

- `deploy/Caddyfile` serves `awtik.ru`, redirects `www.awtik.ru` and `www.awtik.ru` to it, and gets/renews Let's Encrypt certificates automatically (stored in the `caddy_data` volume).
- The app is published on `127.0.0.1:${PORT:-8000}` only; Caddy reaches it at `web:8000`. Set `TRUST_PROXY_HEADERS=true`, otherwise every visitor shares the proxy IP.
- Both containers use `json-file` logging with `10m` × 3 rotation to keep the small disk clean.
- Caddy waits for the app healthcheck (`/healthz`) before starting.
- `deploy/nginx.conf.example` is kept as an alternative if Caddy is ever replaced.

- CSS/JS are served with `Cache-Control: no-cache` because their URLs are not fingerprinted; fonts/images keep a long cache.
- The container runs as a non-root user.
- CI lives in `.github/workflows/ci.yml` and runs ruff, mypy and pytest.
- If the domain is down, first check DNS/TLS and the reverse proxy, then the app container. The app itself does not manage TLS.

## Design notes

- Strict black/white; off-white paper `#f2f2ee`, ink `#0a0a0a`.
- The page alternates paper/ink sections; the header theme follows the section under it.
- FAQ is the final dark band; contact is paper with an ink Telegram card — keep that contrast when editing it.
- The approach section keeps technical details inside the collapsed “technical details” disclosure.
- Avoid outlined/transparent display text and giant watermark words; hierarchy comes from solid type and scale.
- The intro overlay is shown once per browser session; `prefers-reduced-motion` disables it and all reveal animations.
- Case rows open native `<dialog>` elements; hovering a row swaps the sticky preview on desktop. Hover states must not change row geometry.
