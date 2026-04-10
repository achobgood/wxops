# Phase A — Foundations

> **Parent plan:** [2026-04-07-auto-rule-architecture-unification-plan.md](2026-04-07-auto-rule-architecture-unification-plan.md)
> **Source-of-truth spec:** `docs/superpowers/specs/2026-04-07-auto-rule-architecture-unification-design.md`

Phase A builds the non-CLI foundation: the new store method, the enrichment helper, the `rules.py` refactor, the rewritten `decisions.py`, the new default rule, and four new test files. **At the end of Phase A, the CLI is temporarily broken** — `classify_decisions` has a new signature, and `cucm.py`'s callers don't pass `config` yet. That's fixed in Phase B.

Do NOT run the full `tests/migration/` suite at the end of Phase A — it will show CLI test failures in `tests/migration/test_decision_cli.py` and `tests/migration/transform/test_decision_classify.py`. Scope test runs to the touched files per each task's verification step. Full-suite verification happens at the end of Phase B.

## Spec-test inventory for Phase A

These are the tests the spec lists. Phase A creates all of them except the CLI/export-review tests (Phase B) and the grep audit (Phase C):

**In `tests/migration/transform/test_rules.py` (append to existing file, Task 4):**
- `test_preview_auto_rules_returns_pending_only`
- `test_preview_auto_rules_skips_resolved_decisions`
- `test_preview_auto_rules_returns_auto_choice_and_reason`
- `test_preview_auto_rules_uses_rule_reason_field_when_present`
- `test_preview_auto_rules_falls_back_to_synthesized_reason`
- `test_preview_auto_rules_falls_back_when_reason_is_non_string`
- `test_preview_auto_rules_skips_invalid_choices`
- `test_apply_auto_rules_uses_resolved_by_auto_rule`
- `test_calling_permission_mismatch_with_users_not_silently_skipped` (regression guard)
- `test_md_rule_does_not_fire_when_device_is_compatible`
- `test_analyze_then_apply_auto_is_no_op` (idempotent re-run)

**In `tests/migration/transform/test_cross_decision_enrichment.py` (new file, Task 2):**
- `test_enrich_no_decisions`
- `test_enrich_no_incompatible_devices`
- `test_enrich_one_incompatible_one_missing_match`
- `test_enrich_via_affected_objects`
- `test_enrich_idempotent`
- `test_enrich_skips_stale_decisions`
- `test_md_fingerprint_stable_before_and_after_enrichment` (spec: fingerprint safety guard)
- `test_cascade_produced_md_decisions_enriched` (added in Task 3)

**In `tests/migration/transform/test_classify_decisions.py` (new file, Task 7):**
- `test_classify_returns_auto_apply_from_preview`
- `test_classify_needs_input_excludes_auto_apply_decisions`
- `test_classify_with_custom_config_rule`
- `test_classify_with_empty_auto_rules`

**In `tests/migration/transform/test_default_auto_rules_field_alignment.py` (new file, Task 9):**
- One parametrized test over `DEFAULT_AUTO_RULES` asserting every `match` key is written by the producing analyzer.

---

## Task 1: Add `store.update_decision_context()`

