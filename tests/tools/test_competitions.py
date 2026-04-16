"""Tests for competition/phase/task tools."""

from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from codabench_mcp.client import CodabenchClient
from codabench_mcp.tools import competitions
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


async def test_search_competitions_auto_paginates(mcp, client, respx_mock):
    respx_mock.get("/api/competitions/").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {"id": 1, "title": "ImageNet"},
                    {"id": 2, "title": "GLUE"},
                ],
            },
        )
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "search_competitions")
    result = await tool.fn(q="net", public=True, page_size=20, max_pages=5)
    assert result["total_count"] == 2
    assert len(result["results"]) == 2


async def test_get_competition(mcp, client, respx_mock):
    respx_mock.get("/api/competitions/5/").mock(
        return_value=httpx.Response(200, json={"id": 5, "title": "GLUE"})
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "get_competition")
    result = await tool.fn(competition_id=5)
    assert result == {"id": 5, "title": "GLUE"}


async def test_list_competition_phases(mcp, client, respx_mock):
    respx_mock.get("/api/phases/", params={"competition": "5", "page": "1"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{"id": 10, "name": "dev"}],
            },
        )
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "list_competition_phases")
    result = await tool.fn(competition_id=5)
    assert result["total_count"] == 1
    assert result["results"][0]["id"] == 10


async def test_get_phase(mcp, client, respx_mock):
    respx_mock.get("/api/phases/10/").mock(
        return_value=httpx.Response(200, json={"id": 10, "name": "dev"})
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "get_phase")
    result = await tool.fn(phase_id=10)
    assert result == {"id": 10, "name": "dev"}


async def test_get_competition_rules_extracts_rule_pages(mcp, client, respx_mock):
    respx_mock.get("/api/competitions/5/").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 5,
                "title": "GLUE",
                "pages": [
                    {"title": "Overview", "content": "Welcome"},
                    {"title": "Terms and Conditions", "content": "Don't cheat"},
                    {"title": "Evaluation", "content": "Accuracy"},
                ],
            },
        )
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "get_competition_rules")
    result = await tool.fn(competition_id=5)
    assert "Terms and Conditions" in result["rules_markdown"]
    assert "Accuracy" in result["rules_markdown"]


async def test_list_competition_tasks(mcp, client, respx_mock):
    respx_mock.get("/api/tasks/", params={"competition": "5", "page": "1"}).mock(
        return_value=httpx.Response(
            200,
            json={"count": 1, "next": None, "previous": None, "results": [{"id": 7}]},
        )
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "list_competition_tasks")
    result = await tool.fn(competition_id=5)
    assert result["results"][0]["id"] == 7


async def test_get_task(mcp, client, respx_mock):
    respx_mock.get("/api/tasks/7/").mock(
        return_value=httpx.Response(200, json={"id": 7, "name": "classify"})
    )
    competitions.register(mcp, client)
    tool = _get_tool(mcp, "get_task")
    result = await tool.fn(task_id=7)
    assert result == {"id": 7, "name": "classify"}
