# Identity & Numbering: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

## Decision Framework

### DN_AMBIGUOUS: Ownership Resolution
<!-- Source: recommendation_rules.py recommend_dn_ambiguous() lines 241-256 -->

| Condition | Recommendation | Reasoning |
|-----------|---------------|-----------|
| `owner_count == 1` | `assign` | DN has one clear owner. Assign to that user. |
| `primary_owner` exists (line 1 on a device) | `assign` | DN is shared but primary_owner has it as line 1. Assign to primary; other appearances become shared line or virtual extension. |
| Multiple owners, no clear primary | `None` (ambiguous) | No recommendation. Forces LLM/human review. |

The `primary_owner` field is set when a user has the DN on line 1 of any device. Line 1 = the device's primary identity line in CUCM. This is the strongest ownership signal because it determines the device's caller ID and registration identity.

### EXTENSION_CONFLICT: Appearance Count Comparison
<!-- Source: recommendation_rules.py recommend_extension_conflict() lines 259-281 -->

| Condition | Recommendation | Reasoning |
|-----------|---------------|-----------|
| `ext_a_appearances > ext_b_appearances` | `keep_a` | Extension used on more devices for owner_a. Reassign the conflicting extension. |
| `ext_b_appearances > ext_a_appearances` | `keep_b` | Extension used on more devices for owner_b. Reassign the conflicting extension. |
| Equal appearance counts | `None` (ambiguous) | No recommendation. Genuinely ambiguous -- force human decision. |

Appearance count = number of devices where that user has the extension configured. Higher count implies broader usage and more disruption if changed.

### DUPLICATE_USER: Merge Strategy
<!-- Source: recommendation_rules.py recommend_duplicate_user() lines 88-100 -->

| Condition | Recommendation | Confidence | Reasoning |
|-----------|---------------|------------|-----------|
| `email_match` | `merge` | Highest | Both entries share the same email. Definitive identity match. |
| `userid_match` | `merge` | High | Same CUCM userid. Merge; use the entry with the email address. |
| Name-only match (no email/userid match) | `keep_both` | Low | Same name but different emails. Likely different people. |

### NUMBER_CONFLICT: Webex Assignment Takes Precedence
<!-- Source: recommendation_rules.py recommend_number_conflict() lines 72-85 -->

| Condition | Recommendation | Reasoning |
|-----------|---------------|-----------|
| `same_owner` is true | `auto_resolve` | Same user owns number in both systems. No conflict. |
| Different owners | `keep_existing` | Number already assigned to existing Webex owner. CUCM owner needs a different number or existing assignment must be removed first. |

Rationale: Webex is the target system. Existing Webex assignments represent production state that should not be disrupted by incoming CUCM data.

## Edge Cases & Exceptions

- **DNs with 0 appearances** -- Orphaned from device decommissioning. The DN exists in CUCM but no device references it. The DN_AMBIGUOUS rule sees `owner_count == 0` and returns `None`. These typically become skip decisions unless the DN has a phone number worth porting.

- **Shared line DNs where ownership is ambiguous** -- When 2+ users share a DN and none has it on line 1, the rule returns `None`. The advisory system's Pattern 11 (Shared Line Simplification) may reclassify monitoring-only appearances as virtual extensions, reducing the ambiguity.
<!-- Source: advisory_patterns.py Pattern 11 -->

- **Extension conflicts between CUCM internal and Webex-assigned extensions** -- The EXTENSION_CONFLICT rule compares two CUCM entries. Cross-system conflicts (CUCM extension vs existing Webex extension) surface as NUMBER_CONFLICT decisions during the map phase.

- **Users in Webex with different email than CUCM userid** -- DUPLICATE_USER's `userid_match` assumes the CUCM userid maps to the Webex email. If the domains differ (e.g., `jsmith` in CUCM vs `john.smith@corp.com` in Webex), the merge recommendation may be wrong. See DT-ID-001 below.

- **Virtual line for non-user DNs** -- Conference room DIDs, lobby phones, fax lines. These are not person records. The migration planner creates virtual lines for DNs that have no person owner but do have a phone number or active call settings (voicemail, forwarding).
<!-- Source: virtual-lines.md "Common use cases" section -->

## Real-World Patterns

- **"Secretary DN"** -- DN owned by secretary, used as boss's secondary line (shared appearance). The DN_AMBIGUOUS rule resolves to `assign` to the secretary (line 1 owner). The boss's appearance becomes a shared line or monitoring BLF in Webex.

- **"Department DID"** -- DID not assigned to a person, routes to a hunt pilot or CTI route point. DN_AMBIGUOUS sees `owner_count == 0`. The migration planner evaluates whether to create a virtual line (if the DID needs independent call settings) or assign it directly to the target call queue/hunt group/auto attendant.
<!-- Source: virtual-lines.md "Shared department lines" use case -->

- **"Migrated user"** -- Already in Webex with a different extension. Surfaces as both DUPLICATE_USER (if email/userid matches) and potentially EXTENSION_CONFLICT (if extensions differ). The merge decision resolves the identity; extension assignment is a separate decision.

- **"Contractor"** -- CUCM user with no Webex account. No DUPLICATE_USER decision fires. The user flows through normal provisioning as a new person create.
<!-- Source: provisioning.md People API create section -->

- **"Multi-device"** -- User with 3+ devices sharing the same DN. Inflates appearance count for EXTENSION_CONFLICT comparisons. This user's extension has high inertia -- changing it disrupts multiple devices. The rule correctly favors keeping it.

## Webex Constraints

- **Extension length constraints per location** -- Each Webex Calling location has a routing prefix and extension length. Extensions must conform to the location's configured length. The CUCM extension may need zero-padding or truncation.
<!-- Source: provisioning.md "extension field value should not include the location routing prefix" -->

