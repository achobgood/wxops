#!/usr/bin/env python3.11
"""Layer 3 benchmark harness.

Runs the cucm-migrate skill against a fixture migration store via the
Anthropic API. Captures tool-use metadata (file reads, bash calls, token
counts) and produces a structured JSON efficiency report.

Usage:
    python3.11 tools/layer3_benchmark.py --project tests/fixtures/benchmark-migration
    python3.11 tools/layer3_benchmark.py --project tests/fixtures/benchmark-migration --compare docs/reports/layer3-baseline-2026-04-08.json

Requirements:
    - ANTHROPIC_API_KEY env var must be set
    - Run tools/build_benchmark_fixture.py first to create the fixture store

Pinned model: claude-sonnet-4-6
To upgrade the pinned model: run a new baseline, commit the JSON to docs/reports/,
then update PINNED_MODEL below.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PINNED_MODEL = "claude-sonnet-4-6"
REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "cucm-migrate" / "SKILL.md"

# Maps Bash command patterns to fixture response files.
# Key: substring that must appear in the command string.
# Value: filename under tool_responses/.
TOOL_RESPONSE_MAP = {
    "wxcli cucm status": "cucm_status.json",
    "wxcli cucm decisions --status pending": "cucm_decisions_pending.json",
    "wxcli cucm preflight": "preflight_pass.json",
    "wxcli whoami": "whoami_ok.json",
}

# Patterns that indicate the decision-review phase is active.
# These are chosen to be unambiguous — assessment-phase output can
# legitimately mention "auto-apply" and "Group 1/2" in passing, so those
# are excluded. "Phase B" is the skill's explicit per-decision review
# section name, and "wxcli cucm decide" is an actionable call only
# issued during decision review.
DECISION_REVIEW_MARKERS = [
    "Phase B:",
    "per-decision review",
    "wxcli cucm decide",
    "NEEDS YOUR INPUT",
    "Step 1c:",
    "Step 1c-fallback",
]

# Source files that should NOT be read during decision-review phase.
SOURCE_FILE_PREFIXES = ["src/wxcli/migration/"]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Layer 3 benchmark harness")
    parser.add_argument("--project", required=True, help="Path to fixture project directory")
    parser.add_argument("--model", default=PINNED_MODEL, help=f"Model ID (default: {PINNED_MODEL})")
    parser.add_argument("--baseline", default=None, help="Path to baseline JSON for comparison")
    parser.add_argument("--compare", action="store_true", help="Compare against baseline and print regression report")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit without calling API")
    return parser


def empty_session_record(project: str, model: str) -> dict[str, Any]:
    return {
        "session_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "model": model,
        "skill_sha": _file_sha(SKILL_PATH),
        "phases": {
            "assessment": {
                "turns": 0,
                "input_tokens": 0,
                "tool_calls": [],
                "source_file_reads": [],
                "duplicate_reads": [],
            },
            "decision_review": {
                "turns": 0,
                "input_tokens": 0,
                "tool_calls": [],
                "source_file_reads": [],
                "duplicate_reads": [],
                "decisions_resolved": 0,
                "decision_accuracy": None,
                "gotcha_coverage": {
                    "location_address_gate": False,
                    "token_expiry_gate": False,
                    "dissent_protocol": False,
                    "preflight_failure_gate": False,
                },
            },
        },
        "summary": {
            "total_input_tokens": 0,
            "tokens_per_decision": None,
            "source_file_reads_in_review": 0,
            "decision_accuracy": None,
            "gotcha_coverage_rate": None,
            "loops_detected": 0,
            "runbook_lookup_rate": None,
        },
    }


def _file_sha(path: Path) -> str:
    import hashlib
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


class ToolResponseDispatcher:
    """Returns pre-recorded fixture responses for tool calls."""

    def __init__(self, fixture_dir: Path) -> None:
        self.resp_dir = fixture_dir / "tool_responses"

    def dispatch(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        if tool_name == "Bash":
            return self._dispatch_bash(tool_input.get("command", ""))
        if tool_name == "Read":
            return self._dispatch_read(tool_input.get("file_path", ""))
        return ""

    def _dispatch_bash(self, command: str) -> str:
        for pattern, filename in TOOL_RESPONSE_MAP.items():
            if pattern in command:
                resp_file = self.resp_dir / filename
                if resp_file.exists():
                    data = json.loads(resp_file.read_text())
                    return data.get("stdout", "")
        return ""

    def _dispatch_read(self, file_path: str) -> str:
        # For skill and runbook reads, return actual file content.
        resolved = REPO_ROOT / file_path.lstrip("/")
        if resolved.exists():
            return resolved.read_text(encoding="utf-8")[:8000]  # cap at 8K
        return f"[fixture: file not found: {file_path}]"


# Remaining methods (session runner, phase detector, reporter) are stubs
# wired in Task 3.

def run_session(args: argparse.Namespace) -> dict[str, Any]:
    """Stub — implemented in Task 3."""
    raise NotImplementedError("run_session is implemented in Task 3")


def compare_against_baseline(record: dict, baseline_path: str) -> None:
    """Stub — implemented in Task 3."""
    raise NotImplementedError("compare_against_baseline is implemented in Task 3")


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.dry_run:
        print(f"Project:  {args.project}")
        print(f"Model:    {args.model}")
        print(f"Baseline: {args.baseline}")
        print(f"Skill:    {SKILL_PATH}")
        print("Dry run — exiting.")
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY environment variable is not set.")

    record = run_session(args)

    output_path = Path(args.project) / "layer3-report.json"
    output_path.write_text(json.dumps(record, indent=2))
    print(f"Report written to {output_path}")

    if args.compare and args.baseline:
        compare_against_baseline(record, args.baseline)


if __name__ == "__main__":
    main()
