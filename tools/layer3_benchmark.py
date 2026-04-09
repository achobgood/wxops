#!/usr/bin/env python3.11
"""Layer 3 benchmark harness.

Runs the cucm-migrate skill against a fixture migration store via the
Anthropic API. Captures tool-use metadata (file reads, bash calls, token
counts) and produces a structured JSON efficiency report.

Usage:
    python3.11 tools/layer3_benchmark.py --project tests/fixtures/benchmark-migration
    python3.11 tools/layer3_benchmark.py --project tests/fixtures/benchmark-migration --compare --baseline docs/reports/layer3-baseline-2026-04-08.json

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

MAX_FIXTURE_READ_BYTES = 8000  # Cap on file content returned to the model via Read tool;
                               # directly shapes baseline token counts — treat as load-bearing.
MAX_SESSION_TURNS = 50  # Hard stop for run_session; real sessions should be well under this

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
                "signals": {
                    "token_expiry_signal_seen": False,
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

    # TODO(Task 3): harden against UnicodeDecodeError on binary files and absolute-path escapes
    def _dispatch_read(self, file_path: str) -> str:
        # For skill and runbook reads, return actual file content.
        resolved = REPO_ROOT / file_path.lstrip("/")
        if resolved.exists():
            return resolved.read_text(encoding="utf-8")[:MAX_FIXTURE_READ_BYTES]
        return f"[fixture: file not found: {file_path}]"


def detect_phase(text: str) -> str:
    """Identify which SKILL.md phase is active from assistant text."""
    text_lower = text.lower()
    for marker in DECISION_REVIEW_MARKERS:
        if marker.lower() in text_lower:
            return "decision_review"
    return "assessment"


def is_source_file_read(file_path: str) -> bool:
    """Return True if a Read call targets migration source code."""
    return any(file_path.startswith(prefix) for prefix in SOURCE_FILE_PREFIXES)


def extract_resolved_decisions(bash_calls: list[str]) -> dict[str, str]:
    """Extract {decision_id: chosen_option} from Bash tool call strings.

    Tightened regex: decision IDs are always 4 digits (`D\\d{4}`) and options
    are snake_case identifiers (matching the DecisionOption.id field convention
    in src/wxcli/migration/models.py). This rejects flag-shaped "options" like
    `-p` and paths like `benchmark-migration` if a flag-before-positional
    command ever appears.
    """
    pattern = re.compile(r"wxcli\s+cucm\s+decide\s+(D\d{4})\s+([a-z_][a-z0-9_]*)")
    resolved: dict[str, str] = {}
    for call in bash_calls:
        for m in pattern.finditer(call):
            resolved[m.group(1)] = m.group(2)
    return resolved


def compute_decision_accuracy(
    resolved: dict[str, str],
    recommendations: dict[str, str],
) -> float | None:
    """Fraction of recommended decisions where model chose the recommended option."""
    if not recommendations:
        return None
    correct = sum(
        1 for did, rec in recommendations.items()
        if resolved.get(did) == rec
    )
    return correct / len(recommendations)


def compute_regression_report(
    current: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Compare summary metrics and flag regressions."""
    cs = current["summary"]
    bs = baseline["summary"]
    report: dict[str, Any] = {}

    # Tokens per decision: >20% increase = REGRESSION
    if (bs.get("tokens_per_decision") is not None
        and cs.get("tokens_per_decision") is not None
        and bs["tokens_per_decision"] > 0):
        delta = (cs["tokens_per_decision"] - bs["tokens_per_decision"]) / bs["tokens_per_decision"]
        report["tokens_per_decision"] = {
            "baseline": bs["tokens_per_decision"],
            "current": cs["tokens_per_decision"],
            "delta_pct": round(delta * 100, 1),
            "status": "REGRESSION" if delta > 0.20 else "OK",
        }

    # Decision accuracy: >0.10 absolute drop = REGRESSION
    if bs.get("decision_accuracy") is not None and cs.get("decision_accuracy") is not None:
        drop = bs["decision_accuracy"] - cs["decision_accuracy"]
        report["decision_accuracy"] = {
            "baseline": bs["decision_accuracy"],
            "current": cs["decision_accuracy"],
            "drop": round(drop, 3),
            "status": "REGRESSION" if drop > 0.10 else "OK",
        }

    # Gotcha coverage: any drop = REGRESSION
    if bs.get("gotcha_coverage_rate") is not None and cs.get("gotcha_coverage_rate") is not None:
        drop = bs["gotcha_coverage_rate"] - cs["gotcha_coverage_rate"]
        report["gotcha_coverage_rate"] = {
            "baseline": bs["gotcha_coverage_rate"],
            "current": cs["gotcha_coverage_rate"],
            "drop": round(drop, 3),
            "status": "REGRESSION" if drop > 0 else "OK",
        }

    return report


