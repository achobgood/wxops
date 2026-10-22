# Templates — index

One line per template in this folder: what it produces, which skill or agent fills it in, and what it is not. A template fixes the shape of an output; the platform values that go into it come from the reference docs ([../reference/INDEX.md](../reference/INDEX.md)).

## Webex Calling builds

- [deployment-plan.md](deployment-plan.md) — the plan the wxops agent writes before it changes anything; not a design doc for a flow or an AI agent.
- [execution-report.md](execution-report.md) — the report the wxops agent writes after it runs a plan; not a plan.

## Flow Designer and AI agents

- [flow-designer-design-doc.md](flow-designer-design-doc.md) — the design doc for a Flow Designer voice flow, written by the design-flow skill and read by build-flow-designer, build-flow-programmatic and build-spec-diagram; not for AI agents.
- [ai-agent-design-doc.md](ai-agent-design-doc.md) — the design doc for an AI agent build, autonomous or scripted (Section 4d is the scripted plan), read by the build and configure skills; not for voice flows.
- [ai-agent-studio-import-template.json](ai-agent-studio-import-template.json) — the verified skeleton of the AI Agent Studio import JSON for an autonomous agent, filled by the configure-ai-agent skill; its fields are owned by ../reference/ai-agent-studio-import-json.md. Not for scripted agents.
- [design-doc.md](design-doc.md) — **deprecated**: replaced by ai-agent-design-doc.md and flow-designer-design-doc.md, as its own banner says; do not start a new design from it.

## Webex Connect outputs

- [action-config.md](action-config.md) — the 10-step output of the build-action skill: the AI Agent Studio action plus the Connect flow behind it; not a notification.
- [notification-config.md](notification-config.md) — the output of the build-notification skill: an outbound multi-channel notification flow; not a voice call.
- [outbound-flow-config.md](outbound-flow-config.md) — the output of the build-outbound-flow skill: a webhook-triggered outbound voice call with text-to-speech; not a messaging notification.

## See Also

- [../playbooks/INDEX.md](../playbooks/INDEX.md) — the step-by-step guides these builds follow.
- [../examples/INDEX.md](../examples/INDEX.md) — finished examples from real builds.
