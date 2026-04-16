"""Shared pytest fixtures for respx-based HTTP mocking."""
from __future__ import annotations

import pytest
import respx

BASE_URL = "https://test.codabench.invalid"
TOKEN = "test-token-0000"


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("CODABENCH_API_TOKEN", TOKEN)
    monkeypatch.setenv("CODABENCH_BASE_URL", BASE_URL)


@pytest.fixture
def respx_mock():
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as mock:
        yield mock
