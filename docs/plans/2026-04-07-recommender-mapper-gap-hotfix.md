# Recommender Mapper-Gap Hotfix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two silent mapper→recommender integration bugs in `FeatureMapper` / `recommend_feature_approximation` that produce wrong recommendations for CTI Route Points and large non-Simultaneous hunt pilots.

**Architecture:** Two independent mechanical fixes. The recommendation rule at `src/wxcli/migration/advisory/recommendation_rules.py:136` reads decision-context fields that `FeatureMapper` never writes, so the rule's AUTO_ATTENDANT branch is dead code and its routing-type-aware agent-limit check always falls into the "simultaneous" path regardless of actual routing type. Fix #1 adds `classification` + `complex_script` to the CTI RP decision context. Fix #2 changes the rule to read the already-mapped Webex `policy` field instead of trying to infer routing type from a CUCM `algorithm` string that the mapper never writes.

**Tech Stack:** Python 3.11, pytest, existing `tests/migration/advisory/test_recommendation_rules.py` test pattern (synthetic context dicts passed directly to rule functions).

---

## Context: Why These Are Bugs

The verification swarm (V4) and the C4 code quality review surfaced that `recommend_feature_approximation` reads several context fields that no producer writes. Two of those reads produce wrong recommendations in live pipeline runs:

**Bug H — CTI RP classification never set.** `FeatureMapper._map_cti_route_points()` at `src/wxcli/migration/transform/mappers/feature_mapper.py:531-536` writes this decision context for every CTI Route Point:

```python
context={
    "cti_rp_id": cti_id,
    "name": name,
    "has_script": has_script,
    "reason": "cti_rp_to_auto_attendant",
},
```

The recommendation rule at `recommendation_rules.py:140-148` checks:

```python
classification = context.get("classification")
if classification == "AUTO_ATTENDANT":
    if context.get("complex_script"):
        return None
    return ("accept", "Standard CTI Route Point with no complex scripting. ...")
```

The `classification` key is never in the context, so `classification == "AUTO_ATTENDANT"` is always False. The rule falls through to the hunt-pilot logic with default `has_queue=False`, `agent_count=0`, `algorithm=None`, and — because of Bug I below — returns the wrong recommendation (not "accept", possibly a hunt_group recommendation via the `agent_count <= 4` fallback).

**Bug I — Hunt pilot algorithm/policy mismatch.** `FeatureMapper._map_hunt_pilots()` at `feature_mapper.py:289-296` writes this decision context for agent-limit-exceeded hunt pilots:

```python
context={
    "hunt_pilot_id": hp_id,
    "name": name,
    "policy": policy,          # Webex form: "SIMULTANEOUS", "REGULAR", "CIRCULAR", "UNIFORM", "WEIGHTED"
    "agent_count": len(unique_members),
    "agent_limit": agent_limit,
    "reason": "agent_limit_exceeded",
},
```

The recommendation rule at `recommendation_rules.py:152-159` reads:

```python
algorithm = context.get("algorithm")
target_routing = context.get("target_routing_type")
if target_routing is None:
    is_simultaneous = algorithm in ("Broadcast", "Top Down", "undefined", None)
```

The mapper writes `policy` (the already-mapped Webex form), but the rule reads `algorithm` (the CUCM form) and `target_routing_type` (a future-override field that no producer writes). Since `context.get("algorithm")` is always None, `is_simultaneous = None in (..., None)` is always True — the rule always treats every agent-limit decision as simultaneous. For a 1,100-agent CIRCULAR hunt pilot the rule says "exceeds simultaneous cap of 50" when the actual CIRCULAR cap is 1,000.

The rule's algorithm-to-simultaneous inference is also wrong: it treats "Top Down" as simultaneous, but `_ALGORITHM_TO_POLICY` at `feature_mapper.py:154` maps "Top Down" → "REGULAR" (which is NOT simultaneous per `_AGENT_LIMITS`).

The cleanest fix is to stop inferring from `algorithm` entirely and read `policy` directly — it's already in canonical Webex form and correctly populated by the mapper.

## What This Plan Does NOT Fix

