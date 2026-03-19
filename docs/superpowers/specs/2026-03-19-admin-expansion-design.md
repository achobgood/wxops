# Playbook Expansion: Admin & Identity APIs — Design Spec

**Date:** 2026-03-19
**Status:** Review-complete (16 issues fixed)
**Author:** Adam Hobgood + Claude
**Depends on:** wxcli admin CLI groups (35 groups, ~130 commands, all registered — some have generator naming artifacts)

## Problem

The Webex Calling playbook (reference docs, skills, builder agent) covers only Webex Calling APIs. The wxcli CLI now covers 35 admin command groups (~130 commands) spanning org management, SCIM identity, audit/security, hybrid infrastructure, partner operations, and data management. These commands are generated and registered but have:

- No reference documentation
- No guided workflow skills
- No builder agent awareness

Users who clone this repo and try to manage org-level operations (license audits, SCIM sync, audit log export, domain verification) get no guidance. The playbook is public-facing and must work for anyone on the platform — calling admins, IT/security teams, partner MSPs, and compliance officers.

## Goals

- Reference docs covering all 35 admin CLI groups with CLI examples, scope requirements, and raw HTTP fallback
- 3 guided workflow skills for the highest-value admin operations
- Builder agent expansion to recognize and route admin objectives
- CLAUDE.md file map updated with new artifacts
- Cross-reference signposts between admin and calling docs where scopes overlap

## Non-Goals

