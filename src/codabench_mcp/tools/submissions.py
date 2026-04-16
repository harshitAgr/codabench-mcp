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
        return await paginate(client, "/api/submissions/", params=params, max_pages=max_pages)

    @mcp.tool(description="Get full details of a submission including scores.")
    async def get_submission(submission_id: int) -> dict[str, Any]:
        return await client.get(f"/api/submissions/{submission_id}/")

    @mcp.tool(description="Get stdout/stderr/ingestion logs for a submission.")
    async def get_submission_logs(submission_id: int) -> dict[str, Any]:
        return await client.get(f"/api/submissions/{submission_id}/get_details/")

    @mcp.tool(
        description=(
            "Submit a zipped model bundle to a competition phase. Performs "
            "Codabench's 3-step upload: POST /api/data/, PUT to signed URL, "
            "PUT /api/data/upload_completed/, POST /api/submissions/."
        )
    )
    async def submit_to_phase(
        phase_id: int,
        bundle_path: str,
        description: str | None = None,
        task_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        from pathlib import Path

        from ..errors import CodabenchToolError

        bundle = Path(bundle_path)
        if not bundle.is_absolute():
            raise CodabenchToolError(f"bundle_path must be absolute: got {bundle_path!r}")
        if not bundle.is_file():
            raise CodabenchToolError(f"bundle not found: {bundle_path!r}")

        bundle_bytes = bundle.read_bytes()

        # Step 1: create Data record
        data_record = await client.post(
            "/api/data/",
            json={
                "type": "submission",
                "file_size": len(bundle_bytes),
                "filename": bundle.name,
            },
        )
        key = data_record["key"]
        sassy_url = data_record["sassy_url"]

        # Step 2: upload bytes to signed URL (no auth header)
        await client.put_absolute(sassy_url, content=bundle_bytes)

        # Step 3: finalize upload
        await client.put(f"/api/data/upload_completed/{key}/")

        # Step 4: create submission referencing the uploaded data key
        body: dict[str, Any] = {"data": key, "phase": phase_id}
        if task_ids:
            body["tasks"] = task_ids
        if description:
            body["description"] = description
        submission = await client.post("/api/submissions/", json=body)

        return {
            "submission_id": submission.get("id"),
            "status": submission.get("status"),
            "data_key": key,
            "raw": submission,
        }

    @mcp.tool(
        description=(
            "Poll a submission until it reaches a terminal state "
            "(finished/failed/cancelled) or `timeout_seconds` elapses. "
            "Returns the final submission record, or {status: 'still_running'} "
            "on timeout — the agent can choose to poll again."
        )
    )
    async def poll_submission(
        submission_id: int,
        timeout_seconds: float = 600.0,
        interval_seconds: float = 5.0,
    ) -> dict[str, Any]:
        import asyncio
        import time

        terminal = {"finished", "failed", "cancelled"}
        max_interval = interval_seconds * 6
        start = time.monotonic()
        wait = interval_seconds

        while True:
            sub = await client.get(f"/api/submissions/{submission_id}/")
            status = str(sub.get("status", "")).lower()
            if status in terminal:
                return sub

            elapsed = time.monotonic() - start
            remaining = timeout_seconds - elapsed
            if remaining <= 0:
                return {
                    "submission_id": submission_id,
                    "status": "still_running",
                    "last_observed_status": status,
                    "elapsed_seconds": elapsed,
                }

            sleep_for = min(wait, remaining)
            await asyncio.sleep(sleep_for)
            wait = min(wait * 1.5, max_interval)
