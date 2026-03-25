"""CallForwardingMapper — CUCM per-line forwarding → Webex per-person call forwarding.

Reads phone objects from the store (which contain enriched line entries with
call forwarding fields from getLine), resolves user ownership via
device_owned_by_user cross-ref, and produces CanonicalCallForwarding objects.

CUCM has 10 forwarding variants. Webex supports 3 (CFA, CFB, CFNA).
The remaining 5 CUCM-only variants (BusyInt, NoAnswerInt, NoCoverage,
OnFailure, NotRegistered) produce FORWARDING_LOSSY decisions.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from wxcli.migration.models import (
    CanonicalCallForwarding,
    DecisionType,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.models import MapperResult
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    skip_option,
)

logger = logging.getLogger(__name__)

# CUCM-only forwarding variants that have no Webex equivalent
_LOSSY_VARIANTS = (
    "callForwardBusyInt",
    "callForwardNoAnswerInt",
    "callForwardNoCoverage",
    "callForwardNoCoverageInt",
    "callForwardOnFailure",
    "callForwardNotRegistered",
    "callForwardNotRegisteredInt",
)


def _is_forwarding_active(fwd: dict | None) -> bool:
    """Check if a CUCM forwarding setting is actively configured."""
    if not fwd or not isinstance(fwd, dict):
        return False
    dest = fwd.get("destination")
    fwd_to_vm = fwd.get("forwardToVoiceMail")
    # Active if there's a non-empty destination or it forwards to voicemail
    return bool(dest) or (fwd_to_vm in ("true", True))


def _duration_to_rings(duration_ms: int | str | None) -> int | None:
    """Convert CUCM duration (seconds) to Webex ring count.

    CUCM stores call forward no answer timer in seconds.
    Webex uses ring count: divide by 6, round up, clamp to 2-20.
    """
    if duration_ms is None:
        return None
    try:
        val = int(duration_ms)
    except (ValueError, TypeError):
        return None
    if val <= 0:
        return None
    rings = math.ceil(val / 6)
    return max(2, min(20, rings))


class CallForwardingMapper(Mapper):
    """Map CUCM per-line call forwarding to Webex per-person call forwarding.

    Tier 2 expansion: adds CanonicalCallForwarding objects and
    FORWARDING_LOSSY decisions for CUCM-only variants.
    """

    name = "call_forwarding_mapper"
    depends_on = ["user_mapper", "line_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Iterate phones (which contain enriched line entries)
        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}
            lines = state.get("lines", [])
            if not lines:
                continue

            # Resolve owner user via cross-ref
            user_refs = store.find_cross_refs(phone_id, "device_owned_by_user")
            if not user_refs:
                continue
            user_id = user_refs[0]

            # Check if we already created forwarding for this user (multi-device)
            user_name = user_id.split(":", 1)[-1]
            existing = store.get_object(f"call_forwarding:{user_name}")
            if existing:
                continue

            # Use primary line (index 1 or first line)
            primary_line = self._get_primary_line(lines)
            if not primary_line:
                continue

            # Build canonical call forwarding
            cf = self._build_call_forwarding(store, user_id, phone_data, primary_line)
            store.upsert_object(cf)
            result.objects_created += 1

            # Write cross-ref
            store.add_cross_ref(user_id, cf.canonical_id, "user_has_call_forwarding")

            # Check for lossy CUCM-only variants
            lossy_variants = self._detect_lossy_variants(primary_line)
            if lossy_variants:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FORWARDING_LOSSY,
                    severity="LOW",
                    summary=(
                        f"User '{user_name}' has {len(lossy_variants)} "
                        f"CUCM-only forwarding variant(s): {', '.join(lossy_variants)}"
                    ),
                    context={
                        "user_id": user_id,
                        "lossy_variants": lossy_variants,
                    },
                    options=[
                        accept_option(f"Accept loss of {len(lossy_variants)} CUCM-only forwarding variant(s)"),
                        skip_option("Skip call forwarding migration for this user"),
                    ],
                    affected_objects=[user_id, cf.canonical_id],
                )
                result.decisions.append(decision)

        return result

    def _get_primary_line(self, lines: list) -> dict | None:
        """Get the primary line (index 1) from a phone's line list."""
        if not lines:
            return None
        # Find line with index "1" or 1
        for line in lines:
            if isinstance(line, dict):
                idx = line.get("index")
                if str(idx) == "1":
                    return line
        # Fallback: first line
        first = lines[0]
        return first if isinstance(first, dict) else None

    def _build_call_forwarding(
        self,
        store: MigrationStore,
        user_id: str,
        phone_data: dict,
        line: dict,
    ) -> CanonicalCallForwarding:
        """Build a CanonicalCallForwarding from a phone's primary line."""
        user_name = user_id.split(":", 1)[-1]
        prov = extract_provenance(phone_data)

        # CFA (Call Forward All)
        cfa = line.get("callForwardAll") or {}
        # CFB (Call Forward Busy)
        cfb = line.get("callForwardBusy") or {}
        # CFNA (Call Forward No Answer)
        cfna = line.get("callForwardNoAnswer") or {}
        # CUCM-only variants (preserved for decision context)
        cfb_int = line.get("callForwardBusyInt") or {}
        cfna_int = line.get("callForwardNoAnswerInt") or {}
        cfnc = line.get("callForwardNoCoverage") or {}
        cfnc_int = line.get("callForwardNoCoverageInt") or {}
        cff = line.get("callForwardOnFailure") or {}
        cfnr = line.get("callForwardNotRegistered") or {}
        cfnr_int = line.get("callForwardNotRegisteredInt") or {}

        return CanonicalCallForwarding(
            canonical_id=f"call_forwarding:{user_name}",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            user_canonical_id=user_id,
            # CFA
            always_enabled=bool(cfa.get("destination") or cfa.get("forwardToVoiceMail") in ("true", True)),
            always_destination=cfa.get("destination") or None,
            always_to_voicemail=cfa.get("forwardToVoiceMail") in ("true", True),
            # CFB
            busy_enabled=bool(cfb.get("destination") or cfb.get("forwardToVoiceMail") in ("true", True)),
            busy_destination=cfb.get("destination") or None,
            busy_to_voicemail=cfb.get("forwardToVoiceMail") in ("true", True),
            # CFNA
            no_answer_enabled=bool(cfna.get("destination") or cfna.get("forwardToVoiceMail") in ("true", True)),
            no_answer_destination=cfna.get("destination") or None,
            no_answer_to_voicemail=cfna.get("forwardToVoiceMail") in ("true", True),
            no_answer_ring_count=_duration_to_rings(cfna.get("duration")),
            # CUCM-only (preserved in canonical for reporting)
            busy_internal_enabled=_is_forwarding_active(cfb_int),
            busy_internal_destination=cfb_int.get("destination") or None,
            no_answer_internal_enabled=_is_forwarding_active(cfna_int),
            no_answer_internal_destination=cfna_int.get("destination") or None,
            no_coverage_enabled=_is_forwarding_active(cfnc) or _is_forwarding_active(cfnc_int),
            no_coverage_destination=cfnc.get("destination") or cfnc_int.get("destination") or None,
            on_failure_enabled=_is_forwarding_active(cff),
            on_failure_destination=cff.get("destination") or None,
            not_registered_enabled=_is_forwarding_active(cfnr) or _is_forwarding_active(cfnr_int),
            not_registered_destination=cfnr.get("destination") or cfnr_int.get("destination") or None,
        )

    def _detect_lossy_variants(self, line: dict) -> list[str]:
        """Detect CUCM-only forwarding variants that are actively configured."""
        lossy = []
        for variant in _LOSSY_VARIANTS:
            fwd = line.get(variant)
            if _is_forwarding_active(fwd):
                lossy.append(variant)
        return lossy
