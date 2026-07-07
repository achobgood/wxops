"""Tests for all 12 migration analyzers (Wave 1 + Wave 2).

Wave 1:
  1. ExtensionConflictAnalyzer
  2. DNAmbiguityAnalyzer
  3. DeviceCompatibilityAnalyzer
  4. LocationAmbiguityAnalyzer
  5. MissingDataAnalyzer
  6. WorkspaceLicenseAnalyzer

Wave 2:
  7.  SharedLineAnalyzer
  8.  CSSRoutingAnalyzer
  9.  CSSPermissionAnalyzer
  10. DuplicateUserAnalyzer
  11. VoicemailCompatibilityAnalyzer
  12. FeatureApproximationAnalyzer

Each test class uses a fresh SQLite store per test method.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from wxcli.migration.models import (
    CanonicalAutoAttendant,
    CanonicalCallQueue,
    CanonicalCallingPermission,
    CallingPermissionEntry,
    CanonicalDevice,
    CanonicalDialPlan,
    CanonicalHuntGroup,
    CanonicalLine,
    CanonicalLocation,
    CanonicalTrunk,
    CanonicalUser,
    CanonicalVoicemailProfile,
    CanonicalWorkspace,
    DecisionType,
    DeviceCompatibilityTier,
    LineClassification,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore, _now
# Wave 1 analyzers
from wxcli.migration.transform.analyzers.device_compatibility import DeviceCompatibilityAnalyzer
from wxcli.migration.transform.analyzers.dn_ambiguity import DNAmbiguityAnalyzer
from wxcli.migration.transform.analyzers.extension_conflict import ExtensionConflictAnalyzer
from wxcli.migration.transform.analyzers.location_ambiguity import LocationAmbiguityAnalyzer
from wxcli.migration.transform.analyzers.missing_data import MissingDataAnalyzer
from wxcli.migration.transform.analyzers.workspace_license import WorkspaceLicenseAnalyzer
# Wave 2 analyzers
from wxcli.migration.transform.analyzers.shared_line import SharedLineAnalyzer
from wxcli.migration.transform.analyzers.css_routing import CSSRoutingAnalyzer
from wxcli.migration.transform.analyzers.css_permission import CSSPermissionAnalyzer
from wxcli.migration.transform.analyzers.duplicate_user import DuplicateUserAnalyzer
from wxcli.migration.transform.analyzers.voicemail_compatibility import VoicemailCompatibilityAnalyzer
from wxcli.migration.transform.analyzers.feature_approximation import FeatureApproximationAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store() -> tuple[MigrationStore, str]:
    """Create a MigrationStore backed by a temporary SQLite file.

    Returns (store, path) so the caller can clean up the file.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return MigrationStore(tmp.name), tmp.name


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=name,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _save_decision_dict(store: MigrationStore, decision_type: DecisionType,
                         affected_objects: list[str],
                         fingerprint: str = "mapper_fp_001") -> None:
    """Insert a pre-existing mapper decision into the store so analyzers can
    detect it via _get_existing_decisions_for_type."""
    store.save_decision({
        "decision_id": store.next_decision_id(),
        "type": decision_type.value,
        "severity": "MEDIUM",
        "summary": "Pre-existing mapper decision",
        "context": {"_affected_objects": affected_objects},
        "options": [],
        "fingerprint": fingerprint,
        "run_id": store.current_run_id,
    })


# ===================================================================
# 1. ExtensionConflictAnalyzer
# ===================================================================

