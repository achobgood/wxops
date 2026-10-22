# Action Config: [ACTION_NAME]

## 1. Action Description — `[AI Agent Studio]`

(max 1024 chars; reference returned variables in quotes e.g. "variable_name")

```
Call this action when [trigger condition].
Requires: [entity_name] (collected from the user)
Returns: "returned_variable_1", "returned_variable_2", "returned_variable_3"
[Instructions for how the agent should use the returned data]
```

## 2. Input Entities (called "Slots" in the AI Agent Studio UI) — `[AI Agent Studio]`

| Entity Name | Entity Type | Entity Description | Entity Example | Required |
|-------------|-------------|-------------------|----------------|----------|
| entity_name | String | Description the LLM reads to know what to collect | example_value | Yes |

## 3. Configure AI Agent Event -- Sample JSON — `[Webex Connect → Receive node]`

One key per input entity, with realistic example values:

```json
{
  "entity_name": "example_value"
}
```

## 4. HTTP Method — `[Webex Connect → HTTP Request node]`

`GET` / `POST` / `PATCH`

## 5. URL — `[Webex Connect → HTTP Request node]`

```
https://{your-project-ref}.supabase.co/rest/v1/{table_name}?filter_column=eq.$(n2.aiAgent.entity_name)
```

Variable picker placeholders use the format `$(n{nodeNumber}.aiAgent.{entity_name})`. Always use the variable picker in Webex Connect -- never type these manually.

For multi-node flows, document each node separately:

```
Node 1 (GET):  https://...
Node 2 (POST): https://...
```

## 6. Headers — `[Webex Connect → HTTP Request node]`

| Header | Value | Notes |
|--------|-------|-------|
| apikey | {your_api_key} | Required for all requests |
| Authorization | Bearer {your_api_key} | Space before key is required |
| Content-Type | application/json | Always include |
| Accept | application/vnd.pgrst.object+json | Omit for array responses |
| Prefer | return=representation | POST/PATCH only -- returns created/updated record |

Adjust per action:
- **Single object response**: include all 4 base headers
- **Array response**: omit `Accept` header
- **POST/PATCH**: add `Prefer: return=representation`

## 7. Output Variables — `[Webex Connect → HTTP Request node → Output Variables tab]`

| Output Variable Name | Response Path |
|----------------------|---------------|
| descriptive_name | $.field_name |

Notes:
- Use `$.field_name` for single-object responses
- Use `$` for whole array, `$[0].field_name` for first element (avoid if possible)
- Rename `id` to a descriptive name after parsing (e.g., `customer_id`, `order_id`)

## 8. Sample Response JSON — `[Webex Connect → HTTP Request node → Parse button]`

Paste this into the Parse button on the HTTP node to auto-generate output variable rows. Rename `id` to a descriptive name after parsing.

```json
{
  "id": "uuid-here",
  "field_1": "value_1",
  "field_2": "value_2"
}
```

## 9. Flow Outcomes (Enter key and value) — `[Webex Connect → Flow Settings → Flow Outcomes]`

Flow Outcomes is **not a node** — click **Flow Settings** on the Flow Builder page, then **Flow Outcomes**, then open the **Last Execution Status** row. The End node carries no outcome tag.

| Key | Value (use variable picker) |
|-----|----------------------------|
| variable_name | $(nX.httpNode.variable_name) |

**IMPORTANT:**
- Use **Enter key and value**, NOT Enter JSON mode (Enter JSON does not resolve variables)
- Use the variable picker to insert values -- do not type manually
- **One key-set per flow** — you cannot return a different payload per Branch leg. Converge the legs and return a status/error variable through this single key-set. Max payload **16,000 characters**
- Enable **Notify** on the **Last Execution Status** row and confirm **Notify AI Agent** is the selected notification target (see `docs/reference/webex-connect.md` § "The Last Execution Status row" — whether it is pre-selected by default is **UNVERIFIED**)

## 10. Test Result — `[Terminal]`

Run this curl before handing config to the user. Replace placeholders with actual values.

```bash
curl -s \
  -H "apikey: {your_api_key}" \
  -H "Authorization: Bearer {your_api_key}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.pgrst.object+json" \
  "https://{your-project-ref}.supabase.co/rest/v1/{table_name}?filter=eq.value"
```

Expected: HTTP 200 with matching record(s). Verify the response contains all fields referenced in the Action Description.
