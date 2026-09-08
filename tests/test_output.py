import json
import re
from wxcli.output import format_as_json, _resolve_accessor

def test_format_json_list():
    data = [{"id": "1", "name": "Test"}]
    result = format_as_json(data)
    parsed = json.loads(result)
    assert parsed == [{"id": "1", "name": "Test"}]

def test_format_json_single():
    data = {"id": "1", "name": "Test"}
    result = format_as_json(data)
    parsed = json.loads(result)
    assert parsed == {"id": "1", "name": "Test"}

def test_resolve_accessor_dict():
    data = {"name": "Wilmington", "address": {"city": "Wilmington"}}
    assert _resolve_accessor(data, "name") == "Wilmington"
    assert _resolve_accessor(data, "address.city") == "Wilmington"

def test_resolve_accessor_missing():
    data = {"name": "Test"}
    assert _resolve_accessor(data, "nonexistent") is None
    assert _resolve_accessor(data, "a.b.c") is None

def test_resolve_accessor_list():
    """_resolve_accessor returns the raw list — no silent first-element
    reduction. Rendering (truncate-with-count) is _render_cell's job."""
    data = {"emails": ["a@b.com", "c@d.com"]}
    assert _resolve_accessor(data, "emails") == ["a@b.com", "c@d.com"]

class FakeObj:
    def __init__(self):
        self.name = "Test"
        self.nested = type("N", (), {"city": "Wilmington"})()

def test_resolve_accessor_object():
    obj = FakeObj()
    assert _resolve_accessor(obj, "name") == "Test"
    assert _resolve_accessor(obj, "nested.city") == "Wilmington"


import io
import sys
import pytest
from wxcli.output import plain_mode, print_table

BOX_CHARS = set("┏━┓┃┡┩│└┘├┤┬┴┼─╭╮╰╯┳╇")


