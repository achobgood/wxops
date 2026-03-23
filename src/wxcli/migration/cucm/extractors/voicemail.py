"""Voicemail extractor for CUCM AXL.

Pulls Voicemail Profiles and Voicemail Pilots from CUCM AXL.
Optionally extracts per-user Unity Connection settings via CUPI.

Sources:
- 02b-cucm-extraction.md §2.6 (voicemail extraction)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value, to_list
from wxcli.migration.cucm.unity_connection import UnityConnectionClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# ReturnedTags constants
# ------------------------------------------------------------------

# Verified: listVoiceMailProfile does NOT accept voiceMailPilot.
# Use getVoiceMailProfile for pilot reference.
VOICEMAIL_PROFILE_LIST_RETURNED_TAGS = {
    "name": "", "description": "", "voiceMailboxMask": "",
}

# Verified: listVoiceMailPilot CSS field is 'cssName', NOT 'callingSearchSpaceName'.
VOICEMAIL_PILOT_LIST_RETURNED_TAGS = {
    "dirn": "", "description": "",
}


class VoicemailExtractor(BaseExtractor):
    """Extract voicemail configuration from CUCM AXL.

    Covers Voicemail Profiles and Voicemail Pilots.
    Optionally fetches per-user voicemail settings from Unity Connection
    via the CUPI REST API when a ``unity_client`` is provided.

    (from 02b §2.6)
    """

    name = "voicemail"

    def __init__(
        self,
        connection: AXLConnection,
        unity_client: UnityConnectionClient | None = None,
    ) -> None:
        super().__init__(connection)
        self.unity_client = unity_client
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run voicemail extraction (AXL profiles and pilots).

        Unity Connection per-user settings are extracted separately via
        ``extract_unity_settings()`` because the user list comes from
        the discovery extractor.

        Returns an ExtractionResult summarizing total objects and errors.
        """
        result = ExtractionResult(extractor=self.name)

        self.results["voicemail_profiles"] = self._extract_voicemail_profiles(
            result
        )
        self.results["voicemail_pilots"] = self._extract_voicemail_pilots(
            result
        )

        return result

    # ------------------------------------------------------------------
    # Voicemail Profiles
    # ------------------------------------------------------------------

    def _extract_voicemail_profiles(
        self, result: ExtractionResult
    ) -> list[dict[str, Any]]:
        """List all voicemail profiles, then get full detail for each.

        Verified against live CUCM 15.0 (2026-03-23):
        - listVoiceMailProfile method confirmed
        - voiceMailPilot reference NOT returned by list — requires getVoiceMailProfile
        """
        profiles: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listVoiceMailProfile",
                {"name": "%"},
                VOICEMAIL_PROFILE_LIST_RETURNED_TAGS,
            )
        except Exception as exc:
            msg = f"listVoiceMailProfile failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return profiles

        for summary in summaries:
            result.total += 1
            profile_name = summary.get("name", "")
            if not profile_name:
                result.failed += 1
                continue
            try:
                detail = self.get_detail("getVoiceMailProfile", name=profile_name)
            except Exception as exc:
                logger.warning(
                    "[%s] getVoiceMailProfile error for %s: %s",
                    self.name, profile_name, exc,
                )
                profiles.append(summary)
                continue
            if detail is None:
                profiles.append(summary)
                continue
            profiles.append(detail)

        return profiles

    # ------------------------------------------------------------------
    # Voicemail Pilots
    # ------------------------------------------------------------------

    def _extract_voicemail_pilots(
        self, result: ExtractionResult
    ) -> list[dict[str, Any]]:
        """List all voicemail pilots.

        <!-- NEEDS VERIFICATION: listVoiceMailPilot method name and search field
             (may be 'dirn' instead of 'name') -->
        """
        pilots: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(
                "listVoiceMailPilot",
                {"dirn": "%"},
                VOICEMAIL_PILOT_LIST_RETURNED_TAGS,
            )
            pilots.extend(summaries)
            result.total += len(summaries)
        except Exception as exc:
            msg = f"listVoiceMailPilot failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)

        return pilots

    # ------------------------------------------------------------------
    # Unity Connection per-user settings
    # ------------------------------------------------------------------

    def extract_unity_settings(
        self, user_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Extract per-user voicemail settings from Unity Connection.

        This is called separately from ``extract()`` because the user
        list comes from the discovery extractor (02b §2.1), not from
        this extractor.

        Args:
            user_ids: List of CUCM user IDs (aliases) to look up in
                Unity Connection.

        Returns:
            Dict mapping CUCM user ID to their Unity Connection
            voicemail settings. Users not found in UC are omitted.
        """
        if self.unity_client is None:
            logger.info(
                "[%s] No Unity Connection client configured — "
                "skipping per-user VM extraction",
                self.name,
            )
            return {}

        settings: dict[str, dict[str, Any]] = {}
        for user_id in user_ids:
            try:
                user_settings = self.unity_client.extract_user_vm_settings(
                    user_id
                )
                if user_settings is not None:
                    settings[user_id] = user_settings
                else:
                    logger.debug(
                        "[%s] User %s not found in Unity Connection",
                        self.name,
                        user_id,
                    )
            except Exception as exc:
                logger.warning(
                    "[%s] Unity extraction failed for user %s: %s",
                    self.name,
                    user_id,
                    exc,
                )

        logger.info(
            "[%s] Extracted Unity settings for %d/%d users",
            self.name,
            len(settings),
            len(user_ids),
        )
        return settings
