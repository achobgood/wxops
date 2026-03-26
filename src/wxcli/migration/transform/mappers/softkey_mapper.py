"""SoftkeyMapper: CUCM Softkey Templates → Webex PSK config (9800/8875).

Maps CUCM per-call-state softkey assignments to Webex Programmable Softkey
(PSK) keywords and per-state key lists. Only actionable for 9800/8875
phones (PhoneOS with PSK support). Classic MPP phones produce report
entries only (is_psk_target=False).

(from tier2-phase2-phone-config-design.md §4.3)

Cross-ref reads:
    phone_uses_softkey_template  (Phone → SoftkeyTemplate)  — usage + model
"""
from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalSoftkeyConfig,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    extract_provenance,
)

logger = logging.getLogger(__name__)

# CUCM softkey name → Webex PSK keyword (None = unmappable)
CUCM_SOFTKEY_TO_PSK: dict[str, str | None] = {
    "Trnsfer": "xfer",
    "Confrn": "conf",
    "Park": "park",
    "Pickup": "pickup",
    "GPickUp": "gpickup",
    "Hold": "hold",
    "Resume": "resume",
    "EndCall": "endcall",
    "NewCall": "newcall",
    "Redial": "redial",
    "DND": "dnd",
    "Barge": "bridgein",
    "Join": "join",
    "LiveRcd": "crdstart",
    "CfwdAll": "cfwd",
    "Unpark": "unpark",
    "HLog": "acd_login",
    "Answer": "answer",
    # Unmappable
    "CallBack": None,
    "iDivert": None,
    "QRT": None,
    "MeetMe": None,
    "Mobility": None,
    "cBarge": None,
}

# CUCM call state → Webex PSK state key list name
CUCM_STATE_TO_PSK_STATE: dict[str, str | None] = {
    "onHook": "idle",
    "offHook": "offHook",
    "ringIn": "ringing",
    "ringOut": "progressing",
    "connected": "connected",
    "onHold": "hold",
    "sharedActive": "sharedActive",
    "sharedHeld": "sharedHeld",
    "connectedTransfer": "startTransfer",
    "connectedConference": "startConference",
    "transition": "releasing",
    # Unmappable
    "remoteInUse": None,
    "park": None,
}

# 9800/8875 model number substrings that indicate PSK capability
_PSK_MODEL_NUMBERS = {"9811", "9821", "9841", "9851", "9861", "9871", "8875"}


def _is_psk_capable_model(model: str | None) -> bool:
    """Check if a phone model supports Programmable Softkeys (PSK)."""
    if not model:
        return False
    for num in _PSK_MODEL_NUMBERS:
        if num in model:
            return True
    return False


class SoftkeyMapper(Mapper):
    """Maps CUCM Softkey Templates to Webex PSK config or report flags."""

    name = "softkey_mapper"
    depends_on = ["device_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        for tmpl_data in store.get_objects("softkey_template"):
            tmpl_id = tmpl_data["canonical_id"]
            state = tmpl_data.get("pre_migration_state") or {}
            name = state.get("name", tmpl_id.split(":", 1)[-1])
            call_states = state.get("call_states", {})

            # Count phones and determine PSK eligibility
            phone_refs = [r["from_id"] for r in store.get_cross_refs(to_id=tmpl_id, relationship="phone_uses_softkey_template")]
            phones_using = len(phone_refs)

            has_psk_phone = False
            for phone_id in phone_refs:
                phone = store.get_object(phone_id)
                if phone:
                    # Model may be at top level of raw phone dict OR in pre_migration_state
                    model = phone.get("model")
                    if not model:
                        phone_state = phone.get("pre_migration_state") or {}
                        model = phone_state.get("model") or phone_state.get("cucm_product")
                    if _is_psk_capable_model(model):
                        has_psk_phone = True
                        break

            # Map softkeys per call state
            psk_slot_counter = 0
            psk_mappings: list[dict[str, Any]] = []
            state_key_lists: dict[str, list[str]] = {}
            unmapped: list[dict[str, Any]] = []

            for cucm_state, softkeys in call_states.items():
                psk_state = CUCM_STATE_TO_PSK_STATE.get(cucm_state)
                if psk_state is None:
                    # Unmappable state — flag all softkeys in it
                    for sk in softkeys:
                        unmapped.append({"cucm_name": sk, "call_state": cucm_state})
                    continue

                mapped_keywords = []
                for sk_name in softkeys:
                    psk_keyword = CUCM_SOFTKEY_TO_PSK.get(sk_name)
                    if psk_keyword is None and sk_name not in CUCM_SOFTKEY_TO_PSK:
                        # Unknown softkey — treat as unmapped
                        psk_keyword = None
                    if psk_keyword is None:
                        unmapped.append({"cucm_name": sk_name, "call_state": cucm_state})
                    else:
                        mapped_keywords.append(psk_keyword)
                        if has_psk_phone and psk_slot_counter < 16:
                            psk_slot_counter += 1
                            psk_mappings.append({
                                "psk_slot": f"PSK{psk_slot_counter}",
                                "keyword": psk_keyword,
                            })

                if mapped_keywords:
                    state_key_lists[psk_state] = mapped_keywords

            config = CanonicalSoftkeyConfig(
                canonical_id=f"softkey_config:{name}",
                provenance=extract_provenance(tmpl_data),
                status=MigrationStatus.ANALYZED,
                cucm_template_name=name,
                is_psk_target=has_psk_phone,
                psk_mappings=psk_mappings if has_psk_phone else [],
                state_key_lists=state_key_lists,
                unmapped_softkeys=unmapped,
                phones_using=phones_using,
            )
            store.upsert_object(config)
            result.objects_created += 1

        return result