def _render(monkeypatch, *, tty: bool, env=None):
    monkeypatch.delenv("WXCLI_PLAIN", raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    buf = io.StringIO()
    buf.isatty = lambda: tty          # noqa: E731 - Console consults this
    monkeypatch.setattr(sys, "stdout", buf)
    import wxcli.output as out
    monkeypatch.setattr(out, "console", out._make_console())
    print_table([{"id": "a", "name": "Sales"}], columns=[("ID", "id"), ("Name", "name")])
    return buf.getvalue()


def test_piped_output_has_no_box_characters(monkeypatch):
    text = _render(monkeypatch, tty=False)
    assert not (set(text) & BOX_CHARS), f"box chars leaked: {sorted(set(text) & BOX_CHARS)}"
    assert "Sales" in text and "Name" in text


def test_terminal_output_keeps_the_box(monkeypatch):
    text = _render(monkeypatch, tty=True)
    assert set(text) & BOX_CHARS, "terminal output must keep the Rich table box"


def test_wxcli_plain_forces_plain_in_a_terminal(monkeypatch):
    text = _render(monkeypatch, tty=True, env={"WXCLI_PLAIN": "1"})
    assert not (set(text) & BOX_CHARS)


def test_wxcli_plain_zero_forces_rich_when_piped(monkeypatch):
    text = _render(monkeypatch, tty=False, env={"WXCLI_PLAIN": "0"})
    assert set(text) & BOX_CHARS


def test_plain_mode_respects_the_override(monkeypatch):
    monkeypatch.setenv("WXCLI_PLAIN", "1")
    assert plain_mode() is True
    monkeypatch.setenv("WXCLI_PLAIN", "0")
    assert plain_mode() is False


def test_plain_mode_override_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("WXCLI_PLAIN", "FALSE")
    assert plain_mode() is False
    monkeypatch.setenv("WXCLI_PLAIN", "False")
    assert plain_mode() is False
    monkeypatch.setenv("WXCLI_PLAIN", "No")
    assert plain_mode() is False
    monkeypatch.setenv("WXCLI_PLAIN", "NO")
    assert plain_mode() is False
    monkeypatch.setenv("WXCLI_PLAIN", "TRUE")
    assert plain_mode() is True
    monkeypatch.setenv("WXCLI_PLAIN", "1")
    assert plain_mode() is True


def test_column_content_is_unchanged_between_modes(monkeypatch):
    """Only the decoration differs — never the data."""
    plain = _render(monkeypatch, tty=False)
    rich = _render(monkeypatch, tty=True)
    strip = lambda s: "".join(c for c in re.sub(r"\x1b\[[0-9;]*m", "", s) if c not in BOX_CHARS).split()  # noqa: E731
    assert strip(plain) == strip(rich)


def test_piped_table_does_not_truncate_long_values(monkeypatch):
    """Defect 5: Rich defaults to 80 columns when stdout isn't a terminal and
    silently ellipsis-truncates any cell that doesn't fit. An agent reading a
    truncated ID has no way to tell it apart from a whole one, and 404s on
    the next call. A value well over 80 characters must survive intact.
    """
    long_id = "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8" + "X" * 90
    long_email = "someone.with.a.really.long.name.that.keeps.going@" + "example-" * 6 + "com"
    assert len(long_id) > 80
    assert len(long_email) > 80

    monkeypatch.delenv("WXCLI_PLAIN", raising=False)
    buf = io.StringIO()
    buf.isatty = lambda: False
    monkeypatch.setattr(sys, "stdout", buf)
    import wxcli.output as out
    monkeypatch.setattr(out, "console", out._make_console())
    print_table(
        [{"id": long_id, "name": "Sales Queue Reception", "email": long_email}],
        columns=[("ID", "id"), ("Name", "name"), ("Email", "email")],
    )
    text = buf.getvalue()
    assert long_id in text
    assert long_email in text
    assert "…" not in text
    # One record per line: header line + exactly one data line.
    assert len([ln for ln in text.split("\n") if ln.strip()]) == 2


def test_tty_table_rendering_is_byte_for_byte_unchanged(monkeypatch):
    """Defect 5 fix must not touch the human-terminal path at all. This is
    the exact byte string produced by the pre-fix code for a real terminal
    (captured from git HEAD before this change) — pinned so any future
    change to the TTY path fails loudly here.
    """
    text = _render(monkeypatch, tty=True)
    assert text == (
        "┏━━━━┳━━━━━━━┓\n"
        "┃\x1b[1m \x1b[0m\x1b[1mID\x1b[0m\x1b[1m \x1b[0m┃\x1b[1m \x1b[0m\x1b[1mName \x1b[0m\x1b[1m \x1b[0m┃\n"
        "┡━━━━╇━━━━━━━┩\n"
        "│ a  │ Sales │\n"
        "└────┴───────┘\n"
    )


def test_text_output_heterogeneous_keys_stay_aligned():
    """Defect 6: Webex omits absent optional fields per record (e.g.
    `extension` only appears for calling-licensed users). Without a shared
    column order across records, a record missing a field shifts every
    later column, so `cut -f4` silently returns the wrong value for that
    row. Every row must have the same field count, and a named field must
    land in the same tab position on every row.
    """
    from wxcli.output import print_text

    data = [
        {"id": "P1", "name": "Ann", "extension": "1001", "locationId": "L1"},
        {"id": "P2", "name": "Bob", "locationId": "L1"},  # no extension
        {"id": "P3", "name": "Cy", "extension": "1003", "locationId": "L1"},
    ]
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        print_text(data)
    finally:
        sys.stdout = old_stdout

    lines = buf.getvalue().rstrip("\n").split("\n")
    assert len(lines) == 3
    rows = [ln.split("\t") for ln in lines]
    field_counts = {len(r) for r in rows}
    assert field_counts == {4}, f"rows have differing field counts: {rows}"

    # "extension" was first seen at index 2 (id, name, extension, locationId).
    assert rows[0][2] == "1001"
    assert rows[1][2] == ""       # Bob's record omitted extension
    assert rows[2][2] == "1003"
    # locationId (index 3) is unaffected and present on every row.
    assert rows[0][3] == rows[1][3] == rows[2][3] == "L1"


# ── list/dict cell rendering (Wave 2a) ──────────────────────────────────────

from wxcli.output import _render_cell, print_json


def test_render_cell_multi_element_list():
    """A 3-element list must be visibly distinct from a 1-element list."""
    assert _render_cell(["a@b.com", "c@d.com", "e@f.com"]) == "a@b.com (+2 more)"


def test_render_cell_single_element_list():
    assert _render_cell(["a@b.com"]) == "a@b.com"


def test_render_cell_empty_list():
    assert _render_cell([]) == ""


def test_render_cell_dict():
    addr = {"address1": "170 W Tasman Dr", "city": "San Jose", "state": "CA",
             "postalCode": "95134", "country": "US"}
    rendered = _render_cell(addr)
    assert "{'" not in rendered and "{" not in rendered  # no Python repr
    assert rendered == (
        "address1: 170 W Tasman Dr, city: San Jose, state: CA, "
        "postalCode: 95134, country: US"
    )


def test_render_cell_nested_dict():
    data = {"city": "San Jose", "geo": {"lat": 37.4, "lng": -121.9}}
    rendered = _render_cell(data)
    assert "{'" not in rendered
    assert rendered == "city: San Jose, geo: lat: 37.4, lng: -121.9"


def test_print_table_list_and_dict_cells_end_to_end(capsys):
    """Same fix, exercised through the real print_table path rather than
    calling _render_cell directly."""
    data = [{
        "name": "Alice",
        "emails": ["alice@example.com", "a.work@example.com", "a.alt@example.com"],
        "address": {"city": "San Jose", "state": "CA"},
    }]
    print_table(data, columns=[("Name", "name"), ("Emails", "emails"), ("Address", "address")])
    out = capsys.readouterr().out
    assert "alice@example.com (+2 more)" in out
    assert "city: San Jose, state: CA" in out
    assert "{'" not in out


def test_json_output_unaffected_by_cell_rendering(capsys):
    """-o json must stay the raw structured data — list/dict rendering is a
    table-only concern and must not leak into format_as_json/print_json."""
    data = [{
        "name": "Alice",
        "emails": ["alice@example.com", "a.work@example.com", "a.alt@example.com"],
        "address": {"city": "San Jose", "state": "CA"},
    }]
    print_json(data)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed == data
    assert parsed[0]["emails"] == ["alice@example.com", "a.work@example.com", "a.alt@example.com"]
    assert parsed[0]["address"] == {"city": "San Jose", "state": "CA"}