- **`has_queue_features` dead read** at `recommendation_rules.py:150`. V4 flagged this as a "real bug" but the branch that reads it (line 185-191) is only reachable when no agent limit is exceeded, and in the current code the mapper only fires FEATURE_APPROXIMATION decisions for hunt pilots that exceed agent limits. The dead code doesn't affect live pipeline runs. Fixing it is speculative scope and belongs in a future refactor, not this hotfix.
- **`target_routing_type` intentional scaffolding** at `recommendation_rules.py:156`. V4 classified this as "pre-wiring for future routing type detection." Leave it alone; the fix removes its load-bearing role by reading `policy` directly, but keeps the override-check as a fallback.
- **Wave 3 doc corrections.** Plan 3 handles docs drift. This hotfix is code-only.
- **The two-matcher architecture issue (Bug F)** and the **init-only DEFAULT_AUTO_RULES issue (Bug G)** are out of scope for this hotfix — they need design brainstorming in Plan 2.

## File Structure

| File | Change | Purpose |
|---|---|---|
| `src/wxcli/migration/transform/mappers/feature_mapper.py` | Modify CTI RP decision context block (~lines 531-536) | Add `classification="AUTO_ATTENDANT"` + `complex_script=has_script` keys |
| `src/wxcli/migration/advisory/recommendation_rules.py` | Modify `recommend_feature_approximation` algorithm branch (~lines 150-183) | Read `policy` instead of inferring from `algorithm`; drop or soften the algorithm-inference code |
| `tests/migration/advisory/test_recommendation_rules.py` | Add 4 new tests + update 1 existing test | Cover (a) the integration gap (CTI RP context without classification), (b) the policy/algorithm fix (agent-limit decisions with real Webex policy strings) |
| `tests/migration/transform/test_feature_mapper.py` or similar | Add 1 integration test (or extend existing) | Assert the mapper writes `classification` + `complex_script` into CTI RP decision context |

All four files already exist. No new files are created.

## Exit criteria

- CTI RP FEATURE_APPROXIMATION decisions get `recommendation == "accept"` when `has_script=False` and `recommendation is None` when `has_script=True`
- Hunt pilot FEATURE_APPROXIMATION decisions with a CIRCULAR-policy, 1100-agent context get a split recommendation framed against the 1000-agent priority-based cap (not the 50-agent simultaneous cap)
- Hunt pilot decisions with a SIMULTANEOUS-policy, 60-agent context still get a split recommendation framed against the 50-agent simultaneous cap (existing behavior preserved)
- All existing `test_recommendation_rules.py::TestFeatureApproximation` tests still pass
- The full `tests/migration/` suite still passes (1642+ tests)
- No other tests break

---

## Task 1: Fix CTI RP `classification` propagation

**Files:**
- Modify: `src/wxcli/migration/transform/mappers/feature_mapper.py:531-536`
- Test: `tests/migration/advisory/test_recommendation_rules.py`

**Why:** The CTI RP branch at `_map_cti_route_points()` fires a FEATURE_APPROXIMATION decision for every CTI Route Point, but its context dict omits `classification` and `complex_script`. The recommender's AUTO_ATTENDANT branch never fires; every CTI RP gets a wrong recommendation (probably hunt_group via fallthrough).

- [ ] **Step 1: Write the failing test**

The existing `test_cti_rp_simple_recommends_accept` at `test_recommendation_rules.py:236-239` passes a synthetic context that DOES set `classification`. That test is correct for testing the rule in isolation, but doesn't catch the mapper integration gap.

Add a new test at the end of `TestFeatureApproximation` (around line 252) that exercises the recommender with the EXACT context shape the mapper produces today:

```python
    def test_cti_rp_mapper_context_shape_recommends_accept(self):
        """Integration test: CTI RP decision context produced by FeatureMapper._map_cti_route_points
        must cause the recommender to return 'accept' for simple scripts.

        Regression guard for the mapper→recommender integration gap where
        `classification` and `complex_script` were missing from the mapper's
        decision context, causing every CTI RP to receive the wrong recommendation.
        """
        # Simulate the mapper's CTI RP decision context after fix
        mapper_ctx = {
            "cti_rp_id": "cti_rp:abc123",
            "name": "Reception IVR",
            "classification": "AUTO_ATTENDANT",
            "complex_script": False,
            "reason": "cti_rp_to_auto_attendant",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None, "CTI RP context should produce a recommendation"
        assert r[0] == "accept", f"Expected 'accept', got {r[0]!r}"

    def test_cti_rp_mapper_context_complex_script_returns_none(self):
        """Regression guard: CTI RP with complex script must return None (ambiguous)."""
        mapper_ctx = {
            "cti_rp_id": "cti_rp:abc123",
            "name": "Reception IVR",
            "classification": "AUTO_ATTENDANT",
            "complex_script": True,
            "reason": "cti_rp_to_auto_attendant",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is None
```

