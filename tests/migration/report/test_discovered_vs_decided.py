"""F18 — the assessment report contradicted itself about one population.

`generate_key_findings` rendered "1017 of 1100 phones — 611 need firmware
conversion; 91 need replacement; 315 transition to Webex App", counting
`store.get_objects("device")` by `compatibility_tier`, status-unfiltered.
Appendix B's `Incompatible Devices (405)` enumerated 314 transition rows,
because it counts decisions.

Measured on dcloud-fresh: `webex_app` is 314 analyzed + 1 normalized = 315. The
stranded device never reached analyze, so it never got a decision. Both numbers
are defensible; the document presented two measures of one concept with no way
to tell them apart.

Adam's call: label both and show the gap. Filtering the key finding to analyzed
objects was rejected — that is F08's defect (a status filter made 23 users
vanish silently), applied to a customer document.

The fixture below is the measured dcloud-fresh device population.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.report.appendix import _data_quality_group, _decisions_group
from wxcli.migration.report.explainer import generate_key_findings
from wxcli.migration.store import MigrationStore

# tier, status, count — as measured on dcloud-fresh
DCLOUD_FRESH_DEVICES = [
    (DeviceCompatibilityTier.CONVERTIBLE, MigrationStatus.ANALYZED, 611),
    (DeviceCompatibilityTier.INCOMPATIBLE, MigrationStatus.ANALYZED, 91),
    (DeviceCompatibilityTier.INFRASTRUCTURE, MigrationStatus.ANALYZED, 10),
    (DeviceCompatibilityTier.INFRASTRUCTURE, MigrationStatus.NORMALIZED, 3),
    (DeviceCompatibilityTier.NATIVE_MPP, MigrationStatus.ANALYZED, 70),
    (DeviceCompatibilityTier.WEBEX_APP, MigrationStatus.ANALYZED, 314),
    (DeviceCompatibilityTier.WEBEX_APP, MigrationStatus.NORMALIZED, 1),
]


@pytest.fixture
def dcloud_fresh_store(tmp_path):
    store = MigrationStore(tmp_path / "migration.db")
    n = 0
    for tier, status, count in DCLOUD_FRESH_DEVICES:
        for _ in range(count):
            n += 1
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:SEP{n:012d}",
                provenance=Provenance(
                    source_system="cucm", source_id=f"pk{n}",
                    source_name=f"SEP{n:012d}",
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=status,
                mac=f"{n:012X}",
                compatibility_tier=tier,
            ))
    store.conn.commit()
    yield store
    store.close()


def _phone_finding(store) -> str:
    findings = generate_key_findings(store)
    matching = [f["text"] for f in findings if "phones" in f["text"]]
    assert matching, f"no phone finding in {findings}"
    return matching[0]


class TestKeyFindingNamesItsMeasure:
    def test_counts_stay_status_unfiltered(self, dcloud_fresh_store):
        """315, not 314 — the assessment describes what was discovered."""
        text = _phone_finding(dcloud_fresh_store)
        assert "611 need firmware conversion" in text
        assert "91 need replacement" in text
        assert "315 transition to Webex App" in text
        assert "1017 of 1100 phones discovered" in text

    def test_the_gap_is_named_rather_than_hidden(self, dcloud_fresh_store):
        text = _phone_finding(dcloud_fresh_store)
        assert "1 device did not complete analysis" in text
        assert "carries no migration decision" in text
        assert "Appendix J" in text

    def test_no_gap_clause_when_analysis_is_complete(self, tmp_path):
        store = MigrationStore(tmp_path / "clean.db")
        for i in range(5):
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:SEP{i:012d}",
                provenance=Provenance(
                    source_system="cucm", source_id=f"pk{i}", source_name="x",
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=MigrationStatus.ANALYZED,
                mac=f"{i:012X}",
                compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
            ))
        store.conn.commit()
        try:
            text = _phone_finding(store)
        finally:
            store.close()
        assert "5 of 5 phones discovered" in text
        assert "did not complete analysis" not in text

    def test_plural_wording(self, tmp_path):
        store = MigrationStore(tmp_path / "plural.db")
        for i, status in enumerate(
            [MigrationStatus.ANALYZED, MigrationStatus.NORMALIZED,
             MigrationStatus.NORMALIZED]
        ):
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:SEP{i:012d}",
                provenance=Provenance(
                    source_system="cucm", source_id=f"pk{i}", source_name="x",
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=status, mac=f"{i:012X}",
                compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
            ))
        store.conn.commit()
        try:
            text = _phone_finding(store)
        finally:
            store.close()
        assert "2 devices did not complete analysis" in text
        assert "carry no migration decision" in text


class TestAppendixJShowsTheStrandedObjects:
    def test_pointer_target_actually_lists_them(self, dcloud_fresh_store):
        """The key finding says "see Appendix J" — J must carry the answer."""
        html_out = _data_quality_group(dcloud_fresh_store)
        assert "Objects that did not complete analysis" in html_out
        assert "4 objects stopped advancing before analysis finished" in html_out
        assert "normalized" in html_out
        assert "Device" in html_out

    def test_section_absent_when_analysis_is_complete(self, tmp_path):
        store = MigrationStore(tmp_path / "clean.db")
        store.upsert_object(CanonicalDevice(
            canonical_id="device:SEP000000000001",
            provenance=Provenance(
                source_system="cucm", source_id="pk1", source_name="x",
                extracted_at=datetime.now(timezone.utc),
            ),
            status=MigrationStatus.ANALYZED, mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.conn.commit()
        try:
            html_out = _data_quality_group(store)
        finally:
            store.close()
        assert "did not complete analysis" not in html_out


class TestAppendixBNamesItsUnit:
    def test_decision_block_headings_say_decisions(self, tmp_path):
        store = MigrationStore(tmp_path / "d.db")
        for i in range(3):
            store.save_decision({
                "decision_id": f"D{i:04d}",
                "type": "DEVICE_INCOMPATIBLE",
                "severity": "HIGH",
                "summary": "s",
                "context": {},
                "options": [],
                "fingerprint": f"fp{i}",
                "run_id": "r1",
            })
        store.conn.commit()
        try:
            html_out = _decisions_group(store)
        finally:
            store.close()
        assert "(3 decisions)" in html_out
        assert "(3)" not in html_out
