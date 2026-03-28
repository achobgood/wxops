<!-- Updated by playbook session 2026-03-18 -->
<!-- Verified via CLI Batches 1-4, 2026-03-19 through 2026-03-21 -->

# Reporting & Analytics

CDR feed, report templates, report generation/download, and call quality/queue/AA statistics for Webex Calling.

## Sources

- `wxc_sdk.cdr` — SDK source for Detailed CDR API (`../wxc_sdk_reference/wxc_sdk/cdr/__init__.py`)
- `wxc_sdk.reports` — SDK source for Reports API (`../wxc_sdk_reference/wxc_sdk/reports/__init__.py`)
- [Exploring the Webex Calling Reports and Analytics APIs](https://developer.webex.com/blog/exploring-the-webex-calling-reports-and-analytics-apis)
- [Webex CDR field reference](https://help.webex.com/en-us/article/nmug598/Reports-for-Your-Cloud-Collaboration-Portfolio)

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark-admin:calling_cdr_read` | Access Detailed Call History (CDR feed/stream). Authenticating user must also have the "Webex Calling Detailed Call History API access" admin role enabled in Control Hub. |
| `analytics:read_all` | Access Report Templates and Reports APIs. Authenticating user must be a read-only or full administrator. |
| `spark-admin:locations_read` | Filter CDR queries by location name. |

**License requirement:** The Reports API requires the **Pro Pack for Cisco Webex** license on the organization.

---

## 1. Detailed Call History (CDR) API

### Endpoint

| Property | Value |
|----------|-------|
| Base URL (commercial) | `https://analytics-calling.webexapis.com` |
| Base URL (government) | `https://analytics-calling-gov.webexapis.com` |
| CDR Feed path | `/v1/cdr_feed` |
| CDR Stream path | `/v1/cdr_stream` |
| Method | `GET` |

- **CDR Feed** (`cdr_feed`) — Pull records for a specific time window. Best for batch/historical pulls.
- **CDR Stream** (`cdr_stream`) — Returns records based on their **insertion time** into the Webex Calling cloud (when data became available), vs CDR Feed which uses the call's actual start/end time. CDR Stream is better for near-real-time monitoring since it returns records as soon as they are ingested, regardless of when the call occurred. CDR Feed is better for historical/batch pulls where you want all calls within a specific time window. <!-- Verified via OpenAPI spec 2026-03-19: cdr_feed filters by call time period, cdr_stream filters by insertion time into Webex cloud -->

If the region's servers do not host the organization's data, an **HTTP 451** is returned. The response body contains the correct regional endpoint to use instead.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `startTime` | ISO 8601 datetime | Yes | Start of time window (report time = call finish time). Must be between 5 minutes ago and 30 days ago. |
| `endTime` | ISO 8601 datetime | Yes | End of time window. Must be after `startTime`. |
| `locations` | comma-separated strings | No | Location names (as shown in Control Hub). Up to 10. |
| `max` | int | No | Results per page (pagination). |

### Time Range Constraints

- **Oldest data:** 30 days prior to current UTC time.
- **Newest data:** 5 minutes ago (minimum latency before records appear).
- **Maximum window per request:** 12 hours (the gap between `startTime` and `endTime`).
- **Data availability:** A call that ends at 9:46 AM is available starting at 9:51 AM and remains for 30 days.
- **Data generation lag:** CDR records may take up to 24 hours after call completion to appear.

### Rate Limits

- **1 initial request per minute** per user token.
- **Up to 10 additional pagination requests per minute** per user token.

### Pagination

The API returns paginated results via the standard `items` key. The SDK method `session.follow_pagination()` handles automatic page traversal.

### SDK Method

```python
DetailedCDRApi.get_cdr_history(
    start_time: Union[str, datetime] = None,   # Default: ~48 hours ago
    end_time: Union[str, datetime] = None,      # Default: ~5 minutes ago
    locations: list[str] = None,                # Up to 10 location names
    host: str = 'analytics-calling.webexapis.com',
    stream: bool = False,                       # True = use cdr_stream instead of cdr_feed
    **params
) -> Generator[CDR, None, None]
```

When `start_time` and `end_time` are omitted, the SDK defaults to a window of approximately 48 hours ago through 5 minutes ago.

**Usage example:**

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens='<access_token>')

# Pull last 2 hours of CDRs
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc) - timedelta(minutes=5)
start = end - timedelta(hours=2)

for cdr in api.cdr.get_cdr_history(start_time=start, end_time=end):
    print(f"{cdr.start_time} | {cdr.direction} | {cdr.calling_number} -> {cdr.called_number} | {cdr.duration}s")
```

### CLI Examples

```bash
# Pull CDR feed for a 2-hour window (batch/historical)
wxcli cdr list \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z"

# Pull CDR feed filtered by location
wxcli cdr list \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" \
  --locations "San Jose,Austin"

# Pull CDR feed with JSON output for scripting
wxcli cdr list \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" \
  -o json

# Pull CDR feed with pagination control
wxcli cdr list \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" \
  --max 500 --limit 100

# Pull near-real-time CDR stream
wxcli cdr list-cdr_stream \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z"

# CDR stream filtered by location with JSON output
wxcli cdr list-cdr_stream \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" \
  --locations "Denver" -o json
