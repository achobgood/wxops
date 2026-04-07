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
### default-language
### default-country
### outside-dial-digit
### create-method
### include-phoneless-users
### auto-rules
### site-prefix-rules
### category-rules

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
### default-rule-calling-permission-mismatch-zero-users

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
