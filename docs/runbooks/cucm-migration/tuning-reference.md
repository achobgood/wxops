<!-- Last verified: 2026-04-07 against branch claude/identify-missing-questions-8Xe2R, Layer 1 commits 1940991 + 3c55241 -->

# CUCM-to-Webex Configuration Tuning Reference

> **Audience:** Operator configuring for a new customer environment OR debugging a recurring decision pattern.
> **Reading mode:** Reference, scanned by config key or recipe.
> **See also:** [Operator Runbook](operator-runbook.md) · [Decision Guide](decision-guide.md)

## Table of Contents

1. [config.json: Every Key Explained](#configjson-every-key-explained)
2. [Auto-Rule Reference](#auto-rule-reference)
   - [Non-Auto-Ruled DecisionTypes](#non-auto-ruled-decisiontypes)
3. [Score Weights](#score-weights)
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

> One entry per `DEFAULT_CONFIG` key. Anchor slugs are validated by `test_config_key_coverage.py` — update both sides if you rename a key.

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

See §[Auto-Rule Reference](#auto-rule-reference) below for the full treatment — per-rule walkthroughs, the add-your-own pattern, and the list of decision types that intentionally have no default rule.

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

### recording-vendor

**Default:** `"Webex"` (from `src/wxcli/commands/cucm_config.py:73`)
**What it controls:** The call recording vendor name written into the deployment plan during export. Webex Calling includes built-in call recording at no extra cost; per-user recording settings are enabled automatically during execution.
**When to change:** Set to a third-party vendor name (e.g., `"Dubber"`, `"Imagicle"`) if the customer uses an external recording platform instead of Webex's built-in recording. Leave as `"Webex"` for most migrations.
**Consumed by:** `src/wxcli/migration/advisory/advisory_patterns.py:1182` — referenced in the call-recording advisory pattern narrative. The export pipeline reads it from config when generating per-user recording settings.

### enable-device-settings-migration

**Type:** boolean
**Default:** `true`
**Effect:** When `false`, DeviceSettingsMapper is skipped entirely. No device_settings_template objects are created and no device settings are applied during execution.

### bulk-device-threshold

**Default:** `100` (from `src/wxcli/commands/cucm_config.py`)
**What it controls:** Device count at/above which the planner's post-expansion `_optimize_for_bulk()` pass replaces per-device `device:configure_settings`, `device_layout:configure`, and `softkey_config:configure` operations with Webex bulk job submissions (`callDeviceSettings`, `applyLineKeyTemplate`, `dynamicDeviceSettings`) plus a trailing `rebuildPhones` job per location. `device:create` is never replaced — there is no bulk device-create API. Full design in `docs/superpowers/specs/2026-04-10-bulk-operations.md`.
**When to change:** Set to `0` to force bulk optimization for every migration regardless of size. Set to a very large value (`999999`) to disable bulk entirely — required for Webex for Government tenants because `rebuildPhones` is not supported on FedRAMP. Most migrations should leave it at `100`, which is the device count at which per-device operations stop finishing in under ten minutes and bulk jobs start paying back their polling overhead.
**Example non-default:**
```json
{"bulk_device_threshold": 999999}
```
**Consumed by:** `src/wxcli/migration/execute/planner.py:expand_to_operations()` — the threshold is read from project config and passed to `_optimize_for_bulk()` as a post-expansion pass. The engine then dispatches bulk submissions via `execute_bulk_op()` and polls them via `poll_job_until_complete()`.

## Auto-Rule Reference

> Anchor convention for the 7 default rules: `default-rule-` plus the slug-form of the rule's `type` field, with `-<match-key>-<match-value>` appended when a `match` filter is present (e.g., `default-rule-calling-permission-mismatch-assigned-users-count-0`). Validated by `test_default_auto_rules_coverage.py`.

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

### default-rule-missing-data-is-on-incompatible-device-true

**Rule:**
```json
{
  "type": "MISSING_DATA",
  "match": {"is_on_incompatible_device": true},
  "choice": "skip"
}
```
**What it does:** Every `MISSING_DATA` decision whose context reports `is_on_incompatible_device == true` (a data-quality gap on a device that has already been flagged `DEVICE_INCOMPATIBLE` and will be skipped anyway) is resolved to `skip`. The `is_on_incompatible_device` field is written by `enrich_cross_decision_context()` during `analysis_pipeline` step 3.5, which cross-references every non-stale `MISSING_DATA` decision against the current set of `DEVICE_INCOMPATIBLE` decisions before auto-rules fire. Data-quality gaps on devices the pipeline is migrating still reach decision review — this rule only fires on the narrow intersection of "missing data" + "already being skipped".
**Why safe as default:** Fixing missing data on a device that will be excluded from the migration is wasted operator work — the data is thrown away at export time regardless. Without this rule, a single incompatible phone would generate both a `DEVICE_INCOMPATIBLE` decision AND a pending `MISSING_DATA` decision for the same object, forcing the operator to resolve the same underlying choice twice. This is the narrow Bug F shape the auto-rule architecture unification was built to fix: the rule only matches the `is_on_incompatible_device=true` subset, so `MISSING_DATA` decisions on devices that ARE being migrated still surface for human review with no auto-skip.
**When to remove:** Remove this rule for customers whose migration strategy calls for fixing data-quality gaps on incompatible devices before deciding whether to migrate them — for example, a phased migration where some `DEVICE_INCOMPATIBLE` decisions might be reversed after discovery of missing `mac`/`description`/`devicePool` values. Also remove for audit-heavy environments where every `MISSING_DATA` gap must be recorded as explicitly reviewed (not auto-skipped) even on skipped devices, so the compliance record shows operator acknowledgement.
**See also:** `dt-user-001`

### Non-Auto-Ruled DecisionTypes

The 8 default auto-rules above are the *only* `DecisionType` values that the pipeline resolves on its own. Every other type — 14 in total when you count `CALLING_PERMISSION_MISMATCH` (whose default rule narrowly matches `assigned_users_count == 0` and so leaves the populated case unresolved) — flows into the human decision-review queue with no shortcut. The absence of an auto-rule on these types is intentional, not an omission. Each one falls into one of three buckets: the decision requires *judgment too high* for a declarative match (the right answer depends on customer-specific tradeoffs the pipeline cannot see), the decision's *context is too variable* to capture in a single rule without burying real signals, or there is *no safe single answer* — multiple valid choices exist and silently picking one would violate operator trust. The table below enumerates all 14, classifies each, and forward-links to the canonical decision-guide entry for the producer logic and recommendation algorithm.

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
| `MISSING_DATA` (non-incompatible-device case) | context too variable | Most-fired decision type — produced across 7 mappers (`feature_mapper.py`, `voicemail_mapper.py`, `snr_mapper.py`, `routing_mapper.py`, `monitoring_mapper.py`, `user_mapper.py`, `line_mapper.py`) plus `analyzers/missing_data.py:167`. The default rule covers only `is_on_incompatible_device == true` (see [§default-rule-missing-data-is-on-incompatible-device-true](#default-rule-missing-data-is-on-incompatible-device-true)) — gaps on devices the pipeline is migrating still reach decision review. `recommend_missing_data` at `recommendation_rules.py:38` deliberately returns `None` whenever `dependent_count > 0` or `object_type` is `location`, `trunk`, or `route_group`. Auto-skipping infrastructure cascades into blocking everything that depends on it; the rule refuses to make that call. |
| `AUDIO_ASSET_MANUAL` | context too variable | Producers: `moh_mapper.py:77` (Music-on-Hold custom sources) and `announcement_mapper.py:92` (AA greetings and queue comfort/whisper announcements). `recommend_audio_asset_manual` returns `accept` for customer-facing audio (`AA_GREETING`, `QUEUE_COMFORT`, `QUEUE_WHISPER`) and `use_default` for low-usage MOH. The split is a brand/UX decision — auto-defaulting MOH org-wide would silently strip a feature some customers actively rely on. |
| `DN_AMBIGUOUS` | no safe single answer | Producers: `line_mapper.py:149` (mapping-time E.164 ambiguity) and `analyzers/dn_ambiguity.py:100` (cross-object sweep for any line still classified `AMBIGUOUS`). `recommend_dn_ambiguous` returns `assign` only when `owner_count == 1` or `primary_owner` is set; the shared-across-many-users case is genuinely ambiguous and must be human-resolved. User/device DN ownership must be explicit. See [`dt-id-001`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-001). |
| `EXTENSION_CONFLICT` | no safe single answer | Producer: `analyzers/extension_conflict.py:138`. Webex enforces per-location extension uniqueness; CUCM does not. `recommend_extension_conflict` uses an `appearances` count heuristic but returns `None` on a tie — and `keep_a` vs `keep_b` vs `renumber` vs `virtual_line` rewrite the line-to-owner binding that device layouts and shared-line analysis depend on. Shares the kb-* entry with DN ownership: [`dt-id-001`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-001). |
| `DUPLICATE_USER` | no safe single answer | Two producers: `analyzers/duplicate_user.py:120` (CUCM-internal duplicates by email + name) and `preflight/checks.py` (planned CUCM users that already exist in the target Webex org). `recommend_duplicate_user` returns `merge` only on `email_match` or `userid_match` and `keep_both` for everything else; in practice the operator usually has to verify the merge target with the customer's identity team. See [`dt-id-002`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-002). |
| `NUMBER_CONFLICT` | no safe single answer | Producer: preflight sibling of `DUPLICATE_USER`. Detects E.164/extension collisions between planned CUCM resources and what is already provisioned in the target Webex org. There is no automatic answer for "the customer already owns this DID" — porting strategy, CPN routing, and cutover sequencing all depend on which side is authoritative. Shares the kb-* entry with `DUPLICATE_USER`: [`dt-id-002`](../../knowledge-base/migration/kb-identity-numbering.md#dt-id-002). |

## Advisory Pattern Heuristics: Call Intercept Candidates

CUCM has no native call-intercept feature. The advisory `call_intercept_candidates` (Pattern 30 in `advisory/advisory_patterns.py`, severity `MEDIUM`, category `out_of_scope`, recommendation `accept`) surfaces CUCM configurations that *approximate* Webex intercept so the operator can re-configure them manually after cutover. The detection is entirely SQL-driven — it runs inside the Tier 4 extractor at `discover` time, not at `analyze` time — and the advisory itself is a read-over-the-store summary, not a detector.

**Producers:**

- `src/wxcli/migration/cucm/extractors/tier4.py:_extract_intercept_candidates` — runs two SQL queries and writes rows to `raw_data["tier4"]["intercept_candidates"]`.
- `src/wxcli/migration/transform/normalizers.py:normalize_intercept_candidate` — converts each raw row into a `MigrationObject` with `canonical_id = "intercept_candidate:{dn}:{partition}"`.
- `src/wxcli/migration/transform/cross_reference.py:_build_intercept_refs` — wires each candidate to its owning user via the `user_has_intercept_signal` relationship.
- `src/wxcli/migration/transform/mappers/call_settings_mapper.py` (Pass 2 block) — enriches each matched user's `call_settings.intercept = {detected, signal_type, forward_destination, voicemail_enabled}`.
- `src/wxcli/migration/advisory/advisory_patterns.py:detect_call_intercept_candidates` — reads `store.get_objects("intercept_candidate")`, groups by `signal_type`, emits one `AdvisoryFinding` per run.
- `src/wxcli/migration/report/appendix.py:_intercept_candidates` (Section Y) + `report/executive.py` (conditional `Intercept Candidates` stat card on Page 2).

**Detection SQL (`cucm/extractors/tier4.py`, not config-driven):**

- `_BLOCKED_PARTITION_SQL` matches DNs whose partition **name** (not any boolean field) matches `LOWER(rp.name) LIKE '%intercept%' OR '%block%' OR '%out_of_service%' OR '%oos%'`. Joins `numplan → routepartition → devicenumplanmap → device → enduser` to resolve the owning user. Produces `signal_type="blocked_partition"`.
- `_CFA_VOICEMAIL_SQL` matches DNs with `callforwarddynamic.cfadestination != ''` and `cfavoicemailenabled='t'` where `NOT EXISTS` a registered phone behind the line (the `NOT EXISTS` subquery filters on `device.tkclass=1 AND device.tkstatus_registrationstate=2`). Produces `signal_type="cfa_voicemail"`.
- The extractor de-duplicates by DN (a DN hit by both queries is stored once, with the `blocked_partition` signal taking precedence because it runs first). Rows are stored as dicts with keys `userid`, `dn`, `partition`, `signal_type`, `forward_destination`, `voicemail_enabled`.

**What the advisory function actually does:** Reads `store.get_objects("intercept_candidate")`. If empty, returns `[]` (pattern is silent on clean stores). Otherwise, it groups rows by `signal_type`, builds a summary like `"N users with intercept-like configurations"`, formats a detail sentence of the form `"N users have intercept-like configurations in CUCM (M via blocked partition, P via cfa voicemail). Configure Webex intercept manually post-migration."`, and returns exactly one `AdvisoryFinding(pattern_name="call_intercept_candidates", severity="MEDIUM", category="out_of_scope", affected_objects=[…all canonical_ids…])`. It does not re-scan route patterns, CSS assignments, or phone registration state — all of that work happened in the extractor.

**Tuning guidance.** The pipeline does not expose a config key for this heuristic — the partition-name glob list and the CFA-to-voicemail predicate are hard-coded in `tier4.py` at SQL-literal level. If a customer's environment uses a partition naming convention outside the four defaults (`intercept`, `block`, `out_of_service`, `oos`), edit `_BLOCKED_PARTITION_SQL` directly and add additional `LOWER(rp.name) LIKE '%…%'` clauses. Similarly, if the `NOT EXISTS` predicate on `device.tkclass=1 AND tkstatus_registrationstate=2` is too strict (some tenants keep a placeholder CSF device registered on terminated-user lines), relax or remove the `NOT EXISTS` block in `_CFA_VOICEMAIL_SQL`. There is **no** per-decision recommendation rule for call intercept in `recommendation_rules.py` (confirmed: `_PROFESSIONAL_FEATURES` mentions `"intercept"` but the dispatch table has no call-intercept rule) — the advisory itself carries the only recommendation (`accept`), so there is no per-decision-type rule to tune.

**False positives to expect.** The blocked-partition glob will catch dial-plan restriction partitions named `BlockInternational_PT`, `Block911_PT`, etc., even though those should migrate as Webex calling permissions rather than as intercept. The CFA-to-voicemail predicate will catch users who set Call Forward All to their voicemail pilot as an ordinary "do not disturb" preference on an unused spare line. The MEDIUM severity reflects the operational impact of a *true* miss (a terminated employee becoming reachable again), not per-candidate confidence; most individual candidates are benign. Triage belongs in the operator runbook's Call Intercept Verification step, not in the extractor.

**What MEDIUM severity means.** MEDIUM is advisory-only. The pattern does not write a `DecisionType`, produces no blocking decisions, is not covered by any auto-rule, and does not affect the complexity score (the `feature_parity` factor counts `FEATURE_APPROXIMATION` decisions — intercept candidates do not become approximations). `preflight` and `plan` run to completion regardless of candidate count. The severity simply signals to the `cucm-migrate` skill's Phase A advisory bundle that this is worth a deliberate acceptance rather than a rubber-stamp.

## Score Weights

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
| Phone Config Complexity | 8 | Button-template count, KEM-equipped layouts, unmapped button types, and softkey template count — the Tier 2 phone-config pipeline producers. |
| Routing Complexity | 5 | Trunks + route groups + translation patterns. Lowest weight because the routing pipeline is mostly mechanical once trunks are designed. |

The weights are listed here ordered by weight descending (matching the report's own factor bars, which sort by descending score); their sum (100) is enforced by the test suite.

### What `SCORE_CALIBRATED = False` Means

`src/wxcli/migration/report/score.py:50` declares `SCORE_CALIBRATED: bool = False`. This is the source of truth — it propagates into `ScoreResult.calibrated` (`score.py:60`) and from there into the rendered report. While it stays `False`, every report carries an "uncalibrated" disclaimer block in the executive summary, rendered by `src/wxcli/migration/report/executive.py:127-135`:

> **Note:** This complexity score uses design-time weights that have not yet been calibrated against completed migrations. Use as a relative indicator, not an absolute measure.

The disclaimer is a `callout info` block that appears immediately below the score gauge on Page 1 of the executive summary. It is conditional on `not result.calibrated` — flipping `SCORE_CALIBRATED` to `True` removes the block from every subsequent report without any other code change.

### When to Recalibrate

When sufficient real-migration data exists to fit the weights against actual operator effort. "Sufficient" means: enough completed migrations have been logged with both a headline score and an actual-hours record for a statistical fit between the eight factor inputs and reported effort to be meaningful. Once that fit produces weight adjustments that the team accepts, edit `WEIGHTS` and flip `SCORE_CALIBRATED` to `True` in the same commit.

What calibration would look like: a statistical comparison between the eight factor raw scores and operator-reported effort hours across N completed migrations, sufficient to show the weights produce predictions whose residuals are small enough to justify replacing the design-time defaults. The methodology — what fit to use, what N is large enough, how to handle outliers — is **out of scope for this runbook** (per spec D9). This section only documents the flag, the factors, and where the disclaimer renders.

### Where Calibration Data Comes From

The operational instructions for logging calibration data live in [operator-runbook.md §Calibration Data Capture](operator-runbook.md#calibration-data-capture), not here. That section tells the operator what to record during a live migration so the data exists when the calibration workstream opens.

### Calibration Handoff Procedure

This subsection ties together two workstreams that share the word "calibration"
but measure different things:

- **Score calibration** — the migration-complexity score's factor weights
  (`src/wxcli/migration/report/score.py:17`) fit against real operator effort.
  This is what `SCORE_CALIBRATED` is about. The data source is the manual
  `calibration-log.md` described in
  [operator-runbook.md §Calibration Data Capture](operator-runbook.md#calibration-data-capture).
- **Agent-efficiency validation** — periodic manual QA. Invoke
  `wxc-calling-builder` with `/cucm-migrate` against a test project and
  review the agent's decision-review behavior. This is a human judgment
  exercise, not an automated regression guard — LLM non-determinism makes
  automated baselines unreliable.

**To flip `SCORE_CALIBRATED` to `True`:**

1. Accumulate 3+ real-migration entries in `calibration-log.md` following the
   protocol at
   [operator-runbook.md §Calibration Data Capture](operator-runbook.md#calibration-data-capture).
   Each entry needs the headline score, actual hours, and environment
   characteristics.
2. Confirm that a statistical fit of the eight factor inputs against logged
   effort hours produces weight adjustments the team accepts. See
   [§When to Recalibrate](#when-to-recalibrate) above for the shape of the fit;
   the methodology is deliberately out of scope for this runbook.
3. Update `WEIGHTS` in `src/wxcli/migration/report/score.py:17` with the fitted
   weights (the fit and the flag flip should land in the same commit).
4. Set `SCORE_CALIBRATED = True` in `src/wxcli/migration/report/score.py:50`.
5. Remove the uncalibrated-disclaimer callout from
   `src/wxcli/migration/report/executive.py` (search for `calibrated` in that
   file — the conditional block at approximately lines 127-135 guards on
   `not result.calibrated`).
6. Update the `<!-- Last verified: ... -->` header on this file.

## What Is and Isn't Tunable

The pipeline exposes a deliberate, narrow tuning surface. Anything not listed under "tunable" below is intentionally locked and should not be changed without a code-review conversation.

**What IS tunable:**

- **`config.json` keys** — the nine keys documented in [§config.json: Every Key Explained](#configjson-every-key-explained). These are the per-project knobs the operator is expected to set: `country-code`, `default-language`, `default-country`, `outside-dial-digit`, `create-method`, `include-phoneless-users`, `auto-rules`, `site-prefix-rules`, and `category-rules`.
- **Auto-rules** — both the seven defaults documented in [§Auto-Rule Reference](#auto-rule-reference) and any custom rules the operator adds to `config.json` under `auto_rules`. Match operators (`_lte`, `_gte`, `_contains`, plain/list) are listed in `src/wxcli/migration/transform/rules.py:21-91`.
- **Per-decision overrides via `wxcli cucm decide`** — the one-off escape hatch documented in [§Per-Decision Overrides](#per-decision-overrides) immediately below.

**What is NOT tunable (and why):**

- **Severity is NOT tunable.** Severity (`HIGH` / `MEDIUM` / `LOW`) is set by the producing mapper or analyzer at decision-creation time — for example `MissingDataAnalyzer._highest_severity()` at `src/wxcli/migration/transform/analyzers/missing_data.py:135`. There is no config key, no rule, and no CLI flag that re-grades severity after the fact. This is a documented limitation, not a bug: severity reflects the technical impact of the underlying CUCM artifact, not the operator's appetite for risk on a given migration. If a class of decisions is consistently mis-graded, that's a code change to the producer, not a tuning knob.
- **Score weights are tunable in code, NOT via `config.json`.** The `WEIGHTS` dict at `src/wxcli/migration/report/score.py:17` is intentionally code-only. Weights are a calibration artifact that should change exactly once — when sufficient real-migration data exists to fit them — not per-project, not per-customer, and not as a knob to make a particular score look better. See [§Score Weights](#score-weights) for the full rationale.
- **`SCORE_CALIBRATED` is tunable only by flipping the flag in code.** It lives at `src/wxcli/migration/report/score.py:50`. Flipping it from `False` to `True` removes the uncalibrated disclaimer from every subsequent report and is a one-way claim about the trustworthiness of the score. **Don't flip it speculatively** — the flip should land in the same commit as the calibrated weights and should be backed by the calibration evidence described in [§When to Recalibrate](#when-to-recalibrate).
- **`DecisionType` options are NOT tunable.** The set of choices presented for a decision (e.g. `provide_data` / `skip` / `manual` for `MISSING_DATA`) is hardcoded in the producing module's option-generation logic — for `MISSING_DATA`, see `analyzers/missing_data.py:149-165`. There is no config to add, remove, or rename options. If a new option is needed, it's a code change to the producer (and almost always needs a matching `recommend_*` rule and an advisory pattern, so it's not a small change).

The dividing line: **per-project knobs go in `config.json`**, **per-migration overrides go through `wxcli cucm decide`**, and **everything that affects how decisions are graded or what choices exist requires a code change**. That separation is why the tuning surface stays small enough to reason about across hundreds of migrations.

## Per-Decision Overrides

`wxcli cucm decide` is the operator's escape hatch for resolving decisions that aren't covered by an auto-rule. It supports both single-decision and batch resolution, and the choice between `decide` and an auto-rule is the most common tuning question during a live migration.

### CLI usage

The command (verified via `wxcli cucm decide --help`):

```
Usage: wxcli cucm decide [OPTIONS] [DECISION_ID] [CHOICE]

  Resolve a single decision or batch-resolve by type.

Arguments:
  decision_id      [DECISION_ID]  Decision ID to resolve (e.g. D001)
  choice           [CHOICE]       Chosen option ID

Options:
  --type        -t   TEXT  Decision type for batch resolve
  --all                    Batch resolve all matching decisions
  --choice           TEXT  Choice for batch resolve
  --apply-auto             Apply all auto-resolvable decisions
  --yes         -y         Skip confirmation prompt (for non-interactive use)
  --project     -p   TEXT  Project name
```

Three usage modes:

1. **Single decision** — pass the decision ID and the chosen option ID positionally:
   ```bash
   wxcli cucm decide D042 provide_data -p mig-acme
   ```
2. **Batch by type** — resolve every pending decision of one `DecisionType` to the same choice:
   ```bash
   wxcli cucm decide --type MISSING_DATA --all --choice skip -p mig-acme
   ```
3. **Apply all auto-resolvable** — replay the auto-rules in `config.json` against the current decision set without re-running `analyze`:
   ```bash
   wxcli cucm decide --apply-auto -p mig-acme
   ```

The `--all` flag is required when using `--type` to make batch intent explicit; the `/cucm-migrate` skill also exposes batch-accept prompts that wrap this same command for interactive review.

### When to use `decide` vs an auto-rule

The two mechanisms exist for two different timescales:

| Use `wxcli cucm decide` when… | Use an auto-rule when… |
|--|--|
| The override is **one-off**: this specific decision, this specific migration, no expectation of seeing it again. | The override describes a **recurring pattern** — either across many decisions in the current migration, or across future migrations. |
| You're working a single ambiguous case the recommender flagged with no clear answer. | You can name a property of the decision's context (`object_type`, `cucm_model`, `dn_length`, etc.) that uniquely identifies the class of decisions you want resolved the same way. |
| You don't want this answer applied to any future migration. | You want the answer captured in `config.json` so the next `analyze` run for this project — or a sibling project that copies the config — resolves it automatically. |

The mental model: **`decide` writes to the decision row in the SQLite store**, **auto-rules write to `config.json`** and re-resolve on every `analyze` pass. If you find yourself running `decide` more than two or three times for decisions that look the same, stop and write an auto-rule instead.

### Worked example: 30 `MISSING_DATA` decisions on already-incompatible devices

Scenario: `wxcli cucm decisions` shows 30 pending `MISSING_DATA` decisions, all of them `object_type = "phone"`, all on devices that are also flagged `DEVICE_INCOMPATIBLE` and slated for skip. The customer has no intention of supplying the missing fields for hardware that isn't migrating.

The naive approach is 30 separate commands:

```bash
wxcli cucm decide D012 skip -p mig-acme
wxcli cucm decide D027 skip -p mig-acme
wxcli cucm decide D031 skip -p mig-acme
# … 27 more …
```

The right approach is one auto-rule. The `MissingDataAnalyzer` puts these fields in every decision's context (`src/wxcli/migration/transform/analyzers/missing_data.py:143-147`):

```python
context = {
    "object_type": object_type,      # "phone", "user", "line", …
    "canonical_id": canonical_id,
    "missing_fields": missing_names,
}
```

So `object_type` is a real, matchable context key. Add this rule to `config.json`:

```json
{
  "auto_rules": [
    {
      "type": "MISSING_DATA",
      "match": { "object_type": "phone" },
      "choice": "skip"
    }
  ]
}
```

Then re-run analyze (or `wxcli cucm decide --apply-auto -p mig-acme` to replay the rules without a full re-analyze) and all 30 decisions resolve in one pass. The rule travels with the project: a follow-up run after a CUCM re-discovery still resolves the same class automatically, and the operator's review queue stays focused on decisions that actually need a human.

The example above matches **all** phone-typed `MISSING_DATA` decisions regardless of which fields are missing. That is usually what you want when the operator intent is "skip every phone with an incomplete CUCM record" — but it's a blunt instrument. A user-scoped variant works the same way:

```json
{
  "type": "MISSING_DATA",
  "match": { "object_type": "user" },
  "choice": "skip"
}
```

**Why you can't filter on `missing_fields` today.** The `MissingDataAnalyzer` writes `missing_fields` into the context as a list of field names (e.g., `["model"]` or `["model", "description"]`). The plain-key branch of the auto-rule matcher at `src/wxcli/migration/transform/rules.py:79-89` is designed for the inverse case — a *scalar* context value matched against a *list of acceptable values*:

```python
if isinstance(expected, list):
    if actual not in expected:   # actual is a single value, expected is a list
        return False
```

This works for rules like `{"cucm_model": ["7841", "7861"]}` where `actual` is the string `"7841"` and `expected` is the list of acceptable strings. It does **not** work for matching a list-valued context field. Concretely, `["model"] in ["model"]` evaluates to `False` in Python because the only element of `["model"]` is the string `"model"`, not the list `["model"]`. There is currently **no operator** that can express "decisions where `model` is among the missing fields"; implementing that would require a new `_contains_any` (or similar) operator in `transform/rules.py`. Until then, the only supported MISSING_DATA auto-rules are the scalar-keyed ones above.

**Workaround for surgical list-value matching.** If you genuinely need to bulk-skip only the subset of phones missing a *specific* field, use the `/cucm-migrate` skill's bulk-accept prompts on the filtered review queue rather than an auto-rule — the skill walks through the decisions interactively and lets you accept a slice without touching `config.json`. The rule engine's full operator vocabulary lives in `transform/rules.py:21-91`.

## Tuning Recipes

### Recipe 1: Small SMB, single location, 10–50 users

This is the *baseline* recipe — it documents what the defaults assume. If your customer matches the characteristics below, you do not need to touch `config.json`; the 7 default auto-rules (see §[Auto-Rule Reference](#auto-rule-reference)) cover everything that can be resolved automatically, and the review queue will be short enough to walk through in a single sitting.

**Source environment characteristics:**
- Single CUCM device pool (or 1 real + 1 stray "Default" pool).
- 10–50 end users, 10–50 phones (classic 7800/8800 MPP or convertible SKUs — no SCCP-only units).
- Minimal CSS complexity: 1–3 CSSes, no partition ordering dependencies, blocking patterns limited to the standard 900/976/international prefixes.
- No hunt lists, or 1–2 small hunt lists (< 10 agents each, Top Down or Circular algorithm, no queuing features).
- No multi-site routing, no intercluster trunks, no analog fax gateway farms.
- One SIP trunk to PSTN (CCPP or a single LGW).

**Config knobs to set:** none beyond `country_code` / `default_language` / `default_country` for non-NANP customers (see §[config.json](#configjson-every-key-explained)).
```json
{
  "country_code": "+1",
  "default_language": "en_us",
  "default_country": "US"
}
```

**Auto-rules to add or remove:** the 7 defaults — no additions, no removals. All of them are relevant at SMB scale and none of them hide signal the operator needs to see at this size.

**Decisions to expect:**
- `DEVICE_FIRMWARE_CONVERTIBLE`: auto-resolved to `convert` for every convertible-SKU phone (typically the full device fleet).
- `DEVICE_INCOMPATIBLE`: 0–2 stragglers if any — auto-resolved to `skip`.
- `BUTTON_UNMAPPABLE`: 0–10 per phone if button templates use service URLs — auto-resolved to `accept_loss`.
- `SNR_LOSSY`: 0–3 for users with CUCM Single Number Reach — auto-resolved to `accept_loss`.
- `LOCATION_AMBIGUOUS`: 1–2 decisions if CUCM has a stray device pool for infrastructure (CTI manager, CUBE) — needs manual resolution.
- `FEATURE_APPROXIMATION`: 0–1 if the customer has a small hunt list — usually auto-recommended but still reaches review for operator sign-off.

**Advisory patterns likely to fire:**
- `location_consolidation`: almost always fires — the single-device-pool source collapses into a single Webex location. Accept the advisory and move on.
- `restriction_css_consolidation`: fires when the customer has CUCM-style block CSSes (a `Block_900` partition pinned to every non-exec user). Accept → the blocks become a Webex calling permission policy.

**Manual verification post-migration:**
- Place a test call from one migrated user to another (internal dial plan + E.164).
- Place an outbound call to the PSTN through the trunk and verify CPN.
- Leave a voicemail for a migrated user and confirm delivery + email notification.
- Confirm the hunt list (if present) rings the expected agents in the expected order.

**See also:** [`dt-dev-001`](decision-guide.md#device-incompatible) · [`dt-dev-002`](decision-guide.md#device-firmware-convertible) · [`dt-dev-003`](decision-guide.md#button-unmappable) · [`dt-user-002`](decision-guide.md#snr-lossy) · [`dt-loc-001`](decision-guide.md#location-ambiguous) · [`location-consolidation`](decision-guide.md#location-consolidation) · [`restriction-css-consolidation`](decision-guide.md#restriction-css-consolidation)

### Recipe 2: Hunt-list / call-queue heavy migration

This is the recipe for the highest-frequency live decision type. `FEATURE_APPROXIMATION` for hunt pilots is what most real customer migrations spend the most operator time on, because the CUCM-to-Webex mapping is judgment-laden (`hunt_group` vs `call_queue`), the routing-type cap (`SIMULTANEOUS` ≤ 50 agents) is enforced post-migration not pre-migration, and the 5–8 agent ambiguous band is genuinely a coin-flip on the static recommendation. Recipe 2 tunes that pipeline to autoresolve the obvious cases and leave the genuinely-ambiguous ones for the human.

**Source environment characteristics:**
- 30+ hunt lists (CUCM HuntPilot → HuntList → LineGroup chains).
- Mixed distribution algorithms — some `Top Down` / `Circular`, some `Broadcast` (which maps to Webex `SIMULTANEOUS`), occasionally `Longest Idle Time`.
- Agent counts ranging 4–100 per group; at least one queue near or above the 50-agent simultaneous cap.
- A subset of the hunt lists have queueing features enabled (`queueCalls.enabled=true`, `maxCallersInQueue > 0`, overflow destinations set, voicemail-on-no-answer) — these classify as Webex Call Queues, not Hunt Groups.
- A subset are reception-style (small, no queue features, single forwarding fallback) — these classify as Hunt Groups.
- Often paired with one or two CTI Route Points used as IVR-style auto-attendants.

**Config knobs to set:** `country_code` / `default_language` / `default_country` as appropriate for the customer. `category_rules` only if the customer has a non-standard blocking-pattern dial plan that the default heuristic miscategorizes.
```json
{
  "country_code": "+1",
  "default_language": "en_us",
  "default_country": "US",
  "category_rules": [
    {"cucm_pattern": "9.1900[2-9]XXXXXX", "webex_category": "premium"}
  ]
}
```

**Auto-rules to add or remove:** add type-only or `reason`-discriminated rules for the obvious cases. **Read the drift note below before copying this.**
```json
[
  {"type": "FEATURE_APPROXIMATION",
   "match": {"reason": "agent_limit_exceeded", "policy": "SIMULTANEOUS"},
   "choice": "manual"},
  {"type": "FEATURE_APPROXIMATION",
   "match": {"reason": "cti_rp_to_auto_attendant"},
   "choice": "accept"}
]
```

**Drift note — verify match fields against the producer.** The plan that committed this recipe suggested matching on `algorithm`, `agent_count_lte`, and `has_queue_features`, but **none of those fields are placed on the `FEATURE_APPROXIMATION` decision context by `feature_mapper.py`**. `has_queue_features` is a local variable in `_classify_hunt_pilot()` that drives the `HUNT_GROUP` vs `CALL_QUEUE` classification *before* the decision is even created. `algorithm` is the CUCM string ("Top Down", "Broadcast") but only `policy` (the mapped Webex form: `SIMULTANEOUS`, `REGULAR`, `CIRCULAR`, `UNIFORM`, `WEIGHTED`) is stored in context. The fields that *are* on the hunt-pilot agent-limit-exceeded decision context are `hunt_pilot_id`, `name`, `policy`, `agent_count`, `agent_limit`, and `reason="agent_limit_exceeded"`. For the CTI RP → AA decision, the fields are `cti_rp_id`, `name`, `has_script`, and `reason="cti_rp_to_auto_attendant"`. Match against those, not against the spec fields. The example above uses `reason` + `policy` because those are the discriminators that actually exist on the decision context. <!-- Verified against feature_mapper.py:289-296 (hunt) and :531-536 (CTI RP) on 2026-04-07 -->

**Decisions to expect:**
- `FEATURE_APPROXIMATION`: 20–40 total. The two rules above auto-resolve the agent-limit-on-Simultaneous cases (to manual-review) and the CTI-RP-to-AA cases (to accept). Roughly 5–10 are left for manual resolution — usually the 5–8 agent hunt lists that sit in the genuinely-ambiguous `hunt_group` vs `call_queue` band where `recommend_feature_approximation` returns `None`.
- `MISSING_DATA`: a handful — most often hunt list agents whose DN cannot be resolved to a user (the line was never assigned).
- `LOCATION_AMBIGUOUS`: 1–3 if hunt pilot agents span device pools.
- `EXTENSION_CONFLICT`: 0–2 if hunt pilot DNs collide with user DNs across CUCM partitions.

**Advisory patterns likely to fire:**
- `hunt_pilot_reclassification`: fires loudly. The cross-cutting advisor groups all hunt pilots with queue-like behavior and recommends the `call_queue` rebuild path. Accept this advisory before walking the per-decision queue.
- `partition_time_routing`: fires when hunt lists use time-of-day CSS swaps to switch agent groups during business hours. Accept and rebuild as Webex AA business-hours schedules.
- `cumulative_virtual_line_consumption`: may fire if hunt list members include shared lines treated as monitoring-only — those become virtual extensions and add up against the org-wide cap.

**`DT-LIMITS-001` will likely fire** for any queue with `agent_count > 50` whose CUCM algorithm maps to Simultaneous routing. The migration advisor flags it as a routing-type constraint rather than a hard reject — the operator must either split the queue into ≤50-agent shards with overflow chains, or switch the routing type to `WEIGHTED` (≤100 agents) / `CIRCULAR` / `REGULAR` / `UNIFORM` (≤1,000 agents). See [`docs/knowledge-base/migration/kb-webex-limits.md#dt-limits-001`](../../knowledge-base/migration/kb-webex-limits.md#dt-limits-001).

**Manual verification post-migration:**
- For each migrated hunt group: confirm the routing algorithm was preserved (Top Down → REGULAR, Broadcast → SIMULTANEOUS, etc.) and that first-ring lands on the expected agent.
- For each migrated call queue: confirm the overflow chain (queue-full destination, max-wait-time destination, no-agent destination) routes correctly.
- For any queue split because of `DT-LIMITS-001`: confirm each shard's agent set is disjoint and that the overflow chain ties them together as intended.
- Confirm CTI RP → AA migrations have working business-hours and after-hours menus, and that the operator transfer key (`0`) reaches the expected destination.

**See also:** [`dt-feat-001`](decision-guide.md#feature-approximation) · [`dt-data-001`](decision-guide.md#missing-data) · [`dt-loc-001`](decision-guide.md#location-ambiguous) · [`hunt-pilot-reclassification`](decision-guide.md#hunt-pilot-reclassification) · [`partition-time-routing`](decision-guide.md#partition-time-routing) · [`cumulative-virtual-line-consumption`](decision-guide.md#cumulative-virtual-line-consumption)

### Recipe 3: CSS-heavy customer with strict partition ordering

CSS routing is the archetypal "context too variable" decision class. CUCM CSSes resolve overlapping route patterns by *partition order*; Webex Calling does not have partition-order semantics — it uses longest-match routing across the entire dial plan. When the customer's CUCM dial plan depends on partition ordering (e.g., a more-specific allow-pattern in an early partition is intentionally shadowing a broader block-pattern in a later partition), the migration cannot preserve that behavior automatically. Recipe 3 keeps the auto-rules off this surface entirely and steers the operator into the manual partition-decomposition workflow.

**Source environment characteristics:**
- 10+ CSSes, often dozens, with overlapping membership across user populations.
- Partitions whose ordering inside a CSS is load-bearing — removing or reordering one would change which route pattern wins for at least one DN.
- At least one `CSS_ROUTING_MISMATCH` decision expected from `CSSMapper` or `CSSRoutingAnalyzer`.
- Often paired with restriction-style CSSes (block-only) and per-user CSS overrides for executive/operator profiles.
- CUCM-style "allow then block" patterns where the same prefix appears in two partitions with different translation rules.

**Config knobs to set:** defaults. CSS handling is downstream of the standard `country_code` / `default_country` keys; the CSS-heavy structure does not have its own config knob.
```json
{
  "country_code": "+1",
  "default_country": "US"
}
```

**Auto-rules to add or remove:** **none**. Do not add auto-rules for `CSS_ROUTING_MISMATCH`, `CALLING_PERMISSION_MISMATCH`, or any CSS-related type. The §[Non-Auto-Ruled DecisionTypes](#non-auto-ruled-decisiontypes) table classifies CSS_ROUTING_MISMATCH as "context too variable" precisely for this case — partition ordering dependencies differ by CSS, and a single rule cannot capture the difference between a benign overlap and a load-bearing one. Leave the populated case of `CALLING_PERMISSION_MISMATCH` alone too; the default rule narrowly handles only `assigned_users_count == 0`.

**Decisions to expect:**
- `CSS_ROUTING_MISMATCH`: several — one per CSS with branching logic. Each one names the competing patterns and the CSS's intended ordering.
- `CALLING_PERMISSION_MISMATCH`: 0–N depending on how many CSSes have populated assignments. Each one needs the operator to classify the underlying block patterns into Webex categories.
- `MISSING_DATA`: occasionally — if a CSS references a partition that no longer exists or a route pattern with a stale destination.

**Advisory patterns likely to fire:**
- `partition_ordering_loss` (CRITICAL): fires when at least one CSS depends on partition ordering to resolve overlapping patterns. This is the headline finding for a CSS-heavy migration. Accept the advisory and treat the resulting decision queue as a manual partition decomposition.
- `restriction_css_consolidation`: fires when block-only CSSes are detected. These can become Webex calling permission policies instead of dial plans — the rebuild path is straightforward.
- `overengineered_dial_plan`: fires when CUCM patterns match what Webex's built-in extension routing would do anyway — those patterns can be eliminated outright.
- `mixed_css_routing_restriction`: fires when a single CSS contains both routing patterns and restriction patterns — the operator should split the CSS into two Webex constructs (a dial plan + a calling permission policy).

**Manual verification post-migration:**
- For each `CSS_ROUTING_MISMATCH` decision the operator resolved manually: place test calls that exercise both sides of the overlap (the more-specific pattern and the broader pattern) and confirm each call routes to the intended destination.
- For each block-only CSS that became a calling permission policy: place outbound test calls to the blocked categories from a member user and confirm the block.
- Audit the final Webex dial plan against the source CUCM partition list — every CUCM pattern that survived should have a clear Webex equivalent, and every pattern that was eliminated should be documented as either redundant-with-extension-routing or intentionally-dropped.
- Verify per-user CSS overrides for executive/operator profiles came through as the right Webex calling permission tier, not silently flattened to the org default.

**See also:** [`dt-css-001`](decision-guide.md#css-routing-mismatch) · [`dt-css-002`](decision-guide.md#calling-permission-mismatch) · [`partition-ordering-loss`](decision-guide.md#partition-ordering-loss) · [`restriction-css-consolidation`](decision-guide.md#restriction-css-consolidation) · [`overengineered-dial-plan`](decision-guide.md#overengineered-dial-plan) · [`mixed-css`](decision-guide.md#mixed-css)

### Recipe 4: Cert-based trunk customer

Trunk type is immutable after creation in Webex Calling — you cannot convert a Cloud Connected PSTN trunk into a Local Gateway trunk after the fact, and the cert-based authentication chain has to be planned before the trunk is provisioned. Recipe 4 keeps every trunk-related decision in the manual review queue and leans on the cross-cutting advisory patterns to surface the architecture conversation early.

**Source environment characteristics:**
- At least one CUCM SIP trunk configured with TLS + X.509 cert authentication.
- Cert chain terminates either at an upstream carrier (cert-based SIP trunking — Verizon, BT, Telia), at another CUCM cluster (intercluster trunk / ICT), or at a partner-managed CUBE deployment fronting the carrier.
- Often paired with secure SRTP, secure profiles on phone configurations, and a CTL/ITL trust chain that the customer is responsible for migrating to whatever Webex requires post-cut.
- May involve `CallManager-trust` certs that have to be re-issued under a Webex-compatible CA.

**Config knobs to set:** defaults. Trunk authentication does not have a config-knob — every trunk must be reviewed manually because the cert chain, upstream peer, and routing intent are customer-specific.
```json
{
  "country_code": "+1",
  "default_country": "US"
}
```

**Auto-rules to add or remove:** **none**. Trunk creation cannot be auto-resolved. The §[Non-Auto-Ruled DecisionTypes](#non-auto-ruled-decisiontypes) framing — "no safe single answer" — applies in spirit even though the formal decision type is `ARCHITECTURE_ADVISORY` rather than a per-decision producer. Adding an auto-rule for any trunk-adjacent type would suppress the architectural conversation that has to happen before the migration can ship.

**Decisions to expect:**
- Trunk creation decisions emitted by `RoutingMapper`: each SIP trunk is mapped to either a Local Gateway trunk (`LGW`) or a Cloud Connected PSTN trunk (`CCPP`) based on the customer's chosen architecture. The mapper raises a decision when the source CUCM trunk does not give an unambiguous signal.
- `MISSING_DATA`: at minimum the trunk password — `recommend_missing_data` returns `generate` for trunk passwords, but the operator must accept the generated value before execution.
- `ARCHITECTURE_ADVISORY` decisions from the trunk-related advisory patterns (see below). These are bulk-acceptable through the Phase A advisory review.
- `FEATURE_APPROXIMATION` from `routing_mapper.py:471` if any source route pattern uses the `@` macro (national numbering plan) — the cert-trunk customer is more likely than average to have one.

**Advisory patterns likely to fire:**
- `pstn_connection_type` (CRITICAL): classifies the trunk topology into Local Gateway, Cloud Connected PSTN, or Premises-based PSTN. **This pattern drives the entire Webex routing architecture for the customer** — accept it before walking any individual trunk decision.
- `trunk_type_selection`: per-trunk Layer 1 advisory that flags each cert-bearing SIP trunk and surfaces the LGW vs CCPP question per trunk.
- `intercluster_trunk_detection`: fires when at least one trunk terminates at another CUCM cluster (ICT). Webex has no direct ICT analog — the migration design has to either keep the second cluster on CUCM, migrate it together, or replace ICT with a SIP trunk-of-trunks topology.
- `trunk_destination_consolidation`: fires when multiple CUCM trunks point to the same upstream destination. Webex usually wants a single trunk per destination; the rebuild path collapses them.

**Manual verification post-migration:**
- TLS handshake: confirm the new Webex trunk completes a TLS handshake against the upstream peer using the migrated/re-issued cert chain.
- Cert chain validation: walk the chain end-to-end and confirm each intermediate cert is loaded into the appropriate trust store on both sides.
- Outbound call routing: place a call from a migrated user out through the trunk and confirm the call reaches the destination with the expected CPN.
- Inbound call routing: have someone outside the customer's network call a migrated DID and confirm the call lands on the correct migrated user.
- ICT verification (if applicable): place a call from the migrated org to a remaining CUCM cluster and confirm bidirectional reachability.

**See also:** [`dt-data-001`](decision-guide.md#missing-data) · [`dt-feat-001`](decision-guide.md#feature-approximation) · [`pstn-connection-type`](decision-guide.md#pstn-connection-type) · [`trunk-type-selection`](decision-guide.md#trunk-type-selection) · [`intercluster-trunks`](decision-guide.md#intercluster-trunks) · [`trunk-destination-consolidation`](decision-guide.md#trunk-destination-consolidation)

### Recipe 5: Analog-gateway-heavy customer

Analog endpoints — fax lines, paging amps, modems, alarm panels, lobby phones, elevator phones, emergency POTS — never migrate to Webex Calling natively. They require either an ATA (ATA 192/194) on the Webex side or a residual on-prem analog gateway that fronts the migrated environment. Recipe 5 calibrates expectations: most of the analog inventory will get auto-skipped by the default `DEVICE_INCOMPATIBLE → skip` rule, the cross-cutting advisor will surface a bulk-upgrade plan, and the operator's job is to make sure none of the silently-skipped endpoints are load-bearing for life-safety, compliance, or daily operations.

**Source environment characteristics:**
- VG204 / VG310 / VG350 / VG450 analog gateway chassis at one or more sites.
- ATA 190 / 192 / 194 endpoints on individual desks or in fax rooms.
- At least one Cisco IOS gateway with FXS/FXO ports (often a 2900-series or ISR with voice modules) running MGCP, SCCP, or H.323.
- Analog fax lines with carrier-side fax routing.
- POTS lines for emergency response (elevators, hood vents in restaurants, refrigerated medical storage), often regulated.
- Possibly a CER (Cisco Emergency Responder) deployment that has to migrate to a separate workstream.

**Config knobs to set:** defaults. The analog inventory is handled entirely through `DeviceCompatibilityAnalyzer` and the device-bulk-upgrade advisory; there is no analog-specific config knob.
```json
{
  "country_code": "+1",
  "default_country": "US"
}
```

**Auto-rules to add or remove:** the default `DEVICE_INCOMPATIBLE → skip` rule (see [§default-rule-device-incompatible](#default-rule-device-incompatible)) handles the analog gateway inventory automatically. **Decide deliberately whether to keep it or remove it for this customer.**
- **Keep it (default):** every VG/ATA/FXS-port endpoint resolves to `skip`, the assessment lands on a clean migration plan, and the analog inventory is treated as a separate replacement track. This is the right call when the customer is consciously decommissioning analog infrastructure on a different timeline from the Webex cutover.
- **Remove it:** every analog endpoint reaches the decision-review queue. The operator can attach a per-endpoint replacement (e.g., ATA 192) or explicitly mark each one as "out of scope, retain on legacy gateway." This is the right call when the customer wants every analog endpoint accounted for in the migration record (compliance audits, life-safety inventories, partner-handoff documentation).
```json
{
  "auto_rules": [
    // remove the default DEVICE_INCOMPATIBLE rule for this customer
    // by NOT including it; the other 6 defaults still apply.
  ]
}
```

**Decisions to expect:**
- `DEVICE_INCOMPATIBLE`: many — typically every FXS port and every analog gateway chassis. Auto-resolved to `skip` by default; reaches review if you removed the default rule.
- `LOCATION_AMBIGUOUS`: a handful — analog gateways often live in network closets without a clean device pool, and the auto-resolution falls through to the operator.
- `VOICEMAIL_INCOMPATIBLE`: 0–N depending on whether the analog gateway hosts voicemail pilots (Unity Connection IP-to-analog hops, fax-to-email bridges).
- `MISSING_DATA`: occasionally for analog endpoints whose CUCM device record is partially populated (no `description`, no `devicePoolName`).
- `BUTTON_UNMAPPABLE`: not relevant — analog endpoints don't have line keys.

**Advisory patterns likely to fire:**
- `device_bulk_upgrade`: groups all incompatible devices by model and produces a refresh plan with replacement options. For analog-heavy customers, this is the headline finding — accept the advisory and use the produced model breakdown as the procurement input for the customer's hardware refresh.
- `legacy_gateway_protocols` (Layer 1): fires if the source CUCM has gateways running MGCP, SCCP, or H.323. Webex Calling does not support those protocols at all — the customer must replace the chassis or terminate the protocols at a CUBE before reaching Webex.
- `e911_migration_flag`: often fires for analog-heavy customers because analog POTS is the most common emergency-line topology. E911 is always a separate workstream — accept the advisory and route the work to whoever owns RedSky / Intrado integration for the customer.
- `media_resource_scope_removal`: may fire if the analog gateway also serves as a transcoder or conference media resource — those scopes do not migrate; Webex handles media in the cloud.

**Manual verification post-migration:**
- Place a fax test call from each migrated fax line and confirm the fax handshake completes through whatever the new endpoint is (ATA 192, residual analog gateway, fax-to-email service).
- Place an emergency POTS line test (with the customer's safety officer / building management present) on at least one elevator and one hood-vent / freezer / alarm circuit.
- Place an analog phone test from each surviving analog endpoint and confirm dial tone, two-way audio, and DTMF.
- Sign-off on the analog gateway replacement plan from the customer — what hardware is being procured, on what timeline, who owns the cutover, and what remains in service after Webex go-live.
- E911 verification: confirm with whoever owns the E911 workstream that the analog endpoints are accounted for in the post-migration emergency-routing plan.

**See also:** [`dt-dev-001`](decision-guide.md#device-incompatible) · [`dt-loc-001`](decision-guide.md#location-ambiguous) · [`dt-user-003`](decision-guide.md#voicemail-incompatible) · [`device-bulk-upgrade`](decision-guide.md#device-bulk-upgrade) · [`legacy-gateway-protocols`](decision-guide.md#legacy-gateway-protocols) · [`e911-migration-flag`](decision-guide.md#e911-migration-flag) · [`media-resource-scope-removal`](decision-guide.md#media-resource-scope-removal)