```

### CDR Record Fields

The `CDR` model (class `wxc_sdk.cdr.CDR`) contains 55+ fields. Field names arrive from the API in space-separated format (e.g., "Answer time") and are normalized to snake_case by the SDK.

#### Core Call Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `start_time` | `datetime` | Call start time (UTC). Answer time may be slightly after. |
| `answer_time` | `datetime` | Time the call was answered (UTC). |
| `release_time` | `datetime` | Time the call finished (UTC). |
| `duration` | `int` | Call length in seconds. |
| `ring_duration` | `int` | Ringing time before answer/timeout, in seconds. |
| `hold_duration` | `int` | Total hold time in seconds (floor value). |
| `answered` | `bool` | Whether this call leg was answered. |
| `answer_indicator` | `str` | `Yes`, `No`, or `Yes-PostRedirection`. |
| `direction` | `CDRDirection` | `ORIGINATING` or `TERMINATING`. |
| `call_type` | `CDRCallType` | See enum values below. |
| `call_outcome` | `str` | `Success`, `Failure`, or `Refusal`. |
| `call_outcome_reason` | `str` | Detailed reason (e.g., `Normal`, `UserBusy`, `NoAnswer`, `CallRejected`, `UnassignedNumber`, `SIP408`, `AdminCallBlock`, etc.). |
| `releasing_party` | `str` | `Local`, `Remote`, or `Unknown`. |

#### Number / Identity Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `calling_number` | `str` | Incoming: calling party number. Outgoing: user's number. |
| `called_number` | `str` | Incoming: user's number. Outgoing: called party number. |
| `calling_line_id` | `str` | Incoming: calling party line ID. Outgoing: user's line ID. |
| `called_line_id` | `str` | Incoming: user's line ID. Outgoing: called party line ID. |
| `dialed_digits` | `str` | Raw keypad digits before pre-translations. Originating calls only. |
| `user` | `str` | The user who made or received the call. |
| `user_number` | `str` | User's E.164 number (or extension if no number assigned). |
| `user_type` | `CDRUserType` | See enum values below. |
| `user_uuid` | `str` | Unique user identifier across Cisco products. |
| `caller_id_number` | `str` | Presentation number based on caller ID settings in Control Hub. |
| `external_caller_id_number` | `str` | Set when external caller ID is location number or org number (not direct line). |
| `redirecting_number` | `str` | Last redirecting number (for transferred/forwarded calls). |
| `redirecting_party_uuid` | `str` | UUID of the last redirecting party. |
| `original_called_party_uuid` | `str` | UUID of the first redirecting party (alias: `Original Called Party UUID`). |

#### Session / Correlation IDs

| SDK Field | Type | Description |
|-----------|------|-------------|
| `call_id` | `str` | SIP Call ID. Share with Cisco TAC for troubleshooting. |
| `correlation_id` | `str` | Ties together multiple call legs of the same session. |
| `local_session_id` | `str` | UUID from originating user agent (alias: `local_sessionid`). |
| `remote_session_id` | `str` | UUID from terminating user agent (alias: `remote_sessionid`). |
| `final_local_session_id` | `str` | Local Session ID value at call end (alias: `final_local_sessionid`). |
| `final_remote_session_id` | `str` | Remote Session ID value at call end (alias: `final_remote_sessionid`). |
| `local_call_id` | `str` | Used with Remote call ID to correlate CDR legs. |
| `remote_call_id` | `str` | Used with Local call ID to identify remote CDR of a leg. |
| `network_call_id` | `str` | Same value = same call leg across CDRs. |
| `related_call_id` | `str` | Call ID of a call created by this call (service activation). |
| `transfer_related_call_id` | `str` | Call ID of the other party in a transfer. |
| `interaction_id` | `str` | Correlates CDRs linked by service interaction (e.g., consult + transfer). |

#### Routing / Redirect Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `original_reason` | `CDROriginalReason` | Why call was originally redirected. |
| `redirect_reason` | `CDRRedirectReason` | Why call was redirected at this step. |
| `related_reason` | `CDRRelatedReason` | Service-level reason (transfer, forward, park, pickup, etc.). |
| `route_group` | `str` | Route group for outbound calls via premises PSTN. Originating records only. |
| `route_list_calls_overage` | `str` | Number of bursting calls over licensed volume (alias: `Route list calls overage`). |

#### Client / Device Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `client_type` | `CDRClientType` | See enum values below. |
| `client_version` | `str` | Client app version. |
| `os_type` | `str` | Operating system of the app. |
| `model` | `str` | Device model type. |
| `device_mac` | `str` | MAC address of the device. |
| `sub_client_type` | `str` | `MOBILE_NETWORK` for Webex Go calls from mobile. |
| `device_owner_uuid` | `str` | UUID of device owner (for multi-line/shared line). |

#### Location / Organization Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `location` | `str` | Location name for the report. |
| `site_main_number` | `str` | Main number for the user's site. |
| `site_timezone` | `str` | Offset in minutes from UTC for user's timezone. |
| `site_uuid` | `str` | Unique site identifier. |
| `org_uuid` | `str` | Unique organization identifier across Cisco. |
| `department_id` | `str` | User's department name identifier. |
| `authorization_code` | `str` | Auth code for Account/Authorization Codes service. |
| `international_country` | `str` | Country code of dialed number (international calls only). |

#### Trunk Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `inbound_trunk` | `str` | Inbound trunk (present in both Originating and Terminating records). |
| `outbound_trunk` | `str` | Outbound trunk (present in both Originating and Terminating records). |

#### PSTN Vendor Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `pstn_vendor_name` | `str` | PSTN service vendor name for the country. |
| `pstn_legal_entity` | `str` | Regulated business entity for PSTN. Cisco Calling Plans only. |
| `pstn_vendor_org_id` | `str` | Cisco Calling plan org UUID (unique across regions). |
| `pstn_provider_id` | `str` | Immutable Cisco-defined UUID for the PSTN provider. |
| `external_customer_id` | `str` | External customer identifier. |

#### Recording Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `call_recording_platform_name` | `str` | Platform name: `DubberRecorder`, `Webex`, `Eleveo`, `ASCTech`, `MiaRec`, `Imagicle`, or `Unknown`. |
| `call_recording_result` | `str` | `successful`, `failed`, or `successful but not kept`. |
| `call_recording_trigger` | `str` | `always`, `always-pause-resume`, `on-demand`, or `on-demand-user-start`. |

#### Call Queue / Auto-Attendant Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `queue_type` | `str` | `Customer Assist` or `Call Queue` (alias: `Queue Type`). |
| `auto_attendant_key_pressed` | `str` | Last DTMF key pressed by caller (alias: `Auto Attendant Key Pressed`). |

#### Other Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `report_id` | `str` | Unique ID for deduplication. |
| `report_time` | `datetime` | Time this CDR record was created (UTC). |
| `call_transfer_time` | `datetime` | Time the transfer service was invoked (UTC). |
| `recall_type` | `str` | Indicates call park recall (alias: `Recall Type`). |
| `answered_elsewhere` | `str` | `Yes` when another agent/user answered (e.g., hunt group simultaneous ring). |
| `public_calling_ip_address` | `str` | Public IP of calling device (India locations only). |
| `public_called_ip_address` | `str` | Public IP of called device (India locations only). |
| `wx_cc_consult_merge_status` | `str` | WxCC consult transfer/conference status: `Yes`, `No`, or `NA`. |

#### Caller Reputation Fields

| SDK Field | Type | Description |
|-----------|------|-------------|
| `caller_reputation_score` | `str` | Score from caller reputation provider (0.0 to 5.0). |
| `caller_reputation_service_result` | `str` | `allow`, `captcha-allow`, `captcha-block`, or `block`. Terminating CDRs only. |
| `caller_reputation_score_reason` | `str` | Reason for the reputation score, or error details. |

### CDR Enums

#### CDRCallType

| Value | Meaning |
|-------|---------|
| `SIP_MEETING` | Meeting call |
| `SIP_INTERNATIONAL` | International call |
| `SIP_SHORTCODE` | Short code call |
| `SIP_INBOUND` | Inbound SIP call |
| `SIP_EMERGENCY` | Emergency call |
| `SIP_PREMIUM` | Premium rate call |
| `SIP_ENTERPRISE` | Enterprise (on-net) call |
| `SIP_TOLLFREE` | Toll-free call |
| `SIP_NATIONAL` | National call |
| `SIP_MOBILE` | Mobile call |
| `UNKNOWN` | Unknown call type |

#### CDRClientType

| Value | Meaning |
|-------|---------|
| `SIP` | SIP device/endpoint |
| `WXC_CLIENT` | Webex Calling native client |
| `WXC_THIRD_PARTY` | Third-party client |
| `TEAMS_WXC_CLIENT` | Teams with Webex Calling client |
| `WXC_DEVICE` | Webex Calling device |
| `WXC_SIP_GW` | Webex Calling SIP gateway |

#### CDRDirection

| Value | Meaning |
|-------|---------|
| `ORIGINATING` | Outbound call |
| `TERMINATING` | Inbound call |

#### CDROriginalReason

Values: `Unconditional`, `NoAnswer`, `CallQueue`, `HuntGroup`, `TimeOfDay`, `UserBusy`, `FollowMe`, `Unrecognised`, `Deflection`, `Unavailable`, `Unknown`

#### CDRRedirectReason

Values: `Unconditional`, `NoAnswer`, `CallQueue`, `TimeOfDay`, `UserBusy`, `FollowMe`, `HuntGroup`, `Deflection`, `Unknown`, `Unavailable`

#### CDRRelatedReason

Values: `ConsultativeTransfer`, `CallForwardSelective`, `CallPark`, `CallParkRetrieve`, `CallQueue`, `Unrecognised`, `CallPickup`, `CallForwardAlways`, `CallForwardBusy`, `FaxDeposit`, `HuntGroup`, `PushNotificationRetrieval`, `VoiceXMLScriptTermination`, `CallForwardNoAnswer`, `AnywhereLocation`, `CallRetrieve`, `Deflection`, `DirectedCallPickup`, `CallForwardModeBased`

#### CDRUserType

Values: `AutomatedAttendantVideo`, `Anchor`, `BroadworksAnywhere`, `VoiceMailRetrieval`, `LocalGateway`, `HuntGroup`, `GroupPaging`, `User`, `VoiceMailGroup`, `CallCenterStandard`, `CallCenterPremium`, `VoiceXML`, `RoutePoint`, `VirtualLine`, `Place`

---

## 2. Report Templates API

Report templates define the available report types. You must list templates to get the `templateId` needed to create a report.

### SDK Method

```python
ReportsApi.list_templates() -> list[ReportTemplate]
```

**REST equivalent:** `GET https://webexapis.com/v1/report/templates`

