"""Tests for SelectiveCallHandlingAnalyzer."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser,
    DecisionType,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers.selective_call_handling import (
    SelectiveCallHandlingAnalyzer,
)


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="t",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name: str = "t.db") -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), name))


class TestEmptyStore:
    def test_analyzer_returns_empty_on_empty_store(self, tmp_path):
        store = _store(tmp_path)
        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        assert decisions == []

    def test_analyzer_metadata(self):
        analyzer = SelectiveCallHandlingAnalyzer()
        assert analyzer.name == "selective_call_handling"
        assert DecisionType.FEATURE_APPROXIMATION in analyzer.decision_types
        assert "css_routing" in analyzer.depends_on
