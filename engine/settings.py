"""Deployment knobs, read once from environment variables.

Defaults suit local development (caches inside the repo, generous in-memory
caching). A hosted deployment overrides them, e.g. to put the caches on a
persistent disk and cap memory use on a small server:

    F1_CACHE_DIR           Root folder for on-disk caches. FastF1's HTTP/data
                           cache goes in `<root>/fastf1`, circuit outlines in
                           `<root>/circuits`. Unset = `.fastf1_cache/` and
                           `.circuit_cache/` in the repo, as before.
    F1_MAX_CACHED_RACES    How many races to keep loaded in memory at once.
                           A race with telemetry loaded costs ~150-350 MB, so
                           lower this on small servers. Default 16.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_cache_root = os.environ.get("F1_CACHE_DIR")

FASTF1_CACHE_DIR = Path(_cache_root) / "fastf1" if _cache_root else _REPO_ROOT / ".fastf1_cache"
CIRCUIT_CACHE_DIR = Path(_cache_root) / "circuits" if _cache_root else _REPO_ROOT / ".circuit_cache"

MAX_CACHED_RACES = max(1, int(os.environ.get("F1_MAX_CACHED_RACES", "16")))
