"""Migration advisory system — practitioner-level recommendations.

Layer 1 (recommendation_rules): per-decision recommendations
Layer 2 (advisory_patterns + advisor): cross-cutting observations
"""
from __future__ import annotations

from typing import Any

from wxcli.migration.advisory.advisor import ArchitectureAdvisor
from wxcli.migration.advisory.recommendation_rules import RECOMMENDATION_DISPATCH
from wxcli.migration.store import MigrationStore


def populate_recommendations(store: MigrationStore) -> int:
    """Enrich all decisions in the store with recommendations.

    Iterates all decisions, calls the recommendation function for each type,
    and writes results via store.update_recommendation().

    Returns count of recommendations added.
    """
    all_decisions = store.get_all_decisions()
    count = 0
    for dec in all_decisions:
        if dec.get("chosen_option") == "__stale__":
            continue
        dec_type = dec.get("type", "")
        fn = RECOMMENDATION_DISPATCH.get(dec_type)
        if fn is None:
            continue
        context = dec.get("context", {})
        options = dec.get("options", [])
        result = fn(context, options)
        if result is not None:
            option_id, reasoning = result
            store.update_recommendation(dec["decision_id"], option_id, reasoning)
            count += 1
    return count
