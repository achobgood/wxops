# Per-User Migration Diff Report -- Design Spec

**Date:** 2026-04-10
**Author:** Adam Hobgood
**Status:** Draft

---

## Problem Statement

The assessment report tells the SE "your environment has 847 users, 34 decisions, complexity score 42."
The deployment plan tells the SE "we'll create 847 users, 600 devices, 12 hunt groups in 4 batches."
Neither document answers the question an SE actually needs to verify before pressing go: **"What
exactly will happen to User X?"**

Today, if an SE wants to check what a specific user will gain or lose, they have to:

1. Find the user in the SQLite store (`wxcli cucm inventory --type user`)
2. Find their device(s) via cross-references
3. Find their decisions (grep the decisions table for their canonical_id in context blobs)
4. Find their call forwarding rules in the call_forwarding objects
5. Find their voicemail profile
6. Find their device layout and BLF keys
7. Mentally assemble the CUCM state vs. planned Webex state
8. Identify the gaps

This is a 15-30 minute manual process per user. For a 500-user environment where the SE needs to
verify a representative sample (say 20 users), that's 5-10 hours of tedious cross-referencing.

The pipeline's SQLite store already contains all of this data in structured form. The normalizers
captured the CUCM state. The mappers produced the planned Webex state. The analyzers flagged the
gaps. We just need a report that joins these three views per user.

## Target Outcome

The SE runs:

```bash
wxcli cucm user-diff --format html
wxcli cucm user-diff --format csv
wxcli cucm user-diff --user "user:jsmith" --format html   # single user
```

The HTML output is a single page with an expandable section per user. Each section shows:

```
Jane Smith (jsmith@contoso.com) - ext. 1001
+------------------------------------------------------------------+
| Setting              | CUCM (Current)    | Webex (Planned)       |
|------------------------------------------------------------------+
| Phone Model          | Cisco 8851 (SIP)  | Cisco 8851 (MPP)      |
| Compatibility        | --                | Convertible (E2M)     |
| Extension            | 1001              | 1001                  |
| DID                  | +1-214-555-1001   | +1-214-555-1001       |
| Location             | DP-HQ-Phones      | HQ                    |
| Voicemail            | Enabled (Unity)   | Enabled (Webex VM)    |
|                      |                   | Greeting: RE-RECORD   |
| Fwd Always           | Off               | Off                   |
| Fwd Busy             | 1099 (VM)         | Voicemail             |
| Fwd No Answer        | 1099 (VM, 4 rings)| Voicemail (4 rings)   |
| Fwd Busy Internal    | 1099              | NOT MAPPED            |
| Fwd No Coverage      | 1099              | NOT MAPPED            |
| Shared Lines         | None              | None                  |
| BLF Keys             | 3 (all mapped)    | 3 monitoring members  |
| Speed Dials          | 5                 | 5                     |
| Unmapped Buttons     | 0                 | --                    |
| Calling Permissions  | CSS-Internal      | Internal + National   |
| Decisions            | D0012: FORWARDING_LOSSY (auto-resolved)  |
+------------------------------------------------------------------+
```

The CSV output provides the same data in a flat format for bulk review in Excel:
one row per user per setting category.

## Architecture

### Data Flow

```
SQLite store (post-analyze or post-plan)
    |
    +---> store.get_objects("user")         ──> user identity, extension, location
    +---> store.get_objects("device")       ──> device model, compatibility tier
    +---> store.get_objects("line")          ──> DNs, E.164, partitions
    +---> store.get_objects("call_forwarding") ──> per-user forwarding rules
    +---> store.get_objects("voicemail_profile") ──> VM config
    +---> store.get_objects("monitoring_list") ──> BLF/monitored members
    +---> store.get_objects("device_layout") ──> button layout, speed dials, unmapped
    +---> store.get_objects("shared_line")  ──> shared line memberships
    +---> store.get_objects("calling_permission") ──> outgoing call permissions
    +---> store.get_objects("phone")        ──> raw CUCM phone data (pre_migration_state)
    +---> store.get_all_decisions()         ──> decisions affecting each user
    +---> store.get_cross_refs(...)         ──> user-device, user-line, user-vm links
    |
    v
user_diff.py  ──joins per user──>  UserDiffRecord per user
    |
    v
HTML renderer  ──expandable sections──>  user-diff.html
CSV renderer   ──flat rows──>            user-diff.csv
```

### New Files

