## Last Agent Removed Event

<!-- ref-tag: fd-act-last-agent-removed-v1 -->

> **Partially verified — event-spec name known from real flows; Cisco help does not document it (searched 2026-07-12).**
>
> This event handler exists as a shape in the [Cloverhound WxCC Flow Builder Activity Library](https://github.com/Cloverhound/Webex-CC-Flow-Builder-Activity-Library). Its FlowIR `eventSpecificationName` is **`FCAsk(ContactLastAgentRemoved)`** [source: flow-designer-flowir.md § 6 "Available Event Specifications" — listed as used by real flows; the spec endpoint returns only 2 specs, so this name is not API-verified]. The official Cisco Flow Designer help article ([nhovcy4](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer), searched 2026-07-12) does **not** document this event by name — it documents only `AgentAccepted`, `AgentDisconnected`, `PhoneContactEnded`, and the `OnGlobalError` workflow. Firing semantics, output variables, and UI restrictions remain **not verified**.

### What We Know

- **Category:** Event (event handler on the Event Flows canvas)
- **Cloverhound shape dimensions:** 230×146 (same as other event shapes)
- **Likely purpose:** Fires when the last agent is removed from (or disconnects from) the interaction — for example, after a conference call where the last remaining agent hangs up, leaving only the caller. This may differ from `AgentDisconnected` (which fires when *any* agent disconnects) and `PhoneContactEnded` (which fires when the entire contact terminates).

### What Needs Verification

Before using this event in documentation or flow instructions, verify the following against the Cisco help docs or a live WxCC tenant:

- [ ] Exact event handler name in the Flow Designer UI (e.g., `LastAgentRemoved`, `LastAgentDisconnected`, or another variant)
- [ ] When exactly this event fires relative to `AgentDisconnected` and `PhoneContactEnded`
- [ ] Whether this event fires only in multi-agent scenarios (conference, consult transfer) or also for single-agent calls
- [ ] Output variables exposed by this event handler
- [ ] Which main flow activities must be present for this event to appear on the Event Flows canvas
- [ ] Restrictions on which activities can be used inside this event handler

---
