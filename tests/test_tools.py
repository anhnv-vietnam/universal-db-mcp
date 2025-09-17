from __future__ import annotations

import asyncio
import copy

import pytest

from universal_db_mcp.config import ServerConfig
from universal_db_mcp.server import build_server


async def invoke_tool(server, name: str, payload):
    tool = await server.get_tool(name)
    result = await tool.run(payload)
    return result.structured_content


def prepare_database(server) -> None:
    manager = getattr(server, "database_manager")
    manager.execute_query(
        "analytics",
        "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)",
    )
    manager.execute_query("analytics", "DELETE FROM items")
    manager.execute_query("analytics", "INSERT INTO items (name) VALUES (:name)", {"name": "apple"})


def dispose_server(server) -> None:
    manager = getattr(server, "database_manager")
    manager.dispose()


def test_tool_executes_template(server_config: ServerConfig):
    server = build_server(server_config)
    prepare_database(server)

    async def run():
        return await invoke_tool(
            server,
            "run_sql",
            {"template": "top_items", "parameters": {"minimum_id": 1}},
        )

    result = asyncio.run(run())
    assert result["row_count"] == 1
    assert result["rows"][0]["name"] == "apple"
    dispose_server(server)


def test_tool_supports_csv_output(server_config: ServerConfig):
    server = build_server(server_config)
    prepare_database(server)

    async def run():
        return await invoke_tool(
            server,
            "run_sql",
            {"template": "top_items", "parameters": {"minimum_id": 1}, "output_format": "csv"},
        )

    result = asyncio.run(run())
    assert result["format"] == "csv"
    assert "csv" in result
    assert "apple" in result["csv"]
    dispose_server(server)


def test_raw_queries_can_be_disabled(config_dict):
    config_data = copy.deepcopy(config_dict)
    config_data["tools"][0]["allow_arbitrary_queries"] = False
    config = ServerConfig.model_validate(config_data)
    server = build_server(config)
    prepare_database(server)

    async def run():
        return await invoke_tool(
            server,
            "run_sql",
            {"query": "SELECT * FROM items"},
        )

    with pytest.raises(ValueError):
        asyncio.run(run())
    dispose_server(server)


def test_unknown_template_raises(server_config: ServerConfig):
    server = build_server(server_config)
    prepare_database(server)

    async def run():
        return await invoke_tool(
            server,
            "run_sql",
            {"template": "does_not_exist"},
        )

    with pytest.raises(ValueError):
        asyncio.run(run())
    dispose_server(server)