### ReportTemplate Model

```python
class ReportTemplate(ApiModel):
    id: Optional[int]           # Unique template identifier (API key: "Id")
    title: Optional[str]        # Template name
    service: Optional[str]      # Service name (e.g., "Webex Calling")
    max_days: Optional[int]     # Maximum date range allowed
    start_date: Optional[date]  # Earliest available data date
    end_date: Optional[date]    # Latest available data date
    identifier: Optional[str]   # Template reference key
    validations: Optional[list[ValidationRules]]  # Required fields for report creation
```

### Standard Webex Calling Report Templates

| Template Name | Description | Key Metrics |
|---------------|-------------|-------------|
| **Detailed Call History** | Comprehensive call log with timestamps, duration, status, parties | All CDR fields (see Section 1) |
| **Calling Media Quality** | Per-call-leg quality measurements | Latency, jitter, packet loss |
| **Calling Engagement** | Usage and adoption tracking | Call volume, usage patterns, adoption rates over time |
| **Calling Quality** | Client-side quality from Webex Calling app | Jitter, latency, packet loss (client perspective) |
| **Call Queue Stats** | Queue-level performance metrics | Incoming calls, wait times, abandonment rates, handling efficiency |
| **Call Queue Agent Stats** | Per-agent queue performance | Calls handled, average handle time, service level achievements |
| **Auto-attendant Stats Summary** | AA call volume and menu usage | Call volume, handling metrics, caller menu selections |
| **Auto-attendant Business & After-Hours Key Details** | AA interaction patterns by time period | Business hours vs. after-hours key press patterns |

