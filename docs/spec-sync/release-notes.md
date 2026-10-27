# v1.11.1 — weekly spec sync

**Verdict:** patch — 1 new command(s); regenerated modules differ (fields, enums or help text)

## New commands

- `dect_devices update-debug-level`

## Removed flag

- `cc-flow publish --skip-validation` is gone. Cisco removed the `skipValidation`
  query parameter from the flow-publish API, so `cc-flow publish` now always runs
  pre-publish validation. A script that passes `--skip-validation` will exit 2
  with `No such option`; drop the flag.

## Spec delta acknowledged by this sync (check 19)

```
spec-snapshot refresh: 2 structural, 0 ID-kind flip(s), 24 prose delta(s)
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/dectNetworks/{}/debugLevel
               DECT Devices Settings — Update DECT Network Debug Level
  STRUCTURAL   field_removed      webex-contact-center.json POST /{}/project/{}/flows/{}:publish query:skipValidation
               #755bdf
  PROSE        wording_changed    webex-cloud-calling.json PUT /telephony/config/locations/{}/dectNetworks/{} (operation)
               description text changed
  PROSE        constraint_changed webex-contact-center.json DELETE /monitor/{} (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-contact-center.json GET /agents/activities (operation)
               description text changed
  PROSE        wording_changed    webex-contact-center.json GET /agents/statistics (operation)
               description text changed
  PROSE        constraint_changed webex-contact-center.json GET /monitor/sessions (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-contact-center.json POST /agents/buddyList (operation)
               description text changed
  PROSE        constraint_changed webex-contact-center.json POST /agents/login (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-contact-center.json POST /agents/reload (operation)
               description text changed
  PROSE        wording_changed    webex-contact-center.json POST /captures/query (operation)
               description text changed
  PROSE        constraint_changed webex-contact-center.json POST /monitor (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-contact-center.json POST /monitor body:monitorType
               description text changed
  PROSE        constraint_changed webex-contact-center.json POST /monitor/{}/bargeIn (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json POST /monitor/{}/coach (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json POST /monitor/{}/end (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json POST /monitor/{}/hold (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json POST /monitor/{}/unhold (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json POST /v2/agents/login (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-contact-center.json POST /v2/agents/reload (operation)
               description text changed
  PROSE        constraint_changed webex-contact-center.json PUT /agents/logout (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json PUT /agents/session/state (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json PUT /v2/agents/logout (operation)
               the rules stated in this description changed
  PROSE        constraint_changed webex-contact-center.json PUT /v2/agents/session/state (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-contact-center.json PUT /v2/agents/session/state body:agentId
               description text changed
  PROSE        wording_changed    webex-contact-center.json PUT /v2/agents/session/state body:state
               description text changed
wrote tools/spec_semantics.json (captured 2026-10-26)
```

