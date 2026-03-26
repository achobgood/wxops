"""Shared fixtures for migration report tests."""

import gzip
import json
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalAutoAttendant,
    CanonicalCallPark,
    CanonicalCallingPermission,
    CanonicalCallQueue,
    CanonicalDevice,
    CanonicalDialPlan,
    CanonicalHuntGroup,
    CanonicalLine,
    CanonicalLocation,
    CanonicalPickupGroup,
    CanonicalRouteGroup,
    CanonicalTrunk,
    CanonicalUser,
    CanonicalVoicemailProfile,
    DecisionType,
    DeviceCompatibilityTier,
    LineClassification,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov(source_id: str, source_name: str) -> Provenance:
    """Shorthand provenance for fixtures."""
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=source_name,
        extracted_at=datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def populated_store(tmp_path):
    """Build a realistic MigrationStore simulating post-analyze state.

    Contains:
    - 3 locations (Dallas HQ, Austin Branch, London Office)
    - 50 users across locations (25/15/10)
    - 45 devices (40 native MPP CP-8845, 3 convertible CP-7841, 2 incompatible CP-7962G)
    - 3 lines (2 EXTENSION, 1 E164) with partition cross-refs
    - 1 voicemail profile
    - 6 features (2 hunt groups, 1 AA, 1 call queue, 1 call park, 1 pickup group)
    - Routing (2 trunks, 1 route group, 1 dial plan)
    - 3 CSSes with 5 partitions, cross-refs wired
    - Cross-refs: user_has_device (3), device_has_dn (3), dn_in_partition (3)
    - 6 decisions (including VOICEMAIL_INCOMPATIBLE)
    """
    store = MigrationStore(tmp_path / "migration.db")

    # -- Locations --
    locations = [
        ("loc:dallas-hq", "Dallas HQ"),
        ("loc:austin-branch", "Austin Branch"),
        ("loc:london-office", "London Office"),
    ]
    for cid, name in locations:
        store.upsert_object(CanonicalLocation(
            canonical_id=cid,
            provenance=_prov(cid, name),
            status=MigrationStatus.ANALYZED,
            name=name,
        ))

    # -- Users (25 Dallas, 15 Austin, 10 London) --
    user_distribution = [
        ("loc:dallas-hq", 25),
        ("loc:austin-branch", 15),
        ("loc:london-office", 10),
    ]
    user_idx = 0
    for loc_id, count in user_distribution:
        for i in range(count):
            user_idx += 1
            uid = f"user:user-{user_idx:03d}"
            store.upsert_object(CanonicalUser(
                canonical_id=uid,
                provenance=_prov(uid, f"user{user_idx}"),
                status=MigrationStatus.ANALYZED,
                first_name=f"User",
                last_name=f"{user_idx:03d}",
                emails=[f"user{user_idx}@example.com"],
                location_id=loc_id,
                extension=f"{1000 + user_idx}",
            ))

    # -- Devices (40 native MPP, 3 convertible, 2 incompatible) --
    device_specs = (
        [("CP-8845", DeviceCompatibilityTier.NATIVE_MPP)] * 40
        + [("CP-7841", DeviceCompatibilityTier.CONVERTIBLE)] * 3
        + [("CP-7962G", DeviceCompatibilityTier.INCOMPATIBLE)] * 2
    )
    for idx, (model, tier) in enumerate(device_specs, 1):
        did = f"device:dev-{idx:03d}"
        store.upsert_object(CanonicalDevice(
            canonical_id=did,
            provenance=_prov(did, f"SEP00000000{idx:04d}"),
            status=MigrationStatus.ANALYZED,
            model=model,
            compatibility_tier=tier,
            mac=f"00000000{idx:04d}",
            owner_canonical_id=f"user:user-{min(idx, 50):03d}",
        ))

    # -- Features --
    features = [
        CanonicalHuntGroup(
            canonical_id="hunt_group:hg-1",
            provenance=_prov("hg-1", "Sales HG"),
            status=MigrationStatus.ANALYZED,
            name="Sales HG",
            extension="2001",
            location_id="loc:dallas-hq",
        ),
        CanonicalHuntGroup(
            canonical_id="hunt_group:hg-2",
            provenance=_prov("hg-2", "Support HG"),
            status=MigrationStatus.ANALYZED,
            name="Support HG",
            extension="2002",
            location_id="loc:austin-branch",
        ),
        CanonicalAutoAttendant(
            canonical_id="auto_attendant:aa-1",
            provenance=_prov("aa-1", "Main AA"),
            status=MigrationStatus.ANALYZED,
            name="Main AA",
            extension="3001",
            location_id="loc:dallas-hq",
        ),
        CanonicalCallQueue(
            canonical_id="call_queue:cq-1",
            provenance=_prov("cq-1", "Billing CQ"),
            status=MigrationStatus.ANALYZED,
            name="Billing CQ",
            extension="4001",
            location_id="loc:dallas-hq",
        ),
        CanonicalCallPark(
            canonical_id="call_park:cp-1",
            provenance=_prov("cp-1", "Lobby Park"),
            status=MigrationStatus.ANALYZED,
            name="Lobby Park",
            extension="5001",
            location_id="loc:dallas-hq",
        ),
        CanonicalPickupGroup(
            canonical_id="pickup_group:pg-1",
            provenance=_prov("pg-1", "Floor 2 Pickup"),
            status=MigrationStatus.ANALYZED,
            name="Floor 2 Pickup",
            location_id="loc:dallas-hq",
        ),
    ]
    for feat in features:
        store.upsert_object(feat)

    # -- Routing --
    trunk1 = CanonicalTrunk(
        canonical_id="trunk:trunk-1",
        provenance=_prov("trunk-1", "PSTN-GW-1"),
        status=MigrationStatus.ANALYZED,
        name="PSTN-GW-1",
        trunk_type="REGISTERING",
        location_id="loc:dallas-hq",
    )
    trunk2 = CanonicalTrunk(
        canonical_id="trunk:trunk-2",
        provenance=_prov("trunk-2", "PSTN-GW-2"),
        status=MigrationStatus.ANALYZED,
        name="PSTN-GW-2",
        trunk_type="REGISTERING",
        location_id="loc:austin-branch",
    )
    rg = CanonicalRouteGroup(
        canonical_id="route_group:rg-1",
        provenance=_prov("rg-1", "Main RG"),
        status=MigrationStatus.ANALYZED,
        name="Main RG",
    )
    dp = CanonicalDialPlan(
        canonical_id="dial_plan:dp-1",
        provenance=_prov("dp-1", "US Dial Plan"),
        status=MigrationStatus.ANALYZED,
        name="US Dial Plan",
        dial_patterns=["+1!", "9.!"],
    )
    for obj in [trunk1, trunk2, rg, dp]:
        store.upsert_object(obj)

    # -- Gateways (as intermediate MigrationObject) --
    gateways = [
        MigrationObject(
            canonical_id="gateway:VG310-HQ",
            provenance=_prov("gw-1", "VG310-HQ"),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={
                "gateway_name": "VG310-HQ",
                "description": "HQ analog gateway",
                "product": "Cisco VG310",
                "protocol": "MGCP",
                "cucm_device_pool": "DP-HQ-Phones",
            },
        ),
        MigrationObject(
            canonical_id="gateway:ATA191-Lobby",
            provenance=_prov("gw-2", "ATA191-Lobby"),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={
                "gateway_name": "ATA191-Lobby",
                "description": "Lobby fax ATA",
                "product": "Cisco ATA 191",
                "protocol": "SIP",
                "cucm_device_pool": "DP-HQ-Phones",
            },
        ),
        MigrationObject(
            canonical_id="gateway:ISR4321-Branch",
            provenance=_prov("gw-3", "ISR4321-Branch"),
            status=MigrationStatus.ANALYZED,
            pre_migration_state={
                "gateway_name": "ISR4321-Branch",
                "description": "Branch router with analog NIM",
                "product": "Cisco ISR 4321",
                "protocol": "MGCP",
                "cucm_device_pool": "DP-Austin-Branch",
            },
        ),
    ]
    for gw in gateways:
        store.upsert_object(gw)

    # -- CSSes (as intermediate MigrationObject) and Partitions --
    css_names = ["CSS-Internal", "CSS-National", "CSS-International"]
    partition_names = ["PT-Internal", "PT-Local", "PT-National", "PT-International", "PT-Emergency"]

    for pt_name in partition_names:
        pt_id = f"partition:{pt_name}"
        store.upsert_object(MigrationObject(
            canonical_id=pt_id,
            provenance=_prov(pt_id, pt_name),
            status=MigrationStatus.ANALYZED,
        ))

    for css_name in css_names:
        css_id = f"css:{css_name}"
        store.upsert_object(MigrationObject(
            canonical_id=css_id,
            provenance=_prov(css_id, css_name),
            status=MigrationStatus.ANALYZED,
        ))

    # Wire cross-refs: css_contains_partition
    css_partition_map = {
        "css:CSS-Internal": ["partition:PT-Internal", "partition:PT-Emergency"],
        "css:CSS-National": ["partition:PT-Internal", "partition:PT-Local", "partition:PT-National"],
        "css:CSS-International": ["partition:PT-Internal", "partition:PT-Local", "partition:PT-National", "partition:PT-International"],
    }
    for css_id, pt_ids in css_partition_map.items():
        for ordinal, pt_id in enumerate(pt_ids):
            store.add_cross_ref(css_id, pt_id, "css_contains_partition", ordinal=ordinal)

    # -- Lines (DN objects) --
    line_specs = [
        ("line:dn-1001", "1001", "PT-Internal", LineClassification.EXTENSION, "1001"),
        ("line:dn-1002", "1002", "PT-Internal", LineClassification.EXTENSION, "1002"),
        ("line:dn-e164-1", "+14155551234", "PT-National", LineClassification.E164, "+14155551234"),
    ]
    for lid, ext, pt_name, classification, pattern in line_specs:
        store.upsert_object(CanonicalLine(
            canonical_id=lid,
            provenance=_prov(lid, pattern),
            status=MigrationStatus.ANALYZED,
            extension=ext,
            classification=classification,
            cucm_pattern=pattern,
            route_partition_name=pt_name,
        ))

    # -- Voicemail Profile --
    store.upsert_object(CanonicalVoicemailProfile(
        canonical_id="voicemail_profile:vm-default",
        provenance=_prov("vm-default", "Default VM Profile"),
        status=MigrationStatus.ANALYZED,
        cucm_voicemail_profile_name="Default VM Profile",
    ))

    # -- Cross-refs: user_has_device (wire 3 users to devices) --
    store.add_cross_ref("user:user-001", "device:dev-001", "user_has_device")
    store.add_cross_ref("user:user-002", "device:dev-002", "user_has_device")
    store.add_cross_ref("user:user-003", "device:dev-003", "user_has_device")

    # -- Cross-refs: device_has_dn (wire devices to lines) --
    store.add_cross_ref("device:dev-001", "line:dn-1001", "device_has_dn")
    store.add_cross_ref("device:dev-002", "line:dn-1002", "device_has_dn")
    store.add_cross_ref("device:dev-003", "line:dn-e164-1", "device_has_dn")

    # -- Cross-refs: dn_in_partition (wire lines to partitions) --
    store.add_cross_ref("line:dn-1001", "partition:PT-Internal", "dn_in_partition")
    store.add_cross_ref("line:dn-1002", "partition:PT-Internal", "dn_in_partition")
    store.add_cross_ref("line:dn-e164-1", "partition:PT-National", "dn_in_partition")

    # -- Decisions --
    run_id = "20260324T120000-fixture"
    decisions = [
        {
            "decision_id": store.next_decision_id(),
            "type": DecisionType.FEATURE_APPROXIMATION.value,
            "severity": "MEDIUM",
            "summary": "Hunt group 'Sales HG' uses Top Down which maps to REGULAR",
            "context": {"object_id": "hunt_group:hg-1", "cucm_algorithm": "Top Down"},
            "options": [{"id": "accept", "label": "Accept approximation", "impact": "Minor behavior difference"}],
            "fingerprint": "fa-hg-1",
            "run_id": run_id,
        },
        {
            "decision_id": store.next_decision_id(),
            "type": DecisionType.FEATURE_APPROXIMATION.value,
            "severity": "LOW",
            "summary": "Auto attendant 'Main AA' script logic simplified",
            "context": {"object_id": "auto_attendant:aa-1"},
            "options": [{"id": "accept", "label": "Accept", "impact": "Script simplified"}],
            "fingerprint": "fa-aa-1",
            "run_id": run_id,
        },
        {
            "decision_id": store.next_decision_id(),
            "type": DecisionType.CSS_ROUTING_MISMATCH.value,
            "severity": "MEDIUM",
            "summary": "CSS-International has 4 partitions — complex routing scope",
            "context": {"css_id": "css:CSS-International", "partition_count": 4},
            "options": [
                {"id": "map_dial_plan", "label": "Map to dial plan", "impact": "1 dial plan"},
                {"id": "skip", "label": "Skip", "impact": "Manual config"},
            ],
            "fingerprint": "css-intl-1",
            "run_id": run_id,
        },
        {
            "decision_id": store.next_decision_id(),
            "type": DecisionType.DEVICE_INCOMPATIBLE.value,
            "severity": "HIGH",
            "summary": "2 CP-7962G devices are incompatible",
            "context": {"model": "CP-7962G", "count": 2},
            "options": [
                {"id": "replace", "label": "Replace hardware", "impact": "2 new phones"},
                {"id": "skip", "label": "Skip devices", "impact": "2 users without phones"},
            ],
            "chosen_option": "replace",
            "resolved_at": "2026-03-24T12:00:00+00:00",
            "resolved_by": "auto_rule",
            "fingerprint": "dev-incompat-7962",
            "run_id": run_id,
        },
        {
            "decision_id": store.next_decision_id(),
            "type": DecisionType.SHARED_LINE_COMPLEX.value,
            "severity": "HIGH",
            "summary": "Shared line on DN 1001 spans 3 devices",
            "context": {"dn": "1001", "device_count": 3},
            "options": [
                {"id": "virtual_line", "label": "Use virtual line", "impact": "1 virtual line"},
                {"id": "skip", "label": "Skip", "impact": "Manual config"},
            ],
            "fingerprint": "sl-1001",
            "run_id": run_id,
        },
        {
            "decision_id": store.next_decision_id(),
            "type": DecisionType.VOICEMAIL_INCOMPATIBLE.value,
            "severity": "MEDIUM",
            "summary": "Voicemail profile 'Default VM Profile' uses unsupported MWI setting",
            "context": {"profile_name": "Default VM Profile"},
            "options": [
                {"id": "accept", "label": "Accept default mapping", "impact": "MWI may differ"},
            ],
            "fingerprint": "vm-incompat-1",
            "run_id": run_id,
        },
    ]
    for d in decisions:
        store.save_decision(d)

    return store