**Note:** Template IDs are dynamic and may vary by organization. Always use `list_templates()` (or the `GET /report/templates` endpoint) to discover IDs at runtime. The OpenAPI spec example shows ID 130, but actual IDs should not be hardcoded. <!-- Verified via OpenAPI spec (specs/webex-admin.json /report/templates example) and wxc_sdk source (reports/__init__.py) 2026-03-19 -->

### CLI Examples

```bash
# List all available report templates (JSON output)
wxcli report-templates show

# List report templates in table format
wxcli report-templates show -o table
```

### Usage Example

```python
templates = api.reports.list_templates()
calling_templates = [t for t in templates if t.service and 'Calling' in t.service]
for t in calling_templates:
    print(f"ID: {t.id} | {t.title} | max {t.max_days} days")
```

---

## 3. Reports API

Create, list, poll, download, and delete generated reports. Reports are CSV files delivered as ZIP archives.

### Constraints

- **Maximum 50 reports** can exist at any time. Delete old reports to free quota.
- Each report can be downloaded up to 30 times. <!-- Verified via Cisco documentation (developer.webex.com/blog/exploring-the-webex-calling-reports-and-analytics-apis) 2026-03-19 -->
- CSV reports for Webex services are only supported for **North American** organizations. Other regions return blank CSVs for Webex-service reports.
- Reports are delivered in **ZIP format** (Content-Type: `application/zip` or `application/octet-stream`).

### CLI Examples

```bash
# Create a report from a template (e.g., template ID 130 = Call Queue Stats)
wxcli reports create --template-id 130 \
  --start-date "2026-03-01" --end-date "2026-03-15"

# Create a Detailed Call History report
wxcli reports create --template-id 25 \
  --start-date "2026-03-01" --end-date "2026-03-07"

# Create a report using full JSON body
wxcli reports create --json-body '{"templateId": 130, "startDate": "2026-03-01", "endDate": "2026-03-15"}'
```

**Note:** The CLI `reports` group currently has `create` only. To list, poll, or delete reports, use the Raw HTTP or SDK methods below. To download report CSVs, use the SDK `ReportsApi.download()` method.

### Create a Report

```python
ReportsApi.create(
    template_id: int,           # From list_templates()
    start_date: date = None,    # Data start date (YYYY-MM-DD)
    end_date: date = None,      # Data end date (YYYY-MM-DD)
    site_list: str = None       # Required for site-based templates (Webex Meetings)
) -> str                        # Returns report ID
```

**REST equivalent:** `POST https://webexapis.com/v1/reports`

**Request body:**
```json
{
    "templateId": 130,
    "startDate": "2024-02-01",
    "endDate": "2024-02-05"
}
```

**Response:**
```json
{
    "items": {
        "Id": "Y2lz...ZA"
    }
}
```

### List Reports

```python
ReportsApi.list(
    report_id: str = None,      # Filter by report ID
    service: str = None,        # Filter by service name
    template_id: str = None,    # Filter by template ID
    from_date: date = None,     # Reports created on or after this date
    to_date: date = None        # Reports created before this date
) -> Generator[Report, None, None]
```

**REST equivalent:** `GET https://webexapis.com/v1/reports`

Note: `from_date` and `to_date` must be provided together.

### Get Report Details (Poll Status)

```python
ReportsApi.details(
    report_id: str              # Report ID from create()
) -> Report
```

**REST equivalent:** `GET https://webexapis.com/v1/reports/{reportId}`

### Report Model

```python
class Report(ApiModel):
    id: Optional[str]               # Report identifier (API key: "Id")
    title: Optional[str]            # Report template name
    service: Optional[str]          # Service name
    start_date: Optional[date]      # Data range start
    end_date: Optional[date]        # Data range end
    site_list: Optional[str]        # Site (Webex Meetings only)
    created: Optional[datetime]     # Creation timestamp
    created_by: Optional[str]       # Creator's user ID
    schedule_from: Optional[str]    # "api" or "controlHub"
    status: Optional[str]           # "done" or "In progress"
    download_domain: Optional[str]  # Download host
    download_url: Optional[str]     # Full download URL (API key: "downloadURL")
```

