# Deliberate CLI Gaps (generated)

Emitted by `tools/drift_check.py --write-gaps` — do NOT edit by hand.
Spec operations with no CLI command **on purpose**, per `skip_tags` in
`tools/field_overrides.yaml`. Anything missing from the CLI and not
listed here is drift (drift-gate check 1).

**140 skipped operations across 17 spec/tag pairs.**

## webex-admin.json — Partner Reports/Templates (5 ops)
Reason: canonical: webex-cloud-calling.json
- `DELETE /partner/reports/{}`
- `GET /partner/reports`
- `GET /partner/reports/templates`
- `GET /partner/reports/{}`
- `POST /partner/reports`

## webex-admin.json — People (6 ops)
Reason: canonical: webex-cloud-calling.json
- `DELETE /people/{}`
- `GET /people`
- `GET /people/me`
- `GET /people/{}`
- `POST /people`
- `PUT /people/{}`

## webex-admin.json — Recording Report (4 ops)
Reason: canonical: webex-cloud-calling.json
- `GET /recordingReport/accessDetail`
- `GET /recordingReport/accessSummary`
- `GET /recordingReport/meetingArchiveSummaries`
- `GET /recordingReport/meetingArchives/{}`

## webex-admin.json — Reports (4 ops)
Reason: canonical: webex-cloud-calling.json
- `DELETE /reports/{}`
- `GET /reports`
- `GET /reports/{}`
- `POST /reports`

## webex-cloud-calling.json — Beta Call Settings For Me With Userhub Phase1 (16 ops)
Reason: Beta APIs — unstable contracts, excluded until GA
- `DELETE /telephony/config/people/me/settings/executive/callFiltering/criteria/{}`
- `GET /telephony/config/people/me/announcementLanguages`
- `GET /telephony/config/people/me/countries/{}`
- `GET /telephony/config/people/me/settings/callPolicies`
- `GET /telephony/config/people/me/settings/doNotDisturb`
- `GET /telephony/config/people/me/settings/executive/alert`
- `GET /telephony/config/people/me/settings/executive/callFiltering`
- `GET /telephony/config/people/me/settings/executive/callFiltering/criteria/{}`
- `GET /telephony/config/people/me/settings/executive/screening`
- `POST /telephony/config/people/me/settings/executive/callFiltering/criteria`
- `PUT /telephony/config/people/me/settings/callPolicies`
- `PUT /telephony/config/people/me/settings/doNotDisturb`
- `PUT /telephony/config/people/me/settings/executive/alert`
- `PUT /telephony/config/people/me/settings/executive/callFiltering`
- `PUT /telephony/config/people/me/settings/executive/callFiltering/criteria/{}`
- `PUT /telephony/config/people/me/settings/executive/screening`

## webex-cloud-calling.json — Beta Device Call Settings With Dynamic Device Settings (1 ops)
Reason: Beta APIs — unstable contracts, excluded until GA
- `GET /telephony/config/devices/dynamicSettings/validationSchema`

## webex-cloud-calling.json — Beta Settings Features For Barge-In (2 ops)
Reason: Beta APIs — unstable contracts, excluded until GA
- `GET /telephony/config/people/me/settings/bargeIn`
- `PUT /telephony/config/people/me/settings/bargeIn`

## webex-cloud-calling.json — Devices (6 ops)
Reason: canonical: webex-device.json
- `DELETE /devices/{}`
- `GET /devices`
- `GET /devices/{}`
- `PATCH /devices/{}`
- `POST /devices`
- `POST /devices/activationCode`

## webex-cloud-calling.json — Workspaces (6 ops)
Reason: canonical: webex-device.json
- `DELETE /workspaces/{}`
- `GET /workspaces`
- `GET /workspaces/{}`
- `GET /workspaces/{}/capabilities`
- `POST /workspaces`
- `PUT /workspaces/{}`

## webex-contact-center.json — Activities (3 ops)
Reason: flow-store surface embedded in the CC spec (/flow-store/... paths);
- `GET /flow-store/{}/project/{}/v2/activities`
- `GET /flow-store/{}/project/{}/v2/activities/{}`
- `GET /flow-store/{}/project/{}/v2/activities/{}/inputs/{}/choices`

## webex-contact-center.json — Events (1 ops)
Reason: webex-flow-store.json. Deliberate gap in the tracked CLI. 6 ops.
- `GET /flow-store/{}/project/{}/v2/event-specifications`

## webex-contact-center.json — Functions (11 ops)
Reason: colon-action paths (/functions/{id}:publish) — generator cannot
- `DELETE /{}/functions/{}`
- `GET /{}/functions`
- `GET /{}/functions/{}`
- `POST /{}/functions`
- `POST /{}/functions/{}:export`
- `POST /{}/functions/{}:lock`
- `POST /{}/functions/{}:publish`
- `POST /{}/functions/{}:test`
- `POST /{}/functions/{}:unlock`
- `POST /{}/functions:import`
- `PUT /{}/functions/{}`

## webex-contact-center.json — Templates (2 ops)
Reason: covered by the dev-only fs-* groups generated from the untracked
- `GET /flow-store/{}/project/{}/v2/templates`
- `GET /flow-store/{}/project/{}/v2/templates/{}`

