# Selective Call Forwarding Migration

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline gap -- CSS-based caller-specific routing to Webex selective call handling APIs

---

## 1. Problem Statement

CUCM implements caller-specific call handling through CSS/partition manipulation. An administrator who wants "calls from the CEO go straight through, calls from external numbers forward to voicemail after hours" achieves this by placing the user's DN in multiple partitions with different calling search spaces that control reachability per caller or per time of day. The specifics vary widely -- some deployments use dedicated "VIP" partitions, others use time-of-day routing with calling party transformation, and many simply don't implement caller-specific behavior at all.

Webex Calling has four explicit per-person APIs for this functionality:

1. **Selective Call Forwarding** -- forward calls from specific numbers or during specific schedules to a designated destination
2. **Selective Call Acceptance** -- accept calls only from specific callers or during specific schedules (reject the rest)
3. **Selective Call Rejection** -- reject calls from specific callers or during specific schedules
4. **Priority Alert** -- play a distinctive ring for calls matching specific criteria (caller identity, schedule)

These four features share a common `SelectiveCriteria` model with `callsFrom` enum (`ANY_PHONE_NUMBER`, `SELECT_PHONE_NUMBERS`, `ANY_INTERNAL`, `ANY_EXTERNAL`), schedule binding, and per-criteria enable/disable.

### What the pipeline handles today

The `CallForwardingMapper` handles basic forwarding (CFA/CFB/CFNA) and detects lossy CUCM-only variants (BusyInt, NoAnswerInt, NoCoverage, OnFailure, NotRegistered). The `CSSMapper` decomposes CSSes into dial plans and calling permissions, classifying partitions as DIRECTORY/ROUTING/BLOCKING/MIXED. The `CSSRoutingAnalyzer` detects conflicting patterns across routing scopes.

None of these components detect or recommend Webex selective call handling features. The gap is:

- CUCM CSS patterns that implement **per-caller routing differences** are flattened during CSS decomposition. The semantic intent ("VIP callers bypass the after-hours partition") is lost.
- Webex selective call features are fully available via admin API (`/telephony/config/people/{personId}/selectiveForward`, `selectiveAccept`, `selectiveReject`) but the pipeline never suggests them.
- Priority Alert is user-only (no admin API path), so it cannot be auto-configured but should be documented as a post-migration option.

### Realistic scope

Most CUCM deployments do NOT use CSS/partition manipulation for per-caller routing. This is an advanced pattern found in maybe 10-20% of enterprise deployments, typically involving:

- Executive/VIP partitions that bypass after-hours routing
- Dedicated partitions for external vs. internal callers with different forwarding behavior
- Time-of-day routing that treats certain caller groups differently

This feature is a **detection + advisory** feature, not full automation. The pipeline detects CSS patterns that suggest caller-specific routing and produces advisory decisions recommending Webex selective forwarding configuration. It does NOT auto-create selective forwarding rules because:

1. The CUCM source patterns are heuristic -- false positives are possible
2. Selective forwarding rule creation requires specific phone numbers or caller categories that may not map cleanly from CUCM partition membership
3. The Webex rule structure (criteria with schedule + callsFrom + phoneNumbers) doesn't have a 1:1 mapping from CSS/partition semantics

---

## 2. CUCM Source Data

### 2a. CSS/Partition Patterns That Imply Selective Call Handling

CUCM doesn't have a "selective forwarding" feature. Instead, administrators achieve caller-specific behavior through partition architecture. The common patterns:

**Pattern 1: Dual-Partition User DN (Internal vs. External)**

A user's DN appears in two partitions -- one reachable by internal CSSes, another by external/PSTN CSSes. Each partition may have different call forwarding configured on the line appearance. This means "internal callers reach me directly; external callers hit my forwarding rules."

Detection signal: Same DN (`dnOrPattern`) in 2+ partitions assigned to the same user, where the partitions appear in CSSes with different external/internal scopes.

**Pattern 2: VIP/Executive Bypass Partition**

A partition named like "VIP_PT" or "Executive_PT" is included in certain CSSes but not others. Users whose CSSes include the VIP partition can reach DNs in it; others cannot (or are routed through a different path). This implements "only VIP callers reach this person's direct line."

Detection signal: Partition with low membership (few DNs) present in a subset of CSSes. Often the partition name contains keywords like "VIP", "executive", "priority", "direct".

