# Database Integration -- Platform Reference

<!-- ref-tag: db-integration-v2 -->

## Accepting Schema from the User

When building an AI agent that queries a database, the first step is understanding the schema. Users may provide it in three forms:

### SQL DDL

```sql
CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name text NOT NULL,
  phone_number text UNIQUE NOT NULL,
  ...
);
```

Parse to extract: table names, column names, data types, primary keys, foreign keys, unique constraints, defaults.

### JSON Export

A JSON representation of tables and columns (e.g., from a schema introspection tool). Parse the same elements as DDL.

### Plain Description

"I have a customers table with name, phone, email. Orders table with customer_id, order_date, status."

Ask clarifying questions until the schema is clear:
- What are the primary keys?
- Are there foreign key relationships?
- Which columns are unique? (needed for exact-match lookups)
- Are there auto-generated fields (IDs, confirmation numbers, timestamps)?
- What data types are dates/times stored as? (timezone-aware or naive?)

---

## Design Principles for AI-Driven Queries

These principles apply regardless of database backend.

### Key Off Human-Speakable Identifiers

Never use UUIDs as slot entities that the **caller** must provide. Callers cannot say "my ID is a1b2c3d4-e5f6-7890-abcd-ef1234567890" on a phone call.

Use identifiers humans can provide:
- Phone number
- Email address
- Confirmation number (short, alphanumeric)
- Name (with fuzzy matching)

**Internal UUIDs are OK.** UUIDs returned by one action and passed to the next action internally (e.g., `test_id` from a lookup used in a booking) are acceptable — the LLM carries them in context. If this proves unreliable, redesign to use a lookup-by-name pattern.

### Avoid Array Responses

LLMs struggle with array responses -- they may ignore items, miscount, or lose track. Prefer single-object responses where possible:
- Use server-side headers or parameters to force single-object response
- If arrays are unavoidable (e.g., listing available time slots), limit to 3-5 items

### Always Limit Results — No Pagination

AI agent flows should always use `limit` to cap query results (3-5 items max). Pagination (offset/cursor) is impractical:
- The 30-second timeout doesn't allow multiple roundtrips
- The LLM cannot manage "page 1 of 5" state across turns
- Callers on a phone call can't process long lists

Design queries to return the most relevant N items. Use filters (date range, status) to narrow results before limiting.

### Minimize Field Selection Parameters

Prefer omitting field selection (e.g., `select=` in PostgREST). Let the API return the full record and use output variables in the Connect flow to define what gets extracted. This avoids URL complexity and makes debugging easier.

**Exception:** In multi-node flows where you only need one field from an intermediate lookup (e.g., `select=id` to get a patient ID before a POST), field selection keeps payloads small and is acceptable.

### Fuzzy Match for Text Searches

Callers use natural language: "my last order" not "order ID ORD-2026-0042". Use case-insensitive partial matching (e.g., `ilike.*pattern*` in PostgREST) so the query is forgiving.

### Multi-Table Queries

When an action needs data from multiple tables (e.g., appointment details with patient name and test info), you have two options:

**Option A: Multi-node chaining in Connect.** Multiple HTTP GET nodes in one flow, each querying a different table. Use this when you need data from 2 tables. Beyond 2, it gets unwieldy and risks the 30-second timeout.

**Option B: Database views.** Create a view that joins the tables, then query the view like a single table. Preferred when:
- The action needs data from 3+ tables
- The same join is used by multiple actions
- You want a simpler Connect flow (single HTTP node)

PostgREST example (Supabase view):

```sql
CREATE VIEW order_details AS
SELECT o.id, o.order_number, o.created_at, o.status,
       c.first_name, c.last_name, c.phone_number,
       p.name as product_name, p.description,
       l.name as location_name, l.address
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id
JOIN locations l ON o.location_id = l.id;
```

Query the view: `GET /rest/v1/order_details?phone_number=eq.{phone}`

PostgREST also supports foreign-table embedding (`?select=*,table(*)`) but views are simpler to debug and don't require understanding embedding syntax.

### Hardcode Known UUIDs

