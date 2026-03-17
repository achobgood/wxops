# Deployment Plan: [OBJECTIVE_SUMMARY]

Created: [YYYY-MM-DD]
Agent: wxc-provision

---

## 1. Objective

[One-sentence statement of what this deployment will accomplish.]

Example: *Provision 5 users for Webex Calling at the Austin location with shared-line appearance on the front desk phone.*

## 2. Prerequisites

Everything listed here must be confirmed before execution begins. The agent will verify each one via API and report any blockers.

| # | Prerequisite | Verification Method | Status |
|---|-------------|-------------------|--------|
| 1 | Webex org accessible | `webex_api.people.me()` | [ ] |
| 2 | Target location exists | `webex_api.locations.list(name=...)` | [ ] |
| 3 | Sufficient Calling licenses | `webex_api.licenses.list()` | [ ] |
| 4 | Number inventory available | `webex_api.telephony.list_numbers(location_id=...)` | [ ] |
| 5 | [Additional prereqs as needed] | | [ ] |

**Blockers found:** [None / list blockers here]

## 3. API Calls

Ordered sequence of every SDK call the agent will make. Dependencies column indicates which prior steps must succeed first.

| Step | Operation | SDK Method | Key Parameters | Dependencies |
|------|-----------|-----------|---------------|-------------|
| 1 | [e.g., Create user] | `webex_api.people.create()` | `emails, display_name, location_id` | None |
| 2 | [e.g., Assign Calling license] | `webex_api.licenses.assign()` | `person_id, license_id` | Step 1 |
| 3 | [e.g., Assign phone number] | `webex_api.telephony.configure_person()` | `person_id, phone_number` | Steps 1-2 |
| 4 | | | | |

**Total API calls:** [N]

## 4. Resources to Create/Modify

Every resource that will be touched by this deployment.

| Resource Type | Name / Identifier | Action | Details |
|--------------|------------------|--------|---------|
| Person | Jane Smith (jane@example.com) | Create | New Webex Calling user |
| Phone Number | +1 (512) 555-0101 | Assign | Assign to Jane Smith |
| Device | Cisco MPP 8845 (MAC: AABB...) | Update | Add shared line for Jane |
| [etc.] | | | |

## 5. Rollback Plan

If execution fails partway through, these steps will undo what was created. The agent executes rollback automatically on unrecoverable failure, or on user request.

| Trigger | Rollback Action | SDK Method |
|---------|----------------|-----------|
| User creation succeeded but license assignment failed | Delete created user | `webex_api.people.delete(person_id)` |
| Number assignment failed | Remove license, delete user | `webex_api.licenses.assign()` (remove), `webex_api.people.delete()` |
| [Additional rollback scenarios] | | |

**Rollback strategy:** [Full rollback (undo everything) / Partial (keep what succeeded) / Ask user]

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Users added | [N] new Webex Calling users |
| Numbers consumed | [N] DIDs from [location] pool |
| Licenses consumed | [N] Webex Calling Professional licenses |
| Devices affected | [N] devices reconfigured |
| **No change to** | [Existing users, call routing, auto-attendants, etc.] |

## 7. Approval

Review the plan above. The agent will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
