# Phase 1 Audit Gap Findings

> Post-Phase 2 recheck: format variations the Phase 1 audit missed across skills AND reference docs.
> These are pre-existing issues, not regressions from Phase 2.

**Date:** 2026-03-19
**Trigger:** Phase 2 spot-check found 3 skills marked "fully compliant" that had format inconsistencies.
**Method:** Dispatched strict format-check agents for skills + grep-based recheck for reference docs.

---

## What Was Missed

Phase 1 audit agents checked for *existence* of sections but not *exact heading format*. Three specific format dimensions were too loosely checked:

1. **Critical Rules heading** — should be `## Critical Rules` (title case)
2. **Plan gate marker** — Step 5 should contain literal `[SHOW BEFORE EXECUTING]` (no backticks)
3. **Context Compaction heading** — should be `## Context Compaction Recovery` (with "Recovery")

---

## Findings

### 1. Critical Rules Heading — ALL CAPS in 3 skills

| Skill | Actual Heading | Required |
|-------|---------------|----------|
| `provision-calling` | `## CRITICAL RULES` | `## Critical Rules` |
| `manage-identity` | `## CRITICAL RULES` | `## Critical Rules` |
| `manage-licensing` | `## CRITICAL RULES` | `## Critical Rules` |

**Fix:** Change to title case `## Critical Rules`.

### 2. Plan Gate Marker — Format issues in 11 skills

| Skill | Issue | Actual Text |
|-------|-------|-------------|
| `provision-calling` | Missing brackets | `SHOW BEFORE EXECUTING` |
| `manage-identity` | Missing brackets | `SHOW BEFORE EXECUTING` |
| `manage-licensing` | Missing brackets | `SHOW BEFORE EXECUTING` |
| `configure-features` | Uses `--` prefix | `-- [SHOW BEFORE EXECUTING]` |
| `manage-call-settings` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |
| `configure-routing` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |
| `call-control` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |
| `reporting` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |
| `manage-devices` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |
| `device-platform` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |
| `messaging-spaces` | Backticks | `` `[SHOW BEFORE EXECUTING]` `` |

**Fix:** All should use plain `[SHOW BEFORE EXECUTING]` — no backticks, no `--` prefix, brackets required.

### 3. Context Compaction Heading — Missing "Recovery" in 8 skills

| Skill | Actual Heading | Required |
|-------|---------------|----------|
| `provision-calling` | `## Context Compaction` | `## Context Compaction Recovery` |
| `configure-features` | `## Context Compaction` | `## Context Compaction Recovery` |
| `configure-routing` | `## Context Compaction` | `## Context Compaction Recovery` |
| `manage-devices` | `## Context Compaction` | `## Context Compaction Recovery` |
| `device-platform` | `## Context Compaction` | `## Context Compaction Recovery` |
| `manage-identity` | `## Context Compaction` | `## Context Compaction Recovery` |
| `audit-compliance` | `## Context Compaction` | `## Context Compaction Recovery` |
| `manage-licensing` | `## Context Compaction` | `## Context Compaction Recovery` |

**Fix:** Append "Recovery" to heading.

---

## Skills With No Format Issues

| Skill | Critical Rules | Plan Gate | Context Compaction |
|-------|---------------|-----------|-------------------|
| `messaging-bots` | `## Critical Rules` | `[SHOW BEFORE EXECUTING]` (backticks) | `## Context Compaction Recovery` |

**Note:** `messaging-bots` has the backtick issue on plan gate but is otherwise correct. No skill passes all 3 checks perfectly.

---

## Summary

| Issue | Count | Skills |
|-------|-------|--------|
| ALL CAPS Critical Rules | 3 | provision-calling, manage-identity, manage-licensing |
| Plan gate missing brackets | 3 | provision-calling, manage-identity, manage-licensing |
| Plan gate backticks | 8 | manage-call-settings, configure-routing, call-control, reporting, manage-devices, device-platform, messaging-spaces, messaging-bots |
| Missing "Recovery" suffix | 8 | provision-calling, configure-features, configure-routing, manage-devices, device-platform, manage-identity, audit-compliance, manage-licensing |

