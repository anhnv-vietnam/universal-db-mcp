"""Server factory for the Universal DB MCP project."""
from __future__ import annotations

import logging
from typing import List

from fastmcp.server import FastMCP
from starlette.middleware import Middleware

from .config import ServerConfig
from .database import DatabaseManager
from .security import BasicAuthMiddleware
from .tools import SQLExecutionTool

logger = logging.getLogger(__name__)


def build_server(config: ServerConfig) -> FastMCP:
    """Create a configured :class:`FastMCP` server from the supplied configuration."""

    server = FastMCP(
        name=config.server.name,
        instructions=config.server.instructions,
        version=config.server.version,
    )

    manager = DatabaseManager(config.databases)
    setattr(server, "database_manager", manager)  # simple attribute injection for access
    setattr(server, "universal_db_mcp_config", config)

    for tool_config in config.tools:
        SQLExecutionTool(tool_config, manager).register(server)
        logger.debug("Registered tool", extra={"tool": tool_config.name})

    return server


def build_http_middleware(config: ServerConfig) -> List[Middleware]:
    """Construct Starlette middleware definitions for HTTP transports."""

    middleware: List[Middleware] = []
    basic_auth = config.http.basic_auth
    if basic_auth.enabled:
        username, password = basic_auth.resolve_credentials()
        middleware.append(
            Middleware(
                BasicAuthMiddleware,
                username=username,
                password=password,
                realm=basic_auth.realm,
            )
        )
    return middleware


__all__ = ["build_http_middleware", "build_server"]
