"""Integration test: intercept candidates through the full pipeline."""
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.normalizers import NORMALIZER_REGISTRY
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder
from wxcli.migration.transform.mappers.call_settings_mapper import CallSettingsMapper
from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates
from wxcli.migration.report.appendix import generate_appendix


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _build_store_with_intercept():
    """Build a store with a user + intercept candidate, simulating the full pipeline."""
    store = MigrationStore(":memory:")

    # 1. Simulate normalized user
    store.upsert_object(CanonicalUser(
        canonical_id="user:jsmith", provenance=_prov("jsmith"),
        status=MigrationStatus.NORMALIZED,
        emails=["jsmith@test.com"], cucm_userid="jsmith",
    ))

    # 2. Simulate normalized intercept candidate (as normalize_discovery would produce)
    raw_candidate = {
        "userid": "jsmith",
        "dn": "1001",
        "partition": "Blocked_PT",
        "signal_type": "blocked_partition",
        "forward_destination": "",
        "voicemail_enabled": False,
    }
    normalizer = NORMALIZER_REGISTRY["intercept_candidate"]
    obj = normalizer(raw_candidate)
    store.upsert_object(obj)

    # 3. Build cross-references
    builder = CrossReferenceBuilder(store)
    builder.build()

    # 4. Run CallSettingsMapper
    mapper = CallSettingsMapper()
    mapper.map(store)

    return store


class TestInterceptFullPipeline:
    def test_full_pipeline_with_intercept(self):
        """Intercept candidate flows through normalize -> cross-ref -> map -> analyze."""
        store = _build_store_with_intercept()

        # Verify cross-ref was built
        refs = store.find_cross_refs("user:jsmith", "user_has_intercept_signal")
        assert len(refs) == 1

        # Verify user was enriched with intercept settings
        user_data = store.get_object("user:jsmith")
        assert user_data is not None
        call_settings = user_data.get("call_settings", {})
        assert "intercept" in call_settings
        assert call_settings["intercept"]["detected"] is True
        assert call_settings["intercept"]["signal_type"] == "blocked_partition"

        # Verify advisory pattern fires
        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "call_intercept_candidates"
        assert findings[0].severity == "MEDIUM"
        assert findings[0].category == "out_of_scope"

    def test_report_includes_intercept(self):
        """Assessment report appendix includes intercept candidates section."""
        store = _build_store_with_intercept()

        appendix_html = generate_appendix(store)
        assert "intercept-candidates" in appendix_html
        assert "Call Intercept Candidates" in appendix_html
        assert "jsmith" in appendix_html
        assert "Blocked Partition" in appendix_html
