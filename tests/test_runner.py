from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from universal_db_mcp.runner import run_server


class DummyServer(SimpleNamespace):
    def __init__(self):
        super().__init__(
            run_stdio_async=AsyncMock(return_value=None),
            run_http_async=AsyncMock(return_value=None),
            run_sse_async=AsyncMock(return_value=None),
            database_manager=SimpleNamespace(dispose=lambda: None),
        )


@pytest.mark.asyncio
async def test_run_server_invokes_protocols(monkeypatch, server_config):
    server = DummyServer()
    middleware = ["middleware"]

    monkeypatch.setattr("universal_db_mcp.runner.build_server", lambda config: server)
    monkeypatch.setattr("universal_db_mcp.runner.build_http_middleware", lambda config: middleware)

    await run_server(server_config, protocols=["stdio", "http", "sse"])

    server.run_stdio_async.assert_awaited_once()
    server.run_http_async.assert_awaited_once()
    server.run_sse_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_server_validates_protocols(monkeypatch, server_config):
    server = DummyServer()
    monkeypatch.setattr("universal_db_mcp.runner.build_server", lambda config: server)
    monkeypatch.setattr("universal_db_mcp.runner.build_http_middleware", lambda config: [])

    with pytest.raises(ValueError):
        await run_server(server_config, protocols=["invalid"])
