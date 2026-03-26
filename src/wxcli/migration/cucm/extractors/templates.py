"""Template extractor — phone button templates and softkey templates.

Phone button templates use two-step AXL extraction (list → get-detail).
Softkey templates use SQL queries (AXL list/get operations don't exist in v15.0).

Templates are shared objects — typically 5-20 button templates and
3-10 softkey templates per cluster.

AXL gotchas (verified 2026-03-25 against CUCM 15.0):
- listPhoneButtonTemplate returnedTags only supports {name, isUserModifiable},
  NOT basePhoneTemplateName.
- getPhoneButtonTemplate returns buttons with <buttonNumber> (not <index>),
  and "Speed Dial BLF" as the feature name (not "Busy Lamp Field" as in add).
- addSoftkeyTemplate, getSoftkeyTemplate, listSoftkeyTemplate DO NOT EXIST.
  Softkey templates must be queried via executeSQLQuery on the softkeytemplate
  table, with typesoftkey for ID-to-name decoding.

Sources:
- tier2-phase2-phone-config-design.md §1.1, §13.1, §13.2
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value

logger = logging.getLogger(__name__)

# listPhoneButtonTemplate only supports these returnedTags (verified 2026-03-25)
BUTTON_TEMPLATE_LIST_TAGS = {"name": "", "isUserModifiable": ""}


# Softkey ID → name mapping, populated once from typesoftkey SQL table
_SOFTKEY_ID_CACHE: dict[str, str] = {}

# softkeysetclause state positions (verified 2026-03-25, CUCM 15.0)
# Semicolon-delimited, 12 states in fixed order:
SOFTKEY_STATE_ORDER = [
    "On Hook",
    "Connected",
    "On Hold",
    "Ring In",
    "Off Hook",
    "Connected Transfer",
    "Transition",
    "Connected Conference",
    "Park",
    "Alerting",
    "Shared Active",
    "Shared Held",
]


class TemplateExtractor(BaseExtractor):
    """Extract phone button templates and softkey templates from CUCM."""

    name = "templates"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run extraction for button templates (AXL) and softkey templates (SQL)."""
        result = ExtractionResult(extractor=self.name)

        button_templates = self._extract_button_templates(result)
        softkey_templates = self._extract_softkey_templates(result)

        self.results["button_templates"] = button_templates
        self.results["softkey_templates"] = softkey_templates

        logger.info(
            "[%s] Extracted %d button templates, %d softkey templates (%d failed)",
            self.name, len(button_templates), len(softkey_templates), result.failed,
        )
        return result

    # ------------------------------------------------------------------
    # Phone button templates — AXL list + get-detail
    # ------------------------------------------------------------------

    def _extract_button_templates(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """List and get-detail all phone button templates."""
        logger.info("[%s] Listing phone button templates...", self.name)
        try:
            summaries = self.paginated_list(
                method_name="listPhoneButtonTemplate",
                search_criteria={"name": "%"},
                returned_tags=BUTTON_TEMPLATE_LIST_TAGS,
            )
        except Exception as exc:
            logger.warning("[%s] listPhoneButtonTemplate failed: %s", self.name, exc)
            result.errors.append(f"listPhoneButtonTemplate failed: {exc}")
            return []

        result.total += len(summaries)

        templates: list[dict[str, Any]] = []
        for summary in summaries:
            name = ref_value(summary.get("name")) or summary.get("name")
            if not name:
                result.failed += 1
                result.errors.append("Button template with no name")
                continue

            try:
                detail = self.get_detail("getPhoneButtonTemplate", name=name)
            except Exception as exc:
                logger.warning("[%s] getPhoneButtonTemplate(%s) failed: %s", self.name, name, exc)
                result.failed += 1
                result.errors.append(f"getPhoneButtonTemplate failed for {name}")
                continue

            if detail is None:
                result.failed += 1
                result.errors.append(f"getPhoneButtonTemplate returned None for {name}")
                continue

            templates.append(detail)

        return templates

    # ------------------------------------------------------------------
    # Softkey templates — SQL queries (AXL operations don't exist)
    # ------------------------------------------------------------------

    def _extract_softkey_templates(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract softkey templates via SQL (AXL list/get don't exist in v15.0)."""
        logger.info("[%s] Querying softkey templates via SQL...", self.name)

        # Load softkey ID → name mapping
        softkey_names = self._load_softkey_type_names()

        try:
            rows = self.conn.execute_sql(
                "SELECT name, description, softkeyclause, softkeysetclause, "
                "iksoftkeytemplate_base FROM softkeytemplate ORDER BY name"
            )
        except Exception as exc:
            logger.warning("[%s] Softkey template SQL query failed: %s", self.name, exc)
            result.errors.append(f"Softkey template SQL failed: {exc}")
            return []

        result.total += len(rows)
        templates: list[dict[str, Any]] = []

        for row in rows:
            name = row.get("name")
            if not name:
                result.failed += 1
                continue

            try:
                parsed = self._parse_softkey_template(row, softkey_names)
                templates.append(parsed)
            except Exception as exc:
                logger.warning("[%s] Failed to parse softkey template %s: %s", self.name, name, exc)
                result.failed += 1
                result.errors.append(f"Parse failed for softkey template {name}: {exc}")

        return templates

    def _load_softkey_type_names(self) -> dict[str, str]:
        """Load typesoftkey enum → name mapping from CUCM DB."""
        if _SOFTKEY_ID_CACHE:
            return _SOFTKEY_ID_CACHE

        try:
            rows = self.conn.execute_sql(
                "SELECT enum, name FROM typesoftkey ORDER BY enum"
            )
            for row in rows:
                enum_val = str(row.get("enum", ""))
                sk_name = row.get("name", "")
                if enum_val and sk_name:
                    _SOFTKEY_ID_CACHE[enum_val] = sk_name
        except Exception as exc:
            logger.warning("[%s] typesoftkey query failed: %s", self.name, exc)

        return _SOFTKEY_ID_CACHE

    def _parse_softkey_template(
        self, row: dict[str, Any], softkey_names: dict[str, str]
    ) -> dict[str, Any]:
        """Parse a softkeytemplate SQL row into a structured dict.

        Decodes softkeyclause and softkeysetclause into human-readable form.
        """
        name = row.get("name", "")
        description = row.get("description", "")
        base_pkid = row.get("iksoftkeytemplate_base", "")

        # Decode softkeyclause: "0:1:2:3:4" → ["Undefined", "Redial", "NewCall", ...]
        softkey_clause = row.get("softkeyclause", "")
        available_softkeys: list[str] = []
        if softkey_clause:
            for sk_id in softkey_clause.split(":"):
                sk_name = softkey_names.get(sk_id, f"unknown_{sk_id}")
                available_softkeys.append(sk_name)

        # Decode softkeysetclause: semicolon-separated per-state lists
        # Each state: colon-separated softkey IDs
        softkey_set_clause = row.get("softkeysetclause", "")
        call_states: dict[str, list[str]] = {}
        if softkey_set_clause:
            state_parts = softkey_set_clause.split(";")
            for i, state_data in enumerate(state_parts):
                if i >= len(SOFTKEY_STATE_ORDER):
                    break
                state_name = SOFTKEY_STATE_ORDER[i]
                keys: list[str] = []
                if state_data:
                    for sk_id in state_data.split(":"):
                        sk_name = softkey_names.get(sk_id, f"unknown_{sk_id}")
                        keys.append(sk_name)
                call_states[state_name] = keys

        return {
            "name": name,
            "description": description,
            "base_template_pkid": base_pkid,
            "available_softkeys": available_softkeys,
            "call_states": call_states,
        }
