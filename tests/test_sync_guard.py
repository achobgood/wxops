"""sync_guard: the unattended agent may change generated artifacts and docs,
never the definitions of what passes (spec §5.5). Every escape hatch the gate
has is a writable line whose justification only a human checks — so the run
fails closed if its own diff touches one. Paired fires / does-not-fire.
"""
import json

from tools import sync_guard as sg

YAML_OLD = """
skip_tags:
  _global:
    - "Beta *"
naming_ack:
  "numeric-suffix POST /v1/x":
    command: a b
    severity: HIGH
cli_name_overrides:
  _global:
    "Search Metadata": "cc-search-metadata"
tag_overrides:
  webex-meetings.json:
    "Meetings":
      command_name_overrides:
        "create-meetings": "create"
      table_columns:
        list: [["ID", "id"]]
"""


def test_allowed_keys_do_not_fire():
    new = YAML_OLD.replace('"Search Metadata": "cc-search-metadata"',
                           '"Search Metadata": "cc-search-metadata"\n    "New Tag": "new-tag"')
    new = new.replace('"create-meetings": "create"',
                      '"create-meetings": "create"\n        "update-meetings": "update"')
    assert sg.yaml_key_findings(YAML_OLD, new) == []


def test_each_forbidden_key_fires():
    cases = {
        "skip_tags": YAML_OLD.replace('- "Beta *"', '- "Beta *"\n    - "Zeta *"'),
        "naming_ack": YAML_OLD.replace(
            "severity: HIGH",
            'severity: HIGH\n  "bare-verb GET /v1/y":\n    command: c d\n    severity: HIGH'),
    }
    for key, new in cases.items():
        findings = sg.yaml_key_findings(YAML_OLD, new)
        assert findings and key in findings[0], (key, findings)


def test_tag_overrides_other_than_command_names_fire():
    new = YAML_OLD.replace('list: [["ID", "id"]]', 'list: [["Name", "name"]]')
    findings = sg.yaml_key_findings(YAML_OLD, new)
    assert findings and "table_columns" in findings[0]


def test_deleting_a_forbidden_key_also_fires():
    new = YAML_OLD.replace('    - "Beta *"\n', "")
    assert sg.yaml_key_findings(YAML_OLD, new)


CLAUDE_OLD = """# x
## Out-of-Skill-Scope Command Groups
| `partner-tags` | reason |
## Next
`something-else`
"""


def test_out_of_scope_table_edit_fires_and_other_sections_do_not():
    assert sg.out_of_scope_findings(CLAUDE_OLD, CLAUDE_OLD.replace("`something-else`", "`another`")) == []
    assert sg.out_of_scope_findings(CLAUDE_OLD, CLAUDE_OLD.replace("| `partner-tags` | reason |",
                                                                    "| `partner-tags` | reason |\n| `*` | all |"))


def _lock(m):
    return json.dumps({"modules": m})


def test_lock_additive_is_fine_but_modify_or_delete_fires():
    old = _lock({"meetings": {"create": ["POST /meetings"]}})
    assert sg.lock_findings(old, _lock({"meetings": {"create": ["POST /meetings"], "list": ["GET /meetings"]},
                                        "new_mod": {"show": ["GET /n"]}})) == []
    assert sg.lock_findings(old, _lock({"meetings": {"create": ["POST /group"]}}))
    assert sg.lock_findings(old, _lock({"meetings": {}}))
    assert sg.lock_findings(old, _lock({}))


def test_forbidden_paths_fire_by_prefix():
    assert sg.path_findings(["tools/drift_check.py"])
    assert sg.path_findings([".github/workflows/ci.yml"])
    assert sg.path_findings(["tools/sync_guard.py"])
    assert sg.path_findings(["docs/spec-sync-contract.md"])
    assert sg.path_findings(["src/wxcli/commands/meetings.py", "docs/reference/x.md",
                             "tools/field_overrides.yaml", "tools/command_name_lock.json"]) == []
    # The master plan forbids `tools/sync_*.py` as a glob, not just the three we can name today.
    assert sg.path_findings(["tools/sync_future.py"])
    assert sg.path_findings(["tools/sync_guard.py"])
    assert sg.path_findings(["tools/synchronize.py"]) == []


def test_kill_switch():
    assert sg.pipeline_enabled("**Pipeline:** enabled\n") is True
    assert sg.pipeline_enabled("**Pipeline:** disabled — reason\n") is False
    assert sg.pipeline_enabled("no such line\n") is None


def test_guard_against_a_real_git_base(tmp_path):
    """End to end on a throwaway repo: a naming_ack edit fails, a doc edit passes."""
    import subprocess
    r = tmp_path
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=r, check=True)
    (r / "tools").mkdir(); (r / "docs").mkdir()
    (r / "tools" / "field_overrides.yaml").write_text(YAML_OLD)
    (r / "tools" / "command_name_lock.json").write_text(_lock({"m": {"a": []}}))
    (r / "CLAUDE.md").write_text(CLAUDE_OLD)
    (r / "docs" / "x.md").write_text("hi\n")
    subprocess.run(["git", "add", "-A"], cwd=r, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], cwd=r, check=True)
    (r / "docs" / "x.md").write_text("changed\n")
    assert sg.guard("HEAD", r) == []
    (r / "tools" / "field_overrides.yaml").write_text(YAML_OLD.replace('- "Beta *"', '- "Beta *"\n    - "Zeta *"'))
    findings = sg.guard("HEAD", r)
    assert findings and "skip_tags" in findings[0]


def _repo_with_drift_check(root):
    """A throwaway repo whose only tracked file is a forbidden path, committed."""
    import subprocess
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / "tools").mkdir()
    (root / "tools" / "drift_check.py").write_text("# the gate\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
                   cwd=root, check=True)
    return subprocess


def test_a_renamed_forbidden_file_still_fires(tmp_path):
    """git's rename detection would show only the NEW path, hiding the forbidden one."""
    r = tmp_path / "renamed"
    subprocess = _repo_with_drift_check(r)
    subprocess.run(["git", "mv", "tools/drift_check.py", "tools/dc.py"], cwd=r, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "rename"],
                   cwd=r, check=True)
    findings = sg.guard("HEAD~1", r)
    assert any("tools/drift_check.py" in f for f in findings), findings

    d = tmp_path / "deleted"
    subprocess = _repo_with_drift_check(d)
    subprocess.run(["git", "rm", "-q", "tools/drift_check.py"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "delete"],
                   cwd=d, check=True)
    findings = sg.guard("HEAD~1", d)
    assert any("tools/drift_check.py" in f for f in findings), findings
