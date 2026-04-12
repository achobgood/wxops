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


def _seed_partition_with_dns(
    store: MigrationStore,
    partition_name: str,
    dn_count: int,
    in_csses: list[str],
    all_css_names: list[str],
) -> None:
    """Seed a partition with N DNs and place it in a subset of CSSes.

    Notes on FK constraints: every cross-ref target must be a real object
    in `objects`, so we upsert the partition and each DN as MigrationObjects
    before adding the cross-refs.
    """
    pt_id = f"partition:{partition_name}"
    store.upsert_object(
        MigrationObject(
            canonical_id=pt_id,
            provenance=_prov(partition_name),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"partition_name": partition_name},
        )
    )
    for i in range(dn_count):
        dn_cid = f"dn:9{i:03d}:{partition_name}"
        store.upsert_object(
            MigrationObject(
                canonical_id=dn_cid,
                provenance=_prov(dn_cid),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"dn": f"9{i:03d}", "partition": partition_name},
            )
        )
        store.add_cross_ref(pt_id, dn_cid, "partition_has_pattern")
    # Make sure all CSSes exist; place this partition only in `in_csses`
    for css_name in all_css_names:
        css_id = f"css:{css_name}"
        if store.get_object(css_id) is None:
            store.upsert_object(
                MigrationObject(
                    canonical_id=css_id,
                    provenance=_prov(css_name),
                    status=MigrationStatus.NORMALIZED,
                    pre_migration_state={"css_name": css_name, "partitions": []},
                )
            )
    for css_name in in_csses:
        store.add_cross_ref(f"css:{css_name}", pt_id, "css_contains_partition")


class TestLowMembershipPartition:
    def test_low_membership_partition_in_subset_fires(self, tmp_path):
        """Partition with 3 DNs in 1 of 4 CSSes → MEDIUM severity decision."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_VIP_Bypass",
            dn_count=3,
            in_csses=["CSS_VIP"],
            all_css_names=["CSS_All", "CSS_Internal", "CSS_External", "CSS_VIP"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert len(sch) == 1
        d = sch[0]
        assert d.severity == "MEDIUM"
        assert "PT_VIP_Bypass" in d.context["partitions"]
        assert d.context["dn_count"] == 3
        assert d.context["css_count"] == 1
        assert d.context["total_css_count"] == 4

    def test_high_membership_partition_silent(self, tmp_path):
        """Partition with 50 DNs → not VIP/priority pattern, no decision."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_Standard",
            dn_count=50,
            in_csses=["CSS_All"],
            all_css_names=["CSS_All", "CSS_Other"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert sch == []

    def test_low_membership_in_all_csses_silent(self, tmp_path):
        """Partition with few DNs but in ALL CSSes is universal, not VIP."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_Few_All",
            dn_count=2,
            in_csses=["CSS_A", "CSS_B"],
            all_css_names=["CSS_A", "CSS_B"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert sch == []


class TestNamingConvention:
    def test_partition_named_vip_with_structural_signal_high(self, tmp_path):
        """VIP-named partition that ALSO matches low-membership → MEDIUM severity."""
        store = _store(tmp_path)
        # Reuse the seeding helper that puts the partition in a strict subset
        _seed_partition_with_dns(
            store,
            partition_name="VIP_PT",
            dn_count=2,
            in_csses=["CSS_VIP"],
            all_css_names=["CSS_All", "CSS_Internal", "CSS_External", "CSS_VIP"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        # The naming convention heuristic should NOT add a duplicate decision
        # when the same partition was already covered by low_membership.
        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "naming_convention"
        ]
        # No duplicate naming decision when structural already fired
        assert sch == []

        # And the structural decision should still be present at MEDIUM severity
        struct = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert len(struct) == 1
        assert struct[0].severity == "MEDIUM"

    def test_partition_named_vip_only_low_severity(self, tmp_path):
        """VIP-named partition with no structural signal → LOW severity name-only."""
        store = _store(tmp_path)
        # 50 DNs in this partition disqualifies the structural heuristic
        _seed_partition_with_dns(
            store,
            partition_name="Executive_PT",
            dn_count=50,
            in_csses=["CSS_All"],
            all_css_names=["CSS_All"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "naming_convention"
        ]
        assert len(sch) == 1
        d = sch[0]
        assert d.severity == "LOW"
        assert "Executive_PT" in d.context["partitions"]
        assert d.context["confidence"] == "LOW"
        assert d.context["recommended_webex_feature"] == "Priority Alert"

    def test_neutral_named_partition_silent(self, tmp_path):
        """Partition with no VIP keyword and no structural signal → no decision."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_Standard",
            dn_count=20,
            in_csses=["CSS_All"],
            all_css_names=["CSS_All"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        assert decisions == []


class TestFingerprintAndIdempotency:
    def test_fingerprint_stable_across_runs(self, tmp_path):
        """Re-running the analyzer produces identical fingerprints."""
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
        run1 = analyzer.analyze(store)
        run2 = analyzer.analyze(store)

        assert len(run1) == len(run2)
        prints1 = sorted(d.fingerprint for d in run1)
        prints2 = sorted(d.fingerprint for d in run2)
        assert prints1 == prints2

    def test_distinct_dns_get_distinct_fingerprints(self, tmp_path):
        """Two different multi-partition DNs produce two distinct decisions."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store, userid="u1", location_id="loc:hq", dn="1001",
            partition_csses={"PT_A": ["CSS_A"], "PT_B": ["CSS_B"]},
        )
        _seed_user_with_dn_in_partitions(
            store, userid="u2", location_id="loc:hq", dn="1002",
            partition_csses={"PT_C": ["CSS_C"], "PT_D": ["CSS_D"]},
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert len(sch) == 2
        assert sch[0].fingerprint != sch[1].fingerprint