**Files:**
- Modify: `src/wxcli/migration/store.py` (insert a new method in the Decisions section, near `save_decision` at ~line 461)
- Test: `tests/migration/test_store.py` (or nearest existing store test file; if the file doesn't exist, create it)

**Why:** `enrich_cross_decision_context()` (Task 2) needs to patch the `context` column of an existing decision row without re-fingerprinting or touching other columns. `store.save_decision()` is an INSERT-with-ON-CONFLICT-on-fingerprint and requires the full row. A targeted UPDATE keeps the intent clear and avoids accidental re-fingerprinting.

- [ ] **Step 1: Locate or create the store test file**

Run:
```bash
ls tests/migration/ | grep -i store
```

Expected: either `test_store.py` exists, or only other files do. If `test_store.py` exists, append the new test class to it. If not, create `tests/migration/test_store.py` with this header:

```python
"""Tests for MigrationStore helper methods not covered elsewhere."""

from __future__ import annotations

import pytest

from wxcli.migration.store import MigrationStore
```

- [ ] **Step 2: Write the failing test**

Append to `tests/migration/test_store.py`:

```python
class TestUpdateDecisionContext:
    """Targeted context-column update for cross-decision enrichment."""

    def _seed(self, store: MigrationStore) -> None:
        store.save_decision({
            "decision_id": "D0001",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:abc missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:abc",
                "missing_fields": ["mac"],
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_d0001",
            "run_id": store.current_run_id,
        })

    def test_patches_context_in_place(self) -> None:
        store = MigrationStore(":memory:")
        self._seed(store)

        new_ctx = {
            "object_type": "device",
            "canonical_id": "phone:abc",
            "missing_fields": ["mac"],
            "is_on_incompatible_device": True,
        }
        store.update_decision_context("D0001", new_ctx)

        dec = store.get_decision("D0001")
        assert dec is not None
        assert dec["context"]["is_on_incompatible_device"] is True
        # Untouched columns must stay put.
        assert dec["type"] == "MISSING_DATA"
        assert dec["severity"] == "MEDIUM"
        assert dec["summary"] == "phone:abc missing mac"
        assert dec["fingerprint"] == "fp_d0001"
        assert dec["chosen_option"] is None

    def test_raises_on_unknown_decision_id(self) -> None:
        store = MigrationStore(":memory:")
        with pytest.raises(KeyError):
            store.update_decision_context("D_DOES_NOT_EXIST", {"x": 1})

    def test_idempotent(self) -> None:
        store = MigrationStore(":memory:")
        self._seed(store)
        ctx = {
            "object_type": "device",
            "canonical_id": "phone:abc",
            "missing_fields": ["mac"],
            "is_on_incompatible_device": False,
        }
        store.update_decision_context("D0001", ctx)
        store.update_decision_context("D0001", ctx)
        dec = store.get_decision("D0001")
        assert dec["context"]["is_on_incompatible_device"] is False
```

- [ ] **Step 3: Run the failing test**

```bash
python3.11 -m pytest tests/migration/test_store.py::TestUpdateDecisionContext -v
```

Expected: FAIL with `AttributeError: 'MigrationStore' object has no attribute 'update_decision_context'`.

- [ ] **Step 4: Implement `update_decision_context`**

Edit `src/wxcli/migration/store.py`. Immediately after the `save_decision()` method (ends around line 503), add:

```python
    def update_decision_context(
        self,
        decision_id: str,
        context: dict[str, Any],
    ) -> None:
        """Patch only the ``context`` column of an existing decision row.

        Used by ``enrich_cross_decision_context()`` to write cross-decision
        fields (e.g., ``is_on_incompatible_device``) into a MISSING_DATA
        decision without re-fingerprinting or touching other columns.

        Raises ``KeyError`` if the decision_id does not exist.
        """
        cursor = self.conn.execute(
            "UPDATE decisions SET context = ? WHERE decision_id = ?",
            (json.dumps(context), decision_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"decision_id not found: {decision_id}")
        self.conn.commit()
```

Verify the file already imports `json` at the top (it does — `save_decision` already calls `json.dumps` on context).

- [ ] **Step 5: Run the test to verify it passes**

```bash
python3.11 -m pytest tests/migration/test_store.py::TestUpdateDecisionContext -v
```

Expected: 3 PASS.

- [ ] **Step 6: Sanity-check no existing store tests regressed**

```bash
python3.11 -m pytest tests/migration/test_store.py -v 2>&1 | tail -20
```

Expected: all PASS. If the file didn't exist before and you created it, only the 3 new tests should run.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/store.py tests/migration/test_store.py
git commit -m "$(cat <<'EOF'
feat(migration): add store.update_decision_context for targeted patches

Adds a store method that updates only the `context` column of an existing
decision row without re-fingerprinting or touching other columns. Used
by the forthcoming enrich_cross_decision_context pipeline step to write
`is_on_incompatible_device` into non-stale MISSING_DATA decisions.

Raises KeyError for unknown decision_ids. Idempotent.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add `enrich_cross_decision_context()` helper

**Files:**
- Modify: `src/wxcli/migration/transform/analysis_pipeline.py` (new module-level function, NOT a method on `AnalysisPipeline` — the CLI `decide --apply-auto` branch needs to call it without instantiating a pipeline)
- Test: `tests/migration/transform/test_cross_decision_enrichment.py` (new file)

**Why:** The unified matcher (Task 3) needs a config rule like `{"type": "MISSING_DATA", "match": {"is_on_incompatible_device": true}, "choice": "skip"}` to express the cross-decision case that `_check_auto_apply` handled by hand. For that rule to match, something has to write `is_on_incompatible_device` into each MISSING_DATA decision's context. This helper does exactly that, scanning the store for non-stale DEVICE_INCOMPATIBLE decisions and marking every non-stale MISSING_DATA decision whose canonical_id (or any of its `_affected_objects`) appears in that set.

- [ ] **Step 1: Create the new test file**

Create `tests/migration/transform/test_cross_decision_enrichment.py` with this content:

```python
"""Tests for enrich_cross_decision_context().

This helper writes `is_on_incompatible_device: bool` into every non-stale
MISSING_DATA decision's context, based on the set of non-stale
DEVICE_INCOMPATIBLE decisions in the store. The new default auto-rule
`{type: MISSING_DATA, match: {is_on_incompatible_device: true}, choice: skip}`
consumes this field.
"""

from __future__ import annotations

import hashlib

import pytest

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analysis_pipeline import (
    enrich_cross_decision_context,
)


def _fp(did: str, dtype: str) -> str:
    return hashlib.sha256(f"{dtype}:{did}".encode()).hexdigest()[:16]


def _save(
    store: MigrationStore,
    did: str,
    dtype: str,
    context: dict,
    *,
    chosen_option: str | None = None,
) -> None:
    store.save_decision({
        "decision_id": did,
        "type": dtype,
        "severity": "MEDIUM",
        "summary": f"{dtype} {did}",
        "context": context,
        "options": [
            {"id": "skip", "label": "Skip", "impact": "Excluded"},
            {"id": "provide_data", "label": "Provide", "impact": "Supply"},
        ],
        "chosen_option": chosen_option,
        "resolved_at": None,
        "resolved_by": None,
        "fingerprint": _fp(did, dtype),
        "run_id": store.current_run_id,
    })


def test_enrich_no_decisions() -> None:
    store = MigrationStore(":memory:")
    count = enrich_cross_decision_context(store)
    assert count == 0


def test_enrich_no_incompatible_devices() -> None:
    """MISSING_DATA exists but no DEVICE_INCOMPATIBLE → field is False."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
    })
    count = enrich_cross_decision_context(store)
    assert count == 1
    dec = store.get_decision("D0001")
    assert dec["context"]["is_on_incompatible_device"] is False


def test_enrich_one_incompatible_one_missing_match() -> None:
    """DI on phone:001 + MD on phone:001 → True."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "device_id": "phone:001",
        "_affected_objects": ["phone:001"],
    })
    _save(store, "D0002", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
    })
    count = enrich_cross_decision_context(store)
    # Only MISSING_DATA is enriched (DEVICE_INCOMPATIBLE is not touched).
    assert count == 1
    assert store.get_decision("D0002")["context"]["is_on_incompatible_device"] is True
    # DEVICE_INCOMPATIBLE context is untouched.
    assert "is_on_incompatible_device" not in store.get_decision("D0001")["context"]


def test_enrich_via_affected_objects() -> None:
    """MD context without canonical_id but _affected_objects hit → True."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:xyz"],
    })
    _save(store, "D0002", "MISSING_DATA", {
        # No canonical_id — only _affected_objects identifies the device.
        "missing_fields": ["mac"],
        "_affected_objects": ["phone:xyz"],
    })
    count = enrich_cross_decision_context(store)
    assert count == 1
    assert store.get_decision("D0002")["context"]["is_on_incompatible_device"] is True


def test_enrich_idempotent() -> None:
    """Running twice produces the same field values and safe count."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:001"],
    })
    _save(store, "D0002", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
    })
    enrich_cross_decision_context(store)
    # Re-run: field value is stable, no crash.
    enrich_cross_decision_context(store)
    assert store.get_decision("D0002")["context"]["is_on_incompatible_device"] is True


def test_enrich_skips_stale_decisions() -> None:
    """__stale__ decisions are not enriched."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:001"],
    })
    _save(
        store,
        "D0002",
        "MISSING_DATA",
        {
            "object_type": "device",
            "canonical_id": "phone:001",
            "missing_fields": ["mac"],
        },
        chosen_option="__stale__",
    )
    count = enrich_cross_decision_context(store)
    # Stale MD is skipped entirely.
    assert count == 0
    dec = store.get_decision("D0002")
    assert "is_on_incompatible_device" not in dec["context"]


def test_md_fingerprint_stable_before_and_after_enrichment() -> None:
    """Fingerprint-safety guard: MissingDataAnalyzer.fingerprint() only
    hashes type + canonical_id + sorted(missing_fields). Enriching the
    context with is_on_incompatible_device must NOT change what a future
    merge_decisions() call would compute as the fingerprint for the same
    decision. This is load-bearing for the enrichment-before-rules design.
    """
    from wxcli.migration.models import DecisionType
    from wxcli.migration.transform.analyzers.missing_data import MissingDataAnalyzer

    analyzer = MissingDataAnalyzer()
    ctx_before = {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac", "owner_canonical_id"],
    }
    ctx_after = dict(ctx_before)
    ctx_after["is_on_incompatible_device"] = True

    fp_before = analyzer.fingerprint(DecisionType.MISSING_DATA, ctx_before)
    fp_after = analyzer.fingerprint(DecisionType.MISSING_DATA, ctx_after)
    assert fp_before == fp_after
```

- [ ] **Step 2: Run the failing test**

```bash
python3.11 -m pytest tests/migration/transform/test_cross_decision_enrichment.py -v
```

Expected: ImportError / collection failure because `enrich_cross_decision_context` is not defined in `analysis_pipeline.py`.

- [ ] **Step 3: Implement `enrich_cross_decision_context` in `analysis_pipeline.py`**

Edit `src/wxcli/migration/transform/analysis_pipeline.py`. Add a new module-level function after the `ALL_ANALYZERS` list (around line 58, before the `class AnalysisPipeline:` definition):

```python
def enrich_cross_decision_context(store: MigrationStore) -> int:
    """Enrich pending MISSING_DATA decisions with cross-decision context.

    For each non-stale MISSING_DATA decision, set::

        context["is_on_incompatible_device"] = bool

    based on whether the MD decision's ``canonical_id`` or any of its
    ``_affected_objects`` appears in the set of canonical_ids that have a
    non-stale DEVICE_INCOMPATIBLE decision.

    Returns the count of MISSING_DATA decisions that were written.
    (DEVICE_INCOMPATIBLE decisions are read but not modified.)

    Idempotent: re-running with the same store state produces the same
    field values. Fingerprint-safe: the enriched field is NOT part of
    MissingDataAnalyzer.fingerprint() (which hashes only type +
    canonical_id + sorted(missing_fields)), so subsequent merge_decisions()
    runs cannot stale-mark enriched decisions.
    """
    all_decisions = store.get_all_decisions()

    # Collect canonical_ids of non-stale DEVICE_INCOMPATIBLE decisions.
    incompatible_ids: set[str] = set()
    for d in all_decisions:
        if d.get("type") != "DEVICE_INCOMPATIBLE":
            continue
        if d.get("chosen_option") == "__stale__":
            continue
        ctx = d.get("context", {})
        for obj_id in ctx.get("_affected_objects", []):
            incompatible_ids.add(obj_id)
        if ctx.get("device_id"):
            incompatible_ids.add(ctx["device_id"])
        if ctx.get("canonical_id"):
            incompatible_ids.add(ctx["canonical_id"])

    updated = 0
    for d in all_decisions:
        if d.get("type") != "MISSING_DATA":
            continue
        if d.get("chosen_option") == "__stale__":
            continue
        ctx = dict(d.get("context", {}))
        canonical_id = ctx.get("canonical_id")
        affected = ctx.get("_affected_objects", [])
        hit = bool(
            (canonical_id and canonical_id in incompatible_ids)
            or any(aid in incompatible_ids for aid in affected)
        )
        ctx["is_on_incompatible_device"] = hit
        store.update_decision_context(d["decision_id"], ctx)
        updated += 1

    return updated
```

- [ ] **Step 4: Run the tests**

```bash
python3.11 -m pytest tests/migration/transform/test_cross_decision_enrichment.py -v
```

Expected: 7 PASS (the 6 enrichment tests + the fingerprint-stability guard).

- [ ] **Step 5: Sanity-check the existing analysis pipeline tests still pass**

```bash
python3.11 -m pytest tests/migration/transform/test_analysis_pipeline.py -v 2>&1 | tail -30
```

Expected: PASS (no regression — we only added a new module-level function, didn't change `AnalysisPipeline.run()` yet).

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/analysis_pipeline.py tests/migration/transform/test_cross_decision_enrichment.py
git commit -m "$(cat <<'EOF'
feat(migration): add enrich_cross_decision_context helper

Adds a module-level helper in analysis_pipeline.py that writes
`is_on_incompatible_device: bool` into every non-stale MISSING_DATA
decision's context, based on the set of non-stale DEVICE_INCOMPATIBLE
decisions in the store. Idempotent and fingerprint-safe
(MissingDataAnalyzer.fingerprint() hashes only type + canonical_id +
sorted(missing_fields), so the new field cannot stale-mark decisions
on a subsequent merge).

Not wired into AnalysisPipeline.run() yet — that happens in Task 3.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Wire enrichment into `AnalysisPipeline.run()` and `resolve_and_cascade()`

**Files:**
- Modify: `src/wxcli/migration/transform/analysis_pipeline.py` (`AnalysisPipeline.run()` around the existing "Step 3" / "Step 4" comments at lines 124-148; `resolve_and_cascade()` after the cascade save loop at ~line 306)
- Test: `tests/migration/transform/test_cross_decision_enrichment.py` (append one cascade test); also rely on existing `tests/migration/transform/test_analysis_pipeline.py` staying green

**Why:** The enrichment helper exists but isn't called from any pipeline step yet. `AnalysisPipeline.run()` needs to call it between merge and auto-rule application (spec step 3.5). `resolve_and_cascade()` also needs to call it at the end of the save loop because a cascade that re-runs `MissingDataAnalyzer` (e.g., from `LOCATION_AMBIGUOUS` resolution) would otherwise leave newly-produced MISSING_DATA decisions without the `is_on_incompatible_device` field. Spec's "Cascade-path enrichment" paragraph makes this explicit.

- [ ] **Step 1: Write the failing cascade test**

Append this test to `tests/migration/transform/test_cross_decision_enrichment.py`:

```python
def test_cascade_produced_md_decisions_enriched() -> None:
    """When resolve_and_cascade() re-runs MissingDataAnalyzer, the newly
    produced MISSING_DATA decisions must have is_on_incompatible_device
    set on first save. We verify this by spying on the pipeline's
    resolve_and_cascade call and asserting the store state afterwards.

    This test uses a lightweight hand-crafted scenario rather than running
    the full MissingDataAnalyzer: we pre-seed a DEVICE_INCOMPATIBLE decision,
    a LOCATION_AMBIGUOUS decision with cascades_to: ["MISSING_DATA"], and
    a stub "cascade-produced" MISSING_DATA decision via save_decision
    (simulating what the analyzer would produce). Then we call
    enrich_cross_decision_context manually to verify that if the cascade
    path were to call it, the cascade-produced MD decision would be enriched.

    The end-to-end wiring (that resolve_and_cascade actually calls the
    helper) is verified by test_resolve_and_cascade_enriches_md below.
    """
    store = MigrationStore(":memory:")
    _save(store, "DI01", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:cascade"],
    })
    # Simulate a MISSING_DATA decision produced by the cascade analyzer.
    _save(store, "MD01", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:cascade",
        "missing_fields": ["mac"],
    })

    enrich_cross_decision_context(store)
    assert store.get_decision("MD01")["context"]["is_on_incompatible_device"] is True


def test_resolve_and_cascade_enriches_md() -> None:
    """End-to-end: resolve_and_cascade() must call enrich_cross_decision_context
    after its save loop. We use a real AnalysisPipeline with a stub
    analyzer class list that produces one MISSING_DATA decision during
    cascade, and a pre-seeded DEVICE_INCOMPATIBLE decision with a matching
    canonical_id. After the cascade resolves, the MD decision must have
    is_on_incompatible_device=True.
    """
    from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
    from wxcli.migration.transform.analyzers.missing_data import MissingDataAnalyzer
    from wxcli.migration.models import DecisionType

    store = MigrationStore(":memory:")

    # 1. Seed a non-stale DEVICE_INCOMPATIBLE decision that matches phone:xyz.
    _save(store, "DI01", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:xyz"],
    })

    # 2. Seed a LOCATION_AMBIGUOUS decision with cascades_to=["MISSING_DATA"].
    _save(store, "LA01", "LOCATION_AMBIGUOUS", {
        "name": "HQ",
        "cascades_to": ["MISSING_DATA"],
    })

    # 3. Build a MissingDataAnalyzer subclass that produces one MISSING_DATA
    #    decision for phone:xyz when analyze() is called. We use the base
    #    class's _create_decision helper so the Decision is constructed
    #    correctly (decision_id auto-generated, fingerprint computed via
    #    self.fingerprint, run_id wired, canonical field names).
    class _StubMD(MissingDataAnalyzer):
        name = "stub_missing_data"
        decision_types = [DecisionType.MISSING_DATA]

        def analyze(self, store):  # type: ignore[override]
            return [
                self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary="phone:xyz missing mac",
                    context={
                        "object_type": "device",
                        "canonical_id": "phone:xyz",
                        "missing_fields": ["mac"],
                    },
                    options=[],
                    affected_objects=["phone:xyz"],
                )
            ]

    pipeline = AnalysisPipeline(analyzers=[_StubMD])
    pipeline.resolve_and_cascade(store, "LA01", "accept", resolved_by="user")

    # The cascade-produced MD decision must be enriched.
    md_decisions = [d for d in store.get_all_decisions() if d.get("type") == "MISSING_DATA"]
    assert len(md_decisions) >= 1
    assert any(
        d["context"].get("is_on_incompatible_device") is True
        for d in md_decisions
    )
```

**Why `self._create_decision(...)` and NOT a raw `Decision(...)` literal?** `Decision` is a Pydantic `BaseModel` defined at `src/wxcli/migration/models.py:141-159`. Its required fields are `decision_id: str`, `type: DecisionType` (NOT `decision_type`), `severity: str`, `summary: str`, `context: dict`, `options: list[DecisionOption]`, `fingerprint: str` (a STRING, not a callable), and `run_id: str`. Writing a raw constructor by hand is error-prone. The `Analyzer._create_decision(...)` helper at `src/wxcli/migration/transform/analyzers/__init__.py:77-101` is the canonical way to build a `Decision` — it auto-generates `decision_id` via `store.next_decision_id()`, computes `fingerprint = self.fingerprint(decision_type, context)`, and populates `run_id = store.current_run_id`. Every real analyzer uses it. The stub here inherits from `MissingDataAnalyzer`, which inherits from `Analyzer`, so `self._create_decision` is available.

- [ ] **Step 2: Run the failing tests**

```bash
python3.11 -m pytest tests/migration/transform/test_cross_decision_enrichment.py::test_resolve_and_cascade_enriches_md -v
```

Expected: FAIL — `resolve_and_cascade()` doesn't currently call `enrich_cross_decision_context`.

The `test_cascade_produced_md_decisions_enriched` test should PASS (it just verifies the helper works on a seeded scenario, which Task 2 already covered).

- [ ] **Step 3: Wire enrichment into `AnalysisPipeline.run()`**

Edit `src/wxcli/migration/transform/analysis_pipeline.py`. Find the block between the merge (`merge_result = store.merge_decisions(...)`) and the auto-rule application (`auto_resolved = apply_auto_rules(store, self.config)`). Insert a new step 3.5:

```python
        # Step 3.5: Enrich cross-decision context.
        # Writes is_on_incompatible_device into every non-stale MISSING_DATA
        # decision based on the current set of DEVICE_INCOMPATIBLE decisions.
        # Runs between merge and auto-rules so config rules can match the
        # enriched field. Fingerprint-safe (MissingDataAnalyzer.fingerprint()
        # does not hash the full context).
        try:
            enriched = enrich_cross_decision_context(store)
            if enriched:
                logger.info(
                    "Cross-decision enrichment: %d MISSING_DATA decisions updated",
                    enriched,
                )
        except Exception as exc:
            logger.warning("Cross-decision enrichment failed: %s", exc)
```

Place this immediately AFTER the `logger.info("Decision merge: kept=%d, ...")` call and BEFORE the `# Step 4: Apply auto-resolution rules` comment.

- [ ] **Step 4: Refresh the `AnalysisPipeline.run()` docstring**

The current docstring (lines 82-89) lists 4 steps but the inline comments go up to step 7. Replace the docstring with an accurate enumeration that includes step 3.5. Keep it concise:

```python
    def run(self, store: MigrationStore) -> AnalysisResult:
        """Run all analyzers, merge decisions, enrich, apply rules, run advisor.

        Steps:
        1. Sort analyzers by depends_on (topological)
        2. Run each analyzer, collect decisions
        3. Merge new decisions with existing (fingerprint-based)
        3.5. Enrich cross-decision context (is_on_incompatible_device)
        4. Apply auto-resolution rules from config
        5. Run ArchitectureAdvisor (Phase 2)
        6. Populate recommendations on all decisions
        7. Transition shared_line objects from normalized → analyzed

        Returns AnalysisResult with all decisions and per-analyzer stats.
        """
```

This is a doc-only fix. No behavior change beyond the new step.

- [ ] **Step 5: Wire enrichment into `resolve_and_cascade()`**

In the same file, find `resolve_and_cascade()` (around line 204). After the cascade save loop (`for d in new_dicts: ... store.save_decision(d)`) and BEFORE the `# Step 5: Build warnings` comment, add:

```python
        # Enrich cross-decision context for cascade-produced MD decisions.
        # A LOCATION_AMBIGUOUS → MISSING_DATA cascade would otherwise leave
        # newly-produced MD decisions without is_on_incompatible_device.
        try:
            enrich_cross_decision_context(store)
        except Exception as exc:
            logger.warning("Cross-decision enrichment (cascade) failed: %s", exc)
```

- [ ] **Step 6: Run the new tests**

```bash
python3.11 -m pytest tests/migration/transform/test_cross_decision_enrichment.py -v
```

Expected: all 8 PASS (7 from Task 2 + 1 from this task).

- [ ] **Step 7: Run the existing pipeline tests**

```bash
python3.11 -m pytest tests/migration/transform/test_analysis_pipeline.py tests/migration/transform/test_pipeline.py tests/migration/transform/test_integration.py -v 2>&1 | tail -40
```

Expected: all PASS. The enrichment step is idempotent and writes only into non-stale MISSING_DATA decisions; it should not change the behavior of any existing test that doesn't specifically check for the new field.

- [ ] **Step 8: Commit**

```bash
git add src/wxcli/migration/transform/analysis_pipeline.py tests/migration/transform/test_cross_decision_enrichment.py
git commit -m "$(cat <<'EOF'
feat(migration): wire cross-decision enrichment into analysis pipeline

Inserts enrich_cross_decision_context() as step 3.5 of AnalysisPipeline.run(),
between decision merge and auto-rule application. Also calls it at the end
of resolve_and_cascade()'s save loop so cascade-produced MISSING_DATA
decisions get the is_on_incompatible_device field.

Refreshes the AnalysisPipeline.run() docstring to enumerate all 7 steps
(previously listed 4).

No config rule consumes the new field yet — that comes in Task 5 when
DEFAULT_AUTO_RULES is extended.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Refactor `rules.py` — add `_iter_matching_resolutions` and `preview_auto_rules`

**Files:**
- Modify: `src/wxcli/migration/transform/rules.py` (refactor `apply_auto_rules`; add `_iter_matching_resolutions`; add `preview_auto_rules`)
- Test: `tests/migration/transform/test_rules.py` (append a new `TestPreviewAutoRules` class with ~9 new tests; existing tests must stay green)

**Why:** The matcher has to serve two callers: `apply_auto_rules` (mutates the store via `resolve_decision`) and `classify_decisions`/`preview_auto_rules` (pure read, no mutation). To prevent drift between mutate and preview, both must walk the same rule-match logic. Extracting `_iter_matching_resolutions` as a generator is the simplest way to share the walk.

`preview_auto_rules` also needs to surface a human-readable reason. Rules get an optional `reason: str` field. Non-string values fall back to a synthesized reason with a `logger.warning`.

Option-validation parity: if a rule matches but the `choice` isn't in the decision's `options` list, `apply_auto_rules` skips it with a warning (rules.py:169-178 today). `_iter_matching_resolutions` must do the same so preview and apply stay consistent.

- [ ] **Step 1: Write the failing tests**

Append to `tests/migration/transform/test_rules.py` (at the end of the file, after `TestAutoRulesMatchField`):

```python
# ---------------------------------------------------------------------------
# Preview API + reason field + resolved_by marker + regression guards
# ---------------------------------------------------------------------------


class TestPreviewAutoRules:
    """Tests for preview_auto_rules() — pure-read matcher preview.

    preview_auto_rules walks the same matcher logic as apply_auto_rules
    but yields (decision, auto_choice, auto_reason) without mutating the
    store. Both functions share the same internal _iter_matching_resolutions
    generator so they cannot drift on matcher semantics.
    """

    def test_preview_auto_rules_returns_pending_only(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(
            store,
            "D0002",
            dec_type="DEVICE_INCOMPATIBLE",
            chosen_option="skip",
            resolved_by="user",
        )

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)

        ids = {d["decision_id"] for d in result}
        assert ids == {"D0001"}
        # Pure read: store is unchanged.
        assert store.get_decision("D0001")["chosen_option"] is None

    def test_preview_auto_rules_skips_resolved_decisions(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(
            store,
            "D0001",
            dec_type="DEVICE_INCOMPATIBLE",
            chosen_option="manual",
            resolved_by="user",
        )

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)
        assert result == []

    def test_preview_auto_rules_returns_auto_choice_and_reason(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)
        assert len(result) == 1
        d = result[0]
        assert d["auto_choice"] == "skip"
        assert d["auto_reason"]  # non-empty synthesized reason

    def test_preview_auto_rules_uses_rule_reason_field_when_present(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {
                    "type": "DEVICE_INCOMPATIBLE",
                    "choice": "skip",
                    "reason": "No migration path exists for this model",
                },
            ]
        }
        result = preview_auto_rules(store, config)
        assert result[0]["auto_reason"] == "No migration path exists for this model"

    def test_preview_auto_rules_falls_back_to_synthesized_reason(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)
        reason = result[0]["auto_reason"]
        # Synthesized form must mention both the type and the choice.
        assert "DEVICE_INCOMPATIBLE" in reason
        assert "skip" in reason

    def test_preview_auto_rules_falls_back_when_reason_is_non_string(self, caplog) -> None:
        """Non-string reason → fall back to synthesized form and log a warning."""
        import logging
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(store, "D0002", dec_type="DEVICE_FIRMWARE_CONVERTIBLE")

        config = {
            "auto_rules": [
                # Non-string reason: list
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip",
                 "reason": ["a", "b"]},
                # Non-string reason: dict
                {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert",
                 "reason": {"x": 1}},
            ]
        }
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.transform.rules"):
            result = preview_auto_rules(store, config)

        # Both decisions are still previewed (bad reason doesn't break matching).
        assert len(result) == 2
        for d in result:
            # Synthesized fallback, not the raw bad value.
            assert isinstance(d["auto_reason"], str)
            assert d["auto_reason"]

        # At least one warning about a non-string reason was logged.
        warnings = [
            r for r in caplog.records
            if "reason" in r.getMessage().lower() and r.levelname == "WARNING"
        ]
        assert warnings, f"Expected a non-string reason warning, got {caplog.records}"

    def test_preview_auto_rules_skips_invalid_choices(self) -> None:
        """Option-validation parity with apply_auto_rules: rules whose
        choice isn't in the decision's options are not yielded."""
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "nonexistent_choice"},
            ]
        }
        result = preview_auto_rules(store, config)
        assert result == []

    def test_apply_auto_rules_uses_resolved_by_auto_rule(self) -> None:
        """Regression guard: the resolved_by marker must be 'auto_rule'
        (not the legacy 'auto_apply') for every rule-driven resolution."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        apply_auto_rules(store, config)

        dec = store.get_decision("D0001")
        assert dec["resolved_by"] == "auto_rule"

    def test_calling_permission_mismatch_with_users_not_silently_skipped(self) -> None:
        """Regression guard for the Bug F silent data-loss case.

        Before the unification, decide --apply-auto ran _check_auto_apply
        which read a nonexistent key and always treated user_count as 0 —
        silently skipping every pending CALLING_PERMISSION_MISMATCH. After
        the unification, the default rule (match on assigned_users_count == 0)
        correctly does NOT match a decision with assigned_users_count == 5.
        """
        store = _make_store()
        store.save_decision({
            "decision_id": "D_CPM_01",
            "type": "CALLING_PERMISSION_MISMATCH",
            "severity": "MEDIUM",
            "summary": "Permission profile with 5 users",
            "context": {"assigned_users_count": 5, "profile_name": "Internal"},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Manual"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_cpm_01",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {"type": "CALLING_PERMISSION_MISMATCH",
                 "match": {"assigned_users_count": 0},
                 "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)
        assert count == 0
        assert store.get_decision("D_CPM_01")["chosen_option"] is None

    def test_md_rule_does_not_fire_when_device_is_compatible(self) -> None:
        """The new default MD rule must not fire when
        is_on_incompatible_device is False or absent."""
        store = _make_store()
        store.save_decision({
            "decision_id": "D_MD_01",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:001",
                "missing_fields": ["mac"],
                "is_on_incompatible_device": False,
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_md_01",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {"type": "MISSING_DATA",
                 "match": {"is_on_incompatible_device": True},
                 "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)
        assert count == 0
        assert store.get_decision("D_MD_01")["chosen_option"] is None

    def test_analyze_then_apply_auto_is_no_op(self) -> None:
        """Idempotent re-run: running apply_auto_rules twice resolves N the
        first time and 0 the second time."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(store, "D0002", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        first = apply_auto_rules(store, config)
        second = apply_auto_rules(store, config)
        assert first == 2
        assert second == 0