@pytest.fixture()
def sample_collector_file(tmp_path):
    """Write a minimal gzipped JSON collector file to tmp_path and return path."""
    collector_data = {
        "collector_version": "1.0",
        "cucm_version": "14.0.1.13900-155",
        "cluster_name": "CUCM-LAB",
        "collected_at": "2026-03-24T12:00:00Z",
        "objects": {
            "phone": [
                {"name": "SEP001122334455", "model": "Cisco 8845", "protocol": "SIP"},
                {"name": "SEP001122334466", "model": "Cisco 7841", "protocol": "SIP"},
            ],
            "endUser": [
                {"userid": "jsmith", "firstName": "John", "lastName": "Smith"},
            ],
            "devicePool": [
                {"name": "DP-HQ", "dateTimeSettingName": "CMLocal"},
            ],
            "routePartition": [
                {"name": "PT-Internal"},
            ],
            "css": [
                {"name": "CSS-Internal", "members": [{"routePartitionName": "PT-Internal"}]},
            ],
            "huntPilot": [
                {"name": "Sales HP", "pattern": "2001"},
            ],
            "huntList": [],
            "lineGroup": [],
            "ctiRoutePoint": [],
            "callPark": [
                {"pattern": "5001"},
            ],
            "callPickupGroup": [
                {"name": "Floor1-PG"},
            ],
            "routePattern": [],
            "gateway": [],
            "sipTrunk": [
                {"name": "PSTN-GW-1"},
            ],
            "routeGroup": [],
            "routeList": [],
            "transPattern": [],
            "timeSchedule": [],
            "timePeriod": [],
            "voicemailProfile": [],
            "voicemailPilot": [],
        },
    }
    file_path = tmp_path / "collector-output.json.gz"
    with gzip.open(file_path, "wt", encoding="utf-8") as f:
        json.dump(collector_data, f)
    return file_path
