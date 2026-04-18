---
name: teardown
description: |
  Tear down Webex Calling resources in dependency-safe order. Covers single-location
  teardown, multi-location bulk cleanup, migration test cleanup, and org reset.
  Use for: delete, remove, clean up, tear down, reset, decommission.
argument-hint: [scope — e.g. "DP-HQ-Phones", "all GlobalTech locations", "entire org"]
---

# Teardown Skill

Delete Webex Calling resources in the correct dependency order. Use `wxcli cleanup` for automated batch teardown, or follow the manual procedure below.

**Checkpoint — do NOT proceed until you can answer these:**
1. What resource type must be deleted BEFORE disable-calling can succeed on a location? (Answer: workspaces)
2. What is the correct argument order for location-scoped feature deletes? (Answer: `--force LOCATION_ID FEATURE_ID` — location comes FIRST)
3. Do routing delete commands use singular or plural names? (Answer: plural — `delete-route-groups` not `delete-route-group`)

If you cannot answer all three, you skipped reading this skill. Go back and read it.

## Preferred: `wxcli cleanup` (automated)

```bash
# Dry-run first — shows what would be deleted
wxcli cleanup run --scope "Location Name" --dry-run

# Delete all resources at specific locations (--include-users is ORG-WIDE — always pair with --exclude-user-domains)
wxcli cleanup run --scope "DP-HQ-Phones,DP-Branch-Phones" --include-users --exclude-user-domains "wbx.ai" --force

# Delete everything in the org
wxcli cleanup run --all --include-users --include-locations --force

# Delete users but keep admin accounts by domain
wxcli cleanup run --all --include-users --exclude-user-domains "wbx.ai,corp.com" --force

# Control parallelism
wxcli cleanup run --scope "GlobalTech*" --max-concurrent 10 --force
```

`wxcli cleanup` handles the full dependency DAG automatically: inventories all resources, deletes in the correct 13-layer order (including phone number removal before location deletion), and parallelizes within each layer.

**Key behaviors:**
- **Phone numbers** are removed automatically before location deletion (batched in groups of 5, main numbers skipped). Numbers assigned to a location block location deletion with 409.
- **Location deletion cannot be completed via API.** The public API cannot disable Webex Calling on a location — the telephony detach endpoint returns 404 in most orgs. `wxcli cleanup --include-locations` will remove all resources AT the location (features, routing, devices, users, numbers) but the location itself will remain calling-enabled and 409 on delete. **The operator must finish location deletion in Control Hub** (Locations → select location → disable Webex Calling → delete). Always tell the user this upfront when `--include-locations` is requested.
- **`--include-users` is location-scoped when `--scope` is set.** With `--scope`, only users at the specified locations are deleted. With `--all`, all org users are in scope. In both cases, **always use `--exclude-user-domains`** to protect admin and service accounts (e.g., `--exclude-user-domains "wbx.ai,company.com"`).

**Always dry-run first** for any scope larger than a single location.

### What `wxcli cleanup` deletes by default (no flags)

With just `--scope` and `--force`, cleanup deletes: dial plans, route lists, route groups, translation patterns, trunks, call features (HG/CQ/AA/paging/park/pickup), operating modes, schedules, virtual lines, **devices**, **workspaces**, and phone numbers. It does NOT delete users or locations unless `--include-users` / `--include-locations` is passed.

**Selective teardown (features/routing only, keep devices + users + location):**
Do NOT use `wxcli cleanup` — it has no `--exclude-devices` flag and will delete devices and workspaces. Use the manual procedure (Step 2 below), deleting only Layers 1-2 (features + routing).

---

## Manual Teardown Procedure

Use when `wxcli cleanup` is unavailable or you need fine-grained control.

### Step 1: Enumerate ALL resources upfront

Run ALL of these checks before deleting anything. Collect the full inventory.

