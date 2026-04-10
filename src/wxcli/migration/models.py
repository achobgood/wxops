"""Canonical data models for CUCM-to-Webex migration.

All types use canonical field names only — no CUCM or Webex API field names.
Fields prefixed with cucm_ preserve CUCM-specific metadata for decision context.

Sources:
- MigrationStatus, Provenance, MigrationObject: cucm-wxc-migration.md lines 113-143
- Concrete types: cucm-wxc-migration.md lines 145-153
- Field details: 03b-transform-mappers.md mapper field tables
- Object status progression: 07-idempotency-resumability.md lines 149-160
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MigrationStatus(str, Enum):
    """Object-level migration status.

    Four-state progression for analysis: discovered -> normalized -> analyzed -> planned
    Full lifecycle includes execution states.
    (from cucm-wxc-migration.md lines 113-123, 07-idempotency-resumability.md lines 149-160)
    """
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"      # (from 07-idempotency-resumability.md line 158)
    ANALYZED = "analyzed"
    NEEDS_DECISION = "needs_decision"
    PLANNED = "planned"
    PREFLIGHT_PASSED = "preflight_passed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
    STALE = "stale"                # (from 07-idempotency-resumability.md line 179)


class LineClassification(str, Enum):
    """DN classification result from E.164 normalization algorithm.
    (from 03b-transform-mappers.md, line_mapper E.164 algorithm lines 208-211)
    """
    EXTENSION = "EXTENSION"
    NATIONAL = "NATIONAL"
    E164 = "E164"
    AMBIGUOUS = "AMBIGUOUS"


class DeviceCompatibilityTier(str, Enum):
    """Six-tier device model compatibility classification.
    (from 03b-transform-mappers.md, device_mapper compatibility table lines 270-274)
    """
    NATIVE_MPP = "native_mpp"
    CONVERTIBLE = "convertible"
    WEBEX_APP = "webex_app"
    INFRASTRUCTURE = "infrastructure"
    INCOMPATIBLE = "incompatible"
    DECT = "dect"


class DecisionType(str, Enum):
    """Types of migration decisions requiring user input.
    (from 03b-transform-mappers.md, all mapper decision tables)
    (from 03-conflict-detection-engine.md, analyzer decision tables)
    """
    EXTENSION_CONFLICT = "EXTENSION_CONFLICT"
    DN_AMBIGUOUS = "DN_AMBIGUOUS"
    DEVICE_INCOMPATIBLE = "DEVICE_INCOMPATIBLE"
    DEVICE_FIRMWARE_CONVERTIBLE = "DEVICE_FIRMWARE_CONVERTIBLE"
    SHARED_LINE_COMPLEX = "SHARED_LINE_COMPLEX"
    CSS_ROUTING_MISMATCH = "CSS_ROUTING_MISMATCH"
    CALLING_PERMISSION_MISMATCH = "CALLING_PERMISSION_MISMATCH"
    LOCATION_AMBIGUOUS = "LOCATION_AMBIGUOUS"
    DUPLICATE_USER = "DUPLICATE_USER"
    VOICEMAIL_INCOMPATIBLE = "VOICEMAIL_INCOMPATIBLE"
    WORKSPACE_LICENSE_TIER = "WORKSPACE_LICENSE_TIER"
    WORKSPACE_TYPE_UNCERTAIN = "WORKSPACE_TYPE_UNCERTAIN"
    HOTDESK_DN_CONFLICT = "HOTDESK_DN_CONFLICT"
    FEATURE_APPROXIMATION = "FEATURE_APPROXIMATION"
    MISSING_DATA = "MISSING_DATA"
    # Preflight-only decision types (from 05a-preflight-checks.md)
    NUMBER_CONFLICT = "NUMBER_CONFLICT"
    # Advisory system (from migration-advisory-design.md §3.1)
    ARCHITECTURE_ADVISORY = "ARCHITECTURE_ADVISORY"
    # Tier 2 decision types
    FORWARDING_LOSSY = "FORWARDING_LOSSY"
    SNR_LOSSY = "SNR_LOSSY"
    AUDIO_ASSET_MANUAL = "AUDIO_ASSET_MANUAL"
    BUTTON_UNMAPPABLE = "BUTTON_UNMAPPABLE"


# ---------------------------------------------------------------------------
# Base types
# ---------------------------------------------------------------------------

class Provenance(BaseModel):
    """Tracks where a canonical object came from.
    (from cucm-wxc-migration.md lines 125-131)
    """
    source_system: str              # "cucm" or "webex"
    source_id: str                  # CUCM pkid or Webex UUID
    source_name: str
    cluster: str | None = None
    extracted_at: datetime
    cucm_version: str | None = None


class MigrationObject(BaseModel):
    """Base for all migratable objects.
    (from cucm-wxc-migration.md lines 133-143)
    """
    canonical_id: str
    provenance: Provenance
    status: MigrationStatus = MigrationStatus.DISCOVERED
    webex_id: str | None = None
    pre_migration_state: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    batch: str | None = None


# ---------------------------------------------------------------------------
# Decision types — used by mappers and analyzers
# ---------------------------------------------------------------------------

class DecisionOption(BaseModel):
    """One selectable resolution for a Decision.
    (from 03b-transform-mappers.md, shared patterns — Decision Option Builder)
    """
    id: str              # "skip", "virtual_line", "convert", etc.
    label: str           # Human-readable: "Virtual Line"
    impact: str          # "1 virtual line + 4 line assignments"


class Decision(BaseModel):
    """A migration decision requiring user (or auto-rule) resolution.
    (from 03b-transform-mappers.md, shared patterns — _create_decision helper)
    (from 01-data-representation.md, decisions table lines 63-77)
    """
    decision_id: str                    # Auto-incrementing via store.next_decision_id()
    type: DecisionType                  # Enum of 20 decision types
    severity: str                       # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    summary: str                        # Human-readable one-liner
    context: dict[str, Any]             # JSON blob with full details
    options: list[DecisionOption]       # Available resolution options
    chosen_option: str | None = None    # Set when resolved
    resolved_at: str | None = None
    # Production writers set one of: "user" (interactive CLI resolve),
    # "auto_rule" (unified auto-matcher), "batch" (batch --choice resolve),
    # "stale" (superseded by a fingerprint re-run). Historical stored rows
    # from projects predating the Bug F unification may still carry the
    # legacy "auto_apply" marker — new filter/report code should treat it
    # as equivalent to "auto_rule" for backwards compatibility.
    resolved_by: str | None = None
    fingerprint: str                    # Hash of causal data
    run_id: str                         # Analysis run identifier
    affected_objects: list[str] = Field(default_factory=list)  # canonical_ids affected
    recommendation: str | None = None
    recommendation_reasoning: str | None = None


class MapperResult(BaseModel):
    """Return type for Mapper.map().
    (from 03b-transform-mappers.md, mapper contract)
    """
    objects_created: int = 0
    objects_updated: int = 0
    decisions: list[Decision] = Field(default_factory=list)


class MapperError(BaseModel):
    """Records a mapper-level error for TransformResult.
    (from 03b-transform-mappers.md, shared patterns — MapperError)
    """
    mapper_name: str
    error_message: str
    traceback: str | None = None


class TransformResult(BaseModel):
    """Aggregate result from running all mappers in the transform engine.
    (from 03b-transform-mappers.md, shared patterns — TransformResult)
    """
    decisions: list[Decision] = Field(default_factory=list)
    errors: list[MapperError] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical types — Location & Routing infrastructure
# ---------------------------------------------------------------------------

class LocationAddress(BaseModel):
    """Address fields for a Webex location.
    (from 03b-transform-mappers.md, location_mapper field table lines 80-84)
    """
    address1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class CanonicalLocation(MigrationObject):
    """CUCM Device Pool -> Webex Calling Location.
    (from 03b-transform-mappers.md, location_mapper section lines 66-121)
    """
    name: str | None = None
    time_zone: str | None = None
    preferred_language: str | None = None
    announcement_language: str | None = None
    address: LocationAddress = Field(default_factory=LocationAddress)
    routing_prefix: str | None = None
    outside_dial_digit: str | None = None
    calling_enabled: bool = True
    # CUCM metadata
    cucm_device_pool_names: list[str] = Field(default_factory=list)
    cucm_datetime_group_name: str | None = None
    cucm_location_name: str | None = None


class TrunkGatewayRef(BaseModel):
    """Reference to a trunk within a route group, with priority.
    (from 03b-transform-mappers.md, routing_mapper route group field table line 387)
    """
    trunk_canonical_id: str
    priority: int = 1


class CanonicalTrunk(MigrationObject):
    """CUCM Gateway/SIP Trunk -> Webex Calling Trunk.
    (from 03b-transform-mappers.md, routing_mapper trunk field table lines 366-380)
    """
    name: str | None = None
    location_id: str | None = None
    trunk_type: str | None = None           # REGISTERING or CERTIFICATE_BASED
    address: str | None = None              # FQDN or SRV record
    domain: str | None = None
    port: int | None = None
    max_concurrent_calls: int | None = None
    password: str | None = None             # generated placeholder
    dual_identity_support_enabled: bool | None = None
    device_type: str | None = None          # immutable after creation
    p_charge_info_support_policy: str | None = None
    # SIP/Security profile detail (from Tier 2 expansion)
    sip_profile_early_offer: bool | None = None
    sip_profile_srtp_fallback: bool | None = None
    security_mode: str | None = None          # NON_SECURE, TLS, IPSEC
    security_digest_auth: bool | None = None


class CanonicalRouteGroup(MigrationObject):
    """CUCM Route Group -> Webex Calling Route Group.
    (from 03b-transform-mappers.md, routing_mapper route group field table lines 382-387)
    """
    name: str | None = None
    local_gateways: list[TrunkGatewayRef] = Field(default_factory=list)


class CanonicalRouteList(MigrationObject):
    """CUCM Route List -> Webex Calling Route List.

    Webex route lists bind to exactly ONE route group (unlike CUCM which allows
    multiple). Dial plans point to route groups, not route lists, because Webex
    RouteType enum = ROUTE_GROUP | TRUNK only.
    """
    name: str = ""
    location_id: str | None = None
    route_group_id: str | None = None
    numbers: list[str] = Field(default_factory=list)
    cucm_route_list_name: str = ""
    cucm_route_groups: list[str] = Field(default_factory=list)



class CanonicalDialPlan(MigrationObject):
    """CUCM Route Patterns / CSS routing scope -> Webex Calling Dial Plan.
    (from 03b-transform-mappers.md, routing_mapper dial plan lines 389-395
     and css_mapper dial plan lines 469-475)
    """
    name: str | None = None
    dial_patterns: list[str] = Field(default_factory=list)
    route_id: str | None = None
    route_type: str | None = None           # TRUNK or ROUTE_GROUP


class CanonicalTranslationPattern(MigrationObject):
    """CUCM Translation Pattern -> Webex Calling Translation Pattern.
    (from 03b-transform-mappers.md, routing_mapper translation pattern lines 411-417)
    """
    name: str | None = None
    matching_pattern: str | None = None
    replacement_pattern: str | None = None


# ---------------------------------------------------------------------------
# Canonical types — Users, Lines, Devices, Workspaces
# ---------------------------------------------------------------------------

class CanonicalUser(MigrationObject):
    """CUCM End User -> Webex Calling Person.
    (from 03b-transform-mappers.md, user_mapper field table lines 130-148)
    """
    emails: list[str] = Field(default_factory=list)
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    location_id: str | None = None          # canonical_id of CanonicalLocation
    extension: str | None = None
    phone_numbers: list[dict[str, str]] = Field(default_factory=list)
    department: str | None = None
    title: str | None = None
    create_method: str | None = None        # "scim" or "people_api"
    calling_data: bool = True               # must pass callingData=true in API calls
    # CUCM metadata
    cucm_manager_user_id: str | None = None
    cucm_userid: str | None = None
    cucm_mailid: str | None = None
    # Enrichment fields (set by mappers, consumed by planner)
    voicemail_profile_id: str | None = None
    call_settings: dict[str, Any] | None = None


class CanonicalLine(MigrationObject):
    """CUCM DN/Line -> Webex Phone Number + Extension.
    (from 03b-transform-mappers.md, line_mapper field table lines 190-199)
    """
    extension: str | None = None
    e164: str | None = None
    classification: LineClassification | None = None
    shared: bool = False
    # CUCM metadata
    cucm_pattern: str | None = None
    route_partition_name: str | None = None


class CanonicalDevice(MigrationObject):
    """CUCM Phone -> Webex Calling Device.
    (from 03b-transform-mappers.md, device_mapper field table lines 252-266)
    """
    mac: str | None = None
    model: str | None = None
    compatibility_tier: DeviceCompatibilityTier | None = None
    display_name: str | None = None
    owner_canonical_id: str | None = None   # canonical_id of CanonicalUser
    location_canonical_id: str | None = None
    line_appearances: list[dict[str, Any]] = Field(default_factory=list)
    # CUCM metadata
    cucm_protocol: str | None = None        # SIP or SCCP
    cucm_device_name: str | None = None
    device_id_surface: str = "telephony"  # "telephony" (MPP) or "cloud" (9800/8875/PhoneOS)


class CanonicalWorkspace(MigrationObject):
    """CUCM Common-area Phone -> Webex Workspace + Device.
    (from 03b-transform-mappers.md, workspace_mapper field table lines 314-328)
    """
    display_name: str | None = None
    location_id: str | None = None
    supported_devices: str | None = None    # "phones" or "collaborationDevices"
    extension: str | None = None
    phone_number: str | None = None
    calling_type: str = "webexCalling"
    workspace_type: str | None = None       # meetingRoom, desk, other
    hotdesking_status: str | None = None    # on or off
    is_common_area: bool = True
    license_tier: str | None = None         # Workspace or Professional Workspace


# ---------------------------------------------------------------------------
# Canonical types — Call Features
# ---------------------------------------------------------------------------

class CanonicalHuntGroup(MigrationObject):
    """CUCM Hunt Pilot + Hunt List + Line Group -> Webex Hunt Group.
    (from 03b-transform-mappers.md, feature_mapper HG field table lines 601-614)
    """
    name: str | None = None
    extension: str | None = None
    phone_number: str | None = None
    policy: str | None = None               # REGULAR, CIRCULAR, UNIFORM, SIMULTANEOUS
    agents: list[str] = Field(default_factory=list)
    no_answer_rings: int | None = None
    enabled: bool = True
    location_id: str | None = None


class CanonicalCallQueue(MigrationObject):
    """Queue-style CUCM Hunt Pilot -> Webex Call Queue.
    (from 03b-transform-mappers.md, feature_mapper CQ field table lines 616-627)
    """
    name: str | None = None
    extension: str | None = None
    phone_number: str | None = None
    policy: str | None = None               # REGULAR, CIRCULAR, UNIFORM
    routing_type: str = "PRIORITY_BASED"
    agents: list[str] = Field(default_factory=list)
    queue_size: int = 25
    enabled: bool = True
    location_id: str | None = None


class CanonicalAutoAttendant(MigrationObject):
    """CUCM CTI Route Point + Script -> Webex Auto Attendant.
    (from 03b-transform-mappers.md, feature_mapper AA field table lines 629-638)
    """
    name: str | None = None
    extension: str | None = None
    phone_number: str | None = None
    business_schedule: str | None = None
    business_hours_menu: dict[str, Any] | None = None
    after_hours_menu: dict[str, Any] | None = None
    location_id: str | None = None


class CanonicalCallPark(MigrationObject):
    """CUCM Call Park Number -> Webex Call Park Extension.
    (from 03b-transform-mappers.md, feature_mapper simple features line 644)
    """
    name: str | None = None
    extension: str | None = None
    location_id: str | None = None


class CanonicalPickupGroup(MigrationObject):
    """CUCM Pickup Group -> Webex Call Pickup.
    (from 03b-transform-mappers.md, feature_mapper simple features line 645)
    """
    name: str | None = None
    agents: list[str] = Field(default_factory=list)
    location_id: str | None = None


class CanonicalPagingGroup(MigrationObject):
    """CUCM Paging -> Webex Paging Group.
    (from 03b-transform-mappers.md, feature_mapper simple features line 646)
    """
    name: str | None = None
    extension: str | None = None
    targets: list[str] = Field(default_factory=list)
    originators: list[str] = Field(default_factory=list)


class CanonicalOperatingMode(MigrationObject):
    """CUCM Time Period + Time Schedule -> Webex Operating Mode.
    (from 03b-transform-mappers.md, feature_mapper simple features line 647)
    """
    name: str | None = None
    level: str = "ORGANIZATION"
    schedule_type: str | None = None        # SAME_HOURS_DAILY, DIFFERENT_HOURS_DAILY, HOLIDAY
    location_id: str | None = None
    same_hours_daily: dict[str, Any] | None = None
    different_hours_daily: dict[str, Any] | None = None
    holidays: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalLocationSchedule(MigrationObject):
    """CUCM Time Schedule -> Webex Location Schedule.
    Created for schedules referenced by AAs, CQs, or HGs.
    (from fix-schedule-mapping-and-skill-gaps.md Fix 1)
    """
    name: str | None = None
    schedule_type: str | None = None  # businessHours or holidays
    location_id: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    # Reference back to the operating mode (same CUCM source)
    operating_mode_canonical_id: str | None = None


# ---------------------------------------------------------------------------
# Canonical types — Voicemail, Shared Lines, Virtual Lines, Permissions
# ---------------------------------------------------------------------------

class CanonicalVoicemailProfile(MigrationObject):
    """CUCM Unity Connection VM Profile -> Webex per-person voicemail settings.
    (from 03b-transform-mappers.md, voicemail_mapper field table lines 699-724)
    """
    enabled: bool = True
    send_all_calls: dict[str, Any] | None = None
    send_busy_calls: dict[str, Any] | None = None
    send_unanswered_calls: dict[str, Any] | None = None
    notifications: dict[str, Any] | None = None
    email_copy_of_message: dict[str, Any] | None = None
    message_storage: dict[str, Any] | None = None
    fax_message: dict[str, Any] | None = None
    transfer_to_number: dict[str, Any] | None = None
    # CUCM metadata
    cucm_voicemail_profile_name: str | None = None
    user_canonical_id: str | None = None


class CanonicalSharedLine(MigrationObject):
    """Shared line appearance — DN shared across multiple devices/users.
    (from cucm-wxc-migration.md line 185, cucm-wxc-migration.md CUCM mapping table line 204)
    """
    dn_canonical_id: str | None = None      # canonical_id of the shared DN
    owner_canonical_ids: list[str] = Field(default_factory=list)
    device_canonical_ids: list[str] = Field(default_factory=list)


class CanonicalVirtualLine(MigrationObject):
    """Virtual line — Webex Virtual Line for shared line migration.
    (from cucm-wxc-migration.md line 186)
    """
    extension: str | None = None
    phone_number: str | None = None
    location_id: str | None = None
    display_name: str | None = None
    dn_canonical_id: str | None = None


class CanonicalExecutiveAssistant(MigrationObject):
    """CUCM Executive/Assistant pairing -> Webex Executive/Assistant config.
    (from executive-assistant-migration spec §4c)
    """
    executive_canonical_id: str | None = None
    assistant_canonical_ids: list[str] = Field(default_factory=list)
    alerting_mode: str = "SIMULTANEOUS"     # SEQUENTIAL or SIMULTANEOUS
    filter_enabled: bool = False
    filter_type: str = "ALL_CALLS"          # ALL_CALLS, ALL_INTERNAL_CALLS, ALL_EXTERNAL_CALLS
    screening_enabled: bool = False


class CallingPermissionEntry(BaseModel):
    """Single call type permission entry.
    (from 03b-transform-mappers.md, css_mapper field table lines 477-486)
    """
    call_type: str                          # e.g. INTERNAL_CALL, NATIONAL, INTERNATIONAL
    action: str                             # ALLOW or BLOCK
    transfer_enabled: bool = True


class CanonicalCallingPermission(MigrationObject):
    """CSS blocking partitions -> Webex per-user Outgoing Calling Permissions.
    (from 03b-transform-mappers.md, css_mapper field table lines 477-486)
    """
    calling_permissions: list[CallingPermissionEntry] = Field(default_factory=list)
    assigned_users: list[str] = Field(default_factory=list)
    use_custom_enabled: bool = True
    use_custom_permissions: bool = True


# ---------------------------------------------------------------------------
# Canonical types — Tier 2: Call Forwarding, Monitoring
# ---------------------------------------------------------------------------

class CanonicalCallForwarding(MigrationObject):
    """CUCM per-line forwarding → Webex per-person call forwarding."""
    user_canonical_id: str | None = None
    always_enabled: bool = False
    always_destination: str | None = None
    always_to_voicemail: bool = False
    busy_enabled: bool = False
    busy_destination: str | None = None
    busy_to_voicemail: bool = False
    no_answer_enabled: bool = False
    no_answer_destination: str | None = None
    no_answer_to_voicemail: bool = False
    no_answer_ring_count: int | None = None
    busy_internal_enabled: bool = False
    busy_internal_destination: str | None = None
    no_answer_internal_enabled: bool = False
    no_answer_internal_destination: str | None = None
    no_coverage_enabled: bool = False
    no_coverage_destination: str | None = None
    on_failure_enabled: bool = False
    on_failure_destination: str | None = None
    not_registered_enabled: bool = False
    not_registered_destination: str | None = None


class CanonicalMonitoringList(MigrationObject):
    """CUCM BLF → Webex per-person monitoring list."""
    user_canonical_id: str | None = None
    call_park_notification_enabled: bool = False
    monitored_members: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalLineKeyTemplate(MigrationObject):
    """CUCM Phone Button Template → Webex Line Key Template."""
    name: str | None = None
    cucm_template_name: str | None = None
    device_model: str | None = None
    line_keys: list[dict[str, Any]] = Field(default_factory=list)
    kem_module_type: str | None = None
    kem_keys: list[dict[str, Any]] = Field(default_factory=list)
    unmapped_buttons: list[dict[str, Any]] = Field(default_factory=list)
    phones_using: int = 0


class CanonicalDeviceLayout(MigrationObject):
    """Per-device resolved line key + KEM layout."""
    device_canonical_id: str | None = None
    template_canonical_id: str | None = None
    owner_canonical_id: str | None = None
    line_members: list[dict[str, Any]] = Field(default_factory=list)
    resolved_line_keys: list[dict[str, Any]] = Field(default_factory=list)
    resolved_kem_keys: list[dict[str, Any]] = Field(default_factory=list)
    speed_dials: list[dict[str, Any]] = Field(default_factory=list)
    unmapped_buttons: list[dict[str, Any]] = Field(default_factory=list)
    device_id_surface: str = "telephony"  # Copied from associated device at map time


class CanonicalMusicOnHold(MigrationObject):
    """CUCM MOH Audio Source → Webex per-location MOH."""
    location_canonical_id: str | None = None
    source_name: str | None = None
    source_file_name: str | None = None
    is_default: bool = False
    cucm_source_id: str | None = None


class CanonicalAnnouncement(MigrationObject):
    """CUCM Announcement / Unity greeting → Webex announcement repo."""
    name: str | None = None
    location_canonical_id: str | None = None
    file_name: str | None = None
    media_type: str | None = None
    source_system: str | None = None
    usage: str | None = None
    associated_feature_canonical_id: str | None = None


class CanonicalDeviceProfile(MigrationObject):
    """CUCM Device Profile → informs Webex hot desking decisions."""
    profile_name: str | None = None
    user_canonical_id: str | None = None
    model: str | None = None
    protocol: str | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)
    device_pool_name: str | None = None
    speed_dial_count: int = 0
    blf_count: int = 0


class CanonicalReceptionistConfig(MigrationObject):
    """Receptionist configuration detected from CUCM phone layout signals."""
    user_canonical_id: str = ""
    location_canonical_id: str = ""
    blf_count: int = 0
    has_kem: bool = False
    kem_key_count: int = 0
    template_name: str = ""
    detection_score: int = 0
    detection_reasons: list[str] = Field(default_factory=list)
    monitored_members: list[str] = Field(default_factory=list)
    is_main_number_holder: bool = False


class CanonicalE911Config(MigrationObject):
    """CUCM ELIN/GeoLocation → Webex E911 advisory."""
    location_canonical_id: str | None = None
    elin_group_name: str | None = None
    elin_numbers: list[str] = Field(default_factory=list)
    geo_location_name: str | None = None
    geo_country: str | None = None
    has_emergency_route_pattern: bool = False


class CanonicalSingleNumberReach(MigrationObject):
    """CUCM Remote Destination → Webex Single Number Reach."""
    user_canonical_id: str | None = None
    enabled: bool = True
    alert_click_to_dial: bool = False
    numbers: list[dict[str, Any]] = Field(default_factory=list)
    # Each entry: {phone_number, enabled, name, answer_confirmation,
    #              cucm_answer_too_soon, cucm_answer_too_late}


class CanonicalSoftkeyConfig(MigrationObject):
    """CUCM Softkey Template → Webex PSK config (9800/8875) or report flag (classic MPP)."""
    cucm_template_name: str | None = None
    is_psk_target: bool = False
    psk_mappings: list[dict[str, Any]] = Field(default_factory=list)
    state_key_lists: dict[str, list[str]] = Field(default_factory=dict)
    unmapped_softkeys: list[dict[str, Any]] = Field(default_factory=list)
    phones_using: int = 0
    device_canonical_id: str | None = None  # Per-device PSK config: links to device


class CanonicalDeviceSettingsTemplate(MigrationObject):
    """CUCM device settings -> Webex device settings template.

    One template per (model_family, location) group. Settings are the
    majority-vote values across all phones in the group. Per-device overrides
    list phones that differ from the majority.
    """
    model_family: str | None = None  # "9800", "8875", "78xx", "68xx"
    location_canonical_id: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    per_device_overrides: list[dict[str, Any]] = Field(default_factory=list)
    unmappable_settings: list[str] = Field(default_factory=list)
    phones_using: int = 0
    custom_backgrounds: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Inventory — aggregates all canonical types
# ---------------------------------------------------------------------------

class MigrationInventory(BaseModel):
    """Single source of truth for the migration.
    (from cucm-wxc-migration.md lines 165-189)

    Note: The design spec also defines ``unmapped`` and ``pending_decisions``
    fields.  These are intentionally omitted here because the SQLite store
    (MigrationStore) is the authoritative source for decisions and unmapped
    objects are tracked via MigrationStatus.  The ``wxcli cucm export`` command
    populates these on-demand from the store when generating JSON views.
    """
    project_id: str
    cucm_cluster: str
    locations: list[CanonicalLocation] = Field(default_factory=list)
    users: list[CanonicalUser] = Field(default_factory=list)
    devices: list[CanonicalDevice] = Field(default_factory=list)
    lines: list[CanonicalLine] = Field(default_factory=list)
    hunt_groups: list[CanonicalHuntGroup] = Field(default_factory=list)
    call_queues: list[CanonicalCallQueue] = Field(default_factory=list)
    auto_attendants: list[CanonicalAutoAttendant] = Field(default_factory=list)
    trunks: list[CanonicalTrunk] = Field(default_factory=list)
    dial_plans: list[CanonicalDialPlan] = Field(default_factory=list)
    route_groups: list[CanonicalRouteGroup] = Field(default_factory=list)
    translation_patterns: list[CanonicalTranslationPattern] = Field(default_factory=list)
    operating_modes: list[CanonicalOperatingMode] = Field(default_factory=list)
    call_parks: list[CanonicalCallPark] = Field(default_factory=list)
    pickup_groups: list[CanonicalPickupGroup] = Field(default_factory=list)
    paging_groups: list[CanonicalPagingGroup] = Field(default_factory=list)
    voicemail_profiles: list[CanonicalVoicemailProfile] = Field(default_factory=list)
    shared_lines: list[CanonicalSharedLine] = Field(default_factory=list)
    virtual_lines: list[CanonicalVirtualLine] = Field(default_factory=list)
    workspaces: list[CanonicalWorkspace] = Field(default_factory=list)
    calling_permissions: list[CanonicalCallingPermission] = Field(default_factory=list)
    schedules: list[CanonicalLocationSchedule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Type registry — maps object_type strings to classes for deserialization
# ---------------------------------------------------------------------------

CANONICAL_TYPE_REGISTRY: dict[str, type[MigrationObject]] = {
    "location": CanonicalLocation,
    "user": CanonicalUser,
    "device": CanonicalDevice,
    "line": CanonicalLine,
    "hunt_group": CanonicalHuntGroup,
    "call_queue": CanonicalCallQueue,
    "auto_attendant": CanonicalAutoAttendant,
    "trunk": CanonicalTrunk,
    "dial_plan": CanonicalDialPlan,
    "route_group": CanonicalRouteGroup,
    "route_list": CanonicalRouteList,
    "translation_pattern": CanonicalTranslationPattern,
    "operating_mode": CanonicalOperatingMode,
    "call_park": CanonicalCallPark,
    "pickup_group": CanonicalPickupGroup,
    "paging_group": CanonicalPagingGroup,
    "voicemail_profile": CanonicalVoicemailProfile,
    "shared_line": CanonicalSharedLine,
    "virtual_line": CanonicalVirtualLine,
    "workspace": CanonicalWorkspace,
    "calling_permission": CanonicalCallingPermission,
    "schedule": CanonicalLocationSchedule,
    "call_forwarding": CanonicalCallForwarding,
    "monitoring_list": CanonicalMonitoringList,
    "line_key_template": CanonicalLineKeyTemplate,
    "device_layout": CanonicalDeviceLayout,
    "softkey_config": CanonicalSoftkeyConfig,
    "single_number_reach": CanonicalSingleNumberReach,
    "e911_config": CanonicalE911Config,
    "device_profile": CanonicalDeviceProfile,
    "receptionist_config": CanonicalReceptionistConfig,
    "music_on_hold": CanonicalMusicOnHold,
    "announcement": CanonicalAnnouncement,
    "device_settings_template": CanonicalDeviceSettingsTemplate,
}

# Reverse lookup: class -> type name string (O(1) for _object_type_for)
CANONICAL_CLASS_TO_TYPE: dict[type[MigrationObject], str] = {
    cls: name for name, cls in CANONICAL_TYPE_REGISTRY.items()
}
