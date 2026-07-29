---
name: provision-calling
description: |
  Provision Webex Calling users, locations, and licenses via the wxcli CLI.
  Also covers People API profile updates (alternate phone numbers, display name,
  phoneNumbers array including alternate1/alternate2), number inventory management,
  and bulk CSV import. Also covers org-wide calling service defaults (announcement
  language list, org voicemail settings and passcode rules, org music on hold,
  large org status, org call captions) via the calling-service group.
  Guides through auth verification, prerequisite checks,
  deployment planning, execution, and result verification for any provisioning operation.
  Use for: create, enable, assign, bulk provision, update user profile fields.
  For teardown/delete/cleanup operations, use the teardown skill instead.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation — e.g. "create location", "enable user", "assign license", "bulk provision", "org calling defaults"]
---

<!-- Updated by playbook session 2026-03-18 -->

# Provision Calling Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. Can `location_id` be changed after a calling license is assigned? (Answer: No — it is write-once. Wrong location = must remove and re-add calling license.)
2. What case must `announcement_language` use? (Answer: lowercase only — `en_us` not `en_US`. Mixed case causes "Invalid Language Code" error.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/provisioning.md` for People, Licenses, and Locations API patterns
2. For org-level calling defaults (Operation G) only, read `docs/reference/location-calling-core.md` § "CLI: `calling-service` (Org-Level Calling Service Settings)" — skip this unless the user asks about org-wide voicemail, music on hold, or call captions

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags. Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth token is working

Before any provisioning operation, confirm the token is valid and has admin scopes.

```bash
wxcli whoami
```

If this fails with 401/403, stop and troubleshoot auth before proceeding. Common causes:
- Token expired (personal access tokens last 12 hours)
- Token not configured — run `wxcli configure` or check `~/.wxcli/config.json`
- Token lacks admin scopes (`spark-admin:people_write`, `spark-admin:licenses_read`, etc.)

## Step 3: Determine the operation

Ask the user which provisioning operation they need. The seven supported operations are:

| Operation | What It Does | Prerequisites |
|-----------|-------------|---------------|
| **Create location** | Add a new physical location | Admin token with `spark-admin:locations_write` |
| **Enable location for calling** | Turn on Webex Calling for an existing location | Location must exist; `spark-admin:telephony_config_write` |
| **Create user** | Add a new person to the org | Admin token with `spark-admin:people_write` |
| **Enable user for calling** | Assign calling license + location + extension to existing user | Location must exist; calling license available |
| **Assign/change licenses** | Add or remove licenses on a user | License with available capacity |
| **Bulk provision** | Provision multiple users in one run | All of the above |
| **Org-wide calling defaults** | Read/set org voicemail, music on hold, call captions; look up valid announcement language codes | Admin token with `spark-admin:telephony_config_write` |

Confirm with the user before proceeding:
- **Which operation** from the table above
- **Target details** (location name/address, user email, license type, etc.)
- **For bulk**: CSV or list of users to provision

## Step 4: Check prerequisites

Run these checks based on the operation. **Stop and report** if any prerequisite fails.

### For location creation:
```bash
# Check if location name already exists
wxcli locations list --name "target name"
# Look for a match in the output. If the target name appears:
wxcli locations show LOCATION_ID
# Ask user: update existing or abort?
```

### For user provisioning:
```bash
# 1. Verify location exists and is calling-enabled
wxcli location-settings list-1
# Confirm target location appears (only calling-enabled locations are returned)

# 2. Find an available calling license with capacity
wxcli licenses list
# Look for "Webex Calling - Professional" with consumed < total

# 3. Check if user already exists
wxcli users list --email target@example.com --output json
# If user exists, check if already calling-enabled:
wxcli users show PERSON_ID --output json
# If location_id is set, user is already calling-enabled.
# Ask user: update or abort?

# 4. Verify email domain is provisioned in this org
# No CLI command lists currently-claimed org domains — the `domains` group only
# supports get-domain-verification / verify-domain / claim-domain / unverify-domain /
# unclaim-domain (see manage-identity skill for the verification flow). If domain
# status is unknown, check Control Hub, or attempt user creation and watch for a
# domain authorization error; resolve via manage-identity's domain verification
# flow before retrying.
```

### For phone number assignment:
```bash
# Verify number is in location inventory before assigning to a user
# Numbers must be added to location first via numbers-manage commands
wxcli numbers create LOCATION_ID --json-body '{"phoneNumbers": ["+15551234567"], "numberType": "DID"}'
```

## Step 5: Build deployment plan — [SHOW BEFORE EXECUTING]

**Present the plan to the user and wait for approval.** Never execute without confirmation.

Format the plan as:

```
=== Provisioning Plan ===

Operation: [Create Location / Enable User / etc.]

Target:
  - [specific details]

Steps:
  1. [First CLI command — what it does]
  2. [Second CLI command — what it does]
  3. Verify: [what we'll check after]

Prerequisites verified:
  ✓ Auth token valid (authenticated as [name])
  ✓ Location exists: [name] ([id])
  ✓ License available: [name] ([consumed]/[total])
  ✓ [any other checks]

Proceed? [wait for user confirmation]
```

## Step 6: Execute the provisioning operation

### Operation A: Create a Location

Required flags: `--name`, `--time-zone`, `--preferred-language`, `--announcement-language`. Address must go in `--json-body`.

```bash
wxcli locations create \
  --name "San Jose Office" \
  --time-zone "America/Los_Angeles" \
  --preferred-language en_US \
  --announcement-language en_us \
  --json-body '{"address": {"address1": "123 Main St", "city": "San Jose", "state": "CA", "postalCode": "95113", "country": "US"}}'
```

### Operation B: Enable Location for Calling

Creating a location does NOT automatically enable calling. Separate command required.

First, fetch the location details you'll need:
```bash
wxcli locations show LOCATION_ID
```

Then enable calling using those details:
```bash
wxcli location-settings create \
  --id LOCATION_ID \
  --name "San Jose Office" \
  --time-zone "America/Los_Angeles" \
  --preferred-language en_US \
  --announcement-language en_us
```

**Important:** `announcement_language` must be lowercase (`en_us` not `en_US`) or the API rejects with "Invalid Language Code".

To confirm a language code before using it, list the announcement languages the org supports — the `code` field is the exact value to pass to `--announcement-language`, already lowercase:

```bash
wxcli calling-service list
```

Verified live: returns 42 languages as `{"name": "Italian", "code": "it_it"}` pairs. See Operation G for the rest of the `calling-service` group.

**Warning:** Do not promise an API-based "disable calling" step during teardown. Use CLI/API to clear visible blockers first, but final delete of a calling-enabled location may still require Control Hub if the backend continues to hold the telephony reference.

### Operation C: Create a New User

**Before creating:** confirm the user's `firstName`, `lastName`, and `displayName` with the requester. Do not use email-derived placeholders (e.g., `jsmith`/`example`) — they produce incorrect directory entries and cannot be changed without a separate update call.

```bash
wxcli users create \
  --json-body '{"emails":["jsmith@example.com"],"firstName":"John","lastName":"Smith","displayName":"John Smith"}'
```

**Gotcha:** A POST that returns 400 may **still have created the person**. Always check with a GET before retrying:
```bash
wxcli users list --email jsmith@example.com --output json
```

### Operation D: Enable Existing User for Calling

Assign a calling license, location, and extension to an existing user.

```bash
# Look up current user state
wxcli users show PERSON_ID --output json

# Look up the calling license ID
wxcli licenses list --output json
# Find the license where name contains "Calling - Professional"

# Assign the calling license with location and extension
wxcli licenses update --person-id PERSON_ID --json-body '{
  "email": "jsmith@example.com",
  "licenses": [{
    "id": "CALLING_LICENSE_ID",
    "properties": {
      "locationId": "LOCATION_ID",
      "extension": "1001"
    }
  }]
}'
```

**Key constraints:**
- `location_id` is **write-once** — can only be set on initial calling license assignment, cannot be changed after
- `extension` value must NOT include the location routing prefix
- Either `phone_number` or `extension` is mandatory for calling licenses
- To move a user, remove calling license and re-add with new location

### Operation E: Bulk Provision

**Before running:** confirm `firstName`, `lastName`, and `displayName` for each user with the requester. Do not derive names from email aliases.

For small batches (< 20 users), pair each create with an immediate license assignment in a single loop:

```bash
LOCATION_ID="<location_id>"
LICENSE_ID="<calling_license_id>"
EXT=1001

for email in user1@example.com user2@example.com user3@example.com; do
  echo "=== Provisioning $email ==="

  # Step 1: Create the user — capture the returned person ID
  PERSON_ID=$(wxcli people create -o json \
    --json-body "{\"emails\":[\"$email\"],\"firstName\":\"First\",\"lastName\":\"Last\",\"displayName\":\"First Last\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  echo "Created: $email → $PERSON_ID"

  # Step 2: Assign calling license with location and extension
  wxcli licenses update --person-id "$PERSON_ID" --json-body "{
    \"email\": \"$email\",
    \"licenses\": [{
      \"id\": \"$LICENSE_ID\",
      \"operation\": \"add\",
      \"properties\": {
        \"locationId\": \"$LOCATION_ID\",
        \"extension\": \"$EXT\"
      }
    }]
  }"
  echo "Enabled for calling: ext $EXT"

  EXT=$((EXT + 1))
