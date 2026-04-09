"""Unit tests for the Layer 3 benchmark harness — no API calls."""
from __future__ import annotations
import json
import pytest


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
    assert "signals" in phase
    assert "token_expiry_signal_seen" in phase["signals"]
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


def test_phase_detector_identifies_decision_review():
    from tools.layer3_benchmark import detect_phase
    # Uses "per-decision review" to match the deliberately tightened
    # DECISION_REVIEW_MARKERS set from Layer 3 Plan B-1 — loose markers
    # like "decision review" were excluded to avoid false positives when
    # assessment-phase narration mentions the upcoming review in passing.
    assert detect_phase("I'll walk through the per-decision review") == "decision_review"
    assert detect_phase("Generating assessment report") == "assessment"
    assert detect_phase("Here are the NEEDS YOUR INPUT decisions") == "decision_review"


def test_source_file_read_flagged(tmp_path):
    from tools.layer3_benchmark import is_source_file_read
    assert is_source_file_read("src/wxcli/migration/advisory/advisory_patterns.py") is True
    assert is_source_file_read("docs/runbooks/cucm-migration/decision-guide.md") is False
    assert is_source_file_read(".claude/skills/cucm-migrate/SKILL.md") is False


def test_decision_extractor_finds_decide_calls():
    from tools.layer3_benchmark import extract_resolved_decisions
    bash_calls = [
        "wxcli cucm decide D0001 skip -p benchmark-migration",
        "wxcli cucm decide D0002 hunt_group -p benchmark-migration",
        "wxcli cucm status -o json",
    ]
    resolved = extract_resolved_decisions(bash_calls)
    assert resolved == {"D0001": "skip", "D0002": "hunt_group"}


def test_decision_extractor_handles_compound_bash_calls():
    from tools.layer3_benchmark import extract_resolved_decisions
    bash_calls = [
        "wxcli cucm decide D0001 skip && wxcli cucm decide D0002 use_union",
        "wxcli cucm decide D0003 manual ; wxcli cucm decide D0004 generate",
    ]
    resolved = extract_resolved_decisions(bash_calls)
    assert resolved == {"D0001": "skip", "D0002": "use_union", "D0003": "manual", "D0004": "generate"}


def test_decision_accuracy_computation():
    from tools.layer3_benchmark import compute_decision_accuracy
    resolved = {"D0001": "skip", "D0002": "call_queue", "D0003": "use_union"}
    recommendations = {"D0001": "skip", "D0002": "hunt_group", "D0003": "use_union"}
    accuracy = compute_decision_accuracy(resolved, recommendations)
    assert accuracy == pytest.approx(2 / 3)


def test_regression_report_flags_token_increase():
    from tools.layer3_benchmark import compute_regression_report
    baseline = {"summary": {"tokens_per_decision": 1000, "decision_accuracy": 0.9, "gotcha_coverage_rate": 1.0}}
    current  = {"summary": {"tokens_per_decision": 1300, "decision_accuracy": 0.9, "gotcha_coverage_rate": 1.0}}
    report = compute_regression_report(current, baseline)
    assert report["tokens_per_decision"]["status"] == "REGRESSION"
    assert report["decision_accuracy"]["status"] == "OK"
