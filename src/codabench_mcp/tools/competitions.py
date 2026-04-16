"""Competition, phase, and task reading tools."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CodabenchClient
from ..pagination import paginate


def register(mcp: FastMCP, client: CodabenchClient) -> None:

    @mcp.tool(
        description=(
            "Search public Codabench competitions. Auto-paginates up to max_pages."
        )
    )
    async def search_competitions(
        q: str | None = None,
        public: bool = True,
        page_size: int = 20,
        max_pages: int = 10,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": page_size}
        if q:
            params["search"] = q
        if public:
            params["public"] = "true"
        return await paginate(
            client, "/api/competitions/", params=params, max_pages=max_pages
        )

    @mcp.tool(description="Get full details of a single Codabench competition.")
    async def get_competition(competition_id: int) -> dict[str, Any]:
        return await client.get(f"/api/competitions/{competition_id}/")

    @mcp.tool(description="List all phases of a Codabench competition.")
    async def list_competition_phases(
        competition_id: int, max_pages: int = 10
    ) -> dict[str, Any]:
        return await paginate(
            client,
            "/api/phases/",
            params={"competition": str(competition_id)},
            max_pages=max_pages,
        )

    @mcp.tool(description="Get full details of a single phase.")
    async def get_phase(phase_id: int) -> dict[str, Any]:
        return await client.get(f"/api/phases/{phase_id}/")

    @mcp.tool(
        description=(
            "Get a competition's rules, terms, evaluation criteria, and any "
            "other descriptive pages concatenated into a single markdown string."
        )
    )
    async def get_competition_rules(competition_id: int) -> dict[str, Any]:
        comp = await client.get(f"/api/competitions/{competition_id}/")
        pages = comp.get("pages") or []
        chunks: list[str] = []
        for page in pages:
            title = page.get("title", "(untitled)")
            content = page.get("content", "")
            chunks.append(f"# {title}\n\n{content}")
        return {
            "competition_id": competition_id,
            "title": comp.get("title"),
            "rules_markdown": "\n\n---\n\n".join(chunks),
            "page_titles": [p.get("title") for p in pages],
        }

    @mcp.tool(description="List all tasks attached to a Codabench competition.")
    async def list_competition_tasks(
        competition_id: int, max_pages: int = 10
    ) -> dict[str, Any]:
        return await paginate(
            client,
            "/api/tasks/",
            params={"competition": str(competition_id)},
            max_pages=max_pages,
        )

    @mcp.tool(
        description="Get full details of a single task, including dataset keys."
    )
    async def get_task(task_id: int) -> dict[str, Any]:
        return await client.get(f"/api/tasks/{task_id}/")
