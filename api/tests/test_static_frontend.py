"""Serving the built frontend from the API (single-URL deploys). No network:
only /health and static files are requested."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

import api.main
import api.settings


@pytest.fixture
def client_with_frontend(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>F1</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(tmp_path))
    importlib.reload(api.settings)
    yield TestClient(importlib.reload(api.main).app)
    monkeypatch.delenv("FRONTEND_DIST_DIR")
    importlib.reload(api.settings)
    importlib.reload(api.main)


def test_site_is_served_at_root_alongside_the_api(client_with_frontend):
    index = client_with_frontend.get("/")
    assert index.status_code == 200
    assert "<title>F1</title>" in index.text
    assert client_with_frontend.get("/assets/app.js").status_code == 200
    # API routes are registered before the static mount, so they still win.
    assert client_with_frontend.get("/health").json() == {"status": "ok"}


def test_api_only_when_no_frontend_is_configured(monkeypatch):
    monkeypatch.delenv("FRONTEND_DIST_DIR", raising=False)
    importlib.reload(api.settings)
    client = TestClient(importlib.reload(api.main).app)
    assert client.get("/").status_code == 404
    assert client.get("/health").status_code == 200
