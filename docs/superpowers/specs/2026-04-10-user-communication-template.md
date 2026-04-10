# User Communication Template Generator -- Design Spec

**Date:** 2026-04-10
**Author:** Adam Hobgood
**Status:** Draft

---

## Problem Statement

The CUCM migration pipeline produces rich technical analysis -- decision types, device compatibility
tiers, call forwarding loss detection, voicemail mapping, BLF changes -- but all of this lives in the
assessment report and deployment plan. Neither document is user-facing. Neither document answers the
question an end user cares about: "What is happening to my phone?"

Today, every SE writes a user communication email from scratch before migration day. They manually
cross-reference the assessment report to figure out which users are affected by which changes, then
compose paragraphs explaining what's happening. This takes 1-3 hours per migration and the quality
varies wildly. Some SEs send a single vague "your phone system is changing" email to everyone. Others
write detailed per-scenario notices but miss edge cases because the assessment report is organized by
decision type, not by user impact.

The pipeline already has the data to generate this communication automatically. We know which users
have convertible devices. We know which users have lossy call forwarding rules. We know which users
have voicemail. We know which users have BLF keys that need adjustment. The missing piece is a
generator that reads the store, segments users by scenario, and produces a branded, customizable
communication document.

## Target Outcome

After running `wxcli cucm analyze`, the SE runs:

```bash
wxcli cucm user-notice \
  --brand "Contoso" \
  --migration-date "January 15, 2027" \
  --helpdesk "IT Help Desk at ext. 5000 or helpdesk@contoso.com" \
  --prepared-by "Jane Smith, Cisco Partner SE"
```

This produces an HTML document containing:

1. A **generic intro section** ("We're upgrading your phone system from CUCM to Webex Calling")
2. **Scenario-specific sections** -- only the ones that apply to this environment
3. A **what to expect on migration day** timeline
4. A **where to get help** footer with the helpdesk contact

The SE reviews the generated document, makes any edits they want, and sends it to end users.

For larger environments with mixed scenarios, the SE can also generate **per-audience variants**:
one notice for users whose phones are being upgraded, a different notice for users switching to
Webex App, etc. The generator handles the audience segmentation; the SE just picks which variants
to send.

## Architecture

### Data Flow

```
SQLite store (post-analyze)
    |
    v
user_notice.py  ──reads──>  store.get_objects("user")
                             store.get_objects("device")
                             store.get_all_decisions()
                             store.get_cross_refs(...)
    |
    v
Scenario detection  ──matches users to scenarios──>
    |
    v
Template assembly  ──picks paragraphs per scenario──>
    |
    v
HTML/text output  ──branded, customizable──>  user-notice.html
                                               user-notice.txt (plain text)
```

### New Files

| File | Purpose |
|------|---------|
| `src/wxcli/migration/report/user_notice.py` | Scenario detection + template assembly |
| `src/wxcli/migration/report/notice_templates.py` | Pre-written paragraph templates per scenario |
| `tests/migration/report/test_user_notice.py` | Tests for scenario detection and output |

### CLI Integration

New command added to the `cucm` command group:

```python
# In src/wxcli/commands/cucm.py
@app.command()
def user_notice(
    brand: str = typer.Option(..., help="Company/organization name"),
    migration_date: str = typer.Option(..., help="Planned migration date (free text)"),
    helpdesk: str = typer.Option(..., help="Helpdesk contact info"),
    prepared_by: str = typer.Option("", help="SE name for footer attribution"),
    output: Path = typer.Option(None, help="Output file path (default: user-notice.html)"),
    text_only: bool = typer.Option(False, help="Generate plain text instead of HTML"),
    audience: str = typer.Option(
        "all",
        help="Target audience: all, phone-upgrade, webex-app, general"
    ),
):
```

### Prerequisite

Requires `analyze` stage to be complete. Does NOT require `plan`, `preflight`, or `export`.
Same prerequisite as the assessment report.

## Scenario Detection

The generator scans the store and classifies each user into one or more communication scenarios.
A user can match multiple scenarios (e.g., phone upgrade AND voicemail re-record).

### Scenario 1: Phone Model Upgrade (convertible devices)

**Detection logic:**
```python
devices = store.get_objects("device")
convertible_devices = [d for d in devices if d.get("compatibility_tier") == "convertible"]
# Get owners via cross-ref
for device in convertible_devices:
    owner_refs = store.get_cross_refs(from_id=device["canonical_id"], relationship="device_owner")
```

**Affected users:** Users whose primary device has `compatibility_tier == "convertible"`.

