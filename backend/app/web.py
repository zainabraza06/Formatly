"""Serving the built page from the API, when there is one to serve.

In development the page is Vite's on :5173 and the API is on :8000, which is
two origins and the reason CORS is configured at all. A deployment does not
have to work that way: if the built frontend is sitting next to the backend,
the API serves it, everything is one origin, and there is no CORS, no second
host to deploy, and no `VITE_API_URL` to get wrong.

Nothing here runs unless the build exists, so development is untouched.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# The API's own routes. Anything under these is never a page.
API_PREFIXES = ("/docos", "/auth", "/paper", "/documents", "/health", "/docs",
                "/redoc", "/openapi.json")


def built_frontend() -> Optional[Path]:
    """Where the built page is, if it has been built.

    `FRONTEND_DIST` names it outright; otherwise the usual place next to the
    backend, which is where the Docker build puts it.
    """
    named = os.environ.get("FRONTEND_DIST")
    candidates = [Path(named)] if named else []
    here = Path(__file__).resolve().parents[2]
    candidates += [here / "frontend" / "dist", here / "backend" / "static"]

    for path in candidates:
        if (path / "index.html").exists():
            return path
    return None


def serve_frontend(app: FastAPI) -> Optional[Path]:
    """Mount the built page under the API, if there is one. Returns where from.

    The assets are served with their hashed names, and every other path falls
    back to `index.html` — the router lives in the browser, so a reload of
    /app/editor has to reach the same page rather than a 404.
    """
    dist = built_frontend()
    if dist is None:
        return None

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        # A file that really is there — favicon, a logo, robots.txt.
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")

    return dist
