"""Security helpers for HTTP transports."""
from __future__ import annotations

import base64
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.status import HTTP_401_UNAUTHORIZED


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Simple HTTP Basic authentication middleware."""

    def __init__(self, app, username: str, password: str, realm: str = "Universal DB MCP") -> None:
        super().__init__(app)
        self._username = username
        self._password = password
        self._realm = realm

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        header = request.headers.get("Authorization")
        if not header or not header.lower().startswith("basic "):
            return self._unauthorized()

        token = header.split(" ", 1)[1]
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except Exception:  # pragma: no cover - decoding errors are handled uniformly
            return self._unauthorized()

        if ":" not in decoded:
            return self._unauthorized()

        username, password = decoded.split(":", 1)
        if username != self._username or password != self._password:
            return self._unauthorized()

        return await call_next(request)

    def _unauthorized(self) -> Response:
        return PlainTextResponse(
            "Unauthorized",
            status_code=HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": f'Basic realm="{self._realm}"'},
        )


__all__ = ["BasicAuthMiddleware"]
