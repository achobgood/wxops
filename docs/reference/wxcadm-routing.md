# wxcadm -- Routing, PSTN, CDR, Reports, Jobs, Webhooks

Reference for the secondary wxcadm modules that handle call routing infrastructure, PSTN configuration, call detail records, reporting, asynchronous jobs, and webhooks.

Source files:
- `wxcadm/call_routing.py` -- dial plans, trunks, route groups, route lists, translation patterns
- `wxcadm/pstn.py` -- PSTN provider config per location
- `wxcadm/cdr.py` -- call detail record processing
- `wxcadm/reports.py` -- report generation and retrieval
- `wxcadm/jobs.py` -- async job management (number moves, user moves, phone rebuilds)
- `wxcadm/webhooks.py` -- webhook CRUD

---

<!-- Updated by playbook session 2026-03-18 -->
## When to Use wxcadm vs Raw HTTP

| Use wxcadm when | Use raw HTTP when |
|---|---|
| CDR post-processing -- the `Call -> CallLeg -> LegPart` hierarchy with automatic transfer merging is unique to wxcadm and has no raw HTTP equivalent | Call routing CRUD (trunks, route groups, route lists, dial plans, translation patterns) |
| You need the two-phase validate-then-move pattern for `UserMoveJobList` in a single call | PSTN provider configuration per location |
| Object-graph navigation for routing (e.g., `org.call_routing.trunks.get(name=...)`) is more convenient than tracking IDs | Report creation, job management, webhook CRUD |

> **Note:** The playbook uses raw HTTP via `api.session.rest_*()` for standard CRUD operations. All routing, PSTN, report, job, and webhook endpoints are standard Webex REST APIs that work fine with raw HTTP. wxcadm's unique value here is the CDR parsing module (`CallDetailRecords`) which builds a structured call hierarchy from raw CSV records.

---

## Table of Contents