```

- [ ] **Step 2: Run the failing tests**

```bash
python3.11 -m pytest tests/migration/transform/test_rules.py::TestPreviewAutoRules -v
```

Expected: collection error or multiple FAILs (most tests reference `preview_auto_rules` which doesn't exist yet; `test_apply_auto_rules_uses_resolved_by_auto_rule`, `test_md_rule_does_not_fire_when_device_is_compatible`, and `test_analyze_then_apply_auto_is_no_op` may PASS pre-refactor because they exercise existing `apply_auto_rules` behavior that already works).

- [ ] **Step 3: Refactor `rules.py`**

Replace the body of `src/wxcli/migration/transform/rules.py` (from the `_match_rule` function onward) to add `_iter_matching_resolutions`, rewrite `apply_auto_rules` as a consumer, and add `preview_auto_rules`. The `_match_rule` helper is unchanged.

New code to add AFTER `_match_rule` (keep `_match_rule` at lines 21-91 as-is):

```python
def _synthesized_reason(dec_type: str, choice: str) -> str:
    """Default reason when a rule has no explicit `reason` field."""
    return f"Auto-rule: {dec_type} → {choice}"


def _resolve_reason(rule: dict[str, Any], dec_type: str, choice: str) -> str:
    """Pick the reason string for a matched rule.

    Prefer rule['reason'] if it is a non-empty string. Otherwise (missing,
    None, empty, or non-string), fall back to the synthesized form and
    log a warning for the non-string case.
    """
    raw = rule.get("reason")
    if isinstance(raw, str) and raw:
        return raw
    if raw is not None and not isinstance(raw, str):
        logger.warning(
            "auto-rule reason field is not a string (got %r), using synthesized reason",
            type(raw).__name__,
        )
    return _synthesized_reason(dec_type, choice)


