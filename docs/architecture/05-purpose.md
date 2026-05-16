# Purpose — wxcli

## Who Uses This and Why

### Primary audience: Technical Solutions Architects (TSAs) and partner engineers

The person this project is built for manages Webex Calling environments day to day — provisioning users, configuring call features, setting up routing, migrating customers off legacy CUCM clusters. They know the Webex admin portal, they've used Control Hub, and they're increasingly asked to do things at a speed and scale that clicking through a web UI can't deliver.

Specifically:

- **TSAs** supporting Webex Calling deployments and migrations. They need to stand up environments, configure features, verify state, and tear down lab setups repeatedly. The GUI workflow for this is 15 minutes per user; the CLI workflow is seconds.
- **Partner/VAR/MSP engineers** managing multiple customer orgs. They authenticate once with a partner token and operate across orgs without switching browser sessions. 668 commands auto-inject the target org — no extra flags.
- **Migration practitioners** moving customers from CUCM to Webex Calling. The 11-phase pipeline (discover → normalize → map → analyze → plan → execute) replaces weeks of manual mapping spreadsheets with an automated pipeline that preserves decision auditability.

### Secondary audience: anyone building on Webex APIs

The 46 reference docs and 9 OpenAPI specs are useful to any developer working with Webex APIs, regardless of whether they use the CLI or the Claude Code playbook. The reference docs capture 51 SDK/API gotchas that aren't documented in Cisco's official API reference — scope edge cases, undocumented 404s, license-gated endpoints, response shape inconsistencies.

### Not the audience

- **End users** (people who make and receive calls). This is an admin tool, not a client.
- **IT generalists** who manage Webex at the org level but don't touch calling configuration. Control Hub already serves them well.

---

## Success Criteria

### What "working well" looks like

1. **A TSA can stand up a full Webex Calling environment — locations, users, features, routing — in one Claude Code session.** The builder agent interviews them, designs a plan, executes it, and verifies the results. They don't need to know which API endpoints to call or which wxcli commands exist.

2. **A CUCM migration produces a customer-ready assessment report from a single `discover` command.** The pipeline extracts the CUCM environment, normalizes it, maps it to Webex equivalents, surfaces decisions that require human judgment, and generates an HTML report with complexity scores, inventory tables, and effort estimates — suitable for presenting to a customer.

3. **The playbook says "no" correctly.** When a user asks about a Webex Calling capability, the system answers from grounded reference docs, not from training data. If the answer isn't in the docs, it says so. This is more important than being helpful — wrong answers about Cisco product capabilities erode trust faster than "I don't know" does.

4. **Org health checks catch real problems.** The 18 automated checks surface actual security risks (unrestricted international dialing), operational issues (empty call queues), and hygiene problems (orphaned devices) — not false positives that train operators to ignore the report.

### How we know we're losing

- Users bypass the playbook and run raw wxcli commands because the guided workflow is too slow, too rigid, or asks too many questions.
- Migration reports require significant manual correction before they're customer-presentable.
- Skills encode stale command names or flags that have changed since the last generator run.
- The grounding rule gets violated — answers about Webex Calling capabilities come from training data, and the wrong answer reaches a customer.

---

## Out of Scope

### What this project explicitly does NOT do

1. **Runtime call processing.** wxcli configures Webex Calling; it does not participate in the call path. Real-time call control commands exist (via user-level OAuth) for demo/debug purposes, not for building production call-handling applications.

2. **Webex Calling product development.** This project consumes Cisco's APIs as a third-party tool. It doesn't modify the Webex Calling platform, contribute to its roadmap, or have access to internal APIs. If an API doesn't exist for a capability, that capability is out of scope.

3. **Contact Center deployment at scale.** The 48 CC command groups exist for completeness (generated from the CC OpenAPI spec) and basic provisioning. Full Contact Center deployments — flow design, routing strategies, workforce management — are a separate discipline with its own tooling. The `contact-center` skill covers resource CRUD, not solution architecture.

4. **Multi-tenant SaaS hosting.** wxcli is a local CLI tool. It runs on the operator's machine, authenticates with their token, and operates against their org. There is no server, no multi-user access control, no hosted deployment model.

