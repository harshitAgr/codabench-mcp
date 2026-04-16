"""Submission tools: list, get, logs, submit (3-step), poll."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CodabenchClient
from ..pagination import paginate


def register(mcp: FastMCP, client: CodabenchClient) -> None:

    @mcp.tool(description="List the authenticated user's submissions, newest first.")
    async def list_my_submissions(
        phase: int | None = None,
        page_size: int = 20,
        max_pages: int = 10,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"mine": "true", "page_size": page_size}
        if phase is not None:
            params["phase"] = str(phase)
        return await paginate(
            client, "/api/submissions/", params=params, max_pages=max_pages
        )

    @mcp.tool(description="Get full details of a submission including scores.")
    async def get_submission(submission_id: int) -> dict[str, Any]:
        return await client.get(f"/api/submissions/{submission_id}/")

    @mcp.tool(description="Get stdout/stderr/ingestion logs for a submission.")
    async def get_submission_logs(submission_id: int) -> dict[str, Any]:
        return await client.get(f"/api/submissions/{submission_id}/get_details/")
