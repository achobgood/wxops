# Deployment Plan: [OBJECTIVE_SUMMARY]

Created: [YYYY-MM-DD]
Agent: wxc-calling-builder
Saved to: `docs/plans/[YYYY-MM-DD]-[descriptive-name].md`

---

## 1. Objective

[One paragraph stating what this deployment will accomplish and why.]

Example: *Provision 5 Webex Calling users at the Austin location, assign DIDs from the Austin
number pool, and route the front-desk number to a new Support call queue.*

## 2. Scope

What this deployment touches — with specific names and IDs, not categories.

| Level | In scope | Out of scope |
|-------|----------|-------------|
| Org | [Org name / ID, or "no org-wide changes"] | [e.g. org voicemail defaults] |
| Location(s) | [Austin — `Y2lz...abc`] | [All other locations] |
| User(s) | [alice@example.com, bob@example.com] | [Existing users] |
| Feature(s) | [Call queue "Support" (ext 2000)] | [Existing AAs, hunt groups, routing] |

**Resources created or modified:**

| Resource Type | Name / Identifier | Action | Details |
|--------------|------------------|--------|---------|
| Location | Austin | Create | New calling-enabled location |
| Person | Alice Smith (alice@example.com) | Create | New Webex Calling user (ext 1001) |
| Phone Number | +1 (512) 555-0101 | Assign | Assign to Alice Smith |
| Call Queue | Support (ext 2000) | Create | Front-desk overflow |
| [etc.] | | | |

## 3. Prerequisites

Everything listed here must be confirmed before execution begins. The agent verifies each one
with a read-only `wxcli` command and reports any blockers. Mark each as **confirmed** or
**needs-creation**.

| # | Prerequisite | Verification Command | Status |
|---|-------------|---------------------|--------|
| 1 | Authenticated against the right org | `wxcli whoami` | [ ] |
| 2 | Target location exists | `wxcli locations list --name "Austin" --fields '[].{name:name,id:id}' -o json` | [ ] |
| 3 | Location is enabled for Calling | `wxcli location-settings list-calling-details --all -o json` | [ ] |
| 4 | Sufficient Calling licenses | `` wxcli licenses list --all --fields '[?contains(name,`Calling`)].{name:name,total:totalUnits,used:consumedUnits}' -o json `` | [ ] |
| 5 | Unassigned numbers available | `wxcli numbers list --location-id LOCATION_ID --assigned false --all -o json` | [ ] |
| 6 | Target users do not already exist | `wxcli people list --email alice@example.com --calling-data true -o json` | [ ] |
| 7 | [Additional prereqs as needed] | | [ ] |

**Counting rule:** any "how many / which ones / are there any" prerequisite check uses `--all`.
A single fetch returns page one and will silently under-count. On `people`, add
`--calling-data true` before reading `extension` or `locationId` — without it those fields are
omitted and the answer comes back as a confident zero.

**Blockers found:** [None / list blockers here]

## 4. Execution Steps

Ordered `wxcli` commands in dependency order. Show actual values, not placeholders — this is the
script the agent will run.

### Step 1 — [Create the Austin location]

- **Command:**
  ```bash
  wxcli locations create --json-body '{"name":"Austin","timeZone":"America/Chicago","preferredLanguage":"en_US","announcementLanguage":"en_us","address":{"address1":"100 Congress Ave","city":"Austin","state":"TX","postalCode":"78701","country":"US"}}'
  ```
- **Inputs:** name `Austin`, time zone `America/Chicago`, full street address
- **Expected result:** new location ID returned (`create` defaults to `-o id`)
- **Depends on:** None

### Step 2 — [Enable the location for Webex Calling]

- **Command:**
  ```bash
  wxcli location-settings create --id LOCATION_ID --name "Austin" --time-zone "America/Chicago" --preferred-language en_US --announcement-language en_us
  ```
- **Inputs:** the location ID from Step 1
- **Expected result:** location appears in `location-settings list-calling-details`
- **Depends on:** Step 1

### Step 3 — [Create user alice@example.com]

- **Command:**
  ```bash
  wxcli people create --json-body '{"emails":["alice@example.com"],"firstName":"Alice","lastName":"Smith","displayName":"Alice Smith"}'
  ```
- **Inputs:** email, first/last name
- **Expected result:** person ID returned
- **Depends on:** Step 2

### Step 4 — [Assign the phone number and extension to Alice]

- **Command:**
  ```bash
  wxcli user-settings update-numbers PERSON_ID \
    --json-body '{"phoneNumbers":[{"primary":true,"action":"ADD","directNumber":"+15125550101","extension":"1001","ringPattern":"NORMAL"}]}'
  ```
- **Inputs:** person ID from Step 3, a number already in the Austin location pool
- **Expected result:** number and extension appear on `user-settings list-numbers PERSON_ID`
- **Depends on:** Step 3

### Step 5 — [Configure call forwarding for Alice]

- **Command:**
  ```bash
  wxcli user-settings update-call-forwarding PERSON_ID \
    --json-body '{"callForwarding":{"busy":{"enabled":true,"destinationVoicemailEnabled":true},"noAnswer":{"enabled":true,"numberOfRings":4,"destinationVoicemailEnabled":true}}}' \
    --verify
  ```