If a value is fixed for the deployment (e.g., a single office location), hardcode its UUID directly in the Connect flow URL rather than making the LLM carry it as a variable. LLMs cannot reliably transport UUIDs between actions.

### Auto-Generated Fields

If the database auto-generates fields (IDs, confirmation numbers, timestamps via triggers/sequences), do NOT include those fields in POST request bodies. Capture them from the response instead.

### Concurrency: Check-and-Claim Race Conditions

When two callers check availability simultaneously, both may see the same resource as available. If the action only creates a record (INSERT) without marking the resource as claimed, double-booking occurs.

**Fix: Atomic check-and-claim.** Use a database function (RPC) that checks availability and claims in a single transaction:

```sql
-- Example: Supabase RPC function
CREATE OR REPLACE FUNCTION claim_slot(
  p_slot_time timestamptz,
  p_customer_id uuid,
  p_location_id uuid,
  p_service_id uuid
) RETURNS json AS $$
DECLARE
  v_slot available_slots%ROWTYPE;
  v_booking bookings%ROWTYPE;
BEGIN
  -- Lock and claim the slot atomically
  SELECT * INTO v_slot FROM available_slots
    WHERE slot_time = p_slot_time
      AND location_id = p_location_id
      AND is_booked = false
    FOR UPDATE SKIP LOCKED
    LIMIT 1;

  IF NOT FOUND THEN
    RETURN json_build_object('error', 'slot_unavailable');
  END IF;

  UPDATE available_slots SET is_booked = true WHERE id = v_slot.id;

  INSERT INTO bookings (customer_id, location_id, service_id, scheduled_at, status)
    VALUES (p_customer_id, p_location_id, p_service_id, v_slot.slot_time, 'confirmed')
    RETURNING * INTO v_booking;

  RETURN row_to_json(v_booking);
END;
$$ LANGUAGE plpgsql;
```

Call via PostgREST RPC: `POST /rest/v1/rpc/claim_slot` with JSON body.

**For demos without RPC:** At minimum, add a second HTTP node after INSERT that PATCHes `available_slots` to set `is_booked = true`. This isn't atomic but prevents the most obvious double-bookings.

**For non-Supabase backends:** Use your database's equivalent (stored procedures, transactions, optimistic locking with version columns).

---

## WxCC Business Rules Engine (BRE)

For ANI-based routing lookups and simple key-value datasets, the BRE is a native WxCC component that requires no external database. Data is uploaded via CSV or manual entry to the BRE DataSync portal, and queried at runtime via the BRE Request activity in Flow Designer.

### When to Use

- ANI-based call routing (VIP lists, campaign lists, regional routing)
- Simple key-value lookups where the key is the caller's ANI or a small set of known identifiers
- Data that changes in bulk (CSV upload) rather than per-interaction
- You want zero external infrastructure and the data fits within BRE sizing limits

### When NOT to Use

- Per-interaction data (order lookups, customer records, ticket status) — use a database
- Data that needs querying, filtering, joining, or aggregation — BRE is key-value only
- Data updated per-interaction (BRE updates are batch, not real-time per call)
- Large datasets exceeding 100K rows per lookup type
- Data containing PII beyond ANI (BRE prohibits non-ANI PII)
- AI Agent action flows in Webex Connect — BRE Request is a Flow Designer activity only, not available in Connect

### Comparison with Other Data Sources

| Aspect | BRE | Global Variable | External DB (Supabase, etc.) |
|--------|-----|-----------------|------------------------------|
| Setup | Request DataSync access from Cisco | Zero — built into WxCC | Provision and configure |
| Cost | Included with CC license | Included with CC license | Separate service cost |
| Data model | Key-value pairs per Lookup Type | Single string value | Structured tables/rows |
| Max dataset | 100K rows per type, 100 types/org | One value per variable | Unlimited (plan-dependent) |
| Query capability | Exact key match via rules | Read whole value, parse in flow | SQL filters, joins, aggregation |
| Update method | CSV upload or manual entry | API call or Flow Designer | API call per record |
| Update frequency | Batch (bulk changes) | Low (config changes) | High (per-interaction) |
| Access from Flow Designer | BRE Request activity (native) | Variable picker (native) | HTTP Request activity |
| Access from Connect | Not available | HTTP Request to CC API | HTTP Request to DB API |
| PII allowed | ANI only | Any (mark sensitive) | Any (secure as needed) |

