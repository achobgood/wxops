"""Pass 1 normalizers: stateless pure functions (one CUCM dict → one canonical model).

Each normalizer takes a raw CUCM dict (as returned by zeep from AXL) and returns
either a canonical Pydantic model or a MigrationObject with cleaned fields.
Foreign keys stay as CUCM name strings — pass 2 (CrossReferenceBuilder) resolves them.

Properties:
- Testable in isolation (no database, no index, no other objects)
- Order-independent (process in any sequence)
- Parallel-safe (no shared state)

(from 02-normalization-architecture.md, Pass 1 specification)
(from 02b-cucm-extraction.md, per-extractor zeep→canonical mapping tables)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CanonicalDECTNetwork,
    CanonicalDevice,
    CanonicalTranslationPattern,
    CanonicalUser,
    CanonicalVoicemailProfile,
    CanonicalWorkspace,
    DeviceCompatibilityTier,
    MigrationObject,
    MigrationStatus,
    Provenance,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_list(field: dict | list | None, key: str) -> list:
    """Normalize a list field to a flat Python list.

    Handles both extractor format (already flat list from to_list() helper)
    and raw zeep format (nested dict with key wrapper).
    (Reconciled with Phase 03 extractors which pre-normalize via to_list())
    """
    if field is None:
        return []
    if isinstance(field, list):
        # Extractor format: already a flat list
        return field
    if isinstance(field, dict):
        # Raw zeep format: {'member': [...]} or {'member': single_dict}
        inner = field.get(key, [])
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            return [inner]
        if inner is None:
            return []
        return [inner]
    return []


def _extract_member_uuids(members: list) -> list[str]:
    """Extract UUID strings from a list of CUCM member dicts.

    Pickup group members come from AXL as dicts like:
        {'priority': 1, 'pickupGroupLineMember': {'_value_1': 'name', 'uuid': '{UUID}'}}
    This helper walks each member dict to find a UUID in any nested reference
    field and returns a flat list of UUID strings.  Already-string members are
    passed through unchanged.
    (Verified via live CUCM — pickup group member dicts contain nested refs)
    """
    result: list[str] = []
    for member in members:
        if isinstance(member, str):
            result.append(member)
            continue
        if isinstance(member, dict):
            uuid_val = _find_uuid_in_member(member)
            if uuid_val:
                result.append(uuid_val)
    return result


def _find_uuid_in_member(member: dict) -> str | None:
    """Find the UUID in a CUCM member dict by scanning nested reference fields.

    Looks for the zeep reference pattern {'_value_1': str, 'uuid': str} inside
    member dicts.  If a top-level 'uuid' key exists on the member itself, that
    is used as a last resort.
    """
    # First: scan values for nested zeep reference dicts containing 'uuid'
    for key, val in member.items():
        if key == "priority":
            continue
        if isinstance(val, dict) and "uuid" in val:
            uuid = val["uuid"]
            if uuid is not None:
                return str(uuid)
        if isinstance(val, str) and (val.startswith("{") or len(val) == 36):
            # Bare UUID string as a direct value
            return val
    # Fallback: top-level uuid on the member dict itself
    if "uuid" in member:
        uuid = member["uuid"]
        if uuid is not None:
            return str(uuid)
    return None


def _extract_ref(field: dict | str | None) -> str | None:
    """Extract _value_1 from a zeep reference field.

    Zeep AXL references use the pattern {'_value_1': str, 'uuid': str}.
    Empty references come back as {'_value_1': None, 'uuid': None}, NOT plain None.
    (Verified via live CUCM Phase 03)
    """
    if field is None:
        return None
    if isinstance(field, dict):
        val = field.get("_value_1")
        return val if val is not None else None
    return str(field)


def _make_provenance(
    raw: dict, cluster: str = "default", source_name: str | None = None
) -> Provenance:
    """Build a Provenance from a raw CUCM dict.

    (from cucm-wxc-migration.md lines 125-131)
    """
    return Provenance(
        source_system="cucm",
        source_id=raw.get("pkid", ""),
        source_name=source_name or raw.get("name", raw.get("pattern", raw.get("userid", raw.get("dirn", raw.get("domainName", ""))))),
        cluster=cluster,
        extracted_at=_now(),
    )


# ---------------------------------------------------------------------------
# §2.1 — Device Pool normalizer
# ---------------------------------------------------------------------------

def normalize_device_pool(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Device Pool dict into a MigrationObject.

    Device pools are intermediate objects — they feed location_mapper in Phase 05,
    not a direct canonical type. Stored with object_type='device_pool'.

    (from 02b-cucm-extraction.md §2.1, zeep→canonical mapping table)
    """
    name = raw.get("name", "")
    return MigrationObject(
        canonical_id=f"device_pool:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "device_pool_name": name,
            "cucm_datetime_group": _extract_ref(raw.get("dateTimeSettingName")),
            "cucm_location_name": _extract_ref(raw.get("locationName")),
            "cucm_cm_group": _extract_ref(raw.get("callManagerGroupName")),
            "cucm_srst": _extract_ref(raw.get("srstName")),
            "cucm_region": _extract_ref(raw.get("regionName")),
            "cucm_media_resource_list": _extract_ref(
                raw.get("mediaResourceListName")
            ),
        },
    )


# ---------------------------------------------------------------------------
# §2.1 — DateTime Group normalizer
# ---------------------------------------------------------------------------

