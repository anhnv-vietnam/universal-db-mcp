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

## Containerised usage

Container images are provided for both local development and production-style deployments. The default image exposes
the HTTP transport on port `8000` and SSE on `8001`.

### Build & run locally

```bash
docker compose --profile dev up --build server
```

This profile mounts the local `config/` directory so you can iterate on configuration without rebuilding the image. You
can override the exposed ports via `HTTP_PORT`/`SSE_PORT` environment variables.

### Run tests inside a container

```bash
docker compose --profile test run --rm tests
```

The `tests` profile installs the development dependencies (`.[dev]`) and executes the pytest suite in an isolated
environment.

### Production deployment

Build and push the runtime image once:

```bash
docker build -t universal-db-mcp:latest .
```

Run the production profile which reuses the published image and keeps the container alive across restarts:

```bash
docker compose --profile prod up -d server-prod
```

Custom configuration can be supplied by mounting a file or overriding the `UNIVERSAL_DB_MCP_CONFIG` environment
variable.

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