> Full BRE reference: `docs/reference/bre.md`. Setup playbook: `docs/playbooks/bre-setup.md`.

---

## WxCC Global Variables (No Database)

For simple key-value storage (configuration strings, CSV lists, feature flags), a WxCC Global Variable can replace an external database entirely. The value is stored in the CC configuration and accessed via API.

### When to Use

- Storing a short list of values (on-call numbers, routing preferences, feature toggles)
- The data is updated infrequently (admin changes, not per-interaction)
- No query/filter requirements — you read the whole value and parse it in the flow
- You want zero external infrastructure

### When NOT to Use

- Per-interaction data (order lookups, customer records, ticket status)
- Data that needs querying, filtering, or joining
- Large datasets or structured records
- High-frequency updates (multiple writes per second)

### How It Works

1. **Create** a Global Variable in Control Hub > Contact Center > Global Variables, or via POST to the CC config API
2. **Read** the value in a Connect flow via HTTP Request (GET): `GET /organization/{orgId}/cad-variable/{id}` — parse `$.defaultValue`
3. **Update** the value from an SMS flow, web portal, or script via HTTP Request (PUT): `PUT /organization/{orgId}/cad-variable/{id}` — set `defaultValue` in the body
4. In **Flow Designer** flows, the variable is available natively without an HTTP Request node

### API Details

