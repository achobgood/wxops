"""Verify phone_uses_common_phone_config cross-reference is built."""
from datetime import datetime, timezone
from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder

def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )

def test_phone_uses_common_phone_config_ref():
    store = MigrationStore(":memory:")
    phone = MigrationObject(
        canonical_id="phone:SEP001122AABBCC",
        provenance=_prov("SEP001122AABBCC"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "commonPhoneConfigName": {"_value_1": "Standard Common Phone", "uuid": "{CPC1}"},
            "cucm_common_phone_config": "Standard Common Phone",
        },
    )
    store.upsert_object(phone)
    cpc = MigrationObject(
        canonical_id="info_common_phone_config:Standard Common Phone",
        provenance=_prov("Standard Common Phone"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "Standard Common Phone"},
    )
    store.upsert_object(cpc)
    builder = CrossReferenceBuilder(store)
    counts = builder.build()
    assert counts.get("phone_uses_common_phone_config", 0) >= 1
    refs = store.get_cross_refs(
        from_id="phone:SEP001122AABBCC",
        relationship="phone_uses_common_phone_config",
    )
    assert len(refs) == 1
    assert refs[0]["to_id"] == "info_common_phone_config:Standard Common Phone"

def test_phone_without_cpc_no_ref():
    store = MigrationStore(":memory:")
    phone = MigrationObject(
        canonical_id="phone:SEP000000000000",
        provenance=_prov("SEP000000000000"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={},
    )
    store.upsert_object(phone)
    builder = CrossReferenceBuilder(store)
    counts = builder.build()
    assert counts.get("phone_uses_common_phone_config", 0) == 0