**Status values:**
- `"done"` — Report is ready for download. `download_url` is populated.
- `"In progress"` — Report is still generating. Poll again.

### Download a Report

```python
ReportsApi.download(
    url: str                    # The download_url from Report details
) -> Generator[dict, None, None]
```

The SDK handles:
1. Authenticated GET request to the download URL
2. Reading the ZIP archive from the response
3. Extracting the first CSV file
4. Skipping the UTF-8 BOM (3 bytes)
5. Parsing CSV rows into dicts via `csv.DictReader`
6. Yielding each row as a `dict`

### Delete a Report

```python
ReportsApi.delete(
    report_id: str              # Report ID to remove
)
```

**REST equivalent:** `DELETE https://webexapis.com/v1/reports/{reportId}`

### CallingCDR — Typed Report Download

For Detailed Call History reports specifically, use `CallingCDR.from_dicts()` to get typed CDR objects instead of raw dicts:

```python
from wxc_sdk.reports import CallingCDR

# Get the download URL from a completed report
report = api.reports.details(report_id='<id>')
assert report.status == 'done'

# Download and parse into typed CDR objects
cdrs = list(CallingCDR.from_dicts(api.reports.download(url=report.download_url)))
for cdr in cdrs:
    print(f"{cdr.start_time} | {cdr.user} | {cdr.duration}s | {cdr.call_outcome}")
```

`CallingCDR` extends `CDR` — all 55+ fields from Section 1 are available.

---

## 4. Complete Workflow: Generate and Download a Report

### CLI Workflow

```bash
# Step 1: Discover available templates
wxcli report-templates show -o json

# Step 2: Create the report (use the template ID from step 1)
wxcli reports create --template-id 130 \
  --start-date "2026-03-01" --end-date "2026-03-15"
# Note the report ID from the response

# Steps 3-5 (poll, download, delete): Use SDK or Raw HTTP methods below.
# The CLI does not yet have list/show/download/delete commands for reports.
```

### SDK Workflow

```python
from wxc_sdk import WebexSimpleApi
from datetime import date
import time

api = WebexSimpleApi(tokens='<access_token>')

# Step 1: Find the template
templates = api.reports.list_templates()
cq_template = next(t for t in templates if t.title and 'Call Queue Stats' in t.title)
print(f"Using template: {cq_template.id} — {cq_template.title} (max {cq_template.max_days} days)")

# Step 2: Create the report
report_id = api.reports.create(
    template_id=cq_template.id,
    start_date=date(2024, 2, 1),
    end_date=date(2024, 2, 28)
)
print(f"Report created: {report_id}")

# Step 3: Poll until done
while True:
    report = api.reports.details(report_id=report_id)
    print(f"Status: {report.status}")
    if report.status == 'done':
        break
    time.sleep(30)

# Step 4: Download
rows = list(api.reports.download(url=report.download_url))
print(f"Downloaded {len(rows)} rows")

# Step 5: Clean up (free the 50-report quota)
api.reports.delete(report_id=report_id)
```

---

## 5. CDR Feed vs. Reports API — When to Use Which

| Criteria | CDR Feed API | Reports API |
|----------|-------------|-------------|
| **Data freshness** | Near real-time (5-minute delay) | Batch (async generation) |
| **Time range** | Last 30 days, 12-hour window per request | Depends on template `max_days` |
| **Output format** | JSON (paginated) | CSV in ZIP archive |
| **Use case** | Live dashboards, recent call lookup, alerting | Historical analysis, scheduled reports, compliance |
| **Rate limit** | 1 req/min + 10 pagination/min | Standard Webex API limits |
| **Scope** | `spark-admin:calling_cdr_read` | `analytics:read_all` |
| **License** | Admin role required | Pro Pack required |
| **Data fields** | 55+ CDR fields (JSON) | Varies by template (CSV columns) |

---

## 6. Use Cases

### Call Quality Monitoring

Use the **CDR Feed** for near-real-time monitoring, or the **Calling Media Quality** / **Calling Quality** report templates for historical analysis.

```bash
# Pull recent CDR records to check for failures (adjust times to last hour)
wxcli cdr list \
  --start-time "2026-03-17T15:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" -o json

# Create a Calling Media Quality report for historical analysis
wxcli reports create --template-id 26 \
  --start-date "2026-03-01" --end-date "2026-03-15"
```

```python
# Find calls with poor outcomes in the last hour
from datetime import datetime, timedelta, timezone

end = datetime.now(timezone.utc) - timedelta(minutes=5)
start = end - timedelta(hours=1)

failed_calls = [
    cdr for cdr in api.cdr.get_cdr_history(start_time=start, end_time=end)
    if cdr.call_outcome in ('Failure', 'Refusal')
]
for c in failed_calls:
    print(f"{c.start_time} | {c.user} | {c.call_outcome}: {c.call_outcome_reason}")
```

### Agent Performance (Call Queue Agent Stats)

Generate a **Call Queue Agent Stats** report:

```bash
# Create a Call Queue Agent Stats report
wxcli reports create --template-id 131 \
  --start-date "2026-02-01" --end-date "2026-02-28"
```

```python
agent_template = next(t for t in templates if t.title and 'Agent Stats' in t.title)
report_id = api.reports.create(
    template_id=agent_template.id,
    start_date=date(2024, 2, 1),
    end_date=date(2024, 2, 28)
)
# Poll, download, analyze per-agent metrics
```

