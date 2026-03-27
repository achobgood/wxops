"""Preflight check functions for CUCM-to-Webex migration.

Each check reads planned resources from the store and compares them against
live Webex org state queried via wxcli CLI commands (subprocess).

(from 05a-preflight-checks.md — 7 checks + DUPLICATE_USER detection)
(from phase-10-preflight.md — adapted to use wxcli commands)
"""

from __future__ import annotations

import json
from typing import Any

from wxcli.migration.models import DecisionType
from wxcli.migration.preflight import (
    CheckResult,
    CheckStatus,
    PreflightError,
    PreflightIssue,
    _run_wxcli,
    preflight_fingerprint,
)
from wxcli.migration.store import MigrationStore


# ---------------------------------------------------------------------------
# Known default feature limits (from 05a-preflight-checks.md)
# Exact per-org limits vary by subscription and are not API-queryable.
# ---------------------------------------------------------------------------

FEATURE_LIMITS = {
    "auto_attendant": 1000,
    "call_queue": 1000,
    "hunt_group": 1000,
    "paging_group": 100,
}


# ---------------------------------------------------------------------------
# Check 1: User Licenses
# (from 05a-preflight-checks.md Check 1)
# ---------------------------------------------------------------------------


def check_licenses(store: MigrationStore, licenses: list[dict]) -> CheckResult:
    """Check if enough Calling Professional licenses are available."""
    # Use plan_operations count (resource_type='user', op_type='create') rather
    # than raw object count so that unanalyzed/skipped users don't inflate the
    # needed count.
    row = store.conn.execute(
        "SELECT COUNT(*) AS cnt FROM plan_operations "
        "WHERE resource_type = 'user' AND op_type = 'create'"
    ).fetchone()
    user_count = row["cnt"] if row else store.count_by_type("user")
    if user_count == 0:
        return CheckResult(
            name="User licenses",
            status=CheckStatus.SKIP,
            detail="No users in migration plan",
        )

    calling_pro = None
    for lic in licenses:
        name_lower = lic.get("name", "").lower()
        if "calling" in name_lower and "professional" in name_lower:
            calling_pro = lic
            break

    if calling_pro is None:
        return CheckResult(
            name="User licenses",
            status=CheckStatus.FAIL,
            detail="No Webex Calling Professional licenses found in org",
            issues=[PreflightIssue("LICENSE_UNAVAILABLE",
                                   "No Calling Professional license in org")],
        )

    total = calling_pro.get("totalUnits", 0)
    consumed = calling_pro.get("consumedUnits", 0)
    available = total - consumed

    if available >= user_count:
        buffer_pct = ((available - user_count) / user_count * 100) if user_count else 100
        detail = f"{user_count} needed, {available} available ({available - user_count} buffer)"
        if buffer_pct < 10:
            return CheckResult(
                name="User licenses",
                status=CheckStatus.WARN,
                detail=detail + f" (only {buffer_pct:.0f}% buffer)",
                data={"needed": user_count, "available": available},
            )
        return CheckResult(
            name="User licenses",
            status=CheckStatus.PASS,
            detail=detail,
            data={"needed": user_count, "available": available},
        )

    return CheckResult(
        name="User licenses",
        status=CheckStatus.FAIL,
        detail=f"{user_count} needed, {available} available (SHORT {user_count - available})",
        issues=[PreflightIssue(
            "LICENSE_INSUFFICIENT",
            f"Need {user_count - available} more Calling Professional licenses",
        )],
        data={"needed": user_count, "available": available},
    )


# ---------------------------------------------------------------------------
# Check 2: Workspace Licenses
# (from 05a-preflight-checks.md Check 2)
# ---------------------------------------------------------------------------


