# Review Report: authentication.md, provisioning.md, wxc-sdk-patterns.md

**Reviewer:** Claude (automated quality review)
**Date:** 2026-03-17
**Files reviewed:**
1. `authentication.md`
2. `provisioning.md`
3. `wxc-sdk-patterns.md`

---

## 1. authentication.md

### Accuracy

- **Method signatures look correct.** `WebexSimpleApi(tokens=...)`, `Integration(...)`, `Tokens(...)` all match the SDK's public API.
- **Token lifetimes are correct.** 12 hours for personal, 14-day access / 90-day refresh for integrations.
- **OAuth flow is accurate.** The 4-step authorization code flow matches the Webex developer docs.
- **Scope names are correct.** Both user-level (`spark:`) and admin-level (`spark-admin:`) scopes match current API documentation.
- **Error handling section is solid.** HTTP 401/403/429 behaviors and the `RestError` structure are accurately described.
- **Minor issue:** The `ErrorDetail` description (line 598-602) lists `.description` as a top-level field, but the SDK actually nests error descriptions inside `errors[].description`. The doc is slightly ambiguous about whether `error.detail.description` is a convenience accessor or the raw path. This could confuse someone reading the SDK source.

### Gaps

- **No mention of `spark:all` and its relationship to Calling SDK usage.** The scope is mentioned briefly in line 304-306 but not in the context of when SDK-based calling apps might use it (e.g., Webex web-client-style apps).
- **No coverage of token revocation.** There is no mention of how to revoke tokens (POST to `/v1/access_token` with `grant_type=urn:ietf:params:oauth:grant-type:token-revocation` or similar). If revocation is not supported, that should be stated explicitly.
- **No mention of the `WebexSimpleApi` async variant.** The auth doc covers only `WebexSimpleApi` for auth setup but does not mention that `AsWebexSimpleApi` accepts the same token patterns. A single sentence pointing to `wxc-sdk-patterns.md` section 4 would close this gap.
- **No Device Code / Client Credentials flow.** If Webex does not support these, it should be stated. If they do (e.g., for certain partner scenarios), they are missing.

### Cross-References

- **Good:** The doc is self-contained for authentication topics.
- **Missing:** No reference to `provisioning.md` for "what scopes do I need for provisioning?" The Required Scopes table in `provisioning.md` is the authoritative source for provisioning scopes, but `authentication.md` does not point to it.
- **Missing:** No reference to `wxc-sdk-patterns.md` for the full async auth setup or the service app caching pattern (which is more fully developed in `wxc-sdk-patterns.md` section 3, Pattern D).

### Formatting

- Consistent heading levels (H2 for major sections, H3 for subsections).
- Code blocks are correctly fenced with language hints.
- Tables are well-structured and render properly.
- TOC links use correct anchor format.
- **Nit:** Line 135 has an inline HTML comment (`<!-- NEEDS VERIFICATION -->`) mid-sentence, which could render oddly in some Markdown viewers. Consider moving it to its own line.

### Issues Found

| # | Severity | Description | Suggested Fix |
|---|----------|-------------|---------------|
| A1 | Low | No mention of token revocation | Add a subsection or note stating whether revocation is supported and how |
| A2 | Low | No cross-reference to `provisioning.md` scopes table | Add a note in the "Calling-Related Scopes" section: "For provisioning-specific scope requirements, see `provisioning.md` > Required Scopes." |
| A3 | Low | No mention of async API accepting the same auth patterns | Add one line under "wxc_sdk Auth Setup" noting `AsWebexSimpleApi` uses identical token arguments |
| A4 | Info | `ErrorDetail` field paths slightly ambiguous | Clarify that `.description` is a convenience accessor aggregating from the nested `errors` array |

---

## 2. provisioning.md

### Accuracy

- **Method signatures are correct.** `api.people.list()`, `api.people.details()`, `api.people.create()`, `api.people.update()`, `api.licenses.assign_licenses_to_users()` all match the SDK.
- **`calling_data=True` guidance is accurate and well-emphasized.** This is the #1 gotcha and it is correctly highlighted in multiple places.
- **License helper properties are correct.** `webex_calling_professional`, `webex_calling_basic`, `webex_calling_workspaces`, `cx_essentials` match the SDK source.
- **`LicenseRequest` / `LicenseProperties` model is accurately documented.**
- **Gotchas section is excellent.** The 12 gotchas are practical and clearly derived from real experience.
- **Minor accuracy concern (line 31):** The scope `spark-admin:locations_write` is listed for "Enable location for calling" but is tagged `<!-- NEEDS VERIFICATION -->`. The actual scope for enabling calling on a location may also require `spark-admin:telephony_config_write` since the telephony location API is under the telephony config domain, not the locations domain. This is flagged below under NEEDS VERIFICATION.
- **Line 789:** `api.telephony.location.number.add(...)` -- the method path looks correct based on SDK structure, but the exact method name may be `add_phone_numbers_to_location` or similar. Worth verifying.