**Total:** 22 format fixes across 13 of 14 skills (only `wxc-calling-debug` excluded — it has structural issues already captured in the main audit).

---

## Reference Doc False PASSes

Phase 1 audit agents accepted "implicit" or "numbered sections" as passing ToC checks, and accepted variant heading formats as passing scopes/gotchas checks. Phase 2 skipped these files.

### P2-2: Table of Contents — 9 false PASSes

These docs have numbered section headings but no actual `## Table of Contents` section with links:

| File | Sections | Phase 1 Rationale (wrong) |
|------|----------|--------------------------|
| `person-call-settings-handling.md` | 10+ | "structure is clear" |
| `person-call-settings-permissions.md` | 5 | "implicit ToC" |
| `location-call-settings-media.md` | 5 | "implicit ToC by numbered sections" |
| `reporting-analytics.md` | 9 | "not strictly required" |
| `devices-platform.md` | 4+ | "numbered structure provides clarity" |
| `admin-audit-security.md` | 8 | "implicit in markdown hierarchy" |
| `admin-hybrid.md` | 5 | "TOC is not explicitly formatted" |
| `admin-partner.md` | 3 | "No explicit numbered ToC" |
| `messaging-bots.md` | 9 | "explicitly numbered in headings" |

**Fix:** Add `## Table of Contents` with numbered links after Sources/Scopes, before first content section.

### P2-3: Heading Format Inconsistencies (lower priority)

Not content gaps — the information exists but under non-standard headings. These are consistency issues Phase 2 didn't address:

**Required Scopes variants** (11 docs use non-standard heading):
- `authentication.md` — "Calling-Related Scopes" instead of "Required Scopes"
- `call-features-major.md` — "6. Required Scopes" (numbered)
- `person-call-settings-permissions.md` — "Scope Summary"
- `person-call-settings-behavior.md` — "Scope Summary" within "API Access Path Summary"
- `location-call-settings-core.md` — "API Access Path Summary" (scopes in table column)
- `location-call-settings-media.md` — "Auth Scopes Summary" inside cross-cutting section
- `location-call-settings-advanced.md` — scopes per-section, no consolidated heading
- `emergency-services.md` — scopes inline per section, no top-level heading
- `virtual-lines.md` — scopes per API family, no consolidated heading
- `devices-core.md` — scopes in per-section tables (1.1, 2.1, 3.1)
- `messaging-spaces.md` — "Token Type Matrix" instead of "Required Scopes"

**Cross-cutting Gotchas variants** (several docs use numbered headings):
- `call-control.md` — `## 8. Key Gotchas`
- `webhooks-events.md` — `## 9. Key Gotchas`
- `reporting-analytics.md` — `## 8. Gotchas`
- `devices-core.md` — `### Raw HTTP Gotchas` (subsection, not top-level)
- `virtual-lines.md` — `### Raw HTTP Gotchas` (subsection)
- `admin-org-management.md` — `## Gotchas` (correct content, numbered differently)

---

## Full Tally

| Category | Count | Impact |
|----------|-------|--------|
| **Skill heading format fixes** | 22 | 13 of 14 skills |
| **Ref doc ToC false PASSes** | 9 | Phase 2 skipped adding ToC |
| **Ref doc heading variants** | ~17 | Consistency only (content present) |
| **Total actionable** | **31** | 22 skill fixes + 9 ToC additions |

---

## Recommended Fix Approach

**Skills (22 fixes):** Simple find-and-replace. A single agent per skill can fix all format issues in one pass.

**Reference doc ToCs (9 additions):** Each needs a `## Table of Contents` section generated from existing section headings. One agent per 2-3 files.

**Heading variants (17):** Lower priority. Could normalize in a follow-up pass but the content is correct.
