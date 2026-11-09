# v1.11.3 — weekly spec sync

**Verdict:** patch — 23 new command(s); regenerated modules differ (fields, enums or help text)

## New commands

- `ai_receptionist show-call-recordings`
- `ai_receptionist update-call-recordings`
- `auto_attendant list-available-members`
- `auto_attendant list-available-numbers-fax-message`
- `auto_attendant list-members`
- `auto_attendant show-voicemail`
- `auto_attendant update-members`
- `auto_attendant update-passcode`
- `auto_attendant update-voicemail`
- `call_queue list-available-members`
- `call_queue list-available-numbers-fax-message`
- `call_queue list-members`
- `call_queue show-voicemail`
- `call_queue update-members`
- `call_queue update-passcode`
- `call_queue update-voicemail`
- `hunt_group list-available-members`
- `hunt_group list-available-numbers-fax-message`
- `hunt_group list-members`
- `hunt_group show-voicemail`
- `hunt_group update-members`
- `hunt_group update-passcode`
- `hunt_group update-voicemail`

## Spec delta acknowledged by this sync (check 19)

```
spec-snapshot refresh: 29 structural, 0 ID-kind flip(s), 5 prose delta(s)
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/autoAttendants/{}/voicemail/availableMembers
               Features:  Auto Attendant — Read Available Members for an Auto Attendant Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/huntGroups/{}/voicemail/availableMembers
               Features:  Hunt Group — Read Available Members for a Hunt Group Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/aiReceptionists/{}/callRecordings
               AI Receptionist for Webex Calling — Get Call Recording Settings for an AI Receptionist
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/autoAttendants/faxMessage/availableNumbers
               Features:  Auto Attendant — Read Auto Attendant Fax Message Available Phone Numbers
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/autoAttendants/{}/voicemail
               Features:  Auto Attendant — Read Voicemail Settings for an Auto Attendant
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/autoAttendants/{}/voicemail/members
               Features:  Auto Attendant — Retrieve Members for an Auto Attendant Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/huntGroups/faxMessage/availableNumbers
               Features:  Hunt Group — Read Hunt Group Fax Message Available Phone Numbers
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/huntGroups/{}/voicemail
               Features:  Hunt Group — Read Voicemail Settings for a Hunt Group
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/huntGroups/{}/voicemail/members
               Features:  Hunt Group — Retrieve Members for a Hunt Group Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/queues/faxMessage/availableNumbers
               Features:  Call Queue — Read Call Queue Fax Message Available Phone Numbers
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/queues/{}/voicemail
               Features:  Call Queue — Read Voicemail Settings for a Call Queue
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/locations/{}/queues/{}/voicemail/members
               Features:  Call Queue — Retrieve Members for a Call Queue Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /telephony/config/queues/{}/voicemail/availableMembers
               Features:  Call Queue — Read Available Members for a Call Queue Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/aiReceptionists/{}/callRecordings
               AI Receptionist for Webex Calling — Update Call Recording Settings for an AI Receptionist
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/autoAttendants/{}/voicemail
               Features:  Auto Attendant — Configure Voicemail Settings for an Auto Attendant
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/autoAttendants/{}/voicemail/members
               Features:  Auto Attendant — Configure Members for an Auto Attendant Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/autoAttendants/{}/voicemail/passcode
               Features:  Auto Attendant — Reset Voicemail Passcode for an Auto Attendant
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/huntGroups/{}/voicemail
               Features:  Hunt Group — Configure Voicemail Settings for a Hunt Group
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/huntGroups/{}/voicemail/members
               Features:  Hunt Group — Configure Members for a Hunt Group Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/huntGroups/{}/voicemail/passcode
               Features:  Hunt Group — Reset Voicemail Passcode for a Hunt Group
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/queues/{}/voicemail
               Features:  Call Queue — Configure Voicemail Settings for a Call Queue
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/queues/{}/voicemail/members
               Features:  Call Queue — Configure Members for a Call Queue Voicemail
  STRUCTURAL   operation_added    webex-cloud-calling.json PUT /telephony/config/locations/{}/queues/{}/voicemail/passcode
               Features:  Call Queue — Reset Voicemail Passcode for a Call Queue
  STRUCTURAL   field_added        webex-device.json POST /workspaces body:enhancedAI
               #939116%fe83c2
  STRUCTURAL   field_added        webex-device.json POST /workspaces body:enhancedAI.enabled
               !#0397a8
  STRUCTURAL   field_added        webex-device.json POST /workspaces body:enhancedAI.license
               #2f1fa6
  STRUCTURAL   field_added        webex-device.json PUT /workspaces/{} body:enhancedAI
               #438b12
  STRUCTURAL   field_added        webex-device.json PUT /workspaces/{} body:enhancedAI.enabled
               !#0397a8
  STRUCTURAL   field_added        webex-device.json PUT /workspaces/{} body:enhancedAI.license
               #018d06
  PROSE        wording_changed    webex-cloud-calling.json PUT /telephony/config/queues/agents/{}/settings (operation)
               description text changed
  PROSE        wording_changed    webex-device.json GET /workspaces (operation)
               description text changed
  PROSE        wording_changed    webex-device.json GET /workspaces/{} (operation)
               description text changed
  PROSE        constraint_changed webex-device.json POST /workspaces (operation)
               the rules stated in this description changed
  PROSE        wording_changed    webex-device.json PUT /workspaces/{} (operation)
               description text changed
wrote tools/spec_semantics.json (captured 2026-11-09)
```