def check_workspace_licenses(store: MigrationStore, licenses: list[dict]) -> CheckResult:
    """Check if enough Common Area / workspace licenses are available."""
    # Count workspaces that aren't being skipped via a WORKSPACE_LICENSE_TIER decision.
    all_decisions = store.get_all_decisions()
    skipped_ws_ids: set[str] = set()
    for d in all_decisions:
        if d.get("type") == "WORKSPACE_LICENSE_TIER" and d.get("chosen_option") == "skip":
            # context.canonical_id holds the workspace's canonical ID
            ctx = d.get("context", {})
            ws_id = ctx.get("canonical_id") or ctx.get("object_id")
            if ws_id:
                skipped_ws_ids.add(ws_id)

    ws_count = store.count_by_type("workspace") - len(skipped_ws_ids)
    if ws_count == 0:
        return CheckResult(
            name="Workspace licenses",
            status=CheckStatus.SKIP,
            detail="No workspaces in migration plan",
        )

    workspace_lic = None
    for lic in licenses:
        name_lower = lic.get("name", "").lower()
        # Real API returns "Webex Calling - Workspaces" (WORKSPACE enum)
        # and potentially "Webex Calling - Professional Workspaces" (PROFESSIONAL_WORKSPACE enum)
        if "calling" in name_lower and "workspace" in name_lower:
            workspace_lic = lic
            break

    if workspace_lic is None:
        return CheckResult(
            name="Workspace licenses",
            status=CheckStatus.FAIL,
            detail="No Webex Calling Workspace licenses found in org",
            issues=[PreflightIssue("LICENSE_UNAVAILABLE",
                                   "No Workspace license in org")],
        )

    total = workspace_lic.get("totalUnits", 0)
    consumed = workspace_lic.get("consumedUnits", 0)
    available = total - consumed

    if available >= ws_count:
        buffer_pct = ((available - ws_count) / ws_count * 100) if ws_count else 100
        detail = f"{ws_count} needed, {available} available ({available - ws_count} buffer)"
        if buffer_pct < 10:
            return CheckResult(
                name="Workspace licenses",
                status=CheckStatus.WARN,
                detail=detail + f" (only {buffer_pct:.0f}% buffer)",
                data={"needed": ws_count, "available": available},
            )
        return CheckResult(
            name="Workspace licenses",
            status=CheckStatus.PASS,
            detail=detail,
            data={"needed": ws_count, "available": available},
        )

    return CheckResult(
        name="Workspace licenses",
        status=CheckStatus.FAIL,
        detail=f"{ws_count} needed, {available} available (SHORT {ws_count - available})",
        issues=[PreflightIssue(
            "LICENSE_INSUFFICIENT",
            f"Need {ws_count - available} more Workspace licenses",
        )],
        data={"needed": ws_count, "available": available},
    )


# ---------------------------------------------------------------------------
# Check 3: Location Existence
# (from 05a-preflight-checks.md Check 3)
# ---------------------------------------------------------------------------


def check_locations(
    store: MigrationStore,
    webex_locations: list[dict],
    pstn_connections: dict[str, dict] | None = None,
) -> CheckResult:
    """Check if target locations exist in the Webex org and have PSTN configured."""
    planned = store.get_objects("location")
    if not planned:
        return CheckResult(
            name="Locations",
            status=CheckStatus.SKIP,
            detail="No locations in migration plan",
        )

    wx_by_name = {loc.get("name", "").lower(): loc for loc in webex_locations}
    missing: list[str] = []
    found: list[tuple[str, str]] = []  # (name, location_id)

    for loc in planned:
        name = loc.get("name", "")
        wx_loc = wx_by_name.get(name.lower())
        if wx_loc:
            found.append((name, wx_loc.get("id", "")))
        else:
            missing.append(name)

    if missing:
        return CheckResult(
            name="Locations",
            status=CheckStatus.FAIL,
            detail=f"{len(missing)} location(s) not found in Webex: {', '.join(missing)}",
            issues=[PreflightIssue("LOCATION_MISSING", f"Location '{n}' not in Webex")
                    for n in missing],
            data={"found": len(found), "missing": len(missing), "missing_names": missing},
        )

    # PSTN connection sub-check
    if pstn_connections is None:
        return CheckResult(
            name="Locations",
            status=CheckStatus.PASS,
            detail=f"{len(found)}/{len(planned)} target locations exist (PSTN check not available)",
            data={"found": len(found), "total": len(planned)},
        )

    no_pstn: list[str] = []
    for name, loc_id in found:
        if loc_id not in pstn_connections:
            no_pstn.append(name)

    if no_pstn:
        return CheckResult(
            name="Locations",
            status=CheckStatus.WARN,
            detail=(
                f"{len(found)}/{len(planned)} target locations exist; "
                f"{len(no_pstn)} without PSTN: {', '.join(no_pstn)}"
            ),
            issues=[PreflightIssue("PSTN_NOT_CONFIGURED", f"Location '{n}' has no PSTN connection")
                    for n in no_pstn],
            data={"found": len(found), "total": len(planned), "no_pstn": no_pstn},
        )

    return CheckResult(
        name="Locations",
        status=CheckStatus.PASS,
        detail=f"{len(found)}/{len(planned)} target locations exist, all have PSTN connections",
        data={"found": len(found), "total": len(planned)},
    )


