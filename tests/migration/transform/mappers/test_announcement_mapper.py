"""Tests for AnnouncementMapper — CUCM Announcements → Webex announcement repo advisory."""

from __future__ import annotations
from datetime import datetime, timezone

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.announcement_mapper import AnnouncementMapper


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_announcement(
    name: str = "AA-Welcome",
    file_name: str = "welcome.wav",
    description: str = "Auto Attendant welcome greeting",
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"announcement:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": description,
            "file_name": file_name,
        },
    )


class TestAnnouncementMapperBasic:
    def test_creates_canonical_object(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_announcement())

        mapper = AnnouncementMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        ann = store.get_object("announcement:AA-Welcome")
        assert ann is not None

    def test_produces_audio_asset_manual_decision(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_announcement())

        mapper = AnnouncementMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "AUDIO_ASSET_MANUAL"

    def test_wav_media_type(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_announcement(file_name="greeting.wav"))

        mapper = AnnouncementMapper()
        mapper.map(store)

        ann = store.get_object("announcement:AA-Welcome")
        assert ann["media_type"] == "WAV"

    def test_wma_media_type(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_announcement(file_name="greeting.wma"))

        mapper = AnnouncementMapper()
        mapper.map(store)

        ann = store.get_object("announcement:AA-Welcome")
        assert ann["media_type"] == "WMA"


class TestAnnouncementMapperNoData:
    def test_no_announcements_no_objects(self):
        store = MigrationStore(":memory:")

        mapper = AnnouncementMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 0


class TestAnnouncementMapperMultiple:
    def test_multiple_announcements(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_announcement("AA-Welcome", "welcome.wav"))
        store.upsert_object(_make_announcement("CQ-Comfort", "comfort.wav"))

        mapper = AnnouncementMapper()
        result = mapper.map(store)

        assert result.objects_created == 2
        assert len(result.decisions) == 2