**Pattern 3: Time-of-Day Partition Switching**

CUCM time-of-day routing uses `TimeSchedule` + `TimePeriod` to switch between partitions during business hours vs. after hours. A user's DN reachability changes based on the schedule -- effectively implementing "forward calls to voicemail after 6pm except for callers who have the after-hours CSS."

Detection signal: Partitions associated with `time_schedule` objects via route patterns that point to the same DN with different forwarding destinations or different reachability.

**Pattern 4: Calling Party Transformation**

CUCM `callingPartyTransformationPattern` can manipulate the calling party number before it reaches the called party's CSS evaluation. While this is primarily for caller ID manipulation, it can be used to route VIP callers differently by transforming their calling number to match a specific partition's reachability.

Detection signal: `callingPartyTransformationPattern` objects with specific calling-party number matches that map to different CSSes.

### 2b. What the Pipeline Already Extracts

The pipeline already discovers and normalizes:

- **CSSes** with ordered partition lists (cross-ref: `css_contains_partition`)
- **Partitions** with their member DNs (cross-ref: `partition_has_pattern`)
- **Route patterns** with action (ROUTE/BLOCK) and destination
- **User CSS assignments** (cross-ref: `user_has_css`, `device_has_css`, `line_has_css`)
- **Time schedules** and **time periods** (normalized by `RoutingMapper`)

No new AXL extraction is needed. The detection heuristics operate on data already in the store.

### 2c. Detection Heuristics

The detection logic runs as a new analyzer (not a mapper) because it reads cross-object relationships without producing canonical objects:

**Heuristic 1: Multi-Partition DN Detection**

```python
# Find DNs that appear in 2+ partitions
dn_partitions = defaultdict(set)
for dn in store.get_objects("dn"):
    partition_refs = store.find_cross_refs(dn["canonical_id"], "dn_in_partition")
    for ref in partition_refs:
        dn_partitions[dn["canonical_id"]].add(ref)

multi_partition_dns = {dn_id: parts for dn_id, parts in dn_partitions.items() if len(parts) >= 2}
```

For each multi-partition DN, check whether the partitions appear in CSSes with different internal/external scope. If yes, this DN is a selective call handling candidate.

**Heuristic 2: Low-Membership Partition Detection**

```python
# Find partitions with few DNs that appear in a subset of CSSes
for partition in store.get_objects("partition"):
    dn_count = len(store.find_cross_refs(partition["canonical_id"], "partition_has_pattern"))
    css_refs = store.find_cross_refs(partition["canonical_id"], "partition_in_css")
    total_css_count = len(store.get_objects("css"))

    if dn_count <= 10 and len(css_refs) < total_css_count * 0.5:
        # This partition is selectively accessible -- possible VIP/priority pattern
        ...
```

**Heuristic 3: Partition Naming Convention**

Check partition names for keywords: `vip`, `executive`, `priority`, `direct`, `bypass`, `afterhours`, `emergency`. This is a weak signal but useful when combined with structural heuristics.

---

## 3. Webex Target APIs

All four selective call handling features are available on person, workspace, and (for the first three) virtual line entities. The admin-level APIs:

### 3a. Selective Call Forwarding

**Endpoint:** `GET/PUT /telephony/config/people/{personId}/selectiveForward`
**Criteria CRUD:** `POST/GET/PUT/DELETE /telephony/config/people/{personId}/selectiveForward/criteria[/{id}]`
**Scope:** `spark-admin:telephony_config_read` / `spark-admin:telephony_config_write`

Top-level settings:

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Enable/disable selective forward |
| `defaultPhoneNumberToForward` | `str` | Default forward destination |
| `ringReminderEnabled` | `bool` | Play ring reminder tone |
| `destinationVoicemailEnabled` | `bool` | Forward to destination's voicemail |

Criteria fields (extends `SelectiveCriteria`):

| Field | Type | Description |
|-------|------|-------------|
| `forwardEnabled` | `bool` | Enable this criteria |
| `forwardToPhoneNumber` | `str` | Per-criteria forward destination (overrides default) |
| `sendToVoicemailEnabled` | `bool` | Forward to voicemail instead |

### 3b. Selective Call Acceptance

**Endpoint:** `GET/PUT /telephony/config/people/{personId}/selectiveAccept`
**Criteria CRUD:** `POST/GET/PUT/DELETE /telephony/config/people/{personId}/selectiveAccept/criteria[/{id}]`
**Scope:** Same as above.

