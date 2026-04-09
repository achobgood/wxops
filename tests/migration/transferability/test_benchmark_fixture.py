"""Validate the Layer 3 benchmark fixture store has the expected shape.

Run after tools/build_benchmark_fixture.py to confirm the fixture is
ready for use by layer3_benchmark.py.
"""
from __future__ import annotations
from pathlib import Path
import pytest

FIXTURE_DB = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "benchmark-migration" / "migration.db"

EXPECTED_TYPES = {
    "DEVICE_INCOMPATIBLE": 1,
    "FEATURE_APPROXIMATION": 2,
    "CSS_ROUTING_MISMATCH": 2,
    "MISSING_DATA": 2,
    "VOICEMAIL_INCOMPATIBLE": 1,
    "WORKSPACE_LICENSE_TIER": 1,
    "SHARED_LINE_COMPLEX": 1,
    "HOTDESK_DN_CONFLICT": 1,
    "DEVICE_FIRMWARE_CONVERTIBLE": 1,
    "CALLING_PERMISSION_MISMATCH": 1,
    "LOCATION_AMBIGUOUS": 1,
    "EXTENSION_CONFLICT": 1,
    "DUPLICATE_USER": 1,
    "AUDIO_ASSET_MANUAL": 1,
    "BUTTON_UNMAPPABLE": 1,
}

assert sum(EXPECTED_TYPES.values()) == 18, \
    "EXPECTED_TYPES drifted from 18-decision fixture"

RECOMMENDED_IDS = {"D0001", "D0002", "D0003", "D0004", "D0005", "D0007"}


@pytest.fixture
def store():
    if not FIXTURE_DB.exists():
        pytest.skip("Fixture DB not built — run tools/build_benchmark_fixture.py first")
    from wxcli.migration.store import MigrationStore
    s = MigrationStore(FIXTURE_DB)
    yield s
    s.close()


def test_fixture_total_decision_count(store):
    decisions = store.get_all_decisions()
    # 20 logical fixture decisions = 18 in the store + D0008/D0009 mocked
    # via tool_responses/ (whoami token expiry, preflight license fail).
    assert len(decisions) == 18, (
        f"Expected 18 fixture decisions in store (D0008/D0009 are mocked "
        f"via tool_responses), got {len(decisions)}. "
        "Re-run tools/build_benchmark_fixture.py."
    )


def test_fixture_decision_type_distribution(store):
    from collections import Counter
    counts = Counter(d["type"] for d in store.get_all_decisions())
    for dtype, expected_count in EXPECTED_TYPES.items():
        assert counts[dtype] == expected_count, (
            f"Expected {expected_count} {dtype} decisions, got {counts[dtype]}"
        )


def test_fixture_recommended_decisions(store):
    decisions = store.get_all_decisions()
    with_rec = {d["decision_id"] for d in decisions if d.get("recommendation")}
    assert with_rec == RECOMMENDED_IDS, (
        f"Recommended decision IDs mismatch.\n"
        f"  Expected: {sorted(RECOMMENDED_IDS)}\n"
        f"  Got:      {sorted(with_rec)}"
    )


def test_fixture_null_address_gotcha_present(store):
    decisions = store.get_all_decisions()
    null_addr = [
        d for d in decisions
        if d["type"] == "MISSING_DATA" and d.get("context", {}).get("field") == "location_address"
    ]
    assert null_addr, "Fixture is missing the null-address gotcha decision (D0007)"