done
```

**Note:** If `people create` returns 400, the user may still have been created. Check with `wxcli people list --email <email>` before retrying. If the user exists, skip the create and run only the `licenses update` step with the existing person ID.

> **Bulk operations (50+ users):** Shell loops with `sleep 1` work for small batches. For large batches, use the migration engine's async pattern, which handles concurrency, rate limiting, and retry automatically.

### Operation F: Teardown / Delete Location

**For teardown operations, load the `teardown` skill.** It covers single-location teardown, multi-location bulk cleanup, and org reset with the full dependency-safe deletion order and `wxcli cleanup` automation.

Delete-related critical rules (13-15) below still apply.

### Operation G: Org-Wide Calling Service Defaults

The `calling-service` group holds calling settings that apply to the **whole org**, not to a location and not to a person. These are the defaults new locations and users inherit, so they are worth reading during org bootstrap and before bulk provisioning.

Scope check: if the setting is per-location, use the `configure-features` skill. If it is per-person, use `manage-call-settings`. Only org-wide defaults live here.

| Command | What it reads/sets | When you need it |
|---------|-------------------|------------------|
| `calling-service list` | Announcement languages (`name` + `code`) | Look up a valid `--announcement-language` code (Operation B) |
| `calling-service show` / `update` | Org voicemail settings — message expiry, strict deletion, email forwarding | Set org voicemail retention before provisioning users |
| `calling-service show-rules` / `update-rules` | Org voicemail passcode policy — default PIN, expiry, reuse blocking | Set the PIN policy new users inherit |
| `calling-service show-settings` / `update-settings` | Org default music on hold | Choose `OPUS` or `LEGACY` org-wide |
| `calling-service show-large-org-status` | Whether the org crosses the large-org threshold | Check before bulk provisioning — large orgs behave differently |
| `calling-service show-call-captions` / `update-call-captions` | Org closed captions and transcripts | Enable/disable captions org-wide |

**Data (storage) policy region** is a separate group, `data-policies` — it sets the country where the org's calling data is stored, at org level or per location. Upstream moved this off the call recording vendor endpoints, so `call-recording ... --storage-region` no longer exists.

| Command | What it reads/sets |
|---------|-------------------|
| `data-policies list` | Storage regions available to configure (`code`/`name`/`isVoicemailStorageRestrictionEnabled`) |
| `data-policies show` / `update` | Org-level storage region (`--org-data-region`, ISO 3166-1 alpha-2) |
| `data-policies show-data-policies` / `update-data-policies` | Per-location storage region, or inherit the org's |

`data-policies list` is how you discover valid region codes before setting `--org-data-region` or `--location-data-region` — its table is the only source of truth for what's configurable; don't guess a code.

```bash
# Which regions can be configured
wxcli data-policies list -o json
```
Verified live: 9 regions — `AU`, `CA`, `DE`, `GB`, `JP`, `SG`, `SA`, `IN`, `US` — each as `{"code": "US", "name": "United States", "isVoicemailStorageRestrictionEnabled": false}`. Only `SA` (Saudi Arabia) has voicemail storage restriction enabled today.

```bash
# What the org uses today
wxcli data-policies show
```
Verified live: `{"orgDataRegion": "US", "allowEditEnabled": true}`.

```bash
# What a specific location uses today
wxcli data-policies show-data-policies LOCATION_ID
```
Verified live: `{"useOrgDataRegionEnabled": true, "orgDataRegion": "US", "allowEditEnabled": true}`. A location inheriting the org's region still reports it under `orgDataRegion` — there is no separate `locationDataRegion` field until the location is set to its own region.

**Write commands (not live-exercised — changes org/location config; flags confirmed from source):**

```bash
# Set the org-level storage region
wxcli data-policies update --org-data-region US

