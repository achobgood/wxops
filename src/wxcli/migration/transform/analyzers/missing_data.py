"""Missing data analyzer for CUCM-to-Webex migration.

Sweeps the inventory for objects with null/empty required fields
and produces MISSING_DATA decisions so users can supply the data
or choose to skip the object.

MISSING_DATA is a mapper-owned decision type — multiple mappers
can produce these decisions.  This analyzer checks for existing
mapper decisions before creating new ones.

(from 03-conflict-detection-engine.md, linter pattern)
(from phase-06-analyzers.md, Decision Ownership Table — MISSING_DATA is mapper-owned)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


# ---------------------------------------------------------------------------
# Required-field definitions per object type
# ---------------------------------------------------------------------------

# Each entry: (field_name, check_fn, severity, description)
# check_fn receives the field value and returns True if the value is MISSING.

def _is_empty_list(val: Any) -> bool:
    return val is None or (isinstance(val, list) and len(val) == 0)


def _is_none(val: Any) -> bool:
    return val is None


def _is_none_or_blank(val: Any) -> bool:
    return val is None or (isinstance(val, str) and val.strip() == "")


def _get_nested(obj: dict, dotted_key: str) -> Any:
    """Retrieve a value from a dict using dot-notation (e.g., 'address.country')."""
    parts = dotted_key.split(".")
    val = obj
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
    return val


_REQUIRED_FIELDS: dict[str, list[tuple[str, Any, str, str]]] = {
    "user": [
        ("emails", _is_empty_list, "HIGH", "Email address required for Webex identity"),
        ("first_name", _is_none_or_blank, "MEDIUM", "First or last name required"),
        ("last_name", _is_none_or_blank, "MEDIUM", "First or last name required"),
        # Fix 5: location_id required for Webex Calling provisioning
        ("location_id", _is_none_or_blank, "HIGH", "Location assignment required for Webex Calling"),
    ],
    "device": [
        ("mac", _is_none_or_blank, "MEDIUM", "MAC address required for device migration"),
        ("owner_canonical_id", _is_none_or_blank, "MEDIUM", "Device owner required for assignment"),
    ],
    "trunk": [
        ("address", _is_none_or_blank, "MEDIUM", "FQDN/SRV address required for trunk registration"),
        # password NOT checked — Webex Calling trunks use certificate-based TLS,
        # not SIP password auth. CUCM never exposes passwords via AXL anyway.
    ],
    "location": [
        ("name", _is_none_or_blank, "MEDIUM", "Location name required"),
        # Fix 4: Address fields — E911 compliance
        ("address.country", _is_none_or_blank, "HIGH", "Country required for E911 compliance"),
        ("address.address1", _is_none_or_blank, "HIGH", "Street address required for E911 compliance"),
        ("address.city", _is_none_or_blank, "HIGH", "City required for E911 compliance"),
        ("address.state", _is_none_or_blank, "HIGH", "State/province required for E911 compliance"),
        ("address.postal_code", _is_none_or_blank, "MEDIUM", "Postal code required for full address"),
    ],
    # Fix 6: Translation pattern required fields
    "translation_pattern": [
        ("matching_pattern", _is_none_or_blank, "HIGH", "Pattern required for translation"),
        ("name", _is_none_or_blank, "MEDIUM", "Name required for identification"),
    ],
    # Fix 11: Route group required fields
    "route_group": [
        ("local_gateways", _is_empty_list, "HIGH", "At least one gateway required"),
    ],
    # Lines handled separately in _check_lines() — extension is only
    # required for EXTENSION-classified lines (special logic).
}


class MissingDataAnalyzer(Analyzer):
    """Finds objects where required fields are null or empty.

    For users: checks emails (HIGH — blocks identity provisioning), first_name/last_name.
    For users with name fields: only flags if BOTH first_name AND last_name are missing
    (having either one is acceptable).

    For devices: checks mac and owner_canonical_id.
    For trunks: checks address and password.
    For locations: checks name.
    For lines: checks extension (only when classification == EXTENSION).

    (from 03-conflict-detection-engine.md, MissingDataAnalyzer)
    """

    name = "missing_data"
    decision_types = [DecisionType.MISSING_DATA]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all object types for missing required fields."""
        # Collect existing mapper-produced MISSING_DATA decisions so we skip
        # objects that already have one.
        existing = self._get_existing_decisions_for_type(store, DecisionType.MISSING_DATA)

        decisions: list[Decision] = []

        for object_type, field_defs in _REQUIRED_FIELDS.items():
            objects = store.get_objects(object_type)
            for obj in objects:
                canonical_id = obj.get("canonical_id", "")

                # Skip if mapper already produced a MISSING_DATA decision
                if canonical_id in existing:
                    continue

                # Webex App devices (Jabber, CSF, Dual Mode, IP Communicator)
                # don't need a MAC address — they transition to Webex App,
                # not a physical device in Webex.
                if object_type == "device" and obj.get("compatibility_tier") == "webex_app":
                    active_fields = [
                        f for f in field_defs if f[0] != "mac"
                    ]
                else:
                    active_fields = field_defs

                missing = self._check_object(object_type, obj, active_fields)
                if not missing:
                    continue

                # Determine severity — take the highest among missing fields
                severity = self._highest_severity(missing)
                missing_names = sorted([m[0] for m in missing])

                summary = (
                    f"{object_type} '{canonical_id}' missing required fields: "
                    f"{', '.join(missing_names)}"
                )

                context = {
                    "object_type": object_type,
                    "canonical_id": canonical_id,
                    "missing_fields": missing_names,
                }

                options = [
                    DecisionOption(
                        id="provide_data",
                        label="Provide missing data",
                        impact=f"User will supply {len(missing_names)} missing field(s)",
                    ),
                    DecisionOption(
                        id="skip",
                        label="Skip this object",
                        impact=f"1 {object_type} excluded from migration",
                    ),
                    DecisionOption(
                        id="manual",
                        label="Handle manually post-migration",
                        impact=f"Object migrated without {', '.join(missing_names)}; fix manually",
                    ),
                ]

                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity=severity,
                    summary=summary,
                    context=context,
                    options=options,
                    affected_objects=[canonical_id],
                )
                decisions.append(decision)

        # Handle lines separately (extension-only check for EXTENSION lines)
        decisions.extend(self._check_lines(store, existing))

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from canonical_id + sorted missing fields."""
        return self._hash_fingerprint({
            "type": decision_type.value,
            "canonical_id": context.get("canonical_id", ""),
            "missing_fields": sorted(context.get("missing_fields", [])),
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_object(
        object_type: str,
        obj: dict[str, Any],
        field_defs: list[tuple[str, Any, str, str]],
    ) -> list[tuple[str, str, str]]:
        """Return list of (field_name, severity, description) for missing fields.

        Special case for user: first_name/last_name only flagged when BOTH missing.
        Supports dot-notation for nested fields (e.g., 'address.country').
        """
        missing: list[tuple[str, str, str]] = []

        if object_type == "user":
            # Email and location_id are always required
            for field_name, check_fn, severity, desc in field_defs:
                if field_name in ("emails", "location_id"):
                    val = _get_nested(obj, field_name) if "." in field_name else obj.get(field_name)
                    if check_fn(val):
                        missing.append((field_name, severity, desc))
            # Name: flag only if both first_name AND last_name are missing
            first = obj.get("first_name")
            last = obj.get("last_name")
            if _is_none_or_blank(first) and _is_none_or_blank(last):
                missing.append(("first_name/last_name", "MEDIUM", "First or last name required"))
        else:
            for field_name, check_fn, severity, desc in field_defs:
                # Support dot-notation for nested fields (Fix 4)
                val = _get_nested(obj, field_name) if "." in field_name else obj.get(field_name)
                if check_fn(val):
                    missing.append((field_name, severity, desc))

        return missing

    def _check_lines(
        self,
        store: MigrationStore,
        existing: dict[str, dict[str, Any]],
    ) -> list[Decision]:
        """Check lines: extension is required only for EXTENSION-classified lines."""
        decisions: list[Decision] = []
        lines = store.get_objects("line")

        for line in lines:
            canonical_id = line.get("canonical_id", "")
            if canonical_id in existing:
                continue

            classification = line.get("classification")
            extension = line.get("extension")

            # Only flag missing extension for EXTENSION-classified lines
            if classification == "EXTENSION" and _is_none_or_blank(extension):
                context = {
                    "object_type": "line",
                    "canonical_id": canonical_id,
                    "missing_fields": ["extension"],
                }
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=(
                        f"line '{canonical_id}' classified as EXTENSION but extension is empty"
                    ),
                    context=context,
                    options=[
                        DecisionOption(
                            id="provide_data",
                            label="Provide extension number",
                            impact="User will supply the extension value",
                        ),
                        DecisionOption(
                            id="skip",
                            label="Skip this line",
                            impact="1 line excluded from migration",
                        ),
                        DecisionOption(
                            id="manual",
                            label="Handle manually post-migration",
                            impact="Line migrated without extension; fix manually",
                        ),
                    ],
                    affected_objects=[canonical_id],
                )
                decisions.append(decision)

        return decisions

    @staticmethod
    def _highest_severity(missing: list[tuple[str, str, str]]) -> str:
        """Return the highest severity among the missing fields."""
        order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        best = "LOW"
        for _, sev, _ in missing:
            if order.get(sev, 0) > order.get(best, 0):
                best = sev
        return best
