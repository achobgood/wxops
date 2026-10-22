# WxCC Debug -- Quick Reference

## HTTP Status Codes

| Code | Meaning | Cause | Fix |
|------|---------|-------|-----|
| 400 | Bad Request | Wrong filter column or invalid query syntax | Check URL -- column must match actual DB column name |
| 401 | Unauthorized | Auth headers missing or malformed | Verify `apikey` + `Authorization: Bearer ` (space required) |
| 406 | Not Acceptable | Single-object Accept header + 0 rows | Remove Accept header or fix filter to return a row |
| 200 `{}` | Empty object | No rows matched | Verify data exists; check filter value |
| 200 `[]` | Empty array | No rows matched | Same as above |
| 200 wrong data | Path mismatch | `$.field` vs `$[0].field` for response format | Match path to actual response shape |

## Variable Substitution Failures

| What you see | Cause | Fix |
|-------------|-------|-----|
| `$(nX.aiAgent.var)` as literal text | Flow Outcomes in Enter JSON mode | Switch to Enter key and value mode |
| `{{variable_name}}` as literal text | Using `{{}}` syntax for Flow Outcomes data in action description | Use quoted names for Flow Outcomes data: `"variable_name"`. `{{variable}}` works for custom data from State Event. |
| Empty/null value in URL filter | Variable typed manually in Connect | Use variable picker (click, don't type) |
| Wrong node number reference | Flow layout changed | Re-select variable using picker |

## Flow Outcomes Troubleshooting

| Issue | Fix |
|-------|-----|
| Agent never receives flow data | Flow Settings > Flow Outcomes > the **Last Execution Status** row: enable **Notify**, then confirm **Notify AI Agent** is the selected notification target. **UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — Cisco documents it as enabled by default for the AI Agent start node, the platform owner describes selecting it explicitly, and the two have not been reconciled. Check the tenant UI and confirm it is selected either way (open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6) |
| Variables resolve as literal strings | Switch from Enter JSON to Enter key and value mode |
| Value is empty | Re-select using variable picker; verify HTTP node actually outputs that variable |
| Wrong value returned | Check which HTTP node the variable picker is pointing to |

## LLM Behavior Issues

| Issue | Mitigation |
|-------|------------|
| Agent skips a required action | "You MUST call [action] before anything else. No exceptions." |
| Agent asks for UUID from caller | Never use UUIDs as slot entities; use phone_number or confirmation_number |
| Agent reads UTC time to caller | Add to instructions: "Convert all times to Eastern (subtract 5 hours). Never mention UTC." |
| Agent stacks multiple questions | Add to instructions: "Ask one question at a time." |
| Chat preview skips actions | Expected behavior; use voice preview for reliable testing |
| Agent doesn't greet caller | Set Welcome Message field (separate from Instructions) |

## Flow Designer HTTP Connector Issues

| Issue | Fix |
|-------|-----|
| 401/403 calling WxCC API from Flow Designer | Use HTTP Connector (Control Hub → Contact Center → Connectors) instead of manual auth; enable **Use Authenticated Endpoint** in HTTPRequest activity |
| Connector not in HTTPRequest dropdown | Connector not authorized or wrong admin role (needs Full Admin, External Admin Full Access, or CC Service Admin) |
| 429 from WxCC API | API calls from Flow Designer are rate limited; add Case activity to detect 429 and route to fallback |
| HTTP Request returns empty after Queue Contact | Add Play Message or Play Music between Queue Contact and HTTP Request to allow processing time |
| Read connector gets 403 on POST/PUT | Connector access level is Read (GET only); create a Read/Write connector for mutating operations |
| Custom Connector not in dropdown | Check Control Hub → Contact Center → Connectors → Custom Connectors; verify OAuth credentials are valid and connector is authorized |
| Custom Connector 401 on external API | Check Grant Type matches the external service's requirements (Client Credentials vs Password Grant); verify token URL and scopes |

## Debug Checklist (Quick Version)

1. Action ENABLED in AI Agent Studio?
2. Notify AI Agent ON in Connect Flow Settings?
3. Action flow linked to correct Connect flow and Made Live?
4. Any requests in DB/API logs?
5. Correct HTTP status code?
6. Response shape matches output variable paths?
7. Flow Outcomes in Enter key and value mode?
8. No prohibited nodes (Delay, Social Hour Check, Receive Node, Call Workflow)?
9. Curl test succeeds with same URL and headers?
10. Agent instructions use forceful language for required actions?
11. Flow Designer HTTP calling WxCC API? Using HTTP Connector with correct access level?
