# Reference docs — index

One line per reference doc in this folder: what it covers, and what it is not. A reference doc owns **values** — field names, valid values, limits, ports, error codes, syntax. For step-by-step procedures, see the playbooks index ([../playbooks/INDEX.md](../playbooks/INDEX.md)). `archive/`, where it exists, holds only local, untracked files; nothing in it is listed here or shipped.

## The wxcli command layer

- [wxcli-behavior.md](wxcli-behavior.md) — how the `wxcli` command layer behaves: common flags, paging, partner multi-org, the eleven Known Issues, cleanup; not a Webex API reference.

## Calling

- [provisioning.md](provisioning.md) — users, licenses, locations and number inventory for Webex Calling; not per-user number assignment (person-call-settings-behavior.md).
- [call-features-major.md](call-features-major.md) — auto attendants, call queues and hunt groups; not Contact Center queues (contact-center-core.md) and not AI Receptionist.
- [call-features-additional.md](call-features-additional.md) — paging, call park, call pickup, voicemail groups, Customer Assist queues; not the three major features above.
- [ai-receptionist.md](ai-receptionist.md) — AI Receptionist: an AI that answers calls, its intents and knowledge bases; not a key-press auto attendant and not a Contact Center AI agent.
- [person-call-settings-handling.md](person-call-settings-handling.md) — per-person call forwarding, do not disturb, call waiting, simultaneous and sequential ring; not location-level settings.
- [person-call-settings-media.md](person-call-settings-media.md) — per-person voicemail, caller ID, privacy, barge-in, call recording, intercept; not voicemail groups or Contact Center recording.
- [person-call-settings-permissions.md](person-call-settings-permissions.md) — incoming/outgoing permissions, feature access, executive/assistant pairing; not location dial plans.
- [person-call-settings-behavior.md](person-call-settings-behavior.md) — calling behavior, apps, shared lines, hoteling, receptionist, phone number add/remove/reassign, hot-desking members, emergency callback number; not device line keys.
- [self-service-call-settings.md](self-service-call-settings.md) — the `/people/me/` settings a user changes with their own token; not the admin path to the same settings.
- [location-calling-core.md](location-calling-core.md) — enabling a location for calling, internal dialing, voicemail policies, voice portal; not user settings.
- [location-calling-media.md](location-calling-media.md) — announcements, playlists, schedules, access codes; not Contact Center audio files.
- [location-recording-advanced.md](location-recording-advanced.md) — org and location call recording, caller reputation, conference, supervisor, operating modes; not per-person recording.
- [call-routing.md](call-routing.md) — Calling dial plans, trunks, route groups and lists, translation patterns, PSTN; not Contact Center dial plans.
- [call-control.md](call-control.md) — real-time call control (dial, answer, hold, transfer, park, record) with a user-level token; not configuration.
- [webhooks-events.md](webhooks-events.md) — webhooks: create and manage them, telephony and messaging event types and payloads; not Webex Connect webhook triggers or Contact Center subscriptions.
- [reporting-analytics.md](reporting-analytics.md) — Calling call records (CDR), report templates, call quality, queue and auto attendant statistics; not Contact Center analytics.
- [virtual-lines.md](virtual-lines.md) — virtual lines and virtual extensions and their settings; not people or workspaces.
- [emergency-services.md](emergency-services.md) — E911: emergency addresses, callback numbers, location requirements; not general location setup.

## Devices

- [devices-core.md](devices-core.md) — device create, activate, configure, telephony device settings; not DECT or RoomOS configuration.
- [devices-dect.md](devices-dect.md) — DECT networks, base stations, handsets, DECT hot desking; not desk phones.
- [devices-workspaces.md](devices-workspaces.md) — workspaces, workspace settings and locations; not Contact Center "workspaces" (contact-center-journey.md).
- [devices-platform.md](devices-platform.md) — RoomOS and PhoneOS device configurations, workspace personalization, xAPI; 9800-series phones run PhoneOS, not RoomOS.

## Admin and identity

