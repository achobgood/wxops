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


def _synthesized_reason(dec_type: str, choice: str) -> str:
    """Default reason when a rule has no explicit `reason` field."""
    return f"Auto-rule: {dec_type} → {choice}"


def _resolve_reason(rule: dict[str, Any], dec_type: str, choice: str) -> str:
    """Pick the reason string for a matched rule.

    Prefer rule['reason'] if it is a non-empty string. Otherwise (missing,
    None, empty, or non-string), fall back to the synthesized form and
    log a warning for the non-string case.
    """
    raw = rule.get("reason")
    if isinstance(raw, str) and raw:
        return raw
    if raw is not None and not isinstance(raw, str):
        logger.warning(
            "auto-rule reason field is not a string (got %r), using synthesized reason",
            type(raw).__name__,
        )
    return _synthesized_reason(dec_type, choice)


def _iter_matching_resolutions(
    store: MigrationStore,
    config: dict[str, Any],
):
    """Yield ``(decision, choice, reason)`` for every pending decision that
    a config rule would resolve. Pure read — does NOT mutate the store.

    Both ``apply_auto_rules`` and ``preview_auto_rules`` consume this
    generator so they cannot drift on matcher semantics.

    Walks the same rules in the same order as the pre-refactor
    ``apply_auto_rules`` (first-match-wins within a decision type). Skips:
    - already-resolved decisions (``chosen_option is not None``)
    - malformed rules (missing type or choice)
    - rules whose match clause fails
    - rules whose ``choice`` is not in the decision's ``options`` list
      (option-validation parity with ``apply_auto_rules``)
    """
    rules = config.get("auto_rules", [])
    if not rules:
        return

    valid_rules: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("type") and rule.get("choice"):
            valid_rules.append(rule)
        else:
            # Surface config typos — a rule missing `type` or `choice` is
            # almost always a typo (e.g., "tpe" or missing quotes). Without
            # this warning, operators see zero auto-applies with no signal
            # about why. The warning includes the rule dict so they can
            # grep config.json for the bad entry.
            logger.warning(
                "Auto-rule missing 'type' or 'choice' — skipping: %r",
                rule,
            )

    if not valid_rules:
        return

    all_decisions = store.get_all_decisions()

    for dec in all_decisions:
        if dec.get("chosen_option") is not None:
            continue

        dec_type = dec.get("type", "")

        for rule in valid_rules:
            if rule["type"] != dec_type:
                continue
            if not _match_rule(rule, dec):
                continue

            choice = rule["choice"]

            # Option-validation parity with apply_auto_rules.
            options = dec.get("options", [])
            valid_ids = {opt["id"] for opt in options if isinstance(opt, dict)}
            if valid_ids and choice not in valid_ids:
                logger.warning(
                    "Auto-rule choice '%s' for decision %s (type=%s) "
                    "is not a valid option. Valid: %s. Skipping.",
                    choice,
                    dec.get("decision_id", ""),
                    dec_type,
                    valid_ids,
                )
                continue

            reason = _resolve_reason(rule, dec_type, choice)
            yield dec, choice, reason
            break  # First matching rule wins for this decision


def preview_auto_rules(
    store: MigrationStore,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the list of pending decisions that current config rules would
    resolve, each augmented with ``auto_choice`` and ``auto_reason`` keys.

    Pure read: does NOT mutate the store. Used by ``classify_decisions``
    and the CLI preview path in ``wxcli cucm decide --apply-auto``.
    """
    result: list[dict[str, Any]] = []
    for dec, choice, reason in _iter_matching_resolutions(store, config):
        d = dict(dec)
        d["auto_choice"] = choice
        d["auto_reason"] = reason
        result.append(d)
    return result


def apply_auto_rules(store: MigrationStore, config: dict[str, Any]) -> int:
    """Apply auto-resolution rules from config to pending decisions.

    Consumes ``_iter_matching_resolutions`` so apply and preview cannot
    drift on matcher semantics.

    Config format (from 03-conflict-detection-engine.md, Auto-Resolution Rules)::

        {"auto_rules": [
            {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            {"type": "DEVICE_FIRMWARE_CONVERTIBLE",
             "match": {"cucm_model": ["7841", "7861"]},
             "choice": "convert",
             "reason": "Optional human-readable reason"},
            {"type": "DN_AMBIGUOUS",
             "match": {"dn_length_lte": 4},
             "choice": "extension_only"},
        ]}

    Match field supports plain values (exact/list membership), ``_lte``/
    ``_gte``/``_contains`` suffixes, and AND logic across multiple fields.

    Each resolved decision gets::

        chosen_option = <choice from rule>
        resolved_by   = "auto_rule"
        resolved_at   = current UTC timestamp

    Returns count of decisions auto-resolved.

    (from 03-conflict-detection-engine.md, Auto-Resolution Rules)
    """
    resolved_count = 0
    for dec, choice, _reason in _iter_matching_resolutions(store, config):
        store.resolve_decision(
            decision_id=dec["decision_id"],
            chosen_option=choice,
            resolved_by="auto_rule",
        )
        resolved_count += 1
        logger.debug(
            "Auto-resolved decision %s (type=%s) with choice='%s'",
            dec.get("decision_id", ""),
            dec.get("type", ""),
            choice,
        )

    logger.info("Auto-rules resolved %d decision(s)", resolved_count)
    return resolved_count