## webex-device.json — Device Call Settings (47 ops)
Reason: canonical: webex-cloud-calling.json
- `DELETE /telephony/config/devices/backgroundImages`
- `DELETE /telephony/config/devices/lineKeyTemplates/{}`
- `GET /telephony/config/devices/availableMembers/count`
- `GET /telephony/config/devices/backgroundImages`
- `GET /telephony/config/devices/dectNetworks/supportedDevices`
- `GET /telephony/config/devices/dects/supportedDevices`
- `GET /telephony/config/devices/lineKeyTemplates`
- `GET /telephony/config/devices/lineKeyTemplates/{}`
- `GET /telephony/config/devices/settings`
- `GET /telephony/config/devices/{}`
- `GET /telephony/config/devices/{}/availableMembers`
- `GET /telephony/config/devices/{}/availableMembers/count`
- `GET /telephony/config/devices/{}/layout`
- `GET /telephony/config/devices/{}/members`
- `GET /telephony/config/devices/{}/settings`
- `GET /telephony/config/jobs/devices/applyLineKeyTemplate`
- `GET /telephony/config/jobs/devices/applyLineKeyTemplate/{}`
- `GET /telephony/config/jobs/devices/applyLineKeyTemplate/{}/errors`
- `GET /telephony/config/jobs/devices/callDeviceSettings`
- `GET /telephony/config/jobs/devices/callDeviceSettings/{}`
- `GET /telephony/config/jobs/devices/callDeviceSettings/{}/errors`
- `GET /telephony/config/jobs/devices/rebuildPhones`
- `GET /telephony/config/jobs/devices/rebuildPhones/{}`
- `GET /telephony/config/jobs/devices/rebuildPhones/{}/errors`
- `GET /telephony/config/locations/{}/devices/settings`
- `GET /telephony/config/people/{}/devices`
- `GET /telephony/config/people/{}/devices/count`
- `GET /telephony/config/people/{}/devices/settings`
- `GET /telephony/config/workspaces/{}/devices`
- `GET /telephony/config/workspaces/{}/devices/settings`
- `POST /telephony/config/devices/actions/previewApplyLineKeyTemplate/invoke`
- `POST /telephony/config/devices/actions/validateMacs/invoke`
- `POST /telephony/config/devices/lineKeyTemplates`
- `POST /telephony/config/devices/{}/actions/applyChanges/invoke`
- `POST /telephony/config/devices/{}/actions/backgroundImageUpload/invoke`
- `POST /telephony/config/jobs/devices/applyLineKeyTemplate`
- `POST /telephony/config/jobs/devices/callDeviceSettings`
- `POST /telephony/config/jobs/devices/rebuildPhones`
- `PUT /telephony/config/devices/lineKeyTemplates/{}`
- `PUT /telephony/config/devices/{}`
- `PUT /telephony/config/devices/{}/layout`
- `PUT /telephony/config/devices/{}/members`
- `PUT /telephony/config/devices/{}/settings`
- `PUT /telephony/config/people/{}/devices/settings`
- `PUT /telephony/config/people/{}/devices/settings/hoteling`
- `PUT /telephony/config/workspaces/{}/devices`
- `PUT /telephony/config/workspaces/{}/devices/settings`

## webex-device.json — Device Call Settings With Device Dynamic Settings (10 ops)
Reason: canonical: webex-cloud-calling.json
- `GET /telephony/config/devices/dynamicSettings/settingsGroups`
- `GET /telephony/config/jobs/devices/dynamicDeviceSettings`
- `GET /telephony/config/jobs/devices/dynamicDeviceSettings/{}`
- `GET /telephony/config/jobs/devices/dynamicDeviceSettings/{}/errors`
- `GET /telephony/config/supportedDevices`
- `POST /telephony/config/jobs/devices/dynamicDeviceSettings`
- `POST /telephony/config/lists/devices/dynamicSettings/actions/getSettings/invoke`
- `POST /telephony/config/lists/devices/{}/dynamicSettings/actions/getSettings/invoke`
- `POST /telephony/config/lists/locations/{}/devices/dynamicSettings/actions/getSettings/invoke`
- `PUT /telephony/config/devices/{}/dynamicSettings`

## webex-device.json — Hot Desk (2 ops)
Reason: canonical: webex-cloud-calling.json
- `DELETE /hotdesk/sessions/{}`
- `GET /hotdesk/sessions`

## webex-meetings.json — Recordings (14 ops)
Reason: canonical: webex-admin.json (same 14 /recordings ops in both specs)
- `DELETE /admin/recordings/{}`
- `DELETE /recordings/{}`
- `GET /admin/recordings`
- `GET /group/recordings`
- `GET /group/recordings/{}`
- `GET /recordings`
- `GET /recordings/{}`
- `POST /admin/recordings/query`
- `POST /recordings/accessList`
- `POST /recordings/purge`
- `POST /recordings/query`
- `POST /recordings/restore`
- `POST /recordings/softDelete`
- `POST /recordings/{}/accessList`
