# Playbooks — index

One line per playbook in this folder: the goal it walks through, the reference doc that owns its values (its twin), and what it is not. A playbook owns order, prerequisites and judgment; where it repeats a value it names the owner, and the reference doc wins any disagreement. Design docs that the design skills write are saved to `docs/plans/` in the project folder, not here.

## AI agents

- [ai-agent-studio.md](ai-agent-studio.md) — set up an autonomous AI agent end to end, from Studio access to linking it to Contact Center. Twin: [../reference/ai-agent-studio.md](../reference/ai-agent-studio.md). Not scripted agents.
- [scripted-agent-design.md](scripted-agent-design.md) — design a scripted agent's intents, entities, context flow and responses. Twin: [../reference/ai-agent-studio-scripted.md](../reference/ai-agent-studio-scripted.md). Not the build.
- [scripted-agent-build.md](scripted-agent-build.md) — build and deploy a scripted agent in AI Agent Studio, with fulfillment. Twin: [../reference/ai-agent-studio-scripted.md](../reference/ai-agent-studio-scripted.md). Not the design step.
- [connect-flows.md](connect-flows.md) — build the Webex Connect flow behind an AI agent action. Twin: [../reference/webex-connect.md](../reference/webex-connect.md). Not digital inbound conversations.
- [digital-inbound-agent.md](digital-inbound-agent.md) — connect a digital channel to an AI agent for inbound conversations, with escalation to a person. Twin: [../reference/digital-inbound.md](../reference/digital-inbound.md). Not outbound notifications.
- [cross-channel-escalation.md](cross-channel-escalation.md) — move a chat with an AI agent to a voice call with a person, carrying the transcript through CJDS. Twins: [../reference/digital-inbound.md](../reference/digital-inbound.md), [../reference/cjds.md](../reference/cjds.md). Not a plain transfer.

## Contact Center and Flow Designer

- [wxcc-setup.md](wxcc-setup.md) — one-time Control Hub and Flow Designer setup: site, team, queue, entry point, number, flow assignment, testing. Twin: [../reference/wxcc-platform.md](../reference/wxcc-platform.md). Not Calling locations.
- [webex-api-auth.md](webex-api-auth.md) — call Webex APIs from a Contact Center flow: Service App, token-refresh subflow, custom nodes. Twins: [../reference/webex-connect.md](../reference/webex-connect.md) (custom node steps), [../reference/flow-designer-patterns.md](../reference/flow-designer-patterns.md) (token-refresh subflow). Not wxcli's own sign-in.
- [cjds-integration.md](cjds-integration.md) — set up CJDS: region lookup, Service App token, response shape, event types, failure handling. Twin: [../reference/cjds.md](../reference/cjds.md). Not the `cc-journey` commands.
- [custom-connectors-setup.md](custom-connectors-setup.md) — create a custom connector and link it to an HTTP Request activity. Twin: [../reference/flow-designer-activities/custom-connectors.md](../reference/flow-designer-activities/custom-connectors.md). Not Connect custom nodes.
- [functions-setup.md](functions-setup.md) — create, test, publish and use a Custom Function in a flow. Twins: [../reference/flow-designer-activities/functions-activity.md](../reference/flow-designer-activities/functions-activity.md), [../reference/custom-functions.md](../reference/custom-functions.md). Not Connect Evaluate nodes.
- [dual-call-paging.md](dual-call-paging.md) — an IVR choice that pages a group through the Create Task API while transferring the caller. Twin: [../reference/wxcc-platform.md](../reference/wxcc-platform.md). Not Calling paging groups.

## Data sources

- [bre-setup.md](bre-setup.md) — set up the Business Rules Engine: DataSync access, rules, CSV upload, Flow Designer wiring. Twin: [../reference/bre.md](../reference/bre.md). Not an external database.
- [supabase.md](supabase.md) — set up a Supabase data layer: schema, migrations, PostgREST calls, debugging. Twin: [../reference/db-integration.md](../reference/db-integration.md). Not BRE.

## Webex Connect — outbound notifications

- [outbound-sms.md](outbound-sms.md) — send SMS or MMS notifications. Twin: [../reference/connect-sms.md](../reference/connect-sms.md). Not inbound SMS.
- [outbound-email.md](outbound-email.md) — send email notifications. Twin: [../reference/connect-email.md](../reference/connect-email.md).
- [outbound-rcs.md](outbound-rcs.md) — send RCS notifications with SMS fallback. Twin: [../reference/connect-rcs.md](../reference/connect-rcs.md).
- [outbound-apple-messages.md](outbound-apple-messages.md) — send Apple Messages for Business notifications with SMS fallback. Twin: [../reference/connect-apple-messages.md](../reference/connect-apple-messages.md).
- [outbound-whatsapp.md](outbound-whatsapp.md) — send WhatsApp notifications. Twin: [../reference/connect-whatsapp.md](../reference/connect-whatsapp.md).
- [multi-channel-routing.md](multi-channel-routing.md) — one flow that picks the channel and falls back. Twin: [../reference/connect-multi-channel.md](../reference/connect-multi-channel.md). Not a single channel.
- [outbound-voice.md](outbound-voice.md) — place outbound calls with text-to-speech from Connect. Twin: [../reference/webex-connect-advanced.md](../reference/webex-connect-advanced.md). Not Flow Designer voice flows.

## Webex Connect — inbound and triggers

- [inbound-sms.md](inbound-sms.md) — handle inbound SMS without an AI agent. Twin: [../reference/connect-sms.md](../reference/connect-sms.md). With an AI agent, use digital-inbound-agent.md.
- [inbound-voice.md](inbound-voice.md) — handle inbound calls in Connect. Twin: [../reference/webex-connect-advanced.md](../reference/webex-connect-advanced.md). Not a Flow Designer IVR.
- [sequential-dialing.md](sequential-dialing.md) — ring a list of on-call numbers in turn (Call Patch chaining). Twin: [../reference/webex-connect-advanced.md](../reference/webex-connect-advanced.md). Not a Calling hunt group.
- [webhook-triggers.md](webhook-triggers.md) — start a Connect flow from a webhook, with inbound authentication and response codes. Twins: [../reference/webex-connect.md](../reference/webex-connect.md), [../reference/connect-auth.md](../reference/connect-auth.md), [../reference/connect-response-codes.md](../reference/connect-response-codes.md). Not Webex API webhooks (webhooks-events.md).
- [webex-calling-paging.md](webex-calling-paging.md) — the seam between a Connect flow and a Webex Calling paging group. Owners: [../reference/webex-connect-advanced.md](../reference/webex-connect-advanced.md) for the Connect side, [../reference/call-features-additional.md](../reference/call-features-additional.md) for the paging group. Not Calling paging setup itself.

## Webex Calling

- [calling-build.md](calling-build.md) — a Webex Calling build from request to report: interview, deployment plan, running the commands, bulk work, read-back and the execution report. Twin: [../reference/provisioning.md](../reference/provisioning.md). Not a Contact Center build.

## See Also

- [../reference/INDEX.md](../reference/INDEX.md) — every reference doc, grouped by product.
- [../templates/INDEX.md](../templates/INDEX.md) — the design-doc templates the design skills fill in before a build.
