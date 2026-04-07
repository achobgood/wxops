<!-- Last verified: 2026-04-07 against branch claude/identify-missing-questions-8Xe2R, Layer 1 commits 1940991 + 3c55241 -->

# CUCM-to-Webex Decision Interpretation Guide

> **Audience:** Operator mid-decision-review, asking "what does this decision mean and should I take the recommendation?"
> **Reading mode:** Reference. Scanned by `DecisionType` or advisory pattern. Never read end-to-end.
> **See also:** [Operator Runbook](operator-runbook.md) · [Tuning Reference](tuning-reference.md)

## Table of Contents

1. [How to Read a Decision](#how-to-read-a-decision)
2. [Severity Reference](#severity-reference)
3. [Recommendation Confidence and When to Override](#recommendation-confidence-and-when-to-override)
4. [Decision Types A–Z](#decision-types-az)
5. [Advisory Patterns](#advisory-patterns)
6. [Dissent Handling](#dissent-handling)
7. [Bulk-Accept Patterns](#bulk-accept-patterns)

---

## How to Read a Decision

_TBD — Wave 3 Phase C Task C1_

## Severity Reference

_TBD — Wave 3 Phase C Task C1_

## Recommendation Confidence and When to Override

_TBD — Wave 3 Phase C Task C1_

## Decision Types A–Z

<!-- Wave 3 Phase C Task C2: one entry per non-advisory DecisionType. Anchors below are placeholders that the
     test_decision_type_coverage.py test will validate. Do NOT rename — the verification script depends on
     the exact slug-form of each DecisionType. Order is alphabetical for findability. -->

### audio-asset-manual
### button-unmappable
### calling-permission-mismatch
### css-routing-mismatch
### device-firmware-convertible
### device-incompatible
### dn-ambiguous
### duplicate-user
### extension-conflict
### feature-approximation
### forwarding-lossy
### hotdesk-dn-conflict
### location-ambiguous
### missing-data
### number-conflict
### shared-line-complex
### snr-lossy
### voicemail-incompatible
### workspace-license-tier
### workspace-type-uncertain

## Advisory Patterns

<!-- Wave 3 Phase C Task C3: one entry per advisory pattern in ALL_ADVISORY_PATTERNS, grouped by category.
     Anchors below match the function name (with detect_ prefix stripped) — verified by
     test_advisory_pattern_coverage.py. Group order: eliminate / rebuild / out_of_scope / migrate_as_is.
     Note: 2 patterns have a pattern_name field that differs from their function name
     (detect_mixed_css → pattern_name "mixed_css_routing_restriction"; detect_intercluster_trunks →
     "intercluster_trunk_detection"). The anchor uses the function name. -->

### eliminate

#### restriction-css-consolidation
#### translation-pattern-elimination
#### partition-time-routing
#### voicemail-pilot-simplification
#### overengineered-dial-plan

### rebuild

#### hunt-pilot-reclassification
#### location-consolidation
#### shared-line-simplification
#### trunk-destination-consolidation
#### partition-ordering-loss
#### cpn-transformation-chain
#### pstn-connection-type
#### snr-configured-users
#### transformation-patterns
#### extension-mobility-usage
#### mixed-css
#### cumulative-virtual-line-consumption
#### trunk-type-selection
#### intercluster-trunks

### out-of-scope

#### media-resource-scope-removal
#### e911-migration-flag
#### recording-enabled-users
#### user-oauth-required
#### legacy-gateway-protocols

### migrate-as-is

#### device-bulk-upgrade
#### globalized-vs-localized

## Dissent Handling

_TBD — Wave 3 Phase C Task C5_

## Bulk-Accept Patterns

_TBD — Wave 3 Phase C Task C4 — MUST be a markdown table per spec §Artifact 2_