class TestExtensionConflictAnalyzer:

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = ExtensionConflictAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_two_lines_same_ext_same_location_produces_conflict(self) -> None:
        """Two lines sharing an extension in the same location should produce
        exactly one EXTENSION_CONFLICT decision with severity MEDIUM."""
        loc = CanonicalLocation(canonical_id="loc:hq", provenance=_prov("hq"), name="HQ")
        self.store.upsert_object(loc)

        line1 = CanonicalLine(
            canonical_id="line:1001a", provenance=_prov("1001a"),
            extension="1001", cucm_pattern="1001", route_partition_name="PT-Internal",
        )
        line2 = CanonicalLine(
            canonical_id="line:1001b", provenance=_prov("1001b"),
            extension="1001", cucm_pattern="1001", route_partition_name="PT-External",
        )
        self.store.upsert_object(line1)
        self.store.upsert_object(line2)

        dev1 = CanonicalDevice(
            canonical_id="dev:phone1", provenance=_prov("phone1"),
            model="CP-8845", location_canonical_id="loc:hq",
        )
        dev2 = CanonicalDevice(
            canonical_id="dev:phone2", provenance=_prov("phone2"),
            model="CP-8845", location_canonical_id="loc:hq",
        )
        self.store.upsert_object(dev1)
        self.store.upsert_object(dev2)

        # device_has_dn cross-refs: device → line
        self.store.add_cross_ref("dev:phone1", "line:1001a", "device_has_dn")
        self.store.add_cross_ref("dev:phone2", "line:1001b", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.EXTENSION_CONFLICT
        assert d.severity == "MEDIUM"
        assert len(d.affected_objects) == 2
        assert d.fingerprint  # non-empty

    def test_same_ext_different_locations_no_conflict(self) -> None:
        """Two lines sharing an extension in DIFFERENT locations should produce
        zero decisions — extensions only need to be unique per location."""
        loc_hq = CanonicalLocation(canonical_id="loc:hq", provenance=_prov("hq"), name="HQ")
        loc_br = CanonicalLocation(canonical_id="loc:branch", provenance=_prov("branch"), name="Branch")
        self.store.upsert_object(loc_hq)
        self.store.upsert_object(loc_br)

        line1 = CanonicalLine(
            canonical_id="line:1001a", provenance=_prov("1001a"),
            extension="1001", cucm_pattern="1001",
        )
        line2 = CanonicalLine(
            canonical_id="line:1001b", provenance=_prov("1001b"),
            extension="1001", cucm_pattern="1001",
        )
        self.store.upsert_object(line1)
        self.store.upsert_object(line2)

        dev1 = CanonicalDevice(
            canonical_id="dev:phone1", provenance=_prov("phone1"),
            model="CP-8845", location_canonical_id="loc:hq",
        )
        dev2 = CanonicalDevice(
            canonical_id="dev:phone2", provenance=_prov("phone2"),
            model="CP-8845", location_canonical_id="loc:branch",
        )
        self.store.upsert_object(dev1)
        self.store.upsert_object(dev2)

        self.store.add_cross_ref("dev:phone1", "line:1001a", "device_has_dn")
        self.store.add_cross_ref("dev:phone2", "line:1001b", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_three_lines_same_ext_same_location_high_severity(self) -> None:
        """Three-way extension conflict should produce severity HIGH."""
        loc = CanonicalLocation(canonical_id="loc:hq", provenance=_prov("hq"), name="HQ")
        self.store.upsert_object(loc)

        for i in range(3):
            line = CanonicalLine(
                canonical_id=f"line:1001_{i}", provenance=_prov(f"1001_{i}"),
                extension="1001", cucm_pattern="1001",
                route_partition_name=f"PT-{i}",
            )
            self.store.upsert_object(line)

            dev = CanonicalDevice(
                canonical_id=f"dev:phone_{i}", provenance=_prov(f"phone_{i}"),
                model="CP-8845", location_canonical_id="loc:hq",
            )
            self.store.upsert_object(dev)

            self.store.add_cross_ref(f"dev:phone_{i}", f"line:1001_{i}", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.severity == "HIGH"
        assert len(d.affected_objects) == 3

    def test_no_lines_returns_empty(self) -> None:
        """Empty store should produce no decisions."""
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 2. DNAmbiguityAnalyzer
# ===================================================================

class TestDNAmbiguityAnalyzer:

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = DNAmbiguityAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_ambiguous_short_dn_produces_low_severity(self) -> None:
        """An AMBIGUOUS line with cucm_pattern <= 4 digits should be LOW severity."""
        line = CanonicalLine(
            canonical_id="line:short", provenance=_prov("short"),
            classification=LineClassification.AMBIGUOUS,
            cucm_pattern="1234",
        )
        self.store.upsert_object(line)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.DN_AMBIGUOUS
        assert d.severity == "LOW"
        assert d.affected_objects == ["line:short"]
        assert d.fingerprint

    def test_ambiguous_long_dn_produces_medium_severity(self) -> None:
        """An AMBIGUOUS line with cucm_pattern > 4 digits should be MEDIUM severity."""
        line = CanonicalLine(
            canonical_id="line:long", provenance=_prov("long"),
            classification=LineClassification.AMBIGUOUS,
            cucm_pattern="5551234",
        )
        self.store.upsert_object(line)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.DN_AMBIGUOUS
        assert d.severity == "MEDIUM"

    def test_extension_classified_line_no_decision(self) -> None:
        """A line classified as EXTENSION should produce no DN_AMBIGUOUS decision."""
        line = CanonicalLine(
            canonical_id="line:ext", provenance=_prov("ext"),
            classification=LineClassification.EXTENSION,
            cucm_pattern="2001", extension="2001",
        )
        self.store.upsert_object(line)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_pre_existing_mapper_decision_skips_line(self) -> None:
        """If a mapper already produced a DN_AMBIGUOUS decision for a line, the
        analyzer should skip it (no duplicate)."""
        line = CanonicalLine(
            canonical_id="line:already", provenance=_prov("already"),
            classification=LineClassification.AMBIGUOUS,
            cucm_pattern="9999",
        )
        self.store.upsert_object(line)

        # Pre-insert a mapper decision for this line
        _save_decision_dict(
            self.store,
            DecisionType.DN_AMBIGUOUS,
            affected_objects=["line:already"],
            fingerprint="mapper_dn_amb_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_no_lines_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 3. DeviceCompatibilityAnalyzer
# ===================================================================

class TestDeviceCompatibilityAnalyzer:

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = DeviceCompatibilityAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_incompatible_device_produces_decision(self) -> None:
        dev = CanonicalDevice(
            canonical_id="dev:old", provenance=_prov("old"),
            model="CP-7911", mac="AABB00112233",
            compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
            cucm_device_name="SEP_OLD",
        )
        self.store.upsert_object(dev)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.DEVICE_INCOMPATIBLE
        assert d.severity == "MEDIUM"
        assert "dev:old" in d.affected_objects
        assert d.fingerprint

    def test_convertible_device_produces_no_decision(self) -> None:
        """Convertibility is a model classification, not a decision — no decision is emitted."""
        dev = CanonicalDevice(
            canonical_id="dev:conv", provenance=_prov("conv"),
            model="CP-8841", mac="CCDD00112233",
            compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
            cucm_device_name="SEP_CONV",
        )
        self.store.upsert_object(dev)

        decisions = self.analyzer.analyze(self.store)

        assert decisions == []

    def test_native_mpp_no_decision(self) -> None:
        dev = CanonicalDevice(
            canonical_id="dev:mpp", provenance=_prov("mpp"),
            model="CP-8845", mac="EEFF00112233",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            cucm_device_name="SEP_MPP",
        )
        self.store.upsert_object(dev)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_both_incompatible_and_convertible(self) -> None:
        """Convertible devices produce no decision; only the incompatible device does."""
        dev_incompat = CanonicalDevice(
            canonical_id="dev:old", provenance=_prov("old"),
            model="CP-7911",
            compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
            cucm_device_name="SEP_OLD",
        )
        dev_convert = CanonicalDevice(
            canonical_id="dev:conv", provenance=_prov("conv"),
            model="CP-8841",
            compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
            cucm_device_name="SEP_CONV",
        )
        self.store.upsert_object(dev_incompat)
        self.store.upsert_object(dev_convert)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert decisions[0].type == DecisionType.DEVICE_INCOMPATIBLE

    def test_pre_existing_mapper_decision_skips_device(self) -> None:
        """Analyzer should skip a device that already has a mapper-produced decision."""
        dev = CanonicalDevice(
            canonical_id="dev:old", provenance=_prov("old"),
            model="CP-7911",
            compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
            cucm_device_name="SEP_OLD",
        )
        self.store.upsert_object(dev)

        _save_decision_dict(
            self.store,
            DecisionType.DEVICE_INCOMPATIBLE,
            affected_objects=["dev:old"],
            fingerprint="mapper_dev_incompat_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_no_devices_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []

    def test_dect_device_no_decision(self) -> None:
        """DECT-tier devices should NOT generate any analyzer decisions."""
        dev = CanonicalDevice(
            canonical_id="dev:dect-6825", provenance=_prov("dect-6825"),
            model="Cisco 6825", mac="998877665544",
            compatibility_tier=DeviceCompatibilityTier.DECT,
            cucm_device_name="SEP998877665544",
        )
        self.store.upsert_object(dev)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0


# ===================================================================
# 4. LocationAmbiguityAnalyzer
# ===================================================================

class TestLocationAmbiguityAnalyzer:

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = LocationAmbiguityAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_location_with_ambiguous_warning_produces_decision(self) -> None:
        loc = CanonicalLocation(
            canonical_id="loc:hq", provenance=_prov("hq"),
            name="HQ",
            warnings=["ambiguous device pool mapping — DP-HQ and DP-HQ-ALT"],
            cucm_device_pool_names=["DP-HQ", "DP-HQ-ALT"],
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.LOCATION_AMBIGUOUS
        assert d.severity == "HIGH"
        assert d.affected_objects == ["loc:hq"]
        assert d.fingerprint

    @pytest.mark.parametrize("warning_text", [
        "conflicting CUCM location references",
        "multiple cucm locations mapped to single pool",
        "site code mismatch between device pools",
    ])
    def test_various_ambiguity_markers(self, warning_text: str) -> None:
        """Each ambiguity marker substring should trigger a decision."""
        loc = CanonicalLocation(
            canonical_id="loc:test", provenance=_prov("test"),
            name="Test Location",
            warnings=[warning_text],
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 1

    def test_location_no_warnings_no_decision(self) -> None:
        loc = CanonicalLocation(
            canonical_id="loc:clean", provenance=_prov("clean"),
            name="Clean Location",
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_location_with_unrelated_warning_no_decision(self) -> None:
        """A warning that doesn't contain any ambiguity markers should not trigger."""
        loc = CanonicalLocation(
            canonical_id="loc:other", provenance=_prov("other"),
            name="Other",
            warnings=["timezone fallback used — UTC assumed"],
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_pre_existing_mapper_decision_skips_location(self) -> None:
        loc = CanonicalLocation(
            canonical_id="loc:hq", provenance=_prov("hq"),
            name="HQ",
            warnings=["ambiguous device pool mapping"],
        )
        self.store.upsert_object(loc)

        _save_decision_dict(
            self.store,
            DecisionType.LOCATION_AMBIGUOUS,
            affected_objects=["loc:hq"],
            fingerprint="mapper_loc_amb_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_no_locations_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 5. MissingDataAnalyzer
# ===================================================================

class TestMissingDataAnalyzer:

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = MissingDataAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_user_empty_emails_high_severity(self) -> None:
        user = CanonicalUser(
            canonical_id="user:noemail", provenance=_prov("noemail"),
            emails=[],
            first_name="Alice",
            last_name="Smith",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)

        # Should flag missing emails
        email_decisions = [d for d in decisions if "emails" in d.context.get("missing_fields", [])]
        assert len(email_decisions) == 1
        assert email_decisions[0].severity == "HIGH"
        assert email_decisions[0].affected_objects == ["user:noemail"]

    def test_user_first_name_present_no_name_decision(self) -> None:
        """If first_name is present (even without last_name), no name-missing decision."""
        user = CanonicalUser(
            canonical_id="user:firstonly", provenance=_prov("firstonly"),
            emails=["alice@example.com"],
            first_name="Alice",
            last_name=None,
            location_id="location:hq",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_user_last_name_present_no_name_decision(self) -> None:
        """If last_name is present (even without first_name), no name-missing decision."""
        user = CanonicalUser(
            canonical_id="user:lastonly", provenance=_prov("lastonly"),
            emails=["bob@example.com"],
            first_name=None,
            last_name="Jones",
            location_id="location:hq",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_user_both_names_missing_produces_medium(self) -> None:
        """If BOTH first_name and last_name are missing, should produce MEDIUM decision (not HIGH from location)."""
        user = CanonicalUser(
            canonical_id="user:noname", provenance=_prov("noname"),
            emails=["noname@example.com"],
            first_name=None,
            last_name=None,
            location_id="location:hq",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)

        name_decisions = [
            d for d in decisions
            if "first_name/last_name" in d.context.get("missing_fields", [])
        ]
        assert len(name_decisions) == 1
        assert name_decisions[0].severity == "MEDIUM"

    def test_device_no_mac_produces_medium(self) -> None:
        dev = CanonicalDevice(
            canonical_id="dev:nomac", provenance=_prov("nomac"),
            model="CP-8845", mac=None,
            owner_canonical_id="user:someone",
        )
        self.store.upsert_object(dev)

        decisions = self.analyzer.analyze(self.store)

        mac_decisions = [d for d in decisions if "mac" in d.context.get("missing_fields", [])]
        assert len(mac_decisions) == 1
        assert mac_decisions[0].severity == "MEDIUM"

    def test_line_extension_classified_no_extension_produces_medium(self) -> None:
        """An EXTENSION-classified line with no extension should be flagged."""
        line = CanonicalLine(
            canonical_id="line:noext", provenance=_prov("noext"),
            classification=LineClassification.EXTENSION,
            cucm_pattern="1001",
            extension=None,
        )
        self.store.upsert_object(line)

        decisions = self.analyzer.analyze(self.store)

        ext_decisions = [
            d for d in decisions
            if d.context.get("object_type") == "line"
            and "extension" in d.context.get("missing_fields", [])
        ]
        assert len(ext_decisions) == 1
        assert ext_decisions[0].severity == "MEDIUM"

    def test_line_national_classified_no_extension_no_decision(self) -> None:
        """A NATIONAL-classified line should NOT be flagged for missing extension."""
        line = CanonicalLine(
            canonical_id="line:nat", provenance=_prov("nat"),
            classification=LineClassification.NATIONAL,
            cucm_pattern="+15551234567",
            extension=None,
        )
        self.store.upsert_object(line)

        decisions = self.analyzer.analyze(self.store)

        line_decisions = [d for d in decisions if d.context.get("object_type") == "line"]
        assert len(line_decisions) == 0

    def test_trunk_missing_address_produces_medium(self) -> None:
        trunk = CanonicalTrunk(
            canonical_id="trunk:noaddr", provenance=_prov("noaddr"),
            name="SBC-Primary", address=None, password="secret",
        )
        self.store.upsert_object(trunk)

        decisions = self.analyzer.analyze(self.store)

        addr_decisions = [d for d in decisions if "address" in d.context.get("missing_fields", [])]
        assert len(addr_decisions) == 1
        assert addr_decisions[0].severity == "MEDIUM"

    def test_complete_user_no_decision(self) -> None:
        """A fully populated user should produce no MISSING_DATA decisions."""
        user = CanonicalUser(
            canonical_id="user:complete", provenance=_prov("complete"),
            emails=["complete@example.com"],
            first_name="Complete",
            last_name="User",
            location_id="location:hq",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)
        user_decisions = [d for d in decisions if d.context.get("object_type") == "user"]
        assert len(user_decisions) == 0

    def test_pre_existing_mapper_decision_skips_object(self) -> None:
        user = CanonicalUser(
            canonical_id="user:noemail", provenance=_prov("noemail"),
            emails=[],
            first_name="Alice",
        )
        self.store.upsert_object(user)

        _save_decision_dict(
            self.store,
            DecisionType.MISSING_DATA,
            affected_objects=["user:noemail"],
            fingerprint="mapper_missing_001",
        )

        decisions = self.analyzer.analyze(self.store)
        user_decisions = [
            d for d in decisions
            if d.context.get("canonical_id") == "user:noemail"
        ]
        assert len(user_decisions) == 0


# ===================================================================
# 6. WorkspaceLicenseAnalyzer
# ===================================================================

class TestWorkspaceLicenseAnalyzer:

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = WorkspaceLicenseAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_workspace_no_license_tier_produces_decision(self) -> None:
        """Workspace with license_tier=None should produce a decision."""
        ws = CanonicalWorkspace(
            canonical_id="ws:noLicense", provenance=_prov("noLicense"),
            display_name="Lobby Phone",
            license_tier=None,
        )
        self.store.upsert_object(ws)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.WORKSPACE_LICENSE_TIER
        assert d.severity == "MEDIUM"
        assert d.affected_objects == ["ws:noLicense"]
        assert d.fingerprint

    def test_workspace_with_hotdesking_on_produces_decision(self) -> None:
        """Workspace set to Workspace tier but with hot-desking enabled should flag mismatch."""
        ws = CanonicalWorkspace(
            canonical_id="ws:hotdesk", provenance=_prov("hotdesk"),
            display_name="Shared Desk",
            license_tier="Workspace",
            hotdesking_status="on",
        )
        self.store.upsert_object(ws)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.WORKSPACE_LICENSE_TIER
        # Context should mention the detected features
        assert "hot-desking enabled" in d.context.get("features_detected", [])

    def test_workspace_professional_workspace_no_decision(self) -> None:
        """Workspace with Professional Workspace tier and matching features should be fine."""
        ws = CanonicalWorkspace(
            canonical_id="ws:pro", provenance=_prov("pro"),
            display_name="Exec Office",
            license_tier="Professional Workspace",
            hotdesking_status="on",
            phone_number="+15551234567",
        )
        self.store.upsert_object(ws)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_workspace_tier_no_features_no_decision(self) -> None:
        """Workspace set to Workspace tier with no Professional Workspace feature indicators — consistent."""
        ws = CanonicalWorkspace(
            canonical_id="ws:basic", provenance=_prov("basic"),
            display_name="Simple Phone",
            license_tier="Workspace",
            hotdesking_status="off",
            phone_number=None,
        )
        self.store.upsert_object(ws)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_workspace_tier_with_phone_number_produces_decision(self) -> None:
        """Workspace set to Workspace tier but with a DID phone number should flag mismatch."""
        ws = CanonicalWorkspace(
            canonical_id="ws:did", provenance=_prov("did"),
            display_name="Reception",
            license_tier="Workspace",
            phone_number="+15559876543",
        )
        self.store.upsert_object(ws)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert "DID phone number assigned" in decisions[0].context.get("features_detected", [])

    def test_workspace_no_tier_with_voicemail_crossref(self) -> None:
        """Workspace with no tier but voicemail cross-ref should produce decision
        mentioning voicemail in features."""
        ws = CanonicalWorkspace(
            canonical_id="ws:vm", provenance=_prov("vm"),
            display_name="Break Room",
            license_tier=None,
        )
        self.store.upsert_object(ws)

        # Create a non-workspace object so the cross-ref FK is valid
        # (using CanonicalUser to avoid the workspace analyzer picking it up)
        vm_target = CanonicalUser(
            canonical_id="vm:breakroom", provenance=_prov("vm_target"),
            emails=["vm@example.com"], first_name="VM", last_name="Target",
        )
        self.store.upsert_object(vm_target)

        self.store.add_cross_ref("ws:vm", "vm:breakroom", "workspace_has_voicemail")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert "voicemail configured" in decisions[0].context.get("features_detected", [])

    def test_pre_existing_mapper_decision_skips_workspace(self) -> None:
        ws = CanonicalWorkspace(
            canonical_id="ws:decided", provenance=_prov("decided"),
            display_name="Already Decided",
            license_tier=None,
        )
        self.store.upsert_object(ws)

        _save_decision_dict(
            self.store,
            DecisionType.WORKSPACE_LICENSE_TIER,
            affected_objects=["ws:decided"],
            fingerprint="mapper_ws_lic_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_no_workspaces_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 7. SharedLineAnalyzer
# ===================================================================

class TestSharedLineAnalyzer:
    """Finds DNs shared across multiple device owners."""

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = SharedLineAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def _insert_line(self, line_id: str, extension: str, partition: str = "PT1") -> None:
        line = CanonicalLine(
            canonical_id=line_id,
            provenance=_prov(line_id),
            extension=extension,
            route_partition_name=partition,
        )
        self.store.upsert_object(line)

    def _insert_device(self, device_id: str, owner_id: str) -> None:
        dev = CanonicalDevice(
            canonical_id=device_id,
            provenance=_prov(device_id),
            owner_canonical_id=owner_id,
        )
        self.store.upsert_object(dev)

    def test_two_devices_two_owners_medium_severity(self) -> None:
        """1 DN, 2 devices, 2 different owners -> 1 SHARED_LINE_COMPLEX, MEDIUM."""
        self._insert_line("line:1001", "1001")
        self._insert_device("device:A", "user:alice")
        self._insert_device("device:B", "user:bob")
        self.store.add_cross_ref("device:A", "line:1001", "device_has_dn")
        self.store.add_cross_ref("device:B", "line:1001", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.SHARED_LINE_COMPLEX
        assert d.severity == "MEDIUM"
        assert d.affected_objects  # non-empty
        assert d.fingerprint  # non-empty

    def test_three_devices_three_owners_high_severity(self) -> None:
        """1 DN, 3 devices, 3 different owners -> HIGH severity."""
        self._insert_line("line:2001", "2001")
        self._insert_device("device:X", "user:x")
        self._insert_device("device:Y", "user:y")
        self._insert_device("device:Z", "user:z")
        self.store.add_cross_ref("device:X", "line:2001", "device_has_dn")
        self.store.add_cross_ref("device:Y", "line:2001", "device_has_dn")
        self.store.add_cross_ref("device:Z", "line:2001", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert decisions[0].severity == "HIGH"
        assert decisions[0].affected_objects
        assert decisions[0].fingerprint

    def test_two_devices_same_owner_no_decision(self) -> None:
        """1 DN, 2 devices, same owner -> 0 decisions (not a shared line problem)."""
        self._insert_line("line:3001", "3001")
        self._insert_device("device:P", "user:same")
        self._insert_device("device:Q", "user:same")
        self.store.add_cross_ref("device:P", "line:3001", "device_has_dn")
        self.store.add_cross_ref("device:Q", "line:3001", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_shared_line_option_present_when_two_devices(self) -> None:
        """shared_line option present when device_count=2."""
        self._insert_line("line:4001", "4001")
        self._insert_device("device:M", "user:m1")
        self._insert_device("device:N", "user:n1")
        self.store.add_cross_ref("device:M", "line:4001", "device_has_dn")
        self.store.add_cross_ref("device:N", "line:4001", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        option_ids = [o.id for o in decisions[0].options]
        assert "shared_line" in option_ids

    def test_shared_line_option_absent_when_three_devices(self) -> None:
        """shared_line option absent when device_count=3."""
        self._insert_line("line:5001", "5001")
        self._insert_device("device:R", "user:r1")
        self._insert_device("device:S", "user:s1")
        self._insert_device("device:T", "user:t1")
        self.store.add_cross_ref("device:R", "line:5001", "device_has_dn")
        self.store.add_cross_ref("device:S", "line:5001", "device_has_dn")
        self.store.add_cross_ref("device:T", "line:5001", "device_has_dn")

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        option_ids = [o.id for o in decisions[0].options]
        assert "shared_line" not in option_ids

    def test_no_cross_refs_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 8. CSSRoutingAnalyzer
# ===================================================================

class TestCSSRoutingAnalyzer:
    """Finds overlapping dial plan patterns with different routes."""

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = CSSRoutingAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def _insert_dial_plan_raw(
        self, dp_id: str, name: str, patterns: list[str], route_id: str,
    ) -> None:
        """Insert a dial_plan object matching CanonicalDialPlan shape.

        CanonicalDialPlan.dial_patterns is list[str] and route_id is a
        top-level field.  Each dial plan maps all its patterns to one route.
        """
        self.store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                dp_id, "dial_plan", "analyzed",
                json.dumps({
                    "canonical_id": dp_id,
                    "name": name,
                    "dial_patterns": patterns,
                    "route_id": route_id,
                    "provenance": {
                        "source_system": "cucm",
                        "source_id": "test",
                        "source_name": "test",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "status": "analyzed",
                }),
                _now(), _now(),
            ),
        )
        self.store.conn.commit()

    def _insert_user_raw(self, uid: str, location_id: str) -> None:
        """Insert a user object with location_id for CSS scope tests."""
        self.store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                uid, "user", "analyzed",
                json.dumps({
                    "canonical_id": uid,
                    "location_id": location_id,
                    "provenance": {
                        "source_system": "cucm",
                        "source_id": "test",
                        "source_name": "test",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "status": "analyzed",
                }),
                _now(), _now(),
            ),
        )
        self.store.conn.commit()

    def test_same_pattern_different_routes_produces_decision(self) -> None:
        """2 dial_plans with same pattern, different route_ids -> CSS_ROUTING_MISMATCH."""
        self._insert_dial_plan_raw("dial_plan:dp1", "DP1", ["9.XXXX"], "trunk:1")
        self._insert_dial_plan_raw("dial_plan:dp2", "DP2", ["9.XXXX"], "trunk:2")

        decisions = self.analyzer.analyze(self.store)

        routing_decisions = [d for d in decisions if d.type == DecisionType.CSS_ROUTING_MISMATCH]
        assert len(routing_decisions) >= 1
        d = routing_decisions[0]
        assert d.severity == "HIGH"
        assert d.affected_objects  # non-empty
        assert d.fingerprint  # non-empty
        assert "9.XXXX" in d.summary

    def test_same_pattern_same_route_no_decision(self) -> None:
        """2 dial_plans with same pattern, same route_id -> 0 pattern-level decisions."""
        self._insert_dial_plan_raw("dial_plan:dp3", "DP3", ["9.XXXX"], "trunk:1")
        self._insert_dial_plan_raw("dial_plan:dp4", "DP4", ["9.XXXX"], "trunk:1")

        decisions = self.analyzer.analyze(self.store)

        # No pattern-level conflict because routes are identical
        pattern_decisions = [
            d for d in decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("conflicting_pattern")
        ]
        assert len(pattern_decisions) == 0

    def test_no_overlapping_patterns_no_decision(self) -> None:
        """2 dial_plans with different patterns -> 0 pattern-level decisions."""
        self._insert_dial_plan_raw("dial_plan:dp5", "DP5", ["9.XXXX"], "trunk:1")
        self._insert_dial_plan_raw("dial_plan:dp6", "DP6", ["8.XXXX"], "trunk:2")

        decisions = self.analyzer.analyze(self.store)

        pattern_decisions = [
            d for d in decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("conflicting_pattern")
        ]
        assert len(pattern_decisions) == 0

    def test_no_dial_plans_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []

    def test_scope_divergence_different_css_same_location(self) -> None:
        """2 CSSes in same location with different dial plan sets -> scope decision."""
        # Create users in the same location
        self._insert_user_raw("user:u1", "location:hq")
        self._insert_user_raw("user:u2", "location:hq")

        # Create dial plans (different routes so there's a real divergence)
        self._insert_dial_plan_raw("dial_plan:dp1", "DP1", ["9.XXXX"], "trunk:1")
        self._insert_dial_plan_raw("dial_plan:dp2", "DP2", ["8.XXXX"], "trunk:2")

        # Create CSS objects (intermediate objects for cross-refs)
        for css_id in ["css:standard", "css:restricted"]:
            self.store.conn.execute(
                "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (css_id, "css", "analyzed", json.dumps({"canonical_id": css_id}), _now(), _now()),
            )
        self.store.conn.commit()

        # Cross-refs: user -> CSS
        self.store.add_cross_ref("user:u1", "css:standard", "user_has_css")
        self.store.add_cross_ref("user:u2", "css:restricted", "user_has_css")

        # Cross-refs: CSS -> dial_plan (different sets)
        self.store.add_cross_ref("css:standard", "dial_plan:dp1", "css_has_dial_plan")
        self.store.add_cross_ref("css:standard", "dial_plan:dp2", "css_has_dial_plan")
        self.store.add_cross_ref("css:restricted", "dial_plan:dp1", "css_has_dial_plan")
        # css:restricted does NOT have dp2 — divergence

        decisions = self.analyzer.analyze(self.store)

        scope_decisions = [
            d for d in decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("css_ids")
        ]
        assert len(scope_decisions) >= 1
        d = scope_decisions[0]
        assert d.severity == "HIGH"
        assert "css:standard" in d.context["css_ids"]
        assert "css:restricted" in d.context["css_ids"]
        assert d.context["location_id"] == "location:hq"

    def test_mapper_decision_skips_covered_dial_plans(self) -> None:
        """Pre-existing mapper decision for all involved dial plans -> no new decision."""
        self._insert_dial_plan_raw("dial_plan:dp1", "DP1", ["9.XXXX"], "trunk:1")
        self._insert_dial_plan_raw("dial_plan:dp2", "DP2", ["9.XXXX"], "trunk:2")

        _save_decision_dict(
            self.store,
            DecisionType.CSS_ROUTING_MISMATCH,
            affected_objects=["dial_plan:dp1", "dial_plan:dp2"],
            fingerprint="mapper_css_001",
        )

        decisions = self.analyzer.analyze(self.store)
        routing_decisions = [d for d in decisions if d.type == DecisionType.CSS_ROUTING_MISMATCH]
        assert len(routing_decisions) == 0


# ===================================================================
# 9. CSSPermissionAnalyzer
# ===================================================================

class TestCSSPermissionAnalyzer:
    """Finds incomplete or contradictory calling permissions."""

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = CSSPermissionAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def _insert_permission_raw(self, perm_id: str, name: str,
                                calling_permissions: list[dict]) -> None:
        """Insert a calling_permission object with the expected JSON shape."""
        self.store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (
                perm_id, "calling_permission", "analyzed",
                json.dumps({
                    "canonical_id": perm_id,
                    "name": name,
                    "calling_permissions": calling_permissions,
                    "provenance": {
                        "source_system": "cucm",
                        "source_id": "test",
                        "source_name": "test",
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "status": "analyzed",
                }),
                _now(), _now(),
            ),
        )
        self.store.conn.commit()

    def test_empty_calling_permissions_medium_severity(self) -> None:
        """Permission with empty calling_permissions list -> MEDIUM severity."""
        self._insert_permission_raw("calling_permission:cp1", "EmptyPerm", [])

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.CALLING_PERMISSION_MISMATCH
        assert d.severity == "MEDIUM"
        assert d.affected_objects  # non-empty
        assert d.fingerprint  # non-empty

    def test_internal_call_blocked_high_severity(self) -> None:
        """Permission blocking INTERNAL_CALL -> HIGH severity."""
        self._insert_permission_raw("calling_permission:cp2", "BlockInternal", [
            {"call_type": "INTERNAL_CALL", "action": "BLOCK", "transfer_enabled": False},
        ])

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert decisions[0].severity == "HIGH"
        assert decisions[0].affected_objects
        assert decisions[0].fingerprint

    def test_no_assigned_users_orphaned_no_decision(self) -> None:
        """Permission with entries but no user cross-refs -> 0 decisions.

        Orphaned profiles (0 users) are silently dropped by the CSS mapper
        and should not produce decisions if they somehow reach the analyzer.
        """
        self._insert_permission_raw("calling_permission:cp3", "OrphanPerm", [
            {"call_type": "NATIONAL", "action": "ALLOW", "transfer_enabled": True},
        ])
        # No user_has_calling_permission cross-refs

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 0

    def test_pre_existing_mapper_decision_skips(self) -> None:
        """Pre-insert mapper decision -> analyzer skips that object."""
        self._insert_permission_raw("calling_permission:cp4", "CoveredPerm", [])

        _save_decision_dict(
            self.store,
            DecisionType.CALLING_PERMISSION_MISMATCH,
            affected_objects=["calling_permission:cp4"],
            fingerprint="mapper_perm_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_healthy_permission_with_users_no_decision(self) -> None:
        """Permission with entries AND assigned users -> 0 decisions."""
        self._insert_permission_raw("calling_permission:cp5", "HealthyPerm", [
            {"call_type": "NATIONAL", "action": "ALLOW", "transfer_enabled": True},
            {"call_type": "INTERNATIONAL", "action": "BLOCK", "transfer_enabled": False},
        ])
        # Add a user cross-ref so it's not orphaned
        user = CanonicalUser(
            canonical_id="user:u1", provenance=_prov("u1"),
            first_name="Test", emails=["test@example.com"],
        )
        self.store.upsert_object(user)
        self.store.add_cross_ref(
            "user:u1", "calling_permission:cp5", "user_has_calling_permission",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_no_permissions_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 10. DuplicateUserAnalyzer
# ===================================================================

class TestDuplicateUserAnalyzer:
    """Finds users with matching email or name."""

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = DuplicateUserAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def _insert_user(self, user_id: str, first: str, last: str,
                     emails: list[str] | None = None) -> None:
        user = CanonicalUser(
            canonical_id=user_id,
            provenance=_prov(user_id),
            first_name=first,
            last_name=last,
            emails=emails or [],
        )
        self.store.upsert_object(user)

    def test_two_users_same_email_high_severity(self) -> None:
        """2 users with same email -> 1 DUPLICATE_USER, HIGH severity."""
        self._insert_user("user:a1", "Alice", "Smith", ["alice@test.com"])
        self._insert_user("user:a2", "Alice", "Jones", ["alice@test.com"])

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.DUPLICATE_USER
        assert d.severity == "HIGH"
        assert len(d.affected_objects) == 2
        assert d.fingerprint

    def test_two_users_no_email_same_name_duplicate(self) -> None:
        """2 users with no email, same (first, last) -> 1 DUPLICATE_USER."""
        self._insert_user("user:b1", "Bob", "Brown", [])
        self._insert_user("user:b2", "Bob", "Brown", [])

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.DUPLICATE_USER
        assert d.severity == "HIGH"
        assert d.affected_objects
        assert d.fingerprint

    def test_different_emails_no_decision(self) -> None:
        """2 users with different emails -> 0 decisions."""
        self._insert_user("user:c1", "Carol", "Davis", ["carol@test.com"])
        self._insert_user("user:c2", "Carol", "Davis", ["carol2@test.com"])

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_case_insensitive_email_matching(self) -> None:
        """Case-insensitive: 'A@test.com' vs 'a@test.com' -> 1 DUPLICATE_USER."""
        self._insert_user("user:d1", "Dan", "Evans", ["A@test.com"])
        self._insert_user("user:d2", "Dan", "Evans", ["a@test.com"])

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert decisions[0].type == DecisionType.DUPLICATE_USER
        assert decisions[0].severity == "HIGH"

    def test_no_users_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 11. VoicemailCompatibilityAnalyzer
# ===================================================================

class TestVoicemailCompatibilityAnalyzer:
    """Finds VM profiles with incompatible Unity Connection features."""

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = VoicemailCompatibilityAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def _insert_vm_profile(self, vm_id: str, name: str, **kwargs) -> None:
        """Insert a voicemail_profile with custom field overrides."""
        profile = CanonicalVoicemailProfile(
            canonical_id=vm_id,
            provenance=_prov(vm_id),
            cucm_voicemail_profile_name=name,
            **kwargs,
        )
        self.store.upsert_object(profile)

    def test_fax_message_set_produces_decision(self) -> None:
        """VM profile with fax_message set -> expect MEDIUM decision."""
        self._insert_vm_profile(
            "voicemail_profile:vm1", "FaxVM",
            fax_message={"enabled": True, "number": "5551234"},
        )

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.VOICEMAIL_INCOMPATIBLE
        assert d.severity == "MEDIUM"
        assert d.affected_objects  # non-empty
        assert d.fingerprint  # non-empty
        assert "fax_message" in d.summary

    def test_no_incompatible_features_no_decision(self) -> None:
        """VM profile with no incompatible features -> 0 decisions."""
        self._insert_vm_profile(
            "voicemail_profile:vm2", "CleanVM",
            enabled=True,
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_pre_existing_mapper_decision_skips(self) -> None:
        """Pre-insert mapper decision -> analyzer skips that profile."""
        self._insert_vm_profile(
            "voicemail_profile:vm3", "CoveredVM",
            fax_message={"enabled": True},
        )

        _save_decision_dict(
            self.store,
            DecisionType.VOICEMAIL_INCOMPATIBLE,
            affected_objects=["voicemail_profile:vm3"],
            fingerprint="mapper_vm_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_nonstandard_storage_produces_decision(self) -> None:
        """VM profile with non-standard message_storage -> expect decision."""
        self._insert_vm_profile(
            "voicemail_profile:vm4", "StorageVM",
            message_storage={"type": "mwi_only"},
        )

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert decisions[0].type == DecisionType.VOICEMAIL_INCOMPATIBLE
        assert decisions[0].affected_objects
        assert decisions[0].fingerprint

    def test_no_profiles_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []


# ===================================================================
# 12. FeatureApproximationAnalyzer
# ===================================================================

class TestFeatureApproximationAnalyzer:
    """Finds features requiring approximation from CUCM to Webex."""

    def setup_method(self) -> None:
        self.store, self.db_path = _make_store()
        self.analyzer = FeatureApproximationAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()
        os.unlink(self.db_path)

    def test_auto_attendant_null_menu_high_severity(self) -> None:
        """Auto attendant with business_hours_menu=None -> HIGH severity."""
        aa = CanonicalAutoAttendant(
            canonical_id="auto_attendant:aa1",
            provenance=_prov("aa1"),
            name="TestAA",
            business_hours_menu=None,
            after_hours_menu={"key_configs": {}},
        )
        self.store.upsert_object(aa)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.FEATURE_APPROXIMATION
        assert d.severity == "HIGH"
        assert d.affected_objects  # non-empty
        assert d.fingerprint  # non-empty
        assert "auto_attendant" in d.summary

    def test_hunt_group_warning_agent_limit_medium_severity(self) -> None:
        """Hunt group with warning containing 'agent limit' -> MEDIUM severity."""
        hg = CanonicalHuntGroup(
            canonical_id="hunt_group:hg1",
            provenance=_prov("hg1"),
            name="TestHG",
            warnings=["agent limit exceeded: 55 agents, max 50"],
        )
        self.store.upsert_object(hg)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        d = decisions[0]
        assert d.type == DecisionType.FEATURE_APPROXIMATION
        assert d.severity == "MEDIUM"
        assert d.affected_objects
        assert d.fingerprint

    def test_clean_object_no_decision(self) -> None:
        """Object with no warnings or structural issues -> 0 decisions."""
        cq = CanonicalCallQueue(
            canonical_id="call_queue:cq1",
            provenance=_prov("cq1"),
            name="CleanCQ",
        )
        self.store.upsert_object(cq)

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_pre_existing_mapper_decision_skips(self) -> None:
        """Pre-insert mapper decision -> analyzer skips that object."""
        aa = CanonicalAutoAttendant(
            canonical_id="auto_attendant:aa2",
            provenance=_prov("aa2"),
            name="CoveredAA",
            business_hours_menu=None,
        )
        self.store.upsert_object(aa)

        _save_decision_dict(
            self.store,
            DecisionType.FEATURE_APPROXIMATION,
            affected_objects=["auto_attendant:aa2"],
            fingerprint="mapper_feat_001",
        )

        decisions = self.analyzer.analyze(self.store)
        assert len(decisions) == 0

    def test_call_queue_not_supported_warning(self) -> None:
        """Call queue with 'not supported' warning -> expect decision."""
        cq = CanonicalCallQueue(
            canonical_id="call_queue:cq2",
            provenance=_prov("cq2"),
            name="UnsupportedCQ",
            warnings=["overflow to voicemail not supported in Webex"],
        )
        self.store.upsert_object(cq)

        decisions = self.analyzer.analyze(self.store)

        assert len(decisions) == 1
        assert decisions[0].type == DecisionType.FEATURE_APPROXIMATION
        assert decisions[0].affected_objects
        assert decisions[0].fingerprint

    def test_no_feature_objects_returns_empty(self) -> None:
        decisions = self.analyzer.analyze(self.store)
        assert decisions == []
