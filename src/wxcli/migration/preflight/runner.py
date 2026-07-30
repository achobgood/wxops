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
    check_bulk_device_job_support,
    check_duplicate_users,
    check_e911_readiness,
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
#: INCOMPLETE outranks WARN but not FAIL. A definite failure is the more
#: actionable message ("the org is not ready"); INCOMPLETE means "we do not
#: know", which must still stop the gate but should not masquerade as a verdict.
_STATUS_PRIORITY = {
    CheckStatus.FAIL: 4,
    CheckStatus.INCOMPLETE: 3,
    CheckStatus.WARN: 2,
    CheckStatus.PASS: 1,
    CheckStatus.SKIP: 0,
}

#: Which fetched dataset each check's verdict depends on. A check whose data was
#: never retrieved cannot distinguish "nothing found" from "never queried", so it
#: reports INCOMPLETE rather than a verdict it did not earn (finding F06).
#: Checks absent from this map need no Webex data — ``rate-limit`` reads the plan,
#: ``e911-readiness`` reads the store, ``bulk-job-support`` carries its own probe
#: which already SKIPs when auth is unavailable.
_CHECK_FETCH_DEPS: dict[str, tuple[str, ...]] = {
    "licenses": ("licenses",),
    "workspace-licenses": ("licenses",),
    "locations": ("locations",),
    "trunks": ("trunks",),
    "numbers": ("numbers",),
    "users": ("people",),
    "features": ("features",),
}


def _worst_status(results: list[CheckResult]) -> CheckStatus:
    """Return the worst status across all results."""
    worst = CheckStatus.SKIP
    for r in results:
        if _STATUS_PRIORITY.get(r.status, 0) > _STATUS_PRIORITY.get(worst, 0):
            worst = r.status
    return worst