5. **Replacing Control Hub.** The GUI is better for one-off visual tasks (reviewing a single user's settings, browsing device inventory). wxcli is better for bulk operations, automation, migration, and programmatic configuration. They're complementary, not competing.

### What should be pushed back on if requested

- "Can we add a web UI?" — No. The value is in the CLI + AI playbook combination. A web UI would duplicate Control Hub poorly.
- "Can we support non-Webex platforms?" — No. The tool is purpose-built for Webex Calling APIs. Abstracting over multiple UCaaS platforms would sacrifice the depth that makes it useful.
- "Can we automate ongoing monitoring?" — Not in scope for the CLI. Org health checks are point-in-time audits, not continuous monitoring. Webex has its own alerting infrastructure for that.
- "Can we embed this in a CI/CD pipeline for automated provisioning?" — The CLI commands could technically run in CI, but the playbook (Claude Code integration) is interactive by design. Headless automation should use the Webex APIs directly or build on the CLI commands without the AI layer.

---

## Relationship to Other Projects

wxcli is a standalone project. It is not part of a product suite, not a component in a larger platform, and has no code or architectural dependencies on other projects.

### Cisco's official tooling

- **Control Hub** is the web-based admin portal. wxcli operates against the same APIs that Control Hub uses, but from the terminal. They share the same underlying platform and the same authentication (OAuth tokens from developer.webex.com or admin accounts).
- **wxc_sdk** (Cisco's official Python SDK) was an early dependency that has been fully removed. wxcli uses raw HTTP via its own `WebexSession` client. The SDK's typed API methods cover a subset of the surface and lag behind API releases by weeks to months. Reference docs still describe wxc_sdk patterns for educational purposes.
- **wxcadm** (community admin library) is used selectively for XSI real-time events and capabilities that have no REST API equivalent. It's not a dependency in `pyproject.toml` — it's an optional tool the builder agent can invoke when needed.
- **Cisco's Postman collections** serve as a source of truth for understanding the API surface. The OpenAPI specs in `specs/` are the primary input to the code generator.

### Strategic position

wxcli occupies a specific niche: **programmatic Webex Calling administration for practitioners who need speed, repeatability, and auditability.** It's not competing with Cisco's GUI tooling (different UX paradigm), not competing with the SDK (different abstraction level), and not trying to be a general-purpose UCaaS management platform. The Claude Code playbook layer is what differentiates it from a bare CLI — it turns tribal knowledge about Webex Calling configuration into guided, grounded procedures.

---

## Constraints That Aren't Technical

### Intellectual property

This project is Apache 2.0 licensed open source, built by an independent practitioner, not by Cisco. It consumes public Webex APIs through officially documented OAuth scopes. It does not use internal Cisco APIs, proprietary Cisco code, or information obtained under NDA.

The OpenAPI specs in `specs/` are derived from Cisco's publicly available API documentation. The reference docs in `docs/reference/` were originally built from the publicly available wxc_sdk and wxcadm source code (both open source), then maintained and extended independently with wxcli-specific examples and gotchas.

The CUCM migration pipeline connects to customer CUCM clusters via AXL (Administrative XML Layer) — Cisco's supported programmatic interface for CUCM administration. No reverse engineering, screen scraping, or unsupported interfaces are involved.

### Customer-facing implications

Migration assessment reports and user notices generated by the pipeline are designed to be customer-presentable. This means:

- Reports must be accurate — wrong inventory counts or complexity scores damage the operator's credibility with their customer.
- Decision recommendations must be conservative — "accept approximation" is a safer default than "this will work perfectly" when mapping lossy CUCM-to-Webex translations.
- The grounding rule exists specifically because Cisco product information in LLM training data is unreliable. A migration report that cites a feature availability that doesn't actually exist for the customer's license tier creates real business risk.

### Partner enablement implications

Partner engineers using multi-org tokens manage production customer environments. Mistakes are not free:

- Cleanup/teardown operations are irreversible (deleted users lose call history, voicemail, device associations).
- The `--dry-run` flag on cleanup, the confirmation prompts, and the dependency-safe deletion ordering all exist because a partner running `cleanup --all` against the wrong org is a support escalation.
- The builder agent's blocking org confirmation step for partner tokens exists because "which org am I operating on?" is the single highest-consequence question in the workflow.

### Operational boundaries

wxcli operates within the permissions and rate limits of the Webex platform:

- API rate limits (~300 req/min typical) constrain migration execution speed. The async engine's concurrency and 429 retry logic work within these limits, not around them.
- Token validity (12 hours for personal access tokens) means long migrations may require re-authentication mid-execution. The pipeline's phase-based persistence (SQLite store) makes this a resume operation, not a restart.
- Scope requirements vary by API domain. A single token rarely has all scopes — operators need to understand which scopes their workflow requires. The README documents minimum scopes per domain.