Top-level: `enabled` + `criteria` list.
Criteria: `acceptEnabled`, `phoneNumbers` list, schedule binding.

### 3c. Selective Call Rejection

**Endpoint:** `GET/PUT /telephony/config/people/{personId}/selectiveReject`
**Criteria CRUD:** `POST/GET/PUT/DELETE /telephony/config/people/{personId}/selectiveReject/criteria[/{id}]`
**Scope:** Same as above.

Top-level: `enabled` + `criteria` list.
Criteria: `rejectEnabled`, `phoneNumbers` list, schedule binding.

### 3d. Priority Alert

**Endpoint:** User-only at `/telephony/config/people/me/settings/priorityAlert` (no admin path).
**Cannot be auto-configured via admin token.** Advisory-only.

Criteria: `notificationEnabled`, `phoneNumbers` list, schedule binding.

### 3e. Shared Criteria Model (`SelectiveCriteria`)

All four features share:

| Field | Type | Description |
|-------|------|-------------|
| `scheduleName` | `str` | Schedule name (`businessHours` or `holidays`) |
| `scheduleType` | `str` | `businessHours` or `holidays` |
| `callsFrom` | `SelectiveFrom` | `ANY_PHONE_NUMBER`, `SELECT_PHONE_NUMBERS`, `ANY_INTERNAL`, `ANY_EXTERNAL` |
| `anonymousCallersEnabled` | `bool` | Match anonymous callers |
| `unavailableCallersEnabled` | `bool` | Match unavailable callers |
| `phoneNumbers` | `list[str]` | E.164 numbers (when `callsFrom=SELECT_PHONE_NUMBERS`) |

### 3f. Precedence

When multiple selective features are enabled:

1. **Selective Reject** -- highest priority
2. **Selective Accept** -- only accepts matching calls
3. **Selective Forward** -- forwards matching calls (overrides standard forwarding)
4. Standard Call Forwarding (CFA > CFB > CFNA > Business Continuity)

### 3g. Workspace Support

All three admin-configurable features (accept/forward/reject) also work on workspaces:
- `/telephony/config/workspaces/{workspaceId}/selectiveAccept`
- `/telephony/config/workspaces/{workspaceId}/selectiveForward`
- `/telephony/config/workspaces/{workspaceId}/selectiveReject`
- `/telephony/config/workspaces/{workspaceId}/priorityAlert`

Same criteria model. Workspace support means common-area phone migration could also leverage these features.

---

## 4. Pipeline Integration

### 4a. New Analyzer: `SelectiveCallHandlingAnalyzer`

**File:** `src/wxcli/migration/transform/analyzers/selective_call_handling.py`

This is an analyzer (not a mapper) because it reads existing store data to detect patterns and produce advisory decisions. It does not create canonical objects.

**Decision type:** `FEATURE_APPROXIMATION` (reuse existing type -- this is an approximation of CUCM CSS behavior via Webex selective features)

**Depends on:** `css_routing` analyzer (so that CSS decomposition is complete before we run detection)

**Algorithm:**

1. **Multi-partition DN scan:** Find DNs in 2+ partitions. For each, check whether the owning user has CSSes that suggest internal/external routing split.
2. **Low-membership partition scan:** Find partitions with few DNs (<=10) that appear in a strict subset of CSSes. Cross-reference against user assignments to identify who would be "selectively reachable."
3. **Naming convention scan:** Check partition names for VIP/priority/bypass keywords. Combine with structural signals from steps 1-2 for confidence scoring.
4. **Produce advisory decisions:** For each detected pattern, create a `FEATURE_APPROXIMATION` decision with:
   - Summary describing the detected pattern
   - Context containing affected users, partition details, and recommended Webex feature
   - Options: `accept` (acknowledge and plan manual configuration), `skip` (ignore)
   - Severity: `MEDIUM` for structural matches, `LOW` for name-only matches

**Confidence levels:**

| Signal Combination | Confidence | Severity |
|-------------------|-----------|----------|
| Multi-partition DN + different CSS scopes | HIGH | MEDIUM |
| Low-membership partition + subset CSS reachability | HIGH | MEDIUM |
| Partition name keyword + structural signal | HIGH | MEDIUM |
| Partition name keyword only | LOW | LOW |
| Multi-partition DN without CSS scope difference | LOW | LOW |

