"""engine.settings reads env vars at import time, so each case re-imports it
with a patched environment."""

from __future__ import annotations

import importlib
from pathlib import Path

import engine.settings


def _reload(monkeypatch, **env):
    for key in ("F1_CACHE_DIR", "F1_MAX_CACHED_RACES"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(engine.settings)


def test_defaults_keep_caches_in_the_repo(monkeypatch):
    s = _reload(monkeypatch)
    repo = Path(engine.settings.__file__).resolve().parents[1]
    assert s.FASTF1_CACHE_DIR == repo / ".fastf1_cache"
    assert s.CIRCUIT_CACHE_DIR == repo / ".circuit_cache"
    assert s.MAX_CACHED_RACES == 16


def test_cache_root_and_race_limit_come_from_env(monkeypatch, tmp_path):
    s = _reload(monkeypatch, F1_CACHE_DIR=str(tmp_path), F1_MAX_CACHED_RACES="0")
    assert s.FASTF1_CACHE_DIR == tmp_path / "fastf1"
    assert s.CIRCUIT_CACHE_DIR == tmp_path / "circuits"
    assert s.MAX_CACHED_RACES == 1  # clamped: lru_cache(maxsize=0) would disable caching


def teardown_module():
    importlib.reload(engine.settings)