**Template paragraph:**
> Your desk phone ({cucm_model}) will be upgraded to run Webex Calling firmware. This is a
> remote firmware update -- you do not need to do anything. Your phone will restart once during
> the migration window. After the restart, your phone will look slightly different (new menus
> and icons), but your extension ({extension}), speed dials, and call behavior will continue
> to work. The upgrade typically takes 5-10 minutes.

**Variables:** `{cucm_model}`, `{extension}`, `{brand}`

### Scenario 2: Transition to Webex App (webex_app devices)

**Detection logic:**
```python
webex_app_devices = [d for d in devices if d.get("compatibility_tier") == "webex_app"]
```

**Affected users:** Users whose device is a Jabber soft client or other `webex_app` tier device.

**Template paragraph:**
> You currently use Cisco Jabber for voice calls. After migration, you'll use the **Webex App**
> instead. The Webex App provides the same calling features you use today -- plus messaging,
> meetings, and screen sharing in one application. Your IT team will install Webex App on your
> computer before migration day. Your extension ({extension}) and phone number will not change.
>
> **What you need to do:** Sign in to the Webex App when prompted by your IT team. Your call
> history will not transfer, but all other settings (forwarding, voicemail, etc.) will be
> configured automatically.

**Variables:** `{extension}`, `{brand}`

### Scenario 3: Call Forwarding Simplified (FORWARDING_LOSSY decisions)

**Detection logic:**
```python
decisions = store.get_all_decisions()
forwarding_decisions = [
    d for d in decisions
    if d["type"] == "FORWARDING_LOSSY"
]
# Extract affected user canonical_ids from decision context
```

**Affected users:** Users with FORWARDING_LOSSY decisions.

**Template paragraph:**
> Your call forwarding rules have been reviewed and simplified for the new system. CUCM
> supported some forwarding configurations that Webex Calling handles differently. Your IT
> team has reviewed your specific setup and will configure the closest equivalent. If you
> had complex forwarding chains (e.g., forward to a queue that forwards to voicemail after
> hours), please verify your forwarding settings after migration using the Webex App or
> your desk phone's settings menu.
>
> **What you need to do:** After migration, dial a test call to verify your forwarding
> works as expected. If anything needs adjustment, contact {helpdesk}.

**Variables:** `{helpdesk}`

### Scenario 4: Voicemail Greeting Re-record (all users with VM)

**Detection logic:**
```python
vm_profiles = store.get_objects("voicemail_profile")
# Users linked via user_has_voicemail_profile cross-ref or
# voicemail_profile.user_canonical_id field
```

**Affected users:** All users who have a voicemail profile in the store.

**Template paragraph:**
> Your voicemail account will be migrated to Webex Calling voicemail. Your voicemail-to-email
> settings will be preserved. However, **your personal voicemail greeting cannot be migrated
> automatically** -- the old greeting is stored in Cisco Unity Connection in a format that
> doesn't transfer to Webex.
>
> **What you need to do:** After migration, record a new voicemail greeting. You can do this by:
> 1. Dialing your voicemail access number and following the prompts
> 2. Using the Webex App: Settings > Calling > Voicemail > Greeting
>
> Until you record a new greeting, callers will hear the default system greeting.

**Variables:** none (self-contained)

### Scenario 5: Speed Dials and BLF Key Changes (layout changes)

**Detection logic:**
```python
layout_decisions = [
    d for d in decisions
    if d["type"] in ("BUTTON_UNMAPPABLE", "FEATURE_APPROXIMATION")
    and "button" in d.get("summary", "").lower() or "blf" in d.get("summary", "").lower()
]
# Also check device layouts with unmapped_buttons
layouts = store.get_objects("device_layout")
affected_layouts = [l for l in layouts if l.get("unmapped_buttons")]
```

**Affected users:** Users whose devices have unmapped buttons or layout-related decisions.

**Template paragraph:**
> Your phone's button layout (speed dials and BLF busy lamp indicators) may look different
> after migration. Most of your speed dials and BLF keys will transfer automatically, but
> some button types that were available in CUCM don't have a direct equivalent in Webex
> Calling.
>
> **What you need to do:** After migration, review your phone's line keys and speed dials.
> You can reconfigure them using:
> - The Webex App: Settings > Calling > Line Key Configuration
> - Your phone's on-screen menu (varies by model)
> - Contact {helpdesk} for assistance
>
> Your IT team will provide a reference of your current button layout if needed.

**Variables:** `{helpdesk}`

### Scenario 6: Executive/Assistant Line Pickup