### Gaps

- **No coverage of SCIM 2.0 provisioning workflow.** Gotcha #10 mentions SCIM 2.0 is the recommended path, but there is no code example or workflow for it. A brief subsection showing `api.scim.create_user()` followed by `api.licenses.assign_licenses_to_users()` would be valuable.
- **No coverage of bulk provisioning via Jobs API.** The `api.jobs` property is mentioned in `wxc-sdk-patterns.md` but provisioning.md does not reference it for batch user operations.
- **No phone number provisioning workflow.** Gotcha #9 mentions phone numbers must be added to a location first, and gives the API call, but there is no end-to-end example showing: (1) add number to location inventory, (2) assign number to user. This would be a natural addition to the Provisioning Workflow section.
- **No coverage of workspace provisioning.** The doc covers user and location provisioning but omits workspaces, which are covered in `wxc-sdk-patterns.md` recipe 5.12.
- **Missing "How to move a calling user to a new location."** Gotcha #3 mentions `location_id` is write-once and hints at the workaround (remove license, re-add with new location), but a code example would be useful.

### Cross-References

- **Missing (critical):** No reference to `authentication.md` for token setup. The doc assumes the reader already has a working `api = WebexSimpleApi()` but never says "see `authentication.md` for how to obtain and configure your access token." This should be added at the top or in the Required Scopes section.
- **Missing:** No reference to `wxc-sdk-patterns.md` for async bulk provisioning patterns (recipe 5.3 for license-based user identification, recipe 5.4 for bulk settings reads).
- **Missing:** No reference to `wxc-sdk-patterns.md` for workspace provisioning (recipe 5.12).

### Formatting

- Consistent heading levels.
- Code blocks are properly fenced with `python` language hints.
- Tables are consistent and well-formed.
- The two-method comparison (Method A vs Method B) is clear and well-structured.
- **Nit:** The `<!-- NEEDS VERIFICATION -->` tags on lines 31, 430, and 761 are inline and could be pulled to their own lines for clarity.

### Issues Found

| # | Severity | Description | Suggested Fix |
|---|----------|-------------|---------------|
| P1 | Medium | No cross-reference to `authentication.md` for token setup | Add a note at the top: "All examples assume a configured `WebexSimpleApi` instance. See `authentication.md` for token setup." |
| P2 | Low | No SCIM 2.0 provisioning example despite recommending it | Add a brief code example or a "See also" reference |
| P3 | Low | No phone number provisioning end-to-end example | Add to Provisioning Workflow section |
| P4 | Low | No cross-reference to `wxc-sdk-patterns.md` for async patterns and workspace provisioning | Add "See also" links in relevant sections |
| P5 | Low | `location_id` write-once workaround lacks code example | Add a brief example in Gotcha #3 |

---

## 3. wxc-sdk-patterns.md

### Accuracy

- **SDK version listed as 1.30.0.** This should be verified against the current release; if the playbook is being actively maintained, this will drift. Consider noting "check PyPI for the latest version" rather than a fixed number.
- **Constructor parameters are correct.** `tokens`, `concurrent_requests`, `retry_429`, `session` match the source.
- **Token resolution order is correct** and matches the `authentication.md` description.
- **Sync vs Async comparison table is accurate.** Class names, import paths, HTTP libraries, and concurrency models are all correct.
- **Top-Level API Properties table is comprehensive.** 30+ sub-APIs listed with correct class names.
- **Recipes are correct and practical.** Recipes 5.1-5.12 all use correct method signatures and data types.
- **Error handling section is accurate.** `RestError` (sync) and `AsRestError` (async) with correct parent classes.
- **Rate limiting details are correct.** `RETRY_429_MAX_WAIT = 60` seconds, `Retry-After` header handling, semaphore protection.
- **Pagination description is accurate.** RFC 5988 link-header following, transparent to the caller.
- **Minor concern (line 503):** `queue.id` -- the field name on `CallQueue` list responses may be `id` or `queue_id` depending on context. The SDK may alias this. Worth verifying, though the pattern shown is consistent with example code.
- **Recipe 5.12 (line 645):** Uses `await api.workspaces.create(...)` which is the async API, but the surrounding code block does not show the `async with` context. This could confuse readers.

### Gaps

