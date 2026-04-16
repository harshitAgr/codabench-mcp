"""Auto-pagination for DRF list endpoints.

Codabench uses DRF's PageNumberPagination which returns
{count, next, previous, results}. Some endpoints return raw lists instead;
this helper handles both shapes.
"""

from __future__ import annotations

from typing import Any

from .client import CodabenchClient

_HARD_MAX_PAGES = 100


async def paginate(
    client: CodabenchClient,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    max_pages: int = 10,
) -> dict[str, Any]:
    """Fetch up to `max_pages` of a DRF-paginated endpoint.

    Returns {results, total_count, pages_fetched, truncated}.
    """
    capped_max = min(max_pages, _HARD_MAX_PAGES)
    collected: list[Any] = []
    params = dict(params or {})
    params.setdefault("page", 1)
    pages_fetched = 0
    total_count: int | None = None
    truncated = False
    data: Any = None

    while pages_fetched < capped_max:
        data = await client.get(path, params=params)
        pages_fetched += 1

        if isinstance(data, list):
            collected.extend(data)
            total_count = len(collected)
            break

        if isinstance(data, dict) and "results" in data:
            collected.extend(data.get("results", []))
            if total_count is None:
                total_count = data.get("count")
            next_url = data.get("next")
            if not next_url:
                break
            params["page"] = int(params["page"]) + 1
        else:
            collected.append(data)
            total_count = 1
            break

    if pages_fetched >= capped_max:
        if isinstance(data, dict) and data.get("next"):
            truncated = True

    return {
        "results": collected,
        "total_count": total_count if total_count is not None else len(collected),
        "pages_fetched": pages_fetched,
        "truncated": truncated,
    }