def _iter_matching_resolutions(
    store: MigrationStore,
    config: dict[str, Any],
):
    """Yield ``(decision, choice, reason)`` for every pending decision that
    a config rule would resolve. Pure read — does NOT mutate the store.

    Both ``apply_auto_rules`` and ``preview_auto_rules`` consume this
    generator so they cannot drift on matcher semantics.

    Walks the same rules in the same order as the pre-refactor
    ``apply_auto_rules`` (first-match-wins within a decision type). Skips:
    - already-resolved decisions (``chosen_option is not None``)
    - malformed rules (missing type or choice)
    - rules whose match clause fails
    - rules whose ``choice`` is not in the decision's ``options`` list
      (option-validation parity with ``apply_auto_rules``)
    """
    rules = config.get("auto_rules", [])
    if not rules:
        return

    valid_rules: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("type") and rule.get("choice"):
            valid_rules.append(rule)

    if not valid_rules:
        return

    all_decisions = store.get_all_decisions()

    for dec in all_decisions:
        if dec.get("chosen_option") is not None:
            continue

        dec_type = dec.get("type", "")

        for rule in valid_rules:
            if rule["type"] != dec_type:
                continue
            if not _match_rule(rule, dec):
                continue

            choice = rule["choice"]

            # Option-validation parity with apply_auto_rules.
            options = dec.get("options", [])
            valid_ids = {opt["id"] for opt in options if isinstance(opt, dict)}
            if valid_ids and choice not in valid_ids:
                logger.warning(
                    "Auto-rule choice '%s' for decision %s (type=%s) "
                    "is not a valid option. Valid: %s. Skipping.",
                    choice,
                    dec.get("decision_id", ""),
                    dec_type,
                    valid_ids,
                )
                continue

            reason = _resolve_reason(rule, dec_type, choice)
            yield dec, choice, reason
            break  # First matching rule wins for this decision


