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
    F1_RACE_DATA_DIR       Optional folder of pre-downloaded races, laid out
                           like FastF1's cache (`<year>/<date>_<Event_Name>/`).
                           May be read-only, e.g. a Cloud Storage bucket
                           mount. F1's live-timing server blocks cloud hosts
                           such as Google Cloud, so a deployed server can only
                           load races that were downloaded elsewhere first.
    F1_DOWNLOADED_RACES_ONLY
                           "true" = only offer races whose data is already
                           downloaded (in the cache or F1_RACE_DATA_DIR).
                           Set it wherever live timing is unreachable.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_cache_root = os.environ.get("F1_CACHE_DIR")

FASTF1_CACHE_DIR = Path(_cache_root) / "fastf1" if _cache_root else _REPO_ROOT / ".fastf1_cache"
CIRCUIT_CACHE_DIR = Path(_cache_root) / "circuits" if _cache_root else _REPO_ROOT / ".circuit_cache"

MAX_CACHED_RACES = max(1, int(os.environ.get("F1_MAX_CACHED_RACES", "16")))

_race_data = os.environ.get("F1_RACE_DATA_DIR")
RACE_DATA_DIR = Path(_race_data) if _race_data else None

DOWNLOADED_RACES_ONLY = os.environ.get("F1_DOWNLOADED_RACES_ONLY", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