| File | Purpose |
|------|---------|
| `src/wxcli/migration/report/user_diff.py` | Per-user data join + diff rendering |
| `tests/migration/report/test_user_diff.py` | Tests for data join and output |

### CLI Integration

New command added to the `cucm` command group:

```python
@app.command()
def user_diff(
    format: str = typer.Option("html", help="Output format: html or csv"),
    user: str = typer.Option(None, help="Single user canonical_id (e.g., user:jsmith)"),
    output: Path = typer.Option(None, help="Output file path"),
    location: str = typer.Option(None, help="Filter to users in a specific location"),
    include_no_change: bool = typer.Option(
        False, help="Include users with no detected changes"
    ),
):
```

### Prerequisite

Requires `analyze` stage to be complete. Works better after `plan` (which resolves
decisions and sets planned state), but `analyze` is the minimum.

## Per-User Data Model

### `UserDiffRecord`

The core data structure that holds the CUCM vs. Webex comparison for one user:

```python
@dataclass
class UserDiffRecord:
    """Complete CUCM-vs-Webex diff for a single user."""
    # Identity
    canonical_id: str
    display_name: str
    email: str | None
    cucm_userid: str | None
    
    # Extension & Numbers
    extension: str | None
    did: str | None  # E.164 from line mapper
    extension_change: str  # "unchanged", "remapped", "conflict"
    
    # Location
    cucm_location: str | None  # device pool name
    webex_location: str | None  # mapped location name
    
    # Device
    cucm_device_model: str | None
    cucm_device_protocol: str | None  # SIP or SCCP
    webex_device_model: str | None  # same model if convertible/native
    device_tier: str | None  # native_mpp, convertible, webex_app, incompatible
    device_action: str  # "firmware_upgrade", "replace", "webex_app", "no_change"
    
    # Call Forwarding
    forwarding: ForwardingDiff | None
    
    # Voicemail
    cucm_voicemail: str | None  # "Enabled (Unity)" or "Disabled"
    webex_voicemail: str | None  # "Enabled (Webex VM)" or "Disabled"
    voicemail_greeting_action: str  # "re-record", "not_applicable"
    
    # BLF / Monitoring
    blf_count_cucm: int
    blf_count_webex: int
    blf_mapped: int
    blf_unmapped: int
    
    # Speed Dials
    speed_dial_count_cucm: int
    speed_dial_count_webex: int
    
    # Shared Lines
    shared_line_dns: list[str]  # DNs shared with this user
    shared_line_action: str  # "virtual_line", "shared_appearance", "none"
    
    # Button Layout
    total_buttons_cucm: int
    mapped_buttons_webex: int
    unmapped_buttons: list[str]  # descriptions of unmapped buttons
    
    # Calling Permissions
    cucm_css: str | None  # CSS name
    webex_permissions: str | None  # summary of mapped permissions
    
    # Decisions
    decisions: list[UserDecisionSummary]
    
    # Summary flags
    has_changes: bool  # True if anything differs
    change_categories: list[str]  # ["device", "forwarding", "voicemail", ...]


@dataclass
class ForwardingDiff:
    """Detailed call forwarding comparison."""
    rules: list[ForwardingRuleDiff]


@dataclass
class ForwardingRuleDiff:
    """Single forwarding rule comparison."""
    rule_type: str  # "always", "busy", "no_answer", "busy_internal", etc.
    cucm_enabled: bool
    cucm_destination: str | None
    webex_enabled: bool
    webex_destination: str | None
    status: str  # "mapped", "lossy", "not_mapped"


@dataclass
class UserDecisionSummary:
    """Compact decision summary for the diff table."""
    decision_id: str
    type: str
    severity: str
    summary: str
    resolution: str  # "auto-resolved: {option}" or "pending"
```

## Data Join Logic

### Building the Diff

The core function joins data from 10+ store queries:

