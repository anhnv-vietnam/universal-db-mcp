from __future__ import annotations

import copy
from pathlib import Path

import pytest

from universal_db_mcp.config import ALLOWED_PROTOCOLS, ServerConfig, load_config


def write_config(path: Path, data: str) -> Path:
    path.write_text(data)
    return path


def test_load_default_config(tmp_path: Path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
server:
  name: Example
  protocols: [stdio, http]
http:
  host: 0.0.0.0
sse:
  host: 0.0.0.0
  port: 9001
databases:
  - name: analytics
    type: postgresql
    connection_url: sqlite+pysqlite:///./example.db
tools:
  - name: run
    database: analytics
    allow_arbitrary_queries: true
    output_formats: [json]
    default_output_format: json
""",
    )
    config = load_config(config_path)
    assert config.server.name == "Example"
    assert config.protocols == ["stdio", "http"]
    assert config.http.host == "0.0.0.0"
    assert config.sse.port == 9001


def test_environment_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite+pysqlite:///./env.db")
    config_path = write_config(
        tmp_path / "config.yaml",
        """
server:
  name: Env
  protocols: [stdio]
databases:
  - name: main
    type: postgresql
    connection_url: ${TEST_DATABASE_URL}
tools:
  - name: run
    database: main
    allow_arbitrary_queries: true
    output_formats: [json]
    default_output_format: json
""",
    )
    config = load_config(config_path)
    assert config.get_database("main").connection_url.endswith("env.db")


def test_invalid_database_type(tmp_path: Path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
server:
  name: Example
  protocols: [stdio]
databases:
  - name: analytics
    type: invalid
    connection_url: sqlite+pysqlite:///./example.db
tools:
  - name: run
    database: analytics
    allow_arbitrary_queries: true
    output_formats: [json]
    default_output_format: json
""",
    )
    with pytest.raises(ValueError):
        load_config(config_path)


def test_tool_database_validation(config_dict):
    bad_config = copy.deepcopy(config_dict)
    bad_config["tools"][0]["database"] = "unknown"
    with pytest.raises(ValueError):
        ServerConfig.model_validate(bad_config)


def test_protocol_validation(config_dict):
    bad_config = copy.deepcopy(config_dict)
    bad_config["server"]["protocols"] = ["stdio", "invalid"]
    with pytest.raises(ValueError):
        ServerConfig.model_validate(bad_config)


def test_allowed_protocols_constant():
    assert {"stdio", "http", "sse"} == ALLOWED_PROTOCOLS
