"""Leaderboard + my-profile tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CodabenchClient


def register(mcp: FastMCP, client: CodabenchClient) -> None:

    @mcp.tool(description="Get the leaderboard for a phase.")
    async def get_leaderboard(phase_id: int) -> dict[str, Any]:
        data = await client.get("/api/leaderboards/", params={"phase": str(phase_id)})
        if isinstance(data, list):
            return {"results": data}
        return data

    @mcp.tool(description="Get the authenticated user's Codabench profile.")
    async def get_my_profile() -> dict[str, Any]:
        return await client.get("/api/my_profile/")
