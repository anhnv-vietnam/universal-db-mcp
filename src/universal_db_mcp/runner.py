"""Runtime helpers for launching the MCP server."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine, Iterable, Optional

from fastmcp.server import FastMCP

from .config import ALLOWED_PROTOCOLS, ServerConfig
from .server import build_http_middleware, build_server

logger = logging.getLogger(__name__)


async def run_server(config: ServerConfig, *, protocols: Optional[Iterable[str]] = None) -> None:
    """Create and run a FastMCP server according to the supplied configuration."""

    server = build_server(config)
    middleware = build_http_middleware(config)
    selected_protocols = [p.lower() for p in (protocols or config.protocols)]

    invalid = [p for p in selected_protocols if p not in ALLOWED_PROTOCOLS]
    if invalid:
        raise ValueError(f"Unsupported protocols requested: {', '.join(invalid)}")

    logger.info("Starting MCP server", extra={"protocols": selected_protocols})

    coroutines = _build_protocol_coroutines(server, config, middleware, selected_protocols)
    manager = getattr(server, "database_manager", None)
    try:
        if coroutines:
            await asyncio.gather(*coroutines)
    finally:
        if manager is not None:
            manager.dispose()


def _build_protocol_coroutines(
    server: FastMCP,
    config: ServerConfig,
    middleware,
    protocols: Iterable[str],
) -> list[Coroutine[Any, Any, None]]:
    tasks: list[Coroutine[Any, Any, None]] = []
    for protocol in protocols:
        if protocol == "stdio":
            tasks.append(server.run_stdio_async(show_banner=False))
        elif protocol == "http":
            tasks.append(
                server.run_http_async(
                    show_banner=False,
                    transport="http",
                    host=config.http.host,
                    port=config.http.port,
                    path=config.http.message_path,
                    middleware=middleware,
                    stateless_http=config.http.stateless_http,
                )
            )
        elif protocol == "sse":
            tasks.append(
                server.run_sse_async(
                    host=config.sse.host,
                    port=config.sse.port,
                    path=config.sse.path,
                )
            )
        else:  # pragma: no cover - validated earlier
            raise ValueError(f"Unsupported protocol '{protocol}'")
    return tasks


__all__ = ["run_server"]