def run_session(args: argparse.Namespace) -> dict[str, Any]:
    """Run the cucm-migrate skill against the fixture and record efficiency metrics."""
    import anthropic

    fixture_dir = Path(args.project)
    dispatcher = ToolResponseDispatcher(fixture_dir)
    record = empty_session_record(project=str(fixture_dir), model=args.model)

    skill_text = SKILL_PATH.read_text(encoding="utf-8")
    client = anthropic.Anthropic()

    messages: list[dict] = [
        {"role": "user", "content": f"Run the CUCM migration for project {fixture_dir.name}"},
    ]

    current_phase = "assessment"
    bash_calls: list[str] = []
    read_calls: list[str] = []
    phase_read_counts: dict[str, dict[str, int]] = {"assessment": {}, "decision_review": {}}
    turn_count = 0

    while True:
        turn_count += 1
        if turn_count > MAX_SESSION_TURNS:
            record["summary"]["terminated_early"] = "max_turns_exceeded"
            break

        response = client.messages.create(
            model=args.model,
            max_tokens=4096,
            system=skill_text,
            messages=messages,
        )

        # Update phase from assistant text
        assistant_text = " ".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        detected = detect_phase(assistant_text)
        if detected == "decision_review":
            current_phase = "decision_review"

        # Record turn and tokens
        record["phases"][current_phase]["turns"] += 1
        record["phases"][current_phase]["input_tokens"] += (response.usage.input_tokens or 0)

        # Record tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_name = block.name
            tool_input = block.input
            first_value = ""
            if isinstance(tool_input, dict) and tool_input:
                first_value = next(iter(tool_input.values()), "")
            call_summary = f"{tool_name}({first_value})"
            record["phases"][current_phase]["tool_calls"].append(
                {"tool": tool_name, "summary": call_summary}
            )

            # Track source file reads
            if tool_name == "Read":
                fp = tool_input.get("file_path", "")
                read_calls.append(fp)
                if is_source_file_read(fp):
                    record["phases"][current_phase]["source_file_reads"].append(fp)
                # Track duplicates — append exactly once, on the transition
                # from 2 → 3 reads. Further reads of the same file don't
                # re-add it (the summary's loops_detected count uses
                # set(duplicate_reads) but keeping the list itself
                # unique-per-file avoids confusing raw output).
                phase_read_counts[current_phase][fp] = phase_read_counts[current_phase].get(fp, 0) + 1
                if phase_read_counts[current_phase][fp] == 3:
                    record["phases"][current_phase]["duplicate_reads"].append(fp)

            # Track bash calls for decision extraction
            if tool_name == "Bash":
                cmd = tool_input.get("command", "")
                bash_calls.append(cmd)
                _check_gotchas(cmd, assistant_text, record)

            result_text = dispatcher.dispatch(tool_name, tool_input)

            # Token-expiry detection lives here (not in _check_gotchas) because
            # it fires on the *tool result content*, before the model has had
            # a chance to narrate a response. The skill's gate is "if whoami
            # reports <2h, do not proceed" — we observe that by seeing the
            # expiry string in the dispatched fixture response directly.
            if tool_name == "Bash" and "expires in" in result_text.lower():
                expiry_match = re.search(r"expires in\s+(\d+)\s*([hm])", result_text.lower())
                if expiry_match:
                    amount = int(expiry_match.group(1))
                    unit = expiry_match.group(2)
                    minutes = amount * 60 if unit == "h" else amount
                    if minutes < 120:
                        # Tool result itself shows an expiring token — gate
                        # is activated when we see it; the harness will verify
                        # in subsequent turns that the assistant narrates the
                        # refresh warning. Written to `signals` (not
                        # `gotcha_coverage`) so it doesn't shift the
                        # gc_rate denominator.
                        record["phases"][current_phase]["signals"]["token_expiry_signal_seen"] = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })

        messages.append({"role": "assistant", "content": response.content})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn" or not tool_results:
            break

    # Compute summary metrics
    _finalize_record(record, bash_calls, fixture_dir)
    return record


