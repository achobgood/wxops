"""Tests for executive/assistant normalizers and cross-references."""

import pytest

from wxcli.migration.models import MigrationObject, MigrationStatus
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder
from wxcli.migration.transform.normalizers import (
    normalize_executive_assistant_pair,
    normalize_executive_settings,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store():
    """In-memory SQLite store for tests."""
    s = MigrationStore(":memory:")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# TestNormalizeExecutiveAssistantPair
# ---------------------------------------------------------------------------


class TestNormalizeExecutiveAssistantPair:
    def test_normalize_pair(self):
        raw = {
            "executive_userid": "jsmith",
            "assistant_userid": "jdoe",
            "executive_pkid": "{EXEC-PKID-1}",
            "assistant_pkid": "{ASST-PKID-1}",
        }
        obj = normalize_executive_assistant_pair(raw, cluster="lab")

        assert isinstance(obj, MigrationObject)
        assert obj.canonical_id == "exec_asst_pair:jsmith:jdoe"
        assert obj.status == MigrationStatus.NORMALIZED

        state = obj.pre_migration_state
        assert state["executive_userid"] == "jsmith"
        assert state["assistant_userid"] == "jdoe"
        assert state["executive_pkid"] == "{EXEC-PKID-1}"
        assert state["assistant_pkid"] == "{ASST-PKID-1}"

    def test_normalize_pair_provenance(self):
        raw = {
            "executive_userid": "jsmith",
            "assistant_userid": "jdoe",
            "pkid": "{PAIR-PKID}",
        }
        obj = normalize_executive_assistant_pair(raw, cluster="prod")

        assert obj.provenance.source_system == "cucm"
        assert obj.provenance.cluster == "prod"
        assert obj.provenance.source_id == "{PAIR-PKID}"


# ---------------------------------------------------------------------------
# TestNormalizeExecutiveSettings
# ---------------------------------------------------------------------------


class TestNormalizeExecutiveSettings:
    def test_normalize_executive_role(self):
        raw = {
            "userid": "jsmith",
            "service_name": "Executive",
            "servicetype": "Feature",
        }
        obj = normalize_executive_settings(raw)

        assert obj.canonical_id == "exec_setting:jsmith"
        assert obj.status == MigrationStatus.NORMALIZED

        state = obj.pre_migration_state
        assert state["role"] == "EXECUTIVE"
        assert state["userid"] == "jsmith"
        assert state["service_name"] == "Executive"
        assert state["servicetype"] == "Feature"

    def test_normalize_assistant_role(self):
        raw = {
            "userid": "jdoe",
            "service_name": "Executive-Assistant",
            "servicetype": "Feature",
        }
        obj = normalize_executive_settings(raw)

        assert obj.canonical_id == "exec_setting:jdoe"
        state = obj.pre_migration_state
        assert state["role"] == "EXECUTIVE_ASSISTANT"
        assert state["service_name"] == "Executive-Assistant"


# ---------------------------------------------------------------------------
# TestExecutiveAssistantCrossRefs
# ---------------------------------------------------------------------------


class TestExecutiveAssistantCrossRefs:
    def test_builds_executive_assistant_refs(self, store):
        # Seed a pair object
        pair = normalize_executive_assistant_pair({
            "executive_userid": "jsmith",
            "assistant_userid": "jdoe",
            "executive_pkid": "{E1}",
            "assistant_pkid": "{A1}",
        })
        store.upsert_object(pair)

        # Seed executive setting
        exec_setting = normalize_executive_settings({
            "userid": "jsmith",
            "service_name": "Executive",
            "servicetype": "Feature",
        })
        store.upsert_object(exec_setting)

        # Seed assistant setting
        asst_setting = normalize_executive_settings({
            "userid": "jdoe",
            "service_name": "Executive-Assistant",
            "servicetype": "Feature",
        })
        # Override canonical_id to avoid collision (both would be exec_setting:userid)
        # In real data each user has their own userid so no collision, but here
        # we need both in the store
        store.upsert_object(asst_setting)

        # Build cross-refs
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        # Verify pair refs
        assert counts["executive_has_assistant"] == 1
        assert counts["assistant_serves_executive"] == 1

        assistants = store.find_cross_refs("user:jsmith", "executive_has_assistant")
        assert "user:jdoe" in assistants

        executives = store.find_cross_refs("user:jdoe", "assistant_serves_executive")
        assert "user:jsmith" in executives

        # Verify setting refs
        assert counts["user_is_executive"] == 1
        assert counts["user_is_assistant"] == 1

        exec_refs = store.find_cross_refs("user:jsmith", "user_is_executive")
        assert "exec_setting:jsmith" in exec_refs

        asst_refs = store.find_cross_refs("user:jdoe", "user_is_assistant")
        assert "exec_setting:jdoe" in asst_refs

    def test_no_pairs_no_refs(self, store):
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        assert counts.get("executive_has_assistant", 0) == 0
        assert counts.get("assistant_serves_executive", 0) == 0
        assert counts.get("user_is_executive", 0) == 0
        assert counts.get("user_is_assistant", 0) == 0