- **Inputs:** person ID from Step 3
- **Expected result:** `Verified: … all N sent field(s) match.`
- **Depends on:** Step 3

### Step 6 — [Create the Support call queue]

- **Command:**
  ```bash
  wxcli call-queue create LOCATION_ID --name "Support" --extension 2000
  ```
- **Inputs:** location ID from Step 1, calling-enabled by Step 2
- **Expected result:** queue ID returned
- **Depends on:** Steps 1-2

| Step | Description | Command | Depends on |
|------|------------|---------|-----------|
| 1 | [Create location] | `wxcli locations create ...` | None |
| 2 | [Enable calling] | `wxcli location-settings create ...` | Step 1 |
| 3 | [Create user] | `wxcli people create ...` | Step 2 |
| 4 | [Assign number + extension] | `wxcli user-settings update-numbers ...` | Step 3 |
| 5 | [Call forwarding] | `wxcli user-settings update-call-forwarding ... --verify` | Step 3 |
| 6 | [Create queue] | `wxcli call-queue create ...` | Steps 1-2 |

**Total commands:** [N]

**Body construction:** for any command with nested request-body fields, run it once with
`--generate-json-body` to print the skeleton, fill it in, and pass it back with `--json-body`
(inline JSON, `file://path`, a bare path, or `-` for stdin). Required positional arguments are
still required when generating a skeleton — pass a placeholder, e.g.
`wxcli call-queue create dummy-location-id --generate-json-body`.

## 5. Rollback Plan

If execution fails at step N, these commands undo steps 1 through N-1. The agent executes
rollback on unrecoverable failure or on user request. Delete in reverse dependency order —
a location will not delete while resources are still assigned to it.

| Failed at | Rollback Action | Command |
|-----------|----------------|---------|
| Step 4 (number assignment) or Step 5 (call forwarding) | Delete the created user | `wxcli people delete PERSON_ID --force` |
| Step 6 (queue creation) | Delete the user, then the location | `wxcli people delete PERSON_ID --force` then `wxcli locations delete LOCATION_ID --force` |
| Step 6 (queue partially configured) | Delete the queue | `wxcli call-queue delete LOCATION_ID QUEUE_ID --force` |
| [Additional rollback scenarios] | | |

**Rollback strategy:** [Full rollback (undo everything) / Partial (keep what succeeded) / Ask user]

**Note:** for anything larger than a few resources, `wxcli cleanup run` handles dependency-safe
deletion ordering — see the teardown skill before hand-rolling a delete sequence.

## 6. Verification Steps

Every created or modified resource is read back and compared against this plan. Two mechanisms:

**a) `--verify` on writes.** Every update command that has a same-path GET accepts `--verify`.
It re-reads the resource after the write and reports any field you sent that did not take. It
**never changes the exit code** — a 2xx means the request was accepted, not applied — so read
the per-field result, do not infer success from the exit status.

```bash
wxcli user-settings update-call-forwarding PERSON_ID --json-body '{...}' --verify
# → Verified: … all N sent field(s) match.
# → or: sent X, now Y   (server normalised the value, or the write did not take)
```

**b) Read-back for creates, deletes, and commands without `--verify`.**

| # | What to verify | Command | Expected |
|---|---------------|---------|----------|
| 1 | Location exists (Step 1) | `wxcli locations show LOCATION_ID -o json` | name/address match the plan |
| 2 | Location is calling-enabled (Step 2) | `wxcli location-settings show LOCATION_ID -o json` | calling details returned for the location |
| 3 | User exists with the right extension (Steps 3-4) | `wxcli people show PERSON_ID --calling-data true --fields '{name:displayName,ext:extension,loc:locationId}' -o json` | extension `1001`, location Austin |
| 4 | Number is assigned (Step 4) | `wxcli numbers list --location-id LOCATION_ID --assigned true --all -o json` | `+15125550101` shows Alice Smith as owner |
| 5 | Queue exists with the right extension (Step 6) | `wxcli call-queue show LOCATION_ID QUEUE_ID -o json` | name `Support`, extension `2000` |
| 6 | [Additional checks] | | |

**Discrepancies found:** [None / list each field where the read-back differs from the plan]

## 7. Estimated Execution

| Aspect | Detail |
|--------|--------|
| Total commands | [N] |
| Sync vs async | [All synchronous / Steps X-Y are async — location calling-enable and number moves return before the change lands] |
| Estimated wall time | [~2 minutes for N users; bulk jobs of 50+ run through the async engine] |
| Batching | [< 20 items: shell loop / 20-50: shell loop with `sleep 1` / 50+: bulk engine] |
| Rate limits | [429 retry with `Retry-After` backoff is automatic in the bulk engine; a shell loop needs its own pacing] |
| **No change to** | [Existing users, call routing, auto attendants, etc.] |

## 8. Approval

Review the plan above. The agent will not execute until you confirm.

- [ ] **I approve this deployment plan.** Proceed with execution.
- [ ] **I need changes.** [Describe what to modify]
- [ ] **Cancel.** Do not execute.