def preview_auto_rules(
    store: MigrationStore,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the list of pending decisions that current config rules would
    resolve, each augmented with ``auto_choice`` and ``auto_reason`` keys.

    Pure read: does NOT mutate the store. Used by ``classify_decisions``
    and the CLI preview path in ``wxcli cucm decide --apply-auto``.
    """
    result: list[dict[str, Any]] = []
    for dec, choice, reason in _iter_matching_resolutions(store, config):
        d = dict(dec)
        d["auto_choice"] = choice
        d["auto_reason"] = reason
        result.append(d)
    return result
```

Then REPLACE the existing `apply_auto_rules` body (lines 94-195) with a new consumer implementation:

```python
def apply_auto_rules(store: MigrationStore, config: dict[str, Any]) -> int:
    """Apply auto-resolution rules from config to pending decisions.

    Consumes ``_iter_matching_resolutions`` so apply and preview cannot
    drift on matcher semantics.

    Config format (from 03-conflict-detection-engine.md, Auto-Resolution Rules)::

        {"auto_rules": [
            {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            {"type": "DEVICE_FIRMWARE_CONVERTIBLE",
             "match": {"cucm_model": ["7841", "7861"]},
             "choice": "convert",
             "reason": "Optional human-readable reason"},
            {"type": "DN_AMBIGUOUS",
             "match": {"dn_length_lte": 4},
             "choice": "extension_only"},
        ]}

    Match field supports plain values (exact/list membership), ``_lte``/
    ``_gte``/``_contains`` suffixes, and AND logic across multiple fields.

    Each resolved decision gets::

        chosen_option = <choice from rule>
        resolved_by   = "auto_rule"
        resolved_at   = current UTC timestamp

    Returns count of decisions auto-resolved.

    (from 03-conflict-detection-engine.md, Auto-Resolution Rules)
    """
    resolved_count = 0
    for dec, choice, _reason in _iter_matching_resolutions(store, config):
        store.resolve_decision(
            decision_id=dec["decision_id"],
            chosen_option=choice,
            resolved_by="auto_rule",
        )
        resolved_count += 1
        logger.debug(
            "Auto-resolved decision %s (type=%s) with choice='%s'",
            dec.get("decision_id", ""),
            dec.get("type", ""),
            choice,
        )

    logger.info("Auto-rules resolved %d decision(s)", resolved_count)
    return resolved_count
```

**Important:** `_iter_matching_resolutions` reads the store via `store.get_all_decisions()` once at generator start. The generator yields decision snapshots. Because `apply_auto_rules` mutates `chosen_option` during iteration via `store.resolve_decision`, the in-memory snapshots do NOT reflect the mutation — which is fine because each decision is yielded at most once and the rule walk is first-match-wins per decision. Do NOT cache decisions across generator calls or rely on the generator being a live view of the store.

- [ ] **Step 4: Run the new tests**

```bash
python3.11 -m pytest tests/migration/transform/test_rules.py::TestPreviewAutoRules -v
```

Expected: 11 PASS.

- [ ] **Step 5: Run the FULL `test_rules.py` file to verify existing tests still pass**

```bash
python3.11 -m pytest tests/migration/transform/test_rules.py -v 2>&1 | tail -30
```

Expected: all existing 12 tests PASS (including the critical `test_empty_rules_list_returns_zero` canary), plus the new 11 tests. Total 23+ passing.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/rules.py tests/migration/transform/test_rules.py
git commit -m "$(cat <<'EOF'
refactor(migration): unify auto-rule matcher via _iter_matching_resolutions

Extracts the rule-match walk into a private generator
_iter_matching_resolutions that yields (decision, choice, reason)
tuples. Both apply_auto_rules (mutates) and the new preview_auto_rules
(pure read) consume it, so they cannot drift on matcher semantics.

Adds optional `reason` field to rules with non-string fallback + warning
log. apply_auto_rules semantics unchanged (all 12 existing test_rules.py
tests still pass, including the empty-list canary).

Regression guards added:
- test_apply_auto_rules_uses_resolved_by_auto_rule
- test_calling_permission_mismatch_with_users_not_silently_skipped
  (Bug F silent-skip)
- test_md_rule_does_not_fire_when_device_is_compatible
- test_analyze_then_apply_auto_is_no_op (idempotency)
- test_preview_auto_rules_skips_invalid_choices (option-validation parity)
- test_preview_auto_rules_falls_back_when_reason_is_non_string

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add new `MISSING_DATA` default rule and doc comment

**Files:**
- Modify: `src/wxcli/commands/cucm_config.py` (add one entry to `DEFAULT_AUTO_RULES`; optionally backfill `reason` on existing entries; add doc comment block near the constant)
- Test: use existing `tests/migration/transform/test_rules.py` for direct verification (no new test file here — the field-alignment parametrized test arrives in Task 9)

**Why:** The unified matcher has all the plumbing it needs (preview, reason field, enrichment). Adding the new default rule makes `{"type": "MISSING_DATA", "match": {"is_on_incompatible_device": true}, "choice": "skip"}` the out-of-the-box behavior for new projects. Spec §"commands/cucm_config.py changes".

- [ ] **Step 1: Write a quick verification test**

Append to `tests/migration/transform/test_rules.py` (at the very end, outside `TestPreviewAutoRules`):

```python
class TestDefaultAutoRulesMissingDataEntry:
    """Sanity checks for the new is_on_incompatible_device default rule."""

    def test_default_has_md_incompatible_entry(self) -> None:
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES

        matches = [
            r for r in DEFAULT_AUTO_RULES
            if r.get("type") == "MISSING_DATA"
            and r.get("match", {}).get("is_on_incompatible_device") is True
        ]
        assert len(matches) == 1, (
            f"Expected exactly one MISSING_DATA/is_on_incompatible_device "
            f"rule in DEFAULT_AUTO_RULES, got {len(matches)}"
        )
        rule = matches[0]
        assert rule["choice"] == "skip"
        # Reason is optional but recommended for markdown clarity.
        if "reason" in rule:
            assert isinstance(rule["reason"], str)
            assert rule["reason"]
```

- [ ] **Step 2: Run the failing test**

```bash
python3.11 -m pytest tests/migration/transform/test_rules.py::TestDefaultAutoRulesMissingDataEntry -v
```

Expected: FAIL — the new rule doesn't exist in `DEFAULT_AUTO_RULES` yet.

- [ ] **Step 3: Add the new default rule**

Edit `src/wxcli/commands/cucm_config.py`. Find `DEFAULT_AUTO_RULES` (around lines 17-34). Append a new entry at the end of the list (keeping the existing 7 entries in place):

```python
DEFAULT_AUTO_RULES: list[dict[str, Any]] = [
    # Incompatible devices have no migration path — always skip
    {"type": "DEVICE_INCOMPATIBLE", "choice": "skip",
     "reason": "No MPP migration path exists for this device"},
    # Convertible devices can always be firmware-flashed
    {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert",
     "reason": "Device model can be firmware-converted to MPP"},
    # Hotdesk DN conflicts — primary DN always wins
    {"type": "HOTDESK_DN_CONFLICT", "choice": "keep_primary",
     "reason": "Primary DN takes precedence over hotdesk conflict"},
    # CUCM-only forwarding variants — accept the loss (rarely configured)
    {"type": "FORWARDING_LOSSY", "choice": "accept_loss",
     "reason": "CUCM-specific forwarding variant has no Webex equivalent"},
    # SNR timer controls — accept Webex simplification
    {"type": "SNR_LOSSY", "choice": "accept_loss",
     "reason": "SNR timer controls are simplified in Webex"},
    # Unmappable CUCM button types — no Webex equivalent exists
    {"type": "BUTTON_UNMAPPABLE", "choice": "accept_loss",
     "reason": "CUCM button type has no Webex equivalent"},
    # Calling permissions with 0 affected users — orphaned profile
    # Analyzer writes "assigned_users_count" in context (css_permission.py line 128)
    {"type": "CALLING_PERMISSION_MISMATCH",
     "match": {"assigned_users_count": 0}, "choice": "skip",
     "reason": "Orphaned permission profile — 0 users affected"},
    # Missing data on devices that are already incompatible — skip
    # (fixing missing data on a device we're not migrating is pointless)
    # `is_on_incompatible_device` is written by
    # enrich_cross_decision_context() during analysis_pipeline step 3.5.
    {"type": "MISSING_DATA",
     "match": {"is_on_incompatible_device": True}, "choice": "skip",
     "reason": "Missing data on incompatible device — skipping device anyway"},
]
```

Then, ABOVE the `DEFAULT_AUTO_RULES` constant (replacing the 3-line comment block on lines 14-16), add this documentation block:

```python
# Default auto-resolution rules for clear-cut, low-risk decisions.
#
# These reduce manual review burden without risking incorrect choices.
# Override per-project by writing "auto_rules" to config.json.
#
# IMPORTANT: Defaults are seeded into a project's `config.json` ONCE by
# `wxcli cucm init`. They are NOT applied at runtime — `load_config()`
# reads the saved file literally. Operators who edit `config.json` to
# remove a default can restore it via `wxcli cucm config reset auto_rules`
# (which clobbers any custom rules in `auto_rules` — preserve them by
# hand-editing instead).
#
# To add a new default rule WITHOUT regressing existing in-flight projects:
# 1. Append the rule here.
# 2. Document the upgrade procedure in the relevant runbook.
# 3. Operators on existing projects must either (a) hand-edit their
#    config.json to append the new rule, or (b) run
#    `wxcli cucm config reset auto_rules` (destructive to custom rules).
```

- [ ] **Step 4: Run the sanity test + the existing rules tests**

```bash
python3.11 -m pytest tests/migration/transform/test_rules.py -v 2>&1 | tail -30
```

Expected: all tests PASS, including the new `TestDefaultAutoRulesMissingDataEntry` test.

Also run the `cucm_config` tests if any exist:

```bash
python3.11 -m pytest tests/migration/test_cucm_cli.py::TestConfig -v
```

Expected: existing config tests still pass (the constant grew by one entry but the tests don't assert on list length).

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/commands/cucm_config.py tests/migration/transform/test_rules.py
git commit -m "$(cat <<'EOF'
feat(migration): add MISSING_DATA / is_on_incompatible_device default rule

Adds the 8th default auto-rule: MISSING_DATA decisions on devices that
are also flagged as DEVICE_INCOMPATIBLE get auto-skipped, because fixing
missing data on a device we're not migrating is pointless. The
`is_on_incompatible_device` field is written by
enrich_cross_decision_context() during the analysis pipeline.

Also backfills human-readable `reason` fields on the existing 7 defaults
for cleaner markdown review output, and adds a documentation block near
DEFAULT_AUTO_RULES explaining the init-time vs runtime semantics and the
in-flight project upgrade procedure.

New projects (created via `wxcli cucm init` after this work ships) get
the rule automatically. Existing projects must hand-edit config.json OR
run `wxcli cucm config reset auto_rules` (added in a later task).

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Rewrite `classify_decisions` and delete `_check_auto_apply`

**Files:**
- Modify: `src/wxcli/migration/transform/decisions.py` (delete `_check_auto_apply` entirely; rewrite `classify_decisions(store, config)`; update `generate_decision_review(store, project_id, config)` signature)
- Test: see Task 7 for the replacement test file; this task runs the rewritten code against the Task 7 tests

**Why:** `_check_auto_apply` is the drifting matcher we're killing. `classify_decisions` becomes a thin wrapper over `preview_auto_rules` from Task 4. Its signature changes from `(store)` to `(store, config)` — every caller must be updated in lockstep (Phase B handles the CLI callers).

Because Task 6 changes the `classify_decisions` signature, **this task temporarily breaks `tests/migration/transform/test_decision_classify.py` and the CLI callers in `cucm.py`**. That's expected — the old tests are retired in Task 7, and the CLI callers are fixed in Phase B.

- [ ] **Step 1: Delete `_check_auto_apply` and rewrite `classify_decisions`**

Edit `src/wxcli/migration/transform/decisions.py`.

1. **Delete `_check_auto_apply`** (the entire function, lines 196-224 in the current file).
2. **Rewrite `classify_decisions`** (lines 136-193) to take a `config` argument and delegate to `preview_auto_rules`:

```python
def classify_decisions(
    store: MigrationStore,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split pending decisions into auto-apply and needs-input groups.

    Auto-apply = pending decisions that the project's ``config["auto_rules"]``
    would resolve. Each item is augmented with ``auto_choice`` and
    ``auto_reason`` keys (from ``preview_auto_rules``).

    Needs-input = pending decisions that no rule matches.

    Both groups exclude already-resolved decisions and ``__stale__``
    decisions.
    """
    from wxcli.migration.transform.rules import preview_auto_rules

    auto_apply = preview_auto_rules(store, config)
    auto_apply_ids = {d["decision_id"] for d in auto_apply}

    all_decisions = store.get_all_decisions()
    needs_input = [
        d for d in all_decisions
        if d.get("chosen_option") is None
        and d.get("chosen_option") != "__stale__"
        and d["decision_id"] not in auto_apply_ids
    ]

    return auto_apply, needs_input
```

3. **Update `generate_decision_review`** (around line 252) to accept and thread `config`:

```python
def generate_decision_review(
    store: MigrationStore,
    project_id: str,
    config: dict[str, Any],
) -> str:
    """Generate a markdown decision review file with auto-apply and needs-input sections."""
    auto_apply, needs_input = classify_decisions(store, config)

    # ... rest of the existing function body is unchanged
```

Keep the rest of `generate_decision_review`'s body as-is — only the signature and the single `classify_decisions(store)` call inside it change.

- [ ] **Step 2: Remove the `defaultdict` import if it was only used by `_check_auto_apply`**

Check the top of `decisions.py` — `from collections import defaultdict` should still be used by the `summarize_decisions`, `format_decision_report`, and `generate_decision_review` helpers. Do NOT remove it unless grep confirms zero remaining uses.

```bash
grep -n "defaultdict" src/wxcli/migration/transform/decisions.py
```

Expected: multiple hits outside `_check_auto_apply`. Keep the import.

- [ ] **Step 3: Run the module smoke import**

```bash
python3.11 -c "from wxcli.migration.transform.decisions import classify_decisions, generate_decision_review; print('ok')"
```

Expected: `ok`. No import errors, no lingering references to `_check_auto_apply`.

- [ ] **Step 4: Confirm the function is gone**

```bash
grep -n "_check_auto_apply" src/wxcli/migration/transform/decisions.py
```

Expected: empty (zero hits). If any hit remains, delete it.

- [ ] **Step 5: Run only the tests that don't depend on the deleted signature**

Several tests will temporarily break:
- `tests/migration/transform/test_decision_classify.py` — uses `classify_decisions(store)` single-arg.
- `tests/migration/test_decision_cli.py` — exercises the CLI which calls `classify_decisions(store)`.

Do NOT fix those now. Just verify the files we DID touch still behave correctly in isolation:

```bash
python3.11 -m pytest tests/migration/transform/test_rules.py -v 2>&1 | tail -20
```

Expected: all PASS (rules tests don't touch `decisions.py`).

The failing tests in `test_decision_classify.py` and `test_decision_cli.py` are addressed in Task 7 (decisions_classify) and Phase B (test_decision_cli).

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/decisions.py
git commit -m "$(cat <<'EOF'
refactor(migration): delete _check_auto_apply, rewrite classify_decisions

Deletes the drifting auto-apply matcher (_check_auto_apply) from
transform/decisions.py. Rewrites classify_decisions(store, config) as
a thin wrapper over preview_auto_rules — both apply_auto_rules and
classify_decisions now consume _iter_matching_resolutions, so the two
code paths cannot drift.

The signature change (added config parameter) propagates to
generate_decision_review. CLI callers in commands/cucm.py are updated
in a later task (Phase B).

This commit temporarily breaks tests in test_decision_classify.py and
test_decision_cli.py (they expect the old single-arg signature). Those
are updated in the next two tasks and in Phase B.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: New `test_classify_decisions.py` + retire old `test_decision_classify.py`

**Files:**
- Create: `tests/migration/transform/test_classify_decisions.py` (new file, covers the `classify_decisions(store, config)` signature)
- Delete: `tests/migration/transform/test_decision_classify.py` (old file, covered the deleted `_check_auto_apply` semantics and the old single-arg signature)

**Why:** The old test file's entire point was verifying `_check_auto_apply`'s hardcoded 3 cases. That function no longer exists. Rather than rewriting every test to pass `config`, it's cleaner to delete the old file and replace it with a small new file focused on the new contract.

- [ ] **Step 1: Create the new test file**

Create `tests/migration/transform/test_classify_decisions.py` with this content:

```python
"""Tests for classify_decisions(store, config).

classify_decisions is a thin wrapper over preview_auto_rules — its
job is to split pending decisions into (auto_apply, needs_input)
groups based on the project's config["auto_rules"].
"""

from __future__ import annotations

import hashlib

import pytest

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.decisions import (
    classify_decisions,
    generate_decision_review,
)


def _fp(did: str, dtype: str) -> str:
    return hashlib.sha256(f"{dtype}:{did}".encode()).hexdigest()[:16]


def _save(
    store: MigrationStore,
    did: str,
    dtype: str,
    context: dict,
    *,
    options: list | None = None,
    chosen_option: str | None = None,
) -> None:
    opts = options or [
        {"id": "skip", "label": "Skip", "impact": "Excluded"},
        {"id": "manual", "label": "Manual", "impact": "Manual"},
    ]
    store.save_decision({
        "decision_id": did,
        "type": dtype,
        "severity": "MEDIUM",
        "summary": f"{dtype} {did}",
        "context": context,
        "options": opts,
        "chosen_option": chosen_option,
        "resolved_at": None,
        "resolved_by": None,
        "fingerprint": _fp(did, dtype),
        "run_id": store.current_run_id,
    })


@pytest.fixture
def store() -> MigrationStore:
    return MigrationStore(":memory:")


def test_classify_returns_auto_apply_from_preview(store: MigrationStore) -> None:
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})
    _save(store, "D0002", "WORKSPACE_LICENSE_TIER", {"workspace_name": "Lobby"})

    config = {
        "auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]
    }
    auto, needs = classify_decisions(store, config)

    auto_ids = {d["decision_id"] for d in auto}
    needs_ids = {d["decision_id"] for d in needs}
    assert "D0001" in auto_ids
    assert "D0002" in needs_ids

    # Auto_apply entries must carry auto_choice + auto_reason (from preview).
    d1 = next(d for d in auto if d["decision_id"] == "D0001")
    assert d1["auto_choice"] == "skip"
    assert d1["auto_reason"]


