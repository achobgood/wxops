"""CSV activation codes export tests."""
import csv
import io
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalUser,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.export.csv_export import (
    generate_csv_activation_codes,
    has_activation_codes,
)


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _seed_convertible_device(store, *, code=None):
    user = CanonicalUser(
        canonical_id="user:alice",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        emails=["alice@acme.com"],
        display_name="Alice Smith",
    )
    device = CanonicalDevice(
        canonical_id="device:SEP001122AABBCC",
        provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        mac="001122AABBCC",
        model="DMS Cisco 8851",
        compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
        display_name="SEP001122AABBCC",
        owner_canonical_id="user:alice",
        location_canonical_id="location:hq",
    )
    store.upsert_object(user)
    store.upsert_object(device)

    store.conn.execute(
        """INSERT INTO plan_operations
           (node_id, canonical_id, op_type, resource_type, tier, batch,
            api_calls, description, status, webex_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "device:SEP001122AABBCC:create_activation_code",
            "device:SEP001122AABBCC",
            "create_activation_code",
            "device",
            3,
            "location:hq",
            1,
            "Generate activation code for SEP001122AABBCC",
            "completed" if code else "pending",
            code,
        ),
    )
    store.conn.commit()


def test_empty_store_has_no_activation_codes(store):
    assert has_activation_codes(store) is False
    csv_content = generate_csv_activation_codes(store)
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0] == [
        "device_name", "owner_name", "owner_email",
        "model", "activation_code", "status", "location",
    ]


def test_pending_activation_code_exported(store):
    _seed_convertible_device(store, code=None)
    assert has_activation_codes(store) is True

    csv_content = generate_csv_activation_codes(store)
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    row = rows[0]
    assert row["device_name"] == "SEP001122AABBCC"
    assert row["owner_name"] == "Alice Smith"
    assert row["owner_email"] == "alice@acme.com"
    assert row["model"] == "DMS Cisco 8851"
    assert row["activation_code"] == ""
    assert row["status"] == "pending"
    assert row["location"] == "location:hq"


def test_completed_activation_code_exported(store):
    _seed_convertible_device(store, code="5414011256173816")

    csv_content = generate_csv_activation_codes(store)
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    row = rows[0]
    assert row["activation_code"] == "5414011256173816"
    assert row["status"] == "completed"
