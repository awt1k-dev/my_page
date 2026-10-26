from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app


def _make_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    # Tests must never read the developer's real .env. Environment overrides
    # below are the only config.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "10000")
    monkeypatch.setenv("RATE_LIMIT_WINDOW", "60")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    with _make_client(monkeypatch) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def make_client(monkeypatch: pytest.MonkeyPatch):
    clients: list[TestClient] = []

    def factory(**env: str) -> TestClient:
        test_client = _make_client(monkeypatch, **env)
        test_client.__enter__()
        clients.append(test_client)
        return test_client

    yield factory

    for test_client in clients:
        test_client.__exit__(None, None, None)
    get_settings.cache_clear()
