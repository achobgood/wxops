"""Shared pytest fixtures for wxcli tests."""

import os

# Keep the suite hermetic: the CLI's PyPI update check fires from the top-level
# callback on every CliRunner call. Disable it session-wide so no test reaches PyPI.
os.environ.setdefault("WXCLI_NO_UPDATE_CHECK", "1")

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
