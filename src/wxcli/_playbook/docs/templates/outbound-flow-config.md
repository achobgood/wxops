# Outbound Flow Config: [FLOW_NAME]

## 1. Flow Purpose

[One sentence: what triggers it, who gets called, what they hear]

## 2. Webhook Payload -- `[External System → POST]`

```json
{
  "field1": "example_value",
  "field2": "+15551234567"
}
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| field1 | String | [description] |
| field2 | String | [description] |

## 3. Webhook URL -- `[Webex Connect → Start node]`

```
https://{auto-generated-url}
```

Authentication header: `key: {service_key}`

## 4. HTTP Request Node (if applicable) -- `[Webex Connect → HTTP Request node]`

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `https://...?id=eq.$(n1.inboundWebhook.field1)` |

Headers:

| Header | Value |
|--------|-------|
| apikey | {api_key} |
| Authorization | Bearer {api_key} |
| Content-Type | application/json |
| Accept | application/vnd.pgrst.object+json |

Output Variables:

| Variable Name | Response Path |
|---------------|---------------|
| descriptive_name | $.field_name |

Sample Response JSON (paste into Parse button):

```json
{
  "field_name": "value"
}
```

## 5. Call User Configuration -- `[Webex Connect → Call User node]`

| Field | Value |
|-------|-------|
| Destination Type | MSISDN |
| Destination | `$(n1.inboundWebhook.customer_phone)` or `+15557500` (paging DID) |
| From Number | [provisioned number or Dynamic] |
| Expiry Time | [seconds or "not set"] |
| Correlation ID | [optional tracking ID] |

## 6. TTS Message -- `[Webex Connect → Voice Node Group → Play node]`

| Setting | Value |
|---------|-------|
| TTS Processor | Azure |
| Voice Type | Neural |
| Language | [e.g., English (US)] |
| Voice | [e.g., AriaNeural] |
| Input Format | [Plain Text / SSML] |

```xml
<speak>
  [Full TTS message with variable references using $(nX.variableName)]
</speak>
```

Use the **variable picker** to insert all variable references. Never type them manually.

## 7. Call Failure Handling

| Exit Path | Wired To |
|-----------|----------|
| onAnswer | Voice Node Group → Play → End |
| onBusy | [End / Log failure] |
| onNoAnswer | [End / Log failure] |
| onReject | [End / Log failure] |
| onError | [End / Log failure] |
| onCallFail | [End / Log failure] |
| onPolicyFail | End |
| onExpiry | End |

## 8. Paging Group Details (if applicable)

| Setting | Value |
|---------|-------|
| Paging Group Name | [name in Control Hub] |
| DID | [E.164 number] |
| Extension | [internal extension] |
| Originator Enforcement | [tested/untested -- see paging playbook section 4] |
| Target Count | [number of phones/speakers] |

## 9. Test Command

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "key: {service_key}" \
  -d '{"field1": "value", "field2": "+15551234567"}' \
  "https://{webhook-url}"
```

Expected: Response code `1002` (queued). Phone rings. TTS plays with resolved variable values. Call disconnects after message completes.

## 10. Integration Notes

[How to trigger from the user's application or database]

Options:
- **Application-level**: POST to webhook URL when status changes in your app
- **Database trigger**: Supabase Database Webhooks, Edge Functions, or `pg_net` extension
- **Polling service**: Lightweight service polls DB and fires webhook on changes
- **CDC**: Debezium or similar Change Data Capture tool

See `docs/playbooks/webhook-triggers.md` Section 10 for detailed DB trigger patterns.