- [authentication.md](authentication.md) — tokens, scopes, OAuth flows, service apps, partner multi-org tokens; not Contact Center runtime scopes for a custom desktop (contact-center-agent-sdk.md).
- [admin-org-management.md](admin-org-management.md) — organizations, org settings, contacts, roles, domains; not Contact Center tenant settings.
- [admin-identity-scim.md](admin-identity-scim.md) — SCIM users and groups, the People and Groups APIs, identity org settings; not bulk user provisioning for Calling (provisioning.md).
- [admin-licensing.md](admin-licensing.md) — license inventory, assignment, usage audits, reclamation; not call records.
- [admin-audit-security.md](admin-audit-security.md) — admin audit events, security audit, compliance events; not org health checks.
- [admin-hybrid.md](admin-hybrid.md) — hybrid clusters and connectors, analytics, meeting quality; the playbook does not route hybrid clusters or connectors.
- [admin-partner.md](admin-partner.md) — partner admins, tags and partner reports; the playbook works one customer org at a time.
- [admin-apps-data.md](admin-apps-data.md) — service apps, authorizations, activation emails, data sources, recordings, resource groups; not Contact Center data sources.

## Messaging

- [messaging-spaces.md](messaging-spaces.md) — spaces, messages, memberships, teams, ECM, HDS; not Contact Center teams.
- [messaging-bots.md](messaging-bots.md) — bots, adaptive cards, room tabs, cross-domain recipes; not Webex Connect flows.

## Meetings

- [meetings-core.md](meetings-core.md) — meeting create/schedule/manage, templates, controls, registrants, interpreters, breakouts, surveys; not meeting content.
- [meetings-content.md](meetings-content.md) — transcripts, captions, chats, summaries, meeting messages; not call recordings.
- [meetings-settings.md](meetings-settings.md) — preferences, session types, tracking codes, site settings, polls, Q&A, reports; not org settings.
- [meetings-infrastructure.md](meetings-infrastructure.md) — Video Mesh clusters and nodes, participants, invitees; not hybrid connectors.

## Contact Center — provisioning, routing, reporting

