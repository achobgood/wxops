"""Template extractor — phone button templates and softkey templates.

Two-step extraction for each type: list discovers, get fetches detail.
Templates are shared objects — typically 5-20 button templates and
3-10 softkey templates per cluster.

Sources:
- tier2-phase2-phone-config-design.md §1.1
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value

logger = logging.getLogger(__name__)

BUTTON_TEMPLATE_LIST_TAGS = {"name": "", "basePhoneTemplateName": ""}

BUTTON_TEMPLATE_GET_TAGS = {
    "name": "", "basePhoneTemplateName": "", "buttons": "",
}

SOFTKEY_TEMPLATE_LIST_TAGS = {"name": "", "description": ""}

SOFTKEY_TEMPLATE_GET_TAGS = {
    "name": "", "description": "", "defaultSoftkeyTemplateName": "",
}


class TemplateExtractor(BaseExtractor):
    """Extract phone button templates and softkey templates from CUCM."""

    name = "templates"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run two-step extraction for button and softkey templates."""
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

    def _extract_button_templates(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """List and get-detail all phone button templates."""
        logger.info("[%s] Listing phone button templates...", self.name)
        summaries = self.paginated_list(
            method_name="listPhoneButtonTemplate",
            search_criteria={"name": "%"},
            returned_tags=BUTTON_TEMPLATE_LIST_TAGS,
        )
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

    def _extract_softkey_templates(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """List and get-detail all softkey templates."""
        logger.info("[%s] Listing softkey templates...", self.name)
        summaries = self.paginated_list(
            method_name="listSoftkeyTemplate",
            search_criteria={"name": "%"},
            returned_tags=SOFTKEY_TEMPLATE_LIST_TAGS,
        )
        result.total += len(summaries)

        templates: list[dict[str, Any]] = []
        for summary in summaries:
            name = ref_value(summary.get("name")) or summary.get("name")
            if not name:
                result.failed += 1
                result.errors.append("Softkey template with no name")
                continue

            try:
                detail = self.get_detail("getSoftkeyTemplate", name=name)
            except Exception as exc:
                logger.warning("[%s] getSoftkeyTemplate(%s) failed: %s", self.name, name, exc)
                result.failed += 1
                result.errors.append(f"getSoftkeyTemplate failed for {name}")
                continue

            if detail is None:
                result.failed += 1
                result.errors.append(f"getSoftkeyTemplate returned None for {name}")
                continue

            templates.append(detail)

        return templates