# Set a location's region, or have it inherit the org-level one
wxcli data-policies update-data-policies LOCATION_ID --location-data-region US
wxcli data-policies update-data-policies LOCATION_ID --use-org-data-region-enabled
wxcli data-policies update-data-policies LOCATION_ID --no-use-org-data-region-enabled
```

Both writes also accept `--json-body` / `--generate-json-body` for the same fields (`{"orgDataRegion":"..."}` and `{"locationDataRegion":"...","useOrgDataRegionEnabled":true}` respectively).


**Read the current org defaults (all read-only, safe to run during prerequisite checks):**

```bash
# Announcement languages — returns {"name": "Italian", "code": "it_it"} pairs
wxcli calling-service list

# TTS-capable languages only (--tts-language is a boolean filter)
wxcli calling-service list --tts-language true

# Org voicemail settings
wxcli calling-service show

# Org voicemail passcode rules
wxcli calling-service show-rules

# Org default music on hold
wxcli calling-service show-settings

# Large org status
wxcli calling-service show-large-org-status

# Org call captions / transcripts
wxcli calling-service show-call-captions
```

**Change org defaults (write — these hit every user in the org; show the plan and get approval first):**

```bash
# Expire voicemail messages after 30 days
wxcli calling-service update --message-expiry-enabled --number-of-days-for-message-expiry 30

