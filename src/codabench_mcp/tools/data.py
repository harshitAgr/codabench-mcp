"""Dataset download tool."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CodabenchClient
from ..errors import CodabenchToolError

DEFAULT_MAX_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB


def register(mcp: FastMCP, client: CodabenchClient) -> None:

    @mcp.tool(
        description=(
            "Download a Codabench dataset/bundle to a local absolute path. "
            "Streams directly to disk and returns the SHA-256. Refuses to "
            "overwrite unless overwrite=True."
        )
    )
    async def download_dataset(
        key: str,
        dest_path: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        dest = Path(dest_path)
        if not dest.is_absolute():
            raise CodabenchToolError(f"dest_path must be absolute: got {dest_path!r}")
        if dest.exists() and not overwrite:
            raise CodabenchToolError(
                f"dest_path {dest_path!r} exists; pass overwrite=True to replace"
            )
        max_bytes = int(os.environ.get("CODABENCH_MAX_DOWNLOAD_BYTES", DEFAULT_MAX_BYTES))
        return await client.stream_to_file(
            f"/api/datasets/{key}/download/", dest, max_bytes=max_bytes
        )