def test_classify_needs_input_excludes_auto_apply_decisions(
    store: MigrationStore,
) -> None:
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})
    _save(store, "D0002", "DEVICE_INCOMPATIBLE", {})

    config = {
        "auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]
    }
    auto, needs = classify_decisions(store, config)

    assert len(auto) == 2
    # Every decision the config resolves must NOT reappear in needs_input.
    assert needs == []


def test_classify_with_custom_config_rule(store: MigrationStore) -> None:
    """A custom rule in config.json should resolve matching decisions."""
    _save(store, "D0001", "DN_AMBIGUOUS", {"dn_length": 3, "dn": "101"},
          options=[
              {"id": "extension_only", "label": "Extension", "impact": "Internal"},
              {"id": "skip", "label": "Skip", "impact": "Excluded"},
          ])

    config = {
        "auto_rules": [
            {
                "type": "DN_AMBIGUOUS",
                "match": {"dn_length_lte": 4},
                "choice": "extension_only",
                "reason": "3-digit extension matches internal plan",
            }
        ]
    }
    auto, needs = classify_decisions(store, config)

    assert len(auto) == 1
    assert auto[0]["auto_choice"] == "extension_only"
    assert auto[0]["auto_reason"] == "3-digit extension matches internal plan"
    assert needs == []


