"""Normalization pipeline: DiscoveryResult → normalized store → cross-references.

This is the Phase 04 entry point. It connects Phase 03 extraction output
(DiscoveryResult.raw_data) to the normalizers and CrossReferenceBuilder.

Pipeline steps:
1. Iterate raw_data using RAW_DATA_MAPPING to call the right normalizer per item
2. Classify common-area phones as workspaces (post-normalization)
3. Normalize Unity Connection per-user VM settings (if present)
4. Upsert all normalized objects to the MigrationStore
5. Run CrossReferenceBuilder (pass 2)

(from 02-normalization-architecture.md, two-pass ELT design)
(from Phase 03 DiscoveryResult.raw_data contract)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder
from wxcli.migration.transform.normalizers import (
    NORMALIZER_REGISTRY,
    RAW_DATA_MAPPING,
    is_common_area_device,
    normalize_unity_vm_settings,
    normalize_workspace,
)

logger = logging.getLogger(__name__)


def normalize_discovery(
    raw_data: dict[str, dict[str, Any]],
    store: MigrationStore,
    cluster: str = "default",
    default_country_code: str = "US",
    site_prefix_rules: list[dict] | None = None,
) -> dict[str, Any]:
    """Run the full normalization pipeline on discovery raw_data.

    Args:
        raw_data: DiscoveryResult.raw_data from Phase 03 extraction.
        store: MigrationStore to write normalized objects to.
        cluster: CUCM cluster name for provenance.
        default_country_code: ISO country code for E.164 normalization.
        site_prefix_rules: Prefix stripping rules for E.164 normalization.

    Returns:
        Summary dict with counts per step.
    """
    summary: dict[str, Any] = {"pass1": {}, "pass2": {}}

    # ------------------------------------------------------------------
    # Pass 1: Normalize all objects from raw_data
    # ------------------------------------------------------------------

    total_normalized = 0

    for extractor_key, sub_key, normalizer_key in RAW_DATA_MAPPING:
        normalizer_fn = NORMALIZER_REGISTRY.get(normalizer_key)
        if normalizer_fn is None:
            logger.warning("No normalizer for %s/%s (key: %s)", extractor_key, sub_key, normalizer_key)
            continue

        extractor_data = raw_data.get(extractor_key, {})
        items = extractor_data.get(sub_key, [])
        if not isinstance(items, list):
            continue

        count = 0
        for item in items:
            try:
                obj = normalizer_fn(item, cluster=cluster)
                store.upsert_object(obj)
                count += 1
            except Exception:
                logger.exception(
                    "Failed to normalize %s/%s item: %s",
                    extractor_key, sub_key,
                    item.get("name", item.get("pattern", item.get("pkid", "?"))),
                )

        summary["pass1"][f"{extractor_key}/{sub_key}"] = count
        total_normalized += count
        if count > 0:
            logger.info("Normalized %d %s/%s objects", count, extractor_key, sub_key)

    # ------------------------------------------------------------------
    # Post-normalization: classify common-area phones as workspaces
    # (from 02b §2.8: common-area phones have ownerUserName=None, class=Phone)
    # ------------------------------------------------------------------

    phones = raw_data.get("devices", {}).get("phones", [])
    workspace_count = 0
    for phone in phones:
        if is_common_area_device(phone):
            ws_obj = normalize_workspace(phone, cluster=cluster)
            store.upsert_object(ws_obj)
            workspace_count += 1

    summary["pass1"]["workspaces_classified"] = workspace_count
    if workspace_count > 0:
        logger.info("Classified %d common-area phones as workspaces", workspace_count)

    # ------------------------------------------------------------------
    # Unity Connection per-user VM settings (if present)
    # (from Phase 03 unity_connection.py extract_user_vm_settings())
    # ------------------------------------------------------------------

    unity_settings = raw_data.get("voicemail", {}).get("unity_user_settings", {})
    unity_count = 0
    if isinstance(unity_settings, dict):
        for userid, settings in unity_settings.items():
            if isinstance(settings, dict):
                try:
                    obj = normalize_unity_vm_settings(userid, settings, cluster=cluster)
                    store.upsert_object(obj)
                    unity_count += 1
                except Exception:
                    logger.exception("Failed to normalize Unity VM settings for %s", userid)

    summary["pass1"]["unity_vm_settings"] = unity_count
    if unity_count > 0:
        logger.info("Normalized %d Unity Connection per-user VM settings", unity_count)

    summary["pass1"]["total"] = total_normalized + workspace_count + unity_count

    # ------------------------------------------------------------------
    # Pass 2: CrossReferenceBuilder
    # ------------------------------------------------------------------

    builder = CrossReferenceBuilder(
        store,
        default_country_code=default_country_code,
        site_prefix_rules=site_prefix_rules or [],
    )
    pass2_counts = builder.build()
    summary["pass2"] = pass2_counts

    logger.info(
        "Normalization complete: %d objects normalized, %d cross-refs built",
        summary["pass1"]["total"],
        sum(v for v in pass2_counts.values() if isinstance(v, int)),
    )

    return summary
