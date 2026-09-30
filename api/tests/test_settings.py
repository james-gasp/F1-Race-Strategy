"""Unit tests for env-driven API settings (no network)."""

from __future__ import annotations

from api.settings import DEFAULT_ALLOWED_ORIGINS, parse_allowed_origins


def test_unset_or_blank_falls_back_to_local_dev_origin():
    assert parse_allowed_origins(None) == DEFAULT_ALLOWED_ORIGINS
    assert parse_allowed_origins("") == DEFAULT_ALLOWED_ORIGINS
    assert parse_allowed_origins(" , ") == DEFAULT_ALLOWED_ORIGINS


def test_splits_trims_and_strips_trailing_slashes():
    raw = " https://f1.example.app/ ,https://preview.example.app,, "
    assert parse_allowed_origins(raw) == ["https://f1.example.app", "https://preview.example.app"]
