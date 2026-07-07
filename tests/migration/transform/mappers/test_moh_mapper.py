"""Tests for MOHMapper — CUCM Music On Hold → Webex MOH advisory."""

from __future__ import annotations
from datetime import datetime, timezone

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.moh_mapper import MOHMapper


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_moh_source(
    name: str = "SampleAudioSource",
    file_name: str = "hold_music.wav",
    is_default: bool = False,
    source_id: str = "2",
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"moh_source:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "source_file_name": file_name,
            "is_default": is_default,
            "source_id": source_id,
        },
    )


class TestMOHMapperDefault:
    def test_default_source_no_decision(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_moh_source(is_default=True, source_id="1"))

        mapper = MOHMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0


class TestMOHMapperCustom:
    def test_custom_source_produces_audio_asset_manual(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_moh_source(is_default=False))

        mapper = MOHMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "AUDIO_ASSET_MANUAL"

    def test_canonical_fields_correct(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_moh_source(name="CustomMOH", file_name="custom.wav"))

        mapper = MOHMapper()
        mapper.map(store)

        moh = store.get_object("music_on_hold:CustomMOH")
        assert moh is not None
        assert moh["source_name"] == "CustomMOH"
        assert moh["source_file_name"] == "custom.wav"


class TestMOHMapperNoSources:
    def test_no_sources_no_objects(self):
        store = MigrationStore(":memory:")

        mapper = MOHMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 0
