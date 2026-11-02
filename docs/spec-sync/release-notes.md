# v1.11.2 — weekly spec sync

**Verdict:** patch — 0 new command(s); regenerated modules differ (fields, enums or help text)

## Spec delta acknowledged by this sync (check 19)

```
spec-snapshot refresh: 1 structural, 0 ID-kind flip(s), 7 prose delta(s)
  STRUCTURAL   field_added        webex-cloud-calling.json PUT /telephony/config/queues/agents/{}/settings body:agentACDState
               #e14294=AVAILABLE|SIGN_IN|SIGN_OUT|UNAVAILABLE|WRAP_UP
  PROSE        wording_changed    webex-cloud-calling.json POST /telephony/config/locations/{}/aiReceptionists/{}/intents body:name
               description text changed
  PROSE        wording_changed    webex-cloud-calling.json PUT /telephony/config/locations/{}/aiReceptionists/{}/intents/{} body:name
               description text changed
  PROSE        wording_changed    webex-cloud-calling.json PUT /telephony/config/people/me/settings/queues body:agentACDState
               description text changed
  PROSE        wording_changed    webex-cloud-calling.json PUT /telephony/config/people/me/settings/secondaryLines/{}/queues body:agentACDState
               description text changed
  PROSE        wording_changed    webex-cloud-calling.json PUT /telephony/config/queues/agents/{}/settings (operation)
               description text changed
  PROSE        wording_changed    webex-contact-center.json POST /usage-reports (operation)
               description text changed
  PROSE        constraint_changed webex-meetings.json POST /meetingParticipants/admit (operation)
               the rules stated in this description changed
wrote tools/spec_semantics.json (captured 2026-11-02)
```

