"""Tests for server bootstrap, env parsing, and logging configuration."""

from __future__ import annotations

import logging
import sys

import pytest

from codabench_mcp import server


def test_build_config_reads_token_from_env(monkeypatch):
    monkeypatch.setenv("CODABENCH_API_TOKEN", "abc123")
    monkeypatch.delenv("CODABENCH_BASE_URL", raising=False)
    config = server.build_config()
    assert config.token == "abc123"
    assert config.base_url == "https://www.codabench.org"
    assert config.allow_write_raw is False


def test_build_config_overrides_base_url_and_write_flag(monkeypatch):
    monkeypatch.setenv("CODABENCH_API_TOKEN", "abc123")
    monkeypatch.setenv("CODABENCH_BASE_URL", "https://example.test")
    monkeypatch.setenv("CODABENCH_ALLOW_WRITE_RAW", "1")
    config = server.build_config()
    assert config.base_url == "https://example.test"
    assert config.allow_write_raw is True


def test_build_config_exits_when_token_missing(monkeypatch, capsys):
    monkeypatch.delenv("CODABENCH_API_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        server.build_config()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "CODABENCH_API_TOKEN" in captured.err


def test_configure_logging_attaches_stderr_handler_only():
    root = logging.getLogger("codabench_mcp")
    for h in list(root.handlers):
        root.removeHandler(h)

    server.configure_logging()
    handlers = logging.getLogger("codabench_mcp").handlers
    assert len(handlers) == 1
    handler = handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is sys.stderr
