"""MCP server bootstrap.

Responsibilities:
- Parse environment variables into a frozen Config
- Configure stderr-only logging (stdout is the MCP protocol channel)
- Construct the CodabenchClient
- Register all tool modules on a FastMCP instance
- Run the server over stdio
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from .client import CodabenchClient


DEFAULT_BASE_URL = "https://www.codabench.org"


@dataclass(frozen=True)
class Config:
    token: str
    base_url: str
    allow_write_raw: bool


def build_config() -> Config:
    token = os.environ.get("CODABENCH_API_TOKEN", "").strip()
    if not token:
        print(
            "ERROR: CODABENCH_API_TOKEN not set. "
            "See README > Authentication for how to obtain a token.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    base_url = os.environ.get("CODABENCH_BASE_URL", DEFAULT_BASE_URL).strip()
    allow_write_raw = os.environ.get("CODABENCH_ALLOW_WRITE_RAW", "0").strip() == "1"
    return Config(token=token, base_url=base_url, allow_write_raw=allow_write_raw)


def configure_logging() -> None:
    """Attach a single stderr handler to the `codabench_mcp` logger.

    stdout is the MCP protocol channel — nothing may be written there.
    """
    logger = logging.getLogger("codabench_mcp")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def build_server(config: Config, client: CodabenchClient) -> FastMCP:
    """Create the FastMCP instance and register all tool modules."""
    from .tools import competitions, data, leaderboards, raw, submissions

    mcp = FastMCP("codabench-mcp")
    competitions.register(mcp, client)
    leaderboards.register(mcp, client)
    data.register(mcp, client)
    submissions.register(mcp, client)
    raw.register(mcp, client, allow_write=config.allow_write_raw)
    return mcp


def main() -> None:
    """Console-script entry point."""
    configure_logging()
    config = build_config()
    client = CodabenchClient(base_url=config.base_url, token=config.token)
    mcp = build_server(config, client)
    try:
        mcp.run(transport="stdio")
    finally:
        import asyncio

        asyncio.run(client.close())


if __name__ == "__main__":
    main()