### 4b. Advisory Pattern: Selective Call Handling Opportunities

**File:** Add to `src/wxcli/migration/advisory/advisory_patterns.py`

**Pattern name:** `selective_call_handling_opportunities`
**Category:** `feature_opportunity` (Webex feature that could enhance the migration)

**Logic:**
1. Count `FEATURE_APPROXIMATION` decisions from the `SelectiveCallHandlingAnalyzer`
2. Group by detected pattern type (multi-partition DN, VIP partition, time-of-day)
3. Produce an advisory summarizing opportunities

**Finding detail:**
```
N users have CSS patterns suggesting caller-specific routing in CUCM. Webex Calling
offers Selective Forward, Selective Accept, and Selective Reject as explicit per-person
features that can replicate this behavior with admin-level API configuration.

Detected patterns:
- M users with multi-partition DNs (internal vs. external routing split)
- P users reachable only via low-membership partitions (VIP/priority pattern)
- Q partitions with naming conventions suggesting selective access

These are advisory recommendations. The CSS decomposition has already handled the
routing and permission aspects. Selective call handling would add caller-specific
behavior that goes beyond what dial plans and calling permissions provide.
```

### 4c. Recommendation Rules

**File:** Add to `src/wxcli/migration/advisory/recommendation_rules.py`

For `FEATURE_APPROXIMATION` decisions from the selective call handling analyzer (detected via context key `selective_call_handling_pattern`):

- **Recommended option:** `accept` -- acknowledge the pattern and plan manual selective forwarding configuration in Webex
- **Reasoning:** "CUCM CSS pattern suggests caller-specific routing. Configure Webex selective forwarding/acceptance/rejection rules post-migration to preserve this behavior."
- **Confidence:** `MEDIUM` (heuristic detection, not a direct field mapping)

### 4d. No New Canonical Objects

The analyzer produces decisions only. No new canonical model is needed. The affected users already have `CanonicalUser`, `CanonicalCallingPermission`, and `CanonicalDialPlan` objects from the existing mappers.

### 4e. No Execution Operations

This is advisory-only. The pipeline:

1. Detects CSS patterns suggesting selective call handling
2. Produces `FEATURE_APPROXIMATION` decisions listing affected users
3. The advisory pattern summarizes the opportunities
4. The assessment report includes the findings
5. The operator manually configures Webex selective forwarding/acceptance/rejection via `wxcli user-settings` commands or Control Hub

Future work could add execution operations that auto-create selective forwarding rules based on the detected patterns, but the heuristic confidence is not high enough to justify this now.

---

## 5. Report Changes

### 5a. Assessment Report -- Executive Summary

In the "Feature Gaps" or "Recommendations" section, add a conditional row (only when selective call handling patterns detected):

| Metric | Value |
|--------|-------|
| Selective Call Handling Candidates | N users |

### 5b. Assessment Report -- Technical Appendix

Add a subsection in the Tier 4 feature gap area: "Selective Call Handling Opportunities"

- Table of affected users with columns: User, Pattern Type, Partitions Involved, Recommended Webex Feature
- Pattern type: "Multi-Partition DN", "VIP Partition", "Time-of-Day Split"
- Recommended Webex Feature: "Selective Forward", "Selective Accept", "Selective Reject", or "Priority Alert (user-only)"

### 5c. Implementation

Modify `src/wxcli/migration/report/appendix.py`:
- Query the store for `FEATURE_APPROXIMATION` decisions with `selective_call_handling_pattern` in context
- Render a summary table grouped by pattern type

Modify `src/wxcli/migration/report/executive.py`:
- Add conditional selective call handling count to the feature gaps area (only if > 0)

---

## 6. Documentation Updates Required

### 6a. CLAUDE.md Files

| File | Section | What to Add |
|------|---------|-------------|
| `src/wxcli/migration/transform/CLAUDE.md` | 13 Analyzers table | Add `SelectiveCallHandlingAnalyzer` row with `FEATURE_APPROXIMATION` decision type |
| `src/wxcli/migration/transform/analyzers/CLAUDE.md` | Analyzer list (if exists) | Add analyzer description and depends_on |
| `src/wxcli/migration/advisory/CLAUDE.md` | Advisory patterns list | Add `selective_call_handling_opportunities` pattern |
| `src/wxcli/migration/CLAUDE.md` | File Map table | No new files needed in top-level; analyzer is in existing `analyzers/` directory |

