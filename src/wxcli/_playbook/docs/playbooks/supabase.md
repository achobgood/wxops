# Supabase Playbook

<!-- ref-tag: supabase-v1 -->

## Overview

This playbook covers using Supabase as the data layer for a WxCC AI agent: schema design, migrations, seeding, PostgREST API patterns, and debugging.

---

## 1. Project Config

After creating your Supabase project, record these values:

| Key | Value |
|-----|-------|
| Project ref | `{project-ref}` |
| Base URL | `https://{project-ref}.supabase.co` |
| Anon key | `{anon-key}` |

> **Auth strategy for demos:** Anon key directly in Webex Connect HTTP nodes (no RLS). For production, use RLS policies and service-role keys instead.

---

## 2. Schema

Document your tables here after creating them. For each table, capture:
- Column name and type
- Primary key
- Foreign keys (references)
- Unique constraints
- Default values and auto-generated fields
- Triggers and sequences

### Tables

**{table_name}** — describe purpose
```sql
id             uuid primary key default gen_random_uuid()
column_name    text not null
...
created_at     timestamptz default now()
```

**{table_name}** — describe purpose
```sql
id             uuid primary key default gen_random_uuid()
column_name    text
foreign_id     uuid references {other_table}(id)
...
```

### Auto-Generated Fields (if any)

If your schema uses triggers or sequences to auto-generate values (e.g., confirmation numbers, order IDs), document them here. Example pattern:

```sql
CREATE SEQUENCE {sequence_name} START 1;

CREATE OR REPLACE FUNCTION {function_name}()
RETURNS TRIGGER AS $$
DECLARE
  seq_val integer;
BEGIN
  seq_val := nextval('{sequence_name}');
  NEW.{column} := '{PREFIX}-' || LPAD(seq_val::text, 4, '0');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER {trigger_name}
BEFORE INSERT ON {table_name}
FOR EACH ROW
EXECUTE FUNCTION {function_name}();
```

Do NOT include auto-generated columns in POST bodies — the trigger sets them automatically.

---

## 3. Known IDs (Reference Data)

Record hardcoded IDs for reference data that your flows use directly (e.g., a default location, a test record). This saves the LLM from having to look them up at runtime.

| Item | ID |
|------|----|
| {description} | `{uuid}` |
| {description} | `{uuid}` |

---

## 4. PostgREST API Patterns

Base URL for all requests: `https://{project-ref}.supabase.co/rest/v1/`

### Authentication Headers

```
apikey: {anon-key}
Authorization: Bearer {anon-key}
Content-Type: application/json
Accept: application/vnd.pgrst.object+json   <- forces single object, omit for arrays
```

### Common GET Patterns

```bash
# Exact match
GET /{table}?{column}=eq.{value}

# Fuzzy match (ilike)
GET /{table}?name=ilike.*{search_term}*

# Date range filter
GET /{table}?{timestamp_col}=gte.2026-03-10T00:00:00&{timestamp_col}=lte.2026-03-10T23:59:59

# Combined filters + limit + sort
GET /{table}?{column}=eq.{value}&{other_column}=eq.false&order={sort_col}.asc&limit=3

# No select= needed -- returns full record by default
```

### POST (Create Record)

```bash
POST /{table}
Content-Type: application/json
Prefer: return=representation

{
  "foreign_id": "...",
  "field_name": "value",
  "status": "active"
}
```

`Prefer: return=representation` returns the created record including auto-generated fields.

### PATCH (Update Record)

```bash
PATCH /{table}?{unique_column}=eq.{value}
Content-Type: application/json
Prefer: return=representation

{
  "status": "cancelled"
}
```

---

## 5. Response Formats

**Single object** (with `Accept: application/vnd.pgrst.object+json`):
```json
{"id": "...", "name": "Jane", "email": "jane@example.com"}
```
Use response path: `$.field_name`

**Array** (without Accept header):
```json
[{"id": "...", ...}, {"id": "...", ...}]
```
Use response path: `$[0].field_name` for first element, or `$` for whole array

---

## 6. Running Migrations

Using the Supabase MCP server:

```
mcp__supabase-{name}__apply_migration
  name: "migration_name"
  query: "SQL here"
```

### Applied Migrations (in order)

Track your migrations here as you apply them:

1. `create_schema` — tables and relationships
2. `seed_reference_data` — locations, categories, etc.
3. `seed_test_data` — sample records for testing
4. `add_triggers` — auto-generated fields, updated_at, etc.

---

## 7. Debugging with Logs

Check API logs to see exactly what URL and headers arrived at Supabase:

```
mcp__supabase-{name}__get_logs
  service: "api"
```

Look for:
- Incoming URL — verify filter columns and values
- HTTP status in response — 200/400/401/406
- Empty filter value — means variable substitution failed upstream

---

## 8. Curl Test Template

Test any action URL directly before building the Connect flow:

```bash
curl -s \
  -H "apikey: {anon-key}" \
  -H "Authorization: Bearer {anon-key}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.pgrst.object+json" \
  "https://{project-ref}.supabase.co/rest/v1/{table}?{column}=eq.{value}"
```

Omit `Accept` header when testing array responses.

---

## 9. Common Errors

| Code | Meaning | Fix |
|------|---------|-----|
| 401 | Auth headers missing or malformed | Check `apikey` + `Authorization: Bearer ` (with space) |
| 400 | Wrong filter column or invalid query | Check URL — e.g., `id=eq.` applied to a non-UUID value |
| 406 | Single-object Accept header but 0 rows returned | Remove Accept header or fix filter to match a row |
| 200 empty `{}` | No rows matched filter | Verify data exists; check filter value |
| 200 but wrong field | Response path wrong | Check `$.field_name` vs `$[0].field_name` |

---

## 10. Design Principles for AI-Driven Queries

- **Key off human-speakable values** — use phone numbers, names, or short codes as lookup keys; never pass UUIDs as slot entities (callers can't say them)
- **Avoid array responses** — LLM struggles with arrays; use single-object Accept header where possible
- **Don't use `select=`** — omit it; output variables on the HTTP node define what gets extracted
- **Fuzzy match for names** — use `ilike.*{name}*` so callers can use partial or informal names
- **Hardcode known UUIDs** (like a default location_id) directly in flows rather than making the LLM carry them
- **Supabase returns UTC** — if your agent handles time-sensitive data, add explicit timezone conversion instructions in the action description