- **No CDR (Call Detail Records) recipe.** `api.cdr` is listed in the property table but no recipe shows how to query CDR data. This is a common use case for reporting.
- **No webhook recipe.** `api.webhook` is listed but no recipe shows webhook setup or event handling.
- **No auto attendant recipe.** Call queues (5.7) and hunt groups (5.10) are covered but auto attendants are not.
- **No recipe for reading/configuring caller ID settings.** This is under `api.person_settings.caller_id` and is a common provisioning task.
- **No recipe for phone number management beyond listing.** Recipe 5.9 shows listing numbers but not adding, moving, or removing them.
- **No recipe for virtual lines.** `api.telephony.virtual_lines` is mentioned in the telephony sub-APIs list but has no example.
- **Missing proxy authentication example.** Section 7 shows `proxy_url` but not proxy auth (username/password).

### Cross-References

- **Good:** Section 3 (Authentication Patterns) effectively covers all patterns from `authentication.md` with SDK-specific code. This is good but creates duplication.
- **Missing:** No explicit reference to `authentication.md` for deeper coverage of OAuth flows, scopes, and error handling. A line like "For detailed OAuth flow documentation and scope reference, see `authentication.md`" would reduce duplication and connect the docs.
- **Missing:** No reference to `provisioning.md` from the People API or Licenses sections. Recipe 5.1-5.3 overlap with `provisioning.md` content. A cross-reference would help readers find the provisioning workflows.
- **Missing:** The Tokens Class Reference in section 3 duplicates the Tokens Model from `authentication.md` section "Token Refresh Flow." One should reference the other.

### Formatting

- Consistent heading levels. Numbered sections (1-11) at H2, subsections at H3.
- Code blocks are properly fenced with language hints.
- Tables are well-formed.
- The sync vs async side-by-side comparison (section 4) is effective.
- **Nit:** Recipe 5.12 mixes async (`await`) with no surrounding `async def main()` wrapper, unlike all other async recipes. Add the wrapper for consistency.
- **Nit:** The `<!-- NEEDS VERIFICATION -->` tags are properly placed on their own lines.

### Issues Found

| # | Severity | Description | Suggested Fix |
|---|----------|-------------|---------------|
| S1 | Low | SDK version (1.30.0) will go stale | Add "check PyPI for latest" note, or remove the fixed version |
| S2 | Low | Recipe 5.12 uses `await` without showing `async def main()` wrapper | Add the standard async wrapper for consistency |
| S3 | Low | No cross-reference to `authentication.md` or `provisioning.md` | Add "See also" links in sections 3 and 5 |
| S4 | Info | Tokens class reference duplicates `authentication.md` | Reference `authentication.md` instead of duplicating, or note "also documented in authentication.md" |
| S5 | Info | No CDR, webhook, auto attendant, or virtual line recipes | Consider adding in a future update; note as "planned" if needed |
| S6 | Low | `queue.id` field name may be ambiguous | Verify and add a note about ID aliasing if needed |

---

## Cross-Document Issues

| # | Severity | Description | Affected Docs |
|---|----------|-------------|---------------|
| X1 | Medium | **No cross-references between docs.** None of the three documents reference each other. This is the single biggest structural gap. A reader of `provisioning.md` has no way to discover that `authentication.md` explains how to get a token, or that `wxc-sdk-patterns.md` has async bulk provisioning recipes. | All three |
| X2 | Low | **Tokens model documented in two places.** Both `authentication.md` (lines 488-497) and `wxc-sdk-patterns.md` (lines 259-272) document the `Tokens` class with nearly identical content. This creates a maintenance burden. | `authentication.md`, `wxc-sdk-patterns.md` |
| X3 | Low | **Auth patterns documented in two places.** `authentication.md` sections "wxc_sdk Auth Setup" and "Service App" overlap heavily with `wxc-sdk-patterns.md` section 3 (Authentication Patterns). The SDK patterns version adds token caching code; the auth version has more detail on OAuth flows. | `authentication.md`, `wxc-sdk-patterns.md` |
| X4 | Low | **Calling user identification documented in two places.** Both `provisioning.md` ("Identifying Calling Users") and `wxc-sdk-patterns.md` (recipes 5.1 and 5.3) show essentially the same two approaches (filter on `location_id` vs filter on calling license IDs). | `provisioning.md`, `wxc-sdk-patterns.md` |
| X5 | Info | **Scope information split across docs.** `authentication.md` has the comprehensive scope tables. `provisioning.md` has a provisioning-specific scope table. Neither references the other. A reader could miss scopes by reading only one doc. | `authentication.md`, `provisioning.md` |
| X6 | Info | **Consistent terminology for "enable location for calling."** `provisioning.md` mentions `api.telephony.location.enable_for_calling()` (NEEDS VERIFICATION). `wxc-sdk-patterns.md` lists `api.telephony.location` as a sub-API but does not elaborate on enable-for-calling. If this method exists, it should appear in both. If it does not exist, `provisioning.md` should be corrected. | `provisioning.md`, `wxc-sdk-patterns.md` |