```python
def build_user_diffs(
    store: MigrationStore,
    user_filter: str | None = None,
    location_filter: str | None = None,
) -> list[UserDiffRecord]:
    """Build per-user diff records from the store."""
    
    # 1. Load all relevant objects in bulk (avoid N+1 queries)
    users = store.get_objects("user")
    devices = store.get_objects("device")
    lines = store.get_objects("line")
    call_fwds = store.get_objects("call_forwarding")
    vm_profiles = store.get_objects("voicemail_profile")
    monitoring = store.get_objects("monitoring_list")
    layouts = store.get_objects("device_layout")
    shared_lines = store.get_objects("shared_line")
    permissions = store.get_objects("calling_permission")
    phones = store.get_objects("phone")  # raw CUCM data
    decisions = store.get_all_decisions()
    locations = store.get_objects("location")
    
    # 2. Build index maps for O(1) lookups
    device_by_owner = _index_by_field(devices, "owner_canonical_id")
    fwd_by_user = _index_by_field(call_fwds, "user_canonical_id")
    vm_by_user = _index_by_field(vm_profiles, "user_canonical_id")
    monitor_by_user = _index_by_field(monitoring, "user_canonical_id")
    layout_by_device = _index_by_field(layouts, "device_canonical_id")
    location_by_id = {loc["canonical_id"]: loc for loc in locations}
    phone_by_name = {p["canonical_id"]: p for p in phones}
    
    # 3. Index decisions by affected user
    decisions_by_user = _index_decisions_by_user(decisions)
    
    # 4. Index shared lines by member
    shared_by_user = _index_shared_lines_by_user(shared_lines)
    
    # 5. Index calling permissions by assigned user
    perms_by_user = _index_permissions_by_user(permissions)
    
    # 6. Apply filters
    if user_filter:
        users = [u for u in users if u["canonical_id"] == user_filter]
    if location_filter:
        users = [u for u in users if u.get("location_id") == location_filter]
    
    # 7. Build diff record for each user
    results = []
    for user in users:
        record = _build_single_user_diff(
            user, device_by_owner, fwd_by_user, vm_by_user,
            monitor_by_user, layout_by_device, location_by_id,
            phone_by_name, decisions_by_user, shared_by_user,
            perms_by_user,
        )
        results.append(record)
    
    # 8. Sort by display name
    results.sort(key=lambda r: (r.display_name or "").lower())
    
    return results
```

### Key Join Patterns

**User to Device:**
The device's `owner_canonical_id` field points to the user's `canonical_id`.
A user may have 0 or more devices. For the diff, we use the primary device
(first device found, or the one with the most line appearances).

**User to Call Forwarding:**
`CanonicalCallForwarding.user_canonical_id` directly references the user.
One forwarding object per user.

**User to Voicemail:**
`CanonicalVoicemailProfile.user_canonical_id` directly references the user.
One VM profile per user.

**User to Monitoring (BLF):**
`CanonicalMonitoringList.user_canonical_id` directly references the user.
One monitoring list per user, containing `monitored_members` list.

**User to Device Layout:**
Indirect join: User -> Device (via `owner_canonical_id`) -> Layout (via `device_canonical_id`).
The layout contains `resolved_line_keys`, `speed_dials`, and `unmapped_buttons`.

**User to Shared Lines:**
`CanonicalSharedLine.owner_canonical_ids` is a list that may contain the user's canonical_id.

**User to Calling Permissions:**
`CanonicalCallingPermission.assigned_users` is a list that may contain the user's canonical_id.
Also join via CSS cross-refs: `user_has_css` -> `css_has_partition` to show the CUCM CSS name.

**User to Decisions:**
Decisions reference users through their `context` dict. The indexer checks for keys
`user_canonical_id`, `affected_user`, `owner_canonical_id`, and `affected_objects`.

## CUCM vs. Webex State Mapping

For each diff category, the report shows what the user has in CUCM and what they'll
have in Webex. The "CUCM" column comes from the normalized object's
`pre_migration_state` or CUCM-prefixed fields. The "Webex" column comes from the
mapped canonical fields (which represent the planned Webex state).

### Device

| CUCM Field | Source | Webex Field | Source |
|------------|--------|-------------|--------|
| Model | `device.model` or `phone.pre_migration_state.model` | Model | Same (native/convertible) or "Webex App" or "New device TBD" |
| Protocol | `device.cucm_protocol` | Protocol | "SIP" (all Webex devices are SIP) |
| MAC | `device.mac` | MAC | Same (if convertible/native) |
| Name | `device.cucm_device_name` | -- | Not relevant in Webex |

### Call Forwarding