### Queue Analytics (Call Queue Stats)

Generate a **Call Queue Stats** report for queue-level KPIs: incoming call volume, wait times, abandonment rates, handling efficiency.

```bash
# Create a Call Queue Stats report
wxcli reports create --template-id 130 \
  --start-date "2026-02-01" --end-date "2026-02-28"
```

### Auto-Attendant Analytics

Use **Auto-attendant Stats Summary** for overall AA performance, or **Auto-attendant Business & After-Hours Key Details** to analyze DTMF key press patterns across business hours vs. after-hours.

The CDR field `auto_attendant_key_pressed` is also available in real-time CDR records.

```bash
# Create an Auto-Attendant Stats Summary report
wxcli reports create --template-id 132 \
  --start-date "2026-02-01" --end-date "2026-02-28"
```

### Billing / Cost Analysis

Filter CDR records by `call_type` to separate international, toll-free, premium, and national calls:

```python
international = [
    cdr for cdr in api.cdr.get_cdr_history(start_time=start, end_time=end)
    if cdr.call_type and cdr.call_type.value == 'SIP_INTERNATIONAL'
]
```

PSTN vendor fields (`pstn_vendor_name`, `pstn_legal_entity`, `pstn_provider_id`) provide carrier-level detail for cost attribution.

```bash
# Pull CDR records and filter by international calls using JSON output + jq
wxcli cdr list \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" -o json
```

### Call Recording Audit

Filter by recording fields to audit recording compliance:

```bash
# Pull CDR records to audit recording outcomes
wxcli cdr list \
  --start-time "2026-03-17T14:00:00.000Z" \
  --end-time "2026-03-17T16:00:00.000Z" -o json

# List calling recordings to check status
wxcli recordings list --service-type calling --status available

# Get recording audit summaries for compliance review
wxcli recording-report list \
  --from "2026-03-01T00:00:00Z" --to "2026-03-17T00:00:00Z"
```

```python
failed_recordings = [
    cdr for cdr in api.cdr.get_cdr_history(start_time=start, end_time=end)
    if cdr.call_recording_result == 'failed'
]
```

---

## 7. Known API Documentation Bugs (from SDK source)

The SDK source code flags several discrepancies between Webex API documentation and actual behavior:

1. **Report Templates response:** Documentation says `"Template Attributes"` but actual key is `"items"`.
2. **Report Templates `id` field:** Documentation says `"id"` but actual key is `"Id"`.
3. **Report Templates missing fields:** `startDate` and `endDate` are not documented but are returned.
4. **Report Templates validations:** Documentation nests as `"validations"/"validations"` but actual structure is flat `"validations"`.
5. **List Reports response:** Documentation says `"Report Attributes"` but actual key is `"items"`.
6. **List Reports `scheduledFrom`:** Documentation says `"scheduledFrom"` but actual key is `"scheduleFrom"`.
7. **List Reports missing field:** `downloadDomain` is returned but not documented.
8. **Create Report response:** Actual response is `{"items": {"Id": "..."}}`, not documented structure.

---

## 8. Gotchas

- **Regional routing:** If the CDR endpoint returns HTTP 451, parse the response body for the correct regional endpoint URL and retry.
- **12-hour window limit:** CDR Feed requests cannot span more than 12 hours. For longer ranges, issue multiple sequential requests.
- **Empty/NA normalization:** The SDK converts empty strings and `"NA"` values to `None` automatically.
- **Field name aliasing:** Several CDR fields use non-standard aliases in the API (e.g., `"Route list calls overage"`, `"Original Called Party UUID"`, `"Queue Type"`). The SDK handles these via Pydantic `Field(alias=...)`.
- **Timezone:** All CDR timestamps are in UTC. The `site_timezone` field provides the offset in minutes if you need to convert to the user's local time.
- **Report quota:** The 50-report limit is hard. Always delete reports after downloading to avoid hitting the cap.
- **Pro Pack requirement:** The Reports API (templates, create, list, download, delete) requires the Pro Pack license. The CDR Feed API does not require Pro Pack but does require the admin role to be explicitly enabled.
- **Async download not implemented:** The SDK's async variant of `ReportsApi.download()` raises `NotImplementedError`. Use the sync API for report downloads.

---

## 9. Raw HTTP Endpoints
<!-- Updated by playbook session 2026-03-18 -->

