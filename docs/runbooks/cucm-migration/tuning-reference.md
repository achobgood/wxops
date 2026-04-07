<!-- Last verified: 2026-04-07 against branch claude/identify-missing-questions-8Xe2R, Layer 1 commits 1940991 + 3c55241 -->

# CUCM-to-Webex Configuration Tuning Reference

> **Audience:** Operator configuring for a new customer environment OR debugging a recurring decision pattern.
> **Reading mode:** Reference, scanned by config key or recipe.
> **See also:** [Operator Runbook](operator-runbook.md) · [Decision Guide](decision-guide.md)

## Table of Contents

1. [config.json: Every Key Explained](#configjson-every-key-explained)
2. [Auto-Rules: How They Work, the 7 Defaults, How to Add Your Own](#auto-rules-how-they-work-the-7-defaults-how-to-add-your-own)
   - [The 14 Non-Auto-Ruled DecisionTypes and Why](#the-14-non-auto-ruled-decisiontypes-and-why)
3. [Score Weights and the Calibration Disclaimer](#score-weights-and-the-calibration-disclaimer)
4. [What Is and Isn't Tunable](#what-is-and-isnt-tunable)
5. [Per-Decision Overrides](#per-decision-overrides)
6. [Tuning Recipes](#tuning-recipes)
   - [Recipe 1: Small SMB, single location, 10–50 users](#recipe-1-small-smb-single-location-1050-users)
   - [Recipe 2: Hunt-list / call-queue heavy migration](#recipe-2-hunt-list--call-queue-heavy-migration)
   - [Recipe 3: CSS-heavy customer with strict partition ordering](#recipe-3-css-heavy-customer-with-strict-partition-ordering)
   - [Recipe 4: Cert-based trunk customer](#recipe-4-cert-based-trunk-customer)
   - [Recipe 5: Analog-gateway-heavy customer](#recipe-5-analog-gateway-heavy-customer)

---

## config.json: Every Key Explained

<!-- Wave 3 Phase D Task D1: one anchor per DEFAULT_CONFIG key. Anchors below are slug-form (lowercase, hyphenated)
     and validated by test_config_key_coverage.py. Update both sides if you rename a key. -->

### country-code

**Default:** `"+1"` (from `src/wxcli/commands/cucm_config.py:37`)
**What it controls:** The dial prefix used when normalizing and classifying CUCM directory numbers, route patterns, and translation patterns into E.164 form. Drives both phone-number routing decisions and CSS/partition pattern categorization.
**When to change:** Set this for every non-NANP customer. Examples: `"+44"` for UK, `"+49"` for Germany, `"+61"` for Australia. NANP customers (US, Canada, most Caribbean) leave it at `"+1"`.
**Example non-default:**
```json
{"country_code": "+44"}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:175` (RoutingMapper) and `src/wxcli/migration/transform/engine.py:203` (CSSMapper) — passed into pattern classification and E.164 normalization logic.

### default-language

**Default:** `"en_us"` (from `src/wxcli/commands/cucm_config.py:38`)
**What it controls:** The Webex user interface language applied to locations created from CUCM device pools. Users provisioned into those locations inherit it unless their own CUCM user record overrides it.
**When to change:** Set this when the customer's primary operating language is not US English. Use Webex locale codes: `"en_gb"`, `"fr_fr"`, `"de_de"`, `"es_es"`, `"ja_jp"`, etc.
**Example non-default:**
```json
{"default_language": "fr_ca"}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:167` — passed into `LocationMapper` and applied to every `CanonicalLocation` that doesn't have a language derived from its CUCM source.

### default-country

**Default:** `"US"` (from `src/wxcli/commands/cucm_config.py:39`)
**What it controls:** The ISO country code assigned to newly created Webex locations and used by the E.164 normalizer when classifying directory numbers that lack an explicit country context.
**When to change:** Set this for every non-US customer. Use ISO 3166-1 alpha-2 codes: `"CA"`, `"GB"`, `"DE"`, `"AU"`, `"JP"`, etc. Multi-country migrations should pick the primary country and handle exceptions via per-location overrides at execution time.
**Example non-default:**
```json
{"default_country": "GB"}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:168` (LocationMapper) and `src/wxcli/migration/transform/engine.py:187` (LineMapper), and also read directly at the CLI layer in `src/wxcli/commands/cucm.py:764` and passed into `normalize_discovery()` for cross-reference E.164 classification.

### outside-dial-digit

**Default:** `"9"` (from `src/wxcli/commands/cucm_config.py:40`)
**What it controls:** The digit a user must dial to reach an outside line in the source CUCM deployment. The pipeline strips this prefix when translating CUCM route patterns and dial transformations into Webex dial plans.
**When to change:** Change it only when the customer explicitly uses a different outside-access digit (commonly `"8"` or `"0"` outside North America). If the customer has no outside-access prefix (modern DN-routed deployments), leaving it at `"9"` is harmless — the pipeline will not find matching patterns to strip.
**Example non-default:**
```json
{"outside_dial_digit": "0"}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:169` (LocationMapper), `src/wxcli/migration/transform/engine.py:176` (RoutingMapper), and `src/wxcli/migration/transform/engine.py:204` (CSSMapper) — always passed in as a string.

### create-method

**Default:** `"people_api"` (from `src/wxcli/commands/cucm_config.py:41`)
**What it controls:** Which Webex API surface the execution layer uses to create migrated users. Valid values are `"people_api"` (the standard `/v1/people` endpoint) or `"scim"` (the SCIM `/identity/scim/{orgId}/v2/Users` endpoint). The choice is recorded on every `CanonicalUser` object and read by the execute handler.
**When to change:** Use `"scim"` when the customer already has a SCIM-synced identity provider (Okta, Azure AD, Ping) and you want migrated users to land in the SCIM-governed path. Otherwise leave it at `"people_api"`.
**Example non-default:**
```json
{"create_method": "scim"}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:181` — passed into `UserMapper`, which stores it on each `CanonicalUser` at `src/wxcli/migration/transform/mappers/user_mapper.py:210`.

### include-phoneless-users

**Default:** `false` (from `src/wxcli/commands/cucm_config.py:42`)
**What it controls:** Whether `UserMapper` emits `CanonicalUser` objects for CUCM end users who have no associated phone or directory number. When `false`, phoneless users are filtered out at `src/wxcli/migration/transform/mappers/user_mapper.py:130` and never reach the execute plan.
**When to change:** Set to `true` when the customer wants every CUCM user (including analysts, admins, and service accounts with no DN) provisioned in Webex — for example, to pre-stage Webex App logins before the calling cutover. Leave it `false` if you only want users who had a functioning CUCM phone.
**Example non-default:**
```json
{"include_phoneless_users": true}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:182` — passed into `UserMapper`, which checks the flag at `src/wxcli/migration/transform/mappers/user_mapper.py:130` before emitting a user without a location.

### auto-rules

**Default:** the 7 `DEFAULT_AUTO_RULES` entries (from `src/wxcli/commands/cucm_config.py:43`, defined at `src/wxcli/commands/cucm_config.py:17`)
**What it controls:** The list of auto-resolution rules the analysis pipeline applies after analyzers finish running. Each rule matches a `DecisionType` (optionally with additional context predicates) and auto-selects a `choice`, bypassing manual review for clear-cut cases.

See §[Auto-Rules: How They Work, the 7 Defaults, How to Add Your Own](#auto-rules-how-they-work-the-7-defaults-how-to-add-your-own) below for the full treatment — per-rule walkthroughs, the add-your-own pattern, and the list of decision types that intentionally have no default rule.

### site-prefix-rules

**Default:** `[]` (empty list) (from `src/wxcli/commands/cucm_config.py:44`)
**What it controls:** A list of prefix-stripping rules the E.164 normalizer applies to CUCM directory numbers before classifying them. Multi-site deployments that use an access-code prefix (e.g., every DN at site 100 is stored as `100XXXX` but dialed as `XXXX`) need entries here so the normalizer can strip the access code and recover the true 4-digit extension.
**When to change:** Add entries when the customer has a multi-site CUCM deployment with site-prefix access codes. Each entry is a dict with `pattern` and `strip` keys consumed by `apply_prefix_rules()` at `src/wxcli/migration/transform/e164.py:100`. Leave empty for single-site customers or deployments where DNs are stored in their fully-dialable form.
**Example non-default:**
```json
{"site_prefix_rules": [{"pattern": "100", "strip": "100"}, {"pattern": "200", "strip": "200"}]}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:170` (LocationMapper) and `src/wxcli/migration/transform/engine.py:188` (LineMapper), plus `src/wxcli/commands/cucm.py:765` which passes it into `normalize_discovery()` → `CrossReferenceBuilder` at `src/wxcli/migration/transform/cross_reference.py:923` for DN classification during Pass 2.

### category-rules

**Default:** `null` (from `src/wxcli/commands/cucm_config.py:45`; the consumer coerces `None` to `[]` at `src/wxcli/migration/transform/mappers/css_mapper.py:111`)
**What it controls:** A list of customer-specific rules that classify CUCM block patterns into Webex calling permission categories (international, toll, premium, etc.). `CSSMapper` uses these to decide which Webex category a blocking route pattern maps to when the default heuristic is ambiguous or wrong.
**When to change:** Add rules when the customer has a strict CSS/partition model with non-standard blocking patterns — for example, a partition that blocks only 976/900 premium numbers should map to a specific Webex category rather than the default classification. Leave it `null` for most migrations; the default heuristic handles typical CUCM deployments.
**Example non-default:**
```json
{"category_rules": [{"cucm_pattern": "9.1900[2-9]XXXXXX", "webex_category": "premium"}]}
```
**Consumed by:** `src/wxcli/migration/transform/engine.py:202` — passed into `CSSMapper`, which applies the rules at `src/wxcli/migration/transform/mappers/css_mapper.py:612` and `:671` during calling-permission classification.

## Auto-Rules: How They Work, the 7 Defaults, How to Add Your Own

<!-- Wave 3 Phase D Task D2: one anchor per DEFAULT_AUTO_RULES entry. Anchors are `default-rule-` plus the
     slug-form of the rule's `type` field, with `-<match-key>-<match-value>` appended when a `match` filter
     is present (see `default-rule-calling-permission-mismatch-assigned-users-count-0` below).
     Validated by test_default_auto_rules_coverage.py. -->

**What auto-rules do.** An auto-rule is a declarative shortcut that resolves a pending decision at pipeline load-time, before that decision ever reaches the human decision-review queue. Each rule is a small dict with a `type` (matching a `DecisionType` value), an optional `match` block (structural filter against the decision's `context`), and a `choice` (the option ID the rule should select). When `apply_auto_rules()` runs during `wxcli cucm analyze`, it walks every unresolved decision, finds the first rule whose `type` and `match` match, validates that `choice` is a real option ID, and resolves the decision with `resolved_by = "auto_rule"`. The decision then disappears from `wxcli cucm decisions list` and review.

**Match operators.** Declarative only — no `eval`/`exec`. All match keys AND together (every key must match). The operator is inferred from the key's suffix. Implemented in `src/wxcli/migration/transform/rules.py:_match_rule()`:

- **Plain key** (no suffix) — exact equality, or list membership if the value is a list.
  `{"cucm_model": "7841"}` matches when `context["cucm_model"] == "7841"`.
  `{"cucm_model": ["7841", "7861"]}` matches when `context["cucm_model"]` is in that list.
- **`_lte`** — less-than-or-equal numeric comparison. Non-numeric context values skip the rule gracefully (no crash).
  `{"assigned_users_count_lte": 0}` matches when `context["assigned_users_count"] <= 0`.
- **`_gte`** — greater-than-or-equal numeric comparison. Same graceful-skip on non-numeric.
  `{"agent_count_gte": 10}` matches when `context["agent_count"] >= 10`.
- **`_contains`** — substring match (both sides must be strings).
  `{"name_contains": "lobby"}` matches when `"lobby" in context["name"]`.

Missing context keys cause the rule to skip (return `False`), not crash. A rule with no `match` field at all is type-only and matches every decision of that type.

**How to add a new rule.** Edit `<project>/config.json` (written by `wxcli cucm init`, loaded by `load_config()` at `src/wxcli/commands/cucm_config.py:50`). The `auto_rules` key is a list — append your new rule dict and re-run `wxcli cucm analyze`. For example, to auto-resolve every `FEATURE_APPROXIMATION` decision in favor of the `hunt_group` option when the hunt list is small and uses the top-down algorithm:

```json
{
  "auto_rules": [
    {
      "type": "FEATURE_APPROXIMATION",
      "match": {"algorithm": "topDown", "agent_count_lte": 4},
      "choice": "hunt_group"
    }
  ]
}
```

The 7 `DEFAULT_AUTO_RULES` below are merged into the list, so your additions augment the defaults rather than replacing them.

**When NOT to add an auto-rule.** Auto-rules are the wrong tool whenever the correct answer depends on judgment or on information the pipeline cannot see:

- The decision requires a conversation with the customer (licensing tier, PSTN architecture, number-porting cutover strategy).
- The match would hide a signal the operator needs to see — for example, silencing every `CALLING_PERMISSION` decision would bury real outbound-dialing policy gaps that the customer must ratify.
- The rule is correct "most of the time" but the exceptions are high-blast-radius (silently skipping devices with real users attached, silently accepting voicemail data loss).
- You are using it to suppress a failing analyzer rather than fix the underlying mapper or data-quality bug.

In every "NOT" case, prefer a per-decision override via `wxcli cucm decide <decision-id> <choice>` so the resolution is auditable and reviewable rather than invisible.

### default-rule-device-incompatible

**Rule:**
```json
{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}
```
**What it does:** Every decision of type `DEVICE_INCOMPATIBLE` (a CUCM device model that has no Webex Calling equivalent at all — old SCCP-only phones, analog endpoints behind VG series gateways, legacy video units) is resolved to `skip`, meaning the device is left out of the migration plan entirely and its owner keeps working from CUCM until a replacement is procured.
**Why safe as default:** There is no correct "migrate it anyway" answer for a truly incompatible device. The analyzer only flags models that cannot onboard — not ones that merely need a firmware path — so the only real options are `skip` or `procure_replacement`, and procurement is a customer-side decision that happens outside the pipeline. Silently skipping here keeps the migration plan buildable without misrepresenting what will actually work post-cutover.
**When to remove:** If the customer has already ordered replacement hardware and you want each incompatible device to surface in decision review so you can manually attach the replacement model ID, remove this rule and resolve each decision explicitly. Also remove it in assessment-only runs where the count of incompatible devices IS the deliverable — an auto-resolved decision can vanish from some summary views.
**See also:** `dt-dev-001`

### default-rule-device-firmware-convertible

**Rule:**
```json
{"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert"}
```
**What it does:** Every decision of type `DEVICE_FIRMWARE_CONVERTIBLE` (a CUCM phone running enterprise firmware that also ships an MPP or PhoneOS load — classic 88xx, 78xx in convertible SKUs, 9800-series in native MPP mode) is resolved to `convert`, meaning the pipeline will plan a firmware conversion instead of a hardware swap.
**Why safe as default:** Firmware-convertible is a property of the hardware SKU, not a judgment call. The `DeviceCompatibilityAnalyzer` only emits this decision for models where the conversion path is known, supported, and documented by Cisco. The alternative choice (`replace`) is strictly more expensive and disruptive, and there is no deployment scenario where replacing a convertible phone with the same model is the right answer.
**When to remove:** Remove this rule when the customer's refresh cycle already lined up with the migration and they are buying new MPP hardware anyway — in that case, each device should be resolved to `replace` so the cutover plan ships the new phones instead of preserving the old chassis. Also remove it when firmware management is centralized on a partner-supplied config server that the customer does not control (rare) and you need the firmware step to be explicit and reviewable.
**See also:** `dt-dev-002`

### default-rule-hotdesk-dn-conflict

**Rule:**
```json
{"type": "HOTDESK_DN_CONFLICT", "choice": "keep_primary"}
```
**What it does:** Every decision of type `HOTDESK_DN_CONFLICT` (a CUCM hot-dial or Extension Mobility login where the user's primary DN collides with the DN of the device they log into) is resolved to `keep_primary`, meaning the user's primary DN wins and the device-native DN is dropped from the migrated line appearance.
**Why safe as default:** In CUCM hot-dial and Extension Mobility, the intent is almost always that the user's identity (primary DN) follows them onto whatever device they sit at; the device's "home" DN is a fallback that only matters when nobody is logged in. Webex Calling has no direct Extension Mobility analog, so preserving the user's primary DN is the only mapping that keeps inbound calls reaching the right person post-migration. Keeping the device DN instead would disconnect the user from their existing number.
**When to remove:** Remove this rule in environments where the device DN is a real, published extension (a lobby or shared workspace where the device is the identity and no single user "owns" it long-term). In those cases you want each conflict to reach decision review so the operator can resolve to `keep_device` or create a separate hot-desking workspace. Also remove for customers using CUCM Extension Mobility Cross Cluster (EMCC) where the primary/device distinction is deliberately blurred.
**See also:** `dt-id-003`

### default-rule-forwarding-lossy

**Rule:**
```json
{"type": "FORWARDING_LOSSY", "choice": "accept_loss"}
```
**What it does:** Every decision of type `FORWARDING_LOSSY` (a CUCM call-forwarding configuration that uses a feature Webex Calling cannot fully express — per-CSS forwarding, forward-to-voicemail with a CSS override, forward to an internal-only route pattern that won't exist post-cut) is resolved to `accept_loss`, meaning the closest-matching Webex forwarding rule is applied and the fidelity gap is logged.
**Why safe as default:** The `CallForwardingMapper` only marks a forwarding config as lossy when the Webex target exists but the CSS-scoped routing or the internal-only target cannot be carried forward. In every case, the user-visible behavior after migration is the same or strictly better — a forwarded call still reaches the same destination, just without the CSS-gated filter. The gap is in the edge case (caller-specific routing), not the primary path, so accepting the loss preserves the everyday experience without a conversation per user.
**When to remove:** Remove this rule for customers with regulatory or privacy requirements tied to their forwarding rules (healthcare after-hours routing, legal firms with ethical-wall CSSes, compliance-driven forward-to-record flows) — in those environments, every lossy forwarding decision should reach the operator so the gap can be documented and a compensating Webex control (operating modes, schedules, call-intercept) can be planned.
**See also:** `dt-user-001`

### default-rule-snr-lossy

**Rule:**
```json
{"type": "SNR_LOSSY", "choice": "accept_loss"}
```
**What it does:** Every decision of type `SNR_LOSSY` (a CUCM Single Number Reach configuration that uses a feature Webex Calling cannot fully express — SNR with a per-CSS answer-too-soon timer, SNR with multiple remote destinations that exceed Webex's sequential-ring limits, SNR tied to a time-of-day schedule not representable in Webex) is resolved to `accept_loss`, meaning the closest Webex equivalent (Office Anywhere, simultaneous ring, or sequential ring) is applied and the fidelity gap is logged.
**Why safe as default:** The `SNRMapper` only emits this decision when the remote destination ring-to reach and the primary single-number behavior both succeed, and only the secondary knobs (answer-too-soon thresholds, per-destination schedules, ring delays beyond the Webex cap) don't carry forward. Users will still see their calls ring their mobile and their desk phone — just with simpler timing. Because SNR fidelity gaps rarely cause missed calls (they usually cause extra rings or slightly early voicemail), accepting the loss is a safe default for the overwhelming majority of users.
**When to remove:** Remove this rule when the customer has executive or on-call staff whose escalation chains depend on the exact SNR timing (emergency responders, on-call engineers, 24×7 NOC rotations) — for those users, the answer-too-soon and ring-duration values are load-bearing and every lossy SNR decision should reach decision review. Also remove for customers who have built SNR around an auto-attendant or call-queue pre-filter that Webex can't reproduce.
**See also:** `dt-user-002`

### default-rule-button-unmappable

**Rule:**
```json
{"type": "BUTTON_UNMAPPABLE", "choice": "accept_loss"}
```
**What it does:** Every decision of type `BUTTON_UNMAPPABLE` (a line-key slot on a CUCM phone button template that uses a feature Webex Calling cannot bind to a key — service URL to an XML phone service, feature button for a CUCM-only capability like Mobility, Abbreviated Dial with a CUCM-only directory hook) is resolved to `accept_loss`, meaning the key is left empty (or reassigned to a default line) on the migrated device layout and the gap is logged.
**Why safe as default:** The `DeviceLayoutMapper` only flags buttons whose underlying service target either does not exist in Webex Calling or requires a different binding mechanism (XSI macro, device configuration template, workflow integration). Leaving the key blank is a strictly no-harm outcome — the user loses a shortcut they often never used, and the rest of the line layout migrates intact. Pushing these into decision review would generate hundreds of near-identical decisions per environment with no path to a better answer.
**When to remove:** Remove this rule for customers who depend on specific service-URL buttons for daily workflows (retail POS integrations, healthcare EHR launchers, emergency notification buttons, executive VIP dial buttons) — in those cases the unmappable buttons should surface in decision review so the operator can plan the replacement workflow (macro, workspace personalization, RoomOS device configuration, or a paper cutover). Also remove for any customer using shared-line BLF for call-center-style supervisor monitoring that must be preserved.
**See also:** `dt-dev-003`

### default-rule-calling-permission-mismatch-assigned-users-count-0

**Rule:**
```json
{
  "type": "CALLING_PERMISSION_MISMATCH",
  "match": {"assigned_users_count": 0},
  "choice": "skip"
}
```
**What it does:** Every decision of type `CALLING_PERMISSION_MISMATCH` whose context reports `assigned_users_count == 0` (a CUCM CSS whose calling permissions don't line up cleanly with any Webex category, but which has no users actually assigned to it at the time of discovery) is resolved to `skip`, meaning the CSS is left out of the migration and no Webex calling permission is provisioned from it.
**Why safe as default:** A CSS with zero assigned users is a CUCM configuration artifact, not a live policy. Migrating a mismatched calling permission that nobody uses would create a Webex category that exists only to match a CUCM construct — it would clutter the tenant, confuse future auditors, and provide no user-visible benefit. This is the only auto-rule in the default set that uses a `match` filter (`assigned_users_count: 0`), which narrows it to the one case where "skip" is unambiguously correct. Mismatched CSSes WITH users still reach decision review.
**When to remove:** Remove this rule if the customer intends to reuse the CSS shortly after cutover (a known phased-rollout strategy where certain CSSes are staged in CUCM for users who will migrate in a later wave), so that the permission model can be planned rather than silently dropped. Also remove in environments where CSS reuse patterns are load-bearing for compliance audits and every CSS must be accounted for in the migration record.
**See also:** `dt-css-002`

### The 14 Non-Auto-Ruled DecisionTypes and Why

The 7 default auto-rules above are the *only* `DecisionType` values that the pipeline resolves on its own. Every other type — 14 in total when you count `CALLING_PERMISSION_MISMATCH` (whose default rule narrowly matches `assigned_users_count == 0` and so leaves the populated case unresolved) — flows into the human decision-review queue with no shortcut. The absence of an auto-rule on these types is intentional, not an omission. Each one falls into one of three buckets: the decision requires *judgment too high* for a declarative match (the right answer depends on customer-specific tradeoffs the pipeline cannot see), the decision's *context is too variable* to capture in a single rule without burying real signals, or there is *no safe single answer* — multiple valid choices exist and silently picking one would violate operator trust. The table below enumerates all 14, classifies each, and forward-links to the canonical decision-guide entry for the producer logic and recommendation algorithm.

| DecisionType | Reason not auto-ruled | Notes |
|---|---|---|
| `FEATURE_APPROXIMATION` | judgment too high | Producers in 4 mappers plus 2 analyzers: `feature_mapper.py:281,523`, `device_profile_mapper.py:107`, `routing_mapper.py:471`, `monitoring_mapper.py:181`, and `analyzers/feature_approximation.py` + `analyzers/layout_overflow.py`. The 5–8 agent hunt-list band is genuinely ambiguous between `hunt_group` and `call_queue`; routing-type caps depend on the algorithm (50 for Simultaneous, 1,000 for priority-based per `kb-webex-limits.md dt-limits-001`). See [`dt-feat-001`](../../knowledge-base/migration/kb-feature-mapping.md#dt-feat-001). |
| `LOCATION_AMBIGUOUS` | judgment too high | Producers: `location_mapper.py:120` (mapping-time device-pool-to-location ambiguity) and `analyzers/location_ambiguity.py:175` (cross-object sweep). Device-pool-to-location consolidation depends on customer site structure (timezone + region + site_code agreement is necessary but not sufficient; the operator owns whether two device pools really represent one Webex location). Highest-fan-out resolution in the pipeline. See [`dt-loc-001`](../../knowledge-base/migration/kb-location-design.md#dt-loc-001). |
| `VOICEMAIL_INCOMPATIBLE` | judgment too high | Producers: `voicemail_mapper.py:244` (mapper-owned gap analysis) and `analyzers/voicemail_compatibility.py:192` (analyzer safety net). Flags Unity Connection features (call screening rules, caller-input personal greetings, distribution-list voice messaging) that have no Webex equivalent. Whether to accept the loss, redesign the voicemail experience, or hold the affected users on Unity Connection in parallel is a customer-policy call. See [`dt-user-003`](../../knowledge-base/migration/kb-user-settings.md#dt-user-003). |
| `WORKSPACE_LICENSE_TIER` | judgment too high | Producers: `workspace_mapper.py:201` (mapper-owned Basic/Professional tier decision) and `analyzers/workspace_license.py:153` (analyzer safety net). Basic vs Professional workspace licensing is a billing decision the customer must ratify; the 405 footgun on `/telephony/config/` endpoints when a Basic workspace tries Professional features is documented in `devices-workspaces.md`. See [`dt-user-004`](../../knowledge-base/migration/kb-user-settings.md#dt-user-004). |
| `WORKSPACE_TYPE_UNCERTAIN` | judgment too high | Producer: `workspace_mapper.py:174`. Whether a phone in a private office, conference room, or shared cube becomes a `desk`, `huddle`, `meetingRoom`, or `other` workspace depends on physical space conventions only the customer knows. See [`dt-user-005`](../../knowledge-base/migration/kb-user-settings.md#dt-user-005). |
| `CSS_ROUTING_MISMATCH` | context too variable | Producers: `css_mapper.py:236,478,832` (mapper-level) and `analyzers/css_routing.py:155` (cross-object safety net). Branches on `mismatch_type` — `partition_ordering` requires manual decomposition because Webex has no partition-ordering equivalent, `pattern_conflict` names two competing routes with no rule to pick. Partition ordering dependencies differ by CSS. See [`dt-css-001`](../../knowledge-base/migration/kb-css-routing.md#dt-css-001). |
| `SHARED_LINE_COMPLEX` | context too variable | Producer: `analyzers/shared_line.py:137` (analyzer-owned — no mapper produces this type). Shared-line vs virtual-extension vs Call Park are three different Webex constructs with three different operator semantics; the right one depends on whether the line is being used for monitoring, a barge target, or a true multi-appearance identity. See [`dt-feat-002`](../../knowledge-base/migration/kb-feature-mapping.md#dt-feat-002). |
| `CALLING_PERMISSION_MISMATCH` (populated case) | context too variable | The default rule covers only `assigned_users_count == 0` (see [§default-rule-calling-permission-mismatch-assigned-users-count-0](#default-rule-calling-permission-mismatch-assigned-users-count-0)). Mismatched CSSes *with* users still reach decision review because `recommend_calling_permission_mismatch` only matches international/premium prefixes and returns `None` for everything else — a deliberate signal that the human must classify the block pattern. See [`dt-css-002`](../../knowledge-base/migration/kb-css-routing.md#dt-css-002). |
| `MISSING_DATA` | context too variable | Most-fired decision type — produced across 7 mappers (`feature_mapper.py`, `voicemail_mapper.py`, `snr_mapper.py`, `routing_mapper.py`, `monitoring_mapper.py`, `user_mapper.py`, `line_mapper.py`) plus `analyzers/missing_data.py:167`. `recommend_missing_data` at `recommendation_rules.py:38` deliberately returns `None` whenever `dependent_count > 0` or `object_type` is `location`, `trunk`, or `route_group`. Auto-skipping infrastructure cascades into blocking everything that depends on it; the rule refuses to make that call. |
| `AUDIO_ASSET_MANUAL` | context too variable | Producers: `moh_mapper.py:77` (Music-on-Hold custom sources) and `announcement_mapper.py:92` (AA greetings and queue comfort/whisper announcements). `recommend_audio_asset_manual` returns `accept` for customer-facing audio (`AA_GREETING`, `QUEUE_COMFORT`, `QUEUE_WHISPER`) and `use_default` for low-usage MOH. The split is a brand/UX decision — auto-defaulting MOH org-wide would silently strip a feature some customers actively rely on. |
| `DN_AMBIGUOUS` | no safe single answer | Producers: `line_mapper.py:149` (mapping-time E.164 ambiguity) and `analyzers/dn_ambiguity.py:100` (cross-object sweep for any line still classified `AMBIGUOUS`). `recommend_dn_ambiguous` returns `assign` only when `owner_count == 1` or `primary_owner` is set; the shared-across-many-users case is genuinely ambiguous and must be human-resolved. User/device DN ownership must be explicit. See [`dt-id-001`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-001). |
| `EXTENSION_CONFLICT` | no safe single answer | Producer: `analyzers/extension_conflict.py:138`. Webex enforces per-location extension uniqueness; CUCM does not. `recommend_extension_conflict` uses an `appearances` count heuristic but returns `None` on a tie — and `keep_a` vs `keep_b` vs `renumber` vs `virtual_line` rewrite the line-to-owner binding that device layouts and shared-line analysis depend on. Shares the kb-* entry with DN ownership: [`dt-id-001`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-001). |
| `DUPLICATE_USER` | no safe single answer | Two producers: `analyzers/duplicate_user.py:120` (CUCM-internal duplicates by email + name) and `preflight/checks.py` (planned CUCM users that already exist in the target Webex org). `recommend_duplicate_user` returns `merge` only on `email_match` or `userid_match` and `keep_both` for everything else; in practice the operator usually has to verify the merge target with the customer's identity team. See [`dt-id-002`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-002). |
| `NUMBER_CONFLICT` | no safe single answer | Producer: preflight sibling of `DUPLICATE_USER`. Detects E.164/extension collisions between planned CUCM resources and what is already provisioned in the target Webex org. There is no automatic answer for "the customer already owns this DID" — porting strategy, CPN routing, and cutover sequencing all depend on which side is authoritative. Shares the kb-* entry with `DUPLICATE_USER`: [`dt-id-002`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-002). |

## Score Weights and the Calibration Disclaimer

The migration complexity score (`wxcli cucm report`) is a 0-100 number computed from eight weighted factors. Weights live in the `WEIGHTS` dict at `src/wxcli/migration/report/score.py:17` and must sum to 100. They were chosen at design time to reflect what the team believed would predict effort — none of them have been fit against real migrations yet.

### The Eight Factors

| Factor | Weight | What this measures |
|--------|--------|--------------------|
| CSS Complexity | 20 | CSS count, average partition depth, and `CSS_ROUTING_MISMATCH` / `CALLING_PERMISSION_MISMATCH` decisions. CSS dial-plan rewriting is the highest-touch part of most migrations. |
| Feature Parity | 17 | Ratio of `FEATURE_APPROXIMATION` decisions to total CUCM features (hunt groups, call queues, AAs, call park, pickup, paging). Approximations need design conversations with the customer. |
| Device Compatibility | 15 | Mix of native MPP / convertible / incompatible devices, weighted so incompatible (hardware replacement) hurts more than convertible (firmware flash). |
| Decision Density | 15 | Unresolved decisions per total object, log-scaled. Captures "how much hand-tuning the operator still owes" rather than absolute count. |
| Scale | 10 | `log10(user_count) * 10`, capped at 100. Deliberately log-scaled so a 5,000-user customer doesn't flatten the rest of the score. |
| Shared Line Complexity | 10 | Sum of `shared_line` objects and `SHARED_LINE_COMPLEX` decisions. Webex shared-line semantics are looser than CUCM's, and every shared line is a manual review. |
| Phone Config Complexity | 8 | Button-template / softkey / per-line override volume — the Tier 2 phone-config pipeline producers. |
| Routing Complexity | 5 | Trunks + route groups + translation patterns. Lowest weight because the routing pipeline is mostly mechanical once trunks are designed. |

The weights are listed here in the same order as the dict; their sum (100) is enforced by the test suite.

### What `SCORE_CALIBRATED = False` Means

`src/wxcli/migration/report/score.py:50` declares `SCORE_CALIBRATED: bool = False`. This is the source of truth — it propagates into `ScoreResult.calibrated` (`score.py:60`) and from there into the rendered report. While it stays `False`, every report carries an "uncalibrated" disclaimer block in the executive summary, rendered by `src/wxcli/migration/report/executive.py:127-135`:

> **Note:** This complexity score uses design-time weights that have not yet been calibrated against completed migrations. Use as a relative indicator, not an absolute measure.

The disclaimer is a `callout info` block that appears immediately below the score gauge on Page 1 of the executive summary. It is conditional on `not result.calibrated` — flipping `SCORE_CALIBRATED` to `True` removes the block from every subsequent report without any other code change.

### When to Recalibrate

When sufficient real-migration data exists to fit the weights against actual operator effort. "Sufficient" means: enough completed migrations have been logged with both a headline score and an actual-hours record for a statistical fit between the eight factor inputs and reported effort to be meaningful. Once that fit produces weight adjustments that the team accepts, edit `WEIGHTS` and flip `SCORE_CALIBRATED` to `True` in the same commit.

What calibration would look like: a regression (or comparable statistical fit) between the eight factor raw scores and operator-reported effort hours across N completed migrations, where the residuals are small enough to justify replacing the design-time weights. The methodology — what fit to use, what N is large enough, how to handle outliers — is **out of scope for this runbook** (per spec D9). This section only documents the flag, the factors, and where the disclaimer renders.

### Where Calibration Data Comes From

The operational instructions for logging calibration data live in [operator-runbook.md §Calibration Data Capture](operator-runbook.md#calibration-data-capture), not here. That section tells the operator what to record during a live migration so the data exists when the calibration workstream opens.

## What Is and Isn't Tunable

_TBD — Wave 3 Phase D Task D5_

## Per-Decision Overrides

_TBD — Wave 3 Phase D Task D5 — when to use `wxcli cucm decide` vs an auto-rule_

## Tuning Recipes

### Recipe 1: Small SMB, single location, 10–50 users
_TBD — Wave 3 Phase D Task D6_

### Recipe 2: Hunt-list / call-queue heavy migration
_TBD — Wave 3 Phase D Task D6 (the highest-frequency live decision type — see spec D5)_

### Recipe 3: CSS-heavy customer with strict partition ordering
_TBD — Wave 3 Phase D Task D6_

### Recipe 4: Cert-based trunk customer
_TBD — Wave 3 Phase D Task D6_

### Recipe 5: Analog-gateway-heavy customer
_TBD — Wave 3 Phase D Task D6_
