# Universal DB MCP Server

Universal DB MCP is a highly configurable [Model Context Protocol](https://modelcontextprotocol.io/) server built on
[FastMCP](https://gofastmcp.com/). It exposes SQL execution tools backed by SQLAlchemy so that assistants can query
heterogeneous database engines (Oracle, MySQL, MariaDB, PostgreSQL, SQL Server, SQLite, or anything with a DBAPI driver)
through a single, policy-aware interface. Transport layers are opt-in per deployment, configuration is data-driven, and
security guardrails such as parameterised templates and optional HTTP Basic Auth are baked in.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export UNIVERSAL_DB_MCP_CONFIG=config/default.yaml
python -m universal_db_mcp.main --protocols stdio http sse
```

## Installation

- Create a virtual environment (`python3 -m venv .venv && source .venv/bin/activate`).
- Install the runtime or development dependencies:
  - `pip install .` for the lean runtime footprint.
  - `pip install -e .[dev]` when you want editable installs and the pytest tooling.
- Optional DB drivers such as `cx-Oracle`, `mysqlclient`, `pymysql`, `mariadb`, and `psycopg2-binary` are included in the
  base dependency set; make sure system libraries required by each driver are present (see *Requirements*).

## Requirements

- Python **3.11+** (matches `pyproject.toml` and the Docker base image).
- SQLAlchemy-compatible database drivers for every backend you plan to reach. The repository ships example configs for
  SQLite (default) and MySQL (via Docker Compose).
- System libraries for native drivers. The Docker image installs `build-essential`, `pkg-config`, `libaio1t64`,
  `libmariadb-dev`, `libpq-dev`, and `sqlite3`. Mirror those packages locally if you compile wheels from source.
- A MCP-compatible client (e.g. Claude Desktop, Cursor, or any FastMCP consumer) when connecting over stdio/HTTP/SSE.

## Configuration

Configuration is loaded in this order: explicit `--config` CLI flag, `UNIVERSAL_DB_MCP_CONFIG`, `MCP_CONFIG_FILE`, then
`config/default.yaml`. YAML/JSON/TOML are supported, with `${VAR}` and `${VAR:-default}` substitution plus `env:FOO`
shortcuts. See `config/default.yaml` and `config/default.test.yaml` for reference schemas.

| Name | Required | Default | Description |
| ---- | :------: | ------- | ----------- |
| `UNIVERSAL_DB_MCP_CONFIG` | | `config/default.yaml` | Path to the primary server configuration file. |
| `MCP_CONFIG_FILE` | | – | Fallback config path if the primary variable is unset. |
| `HTTP_PORT` | | `8000` | Overrides the HTTP listener port exposed by Docker Compose. |
| `SSE_PORT` | | `8001` | Overrides the SSE listener port exposed by Docker Compose. |
| `UNIVERSAL_DB_MCP_HTTP_USER` | | – | Username for HTTP Basic Auth when enabled in config. |
| `UNIVERSAL_DB_MCP_HTTP_PASSWORD` | | – | Password for HTTP Basic Auth when enabled in config. |
| `UNIVERSAL_DB_MCP_DB_ANALYTICS` | | SQLite file URL | Connection URL for the default analytics database. |
| `UNIVERSAL_DB_MCP_DB_TESTING` | | SQLite file URL | Connection URL for the bundled testing database. |

The main configuration blocks are:

- `server`: MCP metadata (name, version, instructions, protocols).
- `http` / `sse`: network bindings, stream endpoints, and Basic Auth options.
- `databases`: named SQLAlchemy URLs, optional pooling, metadata, and shared templates.
- `tools`: FastMCP tool definitions. Each tool can opt into raw SQL, per-database allow-lists, default templates, and
  supported output formats (`json` or `csv`).

Bundled tool definitions (from `config/default.yaml`):

- `run_sql`: Targets the `analytics` database, allows raw SQL, supports JSON/CSV, and defaults to the
  `high_spenders` template with a configurable `minimum_spend` parameter.
- `inspect_testing_records`: Read-only accessor for the SQLite `testing` database. It exposes canned templates such as
  `list_test_records` and `list_test_records_by_category`.
- `test_anhnv176`: Demonstrates a CSV-first workflow by returning the entire `test_records` table from the testing DB.

## Usage

### CLI

```bash
python -m universal_db_mcp.main --help
```

```text
usage: python -m universal_db_mcp.main [-h] [--config CONFIG_PATH]
                                       [--protocols {http,sse,stdio} [{http,sse,stdio} ...]]
                                       [--log-level LOG_LEVEL]

Universal DB MCP server

options:
  -h, --help            show this help message and exit
  --config CONFIG_PATH  Path to a configuration file (YAML/JSON/TOML)
  --protocols {http,sse,stdio} [{http,sse,stdio} ...]
                        Override the set of protocols defined in the
                        configuration
  --log-level LOG_LEVEL
                        Logging level for the runner (default: INFO)
```

### Runtime protocols

- `stdio`: Suitable for MCP-enabled local tooling. Combine with the default instructions block for in-editor workflows.
- `http`: Provides the FastMCP HTTP transport on `http://<host>:<port>/messages/`. Enable `basic_auth` to protect the
  endpoint in shared environments.
- `sse`: Streams events over Server-Sent Events at `/sse`; works with streaming MCP clients.

### Tool invocation

Every tool registered from configuration shares the same signature:

```json
{
  "tool_name": "run_sql",
  "arguments": {
    "template": "high_spenders",
    "parameters": {"minimum_spend": 1000},
    "database": "analytics",
    "output_format": "json",
    "async_execution": true
  }
}
```

- Provide either `template` **or** `query`. If raw SQL is disabled for the tool, only templates are allowed.
- `database` falls back to the default specified in the tool config.
- `output_format` accepts any format declared in `output_formats` (JSON payload with metadata or CSV string).

## Examples

- Seed the bundled SQLite database with predictable data:
  - `sqlite3 config/testing.db < config/testing_seed.sql`
- Run the server against the MySQL test configuration (expects the Compose MySQL service):
  - `python -m universal_db_mcp.main --config config/default.test.yaml --protocols http sse`
- Create custom templates by extending the `query_templates` block under either `databases` or the tool itself.

## Docker

- Build and run the development profile (mounts local configs):
  - `docker compose --profile dev up --build server`
- Execute the pytest suite inside a disposable container:
  - `docker compose --profile test run --rm tests`
- Launch the production profile with detached containers:
  - `docker compose --profile prod up -d server-prod`

The Compose file exposes a MySQL 8.2 service on `localhost:3307` with seed data from `config/mysql/init.sql`. Override
ports using `HTTP_PORT` / `SSE_PORT` and supply alternative configs via `UNIVERSAL_DB_MCP_CONFIG`.

## Kubernetes

Example manifests are located under `k8s/`:

- `k8s/configmap.yaml` – ships the default configuration via a ConfigMap.
- `k8s/deployment.yaml` – references a published container image and mounts the config volume.
- `k8s/service.yaml` – exposes HTTP (8000) and SSE (8001) ports.

Apply them with `kubectl apply -f k8s/`. Update the container image reference and ConfigMap contents before deploying to
production clusters.

## Development

- Clone the repo and follow the installation steps above.
- Keep database fixtures in `config/testing.db` up to date using `config/testing_seed.sql`.
- The package exposes helper functions (`load_config`, `build_server`, `run_server`) via `universal_db_mcp/__init__.py`
  for downstream integration tests.

## Testing & Linting

- Run the pytest suite locally: `pytest`.
- For parity with CI/container builds: `docker compose --profile test run --rm tests`.
- Markdown linting is not yet wired up; run your preferred tooling before committing if desired.

## Troubleshooting

- **Missing database driver**: Install the relevant wheel (e.g. `pip install pymysql`) and ensure system libraries from the
  Dockerfile are present.
- **HTTP 401 responses**: Set `UNIVERSAL_DB_MCP_HTTP_USER` / `UNIVERSAL_DB_MCP_HTTP_PASSWORD` when `basic_auth.enabled`
  is true.
- **Template errors**: Confirm the template name exists under either the tool or its target database configuration.
- **SQLite locking**: When sharing the default SQLite files between host and container, stop the server before running
  destructive migrations.

## Breaking Changes & Migration

- No breaking API changes observed in the current configuration. Review database driver requirements when upgrading and
  update your config files to include any newly required fields.

## Contributing

- Fork the project, create a feature branch, and run `pytest` before opening a pull request.
- Update configuration examples and tests alongside code changes that alter tool signatures or database schemas.

## License

Released under the terms of the [MIT License](LICENSE).
