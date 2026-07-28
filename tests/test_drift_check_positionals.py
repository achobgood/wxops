"""Drift gate check 10: a documented `wxcli <group> <command> ...` example
must supply the number of POSITIONAL (typer.Argument) values the command
actually declares — not too many, not too few, and none at all on a command
that takes zero. A mismatch means a copy-pasted example aborts before doing
anything; checks 6/7 already prove a documented FLAG exists, but nothing
before this checked positionals.

Two classes must never be flagged, and each has its own case below:
  - a bare `wxcli <group> <command>` with no arguments at all, cited with
    single backticks OUTSIDE a fenced block, is a reference-table mention
    ("see `wxcli people show`"), not a broken runnable example;
  - a dev-only fs_* command module (gitignored, absent from the shipped
    wheel) must not contribute to the CLI-side signature surface, exactly
    like build_cli_surface/build_flag_surface already exclude it.

The same bare citation INSIDE a fenced code block IS a failure: it reads as
a copy-pasteable example missing a required argument.
"""

import textwrap

import pytest

from tools import drift_check as dc


@pytest.fixture(autouse=True)
def _reset_caches():
    dc._MODULE_STATE = None
    dc._IGNORE_CACHE.clear()
    yield
    dc._MODULE_STATE = None
    dc._IGNORE_CACHE.clear()


# ---------------------------------------------------------------- CLI side

def _probe_module(*bodies: str) -> str:
    return textwrap.dedent('''\
        """Probe module."""
        import typer

        app = typer.Typer()
        ''') + "\n".join(bodies)


ZERO_ARG_CMD = '''
@app.command("list")
def list_things(
    output: str = typer.Option("table", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Probe: zero positional args."""
'''

ONE_ARG_CMD = '''
@app.command("show")
def show_thing(
    thing_id: str = typer.Argument(help="thingId"),
    output: str = typer.Option("json", "--output", "-o"),
):
    """Probe: one required positional arg."""
'''


def test_parse_module_signatures_reads_positional_args(tmp_path):
    """The CLI-side half: typer.Argument -> args, typer.Option -> flags with
    takes-value recorded (needed to tell a real positional from a flag's
    value when walking documented tokens)."""
    (tmp_path / "probe.py").write_text(_probe_module(ZERO_ARG_CMD, ONE_ARG_CMD))
    sig = dc.parse_module_signatures("probe", commands_dir=tmp_path)
    assert sig["list"]["args"] == []
    assert sig["show"]["args"] == [("thing_id", True)]
    assert sig["show"]["flags"]["--output"] is True   # takes a value
    assert sig["list"]["flags"]["--debug"] is False   # bool flag on this command
    assert sig["list"]["flags"]["--help"] is False    # typer adds --help everywhere


def test_build_positional_surface_ignores_dev_only_fs_modules(monkeypatch):
    """fs_* modules are gitignored dev-only (absent from the shipped wheel);
    build_positional_surface must exclude them exactly like build_cli_surface
    and build_flag_surface already do — a doc citing an fs_* command's real
    signature must not silently pass check 10 just because the signature was
    never loaded (nor silently fail because a phantom entry appeared)."""
    probe = dc.COMMANDS_DIR / "fs_zz_test_probe.py"
    probe.write_text(_probe_module(ONE_ARG_CMD))
    real_registrations = dc.parse_registrations()
    try:
        monkeypatch.setattr(
            dc, "parse_registrations",
            lambda: {**real_registrations, "zz-probe-group": "fs_zz_test_probe"})
        surface = dc.build_positional_surface()
        assert "zz-probe-group" not in surface
    finally:
        probe.unlink(missing_ok=True)