Place these two new test methods inside the existing `class TestFeatureApproximation` at the bottom of the class (after `test_agent_limit_exceeded_recommends_split` at line 246-250).

These tests will **currently PASS** because the rule's existing AUTO_ATTENDANT branch works correctly when given a context with `classification` set — the bug is that the mapper doesn't set it. The real failure is at the mapper level, so the mapper test below is the load-bearing one.

- [ ] **Step 2: Write the mapper-level failing test**

Find the feature mapper test file:

```bash
ls tests/migration/transform/ | grep -i feature
```

If `test_feature_mapper.py` exists, add a new test to it. If it doesn't, find the nearest existing test file that exercises `FeatureMapper._map_cti_route_points` — likely `tests/migration/transform/test_feature_mapper.py` or `tests/migration/transform/test_mappers.py`. Read it to understand the existing CTI RP test fixture pattern.

Add a new test (adapt the fixture setup to match existing test patterns in the file):

```python
def test_cti_rp_decision_context_sets_classification(tmp_path):
    """Regression guard for mapper→recommender integration gap.

    CTI RP FEATURE_APPROXIMATION decisions must set `classification="AUTO_ATTENDANT"`
    and `complex_script=has_script` in the decision context so that
    recommend_feature_approximation() can route into its AUTO_ATTENDANT branch.

    See docs/plans/2026-04-07-recommender-mapper-gap-hotfix.md for context.
    """
    from wxcli.migration.store import MigrationStore
    from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper

    store = MigrationStore(tmp_path / "test.db")
    store.initialize()

    # Insert a minimal CTI RP raw object
    store.upsert_object({
        "object_type": "cti_rp",
        "canonical_id": "cti_rp:test",
        "pre_migration_state": {
            "name": "TestIVR",
            "isCtiRp": "true",
            "callingSearchSpaceName": None,
        },
        "provenance": {"source": "test", "extracted_at": "2026-04-07T00:00:00Z"},
    })

    mapper = FeatureMapper()
    result = mapper.map(store)

    cti_decisions = [
        d for d in result.decisions
        if d.decision_type.value == "FEATURE_APPROXIMATION"
        and d.context.get("reason") == "cti_rp_to_auto_attendant"
    ]
    assert len(cti_decisions) == 1, f"Expected 1 CTI RP decision, got {len(cti_decisions)}"

    ctx = cti_decisions[0].context
    assert ctx.get("classification") == "AUTO_ATTENDANT", (
        f"CTI RP decision context missing 'classification' key. "
        f"Actual context: {ctx}"
    )
    assert "complex_script" in ctx, (
        f"CTI RP decision context missing 'complex_script' key. "
        f"Actual context: {ctx}"
    )
    assert ctx["complex_script"] is False, (
        f"Expected complex_script=False for CTI RP without script. "
        f"Actual: {ctx['complex_script']}"
    )
```

**Note:** before writing this test, read the existing test file to understand (a) the MigrationStore fixture pattern used in that file — some tests use `tmp_path`, others use a fixture — and (b) the raw CTI RP object shape the existing tests use. Match the existing patterns. If the existing test file uses a different fixture style, adapt to match. If no mapper test file exists for feature_mapper, create `tests/migration/transform/test_feature_mapper.py` with the pytest boilerplate + this test.

- [ ] **Step 3: Run the failing test to confirm it fails**

```bash
python3.11 -m pytest tests/migration/transform/test_feature_mapper.py::test_cti_rp_decision_context_sets_classification -v
```

Expected: FAIL with assertion error "CTI RP decision context missing 'classification' key."

If the test passes unexpectedly, the bug is already fixed — stop and investigate git history before proceeding.

- [ ] **Step 4: Apply the mapper fix**

Edit `src/wxcli/migration/transform/mappers/feature_mapper.py`. Find the CTI RP decision context block (around line 531-536):

```python
                context={
                    "cti_rp_id": cti_id,
                    "name": name,
                    "has_script": has_script,
                    "reason": "cti_rp_to_auto_attendant",
                },
```

Replace with:

```python
                context={
                    "cti_rp_id": cti_id,
                    "name": name,
                    "classification": "AUTO_ATTENDANT",
                    "complex_script": has_script,
                    "has_script": has_script,
                    "reason": "cti_rp_to_auto_attendant",
                },
```

**Keep `has_script`** — it's a valid field the rule may use in the future, and removing it could break other tests or downstream consumers. We're adding two new keys, not replacing existing ones.

- [ ] **Step 5: Run the test to verify it passes**

```bash
python3.11 -m pytest tests/migration/transform/test_feature_mapper.py::test_cti_rp_decision_context_sets_classification -v
python3.11 -m pytest tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation -v
```

Expected: all PASS.

- [ ] **Step 6: Run the full migration test suite to catch regressions**

```bash
python3.11 -m pytest tests/migration/ -x --tb=short 2>&1 | tail -20
```

Expected: no failures. If anything breaks, stop and investigate before proceeding.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/transform/mappers/feature_mapper.py tests/migration/advisory/test_recommendation_rules.py tests/migration/transform/test_feature_mapper.py
git commit -m "$(cat <<'EOF'
fix(migration): CTI RP decision context sets classification + complex_script

FeatureMapper._map_cti_route_points() was omitting `classification` and
`complex_script` from the FEATURE_APPROXIMATION decision context, so
recommend_feature_approximation()'s AUTO_ATTENDANT branch never fired.
Every CTI Route Point received a wrong recommendation via fallthrough to
the hunt-pilot logic.

Fix: set classification="AUTO_ATTENDANT" and complex_script=has_script in
the mapper's decision context. The recommender's existing AUTO_ATTENDANT
branch now correctly returns "accept" for simple scripts and None (ambiguous)
for complex scripts.

Regression guards added:
- Mapper-level: test_cti_rp_decision_context_sets_classification
- Recommender-level: test_cti_rp_mapper_context_shape_recommends_accept + complex_script variant

Discovered via Wave 3 verification swarm — see
docs/plans/2026-04-07-recommender-mapper-gap-hotfix.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Fix recommendation rule to read `policy` instead of `algorithm`

**Files:**
- Modify: `src/wxcli/migration/advisory/recommendation_rules.py:150-183`
- Test: `tests/migration/advisory/test_recommendation_rules.py`

**Why:** The mapper writes `policy` (already-mapped Webex form: SIMULTANEOUS / REGULAR / CIRCULAR / UNIFORM / WEIGHTED). The rule reads `algorithm` (CUCM form) and falls back to defaults when absent. The fallback — `is_simultaneous = None in (None, "Broadcast", "Top Down", "undefined")` — is always True, making every agent-limit decision frame against the 50-agent simultaneous cap even when the actual cap is 1000.

- [ ] **Step 1: Write the failing test for the CIRCULAR policy case**

Add a new test to `test_recommendation_rules.py` inside `TestFeatureApproximation` (after the new CTI RP tests from Task 1):

```python
    def test_large_circular_policy_uses_priority_cap(self):
        """Regression guard: a 1100-agent CIRCULAR-policy hunt pilot should be flagged
        against the 1000-agent priority-based cap, not the 50-agent simultaneous cap.

        Before fix: the rule read `algorithm` (never set by mapper), defaulted to None,
        and `None in (..., None)` returned True → always treated as simultaneous →
        always framed against the 50-cap even for priority-based policies.

        After fix: the rule reads `policy` (Webex form set by mapper) → correctly
        identifies non-SIMULTANEOUS policies → uses the 1000-cap.
        """
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Large Queue",
            "policy": "CIRCULAR",  # non-simultaneous Webex policy
            "agent_count": 1100,
            "agent_limit": 1000,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None, "agent-limit-exceeded decision should produce a recommendation"
        assert r[0] == "split", f"Expected 'split', got {r[0]!r}"
        # The reasoning must reference the 1000-cap, not the 50-cap
        assert "1000" in r[1] or "1,000" in r[1], (
            f"Expected reasoning to reference priority-based cap (1000), got: {r[1]!r}"
        )
        assert "50" not in r[1], (
            f"Reasoning should NOT mention the simultaneous cap (50) "
            f"for a CIRCULAR-policy hunt pilot. Got: {r[1]!r}"
        )

    def test_large_simultaneous_policy_uses_simultaneous_cap(self):
        """Regression guard: 60-agent SIMULTANEOUS-policy hunt pilot still uses the 50-cap."""
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Broadcast Pilot",
            "policy": "SIMULTANEOUS",
            "agent_count": 60,
            "agent_limit": 50,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None
        assert r[0] == "split"
        assert "50" in r[1], (
            f"Expected reasoning to reference simultaneous cap (50), got: {r[1]!r}"
        )

    def test_large_regular_policy_uses_priority_cap(self):
        """Regression guard: 1100-agent REGULAR-policy (Top Down → REGULAR) uses priority cap.

        Also catches the pre-fix bug where the rule treated 'Top Down' as simultaneous.
        """
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Top Down Pilot",
            "policy": "REGULAR",
            "agent_count": 1100,
            "agent_limit": 1000,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None
        assert r[0] == "split"
        assert "1000" in r[1] or "1,000" in r[1]
        assert "50" not in r[1]
```

