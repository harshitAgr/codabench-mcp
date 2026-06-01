from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from codabench_mcp.client import CodabenchClient
from codabench_mcp.tools import leaderboards
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture
async def client():
    c = CodabenchClient(base_url=BASE_URL, token=TOKEN)
    yield c
    await c.close()


@pytest.fixture
def mcp():
    return FastMCP("test")


def _get_tool(mcp: FastMCP, name: str):
    return mcp._tool_manager.get_tool(name)


async def test_get_leaderboard(mcp, client, respx_mock):
    # Resolves phase -> leaderboard id, then fetches the leaderboard detail.
    respx_mock.get("/api/phases/10/").mock(
        return_value=httpx.Response(200, json={"id": 10, "leaderboard": 555})
    )
    respx_mock.get("/api/leaderboards/555/").mock(
        return_value=httpx.Response(
            200,
            json={
                "submissions": [
                    {"owner": "alice", "scores": [{"column_key": "Task1_DSC", "score": "0.95"}]}
                ]
            },
        )
    )
    leaderboards.register(mcp, client)
    tool = _get_tool(mcp, "get_leaderboard")
    result = await tool.fn(phase_id=10)
    assert result["submissions"][0]["owner"] == "alice"


async def test_get_leaderboard_phase_without_board(mcp, client, respx_mock):
    respx_mock.get("/api/phases/11/").mock(
        return_value=httpx.Response(200, json={"id": 11, "leaderboard": None})
    )
    leaderboards.register(mcp, client)
    tool = _get_tool(mcp, "get_leaderboard")
    result = await tool.fn(phase_id=11)
    assert result["submissions"] == []


async def test_get_my_profile(mcp, client, respx_mock):
    respx_mock.get("/api/my_profile/").mock(
        return_value=httpx.Response(200, json={"username": "hars", "id": 99})
    )
    leaderboards.register(mcp, client)
    tool = _get_tool(mcp, "get_my_profile")
    result = await tool.fn()
    assert result["username"] == "hars"
