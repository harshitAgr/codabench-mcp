from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from codabench_mcp.client import CodabenchClient
from codabench_mcp.errors import CodabenchToolError
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


async def test_submit_to_phase_runs_full_upload_flow(mcp, client, tmp_path, respx_mock):
    bundle = tmp_path / "model.zip"
    bundle.write_bytes(b"PK\x03\x04fake-zip")

    sassy_url = "https://storage.googleapis.com/bucket/file?sig=xyz"

    create_data = respx_mock.post("/api/data/").mock(
        return_value=httpx.Response(201, json={"key": "new-key-abc", "sassy_url": sassy_url})
    )
    finalize = respx_mock.put("/api/data/upload_completed/new-key-abc/").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    create_sub = respx_mock.post("/api/submissions/").mock(
        return_value=httpx.Response(
            201, json={"id": 200, "status": "submitted", "data": "new-key-abc"}
        )
    )

    import respx as _respx

    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("submit_to_phase")

    with _respx.mock(assert_all_called=True) as m:
        upload = m.put(sassy_url).mock(return_value=httpx.Response(200))
        result = await tool.fn(
            phase_id=10,
            bundle_path=str(bundle),
            description="first try",
            task_ids=[7, 8],
        )
        assert upload.call_count == 1

    assert create_data.call_count == 1
    assert finalize.call_count == 1
    assert create_sub.call_count == 1
    assert result["submission_id"] == 200
    assert result["status"] == "submitted"

    import json

    sub_req = create_sub.calls.last.request
    body = json.loads(sub_req.content)
    assert body["data"] == "new-key-abc"
    assert body["phase"] == 10
    assert body["tasks"] == [7, 8]
    assert body["description"] == "first try"


async def test_submit_to_phase_rejects_missing_bundle(mcp, client):
    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("submit_to_phase")
    with pytest.raises(CodabenchToolError):
        await tool.fn(phase_id=1, bundle_path="/tmp/does-not-exist-12345.zip")


async def test_poll_submission_returns_immediately_on_terminal_state(mcp, client, respx_mock):
    respx_mock.get("/api/submissions/200/").mock(
        return_value=httpx.Response(200, json={"id": 200, "status": "finished", "scores": []})
    )
    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("poll_submission")
    result = await tool.fn(submission_id=200, timeout_seconds=1, interval_seconds=0.1)
    assert result["status"] == "finished"


async def test_poll_submission_times_out_without_error(mcp, client, respx_mock):
    respx_mock.get("/api/submissions/200/").mock(
        return_value=httpx.Response(200, json={"id": 200, "status": "running"})
    )
    submissions.register(mcp, client)
    tool = mcp._tool_manager.get_tool("poll_submission")
    result = await tool.fn(submission_id=200, timeout_seconds=0.3, interval_seconds=0.1)
    assert result["status"] == "still_running"
    assert result["submission_id"] == 200