All endpoints below use the `api.session.rest_*` methods from `wxc_sdk`. URLs confirmed from working CLI implementations.

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi(tokens='<token>')
BASE = "https://webexapis.com/v1"
```

### Detailed Call History (CDR)

**Important:** The CDR endpoints use a different base URL than the standard Webex API. `startTime` and `endTime` are required and must be in ISO 8601 format (e.g., `2026-03-17T14:00:00.000Z`). The time window cannot exceed 12 hours.

#### CDR Feed (Batch/Historical)

```
GET https://webexapis.com/v1/cdr_feed
```

```python
params = {
    "startTime": "2026-03-17T14:00:00.000Z",  # ISO 8601 — required
    "endTime": "2026-03-17T16:00:00.000Z",     # ISO 8601 — required
    # "locations": "San Jose,Austin",           # optional, up to 10 comma-separated
    "max": 1000                                 # no auto-pagination
}
result = api.session.rest_get(f"{BASE}/cdr_feed", params=params)
# Returns: {"items": [{"Start time": "...", "Answer time": "...", ...}, ...]}
```

#### CDR Stream (Near-Real-Time)

```
GET https://webexapis.com/v1/cdr_stream
```

```python
params = {
    "startTime": "2026-03-17T14:00:00.000Z",
    "endTime": "2026-03-17T16:00:00.000Z",
    "max": 1000
}
result = api.session.rest_get(f"{BASE}/cdr_stream", params=params)
# Same response format as cdr_feed
```

### Report Templates

```
GET https://webexapis.com/v1/report/templates
```

```python
result = api.session.rest_get(f"{BASE}/report/templates")
# Returns: {"items": [{"Id": 130, "title": "Call Queue Stats", "service": "Webex Calling", ...}, ...]}
# Note: API returns "Id" (capital I), not "id"
```

### Reports

#### List Reports

```
GET https://webexapis.com/v1/reports
```

```python
params = {
    # "reportId": "report_id",
    # "service": "Webex Calling",
    # "templateId": "130",
    # "from": "2026-03-01",         # from and to must be provided together
    # "to": "2026-03-17",
    "max": 1000
}
result = api.session.rest_get(f"{BASE}/reports", params=params)
```

#### Get Report Details

```
GET https://webexapis.com/v1/reports/{reportId}
```

```python
result = api.session.rest_get(f"{BASE}/reports/{report_id}")
# Returns: {"Id": "...", "title": "...", "status": "done", "downloadURL": "https://...", ...}
# Poll until status == "done", then use downloadURL to fetch the CSV ZIP
```

#### Create a Report

```
POST https://webexapis.com/v1/reports
```

```python
body = {
    "templateId": 130,              # from report/templates list
    "startDate": "2026-03-01",      # YYYY-MM-DD
    "endDate": "2026-03-15"         # YYYY-MM-DD
    # "siteList": "site_url"        # required only for Webex Meetings templates
}
result = api.session.rest_post(f"{BASE}/reports", json=body)
# Returns: {"items": {"Id": "report_id_here"}}
```

#### Delete a Report

```
DELETE https://webexapis.com/v1/reports/{reportId}
```

```python
api.session.rest_delete(f"{BASE}/reports/{report_id}")
```

### Converged Recordings

#### CLI Examples

```bash
# List all available recordings
wxcli recordings list

# List calling recordings in a date range
wxcli recordings list \
  --from "2026-03-01T00:00:00Z" --to "2026-03-17T00:00:00Z" \
  --service-type calling

# List recordings filtered by status and format
wxcli recordings list --status available --format MP3

# List recordings by location and owner type
wxcli recordings list --location-id "Y2lz...bG9j" --owner-type user

# List recordings in JSON format with pagination
wxcli recordings list --service-type calling -o json --limit 50

# List recordings for admin/compliance (all users in org)
wxcli recordings list-converged-recordings \
  --from "2026-03-01T00:00:00Z" --to "2026-03-17T00:00:00Z"

# Get details for a specific recording
wxcli recordings show "Y2lz...cmVj"

# Get recording metadata
wxcli recordings show-metadata "Y2lz...cmVj"

# Delete a recording
wxcli recordings delete "Y2lz...cmVj"

# Reassign recordings from one owner to another
wxcli recordings create \
  --owner-email "oldowner@company.com" \
  --reassign-owner-email "newowner@company.com"

# Move recordings to recycle bin
wxcli recordings create-soft-delete \
  --json-body '{"trashAll": true, "ownerEmail": "user@company.com"}'

# Restore recordings from recycle bin
wxcli recordings create-restore \
  --json-body '{"restoreAll": true, "ownerEmail": "user@company.com"}'

# Purge recordings permanently from recycle bin
wxcli recordings create-purge \
  --json-body '{"purgeAll": true, "ownerEmail": "user@company.com"}'

# Download a single recording's artifacts (transcript, AI notes, audio)
wxcli converged-recordings download "Y2lz...cmVj"
wxcli converged-recordings download "Y2lz...cmVj" --include-audio
wxcli converged-recordings download "Y2lz...cmVj" -d /tmp/my-recordings

# Bulk export recordings to JSONL (BI-ready)
wxcli converged-recordings export \
  --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z"

# Export with filters
wxcli converged-recordings export \
  --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z" \
  --owner-email user@company.com --service-type calling

# Export as individual files per recording
wxcli converged-recordings export \
  --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z" \
  --format json-per-file

# Export with audio files
wxcli converged-recordings export \
  --from "2026-03-01T00:00:00Z" --to "2026-03-28T00:00:00Z" \
  --include-audio -d /data/recording-export
