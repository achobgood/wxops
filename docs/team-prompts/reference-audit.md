# Reference Doc Audit Team

## When to use

Periodic sweep (weekly or monthly) to catch drift between the 46 reference docs
in `docs/reference/` and the actual API surface in the OpenAPI specs.

Run after Postman spec sync reports or when specs change.

## Workflow

1. Run Postman spec sync first (if specs may have changed)
2. Copy the spawn prompt below and paste it
3. Teammates produce findings reports (no changes yet)
4. Review findings and decide: fix now, defer, or ignore
5. Tell teammates to apply approved fixes

## Spawn Prompt

~~~
Run a reference doc audit against the current OpenAPI specs.

Create an agent team with 4 teammates:

1. "calling-audit" (Sonnet) — Audit these 16 docs in docs/reference/ against specs/webex-cloud-calling.json:
   - call-features-major.md, call-features-additional.md
   - person-call-settings-handling.md, person-call-settings-media.md, person-call-settings-permissions.md, person-call-settings-behavior.md
   - self-service-call-settings.md
   - location-call-settings-core.md, location-call-settings-media.md, location-call-settings-advanced.md
   - call-routing.md, call-control.md
   - virtual-lines.md, emergency-services.md
   - webhooks-events.md, reporting-analytics.md

2. "admin-audit" (Sonnet) — Audit these 12 docs in docs/reference/ against specs/webex-admin.json and specs/webex-cloud-calling.json:
   - authentication.md, provisioning.md, wxc-sdk-patterns.md
   - admin-org-management.md, admin-identity-scim.md, admin-licensing.md
   - admin-audit-security.md, admin-hybrid.md, admin-partner.md, admin-apps-data.md
   - wxcadm-core.md, wxcadm-advanced.md

3. "devices-audit" (Sonnet) — Audit these 11 docs in docs/reference/ against specs/webex-device.json and specs/webex-cloud-calling.json:
   - devices-core.md, devices-dect.md, devices-workspaces.md, devices-platform.md
   - wxcadm-devices-workspaces.md
   - wxcadm-person.md, wxcadm-locations.md, wxcadm-features.md, wxcadm-routing.md
   - wxcadm-xsi-realtime.md

4. "comms-audit" (Sonnet) — Audit these 7 docs in docs/reference/ against specs/webex-messaging.json and specs/webex-meetings.json:
   - messaging-spaces.md, messaging-bots.md
   - meetings-core.md, meetings-content.md, meetings-settings.md, meetings-infrastructure.md

For each doc, check these 5 criteria:
1. Stale endpoints — paths/methods in the doc that no longer exist in the spec
2. Missing endpoints — paths in the spec not covered by the doc
3. Wrong parameters — field names, types, or required flags that have drifted
4. Broken cross-references — links to other docs that point at renamed/removed sections
5. Residual NEEDS VERIFICATION tags — resolve against current spec or flag as unresolvable

Output findings as a markdown table with columns: File | Line | Issue | Severity | Suggested Fix
Severity levels: critical (wrong info), warning (stale/missing), info (style/cross-ref)

Message other teammates when you find cross-doc inconsistencies
(e.g., "authentication.md references a scope that call-routing.md says was deprecated").

Do NOT make changes yet — produce findings only. I'll review before approving fixes.
~~~

## Doc Assignments

| Teammate | Doc Count | Specs |
|----------|-----------|-------|
| calling-audit | 16 | webex-cloud-calling.json |
| admin-audit | 12 | webex-admin.json, webex-cloud-calling.json |
| devices-audit | 11 | webex-device.json, webex-cloud-calling.json |
| comms-audit | 7 | webex-messaging.json, webex-meetings.json |

Note: `devices-audit` covers wxcadm-* docs. These document the wxcadm library (not OpenAPI).
For wxcadm docs, the teammate should compare against the wxcadm source at `../wxcadm_reference/`
if available, otherwise flag as "cannot verify — wxcadm source not available".

## Check Criteria

1. **Stale endpoints** — paths/methods in the doc that no longer exist in the spec
2. **Missing endpoints** — paths in the spec not covered by the doc
3. **Wrong parameters** — field names, types, or required flags that have drifted
4. **Broken cross-references** — links to other docs that point at renamed/removed sections
5. **Residual `NEEDS VERIFICATION` tags** — resolve against current spec or flag as unresolvable