def _check_gotchas(cmd: str, assistant_text: str, record: dict) -> None:
    """Check whether gotcha guard actions appear in the session.

    Signals are chosen to be robust against paraphrasing:
    - location_address_gate: fires when the assistant runs or references
      import-locations (the skill's mandated guard action).
    - token_expiry_gate: fires when the assistant narrates a refresh
      instruction or a do-not-proceed directive in response to an
      expiring token — not merely when the token expiry is mentioned.
    - dissent_protocol: fires when the assistant cites a KB entry
      (DT-{DOMAIN}-NNN or a kb-*.md path) alongside a recommendation.
    - preflight_failure_gate: fires when LICENSE_SHORTAGE appears in
      the preflight output (cmd or tool result forwarded into
      assistant_text) — does NOT rely on the loose substring "fail".
    """
    dr = record["phases"]["decision_review"]["gotcha_coverage"]
    tx = assistant_text.lower()

    if "import-locations" in cmd or "import-locations" in tx:
        dr["location_address_gate"] = True

    # Token expiry: require BOTH a mention of expiry AND a guard-action verb
    # ("refresh", "do not proceed", "2 hours"). Avoids matching incidental
    # narration that merely quotes the whoami output.
    if ("expires" in tx or "expiry" in tx) and (
        "refresh" in tx or "do not proceed" in tx or "2 hours" in tx
    ):
        dr["token_expiry_gate"] = True

    # Dissent protocol: require an explicit KB citation (DT-XXX-NNN or kb-*.md).
    if re.search(r"DT-[A-Z]+-\d+", assistant_text) or ("kb-" in tx and ".md" in tx):
        dr["dissent_protocol"] = True

    # Preflight failure: tightened to the specific shortage token emitted by
    # the fixture tool response, checked in both the command and the
    # (assistant-narrated) output. Does NOT use the loose substring "fail".
    if "LICENSE_SHORTAGE" in (cmd + assistant_text):
        dr["preflight_failure_gate"] = True


def _finalize_record(record: dict, bash_calls: list[str], fixture_dir: Path) -> None:
    """Compute summary metrics after session ends."""
    # Load recommendations from fixture store
    from wxcli.migration.store import MigrationStore
    db_path = fixture_dir / "migration.db"
    if db_path.exists():
        with MigrationStore(db_path) as store:
            decisions = store.get_all_decisions()
        recommendations = {
            d["decision_id"]: d["recommendation"]
            for d in decisions
            if d.get("recommendation")
        }
    else:
        recommendations = {}

    resolved = extract_resolved_decisions(bash_calls)
    dr = record["phases"]["decision_review"]
    dr["decisions_resolved"] = len(resolved)
    dr["decision_accuracy"] = compute_decision_accuracy(resolved, recommendations)

    gc = dr["gotcha_coverage"]
    gc_rate = sum(gc.values()) / len(gc) if gc else None
    dr_tokens = dr["input_tokens"]
    total_tokens = sum(p["input_tokens"] for p in record["phases"].values())

    record["summary"].update({
        "total_input_tokens": total_tokens,
        "tokens_per_decision": (
            round(dr_tokens / dr["decisions_resolved"])
            if dr["decisions_resolved"] > 0 else None
        ),
        "source_file_reads_in_review": len(dr["source_file_reads"]),
        "decision_accuracy": dr["decision_accuracy"],
        "gotcha_coverage_rate": gc_rate,
        "loops_detected": len(set(dr["duplicate_reads"])),
    })


def compare_against_baseline(record: dict, baseline_path: str) -> None:
    baseline = json.loads(Path(baseline_path).read_text())
    report = compute_regression_report(record, baseline)
    print("\n=== Regression Report ===")
    for metric, result in report.items():
        status = result["status"]
        marker = "REGRESSION" if status == "REGRESSION" else "ok"
        print(f"  [{marker}] {metric}: baseline={result.get('baseline')} current={result.get('current')}")


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