# Turn message expiry back off (paired --no- flags exist for every boolean here)
wxcli calling-service update --no-message-expiry-enabled

# Set the org default music on hold — valid values are OPUS or LEGACY
wxcli calling-service update-settings --default-org-moh "OPUS"

# Enable org-level closed captions and transcripts
wxcli calling-service update-call-captions --org-closed-captions-enabled --org-transcripts-enabled
```

`update-rules` (voicemail passcode policy) has nested fields that the flags do not cover — use `--json-body`:

```bash
wxcli calling-service update-rules --json-body '{
  "defaultVoicemailPinEnabled": true,
  "expirePasscode": {"enabled": true, "numberOfDays": 90},
  "changePasscode": {"enabled": true, "numberOfDays": 1},
  "blockPreviousPasscodes": {"enabled": true, "numberOfPasscodes": 3}
}'
```

Read back after any write — every one of these is a `show` away:

```bash
wxcli calling-service show
wxcli calling-service show-settings
wxcli calling-service show-call-captions
```

## Step 7: Verify results

Always read back the created/updated resources to confirm.

### Verify a user:
```bash
wxcli users show PERSON_ID --output json
# Confirm: location_id is set, calling license appears in licenses list, extension is correct
```

### Verify a location:
```bash
wxcli locations show LOCATION_ID --output json
# Confirm: name, address, timezone are correct
```

### Verify bulk:
```bash
# List all users at a location
wxcli users list --location-id LOCATION_ID --output json
# Count results to confirm expected number of users provisioned
```

## Step 8: Report results

Summarize what was done:

```
=== Provisioning Complete ===

Operation: [what was done]
Results:
  - [resource]: [status] ([id])
  - [resource]: [status] ([id])

Verification:
  ✓ [what was confirmed]

Next steps:
  - [any follow-up actions needed]
