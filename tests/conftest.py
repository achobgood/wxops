"""Shared pytest fixtures for wxcli tests."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner():
    """Typer CLI test runner (invokes commands without a live API)."""
    return CliRunner()


@pytest.fixture
def mock_env_token(monkeypatch):
    """Set a fake WEBEX_ACCESS_TOKEN so auth doesn't fail during --help tests."""
    monkeypatch.setenv("WEBEX_ACCESS_TOKEN", "fake-test-token")
