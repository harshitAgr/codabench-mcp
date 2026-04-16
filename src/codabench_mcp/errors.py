"""Error translation from HTTP responses to MCP-facing tool errors.

Every tool error surfaced to the agent goes through this module so:
1. HTTP status codes map to consistent, actionable messages.
2. Any Authorization header value is scrubbed before logging/returning.
"""

from __future__ import annotations

import re

import httpx

_AUTH_HEADER_RE = re.compile(r"(authorization\s*:\s*(?:token|bearer)\s+)\S+", re.IGNORECASE)
_TOKEN_PATTERN_RE = re.compile(r"((?:token|bearer)\s+)\S+", re.IGNORECASE)


class CodabenchToolError(Exception):
    """Raised by tools to return a structured error back to the MCP client."""


def redact_token(text: str) -> str:
    """Strip any `Authorization: Token|Bearer <value>` from text."""
    if not text:
        return text
    # First redact Authorization header format: preserve the header structure
    text = _AUTH_HEADER_RE.sub(r"\1<redacted>", text)
    # Then redact any Token/Bearer patterns in messages/detail text
    text = _TOKEN_PATTERN_RE.sub(r"\1<redacted>", text)
    return text


def _extract_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or ""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        return str(data)
    return str(data)


def translate_http_error(response: httpx.Response, *, request_summary: str) -> CodabenchToolError:
    """Convert a non-2xx httpx response into a CodabenchToolError.

    `request_summary` is a short string like "GET /api/competitions/5/" used
    in the error message so the agent knows which call failed.
    """
    status = response.status_code
    detail = redact_token(_extract_detail(response))
    summary = redact_token(request_summary)

    if status in (401, 403):
        return CodabenchToolError(
            f"Auth failed on {summary}. Token may be invalid or expired — "
            "regenerate via https://www.codabench.org/api/docs/. "
            f"Server said: {detail}"
        )
    if status == 404:
        return CodabenchToolError(f"Not found: {summary}. Server said: {detail}")
    if status == 429:
        retry_after = response.headers.get("Retry-After", "unknown")
        return CodabenchToolError(
            f"Rate limited on {summary}. Retry-After: {retry_after}s. Server said: {detail}"
        )
    if 400 <= status < 500:
        return CodabenchToolError(f"Request rejected ({status}) on {summary}: {detail}")
    if status >= 500:
        return CodabenchToolError(f"Server error ({status}) on {summary}: {detail}")
    return CodabenchToolError(f"Unexpected status {status} on {summary}: {detail}")
