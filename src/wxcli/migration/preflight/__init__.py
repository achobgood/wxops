"""Preflight checks for CUCM-to-Webex migration.

Verifies the Webex org is ready for the migration plan by running
read-only checks against live Webex data via wxcli CLI commands.

(from 05a-preflight-checks.md — 7 checks + DUPLICATE_USER detection)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum


class CheckStatus(str, Enum):
    """Result status for a single preflight check.
    (from 05a-preflight-checks.md, PASS/WARN/FAIL model)
    """
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class PreflightIssue:
    """A single issue found by a preflight check."""
    issue_type: str
    detail: str
    data: dict = field(default_factory=dict)


@dataclass
class CheckResult:
    """Result from a single preflight check.
    (from 05a-preflight-checks.md, per-check result)
    """
    name: str
    status: CheckStatus
    detail: str
    issues: list[PreflightIssue] = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class PreflightResult:
    """Aggregated result from all preflight checks.
    (from 05a-preflight-checks.md, overall result)
    """
    overall: CheckStatus
    checks: list[CheckResult] = field(default_factory=list)
    new_decision_ids: list[str] = field(default_factory=list)
    merge_result: dict = field(default_factory=dict)


class PreflightError(Exception):
    """Raised when a wxcli command fails during preflight."""


def _run_wxcli(args: list[str]) -> list[dict]:
    """Run a wxcli command and parse JSON output.
    (from phase-10-preflight.md, subprocess pattern)
    """
    result = subprocess.run(
        ["wxcli"] + args + ["-o", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise PreflightError(f"wxcli {' '.join(args)} failed: {result.stderr}")
    stdout = result.stdout.strip()
    if not stdout:
        return []
    parsed = json.loads(stdout)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    return []


def preflight_fingerprint(*args) -> str:
    """Compute deterministic fingerprint for preflight decisions.
    (from 05a-preflight-checks.md, fingerprint computation)
    """
    canonical = json.dumps(list(args))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