- [contact-center-core.md](contact-center-core.md) — Contact Center agents, queues, teams, skills, desktop profiles and layouts, sites, business hours, configuration; not Calling call queues.
- [contact-center-routing.md](contact-center-routing.md) — Contact Center dial plans, dial numbers, outdial ANI, callbacks, campaigns, flows and the Flow Store command groups, audio files, data sources, channels; not Calling dial plans.
- [contact-center-analytics.md](contact-center-analytics.md) — Contact Center AI, monitoring, subscriptions, tasks, search; not Calling call records.
- [contact-center-journey.md](contact-center-journey.md) — the `cc-journey` commands for the Journey Data Service (identities, profiles, events); for CJDS platform values see cjds.md.
- [contact-center-agent-sdk.md](contact-center-agent-sdk.md) — the `@webex/contact-center` JavaScript SDK for a custom agent desktop (a human agent's browser softphone); not AI agents and not Cisco's own Agent Desktop layout.
- [wxcc-platform.md](wxcc-platform.md) — Control Hub entities, global variables, CCAI config, Analyzer, tenant setup, the Create Task API; not the REST command reference (contact-center-core.md).
- [wxcc-provisioning-api.md](wxcc-provisioning-api.md) — creating teams, queues, business hours and entry points through the Provisioning API for a programmatic flow build; not Flow Store flow operations.

## Flow Designer

- [flow-designer-essentials.md](flow-designer-essentials.md) — the activities used in almost every voice flow (Play Message, Play Music, Set Variable, Queue Contact, Disconnect, variable types, output variables, global events); not situational activities.
- [flow-designer-activities/](flow-designer-activities/_index.md) — every other activity, one file each (transfers, callbacks, HTTP, BRE Request, Functions, Virtual Agent); start at `_index.md`.
- [flow-designer-patterns.md](flow-designer-patterns.md) — versioning, subflows, dynamic variables, scripted-agent fulfillment, connector auth, TTS, expressions, debugging, CJDS node, management API; not single-activity settings.
- [flow-designer-flowir.md](flow-designer-flowir.md) — FlowIR, the JSON for building flows through the API: endpoints, activity properties, the validate → create workflow, gotchas; not the Flow Designer UI export JSON, which is never generated.
- [flow-blueprints.md](flow-blueprints.md) — common voice flow patterns with their activities and connections tables; not finished flows.
- [custom-functions.md](custom-functions.md) — the Custom Functions API (`handle` contract, fields, runtimes, tags, lifecycle) and the `cc-functions` commands; for the Function activity in a flow see flow-designer-activities/functions-activity.md.
- [flow-designer.md](flow-designer.md) — a pointer page left after the Flow Designer reference was split; it links to the three files above.

## AI Agent Studio

- [ai-agent-studio.md](ai-agent-studio.md) — autonomous AI agents: goal, instructions, actions, slots, Custom Data, Custom Event Fulfillment, deployment; not scripted agents.
- [ai-agent-studio-scripted.md](ai-agent-studio-scripted.md) — scripted AI agents: intents, entities, responses, fulfillment, AI engines, context flow; not autonomous agents.
- [ai-agent-studio-import-json.md](ai-agent-studio-import-json.md) — the import/export JSON that creates an autonomous agent in one step (`bot_type`, `configuration`, `tools`); not scripted agents.

## Webex Connect and digital channels

- [webex-connect.md](webex-connect.md) — Connect flow structure for AI agent actions, node inventory, variable syntax, Flow Outcomes, custom connectors; not Flow Designer.
- [webex-connect-advanced.md](webex-connect-advanced.md) — Branch, Evaluate, voice nodes (Call User, Call Patch), channel nodes; not the core action-flow pattern.
- [digital-inbound.md](digital-inbound.md) — how SMS, WhatsApp, Live Chat, email, Messenger and Apple Messages reach an AI agent through Connect, and escalation to a person; not outbound notifications.
- [connect-sms.md](connect-sms.md) — SMS and MMS nodes, sender IDs, outputs, 10DLC; not other channels.
- [connect-email.md](connect-email.md) — the Email node, sending routes, attachments, tracking; not other channels.
- [connect-rcs.md](connect-rcs.md) — RCS capability check and message nodes with SMS fallback; not Apple Messages.
- [connect-apple-messages.md](connect-apple-messages.md) — Apple Messages for Business, its customer-initiated session rule and message types; not RCS.
- [connect-whatsapp.md](connect-whatsapp.md) — the WhatsApp node, message types, templates, the 24-hour session window; not SMS.
- [connect-multi-channel.md](connect-multi-channel.md) — routing one notification across channels with preference lookup and fallback; not a single channel's settings.
- [connect-auth.md](connect-auth.md) — how an outside caller authenticates to Connect: service keys, JWT, HMAC, IP allowlists, rotation; not Webex API tokens (authentication.md).
- [connect-response-codes.md](connect-response-codes.md) — the one owner of Connect response codes, inbound webhook and per-channel; the two numbering spaces collide, so never merge them.

## Data sources (BRE, databases, CJDS)

- [bre.md](bre.md) — the Business Rules Engine: DataSync, rules, data tables, sizing limits, the BRE Request activity; not an external database.
- [db-integration.md](db-integration.md) — choosing and calling an external database (Supabase and others), HTTP patterns, the research protocol for an undocumented backend; not BRE.
- [cjds.md](cjds.md) — the Customer Journey Data Service: domains, scopes, event schema, identity types, REST endpoints, Connect node outcomes, RSQL; for the `cc-journey` commands see contact-center-journey.md.

## See Also

- [../playbooks/INDEX.md](../playbooks/INDEX.md) — the step-by-step guides, each with the reference doc that owns its values.
- [../templates/INDEX.md](../templates/INDEX.md) — design-doc and output templates the skills fill in.
- [../examples/INDEX.md](../examples/INDEX.md) — working FlowIR flows, a Custom Function and walkthroughs from real builds.
- [flow-designer-activities/_index.md](flow-designer-activities/_index.md) — the activity-by-activity index for Flow Designer.
