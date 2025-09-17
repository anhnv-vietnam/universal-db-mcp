from __future__ import annotations

import asyncio

import pytest

from universal_db_mcp.config import DatabaseConfig
from universal_db_mcp.database import DatabaseManager, QueryResult
from universal_db_mcp.tools import format_query_result


@pytest.fixture
def sqlite_config(tmp_path):
    db_path = tmp_path / "data.db"
    return DatabaseConfig(
        name="analytics",
        type="postgresql",
        connection_url=f"sqlite+pysqlite:///{db_path}",
        query_templates={"select_all": "SELECT * FROM items ORDER BY id"},
        pool={"enabled": True, "size": 1, "max_overflow": 1, "timeout": 5},
    )


@pytest.fixture
def manager(sqlite_config: DatabaseConfig) -> DatabaseManager:
    return DatabaseManager([sqlite_config])


def initialise_schema(manager: DatabaseManager):
    manager.execute_query(
        "analytics",
        "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)",
    )
    manager.execute_query(
        "analytics", "DELETE FROM items",
    )
    manager.execute_query(
        "analytics",
        "INSERT INTO items (name) VALUES (:name)",
        {"name": "apple"},
    )


def test_execute_query_returns_rows(manager: DatabaseManager):
    initialise_schema(manager)
    result = manager.execute_query(
        "analytics", "SELECT id, name FROM items WHERE name=:name", {"name": "apple"}
    )
    assert isinstance(result, QueryResult)
    assert result.rows[0]["name"] == "apple"
    assert result.rowcount == 1


def test_execute_query_async(manager: DatabaseManager):
    initialise_schema(manager)

    async def run():
        return await manager.execute_query_async(
            "analytics", "SELECT count(*) as count FROM items", {}
        )

    result = asyncio.run(run())
    assert result.rows[0]["count"] == 1


def test_parameterised_queries_prevent_injection(manager: DatabaseManager):
    initialise_schema(manager)
    malicious = "banana'); DROP TABLE items; --"
    result = manager.execute_query(
        "analytics",
        "SELECT id FROM items WHERE name=:name",
        {"name": malicious},
    )
    assert result.rowcount == 0
    # table still accessible
    check = manager.execute_query("analytics", "SELECT count(*) as count FROM items")
    assert check.rows[0]["count"] == 1


def test_result_formatting(manager: DatabaseManager):
    initialise_schema(manager)
    result = manager.execute_query("analytics", "SELECT id, name FROM items ORDER BY id")
    json_payload = format_query_result(result, "json")
    assert json_payload["row_count"] == 1
    assert json_payload["rows"][0]["name"] == "apple"

    csv_payload = format_query_result(result, "csv")
    assert "id,name" in csv_payload["csv"]


