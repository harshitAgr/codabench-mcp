from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest
from mcp.server.fastmcp import FastMCP

from codabench_mcp.client import CodabenchClient
from codabench_mcp.errors import CodabenchToolError
from codabench_mcp.tools import data
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture
async def client():
    c = CodabenchClient(base_url=BASE_URL, token=TOKEN)
    yield c
    await c.close()


@pytest.fixture
def mcp():
    return FastMCP("test")


async def test_download_dataset_rejects_relative_path(mcp, client, tmp_path):
    data.register(mcp, client)
    tool = mcp._tool_manager.get_tool("download_dataset")
    with pytest.raises(CodabenchToolError, match="absolute"):
        await tool.fn(key="abc", dest_path="relative/out.zip")


async def test_download_dataset_refuses_overwrite_without_flag(mcp, client, tmp_path, respx_mock):
    existing = tmp_path / "out.zip"
    existing.write_bytes(b"old")
    data.register(mcp, client)
    tool = mcp._tool_manager.get_tool("download_dataset")
    with pytest.raises(CodabenchToolError, match="exists"):
        await tool.fn(key="abc", dest_path=str(existing), overwrite=False)


async def test_download_dataset_writes_file_and_returns_sha256(mcp, client, tmp_path, respx_mock):
    payload = b"DATASET" * 500
    respx_mock.get("/api/datasets/abc/download/").mock(
        return_value=httpx.Response(
            200, content=payload, headers={"Content-Length": str(len(payload))}
        )
    )
    dest = tmp_path / "out.zip"
    data.register(mcp, client)
    tool = mcp._tool_manager.get_tool("download_dataset")
    result = await tool.fn(key="abc", dest_path=str(dest), overwrite=True)
    assert Path(result["path"]).read_bytes() == payload
    assert result["bytes_written"] == len(payload)
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