def normalize_datetime_group(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM DateTime Group dict into a MigrationObject.

    DateTime groups are intermediate objects — they provide timezone data
    for location_mapper. Stored with object_type='datetime_group'.

    (from 02b-cucm-extraction.md §2.1, DateTime Group mapping table)
    """
    name = raw.get("name", "")
    return MigrationObject(
        canonical_id=f"datetime_group:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "datetime_group_name": name,
            "timezone": raw.get("timeZone"),
        },
    )


# ---------------------------------------------------------------------------
# §2.2 — End User normalizer
# ---------------------------------------------------------------------------

def normalize_user(raw: dict, cluster: str = "default") -> CanonicalUser:
    """Normalize a CUCM End User dict into a CanonicalUser.

    Handles two extraction formats:
    - AXL/zeep: associatedDevices is {'device': [str, ...]}, primaryExtension
      has UUID wrappers, callingSearchSpaceName/voiceMailProfile are references
    - SQL (_extracted_via="sql"): associatedDevices is already a flat list,
      primaryExtension is {pattern, routePartitionName} without UUID wrappers,
      callingSearchSpaceName/voiceMailProfile/selfService/userLocale are None

    (from 02b-cucm-extraction.md §2.2, zeep→canonical mapping table)
    (from 03b-transform-mappers.md §2, user_mapper field table)
    (Verified via live CUCM Phase 03)
    """
    userid = raw.get("userid", "")
    mailid = raw.get("mailid")
    extracted_via_sql = raw.get("_extracted_via") == "sql"

    # Email: direct copy, lowercase (from 03b §2: "validated as email format")
    emails: list[str] = []
    if mailid:
        emails = [mailid.lower()]

    # associatedDevices: AXL format {'device': [str, ...]} or SQL flat list
    # (Verified via live CUCM: SQL extraction returns flat list directly)
    associated_devices: list[str] = []
    assoc = raw.get("associatedDevices")
    if assoc is not None:
        if isinstance(assoc, dict):
            devs = assoc.get("device", [])
            if isinstance(devs, str):
                associated_devices = [devs]
            elif isinstance(devs, list):
                associated_devices = devs
        elif isinstance(assoc, list):
            # SQL-extracted: already a flat list of device names
            associated_devices = assoc

    # primaryExtension: AXL has UUID wrappers on routePartitionName,
    # SQL-extracted has plain {pattern, routePartitionName} without wrappers
    primary_ext = raw.get("primaryExtension")
    extension = None
    primary_partition = None
    if isinstance(primary_ext, dict):
        extension = primary_ext.get("pattern")
        rp = primary_ext.get("routePartitionName")
        # Handle both AXL reference format and SQL plain string
        if isinstance(rp, dict):
            primary_partition = _extract_ref(rp)
        elif isinstance(rp, str):
            primary_partition = rp

    # enableCti: may be string or bool depending on extraction method
    enable_cti_raw = raw.get("enableCti")
    if isinstance(enable_cti_raw, bool):
        enable_cti = enable_cti_raw
    else:
        enable_cti = str(enable_cti_raw).lower() == "true" if enable_cti_raw else False

    return CanonicalUser(
        canonical_id=f"user:{userid}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        emails=emails,
        first_name=raw.get("firstName"),
        last_name=raw.get("lastName"),
        display_name=f"{raw.get('firstName', '')} {raw.get('lastName', '')}".strip()
        or None,
        extension=extension,
        department=raw.get("department"),
        title=raw.get("title"),
        cucm_manager_user_id=_extract_ref(raw.get("manager")),
        cucm_userid=userid,
        cucm_mailid=mailid,
        pre_migration_state={
            "telephone_number": raw.get("telephoneNumber"),
            "directory_uri": raw.get("directoryUri"),
            "user_locale": raw.get("userLocale"),
            "voicemail_pilot": raw.get("selfService"),
            "associated_devices": associated_devices,
            "enable_cti": enable_cti,
            "primary_partition": primary_partition,
            "cucm_css": _extract_ref(raw.get("callingSearchSpaceName")),
            "cucm_voicemail_profile": _extract_ref(raw.get("voiceMailProfile")),
            # Flag SQL-extracted users so mappers know some fields are unavailable
            # (callingSearchSpaceName, voiceMailProfile, selfService, userLocale)
            "extracted_via_sql": extracted_via_sql,
        },
    )


# ---------------------------------------------------------------------------
# §2.3 — Phone normalizer (→ CanonicalDevice)
# ---------------------------------------------------------------------------

def _normalize_line_appearance(raw_line: dict) -> dict:
    """Normalize a single line appearance from a phone's lines array.

    (from 02b-cucm-extraction.md §2.3, per-line appearance mapping table)
    """
    dirn = raw_line.get("dirn") or {}

    # associatedEndusers: extract list of userId values
    # Extractor format (Phase 03): already flat list of strings ['jdoe', 'asmith']
    # Zeep raw format: {'enduser': [{'userId': 'jdoe'}, ...]}
    endusers: list[str] = []
    assoc = raw_line.get("associatedEndusers")
    if isinstance(assoc, list):
        # Extractor format: flat list of user ID strings
        endusers = [str(u) for u in assoc if u]
    elif isinstance(assoc, dict):
        # Zeep raw format
        eu_list = assoc.get("enduser", [])
        if isinstance(eu_list, dict):
            eu_list = [eu_list]
        for eu in eu_list:
            if isinstance(eu, dict) and "userId" in eu:
                endusers.append(eu["userId"])
            elif isinstance(eu, str):
                endusers.append(eu)

    # Call forwarding fields — 10 fields per line, verified via live CUCM Phase 03.
    # voicemail_mapper reads forwardToVoiceMail flags from these.
    def _extract_cf(field_name: str) -> dict | None:
        cf = dirn.get(field_name)
        if not cf or not isinstance(cf, dict):
            return None
        return {
            "destination": cf.get("destination"),
            "forward_to_voicemail": cf.get("forwardToVoiceMail"),
            "calling_search_space": _extract_ref(cf.get("callingSearchSpaceName")),
        }

    return {
        "line_index": int(raw_line.get("index", 0)),
        "dn": dirn.get("pattern"),
        "partition": _extract_ref(dirn.get("routePartitionName")),
        "line_label": raw_line.get("label"),
        "display_name": raw_line.get("display"),
        "e164_mask": raw_line.get("e164Mask"),
        "alerting_name": dirn.get("alertingName"),
        "dn_description": dirn.get("description"),
        "shared_line_css": _extract_ref(dirn.get("shareLineAppearanceCssName")),
        "line_css": _extract_ref(dirn.get("callingSearchSpaceName")),
        "associated_endusers": endusers,
        # Call forwarding (verified via live CUCM Phase 03)
        "call_forward_all": _extract_cf("callForwardAll"),
        "call_forward_busy": _extract_cf("callForwardBusy"),
        "call_forward_busy_int": _extract_cf("callForwardBusyInt"),
        "call_forward_no_answer": _extract_cf("callForwardNoAnswer"),
        "call_forward_no_answer_int": _extract_cf("callForwardNoAnswerInt"),
        "call_forward_no_coverage": _extract_cf("callForwardNoCoverage"),
        "call_forward_no_coverage_int": _extract_cf("callForwardNoCoverageInt"),
        "call_forward_on_failure": _extract_cf("callForwardOnFailure"),
        "call_forward_alternate_party": _extract_cf("callForwardAlternateParty"),
        "call_forward_unregistered": _extract_cf("callForwardUnregistered"),
    }


def _normalize_psc(psc: Any) -> dict | None:
    """Normalize productSpecificConfiguration to a flat dict."""
    if psc is None:
        return None
    if isinstance(psc, dict):
        return {k: v for k, v in psc.items() if v is not None} or None
    if isinstance(psc, str):
        return _parse_vendor_config_xml(psc)
    return None


def _parse_vendor_config_xml(xml_str: str) -> dict | None:
    """Parse a vendorConfig or productSpecificConfiguration XML string to flat dict."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return None
    result = {}
    for child in root:
        tag = child.tag
        text = child.text
        if text is not None:
            result[tag] = text.strip()
    return result or None


def normalize_phone(raw: dict, cluster: str = "default") -> CanonicalDevice:
    """Normalize a CUCM Phone dict into a CanonicalDevice.

    (from 02-normalization-architecture.md, Pass 1 example)
    (from 02b-cucm-extraction.md §2.3, zeep→canonical mapping table)
    """
    device_name = raw.get("name", "")

    # MAC extraction: 12 hex digits after SEP prefix
    # (from 03b §4: "Extract 12 hex digits after SEP prefix")
    mac = None
    if device_name.startswith("SEP") and len(device_name) >= 15:
        mac = device_name[3:]

    # Lines: handle empty, None, single dict, or list
    # (from 02b §2.3: "lines may be empty dict or None",
    #  "lines.line may be a single dict, not a list")
    # Lines: extractor returns flat list, zeep returns {'line': [...]}
    line_entries = _to_list(raw.get("lines"), "line")

    # Filter out speed dials: only entries with a dirn element are line appearances
    # (from 02b §2.3: "Speed dial entries have no dirn element")
    line_appearances = [
        _normalize_line_appearance(l) for l in line_entries if l.get("dirn")
    ]
    line_appearances.sort(key=lambda x: x["line_index"])

    return CanonicalDevice(
        canonical_id=f"device:{device_name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        mac=mac,
        model=raw.get("model"),
        display_name=raw.get("description") or device_name,
        cucm_protocol=raw.get("protocol"),
        cucm_device_name=device_name,
        line_appearances=line_appearances,
        pre_migration_state={
            "cucm_device_pool": _extract_ref(raw.get("devicePoolName")),
            "cucm_css": _extract_ref(raw.get("callingSearchSpaceName")),
            "cucm_owner_user": _extract_ref(raw.get("ownerUserName")),
            "cucm_phone_template": _extract_ref(raw.get("phoneTemplateName")),
            "cucm_softkey_template": _extract_ref(raw.get("softkeyTemplateName")),
            "cucm_product": raw.get("product"),
            "cucm_class": raw.get("class"),
            # Device settings fields (for DeviceSettingsMapper)
            "cucm_common_phone_config": _extract_ref(raw.get("commonPhoneConfigName")),
            "product_specific_config": _normalize_psc(raw.get("productSpecificConfiguration")),
            "cucm_user_locale": raw.get("userLocale"),
            "cucm_network_locale": raw.get("networkLocale"),
            "cucm_dnd_option": raw.get("dndOption"),
            "cucm_dnd_status": raw.get("dndStatus"),
            "cucm_extension_mobility": raw.get("enableExtensionMobility"),
        },
    )


# ---------------------------------------------------------------------------
# §2.8 — Common-Area Phone normalizer (→ CanonicalWorkspace)
# ---------------------------------------------------------------------------

def is_common_area_device(raw: dict) -> bool:
    """Classify a phone as common-area based on ownership and type.

    (from 02b-cucm-extraction.md §2.8: classification filter)
    (from 03b §5: "A CUCM common-area phone with no user owner is a workspace")
    """
    # Use _extract_ref to unwrap zeep empty references:
    # {'_value_1': None, 'uuid': None} should be treated as no owner.
    # (Found by code review — zeep returns empty refs as dicts, not None)
    if _extract_ref(raw.get("ownerUserName")) is not None:
        return False
    device_class = raw.get("class", "")
    return device_class == "Phone"


def normalize_workspace(raw: dict, cluster: str = "default") -> CanonicalWorkspace:
    """Normalize a CUCM common-area phone dict into a CanonicalWorkspace.

    (from 02b-cucm-extraction.md §2.8)
    (from 03b-transform-mappers.md §5, workspace_mapper field table)
    """
    device_name = raw.get("name", "")

    # Primary line extension
    # Lines: extractor returns flat list, zeep returns {'line': [...]}
    line_entries = _to_list(raw.get("lines"), "line")

    extension = None
    for l in line_entries:
        dirn = l.get("dirn")
        if dirn and str(l.get("index", "0")) == "1":
            extension = dirn.get("pattern")
            break

    return CanonicalWorkspace(
        canonical_id=f"workspace:{device_name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        display_name=raw.get("description") or device_name,
        extension=extension,
        is_common_area=True,
        pre_migration_state={
            "cucm_device_pool": _extract_ref(raw.get("devicePoolName")),
            "cucm_css": _extract_ref(raw.get("callingSearchSpaceName")),
            "cucm_model": raw.get("model"),
            "cucm_protocol": raw.get("protocol"),
            "cucm_product": raw.get("product"),
            "cucm_device_name": device_name,
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — CSS normalizer (intermediate for cross-refs)
# ---------------------------------------------------------------------------

def normalize_css(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM CSS dict into a MigrationObject.

    CSS objects are intermediate — css_mapper in Phase 05 consumes them.
    The critical data is the ordered partition membership list.

    (from 02b-cucm-extraction.md §2.4, CSS mapping table)
    (from 04-css-decomposition.md: "ordinal values preserving partition priority")
    """
    name = raw.get("name", "")

    # Members: ordered list of (partition_name, index) — MUST preserve ordering
    # (from 02b §2.4: "The index field is the partition priority within this CSS
    #  and MUST be preserved")
    # Members: extractor returns flat list, zeep returns {'member': [...]}
    member_list = _to_list(raw.get("members"), "member")

    partitions = []
    for m in member_list:
        pt_name = _extract_ref(m.get("routePartitionName"))
        index = int(m.get("index", 0))
        if pt_name:
            partitions.append({"partition_name": pt_name, "index": index})
    partitions.sort(key=lambda x: x["index"])

    return MigrationObject(
        canonical_id=f"css:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "css_name": name,
            "description": raw.get("description"),
            "partitions": partitions,
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — Partition normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_partition(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Route Partition dict into a MigrationObject.

    Partitions are intermediate objects used by cross-reference builder.

    (from 02b-cucm-extraction.md §2.4, Partition returnedTags)
    """
    name = raw.get("name", "")
    return MigrationObject(
        canonical_id=f"partition:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "partition_name": name,
            "description": raw.get("description"),
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — Route Pattern normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_route_pattern(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Route Pattern dict into a MigrationObject.

    Route patterns are intermediate — routing_mapper in Phase 05 consumes them.

    (from 02b-cucm-extraction.md §2.4, Route Pattern mapping table)
    """
    pattern = raw.get("pattern", "")
    partition = _extract_ref(raw.get("routePartitionName"))
    # Canonical ID includes partition for uniqueness (same pattern in different partitions)
    canonical_id = f"route_pattern:{pattern}:{partition or '<None>'}"

    # blockEnable: string to action classification
    # (from 04-css-decomposition.md Step 2: "classify patterns as ROUTE or BLOCK")
    block_enable = raw.get("blockEnable")
    action = "BLOCK" if str(block_enable).lower() == "true" else "ROUTE"

    # Destination/target extraction — getRoutePattern returns the routing target
    # as one of: destination (complex), gatewayName (ref), routeListName (ref)
    gateway_name = _extract_ref(raw.get("gatewayName"))
    route_list_name = _extract_ref(raw.get("routeListName"))
    # Determine target type and name for cross-ref builder and routing mapper
    if gateway_name:
        target_type = "gateway"
        target_name = gateway_name
    elif route_list_name:
        target_type = "route_list"
        target_name = route_list_name
    else:
        target_type = None
        target_name = None

    return MigrationObject(
        canonical_id=canonical_id,
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pattern": pattern,
            "partition": partition,
            "action": action,
            "description": raw.get("description"),
            "called_transform_mask": raw.get("calledPartyTransformationMask"),
            "calling_transform_mask": raw.get("callingPartyTransformationMask"),
            "prefix_digits_out": raw.get("prefixDigitsOut"),
            "network_location": raw.get("networkLocation"),
            "target_type": target_type,
            "target_name": target_name,
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — Translation Pattern normalizer
# ---------------------------------------------------------------------------

def normalize_translation_pattern(
    raw: dict, cluster: str = "default"
) -> CanonicalTranslationPattern:
    """Normalize a CUCM Translation Pattern dict into a CanonicalTranslationPattern.

    (from 02b-cucm-extraction.md §2.4, Translation Pattern mapping table)
    (from 03b-transform-mappers.md §6, translation pattern field table)
    """
    pattern = raw.get("pattern", "")
    partition = _extract_ref(raw.get("routePartitionName"))
    canonical_id = f"translation_pattern:{pattern}:{partition or '<None>'}"

    return CanonicalTranslationPattern(
        canonical_id=canonical_id,
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        name=raw.get("description") or pattern,
        matching_pattern=pattern,
        replacement_pattern=raw.get("calledPartyTransformationMask"),
        pre_migration_state={
            "partition": partition,
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Hunt Pilot normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_hunt_pilot(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Hunt Pilot dict into a MigrationObject.

    Hunt pilots are intermediate — feature_mapper resolves the hunt_pilot →
    hunt_list → line_group chain to produce CanonicalHuntGroup or CanonicalCallQueue.

    (from 02b-cucm-extraction.md §2.5, Hunt Pilot mapping)
    (from 03b-transform-mappers.md §8, feature_mapper)
    """
    pattern = raw.get("pattern", "")
    partition = _extract_ref(raw.get("routePartitionName"))
    canonical_id = f"hunt_pilot:{pattern}:{partition or '<None>'}"

    # Queue-style detection fields
    # (from 03b §10: queue-style heuristics)
    queue_calls = raw.get("queueCalls")
    queue_enabled = False
    if isinstance(queue_calls, dict):
        queue_enabled = str(queue_calls.get("enabled", "false")).lower() == "true"
    elif isinstance(queue_calls, str):
        queue_enabled = queue_calls.lower() == "true"

    # Forward settings
    fwd_no_answer = raw.get("forwardHuntNoAnswer") or {}
    fwd_busy = raw.get("forwardHuntBusy") or {}

    return MigrationObject(
        canonical_id=canonical_id,
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pattern": pattern,
            "partition": partition,
            "description": raw.get("description"),
            "hunt_list_name": _extract_ref(raw.get("huntListName")),
            "forward_no_answer_destination": fwd_no_answer.get("destination"),
            "forward_no_answer_enabled": str(
                fwd_no_answer.get("enabled", "false")
            ).lower()
            == "true",
            "forward_busy_destination": fwd_busy.get("destination"),
            "forward_busy_enabled": str(
                fwd_busy.get("enabled", "false")
            ).lower()
            == "true",
            "queue_calls_enabled": queue_enabled,
            "max_callers_in_queue": raw.get("maxCallersInQueue"),
            "moh_source_id": raw.get("mohSourceId"),
            "hunt_timer_call_pick": raw.get("huntTimerCallPick"),
            "overflow_destination": raw.get("overflowDestination"),
            "enabled": str(raw.get("enabled", "true")).lower() == "true",
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Hunt List normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_hunt_list(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Hunt List dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.5, Hunt List returnedTags)
    """
    name = raw.get("name", "")

    # Members: list of line group references
    # Members: extractor returns flat list, zeep returns {'member': [...]}
    member_list = _to_list(raw.get("members"), "member")

    line_groups = []
    for m in member_list:
        # Extractor uses 'userOrDeviceName', design spec uses 'lineGroupName'
        lg_name = (
            _extract_ref(m.get("lineGroupName"))
            or _extract_ref(m.get("userOrDeviceName"))
        )
        if lg_name:
            line_groups.append(lg_name)

    return MigrationObject(
        canonical_id=f"hunt_list:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "hunt_list_name": name,
            "description": raw.get("description"),
            "hunt_algorithm": raw.get("huntAlgorithm"),
            "voice_mail_usage": raw.get("voiceMailUsage"),
            "route_list_enabled": raw.get("routeListEnabled"),
            "line_groups": line_groups,
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Line Group normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_line_group(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Line Group dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.5, Line Group returnedTags)
    """
    name = raw.get("name", "")

    # Members: list of DN/line references
    # Members: extractor returns flat list, zeep returns {'member': [...]}
    member_list = _to_list(raw.get("members"), "member")

    return MigrationObject(
        canonical_id=f"line_group:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "line_group_name": name,
            "rna_reversion_timeout": raw.get("rnaReversionTimeOut"),
            "distribution_algorithm": raw.get("distributionAlgorithm"),
            "members": member_list,
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — CTI Route Point normalizer (intermediate, feeds AA creation)
# ---------------------------------------------------------------------------

def normalize_cti_route_point(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM CTI Route Point dict into a MigrationObject.

    CTI RPs feed feature_mapper for Auto Attendant creation.

    (from 02b-cucm-extraction.md §2.5, CTI Route Point returnedTags)
    """
    name = raw.get("name", "")

    # Lines: same structure as phones
    # Lines: extractor returns flat list, zeep returns {'line': [...]}
    line_entries = _to_list(raw.get("lines"), "line")

    line_appearances = [
        _normalize_line_appearance(l) for l in line_entries if l.get("dirn")
    ]

    return MigrationObject(
        canonical_id=f"cti_rp:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "cti_rp_name": name,
            "description": raw.get("description"),
            "cucm_device_pool": _extract_ref(raw.get("devicePoolName")),
            "cucm_css": _extract_ref(raw.get("callingSearchSpaceName")),
            "lines": line_appearances,
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Call Park normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_call_park(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Call Park Number dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.5, Call Park returnedTags)
    """
    pattern = raw.get("pattern", "")
    partition = _extract_ref(raw.get("routePartitionName"))

    return MigrationObject(
        canonical_id=f"call_park:{pattern}:{partition or '<None>'}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pattern": pattern,
            "partition": partition,
            "description": raw.get("description"),
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Pickup Group normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_pickup_group(raw: dict, cluster: str = "default") -> MigrationObject | None:
    """Normalize a CUCM Pickup Group dict into a MigrationObject.

    Verified via live CUCM: pickup groups use 'pattern' as search criteria,
    and the AXL object has both 'name' and 'pattern' fields.

    Returns None if the pickup group has no usable name (Fix 7: dedup guard).

    (from 02b-cucm-extraction.md §2.5, Pickup Group returnedTags)
    """
    # Use name if available, fall back to pattern
    name = raw.get("name", "") or raw.get("pattern", "")

    # Fix 7: Guard against empty/None name — skip objects with no identity
    if not name or not name.strip():
        return None

    # Members: extractor returns flat list, zeep returns {'member': [...]}
    # Each member is a dict like {'priority': int, 'someRefField': {'_value_1': name, 'uuid': '{UUID}'}}.
    # Extract UUID strings so downstream consumers (CanonicalPickupGroup.agents) get list[str].
    member_list = _to_list(raw.get("members"), "member")
    member_ids = _extract_member_uuids(member_list)

    return MigrationObject(
        canonical_id=f"pickup_group:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pickup_group_name": name,
            "pattern": raw.get("pattern"),
            "members": member_ids,
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Time Schedule normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_time_schedule(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Time Schedule dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.5, Time Schedule returnedTags)
    """
    name = raw.get("name", "")

    # Members: extractor returns flat list, zeep returns {'member': [...]}
    member_list = _to_list(raw.get("members"), "member")

    time_period_names = []
    for m in member_list:
        tp_name = _extract_ref(m.get("timePeriodName"))
        if tp_name:
            time_period_names.append(tp_name)

    return MigrationObject(
        canonical_id=f"time_schedule:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "schedule_name": name,
            "time_periods": time_period_names,
        },
    )


# ---------------------------------------------------------------------------
# §2.5 — Time Period normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_time_period(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Time Period dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.5, Time Period returnedTags)
    """
    name = raw.get("name", "")

    return MigrationObject(
        canonical_id=f"time_period:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "time_period_name": name,
            "start_time": raw.get("startTime"),
            "end_time": raw.get("endTime"),
            "start_date": raw.get("startDate"),
            "end_date": raw.get("endDate"),
            "month_of_year": raw.get("monthOfYear"),
            "day_of_month": raw.get("dayOfMonth"),
            "day_of_week": raw.get("dayOfWeek"),
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — Gateway normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_gateway(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Gateway dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.4, Gateway returnedTags)
    """
    name = raw.get("domainName", raw.get("name", ""))

    return MigrationObject(
        canonical_id=f"gateway:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "gateway_name": name,
            "description": raw.get("description"),
            "product": raw.get("product"),
            "protocol": raw.get("protocol"),
            "cucm_device_pool": _extract_ref(raw.get("devicePoolName")),
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — SIP Trunk normalizer (intermediate)
# ---------------------------------------------------------------------------


def _get_profile_field(profile_detail: dict | None, field_name: str) -> Any:
    """Extract a field from a profile detail dict, returning None if not present."""
    if profile_detail is None:
        return None
    return profile_detail.get(field_name)


def normalize_sip_trunk(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM SIP Trunk dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.4, SIP Trunk returnedTags)
    (from 03b-transform-mappers.md §6, trunk field table)
    """
    name = raw.get("name", "")

    # Verified via live CUCM: destinations is a list of dicts with
    # {addressIpv4, addressIpv6, port, sortOrder}, NOT flat
    # destinationAddress/destinationPort fields.
    # Extractor returns flat list, zeep returns {'destination': [...]}
    dest_list = _to_list(raw.get("destinations"), "destination")

    destinations = []
    for d in dest_list:
        if isinstance(d, dict):
            destinations.append({
                "address": d.get("addressIpv4") or d.get("addressIpv6"),
                "port": d.get("port"),
                "sort_order": d.get("sortOrder"),
            })

    # Fallback: also check flat fields for design-spec format
    if not destinations:
        flat_addr = raw.get("destinationAddress")
        flat_port = raw.get("destinationPort")
        if flat_addr:
            destinations = [{"address": flat_addr, "port": flat_port, "sort_order": 1}]

    return MigrationObject(
        canonical_id=f"sip_trunk:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "trunk_name": name,
            "description": raw.get("description"),
            "destinations": destinations,
            "max_num_calls": raw.get("maxNumCalls"),
            "cucm_device_pool": _extract_ref(raw.get("devicePoolName")),
            "sip_profile": _extract_ref(raw.get("sipProfileName")),
            "security_profile": _extract_ref(raw.get("securityProfileName")),
            "sip_trunk_type": raw.get("sipTrunkType"),
            "dual_identity_support": raw.get("dualIdentitySupportEnabled"),
            "sip_profile_early_offer": _get_profile_field(raw.get("_sip_profile_detail"), "earlyOfferSupportForVoiceCall"),
            "sip_profile_srtp_fallback": _get_profile_field(raw.get("_sip_profile_detail"), "srtpFallbackAllowed"),
            "security_mode": _get_profile_field(raw.get("_security_profile_detail"), "securityMode"),
            "security_digest_auth": _get_profile_field(raw.get("_security_profile_detail"), "enableDigestAuthentication"),
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — Route Group normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_route_group(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Route Group dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.4, Route Group returnedTags)
    """
    name = raw.get("name", "")

    # Members: extractor returns flat list, zeep returns {'member': [...]}
    member_list = _to_list(raw.get("members"), "member")

    trunks = []
    for m in member_list:
        # Extractor uses 'sipTrunkName', design spec uses 'deviceName'
        trunk_name = (
            _extract_ref(m.get("deviceName"))
            or _extract_ref(m.get("sipTrunkName"))
        )
        if trunk_name:
            trunks.append({
                "trunk_name": trunk_name,
                "priority": m.get("priority", 1),
            })

    return MigrationObject(
        canonical_id=f"route_group:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "route_group_name": name,
            "description": raw.get("description"),
            "trunks": trunks,
        },
    )


# ---------------------------------------------------------------------------
# §2.4 — Route List normalizer (intermediate)
# ---------------------------------------------------------------------------

def normalize_route_list(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Route List dict into a MigrationObject.

    (from 02b-cucm-extraction.md §2.4, Route List returnedTags)
    """
    name = raw.get("name", "")

    # Members: extractor returns flat list, zeep returns {'member': [...]}
    member_list = _to_list(raw.get("members"), "member")

    route_groups = []
    for m in member_list:
        rg_name = _extract_ref(m.get("routeGroupName"))
        if rg_name:
            route_groups.append(rg_name)

    return MigrationObject(
        canonical_id=f"route_list:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "route_list_name": name,
            "description": raw.get("description"),
            "route_groups": route_groups,
        },
    )


# ---------------------------------------------------------------------------
# §2.6 — Voicemail Profile normalizer
# ---------------------------------------------------------------------------

def _extract_vm_pilot(field: dict | str | None) -> str | None:
    """Extract the voicemail pilot number from the voiceMailPilot field.

    Live CUCM returns voiceMailPilot as a complex type {dirn, cssName, uuid},
    NOT the simple {_value_1, uuid} reference pattern. The pilot number is
    in the 'dirn' key.
    (Verified via live CUCM Phase 03 — 02b spec had this wrong)
    """
    if field is None:
        return None
    if isinstance(field, dict):
        # Real structure: {dirn: str, cssName: str, uuid: str}
        if "dirn" in field:
            return field["dirn"]
        # Fallback: design spec structure {_value_1: str, uuid: str}
        if "_value_1" in field:
            return field["_value_1"]
    if isinstance(field, str):
        return field
    return None


def normalize_voicemail_profile(
    raw: dict, cluster: str = "default"
) -> CanonicalVoicemailProfile:
    """Normalize a CUCM Voicemail Profile dict into a CanonicalVoicemailProfile.

    (from 02b-cucm-extraction.md §2.6, Voicemail Profile mapping)
    (from 03b-transform-mappers.md §9, voicemail_mapper field table)
    """
    name = raw.get("name", "")
    vm_pilot_field = raw.get("voiceMailPilot")

    return CanonicalVoicemailProfile(
        canonical_id=f"voicemail_profile:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        cucm_voicemail_profile_name=name,
        pre_migration_state={
            "description": raw.get("description"),
            "voicemail_pilot": _extract_vm_pilot(vm_pilot_field),
            "voicemail_pilot_css": vm_pilot_field.get("cssName")
            if isinstance(vm_pilot_field, dict)
            else None,
            "voicemail_box_mask": raw.get("voiceMailboxMask"),
        },
    )


# ---------------------------------------------------------------------------
# §2.6 — Unity Connection per-user VM settings normalizer
# ---------------------------------------------------------------------------

def normalize_unity_vm_settings(
    userid: str, settings: dict, cluster: str = "default"
) -> MigrationObject:
    """Normalize Unity Connection per-user voicemail settings into a MigrationObject.

    These are the ~12 per-user fields from extract_user_vm_settings() in
    unity_connection.py. Stored separately from the AXL voicemail profile
    because profiles are shared (many users → one profile) while UC settings
    are per-user.

    The voicemail_mapper (Phase 05) joins these with the profile-level data
    via cross_ref user_has_voicemail_profile + these per-user settings.

    (from Phase 03 unity_connection.py extract_user_vm_settings())
    """
    return MigrationObject(
        canonical_id=f"unity_vm:{userid}",
        provenance=Provenance(
            source_system="unity_connection",
            source_id=settings.get("uc_object_id", ""),
            source_name=userid,
            cluster=cluster,
            extracted_at=_now(),
        ),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": userid,
            "vm_enabled": settings.get("vm_enabled", False),
            "call_handler_id": settings.get("call_handler_id"),
            # Notification settings
            "notification_enabled": settings.get("notification_enabled", False),
            "notification_destination": settings.get("notification_destination"),
            # Call handler transfer rules
            "send_all_calls": settings.get("send_all_calls"),
            "send_busy_calls": settings.get("send_busy_calls"),
            "send_unanswered_calls": settings.get("send_unanswered_calls"),
            "unanswered_rings": settings.get("unanswered_rings"),
            "busy_greeting_type": settings.get("busy_greeting_type"),
            # Message store
            "storage_type": settings.get("storage_type"),
            "mwi_enabled": settings.get("mwi_enabled"),
            "external_email": settings.get("external_email"),
            "email_copy_enabled": settings.get("email_copy_enabled"),
            # Transfer to zero
            "transfer_to_zero_enabled": settings.get("transfer_to_zero_enabled"),
            "transfer_to_zero_destination": settings.get(
                "transfer_to_zero_destination"
            ),
            # Fax
            "fax_enabled": settings.get("fax_enabled"),
            "fax_number": settings.get("fax_number"),
        },
    )


# ---------------------------------------------------------------------------
# §2.6 — Unity Connection shared/group mailbox normalizer
# (from docs/superpowers/specs/2026-04-10-voicemail-groups.md)
# ---------------------------------------------------------------------------


def normalize_voicemail_group(
    raw: dict, cluster: str = "default"
) -> MigrationObject | None:
    """Normalize a Unity Connection shared mailbox (call handler) into a
    MigrationObject for later consumption by VoicemailGroupMapper.

    Returns None when DisplayName is missing — shared mailboxes without a
    display name can't be mapped reliably and should be skipped.

    (from Unity Connection CUPI /vmrest/handlers/callhandlers)
    """
    name = raw.get("DisplayName") or raw.get("display_name") or ""
    if not name:
        return None

    extension = (
        raw.get("DtmfAccessId")
        or raw.get("Extension")
        or raw.get("extension")
    )
    object_id = raw.get("ObjectId") or raw.get("pkid") or ""

    return MigrationObject(
        canonical_id=f"voicemail_group:{name}",
        provenance=Provenance(
            source_system="unity_connection",
            source_id=object_id,
            source_name=name,
            cluster=cluster,
            extracted_at=_now(),
        ),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "extension": str(extension) if extension is not None else None,
            "cucm_object_id": object_id,
            "notification_destination": (
                raw.get("SmtpAddress")
                or raw.get("notification_destination")
            ),
            "language_code": raw.get("language_code", "en_us"),
            "greeting_type": raw.get("greeting_type", "DEFAULT"),
            "transfer_destination": raw.get("transfer_destination"),
            "fax_enabled": bool(raw.get("fax_enabled")),
            "fax_number": raw.get("fax_number"),
        },
    )


# ---------------------------------------------------------------------------
# §2.6 — Voicemail Pilot normalizer (intermediate, for UUID→dirn resolution)
# ---------------------------------------------------------------------------

def normalize_voicemail_pilot(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Voicemail Pilot dict into a MigrationObject.

    Voicemail pilots are intermediate objects used to resolve the
    voiceMailPilot.uuid on profiles to an actual pilot dirn number.
    The profile's voiceMailPilot.dirn is often None — the UUID must be
    matched against these pilot objects to get the actual dirn.
    (Confirmed by Phase 03 live CUCM validation)
    """
    dirn = raw.get("dirn", "")
    pkid = raw.get("pkid", "")
    return MigrationObject(
        canonical_id=f"voicemail_pilot:{dirn or pkid}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "dirn": dirn,
            "description": raw.get("description"),
            # Store UUID for profile→pilot resolution
            "uuid": pkid,
        },
    )


# ---------------------------------------------------------------------------
# §2.1 — CUCM Location normalizer (CAC bandwidth objects, no address data)
# ---------------------------------------------------------------------------

def normalize_cucm_location(raw: dict, cluster: str = "default") -> MigrationObject:
    """Normalize a CUCM Location entity (CAC object) into a MigrationObject.

    These are Call Admission Control bandwidth objects, NOT physical locations.
    No address fields exist. The location_mapper's MISSING_DATA decision for
    addresses is the correct path.
    (Confirmed by Phase 03 live CUCM validation: shape is {name, id, uuid,
     withinAudioBandwidth, withinVideoBandwidth, withinImmersiveKbits})
    """
    name = raw.get("name", "")
    return MigrationObject(
        canonical_id=f"cucm_location:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "cucm_location_name": name,
            # No address fields — confirmed via live CUCM
        },
    )


# ---------------------------------------------------------------------------
# §2.1 — Phone Button Template normalizer
# ---------------------------------------------------------------------------

def normalize_button_template(raw: dict, cluster: str = "default") -> MigrationObject | None:
    """Normalize a CUCM PhoneButtonTemplate dict.

    (from tier2-phase2-phone-config-design.md §2.1)
    """
    name = raw.get("name")
    if not name:
        return None

    raw_buttons = raw.get("buttons")
    button_list = _to_list(raw_buttons, "button") if isinstance(raw_buttons, dict) else []
    buttons = []
    for btn in button_list:
        if not isinstance(btn, dict):
            continue
        # AXL getPhoneButtonTemplate uses <buttonNumber>, not <index>
        idx = btn.get("buttonNumber") or btn.get("index")
        feature = btn.get("feature", "")
        buttons.append({"index": int(idx) if idx else 0, "feature": feature})
    buttons.sort(key=lambda b: b["index"])

    return MigrationObject(
        canonical_id=f"button_template:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "base_template": _extract_ref(raw.get("basePhoneTemplateName")),
            "buttons": buttons,
        },
    )


# ---------------------------------------------------------------------------
# §2.2 — Softkey Template normalizer
# ---------------------------------------------------------------------------

def normalize_softkey_template(raw: dict, cluster: str = "default") -> MigrationObject | None:
    """Normalize a CUCM SoftkeyTemplate dict.

    (from tier2-phase2-phone-config-design.md §2.2)
    """
    name = raw.get("name")
    if not name:
        return None

    # Softkey templates come from SQL (AXL operations don't exist in v15.0).
    # The TemplateExtractor pre-parses SQL rows into structured dicts with
    # call_states already decoded. Pass through the parsed data.
    call_states = raw.get("call_states", {})
    available_softkeys = raw.get("available_softkeys", [])

    return MigrationObject(
        canonical_id=f"softkey_template:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": raw.get("description") or "",
            "default_template": (
                raw.get("base_template_pkid")
                or _extract_ref(raw.get("defaultSoftkeyTemplateName"))
                or ""
            ),
            "call_states": call_states,
            "available_softkeys": available_softkeys,
        },
    )


# ---------------------------------------------------------------------------
# Device Profile normalizer (Tier 2 — §2.2 Extension Mobility)
# ---------------------------------------------------------------------------

def normalize_device_profile(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Device Profile to a MigrationObject.

    (from tier2-enterprise-expansion.md §5)
    """
    name = raw.get("name") or ""
    product = raw.get("product") or ""
    protocol = raw.get("protocol") or ""
    device_pool = _extract_ref(raw.get("devicePoolName"))

    # Extract line info
    lines_raw = raw.get("lines") or []
    if isinstance(lines_raw, dict):
        lines_raw = lines_raw.get("line", [])
    if isinstance(lines_raw, dict):
        lines_raw = [lines_raw]

    lines = []
    for line in (lines_raw if isinstance(lines_raw, list) else []):
        if not isinstance(line, dict):
            continue
        dirn = line.get("dirn") or {}
        if isinstance(dirn, dict):
            pattern = dirn.get("pattern") or ""
            partition = _extract_ref(dirn.get("routePartitionName"))
        else:
            pattern = str(dirn)
            partition = None
        lines.append({
            "dn_pattern": pattern,
            "partition": partition,
            "index": line.get("index"),
        })

    # Count speed dials and BLFs
    sd = raw.get("speeddials") or []
    blf = raw.get("busyLampFields") or []
    sd_count = len(sd) if isinstance(sd, list) else 0
    blf_count = len(blf) if isinstance(blf, list) else 0

    return MigrationObject(
        canonical_id=f"device_profile:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "profile_name": name,
            "model": product,
            "protocol": protocol,
            "device_pool_name": device_pool,
            "lines": lines,
            "speed_dial_count": sd_count,
            "blf_count": blf_count,
        },
    )


# ---------------------------------------------------------------------------
# E911 normalizers (Tier 2 — §2.6 E911/ELIN)
# ---------------------------------------------------------------------------

def normalize_elin_group(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM ELIN Group to a MigrationObject.

    (from tier2-enterprise-expansion.md §6)
    """
    name = raw.get("name") or ""
    # ELIN numbers may come as a nested structure or flat list
    elin_raw = raw.get("elinNumbers") or raw.get("elinNumber") or []
    elin_numbers = []
    if isinstance(elin_raw, list):
        for e in elin_raw:
            if isinstance(e, str):
                elin_numbers.append(e)
            elif isinstance(e, dict):
                num = e.get("_value_1") or e.get("number") or e.get("dirn") or ""
                if num:
                    elin_numbers.append(str(num))
    elif isinstance(elin_raw, str) and elin_raw:
        elin_numbers = [elin_raw]

    return MigrationObject(
        canonical_id=f"elin_group:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": raw.get("description") or "",
            "elin_numbers": elin_numbers,
        },
    )


def normalize_geo_location(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Geographic Location to a MigrationObject.

    (from tier2-enterprise-expansion.md §6)
    """
    name = raw.get("name") or ""
    return MigrationObject(
        canonical_id=f"geo_location:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": raw.get("description") or "",
            "country": raw.get("country") or "",
        },
    )


# ---------------------------------------------------------------------------
# Remote Destination normalizer (Tier 2 — §2.7 SNR)
# ---------------------------------------------------------------------------

def normalize_remote_destination(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Remote Destination to a MigrationObject.

    Preserves raw fields for the SNR mapper to consume.
    (from tier2-enterprise-expansion.md §4)
    """
    name = raw.get("name") or ""
    owner = raw.get("ownerUserId") or ""
    dest = raw.get("destination") or ""

    return MigrationObject(
        canonical_id=f"remote_destination:{owner}:{name}" if owner else f"remote_destination:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "destination": dest,
            "ownerUserId": owner,
            "isMobilePhone": raw.get("isMobilePhone"),
            "enableMobileConnect": raw.get("enableMobileConnect"),
            "answerTooSoonTimer": raw.get("answerTooSoonTimer"),
            "answerTooLateTimer": raw.get("answerTooLateTimer"),
            "lineAssociations": raw.get("lineAssociations"),
            "remoteDestinationProfileName": raw.get("remoteDestinationProfileName"),
        },
    )


# ---------------------------------------------------------------------------
# MOH normalizer (Tier 2 — §2.3 MOH Sources)
# ---------------------------------------------------------------------------

def normalize_moh_source(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM MOH Audio Source to a MigrationObject.

    Preserves raw fields for the MOH mapper to consume.
    (from tier2-enterprise-expansion.md §2.3)
    """
    name = raw.get("name") or ""
    source_file = raw.get("sourceFileName") or ""
    is_default_raw = raw.get("isDefault")
    # AXL returns isDefault as string "true"/"false" or bool
    if isinstance(is_default_raw, str):
        is_default = is_default_raw.lower() == "true"
    else:
        is_default = bool(is_default_raw) if is_default_raw is not None else False
    source_id = raw.get("sourceId") or ""

    return MigrationObject(
        canonical_id=f"moh_source:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "source_file_name": source_file,
            "is_default": is_default,
            "source_id": source_id,
        },
    )


# ---------------------------------------------------------------------------
# Announcement normalizer (Tier 2 — §2.4 Announcements)
# ---------------------------------------------------------------------------

def normalize_announcement(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Announcement to a MigrationObject.

    Preserves name, description, and file name for the announcement mapper.
    (from tier2-enterprise-expansion.md §2.4)
    """
    name = raw.get("name") or ""
    file_name = raw.get("announcementFile") or ""

    return MigrationObject(
        canonical_id=f"announcement:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": raw.get("description") or "",
            "file_name": file_name,
        },
    )


# ---------------------------------------------------------------------------
# Tier 4 informational normalizers (Wave 1: extract + flag, no mappers)
# ---------------------------------------------------------------------------

def normalize_recording_profile(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Recording Profile to informational MigrationObject."""
    name = raw.get("name") or ""
    return MigrationObject(
        canonical_id=f"info_recording:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "recordingCssName": raw.get("recordingCssName") or "",
            "recorderDestination": raw.get("recorderDestination") or "",
        },
    )


def normalize_calling_party_xform(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Calling Party Transformation Pattern."""
    pattern = raw.get("pattern") or ""
    partition = raw.get("routePartitionName") or ""
    return MigrationObject(
        canonical_id=f"info_calling_xform:{pattern}:{partition}" if partition else f"info_calling_xform:{pattern}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pattern": pattern,
            "description": raw.get("description") or "",
            "callingSearchSpaceName": raw.get("callingSearchSpaceName") or "",
            "routePartitionName": partition,
            "callingPartyTransformationMask": raw.get("callingPartyTransformationMask") or "",
            "callingPartyPrefixDigits": raw.get("callingPartyPrefixDigits") or "",
            "digitDiscardInstructionName": raw.get("digitDiscardInstructionName") or "",
        },
    )


def normalize_called_party_xform(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Called Party Transformation Pattern."""
    pattern = raw.get("pattern") or ""
    partition = raw.get("routePartitionName") or ""
    return MigrationObject(
        canonical_id=f"info_called_xform:{pattern}:{partition}" if partition else f"info_called_xform:{pattern}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pattern": pattern,
            "description": raw.get("description") or "",
            "callingSearchSpaceName": raw.get("callingSearchSpaceName") or "",
            "routePartitionName": partition,
            "calledPartyTransformationMask": raw.get("calledPartyTransformationMask") or "",
            "calledPartyPrefixDigits": raw.get("calledPartyPrefixDigits") or "",
            "digitDiscardInstructionName": raw.get("digitDiscardInstructionName") or "",
        },
    )


def normalize_info_device_profile(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM Device Profile (Extension Mobility) — Tier 4 informational.

    Note: NOT the same as the Tier 2 `normalize_device_profile` which creates
    `device_profile:*` objects for the full mapper pipeline. This creates
    `info_device_profile:*` objects for report-only flagging.
    """
    name = raw.get("name") or ""
    return MigrationObject(
        canonical_id=f"info_device_profile:{name}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": raw.get("description") or "",
            "product": raw.get("product") or "",
            "protocol": raw.get("protocol") or "",
        },
    )




def normalize_intercept_candidate(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM intercept candidate signal."""
    dn = raw.get("dn") or ""
    partition = raw.get("partition") or "<None>"
    return MigrationObject(
        canonical_id=f"intercept_candidate:{dn}:{partition}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": raw.get("userid") or "",
            "dn": dn,
            "partition": partition if partition != "<None>" else "",
            "signal_type": raw.get("signal_type") or "unknown",
            "forward_destination": raw.get("forward_destination") or "",
            "voicemail_enabled": raw.get("voicemail_enabled", False),
        },
    )


# ---------------------------------------------------------------------------
# Tier 3: Informational type normalizers (generic factory)
# ---------------------------------------------------------------------------

def _make_info_normalizer(suffix: str):
    """Factory: creates a normalizer for an informational type."""
    if suffix == "app_user":
        name_field = "userid"
    elif suffix == "intercom":
        name_field = "dnorpattern"
    else:
        name_field = "name"

    def normalizer(item: dict, cluster: str = "default") -> MigrationObject | None:
        name_val = item.get(name_field)
        if not name_val:
            return None
        if isinstance(name_val, dict):
            name_val = name_val.get("_value_1", str(name_val))
        return MigrationObject(
            canonical_id=f"info_{suffix}:{name_val}",
            provenance=Provenance(
                source_system="cucm",
                source_id=item.get("pkid", ""),
                source_name=str(name_val),
                cluster=cluster,
                extracted_at=_now(),
            ),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state=item,
        )

    return normalizer


_INFO_SUFFIXES = [
    "region", "srst", "media_resource_group", "media_resource_list",
    "aar_group", "device_mobility_group", "conference_bridge",
    "softkey_template", "ip_phone_service", "intercom",
    "common_phone_config", "phone_button_template",
    "feature_control_policy", "credential_policy",
    "recording_profile", "ldap_directory",
    "app_user", "h323_gateway", "enterprise_params", "service_params",
]


# ---------------------------------------------------------------------------
# Executive/Assistant normalizers
# ---------------------------------------------------------------------------

def normalize_executive_assistant_pair(
    raw: dict, cluster: str = "default",
) -> MigrationObject:
    """Normalize an executive/assistant relationship pair from SQL query."""
    exec_userid = raw.get("executive_userid", "")
    asst_userid = raw.get("assistant_userid", "")
    return MigrationObject(
        canonical_id=f"exec_asst_pair:{exec_userid}:{asst_userid}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "executive_userid": exec_userid,
            "assistant_userid": asst_userid,
            "executive_pkid": raw.get("executive_pkid"),
            "assistant_pkid": raw.get("assistant_pkid"),
        },
    )


def normalize_executive_settings(
    raw: dict, cluster: str = "default",
) -> MigrationObject:
    """Normalize executive/assistant user service subscription."""
    userid = raw.get("userid", "")
    service_name = raw.get("service_name", "")
    role = "EXECUTIVE" if service_name == "Executive" else "EXECUTIVE_ASSISTANT"
    return MigrationObject(
        canonical_id=f"exec_setting:{userid}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": userid,
            "role": role,
            "service_name": service_name,
            "servicetype": raw.get("servicetype"),
        },
    )


# ---------------------------------------------------------------------------
# Post-normalization: DECT network grouping
# ---------------------------------------------------------------------------

def normalize_dect_group(
    store: Any,
    dect_inventory: list[dict[str, str]] | None = None,
) -> list[CanonicalDECTNetwork]:
    """Group DECT handsets by device pool and create CanonicalDECTNetwork objects.

    Post-normalization step — runs after Pass 2 CrossReferenceBuilder so that
    compatibility_tier has been classified on each CanonicalDevice.  Reads all
    devices with compatibility_tier == "dect", groups them by device pool name,
    and creates one CanonicalDECTNetwork per group.

    The mapper (DECTMapper, Task 3) will enrich each network with location refs,
    handset owner resolution, and access codes.

    Args:
        store: MigrationStore instance with normalized + cross-ref'd objects.
        dect_inventory: Optional list of base station dicts from the
            --dect-inventory CLI flag.  Each dict has keys: coverage_zone,
            base_station_mac, base_station_model.  When provided, stations
            whose coverage_zone matches the network's device pool name are
            attached to the CanonicalDECTNetwork.base_stations list.

    Returns:
        List of CanonicalDECTNetwork objects (also written to the store).
    """
    # Build coverage_zone → base station list index for fast lookup
    inventory_by_zone: dict[str, list[dict[str, str]]] = {}
    for entry in (dect_inventory or []):
        zone = entry.get("coverage_zone", "")
        if zone:
            inventory_by_zone.setdefault(zone, []).append(entry)

    # Collect all DECT-tier devices
    dect_by_pool: dict[str, list[CanonicalDevice]] = {}
    for obj in store.query_by_type("device"):
        if not isinstance(obj, CanonicalDevice):
            continue
        if obj.compatibility_tier != DeviceCompatibilityTier.DECT:
            continue
        pool_name = (obj.pre_migration_state or {}).get("cucm_device_pool") or "DEFAULT"
        dect_by_pool.setdefault(pool_name, []).append(obj)

    networks: list[CanonicalDECTNetwork] = []
    for pool_name, devices in dect_by_pool.items():
        network_name = f"DECT-{pool_name}"
        handset_assignments = [
            {"device_canonical_id": d.canonical_id, "cucm_device_name": d.cucm_device_name}
            for d in devices
        ]

        # Attach base stations from inventory whose coverage_zone matches this pool
        base_stations: list[dict] = []
        for entry in inventory_by_zone.get(pool_name, []):
            base_stations.append({
                "mac": entry["base_station_mac"],
                "model": entry["base_station_model"],
                "coverage_zone": entry["coverage_zone"],
            })

        # Derive DECT network model from inventory (first station's model; PENDING if absent)
        network_model = base_stations[0]["model"] if base_stations else "PENDING"

        network = CanonicalDECTNetwork(
            canonical_id=f"dect_network:{pool_name}",
            provenance=Provenance(
                source_system="cucm",
                source_id=pool_name,
                source_name=network_name,
                cluster=devices[0].provenance.cluster if devices[0].provenance else "default",
                extracted_at=_now(),
            ),
            status=MigrationStatus.NORMALIZED,
            network_name=network_name,
            display_name=network_name,
            model=network_model,
            access_code="",
            base_stations=base_stations,
            handset_assignments=handset_assignments,
            pre_migration_state={
                "cucm_device_pool": pool_name,
                "handset_count": len(devices),
                "base_station_count": len(base_stations),
            },
        )
        store.upsert_object(network)
        networks.append(network)

    return networks


# ---------------------------------------------------------------------------
# Registry: maps extractor object types to normalizer functions
# ---------------------------------------------------------------------------

NORMALIZER_REGISTRY: dict[str, callable] = {
    "device_pool": normalize_device_pool,
    "datetime_group": normalize_datetime_group,
    "user": normalize_user,
    "phone": normalize_phone,
    "workspace": normalize_workspace,
    "css": normalize_css,
    "partition": normalize_partition,
    "route_pattern": normalize_route_pattern,
    "translation_pattern": normalize_translation_pattern,
    "hunt_pilot": normalize_hunt_pilot,
    "hunt_list": normalize_hunt_list,
    "line_group": normalize_line_group,
    "cti_route_point": normalize_cti_route_point,
    "call_park": normalize_call_park,
    "pickup_group": normalize_pickup_group,
    "time_schedule": normalize_time_schedule,
    "time_period": normalize_time_period,
    "gateway": normalize_gateway,
    "sip_trunk": normalize_sip_trunk,
    "route_group": normalize_route_group,
    "route_list": normalize_route_list,
    "voicemail_profile": normalize_voicemail_profile,
    "voicemail_pilot": normalize_voicemail_pilot,
    "voicemail_group": normalize_voicemail_group,
    "cucm_location": normalize_cucm_location,
    "button_template": normalize_button_template,
    "softkey_template": normalize_softkey_template,
    "remote_destination": normalize_remote_destination,
    "recording_profile": normalize_recording_profile,
    "calling_party_xform": normalize_calling_party_xform,
    "called_party_xform": normalize_called_party_xform,
    "info_device_profile": normalize_info_device_profile,
    "intercept_candidate": normalize_intercept_candidate,
    "elin_group": normalize_elin_group,
    "geo_location": normalize_geo_location,
    "device_profile": normalize_device_profile,
    "moh_source": normalize_moh_source,
    "announcement": normalize_announcement,
    "executive_assistant_pair": normalize_executive_assistant_pair,
    "executive_settings": normalize_executive_settings,
    **{f"info_{s}": _make_info_normalizer(s) for s in _INFO_SUFFIXES},
}


# ---------------------------------------------------------------------------
# DiscoveryResult.raw_data sub-key → normalizer mapping
# Maps each raw_data path to the normalizer function to call on each item.
# (from Phase 03 DiscoveryResult docstring)
# ---------------------------------------------------------------------------

RAW_DATA_MAPPING: list[tuple[str, str, str]] = [
    # (extractor_key, sub_key, normalizer_registry_key)
    ("locations", "device_pools", "device_pool"),
    ("locations", "datetime_groups", "datetime_group"),
    ("locations", "cucm_locations", "cucm_location"),
    ("users", "users", "user"),
    ("devices", "phones", "phone"),
    # workspace classification happens after phone normalization (see normalize_discovery)
    ("routing", "partitions", "partition"),
    ("routing", "css_list", "css"),
    ("routing", "route_patterns", "route_pattern"),
    ("routing", "gateways", "gateway"),
    ("routing", "sip_trunks", "sip_trunk"),
    ("routing", "route_groups", "route_group"),
    ("routing", "route_lists", "route_list"),
    ("routing", "translation_patterns", "translation_pattern"),
    ("features", "hunt_pilots", "hunt_pilot"),
    ("features", "hunt_lists", "hunt_list"),
    ("features", "line_groups", "line_group"),
    ("features", "cti_route_points", "cti_route_point"),
    ("features", "call_parks", "call_park"),
    ("features", "pickup_groups", "pickup_group"),
    ("features", "time_schedules", "time_schedule"),
    ("features", "time_periods", "time_period"),
    ("voicemail", "voicemail_profiles", "voicemail_profile"),
    ("voicemail", "voicemail_pilots", "voicemail_pilot"),
    ("voicemail", "shared_mailboxes", "voicemail_group"),
    ("templates", "button_templates", "button_template"),
    ("templates", "softkey_templates", "softkey_template"),
    ("remote_destinations", "remote_destinations", "remote_destination"),
    ("tier4", "recording_profiles", "recording_profile"),
    ("tier4", "remote_destination_profiles", "remote_destination"),  # reuses existing normalizer
    ("tier4", "calling_party_transformations", "calling_party_xform"),
    ("tier4", "called_party_transformations", "called_party_xform"),
    ("tier4", "device_profiles", "info_device_profile"),
    ("tier4", "intercept_candidates", "intercept_candidate"),
    ("e911", "elin_groups", "elin_group"),
    ("e911", "geo_locations", "geo_location"),
    ("device_profiles", "device_profiles", "device_profile"),
    ("moh", "moh_sources", "moh_source"),
    ("announcements", "announcements", "announcement"),
    ("features", "executive_assistant_pairs", "executive_assistant_pair"),
    ("features", "executive_settings", "executive_settings"),
    # Tier 3: Informational types (all under "informational" extractor key)
    *[("informational", suffix, f"info_{suffix}") for suffix in _INFO_SUFFIXES],
]