### Recommendation for Cross-References

Add a "See Also" block at the top or bottom of each doc:

**authentication.md:**
> See also: `provisioning.md` for provisioning-specific scope requirements. `wxc-sdk-patterns.md` for SDK recipes and async patterns.

**provisioning.md:**
> See also: `authentication.md` for token setup and OAuth flows. `wxc-sdk-patterns.md` for async bulk provisioning and workspace recipes.

**wxc-sdk-patterns.md:**
> See also: `authentication.md` for detailed OAuth flows and scope reference. `provisioning.md` for end-to-end user provisioning workflows.

---

## All NEEDS VERIFICATION Items

| # | File | Line(s) | Content | Assessment |
|---|------|---------|---------|------------|
| V1 | `authentication.md` | 135 | PKCE support: specific parameters (`code_challenge`, `code_challenge_method`) and whether `wxc_sdk` supports PKCE natively | **Cannot resolve from other docs.** Requires checking Webex developer documentation and SDK source. |
| V2 | `authentication.md` | 143 | OpenID Connect discovery endpoint: exact URL path `https://webexapis.com/v1/.well-known/openid-configuration` | **Cannot resolve from other docs.** Requires a live API call or Webex developer docs check. |
| V3 | `authentication.md` | 234 | Exact list of calling-related scopes available to bots | **Cannot resolve from other docs.** Requires checking Webex bot documentation. |
| V4 | `authentication.md` | 257 | Exact guest token lifetime | **Cannot resolve from other docs.** Requires Webex guest issuer documentation. |
| V5 | `provisioning.md` | 31 | Whether `spark-admin:locations_write` is the correct scope for enabling a location for calling | **Partially resolvable.** `authentication.md` lists `spark-admin:telephony_config_write` for telephony configuration changes. Enabling calling on a location is likely a telephony config operation, so the correct scope may be `spark-admin:telephony_config_write` (possibly in addition to `spark-admin:locations_write`). Recommend verifying and updating. |
| V6 | `provisioning.md` | 430 | The `api.telephony.location.enable_for_calling()` method existence and signature | **Partially resolvable.** `wxc-sdk-patterns.md` lists `api.telephony.location` as a sub-API for "Location-level telephony settings" but does not confirm an `enable_for_calling` method. Requires SDK source inspection. |
| V7 | `provisioning.md` | 761 | Whether removing and re-adding a calling license is the correct procedure to change a user's location | **Cannot resolve from other docs.** Requires Webex API documentation or empirical testing. |
| V8 | `wxc-sdk-patterns.md` | 127 | Full list of `api.telephony` sub-properties | **Cannot resolve from other docs.** The listed sub-properties are confirmed from examples, but the full list requires inspecting the SDK's `as_api.py` source. |
| V9 | `wxc-sdk-patterns.md` | 834 | `HarWriter` constructor parameter names | **Cannot resolve from other docs.** Requires SDK source inspection. |

**Summary:** 9 total NEEDS VERIFICATION items. V5 and V6 can be partially resolved by cross-referencing the other docs (and likely point to a correction needed in `provisioning.md`). The remaining 7 require external verification against Webex developer documentation or the SDK source code.

---

## Overall Quality Rating

| Doc | Rating | Summary |
|-----|--------|---------|
| `authentication.md` | **Good** | Comprehensive coverage of all auth methods, scopes, and SDK patterns. Well-structured. Missing cross-references and token revocation. 4 NEEDS VERIFICATION items, all on peripheral topics. |
| `provisioning.md` | **Good** | Strong coverage of the enable-user workflow with two methods. Excellent gotchas section. Missing cross-references to auth and SDK docs. Could benefit from SCIM 2.0 and phone number provisioning examples. 3 NEEDS VERIFICATION items. |
| `wxc-sdk-patterns.md` | **Good** | The most comprehensive of the three. Excellent recipe collection covering sync, async, and bulk patterns. Missing some common recipes (CDR, webhooks, auto attendants) but what is present is accurate and practical. 2 NEEDS VERIFICATION items. |
| **Overall** | **Good (with cross-reference gap)** | All three docs are individually strong. The main structural issue is the complete absence of cross-references between them, which forces readers to discover each doc independently. The duplication of auth patterns and Tokens model across two docs creates a maintenance risk. Adding "See Also" blocks and deduplicating the Tokens reference would elevate these from Good to Excellent. |
