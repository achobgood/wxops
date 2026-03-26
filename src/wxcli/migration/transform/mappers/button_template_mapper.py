"""ButtonTemplateMapper: CUCM Phone Button Templates -> Webex Line Key Templates.

Maps CUCM button feature types to Webex LineKeyType values. Determines KEM
boundaries from model-specific line key counts. Produces CanonicalLineKeyTemplate
objects and BUTTON_UNMAPPABLE decisions for unmappable buttons.

(from tier2-phase2-phone-config-design.md S4.1)

Cross-ref reads:
    phone_uses_button_template  (Phone -> ButtonTemplate)  -- usage count
"""
from __future__ import annotations

import logging
import re
from typing import Any

from wxcli.migration.models import (
    CanonicalLineKeyTemplate,
    DecisionOption,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    decision_to_store_dict,
    extract_provenance,
    skip_option,
)

logger = logging.getLogger(__name__)

# CUCM button feature -> Webex LineKeyType
CUCM_BUTTON_TO_WEBEX: dict[str, str | None] = {
    "Line": "PRIMARY_LINE",
    "Speed Dial": "SPEED_DIAL",
    "Busy Lamp Field": "MONITOR",
    "Call Park": "CALL_PARK_EXTENSION",
    "Abbreviated Dial": "SPEED_DIAL",
    "None": "OPEN",
    "Unassigned": "OPEN",
    # Unmappable -- return None
    "Intercom": None,
    "Service URL": None,
    "Privacy": None,
    "Malicious Call ID": None,
    "Quality Report Tool": None,
    "Do Not Disturb": None,
    "Feature": None,
}

# Max line key count per phone model (buttons beyond this are KEM keys)
_MODEL_LINE_KEY_COUNTS: dict[str, int] = {
    "7821": 2, "7841": 4, "7861": 16,
    "8811": 10, "8832": 0, "8841": 10, "8845": 10, "8851": 10, "8861": 10, "8865": 10,
    "8875": 10,
    "9811": 2, "9821": 2, "9841": 4, "9851": 10, "9861": 16, "9871": 32,
    "6821": 2, "6841": 4, "6851": 12, "6861": 16, "6871": 10,
}

# Regex to extract 4-digit model number from base template name
_MODEL_RE = re.compile(r"(\d{4})")


def _parse_model_from_base_template(base_template: str | None) -> str | None:
    """Extract the 4-digit phone model from a CUCM base template name.

    E.g. "Standard 8845" -> "8845", "Universal Phone Template" -> None
    """
    if not base_template:
        return None
    match = _MODEL_RE.search(base_template)
    return match.group(1) if match else None


class ButtonTemplateMapper(Mapper):
    """Maps CUCM Phone Button Templates to Webex Line Key Templates."""

    name = "button_template_mapper"
    depends_on = ["device_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        for tmpl_data in store.get_objects("button_template"):
            tmpl_id = tmpl_data["canonical_id"]
            state = tmpl_data.get("pre_migration_state") or {}
            name = state.get("name", tmpl_id.split(":", 1)[-1])
            base_template = state.get("base_template")
            buttons = state.get("buttons", [])

            # Count phones using this template
            phone_refs = [
                r["from_id"]
                for r in store.get_cross_refs(
                    to_id=tmpl_id, relationship="phone_uses_button_template"
                )
            ]
            phones_using = len(phone_refs)

            # Determine model and max line keys
            model_num = (
                _parse_model_from_base_template(base_template)
                or _parse_model_from_base_template(name)
            )
            max_keys = _MODEL_LINE_KEY_COUNTS.get(model_num, 999)

            line_keys: list[dict[str, Any]] = []
            kem_keys: list[dict[str, Any]] = []
            unmapped: list[dict[str, Any]] = []

            for btn in buttons:
                idx = btn.get("index", 0)
                feature = btn.get("feature", "")
                webex_type = CUCM_BUTTON_TO_WEBEX.get(feature)

                if webex_type is None and feature:
                    # Unknown or unmappable feature
                    unmapped.append({"index": idx, "feature": feature})
                    continue

                if not webex_type:
                    webex_type = "OPEN"

                entry = {"index": idx, "key_type": webex_type}

                if idx <= max_keys:
                    line_keys.append(entry)
                else:
                    kem_keys.append(entry)

            # Determine KEM module type from key count
            kem_module_type = None
            if kem_keys:
                kem_count = len(kem_keys)
                if kem_count <= 14:
                    kem_module_type = "KEM_14_KEYS"
                elif kem_count <= 18:
                    kem_module_type = "KEM_18_KEYS"
                else:
                    kem_module_type = "KEM_20_KEYS"

            lkt = CanonicalLineKeyTemplate(
                canonical_id=f"line_key_template:{name}",
                provenance=extract_provenance(tmpl_data),
                status=MigrationStatus.ANALYZED,
                name=name,
                cucm_template_name=name,
                device_model=f"DMS Cisco {model_num}" if model_num else None,
                line_keys=line_keys,
                kem_module_type=kem_module_type,
                kem_keys=kem_keys,
                unmapped_buttons=unmapped,
                phones_using=phones_using,
            )
            store.upsert_object(lkt)
            result.objects_created += 1

            # Decision for unmappable buttons (only if phones use this template)
            if unmapped and phones_using > 0:
                features = list({u["feature"] for u in unmapped})
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.BUTTON_UNMAPPABLE,
                    severity="LOW",
                    summary=(
                        f"Template '{name}' has {len(unmapped)} button(s) with no Webex "
                        f"equivalent: {', '.join(features)} ({phones_using} phones affected)"
                    ),
                    context={
                        "template_name": name,
                        "unmapped_features": features,
                        "phones_using": phones_using,
                    },
                    options=[
                        DecisionOption(
                            id="accept_loss",
                            label="Accept loss",
                            impact="Accept -- these button types don't exist in Webex",
                        ),
                        skip_option("Skip template migration for these phones"),
                    ],
                    affected_objects=[lkt.canonical_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

        return result