```

#### List Recordings (User)

```
GET https://webexapis.com/v1/convergedRecordings
```

```python
params = {
    # "from": "2026-03-01T00:00:00Z",
    # "to": "2026-03-17T00:00:00Z",
    # "status": "available",
    # "serviceType": "calling",
    # "format": "MP3",
    # "ownerType": "user",
    # "storageRegion": "US",
    # "locationId": "location_id",
    # "topic": "search_term",
    "max": 1000
}
result = api.session.rest_get(f"{BASE}/convergedRecordings", params=params)
```

#### List Recordings (Admin/Compliance)

```
GET https://webexapis.com/v1/admin/convergedRecordings
```

```python
params = {
    # "ownerId": "user_id",
    # "ownerEmail": "user@company.com",
    # All same params as user endpoint above
    "max": 1000
}
result = api.session.rest_get(f"{BASE}/admin/convergedRecordings", params=params)
```

#### Get Recording Details

```
GET https://webexapis.com/v1/convergedRecordings/{recordingId}
```

```python
result = api.session.rest_get(f"{BASE}/convergedRecordings/{recording_id}")
```

#### Delete a Recording

```
DELETE https://webexapis.com/v1/convergedRecordings/{recordingId}
```

```python
api.session.rest_delete(f"{BASE}/convergedRecordings/{recording_id}")
```

#### Get Recording Metadata

```
GET https://webexapis.com/v1/convergedRecordings/{recordingId}/metadata
```

```python
params = {"showAllTypes": "true"}  # optional — show all attribute types
result = api.session.rest_get(f"{BASE}/convergedRecordings/{recording_id}/metadata", params=params)
```

#### Reassign Recordings

```
POST https://webexapis.com/v1/convergedRecordings/reassign
```

```python
body = {
    "reassignOwnerEmail": "newowner@company.com",
    "ownerEmail": "oldowner@company.com"
    # or "ownerID": "user_id"
}
result = api.session.rest_post(f"{BASE}/convergedRecordings/reassign", json=body)
```

#### Move Recordings to Recycle Bin

```
POST https://webexapis.com/v1/convergedRecordings/softDelete
```

```python
body = {
    "trashAll": True,
    "ownerEmail": "user@company.com"
}
result = api.session.rest_post(f"{BASE}/convergedRecordings/softDelete", json=body)
```

#### Restore Recordings from Recycle Bin

```
POST https://webexapis.com/v1/convergedRecordings/restore
```

```python
body = {
    "restoreAll": True,
    "ownerEmail": "user@company.com"
}
result = api.session.rest_post(f"{BASE}/convergedRecordings/restore", json=body)
```

#### Download Recording Artifacts

Downloads a single recording's transcript, AI-generated notes, and optionally the MP3 audio file to a local directory. Uses the `temporaryDirectDownloadLinks` from the recording detail response. The download URLs are pre-signed — they are fetched directly with HTTP GET, no Bearer token needed.

```bash
wxcli converged-recordings download RECORDING_ID [--include-audio] [-d OUTPUT_DIR]
```

Output structure:
```
{output_dir}/{recording_id}/
  metadata.json          # full recording detail response
  transcript.txt         # if available
  suggested_notes.html   # if available
  short_notes.html       # if available
  action_items.html      # if available
  audio.mp3              # if --include-audio and available
```

#### Bulk Export Recordings

Paginates the admin listing endpoint, fetches detail for each recording, and downloads all text/AI artifacts. Produces either a single JSONL file (BI-ready) or one directory per recording.

```bash
wxcli converged-recordings export --from START --to END [filters...] [--format jsonl|json-per-file]
```

JSONL mode (default): writes `recordings.jsonl` with one JSON object per line containing all metadata and inline text content. Audio files (if `--include-audio`) go to `{output_dir}/audio/{recording_id}.mp3`.

JSON-per-file mode: same directory structure as the `download` command, one directory per recording.

Processing is sequential — each recording is fully fetched and downloaded before moving to the next, since download links expire in 3 hours.

#### Purge Recordings from Recycle Bin

```
POST https://webexapis.com/v1/convergedRecordings/purge
```

```python
body = {
    "purgeAll": True,
    "ownerEmail": "user@company.com"
}
result = api.session.rest_post(f"{BASE}/convergedRecordings/purge", json=body)
```

### Recording Reports

#### CLI Examples

```bash
# List recording audit report summaries
wxcli recording-report list \
  --from "2026-03-01T00:00:00Z" --to "2026-03-17T00:00:00Z"

# List recording audit summaries for a specific host
wxcli recording-report list --host-email "host@company.com"

# Get recording audit report access details
wxcli recording-report list-access-detail --recording-id "Y2lz...cmVj"

# List meeting archive summaries
wxcli recording-report list-meeting-archive-summaries

# Get meeting archive details
wxcli recording-report show "Y2lz...YXJj"
```

#### Access Summary

```
GET https://webexapis.com/v1/recordingReport/accessSummary
```

```python
params = {
    # "recordingId": "recording_id",
    "max": 1000
}
result = api.session.rest_get(f"{BASE}/recordingReport/accessSummary", params=params)
```

#### Access Detail

```
GET https://webexapis.com/v1/recordingReport/accessDetail
```

```python
params = {
    # "recordingId": "recording_id",
    "max": 1000
}
result = api.session.rest_get(f"{BASE}/recordingReport/accessDetail", params=params)
```

#### Meeting Archive Summaries

```
GET https://webexapis.com/v1/recordingReport/meetingArchiveSummaries
```

```python
result = api.session.rest_get(f"{BASE}/recordingReport/meetingArchiveSummaries", params={"max": 1000})
```

#### Meeting Archive Detail

```
GET https://webexapis.com/v1/recordingReport/meetingArchives/{archiveId}
```

```python
result = api.session.rest_get(f"{BASE}/recordingReport/meetingArchives/{archive_id}")
```

---

## See Also

- **[authentication.md](authentication.md)** — OAuth scopes and token management. CDR access requires `spark-admin:calling_cdr_read` with an explicit admin role; Reports API requires `analytics:read_all` with Pro Pack.
- **[call-features-major.md](call-features-major.md)** — Call Queue and Auto Attendant configuration. CDR fields like `queue_type`, `auto_attendant_key_pressed`, and queue-related report templates correspond to features configured there.