### 6b. Reference Docs

| File | Section | What to Add |
|------|---------|-------------|
| `docs/reference/person-call-settings-handling.md` | Sections 7-10 (Selective Accept/Forward/Reject, Priority Alert) | Already fully documented. No changes needed. |

### 6c. Knowledge Base

| File | Section | What to Add |
|------|---------|-------------|
| `docs/knowledge-base/migration/kb-css-routing.md` | CSS decomposition patterns | Add section: "Selective Call Handling Detection" describing the 3 heuristics and how CSS patterns map to Webex selective features |
| `docs/knowledge-base/migration/kb-user-settings.md` | Call settings mapping table | Add rows for Selective Forward, Selective Accept, Selective Reject, Priority Alert noting "No direct CUCM equivalent; detected via CSS/partition heuristics" |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Feature mapping table | Add rows for all 4 selective call handling features with mapping source "CSS partition analysis heuristic" |

### 6d. Runbooks

| File | Section | What to Add |
|------|---------|-------------|
| `docs/runbooks/cucm-migration/operator-runbook.md` | Post-migration verification | Add step: "Review selective call handling advisories; configure Webex selective forwarding/acceptance/rejection for flagged users" |
| `docs/runbooks/cucm-migration/decision-guide.md` | FEATURE_APPROXIMATION entries | Add entry for selective call handling pattern decisions |

### 6e. Models

No new model or DecisionType needed. Reuses `FEATURE_APPROXIMATION` with a distinguishing context key (`selective_call_handling_pattern`).

---

## 7. Test Strategy

### 7a. Unit Tests -- Analyzer

**File:** `tests/migration/transform/analyzers/test_selective_call_handling.py`

| Test | Description |
|------|-------------|
| `test_multi_partition_dn_detection` | DN in 2 partitions with different CSS scopes produces FEATURE_APPROXIMATION decision |
| `test_multi_partition_dn_same_scope_no_decision` | DN in 2 partitions but CSSes have same scope -- no decision produced |
| `test_low_membership_partition_detection` | Partition with 3 DNs in subset of CSSes produces decision |
| `test_high_membership_partition_no_decision` | Partition with 50 DNs -- not a VIP/priority pattern, no decision |
| `test_partition_naming_vip` | Partition named "VIP_PT" with structural signal produces HIGH confidence decision |
| `test_partition_naming_only_low_confidence` | Partition named "VIP_PT" without structural signal produces LOW confidence decision |
| `test_no_selective_patterns` | Clean environment with simple CSS structure -- no decisions |
| `test_multiple_patterns_multiple_decisions` | Multiple users with different patterns each get their own decision |
| `test_fingerprint_stability` | Re-running analyzer produces same fingerprint (idempotent) |
| `test_decision_context_contains_recommended_feature` | Decision context includes which Webex selective feature to recommend |

### 7b. Unit Tests -- Advisory Pattern

**File:** `tests/migration/advisory/test_advisory_selective.py`

| Test | Description |
|------|-------------|
| `test_pattern_fires_with_candidates` | Store has selective call handling decisions -- advisory produced |
| `test_pattern_silent_no_candidates` | No selective call handling decisions -- empty findings |
| `test_pattern_groups_by_type` | Multiple pattern types in detail string |
| `test_pattern_category` | Verify category is `feature_opportunity` |
| `test_pattern_severity` | Verify severity is MEDIUM |

### 7c. Unit Tests -- Recommendation Rule

**File:** `tests/migration/advisory/test_recommendation_selective.py`

| Test | Description |
|------|-------------|
| `test_recommendation_accept` | FEATURE_APPROXIMATION with selective context gets `accept` recommendation |
| `test_recommendation_confidence_medium` | Recommendation confidence is MEDIUM |
| `test_non_selective_feature_approx_unaffected` | Other FEATURE_APPROXIMATION decisions are not affected by this rule |

### 7d. Integration Tests

**File:** `tests/migration/transform/test_selective_integration.py`

| Test | Description |
|------|-------------|
| `test_full_pipeline_with_vip_partition` | Normalize -> map -> analyze with a VIP partition pattern produces advisory |
| `test_full_pipeline_no_selective_patterns` | Clean CSS structure produces no selective advisory |
| `test_report_includes_selective_candidates` | Assessment report includes selective call handling section when candidates exist |

### Estimated test count: 18-21 tests

---