1. [Call Routing](#1-call-routing)
   - [CallRouting (entry point)](#callrouting-entry-point)
   - [Trunks / Trunk](#trunks--trunk)
   - [RouteGroups / RouteGroup](#routegroups--routegroup)
   - [RouteLists / RouteList](#routelists--routelist)
   - [DialPlans / DialPlan](#dialplans--dialplan)
   - [TranslationPatternList / TranslationPattern](#translationpatternlist--translationpattern)
2. [PSTN Configuration](#2-pstn-configuration)
3. [Call Detail Records (CDR)](#3-call-detail-records-cdr)
4. [Reports](#4-reports)
5. [Jobs](#5-jobs)
   - [Number Management Jobs](#number-management-jobs)
   - [User Move Jobs](#user-move-jobs)
   - [Rebuild Phones Jobs](#rebuild-phones-jobs)
6. [Webhooks](#6-webhooks)
7. [wxcadm vs wxc_sdk Comparison](#7-wxcadm-vs-wxc_sdk-comparison)

---

## 1. Call Routing

All call routing objects live under `org.call_routing`, which returns a `CallRouting` instance. The API base path for premise PSTN routing is `/v1/telephony/config/premisePstn/`. Translation patterns use `/v1/telephony/config/callRouting/translationPatterns`.

### CallRouting (entry point)

```python
class CallRouting:
    def __init__(self, org: wxcadm.Org)
```

**Properties** (each returns a freshly-initialized collection -- no caching):

| Property | Returns | Description |
|----------|---------|-------------|
| `trunks` | `Trunks` | All trunks in the org |
| `route_groups` | `RouteGroups` | All route groups in the org |
| `route_lists` | `RouteLists` | All route lists in the org |
| `dial_plans` | `DialPlans` | All dial plans in the org |

**Methods:**

```python
def test(
    self,
    originator: Person | Trunk,
    destination: str,
    orig_number: Optional[str] = None
) -> dict
```

Tests call routing for a given originator and destination. The `originator` must be a `Person` or `Trunk` instance -- the method determines `originatorType` (`USER` or `TRUNK`) automatically. `orig_number` is only used for `TRUNK` originators. Returns the raw API response dict because the response format varies by routing outcome.

API endpoint: `POST /v1/telephony/config/actions/testCallRouting/invoke`

---

### Trunks / Trunk

#### Trunks (collection)

```python
class Trunks(UserList):
    def __init__(self, org: wxcadm.Org)
```

Fetches all trunks on init from `GET /v1/telephony/config/premisePstn/trunks` (items key: `trunks`). Iterable list of `Trunk` instances.

**Methods:**

```python
def get(
    self,
    name: Optional[str] = None,
    id: Optional[str] = None
) -> Optional[Trunk]
```

Find a trunk by name or ID. Raises `ValueError` if both are `None`.

```python
def add_trunk(
    self,
    name: str,
    location: Location | str,
    password: str,
    dual_identity_support: bool,
    type: str,                                    # 'REGISTERING' or 'CERTIFICATE_BASED'
    device_type: Optional[str] = 'Cisco Unified Border Element',
    address: Optional[str] = None,                # required for certificate-based
    domain: Optional[str] = None,                 # required for certificate-based
    port: Optional[int] = None,                   # required for certificate-based
    max_concurrent_calls: Optional[int] = None    # required for certificate-based
) -> bool
```

Creates a new trunk. For `CERTIFICATE_BASED` type, the optional parameters (`address`, `domain`, `port`, `max_concurrent_calls`) are required. Returns `True` on success, `False` otherwise.

#### Trunk (dataclass)

```python
@dataclass_json
@dataclass
class Trunk:
    org: wxcadm.Org
    id: str
    name: str
    location: dict | Location    # resolved to Location in __post_init__
    in_use: bool                 # JSON field: "inUse"
    trunk_type: str              # JSON field: "trunkType" -- 'REGISTERING' or 'CERTIFICATE_BASED'
    dedicated_instance_only: bool  # JSON field: "isRestrictedToDedicatedInstance"
```

**Lazy-loaded detail fields** (populated on first attribute access via `__getattr__`, triggering `GET /v1/telephony/config/premisePstn/trunks/{id}`):

| Attribute | Type | Description |
|-----------|------|-------------|
| `otg_dtg` | `str` | OTG/DTG identifier |
| `lineport` | `str` | Line/Port identifier |
| `used_by_locations` | `list[dict]` | Locations using this trunk for PSTN |
| `pilot_user_id` | `str` | Pilot user ID |
| `outbound_proxy` | `OutboundProxy | None` | Outbound proxy config |
| `sip_auth_user` | `str` | SIP auth username |
| `status` | `str` | Trunk status |
| `response_status` | `list` | Status messages |
| `dual_identity_support` | `bool` | Dual identity flag |
| `device_type` | `str` | Device type |
| `max_calls` | `int` | Max concurrent calls |

**Methods:**

```python
def set_dual_identity_support(self, enabled: bool) -> bool
```

Sets the dual identity support flag. Returns `True` on success. Raises `wxcadm.ApiError` on API failure.

```python
def set_max_calls(self, calls: int) -> bool
```

Sets max concurrent calls. Only supported for `CERTIFICATE_BASED` trunks. Raises `ValueError` for registering trunks.

---

### RouteGroups / RouteGroup

#### RouteGroups (collection)

```python
class RouteGroups(UserList):
    def __init__(self, org: wxcadm.Org)
```

Fetches from `GET /v1/telephony/config/premisePstn/routeGroups` (items key: `routeGroups`).

**Methods:**

```python
def get(
    self,
    id: Optional[str] = None,
    name: Optional[str] = None
) -> Optional[RouteGroup]
```

Find a route group by ID or name.

#### RouteGroup (dataclass)

```python
@dataclass
class RouteGroup:
    org: wxcadm.Org
    id: str
    name: str
    inUse: bool    # whether the route group is used by any location, route list, or dial plan
```

**Properties:**

```python
@property
def trunks(self) -> List[dict]
```

Returns the trunks within the route group with their priorities. Each dict contains trunk details and a `priority` key. Fetches from `GET /v1/telephony/config/premisePstn/routeGroups/{id}` (items key: `localGateways`).

**Methods:**

```python
def add_trunk(
    self,
    trunk: Trunk,
    priority: Union[str, int]    # int, or 'next' / 'with_last'
) -> bool
```

Adds a trunk to the route group. The `priority` parameter accepts:
- An `int` for a specific priority value
- `'next'` to set priority one higher than the current highest
- `'with_last'` to match the current highest priority (equal weight)

Returns `True` on success.

---

### RouteLists / RouteList

#### RouteLists (collection)

```python
class RouteLists(UserList):
    def __init__(self, org: wxcadm.Org)
```

Fetches from `GET /v1/telephony/config/premisePstn/routeLists` (items key: `routeLists`).

**Methods:**

```python
def create(
    self,
    location: Location,
    route_group: RouteGroup,
    name: str
) -> RouteList
```

Creates a new route list and returns the `RouteList` instance.

```python
def get(
    self,
    name: Optional[str] = None,
    id: Optional[str] = None
) -> Optional[RouteList]
```

Find a route list by name or ID. Raises `ValueError` if both are `None`.

#### RouteList (dataclass)

```python
@dataclass
class RouteList:
    org: wxcadm.Org
    id: str
    name: str
    locationId: str       # resolved to Location instance in __post_init__
    locationName: str     # deleted after __post_init__
    routeGroupId: str     # resolved to RouteGroup instance in __post_init__
    routeGroupName: str   # deleted after __post_init__
```

After `__post_init__`, the raw ID/name fields are replaced with:
- `self.location` -- resolved `Location` instance
- `self.route_group` -- resolved `RouteGroup` instance

<!-- Verified via wxcadm source 2026-03-19 --> **Bug:** `__post_init__` calls `self.org.call_routing.route_groups.get_route_group(id=...)` but the `RouteGroups` class only defines `get()`, not `get_route_group()`. This will raise `AttributeError` at runtime when a `RouteList` is instantiated. Workaround: iterate `route_groups` manually or call `.get(id=...)` instead.

**Properties:**

```python
@property
def numbers(self)
```

Returns the numbers assigned to this route list. Fetches from `GET /v1/telephony/config/premisePstn/routeLists/{id}/numbers`.

<!-- Verified via wxcadm source 2026-03-19 --> **Bug:** The `numbers` property calls `response.json()` on the return value of `org.api.get()`, but `org.api.get()` already returns a parsed dict (not a raw `Response` object). This will raise `AttributeError: 'dict' object has no attribute 'json'` at runtime. Workaround: use raw HTTP `GET /v1/telephony/config/premisePstn/routeLists/{id}/numbers` instead.

**Not implemented:** Delete route list (noted as TODO in source).

---

### DialPlans / DialPlan

#### DialPlans (collection)

```python
class DialPlans(UserList):
    def __init__(self, org: wxcadm.Org)
```

Fetches from `GET /v1/telephony/config/premisePstn/dialPlans` (items key: `dialPlans`).

No `get()` method is defined on the collection. To find a specific dial plan, iterate manually:

```python
dp = next((d for d in org.call_routing.dial_plans if d.name == "My Plan"), None)
```

#### DialPlan (dataclass)

```python
@dataclass
class DialPlan:
    org: wxcadm.Org
    id: str
    name: str
    routeId: str       # ID of the route (trunk, route group, or route list)
    routeName: str     # name of the route
    routeType: str     # type of the route
```

**Properties:**

```python
@property
def patterns(self) -> list
```

Returns the dial patterns within the dial plan. Fetches from `GET /v1/telephony/config/premisePstn/dialPlans/{id}/dialPatterns` (items key: `dialPatterns`).

**Methods:**

```python
def add_pattern(self, pattern: str) -> bool
```

Adds a dial pattern. Sends `PUT` with action `ADD`. Returns `True` on success.

```python
def delete_pattern(self, pattern: str) -> bool
```

Deletes an existing dial pattern. Sends `PUT` with action `DELETE`. Returns `True` on success.

---

### TranslationPatternList / TranslationPattern

Translation patterns can exist at org level or location level.

#### TranslationPatternList (collection)

```python
class TranslationPatternList(UserList):
    def __init__(
        self,
        org: wxcadm.Org,
        location: Optional[Location] = None
    )
```

If `location` is provided, fetches patterns scoped to that location via `limitToLocationId` param. Otherwise fetches all org-level patterns.

API endpoint: `GET /v1/telephony/config/callRouting/translationPatterns`

**Methods:**

```python
def refresh(self) -> list
```

Re-fetches the list from the API. Returns the updated data list.

```python
def get(
    self,
    id: Optional[str] = None,
    name: Optional[str] = None,
    match_pattern: Optional[str] = None,
    replacement_pattern: Optional[str] = None
) -> Optional[TranslationPattern]
```

Finds a translation pattern matching ALL provided criteria (AND logic). Any parameter left as `None` is treated as a wildcard.

```python
def create(
    self,
    name: str,
    match_pattern: str,
    replacement_pattern: str,
    location: Optional[Location] = None
) -> TranslationPattern
```

Creates a new translation pattern. Scope logic:
- If `location` argument is provided, creates at that location's scope
- If no `location` argument but the list was initialized with a location, uses the list's location
- Otherwise creates at org scope

Returns the newly created `TranslationPattern` instance (fetched back from API after creation).

#### TranslationPattern

```python
class TranslationPattern:
    def __init__(
        self,
        org: wxcadm.Org,
        location: Optional[Location] = None,
        config: Optional[dict] = None
    )
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Pattern name |
| `match_pattern` | `str` | The pattern to match (from `matchingPattern`) |
| `replacement_pattern` | `str` | The replacement (from `replacementPattern`) |
| `location` | `Location | None` | Associated location, or `None` for org-level |
| `level` | `str | None` | `'Location'` or `None` |

**Methods:**

```python
def update(
    self,
    name: Optional[str] = None,
    match_pattern: Optional[str] = None,
    replacement_pattern: Optional[str] = None
) -> bool
```

Updates the translation pattern. Only provided fields are changed; `None` fields keep current values. Uses location-scoped or org-scoped URL based on `self.location`. Returns `True` on success.

```python
def delete(self) -> bool
```

Deletes the translation pattern. Returns `True` on success.

---

## 2. PSTN Configuration

PSTN config is location-scoped, accessed via `LocationPSTN`.

### LocationPSTN

```python
class LocationPSTN:
    def __init__(self, location: wxcadm.Location)
```

On init, fetches the current PSTN connection for the location from `GET /v1/telephony/pstn/locations/{id}/connection`. If no PSTN is configured, `self.provider` is set to `None` (does not raise).

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `location` | `Location` | The associated location |
| `available_providers` | `PSTNProviderList` | Available PSTN providers for this location |
| `provider` | `PSTNProvider | None` | Currently configured provider |
| `type` | `str` | PSTN connection type (e.g. `pstnConnectionType` value) |

**Methods:**

```python
def set_provider(
    self,
    provider: PSTNProvider | str | RouteGroup | Trunk
) -> bool
```

Sets the PSTN provider for the location. Accepts:
- `PSTNProvider` instance -- sets by provider ID
- `str` -- looked up as a provider ID in `available_providers`
- `Trunk` -- sets `premiseRouteType: 'TRUNK'` with the trunk ID
- `RouteGroup` -- sets `premiseRouteType: 'ROUTE_GROUP'` with the route group ID

Returns `True` on success.

API endpoint: `PUT /v1/telephony/pstn/locations/{id}/connection`

### PSTNProvider (dataclass)

```python
@dataclass_json
@dataclass
class PSTNProvider:
    id: str
    name: str                  # JSON field: "displayName"
    services: list             # JSON field: "pstnServices"
```

### PSTNProviderList (collection)

```python
class PSTNProviderList(UserList):
    def __init__(self, location: wxcadm.Location)
```

Fetches available connection options from `GET /v1/telephony/pstn/locations/{id}/connectionOptions`.

**Methods:**

```python
def get(
    self,
    id: Optional[str] = None,
    name: Optional[str] = None
) -> Optional[PSTNProvider]
```

Find a provider by ID or name.

---

## 3. Call Detail Records (CDR)

The CDR module processes raw CDR records into a structured call hierarchy. **It does not fetch CDRs from the API directly** -- records must be obtained externally (typically via the Reports module's `cdr_report()` method) and passed in as a list of dicts with raw CSV field names.

### Data Model Hierarchy

```
CallDetailRecords
  -> calls: list[Call]
       -> legs: list[CallLeg]
            -> parts: list[LegPart]
```

### CallDetailRecords (entry point)

```python
class CallDetailRecords:
    def __init__(
        self,
        records: list,                          # list of dicts with raw CDR field names
        webex: Optional[wxcadm.Webex] = None    # enables user/endpoint lookup
    )
```

On init, processes all records into `Call` objects and merges transferred calls based on matching part IDs within a 24-hour window.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `records` | `list` | The raw records passed in |
| `webex` | `Webex | None` | Webex connection for resolving user IDs |
| `calls` | `list[Call]` | Unordered list of processed calls |

**Properties:**

```python
@property
def calls_sorted(self) -> list[Call]
```

Returns calls sorted by start time (ascending).

**Methods:**

```python
def get_call_by_correlation_id(self, correlation_id: str) -> Optional[Call]
```

```python
def get_call_by_part_call_id(self, part_call_id: str) -> Optional[Call]
```

```python
def get_abandoned_calls(self) -> list[Call]
```

Returns calls where the caller hung up in a call queue before an agent answered.

```python
def get_pstn_calls(self) -> list[Call]
```

Returns calls with at least one PSTN (off-net) leg.

```python
def get_voicemail_deposit_calls(self) -> list[Call]
```

Returns calls where the caller was sent to voicemail.

### Call

```python
class Call:
    def __init__(self, correlation_id: str)
```

**Attributes:**
- `id` (`str`) -- the correlation ID
- `legs` (`list[CallLeg]`) -- the call legs
- `correlation_ids` (`list[str]`) -- all correlation IDs (includes merged transfers)

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `start_time` | `datetime` | Earliest leg start time |
| `end_time` | `datetime` | Latest leg end time |
| `duration` | `str` | Formatted duration (HH:MM:SS) |
| `calling_number` | `str` | Calling number from the first sorted leg |
| `leg_count` | `int` | Number of legs |
| `legs_sorted` | `list[CallLeg]` | Legs sorted by start time |
| `part_ids` | `set` | All part IDs in the call |
| `transfer_ids` | `list` | All transfer-related call IDs |
| `answered_legs` | `int` | Count of answered legs |
| `has_queue_leg` | `bool` | Whether any leg involves a call queue |
| `has_pstn_leg` | `bool` | Whether any leg is PSTN |
| `has_vm_deposit_leg` | `bool` | Whether any leg is a voicemail deposit |
| `is_queue_abandon` | `bool` | Caller hung up in queue without agent answer |

**Methods:**

```python
def add_record(self, record: dict)
```

Adds a CDR record to the call, either to an existing leg (if part IDs match) or by creating a new leg.

### CallLeg

```python
class CallLeg:
    def __init__(self)
```

Contains `parts: list[LegPart]`.

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `start_time` | `datetime` | First part's start time |
| `end_time` | `datetime` | End time (accounts for transfers) |
| `pstn_leg` | `bool` | Whether this leg is PSTN |
| `duration` | `int` | Duration in seconds |
| `ring_duration` | `int` | Ring time in seconds |
| `transfer_ids` | `list` | Transfer-related call IDs |
| `orig_part` | `LegPart | None` | Originating part |
| `term_part` | `LegPart | None` | Terminating part |
| `is_queue_leg` | `bool` | Terminating user type is `CALLCENTERPREMIUM` |
| `is_aa_leg` | `bool` | Terminating user type is `AUTOMATEDATTENDANTVIDEO` |
| `is_agent_leg` | `bool` | User type `USER` with redirect reason `CALLQUEUE` |
| `is_vm_deposit` | `bool` | Called line is `Voice Portal Voice Messaging Group` |
| `label` | `str` | Display label for the leg |
| `calling_number` | `str` | Calling party number |
| `leg_description` | `str` | "From X to Y" description |
| `new_leg_description` | `str` | Enhanced description with reasons |
| `in_reason` | `str | None` | Why the leg was received (e.g. `SIP Inbound`, redirect reason) |
| `out_reason` | `str | None` | Why the leg originated (e.g. `Queue Callback`) |
| `answered` | `bool` | Whether any part was answered |
| `answered_label` | `str` | `'Answered'` or `'Unanswered'` |
| `parts_id` | `list` | All local and remote IDs from parts |
| `recorded` | `bool` | Whether any part has a successful recording |

**Methods:**

```python
def add_part(self, record: dict) -> LegPart
```

### LegPart

```python
class LegPart:
    def __init__(self, record: dict)
```

Wraps a single CDR record. Key attributes parsed from the raw dict:

| Attribute | Source Field | Type |
|-----------|-------------|------|
| `start_time` | `Start time` | `datetime` |
| `end_time` | `Release time` | `datetime` |
| `answer_time` | `Answer time` | `datetime | None` |
| `answered` | `Answered` | `bool` |
| `local_id` | `Local call ID` | `str | None` |
| `remote_id` | `Remote call ID` | `str | None` |
| `direction` | `Direction` | `str` |
| `calling_line_id` | `Calling line ID` | `str` |
| `called_line_id` | `Called line ID` | `str` |
| `dialed_digits` | `Dialed digits` | `str` |
| `user_number` | `User number` | `str` |
| `called_number` | `Called number` | `str` |
| `calling_number` | `Calling number` | `str` |
| `redirecting_number` | `Redirecting number` | `str` |
| `location_name` | `Location` | `str` |
| `user_type` | `User type` | `str` |
| `user` | `User` | `str` |
| `call_type` | `Call type` | `str` |
| `duration` | `Duration` | `str` |
| `time_offset` | `Site timezone` | `str` |
| `releasing_party` | `Releasing party` | `str` |
| `original_reason` | `Original reason` | `str` |
| `redirect_reason` | `Redirect reason` | `str` |
| `related_reason` | `Related reason` | `str` |
| `outcome` | `Call outcome` | `str` |
| `outcome_reason` | `Call outcome reason` | `str` |
| `ring_duration` | `Ring duration` | `str` |
| `device_owner_uuid` | `Device owner UUID` | `str` |
| `recording_platform` | `Call Recording Platform Name` | `str` |
| `recording_result` | `Call Recording Result` | `str` |
| `recording_trigger` | `Call Recording Trigger` | `str` |
| `device_mac` | `Device MAC` or `Device Mac` | `str` |
| `transfer_time` | `Call transfer time` | `datetime | None` |
| `transfer_related_call_id` | `Transfer related call ID` | `str` |
| `pstn_inbound` | derived | `bool` -- `True` if call type is `SIP_INBOUND` |
| `internal_call` | derived | `bool` -- `True` if call type is `SIP_ENTERPRISE` |
| `pstn_outbound` | derived | `bool` -- `True` if call type is `SIP NATIONAL` or `SIP_INTERNATIONAL` |

---

## 4. Reports

Report management lives under `org.reports`, which returns a `ReportList` instance.

### ReportList (collection)

```python
class ReportList(UserList):
    def __init__(self, org: wxcadm.Org)
```

Fetches existing reports on init from `GET /v1/reports`.

**Properties:**

```python
@property
def templates(self) -> list[ReportTemplate]
```

Lazy-loaded list of available report templates from `GET /v1/report/templates`.

**Methods:**

```python
def get_template(self, id: int) -> Optional[ReportTemplate]
```

Find a template by ID.

```python
def list_reports(self) -> list[Report]
```

Returns the current list of reports. Note: only shows API-created reports, not Control Hub reports.

```python
def create_report(
    self,
    template: ReportTemplate,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    site_list: Optional[list] = None
) -> Report
```

Creates a new report. Arguments depend on the template's `validations`.

```python
def delete_report(self, report_id: str) -> bool
```

Deletes a report. Returns `True` on success, `False` on exception.

```python
def report_status(self, report_id: str) -> Optional[str]
```

Returns the current status string of a report (triggers a refresh).

```python
def get_report_lines(self, report_id: str) -> Optional[list]
```

Downloads and returns the report lines as a list.

```python
def cdr_report(
    self,
    start: Optional[str] = None,    # YYYY-MM-DD
    end: Optional[str] = None,      # YYYY-MM-DD
    days: Optional[int] = None
) -> Report | bool
```

Shortcut to create a "Calling Detailed Call History" report. Must provide either `start`/`end` or `days` (not both). When using `days`, the end date is set to yesterday. Returns the `Report` instance, or `False` if the CDR template is not found.

### Report

```python
class Report:
    def __init__(
        self,
        org: wxcadm.Org,
        id: Optional[str] = None,
        config: Optional[dict] = None
    )
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Report ID |
| `title` | `str` | Report title |
| `service` | `str` | Associated Webex service |
| `start_date` | `str` | Report period start |
| `end_date` | `str` | Report period end |
| `site_list` | `str` | Webex Meetings site list |
| `created` | `str` | Creation date |
| `created_by` | `str` | Creator ID |
| `scheduled_from` | `str` | `'API'` or `'Control Hub'` |
| `download_url` | `str | None` | URL to download the report |

**Properties:**

```python
@property
def status(self) -> str
```

Returns the current status. Automatically calls `refresh()` first.

**Methods:**

```python
def refresh(self)
```

Re-fetches report details from the API.

```python
def get_report_lines(self) -> list
```

Downloads the report. Handles both ZIP and plain-text content types. Returns lines as a list of strings. No further parsing is done -- the caller must split/clean lines.

### ReportTemplate

```python
class ReportTemplate:
    def __init__(self, config: dict)
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Template ID |
| `title` | `str` | Template title |
| `service` | `str` | Webex service |
| `max_days` | `int` | Maximum days the report can span |
| `identifier` | `str` | Additional identifiers |
| `validations` | `list` | Validation rules for creating a report |

---

## 5. Jobs

Three async job types are supported, all following the same pattern: a job list class (fetches/creates jobs) and a job class (tracks status).

### Number Management Jobs

For moving phone numbers between locations.

#### NumberManagementJobList

```python
class NumberManagementJobList(UserList):
    def __init__(self, org: wxcadm.Org)
```

API endpoint: `v1/telephony/config/jobs/numbers/manageNumbers`

**Methods:**

```python
def refresh(self) -> bool
```

```python
def get(self, id: str) -> Optional[NumberManagementJob]
```

```python
def create(
    self,
    job_type: str,                        # only "move" supported
    target_location: Location | str,
    numbers: list[str]                    # list of phone numbers to move
) -> NumberManagementJob
```

Creates a number move job. Validates numbers against `org.numbers` first. Raises `KeyError` if a number is not found in the org.

**Limitation:** The API currently supports only a single number per job, despite the list parameter.

#### NumberManagementJob

```python
class NumberManagementJob:
    def __init__(self, org: wxcadm.Org, id: str, details: Optional[dict] = None)
```

**Properties:**

```python
@property
def completed(self) -> bool
```

Checks if `latestExecutionStatus == 'COMPLETED'`. Refreshes details on each call.

```python
@property
def success(self) -> bool
```

Checks counts: `True` if `numbersFailed == 0` and `numbersMoved + numbersDeleted == totalNumbers`. Should only be checked after `completed` is `True`.

---

### User Move Jobs

For moving users between locations.

#### UserMoveJobList

```python
class UserMoveJobList(UserList):
    def __init__(self, org: wxcadm.Org)
```

API endpoint: `v1/telephony/config/jobs/person/moveLocation`

**Methods:**

```python
def refresh(self) -> bool
```

```python
def get(self, id: str) -> Optional[UserMoveJob]
```

```python
def create(
    self,
    target_location: Location | str,
    people: list[Person],               # max 100
    validate_only: Optional[bool] = False
) -> tuple[UserMoveValidationResults, UserMoveJob | None]
```

Two-phase process:
1. **Validation** -- validates the first user in the list. If validation fails (`errors` present), the move is not attempted.
2. **Move** -- if validation passes and `validate_only` is `False`, creates the actual move job.

Returns a tuple of `(UserMoveValidationResults, UserMoveJob | None)`. The job is `None` if validation failed or `validate_only` was `True`.

Raises `ValueError` if more than 100 people are provided.

#### UserMoveJob

```python
class UserMoveJob:
    def __init__(self, org: wxcadm.Org, id: str, details: Optional[dict] = None)
```

**Properties:**

```python
@property
def completed(self) -> bool
```

Checks `latestExecutionStatus == 'COMPLETED'`.

```python
@property
def success(self) -> bool
```

Checks `failed == 0` and `moved == totalMoves`.

#### UserMoveValidationResults

```python
class UserMoveValidationResults:
    def __init__(self)
```

**Attributes:**
- `messages` (`list[dict]`) -- each dict has `severity` (`'error'` or `'impact'`), `code`, and `message`

**Properties:**

```python
@property
def passed(self) -> bool
```

`True` if no messages have severity `'error'`.

**Methods:**

```python
def add_message(self, severity: str, code: Optional[str] = None, message: Optional[str] = None) -> bool
```

---

### Rebuild Phones Jobs

For triggering phone configuration rebuilds at a location.

#### RebuildPhonesJobList

```python
class RebuildPhonesJobList(UserList):
    def __init__(self, org: wxcadm.Org)
```

API endpoint: `v1/telephony/config/jobs/devices/rebuildPhones`

**Methods:**

```python
def refresh(self) -> bool
```

```python
def get(self, id: str) -> Optional[RebuildPhonesJob]
```

```python
def create(self, location: Location | str) -> RebuildPhonesJob
```

Creates a rebuild phones job for a given location. Only location-level rebuilds are supported.

#### RebuildPhonesJob

```python
class RebuildPhonesJob:
    def __init__(self, org: wxcadm.Org, id: str, details: Optional[dict] = None)
```

**Properties:**

```python
@property
def completed(self) -> bool
```

```python
@property
def device_count(self) -> int
```

Returns the number of devices included in the rebuild job.

<!-- Verified via wxcadm source 2026-03-19 --> `RebuildPhonesJob` does not have a `success` property unlike the other job types (`NumberManagementJob` and `UserMoveJob` both have one). The `completed` property's docstring incorrectly references a `success` attribute that was never implemented. To check success, inspect `self.details` dict directly after `completed` returns `True` (look for `deviceCount` and execution status fields).

---

## 6. Webhooks

Webhook management is accessed via `org.webhooks`, returning a `Webhooks` instance.

### Webhooks (collection)

```python
class Webhooks(UserList):
    def __init__(self, org: wxcadm.Org)
```

Fetches all webhooks from `GET /v1/webhooks` and filters to the current org.

Note: Uses `self.org._parent.api` (the Webex-level API) rather than `self.org.api`, because webhooks are a platform-level resource.

**Properties:**

```python
@property
def active(self) -> list[Webhook]
```

Returns only webhooks with status `'active'`.

```python
@property
def inactive(self) -> list[Webhook]
```

Returns only webhooks with status `'inactive'`.

**Methods:**

```python
def add(
    self,
    name: str,
    url: str,
    resource: str,
    event: str,
    filter: str = None,
    secret: str = None,
    owner: str = None
) -> bool
```

Creates a new webhook. See [Webex webhook docs](https://developer.webex.com/docs/webhooks) for valid `resource`, `event`, and `filter` values. Returns `True` on success, `False` otherwise.

### Webhook (dataclass)

```python
@dataclass
class Webhook:
    api: wxcadm.WebexApi
    orgId: str
    appId: str
    id: str
    name: str
    targetUrl: str
    resource: str
    event: str
    status: str          # 'active' or 'inactive'
    created: str
    createdBy: str
    ownedBy: str
    filter: Optional[str] = None
    secret: Optional[str] = None
```

**Methods:**

All update methods send a full `PUT` to `v1/webhooks/{id}` with all fields (the API requires a complete payload on update).

```python
def delete(self) -> bool
```

Deletes the webhook.

```python
def change_url(self, url: str) -> bool
```

Changes the target URL.

```python
def change_name(self, name: str) -> bool
```

Changes the webhook name.

```python
def change_secret(self, secret: str) -> bool
```

Changes the secret value for signature generation.

```python
def change_owner(self, owner: str) -> bool
```

Changes the webhook owner.

```python
def deactivate(self) -> bool
```

Sets status to `'inactive'`. Returns `True` even if already inactive.

```python
def activate(self) -> bool
```

Sets status to `'active'`. Returns `True` even if already active.

---

## 7. wxcadm vs wxc_sdk Comparison

<!-- Verified via wxc_sdk v1.30.0 source 2026-03-19 -->

| Feature Area | wxcadm | wxc_sdk |
|-------------|--------|---------|
| **Trunks** | `org.call_routing.trunks` -- full CRUD, lazy detail loading | `api.telephony.prem_pstn.trunk` -- similar CRUD via Webex API |
| **Route Groups** | `org.call_routing.route_groups` -- list, get, add trunk to group | `api.telephony.prem_pstn.route_group` -- full CRUD |
| **Route Lists** | `org.call_routing.route_lists` -- list, get, create (no delete) | `api.telephony.prem_pstn.route_list` -- full CRUD including delete |
| **Dial Plans** | `org.call_routing.dial_plans` -- list, pattern add/delete (no collection `get()`) | `api.telephony.prem_pstn.dial_plan` -- full CRUD |
| **Translation Patterns** | `TranslationPatternList` -- org or location scope, full CRUD | `api.telephony.call_routing.tp` -- similar scope and CRUD |
| **Call Routing Test** | `org.call_routing.test()` | `api.telephony.test_call_routing()` |
| **PSTN** | `LocationPSTN` -- get/set provider per location | Covered under location telephony settings |
| **CDR** | `CallDetailRecords` -- post-processing class, records passed in externally | No direct equivalent; CDRs obtained via reports or analytics API |
| **Reports** | `ReportList` -- template-based report creation with `cdr_report()` shortcut | `api.reports` -- similar template-based approach |
| **Jobs (Number Move)** | `NumberManagementJobList` -- move only, single number limit | `api.telephony.jobs.manage_numbers` -- similar |
| **Jobs (User Move)** | `UserMoveJobList` -- validate-then-move pattern, max 100 users | `api.telephony.jobs.move_users` -- similar |
| **Jobs (Rebuild Phones)** | `RebuildPhonesJobList` -- location-level only | `api.telephony.jobs.rebuild_phones` -- similar |
| **Webhooks** | `Webhooks` -- full CRUD with activate/deactivate | `api.webhook` -- full CRUD |

**Key architectural differences:**

- **wxcadm** uses `UserList` subclasses throughout, so collections are iterable lists that also have `.get()` methods. Properties often trigger API calls on access (lazy loading).
- **wxc_sdk** uses explicit list/get/create/update/delete methods on API wrapper classes. Data is returned as typed dataclass models.
- **wxcadm CDR processing** is unique -- it builds a `Call -> CallLeg -> LegPart` hierarchy from raw CSV records with automatic transfer merging. wxc_sdk does not have an equivalent post-processing layer.
- **wxcadm job validation** (particularly `UserMoveJobList.create`) performs a two-phase validate-then-execute pattern in a single method call, returning both validation results and the job. wxc_sdk typically separates these concerns.

---

## API Endpoint Summary

| Module | Endpoint Pattern |
|--------|-----------------|
| Trunks | `v1/telephony/config/premisePstn/trunks` |
| Route Groups | `v1/telephony/config/premisePstn/routeGroups` |
| Route Lists | `v1/telephony/config/premisePstn/routeLists` |
| Dial Plans | `v1/telephony/config/premisePstn/dialPlans` |
| Translation Patterns | `v1/telephony/config/callRouting/translationPatterns` |
| Translation Patterns (location) | `v1/telephony/config/locations/{id}/callRouting/translationPatterns` |
| Call Routing Test | `v1/telephony/config/actions/testCallRouting/invoke` |
| PSTN Connection | `v1/telephony/pstn/locations/{id}/connection` |
| PSTN Connection Options | `v1/telephony/pstn/locations/{id}/connectionOptions` |
| Reports | `v1/reports` |
| Report Templates | `v1/report/templates` |
| Number Move Jobs | `v1/telephony/config/jobs/numbers/manageNumbers` |
| User Move Jobs | `v1/telephony/config/jobs/person/moveLocation` |
| Rebuild Phones Jobs | `v1/telephony/config/jobs/devices/rebuildPhones` |
| Webhooks | `v1/webhooks` |

---

## See Also

- [call-routing.md](call-routing.md) — wxc_sdk call routing APIs (trunks, route groups, route lists, dial plans, translation patterns)
- [reporting-analytics.md](reporting-analytics.md) — wxc_sdk reporting and CDR access patterns for comparison with wxcadm's CDR post-processing
