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

<!-- Wave 3 Phase D Task D2: one anchor per DEFAULT_AUTO_RULES entry. Anchors are the slug-form of the rule's
     `type` field, with a `-N` suffix when multiple rules share a type (none currently do).
     Validated by test_default_auto_rules_coverage.py. -->

### default-rule-device-incompatible
### default-rule-device-firmware-convertible
### default-rule-hotdesk-dn-conflict
### default-rule-forwarding-lossy
### default-rule-snr-lossy
### default-rule-button-unmappable
### default-rule-calling-permission-mismatch-assigned-users-count-0

### The 14 Non-Auto-Ruled DecisionTypes and Why

_TBD — Wave 3 Phase D Task D3 — MUST enumerate every DecisionType not in DEFAULT_AUTO_RULES with one of: judgment too high / context too variable / no safe single answer_

## Score Weights and the Calibration Disclaimer

_TBD — Wave 3 Phase D Task D4 — names SCORE_CALIBRATED flag, lists 8 factors, links to executive disclaimer_

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
