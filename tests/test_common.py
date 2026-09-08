import json
import pytest
import typer
from wxcli.common import apply_fields, emit, _record_count



def test_apply_fields_none_returns_input_unchanged():
    data = [{"id": "a", "name": "Sales"}]
    assert apply_fields(data, None) is data


def test_apply_fields_projects():
    data = [{"id": "a", "name": "Sales"}, {"id": "b", "name": "Support"}]
    assert apply_fields(data, "[].name") == ["Sales", "Support"]


def test_apply_fields_filters():
    data = [{"name": "Sales", "type": "AGENT"}, {"name": "Support", "type": "STANDARD"}]
    assert apply_fields(data, "[?type=='AGENT'].name") == ["Sales"]


def test_apply_fields_invalid_expression_exits_2(capsys):
    with pytest.raises(typer.Exit) as exc:
        apply_fields([{"a": 1}], "[[[")
    assert exc.value.exit_code == 2
    assert "invalid --fields" in capsys.readouterr().err


def test_projection_drives_table_columns(capsys):
    emit([{"id": "a", "name": "Sales", "type": "AGENT"}], output="table",
         fields="[].{Name:name,Type:type}", columns=[("ID", "id"), ("Name", "name")])
    out = capsys.readouterr().out
    assert "Type" in out and "AGENT" in out
    assert "ID" not in out


def test_table_without_fields_uses_configured_columns(capsys):
    emit([{"id": "a", "name": "Sales"}], output="table", columns=[("ID", "id")])
    out = capsys.readouterr().out
    assert "ID" in out and "Sales" not in out


def test_emit_table_falls_back_to_json_for_scalar_result(capsys):
    emit([{"id": "a"}], output="table", fields="[0].id", columns=[("ID", "id")])
    assert json.loads(capsys.readouterr().out) == "a"


def test_emit_table_renders_a_dict_as_one_row_table(capsys):
    """Preserves today's `show -o table`: a single object becomes a one-row
    table, not JSON (see the Task 1 note on locations.py:126-134)."""
    emit({"id": "a", "name": "HQ"}, output="table")
    out = capsys.readouterr().out
    assert "HQ" in out and "Name" in out
    assert not out.lstrip().startswith("{")


def test_empty_projection_on_nonempty_data_warns(capsys):
    emit([{"id": "a"}, {"id": "b"}], output="json", fields="[?id=='zzz']")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == []
    assert "2 record" in captured.err
    assert "--fields" in captured.err


def test_null_projection_on_nonempty_data_warns(capsys):
    emit([{"id": "a"}], output="json", fields="nope")
    assert "1 record" in capsys.readouterr().err


def test_genuinely_empty_data_does_not_warn(capsys):
    emit([], output="json", fields="[?id=='zzz']")
    assert capsys.readouterr().err == ""


def test_filter_matching_zero_of_n_warns_without_asserting_error(capsys):
    """A filter that legitimately matches 0 of N records still gets the note
    (the guard can't tell this apart from a bad expression), but the note
    must state the fact — not claim the expression is wrong."""
    emit([{"name": "Sales", "enabled": True}, {"name": "Support", "enabled": True}],
         output="json", fields="[?enabled==`false`].name")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == []
    err = captured.err
    assert "0 of 2 record" in err
    assert "wrong" not in err
    assert "before concluding the result is empty" not in err
    assert "matched nothing" not in err


def test_matching_projection_does_not_warn(capsys):
    emit([{"id": "a"}], output="json", fields="[].id")
    assert capsys.readouterr().err == ""


def test_no_fields_never_warns(capsys):
    emit([], output="json")
    assert capsys.readouterr().err == ""


def test_record_count_empty_string_is_zero():
    assert _record_count("") == 0


def test_record_count_zero_is_one():
    assert _record_count(0) == 1


def test_record_count_false_is_one():
    assert _record_count(False) == 1


def test_record_count_none_is_zero():
    assert _record_count(None) == 0


def test_record_count_nonempty_string_is_one():
    assert _record_count("x") == 1


def test_record_count_empty_list_is_zero():
    assert _record_count([]) == 0


def test_record_count_empty_dict_is_zero():
    assert _record_count({}) == 0


def test_record_count_nonempty_list_counts_items():
    assert _record_count([1, 2]) == 2


def test_record_count_nonempty_dict_is_one():
    assert _record_count({"a": 1}) == 1


def test_id_output_prints_bare_id(capsys):
    emit({"id": "abc123", "name": "x"}, output="id")
    assert capsys.readouterr().out.strip() == "abc123"


def test_text_list_of_dicts_is_tab_separated(capsys):
    emit([{"id": "a", "name": "Sales"}], output="text")
    assert capsys.readouterr().out == "a\tSales\n"


def test_text_list_of_scalars_is_newline_separated(capsys):
    """The pipeline case: --fields '[].name' -o text | while read name."""
    emit(["Sales", "Support"], output="text")
    assert capsys.readouterr().out == "Sales\nSupport\n"


def test_text_scalar(capsys):
    emit("Sales", output="text")
    assert capsys.readouterr().out == "Sales\n"


def test_text_nested_values_are_compact_json(capsys):
    emit([{"id": "a", "tags": ["x", "y"]}], output="text")
    assert capsys.readouterr().out == 'a\t["x","y"]\n'


def test_text_none_becomes_empty_cell(capsys):
    emit([{"id": "a", "name": None}], output="text")
    assert capsys.readouterr().out == "a\t\n"


def test_fields_then_text_composes(capsys):
    emit([{"id": "a", "name": "Sales"}], output="text", fields="[].name")
    assert capsys.readouterr().out == "Sales\n"


def test_load_json_body_inline():
    from wxcli.common import load_json_body
    assert load_json_body('{"a": 1}') == {"a": 1}


def test_load_json_body_file_url(tmp_path):
    from wxcli.common import load_json_body
    p = tmp_path / "b.json"
    p.write_text('{"a": 2}')
    assert load_json_body(f"file://{p}") == {"a": 2}


def test_load_json_body_bare_path(tmp_path):
    from wxcli.common import load_json_body
    p = tmp_path / "b.json"
    p.write_text('{"a": 3}')
    assert load_json_body(str(p)) == {"a": 3}


def test_load_json_body_stdin(monkeypatch):
    import io
    from wxcli.common import load_json_body
    monkeypatch.setattr("sys.stdin", io.StringIO('{"a": 4}'))
    assert load_json_body("-") == {"a": 4}


def test_load_json_body_missing_file_exits_2(capsys):
    from wxcli.common import load_json_body
    with pytest.raises(typer.Exit) as exc:
        load_json_body("file:///nope/missing.json")
    assert exc.value.exit_code == 2
    assert "missing.json" in capsys.readouterr().err


def test_load_json_body_malformed_exits_2(capsys):
    from wxcli.common import load_json_body
    with pytest.raises(typer.Exit) as exc:
        load_json_body("{not json")
    assert exc.value.exit_code == 2
    assert "not valid JSON" in capsys.readouterr().err