- [ ] **Step 2: Run the failing tests to confirm they fail**

```bash
python3.11 -m pytest tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation::test_large_circular_policy_uses_priority_cap tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation::test_large_simultaneous_policy_uses_simultaneous_cap tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation::test_large_regular_policy_uses_priority_cap -v
```

Expected:
- `test_large_circular_policy_uses_priority_cap` **FAIL** — the rule returns split framed against the 50-cap because it reads `algorithm=None` and infers simultaneous.
- `test_large_simultaneous_policy_uses_simultaneous_cap` **may PASS or FAIL** depending on the current-bug behavior (the wrong logic coincidentally produces the right answer here because `None in (..., None)` → True and `60 > 50` → True). Don't worry if it passes pre-fix — it will still pass post-fix.
- `test_large_regular_policy_uses_priority_cap` **FAIL** — same reason as the circular case.

- [ ] **Step 3: Apply the rule fix**

Edit `src/wxcli/migration/advisory/recommendation_rules.py`. Find the algorithm-inference block (around lines 150-159):

```python
    has_queue = context.get("has_queue_features", False)
    agent_count = context.get("agent_count", 0)
    algorithm = context.get("algorithm")

    # Agent limit check — routing-type-aware (kb-webex-limits.md DT-LIMITS-001).
    # Simultaneous routing caps at 50 agents; other routing types cap at 1,000.
    target_routing = context.get("target_routing_type")  # explicit override
    if target_routing is None:
        # Infer: Broadcast/Top Down maps to Simultaneous; others to priority-based
        is_simultaneous = algorithm in ("Broadcast", "Top Down", "undefined", None)
    else:
        is_simultaneous = target_routing.upper() == "SIMULTANEOUS"
```

Replace with:

```python
    has_queue = context.get("has_queue_features", False)
    agent_count = context.get("agent_count", 0)
    # policy is the Webex form written by FeatureMapper (SIMULTANEOUS / REGULAR /
    # CIRCULAR / UNIFORM / WEIGHTED). Prefer this over the CUCM `algorithm` string
    # since the mapping is already done.
    policy = context.get("policy")

    # Agent limit check — routing-type-aware (kb-webex-limits.md DT-LIMITS-001).
    # SIMULTANEOUS caps at 50; WEIGHTED caps at 100; REGULAR/CIRCULAR/UNIFORM cap at 1000.
    target_routing = context.get("target_routing_type")  # explicit override (future scaffold)
    if target_routing is not None:
        is_simultaneous = target_routing.upper() == "SIMULTANEOUS"
    elif policy is not None:
        is_simultaneous = policy == "SIMULTANEOUS"
    else:
        # Fallback for decisions without a policy field (should not happen in
        # live code paths; this branch exists only for defensive parsing of
        # legacy or hand-constructed contexts).
        algorithm = context.get("algorithm")
        is_simultaneous = algorithm in ("Broadcast", None)
```

**Notes on the fix:**
1. **`policy` is now the primary source.** The rule no longer tries to infer routing type from CUCM algorithm strings.
2. **`target_routing_type` is kept as an override.** V4 classified this as "intentional scaffolding" — preserving it keeps the door open for a future override analyzer without changing the scaffolding contract.
3. **The legacy `algorithm` fallback is narrowed.** Only "Broadcast" (which maps to SIMULTANEOUS) is still treated as simultaneous in the fallback. "Top Down" is removed because it maps to REGULAR (not simultaneous).
4. **The fallback exists only for defensive parsing.** In live pipeline runs, the mapper always writes `policy`, so this branch is unreachable. Tests that pass synthetic contexts without `policy` may hit it; that's fine.

