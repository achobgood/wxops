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


def _seed_user_with_dn_in_partitions(
    store: MigrationStore,
    userid: str,
    location_id: str,
    dn: str,
    partition_csses: dict[str, list[str]],
) -> None:
    """Seed a user, partitions, CSSes, DN cross-refs, and user_has_css.

    `partition_csses`: {partition_name: [css_name, ...]} — each partition is
    placed in the given CSSes, and each CSS is associated with the user via
    user_has_css. The DN appears in every partition listed.
    """
    user_id = f"user:{userid}"
    store.upsert_object(
        CanonicalUser(
            canonical_id=user_id,
            provenance=_prov(userid),
            status=MigrationStatus.ANALYZED,
            cucm_userid=userid,
            location_id=location_id,
            extension=dn,
        )
    )
    # Partitions and DN cross-refs
    for pt_name in partition_csses:
        store.upsert_object(
            MigrationObject(
                canonical_id=f"partition:{pt_name}",
                provenance=_prov(pt_name),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"partition_name": pt_name},
            )
        )
        # Use one DN canonical_id per partition (matches cross_reference.py form)
        per_partition_dn_id = f"dn:{dn}:{pt_name}"
        # DN cross-ref endpoints must exist as objects (FK constraint)
        store.upsert_object(
            MigrationObject(
                canonical_id=per_partition_dn_id,
                provenance=_prov(per_partition_dn_id),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"dn": dn, "partition": pt_name},
            )
        )
        store.add_cross_ref(per_partition_dn_id, f"partition:{pt_name}", "dn_in_partition")
        store.add_cross_ref(user_id, per_partition_dn_id, "user_has_primary_dn")
    # CSSes and user_has_css
    seen_csses: set[str] = set()
    for pt_name, css_names in partition_csses.items():
        for css_name in css_names:
            css_id = f"css:{css_name}"
            if css_name not in seen_csses:
                store.upsert_object(
                    MigrationObject(
                        canonical_id=css_id,
                        provenance=_prov(css_name),
                        status=MigrationStatus.NORMALIZED,
                        pre_migration_state={"css_name": css_name, "partitions": []},
                    )
                )
                store.add_cross_ref(user_id, css_id, "user_has_css")
                seen_csses.add(css_name)
            store.add_cross_ref(css_id, f"partition:{pt_name}", "css_contains_partition")


class TestMultiPartitionDN:
    def test_dn_in_two_partitions_with_different_css_scopes(self, tmp_path):
        """Pattern 1: DN in 2 partitions, each reachable via different CSS."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="alice",
            location_id="loc:hq",
            dn="1001",
            partition_csses={
                "PT_Internal": ["CSS_Internal"],
                "PT_External": ["CSS_External"],
            },
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch_decisions = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert len(sch_decisions) == 1
        d = sch_decisions[0]
        assert d.severity == "MEDIUM"
        assert d.type == DecisionType.FEATURE_APPROXIMATION
        assert "1001" in d.summary
        assert "PT_Internal" in d.context["partitions"]
        assert "PT_External" in d.context["partitions"]
        assert d.context["user_canonical_id"] == "user:alice"
        assert d.context["recommended_webex_feature"] == "Selective Forward"

    def test_dn_in_two_partitions_same_css_scope_low_severity(self, tmp_path):
        """Pattern 1 weak case: DN in 2 partitions but both reachable via same CSS."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="bob",
            location_id="loc:hq",
            dn="1002",
            partition_csses={
                "PT_A": ["CSS_All"],
                "PT_B": ["CSS_All"],
            },
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch_decisions = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert len(sch_decisions) == 1
        assert sch_decisions[0].severity == "LOW"

    def test_dn_in_single_partition_no_decision(self, tmp_path):
        """Pattern 1 silent case: DN only in one partition."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="carol",
            location_id="loc:hq",
            dn="1003",
            partition_csses={"PT_Only": ["CSS_All"]},
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        assert decisions == []

    def test_multi_site_dn_filtered_out(self, tmp_path):
        """Mitigation 8a: multi-site DN is NOT a selective call handling pattern."""
        store = _store(tmp_path)
        # Two users at different locations sharing the same DN number
        _seed_user_with_dn_in_partitions(
            store, userid="dave", location_id="loc:nyc", dn="2000",
            partition_csses={"PT_NYC": ["CSS_NYC"]},
        )
        _seed_user_with_dn_in_partitions(
            store, userid="eve", location_id="loc:lax", dn="2000",
            partition_csses={"PT_LAX": ["CSS_LAX"]},
        )
        # Both DN cross-refs (dn:2000:PT_NYC and dn:2000:PT_LAX) exist; the
        # multi-site filter should suppress this case.

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch_decisions = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert sch_decisions == []
