from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from codabench_mcp.client import CodabenchClient
from codabench_mcp.errors import CodabenchToolError
from codabench_mcp.tools import raw
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture
async def client():
    c = CodabenchClient(base_url=BASE_URL, token=TOKEN)
    yield c
    await c.close()


@pytest.fixture
def mcp():
    return FastMCP("test")


async def test_codabench_request_allows_get_by_default(mcp, client, respx_mock):
    respx_mock.get("/api/anything/").mock(
        return_value=httpx.Response(200, json={"hello": "world"})
    )
    raw.register(mcp, client, allow_write=False)
    tool = mcp._tool_manager.get_tool("codabench_request")
    result = await tool.fn(method="GET", path="/api/anything/")
    assert result["body"] == {"hello": "world"}
    assert result["status_code"] == 200


async def test_codabench_request_blocks_post_without_allow_write(mcp, client):
    raw.register(mcp, client, allow_write=False)
    tool = mcp._tool_manager.get_tool("codabench_request")
    with pytest.raises(CodabenchToolError, match="CODABENCH_ALLOW_WRITE_RAW"):
        await tool.fn(method="POST", path="/api/competitions/1/", body={"x": 1})


async def test_codabench_request_allows_post_when_allow_write(mcp, client, respx_mock):
    respx_mock.post("/api/thing/").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    raw.register(mcp, client, allow_write=True)
    tool = mcp._tool_manager.get_tool("codabench_request")
    result = await tool.fn(method="POST", path="/api/thing/", body={"name": "x"})
    assert result["status_code"] == 201


async def test_codabench_request_passes_params(mcp, client, respx_mock):
    route = respx_mock.get("/api/competitions/").mock(
        return_value=httpx.Response(200, json={"count": 0, "results": []})
    )
    raw.register(mcp, client, allow_write=False)
    tool = mcp._tool_manager.get_tool("codabench_request")
    await tool.fn(method="GET", path="/api/competitions/", params={"search": "foo"})
    sent = route.calls.last.request
    assert "search=foo" in str(sent.url)
