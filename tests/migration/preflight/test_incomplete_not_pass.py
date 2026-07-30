"""A check that could not run must not report PASS (finding F06).

With no Webex token at all, `wxcli cucm preflight` printed one
`Error: No token found` line and then reported confident verdicts for all 10
checks — including:

    ✓ PASS Number conflicts: No number/extension conflicts with existing
           Webex assignments
    ✓ PASS Duplicate users: No cross-system duplicate users detected

Cause: `PreflightRunner._fetch` catches `PreflightError` and returns `[]`, so
every check receives an empty list and cannot distinguish "nothing found" from
"never queried". Those two checks exist specifically to prevent the number and
duplicate-user collisions that corrupt a live org on execute, and this is exactly
the false negative the project's Discovery-First rule warns about: a negative
result is only trustworthy once the query could have returned a positive.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalTrunk,
    CanonicalUser,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.preflight import CheckStatus, PreflightError
from wxcli.migration.preflight.runner import PreflightRunner
from wxcli.migration.store import MigrationStore
from datetime import datetime, timezone


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk",
        source_name="n",
        extracted_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
    )


@pytest.fixture()
def store_with_plan(tmp_path):
    """A store with objects the checks would have something to say about."""
    s = MigrationStore(tmp_path / "t.db")
    loc = CanonicalLocation(
        canonical_id="location:hq",
        provenance=_prov(),
        name="HQ",
        time_zone="America/New_York",
        preferred_language="en_US",
        announcement_language="en_us",
    )
    loc.status = MigrationStatus.ANALYZED
    s.upsert_object(loc)
    for i in range(3):
        u = CanonicalUser(
            canonical_id=f"user:u{i}",
            provenance=_prov(),
            emails=[f"u{i}@acme.com"],
            location_id="location:hq",
            extension=f"100{i}",
        )
        u.status = MigrationStatus.ANALYZED
        s.upsert_object(u)
    trunk = CanonicalTrunk(
        canonical_id="trunk:t1",
        provenance=_prov(),
        name="HQ-Trunk",
        location_id="location:hq",
    )
    trunk.status = MigrationStatus.ANALYZED
    s.upsert_object(trunk)
    yield s
    s.close()


class TestUnfetchedChecksReportIncomplete:
    """Every fetch fails — no check may claim a clean result."""

    def test_no_check_reports_pass_when_nothing_could_be_fetched(
        self, store_with_plan
    ):
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(store_with_plan)

        passes = [c for c in result.checks if c.status == CheckStatus.PASS]
        fetch_dependent = [
            c for c in passes
            if c.name in ("Trunks", "Number conflicts", "Duplicate users",
                          "User licenses", "Workspace licenses", "Locations")
        ]
        assert not fetch_dependent, (
            "unearned PASS on: "
            + ", ".join(f"{c.name} ({c.detail})" for c in fetch_dependent)
        )

    def test_number_conflict_check_is_incomplete_not_pass(self, store_with_plan):
        """One of the two checks that stop a live org being corrupted."""
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(store_with_plan)

        check = next(c for c in result.checks if c.name == "Number conflicts")
        assert check.status == CheckStatus.INCOMPLETE
        assert check.status != CheckStatus.PASS

    def test_duplicate_user_check_is_incomplete_not_pass(self, store_with_plan):
        """The other one."""
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(store_with_plan)

        check = next(c for c in result.checks if c.name == "Duplicate users")
        assert check.status == CheckStatus.INCOMPLETE

    def test_incomplete_detail_says_why(self, store_with_plan):
        """The operator must be able to tell this from a genuine empty result."""
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(store_with_plan)

        incomplete = [c for c in result.checks if c.status == CheckStatus.INCOMPLETE]
        assert incomplete, "expected at least one INCOMPLETE check"
        for c in incomplete:
            assert "could not" in c.detail.lower() or "not queried" in c.detail.lower()

    def test_overall_is_not_pass(self, store_with_plan):
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(store_with_plan)
        assert result.overall != CheckStatus.PASS

    def test_incomplete_is_its_own_status_not_folded_into_pass_or_warn(
        self, store_with_plan
    ):
        """"Could not check" is neither "passed" nor "the org is not ready".

        It gets its own status because the remedy differs — fix auth and re-run,
        rather than fix the org. A genuine FAIL still outranks it: on this fixture
        a store-only check (E911 readiness, which needs no fetch) legitimately
        fails, so ``overall`` is FAIL. That ordering is deliberate — a definite
        failure is the more actionable message.
        """
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(store_with_plan)

        assert result.overall not in (
            CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP
        )
        assert any(c.status == CheckStatus.INCOMPLETE for c in result.checks)

    def test_overall_is_incomplete_when_nothing_else_objects(self, tmp_path):
        """With no store-level failures to outrank it, INCOMPLETE is the verdict."""
        s = MigrationStore(tmp_path / "empty.db")
        trunk = CanonicalTrunk(
            canonical_id="trunk:t1",
            provenance=_prov(),
            name="HQ-Trunk",
        )
        trunk.status = MigrationStatus.ANALYZED
        s.upsert_object(trunk)

        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("No token found"),
        ):
            result = PreflightRunner().run(s)
        s.close()

        assert result.overall == CheckStatus.INCOMPLETE, (
            "statuses present: "
            + ", ".join(f"{c.name}={c.status.value}" for c in result.checks)
        )


class TestSuccessfulFetchStillWorks:
    """A genuine empty result must still be reportable as PASS."""

    def test_empty_but_successful_fetch_can_pass(self, store_with_plan):
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            return_value=[],
        ):
            result = PreflightRunner().run(store_with_plan)

        trunks = next(c for c in result.checks if c.name == "Trunks")
        assert trunks.status == CheckStatus.PASS, (
            "an empty Webex trunk list genuinely means no name conflicts"
        )
        assert "no name conflicts" in trunks.detail.lower()

    def test_incomplete_never_appears_when_fetches_succeed(self, store_with_plan):
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            return_value=[],
        ):
            result = PreflightRunner().run(store_with_plan)
        assert not [
            c for c in result.checks if c.status == CheckStatus.INCOMPLETE
        ]


class TestRegistryNamesCannotDrift:
    def test_registered_names_match_the_registry(self, tmp_path):
        """CHECK_NAMES must equal the dict `run()` actually builds.

        The total is what tells a full run from a partial one, so a name added to
        one and not the other would silently shrink the denominator.
        """
        s = MigrationStore(tmp_path / "names.db")
        with patch(
            "wxcli.migration.preflight.runner._run_wxcli",
            side_effect=PreflightError("no token"),
        ):
            result = PreflightRunner().run(s)
        s.close()

        assert len(result.checks) == len(PreflightRunner.registered_check_names())

    def test_ten_checks_are_registered(self):
        """The measured ground truth for finding F17 — no source claimed 10."""
        assert len(PreflightRunner.registered_check_names()) == 10
