# tests/migration/transform/test_shared_line_status.py
"""Test that shared_line objects reach 'analyzed' status after analysis pipeline."""
from datetime import datetime, timezone
from wxcli.migration.models import (
    CanonicalSharedLine, CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def test_shared_lines_reach_analyzed_after_analysis():
    """Shared lines created by cross-ref builder at 'normalized' must transition to 'analyzed'."""
    store = MigrationStore(":memory:")

    # Two users sharing a line
    store.upsert_object(CanonicalUser(
        canonical_id="user:alice", provenance=_prov("alice"),
        status=MigrationStatus.ANALYZED, emails=["alice@test.com"],
    ))
    store.upsert_object(CanonicalUser(
        canonical_id="user:bob", provenance=_prov("bob"),
        status=MigrationStatus.ANALYZED, emails=["bob@test.com"],
    ))

    # Shared line at normalized (as cross-ref builder creates it)
    sl = CanonicalSharedLine(
        canonical_id="shared_line:1001:PT-Internal",
        provenance=_prov("1001:PT-Internal"),
        status=MigrationStatus.NORMALIZED,
        dn_canonical_id="dn:1001:PT-Internal",
        owner_canonical_ids=["user:alice", "user:bob"],
        device_canonical_ids=["device:SEP111", "device:SEP222"],
    )
    store.upsert_object(sl)

    # Run analysis pipeline
    pipeline = AnalysisPipeline()
    pipeline.run(store)

    # Verify shared line is now at analyzed status
    obj = store.get_object("shared_line:1001:PT-Internal")
    assert obj is not None
    assert obj.get("status") == "analyzed", (
        f"Shared line should be 'analyzed' after analysis pipeline, got '{obj.get('status')}'"
    )
