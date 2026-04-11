"""Tests for executive/assistant advisory pattern and recommendation rule."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from wxcli.migration.advisory.advisory_patterns import detect_executive_assistant_migration
from wxcli.migration.advisory.recommendation_rules import recommend_missing_data
from wxcli.migration.models import (
    CanonicalUser,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov(name="test"):
    return Provenance(
        source_system="cucm",
        source_id="t",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name="t.db"):
    return MigrationStore(os.path.join(str(tmp_path), name))


def _seed_user(store, userid):
    store.upsert_object(
        CanonicalUser(
            canonical_id=f"user:{userid}",
            provenance=_prov(userid),
            status=MigrationStatus.ANALYZED,
            emails=[f"{userid}@acme.com"],
            cucm_userid=userid,
        )
    )


def _seed_pair(store, exec_userid, asst_userid):
    store.upsert_object(
        MigrationObject(
            canonical_id=f"exec_asst_pair:{exec_userid}:{asst_userid}",
            provenance=_prov(f"{exec_userid}:{asst_userid}"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "executive_userid": exec_userid,
                "assistant_userid": asst_userid,
            },
        )
    )


# ===================================================================
# Advisory pattern tests
# ===================================================================


class TestExecutiveAssistantPattern:
    """Tests for detect_executive_assistant_migration pattern."""

    def test_pattern_fires_with_complete_pairs(self, tmp_path):
        """Both users seeded -> severity MEDIUM, category migrate_as_is."""
        store = _store(tmp_path)
        _seed_user(store, "jsmith")
        _seed_user(store, "jdoe")
        _seed_pair(store, "jsmith", "jdoe")

        findings = detect_executive_assistant_migration(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.pattern_name == "executive_assistant_migration"
        assert f.severity == "MEDIUM"
        assert f.category == "migrate_as_is"
        assert "will migrate automatically" in f.summary
        assert len(f.affected_objects) == 1

    def test_pattern_silent_no_pairs(self, tmp_path):
        """No pairs in store -> empty findings."""
        store = _store(tmp_path)
        _seed_user(store, "jsmith")

        findings = detect_executive_assistant_migration(store)

        assert findings == []

    def test_pattern_broken_pair_high_severity(self, tmp_path):
        """One side missing -> severity HIGH."""
        store = _store(tmp_path)
        _seed_user(store, "jsmith")
        # assistant 'missing_user' not seeded
        _seed_pair(store, "jsmith", "missing_user")

        findings = detect_executive_assistant_migration(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.severity == "HIGH"
        assert f.category == "out_of_scope"
        assert "broken" in f.summary.lower() or "broken" in f.detail.lower()
        assert "missing_user" in f.detail

    def test_pattern_mixed_complete_and_broken(self, tmp_path):
        """Mix of complete and broken pairs -> severity HIGH, mentions broken."""
        store = _store(tmp_path)
        _seed_user(store, "exec1")
        _seed_user(store, "asst1")
        _seed_user(store, "exec2")
        # asst2 NOT seeded -> broken pair

        _seed_pair(store, "exec1", "asst1")  # complete
        _seed_pair(store, "exec2", "asst2")  # broken

        findings = detect_executive_assistant_migration(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.severity == "HIGH"
        assert f.category == "migrate_as_is"
        assert "missing" in f.summary.lower()
        assert "asst2" in f.detail

    def test_pattern_all_broken_multiple(self, tmp_path):
        """Multiple pairs all broken -> out_of_scope."""
        store = _store(tmp_path)
        # No users seeded at all
        _seed_pair(store, "exec1", "asst1")
        _seed_pair(store, "exec2", "asst2")

        findings = detect_executive_assistant_migration(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.severity == "HIGH"
        assert f.category == "out_of_scope"
        assert "2" in f.summary and "missing" in f.summary.lower()

    def test_pattern_multiple_complete_pairs(self, tmp_path):
        """Multiple complete pairs -> MEDIUM, all migrate."""
        store = _store(tmp_path)
        _seed_user(store, "exec1")
        _seed_user(store, "asst1")
        _seed_user(store, "exec2")
        _seed_user(store, "asst2")

        _seed_pair(store, "exec1", "asst1")
        _seed_pair(store, "exec2", "asst2")

        findings = detect_executive_assistant_migration(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.severity == "MEDIUM"
        assert f.category == "migrate_as_is"
        assert "2" in f.summary and "migrate automatically" in f.summary.lower()
        assert len(f.affected_objects) == 2


# ===================================================================
# Recommendation rule tests
# ===================================================================


class TestBrokenPairRecommendation:
    """Tests for recommend_missing_data executive/assistant extension."""

    def test_broken_pair_permanently_excluded_recommends_skip(self):
        """Context with permanently_excluded=True -> returns ('skip', ...)."""
        context = {
            "missing_reason": "executive_assistant_broken_pair",
            "permanently_excluded": True,
            "missing_side": "assistant",
        }
        result = recommend_missing_data(context, [])

        assert result is not None
        option, reasoning = result
        assert option == "skip"
        assert "assistant" in reasoning
        assert "permanently excluded" in reasoning
        assert "manual Webex configuration" in reasoning

    def test_broken_pair_might_be_added_returns_none(self):
        """Context with missing_reason but no permanently_excluded -> None."""
        context = {
            "missing_reason": "executive_assistant_broken_pair",
            "missing_side": "executive",
        }
        result = recommend_missing_data(context, [])

        assert result is None

    def test_broken_pair_permanently_excluded_executive_side(self):
        """Permanently excluded executive side uses correct label."""
        context = {
            "missing_reason": "executive_assistant_broken_pair",
            "permanently_excluded": True,
            "missing_side": "executive",
        }
        result = recommend_missing_data(context, [])

        assert result is not None
        option, reasoning = result
        assert option == "skip"
        assert "executive" in reasoning

    def test_broken_pair_default_missing_side(self):
        """Missing missing_side defaults to 'user'."""
        context = {
            "missing_reason": "executive_assistant_broken_pair",
            "permanently_excluded": True,
        }
        result = recommend_missing_data(context, [])

        assert result is not None
        _, reasoning = result
        assert "user" in reasoning