- [ ] **Step 4: Run the new tests to verify they pass**

```bash
python3.11 -m pytest tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation::test_large_circular_policy_uses_priority_cap tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation::test_large_simultaneous_policy_uses_simultaneous_cap tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation::test_large_regular_policy_uses_priority_cap -v
```

Expected: all PASS.

- [ ] **Step 5: Run the full TestFeatureApproximation class**

```bash
python3.11 -m pytest tests/migration/advisory/test_recommendation_rules.py::TestFeatureApproximation -v
```

Expected: ALL existing tests still pass, plus the 5 new tests added across Tasks 1 and 2 (2 CTI RP regression guards + 3 policy regression guards). No prior test should break.

**If `test_agent_limit_exceeded_recommends_split` at line 246-250 fails:** read its context:
```python
    def test_agent_limit_exceeded_recommends_split(self):
        r = recommend_feature_approximation(
            {"has_queue_features": True, "agent_count": 60}, [])
        assert r[0] == "split"
        assert "50" in r[1]
```
This test passes a context without `policy`. With the fix, the fallback branch runs: `algorithm = None`, `algorithm in ("Broadcast", None)` → True, `is_simultaneous = True`, 60 > 50 → returns split with 50 in message. Should still pass. If it doesn't, the fallback branch logic is wrong and needs re-reading.

**If `test_small_group_no_queue_recommends_hg` at line 225-229 fails:** it passes `"algorithm": "Top Down"` expecting hunt_group. With the fix, the rule only reads `algorithm` as a fallback for when `policy` is absent. `algorithm="Top Down"` is not in the fallback's `("Broadcast", None)` set, so `is_simultaneous=False`. `agent_count=3 > 1000` is False → falls through. The rest of the logic (agent_count <= 4 and algorithm in ("Top Down", ...)) still checks `algorithm`, so this test path still works as written.

Verify by reading lines 201-207 of the post-fix `recommendation_rules.py`:
```python
    if agent_count <= 4 and algorithm in ("Top Down", "undefined", None):
        return ("hunt_group", ...)
```
This still reads `algorithm` directly for the small-group fallback classification. If the fix accidentally removed the `algorithm` variable binding, this line will throw NameError. Make sure `algorithm` is still defined (either in the fallback branch above, or extracted to a module-level variable binding).

**Recommended safer fix:** keep `algorithm = context.get("algorithm")` as an unconditional variable at the top of the function (alongside `has_queue`, `agent_count`), and only scope the `policy` read to the routing-type-aware block. This avoids breaking downstream reads:

```python
    has_queue = context.get("has_queue_features", False)
    agent_count = context.get("agent_count", 0)
    algorithm = context.get("algorithm")  # legacy; still read below for small-group check
    policy = context.get("policy")        # preferred; Webex form from mapper

    target_routing = context.get("target_routing_type")
    if target_routing is not None:
        is_simultaneous = target_routing.upper() == "SIMULTANEOUS"
    elif policy is not None:
        is_simultaneous = policy == "SIMULTANEOUS"
    else:
        # Fallback: legacy contexts without `policy`.
        is_simultaneous = algorithm in ("Broadcast", None)
```

Use this version. It keeps `algorithm` in scope for the small-group check at line 201.

- [ ] **Step 6: Run the full migration test suite**

```bash
python3.11 -m pytest tests/migration/ -x --tb=short 2>&1 | tail -20
```

Expected: no failures.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/advisory/recommendation_rules.py tests/migration/advisory/test_recommendation_rules.py
git commit -m "$(cat <<'EOF'
fix(migration): recommend_feature_approximation reads `policy` not `algorithm`

FeatureMapper._map_hunt_pilots() writes the Webex `policy` field (SIMULTANEOUS /
REGULAR / CIRCULAR / UNIFORM / WEIGHTED) to FEATURE_APPROXIMATION decision contexts
for agent-limit-exceeded hunt pilots, but the recommendation rule was reading the
CUCM `algorithm` field that no producer ever wrote. The rule's fallback
(`None in (None, ...)`) always returned True, causing every agent-limit decision
to be framed against the 50-agent Simultaneous cap even for CIRCULAR / REGULAR /
UNIFORM / WEIGHTED policies with much larger caps (1000, 100).

