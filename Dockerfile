# syntax=docker/dockerfile:1
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG INSTALL_DEV=false

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir --upgrade pip \
    && if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir '.[dev]'; \
    else \
        pip install --no-cache-dir .; \
    fi \
    && rm -rf /root/.cache/pip

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

ENV UNIVERSAL_DB_MCP_CONFIG=/app/config/default.yaml

EXPOSE 8000
EXPOSE 8001

ENTRYPOINT ["python", "-m", "universal_db_mcp.main"]
CMD ["--protocols", "http", "sse"]