def test_build_positional_surface_includes_a_countable_probe(monkeypatch):
    """The not-vacuous half of the case above: a probe module that is NOT
    fs_*-prefixed (present + not gitignored, same as check 8's "countable")
    DOES appear — proving the fs_* exclusion is real, not a check that never
    fires either way."""
    probe = dc.COMMANDS_DIR / "zz_test_probe.py"
    probe.write_text(_probe_module(ONE_ARG_CMD))
    real_registrations = dc.parse_registrations()
    try:
        monkeypatch.setattr(
            dc, "parse_registrations",
            lambda: {**real_registrations, "zz-probe-group": "zz_test_probe"})
        surface = dc.build_positional_surface()
        assert surface["zz-probe-group"]["show"]["args"] == [("thing_id", True)]
    finally:
        probe.unlink(missing_ok=True)


# ---------------------------------------------------------------- doc side

def _run(tmp_path, monkeypatch, doc_text, surface, positional_surface):
    """Point check 10's scan at exactly one fixture file, standing in for
    docs/reference/**. tracked_files is patched per-pattern (not blanket) so
    the fixture isn't scanned once per SCAN_PATTERNS entry (6x duplicates)."""
    doc = tmp_path / "fixture.md"
    doc.write_text(doc_text)

    def fake_tracked_files(pattern):
        return [str(doc)] if pattern == "docs/reference/**" else []

    monkeypatch.setattr(dc, "tracked_files", fake_tracked_files)
    return dc.check_positionals(surface, positional_surface)


SHOW_SURFACE = {"probe-group": {"show": []}}
SHOW_SIG = {"probe-group": {"show": {
    "args": [("thing_id", True)], "flags": {"--help": False}}}}

LIST_SURFACE = {"probe-group": {"list": []}}
LIST_SIG = {"probe-group": {"list": {
    "args": [], "flags": {"--help": False}}}}


def test_too_many_positionals_fails(tmp_path, monkeypatch):
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group show THING_ID EXTRA_ID
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert [f["kind"] for f in findings] == ["too_many"]
    assert findings[0]["supplied"] == 2 and findings[0]["total"] == 1
    assert bare == 0


def test_too_few_positionals_fails(tmp_path, monkeypatch):
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group show --output json
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert [f["kind"] for f in findings] == ["too_few"]
    assert findings[0]["supplied"] == 0 and findings[0]["need"] == 1
    assert bare == 0


def test_positional_on_zero_arg_command_fails(tmp_path, monkeypatch):
    """The single most common real-world case (54 of the 85 ground-truth
    findings): an orgId or resource id typed positionally on a command whose
    real value comes from a flag or injected config, not an Argument."""
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group list ORG_ID
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, LIST_SURFACE, LIST_SIG)
    assert [f["kind"] for f in findings] == ["positional_on_zero_arg"]
    assert findings[0]["supplied"] == 1 and findings[0]["total"] == 0
    assert bare == 0


def test_bare_name_citation_outside_fenced_block_does_not_fail(tmp_path, monkeypatch):
    """A reference-table mention with no arguments at all, cited inline
    (single backticks, no fence) is incomplete, not broken — it still fails
    loudly at runtime rather than silently. Must not fail the gate."""
    doc = "See `wxcli probe-group show` for details.\n"
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert findings == []
    assert bare == 1


def test_same_bare_citation_inside_fenced_block_does_fail(tmp_path, monkeypatch):
    """The same zero-argument citation, but presented as a runnable example
    inside a fenced code block, reads as copy-pasteable and IS a failure."""
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group show
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert [f["kind"] for f in findings] == ["too_few"]
    assert bare == 0


def test_matching_positional_count_passes(tmp_path, monkeypatch):
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group show THING_ID -o json
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert findings == []
    assert bare == 0


