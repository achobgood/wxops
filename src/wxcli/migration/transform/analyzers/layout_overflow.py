"""Layout overflow analyzer — detects button count overflow and KEM incompatibility.

Sweeps CanonicalDeviceLayout objects cross-referenced with CanonicalDevice objects.
Detects phones where the CUCM button template assigns more line keys than the Webex
device model supports, or where KEM buttons exist but the Webex model doesn't support KEM.

Sources:
- tier2-phase2-phone-config-design.md §5.1
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision

logger = logging.getLogger(__name__)

# Phone model → max line key count — imported from the single source of truth
from wxcli.migration.phone_models import MODEL_LINE_KEY_COUNTS as _MODEL_LINE_KEY_COUNTS

# Models that support KEM expansion modules
_KEM_SUPPORTED_MODELS: set[str] = {
    "8845", "8851", "8861", "8865",
    "9851", "9861",
    "6851", "6861", "6871",
}


def _extract_model_number(model: str) -> str:
    """Extract numeric model identifier from full model string.

    Examples:
        "CP-8845" → "8845"
        "Cisco 9841" → "9841"
        "DMS Cisco 8845" → "8845"
    """
    if not model:
        return ""
    # Strip common prefixes
    cleaned = model.replace("CP-", "").replace("Cisco ", "").replace("DMS ", "")
    # Take first token that looks like a model number (4 digits)
    for token in cleaned.split():
        digits = "".join(c for c in token if c.isdigit())
        if len(digits) >= 4:
            return digits
    # Fallback: return cleaned string
    return cleaned.strip()


class LayoutOverflowAnalyzer(Analyzer):
    """Detects layout overflow (too many line keys) and KEM incompatibility.

    Sweeps all CanonicalDeviceLayout objects and checks:
    - resolved_line_keys count vs device model max_line_count
    - resolved_kem_keys present but device model doesn't support KEM
    """

    name = "layout_overflow"
    decision_types = [DecisionType.FEATURE_APPROXIMATION]
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        decisions: list[Decision] = []

        layouts = store.get_objects("device_layout")
        if not layouts:
            return decisions

        for layout in layouts:
            device_cid = layout.get("device_canonical_id", "")
            if not device_cid:
                continue

            device = store.get_object(device_cid)
            if device is None:
                continue

            model_raw = device.get("model", "")
            model_num = _extract_model_number(model_raw)

            resolved_keys = layout.get("resolved_line_keys", [])
            kem_keys = layout.get("resolved_kem_keys", [])
            layout_cid = layout.get("canonical_id", "")

            # Check 1: Line key overflow
            max_keys = _MODEL_LINE_KEY_COUNTS.get(model_num)
            if max_keys is not None and len(resolved_keys) > max_keys:
                context = {
                    "layout_canonical_id": layout_cid,
                    "device_canonical_id": device_cid,
                    "model": model_raw,
                    "model_number": model_num,
                    "max_line_keys": max_keys,
                    "actual_line_keys": len(resolved_keys),
                    "overflow_count": len(resolved_keys) - max_keys,
                    "overflow_type": "line_key_count",
                }
                options = [
                    DecisionOption(
                        id="accept",
                        label=f"Truncate to first {max_keys} keys",
                        impact=f"{len(resolved_keys) - max_keys} line keys will be dropped",
                    ),
                    DecisionOption(
                        id="manual",
                        label="Create custom line key template",
                        impact="Manually assign line keys to fit device capacity",
                    ),
                    DecisionOption(
                        id="skip",
                        label="Use Webex default layout",
                        impact="Phone will use Webex default line key assignment",
                    ),
                ]
                decisions.append(self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="MEDIUM",
                    summary=(
                        f"Line key overflow on {model_raw}: "
                        f"{len(resolved_keys)} keys exceeds max {max_keys}"
                    ),
                    context=context,
                    options=options,
                    affected_objects=[layout_cid, device_cid],
                ))

            # Check 2: KEM buttons on non-KEM device
            if kem_keys and model_num not in _KEM_SUPPORTED_MODELS:
                context = {
                    "layout_canonical_id": layout_cid,
                    "device_canonical_id": device_cid,
                    "model": model_raw,
                    "model_number": model_num,
                    "kem_key_count": len(kem_keys),
                    "overflow_type": "kem_not_supported",
                }
                options = [
                    DecisionOption(
                        id="accept_loss",
                        label="KEM buttons will be lost",
                        impact=f"{len(kem_keys)} KEM buttons cannot be migrated — device does not support KEM",
                    ),
                    DecisionOption(
                        id="manual",
                        label="Attach compatible KEM to new device",
                        impact="Replace device with KEM-compatible model or add KEM module",
                    ),
                ]
                decisions.append(self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="MEDIUM",
                    summary=(
                        f"KEM buttons on {model_raw} which does not support KEM: "
                        f"{len(kem_keys)} KEM keys will be lost"
                    ),
                    context=context,
                    options=options,
                    affected_objects=[layout_cid, device_cid],
                ))

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        return self._hash_fingerprint({
            "device_canonical_id": context.get("device_canonical_id", ""),
            "overflow_type": context.get("overflow_type", ""),
            "model": context.get("model", ""),
        })