def test_classify_with_empty_auto_rules(store: MigrationStore) -> None:
    """Empty auto_rules → every pending decision is needs_input."""
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})
    _save(store, "D0002", "WORKSPACE_LICENSE_TIER", {"workspace_name": "Lobby"})

    config = {"auto_rules": []}
    auto, needs = classify_decisions(store, config)
    assert auto == []
    assert {d["decision_id"] for d in needs} == {"D0001", "D0002"}


def test_classify_excludes_resolved_decisions(store: MigrationStore) -> None:
    """Already-resolved decisions must not appear in either group."""
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {}, chosen_option="manual")
    _save(store, "D0002", "DEVICE_INCOMPATIBLE", {})

    config = {
        "auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]
    }
    auto, needs = classify_decisions(store, config)
    assert {d["decision_id"] for d in auto} == {"D0002"}
    assert needs == []


def test_generate_decision_review_threads_config(store: MigrationStore) -> None:
    """generate_decision_review takes config and passes it to classify_decisions."""
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})

    config = {
        "auto_rules": [
            {"type": "DEVICE_INCOMPATIBLE", "choice": "skip",
             "reason": "Custom reason from test"},
        ]
    }
    md = generate_decision_review(store, "test-project", config)
    assert "## Auto-Apply (1 decisions)" in md
    assert "Custom reason from test" in md
```

- [ ] **Step 2: Delete the old test file**

```bash
git rm tests/migration/transform/test_decision_classify.py
```

This is a destructive-looking delete, but it's safe: the old file's tests are all covered by the new `test_classify_decisions.py` contract tests (which now use the new signature) plus the existing `test_rules.py` tests for rule-matching behavior. Do NOT `rm` without `git rm` — we want the deletion tracked in git.

- [ ] **Step 3: Run the new tests**

```bash
python3.11 -m pytest tests/migration/transform/test_classify_decisions.py -v
```

Expected: 6 PASS.

- [ ] **Step 4: Confirm no residual references to the old file**

```bash
grep -rn "test_decision_classify" tests/ docs/ || echo "clean"
```

Expected: `clean`.

- [ ] **Step 5: Commit**

**Note:** the `git rm` from Step 2 already staged the deletion of `test_decision_classify.py` in the index. The `git add` below only stages the new `test_classify_decisions.py`. The single `git commit` below records BOTH the new file AND the deletion in one commit. Do NOT `git restore --staged tests/migration/transform/test_decision_classify.py` — that would undo the deletion.

```bash
git add tests/migration/transform/test_classify_decisions.py
git commit -m "$(cat <<'EOF'
test(migration): add test_classify_decisions.py, delete test_decision_classify.py