```bash
LOC=<LOCATION_ID>

# Layer 1: Features
wxcli hunt-group list --location-id $LOC -o json 2>&1
wxcli call-queue list --location-id $LOC -o json 2>&1
wxcli call-queue list --location-id $LOC --has-cx-essentials true -o json 2>&1
wxcli auto-attendant list --location-id $LOC -o json 2>&1
wxcli paging-group list --location-id $LOC -o json 2>&1
# Call parks and pickups REQUIRE location as positional arg — org-wide list returns EMPTY
wxcli call-park list $LOC -o json 2>&1
wxcli call-pickup list $LOC -o json 2>&1
wxcli location-voicemail list-voicemail-groups $LOC -o json 2>&1

# Layer 2: Routing (org-wide — filter by location in output)
wxcli call-routing list -o json 2>&1               # dial plans
wxcli call-routing list-route-lists -o json 2>&1   # route lists
wxcli call-routing list-route-groups -o json 2>&1  # check which reference trunks in this location
wxcli call-routing list-trunks -o json 2>&1        # filter by location in output

# Layer 3: Supporting resources
wxcli virtual-extensions list --location-id $LOC -o json 2>&1
wxcli location-schedules list $LOC -o json 2>&1
wxcli operating-modes list --location-id $LOC -o json 2>&1

# Layer 4: Users
wxcli users list --location-id $LOC -o json 2>&1

# Layer 5: Workspaces (no --location-id flag — filter client-side by locationId)
wxcli workspaces list -o json 2>&1
```

Present the full inventory to the user before proceeding.

### Step 2: Delete in dependency order

Delete **layer by layer, top to bottom**. Resources within the same layer have no interdependencies and can be deleted in parallel.

#### Layer 1: Features
```bash
wxcli hunt-group delete --force $LOC <HG_ID>
wxcli call-queue delete --force $LOC <CQ_ID>
wxcli auto-attendant delete --force $LOC <AA_ID>
wxcli call-park delete --force $LOC <PARK_ID>
wxcli call-pickup delete --force $LOC <PICKUP_ID>
wxcli paging-group delete --force $LOC <PG_ID>
```

#### Layer 2: Routing (reverse creation order)
```bash
# Dial plans first, then route lists, then route groups, then trunks
wxcli call-routing delete-dial-plans --force <DP_ID>
wxcli call-routing delete-route-lists --force <RL_ID>
wxcli call-routing delete-route-groups --force <RG_ID>
wxcli call-routing delete-translation-patterns --force <TP_ID>
wxcli call-routing delete-trunks --force <TRUNK_ID>
```

#### Layer 3: Supporting resources
```bash
wxcli virtual-extensions delete --force <VE_ID>
wxcli location-schedules delete --force $LOC <TYPE> <SCHEDULE_ID>
wxcli operating-modes delete --force <OM_ID>
```

#### Layer 4: Users
```bash
wxcli users delete --force <USER_ID>
```

#### Layer 5: Workspaces
```bash
# Must delete workspaces BEFORE disabling calling on the location
wxcli workspaces delete --force <WORKSPACE_ID>
```

#### Layer 6: Phone Numbers
```bash
# Remove phone numbers BEFORE location deletion — numbers block location delete with 409
# List numbers for the location
wxcli numbers list --location-id $LOC -o json
# Delete numbers (API accepts max 5 per request, main number cannot be removed)
# Use wxcli numbers delete $LOC or raw API:
#   DELETE /telephony/config/locations/{LOC}/numbers  body: {"phoneNumbers": ["+1..."]}
```

#### Layer 7: Locations
```bash
# The API CANNOT disable Webex Calling on a location. After clearing all
# dependencies above, the location will still 409 on delete because it
# remains calling-enabled. Attempt the delete — it may work in rare cases:
wxcli location-settings safe-delete-check $LOC
wxcli locations delete --force $LOC
# If 409: tell the user to finish in Control Hub (disable calling → delete).
```

### Step 3: Handle 409 on location delete

If `locations delete` returns 409 "being referenced", check these in order:

