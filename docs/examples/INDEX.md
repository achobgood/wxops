# Examples — index

One line per example in this folder: what it shows, and what it is not. Examples are working artifacts from real builds; the values in them belong to the org they came from, and the reference docs ([../reference/INDEX.md](../reference/INDEX.md)) own every field and rule they follow.

## FlowIR flows (Flow Designer, built through the API)

- [flowir/simple-inbound.json](flowir/simple-inbound.json) — greeting, queue, hold music, disconnect; shows the text-to-speech connector pattern and Queue Contact. Not a UI export.
- [flowir/menu-routing.json](flowir/menu-routing.json) — greeting, key-press menu, route to queues by digit; shows the Menu activity.
- [flowir/business-hours-routing.json](flowir/business-hours-routing.json) — check a schedule, then the open path or the closed path; shows the Business Hours activity.
- [flowir/data-dip-routing.json](flowir/data-dip-routing.json) — collect an account number, look it up over HTTP, branch on the result; shows the HTTP Request activity and output variables.

## Custom Functions

- [format-store-hours.json](format-store-hours.json) — a working Custom Function definition that turns a schedule API response into spoken store hours in English and Spanish; see ../reference/custom-functions.md.
- [function-import.json](function-import.json) — the empty import file for a Custom Function (every field blank); see ../reference/custom-functions.md and ../playbooks/functions-setup.md.

## Flow import substitution lists

- [flow-designer-autonomous-package-tracking.env.template](flow-designer-autonomous-package-tracking.env.template) — the org-specific values to replace in the autonomous package-tracking sample flow (exported from a Cisco sample org) before importing it; the flow JSON itself is not in this folder.
- [flow-designer-scripted-track-package.env.template](flow-designer-scripted-track-package.env.template) — the same list for the scripted package-tracking sample flow.
- [flow-designer-scripted-doctors-appointment.env.template](flow-designer-scripted-doctors-appointment.env.template) — the same list for the scripted doctor's-appointment sample flow.

## Walkthroughs

- [demo-outbound-notifications.md](demo-outbound-notifications.md) — a worked session of the build-notification skill, from questions to the finished notification config; not a reference.

## See Also

- [../templates/INDEX.md](../templates/INDEX.md) — the blank templates these examples were filled from.
- [../reference/flow-designer-flowir.md](../reference/flow-designer-flowir.md) — the FlowIR format the four flows follow.
