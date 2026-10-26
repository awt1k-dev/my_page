from __future__ import annotations

TELEGRAM_URL = "https://t.me/valerarsdj"


def test_home_ru(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="ru"' in response.text
    assert "ДО СЕРВЕРА" in response.text
    assert 'data-case="cloth-drop"' in response.text
    assert f'href="{TELEGRAM_URL}"' in response.text
    assert "Написать в Telegram" in response.text
    assert 'id="contact-form"' not in response.text
    assert "Content-Security-Policy" in response.headers


def test_home_en(client):
    response = client.get("/en/")
    assert response.status_code == 200
    assert 'lang="en"' in response.text
    assert "ALL THE WAY" in response.text
    assert "Cloth Drop" in response.text
    assert "/static/img/og-en.png" in response.text
    assert f'href="{TELEGRAM_URL}"' in response.text
    assert "Message on Telegram" in response.text


def test_en_redirect(client):
    response = client.get("/en", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "/en/"


def test_privacy_ru_and_en(client):
    ru = client.get("/privacy")
    en = client.get("/en/privacy")
    assert ru.status_code == 200 and en.status_code == 200
    assert "Политика конфиденциальности" in ru.text
    assert "Privacy policy" in en.text
    assert "IP-адрес" in ru.text
    assert "IP address" in en.text
    assert "форм" in ru.text
    assert "Отправляя форму" not in ru.text


def test_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert "NOT FOUND" in response.text
    assert 'content="noindex, follow"' in response.text


def test_404_en(client):
    response = client.get("/en/nope")
    assert response.status_code == 404
    assert 'lang="en"' in response.text
    assert "Page not found." in response.text


def test_removed_form_routes_are_gone(client):
    assert client.get("/contact-fallback").status_code == 404
    assert client.get("/en/contact-fallback").status_code == 404
    assert client.post("/api/contact", json={}).status_code == 404


def test_api_404_is_json(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "not_found"}


def test_robots_and_sitemap(client):
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap: https://awtik.ru/sitemap.xml" in robots.text
    assert "Disallow: /api/" not in robots.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "https://awtik.ru/en/" in sitemap.text
    assert "<lastmod>" in sitemap.text
    assert sitemap.headers["content-type"].startswith("application/xml")


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "nonce-" in response.headers["Content-Security-Policy"]


def test_static_font_cache_header(client):
    response = client.get("/static/fonts/manrope-latin.woff2")
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("public")


def test_css_and_js_are_revalidated(client):
    for path in ("/static/css/main.css", "/static/js/main.js"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-cache"


def test_html_is_revalidated(client):
    response = client.get("/")
    assert response.headers["Cache-Control"] == "no-cache"


def test_rate_limit_applies_to_page_requests(make_client):
    client = make_client(RATE_LIMIT_REQUESTS="1", RATE_LIMIT_WINDOW="600")
    first = client.get("/")
    second = client.get("/")
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "600"
    assert second.text == "Too many requests"


def test_rate_limit_response_keeps_security_headers(make_client):
    client = make_client(RATE_LIMIT_REQUESTS="1")
    client.get("/")
    response = client.get("/")
    assert response.status_code == 429
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "nonce-" in response.headers["Content-Security-Policy"]


def test_healthz_is_not_rate_limited(make_client):
    client = make_client(RATE_LIMIT_REQUESTS="1")
    assert client.get("/").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert client.get("/healthz").status_code == 200


def test_trust_proxy_uses_forwarded_ip(make_client):
    client = make_client(TRUST_PROXY_HEADERS="true", RATE_LIMIT_REQUESTS="1")
    a = client.get("/", headers={"X-Forwarded-For": "10.0.0.1"})
    b = client.get("/", headers={"X-Forwarded-For": "10.0.0.1"})
    c = client.get("/", headers={"X-Forwarded-For": "10.0.0.2"})
    assert a.status_code == 200
    assert b.status_code == 429
    assert c.status_code == 200


def test_i18n_keys_match():
    from collections.abc import Mapping

    from app.i18n import CONTENT

    def keys(value, prefix=""):
        found = set()
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(item, Mapping):
                found |= keys(item, path)
            else:
                found.add(path)
        return found

    assert keys(CONTENT["ru"]) == keys(CONTENT["en"])
