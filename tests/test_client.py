"""Tests for CodabenchClient."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from codabench_mcp.client import CodabenchClient
from codabench_mcp.errors import CodabenchToolError
from tests.conftest import BASE_URL, TOKEN


@pytest.fixture
async def client():
    c = CodabenchClient(base_url=BASE_URL, token=TOKEN)
    yield c
    await c.close()


async def test_get_attaches_token_header(client, respx_mock):
    route = respx_mock.get("/api/my_profile/").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    data = await client.get("/api/my_profile/")
    assert data == {"id": 1}
    sent = route.calls.last.request
    assert sent.headers["authorization"] == f"Token {TOKEN}"


async def test_get_prepends_base_url_when_path_is_relative(client, respx_mock):
    respx_mock.get("/api/competitions/5/").mock(return_value=httpx.Response(200, json={"id": 5}))
    data = await client.get("/api/competitions/5/")
    assert data == {"id": 5}


async def test_get_raises_on_404(client, respx_mock):
    respx_mock.get("/api/competitions/999/").mock(
        return_value=httpx.Response(404, json={"detail": "Not found."})
    )
    with pytest.raises(CodabenchToolError, match="Not found"):
        await client.get("/api/competitions/999/")


async def test_post_json_body(client, respx_mock):
    route = respx_mock.post("/api/submissions/").mock(
        return_value=httpx.Response(201, json={"id": 42})
    )
    data = await client.post("/api/submissions/", json={"phase": 1, "data": "abc"})
    assert data == {"id": 42}
    sent = route.calls.last.request
    assert b'"phase"' in sent.content and b"1" in sent.content


async def test_put_absolute_url_bypasses_base_url_and_auth(client, respx_mock):
    import respx as _respx

    with _respx.mock(assert_all_called=False) as m:
        route = m.put("https://storage.googleapis.com/bucket/x?sig=abc").mock(
            return_value=httpx.Response(200)
        )
        await client.put_absolute(
            "https://storage.googleapis.com/bucket/x?sig=abc", content=b"payload"
        )
        sent = route.calls.last.request
        assert "authorization" not in {k.lower() for k in sent.headers.keys()}
        assert sent.content == b"payload"


async def test_put_absolute_mirrors_signed_content_type(client):
    import respx as _respx

    url = (
        "https://minio.example/bucket/best_v1.zip"
        "?AWSAccessKeyId=k&Signature=s&content-type=application%2Fzip&Expires=1"
    )
    with _respx.mock(assert_all_called=True) as m:
        route = m.put(url).mock(return_value=httpx.Response(200))
        await client.put_absolute(url, content=b"PK\x03\x04")
        sent = route.calls.last.request
        assert sent.headers["content-type"] == "application/zip"


async def test_retry_once_on_5xx(client, respx_mock):
    route = respx_mock.get("/api/competitions/").mock(
        side_effect=[
            httpx.Response(502, text="bad gateway"),
            httpx.Response(200, json={"results": []}),
        ]
    )
    data = await client.get("/api/competitions/")
    assert data == {"results": []}
    assert route.call_count == 2


async def test_no_retry_on_4xx(client, respx_mock):
    route = respx_mock.get("/api/competitions/999/").mock(
        return_value=httpx.Response(404, json={"detail": "Not found."})
    )
    with pytest.raises(CodabenchToolError):
        await client.get("/api/competitions/999/")
    assert route.call_count == 1


async def test_stream_to_file_writes_bytes_and_computes_sha256(client, respx_mock, tmp_path: Path):
    payload = b"hello world" * 1000
    respx_mock.get("/api/datasets/abc/download/").mock(
        return_value=httpx.Response(
            200, content=payload, headers={"Content-Length": str(len(payload))}
        )
    )
    dest = tmp_path / "out.bin"
    result = await client.stream_to_file("/api/datasets/abc/download/", dest, max_bytes=10_000_000)
    assert dest.read_bytes() == payload
    assert result["bytes_written"] == len(payload)
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["path"] == str(dest)


async def test_stream_to_file_rejects_oversized_response(client, respx_mock, tmp_path: Path):
    respx_mock.get("/api/datasets/big/download/").mock(
        return_value=httpx.Response(200, content=b"x", headers={"Content-Length": "999999999"})
    )
    dest = tmp_path / "out.bin"
    with pytest.raises(CodabenchToolError, match="exceeds max"):
        await client.stream_to_file("/api/datasets/big/download/", dest, max_bytes=1024)
    assert not dest.exists()
