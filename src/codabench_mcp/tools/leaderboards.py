"""Leaderboard + my-profile tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CodabenchClient


def register(mcp: FastMCP, client: CodabenchClient) -> None:

    @mcp.tool(description="Get the leaderboard (ranked submissions) for a phase.")
    async def get_leaderboard(phase_id: int) -> dict[str, Any]:
        # The list endpoint /api/leaderboards/?phase=<id> returns [] even when the
        # board is populated. The real data lives on the leaderboard DETAIL, which
        # carries .submissions[] (each with .scores[]). Resolve the phase's
        # leaderboard id from the phase object, then fetch that detail.
        phase = await client.get(f"/api/phases/{phase_id}/")
        leaderboard_id = phase.get("leaderboard")
        if not leaderboard_id:
            return {"submissions": [], "detail": f"phase {phase_id} has no leaderboard"}
        return await client.get(f"/api/leaderboards/{leaderboard_id}/")

    @mcp.tool(description="Get the authenticated user's Codabench profile.")
    async def get_my_profile() -> dict[str, Any]:
        return await client.get("/api/my_profile/")
