---
name: feedback_help_gate_for_skills
description: Skills must include a mandatory --help verification gate to prevent agents from fabricating CLI command names from model training knowledge or reference doc filenames
type: feedback
---

Skills that reference wxcli commands must include a mandatory `--help` verification gate in their checkpoint section. Without this, agents construct command names from model training (e.g., `location-call-settings show-call-recording` from Webex API knowledge) rather than using the actual CLI groups.

**Why:** Discovered during manage-call-settings research (2026-04-17). Across 6 experiments, warnings, recipes, conditional loading, and file renames all failed to prevent wrong command names. Only the `--help` gate worked — it forces the agent to verify commands against the live CLI binary, which is ground truth.

**How to apply:** Add to any skill's checkpoint section:
```
MANDATORY: Before including ANY wxcli command in your plan, verify it exists.
Run `wxcli <group> --help` to confirm the command group exists and list its commands.
```
Also add Quick Recipes with exact commands before Step 1 (load references), so the agent sees correct commands before reading reference docs. Reference doc filenames can prime wrong CLI group names (e.g., `location-call-settings-advanced.md` → agent constructs `location-call-settings` as a CLI group).

Consider applying to: configure-routing, manage-devices, configure-features, and any other skill with counterintuitive CLI group names.
