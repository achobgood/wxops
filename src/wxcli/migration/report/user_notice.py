"""User communication notice generator.

Reads the post-analyze migration store, classifies each user into
communication scenarios, and assembles an HTML or plain-text notice
document. The SE customizes brand, date, and helpdesk contact via CLI flags.
"""

from __future__ import annotations

import html as html_mod
import re as re_mod
from collections import defaultdict
from dataclasses import dataclass, field

from wxcli.migration.store import MigrationStore

from wxcli.migration.report.notice_templates import (
    AUDIENCE_FILTERS,
    FOOTER_TEMPLATE,
    INTRO_TEMPLATE,
    SCENARIO_ORDER,
    SCENARIOS,
    TIMELINE_TEMPLATE,
)


@dataclass
class UserScenario:
    """A user and their applicable communication scenarios."""

    user_canonical_id: str
    display_name: str
    extension: str | None
    scenarios: list[str] = field(default_factory=list)
    device_model: str | None = None
    device_tier: str | None = None


# ---------------------------------------------------------------------------
# Scenario detection
# ---------------------------------------------------------------------------


def _build_scenario_matrix(store: MigrationStore) -> list[UserScenario]:
    """Scan store and classify each user into applicable scenarios."""
    users = store.get_objects("user")
    devices = store.get_objects("device")
    decisions = store.get_all_decisions()

    # Build lookup: owner_canonical_id -> device dict
    device_by_owner: dict[str, dict] = {}
    for d in devices:
        owner = d.get("owner_canonical_id")
        if owner:
            device_by_owner[owner] = d

    # Build lookup: user_canonical_id -> list of decisions
    decisions_by_user: dict[str, list[dict]] = defaultdict(list)
    for dec in decisions:
        ctx = dec.get("context", {})
        for key in ("user_canonical_id", "affected_user", "owner_canonical_id"):
            uid = ctx.get(key)
            if uid:
                decisions_by_user[uid].append(dec)

    # Build set of users with voicemail (via cross-ref or object field)
    vm_cross_refs = store.get_cross_refs(relationship="user_has_voicemail_profile")
    users_with_vm: set[str] = {ref["from_id"] for ref in vm_cross_refs}
    for vm in store.get_objects("voicemail_profile"):
        uid = vm.get("user_canonical_id")
        if uid:
            users_with_vm.add(uid)

    # Build set of users with unmapped layout buttons
    users_with_layout_issues: set[str] = set()
    for layout in store.get_objects("device_layout"):
        if layout.get("unmapped_buttons"):
            owner = layout.get("owner_canonical_id")
            if owner:
                users_with_layout_issues.add(owner)

    # Classify each user
    result: list[UserScenario] = []
    for user in users:
        uid = user["canonical_id"]
        scenarios: list[str] = []
        device = device_by_owner.get(uid)

        # Scenario 1: Phone upgrade (convertible)
        if device and device.get("compatibility_tier") == "convertible":
            scenarios.append("phone_upgrade")

        # Scenario 2: Webex App transition
        if device and device.get("compatibility_tier") == "webex_app":
            scenarios.append("webex_app_transition")

        # Scenario 7: Incompatible device
        if device and device.get("compatibility_tier") == "incompatible":
            scenarios.append("device_replacement")

        # Scenario 3: Call forwarding simplified
        user_decisions = decisions_by_user.get(uid, [])
        if any(d["type"] == "FORWARDING_LOSSY" for d in user_decisions):
            scenarios.append("forwarding_simplified")

        # Scenario 4: Voicemail re-record
        if uid in users_with_vm:
            scenarios.append("voicemail_rerecord")

        # Scenario 5: BLF/speed dial changes
        has_button_decision = any(
            d["type"] in ("BUTTON_UNMAPPABLE", "FEATURE_APPROXIMATION")
            and (
                "button" in d.get("summary", "").lower()
                or "blf" in d.get("summary", "").lower()
            )
            for d in user_decisions
        )
        if has_button_decision or uid in users_with_layout_issues:
            scenarios.append("layout_changes")

        # Scenario 6: Executive/assistant
        if any(
            "executive" in d.get("summary", "").lower()
            or "assistant" in d.get("summary", "").lower()
            for d in user_decisions
        ):
            scenarios.append("exec_assistant")

        # Build display_name from first_name + last_name if not set
        display_name = user.get("display_name") or ""
        if not display_name:
            parts = [user.get("first_name", ""), user.get("last_name", "")]
            display_name = " ".join(p for p in parts if p)

        result.append(UserScenario(
            user_canonical_id=uid,
            display_name=display_name,
            extension=user.get("extension"),
            scenarios=scenarios,
            device_model=device.get("model") if device else None,
            device_tier=str(device.get("compatibility_tier", "")) if device else None,
        ))

    return result


