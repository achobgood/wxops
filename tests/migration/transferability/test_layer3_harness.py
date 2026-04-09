"""Unit tests for the Layer 3 benchmark harness — no API calls."""
from __future__ import annotations
import json


def test_arg_parser_project_flag(tmp_path):
    from tools.layer3_benchmark import build_arg_parser
    parser = build_arg_parser()
    args = parser.parse_args(["--project", str(tmp_path), "--dry-run"])
    assert args.project == str(tmp_path)
    assert args.dry_run is True


def test_arg_parser_defaults():
    from tools.layer3_benchmark import build_arg_parser
    parser = build_arg_parser()
    args = parser.parse_args(["--project", "/tmp/x"])
    assert args.model == "claude-sonnet-4-6"
    assert args.dry_run is False
    assert args.baseline is None
    assert args.compare is False


def test_session_record_schema():
    from tools.layer3_benchmark import empty_session_record
    record = empty_session_record(project="test", model="claude-sonnet-4-6")
    assert "session_id" in record
    assert "phases" in record
    assert "decision_review" in record["phases"]
    phase = record["phases"]["decision_review"]
    assert "turns" in phase
    assert "input_tokens" in phase
    assert "source_file_reads" in phase
    assert "decisions_resolved" in phase
    assert "decision_accuracy" in phase
    assert "gotcha_coverage" in phase
    assert "summary" in record


def test_tool_response_dispatch_bash(tmp_path):
    from tools.layer3_benchmark import ToolResponseDispatcher
    resp_dir = tmp_path / "tool_responses"
    resp_dir.mkdir()
    (resp_dir / "cucm_status.json").write_text(
        json.dumps({"stdout": "ANALYZED", "returncode": 0})
    )
    dispatcher = ToolResponseDispatcher(fixture_dir=tmp_path)
    result = dispatcher.dispatch("Bash", {"command": "wxcli cucm status -o json"})
    assert "ANALYZED" in result


def test_tool_response_dispatch_unknown_returns_empty(tmp_path):
    from tools.layer3_benchmark import ToolResponseDispatcher
    (tmp_path / "tool_responses").mkdir()
    dispatcher = ToolResponseDispatcher(fixture_dir=tmp_path)
    result = dispatcher.dispatch("Bash", {"command": "wxcli cucm unknown-command"})
    assert result == ""
