# Playbook Expansion: Admin & Identity APIs

## Context

The wxcli CLI now covers the `webex-admin.json` OpenAPI spec: 35 command groups, ~124 commands covering org management, identity/SCIM, audit/security, hybrid infrastructure, partner admin, and data management. The playbook (reference docs, skills, agent) currently covers only Webex Calling. This session expands coverage to the Admin domain.

**What exists today:**
- CLI commands are generated and registered (`wxcli <group> --help` works for all 35 groups)
- No reference docs exist for admin APIs
- No skills exist for admin workflows
- The builder agent (`wxc-calling-builder`) doesn't know about admin operations

**Your job:** Investigate the admin CLI surface, map it to Control Hub functionality and real-world use cases, then build the reference docs and skills to support it.

---

## Phase 1: Discovery (do this FIRST, before writing anything)

### 1a. Map every admin CLI group

Run `--help` on each of the 35 admin command groups to understand what they do. The groups are:

**Org Management:**
- `wxcli organizations --help`
- `wxcli org-settings --help`
- `wxcli org-contacts --help`
- `wxcli roles --help`
- `wxcli licenses-api --help`

**Identity/SCIM:**
- `wxcli scim-users --help`
- `wxcli scim-groups --help`
- `wxcli scim-schemas --help`
- `wxcli scim-bulk --help`
- `wxcli identity-org --help`

**User/Group Management:**
- `wxcli groups --help`
- `wxcli authorizations --help`
- `wxcli service-apps --help`
- `wxcli activation-email --help`
- `wxcli archive-users --help`
- `wxcli guest-management --help`

**Audit/Security:**
- `wxcli audit-events --help`
- `wxcli security-audit --help`
- `wxcli events --help`

**Hybrid/Infrastructure:**
- `wxcli hybrid-clusters --help`
- `wxcli hybrid-connectors --help`
- `wxcli live-monitoring --help`
- `wxcli analytics --help`
- `wxcli meeting-qualities --help`

**Partner/Admin:**
- `wxcli partner-admins --help`
- `wxcli partner-tags --help`

**Recordings/Reports:**
- `wxcli admin-recordings --help`
- `wxcli report-templates --help`

**Data/Resources:**
- `wxcli data-sources --help`
- `wxcli classifications --help`
- `wxcli resource-groups --help`
- `wxcli resource-group-memberships --help`
- `wxcli domains --help`

For each group, note: command count, read vs write operations, what Control Hub area it maps to.

### 1b. Identify Control Hub mappings

Map each group to the corresponding Control Hub UI area. This tells users "you can do what you'd normally do in Control Hub > X > Y, but programmatically." Categories:

| Control Hub Area | CLI Groups |
|------------------|------------|
| Management > Organization | organizations, org-settings, org-contacts |
| Management > Roles | roles |
| Management > Licenses | licenses-api |
| Users > User Management | (people already covered), activation-email, archive-users, guest-management |
| Users > Groups | groups |
| Users > SCIM/Directory Sync | scim-users, scim-groups, scim-schemas, scim-bulk, identity-org |
| Management > Apps > Service Apps | service-apps, authorizations |
| Troubleshooting > Audit Logs | audit-events, security-audit |
| Services > Hybrid | hybrid-clusters, hybrid-connectors |
| Analytics | analytics, meeting-qualities, live-monitoring |
| Partner Hub | partner-admins, partner-tags |
| Data & Compliance | data-sources, classifications, resource-groups, resource-group-memberships, domains |
| Recordings | admin-recordings |
| Reports | report-templates |

Verify and correct this mapping by checking what each group actually does.

### 1c. Identify use cases

For each cluster of related groups, identify 3-5 real-world use cases. Examples to investigate:

- **SCIM identity sync:** Automate user provisioning from Azure AD/Okta, bulk user creation, directory cleanup
- **Audit & compliance:** Pull audit logs for security reviews, monitor admin actions, compliance reporting
- **License management:** Audit license usage across org, reclaim unused licenses, license assignment automation
- **Hybrid management:** Monitor hybrid connector health, manage cluster configurations
- **Partner operations:** Multi-tenant management, partner-level reporting, wholesale provisioning
- **Service app management:** Create/manage service apps, rotate credentials, manage authorizations
- **Org settings:** Branding, security policies, domain management, classification labels

### 1d. Identify scope requirements

For each group, determine what OAuth scopes are needed. Run a few test commands with `--debug` to see what scopes the API expects. Common admin scopes:
- `spark-admin:organizations_read/write`
- `spark-admin:roles_read`
- `spark-admin:licenses_read`
- `spark-admin:people_read/write`
- `identity:placeonetimepassword_create`
- `audit:events_read`

---

## Phase 2: Reference Docs

Based on Phase 1 findings, create reference docs. Follow the pattern of existing calling reference docs (see `docs/reference/authentication.md` for style). Each doc should have:

- API surface overview with method signatures
- Required scopes
- CLI command mappings
- Common patterns and recipes
- Gotchas section
- Raw HTTP fallback patterns

Suggested doc structure (adjust based on what you find):

| File | Covers |
|------|--------|
| `docs/reference/admin-org-management.md` | Organizations, org settings, contacts, roles, domains |
| `docs/reference/admin-identity-scim.md` | SCIM users, groups, schemas, bulk operations, identity org |
| `docs/reference/admin-licensing.md` | Licenses API, license assignment, usage auditing |
| `docs/reference/admin-audit-security.md` | Audit events, security audit, compliance events |
| `docs/reference/admin-hybrid.md` | Hybrid clusters, connectors, monitoring |
| `docs/reference/admin-partner.md` | Partner admins, tags, wholesale management |
| `docs/reference/admin-apps-data.md` | Service apps, authorizations, data sources, classifications, resource groups |

---

## Phase 3: Skills

Create skills for the most actionable admin workflows. Not every CLI group needs its own skill — group related functionality.

Suggested skills (adjust based on Phase 1 findings):

| Skill | Covers |
|-------|--------|
| `manage-org` | Org settings, roles, domains, contacts, branding — "Configure your Webex org" |
| `manage-identity` | SCIM provisioning, directory sync, bulk user operations, guest management — "Sync users from your IdP" |
| `audit-compliance` | Audit events, security audit, compliance reporting — "Pull audit logs and security reports" |

Each skill should follow the same structure as the calling skills (frontmatter, decision matrix, prerequisites, CLI commands, critical rules, verification).

---

## Phase 4: Agent & CLAUDE.md Updates

1. Update the builder agent's SKILL DISPATCH table to include new skills
2. Update the agent's INTERVIEW PHASE to recognize admin objectives
3. Update the agent frontmatter `skills:` list
4. Update CLAUDE.md file map with new reference docs and skills
5. Update the agent's REFERENCE DOC LOADING section with new docs

---

## Constraints

- Do NOT modify any CLI code — only documentation, skills, and agent definition
- Do NOT modify existing calling reference docs or skills
- Follow existing patterns — match the structure and style of calling docs/skills
- Every CLI command reference should be verified by running `wxcli <group> <command> --help`
- Mark unverified information with `<!-- NEEDS VERIFICATION -->`
- Keep skills focused on operational workflows, not API encyclopedias
