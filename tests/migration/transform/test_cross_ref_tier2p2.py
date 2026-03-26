"""Tests for Tier2-Phase2 cross-reference relationships."""
from datetime import datetime, timezone

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _setup_store_with_templates():
    """Store with a phone that references both template types."""
    store = MigrationStore(":memory:")

    # Phone with template references
    phone = MigrationObject(
        canonical_id="phone:SEP001122334455",
        provenance=_prov("SEP001122334455"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "cucm_phone_template": "Standard 8845",
            "cucm_softkey_template": "Standard User",
            "cucm_device_pool": "DP-HQ",
            "cucm_owner_user": "jdoe",
        },
    )
    store.upsert_object(phone)

    # Button template
    bt = MigrationObject(
        canonical_id="button_template:Standard 8845",
        provenance=_prov("Standard 8845"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "Standard 8845", "buttons": []},
    )
    store.upsert_object(bt)

    # Softkey template
    sk = MigrationObject(
        canonical_id="softkey_template:Standard User",
        provenance=_prov("Standard User"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": "Standard User", "call_states": {}},
    )
    store.upsert_object(sk)

    # Minimal device pool + user so existing build steps don't break
    dp = MigrationObject(
        canonical_id="device_pool:DP-HQ", provenance=_prov("DP-HQ"),
        status=MigrationStatus.NORMALIZED,
    )
    store.upsert_object(dp)

    user = MigrationObject(
        canonical_id="user:jdoe", provenance=_prov("jdoe"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"userid": "jdoe"},
    )
    store.upsert_object(user)

    return store


class TestPhoneUsesButtonTemplate:
    def test_cross_ref_built(self):
        store = _setup_store_with_templates()
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("phone:SEP001122334455", "phone_uses_button_template")
        assert refs == ["button_template:Standard 8845"]

    def test_no_ref_when_no_template(self):
        store = MigrationStore(":memory:")
        phone = MigrationObject(
            canonical_id="phone:SEPNOTEMPLATE",
            provenance=_prov("SEPNOTEMPLATE"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"cucm_phone_template": None, "cucm_device_pool": None, "cucm_owner_user": None},
        )
        store.upsert_object(phone)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("phone:SEPNOTEMPLATE", "phone_uses_button_template")
        assert refs == []


class TestPhoneUsesSoftkeyTemplate:
    def test_cross_ref_built(self):
        store = _setup_store_with_templates()
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("phone:SEP001122334455", "phone_uses_softkey_template")
        assert refs == ["softkey_template:Standard User"]

    def test_no_ref_when_no_template(self):
        store = MigrationStore(":memory:")
        phone = MigrationObject(
            canonical_id="phone:SEPNOSK",
            provenance=_prov("SEPNOSK"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"cucm_softkey_template": None, "cucm_device_pool": None, "cucm_owner_user": None},
        )
        store.upsert_object(phone)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("phone:SEPNOSK", "phone_uses_softkey_template")
        assert refs == []
