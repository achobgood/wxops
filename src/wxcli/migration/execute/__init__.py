"""Execution planning layer — models, constants, and tier assignments.

Defines the data structures for the execution DAG: operations (nodes),
dependency types (edge labels), broken cycles, and batches. Also contains
the static tier assignments and API call estimates sourced from
05-dependency-graph.md.

(from 05-dependency-graph.md — MigrationOp, DependencyType, batch model)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DependencyType(str, Enum):
    """Edge types in the dependency DAG.
    (from 05-dependency-graph.md lines 104-108)
    """
    REQUIRES = "requires"       # hard: A must exist before B can be created
    CONFIGURES = "configures"   # hard: A must be created before settings applied
    SOFT = "soft"               # breakable: nice-to-have ordering


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class MigrationOp(BaseModel):
    """One node in the dependency DAG.
    (from 05-dependency-graph.md lines 22-32)
    """
    canonical_id: str           # links back to objects table
    op_type: str                # "create", "configure", "assign", etc.
    resource_type: str          # "location", "user", "device", etc.
    tier: int                   # from TIER_ASSIGNMENTS
    batch: str | None = None    # site/batch assignment
    api_calls: int = 1          # estimated API call count for rate limit budgeting
    description: str = ""       # human-readable: "Create user jsmith@acme.com"
    depends_on: list[str] = Field(default_factory=list)  # node_ids this op must wait for


class BrokenCycle(BaseModel):
    """Record of a cycle that was broken during DAG construction.
    (from 05-dependency-graph.md lines 186-193)
    """
    from_node: str
    to_node: str
    dep_type: str | None = None
    reason: str = ""


class Batch(BaseModel):
    """A group of operations to execute together.
    (from 05-dependency-graph.md lines 244-258)
    """
    site: str                   # "org-wide" or a location canonical_id
    tier: int
    operations: list[str] = Field(default_factory=list)  # node_ids
    estimated_api_calls: int = 0


# ---------------------------------------------------------------------------
# Static tier assignments
# (from 05-dependency-graph.md — tier system lines 79-100, batch ordering
#  lines 206-216, expand_to_operations example lines 41-74)
# ---------------------------------------------------------------------------

TIER_ASSIGNMENTS: dict[tuple[str, str], int] = {
    # Tier 0: Infrastructure — locations created first, then calling enabled
    ("location", "create"): 0,
    ("location", "enable_calling"): 0,
    # Tier 1: Routing backbone — trunks, schedules, route groups, line key templates
    ("trunk", "create"): 1,
    ("route_group", "create"): 1,
    ("route_list", "create"): 1,
    ("route_list", "configure_numbers"): 1,
    ("operating_mode", "create"): 1,
    ("schedule", "create"): 1,
    ("line_key_template", "create"): 1,
    # Tier 2: People creation + org-wide routing objects
    ("user", "create"): 2,
    ("workspace", "create"): 2,
    ("dial_plan", "create"): 2,
    ("translation_pattern", "create"): 2,
    # calling_permission has no "create" op — permissions are per-user, not standalone
    # Tier 3: Numbers, devices (Fix 12: license+number folded into create)
    ("workspace", "assign_number"): 3,
    ("device", "create"): 3,
    # Tier 4: Call features (depend on users/workspaces existing)
    ("hunt_group", "create"): 4,
    ("call_queue", "create"): 4,
    ("auto_attendant", "create"): 4,
    ("call_park", "create"): 4,
    ("pickup_group", "create"): 4,
    ("paging_group", "create"): 4,
    # Tier 5: Settings configuration (depends on licensed users)
    ("user", "configure_settings"): 5,
    ("user", "configure_voicemail"): 5,
    ("workspace", "configure_settings"): 5,
    ("device", "configure_settings"): 5,
    ("calling_permission", "assign"): 5,
    ("call_forwarding", "configure"): 5,
    ("single_number_reach", "configure"): 5,
    ("ecbn_config", "configure"): 5,
    # Tier 6: Shared/virtual lines + monitoring (depend on users + devices)
    ("shared_line", "configure"): 6,
    ("virtual_line", "create"): 6,
    ("virtual_line", "configure"): 6,
    ("monitoring_list", "configure"): 6,
    ("receptionist_config", "configure"): 6,
    # Tier 7: Device finalization + cycle fixups
    # NOTE: tier 7 is shared between device finalization and cycle-break fixups.
    # Fixups use batch="fixups"; device ops use location-derived batches — no conflict.
    ("device_layout", "configure"): 7,
    ("softkey_config", "configure"): 7,
    # Device settings templates — location-level config at tier 1, per-device overrides at tier 5
    ("device_settings_template", "apply_location_settings"): 1,
    ("device_settings_template", "apply_device_override"): 5,
    # Hoteling / Hot Desking (depends on users + devices)
    ("device_profile", "enable_hoteling_guest"): 5,
    ("device_profile", "enable_hoteling_host"): 5,
    ("hoteling_location", "enable_hotdesking"): 0,  # Same tier as location:enable_calling
}

# ---------------------------------------------------------------------------
# API call estimates per operation
# (from 05-dependency-graph.md lines 268-281)
# ---------------------------------------------------------------------------

API_CALL_ESTIMATES: dict[str, int] = {
    # Tier 0: Infrastructure
    "location:create": 1,           # POST /locations (from provisioning.md)
    "location:enable_calling": 1,   # POST /telephony/config/locations (Fix 13)
    # Tier 1: Routing backbone + org-wide infrastructure
    "trunk:create": 1,              # POST /telephony/config/premisePstn/trunks (from call-routing.md)
    "route_group:create": 1,        # POST /telephony/config/premisePstn/routeGroups (from call-routing.md)
    "route_list:create": 1,              # POST /telephony/config/premisePstn/routeLists
    "route_list:configure_numbers": 1,   # PUT /telephony/config/premisePstn/routeLists/{id}/numbers
    "operating_mode:create": 1,     # POST /telephony/config/operatingModes (from location-call-settings-media.md)
    "schedule:create": 1,           # POST /telephony/config/locations/{id}/schedules (from location-call-settings-media.md)
    "line_key_template:create": 1,  # POST /telephony/config/devices/lineKeyTemplates
    # Tier 2: People + org-wide routing
    "user:create": 1,               # POST /people (from provisioning.md) — Fix 12: includes license + extension
    "user:configure_settings": 5,   # ~5 PUT calls: callForwarding, callerId, callWaiting, doNotDisturb,
                                    # + 1 more (monitoring/recording/intercept) (from person-call-settings-*.md)
    "user:configure_voicemail": 1,  # PUT /people/{id}/features/voicemail (from person-call-settings-media.md)
    "workspace:create": 1,          # POST /workspaces with calling config (from devices-workspaces.md)
    "workspace:assign_number": 1,   # PUT number assignment if DID needed beyond extension in create
                                    # (from devices-workspaces.md Raw HTTP section)
    "workspace:configure_settings": 3,  # ~3 PUT calls: callForwarding, callWaiting, callerId
                                        # (from devices-workspaces.md Workspace Call Settings section)
    "device:create": 1,             # POST /devices by MAC or POST /devices/activationCode
                                    # (from devices-core.md lines 1312-1323, 1304-1308)
    "device:configure_settings": 1, # PUT /telephony/config/devices/{id}/settings (from devices-core.md)
    "dial_plan:create": 1,          # POST /telephony/config/premisePstn/dialPlans (from call-routing.md)
    "translation_pattern:create": 1,  # POST /telephony/config/callRouting/translationPatterns (from call-routing.md)
    "calling_permission:create": 0,   # logical grouping only — no standalone API (from person-call-settings-permissions.md)
    "calling_permission:assign": 1,   # PUT /people/{id}/features/outgoingPermission per user
                                      # (from person-call-settings-permissions.md line 401)
    "call_forwarding:configure": 1,   # PUT /people/{id}/features/callForwarding
    "single_number_reach:configure": 2,  # PUT SNR enable + POST per number
    "ecbn_config:configure": 1,  # PUT /telephony/config/{kind}/{id}/emergencyCallbackNumber
    # Tier 4: Call features
    "hunt_group:create": 1,         # POST /telephony/config/locations/{id}/huntGroups
                                    # agents optional at create (from call-features-major.md line 894)
    "call_queue:create": 1,         # POST /telephony/config/locations/{id}/queues
                                    # (from call-features-major.md lines 616-627)
    "auto_attendant:create": 1,     # POST /telephony/config/locations/{id}/autoAttendants — menu is part of
                                    # the create body, not a separate PUT (from call-features-major.md line 184)
    "call_park:create": 1,          # POST /telephony/config/locations/{id}/callParks (from call-features-additional.md)
    "pickup_group:create": 1,       # POST /telephony/config/locations/{id}/callPickups (from call-features-additional.md)
    "paging_group:create": 1,       # POST /telephony/config/locations/{id}/paging (from call-features-additional.md)
    # Tier 6: Shared/virtual lines + monitoring
    "shared_line:configure": 2,     # Approximate — one PUT per owner to /people/{id}/applications/members
                                    # (from person-call-settings-behavior.md §4)
    "virtual_line:create": 1,       # POST /telephony/config/virtualLines (from virtual-lines.md lines 93-104)
    "virtual_line:configure": 1,    # PUT /telephony/config/virtualLines/{id} (from virtual-lines.md lines 132-147)
    "monitoring_list:configure": 1,
    "receptionist_config:configure": 2,  # PUT reception + POST directory # PUT /people/{id}/features/monitoring
    # Tier 7: Device finalization
    "device_layout:configure": 3,   # PUT members + PUT layout + POST applyChanges
    "softkey_config:configure": 2,  # PUT dynamicSettings + POST applyChanges
    # Device settings templates
    "device_settings_template:apply_location_settings": 1,  # PUT /telephony/config/locations/{id}/devices/settings
    "device_settings_template:apply_device_override": 1,    # PUT /telephony/config/devices/{id}/settings
    # Hoteling / Hot Desking
    "device_profile:enable_hoteling_guest": 1,  # PUT /people/{id}/features/hoteling
    "device_profile:enable_hoteling_host": 1,   # PUT /telephony/config/people/{id}/devices/settings/hoteling
    "hoteling_location:enable_hotdesking": 1,   # PUT /telephony/config/locations/{id}/features/hotDesking
}

# ---------------------------------------------------------------------------
# Org-wide resource types — these go into the "org-wide" batch, not per-site
# (from 05-dependency-graph.md batch ordering lines 206-216)
# ---------------------------------------------------------------------------

ORG_WIDE_TYPES: set[str] = {
    "location",
    "trunk",
    "route_group",
    "route_list",
    "operating_mode",
    "dial_plan",
    "translation_pattern",
    "calling_permission",
    "line_key_template",    # Org-scoped; not tied to a specific location
}
