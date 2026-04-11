"""Maps CUCM executive/assistant pairings to Webex Executive/Assistant config.

Reads normalized exec_asst_pair objects from the store, groups by executive,
resolves assistant user canonical_ids, and produces CanonicalExecutiveAssistant
objects. Generates MISSING_DATA decisions when one side of a pair is not in
migration scope.

(from executive-assistant-migration spec §4c)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from wxcli.migration.models import (
    CanonicalExecutiveAssistant,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    decision_to_store_dict,
    extract_provenance,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)


class ExecutiveAssistantMapper(Mapper):
    """Maps CUCM executive/assistant pairs to Webex config objects."""

    name = "executive_assistant_mapper"
    depends_on = ["user_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Group pairs by executive userid
        pairs_by_exec: dict[str, list[str]] = defaultdict(list)
        for pair_data in store.get_objects("exec_asst_pair"):
            state = pair_data.get("pre_migration_state") or {}
            exec_userid = state.get("executive_userid")
            asst_userid = state.get("assistant_userid")
            if exec_userid and asst_userid:
                pairs_by_exec[exec_userid].append(asst_userid)

        if not pairs_by_exec:
            return result

        # Build settings lookup
        settings_by_userid: dict[str, dict[str, Any]] = {}
        for setting_data in store.get_objects("exec_setting"):
            state = setting_data.get("pre_migration_state") or {}
            userid = state.get("userid")
            if userid:
                settings_by_userid[userid] = state

        # Process each executive
        for exec_userid, asst_userids in pairs_by_exec.items():
            exec_canonical_id = f"user:{exec_userid}"

            # Verify executive exists in store
            exec_obj = store.get_object(exec_canonical_id)
            if exec_obj is None:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="HIGH",
                    summary=(
                        f"Executive '{exec_userid}' not in migration scope \u2014 "
                        f"{len(asst_userids)} assistant pairing(s) cannot be migrated"
                    ),
                    context={
                        "missing_reason": "executive_assistant_broken_pair",
                        "missing_side": "executive",
                        "executive_userid": exec_userid,
                        "assistant_userids": asst_userids,
                    },
                    options=[
                        manual_option(
                            "Configure executive/assistant manually in Webex after migration"
                        ),
                        skip_option("Executive/assistant pairing not migrated"),
                    ],
                    affected_objects=[exec_canonical_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                continue

            # Verify each assistant exists
            valid_assistants: list[str] = []
            for asst_userid in asst_userids:
                asst_canonical_id = f"user:{asst_userid}"
                asst_obj = store.get_object(asst_canonical_id)
                if asst_obj is None:
                    decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.MISSING_DATA,
                        severity="HIGH",
                        summary=(
                            f"Assistant '{asst_userid}' for executive '{exec_userid}' "
                            f"not in migration scope"
                        ),
                        context={
                            "missing_reason": "executive_assistant_broken_pair",
                            "missing_side": "assistant",
                            "executive_userid": exec_userid,
                            "assistant_userid": asst_userid,
                        },
                        options=[
                            manual_option(
                                "Configure assistant manually in Webex after migration"
                            ),
                            skip_option("This assistant pairing not migrated"),
                        ],
                        affected_objects=[exec_canonical_id, asst_canonical_id],
                    )
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)
                else:
                    valid_assistants.append(asst_canonical_id)

            if not valid_assistants:
                continue

            # Read executive settings
            exec_settings = settings_by_userid.get(exec_userid, {})

            ea_obj = CanonicalExecutiveAssistant(
                canonical_id=f"executive_assistant:{exec_userid}",
                provenance=extract_provenance(exec_obj),
                status=MigrationStatus.ANALYZED,
                executive_canonical_id=exec_canonical_id,
                assistant_canonical_ids=valid_assistants,
                alerting_mode=exec_settings.get("alerting_mode", "SIMULTANEOUS"),
                filter_enabled=bool(exec_settings.get("filter_enabled", False)),
                filter_type=exec_settings.get("filter_type", "ALL_CALLS"),
                screening_enabled=bool(exec_settings.get("screening_enabled", False)),
            )

            store.upsert_object(ea_obj)
            result.objects_created += 1

            store.add_cross_ref(
                exec_canonical_id,
                ea_obj.canonical_id,
                "user_has_executive_assistant_config",
            )

        return result