# ---------------------------------------------------------------------------
# Check 4: Trunk Conflicts
# (from 05a-preflight-checks.md Check 4)
# ---------------------------------------------------------------------------


def check_trunks(store: MigrationStore, webex_trunks: list[dict]) -> CheckResult:
    """Check trunk name conflicts and status."""
    planned = store.get_objects("trunk")
    if not planned:
        return CheckResult(
            name="Trunks",
            status=CheckStatus.SKIP,
            detail="No trunks in migration scope",
        )

    wx_by_name = {t.get("name", "").lower(): t for t in webex_trunks}
    conflicts = []

    for trunk in planned:
        name = trunk.get("name", "")
        if name.lower() in wx_by_name:
            conflicts.append(name)

    if conflicts:
        return CheckResult(
            name="Trunks",
            status=CheckStatus.WARN,
            detail=f"{len(conflicts)} trunk name(s) already exist: {', '.join(conflicts)}",
            issues=[PreflightIssue("TRUNK_CONFLICT", f"Trunk '{n}' already exists")
                    for n in conflicts],
        )

    return CheckResult(
        name="Trunks",
        status=CheckStatus.PASS,
        detail=f"{len(planned)} planned trunk(s), no name conflicts",
    )


# ---------------------------------------------------------------------------
# Check 5: Feature Entitlements
# (from 05a-preflight-checks.md Check 5)
# ---------------------------------------------------------------------------


def check_feature_entitlements(
    store: MigrationStore,
    existing_features: dict[str, int],
) -> CheckResult:
    """Check if combined existing + planned features approach known limits."""
    feature_types = {
        "auto_attendant": "Auto Attendants",
        "call_queue": "Call Queues",
        "hunt_group": "Hunt Groups",
        "paging_group": "Paging Groups",
    }

    has_any = False
    warnings = []
    details = []

    for obj_type, label in feature_types.items():
        planned = store.count_by_type(obj_type)
        existing = existing_features.get(obj_type, 0)
        combined = planned + existing
        limit = FEATURE_LIMITS[obj_type]

        if planned > 0:
            has_any = True
            details.append(f"{label}({planned}+{existing}={combined})")
            if combined > limit * 0.8:
                warnings.append(
                    f"{label}: {existing} existing + {planned} planned = {combined} "
                    f"(exceeds 80% of typical {limit} limit)"
                )

    if not has_any:
        return CheckResult(
            name="Feature entitlements",
            status=CheckStatus.SKIP,
            detail="No call features in migration plan",
        )

    if warnings:
        return CheckResult(
            name="Feature entitlements",
            status=CheckStatus.WARN,
            detail="; ".join(warnings),
            issues=[PreflightIssue("FEATURE_LIMIT", w) for w in warnings],
        )

    return CheckResult(
        name="Feature entitlements",
        status=CheckStatus.PASS,
        detail=", ".join(details) + " within limits",
    )


