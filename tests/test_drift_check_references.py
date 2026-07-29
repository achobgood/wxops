"""Drift gate check 2 allowlist scoping: `ref <file> <group>` /
`ref <file> <group> <command>` exempt a dead reference only in the ONE file
that has a documented reason for it, unlike the bare `<group>` /
`<group> <command>` forms which exempt everywhere.

Regression cover for a live false negative: `user-call-settings` was
allowlisted bare for a deliberate negative example in
.claude/skills/manage-devices/SKILL.md ("that group does not exist"). Because
the allowlist check was `entry in allow or group in allow` with no file
scoping, the same bare entry also silently exempted 6 genuinely broken
citations of the same wrong group name in
docs/reference/person-call-settings-behavior.md. The allowlist's own header
says "Do NOT add real commands here to silence the gate" — the bare-group
form made that rule unenforceable for any name that happens to be both a
deliberate negative example somewhere AND a real typo elsewhere.
"""

from tools import drift_check as dc


def _write_docs(tmp_path, files: dict[str, str]) -> dict[str, str]:
    """{relative-name: content} -> {relative-name: absolute path written}."""
    paths = {}
    for name, text in files.items():
        p = tmp_path / name
        p.write_text(text)
        paths[name] = str(p)
    return paths


def _run(monkeypatch, paths: dict[str, str], allow: set[str],
        surface: dict | None = None, top_level: set | None = None):
    """Point check 2's scan at exactly these fixture files, standing in for
    docs/reference/**. tracked_files is patched per-pattern (not blanket) so
    the fixtures aren't scanned once per SCAN_PATTERNS entry (6x duplicates).

    tracked_files returns ABSOLUTE paths (the same `REPO / rel` returns rel
    unchanged trick check_table_columns's tests use) — so `rel` inside
    check_references, and therefore any "ref <rel> ..." allowlist entry, is
    the absolute path, not the short fixture name. Callers build `allow`
    from the `paths` dict this returns for exactly that reason.
    """
    def fake_tracked_files(pattern):
        return sorted(paths.values()) if pattern == "docs/reference/**" else []

    monkeypatch.setattr(dc, "tracked_files", fake_tracked_files)
    monkeypatch.setattr(dc, "load_allowlist", lambda: allow)
    dead, _group_refs, _prefixless = dc.check_references(
        surface or {}, top_level or set())
    by_abs = {v: k for k, v in paths.items()}
    return [{**d, "file": by_abs[d["file"]]} for d in dead]


UNKNOWN_GROUP = "zz-unknown-group"


def test_bare_entry_exempts_every_file(tmp_path, monkeypatch):
    paths = _write_docs(tmp_path, {"a.md": f"`wxcli {UNKNOWN_GROUP} show THING`\n",
                                    "b.md": f"`wxcli {UNKNOWN_GROUP} show THING`\n"})
    dead = _run(monkeypatch, paths, allow={UNKNOWN_GROUP})
    assert dead == []


def test_file_scoped_entry_exempts_only_its_own_file(tmp_path, monkeypatch):
    """The core regression: a.md's citation is the documented negative
    example and stays exempt; b.md's identical citation has no such
    documentation attached and must surface as a real dead reference."""
    paths = _write_docs(tmp_path, {"a.md": f"`wxcli {UNKNOWN_GROUP} show THING`\n",
                                    "b.md": f"`wxcli {UNKNOWN_GROUP} show THING`\n"})
    dead = _run(monkeypatch, paths, allow={f"ref {paths['a.md']} {UNKNOWN_GROUP}"})
    assert [d["file"] for d in dead] == ["b.md"]
    assert dead[0]["kind"] == "group"
    assert dead[0]["ref"] == f"wxcli {UNKNOWN_GROUP}"


def test_no_allowlist_entry_flags_both_files(tmp_path, monkeypatch):
    """The not-vacuous half: with no exemption at all, both files are
    flagged — proving the exemptions above are doing real work, not just
    matching a check that never fires."""
    paths = _write_docs(tmp_path, {"a.md": f"`wxcli {UNKNOWN_GROUP} show THING`\n",
                                    "b.md": f"`wxcli {UNKNOWN_GROUP} show THING`\n"})
    dead = _run(monkeypatch, paths, allow=set())
    assert sorted(d["file"] for d in dead) == ["a.md", "b.md"]


PROBE_SURFACE = {"probe-group": {"real-cmd": []}}


def test_file_scoped_group_command_form_exempts_only_that_pair(tmp_path, monkeypatch):
    """The narrower `ref <file> <group> <command>` form: probe-group itself
    resolves (it's a real group), so a citation of a command it does NOT
    declare is a "command"-kind dead ref, not "group"-kind. The file-scoped
    exemption for one fake command must not swallow a second, different
    fake command in the same file."""
    paths = _write_docs(tmp_path, {"a.md": ("`wxcli probe-group fake-one THING`\n"
                                            "`wxcli probe-group fake-two THING`\n")})
    dead = _run(monkeypatch, paths,
                allow={f"ref {paths['a.md']} probe-group fake-one"},
                surface=PROBE_SURFACE)
    assert [(d["file"], d["ref"], d["kind"]) for d in dead] == [
        ("a.md", "wxcli probe-group fake-two", "command")]


def test_file_scoped_group_command_form_does_not_leak_to_other_files(tmp_path, monkeypatch):
    paths = _write_docs(tmp_path, {"a.md": "`wxcli probe-group fake-one THING`\n",
                                    "b.md": "`wxcli probe-group fake-one THING`\n"})
    dead = _run(monkeypatch, paths,
                allow={f"ref {paths['a.md']} probe-group fake-one"},
                surface=PROBE_SURFACE)
    assert [d["file"] for d in dead] == ["b.md"]


def test_the_live_tree_has_no_dead_references():
    """The live tree must stay clean.

    This test originally asserted exactly 6 dead references — the
    user-call-settings citations in person-call-settings-behavior.md that a
    too-broad allowlist entry had been hiding. Those are now FIXED (the doc
    names `user-settings`, and the two citations whose VERB was also wrong say
    list-reception / list-push-to-talk), so the expectation moved to zero.

    Asserting zero rather than a count is the stronger form: any newly hidden
    dead reference fails here, not just the ones we happened to know about.
    The narrow, file-scoped exemption is covered by the fixture tests above,
    which is where that behaviour belongs.
    """
    surface, top_level = dc.build_cli_surface()
    dead, _, _ = dc.check_references(surface, top_level)
    assert dead == [], (
        f"{len(dead)} dead wxcli reference(s): "
        + ", ".join(f"{d['file']}:{d['line']} {d['ref']}" for d in dead[:10])
    )
