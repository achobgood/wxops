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


def _steps():
    wf = _load()
    return wf["jobs"]["publish"]["steps"]


def test_ci_gate_runs_before_anything_is_built():
    """The gate must be the first `run:` step: a failed build step would
    otherwise mask a missing-CI failure with a different red X."""
    steps = _steps()
    names = [s.get("name", s.get("uses", "")) for s in steps]
    gate = next(i for i, n in enumerate(names) if "green CI" in n)
    assert all("run" not in s for s in steps[:gate]), "only checkout/setup may precede the gate"
    assert gate < names.index("Playbook bundle freshness guard")


def test_ci_gate_fails_closed_on_no_run_and_on_non_success():
    text = WORKFLOW.read_text()
    assert "actions/workflows/ci.yml/runs?head_sha=" in text, "must query CI runs for the release SHA"
    assert "No CI run found" in text, "absence of evidence must fail, not pass"
    assert '"completed"' in text and '"success"' in text
    assert "newest" in text.lower() and ".[0]" in text, "judge the NEWEST run, so a re-run that went green counts and a re-run that went red counts too"


def test_ci_gate_uses_the_checked_out_sha_not_the_event_payload():
    text = WORKFLOW.read_text()
    assert "git rev-parse HEAD" in text