# ---------------------------------------------------------------------------
# Check 6: Number Conflicts
# (from 05a-preflight-checks.md Check 6)
# ---------------------------------------------------------------------------


def check_number_conflicts(
    store: MigrationStore,
    webex_numbers: list[dict],
) -> tuple[CheckResult, list[dict]]:
    """Check for E.164 number collisions between planned and existing.

    Returns (CheckResult, list of decision dicts for NUMBER_CONFLICT).
    (from 05a-preflight-checks.md Check 6, NUMBER_CONFLICT algorithm)
    """
    # Build indexes from existing Webex numbers
    wx_by_e164: dict[str, dict] = {}
    wx_by_ext_loc: dict[tuple[str, str], dict] = {}

    for num in webex_numbers:
        pn = num.get("phoneNumber", "")
        if pn:
            wx_by_e164[pn] = num
        ext = num.get("extension", "")
        loc_id = (num.get("location") or {}).get("id", "")
        if ext and loc_id:
            wx_by_ext_loc[(ext, loc_id)] = num

    # Gather planned numbers from users, workspaces, virtual lines, lines
    planned_numbers: list[dict] = []
    for obj_type in ("user", "workspace", "virtual_line"):
        for obj in store.get_objects(obj_type):
            entry: dict[str, Any] = {"canonical_id": obj.get("canonical_id", "")}
            # E.164 numbers
            for pn in obj.get("phone_numbers", []):
                if pn.get("value"):
                    entry["e164"] = pn["value"]
            if obj.get("phone_number"):
                entry["e164"] = obj["phone_number"]
            if obj.get("e164"):
                entry["e164"] = obj["e164"]
            # Extension
            entry["extension"] = obj.get("extension")
            entry["location_id"] = obj.get("location_id")
            entry["email"] = (obj.get("emails") or [""])[0] if obj.get("emails") else ""
            planned_numbers.append(entry)

    for obj in store.get_objects("line"):
        if obj.get("e164"):
            planned_numbers.append({
                "canonical_id": obj.get("canonical_id", ""),
                "e164": obj["e164"],
                "extension": obj.get("extension"),
                "location_id": None,
                "email": "",
            })

    decisions = []
    conflict_count = 0

    for planned in planned_numbers:
        cid = planned["canonical_id"]
        e164 = planned.get("e164")
        ext = planned.get("extension")
        loc_id = planned.get("location_id")

        planned_email = planned.get("email", "")

        # E.164 collision
        if e164 and e164 in wx_by_e164:
            existing = wx_by_e164[e164]
            # Skip if same owner email — handled by DUPLICATE_USER check
            # (from 05a-preflight-checks.md lines 403-409)
            existing_email = _get_owner_email(existing)
            if existing_email and planned_email and existing_email.lower() == planned_email.lower():
                continue
            conflict_count += 1
            decisions.append(_build_number_conflict_decision(
                store, cid, planned_email, e164,
                "E164", existing,
            ))

        # Extension collision (same location)
        if ext and loc_id and (ext, loc_id) in wx_by_ext_loc:
            existing = wx_by_ext_loc[(ext, loc_id)]
            existing_email = _get_owner_email(existing)
            if existing_email and planned_email and existing_email.lower() == planned_email.lower():
                continue
            conflict_count += 1
            decisions.append(_build_number_conflict_decision(
                store, cid, planned_email, f"ext:{ext}@{loc_id}",
                "EXTENSION", existing,
            ))

    if conflict_count == 0:
        result = CheckResult(
            name="Number conflicts",
            status=CheckStatus.PASS,
            detail="No number/extension conflicts with existing Webex assignments",
        )
    else:
        result = CheckResult(
            name="Number conflicts",
            status=CheckStatus.WARN,
            detail=f"{conflict_count} number conflict(s) found",
            issues=[PreflightIssue("NUMBER_CONFLICT", f"{conflict_count} collisions")],
        )

    return result, decisions