# ---------------------------------------------------------------------------
# Audience filtering
# ---------------------------------------------------------------------------


def _get_active_scenarios(matrix: list[UserScenario]) -> set[str]:
    """Return the set of scenario IDs that have at least one affected user."""
    active: set[str] = set()
    for user in matrix:
        active.update(user.scenarios)
    return active


def _filter_by_audience(
    matrix: list[UserScenario], audience: str
) -> list[UserScenario]:
    """Filter the matrix to a specific audience segment."""
    if audience == "all":
        return matrix
    if audience == "general":
        device_scenarios = {"phone_upgrade", "webex_app_transition", "device_replacement"}
        return [u for u in matrix if not (set(u.scenarios) & device_scenarios)]
    allowed = AUDIENCE_FILTERS.get(audience, set())
    if not allowed:
        return matrix
    return [u for u in matrix if set(u.scenarios) & allowed]


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def _render_intro(brand: str, migration_date: str) -> str:
    text = INTRO_TEMPLATE.format(
        brand=html_mod.escape(brand),
        migration_date=html_mod.escape(migration_date),
    )
    return f'<div class="notice-intro">\n{text}\n</div>'


def _render_scenario(
    scenario_id: str,
    affected_count: int,
    brand: str,
    helpdesk: str,
) -> str:
    scenario = SCENARIOS[scenario_id]
    title = html_mod.escape(scenario["title"])
    variables: dict[str, str] = {
        "brand": html_mod.escape(brand),
        "helpdesk": html_mod.escape(helpdesk),
        "cucm_model": "",
        "extension": "",
    }
    body = scenario["template"].format_map(variables)
    count_label = f"Applies to {affected_count} user{'s' if affected_count != 1 else ''}"
    return (
        f'<div class="scenario-section">\n'
        f"<h3>{title}</h3>\n"
        f'<p class="affected-count">{count_label}</p>\n'
        f"<p>{body}</p>\n"
        f"</div>"
    )


def _render_timeline(migration_date: str, helpdesk: str) -> str:
    text = TIMELINE_TEMPLATE.format(
        migration_date=html_mod.escape(migration_date),
        helpdesk=html_mod.escape(helpdesk),
    )
    return f'<div class="notice-timeline">\n<h2>Migration Day Timeline</h2>\n{text}\n</div>'


def _render_footer(helpdesk: str, prepared_by: str, brand: str) -> str:
    text = FOOTER_TEMPLATE.format(
        helpdesk=html_mod.escape(helpdesk),
        prepared_by=html_mod.escape(prepared_by) if prepared_by else "",
        brand=html_mod.escape(brand),
    )
    return f'<div class="notice-footer">\n{text}\n</div>'