```

---

## Critical Rules

1. **ALWAYS test auth first** — Run `wxcli whoami` before any provisioning call. Do not proceed on auth failure.

2. **ALWAYS show plan before executing** — Present the deployment plan and wait for user confirmation. Never provision without approval.

3. **`location_id` is write-once** — Can only be set when first assigning a calling license. Cannot be changed after. To move a user, remove calling license and re-add with new location.

4. **`announcement_language` must be lowercase** — `en_us` not `en_US`. The telephony `enable_for_calling` API rejects mixed case with "Invalid Language Code".

5. **`announcement_language` returns None from details** — Always set it explicitly before calling `enable_for_calling`, even if it was set during creation.

6. **Do not promise API disable-calling on locations** — the older `wxcli location-settings update-location-calling ...` guidance is stale in this repo. For teardown, use CLI/API to remove visible blockers, run `wxcli location-settings safe-delete-check LOCATION_ID`, retry delete, and warn that final removal of a calling-enabled location may still require Control Hub.

7. **Phone numbers must be in location inventory first** — Before assigning a DID to a user, add it via `wxcli numbers create LOCATION_ID`.

8. **POST/PUT may partially succeed** — A 400 response on user create/update may have still created/modified the resource. Always verify with a subsequent GET before retrying.

9. **License IDs are org-specific base64 strings** — Never hardcode them. Always retrieve via `wxcli licenses list`.

10. **Extension values must NOT include the routing prefix** — Set extension to `1001`. The work_extension in the response will include the prefix (e.g., `8001001`), but when writing, omit it. To check for extension conflicts before assigning, run `wxcli numbers list --location-id LOCATION_ID` and scan the extension column.

11. **Log all operations** — Print what you're about to do before each CLI command, and print the result after. This creates an audit trail for troubleshooting.

12. **For bulk operations (50+ users), use the migration engine's async pattern** — wxcli runs one command at a time. For large batches, the proven async pattern handles concurrency, rate limiting, and retry. For smaller batches (<50), shell loops with `sleep 1` suffice.

13. **Location-scoped feature deletes require LOCATION_ID as FIRST argument** — `wxcli hunt-group delete --force LOCATION_ID HG_ID`, not `hunt-group delete --force HG_ID`. The LOCATION_ID comes before the feature ID.

14. **Always use `--force` for programmatic deletes** — Without `--force`, delete commands prompt `[y/N]` which blocks non-interactive execution.

15. **Routing delete commands use PLURAL names** — `delete-route-groups`, `delete-trunks`, `delete-route-lists`. The singular form (`delete-route-group`) does not exist.

16. **`calling-service` is org-wide, not per-location** — Every `update*` in that group changes the default for the entire org, including users you did not provision. There is no location or person argument to scope it. Treat these as high-blast-radius writes and get explicit approval.

17. **`calling-service` command names do not say what they touch** — The generated names are generic: `show`/`update` are **voicemail** settings, `show-settings`/`update-settings` are **music on hold**, and `list` is **announcement languages**. Read the Operation G table before running any of them; the name alone will mislead you.

---

## Error Handling

When a wxcli command fails:

**A. Fix and retry** — Missing required field, wrong ID, format issue:
1. Read the full error message
2. Run `wxcli <group> <command> --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** — Resource already exists or already configured:
1. Verify current state: `wxcli users show PERSON_ID` or `wxcli locations show LOCATION_ID`
2. If state is correct, skip to next operation

**C. Escalate** — Unclear or persistent error:
1. Run with `--debug` for raw HTTP details
2. Invoke `/wxc-calling-debug` for systematic diagnosis

**D. 409 Conflict (50003 "Location is being referenced")**

The location still has dependent resources. Load the `teardown` skill and follow its enumeration procedure. If all resources are deleted and the 409 persists, calling is still enabled — disable it and wait 90+ seconds.

Provisioning-specific errors:
- 400 on `users create`: Check email format, verify no existing user with same email
- 400 on `numbers create`: Check E.164 format (+1XXXXXXXXXX), verify number not already assigned
- 403: Check token has `spark-admin:people_write` and `spark-admin:telephony_config_write` scopes
- 409: User/location already exists — GET current state first

---

## Required Scopes Reference

| Operation | Scope(s) |
|-----------|----------|
| List/view people | `spark-admin:people_read` |
| Create/update/delete people | `spark-admin:people_write` + `spark-admin:people_read` |
| List licenses | `spark-admin:licenses_read` |
| Assign licenses (PATCH) | `spark-admin:people_write` |
| List/view locations | `spark-admin:locations_read` |
| Create/update/delete locations | `spark-admin:locations_write` |
| Enable location for calling | `spark-admin:telephony_config_write` |

---

## License Lookup Quick Reference

> For bulk license assignment, usage auditing, and reclamation workflows, see the `manage-licensing` skill. The `licenses update` command provides CLI-native license assignment (`licenses-api` remains a deprecated alias for one release).

```bash
# List all licenses — look for "Webex Calling - Professional" with available capacity
wxcli licenses list

# Key license types to look for in the output:
#   "Webex Calling - Professional"   — full calling license
#   "Webex Calling - Basic"          — basic calling (limited features)
#   "Webex Calling - Workspaces"     — for workspace devices
# Check that consumed < total for the license you need
```

---

## Two License Assignment Methods

| | Method A: People API PUT | Method B: Licenses PATCH API |
|---|---|---|
| **CLI equivalent** | `wxcli users update` (modify user fields) | Raw HTTP PATCH `/licenses/users` (license assignment not in CLI yet) |
| **Best for** | Migrating existing users, changing multiple Person fields | Net-new provisioning, SCIM users, atomic license+location+extension |
| **Gotcha** | Must GET full person first, include ALL fields in PUT | Requires extension or phone_number for calling licenses |
| **Can combine add+remove** | Manually modify the licenses list | Yes, add + remove operations in same call |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