def _get_owner_email(number_record: dict) -> str | None:
    """Extract owner email from a Webex number record, if available."""
    owner = number_record.get("owner") or {}
    return owner.get("email") or owner.get("firstName")  # email preferred


def _build_number_conflict_decision(
    store: MigrationStore,
    planned_cid: str,
    planned_email: str,
    planned_number: str,
    conflict_type: str,
    existing: dict,
) -> dict:
    """Build a NUMBER_CONFLICT decision dict.
    (from 05a-preflight-checks.md, NUMBER_CONFLICT decision structure)
    """
    owner = existing.get("owner") or {}
    existing_owner_id = owner.get("id", "")
    existing_owner_type = owner.get("type", "unknown")
    existing_name = owner.get("lastName", owner.get("firstName", "unknown"))

    return {
        "decision_id": store.next_decision_id(),
        "type": DecisionType.NUMBER_CONFLICT.value,
        "severity": "HIGH",
        "summary": (
            f"{conflict_type} conflict: {planned_number} planned for "
            f"{planned_email or planned_cid} but assigned to "
            f"{existing_name} ({existing_owner_type})"
        ),
        "context": {
            "conflict_type": conflict_type,
            "planned_number": planned_number,
            "planned_email": planned_email,
            "planned_canonical_id": planned_cid,
            "existing_owner_id": existing_owner_id,
            "existing_owner_type": existing_owner_type,
            "existing_owner_name": existing_name,
            "existing_location_id": (existing.get("location") or {}).get("id", ""),
        },
        "affected_objects": [planned_cid],
        "options": [
            {"id": "reassign", "label": "Reassign planned number",
             "impact": f"Migrate with a different number. {planned_number} stays with existing owner."},
            {"id": "remove_existing", "label": "Remove existing assignment",
             "impact": f"WARNING: Removes {planned_number} from {existing_name}."},
            {"id": "skip_number", "label": "Skip this number",
             "impact": f"Migrate without {planned_number}."},
        ],
        "fingerprint": preflight_fingerprint(
            "NUMBER_CONFLICT", conflict_type, planned_number,
            planned_email, existing_owner_id,
        ),
        "run_id": store.current_run_id,
    }


# ---------------------------------------------------------------------------
# Check 7: Duplicate Users
# (from 05a-preflight-checks.md, DUPLICATE_USER detection)
# ---------------------------------------------------------------------------


def check_duplicate_users(
    store: MigrationStore,
    webex_people: list[dict],
) -> tuple[CheckResult, list[dict]]:
    """Check if planned users already exist in Webex.

    Returns (CheckResult, list of decision dicts for DUPLICATE_USER).
    (from 05a-preflight-checks.md, DUPLICATE_USER algorithm)
    """
    wx_by_email: dict[str, dict] = {}
    for person in webex_people:
        for email in person.get("emails", []):
            wx_by_email[email.lower()] = person

    planned_users = store.get_objects("user")
    decisions = []

    for user in planned_users:
        emails = user.get("emails", [])
        for email in emails:
            existing = wx_by_email.get(email.lower())
            if not existing:
                continue

            existing_location = existing.get("locationId")
            existing_has_calling = existing_location is not None
            planned_location = user.get("location_id")

            if existing_has_calling:
                location_matches = (existing_location == planned_location)
                scenario = "already_calling"
                severity = "HIGH"
            else:
                location_matches = False
                scenario = "exists_no_calling"
                severity = "MEDIUM"

            decisions.append({
                "decision_id": store.next_decision_id(),
                "type": DecisionType.DUPLICATE_USER.value,
                "severity": severity,
                "summary": (
                    f"{'Calling user' if existing_has_calling else 'User'} "
                    f"{email} already exists in Webex"
                    f"{' at same location' if location_matches else ''}"
                ),
                "context": {
                    "email": email,
                    "planned_canonical_id": user.get("canonical_id"),
                    "existing_person_id": existing.get("id"),
                    "existing_display_name": existing.get("displayName"),
                    "existing_location_id": existing_location,
                    "planned_location_id": planned_location,
                    "existing_has_calling": existing_has_calling,
                    "location_matches": location_matches,
                    "scenario": scenario,
                },
                "affected_objects": [user.get("canonical_id")],
                "options": _duplicate_user_options(scenario, email, location_matches),
                "fingerprint": preflight_fingerprint(
                    "DUPLICATE_USER", email.lower(), existing.get("id", ""),
                ),
                "run_id": store.current_run_id,
            })
            break  # Only check first matching email per user

    if not decisions:
        result = CheckResult(
            name="Duplicate users",
            status=CheckStatus.PASS,
            detail="No cross-system duplicate users detected",
        )
    else:
        result = CheckResult(
            name="Duplicate users",
            status=CheckStatus.WARN,
            detail=f"{len(decisions)} user(s) already exist in Webex",
            issues=[PreflightIssue("DUPLICATE_USER", f"{len(decisions)} duplicates found")],
        )

    return result, decisions


