"""Tests for DRF pagination helper."""
from __future__ import annotations

import httpx
import pytest

from codabench_mcp.client import CodabenchClient
from codabench_mcp.pagination import paginate
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture
async def client():
    c = CodabenchClient(base_url=BASE_URL, token=TOKEN)
    yield c
    await c.close()


async def test_paginate_returns_all_results_across_pages(client, respx_mock):
    respx_mock.get("/api/competitions/", params={"page": "1"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 3,
                "next": f"{BASE_URL}/api/competitions/?page=2",
                "previous": None,
                "results": [{"id": 1}, {"id": 2}],
            },
        )
    )
    respx_mock.get("/api/competitions/", params={"page": "2"}).mock(
        return_value=httpx.Response(
            200,
            json={"count": 3, "next": None, "previous": None, "results": [{"id": 3}]},
        )
    )

    result = await paginate(client, "/api/competitions/", params={}, max_pages=10)
    assert result["total_count"] == 3
    assert [r["id"] for r in result["results"]] == [1, 2, 3]
    assert result["pages_fetched"] == 2


async def test_paginate_stops_at_max_pages(client, respx_mock):
    respx_mock.get("/api/competitions/", params={"page": "1"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 100,
                "next": f"{BASE_URL}/api/competitions/?page=2",
                "previous": None,
                "results": [{"id": 1}],
            },
        )
    )
    result = await paginate(client, "/api/competitions/", params={}, max_pages=1)
    assert result["pages_fetched"] == 1
    assert len(result["results"]) == 1
    assert result["truncated"] is True


async def test_paginate_caps_max_pages_at_100(client, respx_mock):
    def _respond(request):
        return httpx.Response(
            200,
            json={
                "count": 999999,
                "next": f"{BASE_URL}/api/competitions/?page=X",
                "previous": None,
                "results": [{"id": 1}],
            },
        )

    respx_mock.get("/api/competitions/").mock(side_effect=_respond)
    result = await paginate(client, "/api/competitions/", params={}, max_pages=10000)
    assert result["pages_fetched"] == 100
    assert result["truncated"] is True


async def test_paginate_handles_non_paginated_list_response(client, respx_mock):
    """Some DRF endpoints return a raw list, not a paginated object."""
    respx_mock.get("/api/phases/").mock(
        return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
    )
    result = await paginate(client, "/api/phases/", params={}, max_pages=10)
    assert result["total_count"] == 2
    assert [r["id"] for r in result["results"]] == [1, 2]
    assert result["pages_fetched"] == 1