def test_unresolved_command_is_left_to_check_2(tmp_path, monkeypatch):
    """A group/command that doesn't resolve against the CLI at all is check
    2's job (dead references); check 10 must skip it rather than double-report
    or crash on a missing signature."""
    doc = textwrap.dedent('''\
        ```bash
        wxcli nonexistent-group made-up-command THING_ID EXTRA
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, {}, {})
    assert findings == []
    assert bare == 0


def test_multiline_json_body_with_an_apostrophe_does_not_swallow_the_next_line(
        tmp_path, monkeypatch):
    """Regression: a multi-line --json-body '{ ... }' block must be joined
    (join_quotes) so the invocation tokenizes at all, but an apostrophe in
    unrelated PROSE sharing the fence (e.g. "the user's inputs") must NOT
    open a quote that swallows every following line up to fence-close — that
    false merge previously manufactured 8 phantom positional tokens on an
    unrelated, later citation in this repo's own docs (messaging-bots.md)."""
    doc = textwrap.dedent('''\
        ```
        1. Do a thing with the user's data

        2. wxcli probe-group show THING_ID
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert findings == []
    assert bare == 0


def test_trailing_shell_comment_is_not_counted_as_a_positional(tmp_path, monkeypatch):
    """Regression: `wxcli probe-group list  # Get the IDs` must not tokenize
    the comment text as 4 phantom positional arguments — arg_region's
    strip_comment (check 10 only; check 6 never needed it, since its
    FLAG_CITE regex only matches `--flag`-shaped tokens)."""
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group list                       # Get the IDs
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, LIST_SURFACE, LIST_SIG)
    assert findings == []
    assert bare == 0


def test_continuation_backslash_before_a_comment_is_not_a_phantom_token(
        tmp_path, monkeypatch):
    """Regression: `wxcli probe-group list \\    # comment` — code_spans only
    recognizes a continuation when `\\` is the line's literal last character,
    so with trailing prose the line is never joined, and comment-stripping
    then leaves a bare `\\` dangling. Left in, posix shlex reads it as an
    escaped space and manufactures a phantom positional."""
    doc = textwrap.dedent('''\
        ```bash
        wxcli probe-group list \\    # Extract from somewhere
          --output json
        ```
        ''')
    findings, bare = _run(tmp_path, monkeypatch, doc, LIST_SURFACE, LIST_SIG)
    assert findings == []
    assert bare == 0


def test_ellipsis_elided_example_is_not_a_too_few_finding(tmp_path, monkeypatch):
    """`wxcli probe-group show ...` is an explicitly elided example, not a
    broken one."""
    doc = "`wxcli probe-group show ...`\n"
    findings, bare = _run(tmp_path, monkeypatch, doc, SHOW_SURFACE, SHOW_SIG)
    assert findings == []
    assert bare == 0


# --- shell redirects must not manufacture positionals -----------------------
# Found live: 15 of teardown/SKILL.md's 16 findings were this artifact and
# nothing else, on lines whose documented arguments were already correct.
# `arg_region` stopped the region at the `>` of `2>&1`, which left the file
# descriptor `2` behind as a bare token; shlex read it as its own word and
# check 10 counted it as an extra positional. It hit EVERY line ending in a
# redirect regardless of the real arguments, and inflated check 10 by ~111.

import pytest

from tools.drift_check import arg_region


@pytest.mark.parametrize("rest,expected", [
    (" --location-id $LOC -o json 2>&1", "--location-id $LOC -o json"),
    (" LOC_ID -o json 2>&1",             "LOC_ID -o json"),
    (" --name x 2>/dev/null",            "--name x"),
    (" PERSON_ID 2>&1 | tee log",        "PERSON_ID"),
    (" -o json > out.txt",               "-o json"),
])
def test_fd_redirect_does_not_leave_a_phantom_positional(rest, expected):
    assert arg_region(rest).strip() == expected


def test_a_real_argument_ending_in_a_digit_survives():
    """Only a LONE digit before the redirect is dropped. `SITE2 > out` must
    keep SITE2 — stripping any trailing digit would delete real arguments."""
    assert arg_region(" SITE2 > out").strip() == "SITE2"


def test_angle_bracket_placeholders_are_still_not_redirects():
    """Examples are written `--location-id <loc_id> --paging-id <pg_id>`;
    treating the `>` of a placeholder as a redirect truncates the line and
    silently skips every flag after the first one."""
    rest = " --location-id <loc_id> --paging-id <pg_id>"
    assert arg_region(rest).strip() == rest.strip()
