"""Discovery orchestrator — runs all extractors and writes results to store.

Entry point for the extraction phase. Connects to CUCM via AXL SOAP,
runs each extractor in sequence, and writes raw CUCM dicts into the SQLite
store for pass 1 normalization.

Sources:
- 02b-cucm-extraction.md §1 (orchestration, extractor order, summary)
- 02-normalization-architecture.md (two-pass ELT pattern)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from rich.console import Console

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import ExtractionResult
from wxcli.migration.cucm.extractors.devices import DeviceExtractor
from wxcli.migration.cucm.extractors.features import FeatureExtractor
from wxcli.migration.cucm.extractors.locations import LocationExtractor
from wxcli.migration.cucm.extractors.routing import RoutingExtractor
from wxcli.migration.cucm.extractors.users import UserExtractor
from wxcli.migration.cucm.extractors.templates import TemplateExtractor
from wxcli.migration.cucm.extractors.voicemail import VoicemailExtractor
from wxcli.migration.cucm.extractors.informational import InformationalExtractor
from wxcli.migration.cucm.extractors.tier4 import Tier4Extractor
from wxcli.migration.cucm.unity_connection import UnityConnectionClient
from wxcli.migration.store import MigrationStore

logger = logging.getLogger(__name__)
console = Console()

# Extraction order (from 02b §1).
# Extractors are independent at the extraction phase — order is flexible.
# shared_lines and workspaces are post-processing steps, not AXL extractors,
# and run during normalization pass 2.
EXTRACTOR_ORDER = [
    "locations",   # Device pools, datetime groups, CUCM locations — no dependencies
    "users",       # EndUsers — no extraction-phase dependencies
    "devices",     # Phones — no extraction-phase dependencies
    "routing",     # Partitions, CSS, route patterns, gateways, trunks — no dependencies
    "features",    # Hunt pilots, CTI RPs, call park, pickup, schedules — no dependencies
    "voicemail",   # Voicemail profiles, pilot numbers — no dependencies
    "templates",   # Button templates, softkey templates — no dependencies
    "informational",  # Tier 3: report-only informational objects — no dependencies
    "tier4",  # Tier 4 feature gaps: recording, SNR, transformations, EM profiles
]


class DiscoveryResult:
    """Aggregate result of a full discovery run.

    (from 02b §1: discovery run summary)

    **Data flow contract for Phase 04 normalizers:**

    Discovery does NOT write raw data to the SQLite store. Raw CUCM dicts
    live in ``raw_data`` (in-memory). Phase 04 normalizers consume
    ``raw_data``, transform to canonical models, and write to the store
    via ``MigrationStore.upsert_object()``.

    **raw_data structure per extractor:**

    - ``raw_data["locations"]``: ``device_pools``, ``datetime_groups``, ``cucm_locations``
    - ``raw_data["users"]``: ``users``
    - ``raw_data["devices"]``: ``phones`` (lines pre-filtered: speed dials removed)
    - ``raw_data["routing"]``: ``partitions``, ``css_list``, ``route_patterns``,
      ``gateways``, ``sip_trunks``, ``route_groups``, ``route_lists``,
      ``translation_patterns``
    - ``raw_data["features"]``: ``hunt_pilots``, ``hunt_lists``, ``line_groups``,
      ``cti_route_points``, ``call_parks``, ``pickup_groups``, ``time_schedules``,
      ``time_periods``
    - ``raw_data["voicemail"]``: ``voicemail_profiles``, ``voicemail_pilots``,
      and optionally ``unity_user_settings`` (dict keyed by CUCM userid)
    """

    def __init__(self) -> None:
        self.run_id: str = ""
        self.cucm_version: str = ""
        self.started_at: str = ""
        self.completed_at: str = ""
        self.extractor_results: dict[str, ExtractionResult] = {}
        self.raw_data: dict[str, dict[str, Any]] = {}

    @property
    def total_objects(self) -> int:
        return sum(r.total for r in self.extractor_results.values())

    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.extractor_results.values())

    def to_summary(self) -> dict[str, Any]:
        """Produce the journal summary dict (from 02b §1)."""
        return {
            "run_type": "discovery",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cucm_version": self.cucm_version,
            "extractors": {
                name: {"total": r.total, "failed": r.failed}
                for name, r in self.extractor_results.items()
            },
        }


def run_discovery(
    connection: AXLConnection,
    store: MigrationStore,
    unity_client: UnityConnectionClient | None = None,
) -> DiscoveryResult:
    """Run full CUCM discovery — extract all object types.

    (from 02b §1: discovery orchestration)

    Args:
        connection: Established AXL SOAP connection.
        store: Migration store for writing results and journal entries.
        unity_client: Optional Unity Connection client for voicemail detail.

    Returns:
        DiscoveryResult with per-extractor counts, errors, and raw data.
    """
    result = DiscoveryResult()
    result.run_id = store.current_run_id
    result.started_at = datetime.now(timezone.utc).isoformat()

    # Detect CUCM version (from cucm-wxc-migration.md line 309)
    try:
        result.cucm_version = connection.get_version()
        logger.info("CUCM version: %s", result.cucm_version)
    except Exception as exc:
        logger.warning("Could not detect CUCM version: %s", exc)
        result.cucm_version = "unknown"

    # Build extractors in order (from 02b §1: EXTRACTOR_ORDER)
    extractors: dict[str, Any] = {
        "locations": LocationExtractor(connection),
        "users": UserExtractor(connection),
        "devices": DeviceExtractor(connection),
        "routing": RoutingExtractor(connection),
        "features": FeatureExtractor(connection),
        "voicemail": VoicemailExtractor(connection, unity_client=unity_client),
        "templates": TemplateExtractor(connection),
        "informational": InformationalExtractor(connection),
        "tier4": Tier4Extractor(connection),
    }

    # Run each extractor in order
    for name in EXTRACTOR_ORDER:
        extractor = extractors[name]
        logger.info("--- Running extractor: %s ---", name)
        console.print(f"  Extracting {name}...")
        try:
            ext_result = extractor.extract()
        except Exception as exc:
            logger.error("[%s] Extraction failed: %s", name, exc)
            ext_result = ExtractionResult(extractor=name)
            ext_result.errors.append(f"Unrecoverable error: {exc}")

        result.extractor_results[name] = ext_result
        result.raw_data[name] = extractor.results
        console.print(f"  {name}: {ext_result.total} objects")
        if ext_result.errors:
            for err in ext_result.errors:
                console.print(f"  [yellow]{name}: {err}[/yellow]")

    # Extract Unity Connection per-user voicemail settings if client available
    if unity_client is not None:
        user_extractor = extractors["users"]
        user_dicts = user_extractor.results.get("users", [])
        user_ids = [u.get("userid", "") for u in user_dicts if u.get("userid")]
        vm_extractor = extractors["voicemail"]
        unity_settings = vm_extractor.extract_unity_settings(user_ids)
        # Store Unity settings alongside AXL voicemail data
        result.raw_data.setdefault("voicemail", {})["unity_user_settings"] = unity_settings

    result.completed_at = datetime.now(timezone.utc).isoformat()

    # Write summary to journal (from 02b §1: discovery run summary)
    # Ensure the system sentinel object exists so the FK constraint is satisfied
    store.conn.execute(
        """INSERT OR IGNORE INTO objects
           (canonical_id, object_type, status, data, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("system:discovery", "system", "discovered", "{}", result.completed_at, result.completed_at),
    )
    store.conn.commit()
    summary = result.to_summary()
    store.add_journal_entry(
        entry_type="discovery_complete",
        canonical_id="system:discovery",
        resource_type="discovery",
        request=summary,
    )

    logger.info(
        "Discovery complete: %d objects extracted (%d failed) across %d extractors",
        result.total_objects,
        result.total_failed,
        len(result.extractor_results),
    )

    return result
