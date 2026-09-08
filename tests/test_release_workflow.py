from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"


def _load():
    # PyYAML parses the bare `on:` key as boolean True; read it back with that in mind.
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_exists():
    assert WORKFLOW.exists()


def test_triggers_on_release_published():
    wf = _load()
    trigger = wf.get("on", wf.get(True))  # 'on' may parse as the boolean True
    assert trigger["release"]["types"] == ["published"]


def test_declares_oidc_and_contents_permissions():
    text = WORKFLOW.read_text()
    assert "id-token: write" in text
    assert "contents: write" in text


def test_checkout_uses_full_history():
    text = WORKFLOW.read_text()
    assert "fetch-depth: 0" in text


def test_has_version_guard_and_trusted_publish_and_asset_upload():
    text = WORKFLOW.read_text()
    assert "pypa/gh-action-pypi-publish" in text
    assert "gh release upload" in text
    # version guard fails on a dirty/mismatched version
    assert ".dev" in text and "Version" in text


def test_builds_on_python_311():
    text = WORKFLOW.read_text()
    assert "3.11" in text
