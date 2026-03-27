<!-- Verified via CLI Batches 1-4, 2026-03-19 through 2026-03-21 -->
# Admin: Hybrid Infrastructure & Analytics

Hybrid cluster/connector monitoring, historical analytics, live meeting monitoring, and meeting quality analysis.

## Sources

- `specs/webex-admin.json` -- OpenAPI 3.0 spec for admin/org management APIs (hybrid clusters, hybrid connectors, analytics, meeting qualities, live monitoring)
- [Webex Hybrid Services](https://developer.webex.com/docs/api/v1/hybrid-clusters) -- Official API docs
- [Meeting Qualities API](https://developer.webex.com/docs/api/v1/meeting-qualities) -- Official API docs

---

## Required Scopes

| Scope | Purpose |
|-------|---------|
| `spark-admin:hybrid_clusters_read` | List and get details for hybrid clusters. |
| `spark-admin:hybrid_connectors_read` | List and get details for hybrid connectors. |
| `analytics:read_all` | Access historical analytics (messaging, room devices, meetings). Also required for live monitoring and meeting qualities. |

**Admin requirement:** The authenticated user must be a full or read-only administrator for the organization.

---

## 1. Hybrid Clusters

Hybrid clusters represent on-premises infrastructure nodes registered to Webex (e.g., Expressway, calendar connector hosts). Use these commands to inventory and monitor cluster health.

### CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wxcli hybrid-clusters list` | List all hybrid clusters | `--limit`, `--offset`, `-o table\|json` |
| `wxcli hybrid-clusters show <id>` | Get details for a specific cluster | `-o table\|json` |

### CLI Examples

```bash
# List all hybrid clusters in the org
wxcli hybrid-clusters list

# List clusters as JSON for scripting
wxcli hybrid-clusters list -o json

# Get details for a specific cluster
wxcli hybrid-clusters show Y2lzY29zcGFyazovL3VzL0hZQlJJRF9DTFVTVEVSLzEyMzQ
```

### Raw HTTP Fallback

```bash
# List hybrid clusters
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/hybrid/clusters" | jq '.items[]'

# Get cluster details
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/hybrid/clusters/{hybridClusterId}" | jq .
```

### API Details

| Property | Value |
|----------|-------|
| List endpoint | `GET https://webexapis.com/v1/hybrid/clusters` |
| Detail endpoint | `GET https://webexapis.com/v1/hybrid/clusters/{hybridClusterId}` |
| Response key (list) | `items` |
| Table columns | `id`, `name` |

---

## 2. Hybrid Connectors

Hybrid connectors are the individual service instances running on hybrid cluster nodes (e.g., Calendar Connector, Call Connector, Management Connector). Each connector belongs to a cluster.

### CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wxcli hybrid-connectors list` | List all hybrid connectors | `--limit`, `--offset`, `-o table\|json` |
| `wxcli hybrid-connectors show <id>` | Get details for a specific connector | `-o table\|json` |

### CLI Examples

```bash
# List all connectors
wxcli hybrid-connectors list

# List connectors as JSON
wxcli hybrid-connectors list -o json

# Get details for a specific connector
wxcli hybrid-connectors show Y2lzY29zcGFyazovL3VzL0hZQlJJRF9DT05ORUNUT1IvMTIz
```

### Raw HTTP Fallback

```bash
# List hybrid connectors
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/hybrid/connectors" | jq '.items[]'

# Get connector details
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/hybrid/connectors/{connectorId}" | jq .
```

### API Details

| Property | Value |
|----------|-------|
| List endpoint | `GET https://webexapis.com/v1/hybrid/connectors` |
| Detail endpoint | `GET https://webexapis.com/v1/hybrid/connectors/{connectorId}` |
| Response key (list) | `items` |
| Table columns | `id`, `name` |

---

## 3. Live Monitoring

Retrieves live meeting metrics categorized by country. Despite the CLI command name `create`, this is a **read operation** -- the Webex API uses POST for this query, and the generator maps POST to `create`.

### CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wxcli live-monitoring create` | Get live meeting metrics by country | `--site-url`, `--json-body` |

### CLI Examples

```bash
# Get live meeting metrics for a specific site
wxcli live-monitoring create --site-url "mysite.webex.com"

# Get live meeting metrics with full JSON body
wxcli live-monitoring create --json-body '{"siteUrl": "mysite.webex.com"}'
```

### Raw HTTP Fallback

```bash
# Get live meeting metrics by country (POST with JSON body)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"siteUrl": "mysite.webex.com"}' \
  "https://webexapis.com/v1/livemonitoring/liveMeetingsByCountry" | jq .
```

### API Details

| Property | Value |
|----------|-------|
| Endpoint | `POST https://webexapis.com/v1/livemonitoring/liveMeetingsByCountry` |
| Request body | `{"siteUrl": "..."}` (optional) |
| Method | POST (but semantically a read/query operation) |

---

## 4. Analytics (Historical)

Historical analytics covering messaging activity, room device usage, and meeting aggregates. Three separate commands query three different metric endpoints.

### KNOWN BUG: `/v1/v1/` Double-Path

All three `analytics` commands have a confirmed bug in the generated code: the URL contains `/v1/v1/` instead of `/v1/`. For example, the `show` command hits `https://webexapis.com/v1/v1/analytics/messagingMetrics/dailyTotals` instead of the correct `https://webexapis.com/v1/analytics/messagingMetrics/dailyTotals`. This causes all three commands to fail at runtime with a 404 or routing error.

**Workaround:** Use raw HTTP (curl) until the bug is fixed via `field_overrides.yaml` and regeneration.

**Affected commands:**
- `wxcli analytics show` -- path: `/v1/v1/analytics/messagingMetrics/dailyTotals` (should be `/v1/analytics/messagingMetrics/dailyTotals`)
- `wxcli analytics show-daily-totals` -- path: `/v1/v1/analytics/roomDeviceMetrics/dailyTotals` (should be `/v1/analytics/roomDeviceMetrics/dailyTotals`)
- `wxcli analytics show-aggregates` -- path: `/v1/v1/analytics/meetingsMetrics/aggregates` (should be `/v1/analytics/meetingsMetrics/aggregates`)

### CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wxcli analytics show` | Messaging historical data (daily totals) | `--from`, `--to`, `-o json` |
| `wxcli analytics show-daily-totals` | Room device historical data (daily totals) | `--from`, `--to`, `-o json` |
| `wxcli analytics show-aggregates` | Meeting historical data (aggregates) | `--site-url` (required), `--from`, `--to`, `-o json` |

### CLI Examples (will fail until bug is fixed)

```bash
# Messaging metrics for a date range
wxcli analytics show --from 2026-03-01 --to 2026-03-15

# Room device metrics
wxcli analytics show-daily-totals --from 2026-03-01 --to 2026-03-15

# Meeting aggregates for a specific site (--site-url is required)
wxcli analytics show-aggregates --site-url "mysite.webex.com" --from 2026-03-01 --to 2026-03-15
```

### Raw HTTP Fallback (use these until the CLI bug is fixed)

```bash
# Messaging metrics -- daily totals
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/analytics/messagingMetrics/dailyTotals?from=2026-03-01&to=2026-03-15" | jq .

# Room device metrics -- daily totals
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/analytics/roomDeviceMetrics/dailyTotals?from=2026-03-01&to=2026-03-15" | jq .

# Meeting metrics -- aggregates (siteUrl is required)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/analytics/meetingsMetrics/aggregates?siteUrl=mysite.webex.com&from=2026-03-01&to=2026-03-15" | jq .
```

### API Details

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/analytics/messagingMetrics/dailyTotals` | GET | Daily messaging activity totals |
| `/v1/analytics/roomDeviceMetrics/dailyTotals` | GET | Daily room device usage totals |
| `/v1/analytics/meetingsMetrics/aggregates` | GET | Meeting aggregate metrics (requires `siteUrl`) |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from` | UTC date string | No | Start date for the historical data window |
| `to` | UTC date string | No | End date for the historical data window |
| `siteUrl` | string | Meetings only | URL of the Webex site (required for `meetingsMetrics/aggregates`) |

---

## 5. Meeting Qualities

Retrieves media quality metrics for a specific meeting instance, including jitter, latency, and packet loss data per media session.

### CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `wxcli meeting-qualities list` | Get meeting quality metrics | `--meeting-id`, `--max`, `--offset`, `--limit`, `-o table\|json` |

### CLI Examples

```bash
# Get quality metrics for a specific meeting
wxcli meeting-qualities list --meeting-id "a]b1c2d3e4f5"

# Get quality metrics as JSON
wxcli meeting-qualities list --meeting-id "a1b2c3d4e5f6" -o json

# Limit results
wxcli meeting-qualities list --meeting-id "a1b2c3d4e5f6" --max 10
```

### Raw HTTP Fallback

```bash
# Get meeting quality data
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/meeting/qualities?meetingId=a1b2c3d4e5f6" | jq .

# With pagination
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/meeting/qualities?meetingId=a1b2c3d4e5f6&max=10&offset=0" | jq .
```

### API Details

| Property | Value |
|----------|-------|
| Endpoint | `GET https://webexapis.com/v1/meeting/qualities` |
| Response key | `items` |
| Table columns | `id`, `name` (default -- actual response fields may differ) |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `meetingId` | string | Yes (effectively) | Unique identifier for the meeting instance |
| `max` | int | No | Maximum number of media sessions to return |
| `offset` | int | No | Offset for pagination |

---

## Recipes

### Monitor hybrid connector health across the org

List all connectors, then inspect any that show issues.

```bash
# Step 1: List all connectors
wxcli hybrid-connectors list -o json | jq '.[] | {id, hostname, status: .status.state}'

# Step 2: Get details on a specific connector that looks unhealthy
wxcli hybrid-connectors show <connector-id> -o json | jq '{hostname, status, version, cluster}'

# Step 3: Cross-reference with the parent cluster
wxcli hybrid-clusters show <cluster-id>
```

Raw HTTP version (if CLI is unavailable):

```bash
# List all connectors and filter for non-running states
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/hybrid/connectors" | \
  jq '.items[] | select(.status.state != "running") | {id, hostname, state: .status.state}'
```

### Pull historical analytics for messaging/meetings/devices

Due to the `/v1/v1/` bug in the CLI, use raw HTTP for now.

```bash
# Messaging activity over the last 30 days
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/analytics/messagingMetrics/dailyTotals?from=2026-02-17&to=2026-03-19" | jq .

# Room device usage over the last 7 days
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/analytics/roomDeviceMetrics/dailyTotals?from=2026-03-12&to=2026-03-19" | jq .

# Meeting aggregates for a site
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/analytics/meetingsMetrics/aggregates?siteUrl=mysite.webex.com&from=2026-03-01&to=2026-03-19" | jq .
```

### Investigate meeting quality issues (jitter, latency, packet loss)

You need a `meetingId` to query quality data. Get it from the Meetings API or Control Hub.

```bash
# Step 1: Get quality metrics for a specific meeting
wxcli meeting-qualities list --meeting-id "a1b2c3d4e5f6" -o json

# Step 2: Parse the response for quality indicators
wxcli meeting-qualities list --meeting-id "a1b2c3d4e5f6" -o json | \
  jq '.[] | {participant: .displayName, audioJitter: .mediaQuality.audioJitter, videoPacketLoss: .mediaQuality.videoPacketLoss, latency: .mediaQuality.latency}'
```

Raw HTTP version:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://webexapis.com/v1/meeting/qualities?meetingId=a1b2c3d4e5f6" | \
  jq '.items[] | {participant: .displayName, audioJitter: .mediaQuality.audioJitter, videoPacketLoss: .mediaQuality.videoPacketLoss}'
```

---

## Gotchas

### `live-monitoring create` is a read operation

The `create` command name is misleading. The Webex API uses `POST` for this query endpoint (`/v1/livemonitoring/liveMeetingsByCountry`), and the generator maps all POST operations to `create`. The command reads live meeting metrics -- it does not create anything.

### All groups are read-only

None of these 5 command groups have write operations. There are no `update`, `delete`, or true `create` commands. The `live-monitoring create` is the only POST, and it is semantically a read (see above).

### Meeting quality requires a specific `meetingId`

The `meeting-qualities list` command is effectively useless without `--meeting-id`. Without it, the API may return an error or empty results. You need to obtain the meeting ID from the Meetings API (`wxcli meetings list` or the Control Hub meeting history) before querying quality data.

### CONFIRMED BUG: `analytics` commands have a `/v1/v1/` double-path

All three `analytics` commands (`show`, `show-daily-totals`, `show-aggregates`) generate URLs with `/v1/v1/` instead of `/v1/`. This is a generator bug -- the OpenAPI spec paths already include `/v1/`, and the generator prepends the base URL which also ends in `/v1`. The result is a broken double-path like `https://webexapis.com/v1/v1/analytics/messagingMetrics/dailyTotals`.

**Impact:** All three commands fail at runtime. Use raw HTTP (curl) as shown in the fallback examples above.

**Fix:** Add URL override entries in `tools/field_overrides.yaml` for the three analytics endpoints to strip the extra `/v1`, then regenerate with:

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-admin.json --tag "Historical Analytics APIs"
pip3.11 install -e . -q
```

### Scope troubleshooting

- **`spark-admin:hybrid_clusters_read`** and **`spark-admin:hybrid_connectors_read`** are separate scopes. Having one does not grant the other.
- **`analytics:read_all`** covers analytics, meeting qualities, and live monitoring. If you get a 403, verify this scope is included in your token and that the authenticated user has admin privileges.
- Hybrid scopes require the org to have hybrid services deployed. If no hybrid infrastructure exists, the list endpoints return empty results (not an error).

---

## See Also

- `docs/reference/reporting-analytics.md` -- CDR feed, report templates, call quality/queue/AA statistics
- `docs/reference/authentication.md` -- Token types, scopes, OAuth flows
- `docs/reference/wxcadm-core.md` -- wxcadm org/auth patterns (alternative to raw HTTP)
