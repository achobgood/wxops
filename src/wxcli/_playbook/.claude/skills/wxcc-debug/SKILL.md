---
name: wxcc-debug
description: |
  Debug a failing WxCC AI agent action. Walks through a systematic checklist
  covering the Webex Connect action flow, HTTP Request node, headers, Flow
  Outcomes, AI Agent Studio action config, and CCAI wiring.
  Use for: when an autonomous agent action doesn't fire, returns wrong data,
  times out, or produces an error.
  NOT for: Flow Designer voice flows, scripted agent fulfillment, or standalone Connect flows.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [symptom-or-action-name]
---

# WxCC Debug Workflow

> **Not this skill:** a Flow Designer voice flow that isn't routing → `docs/reference/flow-designer-patterns.md` § Flow Debugging; scripted agent fulfillment → check its inline fulfillment wiring in the conversation flow; a standalone Connect flow that isn't an agent action → check it node by node in Connect.

## Step 0: Load references

YOU MUST use the Read tool on this file before proceeding. Do not skip this step.

1. Read this skill's `reference.md` for the troubleshooting lookup table, common error codes, and platform-specific debug patterns

**Checkpoint — do NOT proceed until you can confirm:**
- You have loaded `reference.md` and can see the troubleshooting table rows
- You will only reference error codes, field names, and debug steps that appear in the loaded docs

If you cannot confirm, go back and read the docs.

## Step 1: Identify the symptom

Ask the user: **What happened?** Map their answer to one of these categories:

| Category | User says something like... |
|----------|-----------------------------|
| Action never fired | "Nothing happened", "Agent didn't do anything", "No response" |
| HTTP error | "Got a 400/401/406 error", "Error in logs" |
| 200 but wrong data | "Wrong name came back", "Fields are empty", "Missing data" |
| Agent gives wrong info | "Said the wrong time", "Read back gibberish", "Variables showed as text" |
| 30-second timeout | "Agent went silent for 30 seconds", "Timed out" |
| Agent skips action | "Agent answered without looking anything up", "Didn't call the action" |
| BRE routing wrong | "Caller went to wrong queue", "VIP caller not recognized", "BRE returns NotFound" |

## Step 2: Check the obvious first

These two toggles are the most common root causes. Check them FIRST before doing anything else:

1. **Is the action ENABLED in AI Agent Studio?**
   - If OFF, the action silently does not execute. No error, no log, nothing.
   - This is the #1 most common issue.

2. **Is Notify AI Agent enabled in the Connect flow?**
   - Flow Settings > Flow Outcomes > the **Last Execution Status** row > enable **Notify** > confirm **Notify AI Agent** is the selected notification target
   - **UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — Cisco documents it as enabled by default for the AI Agent start node, the platform owner describes selecting it explicitly, and the two have not been reconciled. Check the tenant UI and confirm it is selected either way — open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6. Do not assume it is already on.
   - If not enabled, the flow runs but the agent never receives the response data.

3. **Is the HTTP Request URL correct for reads vs. writes?**
   - CJDS reads (alias lookup, events query): `api.wxcc-{region}.cisco.com` (verified 2026-10-19 on `us1`; until 2026-10-19 this line gave `api-jds.prod-{region}.ciscowxdap.com`, which does not resolve: DNS gives NXDOMAIN)
   - CJDS writes (event posting): `api.wxcc-{region}.cisco.com`
   - These are DIFFERENT domains. Using the wrong one returns 500 or 404.

## Step 3: Check DB/API logs

Pull recent API logs to see what actually hit the database:

- Use your database's log viewer or API logs
- Look for:
  - **Was a request received at all?** (No request = action never fired)
  - **What URL was called?** (Check for empty filter values, wrong columns)
  - **What status code was returned?** (Match to the table below)
  - **What was the response body?** (Empty array? Wrong record?)