- **Base URL:** `https://api.wxcc-{region}.cisco.com` — region one of `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1` (the 7 codes on Cisco's Salesforce-integration help page, fetched 2026-10-19, and the 7 `wxcli set-cc-region` offers; `in1` resolves in DNS but no Cisco page read names it; only `us1` used live) [owner: `contact-center-core.md` § API Base and Authentication]. Listed `us1, eu1, ca1, jp1, sg1` before 2026-10-19.
- **Auth scopes:** `cjp:config_read` (GET), `cjp:config_write` (PUT/POST)
- **Variable type:** `String` (title case) for CSV lists, JSON strings, or any text value. Verified live 2026-10-19: `"STRING"` is rejected with a 400 and `"String"` is accepted [owner: `contact-center-core.md` § 25 Gotchas, gotcha 21]. Said `STRING` before 2026-10-19.

### Example: On-Call Number List

Store a CSV of phone numbers in a Global Variable's `defaultValue`:

```
+19105551234,+15559876543,+15553334444
```

Connect flow reads it via GET, Evaluate node splits on comma into individual variables, Call Patch dials each sequentially.

### Comparison with External Database

| Aspect | Global Variable | External DB (Supabase, etc.) |
|--------|----------------|------------------------------|
| Setup | Zero — built into WxCC | Provision and configure |
| Cost | Included with CC license | Separate service cost |
| Data model | Single string value | Structured tables/rows |
| Query capability | Read whole value, parse in flow | SQL filters, joins, aggregation |
| Update frequency | Low (config changes) | High (per-interaction) |
| Access from Flow Designer | Native (variable picker) | HTTP Request node |
| Access from Connect | HTTP Request to CC API | HTTP Request to DB API |

---

## Supabase / PostgREST Backend

Supabase exposes a PostgREST API for every table automatically. This section covers the HTTP patterns.

### Base URL

```
https://{project-ref}.supabase.co/rest/v1/{table}
```

### Authentication Headers

```
apikey: {anon_key}
Authorization: Bearer {anon_key}
Content-Type: application/json
```

Note: `Bearer ` requires a space before the key. Missing this space causes 401 errors.

### Security Note

Hardcoding API keys directly in Connect flow headers is acceptable for demos and proofs of concept. For production deployments:
- Enable **Row Level Security (RLS)** with user-scoped tokens
- Use **externalized variables** in Connect (set per flow at launch) for credentials
- Use **Node Runtime Authorization** (OAuth/API key configs stored at service level)

### Data Minimization

Only return fields the agent needs to speak or use in downstream actions via Flow Outcomes. Avoid sending sensitive data (SSN, full credit card numbers, internal system IDs) to the LLM unnecessarily. The LLM processes everything returned in Flow Outcomes — minimize the surface area.

### Accept Header for Response Format

| Header | Response Format | Use When |
|--------|----------------|----------|
| `Accept: application/vnd.pgrst.object+json` | Single JSON object | Lookup by unique field (phone, email) |
| (omit Accept header) | JSON array | Listing multiple records (slots, search results) |

If the single-object Accept header is used but the query returns 0 rows, you get a **406 error**. Use it only when you expect exactly one result.

### GET Filters

| Operation | Syntax | Example |
|-----------|--------|---------|
| Exact match | `eq.{value}` | `?phone_number=eq.5551234567` |
| Case-insensitive partial match | `ilike.*{pattern}*` | `?name=ilike.*blood*` |
| Greater than or equal | `gte.{value}` | `?scheduled_at=gte.2026-03-10T00:00:00` |
| Less than or equal | `lte.{value}` | `?scheduled_at=lte.2026-03-10T23:59:59` |
| Sort ascending | `?order={col}.asc` | `?order=slot_time.asc` |
| Sort descending | `?order={col}.desc` | `?order=created_at.desc` |
| Limit results | `?limit={n}` | `?limit=3` |
| Boolean filter | `eq.{true\|false}` | `?is_booked=eq.false` |

Filters can be combined with `&`:

```
?location_id=eq.{uuid}&is_booked=eq.false&slot_time=gte.{start}&slot_time=lte.{end}&order=slot_time.asc&limit=3
```

### POST (Create Record)

```http
POST /rest/v1/{table}
Content-Type: application/json
Prefer: return=representation

{
  "customer_id": "...",
  "location_id": "...",
  "scheduled_at": "2026-03-10T12:30:00Z",
  "status": "active"
}
```

`Prefer: return=representation` returns the created record including auto-generated fields (IDs, confirmation numbers, timestamps).

### PATCH (Update Record)

```http
PATCH /rest/v1/{table}?{filter}
Content-Type: application/json
Prefer: return=representation

{
  "status": "cancelled"
}
```

Filter identifies which row(s) to update. Always filter on a unique column to avoid updating multiple rows.

### DELETE (Remove Record)

```http
DELETE /rest/v1/{table}?{filter}
```

Filter identifies which row(s) to delete. Always filter on a unique column.

### Soft Delete vs. Hard Delete

For AI agent use cases, **prefer soft delete** (PATCH to set `status='cancelled'`) over hard DELETE:

- Soft delete preserves audit trail and allows "undo"
- Hard delete is permanent — if the LLM calls it incorrectly, data is lost
- Confirmation numbers, appointment history, and reporting all break with hard deletes

Use hard DELETE only for truly disposable data (e.g., clearing test records).

### Response Formats

> ⚠ **The JSONPath-style response-path notation below is NOT documented for the Webex Connect HTTP Request node.** That node's UI uses **key-path selection**; JSONPath-style notation (`$.field_name`, `$[0].field_name`, `$`) appears only on the **Data Parser** page. The paths are kept here because they may well be correct — but treat them as unconfirmed, and check the key paths the node actually offers in your tenant rather than assuming this is a documented format. **Owner: [`webex-connect.md` § HTTP Request Node → Output Variables Tab]**, which wins on any disagreement [sources: https://help.webexconnect.io/docs/http-request-node, https://help.webexconnect.io/docs/data-parser-node].
>
> This hedge applies to both response paths in this section **and** to the "Response path mismatch" row in § Common Errors below.

**Single object** (with `Accept: application/vnd.pgrst.object+json`):
```json
{"id": "...", "first_name": "Jane", "phone_number": "5551234567"}
```
Response path (**format not documented for the HTTP Request node** — see the note above): `$.field_name`

**Array** (without Accept header):
```json
[{"id": "...", "slot_time": "2026-03-10T12:00:00Z"}, {"id": "...", "slot_time": "2026-03-10T14:00:00Z"}]
```
Response path (**format not documented for the HTTP Request node** — see the note above): `$[0].field_name` for first element, or `$` for whole array.

### MCP Server Setup

For Claude Code integration with Supabase, use the MCP server:

```
npx @supabase/mcp-server-supabase@latest --project-ref {project-ref}
```

This enables SQL execution, migrations, log inspection, and more directly from the Claude Code session.

### Common Errors

| Code | Meaning | Fix |
|------|---------|-----|
| 401 | Auth headers missing or malformed | Check `apikey` header and `Authorization: Bearer ` (with space) |
| 400 | Wrong filter column or invalid query | Check URL -- filter column must match actual DB column name |
| 406 | Single-object Accept header but 0 rows returned | Remove Accept header or fix filter to return a row |
| 200 empty `{}` | No rows matched filter | Verify data exists; check filter value spelling/format |
| 200 but wrong field | Response path mismatch | Check `$.field_name` vs `$[0].field_name` for your response format. ⚠ This JSONPath-style notation is **not documented for the HTTP Request node** (its UI uses key-path selection) — see § Response Formats [owner: `webex-connect.md` § HTTP Request Node → Output Variables Tab] |

### Rate Limits

Check your backend's rate limits before production deployment. Supabase free tier allows ~500 requests per 5 minutes; paid tiers vary. Each AI agent action = 1+ API requests per caller turn, so high call volume can hit limits quickly. Monitor API usage and consider connection pooling for high-traffic deployments.

---

## DB-Research Subagent Prompt (Unknown Backends)

When the user's database is not Supabase/PostgREST, use this prompt template to research the correct HTTP patterns:

```
Research how to query [DB_TYPE] via REST API. The user's schema is:
[PASTE SCHEMA HERE]

Determine:
1. Base URL pattern for CRUD operations
2. Authentication header format
3. GET filter syntax (exact match, fuzzy/partial match, date range, ordering, limit)
4. POST body format for creating records
5. PATCH/PUT body format for updating records
6. Response format (JSON structure) and how to extract fields via JSONPath
7. Any special headers needed (content type, accept, prefer/return)

Search the web for official documentation. Return a completed HTTP node config
template showing URL, headers, body, and response path patterns.
```

### When to Use This

- User specifies a database you haven't built for before (Firebase, Airtable, Hasura, custom REST API, etc.)
- User provides a schema but the query patterns are unclear
- The backend has non-standard authentication or filtering syntax

### Mapping DB Needs to HTTP Node Config

Once patterns are known, map each AI agent action to an HTTP node configuration:

| Component | What to Determine |
|-----------|------------------|
| **URL** | Base URL + endpoint + filter syntax |
| **Method** | GET for reads, POST for creates, PATCH/PUT for updates, DELETE for deletions |
| **Headers** | Auth, content type, accept format, any return-representation equivalent |
| **Body** | JSON structure for POST/PATCH with variable picker placeholders |
| **Response Path** | The path used to extract specific fields from the response. ⚠ **JSONPath notation is not documented for the Connect HTTP Request node** — that node's UI uses key-path selection, and JSONPath appears only on the Data Parser page. See the hedge under § Response Formats [owner: `webex-connect.md` § HTTP Request Node → Output Variables Tab] |

The goal is always the same: translate the user's schema and action requirements into concrete HTTP Request node configurations that the Webex Connect flow can execute.

---

## Curl Test Template (Generic)

Always test the API call directly before building the Connect flow:

```bash
curl -s \
  -H "Authorization: Bearer {api_key}" \
  -H "Content-Type: application/json" \
  "{base_url}/{endpoint}?{filters}"
```

Verify:
- HTTP status code (200, 201 for success)
- Response shape matches expected output variables
- Filter returns the correct data
- Auto-generated fields appear in response (for POST with return-representation)

## See Also

- [webex-connect.md](webex-connect.md) — the HTTP Request node that makes these database calls
- [bre.md](bre.md) — the Business Rules Engine, another way to fetch customer data
- [supabase.md](../playbooks/supabase.md) — the Supabase build steps that pair with this reference
