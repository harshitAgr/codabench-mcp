"""Tests for error translation and token redaction."""
from __future__ import annotations

import httpx

from codabench_mcp.errors import CodabenchToolError, redact_token, translate_http_error


def test_redact_token_strips_authorization_header_value():
    text = "Authorization: Token secret-abc-123\nContent-Type: application/json"
    assert "secret-abc-123" not in redact_token(text)
    assert "Authorization: Token <redacted>" in redact_token(text)


def test_redact_token_handles_bearer_variant():
    text = "authorization: bearer my-jwt"
    assert "my-jwt" not in redact_token(text)


def test_redact_token_returns_empty_string_unchanged():
    assert redact_token("") == ""


def test_translate_401_produces_auth_error():
    response = httpx.Response(401, text='{"detail":"Invalid token."}')
    err = translate_http_error(response, request_summary="GET /api/my_profile/")
    assert isinstance(err, CodabenchToolError)
    assert "Auth failed" in str(err)
    assert "regenerate" in str(err).lower()


def test_translate_404_echoes_resource():
    response = httpx.Response(404, text='{"detail":"Not found."}')
    err = translate_http_error(response, request_summary="GET /api/competitions/999/")
    assert "Not found" in str(err)
    assert "999" in str(err)


def test_translate_429_includes_retry_after():
    response = httpx.Response(
        429, text="", headers={"Retry-After": "30"}
    )
    err = translate_http_error(response, request_summary="GET /api/competitions/")
    assert "30" in str(err)
    assert "rate" in str(err).lower()


def test_translate_400_passes_detail_through_after_redaction():
    response = httpx.Response(
        400, text='{"detail":"phase field required. Token secret-xyz was seen."}'
    )
    err = translate_http_error(response, request_summary="POST /api/submissions/")
    assert "phase field required" in str(err)
    assert "secret-xyz" not in str(err)


def test_translate_500_signals_server_error():
    response = httpx.Response(500, text="server exploded")
    err = translate_http_error(response, request_summary="GET /api/competitions/")
    assert "server" in str(err).lower()