- **Phone numbers must be assigned to location before user** -- Numbers are location-scoped. The provisioning workflow is: add number to location inventory, then assign to person/virtual line via create or update.
<!-- Source: call-routing.md Phone Number Management section; provisioning.md Provisioning Workflow -->

- **Number porting requires carrier coordination** -- Moving CUCM PSTN numbers to Webex Calling requires a porting request through the Webex PSTN provider (Cisco Calling Plans, Cloud Connected PSTN, or Local Gateway). The `validate_phone_numbers` API checks availability but cannot initiate ports.
<!-- Source: call-routing.md validate_phone_numbers section -->

- **Virtual extensions use different ID type than virtual lines (VIRTUAL_EXTENSION vs VIRTUAL_LINE)** -- The `virtual-extensions` command group uses VIRTUAL_EXTENSION-encoded IDs. Virtual lines created via `/telephony/config/virtualLines` use VIRTUAL_LINE IDs. These are not interchangeable. `virtual-extensions list` returns empty for virtual lines, and `virtual-extensions delete` returns 400 for virtual line IDs.
<!-- Source: CLAUDE.md Known Issue #12 -->

- **Email is the primary user identifier in Webex** -- The People API uses `emails` as the identity key. Currently only one email is supported per person. All lookups, deduplication, and merge operations should key on email. The CUCM userid is not a Webex-native concept.
<!-- Source: provisioning.md Person data model: "emails list[str] Currently only one email supported"; People API list filter: email parameter -->

- **Max virtual lines per org: not documented** -- No official per-org limit for virtual lines is stated in the API docs or SDK reference. The `LIMIT_EXCEEDED` validation status exists in the virtual extension range validation model, suggesting a limit exists but its value is not published.
<!-- From training, needs verification -->

- **Number validation states** -- Before assigning numbers, use `validate_phone_numbers`. Possible states: `Available`, `Duplicate`, `Duplicate In List`, `Invalid`, `Unavailable`. Only `Available` numbers can be assigned.
<!-- Source: call-routing.md ValidatePhoneNumberStatus model -->

## Dissent Triggers

### DT-ID-001: Duplicate user merged by userid but email domains differ

- **Condition:** DUPLICATE_USER recommends `merge` based on `userid_match` BUT the CUCM userid and Webex email have different domain suffixes (e.g., CUCM userid `jsmith` resolves to `jsmith@cucm-domain.local` while Webex email is `john.smith@company.com`)
- **Why static rule may be wrong:** `userid_match` assumes the CUCM userid maps to the Webex email identity. When domains differ, the userid match may be coincidental -- two different people named J. Smith, or the same person whose email changed during a domain migration.
- **Advisor should:** Flag the domain mismatch, present both identities side by side, and ask the admin to confirm whether they are the same person before merging.
- **Confidence:** MEDIUM -- userid matches are strong signals but domain mismatches introduce real ambiguity.
- **Testable condition:** `context.get("userid_match") and cucm_email_domain != webex_email_domain`

### DT-ID-002: Extension conflict resolved by appearance count but lower-count user is business-critical

- **Condition:** EXTENSION_CONFLICT recommends `keep_a` (higher appearance count) BUT `user_b` has the extension on line 1 (their primary device identity line), while `user_a` has it as line 2+ on multiple devices (shared/monitoring appearances).
- **Why static rule may be wrong:** Appearance count measures breadth of deployment, not importance. A user with the extension on line 1 of one phone treats it as their primary identity. A user with the extension on line 2 of five phones uses it for monitoring or shared access -- it is not their primary number.
- **Advisor should:** Flag when the lower-count user has the extension on line 1 of any device. Present the line position data alongside the appearance count. Recommend reviewing whether the higher-count appearances are monitoring/BLF (which could become virtual extensions instead).
- **Confidence:** LOW -- requires understanding of line position semantics that the appearance count alone cannot capture.
- **Testable condition:** `ext_a_appearances > ext_b_appearances and context.get("b_has_line1")`

### DT-ID-003: Number conflict auto-resolved but number was reassigned in Webex

- **Condition:** NUMBER_CONFLICT recommends `auto_resolve` because `same_owner` is true, BUT the number was recently reassigned in Webex (e.g., user left and number was recycled to a new hire). The CUCM data is stale relative to the Webex state.
- **Why static rule may be wrong:** `same_owner` is determined by matching person identity across systems. If the Webex number was reassigned after the CUCM discovery snapshot, the ownership match is based on stale data.
- **Advisor should:** Flag when the Webex number assignment timestamp is more recent than the CUCM discovery timestamp. Recommend re-running discovery or confirming current ownership.
- **Confidence:** LOW -- requires temporal awareness that the static rules do not currently track.
- **Testable condition:** `context.get("same_owner") and webex_assignment_date > cucm_discovery_date`

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | Max 1000 virtual lines per org | **Not verified** | `virtual-lines.md` | No org-level limit documented. The `max=1000` values in the doc are pagination page sizes, not org limits. A `LIMIT_EXCEEDED` validation status exists but no number is stated. Marked `<!-- From training, needs verification -->`. |
| 2 | Virtual extension vs virtual line ID type issue | Yes | CLAUDE.md Known Issue #12 | `virtual-extensions` uses `VIRTUAL_EXTENSION` IDs, virtual lines use `VIRTUAL_LINE` IDs. `virtual-extensions list` returns empty, `delete` returns 400. Confirmed. |
| 3 | Email as primary Webex identifier | Yes | `provisioning.md` Person data model line 1109 | `emails: list[str]` — currently only one email supported. People API uses email as filter/lookup key. |
