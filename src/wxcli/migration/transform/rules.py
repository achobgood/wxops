"""Auto-resolution rules engine for migration decisions.

Applies configurable rules to automatically resolve pending decisions
without requiring manual user input.  Rules are driven by the config
dict passed to apply_auto_rules().

(from 03-conflict-detection-engine.md, Auto-Resolution Rules)
(from 03b-transform-mappers.md section 13, TransformEngine integration)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.store import MigrationStore

logger = logging.getLogger(__name__)


def _match_rule(rule: dict[str, Any], decision: dict[str, Any]) -> bool:
    """Check if a rule's ``match`` field matches a decision's context.

    Supports declarative matching only — no eval/exec.

    Match field format (from 03-conflict-detection-engine.md, Auto-Resolution Rules):
    - Plain key: exact match, or membership if value is a list
      ``{"cucm_model": ["7841", "7861"]}`` → context["cucm_model"] in list
    - ``_lte`` suffix: less-than-or-equal comparison
      ``{"dn_length_lte": 4}`` → context["dn_length"] <= 4
    - ``_gte`` suffix: greater-than-or-equal comparison
    - ``_contains`` suffix: substring match
      ``{"name_contains": "lobby"}`` → "lobby" in context["name"]

    All match fields use AND logic — every field must match.
    If a match key is not present in the decision's context, the rule is skipped.
    Non-numeric context values with _lte/_gte operators are skipped (no crash).
    """
    match = rule.get("match")
    if not match or not isinstance(match, dict):
        return True  # No match field → type-only rule, always matches

    context = decision.get("context", {})

    for key, expected in match.items():
        # Determine operator suffix
        if key.endswith("_lte"):
            base_key = key[:-4]
            actual = context.get(base_key)
            if actual is None:
                return False
            try:
                if float(actual) > float(expected):
                    return False
            except (ValueError, TypeError):
                return False  # Non-numeric → skip gracefully

        elif key.endswith("_gte"):
            base_key = key[:-4]
            actual = context.get(base_key)
            if actual is None:
                return False
            try:
                if float(actual) < float(expected):
                    return False
            except (ValueError, TypeError):
                return False

        elif key.endswith("_contains"):
            base_key = key[:-9]
            actual = context.get(base_key)
            if actual is None:
                return False
            if not isinstance(actual, str) or not isinstance(expected, str):
                return False
            if expected not in actual:
                return False

        else:
            # Plain key: exact match or list membership
            actual = context.get(key)
            if actual is None:
                return False
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False

    return True


def apply_auto_rules(store: MigrationStore, config: dict[str, Any]) -> int:
    """Apply auto-resolution rules from config to pending decisions.

    Config format (from 03-conflict-detection-engine.md, Auto-Resolution Rules):
    {"auto_rules": [
        {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
        {"type": "DEVICE_FIRMWARE_CONVERTIBLE",
         "match": {"cucm_model": ["7841", "7861"]},
         "choice": "convert"},
        {"type": "DN_AMBIGUOUS",
         "match": {"dn_length_lte": 4},
         "choice": "extension_only"},
    ]}

    Match field supports:
    - Plain values: exact match (``context[key] == value``)
    - List values: membership (``context[key] in value``)
    - ``_lte`` suffix: less-than-or-equal
    - ``_gte`` suffix: greater-than-or-equal
    - ``_contains`` suffix: substring match
    - Multiple match fields: AND logic (all must match)
    - Missing context key: rule skipped (no crash)

    Only applies to pending (unresolved) decisions — those with
    chosen_option == None.

    Each resolved decision gets:
        chosen_option = <choice from rule>
        resolved_by   = "auto_rule"
        resolved_at   = current UTC timestamp

    Returns count of decisions auto-resolved.

    (from 03-conflict-detection-engine.md, Auto-Resolution Rules)
    """
    rules = config.get("auto_rules", [])
    if not rules:
        return 0

    # Validate rules: each must have type and choice
    valid_rules: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("type") and rule.get("choice"):
            valid_rules.append(rule)

    if not valid_rules:
        return 0

    # Fetch all decisions, apply rules to unresolved ones
    all_decisions = store.get_all_decisions()
    resolved_count = 0

    for dec in all_decisions:
        # Skip already-resolved decisions
        if dec.get("chosen_option") is not None:
            continue

        dec_type = dec.get("type", "")

        # Try each rule in order (first match wins)
        for rule in valid_rules:
            if rule["type"] != dec_type:
                continue

            # Check match field against decision context
            if not _match_rule(rule, dec):
                continue

            choice = rule["choice"]
            decision_id = dec["decision_id"]

            # Validate that the choice matches a valid option ID
            options = dec.get("options", [])
            valid_ids = {opt["id"] for opt in options if isinstance(opt, dict)}

            if valid_ids and choice not in valid_ids:
                logger.warning(
                    "Auto-rule choice '%s' for decision %s (type=%s) "
                    "is not a valid option. Valid: %s. Skipping.",
                    choice,
                    decision_id,
                    dec_type,
                    valid_ids,
                )
                continue

            store.resolve_decision(
                decision_id=decision_id,
                chosen_option=choice,
                resolved_by="auto_rule",
            )
            resolved_count += 1
            logger.debug(
                "Auto-resolved decision %s (type=%s) with choice='%s'",
                decision_id,
                dec_type,
                choice,
            )
            break  # First matching rule wins for this decision

    logger.info("Auto-rules resolved %d decision(s)", resolved_count)
    return resolved_count
