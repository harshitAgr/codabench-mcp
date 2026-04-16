"""Generic escape-hatch tool: codabench_request.

Exposes arbitrary REST access. Non-GET methods are blocked unless the
server was started with CODABENCH_ALLOW_WRITE_RAW=1 — this prevents the
agent from issuing accidental destructive writes (DELETE, PATCH, etc.).
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CodabenchClient
from ..errors import CodabenchToolError


_READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def register(mcp: FastMCP, client: CodabenchClient, *, allow_write: bool) -> None:

    @mcp.tool(
        description=(
            "Generic Codabench REST escape hatch. Use when no curated tool "
            "fits. Path must start with '/api/'. By default only GET/HEAD/"
            "OPTIONS are allowed; start the server with "
            "CODABENCH_ALLOW_WRITE_RAW=1 to permit POST/PUT/PATCH/DELETE."
        )
    )
    async def codabench_request(
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: Any = None,
    ) -> dict[str, Any]:
        upper = method.strip().upper()
        if not path.startswith("/api/"):
            raise CodabenchToolError(
                f"path must start with '/api/': got {path!r}"
            )
        if upper not in _READ_METHODS and not allow_write:
            raise CodabenchToolError(
                f"Method {upper} blocked. Set CODABENCH_ALLOW_WRITE_RAW=1 "
                "in the MCP server env to permit non-read methods."
            )

        resp = await client.request(upper, path, params=params, json=body)
        try:
            parsed = resp.json() if resp.content else None
        except ValueError:
            parsed = resp.text
        return {
            "status_code": resp.status_code,
            "body": parsed,
        }