| CUCM Field | Source | Webex Field | Source |
|------------|--------|-------------|--------|
| Fwd Always | `call_forwarding.always_enabled/destination` | Fwd Always | Same fields (if mapped) |
| Fwd Busy | `call_forwarding.busy_enabled/destination` | Fwd Busy | Same fields |
| Fwd No Answer | `call_forwarding.no_answer_enabled/destination/ring_count` | Fwd No Answer | Same fields |
| Fwd Busy Internal | `call_forwarding.busy_internal_enabled/destination` | -- | NOT MAPPED (Webex doesn't support) |
| Fwd No Coverage | `call_forwarding.no_coverage_enabled/destination` | -- | NOT MAPPED |
| Fwd On Failure | `call_forwarding.on_failure_enabled/destination` | -- | NOT MAPPED |
| Fwd Not Registered | `call_forwarding.not_registered_enabled/destination` | -- | NOT MAPPED |

Rules marked "NOT MAPPED" are where CUCM has forwarding types that Webex Calling
doesn't support. These appear in `FORWARDING_LOSSY` decisions.

### Voicemail

| CUCM | Webex | Notes |
|------|-------|-------|
| Enabled (Unity Connection) | Enabled (Webex VM) | Settings migrated, greeting requires re-record |
| Disabled | Disabled | No action |
| Message Waiting Indicator | Yes | Preserved on MPP phones |
| Voicemail-to-Email | Configured per profile | Mapped if email available |

### BLF / Monitoring

CUCM BLF entries (from `busyLampFields` on the raw phone object) map to Webex
monitoring list members. The diff shows:

- Total BLF count in CUCM vs. mapped monitoring members in Webex
- Unmapped BLFs (those targeting DNs not in the migration scope)

### Speed Dials

From the `device_layout.speed_dials` list. Shows count and any that couldn't map.

### Button Layout

Summarizes the full button template comparison:
- Total CUCM buttons (from button template + per-device overrides)
- Mapped Webex line keys
- Unmapped buttons with descriptions (e.g., "Privacy button", "Park button")

## HTML Output

### Page Structure

```html
<!DOCTYPE html>
<html>
<head>
    <title>Per-User Migration Diff -- {brand}</title>
    <style>/* inline CSS */</style>
</head>
<body>
    <header>
        <h1>Per-User Migration Diff</h1>
        <p>Generated {date} | {user_count} users | {location_count} locations</p>
    </header>
    
    <div class="summary-bar">
        <div class="stat">Users with changes: {change_count}</div>
        <div class="stat">Users with no changes: {no_change_count}</div>
        <div class="stat">Pending decisions: {pending_count}</div>
    </div>
    
    <div class="filter-bar">
        <input type="text" id="search" placeholder="Search by name or extension...">
        <select id="filter-category">
            <option value="all">All Users</option>
            <option value="device">Device Changes</option>
            <option value="forwarding">Forwarding Changes</option>
            <option value="voicemail">Voicemail Changes</option>
            <option value="decisions">Has Decisions</option>
        </select>
    </div>
    
    <!-- Per-user sections -->
    <details class="user-diff" data-categories="device,voicemail">
        <summary>
            <strong>Jane Smith</strong> (jsmith@contoso.com) -- ext. 1001
            <span class="badge warning">2 changes</span>
        </summary>
        <table class="diff-table">
            <thead>
                <tr><th>Setting</th><th>CUCM (Current)</th><th>Webex (Planned)</th></tr>
            </thead>
            <tbody>
                <tr><td>Phone Model</td><td>Cisco 8851 (SIP)</td><td>Cisco 8851 (MPP)</td></tr>
                <!-- ... -->
            </tbody>
        </table>
        <div class="decisions-section">
            <h4>Decisions</h4>
            <ul>
                <li>D0012: FORWARDING_LOSSY -- auto-resolved: accept_lossy</li>
            </ul>
        </div>
    </details>
    
    <!-- Repeat for each user -->
    
    <script>/* search/filter JS */</script>
</body>
</html>
```

### Interactive Features

The HTML output includes minimal JavaScript for usability:

1. **Text search:** Filters visible user sections by name, email, or extension.
2. **Category filter:** Dropdown to show only users with specific change types.
3. **Expand/collapse all:** Button to open or close all `<details>` elements.
4. **Summary counts:** Updates dynamically as filters are applied.

These are progressive enhancements -- the document is fully readable without JavaScript
(all `<details>` elements work natively).

### Styling

Uses the same design language as the assessment report (teal accent, warm neutrals,
Lora/Source Sans fonts) but in a more compact table-oriented layout.

```css
.user-diff {
    border: 1px solid var(--warm-200);
    border-radius: 4px;
    margin: 8px 0;
}
.user-diff summary {
    padding: 12px 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 12px;
}
.user-diff[open] summary {
    border-bottom: 1px solid var(--warm-200);
    background: var(--warm-50);
}
.diff-table {
    width: 100%;
    border-collapse: collapse;
}
.diff-table th {
    text-align: left;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    color: var(--slate-500);
    padding: 8px 12px;
    border-bottom: 2px solid var(--warm-200);
}
.diff-table td {
    padding: 6px 12px;
    border-bottom: 1px solid var(--warm-100);
}
.diff-table .not-mapped {
    color: #C62828;
    font-style: italic;
}
.diff-table .unchanged {
    color: var(--slate-400);
}
.diff-table .changed {
    color: #EF6C00;
    font-weight: 600;
}
```

### Diff Highlighting

Table cells use color coding to highlight changes:

| Status | Color | Example |
|--------|-------|---------|
| Unchanged | Gray (slate-400) | Extension: 1001 -> 1001 |
| Changed | Orange (#EF6C00) | Protocol: SCCP -> SIP |
| Not Mapped | Red (#C62828, italic) | Fwd Busy Internal: NOT MAPPED |
| New | Green (#2E7D32) | Voicemail-to-Email: Configured |
| Action Required | Teal badge | Greeting: RE-RECORD |

## CSV Output

### Format

One row per user per setting category. Designed for Excel/Google Sheets review.

```csv
User,Email,Extension,Category,CUCM_Value,Webex_Value,Status,Decision_ID
Jane Smith,jsmith@contoso.com,1001,Phone Model,"Cisco 8851 (SIP)","Cisco 8851 (MPP)",changed,
Jane Smith,jsmith@contoso.com,1001,Compatibility,--,"Convertible (E2M)",new,
Jane Smith,jsmith@contoso.com,1001,Extension,1001,1001,unchanged,
Jane Smith,jsmith@contoso.com,1001,DID,+1-214-555-1001,+1-214-555-1001,unchanged,
Jane Smith,jsmith@contoso.com,1001,Location,DP-HQ-Phones,HQ,changed,
Jane Smith,jsmith@contoso.com,1001,Voicemail,"Enabled (Unity)","Enabled (Webex VM)",changed,
Jane Smith,jsmith@contoso.com,1001,Voicemail Greeting,--,RE-RECORD,action_required,
Jane Smith,jsmith@contoso.com,1001,Fwd Busy,"1099 (VM)",Voicemail,mapped,
Jane Smith,jsmith@contoso.com,1001,Fwd Busy Internal,1099,NOT MAPPED,not_mapped,D0012
Jane Smith,jsmith@contoso.com,1001,BLF Keys,3,3,unchanged,
Jane Smith,jsmith@contoso.com,1001,Speed Dials,5,5,unchanged,
```

### CSV Renderer

```python
def render_csv(records: list[UserDiffRecord]) -> str:
    """Render diff records as CSV."""
    rows = [["User", "Email", "Extension", "Category",
             "CUCM_Value", "Webex_Value", "Status", "Decision_ID"]]
    
    for r in records:
        base = [r.display_name, r.email or "", r.extension or ""]
        
        # Device
        rows.append(base + [
            "Phone Model",
            f"{r.cucm_device_model} ({r.cucm_device_protocol})" if r.cucm_device_model else "",
            r.webex_device_model or "",
            "changed" if r.cucm_device_model != r.webex_device_model else "unchanged",
            "",
        ])
        
        # Extension
        rows.append(base + [
            "Extension", r.extension or "", r.extension or "",
            r.extension_change, "",
        ])
        
        # ... similar for each category
        
        # Forwarding rules
        if r.forwarding:
            for rule in r.forwarding.rules:
                rows.append(base + [
                    f"Fwd {rule.rule_type.replace('_', ' ').title()}",
                    rule.cucm_destination or ("Enabled" if rule.cucm_enabled else "Off"),
                    rule.webex_destination or ("Enabled" if rule.webex_enabled else "Off"
                        if rule.status != "not_mapped" else "NOT MAPPED"),
                    rule.status,
                    "",  # decision_id filled from decisions list
                ])
        
        # Decisions
        for dec in r.decisions:
            rows.append(base + [
                f"Decision: {dec.type}",
                dec.summary,
                dec.resolution,
                dec.severity.lower(),
                dec.decision_id,
            ])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()
```

## Performance Considerations

For large environments (1000+ users), the diff generator must be efficient:

1. **Bulk load, then index.** All `store.get_objects()` calls happen upfront.
   No per-user queries. The index maps give O(1) lookup per user.

2. **Lazy HTML rendering.** The `<details>` elements in HTML are collapsed by default.
   Browsers don't render collapsed content, so even 1000+ user sections load fast.

3. **CSV streaming.** For very large environments, the CSV renderer writes row-by-row
   to avoid holding the entire output in memory.

4. **Location filter.** The `--location` flag reduces the working set to a single site,
   which is the common use case for pre-migration verification.

## Documentation Updates Required

1. **`src/wxcli/migration/report/CLAUDE.md`** -- Add `user_diff.py` to the file table.
   Add a "Per-User Diff" section describing the data join pattern and output formats.

2. **`CLAUDE.md` (project root)** -- Add `wxcli cucm user-diff` to the Pipeline Commands
   section. Note that it reads from the post-analyze store.

3. **`src/wxcli/migration/CLAUDE.md`** -- Add `user-diff` to the CLI commands list
   (currently 13 commands, becomes 14 -- or 15 if user-notice is also added).

4. **`docs/runbooks/cucm-migration/operator-runbook.md`** -- Add a section on generating
   per-user diffs as a pre-execution verification step.

## Test Plan

### Unit Tests (`test_user_diff.py`)

1. **Data join correctness:** Populate a store with known users, devices, forwarding rules,
   voicemail profiles, monitoring lists, layouts, and decisions. Verify the `UserDiffRecord`
   for each user contains the expected values.

2. **Device join:** User with a device -> verify model, tier, protocol are populated.
   User without a device -> verify device fields are None.

3. **Forwarding diff:** User with CUCM forwarding rules that partially map to Webex.
   Verify mapped rules show "mapped", unmapped rules show "not_mapped".

4. **Voicemail diff:** User with Unity VM -> verify "Enabled (Unity)" / "Enabled (Webex VM)"
   and greeting action "re-record". User without VM -> verify "Disabled".

5. **BLF/monitoring diff:** User with 5 BLFs, 3 mapped -> verify counts.

6. **Shared line join:** User on a shared DN -> verify shared_line_dns populated.

7. **Decision association:** User referenced in 2 decisions -> verify both appear in record.

8. **Single user filter:** `--user user:jsmith` produces only one record.

9. **Location filter:** `--location location:HQ` produces only users in that location.

10. **HTML output structure:** Verify output has `<details>` per user, `<table>` with
    expected columns, badge counts.

11. **CSV output structure:** Verify header row and correct column count per data row.

12. **Empty store:** Graceful handling when no users exist.

13. **No-change users:** When `include_no_change=False` (default), users with zero
    differences are excluded. When True, they appear with "unchanged" status.

### Integration Test

14. **CLI integration:** Run `wxcli cucm user-diff` against the test fixture store.
    Verify exit code 0 and output file creation.

15. **Round-trip with assessment report fixture:** The `populated_store` fixture from
    `conftest.py` has 50 users and 45 devices. Verify the diff produces records for
    all 50 users with reasonable device joins.

## Success Criteria

- SE can generate a per-user diff in < 10 seconds for 1000 users
- Every user in the store appears in the output (unless filtered)
- Each diff row has both CUCM and Webex columns populated (or explicitly marked as N/A)
- Forwarding rules that don't map to Webex are clearly flagged as NOT MAPPED
- Decisions affecting a user appear in that user's section
- HTML is self-contained (no external dependencies) and viewable in any browser
- CSV is importable into Excel without encoding issues (UTF-8 BOM)
- `--user` flag allows single-user lookup without scanning the entire store output

## Open Questions

1. **Include workspace users?** Common-area phones have no human user -- should they
   appear in the diff? Proposal: Include them with a "Workspace" badge, showing the
   device and extension mapping. They don't have forwarding/VM/BLF but do have device
   tier and location.

2. **Diff against post-plan vs. post-analyze?** After `plan`, decisions are resolved
   and the planned state is more concrete. After `analyze`, some decisions may still be
   pending. The diff should work at both stages but indicate when decisions are unresolved
   (showing "pending" instead of the resolved option).

3. **Historical comparison?** If the pipeline is re-run (e.g., after a CUCM config change),
   should we support diffing two pipeline runs? Deferred -- this is a v2 feature. The current
   scope compares CUCM state vs. Webex planned state within a single run.

4. **Companion to user-notice?** The per-user diff is an SE verification tool. The
   user-notice is a user communication tool. They share scenario detection logic. Consider
   extracting shared helpers into a common module if both are implemented.