**Detection logic:**
```python
# Check for exec/assistant cross-refs or features
exec_decisions = [
    d for d in decisions
    if d["type"] == "FEATURE_APPROXIMATION"
    and "executive" in d.get("summary", "").lower()
    or "assistant" in d.get("summary", "").lower()
]
```

**Affected users:** Users involved in executive/assistant relationships.

**Template paragraph:**
> Your executive/assistant call handling will continue to work after migration. Webex Calling
> supports executive/assistant call filtering, with your assistant able to answer, screen, and
> transfer calls on your behalf. The configuration will be migrated automatically.
>
> **Note:** If you currently use the Cisco Unified Attendant Console, your assistant may need
> to use the Webex Receptionist Client instead. Your IT team will provide training before
> migration day.

**Variables:** none

### Scenario 7: Incompatible Device Replacement

**Detection logic:**
```python
incompatible_devices = [d for d in devices if d.get("compatibility_tier") == "incompatible"]
```

**Affected users:** Users whose device is incompatible and requires hardware replacement.

**Template paragraph:**
> Your current desk phone ({cucm_model}) is not compatible with Webex Calling and will be
> replaced with a new phone. Your IT team will coordinate the swap -- you'll receive a new
> phone at your desk before or on migration day. Your extension ({extension}) and phone
> number will not change.
>
> **What you need to do:** When your new phone arrives, it will already be configured with
> your line and basic settings. You may want to:
> - Reconfigure your speed dials and personal ring settings
> - Set your preferred display brightness and ringtone
> - Contact {helpdesk} if you need help with the new phone's features

**Variables:** `{cucm_model}`, `{extension}`, `{helpdesk}`

### Generic Sections (Always Included)

#### Introduction

> **Your phone system is being upgraded**
>
> {brand} is upgrading from Cisco Unified Communications Manager (CUCM) to Webex Calling.
> This upgrade brings a modern, cloud-managed phone system with the same reliability you
> expect, plus new features like the Webex App for calling, messaging, and meetings from
> any device.
>
> **Migration date:** {migration_date}
>
> Below is a summary of what this means for you specifically, based on your current phone
> and settings.

#### Migration Day Timeline

> **What to expect on {migration_date}:**
>
> - **Before the migration window:** Everything works normally. No action needed.
> - **During the migration window:** Your phone may restart once. Calls will not be
>   available for 5-15 minutes during this restart.
> - **After migration:** Your phone (or Webex App) will be operational on the new system.
>   Your extension and phone number are unchanged. Test a call to verify.
>
> If you experience any issues after migration, contact {helpdesk}.

#### Where to Get Help

