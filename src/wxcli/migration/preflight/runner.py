"""Preflight runner — orchestrates all checks and manages shared data.

Fetches shared Webex data once (licenses, locations, numbers, people, trunks),
runs all checks, merges decisions, and stores results in state.json.

(from 05a-preflight-checks.md, PreflightRunner class)
(from phase-10-preflight.md, runner orchestrator)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wxcli.migration.preflight import (
    CheckResult,
    CheckStatus,
    PreflightError,
    PreflightResult,
    _run_wxcli,
)
from wxcli.migration.preflight.checks import (
    check_duplicate_users,
    check_feature_entitlements,
    check_licenses,
    check_locations,
    check_number_conflicts,
    check_rate_limit_budget,
    check_trunks,
    check_workspace_licenses,
)
from wxcli.migration.store import MigrationStore


# Priority order for overall result (worst wins)
_STATUS_PRIORITY = {
    CheckStatus.FAIL: 3,
    CheckStatus.WARN: 2,
    CheckStatus.PASS: 1,
    CheckStatus.SKIP: 0,
}


def _worst_status(results: list[CheckResult]) -> CheckStatus:
    """Return the worst status across all results."""
    worst = CheckStatus.SKIP
    for r in results:
        if _STATUS_PRIORITY.get(r.status, 0) > _STATUS_PRIORITY.get(worst, 0):
            worst = r.status
    return worst


class PreflightRunner:
    """Orchestrates all 7 preflight checks + DUPLICATE_USER detection.

    Fetches shared data once before running individual checks.
    (from 05a-preflight-checks.md, Shared Data Between Checks)
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def run(
        self,
        store: MigrationStore,
        check_filter: str | None = None,
        dry_run: bool = False,
    ) -> PreflightResult:
        """Run all preflight checks (or a single check by name).

        Args:
            store: Migration store with planned objects.
            check_filter: Run only this check (e.g., "numbers", "licenses").
            dry_run: Show what would be checked without querying Webex.
        """
        if dry_run:
            return self._dry_run(store, check_filter)

        # Fetch shared data — only what's needed for the filtered check
        # (from 05a-preflight-checks.md, Shared Data Between Checks)
        def _needs(*checks: str) -> bool:
            return check_filter is None or check_filter in checks

        licenses = self._fetch("licenses", ["licenses", "list", "--calling-only"]) if _needs("licenses", "workspace-licenses") else []
        locations = self._fetch("locations", ["locations", "list"]) if _needs("locations") else []
        numbers = self._fetch("numbers", ["numbers", "list", "--limit", "0"]) if _needs("numbers") else []
        # Note: ideally would fetch with callingData=true to detect
        # already-calling users. Without it, locationId is absent and all
        # duplicates classify as exists_no_calling (safe but imprecise).
        # Adding a --calling-data flag to wxcli users list is a future enhancement.
        people = self._fetch("people", ["users", "list", "--limit", "0"]) if _needs("users") else []
        trunks = self._fetch("trunks", ["call-routing", "list-trunks"]) if _needs("trunks") else []

        existing_features: dict[str, int] = {}
        if _needs("features"):
            existing_features = self._count_existing_features()

        # Run checks
        all_checks = {
            "licenses": lambda: check_licenses(store, licenses),
            "workspace-licenses": lambda: check_workspace_licenses(store, licenses),
            "locations": lambda: check_locations(store, locations),
            "trunks": lambda: check_trunks(store, trunks),
            "features": lambda: check_feature_entitlements(store, existing_features),
            "numbers": lambda: self._run_number_check(store, numbers),
            "users": lambda: self._run_duplicate_check(store, people),
            "rate-limit": lambda: check_rate_limit_budget(store, self.config),
        }

        results: list[CheckResult] = []
        all_decisions: list[dict] = []
        self._number_decisions: list[dict] = []
        self._user_decisions: list[dict] = []

        if check_filter:
            if check_filter not in all_checks:
                valid = ", ".join(sorted(all_checks.keys()))
                raise PreflightError(f"Unknown check '{check_filter}'. Valid: {valid}")
            result = all_checks[check_filter]()
            results.append(result)
        else:
            for name, check_fn in all_checks.items():
                try:
                    result = check_fn()
                    results.append(result)
                except PreflightError as e:
                    results.append(CheckResult(
                        name=name,
                        status=CheckStatus.FAIL,
                        detail=str(e),
                    ))

        all_decisions = self._number_decisions + self._user_decisions

        # Merge decisions into store — scoped to preflight types only
        # to avoid stale-marking analyzer decisions
        # (from 05a-preflight-checks.md lines 920-929)
        merge_result: dict[str, int] = {}
        new_decision_ids: list[str] = []
        if all_decisions:
            merge_result = store.merge_decisions(
                all_decisions,
                decision_types=["NUMBER_CONFLICT", "DUPLICATE_USER"],
                stage="preflight",
            )
            new_decision_ids = [d["decision_id"] for d in all_decisions]

        overall = _worst_status(results)

        return PreflightResult(
            overall=overall,
            checks=results,
            new_decision_ids=new_decision_ids,
            merge_result=merge_result,
        )

    def _run_number_check(self, store: MigrationStore, numbers: list[dict]) -> CheckResult:
        """Run number conflict check and capture decisions."""
        result, decisions = check_number_conflicts(store, numbers)
        self._number_decisions = decisions
        return result

    def _run_duplicate_check(self, store: MigrationStore, people: list[dict]) -> CheckResult:
        """Run duplicate user check and capture decisions."""
        result, decisions = check_duplicate_users(store, people)
        self._user_decisions = decisions
        return result

    def _fetch(self, label: str, args: list[str]) -> list[dict]:
        """Fetch data from wxcli, returning empty list on failure."""
        try:
            return _run_wxcli(args)
        except PreflightError:
            return []

    def _count_existing_features(self) -> dict[str, int]:
        """Count existing features in the Webex org."""
        counts = {}
        cmd_map = {
            "auto_attendant": ["auto-attendant", "list"],
            "call_queue": ["call-queue", "list"],
            "hunt_group": ["hunt-group", "list"],
            "paging_group": ["paging-group", "list"],
        }
        for obj_type, args in cmd_map.items():
            try:
                data = _run_wxcli(args)
                counts[obj_type] = len(data)
            except PreflightError:
                counts[obj_type] = 0
        return counts

    def _dry_run(
        self,
        store: MigrationStore,
        check_filter: str | None,
    ) -> PreflightResult:
        """Show what would be checked without querying Webex."""
        checks_info = [
            ("licenses", "User licenses", f"{store.count_by_type('user')} users to check"),
            ("workspace-licenses", "Workspace licenses", f"{store.count_by_type('workspace')} workspaces to check"),
            ("locations", "Locations", f"{len(store.get_objects('location'))} locations to verify"),
            ("trunks", "Trunks", f"{len(store.get_objects('trunk'))} trunks to verify"),
            ("features", "Feature entitlements", "AA, CQ, HG, Paging counts"),
            ("numbers", "Number conflicts", "E.164 and extension collision check"),
            ("users", "Duplicate users", f"{store.count_by_type('user')} users to check against Webex"),
            ("rate-limit", "Rate limit budget", "API call estimate from plan_operations"),
        ]

        results = []
        for key, name, detail in checks_info:
            if check_filter and check_filter != key:
                continue
            results.append(CheckResult(
                name=name,
                status=CheckStatus.SKIP,
                detail=f"[dry-run] Would check: {detail}",
            ))

        return PreflightResult(
            overall=CheckStatus.SKIP,
            checks=results,
        )