## 8. Risks and Open Questions

### 8a. Heuristic Accuracy

The multi-partition DN detection may produce false positives in deployments where multiple partitions serve other purposes (e.g., number portability, multi-site DN overlaps). The analyzer should exclude known non-selective patterns:
- Partitions used purely for device mobility (EM)
- Partitions used for inter-site dial plan segmentation (same DN in different sites)
- Translation pattern partitions

**Mitigation:** Cross-reference against location assignments. If multi-partition DNs correspond to multi-site users (different locations), this is likely a site-based routing pattern, not a selective call handling pattern. Filter these out.

### 8b. Partition Naming Conventions Vary Wildly

The naming heuristic (`vip`, `executive`, `priority`) will miss organizations that use numeric or acronym-based partition naming (e.g., "PT_01", "CSS_EXEC"). It will also false-positive on partitions named "Priority_VM" that are voicemail-related.

**Mitigation:** Naming is a weak signal. Only produce LOW severity decisions for name-only matches. Require structural confirmation (multi-partition DN or low-membership subset pattern) for MEDIUM severity.

### 8c. No Direct Number Mapping

Even when we detect a VIP partition pattern, we often cannot extract the specific phone numbers that should go into Webex selective forwarding criteria. CUCM's CSS model controls reachability by partition membership of the *caller's* CSS, not by the *caller's* phone number. Translating "callers with CSS X can reach partition Y" into "forward calls from numbers A, B, C" requires resolving all DNs in all partitions accessible via CSS X -- which may be hundreds of numbers.

**Mitigation:** The advisory recommends Webex selective features and lists the CUCM CSS/partition context, but does NOT attempt to generate a phone number list for criteria. The operator decides which callers to include in selective rules.

### 8d. Priority Alert Limitation

Priority Alert has no admin-level API. The advisory can recommend it for "VIP caller distinctive ring" patterns, but the operator must configure it per-user via the Webex user portal or user-level OAuth token.

**Mitigation:** Advisory explicitly notes that Priority Alert requires user-level configuration and suggests Selective Forward or Selective Accept as admin-configurable alternatives.

### 8e. Volume Expectations

In a typical CUCM deployment:
- 70-80% of users have simple CSS assignments (one CSS, standard partitions) -- no selective patterns detected
- 10-20% may have multi-partition DNs due to site-based routing (filtered out as false positives by the location cross-check)
- 5-10% may have genuine selective call handling patterns worth advising on
- 1-5% may have VIP/executive partition patterns

The analyzer should handle large deployments (10,000+ users) without performance issues. The multi-partition DN scan is O(N) where N is the number of DNs.

---

## 9. Effort Estimate

| Component | Estimated Lines | Effort |
|-----------|----------------|--------|
| SelectiveCallHandlingAnalyzer | ~200 | Medium |
| Advisory pattern addition | ~50 | Small |
| Recommendation rule addition | ~30 | Small |
| Report changes (appendix + executive) | ~50 | Small |
| Tests (18-21) | ~500 | Medium |
| Doc updates (5-6 files) | ~100 | Small |
| **Total** | **~930** | **Medium** |

Estimated implementation time: 1 session.

---

## 10. Comparison: This Feature vs. Other Advisory-Only Specs

| Dimension | Selective Call Handling | Call Intercept | Executive/Assistant |
|-----------|----------------------|---------------|-------------------|
| CUCM source | CSS/partition analysis (already extracted) | Heuristic detection (CFA + partition names) | Direct SQL table |
| New extraction needed | No | Yes (tier4 extractor) | Yes (AXL query) |
| Webex target | 4 APIs (3 admin-configurable + 1 user-only) | 1 API (person intercept) | 6 APIs (exec/assistant) |
| Pipeline output | Analyzer decisions + advisory | Mapper extension + advisory | New mapper + canonical object |
| Auto-migration | No (heuristic confidence too low) | No (too disruptive) | Possible (direct mapping) |
| Decision type | `FEATURE_APPROXIMATION` (reuse) | None (advisory only) | `MISSING_DATA` for broken pairs |
| Typical volume | 5-15% of users flagged | < 5% of users | 5-50 executives per org |
| Risk of false positive | Medium (CSS patterns ambiguous) | Medium (partition naming) | Low (direct SQL) |
| Day-1 impact | LOW (enhancement, not regression) | MEDIUM (terminated users) | HIGH (executives notice) |
