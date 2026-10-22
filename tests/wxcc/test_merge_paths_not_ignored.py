"""Guard: every path Plan 2 plans to add must be visible to git.

A path matched by .gitignore would never be committed and never run in CI.
"""
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

PLANNED_PATHS = [
    "tests/wxcc/test_client.py",
    "tests/wxcc/conftest.py",
    "tests/wxcc/fixtures/mini_flow_store.json",
    "tests/wxcc/fixtures/expected_widgets.py",
    "src/wxcli/_playbook/.mcp.json",
    "specs/webex-cc-flow-store.json",
    "src/wxcli/commands/cc_flow_store.py",
    "src/wxcli/commands/cc_flow_authoring.py",
    "src/wxcli/commands/cc_functions_test.py",
    "tools/flow_store_spec.py",
    "tools/flow_store_host_probe.py",
    "wxcli-dist/mcp.bundled.json",
    "docs/playbooks/wxcc-setup.md",
    "docs/examples/flowir/simple-inbound.json",
    "docs/reference/flow-designer-activities/_index.md",
]

# Plan 3 (P3-2): wxcc files that stay local-only must be ignored, so they are
# never staged by accident.
LOCAL_ONLY_DESTINATIONS = [
    "docs/tests/findings/x.md",
    "docs/plans/x.md",
    "docs/superpowers/plans/x.md",
    "docs/prompts/CODEX_PORT_PROMPT.md",
    "docs/reference/archive/x.md.bak",
    "docs/wxcc-pipeline-visual.html",
    ".superpowers/wxcc-sdd/x.md",
    ".superpowers/brainstorm/x/y.html",
]


@pytest.mark.parametrize("path", PLANNED_PATHS)
def test_planned_paths_are_not_ignored(path):
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=REPO
    )
    if result.returncode != 1:
        why = subprocess.run(
            ["git", "check-ignore", "--no-index", "-v", path],
            cwd=REPO, capture_output=True, text=True,
        ).stdout.strip()
        pytest.fail(f"{path} is ignored by: {why}")


@pytest.mark.parametrize(
    "path",
    [
        "tests/wxcc/__pycache__/x.pyc",
        "tests/wxcc/sub/__pycache__/y.pyc",
    ],
)
def test_bytecode_under_tests_wxcc_stays_ignored(path):
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=REPO
    )
    assert result.returncode == 0, f"{path} is not ignored"


@pytest.mark.parametrize("path", LOCAL_ONLY_DESTINATIONS)
def test_local_only_destinations_are_ignored(path):
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=REPO
    )
    assert result.returncode == 0, f"{path} is not ignored"