NOTICE_CSS: str = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    color: #1a1f25;
    background: #ffffff;
    margin: 0;
    padding: 0;
}
.notice-container {
    max-width: 640px;
    margin: 0 auto;
    padding: 32px 24px;
}
.notice-intro {
    margin-bottom: 24px;
}
.notice-intro strong:first-child {
    font-size: 1.4em;
    display: block;
    margin-bottom: 12px;
    color: #242a33;
}
.scenario-section {
    border-left: 4px solid #00897B;
    background: #f8faf9;
    padding: 16px 20px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
}
.scenario-section h3 {
    margin-top: 0;
    color: #242a33;
}
.affected-count {
    font-size: 0.85em;
    color: #636e7e;
    margin-top: -8px;
    margin-bottom: 8px;
}
.notice-timeline {
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid #e0e0e0;
}
.notice-timeline h2 {
    color: #242a33;
    margin-top: 0;
}
.notice-footer {
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid #e0e0e0;
    font-size: 0.95em;
}
h2 { font-size: 1.25em; }
h3 { font-size: 1.1em; }
ul, ol { padding-left: 24px; }
a { color: #00897B; }
"""


# ---------------------------------------------------------------------------
# Plain text rendering
# ---------------------------------------------------------------------------


def _strip_html(html_text: str) -> str:
    """Convert HTML fragment to plain text."""
    text = html_text
    text = re_mod.sub(r"<strong>(.*?)</strong>", r"**\1**", text)
    text = re_mod.sub(r"<em>(.*?)</em>", r"_\1_", text)
    text = re_mod.sub(r"<li>(.*?)</li>", r"  - \1", text)
    text = re_mod.sub(r'<a href="([^"]*)">(.*?)</a>', r"\2 (\1)", text)
    text = re_mod.sub(r"<[^>]+>", "", text)
    text = re_mod.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _render_plain_intro(brand: str, migration_date: str) -> str:
    text = INTRO_TEMPLATE.format(brand=brand, migration_date=migration_date)
    return _strip_html(text)


def _render_plain_scenario(
    scenario_id: str,
    affected_count: int,
    brand: str,
    helpdesk: str,
) -> str:
    scenario = SCENARIOS[scenario_id]
    title = scenario["title"]
    variables: dict[str, str] = {
        "brand": brand,
        "helpdesk": helpdesk,
        "cucm_model": "",
        "extension": "",
    }
    body = _strip_html(scenario["template"].format_map(variables))
    count_label = f"Applies to {affected_count} user{'s' if affected_count != 1 else ''}"
    underline = "-" * len(title)
    return f"{title}\n{underline}\n{count_label}\n\n{body}"


def _render_plain_timeline(migration_date: str, helpdesk: str) -> str:
    text = _strip_html(
        TIMELINE_TEMPLATE.format(migration_date=migration_date, helpdesk=helpdesk)
    )
    title = "Migration Day Timeline"
    return f"{title}\n{'=' * len(title)}\n\n{text}"


def _render_plain_footer(helpdesk: str, prepared_by: str, brand: str) -> str:
    return _strip_html(
        FOOTER_TEMPLATE.format(
            helpdesk=helpdesk, prepared_by=prepared_by or "", brand=brand
        )
    )


def _assemble_plain_text(
    matrix: list[UserScenario],
    active_scenarios: set[str],
    brand: str,
    migration_date: str,
    helpdesk: str,
    prepared_by: str,
) -> str:
    sections: list[str] = [_render_plain_intro(brand, migration_date)]
    for scenario_id in SCENARIO_ORDER:
        if scenario_id in active_scenarios:
            affected_count = sum(1 for u in matrix if scenario_id in u.scenarios)
            sections.append(
                _render_plain_scenario(scenario_id, affected_count, brand, helpdesk)
            )
    sections.append(_render_plain_timeline(migration_date, helpdesk))
    sections.append(_render_plain_footer(helpdesk, prepared_by, brand))
    return "\n\n\n".join(sections)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_user_notice(
    store: MigrationStore,
    brand: str,
    migration_date: str,
    helpdesk: str,
    prepared_by: str = "",
    audience: str = "all",
    text_only: bool = False,
) -> str:
    """Generate user-facing migration communication document."""
    matrix = _build_scenario_matrix(store)

    if audience != "all":
        matrix = _filter_by_audience(matrix, audience)

    active_scenarios = _get_active_scenarios(matrix)

    if text_only:
        return _assemble_plain_text(
            matrix, active_scenarios, brand, migration_date, helpdesk, prepared_by
        )

    # Assemble HTML
    sections: list[str] = [_render_intro(brand, migration_date)]
    for scenario_id in SCENARIO_ORDER:
        if scenario_id in active_scenarios:
            affected_count = sum(1 for u in matrix if scenario_id in u.scenarios)
            sections.append(
                _render_scenario(scenario_id, affected_count, brand, helpdesk)
            )
    sections.append(_render_timeline(migration_date, helpdesk))
    sections.append(_render_footer(helpdesk, prepared_by, brand))

    body = "\n\n".join(sections)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>Migration Notice \u2014 {html_mod.escape(brand)}</title>\n"
        f"<style>\n{NOTICE_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="notice-container">\n'
        f"{body}\n"
        "</div>\n"
        "</body>\n"
        "</html>"
    )
