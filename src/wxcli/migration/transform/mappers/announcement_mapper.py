"""AnnouncementMapper — CUCM Announcements → audio asset advisory.

This mapper is advisory-only — there is no automated audio file transfer
from CUCM to Webex. Every announcement produces an AUDIO_ASSET_MANUAL
decision requiring the admin to manually download and re-upload audio.

(from tier2-enterprise-expansion.md §2.4)
"""

from __future__ import annotations

import logging

from wxcli.migration.models import (
    CanonicalAnnouncement,
    DecisionOption,
    DecisionType,
    MigrationStatus,
    MapperResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    skip_option,
)

logger = logging.getLogger(__name__)

# File extension → media type mapping
_EXT_TO_MEDIA_TYPE: dict[str, str] = {
    ".wav": "WAV",
    ".wma": "WMA",
    ".mp3": "MP3",
    ".au": "AU",
}


def _detect_media_type(file_name: str | None) -> str:
    """Detect media type from file extension."""
    if not file_name:
        return "UNKNOWN"
    lower = file_name.lower()
    for ext, media_type in _EXT_TO_MEDIA_TYPE.items():
        if lower.endswith(ext):
            return media_type
    return "UNKNOWN"


class AnnouncementMapper(Mapper):
    """Map CUCM Announcements to CanonicalAnnouncement objects with decisions.

    Every announcement produces an AUDIO_ASSET_MANUAL decision because
    there is no automated audio transfer path from CUCM to Webex.

    Tier 2 expansion: depends on location_mapper and feature_mapper
    for cross-reference context.
    """

    name = "announcement_mapper"
    depends_on = ["location_mapper", "feature_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        announcements = store.get_objects("announcement")
        if not announcements:
            return result

        for ann_data in announcements:
            state = ann_data.get("pre_migration_state") or {}
            name = state.get("name") or ""
            description = state.get("description") or ""
            file_name = state.get("file_name") or ""
            media_type = _detect_media_type(file_name)

            prov = extract_provenance(ann_data)
            canonical = CanonicalAnnouncement(
                canonical_id=f"announcement:{name}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                name=name,
                file_name=file_name,
                media_type=media_type,
                source_system="cucm",
            )
            store.upsert_object(canonical)
            result.objects_created += 1

            # Every announcement needs manual audio migration
            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.AUDIO_ASSET_MANUAL,
                severity="MEDIUM",
                summary=(
                    f"Announcement '{name}' requires manual audio migration"
                    f"{f' ({media_type} file: {file_name})' if file_name else ''}"
                ),
                context={
                    "announcement_name": name,
                    "file_name": file_name,
                    "media_type": media_type,
                    "description": description,
                    "advisory_type": "audio_asset_manual",
                },
                options=[
                    accept_option(
                        "Admin downloads audio from CUCM and uploads to Webex announcement repository"
                    ),
                    DecisionOption(
                        id="use_default",
                        label="Use Webex default",
                        impact="Feature uses Webex default greeting instead of custom audio",
                    ),
                    skip_option("Feature configured without custom audio"),
                ],
                affected_objects=[f"announcement:{name}"],
            )
            result.decisions.append(decision)

        return result