def _duplicate_user_options(scenario: str, email: str, location_matches: bool) -> list[dict]:
    """Build resolution options based on the duplicate scenario.
    (from 05a-preflight-checks.md, _duplicate_user_options)
    """
    if scenario == "already_calling" and location_matches:
        return [
            {"id": "update_existing", "label": "Update existing person",
             "impact": f"MODIFY {email}'s call settings instead of creating."},
            {"id": "skip", "label": "Skip this user",
             "impact": f"{email} already in Webex with calling at this location."},
        ]
    elif scenario == "already_calling":
        return [
            {"id": "update_existing", "label": "Update existing person (settings only)",
             "impact": f"Update call settings for {email}. locationId cannot be changed via API."},
            {"id": "skip", "label": "Skip this user",
             "impact": f"{email} already calling-enabled at a different location."},
            {"id": "fail", "label": "Block migration",
             "impact": "Require manual resolution before proceeding."},
        ]
    else:
        return [
            {"id": "update_existing", "label": "Enable calling on existing person",
             "impact": f"Add Calling license and configure {email}."},
            {"id": "skip", "label": "Skip this user",
             "impact": f"{email} exists in Webex without calling."},
        ]


# ---------------------------------------------------------------------------
# Check 8: Rate Limit Budget
# (from 05a-preflight-checks.md Check 7)
# ---------------------------------------------------------------------------


def check_rate_limit_budget(store: MigrationStore, config: dict) -> CheckResult:
    """Estimate total API calls and warn if migration will be long.
    (from 05a-preflight-checks.md Check 7 — local computation only)
    """
    rate_limit = config.get("rate_limit_per_minute", 100)
    max_hours = config.get("max_migration_hours", 8)

    row = store.conn.execute(
        "SELECT SUM(api_calls) as total FROM plan_operations WHERE status = 'pending'"
    ).fetchone()
    total_api_calls = (row["total"] or 0) if row else 0

    if total_api_calls == 0:
        return CheckResult(
            name="Rate limit budget",
            status=CheckStatus.SKIP,
            detail="No plan operations found (run 'wxcli cucm plan' first)",
        )

    estimated_minutes = total_api_calls / rate_limit
    estimated_hours = estimated_minutes / 60

    detail = (
        f"~{total_api_calls:,} API calls, estimated {estimated_minutes:.0f} minutes "
        f"({estimated_hours:.1f} hours) at {rate_limit} req/min"
    )

    if estimated_hours >= max_hours:
        return CheckResult(
            name="Rate limit budget",
            status=CheckStatus.WARN,
            detail=detail + ". Consider splitting into site batches.",
            data={"api_calls": total_api_calls, "hours": round(estimated_hours, 1)},
        )

    return CheckResult(
        name="Rate limit budget",
        status=CheckStatus.PASS,
        detail=detail,
        data={"api_calls": total_api_calls, "hours": round(estimated_hours, 1)},
    )
