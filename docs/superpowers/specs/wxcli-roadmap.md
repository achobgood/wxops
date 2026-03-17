# wxcli Roadmap

**Last updated:** 2026-03-17

## v0.1.0 — Provisioning Core (SHIPPED)

Locations, users, numbers, licenses. The "day 1" operations.

| Command group | Status | Commands |
|---|---|---|
| `configure` | Done | configure, whoami |
| `locations` | Done | list, show, create, enable-calling, update, delete |
| `users` | Done | list, show, create, update, delete |
| `numbers` | Done | list |
| `licenses` | Done | list, show |

Known limitations:
- `numbers assign/unassign` deferred (complex read-modify-write)
- Calling-enabled locations can't be deleted via API (Webex platform limitation)
- OAuth refresh flow not implemented (dev tokens expire in 12h)

---

## v2 — Core Call Features (NEXT)

The features you configure after provisioning a site. These make Webex Calling actually useful.

| Command group | SDK API | Methods | Priority |
|---|---|---|---|
| `auto-attendants` | AutoAttendantApi | 11 | High — IVR menus, after-hours routing |
| `hunt-groups` | HuntGroupApi | 9 | High — ring groups |
| `call-queues` | CallQueueApi | 12 | High — ACD queues |
| `schedules` | ScheduleApi | 9 | High — business hours, holidays (AA/HG/CQ depend on these) |
| `call-park` | CallParkApi | 9 | Medium — park/retrieve |
| `call-pickup` | CallPickupApi | 6 | Medium — pick up ringing phones |
| `paging` | PagingApi | 6 | Medium — overhead paging |
| `voicemail-groups` | VoicemailGroupsApi | 6 | Medium — shared voicemail |
| `operating-modes` | OperatingModesApi | 10 | Medium — open/closed/override |

---

## v3 — Routing + Devices

Call routing infrastructure and phone provisioning.

| Command group | SDK API | Methods | Notes |
|---|---|---|---|
| `call-routing` | CallRoutingApi | varies | Dial plans, route groups, route lists, translation patterns |
| `access-codes` | LocationAccessCodesApi | 4 | Authorization codes |
| `call-intercept` | LocationInterceptApi | 2 | Intercept all calls at location |
| `devices` | TelephonyDevicesApi | 28 | Phones, ATAs, provisioning |
| `dect-devices` | DECTDevicesApi | 26 | DECT base stations + handsets |
| `hotdesk` | HotDeskApi | 2 | Hot desking config |
| `announcements` | AnnouncementsRepositoryApi | 5 | Audio file management |
| `playlists` | PlayListApi | 7 | Music on hold playlists |

---

## v4 — Virtual Lines, Recording, Emergency, Real-time

Advanced features, compliance, and real-time call control.

| Command group | SDK API | Methods | Notes |
|---|---|---|---|
| `virtual-lines` | VirtualLinesApi | 8 | Shared appearances |
| `virtual-extensions` | VirtualExtensionsApi | 14 | Virtual extensions |
| `supervisors` | SupervisorApi | 7 | Supervisor/agent relationships |
| `cx-essentials` | CustomerExperienceEssentialsApi | 3 | CX features |
| `call-recording` | CallRecordingSettingsApi | 15 | Recording policies |
| `emergency-address` | EmergencyAddressApi | 4 | E911 addresses |
| `emergency-services` | OrgEmergencyServicesApi | 2 | Org-level emergency config |
| `calls` | CallsApi | 25 | Real-time: dial, answer, hold, transfer, park |
| `numbers assign/unassign` | PersonSettingsApi | complex | Deferred from v1 — needs dry-run |
| `locations teardown` | multiple | complex | Strip calling config before delete |
| `configure --oauth` | Integration | — | OAuth refresh flow (90-day tokens) |

---

## Cross-cutting (any version)

- Per-user call settings (forwarding, DND, voicemail, caller ID) — 30+ settings
- Per-location call settings (voicemail policy, music on hold, dial patterns)
- Workspace call settings
- Webhooks for call events
- CDR / reporting
