"""Tests for generate_commands.py — the CLI orchestrator that ties parser + renderer together."""

import json
import sys
from pathlib import Path

import pytest

from tools.generate_commands import generate_tag, merge_tags, should_skip_tag, main


FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_SPEC = FIXTURES / "mini-openapi.json"


@pytest.fixture
def spec():
    with open(FIXTURE_SPEC) as f:
        return json.load(f)


@pytest.fixture
def overrides():
    return {"omit_query_params": ["orgId"]}


# ── generate_tag ─────────────────────────────────────────────────────────────


class TestGenerateTag:
    def test_generates_file(self, spec, overrides, tmp_path):
        """generate_tag writes a .py file to the output directory."""
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        assert module == "things"
        assert cli == "things"
        assert count > 0
        out_file = tmp_path / "things.py"
        assert out_file.exists()
        assert len(out_file.read_text()) > 100

    def test_dry_run_no_file(self, spec, overrides, tmp_path, capsys):
        """dry_run=True prints info but writes no file."""
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, True, seen)
        assert count > 0
        assert not (tmp_path / "things.py").exists()
        captured = capsys.readouterr()
        assert "Things" in captured.out
        assert "things.py" in captured.out

    def test_dry_run_shows_commands(self, spec, overrides, tmp_path, capsys):
        """dry_run output lists each command with method and type."""
        seen = set()
        generate_tag("Things", spec, overrides, tmp_path, True, seen)
        captured = capsys.readouterr()
        assert "GET" in captured.out
        assert "POST" in captured.out
        assert "list" in captured.out

    def test_dry_run_shows_skipped_uploads(self, spec, overrides, tmp_path, capsys):
        """dry_run output shows skipped upload endpoints."""
        seen = set()
        generate_tag("Things", spec, overrides, tmp_path, True, seen)
        captured = capsys.readouterr()
        assert "SKIP" in captured.out
        assert "upload" in captured.out.lower()

    def test_cli_name_override(self, spec, tmp_path):
        """cli_name_overrides in overrides → uses override name."""
        overrides = {
            "omit_query_params": ["orgId"],
            "cli_name_overrides": {"Things": "my-things"},
        }
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        assert cli == "my-things"
        assert module == "my_things"
        assert (tmp_path / "my_things.py").exists()

    def test_auto_inject_from_config(self, spec, tmp_path):
        """auto_inject_from_config generates get_org_id() calls instead of CLI flags."""
        overrides = {
            "auto_inject_from_config": ["orgId"],
        }
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        code = (tmp_path / f"{module}.py").read_text()
        # orgId should NOT appear as a CLI flag (--org-id)
        assert "--org-id" not in code
        # But should appear as auto-injected from config
        assert "get_org_id" in code

    def test_seen_op_ids_shared(self, spec, overrides, tmp_path):
        """Seen operation IDs prevent duplicate processing across tags."""
        seen = set()
        _, _, count1 = generate_tag("Things", spec, overrides, tmp_path, True, seen)
        _, _, count2 = generate_tag("Things", spec, overrides, tmp_path, True, seen)
        assert count1 > 0
        assert count2 == 0  # All ops already seen

    def test_endpoint_overrides_applied(self, spec, tmp_path):
        """Folder-level overrides (e.g. table_columns) are applied."""
        overrides = {
            "omit_query_params": ["orgId"],
            "Things": {
                "list": {"table_columns": [["Custom", "customField"]]},
            },
        }
        seen = set()
        module, _, _ = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        code = (tmp_path / f"{module}.py").read_text()
        assert "customField" in code

    def test_generated_output_includes_registration_info(self, spec, overrides, tmp_path, capsys):
        """Non-dry-run prints total + registration block."""
        seen = set()
        generate_tag("Things", spec, overrides, tmp_path, False, seen)
        captured = capsys.readouterr()
        assert "Generated:" in captured.out
        assert "things.py" in captured.out


# ── main() via monkeypatch (in-process, so coverage tracks it) ───────────────


class TestMainCLI:
    """Test main() by monkeypatching sys.argv. Runs in-process for coverage."""

    def _run_main(self, monkeypatch, *args):
        """Patch sys.argv and call main(), catching SystemExit."""
        monkeypatch.setattr(sys, "argv", ["generate_commands", *args])
        try:
            main()
            return 0
        except SystemExit as e:
            return e.code or 0

    def test_list_tags(self, monkeypatch, capsys):
        """--list-tags prints all tags from the fixture spec."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--list-tags")
        assert rc == 0
        assert "Things" in capsys.readouterr().out

    def test_list_folders_alias(self, monkeypatch, capsys):
        """--list-folders is a backward-compat alias for --list-tags."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--list-folders")
        assert rc == 0
        assert "Things" in capsys.readouterr().out

    def test_dry_run_single_tag(self, monkeypatch, capsys, tmp_path):
        """--tag X --dry-run prints info, writes nothing."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "Things",
            "--dry-run", "--output", str(tmp_path),
        )
        assert rc == 0
        assert "Things" in capsys.readouterr().out
        assert not list(tmp_path.glob("*.py"))

    def test_generate_single_tag(self, monkeypatch, capsys, tmp_path):
        """--tag X writes a command file."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "Things",
            "--output", str(tmp_path),
        )
        assert rc == 0
        assert (tmp_path / "things.py").exists()

    def test_generate_all(self, monkeypatch, capsys, tmp_path):
        """--all generates files for all non-skipped tags."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--all",
            "--output", str(tmp_path),
        )
        assert rc == 0
        captured = capsys.readouterr().out
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) >= 5
        assert "Total:" in captured
        assert "Registration block" in captured

    def test_folder_alias(self, monkeypatch, capsys, tmp_path):
        """--folder is a backward-compat alias for --tag."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--folder", "Things",
            "--dry-run", "--output", str(tmp_path),
        )
        assert rc == 0
        assert "Things" in capsys.readouterr().out

    def test_missing_spec_exits_1(self, monkeypatch, capsys):
        """Non-existent spec file → exit 1 with error message."""
        rc = self._run_main(monkeypatch, "--spec", "/nonexistent/spec.json", "--list-tags")
        assert rc == 1
        assert "Spec not found" in capsys.readouterr().err

    def test_unknown_tag_exits_1(self, monkeypatch, capsys):
        """Non-existent tag → exit 1 with suggestion."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "Nonexistent")
        assert rc == 1
        assert "Tag not found" in capsys.readouterr().err

    def test_similar_tag_suggestion(self, monkeypatch, capsys):
        """Misspelled tag → 'Did you mean' suggestion."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "thing")
        assert rc == 1
        assert "Did you mean" in capsys.readouterr().err

    def test_no_args_shows_help(self, monkeypatch, capsys):
        """No arguments → shows help."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC))
        assert rc == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "Generate" in captured.out
