"""API-level deployment settings, read from environment variables.

    ALLOWED_ORIGINS   Comma-separated browser origins allowed to call the API
                      (CORS), e.g. "https://my-f1-app.vercel.app". Defaults to
                      the local Vite dev server.
"""

from __future__ import annotations

import os

DEFAULT_ALLOWED_ORIGINS = ["http://localhost:5173"]


def parse_allowed_origins(raw: str | None) -> list[str]:
    """Split a comma-separated origin list, dropping blanks and trailing
    slashes (browsers send the Origin header without one, so
    "https://x.app/" would otherwise never match)."""
    if not raw:
        return list(DEFAULT_ALLOWED_ORIGINS)
    origins = [o.strip().rstrip("/") for o in raw.split(",")]
    return [o for o in origins if o] or list(DEFAULT_ALLOWED_ORIGINS)


ALLOWED_ORIGINS = parse_allowed_origins(os.environ.get("ALLOWED_ORIGINS"))
