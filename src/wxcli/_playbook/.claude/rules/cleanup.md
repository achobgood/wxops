---
paths:
  - "src/wxcli/commands/cleanup.py"
---

# Cleanup Command

`wxcli cleanup run` batch-deletes Webex Calling resources in dependency-safe order.

**Flags:**
- `--scope "Name1,Name2"` — limit to specific locations (by name or ID)
- `--all` — clean up entire org (required if --scope not given)
- `--include-users` — also delete users (off by default)
- `--include-locations` — also delete locations (off by default, includes 90s wait for calling disable propagation)
- `--exclude-user-domains "wbx.ai,corp.com"` — keep users matching these email domains (use with `--include-users`)
- `--dry-run` — show what would be deleted without deleting
- `--max-concurrent N` — parallel deletions per layer (default 5)
- `--force` — skip confirmation prompt

**Deletion order** (13 layers, reverse of creation): dial plans → route lists → route groups → translation patterns → trunks → call features → schedules/operating modes → virtual lines → devices → workspaces → users → numbers → locations.

**Known behaviors:**
- Virtual lines use raw API (not `wxcli virtual-extensions`) due to ID type mismatch bug
- Location deletion requires disabling calling first + 90s propagation wait
- Location delete may still 409 after wait — re-run cleanup to retry
- Calling disable is best-effort — locations where calling is already off are still attempted for deletion
- Phone numbers are removed before location deletion (max 5 per API request, main numbers skipped)
- Call parks and call pickups are enumerated per-location (no org-wide list endpoint)
- Workspaces must be deleted before disable-calling can succeed — API has no location filter, client-side filtering by locationId
