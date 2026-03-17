# Manage Call Settings Skill

<!-- SKELETON — To be built after reference docs are complete -->

## When to Invoke

After confirming the user wants to configure person-level or workspace-level call settings: forwarding, voicemail, DND, caller ID, call waiting, recording, intercept, privacy, etc.

## Reference Docs to Load

- `docs/reference/authentication.md`
- `docs/reference/person-call-settings.md`
- `docs/reference/workspace-call-settings.md`
- `docs/reference/wxc-sdk-patterns.md`

## Workflow

1. Verify auth token is working
2. Identify target (person or workspace)
3. Identify which settings to configure
4. Build deployment plan
5. Execute API calls
6. Verify results

## TODO

- [ ] Person settings workflow (30+ sub-settings)
- [ ] Workspace settings workflow
- [ ] Bulk settings changes
- [ ] Setting categories and dependencies
