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

# Delete all resources at specific locations
wxcli cleanup run --scope "DP-HQ-Phones,DP-Branch-Phones" --include-users --force

# Delete everything in the org
wxcli cleanup run --all --include-users --include-locations --force

# Control parallelism
wxcli cleanup run --scope "GlobalTech*" --max-concurrent 10 --force
```

`wxcli cleanup` handles the full dependency DAG automatically: inventories all resources, deletes in the correct 12-layer order, parallelizes within each layer, and waits for async operations like disable-calling propagation.

**Always dry-run first** for any scope larger than a single location.

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

#### Layer 6: Locations
```bash
# Disable calling first — this is ASYNC
wxcli location-call-settings update-location-calling $LOC --calling-enabled false
# Wait 90+ seconds for backend propagation
sleep 90
# Then delete
wxcli locations delete --force $LOC
```

### Step 3: Handle 409 on location delete

If `locations delete` returns 409 "being referenced", check these in order:

1. **CX Essentials queues** hidden from default `call-queue list` — need `--has-cx-essentials true`
2. **Call parks / pickups** not found — `call-park list` and `call-pickup list` without `$LOC` as first positional arg return empty
3. **Virtual lines** — discoverable via `wxcli numbers list -o json` (owner.type == VIRTUAL_LINE), not always via `virtual-extensions list`
4. **Workspaces** still assigned — workspaces API has no location filter, must filter client-side by `locationId` field
5. **Operating modes** referencing deleted schedules
6. **Calling still propagating** — even after `--calling-enabled false`, 409 may persist for minutes. Wait and retry.

---

## Critical Rules

1. **Always use `--force`** — skip interactive confirmation for programmatic deletes
2. **Location-scoped feature deletes take LOCATION_ID FIRST** — `wxcli hunt-group delete --force LOCATION_ID HG_ID`, not `HG_ID LOCATION_ID`
3. **Routing delete commands use PLURAL names** — `delete-route-groups` not `delete-route-group`, `delete-trunks` not `delete-trunk`
4. **Workspaces block location deletion** — delete all workspaces at a location BEFORE running disable-calling
5. **Disable-calling is async** — poll with `wxcli location-settings show-errors <JOB_ID>` until complete, minimum 90 seconds
6. **Enumerate before deleting** — never start deleting without a full inventory; hidden resources (CX queues, call parks, workspaces) will block location delete
7. **Multi-location teardown** — repeat the procedure per location, or use `wxcli cleanup run --scope "Loc1,Loc2"` for automation
