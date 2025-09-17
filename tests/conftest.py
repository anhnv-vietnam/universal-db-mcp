from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict

import pytest

from universal_db_mcp.config import ServerConfig


@pytest.fixture
def config_dict(tmp_path: Path) -> Dict[str, Any]:
    db_path = tmp_path / "analytics.db"
    return {
        "server": {
            "name": "Test Server",
            "version": "0.0.1",
            "instructions": "Test instructions",
            "protocols": ["stdio", "http", "sse"],
            "metadata": {"env": "test"},
        },
        "http": {
            "host": "127.0.0.1",
            "port": 8765,
            "message_path": "/messages/",
            "streamable_http_path": "/mcp",
            "stateless_http": False,
        },
        "sse": {
            "host": "127.0.0.1",
            "port": 8766,
            "path": "/sse",
        },
        "databases": [
            {
                "name": "analytics",
                "type": "postgresql",
                "connection_url": f"sqlite+pysqlite:///{db_path}",
                "pool": {
                    "enabled": True,
                    "size": 2,
                    "max_overflow": 1,
                    "timeout": 5,
                },
                "query_templates": {
                    "list_items": "SELECT * FROM items ORDER BY id",
                },
            }
        ],
        "tools": [
            {
                "name": "run_sql",
                "title": "Run SQL",
                "description": "Execute SQL queries",
                "database": "analytics",
                "allow_arbitrary_queries": True,
                "supported_databases": ["analytics"],
                "output_formats": ["json", "csv"],
                "default_output_format": "json",
                "metadata": {"category": "test"},
                "query_templates": {
                    "top_items": "SELECT * FROM items WHERE id >= :minimum_id ORDER BY id",
                },
            }
        ],
    }


@pytest.fixture
def server_config(config_dict: Dict[str, Any]) -> ServerConfig:
    return ServerConfig.model_validate(copy.deepcopy(config_dict))
