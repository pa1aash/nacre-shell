"""Shared helpers for the Pourbaix and window tests (offline: the cache only)."""
import socket
from pathlib import Path

import pytest

from nacre.pourbaix import config
from nacre.pourbaix.paths import CONFIG_DIR, REPO

MOCK = CONFIG_DIR / "mock.yaml"
SMOKE = CONFIG_DIR / "smoke.yaml"


@pytest.fixture
def offline(monkeypatch):
    """Fail any attempt to open a network connection."""
    def refuse(*args, **kwargs):
        raise RuntimeError("network access attempted in an offline test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    yield


def mock_config():
    return config.load(MOCK, allow_mock=True)


def env_key():
    """The MP key from .env, or None. Never printed: callers compare, they do not show it."""
    env = REPO / ".env"
    if not Path(env).is_file():
        return None
    for line in Path(env).read_text(encoding="utf-8").splitlines():
        if line.startswith("MP_API_KEY="):
            return line.split("=", 1)[1].strip() or None
    return None