- Modifying any CLI code or generated command files
- Modifying existing calling reference docs or skills (cross-reference signposts only)
- Live-testing admin CLI commands (that's a separate session)
- Covering the device or messaging API specs (separate expansion)

## Constraints

- Do NOT hand-edit generated CLI files
- Follow existing doc/skill style patterns exactly
- Mark unverified info with `<!-- NEEDS VERIFICATION -->`
- Every CLI command referenced must be verified via `wxcli <group> <command> --help`
- Skills must be self-contained and runnable standalone (not just as agent sub-workflows)

---

## Discovery Summary

### All 35 Admin CLI Groups

| Category | CLI Group | Commands | R/W | Control Hub Area |
|----------|-----------|----------|-----|-----------------|
| **Org Management** | `organizations` | 3 (list, show, delete) | R/W | Management > Organization |
| | `org-settings` | 2 (show, create) | R/W | Management > Organization Settings |
| | `org-contacts` | 7 (CRUD + bulk) | R/W | Management > Organization Contacts |
| | `roles` | 2 (list, show) | R | Management > Roles |
| | `domains` | 5 (verify, claim, unverify, unclaim, get-token) | R/W | Management > Domains |
| **Identity/SCIM** | `scim-users` | 7 (CRUD + search + /me) | R/W | Users > SCIM/Directory Sync |
| | `scim-groups` | 6 (CRUD + search) | R/W | Users > SCIM/Directory Sync |
| | `scim-schemas` | 3 (group/user/by-ID) | R | SCIM 2.0 schema introspection |
| | `scim-bulk` | 1 (bulk create) | W | Bulk SCIM provisioning |
| | `identity-org` | 3 (show, update, generate-otp) | R/W | Management > Identity Settings |
| **User/Group Mgmt** | `groups` | 6 (CRUD + list-members) | R/W | Users > Groups |
| | `authorizations` | 4 (list, delete x2, show) | R/W | Management > Apps |
| | `service-apps` | 1 (create token) | W | Management > Service Apps |
| | `activation-email` | 3 (create job, status, errors) | R/W | Users > Activation |
| | `archive-users` | 1 (show) | R | Users > Archive |
| | `guest-management` | 2 (create, list count) | R/W | Users > Guests |
| **Audit/Security** | `audit-events` | 2 (list events, list categories) | R | Troubleshooting > Audit Logs |
| | `security-audit` | 1 (list) | R | Troubleshooting > Security Audit |
| | `events` | 2 (list, show) | R | Compliance Events |
| **Hybrid/Infra** | `hybrid-clusters` | 2 (list, show) | R | Services > Hybrid |
| | `hybrid-connectors` | 2 (list, show) | R | Services > Hybrid |
| | `live-monitoring` | 1 (create — actually a POST read) | R | Analytics > Live Monitoring |
| | `analytics` | 3 (messaging, devices, meetings) | R | Analytics > Historical |
| | `meeting-qualities` | 1 (list) | R | Troubleshooting > Meeting Quality |
| **Licensing** | `licenses-api` | 3 (list, show, update) | R/W | Management > Licenses |
| **Partner/Admin** | `partner-admins` | 5 (list customers, list admins, assign, unassign, revoke) | R/W | Partner Hub |
| | `partner-tags` | 7 (customer/subscription tags) | R/W | Partner Hub |
| | `partner-reports` | 5 (list, create, show, delete reports + list templates) | R/W | Partner Hub > Reports |
| **Recordings/Reports** | `admin-recordings` | 12 (CRUD, admin list, recycle bin, sharing, group) | R/W | Recordings |
| | `report-templates` | 1 (show) | R | Reports |
| **Data/Resources** | `data-sources` | 7 (CRUD + schemas) | R/W | Data & Compliance |
| | `classifications` | 1 (list) | R | Data & Compliance |
| | `resource-groups` | 2 (list, show) | R | Management > Resource Groups |
| | `resource-group-memberships` | 4 (list, list-v2, show, update) | R/W | Management > Resource Groups |
| **People** | `people` | 6 (CRUD + /me) | R/W | Users > People |
| **Workspace Locations** | *(in admin spec but covered by calling docs)* | — | — | Workspaces |

### Scope Requirements by Group

| CLI Group(s) | Required Scopes |
|---|---|
| `scim-users`, `scim-groups`, `scim-bulk` | `identity:people_rw` (write), `identity:people_read` (read) |
| `scim-schemas` | `identity:people_rw` or `identity:organizations_rw` |
| `identity-org` | `identity:organizations_rw` (write), `identity:organizations_read` (read) |
| `domains` | `identity:organizations_rw` |
| `identity-org generate-otp` | `Identity:one_time_password`, `Identity:Config` |
| `security-audit` | `audit:events_read` |
| `hybrid-clusters` | `spark-admin:hybrid_clusters_read` |
| `hybrid-connectors` | `spark-admin:hybrid_connectors_read` |
| `live-monitoring`, `analytics` | `analytics:read_all` |
| `service-apps` | `spark:applications_token` |
| `activation-email` | `spark-admin:people_write` (create), `spark-admin:people_read` (status/errors) |
| `archive-users` | `identity:people_read` or `identity:people_rw` |
| `data-sources` | `spark-admin:datasource_read` (read), `spark-admin:datasource_write` (write) |
| `org-settings` | `identity:organizations_read` (read), `identity:organizations_rw` (write) |
| `partner-reports` | `spark-admin:reports_read` (read), `spark-admin:reports_write` (write) |
| `organizations`, `roles`, `licenses-api`, `groups`, `authorizations`, `events`, `org-contacts`, `classifications`, `resource-groups`, `admin-recordings`, `report-templates`, `meeting-qualities`, `guest-management`, `partner-admins`, `partner-tags`, `people` | Standard admin token (scopes not explicitly documented in OpenAPI spec) |

---

## Deliverables

### 1. Reference Docs (7 files)

Each doc follows the existing pattern: title, coverage summary, required scopes table, per-group API surface tables with CLI examples, raw HTTP fallback, common patterns/recipes, gotchas section.

**Required in every doc's gotchas section:** A scope troubleshooting sub-section mapping common 401/403 errors to the specific admin scopes required, with guidance on checking scopes via `wxcli whoami`. Admin scopes are significantly more varied than calling scopes (e.g., `identity:people_rw`, `audit:events_read`, `Identity:one_time_password` with unusual casing) and users will hit scope errors frequently.

**Cross-reference strategy:** Standalone docs per domain. Where admin and calling scopes touch, add a one-line signpost: `> For per-user call recordings, see [reporting-analytics.md](reporting-analytics.md).` No explanatory paragraphs about what's out of scope.

#### Doc 1: `docs/reference/admin-org-management.md`

**Title:** Admin: Organization Management
**Groups covered (5 groups, 19 commands):**
- `organizations` (3) — list orgs, show details, delete org
- `org-settings` (2) — show/update org settings (identity settings like SSO, MFA)
- `org-contacts` (7) — CRUD + bulk import/delete of org directory contacts
- `roles` (2) — list/show admin roles
- `domains` (5) — domain verification, claim, unclaim workflow

**Key recipes to document:**
- Domain verification workflow: get token → add DNS TXT record → verify → claim
- Org contacts bulk import from CSV
- List all admin roles and their permissions
- View/update org identity settings

**Gotchas to document:**
- `org-settings create` is a POST that functions as "Create or Update" — same naming pattern as `live-monitoring create`. The generator maps POST → `create` even when the operation is an upsert.

**Cross-reference signposts:**
- `organizations` vs `locations` (calling): "For Webex Calling locations within an org, see [provisioning.md](provisioning.md)."

#### Doc 2: `docs/reference/admin-identity-scim.md`

**Title:** Admin: Identity & SCIM
**Groups covered (7 groups, 32 commands):**
- `scim-users` (7) — SCIM 2.0 user CRUD + search + /me
- `scim-groups` (6) — SCIM 2.0 group CRUD + search
- `scim-schemas` (3) — schema introspection (group, user, by ID)
- `scim-bulk` (1) — bulk user/group operations
- `identity-org` (3) — org identity settings, OTP generation
- `groups` (6) — Webex groups CRUD + list members
- `people` (6) — People API CRUD + /me

**Key concepts to document:**
- SCIM 2.0 protocol basics (for users who've never used SCIM)
- PUT (full replace) vs PATCH (partial update) — this is where users get burned
- SCIM filter syntax with examples (`filter=userName eq "user@example.com"`)
- `scim-users` vs `people` — when to use which (SCIM for IdP sync, People for Webex-native management)
- `scim-groups` vs `groups` — same distinction

**Key recipes to document:**
- Provision users from Azure AD/Okta via SCIM bulk
- Search for users by email, displayName, department
- Bulk deactivate stale users
- Group membership management
- OTP generation for password reset

**Cross-reference signposts:**
- `people` vs `users` (calling): "For Webex Calling user provisioning (licenses, extensions, locations), see [provisioning.md](provisioning.md)."
- "For calling-specific person settings, see [person-call-settings-*.md](person-call-settings-handling.md)."

#### Doc 3: `docs/reference/admin-licensing.md`

**Title:** Admin: Licensing
**Groups covered (1 group, 3 commands + cross-ref to calling `licenses`):**
- `licenses-api` (3) — list all org licenses, show details, assign licenses to users (PATCH)

**Key concepts to document:**
- License types (Calling Professional/Basic, Meetings, Messaging, Contact Center, Common Area, etc.)
- `licenses-api list` (admin spec, full org) vs `licenses list` (calling spec, calling-focused)
- The PATCH `/licenses/users` pattern for bulk assignment (requires `--json-body`)

**Key recipes to document:**
- Audit license usage: list all licenses, show consumed vs total
- Find users without a specific license
- Bulk license assignment workflow (list → identify → PATCH)
- Reclaim unused licenses (find inactive users → remove license)

**Cross-reference signposts:**
- "For calling license assignment during user provisioning, see [provisioning.md](provisioning.md) and the `provision-calling` skill."
- In `docs/reference/provisioning.md` Licenses section, add signpost: "For full org-wide license auditing, assignment, and reclamation, see [admin-licensing.md](admin-licensing.md)."
- In `provision-calling` skill, add signpost: "For bulk license assignment and auditing, see the `manage-licensing` skill and `licenses-api` group (which now provides CLI-native license assignment via `licenses-api update`)."

#### Doc 4: `docs/reference/admin-audit-security.md`

**Title:** Admin: Audit & Security
**Groups covered (3 groups, 5 commands):**
- `audit-events` (2) — list admin audit events, list event categories
- `security-audit` (1) — list security audit events
- `events` (2) — list/show compliance events

**Key concepts to document:**
- Three different event APIs — explain when to use each:
  - Admin Audit Events: who changed what in Control Hub (admin actions)
  - Security Audit Events: login failures, suspicious activity, security policy changes
  - Events: general Webex platform events (messages created/deleted, calls, meetings) for compliance
- Event categories (from `list-event-categories`) as a filtering aid

**Key recipes to document:**
- Pull audit trail for a specific admin over a date range
- Export security events for external SIEM ingestion
- Compliance event review for a specific user
- Filter audit events by category

**Cross-reference signposts:**
- "For Webex Calling CDR (call detail records), see [reporting-analytics.md](reporting-analytics.md)."

#### Doc 5: `docs/reference/admin-hybrid.md`

**Title:** Admin: Hybrid Infrastructure & Analytics
**Groups covered (5 groups, 9 commands):**
- `hybrid-clusters` (2) — list/show hybrid clusters
- `hybrid-connectors` (2) — list/show hybrid connectors
- `live-monitoring` (1) — live meeting metrics by country (POST that reads)
- `analytics` (3) — historical messaging, room devices, meetings analytics
- `meeting-qualities` (1) — meeting quality data by meeting ID

**Key recipes to document:**
- Monitor hybrid connector health across the org
- Pull historical analytics for messaging/meetings/devices
- Investigate meeting quality issues (jitter, latency, packet loss)

**Gotchas to document:**
- `live-monitoring create` is a read operation despite being a POST (CLI uses `create` because the generator maps POST → create)
- All groups are read-only — no write operations
- Meeting quality requires a specific `meetingId`
- **CONFIRMED BUG:** Analytics endpoints have a double `/v1/v1/` path bug in the generated code. All three commands (`show`, `show-daily-totals`, `show-aggregates`) will fail at runtime. Must be fixed via `field_overrides.yaml` and regeneration before these commands are useful. Document as a known issue.

#### Doc 6: `docs/reference/admin-partner.md`

**Title:** Admin: Partner Operations
**Groups covered (3 groups, 17 commands):**
- `partner-admins` (5) — list customers, list admins, assign, unassign, revoke all roles
- `partner-tags` (7) — customer tags, subscription tags, org-tag queries
- `partner-reports` (5) — list/create/show/delete partner reports, list templates

**Key concepts to document:**
- Partner/VAR/MSP context: these commands only work with partner-level tokens
- Customer org management from the partner perspective
- Tag-based org organization for multi-tenant management

**Key recipes to document:**
- List all customer orgs managed by a partner admin
- Assign a partner admin to a customer org
- Tag customers by region/tier/contract type
- Generate partner-level reports across customer orgs

**Audience note:** This doc serves a niche audience (partner/VAR organizations). Most single-org admins will never use these commands. The doc should state this upfront.

#### Doc 7: `docs/reference/admin-apps-data.md`

**Title:** Admin: Apps, Data & Resources
**Groups covered (11 groups, 38 commands):**
- `service-apps` (1) — create service app access token
- `authorizations` (4) — list/delete authorizations, check token expiry
- `activation-email` (3) — bulk activation email resend job
- `archive-users` (1) — get archived user info
- `guest-management` (2) — create guest, get guest count
- `data-sources` (7) — register/list/update/delete data sources and schemas
- `classifications` (1) — list content classifications
- `resource-groups` (2) — list/show resource groups
- `resource-group-memberships` (4) — list/show/update resource group memberships
- `admin-recordings` (12) — recordings CRUD, admin list, recycle bin, sharing, group recordings
- `report-templates` (1) — list report templates

**Rationale for grouping:** These are the "everything else" admin operations that don't fit neatly into org management, identity, audit, hybrid, or partner categories. They're grouped by proximity to platform administration rather than by workflow affinity. Note: this is the largest admin doc (38 commands) — the sub-section structure keeps it navigable.

**Sub-sections within the doc:**
1. Service Apps & Authorizations (5 commands) — token lifecycle, OAuth grant management
2. User Lifecycle (6 commands) — activation emails, archive, guests
3. Recordings (12 commands) — admin recording management, recycle bin, sharing, group recordings
4. Data & Compliance (14 commands) — data sources, classifications, resource groups, report templates

**Cross-reference signposts:**
- `admin-recordings` vs `recordings` (calling spec): "Both `admin-recordings` and `recordings` operate on the Webex recordings API. Use `admin-recordings` for org-wide admin/compliance operations (admin list, purge, recycle bin). Use `recordings` for user-scoped recording access. See [reporting-analytics.md](reporting-analytics.md)."
- `report-templates` vs calling reports: "For calling-specific report creation and download, see [reporting-analytics.md](reporting-analytics.md)."

---

### 2. Skills (3 files)

Each skill follows the existing pattern: frontmatter (name, description, allowed-tools, argument-hint), step-by-step workflow (load references → verify auth → identify need → check prerequisites → build plan → execute → verify → report), decision matrix, critical rules, error handling, scope reference.

#### Skill 1: `manage-identity`

**File:** `.claude/skills/manage-identity/SKILL.md`
**Frontmatter description:** Manage Webex identity and directory: SCIM user/group sync, bulk provisioning, domain verification, org contacts, group membership, and directory cleanup. Guides from prerequisites through execution and verification.

**Scope:** 7 CLI groups (scim-users, scim-groups, scim-bulk, scim-schemas, groups, org-contacts, domains)

**Reference docs loaded:** `admin-identity-scim.md`, `admin-org-management.md` (for domains and org-contacts), `authentication.md`

**Decision matrix (what the skill asks the user):**

| Need | Operation | CLI Group |
|------|-----------|-----------|
| Sync users from IdP (Azure AD, Okta) | SCIM bulk import | scim-bulk, scim-users |
| Search/find users in directory | SCIM user search | scim-users |
| Create/update/delete individual users | SCIM user CRUD | scim-users |
| Manage groups and membership | Group CRUD | scim-groups or groups |
| Import org contacts (directory listing) | Bulk contact import | org-contacts |
| Verify/claim a domain before sync | Domain verification | domains |
| Clean up stale/inactive users | Directory cleanup | scim-users, archive-users |
| Check SCIM schema for field mapping | Schema introspection | scim-schemas |

**Domain verification as prerequisite:** When the user's objective involves SCIM sync from an external IdP, the skill checks domain verification status first: "Before syncing users, your domain must be verified and claimed. Let me check..."

**Critical rules:**
1. SCIM PUT replaces the entire resource — always GET first to preserve fields you're not changing
2. SCIM PATCH is partial update — safer for targeted changes
3. `scim-users` requires `--org-id` on every command <!-- NEEDS VERIFICATION -->
4. Bulk operations can partially fail — always check the response for per-item status
5. `/me` endpoint requires a user-level token, not admin token
6. Domain verification requires DNS TXT record — the skill cannot verify DNS, only check the API status
7. Org contacts bulk import/delete are async jobs — poll for completion

#### Skill 2: `audit-compliance`

**File:** `.claude/skills/audit-compliance/SKILL.md`
**Frontmatter description:** Pull and analyze Webex audit logs, security events, and compliance data. Covers admin audit trail, security audit events, authorization review, and service app credential management. Guides from query design through export.

**Scope:** 5 CLI groups (audit-events, security-audit, events, authorizations, service-apps)

**Reference docs loaded:** `admin-audit-security.md`, `admin-apps-data.md` (for authorizations/service-apps), `authentication.md`

**Decision matrix:**

| Need | Operation | CLI Group |
|------|-----------|-----------|
| Who changed what in Control Hub | Admin audit events | audit-events |
| Security incidents (failed logins, policy changes) | Security audit events | security-audit |
| Compliance review (messages, calls, meetings) | Platform events | events |
| Review OAuth grants and integrations | Authorization audit | authorizations |
| Create/rotate service app credentials | Service app token | service-apps |
| List available audit event categories | Category reference | audit-events |

**Service apps folded in:** Service app token creation and authorization review are related compliance workflows — "who has access to what" and "rotate credentials."

**Critical rules:**
1. `audit-events` and `security-audit` are different APIs with different scopes — don't confuse them
2. `security-audit` requires `audit:events_read` scope specifically
3. Date range filtering is essential — without it, you get the full event stream
4. Events API covers all platform events (not just calling) — filter by `resource` and `type`
5. `authorizations delete` revokes access — this is destructive, confirm before executing
6. Service app token creation returns a short-lived token — store it immediately

#### Skill 3: `manage-licensing`

**File:** `.claude/skills/manage-licensing/SKILL.md`
**Frontmatter description:** Audit, assign, and reclaim Webex licenses across the organization. Covers license inventory, usage analysis, bulk assignment, and license reclamation workflows.

**Scope:** 2 CLI groups (licenses-api, licenses from calling spec)

**Reference docs loaded:** `admin-licensing.md`, `authentication.md`

**Decision matrix:**

| Need | Operation | CLI Group |
|------|-----------|-----------|
| See all licenses and usage counts | License inventory | licenses-api |
| Get details for a specific license | License details | licenses-api |
| Assign licenses to users | Bulk assignment | licenses-api (PATCH with --json-body) |
| Find unused/unassigned licenses | Usage audit | licenses-api + people (cross-reference) |
| Reclaim licenses from inactive users | Reclamation workflow | licenses-api + people |
| Check calling-specific licenses | Calling license list | licenses (calling spec) |

**Multi-step workflow emphasis:** The value of this skill is the multi-step workflows, not the individual commands:
1. **License audit:** `licenses-api list` → parse consumed vs total → identify overused/underused
2. **Find unlicensed users:** `people list` → cross-reference with `licenses-api show` → identify gaps
3. **Bulk assign:** Build JSON payload → `licenses-api update --json-body '{...}'` → verify
4. **Reclaim:** `people list` → find inactive (last login > N days) → remove license → verify capacity restored

**Critical rules:**
1. `licenses-api update` uses PATCH semantics with `--json-body` — the payload format is specific
2. `licenses-api` (admin spec) shows all org licenses; `licenses` (calling spec) is calling-focused
3. License IDs are org-specific base64 strings — never hardcode
4. Removing a calling license from a user also removes their calling configuration (extension, forwarding, etc.) — this is destructive
5. License assignment may fail silently if the user already has the license — always verify after

---

### 3. Agent Updates

**File:** `.claude/agents/wxc-calling-builder.md`

#### 3a. Frontmatter `skills:` list

Add 3 new skills:
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, device-platform, call-control, reporting, wxc-calling-debug, manage-identity, audit-compliance, manage-licensing
```

#### 3b. INTERVIEW PHASE expansion

Add admin objectives to the Question 1 listener. Currently the agent listens for calling domains (provisioning, call features, person settings, etc.). Add:

```
- **Identity/directory**: SCIM sync, user import, group management, domain verification, directory cleanup
- **Audit/compliance**: audit logs, security events, compliance review, authorization management
- **Licensing**: license audit, usage reporting, license assignment, reclamation
- **Org management**: org settings, contacts, roles, domain management
- **Partner operations**: multi-tenant management, partner admin assignment, customer tagging
- **Hybrid monitoring**: hybrid connector health, analytics, meeting quality
- **Recordings/data**: recording management, recycle bin, data sources, resource groups, report templates
```

#### 3c. SKILL DISPATCH table

Add 3 rows to the dispatch table:

| Task Domain | Skill File | What It Provides |
|---|---|---|
| SCIM sync, directory, groups, contacts, domains | `.claude/skills/manage-identity/SKILL.md` | SCIM gotchas, bulk patterns, PUT vs PATCH, domain prereqs |
| Audit events, security, compliance, authorizations | `.claude/skills/audit-compliance/SKILL.md` | Event query patterns, date filtering, export recipes, auth review |
| License audit, reclaim, bulk assignment | `.claude/skills/manage-licensing/SKILL.md` | Usage analysis, reclaim workflow, multi-step assignment |

#### 3d. REFERENCE DOC LOADING section

Add new sections:

```
### Organization Management
docs/reference/admin-org-management.md

### Identity & SCIM
docs/reference/admin-identity-scim.md

### Licensing
docs/reference/admin-licensing.md

### Audit & Security
docs/reference/admin-audit-security.md

### Hybrid Infrastructure & Analytics
docs/reference/admin-hybrid.md

### Partner Operations
docs/reference/admin-partner.md

### Apps, Data & Resources
docs/reference/admin-apps-data.md
```

#### 3e. No-skill admin operations

For admin operations that don't have a dedicated skill, the builder agent handles them inline using reference docs:
- Org settings (show/update): reference `admin-org-management.md`, run `wxcli org-settings show/create` directly
- Hybrid monitoring: reference `admin-hybrid.md`, run `wxcli hybrid-clusters list` directly
- Partner operations: reference `admin-partner.md`, run partner commands directly
- Data/resource operations: reference `admin-apps-data.md`, run commands directly

**Inline handling criteria:** Handle inline when: (a) the operation is a single read-only command, (b) the group has fewer than 5 commands, or (c) there are no destructive operations involved. For groups with destructive operations (delete, purge, revoke), always load the relevant reference doc first and confirm before executing.

The agent should say: "This is a straightforward operation — I'll handle it directly using the CLI rather than loading a full workflow."

---

### 4. CLAUDE.md Updates

#### 4a. File Map — add to Agent & Skills table

```
| `.claude/skills/manage-identity/` | Skill: SCIM sync, directory, groups, contacts, domains |
| `.claude/skills/audit-compliance/` | Skill: audit events, security, compliance, authorizations |
| `.claude/skills/manage-licensing/` | Skill: license audit, assignment, reclamation |
```

#### 4b. File Map — add Reference Docs table for Admin APIs

```
### Reference Docs — Admin & Identity APIs

| Path | Purpose |
|------|---------|
| `docs/reference/admin-org-management.md` | Organizations, org settings, contacts, roles, domains |
| `docs/reference/admin-identity-scim.md` | SCIM users/groups, schemas, bulk ops, identity org, people, groups |
| `docs/reference/admin-licensing.md` | License inventory, assignment, usage auditing |
| `docs/reference/admin-audit-security.md` | Admin audit events, security audit, compliance events |
| `docs/reference/admin-hybrid.md` | Hybrid clusters/connectors, analytics, meeting quality |
| `docs/reference/admin-partner.md` | Partner admins, tags, partner reports |
| `docs/reference/admin-apps-data.md` | Service apps, authorizations, activation emails, data sources, recordings, resource groups |
```

#### 4c. Agent description update

Update the builder agent description in CLAUDE.md Quick Start to reflect that it now handles both calling and admin operations:

```
Use `/agents` and select **wxc-calling-builder** to start building. The agent walks you through
authentication, interviews you about what you want to build, designs a deployment plan, executes
via `wxcli` commands, and verifies the results. Covers Webex Calling, admin/org management,
identity/SCIM, licensing, audit/compliance, and partner operations.
```

---

## Implementation Order

Each deliverable is independent and can be parallelized within waves.

### Wave 1: Reference Docs (5 agents, then 2)

Write all 7 reference docs. Each agent gets:
- The relevant CLI group help output (already captured in discovery)
- OpenAPI spec scope data (already extracted)
- An existing reference doc as style template
- The doc outline from this spec (above)

Per swarm sizing rule: launch first 5 docs, then remaining 2 after the first wave completes.

### Wave 2: Skills (3 parallel agents)

Write all 3 skills. Each agent gets:
- An existing skill as style template (provision-calling for manage-identity and manage-licensing; reporting for audit-compliance)
- The relevant reference doc(s) written in Wave 1 (read them for accurate CLI commands)
- The skill outline from this spec (above)

### Wave 3: Agent & CLAUDE.md Updates (1 agent)

Single agent updates:
1. Builder agent frontmatter, interview phase, dispatch table, reference doc loading
2. CLAUDE.md file map and description

This must run after Wave 2 because it references the skill files.

### Wave 4: Verification

Single agent or manual verification:
- Run `wxcli <group> --help` for every CLI command referenced in the new docs/skills
- Verify all cross-reference signpost links point to real files
- Verify the builder agent's skill dispatch table has correct file paths

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Scope data from OpenAPI spec is incomplete (many groups have no explicit scopes) | Mark with `<!-- NEEDS VERIFICATION -->`, note "standard admin token" as fallback |
| Admin CLI commands not yet live-tested | Docs describe CLI help output, not verified API behavior. State this clearly. |
| `live-monitoring create`, `org-settings create`, and other POST-as-upsert operations confuse users | Document the generator naming convention explicitly in gotchas |
| Analytics endpoints have confirmed `/v1/v1/` double-path bug — all 3 commands fail at runtime | Document as known issue in admin-hybrid.md. Fix requires `field_overrides.yaml` update + regeneration (separate task). |
| Partner commands require partner-level tokens most users won't have | State the audience limitation upfront in admin-partner.md |
| `admin-apps-data.md` is a grab-bag of unrelated groups | Use clear sub-sections within the doc; each sub-section is self-contained |
| `admin-recordings` has truncated description artifact (`Officer.` from "Compliance Officer") | Cosmetic issue in command description, not command name. Document if confusing. |
