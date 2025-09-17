"""Command line entry point for running the Universal DB MCP server."""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Iterable, Optional

from .config import ALLOWED_PROTOCOLS, load_config
from .runner import run_server

logger = logging.getLogger(__name__)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Universal DB MCP server")
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Path to a configuration file (YAML/JSON/TOML)",
    )
    parser.add_argument(
        "--protocols",
        nargs="+",
        choices=sorted(ALLOWED_PROTOCOLS),
        help="Override the set of protocols defined in the configuration",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level for the runner (default: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    config = load_config(args.config_path)
    protocols = [p.lower() for p in args.protocols] if args.protocols else None

    try:
        asyncio.run(run_server(config, protocols=protocols))
    except KeyboardInterrupt:  # pragma: no cover - manual interrupt
        logger.info("Server interrupted by user")


if __name__ == "__main__":  # pragma: no cover
    main()