> **Questions or issues?**
>
> Contact {helpdesk} for assistance with any migration-related questions.
>
> Additional resources:
> - Webex App quick start guide: [help.webex.com/getting-started](https://help.webex.com)
> - Voicemail setup: [help.webex.com/voicemail](https://help.webex.com)
>
> *Prepared by {prepared_by} on behalf of {brand}.*

## Template Assembly Logic

### User-Scenario Matrix

The generator builds an internal matrix mapping each user to their applicable scenarios:

```python
@dataclass
class UserScenario:
    user_canonical_id: str
    display_name: str
    extension: str | None
    scenarios: list[str]  # ["phone_upgrade", "voicemail_rerecord", ...]
    device_model: str | None
    device_tier: str | None
```

### Document Assembly

For the "all" audience (default), the generator produces a single document with all
applicable scenario sections. Sections with zero affected users are omitted entirely.

```python
def generate_user_notice(
    store: MigrationStore,
    brand: str,
    migration_date: str,
    helpdesk: str,
    prepared_by: str = "",
    audience: str = "all",
) -> str:
    """Generate user-facing migration communication document."""
    # 1. Build user-scenario matrix
    matrix = _build_scenario_matrix(store)
    
    # 2. Filter by audience if specified
    if audience != "all":
        matrix = _filter_by_audience(matrix, audience)
    
    # 3. Determine which scenario sections to include
    active_scenarios = _get_active_scenarios(matrix)
    
    # 4. Assemble document
    sections = [_render_intro(brand, migration_date)]
    for scenario_id in SCENARIO_ORDER:
        if scenario_id in active_scenarios:
            affected_count = sum(1 for u in matrix if scenario_id in u.scenarios)
            sections.append(_render_scenario(
                scenario_id, affected_count, brand, helpdesk
            ))
    sections.append(_render_timeline(migration_date, helpdesk))
    sections.append(_render_footer(helpdesk, prepared_by, brand))
    
    return "\n\n".join(sections)
```

### Audience Segmentation

The `--audience` flag filters the output to a specific user segment:

| Audience | Filter | Use Case |
|----------|--------|----------|
| `all` | No filter | Single notice to all users |
| `phone-upgrade` | Users with convertible or incompatible devices | Targeted notice for device changes |
| `webex-app` | Users transitioning from Jabber/softphone | Targeted notice for software transition |
| `general` | Users with no device changes | "Nothing changes for you" reassurance |

### Affected User Counts

Each scenario section includes a count of affected users. This helps the SE gauge
the communication's reach and decide whether to split into multiple notices:

> **Applies to {count} users** in your organization.

## Output Formats

### HTML

Primary output. Uses a simplified version of the assessment report's CSS (from `styles.py`)
but with a more "email-friendly" layout:

- Single column, max-width 640px (email-safe)
- System fonts (no Google Fonts dependency -- email clients strip external fonts)
- Inline CSS (email clients strip `<style>` blocks in some cases)
- No sidebar, no navigation, no interactive elements
- Print-friendly (no page breaks needed -- it's a single continuous document)

The HTML is designed to be:
1. Viewable directly in a browser
2. Copy-pastable into an email client
3. Convertible to PDF if needed

### Plain Text

Optional output via `--text-only`. Strips all HTML, preserves headings with underlines,
preserves bullet lists. For SEs who prefer to paste into plain-text email.

## Customization Points

| Parameter | Type | Description |
|-----------|------|-------------|
| `brand` | Required | Company name -- appears throughout |
| `migration_date` | Required | Free-text date string ("January 15, 2027", "Q1 2027", etc.) |
| `helpdesk` | Required | Contact info -- can be email, phone, URL, or free text |
| `prepared_by` | Optional | SE attribution in footer |
| `audience` | Optional | Filter to specific user segment |
| `output` | Optional | Output file path |
| `text_only` | Optional | Plain text instead of HTML |

### Post-Generation Editing

The generated HTML is intentionally simple and hand-editable. SEs can:
- Add/remove sections
- Edit paragraph text
- Add company logo (insert `<img>` tag)
- Adjust formatting

The generator does NOT try to produce a pixel-perfect final product. It produces a
solid first draft that covers all the technical scenarios, which the SE then customizes
for tone and branding.

## Scenario Detection Implementation

### `notice_templates.py`

Contains the template strings and scenario metadata:

```python
SCENARIOS = {
    "phone_upgrade": {
        "title": "Your Phone Is Being Upgraded",
        "icon": "phone",
        "priority": 1,  # display order
        "template": "...",  # the paragraph text with {variables}
        "variables": ["cucm_model", "extension", "brand"],
    },
    "webex_app_transition": {
        "title": "You'll Use Webex App Instead of Jabber",
        "icon": "app",
        "priority": 2,
        "template": "...",
        "variables": ["extension", "brand"],
    },
    # ... etc for all 7 scenarios
}
```

### `user_notice.py`

Contains the detection logic and assembly:

```python
def _build_scenario_matrix(store: MigrationStore) -> list[UserScenario]:
    """Scan store and classify each user into applicable scenarios."""
    users = store.get_objects("user")
    devices = store.get_objects("device")
    decisions = store.get_all_decisions()
    vm_profiles = store.get_objects("voicemail_profile")
    layouts = store.get_objects("device_layout")
    
    # Build lookup: user_canonical_id -> device
    device_by_owner = {}
    for d in devices:
        owner = d.get("owner_canonical_id")
        if owner:
            device_by_owner[owner] = d
    
    # Build lookup: user_canonical_id -> decisions
    decisions_by_user = defaultdict(list)
    for dec in decisions:
        ctx = dec.get("context", {})
        for key in ("user_canonical_id", "affected_user", "owner_canonical_id"):
            if key in ctx:
                decisions_by_user[ctx[key]].append(dec)
    
    # Build lookup: user_canonical_id -> voicemail
    vm_by_user = {}
    for vm in vm_profiles:
        uid = vm.get("user_canonical_id")
        if uid:
            vm_by_user[uid] = vm
    
    # Classify each user
    result = []
    for user in users:
        uid = user["canonical_id"]
        scenarios = []
        device = device_by_owner.get(uid)
        
        # Scenario 1: Phone upgrade
        if device and device.get("compatibility_tier") == "convertible":
            scenarios.append("phone_upgrade")
        
        # Scenario 2: Webex App transition
        if device and device.get("compatibility_tier") == "webex_app":
            scenarios.append("webex_app_transition")
        
        # Scenario 3: Call forwarding simplified
        user_decisions = decisions_by_user.get(uid, [])
        if any(d["type"] == "FORWARDING_LOSSY" for d in user_decisions):
            scenarios.append("forwarding_simplified")
        
        # Scenario 4: Voicemail re-record
        if uid in vm_by_user:
            scenarios.append("voicemail_rerecord")
        
        # Scenario 5: BLF/speed dial changes
        if any(d["type"] in ("BUTTON_UNMAPPABLE", "FEATURE_APPROXIMATION")
               for d in user_decisions):
            scenarios.append("layout_changes")
        
        # Scenario 6: Exec/assistant
        if any("executive" in d.get("summary", "").lower()
               or "assistant" in d.get("summary", "").lower()
               for d in user_decisions):
            scenarios.append("exec_assistant")
        
        # Scenario 7: Incompatible device
        if device and device.get("compatibility_tier") == "incompatible":
            scenarios.append("device_replacement")
        
        result.append(UserScenario(
            user_canonical_id=uid,
            display_name=user.get("display_name", ""),
            extension=user.get("extension"),
            scenarios=scenarios,
            device_model=device.get("model") if device else None,
            device_tier=device.get("compatibility_tier") if device else None,
        ))
    
    return result
```

## Styling

The notice uses a minimal, email-safe CSS approach:

- **No external dependencies.** No Google Fonts, no external stylesheets.
- **Inline-safe.** All styles can be inlined for email delivery.
- **Brand color:** Uses teal (#00897B) as accent color, matching the assessment report.
- **Layout:** Single column, 640px max-width, generous padding.
- **Typography:** System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).

### Section Styling

Each scenario section gets a left-border accent and light background, similar to
the assessment report's effort bands:

```css
.scenario-section {
    border-left: 4px solid #00897B;
    background: #f8faf9;
    padding: 16px 20px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
}
.scenario-section h3 {
    margin-top: 0;
    color: #242a33;
}
.action-item {
    background: #fff;
    border: 1px solid #e0e0e0;
    padding: 12px 16px;
    border-radius: 4px;
    margin-top: 12px;
}
.action-item strong {
    color: #00897B;
}
```

## Documentation Updates Required

1. **`src/wxcli/migration/report/CLAUDE.md`** -- Add `user_notice.py` and `notice_templates.py`
   to the file table. Add a "User Communication" section describing the generator.

2. **`CLAUDE.md` (project root)** -- Add `wxcli cucm user-notice` to the Pipeline Commands
   section with a brief description.

3. **`src/wxcli/migration/CLAUDE.md`** -- Add `user-notice` to the CLI commands list
   (currently 13 commands, becomes 14).

4. **`docs/runbooks/cucm-migration/operator-runbook.md`** -- Add a section on generating
   user communications as a post-analysis step.

## Test Plan

### Unit Tests (`test_user_notice.py`)

1. **Scenario detection:** Populate a store with known user/device/decision combinations.
   Verify each scenario is detected correctly.
2. **Scenario exclusion:** Verify scenarios with zero affected users are omitted from output.
3. **Audience filtering:** Verify `--audience phone-upgrade` only includes phone upgrade content.
4. **Template rendering:** Verify variables are substituted correctly in all templates.
5. **HTML output:** Verify output is valid HTML with expected structure.
6. **Plain text output:** Verify `--text-only` produces readable plain text.
7. **Empty store:** Verify graceful handling when store has no users.
8. **Multi-scenario users:** Verify users appearing in multiple scenarios get all relevant sections.

### Integration Test

9. **CLI integration:** Run `wxcli cucm user-notice` against the test fixture store
   (from `conftest.py`'s `populated_store`). Verify the command exits 0 and produces output.

## Success Criteria

- SE can generate a user communication in < 5 seconds after `analyze` completes
- Generated notice covers all detected scenarios with no false positives
- Output is directly usable as an email body (copy-paste into Outlook/Gmail)
- Plain text variant is readable in terminal and plain-text email
- All template variables are substituted; no `{variable}` markers in output
- SE can customize brand, date, and helpdesk contact via CLI flags

## Open Questions

1. **Multi-language support?** Deferred. English-only for v1. Could add `--language` flag
   later with translated templates.

2. **Per-user personalized notices?** Deferred to the per-user diff report (separate spec).
   This generator produces a single notice per audience segment, not per user.

3. **Attachment of user list?** Consider generating a companion CSV listing which users
   are in which scenario group, so the SE can send targeted emails via mail merge.
   This could be a `--include-roster` flag that appends a CSV.
