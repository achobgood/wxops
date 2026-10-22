"""Guards that keep the shipped wheel honest: CI must smoke-test the installed
package, and package-data must include every hidden tree in the bundle."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_release_workflow_runs_wheel_smoke_after_build():
    text = (REPO / ".github/workflows/release.yml").read_text()
    assert "tools/wheel_playbook_smoke.py dist" in text
    assert text.index("Build wheel") < text.index("wheel_playbook_smoke")
    assert text.index("wheel_playbook_smoke") < text.index("Publish to PyPI")


def test_package_data_ships_all_hidden_bundle_trees():
    text = (REPO / "pyproject.toml").read_text()
    for pattern in ('"_playbook/.claude/**"', '"_playbook/.codex/**"',
                    '"_playbook/.mcp.json"'):  # no .agents tree: P2-4 keeps wxcli's Codex layout
        assert pattern in text, pattern


def test_smoke_script_exists_and_is_stdlib_only():
    src = (REPO / "tools/wheel_playbook_smoke.py").read_text()
    import ast
    tree = ast.parse(src)
    stdlib_ok = {"argparse", "json", "os", "subprocess", "sys", "tempfile",
                 "tomllib", "pathlib", "re", "__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name.split(".")[0] in stdlib_ok for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in stdlib_ok


def test_ci_workflow_gates_prs_with_full_suite_and_wheel_smoke():
    text = (REPO / ".github/workflows/ci.yml").read_text()
    assert "pull_request" in text                                  # runs on PRs
    assert "wxcli-dist/assemble.py" in text                        # playbook freshness rebuild
    assert "pytest" in text                                        # offline suite
    assert "tools.drift_check --enforce" in text                   # drift gate
    assert "tools/wheel_playbook_smoke.py dist" in text            # installed-wheel smoke
    assert text.index("python -m build") < text.index("wheel_playbook_smoke")  # build before smoke


def test_smoke_checks_sanitized_mcp_and_env_backed_codex():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "wheel_playbook_smoke", REPO / "tools/wheel_playbook_smoke.py")
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    assert smoke.SANITIZED == ((".mcp.json", "YOUR_FLOW_STORE_TOKEN"),)
    assert smoke.ENV_BACKED == ((".codex/config.toml", "WEBEX_ACCESS_TOKEN"),)
