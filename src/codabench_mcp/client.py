"""Thin wrapper around httpx.AsyncClient.

Centralises:
- Base URL joining
- Authorization header attachment (skipped for put_absolute)
- Status code handling — raises CodabenchToolError via errors.translate_http_error
- Single delayed retry on 5xx responses
- Streaming downloads with size caps and SHA-256
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

import httpx

from .errors import CodabenchToolError, translate_http_error

log = logging.getLogger("codabench_mcp.client")

_RETRY_DELAY_SECONDS = 2.0
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class CodabenchClient:
    def __init__(self, *, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=_DEFAULT_TIMEOUT,
            headers={"Authorization": f"Token {token}"},
        )
        self._unauth_client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()
        await self._unauth_client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        content: bytes | None = None,
        files: Any = None,
    ) -> httpx.Response:
        """Low-level request with 5xx retry. Returns the raw response."""
        summary = f"{method.upper()} {path}"

        async def _do() -> httpx.Response:
            return await self._client.request(
                method, path, params=params, json=json, content=content, files=files
            )

        try:
            resp = await _do()
            if 500 <= resp.status_code < 600:
                log.warning(
                    "5xx on %s, retrying once in %.1fs", summary, _RETRY_DELAY_SECONDS
                )
                await asyncio.sleep(_RETRY_DELAY_SECONDS)
                resp = await _do()
        except httpx.HTTPError as exc:
            raise CodabenchToolError(f"Network error on {summary}: {exc}") from exc

        if resp.status_code >= 400:
            raise translate_http_error(resp, request_summary=summary)
        return resp

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = await self.request("GET", path, params=params)
        return resp.json() if resp.content else None

    async def post(
        self,
        path: str,
        *,
        json: Any = None,
        files: Any = None,
    ) -> Any:
        resp = await self.request("POST", path, json=json, files=files)
        return resp.json() if resp.content else None

    async def put(self, path: str, *, json: Any = None) -> Any:
        resp = await self.request("PUT", path, json=json)
        return resp.json() if resp.content else None

    async def patch(self, path: str, *, json: Any = None) -> Any:
        resp = await self.request("PATCH", path, json=json)
        return resp.json() if resp.content else None

    async def delete(self, path: str) -> Any:
        resp = await self.request("DELETE", path)
        return resp.json() if resp.content else None

    async def put_absolute(self, url: str, *, content: bytes) -> None:
        """PUT raw bytes to an absolute URL (e.g. GCS signed URL).

        No Authorization header is attached — the signed URL carries auth.
        """
        try:
            resp = await self._unauth_client.put(url, content=content)
        except httpx.HTTPError as exc:
            raise CodabenchToolError(f"Network error on PUT {url}: {exc}") from exc
        if resp.status_code >= 400:
            raise translate_http_error(resp, request_summary=f"PUT {url}")

    async def stream_to_file(
        self, path: str, dest: Path, *, max_bytes: int
    ) -> dict[str, Any]:
        """Stream a GET response to `dest`, computing SHA-256 on the fly.

        Aborts and deletes `dest` if the server-reported Content-Length
        exceeds `max_bytes`. Returns {path, bytes_written, sha256}.
        """
        summary = f"GET {path}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256()
        total = 0

        try:
            async with self._client.stream("GET", path) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    raise translate_http_error(resp, request_summary=summary)
                content_length_header = resp.headers.get("Content-Length")
                if content_length_header and int(content_length_header) > max_bytes:
                    raise CodabenchToolError(
                        f"Download {summary} exceeds max_bytes "
                        f"({content_length_header} > {max_bytes})"
                    )
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        total += len(chunk)
                        if total > max_bytes:
                            raise CodabenchToolError(
                                f"Download {summary} exceeds max_bytes (mid-stream)"
                            )
                        sha.update(chunk)
                        f.write(chunk)
        except CodabenchToolError:
            if dest.exists():
                dest.unlink()
            raise
        except httpx.HTTPError as exc:
            if dest.exists():
                dest.unlink()
            raise CodabenchToolError(f"Network error on {summary}: {exc}") from exc

        return {"path": str(dest), "bytes_written": total, "sha256": sha.hexdigest()}