Replaces the old test_decision_classify.py (which verified the deleted
_check_auto_apply behavior and the single-arg classify_decisions
signature) with a smaller test_classify_decisions.py that covers the
new (store, config) signature and verifies the preview_auto_rules
delegation.

6 tests: auto_apply/needs_input split, custom rules, empty rules,
resolved-decision exclusion, generate_decision_review config threading.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Field-alignment parametrized test

**Files:**
- Create: `tests/migration/transform/test_default_auto_rules_field_alignment.py` (new file)

**Why:** The CALLING_PERMISSION_MISMATCH silent-skip bug came from analyzer-rule field-name drift: the rule matched on a key the analyzer never wrote. This parametrized test catches the entire class at CI time: for every rule in `DEFAULT_AUTO_RULES` with a `match` field, assert that every match key (stripped of `_lte`/`_gte`/`_contains` suffixes) appears in the producing analyzer's synthetic output or in the cross-decision enrichment output.

Today the test covers two rules:
- `CALLING_PERMISSION_MISMATCH` / `assigned_users_count` — produced by `CSSPermissionAnalyzer` at `css_permission.py:128`.
- `MISSING_DATA` / `is_on_incompatible_device` — produced by `enrich_cross_decision_context`.

Future defaults with match fields get covered automatically when they land in `DEFAULT_AUTO_RULES`.

- [ ] **Step 1: Create the new test file**

Create `tests/migration/transform/test_default_auto_rules_field_alignment.py`:

```python
"""Parametrized test: every DEFAULT_AUTO_RULES match key must exist in
the producing analyzer's (or enrichment's) decision context.

This is a CI-time guard against the class of bugs where a rule references
a context field that no producer writes — the CALLING_PERMISSION_MISMATCH
silent-skip bug (Bug F) was exactly this shape.

New default rules with a `match` field get covered automatically as soon
as they're added to DEFAULT_AUTO_RULES. If a rule matches on a field no
producer knows about, this test fails at collection time (if the analyzer
cannot be identified) or at assert time (if the synthetic producer output
doesn't contain the key).
"""

from __future__ import annotations

from typing import Any

import pytest

from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES


def _strip_operator_suffix(key: str) -> str:
    """Strip _lte / _gte / _contains suffixes for field-name alignment."""
    for suffix in ("_lte", "_gte", "_contains"):
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


# ---------------------------------------------------------------------------
# Synthetic producers: one factory per (decision_type, key) pair.
#
# Each factory returns a dict that represents what the analyzer / enrichment
# would write into a decision's context. The test asserts every stripped
# match key is present in this dict.
#
# When a new default rule lands with a new (type, key), add a factory here.
# ---------------------------------------------------------------------------


def _css_permission_synthetic_context() -> dict[str, Any]:
    """Mirror what CSSPermissionAnalyzer writes at css_permission.py:128."""
    return {
        "profile_name": "test-profile",
        "assigned_users_count": 0,  # key the default rule matches on
        "assigned_users": [],
    }


def _missing_data_enriched_synthetic_context() -> dict[str, Any]:
    """Mirror what enrich_cross_decision_context() writes into MISSING_DATA
    decisions after analysis_pipeline step 3.5."""
    return {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
        "is_on_incompatible_device": True,  # key the default rule matches on
    }


# Registry: decision_type → synthetic context factory.
# Multiple rules for the same type share one factory.
_SYNTHETIC_PRODUCERS: dict[str, Any] = {
    "CALLING_PERMISSION_MISMATCH": _css_permission_synthetic_context,
    "MISSING_DATA": _missing_data_enriched_synthetic_context,
}


# Rules with a `match` field — parametrize over every one.
_RULES_WITH_MATCH = [
    r for r in DEFAULT_AUTO_RULES if r.get("match")
]


@pytest.mark.parametrize(
    "rule",
    _RULES_WITH_MATCH,
    ids=[f"{r['type']}:{','.join(r.get('match', {}))}" for r in _RULES_WITH_MATCH],
)
def test_default_rule_match_fields_are_produced(rule: dict[str, Any]) -> None:
    """Every match key in a default rule must be writable by a known producer.

    Regression guard for analyzer-rule field-name drift.
    """
    dec_type = rule["type"]
    match = rule.get("match", {})
    assert match, f"Rule for {dec_type} has empty match field"

    producer = _SYNTHETIC_PRODUCERS.get(dec_type)
    assert producer is not None, (
        f"No synthetic producer registered for decision type {dec_type!r}. "
        f"Add one to _SYNTHETIC_PRODUCERS in "
        f"test_default_auto_rules_field_alignment.py that mirrors whatever "
        f"analyzer / enrichment writes the context for this decision type."
    )

    ctx = producer()
    missing_keys = []
    for raw_key in match:
        base_key = _strip_operator_suffix(raw_key)
        if base_key not in ctx:
            missing_keys.append(base_key)

    assert not missing_keys, (
        f"Default auto-rule for {dec_type} matches on context fields "
        f"that the synthetic producer does not write: {missing_keys}. "
        f"Either (a) the rule's match field is wrong, or (b) the producer "
        f"actually writes a different key name, or (c) the synthetic "
        f"producer is out of date with the real producer's code."
    )


def test_every_producer_has_at_least_one_rule() -> None:
    """Sanity: every synthetic producer maps to at least one rule. This
    keeps the registry tight — if a producer is removed, the test that
    needs it will fail loudly instead of silently drifting."""
    rule_types = {r["type"] for r in _RULES_WITH_MATCH}
    orphans = [t for t in _SYNTHETIC_PRODUCERS if t not in rule_types]
    assert not orphans, (
        f"_SYNTHETIC_PRODUCERS has factories for decision types with no "
        f"corresponding default rules: {orphans}. Either add a rule or "
        f"remove the producer."
    )
```

- [ ] **Step 2: Run the new tests**

```bash
python3.11 -m pytest tests/migration/transform/test_default_auto_rules_field_alignment.py -v
```

Expected: 2 tests from the parametrized class (one per rule with a `match` field — `CALLING_PERMISSION_MISMATCH` and `MISSING_DATA`) + 1 from `test_every_producer_has_at_least_one_rule`. All PASS.

If one of the parametrized tests fails with "synthetic producer does not write ...", it means either the real producer and the registry here disagree. Fix the registry to match the real producer, not the other way around.

- [ ] **Step 3: Commit**

```bash
git add tests/migration/transform/test_default_auto_rules_field_alignment.py
git commit -m "$(cat <<'EOF'
test(migration): add field-alignment parametrized test for DEFAULT_AUTO_RULES

CI-time guard against analyzer-rule field-name drift (the class of bug
that produced the CALLING_PERMISSION_MISMATCH silent-skip in Bug F).
For every rule in DEFAULT_AUTO_RULES with a `match` field, asserts that
every match key (stripped of _lte/_gte/_contains) exists in the producing
analyzer/enrichment's synthetic output.

Registered producers today:
- CALLING_PERMISSION_MISMATCH → CSSPermissionAnalyzer (assigned_users_count)
- MISSING_DATA → enrich_cross_decision_context (is_on_incompatible_device)

New rules with match fields get covered automatically.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase A exit verification

Run these scoped checks. Do NOT run the full `tests/migration/` suite at this point — the CLI tests in `test_decision_cli.py` will be broken until Phase B.

```bash
python3.11 -m pytest tests/migration/test_store.py \
                     tests/migration/transform/test_rules.py \
                     tests/migration/transform/test_cross_decision_enrichment.py \
                     tests/migration/transform/test_classify_decisions.py \
                     tests/migration/transform/test_default_auto_rules_field_alignment.py \
                     tests/migration/transform/test_analysis_pipeline.py \
                     -v 2>&1 | tail -40
```

Expected: all PASS. If anything fails, return to the failing task's TDD cycle.

```bash
grep -n "_check_auto_apply" src/wxcli/migration/ -r
```

Expected: empty (zero hits). If the grep returns anything, it means Task 6 wasn't fully applied.

```bash
git log --oneline | head -10
```

Expected: 8 new commits (Tasks 1-8) on top of the pre-Phase-A baseline.

Phase A is complete. Proceed to [Phase B](2026-04-07-auto-rule-architecture-unification-plan-phase-b.md).