1. **Phone numbers still assigned** — `wxcli numbers list --location-id $LOC -o json`. Remove non-main numbers before location delete. `wxcli cleanup` handles this automatically (Layer 12).
2. **CX Essentials queues** hidden from default `call-queue list` — need `--has-cx-essentials true`
3. **Call parks / pickups** not found — `call-park list` and `call-pickup list` without `$LOC` as first positional arg return empty
4. **Virtual lines** — discoverable via `wxcli numbers list -o json` (owner.type == VIRTUAL_LINE), not always via `virtual-extensions list`
5. **Workspaces** still assigned — workspaces API has no location filter, must filter client-side by `locationId` field
6. **Operating modes** referencing deleted schedules
7. **Calling-enabled location (most common cause)** — the public API cannot disable Webex Calling on a location. Even with all visible dependencies gone, the location remains calling-enabled and 409s on delete. The telephony detach endpoint (`DELETE /telephony/config/locations/{id}`) returns 404 in most orgs. **This is not fixable via CLI/API — the operator must disable Webex Calling in Control Hub** (Locations → select → disable calling → delete).
8. **Ghost/stale locations** — locations returning 404 on sub-resource queries may still be deletable. Attempt deletion regardless.

### Rule: never hand-roll polling loops

When a 409 persists after the built-in 90s wait (or any other "wait and retry" situation in teardown), follow these rules strictly. Violating them causes silent Bash-tool timeouts mid-loop and unrecoverable partial state.

1. **Do NOT** write external Python or bash polling loops with `time.sleep` / `sleep` inside a single Bash tool call. The Bash tool has a ~10-minute hard timeout; long loops die silently with no useful output.
2. **Do** re-invoke `wxcli cleanup run` (with the same `--scope` / flags). It is **idempotent** — safe to repeat — and resumes cleanup from wherever it left off. This is the preferred recovery path for 409s.
3. If bespoke per-location retry is truly required, split it into **discrete Bash tool calls** — one call per location per attempt (or per round) — with a short `sleep` **between** tool calls, not inside them. Each call returns control to the parent before the next wait begins.
4. Cap any necessary hand-written retry script at **≤3 minutes wall time**. Beyond that, exit the script and let the parent re-dispatch — do not stretch a single Bash call toward the 10-minute ceiling.
5. If `cleanup run` exits with remaining 409s, **report them in the task summary and stop**. Do not loop silently. The operator (or parent agent) decides whether to re-invoke.

### Gotcha: CCP-integrated PSTN backend gate (dCloud / Cisco Calling Plan orgs)

When the target org uses **Cisco Calling Plan** (CCP-integrated PSTN), number deletion fails with `ERR.V.TRM.TMN60004` ("DELETE number is supported only for non-integrated CCP") — these numbers are managed via the PSTN portal, not the API. After trunk/route-group/feature/user teardown, **location delete then 409s with "being referenced"** for hours even though there are no locally visible dependencies. Webex's internal PSTN backend is async-releasing trunk references and typically clears in **1-4 hours** in dCloud/CCP orgs. No API action can speed this up.

`wxcli cleanup run` now detects the explicit number-delete signature and short-circuits those number removals:
- **Number delete:** skipped with a `[number=<ext/e164>] skipped — CCP-integrated, managed via PSTN portal` log line, not counted as a failure.
- **Location delete:** do **not** infer CCP solely from a generic `409 "being referenced"` response. Generic 409s can also mean preserved users, voice portal state, or the fact that the location is still calling-enabled and must be finished in Control Hub.

---

## Critical Rules

1. **Always use `--force`** — skip interactive confirmation for programmatic deletes
2. **Location-scoped feature deletes take LOCATION_ID FIRST** — `wxcli hunt-group delete --force LOCATION_ID HG_ID`, not `HG_ID LOCATION_ID`
3. **Routing delete commands use PLURAL names** — `delete-route-groups` not `delete-route-group`, `delete-trunks` not `delete-trunk`
4. **Workspaces block location deletion** — delete all workspaces at a location BEFORE running disable-calling
5. **Do not promise API disable-calling** — use CLI/API to remove visible blockers, but warn that final delete of a calling-enabled location may still require Control Hub
6. **Enumerate before deleting** — never start deleting without a full inventory; hidden resources (CX queues, call parks, workspaces) will block location delete
7. **Multi-location teardown** — repeat the procedure per location, or use `wxcli cleanup run --scope "Loc1,Loc2"` for automation
