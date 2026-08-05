"""Check 21 — a destructive operation's command carries a confirmation gate.

Guards the assertion `02-drift.md` F3 found nothing was making. The cost of its
absence was measured by mutation in audit Phase 4: deleting every
`_render_destructive_gate` call site from `tools/command_renderer.py`
regenerates cleanly, drops all 24 confirmation gates added on 2026-08-04, and
reports drift-gate PASS with 415/415 tracked tests green.

Paired does-not-fire / does-fire cases throughout. The check-9 suite once had
6 of 8 cases passing without ever reaching the check, so every "clean" case
here has a mutated twin that must fail — a suite where only the clean cases
pass proves nothing.

Stdlib + pytest only. Imports `tools.*` (resolved by pyproject's
`pythonpath = ["."]`), never `wxcli`. No network, no live API, no dependency on
the untracked tests/conftest.py.
"""
import ast
import textwrap

import pytest

from tools.drift_check import (
    build_confirm_surface,
    check_confirm_gates,
    destructive_spec_ops,
    load_overrides,
    load_spec_ops,
    parse_module_confirms,
)


OP = ("POST", "/organization/{}/auxiliary-code/purge-inactive-entities")
SURFACE = {"cc-aux-code": {"delete-purge-inactive-entities": [OP]}}
DESTRUCTIVE = {OP: "purge"}


class TestCheckFiresAndDoesNot:
    def test_gated_destructive_op_is_not_a_finding(self):
        findings = check_confirm_gates(
            SURFACE, {OP: ("spec.json", "tag")},
            confirms={"cc-aux-code": {"delete-purge-inactive-entities": True}},
            destructive=DESTRUCTIVE)
        assert findings == []

    def test_ungated_destructive_op_IS_a_finding(self):
        findings = check_confirm_gates(
            SURFACE, {OP: ("spec.json", "tag")},
            confirms={"cc-aux-code": {"delete-purge-inactive-entities": False}},
            destructive=DESTRUCTIVE)
        assert len(findings) == 1
        assert findings[0]["command"] == "delete-purge-inactive-entities"
        assert findings[0]["verb"] == "purge"

    def test_ungated_NON_destructive_op_is_not_a_finding(self):
        """The check is scoped to what the generator flags, and nothing else.

        A plain `create` with no confirm is correct, not a finding. Without
        this case the check could pass its does-fire test by simply flagging
        every ungated write — 755 of them.
        """
        findings = check_confirm_gates(
            SURFACE, {OP: ("spec.json", "tag")},
            confirms={"cc-aux-code": {"delete-purge-inactive-entities": False}},
            destructive={})
        assert findings == []

    def test_op_with_no_rendered_command_is_not_a_finding(self):
        """A destructive op in a skipped tag has no command to gate."""
        findings = check_confirm_gates(
            {}, {OP: ("spec.json", "tag")},
            confirms={}, destructive=DESTRUCTIVE)
        assert findings == []


class TestConfirmDetectionIsAstNotSubstring:
    """`05-safety.md` 2 measured the difference: a substring test over the
    dumped function reports 208 gated commands where the parse tree reports
    203, over-counting by 5 on commands whose HELP TEXT contains the word."""

    def _confirms(self, tmp_path, monkeypatch, src):
        import tools.drift_check as dc
        mod = tmp_path / "fake_group.py"
        mod.write_text(textwrap.dedent(src))
        monkeypatch.setattr(dc, "COMMANDS_DIR", tmp_path)
        return parse_module_confirms("fake_group")

    def test_real_confirm_is_detected(self, tmp_path, monkeypatch):
        out = self._confirms(tmp_path, monkeypatch, '''
            @app.command("delete")
            def delete(force: bool = typer.Option(False, "--force")):
                """Delete a thing."""
                if not force:
                    typer.confirm("Delete this?", abort=True)
            ''')
        assert out == {"delete": True}

    def test_the_word_confirm_in_help_text_is_NOT_a_gate(self, tmp_path, monkeypatch):
        out = self._confirms(tmp_path, monkeypatch, '''
            @app.command("delete")
            def delete(
                force: bool = typer.Option(False, "--force",
                                           help="Skip confirmation prompt"),
            ):
                """Delete a thing. Ask the user to confirm first."""
                pass
            ''')
        assert out == {"delete": False}, (
            "a substring test would call this gated; it has no typer.confirm")


class TestRenamedCommandsResolveUnderBothNames:
    """Regression for `02-drift.md` F1, which broke this check in development.

    `build_cli_surface` (via `parse_module_commands`) emits an entry per
    DECORATOR, so a renamed command appears under its hidden legacy alias AND
    its visible name. `_command_name` returns only the first. Keying the
    confirm surface on `_command_name` left every renamed destructive command
    looking ungated: the check reported 15 findings on a tree where all 15 were
    correctly gated. A confirm is a property of the FUNCTION, so both names
    must carry the function's answer.
    """

    def test_both_decorator_names_carry_the_functions_answer(
            self, tmp_path, monkeypatch):
        import tools.drift_check as dc
        mod = tmp_path / "fake_group.py"
        mod.write_text(textwrap.dedent('''
            @app.command("create-purge-inactive-entities", hidden=True)
            @app.command("delete-purge-inactive-entities")
            def delete_purge_inactive_entities(force: bool = None):
                """Purge inactive Auxiliary Code(s)."""
                if not force:
                    typer.confirm("Purge Inactive Entities?", abort=True)
            '''))
        monkeypatch.setattr(dc, "COMMANDS_DIR", tmp_path)
        out = parse_module_confirms("fake_group")
        assert out == {
            "create-purge-inactive-entities": True,
            "delete-purge-inactive-entities": True,
        }

    def test_an_ungated_renamed_command_is_False_under_both_names(
            self, tmp_path, monkeypatch):
        import tools.drift_check as dc
        mod = tmp_path / "fake_group.py"
        mod.write_text(textwrap.dedent('''
            @app.command("create-purge-inactive-entities", hidden=True)
            @app.command("delete-purge-inactive-entities")
            def delete_purge_inactive_entities(force: bool = None):
                """Purge inactive Auxiliary Code(s)."""
                pass
            '''))
        monkeypatch.setattr(dc, "COMMANDS_DIR", tmp_path)
        assert parse_module_confirms("fake_group") == {
            "create-purge-inactive-entities": False,
            "delete-purge-inactive-entities": False,
        }


class TestAgainstTheRealTree:
    """The check must be able to see the real corpus, not only fixtures."""

    def test_the_classifier_finds_the_known_destructive_population(self):
        spec_ops, _ = load_spec_ops(load_overrides()["skip_tags"])
        destructive = destructive_spec_ops(spec_ops)
        # 199 destructive operations across the 9 tracked specs is the figure
        # the audit spec states and Phase 5 re-measured; restricted here to the
        # rendered (non-skipped) ones, which is what this check can act on.
        assert len(destructive) > 100, (
            f"classifier found only {len(destructive)} destructive ops — it has "
            "stopped seeing the corpus, and a check that finds nothing to "
            "check reports a confident 0")
        assert any(v == "purge" for v in destructive.values())
        assert any(v == "delete" for v in destructive.values())

    def test_confirm_surface_covers_the_registered_groups(self):
        confirms = build_confirm_surface()
        assert len(confirms) > 150, f"only {len(confirms)} groups seen"
        gated = sum(1 for cmds in confirms.values() for v in cmds.values() if v)
        assert gated > 150, (
            f"only {gated} gated commands found; 179 DELETE gates alone are "
            "expected to be present")
