from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from codabench_mcp.client import CodabenchClient
from codabench_mcp.tools import submissions
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture
async def client():
    c = CodabenchClient(base_url=BASE_URL, token=TOKEN)
    yield c
    await c.close()


@pytest.fixture
def mcp():
    return FastMCP("test")


async def test_list_my_submissions(mcp, client, respx_mock):
    respx_mock.get("/api/submissions/", params={"mine": "true", "page": "1"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{"id": 100, "status": "finished"}],
            },
        )
    )
    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("list_my_submissions")
    result = await tool.fn()
    assert result["results"][0]["id"] == 100


async def test_get_submission(mcp, client, respx_mock):
    respx_mock.get("/api/submissions/100/").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 100,
                "status": "finished",
                "scores": [{"key": "acc", "score": 0.9}],
            },
        )
    )
    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("get_submission")
    result = await tool.fn(submission_id=100)
    assert result["status"] == "finished"


async def test_get_submission_logs(mcp, client, respx_mock):
    respx_mock.get("/api/submissions/100/get_details/").mock(
        return_value=httpx.Response(
            200, json={"stdout": "hello", "stderr": "", "ingestion_stderr": ""}
        )
    )
    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("get_submission_logs")
    result = await tool.fn(submission_id=100)
    assert result["stdout"] == "hello"
