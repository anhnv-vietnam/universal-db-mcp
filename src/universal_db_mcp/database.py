"""Database abstractions for the Universal DB MCP server."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ResourceClosedError, SQLAlchemyError
from sqlalchemy.pool import NullPool

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueryResult:
    """Container for SQL query results."""

    rows: list[dict[str, Any]]
    columns: list[str]
    rowcount: int


class DatabaseError(RuntimeError):
    """Base class for database-related errors."""


class DatabaseNotFoundError(DatabaseError):
    """Raised when a requested database is not configured."""


class SQLAlchemyDatabase:
    """Wrapper around :mod:`sqlalchemy` for executing queries."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine: Engine = self._create_engine(config)

    def _create_engine(self, config: DatabaseConfig) -> Engine:
        engine_kwargs: Dict[str, Any] = {"future": True, "pool_pre_ping": True}
        if config.pool.enabled:
            if config.pool.size is not None:
                engine_kwargs["pool_size"] = config.pool.size
            if config.pool.max_overflow is not None:
                engine_kwargs["max_overflow"] = config.pool.max_overflow
            if config.pool.timeout is not None:
                engine_kwargs["pool_timeout"] = config.pool.timeout
        else:
            engine_kwargs["poolclass"] = NullPool
        logger.debug("Creating SQLAlchemy engine", extra={"database": config.name, "url": config.connection_url})
        return create_engine(config.connection_url, **engine_kwargs)

    def dispose(self) -> None:
        """Dispose of the underlying SQLAlchemy engine."""

        self.engine.dispose()

    def execute_query(self, query: str, parameters: Optional[Mapping[str, Any]] = None) -> QueryResult:
        """Execute a SQL query synchronously."""

        params = dict(parameters or {})
        logger.debug(
            "Executing SQL query",
            extra={"database": self.config.name, "query": query, "parameters": params},
        )
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params)
                rows: list[dict[str, Any]]
                columns: list[str]
                try:
                    rows = [dict(row) for row in result.mappings()]
                    columns = list(result.keys())
                except ResourceClosedError:
                    rows = []
                    columns = []
                rowcount = result.rowcount if result.rowcount != -1 else len(rows)
                connection.commit()
                return QueryResult(rows=rows, columns=columns, rowcount=rowcount)
        except SQLAlchemyError as exc:  # pragma: no cover - tested indirectly via manager
            logger.exception("Database query failed", extra={"database": self.config.name})
            raise DatabaseError(str(exc)) from exc

    async def execute_query_async(
        self, query: str, parameters: Optional[Mapping[str, Any]] = None
    ) -> QueryResult:
        """Execute a SQL query asynchronously using a background thread."""

        return await asyncio.to_thread(self.execute_query, query, parameters)


class DatabaseManager:
    """Manage multiple SQLAlchemy-backed database connections."""

    def __init__(self, configs: Iterable[DatabaseConfig]):
        self._databases: Dict[str, SQLAlchemyDatabase] = {
            config.name: SQLAlchemyDatabase(config) for config in configs
        }

    def list_databases(self) -> list[str]:
        return sorted(self._databases)

    def get(self, name: str) -> SQLAlchemyDatabase:
        try:
            return self._databases[name]
        except KeyError as exc:  # pragma: no cover - trivial guard
            raise DatabaseNotFoundError(f"Database '{name}' is not configured") from exc

    def execute_query(
        self, name: str, query: str, parameters: Optional[Mapping[str, Any]] = None
    ) -> QueryResult:
        database = self.get(name)
        return database.execute_query(query, parameters)

    async def execute_query_async(
        self, name: str, query: str, parameters: Optional[Mapping[str, Any]] = None
    ) -> QueryResult:
        database = self.get(name)
        return await database.execute_query_async(query, parameters)

    def dispose(self) -> None:
        for database in self._databases.values():
            database.dispose()


__all__ = [
    "DatabaseError",
    "DatabaseManager",
    "DatabaseNotFoundError",
    "QueryResult",
    "SQLAlchemyDatabase",
]