Fix: read `policy` from the decision context and check `policy == "SIMULTANEOUS"`.
Keep `target_routing_type` as an explicit override (intentional scaffolding per
V4 verification). Narrow the legacy `algorithm` fallback to only "Broadcast" ->
simultaneous — removes the incorrect "Top Down" -> simultaneous treatment.

Impact: A 1100-agent CIRCULAR-policy hunt pilot now correctly recommends splitting
against the 1000-agent priority-based cap instead of the 50-agent simultaneous cap.

Regression guards added:
- test_large_circular_policy_uses_priority_cap
- test_large_simultaneous_policy_uses_simultaneous_cap
- test_large_regular_policy_uses_priority_cap

Discovered via Wave 3 verification swarm — see
docs/plans/2026-04-07-recommender-mapper-gap-hotfix.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Final verification + update drift list

**Files:**
- Test: none (verification only)
- Modify: none
- Verify: git log + full test run

- [ ] **Step 1: Run the full migration test suite end-to-end**

```bash
python3.11 -m pytest tests/migration/ -v 2>&1 | tail -30
```

Expected: all tests pass. No new failures introduced. Test count should be the pre-existing number (1642+) plus the 6 new tests added in Tasks 1 and 2 (2 + 4 = 6 new tests), so 1648+ total.

- [ ] **Step 2: Run the transferability test suite (Wave 3 holdover)**

```bash
python3.11 -m pytest tests/migration/transferability/ -v 2>&1 | tail -10
```

Expected: 8 PASS + 1 FAIL (the persistent `test_advisor_routing_table_lists_all_patterns` — Wave 4 work item, unrelated to this hotfix).

- [ ] **Step 3: Sanity-check the two commits**

```bash
git log --oneline | head -5
```

Expected: two new commits, one per task, in order:
1. `fix(migration): recommend_feature_approximation reads \`policy\` not \`algorithm\``
2. `fix(migration): CTI RP decision context sets classification + complex_script`

(Or reverse order — whichever task landed first.)

- [ ] **Step 4: Verify with a fresh grep that the fix landed**

```bash
# Mapper fix:
grep -n 'classification.*AUTO_ATTENDANT' src/wxcli/migration/transform/mappers/feature_mapper.py
# Expected: hit inside _map_cti_route_points around line 531-538

# Rule fix:
grep -n 'policy = context.get\|policy == "SIMULTANEOUS"' src/wxcli/migration/advisory/recommendation_rules.py
# Expected: both hits inside recommend_feature_approximation around line 150-165
```

- [ ] **Step 5: No commit in this task**

Task 3 is verification only. If any check fails, return to the failing task and re-run its TDD cycle.

---

## Self-Review Checklist

Run through this after writing all three task bodies:

- [x] Every task cites exact file paths with line number ranges
- [x] Every code change has the full before/after snippet, not a description
- [x] Every test has the full test code, not a sketch
- [x] Every step has the exact command to run with expected output
- [x] No `TODO` or `TBD` markers anywhere
- [x] TDD cycle is preserved: failing test → minimal fix → verify passing → commit
- [x] Tasks 1 and 2 are independent and can be committed separately
- [x] Task 3 is verification only (no commit)
- [x] Exit criteria are checkable
- [x] The plan acknowledges its own scope limits (the "What This Plan Does NOT Fix" section)
- [x] Cross-task type consistency: both tasks refer to `recommend_feature_approximation` by the same function name; `classification`, `complex_script`, `policy`, `has_queue_features` all use consistent casing

## Cross-plan reference

- This is **Plan 1 of 3** in the Wave 3 drift follow-up track. Plans 2 and 3 are separate:
  - **Plan 2** — architecture brainstorm for Bug F (two matchers) + Bug G (init-only DEFAULT_AUTO_RULES). Needs design discussion, not mechanical fix.
  - **Plan 3** — Wave 3 doc corrections (ζ/η/θ/ι) + optional test fixture for the advisor dissent format (V6). Follows Plan 2's architecture decisions.
- This hotfix ships independently of Plans 2 and 3. No cross-plan dependencies.
- Source for the bug findings: the Wave 3 verification swarm (V4 dead-fields audit + C4 code quality review). See `docs/plans/transferability-phase-2-plan-wave3-guides.md` Wave 3 drift list entries H and I.
