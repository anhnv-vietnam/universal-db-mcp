# Universal DB MCP Server

Universal DB MCP is a highly configurable [Model Context Protocol](https://modelcontextprotocol.io/) server built with
[FastMCP](https://gofastmcp.com/) that exposes SQL execution capabilities across heterogeneous database engines. The
server is designed for flexibility and security—configuration is data-driven, protocols can be toggled on or off, and
database connections are managed through a shared abstraction layer.

## Features

* **Multiple transports** – run the server over stdio, HTTP, and Server-Sent Events (SSE).
* **Database agnostic** – execute parameterised SQL against OracleDB, MySQL, MariaDB, PostgreSQL, SQL Server, or any
  SQLAlchemy compatible backend. SQLite is supported for local development and automated tests.
* **Rich configuration** – control tool metadata, supported databases, query templates, authentication, and protocol
  behaviour through YAML/JSON/TOML configuration files or environment variables.
* **Async aware** – synchronous and asynchronous query execution helpers are available.
* **Optional extras** – connection pooling, result formatting (JSON or CSV), and optional HTTP basic authentication are
  included out of the box.

## Getting started

1. **Install dependencies**

   ```bash
   pip install -e .[dev]
   ```

2. **Configure the server**

   Edit `config/default.yaml` or provide your own configuration file and set `UNIVERSAL_DB_MCP_CONFIG=/path/to/config.yaml`.
   The configuration schema is documented inline within the default file.

3. **Run the server**

   ```bash
   python -m universal_db_mcp.main --config config/default.yaml --protocols stdio http
   ```

   The CLI flags can override the protocols declared in the configuration file when you need to experiment locally.

## Testing

```bash
pytest
```

Unit and integration tests cover configuration parsing, database execution helpers, transport orchestration, and security
behaviour for parameterised SQL statements.

## Project layout

```
.
├── config/              # Example configuration files
├── src/universal_db_mcp # Server implementation
└── tests/               # Automated tests
```

## Database drivers

The project relies on SQLAlchemy for database connectivity. Depending on the backend you want to access you will need the
appropriate DBAPI driver installed (e.g. `cx_Oracle` for OracleDB, `psycopg[binary]` for PostgreSQL, `pymssql` or
`pytds` for SQL Server). The built-in integration tests use SQLite so no additional dependencies are required for running
`pytest` in this repository.
