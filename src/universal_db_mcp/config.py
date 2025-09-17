"""Configuration models and helpers for the Universal DB MCP server."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib  # type: ignore


ALLOWED_PROTOCOLS = {"stdio", "http", "sse"}

_DB_TYPE_ALIASES: Dict[str, str] = {
    "oracle": "oracle",
    "oracledb": "oracle",
    "oracle-db": "oracle",
    "oracle_db": "oracle",
    "mysql": "mysql",
    "mariadb": "mariadb",
    "maria": "mariadb",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "pgsql": "postgresql",
    "sqlserver": "sqlserver",
    "sql-server": "sqlserver",
    "mssql": "sqlserver",
    "sqlite": "sqlite",  # primarily for local development and testing
}


class PoolConfig(BaseModel):
    """Connection pooling configuration."""

    enabled: bool = False
    size: Optional[int] = Field(default=None, ge=1)
    max_overflow: Optional[int] = Field(default=None, ge=0)
    timeout: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _ensure_parameters_when_enabled(self) -> "PoolConfig":
        if self.enabled and self.size is None:
            # Provide a small but sensible default pool size
            self.size = 5
        return self


class DatabaseConfig(BaseModel):
    """Configuration for a single database backend."""

    name: str
    type: str
    connection_url: str
    pool: PoolConfig = Field(default_factory=PoolConfig)
    query_templates: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, value: str) -> str:
        key = value.lower().strip()
        if key not in _DB_TYPE_ALIASES:
            supported = sorted({v for v in _DB_TYPE_ALIASES.values() if v != "sqlite"})
            raise ValueError(
                "Unsupported database type. Expected one of %s, received %s"
                % (", ".join(supported), value)
            )
        return _DB_TYPE_ALIASES[key]

    @field_validator("query_templates")
    @classmethod
    def _strip_templates(cls, value: Dict[str, str]) -> Dict[str, str]:
        return {k: v.strip() for k, v in value.items()}


class ToolConfig(BaseModel):
    """Configuration for a tool exposed via FastMCP."""

    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    database: str
    allow_arbitrary_queries: bool = False
    supported_databases: Optional[List[str]] = None
    output_formats: List[str] = Field(default_factory=lambda: ["json"])
    default_output_format: str = "json"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    query_templates: Dict[str, str] = Field(default_factory=dict)

    @field_validator("output_formats", mode="before")
    @classmethod
    def _deduplicate_formats(cls, value: Iterable[str]) -> List[str]:
        seen: List[str] = []
        for item in value:
            lowered = item.lower()
            if lowered not in seen:
                seen.append(lowered)
        return seen

    @model_validator(mode="after")
    def _validate_default_format(self) -> "ToolConfig":
        if self.default_output_format.lower() not in {fmt.lower() for fmt in self.output_formats}:
            raise ValueError(
                f"default_output_format '{self.default_output_format}' must be one of {self.output_formats}"
            )
        self.default_output_format = self.default_output_format.lower()
        self.output_formats = [fmt.lower() for fmt in self.output_formats]
        return self

    @field_validator("query_templates")
    @classmethod
    def _strip_tool_templates(cls, value: Dict[str, str]) -> Dict[str, str]:
        return {k: v.strip() for k, v in value.items()}


class BasicAuthConfig(BaseModel):
    """Basic authentication settings for HTTP transports."""

    enabled: bool = False
    username_env: Optional[str] = None
    password_env: Optional[str] = None
    realm: str = "Universal DB MCP"

    def resolve_credentials(self) -> Optional[tuple[str, str]]:
        """Resolve credentials from the environment if authentication is enabled."""

        if not self.enabled:
            return None

        if not self.username_env or not self.password_env:
            raise ValueError("Both username_env and password_env must be provided when basic auth is enabled")

        username = os.getenv(self.username_env)
        password = os.getenv(self.password_env)
        if username is None or password is None:
            raise ValueError(
                f"Environment variables {self.username_env!r} and {self.password_env!r} must be set when basic auth is enabled"
            )
        return username, password


class HTTPConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    message_path: str = "/messages/"
    streamable_http_path: str = "/mcp"
    stateless_http: bool = False
    basic_auth: BasicAuthConfig = Field(default_factory=BasicAuthConfig)


class SSEConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8001
    path: str = "/sse"


class CoreServerConfig(BaseModel):
    name: str
    version: Optional[str] = None
    instructions: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    protocols: List[str] = Field(default_factory=lambda: ["stdio"])

    @field_validator("protocols")
    @classmethod
    def _validate_protocols(cls, value: Iterable[str]) -> List[str]:
        unique: List[str] = []
        for protocol in value:
            lowered = protocol.lower()
            if lowered not in ALLOWED_PROTOCOLS:
                raise ValueError(f"Unsupported protocol '{protocol}'. Allowed protocols: {sorted(ALLOWED_PROTOCOLS)}")
            if lowered not in unique:
                unique.append(lowered)
        if not unique:
            raise ValueError("At least one protocol must be enabled")
        return unique


class ServerConfig(BaseModel):
    """Top level configuration object."""

    server: CoreServerConfig
    http: HTTPConfig = Field(default_factory=HTTPConfig)
    sse: SSEConfig = Field(default_factory=SSEConfig)
    databases: List[DatabaseConfig]
    tools: List[ToolConfig]

    @model_validator(mode="after")
    def _validate_references(self) -> "ServerConfig":
        db_names = {db.name for db in self.databases}
        if len(db_names) != len(self.databases):
            raise ValueError("Database names must be unique")

        tool_names = {tool.name for tool in self.tools}
        if len(tool_names) != len(self.tools):
            raise ValueError("Tool names must be unique")

        for tool in self.tools:
            if tool.database not in db_names:
                raise ValueError(f"Tool '{tool.name}' references unknown database '{tool.database}'")
            if tool.supported_databases:
                missing = set(tool.supported_databases) - db_names
                if missing:
                    raise ValueError(
                        f"Tool '{tool.name}' references unsupported databases: {', '.join(sorted(missing))}"
                    )
        return self

    @property
    def protocols(self) -> List[str]:
        return self.server.protocols

    def get_database(self, name: str) -> DatabaseConfig:
        for db in self.databases:
            if db.name == name:
                return db
        raise KeyError(name)


def _resolve_env_values(value: Any) -> Any:
    """Recursively expand environment variables in the loaded configuration."""

    if isinstance(value, str):
        if value.startswith("env:"):
            env_name = value.split(":", 1)[1]
            return os.getenv(env_name, "")
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_resolve_env_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_env_values(item) for key, item in value.items()}
    return value


def _read_file(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if path.suffix.lower() in {".toml", ".tml"}:
        return tomllib.loads(text)
    raise ValueError(f"Unsupported configuration format for '{path}'")


def load_config(config_path: Optional[os.PathLike[str] | str] = None) -> ServerConfig:
    """Load configuration from disk.

    The lookup order is:

    1. The explicit ``config_path`` argument when provided.
    2. The ``UNIVERSAL_DB_MCP_CONFIG`` environment variable.
    3. The ``MCP_CONFIG_FILE`` environment variable.
    4. The bundled ``config/default.yaml`` file.
    """

    candidate_paths: List[Path] = []
    if config_path:
        candidate_paths.append(Path(config_path))
    env_path = os.getenv("UNIVERSAL_DB_MCP_CONFIG") or os.getenv("MCP_CONFIG_FILE")
    if env_path:
        candidate_paths.append(Path(env_path))
    candidate_paths.append(Path(__file__).resolve().parent.parent / "config" / "default.yaml")

    for path in candidate_paths:
        if path.exists():
            raw = _read_file(path)
            resolved = _resolve_env_values(raw)
            try:
                return ServerConfig.model_validate(resolved)
            except ValidationError as exc:  # pragma: no cover - helpful error message
                raise ValueError(f"Invalid configuration in '{path}': {exc}") from exc
    raise FileNotFoundError("No configuration file found. Provide a path or set UNIVERSAL_DB_MCP_CONFIG")


__all__ = [
    "ALLOWED_PROTOCOLS",
    "ServerConfig",
    "DatabaseConfig",
    "ToolConfig",
    "HTTPConfig",
    "SSEConfig",
    "BasicAuthConfig",
    "PoolConfig",
    "load_config",
]
