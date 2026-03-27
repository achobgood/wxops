"""MOH mapper: CUCM MOH Audio Sources -> Webex per-location Music On Hold.

Maps CUCM Music On Hold audio sources to Webex Calling per-location MOH
settings (CanonicalMusicOnHold).

Default MOH sources map automatically. Custom audio sources produce
AUDIO_ASSET_MANUAL decisions because the WAV file must be manually
downloaded from CUCM and uploaded to Webex.

(from tier2-enterprise-expansion.md §2.3)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalMusicOnHold,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    skip_option,
)

logger = logging.getLogger(__name__)


class MOHMapper(Mapper):
    """Map CUCM MOH audio sources to Webex per-location MOH settings.

    For each moh_source in the store:
    - Default sources: create CanonicalMusicOnHold, no decision needed
    - Custom sources: create CanonicalMusicOnHold + AUDIO_ASSET_MANUAL decision

    (from tier2-enterprise-expansion.md §2.3)
    """

    name = "moh_mapper"
    depends_on = ["location_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        """Read CUCM MOH sources and produce Webex MOH settings."""
        result = MapperResult()

        for moh_data in store.get_objects("moh_source"):
            canonical_id = moh_data["canonical_id"]
            state = moh_data.get("pre_migration_state") or {}

            name = state.get("name") or ""
            source_file_name = state.get("source_file_name") or ""
            is_default = state.get("is_default", False)
            source_id = state.get("source_id") or ""

            prov = extract_provenance(moh_data)

            moh_obj = CanonicalMusicOnHold(
                canonical_id=f"music_on_hold:{name}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                source_name=name,
                source_file_name=source_file_name,
                is_default=is_default,
                cucm_source_id=source_id,
            )
            store.upsert_object(moh_obj)
            result.objects_created += 1

            # Custom audio sources need manual intervention
            if not is_default:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.AUDIO_ASSET_MANUAL,
                    severity="MEDIUM",
                    summary=(
                        f"Custom MOH audio source '{name}' "
                        f"(file: {source_file_name or 'unknown'}) "
                        f"requires manual download from CUCM and upload to Webex"
                    ),
                    context={
                        "moh_source_name": name,
                        "source_file_name": source_file_name,
                        "source_id": source_id,
                        "canonical_id": f"music_on_hold:{name}",
                    },
                    options=[
                        accept_option(
                            "Admin downloads WAV from CUCM and uploads to Webex location MOH"
                        ),
                        _use_default_option(),
                        skip_option("Skip MOH migration for this source"),
                    ],
                    affected_objects=[f"music_on_hold:{name}"],
                )
                result.decisions.append(decision)

        return result


def _use_default_option():
    """Create a 'Use default MOH' decision option."""
    from wxcli.migration.models import DecisionOption

    return DecisionOption(
        id="use_default",
        label="Use Webex default",
        impact="Accept Webex default MOH instead of custom audio",
    )
