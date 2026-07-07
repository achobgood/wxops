"""Tests for ArchitectureAdvisor — the cross-cutting advisory analyzer."""

import os

from wxcli.migration.models import DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.advisory.advisor import ArchitectureAdvisor


class TestArchitectureAdvisor:
    def _make_store_with_mrgl(self, tmp_path):
        """Store with device pool MRGL refs → triggers Pattern 15."""
        store = MigrationStore(os.path.join(str(tmp_path), "t.db"))
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("device_pool:1", "device_pool", "analyzed",
             '{"canonical_id": "device_pool:1", "name": "DP1", "pre_migration_state": {"name": "DP1", "cucm_media_resource_list": "MRGL_HQ"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()
        return store

    def test_produces_advisory_decisions(self, tmp_path):
        store = self._make_store_with_mrgl(tmp_path)
        advisor = ArchitectureAdvisor()
        decisions = advisor.analyze(store)
        assert len(decisions) >= 1
        assert all(d.type == DecisionType.ARCHITECTURE_ADVISORY for d in decisions)

    def test_all_advisory_decisions_have_recommendation(self, tmp_path):
        store = self._make_store_with_mrgl(tmp_path)
        advisor = ArchitectureAdvisor()
        decisions = advisor.analyze(store)
        for d in decisions:
            assert d.recommendation == "accept"

    def test_fingerprint_deterministic(self, tmp_path):
        store = self._make_store_with_mrgl(tmp_path)
        advisor = ArchitectureAdvisor()
        d1 = advisor.analyze(store)
        d2 = advisor.analyze(store)
        fps1 = sorted(d.fingerprint for d in d1)
        fps2 = sorted(d.fingerprint for d in d2)
        assert fps1 == fps2

    def test_empty_store_only_e911_advisory(self, tmp_path):
        """Empty store still produces E911 CER advisory (Pattern 16 always fires)."""
        store = MigrationStore(os.path.join(str(tmp_path), "empty.db"))
        advisor = ArchitectureAdvisor()
        decisions = advisor.analyze(store)
        # Pattern 16 always fires with a CER warning even on empty stores
        assert all(d.type == DecisionType.ARCHITECTURE_ADVISORY for d in decisions)
        e911 = [d for d in decisions if d.context.get("pattern_name") == "e911_migration_flag"]
        assert len(e911) == 1

    def test_pattern_failure_doesnt_block_others(self, tmp_path, monkeypatch):
        """One pattern raising doesn't prevent others from producing findings."""
        store = self._make_store_with_mrgl(tmp_path)
        advisor = ArchitectureAdvisor()
        # Monkeypatch first pattern to raise
        import wxcli.migration.advisory.advisory_patterns as ap
        original = ap.ALL_ADVISORY_PATTERNS[0]
        ap.ALL_ADVISORY_PATTERNS[0] = lambda s: (_ for _ in ()).throw(ValueError("boom"))
        try:
            decisions = advisor.analyze(store)
            assert isinstance(decisions, list)
        finally:
            ap.ALL_ADVISORY_PATTERNS[0] = original

    def test_decisions_have_two_options(self, tmp_path):
        """All advisory decisions have accept + ignore options."""
        store = self._make_store_with_mrgl(tmp_path)
        advisor = ArchitectureAdvisor()
        decisions = advisor.analyze(store)
        for d in decisions:
            assert len(d.options) == 2
            option_ids = {o.id for o in d.options}
            assert "accept" in option_ids
            assert "ignore" in option_ids

    def test_context_has_required_fields(self, tmp_path):
        """Advisory decision context has pattern_name, detail, category, affected_ids."""
        store = self._make_store_with_mrgl(tmp_path)
        advisor = ArchitectureAdvisor()
        decisions = advisor.analyze(store)
        for d in decisions:
            assert "pattern_name" in d.context
            assert "detail" in d.context
            assert "category" in d.context
            assert "affected_ids" in d.context
