"""Tool registration for the Universal DB MCP server."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, Mapping, Optional

from fastmcp.server import FastMCP
from fastmcp.server.dependencies import get_context

from .config import ToolConfig
from .database import DatabaseError, DatabaseManager, QueryResult

logger = logging.getLogger(__name__)


def format_query_result(result: QueryResult, output_format: str) -> Any:
    """Format query results into the requested representation."""

    fmt = output_format.lower()
    if fmt == "json":
        return {
            "format": "json",
            "columns": result.columns,
            "row_count": result.rowcount,
            "rows": result.rows,
        }
    if fmt == "csv":
        buffer = io.StringIO()
        if result.columns:
            writer = csv.DictWriter(buffer, fieldnames=result.columns)
            writer.writeheader()
            writer.writerows(result.rows)
        return buffer.getvalue()
    raise ValueError(f"Unsupported output format '{output_format}'. Available formats: json, csv")


class SQLExecutionTool:
    """Register an SQL execution tool on a :class:`FastMCP` server."""

    def __init__(self, config: ToolConfig, manager: DatabaseManager) -> None:
        self.config = config
        self.manager = manager

    def register(self, server: FastMCP) -> None:
        """Register the tool with the provided server instance."""

        @server.tool(
            name=self.config.name,
            title=self.config.title,
            description=self.config.description,
            meta=self.config.metadata or None,
        )
        async def execute_sql(  # type: ignore[unused-variable]
            query: Optional[str] = None,
            template: Optional[str] = None,
            parameters: Optional[Mapping[str, Any]] = None,
            database: Optional[str] = None,
            output_format: Optional[str] = None,
            async_execution: bool = True,
        ) -> Dict[str, Any] | str:
            """Execute a SQL query or template against one of the configured databases."""

            db_name = (database or self.config.database).strip()
            if self.config.supported_databases and db_name not in self.config.supported_databases:
                raise ValueError(
                    f"Database '{db_name}' is not allowed for tool '{self.config.name}'."
                )

            chosen_format = (output_format or self.config.default_output_format).lower()
            if chosen_format not in self.config.output_formats:
                raise ValueError(
                    f"Unsupported output format '{output_format}'. Available formats: {self.config.output_formats}"
                )

            if query and template:
                raise ValueError("Provide either a raw query or a template, not both")

            chosen_template: Optional[str]

            if query:
                if not self.config.allow_arbitrary_queries:
                    raise ValueError("Raw SQL queries are disabled for this tool")
                sql = query.strip()
                chosen_template = None
            else:
                chosen_template = (template.strip() if template else None) or self.config.default_template
                if chosen_template:
                    sql = self._resolve_template(db_name, chosen_template)
                elif self.config.default_query:
                    sql = self.config.default_query
                else:
                    raise ValueError("Either 'query' or 'template' must be supplied")

            params: Dict[str, Any] = dict(self.config.default_parameters)
            if parameters:
                params.update(dict(parameters))

            try:
                context = get_context()
            except RuntimeError:
                context = None

            if context is not None:
                await context.info(
                    "Executing SQL query",
                    extra={"database": db_name, "template": chosen_template, "query": sql},
                )

            try:
                if async_execution:
                    result = await self.manager.execute_query_async(db_name, sql, params)
                else:
                    result = self.manager.execute_query(db_name, sql, params)
            except DatabaseError as exc:
                logger.exception("Database execution failed", extra={"database": db_name})
                raise RuntimeError(str(exc)) from exc

            payload = format_query_result(result, chosen_format)
            if chosen_format == "csv":
                return payload

            payload.update({
                "database": db_name,
                "query": sql,
                "template": chosen_template,
                "parameters": params,
            })
            return payload

    def _resolve_template(self, database: str, template_name: str) -> str:
        template_key = template_name.strip()
        if template_key in self.config.query_templates:
            return self.config.query_templates[template_key]

        db = self.manager.get(database)
        if template_key in db.config.query_templates:
            return db.config.query_templates[template_key]

        raise ValueError(
            f"Unknown query template '{template_name}' for database '{database}'"
        )


__all__ = ["SQLExecutionTool", "format_query_result"]