class PreflightRunner:
    """Orchestrates all 10 preflight checks + DUPLICATE_USER detection.

    Fetches shared data once before running individual checks.
    (from 05a-preflight-checks.md, Shared Data Between Checks)
    """

    #: Every check this runner knows about, in registry order. Callers need the
    #: total to tell a full run from a partial one — `--check <one>` used to mark
    #: the "MANDATORY, NOT SKIPPABLE" gate complete, leaving a state file
    #: indistinguishable from a full 10-check pass (finding F07).
    #: `test_registered_names_match_the_registry` pins this against the dict
    #: built inside `run()`, so the two cannot drift.
    CHECK_NAMES: tuple[str, ...] = (
        "licenses",
        "workspace-licenses",
        "locations",
        "trunks",
        "features",
        "numbers",
        "users",
        "rate-limit",
        "e911-readiness",
        "bulk-job-support",
    )

    @classmethod
    def registered_check_names(cls) -> tuple[str, ...]:
        """The full set of check names — what a complete run covers."""
        return cls.CHECK_NAMES

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
        # Reset per-run so a reused runner instance cannot leak a stale failure.
        self._fetch_failures: dict[str, str] = {}

        if dry_run:
            return self._dry_run(store, check_filter)

        # Fetch shared data — only what's needed for the filtered check
        # (from 05a-preflight-checks.md, Shared Data Between Checks)
        def _needs(*checks: str) -> bool:
            return check_filter is None or check_filter in checks

        licenses = self._fetch("licenses", ["licenses", "list", "--output", "json"]) if _needs("licenses", "workspace-licenses") else []
        locations = self._fetch("locations", ["locations", "list"]) if _needs("locations") else []
        numbers = self._fetch("numbers", ["numbers", "list", "--limit", "0"]) if _needs("numbers") else []
        people = self._fetch("people", ["users", "list", "--calling-data", "true", "--limit", "0"]) if _needs("users") else []
        trunks = self._fetch("trunks", ["call-routing", "list-trunks"]) if _needs("trunks") else []

        # Fetch PSTN connection data per location
        pstn_by_loc: dict[str, dict] = {}
        if locations and _needs("locations"):
            for loc in locations:
                loc_id = loc.get("id")
                if loc_id:
                    conn = self._fetch(f"pstn-{loc_id}",
                                       ["pstn", "list-connection", loc_id, "--output", "json"])
                    if conn:
                        pstn_by_loc[loc_id] = conn[0] if isinstance(conn, list) and conn else conn if isinstance(conn, dict) else {}

        existing_features: dict[str, int] = {}
        if _needs("features"):
            existing_features = self._count_existing_features()

        # Build bulk-job probe only when the plan contains bulk ops
        # (avoids initialising a WebexSimpleApi session otherwise).
        probe_fn = None
        if _needs("bulk-job-support"):
            probe_fn = self._build_bulk_job_probe()

        # Run checks
        all_checks = {
            "licenses": lambda: check_licenses(store, licenses),
            "workspace-licenses": lambda: check_workspace_licenses(store, licenses),
            "locations": lambda: check_locations(store, locations, pstn_connections=pstn_by_loc if locations else None),
            "trunks": lambda: check_trunks(store, trunks),
            "features": lambda: check_feature_entitlements(store, existing_features),
            "numbers": lambda: self._run_number_check(store, numbers),
            "users": lambda: self._run_duplicate_check(store, people),
            "rate-limit": lambda: check_rate_limit_budget(store, self.config),
            "e911-readiness": lambda: check_e911_readiness(store),
            "bulk-job-support": lambda: check_bulk_device_job_support(store, probe_fn),
        }

        results: list[CheckResult] = []
        all_decisions: list[dict] = []
        self._number_decisions: list[dict] = []
        self._user_decisions: list[dict] = []

        if check_filter:
            if check_filter not in all_checks:
                valid = ", ".join(sorted(all_checks.keys()))
                raise PreflightError(f"Unknown check '{check_filter}'. Valid: {valid}")
            result = self._mark_incomplete_if_unfetched(
                check_filter, all_checks[check_filter]()
            )
            results.append(result)
        else:
            for name, check_fn in all_checks.items():
                try:
                    result = self._mark_incomplete_if_unfetched(name, check_fn())
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

    def _mark_incomplete_if_unfetched(
        self, check_name: str, result: CheckResult
    ) -> CheckResult:
        """Replace a check's verdict with INCOMPLETE when its data never arrived.

        The check function still runs — it is a pure function of (store, data) and
        running it is how the display name is obtained — but its verdict is
        discarded, because a verdict computed from an empty list that was supposed
        to hold the org's numbers is not a verdict.

        Any decisions the check captured are dropped too: a NUMBER_CONFLICT set
        derived from zero fetched numbers would merge "no conflicts" into the
        store as fact.
        """
        failed = [
            dep for dep in _CHECK_FETCH_DEPS.get(check_name, ())
            if dep in self._fetch_failures
        ]
        if not failed:
            return result

        if check_name == "numbers":
            self._number_decisions = []
        elif check_name == "users":
            self._user_decisions = []

        reasons = "; ".join(
            f"{dep}: {self._fetch_failures[dep]}" for dep in failed
        )
        return CheckResult(
            name=result.name,
            status=CheckStatus.INCOMPLETE,
            detail=(
                f"Could not check — required Webex data was not retrieved "
                f"({reasons}). This is not a pass: re-run preflight once the "
                f"query succeeds."
            ),
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
        """Fetch data from wxcli, recording failure so callers can tell.

        Still returns ``[]`` so the shared-data plumbing is unchanged, but the
        failure is recorded against ``label``. Without that record every check
        received an empty list and could not distinguish "nothing found" from
        "never queried" — which turned a missing token into three confident
        PASSes (finding F06).
        """
        try:
            return _run_wxcli(args)
        except PreflightError as exc:
            self._fetch_failures[label] = str(exc)
            return []

    def _build_bulk_job_probe(self):
        """Return a zero-arg callable that probes the bulk device job endpoint.

        Returns ``None`` if auth is unavailable — the check then SKIPs.
        On invocation the callable returns ``(status_code, error_message)``.
        Uses ``WebexSimpleApi`` so auth/orgId injection matches the rest of
        the CLI.

        Design note (Finding #11): this preflight module's convention is
        **subprocess, not import** — checks normally shell out to ``wxcli``
        via ``_run_wxcli`` to reuse the CLI's auth, pagination, and error
        handling (see the module CLAUDE.md). This probe deliberately deviates
        and calls ``api.session.get`` directly because there is no equivalent
        ``wxcli`` subcommand that lists bulk device jobs — generating one
        just to satisfy the convention would be overkill for a single
        read-only probe. If ``wxcli`` ever gains a
        ``bulk-device-jobs list --job-type callDeviceSettings --max 1``
        command, this probe should be re-routed through ``_run_wxcli`` to
        restore convention parity.
        (Wave 4, Issue #9)
        """
        try:
            from wxcli.auth import get_api
        except Exception:
            return None

        try:
            api = get_api()
        except SystemExit:
            # get_api raises typer.Exit when no token is configured
            return None
        except Exception:
            return None

        def _probe() -> tuple[int, str]:
            import requests

            url = api.session.ep("telephony/config/jobs/devices/callDeviceSettings")
            params: dict[str, str] = {"max": "1"}
            org_id = self.config.get("orgId") if isinstance(self.config, dict) else None
            if org_id:
                params["orgId"] = org_id
            try:
                resp = api.session.get(url, params=params)
            except requests.RequestException as exc:
                return 0, str(exc)
            return resp.status_code, getattr(resp, "text", "") or ""

        return _probe

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
            except PreflightError as exc:
                # Same swallow as _fetch had: a count of 0 from a failed query
                # reads as "no features exist" and the entitlement check then
                # passes on headroom it never confirmed.
                counts[obj_type] = 0
                self._fetch_failures["features"] = str(exc)
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
            ("e911-readiness", "E911 readiness", f"{store.count_by_type('user')} users ECBN candidate check"),
            ("bulk-job-support", "Bulk device job support", "Probe for FedRAMP bulk device job support"),
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