## Step 4: Match symptom to cause and fix

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No request in DB logs | Action never fired -- enable toggle OFF or LLM skipped it | Check enable toggle; strengthen instruction language ("You MUST call...") |
| No request in DB logs (toggle ON) | Action flow not linked or not Made Live in Connect | Verify the action in AI Agent Studio points to the correct Connect flow and that the action flow is Made Live (separate from the parent flow) |
| 400 Bad Request | Wrong filter column or invalid query syntax | Check URL -- e.g., `id=eq.` when you need `phone_number=eq.` |
| 401 Unauthorized | Auth headers missing or malformed | Check `apikey` header and `Authorization: Bearer ` (with space before key) |
| 406 Not Acceptable | `Accept: application/vnd.pgrst.object+json` header but 0 rows returned | Remove Accept header (switch to array response) or fix filter to match a row |
| 200 but empty response | No rows matched the filter | Verify data exists in DB; check filter value spelling and format |
| 200 but wrong field values | Response path mismatch in output variables | Check `$.field_name` vs `$[0].field_name` for your response format |
| Variables show as literal `$(nX.var)` strings | Flow Outcomes using Enter JSON mode instead of Enter key and value mode | Switch to Enter key and value in the Flow Outcomes settings area — click **Flow Settings** on the Flow Builder page, then **Flow Outcomes**, then the **Last Execution Status** row (there is no Flow Outcomes node on the canvas) |
| Variables show as literal `{{var}}` strings | Using `{{variable}}` syntax to reference Flow Outcomes data in action description | Use quoted variable names for Flow Outcomes data: `"variable_name"`. Note: `{{variable}}` works correctly for custom data variables from Flow Designer State Event. |
| 30-second timeout | Prohibited node in the Connect flow | Remove Delay, Social Hour Check, Receive Node, or Call Workflow nodes |
| Agent says wrong time | UTC timestamps not converted | Add timezone conversion note in action description and agent instructions |
| Agent skips the action entirely | LLM non-determinism | Add forceful language: "You MUST call [action] before anything else. No exceptions." |
| Agent uses wrong data between actions | LLM lost a UUID between actions | Never pass UUIDs as slot entities; use phone_number or confirmation_number instead |
| Output variable `id` collision | Multiple HTTP nodes both output `id` | Rename to descriptive names: `customer_id`, `order_id` |
| Flow Designer HTTP returns 401/403 calling WxCC API | Manual auth headers instead of HTTP Connector, or connector misconfigured | Use an HTTP Connector (Control Hub → Contact Center → Connectors) with **Use Authenticated Endpoint** enabled; check connector access level (Read vs Read/Write) |
| Flow Designer HTTP returns 429 | WxCC API rate limit hit | Add a Case activity to detect 429 and route to fallback path |
| Flow Designer HTTP returns empty after Queue Contact | Queue Contact hasn't finished processing | Add a Play Message or Play Music activity between Queue Contact and HTTP Request |
| SMS/Email node fails silently | Gateway Submit mode not set, or invalid destination number/email | Check Wait For setting (must be "Gateway Submit"); verify destination variable resolves |
| Evaluate node returns empty | JavaScript error in script, or variable name is case-sensitive | Check script syntax; verify variable names match exactly (case-sensitive) |
| Branch node always takes default path | Condition variable not matching — often a type mismatch (string vs number) | Log the variable value with Transition Actions; check if status code is string "200" not number 200 |
| RCS message not received | Recipient device doesn't support RCS, or capability check skipped | Add RCS Capability node before RCS Message; fall back to SMS on failure |
| 406 on fuzzy search (ilike) | `Accept: application/vnd.pgrst.object+json` used but ilike matched multiple rows | Switch to array response (remove Accept header) with `limit=1`, or use exact match instead of ilike |
| Condition expression rejects `== ""` | Flow Designer Condition node cannot compare to empty string — quotes collide with expression syntax | Use a numeric field instead: parse `$.meta.resultCount` and check `{{count}} > 0` |
| Set Variable appends `.substring(2)` literally | Flow Designer Set Variable has no string functions — it treats function calls as literal text | Design API calls to accept raw variable formats; use APIs that normalize input (e.g., CJDS alias lookup normalizes phone formats) |
| CJDS RSQL filter returns 400 ParseException | Filter values are unquoted — RSQL requires single quotes | Use `phone=='value'` not `phone==value` |
| CJDS event POST returns 400 "workspaceId missing" | `workspaceId` not passed as query parameter on event posting endpoint | Add `workspaceId` as a Query Parameter key-value pair, not in the URL path |
| CJDS event POST returns 500 "not a valid HTTP URL" | Wrong base URL — event posting uses `api.wxcc-{region}.cisco.com` | CJDS reads and writes use one host, `api.wxcc-{region}.cisco.com` (verified 2026-10-19 on `us1`). Until 2026-10-19 this row said reads use `api-jds.prod-{region}.ciscowxdap.com`; that host does not resolve (NXDOMAIN) |
| CJDS alias lookup returns 404 for known caller | Wrong URL path — missing `/admin` prefix | Use `/admin/v1/api/person/workspace-id/...` not `/v1/api/person/workspace-id/...` |
| HTTP Request Query Parameters empty at runtime | Parameters typed manually in URL instead of Query Parameters field | Use the Query Parameters key-value rows (click Add New), not URL query string |
| SCIM2 API returns 401 but People API works with same token | Wrong OAuth scope — SCIM2 requires `identity:people_read`, not `spark-admin:people_read` | Create an OAuth Integration or Service App with `identity:people_read` scope explicitly selected. PATs may not include it. |
| BRE Request returns "NotFound" for a known ANI | `context` parameter value doesn't match the Context name in BRE Utility, or ANI format mismatch (e.g., `+17251600011` in the call vs `7251600011` in BRE data) | Verify `context` value is case-sensitive exact match; verify ANI format in BRE DataSync matches what `{{NewPhoneContact.ANI}}` returns (with or without country code prefix) |
| BRE Request times out | No data uploaded for the specified Lookup Type, or DataSync URL is wrong region | Check BRE Data List in DataSync portal; verify you're using the correct regional URL |
| BRE Request returns empty httpResponseBody | Rules not created or not marked Active in BRE Utility | Open BRE Utility > Contexts > verify rules exist and the Active checkbox is checked |
| BRE Request returns 5xx errors | BRE service issue or malformed Drools rule syntax | Check rule syntax in the Rule Editor; contact Cisco TAC if service-level issue |

## Step 5: Test directly

Run the same API call with curl to isolate whether the issue is in Connect or in the API:

```bash
curl -s \
  -H "apikey: {anon_key}" \
  -H "Authorization: Bearer {anon_key}" \
  -H "Content-Type: application/json" \
  "{base_url}/rest/v1/{table}?{filters}"
```

Compare the curl response to what the Connect flow's output variables expect:
- Does the response shape match? (single object vs. array)
- Are all expected fields present?
- Does the filter return the correct row?

If curl works but the flow doesn't, the issue is in Connect (variable picker, headers, Flow Outcomes config).
If curl also fails, the issue is in the URL, headers, or data.

## Step 6: Verify the fix

After applying the fix:

1. Have the user test end-to-end again (voice preview is more reliable than chat preview)
2. Check DB logs to confirm the request arrives with correct URL and headers
3. Verify the response contains the expected data
4. Confirm the agent speaks the correct information back to the caller

If the fix didn't work, return to Step 4 and check the next most likely cause.

---

## ANTI-HALLUCINATION GUARD

Every error code, header value, node name, field name, and troubleshooting step in your output MUST appear verbatim in the docs you loaded in Step 0 or in the symptom table above. If you are about to suggest a fix you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
