# v1.9.0 — weekly spec sync

**Verdict:** human — blast radius: 106 command names changed > 40 — green is not intended

**Released with maintainer approval (2026-10-07).** The size of this release (106 added names, every one additive: 0 removed, 0 retargeted) held the weekly automation back for two runs; a maintainer reviewed it and approved shipping it as one minor release. Every previously shipped command keeps its name and target.

## New command groups

- `call_controls_members`
- `call_controls_members_me`
- `cc_monitoring_schedules`
- `cc_org_settings`
- `cc_tenant_config`
- `external_data_updates`
- `user_call_settings_members`
- `user_call_settings_members_me`

### Routing decision

# Routing decisions — spec-sync 2026-10-07

Eight new command groups (five carried from the 2026-09-28 refresh, three new since). One line each, per contract §2 B.

- call-controls-members -> call-control (sets wrap-up reasons on a member's last completed Calling call; the WxCC `cc-aux-code` lookalike belongs to contact-center)
- call-controls-members-me -> call-control (same operation, self-scoped; kept with its pair so the token-scope choice is visible at the point of use)
- external-data-updates -> contact-center (writes global-variable values onto one handled CC task per request; calls the region-scoped CC host this skill sets up, not the Webex Calling API its help text names)
- user-call-settings-members -> manage-call-settings (voicemail MESSAGE state; this skill owns per-person voicemail, and `user-settings` voicemail CONFIG is the thing users will confuse it with)
- user-call-settings-members-me -> manage-call-settings (self-scoped twin of the above)
- cc-monitoring-schedules -> contact-center (WxCC supervisor monitoring schedules; sits beside the live-session group `cc-call-monitoring` in the same skill — renamed from the derived `call-monitoring-request` via cli_name_overrides)
- cc-org-settings -> contact-center (WxCC tenant entitlements/thresholds; renamed from `organization-setting` so it cannot be mistaken for the Webex-org `org-settings` group in manage-identity)
- cc-tenant-config -> contact-center (WxCC tenant configuration; renamed from `tenant-configuration` to carry the cc- prefix every WxCC group uses)

## New commands

- `call_controls create-barge-in-me`
- `call_controls create-barge-in-members`
- `call_controls create-divert-me`
- `call_controls create-divert-members`
- `call_controls create-hold-me`
- `call_controls create-hold-members`
- `call_controls create-mute-me`
- `call_controls create-mute-members`
- `call_controls create-park-me`
- `call_controls create-park-members`
- `call_controls create-pause-recording-me`
- `call_controls create-pause-recording-members`
- `call_controls create-pickup-me`
- `call_controls create-pickup-members`
- `call_controls create-pull-me`
- `call_controls create-pull-members`
- `call_controls create-push-me`
- `call_controls create-push-members`
- `call_controls create-reject-me`
- `call_controls create-reject-members`
- `call_controls create-resume-me`
- `call_controls create-resume-members`
- `call_controls create-resume-recording-me`
- `call_controls create-resume-recording-members`
- `call_controls create-retrieve-me`
- `call_controls create-retrieve-members`
- `call_controls create-start-recording-me`
- `call_controls create-start-recording-members`
- `call_controls create-stop-recording-me`
- `call_controls create-stop-recording-members`
- `call_controls create-transfer-me`
- `call_controls create-transfer-members`
- `call_controls create-transmit-dtmf-me`
- `call_controls create-transmit-dtmf-members`
- `call_controls create-unmute-me`
- `call_controls create-unmute-members`
- `call_controls list-history-me`
- `call_controls list-history-members`
- `conference create-add-participant-me`
- `conference create-add-participant-members`
- `conference create-barge-in-me`
- `conference create-barge-in-members`
- `conference create-conference-me`
- `conference create-conference-members`
- `conference create-deafen-me`
- `conference create-deafen-members`
- `conference create-hold-me`
- `conference create-hold-members`
- `conference create-mute-me`
- `conference create-mute-members`
- `conference create-resume-me`
- `conference create-resume-members`
- `conference create-silent-monitor-me`
- `conference create-silent-monitor-members`
- `conference create-supervisor-coach-me`
- `conference create-supervisor-coach-members`
- `conference create-undeafen-me`
- `conference create-undeafen-members`
- `conference create-unmute-me`
- `conference create-unmute-members`
- `conference delete-conference-me`
- `conference delete-conference-members`
- `conference list-conference-me`
- `conference list-conference-members`
- `external_voicemail create-mwi`
- `user_settings list-available-preferred-answer-endpoints`
- `user_settings list-memberships`
- `user_settings show-answer-settings`
- `user_settings update-answer-settings`
- `virtual_line_settings list-available-preferred-answer-endpoints`
- `virtual_line_settings show-answer-settings`
- `virtual_line_settings update-answer-settings`
- `workspace_settings list-available-preferred-answer-endpoints`
- `workspace_settings show-answer-settings`
- `workspace_settings update-answer-settings`
- `call_controls_members create-wrapupreasons`
- `call_controls_members_me create-wrapupreasons`
- `cc_monitoring_schedules create`
- `cc_monitoring_schedules create-delete-reference`
- `cc_monitoring_schedules delete`
- `cc_monitoring_schedules list`
- `cc_monitoring_schedules show`
- `cc_monitoring_schedules update`
- `cc_monitoring_schedules update-call-monitoring`
- `cc_org_settings list`
- `cc_org_settings list-organization-setting`
- `cc_org_settings show`
- `cc_org_settings update`
- `cc_org_settings update-organization-setting`
- `cc_tenant_config list`
- `cc_tenant_config list-tenant-configuration`
- `cc_tenant_config show`
- `cc_tenant_config update`
- `external_data_updates update`
- `user_call_settings_members create-mark-as-read`
- `user_call_settings_members create-mark-as-unread`
- `user_call_settings_members delete-voice-messages`
- `user_call_settings_members list-memberships`
- `user_call_settings_members list-voice-messages`
- `user_call_settings_members show-summary`
- `user_call_settings_members_me create-mark-as-read`
- `user_call_settings_members_me create-mark-as-unread`
- `user_call_settings_members_me delete-voice-messages`
- `user_call_settings_members_me list-memberships`
- `user_call_settings_members_me list-voice-messages`
- `user_call_settings_members_me show-summary`

## Spec delta acknowledged by this sync (check 19)

```
spec-snapshot refresh: 0 structural, 0 ID-kind flip(s), 0 prose delta(s)
wrote tools/spec_semantics.json (captured 2026-10-07)
```

