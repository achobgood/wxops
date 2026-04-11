# Selective Call Forwarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect CUCM CSS/partition patterns that imply per-caller routing (selective call handling) and produce `FEATURE_APPROXIMATION` advisory decisions recommending the operator configure Webex Selective Forward / Accept / Reject / Priority Alert post-migration.

**Architecture:** A new analyzer (`SelectiveCallHandlingAnalyzer`) sweeps existing store data — DNs, partitions, CSSes, user assignments — using three heuristics (multi-partition DN, low-membership partition, naming convention). It produces `FEATURE_APPROXIMATION` decisions with a distinguishing context key `selective_call_handling_pattern`. A new advisory pattern (`detect_selective_call_handling_opportunities`) summarizes the findings as a cross-cutting `ARCHITECTURE_ADVISORY`. The existing `recommend_feature_approximation` rule is extended to recognize the new context key and recommend `accept`. The assessment report appendix gains a new section that lists candidates by pattern type. No new canonical models, no new mappers, no execution operations — advisory only.

**Tech Stack:** Python 3.11, Pydantic, pytest, SQLite (via `MigrationStore`).

**Spec:** `docs/superpowers/specs/2026-04-10-selective-call-forwarding.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/wxcli/migration/transform/analyzers/selective_call_handling.py` | Create | New analyzer class (`SelectiveCallHandlingAnalyzer`) implementing the 3 heuristics + fingerprint + decision builder |
| `src/wxcli/migration/transform/analysis_pipeline.py` | Modify | Register analyzer in `ALL_ANALYZERS` |
| `src/wxcli/migration/advisory/advisory_patterns.py` | Modify | Add `detect_selective_call_handling_opportunities` + register in `ALL_ADVISORY_PATTERNS` |
| `src/wxcli/migration/advisory/recommendation_rules.py` | Modify | Extend `recommend_feature_approximation` to short-circuit on `selective_call_handling_pattern` context key |
| `src/wxcli/migration/report/appendix.py` | Modify | Add new section `_selective_call_handling()` (letter `AB`) and register in `generate_appendix()` |
| `src/wxcli/migration/report/executive.py` | Modify | Conditionally render selective call handling stat row in feature gaps area |
| `src/wxcli/migration/transform/CLAUDE.md` | Modify | Add row in 13 Analyzers table |
| `src/wxcli/migration/advisory/CLAUDE.md` | Modify | Add new pattern under "Tier 4 feature gap patterns" |
| `docs/knowledge-base/migration/kb-css-routing.md` | Modify | Add "Selective Call Handling Detection" subsection |
| `docs/knowledge-base/migration/kb-user-settings.md` | Modify | Add table rows for the 4 selective call handling features |
| `docs/knowledge-base/migration/kb-feature-mapping.md` | Modify | Add table rows for the 4 selective call handling features |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Modify | Add post-migration verification step |
| `docs/runbooks/cucm-migration/decision-guide.md` | Modify | Add advisory pattern entry under "feature_opportunity" |
| `tests/migration/transform/test_selective_call_handling_analyzer.py` | Create | 10 unit tests for the analyzer |
| `tests/migration/advisory/test_advisory_selective.py` | Create | 5 unit tests for advisory pattern |
| `tests/migration/advisory/test_recommendation_selective.py` | Create | 3 unit tests for recommendation rule extension |
| `tests/migration/transform/test_selective_integration.py` | Create | 3 integration tests covering pipeline + report rendering |

**Pre-existing test failures (DO NOT FIX in this branch — they exist on main):**
1. `tests/migration/report/test_user_notice.py` — missing `populated_store` fixture (1 ERROR)
2. `tests/migration/transferability/test_runbook_cites.py::test_file_line_citations_resolve[operator-runbook.md]` — broken citation to non-existent `docs/plans/cucm-migration-roadmap.md`

These are baseline failures. Verification steps below explicitly skip them.

---

## Background: Code Patterns the Implementer Must Follow

This codebase has several conventions that are not obvious. Read this before starting Task 1.

### Analyzer base class

Defined at `src/wxcli/migration/transform/analyzers/__init__.py`. New analyzers MUST:
- Subclass `Analyzer`
- Set class attrs `name: str`, `decision_types: list[DecisionType]`, `depends_on: list[str]`
- Implement `analyze(store) -> list[Decision]` and `fingerprint(decision_type, context) -> str`
- Use `self._create_decision(...)` (auto-generates `decision_id`, `fingerprint`, `run_id`) instead of building `Decision` objects directly
- Use `self._hash_fingerprint(dict)` for fingerprint hashing (16-char SHA256 prefix)

### CSS / Partition store conventions

CSSes and partitions are intermediate `MigrationObject` types whose `object_type` is derived from the `canonical_id` prefix. Do NOT use `store.get_objects("calling_search_space")` (a known bug in some existing advisory patterns — those patterns silently return empty lists). Use:

- `store.get_objects("css")` — list of CSS dicts
- `store.get_objects("partition")` — list of partition dicts
- `store.find_cross_refs(css_id, "css_contains_partition")` — partition IDs in a CSS (returns list of `to_id` strings)
- `store.find_cross_refs(partition_id, "partition_has_pattern")` — DN/route_pattern IDs in a partition

### DN identity (no DN objects)

DNs are NOT stored as objects. They exist only as cross-ref endpoints with the form `dn:{number}:{partition}` (see `src/wxcli/migration/transform/cross_reference.py:287, :315`). To enumerate DNs in 2+ partitions:

```python
# Query the cross_refs table directly
rows = store.conn.execute(
    "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'dn_in_partition'"
).fetchall()
dn_partitions: dict[str, set[str]] = defaultdict(set)
for row in rows:
    dn_partitions[row["from_id"]].add(row["to_id"])
multi_partition_dns = {dn: parts for dn, parts in dn_partitions.items() if len(parts) >= 2}
```

To find the owner of a DN, query the reverse of `user_has_primary_dn`:

```python
rows = store.conn.execute(
    "SELECT from_id FROM cross_refs WHERE relationship = 'user_has_primary_dn' AND to_id = ?",
    (dn_id,),
).fetchall()
owner_user_ids = [r["from_id"] for r in rows]
```

### Decision creation pattern

Always use `self._create_decision(...)`. The helper writes `_affected_objects` into context, so the fingerprint method MUST NOT include `_affected_objects` itself — it should hash sorted natural keys (canonical_ids you generated, not the helper-injected list).

### Test file conventions

Look at `tests/migration/advisory/test_advisory_intercept.py` and `tests/migration/advisory/test_advisory_executive_assistant.py` as reference. Each test file defines:

```python
def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id="t", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )

def _store(tmp_path, name="t.db"):
    return MigrationStore(os.path.join(str(tmp_path), name))
```

There is NO shared conftest for these tests. Each test file is self-contained.

### Advisory pattern signature

```python
def detect_<name>(store: MigrationStore) -> list[AdvisoryFinding]:
```

Returns `[]` when nothing fires. `AdvisoryFinding` is a dataclass at `advisory_patterns.py` lines 19-34. Constructor: `pattern_name, severity, summary, detail, affected_objects, recommendation="accept", recommendation_reasoning="", category=""`.

Register the function in `ALL_ADVISORY_PATTERNS` at the bottom of `advisory_patterns.py`.

### `_VIP_KEYWORDS` shared constant

The naming heuristic uses a shared keyword set. Define it once at module scope in `selective_call_handling.py`:

```python
_VIP_KEYWORDS = (
    "vip", "executive", "exec", "priority", "direct",
    "bypass", "afterhours", "after_hours", "after-hours", "emergency",
)
```

Match case-insensitively against the partition's `name` field (from `pre_migration_state.partition_name`) AND against the canonical_id suffix.

### Severity / confidence matrix (from spec §4a)

| Signal Combination | Confidence | Severity |
|-------------------|-----------|----------|
| Multi-partition DN + different CSS scopes | HIGH | MEDIUM |
| Low-membership partition + subset CSS reachability | HIGH | MEDIUM |
| Partition name keyword + structural signal | HIGH | MEDIUM |
| Partition name keyword only | LOW | LOW |
| Multi-partition DN without CSS scope difference | LOW | LOW |

The "different CSS scopes" check (spec §2a Pattern 1): two CSSes are considered to have different scopes when one CSS contains a partition the other does not. Implementation: compute the partition set difference between the two user CSSes and check `len(diff) > 0`. This is a coarse heuristic that errs toward firing — combined with severity LOW for the no-owner / no-scope-diff case, false positives stay low priority.

### Multi-site filter (spec §8a mitigation)

Cross-reference multi-partition DNs against location assignments. If two DNs with the same number live in partitions belonging to different `CanonicalUser.location_id` values, this is a multi-site routing pattern, not selective call handling. Filter these out.

Implementation: for each multi-partition DN, look up the owning user via `user_has_primary_dn` reverse query. Get the user's `location_id`. If multiple distinct `location_id` values are present across the partition group, skip the DN.

---

## Task 1: Create the analyzer scaffold and register it

**Files:**
- Create: `src/wxcli/migration/transform/analyzers/selective_call_handling.py`
- Modify: `src/wxcli/migration/transform/analysis_pipeline.py`
- Create: `tests/migration/transform/test_selective_call_handling_analyzer.py`

- [ ] **Step 1: Write the failing test for empty store**

Create `tests/migration/transform/test_selective_call_handling_analyzer.py`:

```python
"""Tests for SelectiveCallHandlingAnalyzer."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser,
    DecisionType,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers.selective_call_handling import (
    SelectiveCallHandlingAnalyzer,
)


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="t",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name: str = "t.db") -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), name))


class TestEmptyStore:
    def test_analyzer_returns_empty_on_empty_store(self, tmp_path):
        store = _store(tmp_path)
        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        assert decisions == []

    def test_analyzer_metadata(self):
        analyzer = SelectiveCallHandlingAnalyzer()
        assert analyzer.name == "selective_call_handling"
        assert DecisionType.FEATURE_APPROXIMATION in analyzer.decision_types
        assert "css_routing" in analyzer.depends_on
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py -v
```

Expected: `ImportError` / `ModuleNotFoundError` for `selective_call_handling`.

- [ ] **Step 3: Create the analyzer scaffold**

Create `src/wxcli/migration/transform/analyzers/selective_call_handling.py`:

```python
"""Selective call handling analyzer for CUCM-to-Webex migration.

Detects CUCM CSS/partition patterns that imply per-caller routing differences
and produces FEATURE_APPROXIMATION advisory decisions recommending Webex
selective call handling features (Selective Forward / Accept / Reject /
Priority Alert).

Three heuristics:
1. Multi-partition DN — same DN in 2+ partitions reachable via different
   user CSSes (internal vs external routing split).
2. Low-membership partition — partition with few DNs that appears in only
   a subset of CSSes (VIP/priority bypass pattern).
3. Naming convention — partition name contains VIP/executive/priority
   keywords (weak signal, only LOW severity unless paired with structural
   signal).

This analyzer reuses DecisionType.FEATURE_APPROXIMATION with a distinguishing
context key `selective_call_handling_pattern`. The recommendation rule and
report renderer key off this context key.

Spec: docs/superpowers/specs/2026-04-10-selective-call-forwarding.md
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


_VIP_KEYWORDS = (
    "vip",
    "executive",
    "exec",
    "priority",
    "direct",
    "bypass",
    "afterhours",
    "after_hours",
    "after-hours",
    "emergency",
)


class SelectiveCallHandlingAnalyzer(Analyzer):
    """Detects CSS/partition patterns suggesting selective call handling.

    See module docstring for the three heuristics. Produces
    FEATURE_APPROXIMATION decisions with context key
    `selective_call_handling_pattern` set to one of:
        - "multi_partition_dn"
        - "low_membership_partition"
        - "naming_convention"
    """

    name = "selective_call_handling"
    decision_types = [DecisionType.FEATURE_APPROXIMATION]
    # Run after css_routing so CSS decomposition decisions are merged first.
    depends_on = ["css_routing"]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        decisions: list[Decision] = []
        decisions.extend(self._heuristic_multi_partition_dn(store))
        decisions.extend(self._heuristic_low_membership_partition(store))
        decisions.extend(self._heuristic_naming_convention(store, decisions))
        return decisions

    def fingerprint(
        self, decision_type: DecisionType, context: dict[str, Any]
    ) -> str:
        """Deterministic fingerprint from pattern type + natural keys."""
        return self._hash_fingerprint({
            "type": decision_type.value,
            "pattern": context.get("selective_call_handling_pattern", ""),
            "primary_key": context.get("primary_key", ""),
            "partitions": sorted(context.get("partitions", [])),
            "user": context.get("user_canonical_id", ""),
        })

    # ------------------------------------------------------------------
    # Heuristics — implemented in later tasks
    # ------------------------------------------------------------------

    def _heuristic_multi_partition_dn(
        self, store: MigrationStore
    ) -> list[Decision]:
        return []

    def _heuristic_low_membership_partition(
        self, store: MigrationStore
    ) -> list[Decision]:
        return []

    def _heuristic_naming_convention(
        self,
        store: MigrationStore,
        existing_decisions: list[Decision],
    ) -> list[Decision]:
        return []
```

- [ ] **Step 4: Register the analyzer in the pipeline**

Edit `src/wxcli/migration/transform/analysis_pipeline.py`. Add the import and pipeline registration. Add this import after the other analyzer imports (around line 35):

```python
from wxcli.migration.transform.analyzers.selective_call_handling import SelectiveCallHandlingAnalyzer
```

Add to `ALL_ANALYZERS` list (after `LayoutOverflowAnalyzer`, around line 57):

```python
ALL_ANALYZERS: list[type[Analyzer]] = [
    ExtensionConflictAnalyzer,
    DNAmbiguityAnalyzer,
    DeviceCompatibilityAnalyzer,
    SharedLineAnalyzer,
    CSSRoutingAnalyzer,
    CSSPermissionAnalyzer,
    LocationAmbiguityAnalyzer,
    DuplicateUserAnalyzer,
    VoicemailCompatibilityAnalyzer,
    WorkspaceLicenseAnalyzer,
    FeatureApproximationAnalyzer,
    MissingDataAnalyzer,
    LayoutOverflowAnalyzer,
    SelectiveCallHandlingAnalyzer,
]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Verify the analyzer is wired into the pipeline**

```bash
PYTHONPATH=. python3.11 -c "from wxcli.migration.transform.analysis_pipeline import ALL_ANALYZERS; print([c.__name__ for c in ALL_ANALYZERS])"
```

Expected: list ends with `'SelectiveCallHandlingAnalyzer'`.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/transform/analyzers/selective_call_handling.py src/wxcli/migration/transform/analysis_pipeline.py tests/migration/transform/test_selective_call_handling_analyzer.py docs/superpowers/plans/2026-04-11-selective-call-forwarding.md
git commit -m "feat(migration): scaffold SelectiveCallHandlingAnalyzer

Empty analyzer wired into the pipeline. Heuristics implemented in
follow-up commits.

Spec: docs/superpowers/specs/2026-04-10-selective-call-forwarding.md
Plan: docs/superpowers/plans/2026-04-11-selective-call-forwarding.md"
```

---

## Task 2: Implement multi-partition DN heuristic

**Files:**
- Modify: `src/wxcli/migration/transform/analyzers/selective_call_handling.py`
- Modify: `tests/migration/transform/test_selective_call_handling_analyzer.py`

- [ ] **Step 1: Write the failing test for the positive case**

Append to `tests/migration/transform/test_selective_call_handling_analyzer.py`:

```python
def _seed_user_with_dn_in_partitions(
    store: MigrationStore,
    userid: str,
    location_id: str,
    dn: str,
    partition_csses: dict[str, list[str]],
) -> None:
    """Seed a user, partitions, CSSes, DN cross-refs, and user_has_css.

    `partition_csses`: {partition_name: [css_name, ...]} — each partition is
    placed in the given CSSes, and each CSS is associated with the user via
    user_has_css. The DN appears in every partition listed.
    """
    user_id = f"user:{userid}"
    store.upsert_object(
        CanonicalUser(
            canonical_id=user_id,
            provenance=_prov(userid),
            status=MigrationStatus.ANALYZED,
            cucm_userid=userid,
            location_id=location_id,
            extension=dn,
        )
    )
    # Partitions and DN cross-refs
    dn_id = f"dn:{dn}:{list(partition_csses.keys())[0]}"
    for pt_name in partition_csses:
        store.upsert_object(
            MigrationObject(
                canonical_id=f"partition:{pt_name}",
                provenance=_prov(pt_name),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"partition_name": pt_name},
            )
        )
        # Use one DN canonical_id per partition (matches cross_reference.py form)
        per_partition_dn_id = f"dn:{dn}:{pt_name}"
        store.add_cross_ref(per_partition_dn_id, f"partition:{pt_name}", "dn_in_partition")
        store.add_cross_ref(user_id, per_partition_dn_id, "user_has_primary_dn")
    # CSSes and user_has_css
    seen_csses: set[str] = set()
    for pt_name, css_names in partition_csses.items():
        for css_name in css_names:
            css_id = f"css:{css_name}"
            if css_name not in seen_csses:
                store.upsert_object(
                    MigrationObject(
                        canonical_id=css_id,
                        provenance=_prov(css_name),
                        status=MigrationStatus.NORMALIZED,
                        pre_migration_state={"css_name": css_name, "partitions": []},
                    )
                )
                store.add_cross_ref(user_id, css_id, "user_has_css")
                seen_csses.add(css_name)
            store.add_cross_ref(css_id, f"partition:{pt_name}", "css_contains_partition")


class TestMultiPartitionDN:
    def test_dn_in_two_partitions_with_different_css_scopes(self, tmp_path):
        """Pattern 1: DN in 2 partitions, each reachable via different CSS."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="alice",
            location_id="loc:hq",
            dn="1001",
            partition_csses={
                "PT_Internal": ["CSS_Internal"],
                "PT_External": ["CSS_External"],
            },
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch_decisions = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert len(sch_decisions) == 1
        d = sch_decisions[0]
        assert d.severity == "MEDIUM"
        assert d.type == DecisionType.FEATURE_APPROXIMATION
        assert "1001" in d.summary
        assert "PT_Internal" in d.context["partitions"]
        assert "PT_External" in d.context["partitions"]
        assert d.context["user_canonical_id"] == "user:alice"
        assert d.context["recommended_webex_feature"] == "Selective Forward"

    def test_dn_in_two_partitions_same_css_scope_low_severity(self, tmp_path):
        """Pattern 1 weak case: DN in 2 partitions but both reachable via same CSS."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="bob",
            location_id="loc:hq",
            dn="1002",
            partition_csses={
                "PT_A": ["CSS_All"],
                "PT_B": ["CSS_All"],
            },
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch_decisions = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert len(sch_decisions) == 1
        assert sch_decisions[0].severity == "LOW"

    def test_dn_in_single_partition_no_decision(self, tmp_path):
        """Pattern 1 silent case: DN only in one partition."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="carol",
            location_id="loc:hq",
            dn="1003",
            partition_csses={"PT_Only": ["CSS_All"]},
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        assert decisions == []

    def test_multi_site_dn_filtered_out(self, tmp_path):
        """Mitigation 8a: multi-site DN is NOT a selective call handling pattern."""
        store = _store(tmp_path)
        # Two users at different locations sharing the same DN number
        _seed_user_with_dn_in_partitions(
            store, userid="dave", location_id="loc:nyc", dn="2000",
            partition_csses={"PT_NYC": ["CSS_NYC"]},
        )
        _seed_user_with_dn_in_partitions(
            store, userid="eve", location_id="loc:lax", dn="2000",
            partition_csses={"PT_LAX": ["CSS_LAX"]},
        )
        # Both DN cross-refs (dn:2000:PT_NYC and dn:2000:PT_LAX) exist; the
        # multi-site filter should suppress this case.

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch_decisions = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert sch_decisions == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestMultiPartitionDN -v
```

Expected: 4 failures (heuristic returns empty list).

- [ ] **Step 3: Implement `_heuristic_multi_partition_dn`**

Replace the stub in `src/wxcli/migration/transform/analyzers/selective_call_handling.py` with:

```python
    def _heuristic_multi_partition_dn(
        self, store: MigrationStore
    ) -> list[Decision]:
        """Find DNs in 2+ partitions reachable via different user CSSes."""
        # Build {dn_number: {partition_name: dn_canonical_id}} from cross_refs.
        # The dn_canonical_id form is "dn:{number}:{partition}".
        rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'dn_in_partition'"
        ).fetchall()
        dn_to_partitions: dict[str, dict[str, str]] = defaultdict(dict)
        for row in rows:
            dn_canonical_id = row["from_id"]
            partition_canonical_id = row["to_id"]
            # Extract the dn number from "dn:{number}:{partition}"
            parts = dn_canonical_id.split(":", 2)
            if len(parts) < 3:
                continue
            dn_number = parts[1]
            partition_name = partition_canonical_id.split(":", 1)[1] if ":" in partition_canonical_id else partition_canonical_id
            dn_to_partitions[dn_number][partition_name] = dn_canonical_id

        # Map user_id → set of CSS canonical_ids and CSS → set of partition_ids
        user_csses = self._build_user_css_index(store)
        css_partitions = self._build_css_partition_index(store)
        # Map dn canonical_id → owner user canonical_id (from user_has_primary_dn)
        owner_rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'user_has_primary_dn'"
        ).fetchall()
        dn_owner: dict[str, str] = {row["to_id"]: row["from_id"] for row in owner_rows}

        decisions: list[Decision] = []
        for dn_number, partition_map in sorted(dn_to_partitions.items()):
            if len(partition_map) < 2:
                continue

            # Multi-site filter (mitigation 8a):
            # Get owners across all partition variants for this DN number.
            owner_ids: set[str] = set()
            for dn_cid in partition_map.values():
                owner = dn_owner.get(dn_cid)
                if owner:
                    owner_ids.add(owner)
            owner_locations = self._owner_locations(store, owner_ids)
            if len(owner_locations) > 1:
                # Multi-site routing pattern, not selective call handling.
                continue

            # Determine severity: HIGH/MEDIUM if owning user's CSSes have
            # different scopes (different partition sets).
            primary_owner = next(iter(owner_ids), "")
            scopes = self._user_css_scopes(primary_owner, user_csses, css_partitions)
            severity = "MEDIUM" if self._scopes_differ(scopes) else "LOW"

            partitions_sorted = sorted(partition_map.keys())
            context = {
                "selective_call_handling_pattern": "multi_partition_dn",
                "primary_key": dn_number,
                "dn_number": dn_number,
                "partitions": partitions_sorted,
                "user_canonical_id": primary_owner,
                "recommended_webex_feature": "Selective Forward",
                "confidence": "HIGH" if severity == "MEDIUM" else "LOW",
            }
            options = self._build_options("Selective Forward")
            summary = (
                f"DN {dn_number} appears in {len(partitions_sorted)} partitions "
                f"({', '.join(partitions_sorted)}); CUCM caller-specific routing "
                f"pattern detected"
            )
            decisions.append(
                self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity=severity,
                    summary=summary,
                    context=context,
                    options=options,
                    affected_objects=[primary_owner] if primary_owner else [],
                )
            )
        return decisions

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _build_user_css_index(
        self, store: MigrationStore
    ) -> dict[str, set[str]]:
        rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'user_has_css'"
        ).fetchall()
        index: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            index[row["from_id"]].add(row["to_id"])
        return index

    def _build_css_partition_index(
        self, store: MigrationStore
    ) -> dict[str, set[str]]:
        rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'css_contains_partition'"
        ).fetchall()
        index: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            index[row["from_id"]].add(row["to_id"])
        return index

    def _owner_locations(
        self, store: MigrationStore, owner_ids: set[str]
    ) -> set[str]:
        locations: set[str] = set()
        for owner_id in owner_ids:
            obj = store.get_object(owner_id)
            if obj is None:
                continue
            loc = obj.get("location_id")
            if loc:
                locations.add(loc)
        return locations

    def _user_css_scopes(
        self,
        user_id: str,
        user_csses: dict[str, set[str]],
        css_partitions: dict[str, set[str]],
    ) -> list[set[str]]:
        return [
            css_partitions.get(css_id, set())
            for css_id in user_csses.get(user_id, set())
        ]

    @staticmethod
    def _scopes_differ(scopes: list[set[str]]) -> bool:
        if len(scopes) < 2:
            return False
        # Any pair with non-empty symmetric difference → scopes differ.
        for i in range(len(scopes)):
            for j in range(i + 1, len(scopes)):
                if scopes[i] ^ scopes[j]:
                    return True
        return False

    @staticmethod
    def _build_options(recommended_feature: str) -> list[DecisionOption]:
        return [
            DecisionOption(
                id="accept",
                label=f"Configure {recommended_feature} post-migration",
                impact=(
                    f"Operator manually configures Webex {recommended_feature} "
                    f"to preserve CUCM caller-specific routing behavior"
                ),
            ),
            DecisionOption(
                id="skip",
                label="Skip — accept loss of caller-specific routing",
                impact=(
                    "Per-caller routing differences are not preserved; "
                    "callers reach the user via standard Webex routing"
                ),
            ),
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestMultiPartitionDN -v
```

Expected: 4 passed.

- [ ] **Step 5: Run the full file to confirm no regressions**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py -v
```

Expected: 6 passed (2 from Task 1 + 4 from Task 2).

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/analyzers/selective_call_handling.py tests/migration/transform/test_selective_call_handling_analyzer.py
git commit -m "feat(migration): multi-partition DN heuristic for selective call handling

Detects DNs appearing in 2+ partitions with different CSS scopes,
filters out multi-site routing false positives via location cross-check."
```

---

## Task 3: Implement low-membership partition heuristic

**Files:**
- Modify: `src/wxcli/migration/transform/analyzers/selective_call_handling.py`
- Modify: `tests/migration/transform/test_selective_call_handling_analyzer.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/migration/transform/test_selective_call_handling_analyzer.py`:

```python
def _seed_partition_with_dns(
    store: MigrationStore,
    partition_name: str,
    dn_count: int,
    in_csses: list[str],
    all_css_names: list[str],
) -> None:
    """Seed a partition with N DNs and place it in a subset of CSSes."""
    pt_id = f"partition:{partition_name}"
    store.upsert_object(
        MigrationObject(
            canonical_id=pt_id,
            provenance=_prov(partition_name),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"partition_name": partition_name},
        )
    )
    for i in range(dn_count):
        dn_cid = f"dn:9{i:03d}:{partition_name}"
        store.add_cross_ref(pt_id, dn_cid, "partition_has_pattern")
    # Make sure all CSSes exist; place this partition only in `in_csses`
    for css_name in all_css_names:
        css_id = f"css:{css_name}"
        if store.get_object(css_id) is None:
            store.upsert_object(
                MigrationObject(
                    canonical_id=css_id,
                    provenance=_prov(css_name),
                    status=MigrationStatus.NORMALIZED,
                    pre_migration_state={"css_name": css_name, "partitions": []},
                )
            )
    for css_name in in_csses:
        store.add_cross_ref(f"css:{css_name}", pt_id, "css_contains_partition")


class TestLowMembershipPartition:
    def test_low_membership_partition_in_subset_fires(self, tmp_path):
        """Partition with 3 DNs in 1 of 4 CSSes → MEDIUM severity decision."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_VIP_Bypass",
            dn_count=3,
            in_csses=["CSS_VIP"],
            all_css_names=["CSS_All", "CSS_Internal", "CSS_External", "CSS_VIP"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert len(sch) == 1
        d = sch[0]
        assert d.severity == "MEDIUM"
        assert "PT_VIP_Bypass" in d.context["partitions"]
        assert d.context["dn_count"] == 3
        assert d.context["css_count"] == 1
        assert d.context["total_css_count"] == 4

    def test_high_membership_partition_silent(self, tmp_path):
        """Partition with 50 DNs → not VIP/priority pattern, no decision."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_Standard",
            dn_count=50,
            in_csses=["CSS_All"],
            all_css_names=["CSS_All", "CSS_Other"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert sch == []

    def test_low_membership_in_all_csses_silent(self, tmp_path):
        """Partition with few DNs but in ALL CSSes is universal, not VIP."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_Few_All",
            dn_count=2,
            in_csses=["CSS_A", "CSS_B"],
            all_css_names=["CSS_A", "CSS_B"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert sch == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestLowMembershipPartition -v
```

Expected: 1 failure (`test_low_membership_partition_in_subset_fires`); the silent cases pass because the heuristic returns `[]`.

- [ ] **Step 3: Implement `_heuristic_low_membership_partition`**

Replace the stub:

```python
    def _heuristic_low_membership_partition(
        self, store: MigrationStore
    ) -> list[Decision]:
        """Find partitions with few DNs that appear in only a subset of CSSes."""
        partitions = store.get_objects("partition")
        if not partitions:
            return []
        css_partitions = self._build_css_partition_index(store)
        total_css_count = len(css_partitions)
        if total_css_count == 0:
            return []

        # Build reverse: partition_id → set of CSS canonical_ids that contain it
        partition_in_css: dict[str, set[str]] = defaultdict(set)
        for css_id, pt_ids in css_partitions.items():
            for pt_id in pt_ids:
                partition_in_css[pt_id].add(css_id)

        decisions: list[Decision] = []
        for pt in partitions:
            pt_id = pt.get("canonical_id", "")
            if not pt_id:
                continue
            dn_refs = store.find_cross_refs(pt_id, "partition_has_pattern")
            dn_count = len(dn_refs)
            if dn_count == 0 or dn_count > 10:
                continue

            css_count = len(partition_in_css.get(pt_id, set()))
            # Universal partition (in every CSS) → not selective
            if css_count == 0 or css_count >= total_css_count:
                continue
            # Strict subset check: must be in less than half of all CSSes
            if css_count >= total_css_count * 0.5:
                continue

            partition_name = (
                pt.get("pre_migration_state", {}).get("partition_name")
                or pt_id.split(":", 1)[-1]
            )

            context = {
                "selective_call_handling_pattern": "low_membership_partition",
                "primary_key": partition_name,
                "partitions": [partition_name],
                "dn_count": dn_count,
                "css_count": css_count,
                "total_css_count": total_css_count,
                "recommended_webex_feature": "Selective Accept",
                "confidence": "HIGH",
            }
            options = self._build_options("Selective Accept")
            summary = (
                f"Partition '{partition_name}' has {dn_count} DN(s) and is "
                f"reachable via only {css_count}/{total_css_count} CSSes "
                f"(VIP/priority bypass pattern)"
            )
            decisions.append(
                self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="MEDIUM",
                    summary=summary,
                    context=context,
                    options=options,
                    affected_objects=[pt_id],
                )
            )
        return decisions
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestLowMembershipPartition -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full analyzer suite**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py -v
```

Expected: 9 passed.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/analyzers/selective_call_handling.py tests/migration/transform/test_selective_call_handling_analyzer.py
git commit -m "feat(migration): low-membership partition heuristic

Detects partitions with <=10 DNs reachable via fewer than half of all
CSSes — the classic CUCM VIP/executive bypass pattern."
```

---

## Task 4: Implement naming convention heuristic

**Files:**
- Modify: `src/wxcli/migration/transform/analyzers/selective_call_handling.py`
- Modify: `tests/migration/transform/test_selective_call_handling_analyzer.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
class TestNamingConvention:
    def test_partition_named_vip_with_structural_signal_high(self, tmp_path):
        """VIP-named partition that ALSO matches low-membership → MEDIUM severity."""
        store = _store(tmp_path)
        # Reuse the seeding helper that puts the partition in a strict subset
        _seed_partition_with_dns(
            store,
            partition_name="VIP_PT",
            dn_count=2,
            in_csses=["CSS_VIP"],
            all_css_names=["CSS_All", "CSS_Internal", "CSS_External", "CSS_VIP"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        # The naming convention heuristic should NOT add a duplicate decision
        # when the same partition was already covered by low_membership.
        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "naming_convention"
        ]
        # No duplicate naming decision when structural already fired
        assert sch == []

        # And the structural decision should still be present at MEDIUM severity
        struct = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "low_membership_partition"
        ]
        assert len(struct) == 1
        assert struct[0].severity == "MEDIUM"

    def test_partition_named_vip_only_low_severity(self, tmp_path):
        """VIP-named partition with no structural signal → LOW severity name-only."""
        store = _store(tmp_path)
        # 50 DNs in this partition disqualifies the structural heuristic
        _seed_partition_with_dns(
            store,
            partition_name="Executive_PT",
            dn_count=50,
            in_csses=["CSS_All"],
            all_css_names=["CSS_All"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "naming_convention"
        ]
        assert len(sch) == 1
        d = sch[0]
        assert d.severity == "LOW"
        assert "Executive_PT" in d.context["partitions"]
        assert d.context["confidence"] == "LOW"
        assert d.context["recommended_webex_feature"] == "Priority Alert"

    def test_neutral_named_partition_silent(self, tmp_path):
        """Partition with no VIP keyword and no structural signal → no decision."""
        store = _store(tmp_path)
        _seed_partition_with_dns(
            store,
            partition_name="PT_Standard",
            dn_count=20,
            in_csses=["CSS_All"],
            all_css_names=["CSS_All"],
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)
        assert decisions == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestNamingConvention -v
```

Expected: 1 failure (`test_partition_named_vip_only_low_severity`); the other two pass because the heuristic returns `[]`.

- [ ] **Step 3: Implement `_heuristic_naming_convention`**

Replace the stub:

```python
    def _heuristic_naming_convention(
        self,
        store: MigrationStore,
        existing_decisions: list[Decision],
    ) -> list[Decision]:
        """Flag VIP/executive-named partitions not already covered structurally."""
        partitions = store.get_objects("partition")
        if not partitions:
            return []

        # Set of partition canonical_ids already covered by a structural heuristic
        covered: set[str] = set()
        for dec in existing_decisions:
            for obj_id in dec.affected_objects:
                if obj_id.startswith("partition:"):
                    covered.add(obj_id)

        decisions: list[Decision] = []
        for pt in partitions:
            pt_id = pt.get("canonical_id", "")
            if pt_id in covered:
                continue
            partition_name = (
                pt.get("pre_migration_state", {}).get("partition_name")
                or pt_id.split(":", 1)[-1]
            )
            if not self._matches_vip_keyword(partition_name):
                continue

            context = {
                "selective_call_handling_pattern": "naming_convention",
                "primary_key": partition_name,
                "partitions": [partition_name],
                "matched_keyword": self._matched_keyword(partition_name),
                "recommended_webex_feature": "Priority Alert",
                "confidence": "LOW",
            }
            options = self._build_options("Priority Alert")
            summary = (
                f"Partition '{partition_name}' name suggests selective access "
                f"(matched keyword '{context['matched_keyword']}'); CUCM "
                f"caller-specific routing intent inferred from naming only"
            )
            decisions.append(
                self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="LOW",
                    summary=summary,
                    context=context,
                    options=options,
                    affected_objects=[pt_id],
                )
            )
        return decisions

    @staticmethod
    def _matches_vip_keyword(name: str) -> bool:
        if not name:
            return False
        lowered = name.lower()
        return any(kw in lowered for kw in _VIP_KEYWORDS)

    @staticmethod
    def _matched_keyword(name: str) -> str:
        lowered = (name or "").lower()
        for kw in _VIP_KEYWORDS:
            if kw in lowered:
                return kw
        return ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestNamingConvention -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full analyzer suite + sanity check**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py -v
```

Expected: 12 passed.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/analyzers/selective_call_handling.py tests/migration/transform/test_selective_call_handling_analyzer.py
git commit -m "feat(migration): partition naming convention heuristic

Flags partitions whose names contain VIP/executive/priority keywords
when no structural signal already covered them. LOW severity since
naming alone is a weak signal."
```

---

## Task 5: Add fingerprint stability and idempotency tests

**Files:**
- Modify: `tests/migration/transform/test_selective_call_handling_analyzer.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
class TestFingerprintAndIdempotency:
    def test_fingerprint_stable_across_runs(self, tmp_path):
        """Re-running the analyzer produces identical fingerprints."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store,
            userid="alice",
            location_id="loc:hq",
            dn="1001",
            partition_csses={
                "PT_Internal": ["CSS_Internal"],
                "PT_External": ["CSS_External"],
            },
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        run1 = analyzer.analyze(store)
        run2 = analyzer.analyze(store)

        assert len(run1) == len(run2)
        prints1 = sorted(d.fingerprint for d in run1)
        prints2 = sorted(d.fingerprint for d in run2)
        assert prints1 == prints2

    def test_distinct_dns_get_distinct_fingerprints(self, tmp_path):
        """Two different multi-partition DNs produce two distinct decisions."""
        store = _store(tmp_path)
        _seed_user_with_dn_in_partitions(
            store, userid="u1", location_id="loc:hq", dn="1001",
            partition_csses={"PT_A": ["CSS_A"], "PT_B": ["CSS_B"]},
        )
        _seed_user_with_dn_in_partitions(
            store, userid="u2", location_id="loc:hq", dn="1002",
            partition_csses={"PT_C": ["CSS_C"], "PT_D": ["CSS_D"]},
        )

        analyzer = SelectiveCallHandlingAnalyzer()
        decisions = analyzer.analyze(store)

        sch = [
            d for d in decisions
            if d.context.get("selective_call_handling_pattern") == "multi_partition_dn"
        ]
        assert len(sch) == 2
        assert sch[0].fingerprint != sch[1].fingerprint
```

- [ ] **Step 2: Run tests**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py::TestFingerprintAndIdempotency -v
```

Expected: 2 passed (the existing implementation already supports this — these tests are guards).

- [ ] **Step 3: Run full file**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_call_handling_analyzer.py -v
```

Expected: 14 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/migration/transform/test_selective_call_handling_analyzer.py
git commit -m "test(migration): fingerprint stability and idempotency for selective analyzer"
```

---

## Task 6: Add advisory pattern `detect_selective_call_handling_opportunities`

**Files:**
- Modify: `src/wxcli/migration/advisory/advisory_patterns.py`
- Create: `tests/migration/advisory/test_advisory_selective.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/advisory/test_advisory_selective.py`:

```python
"""Tests for selective call handling advisory pattern."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.advisory.advisory_patterns import (
    ALL_ADVISORY_PATTERNS,
    detect_selective_call_handling_opportunities,
)
from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import decision_to_store_dict


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm", source_id="t", source_name="t",
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path) -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _seed_decision(
    store: MigrationStore,
    decision_id: str,
    pattern: str,
    severity: str = "MEDIUM",
) -> None:
    decision = Decision(
        decision_id=decision_id,
        type=DecisionType.FEATURE_APPROXIMATION,
        severity=severity,
        summary=f"selective: {pattern}",
        context={
            "selective_call_handling_pattern": pattern,
            "_affected_objects": [f"user:test_{decision_id}"],
            "recommended_webex_feature": "Selective Forward",
        },
        options=[
            DecisionOption(id="accept", label="Accept", impact="—"),
            DecisionOption(id="skip", label="Skip", impact="—"),
        ],
        affected_objects=[f"user:test_{decision_id}"],
        fingerprint=f"fp_{decision_id}",
        run_id="run1",
    )
    store.merge_decisions(
        [decision_to_store_dict(decision)],
        decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
    )


class TestSelectiveAdvisoryPattern:
    def test_pattern_silent_no_decisions(self, tmp_path):
        store = _store(tmp_path)
        findings = detect_selective_call_handling_opportunities(store)
        assert findings == []

    def test_pattern_silent_no_selective_context(self, tmp_path):
        store = _store(tmp_path)
        # Create a non-selective FEATURE_APPROXIMATION decision
        decision = Decision(
            decision_id="d1",
            type=DecisionType.FEATURE_APPROXIMATION,
            severity="MEDIUM",
            summary="hunt pilot",
            context={"feature_type": "hunt_group"},
            options=[],
            affected_objects=["hunt_group:HG1"],
            fingerprint="fp1",
            run_id="run1",
        )
        store.merge_decisions(
            [decision_to_store_dict(decision)],
            decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
        )
        findings = detect_selective_call_handling_opportunities(store)
        assert findings == []

    def test_pattern_fires_with_candidates(self, tmp_path):
        store = _store(tmp_path)
        _seed_decision(store, "d1", "multi_partition_dn")
        _seed_decision(store, "d2", "multi_partition_dn")
        _seed_decision(store, "d3", "low_membership_partition")
        _seed_decision(store, "d4", "naming_convention")

        findings = detect_selective_call_handling_opportunities(store)

        assert len(findings) == 1
        f = findings[0]
        assert f.pattern_name == "selective_call_handling_opportunities"
        assert f.severity == "MEDIUM"
        assert f.category == "out_of_scope"
        assert "4" in f.summary  # 4 candidates total
        assert "multi_partition_dn" in f.detail or "multi-partition" in f.detail.lower()
        assert "selective forward" in f.detail.lower()

    def test_pattern_groups_by_type(self, tmp_path):
        store = _store(tmp_path)
        _seed_decision(store, "d1", "multi_partition_dn")
        _seed_decision(store, "d2", "low_membership_partition")
        _seed_decision(store, "d3", "low_membership_partition")
        _seed_decision(store, "d4", "naming_convention")

        findings = detect_selective_call_handling_opportunities(store)
        assert len(findings) == 1
        # Detail should reference each pattern type
        detail = findings[0].detail.lower()
        assert "multi" in detail
        assert "low" in detail or "vip" in detail or "membership" in detail
        assert "naming" in detail

    def test_pattern_registered(self):
        assert detect_selective_call_handling_opportunities in ALL_ADVISORY_PATTERNS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/advisory/test_advisory_selective.py -v
```

Expected: ImportError for `detect_selective_call_handling_opportunities`.

- [ ] **Step 3: Implement the advisory pattern**

Edit `src/wxcli/migration/advisory/advisory_patterns.py`. Add the function ABOVE the `ALL_ADVISORY_PATTERNS` list (before line 2030):

```python
# ===================================================================
# Pattern 31: Selective Call Handling Opportunities
# ===================================================================

def detect_selective_call_handling_opportunities(
    store: MigrationStore,
) -> list[AdvisoryFinding]:
    """Aggregate FEATURE_APPROXIMATION decisions with the
    `selective_call_handling_pattern` context key into a single
    cross-cutting advisory.

    Spec: docs/superpowers/specs/2026-04-10-selective-call-forwarding.md §4b
    """
    decisions = store.get_all_decisions()
    by_pattern: dict[str, list[dict[str, Any]]] = defaultdict(list)
    affected: list[str] = []
    for d in decisions:
        if d.get("type") != "FEATURE_APPROXIMATION":
            continue
        if d.get("chosen_option") == "__stale__":
            continue
        ctx = d.get("context", {}) or {}
        pattern = ctx.get("selective_call_handling_pattern")
        if not pattern:
            continue
        by_pattern[pattern].append(d)
        for obj_id in ctx.get("_affected_objects", []) or []:
            affected.append(obj_id)

    if not by_pattern:
        return []

    total = sum(len(v) for v in by_pattern.values())
    multi = len(by_pattern.get("multi_partition_dn", []))
    low = len(by_pattern.get("low_membership_partition", []))
    naming = len(by_pattern.get("naming_convention", []))

    parts = []
    if multi:
        parts.append(
            f"{multi} multi-partition DN candidate(s) (internal vs external "
            f"routing split)"
        )
    if low:
        parts.append(
            f"{low} low-membership partition candidate(s) (VIP/priority bypass)"
        )
    if naming:
        parts.append(
            f"{naming} naming-convention candidate(s) (partition name keyword "
            f"only — weak signal)"
        )

    detail = (
        f"{total} CSS/partition pattern(s) suggest CUCM caller-specific "
        f"routing. Webex Calling offers explicit per-person Selective Forward, "
        f"Selective Accept, and Selective Reject features (admin-configurable) "
        f"plus Priority Alert (user-only) that can replicate this behaviour. "
        f"These advisories do not auto-create rules — the operator must review "
        f"each candidate and configure the appropriate Webex selective rule "
        f"manually post-migration. "
        f"Detected patterns: " + "; ".join(parts) + "."
    )

    return [AdvisoryFinding(
        pattern_name="selective_call_handling_opportunities",
        severity="MEDIUM",
        summary=(
            f"{total} user/partition candidate(s) for Webex selective call "
            f"handling — manual configuration"
        ),
        detail=detail,
        affected_objects=sorted(set(affected)),
        category="out_of_scope",
    )]
```

Then register it in `ALL_ADVISORY_PATTERNS`. Add this entry at the end of the existing list (right before the final `]`):

```python
    detect_selective_call_handling_opportunities,  # Pattern 31 (selective call handling)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/advisory/test_advisory_selective.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run the broader advisory suite to confirm no regressions**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/advisory -v
```

Expected: all advisory tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/advisory/advisory_patterns.py tests/migration/advisory/test_advisory_selective.py
git commit -m "feat(migration): selective call handling advisory pattern

Aggregates FEATURE_APPROXIMATION decisions tagged with
selective_call_handling_pattern into a single cross-cutting advisory
that lists candidate counts by detection heuristic."
```

---

## Task 7: Extend `recommend_feature_approximation` for selective call handling

**Files:**
- Modify: `src/wxcli/migration/advisory/recommendation_rules.py`
- Create: `tests/migration/advisory/test_recommendation_selective.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/advisory/test_recommendation_selective.py`:

```python
"""Tests for selective call handling recommendation rule extension."""
from __future__ import annotations

from wxcli.migration.advisory.recommendation_rules import (
    recommend_feature_approximation,
)


class TestRecommendSelective:
    def test_selective_multi_partition_recommends_accept(self):
        context = {
            "selective_call_handling_pattern": "multi_partition_dn",
            "dn_number": "1001",
            "recommended_webex_feature": "Selective Forward",
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        option_id, reasoning = result
        assert option_id == "accept"
        assert "selective forward" in reasoning.lower()

    def test_selective_low_membership_recommends_accept(self):
        context = {
            "selective_call_handling_pattern": "low_membership_partition",
            "recommended_webex_feature": "Selective Accept",
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        assert result[0] == "accept"
        assert "selective accept" in result[1].lower()

    def test_selective_naming_only_recommends_accept_low_confidence(self):
        context = {
            "selective_call_handling_pattern": "naming_convention",
            "confidence": "LOW",
            "recommended_webex_feature": "Priority Alert",
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        assert result[0] == "accept"
        assert "priority alert" in result[1].lower()
        assert "user-only" in result[1].lower() or "weak" in result[1].lower()

    def test_non_selective_feature_approx_not_affected(self):
        """Existing behaviour for non-selective contexts must not change."""
        context = {
            "classification": "EXTENSION_MOBILITY",
            "line_count": 1,
            "speed_dial_count": 0,
            "blf_count": 0,
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        # EM still recommends accept (existing behaviour)
        assert result[0] == "accept"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/advisory/test_recommendation_selective.py -v
```

Expected: 3 failures (selective context not handled — falls through to None or other branches).

- [ ] **Step 3: Extend `recommend_feature_approximation`**

Edit `src/wxcli/migration/advisory/recommendation_rules.py`. At the very top of the function body of `recommend_feature_approximation` (right after the docstring at line 150), add the selective call handling short-circuit:

```python
def recommend_feature_approximation(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.1: Feature approximation — CTI RP or Line Group → CQ/HG.

    Also handles selective call handling decisions tagged with
    `selective_call_handling_pattern` in context (spec
    docs/superpowers/specs/2026-04-10-selective-call-forwarding.md §4c).
    """
    # Selective call handling — recommend accept with feature-specific reasoning.
    sch_pattern = context.get("selective_call_handling_pattern")
    if sch_pattern:
        feature = context.get("recommended_webex_feature", "selective call handling")
        confidence = (context.get("confidence") or "").upper()
        if sch_pattern == "naming_convention" or confidence == "LOW":
            note = (
                " Note: this is a weak signal based on partition naming only — "
                "verify the CUCM behaviour before configuring. Priority Alert "
                "specifically requires user-only OAuth and cannot be configured "
                "via admin token."
                if feature.lower() == "priority alert"
                else " Note: this is a weak signal based on partition naming "
                "only — verify the CUCM behaviour before configuring."
            )
            return (
                "accept",
                f"CUCM CSS/partition pattern suggests caller-specific routing. "
                f"Configure Webex {feature} post-migration to preserve this "
                f"behaviour.{note}",
            )
        return (
            "accept",
            f"CUCM CSS/partition pattern suggests caller-specific routing. "
            f"Configure Webex {feature} post-migration to preserve this "
            f"behaviour. The pipeline cannot auto-create the rule because the "
            f"phone-number criteria require operator review.",
        )

    # EM profile → hot desking: always recommend accept (no alternative exists)
    if context.get("classification") == "EXTENSION_MOBILITY":
```

(Leave the rest of the existing function body unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/advisory/test_recommendation_selective.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run advisory suite to confirm no regressions**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/advisory -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/advisory/recommendation_rules.py tests/migration/advisory/test_recommendation_selective.py
git commit -m "feat(migration): recommendation rule for selective call handling

Extends recommend_feature_approximation to short-circuit on
selective_call_handling_pattern context with feature-specific
reasoning. Naming-only matches get a weak-signal warning."
```

---

## Task 8: Add report appendix section

**Files:**
- Modify: `src/wxcli/migration/report/appendix.py`
- Create: `tests/migration/report/test_appendix_selective.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/report/test_appendix_selective.py`:

```python
"""Tests for selective call handling appendix section."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
    Provenance,
)
from wxcli.migration.report.appendix import generate_appendix
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import decision_to_store_dict


def _store(tmp_path) -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _seed_selective_decision(
    store: MigrationStore,
    decision_id: str,
    pattern: str,
    user_id: str,
    feature: str,
) -> None:
    decision = Decision(
        decision_id=decision_id,
        type=DecisionType.FEATURE_APPROXIMATION,
        severity="MEDIUM",
        summary=f"selective {pattern} for {user_id}",
        context={
            "selective_call_handling_pattern": pattern,
            "recommended_webex_feature": feature,
            "_affected_objects": [user_id],
            "partitions": ["PT_Test"],
        },
        options=[
            DecisionOption(id="accept", label="Accept", impact="—"),
            DecisionOption(id="skip", label="Skip", impact="—"),
        ],
        affected_objects=[user_id],
        fingerprint=f"fp_{decision_id}",
        run_id="run1",
    )
    store.merge_decisions(
        [decision_to_store_dict(decision)],
        decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
    )


class TestSelectiveAppendix:
    def test_section_omitted_when_no_candidates(self, tmp_path):
        store = _store(tmp_path)
        html = generate_appendix(store)
        assert "AB. Selective Call Handling" not in html

    def test_section_rendered_with_candidates(self, tmp_path):
        store = _store(tmp_path)
        _seed_selective_decision(
            store, "d1", "multi_partition_dn", "user:alice", "Selective Forward"
        )
        _seed_selective_decision(
            store, "d2", "low_membership_partition", "user:bob", "Selective Accept"
        )
        _seed_selective_decision(
            store, "d3", "naming_convention", "user:carol", "Priority Alert"
        )

        html = generate_appendix(store)

        assert "AB. Selective Call Handling" in html
        assert "Selective Forward" in html
        assert "Selective Accept" in html
        assert "Priority Alert" in html
        # Pattern type column
        assert "Multi-Partition DN" in html
        assert "Low-Membership Partition" in html
        assert "Naming Convention" in html
        # Affected user names rendered (without canonical_id prefix)
        assert "alice" in html
        assert "bob" in html
        assert "carol" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report/test_appendix_selective.py -v
```

Expected: failures (section does not exist).

- [ ] **Step 3: Add the appendix section**

Edit `src/wxcli/migration/report/appendix.py`. Add the new section function near the end of the module (after `_receptionist_group`):

```python
# ---------------------------------------------------------------------------
# AB. Selective Call Handling Opportunities
# ---------------------------------------------------------------------------

_SCH_PATTERN_DISPLAY = {
    "multi_partition_dn": "Multi-Partition DN",
    "low_membership_partition": "Low-Membership Partition",
    "naming_convention": "Naming Convention",
}


def _selective_call_handling(store: MigrationStore) -> str:
    """AB. Selective Call Handling Opportunities — CUCM CSS patterns."""
    candidates: list[dict[str, Any]] = []
    for d in store.get_all_decisions():
        if d.get("type") != "FEATURE_APPROXIMATION":
            continue
        if d.get("chosen_option") == "__stale__":
            continue
        ctx = d.get("context", {}) or {}
        pattern = ctx.get("selective_call_handling_pattern")
        if not pattern:
            continue
        candidates.append(d)

    if not candidates:
        return ""

    parts = [
        '<details id="selective-call-handling">',
        f'<summary>AB. Selective Call Handling '
        f'<span class="summary-count">— {len(candidates)} candidate(s)</span>'
        f'</summary>',
        '<div class="details-content">',
        '<p>CUCM CSS/partition patterns suggest caller-specific routing. '
        'Webex Calling offers four explicit per-person features that can '
        'replicate this behaviour: Selective Forward, Selective Accept, '
        'Selective Reject, and Priority Alert. The first three are '
        'admin-configurable; Priority Alert requires per-user OAuth.</p>',
        '<table>',
        '<thead><tr>'
        '<th>Affected Object</th>'
        '<th>Pattern Type</th>'
        '<th>Partitions</th>'
        '<th>Recommended Webex Feature</th>'
        '</tr></thead>',
        '<tbody>',
    ]

    for d in sorted(candidates, key=lambda x: x.get("decision_id", "")):
        ctx = d.get("context", {}) or {}
        pattern = ctx.get("selective_call_handling_pattern", "")
        pattern_display = _SCH_PATTERN_DISPLAY.get(
            pattern, pattern.replace("_", " ").title()
        )
        affected_ids = ctx.get("_affected_objects", []) or []
        affected_display = ", ".join(
            strip_canonical_id(obj_id) for obj_id in affected_ids
        ) or "—"
        partitions = ", ".join(ctx.get("partitions", [])) or "—"
        feature = ctx.get("recommended_webex_feature", "—")
        parts.append(
            f'<tr>'
            f'<td>{html.escape(affected_display)}</td>'
            f'<td>{html.escape(pattern_display)}</td>'
            f'<td>{html.escape(partitions)}</td>'
            f'<td>{html.escape(feature)}</td>'
            f'</tr>'
        )

    parts.extend(['</tbody></table>', '</div></details>'])
    return "\n".join(parts)
```

Then register the section in `generate_appendix()`. Edit the `sections` list (around line 52) and add `("AB", _selective_call_handling(store))` after `("AA", _receptionist_group(store))`:

```python
        ("AA", _receptionist_group(store)),
        ("AB", _selective_call_handling(store)),
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report/test_appendix_selective.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run the full report appendix suite**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report -k "appendix" -v --ignore=tests/migration/report/test_user_notice.py
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/report/appendix.py tests/migration/report/test_appendix_selective.py
git commit -m "feat(migration): assessment report appendix section AB

Renders selective call handling candidates as a table grouped by
pattern type with the recommended Webex feature."
```

---

## Task 9: Add executive summary stat row (conditional)

**Files:**
- Modify: `src/wxcli/migration/report/executive.py`
- Create: `tests/migration/report/test_executive_selective.py`

This is a small conditional addition — only render the stat when at least one selective call handling decision exists. The stat shows up as a stat-card with a callout pointing to the appendix section.

- [ ] **Step 1: Locate the existing stat-grid in `executive.py`**

```bash
grep -n "stat-card\|stat-grid\|page_scope\|_page_scope\|feature gap" src/wxcli/migration/report/executive.py | head -20
```

Read the relevant section so you can find the right insertion point. The new card belongs in the "What Needs Attention" / scope page where decision counts and feature gap stats already render.

- [ ] **Step 2: Write the failing tests**

Create `tests/migration/report/test_executive_selective.py`:

```python
"""Tests for selective call handling stat in executive summary."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
    Provenance,
)
from wxcli.migration.report.executive import generate_executive_summary
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import decision_to_store_dict


def _store(tmp_path) -> MigrationStore:
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _seed_selective_decision(store: MigrationStore, decision_id: str) -> None:
    decision = Decision(
        decision_id=decision_id,
        type=DecisionType.FEATURE_APPROXIMATION,
        severity="MEDIUM",
        summary="selective",
        context={
            "selective_call_handling_pattern": "multi_partition_dn",
            "_affected_objects": [f"user:{decision_id}"],
        },
        options=[
            DecisionOption(id="accept", label="Accept", impact="—"),
            DecisionOption(id="skip", label="Skip", impact="—"),
        ],
        affected_objects=[f"user:{decision_id}"],
        fingerprint=f"fp_{decision_id}",
        run_id="run1",
    )
    store.merge_decisions(
        [decision_to_store_dict(decision)],
        decision_types=[DecisionType.FEATURE_APPROXIMATION.value],
    )


class TestExecutiveSelective:
    def test_stat_omitted_when_no_candidates(self, tmp_path):
        store = _store(tmp_path)
        html = generate_executive_summary(store, brand="Acme", prepared_by="SE")
        assert "Selective Call Handling" not in html

    def test_stat_rendered_with_candidates(self, tmp_path):
        store = _store(tmp_path)
        _seed_selective_decision(store, "d1")
        _seed_selective_decision(store, "d2")
        _seed_selective_decision(store, "d3")
        html = generate_executive_summary(store, brand="Acme", prepared_by="SE")

        assert "Selective Call Handling" in html
        assert "3" in html  # 3 candidates
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report/test_executive_selective.py -v
```

Expected: `test_stat_rendered_with_candidates` fails.

- [ ] **Step 4: Add a helper that counts selective candidates and inject the stat**

In `src/wxcli/migration/report/executive.py`, add a small helper near the top of the module (after the imports and constants):

```python
def _count_selective_call_handling_candidates(store: MigrationStore) -> int:
    """Count non-stale FEATURE_APPROXIMATION decisions tagged with the
    selective_call_handling_pattern context key."""
    count = 0
    for d in store.get_all_decisions():
        if d.get("type") != "FEATURE_APPROXIMATION":
            continue
        if d.get("chosen_option") == "__stale__":
            continue
        ctx = d.get("context", {}) or {}
        if ctx.get("selective_call_handling_pattern"):
            count += 1
    return count
```

Then locate the `_page_scope` function (this is the "What Needs Attention" page that already renders feature gap stats). At the end of the function, just before the closing `</div>` tag of the page (use `grep -n "_page_scope" src/wxcli/migration/report/executive.py` to find it), add a conditional block:

```python
    sch_count = _count_selective_call_handling_candidates(store)
    if sch_count:
        parts.append(
            f'<div class="callout">'
            f'<p><strong>Selective Call Handling:</strong> {sch_count} '
            f'candidate(s) for Webex Selective Forward / Accept / Reject. '
            f'See appendix section AB for the per-user breakdown.</p>'
            f'</div>'
        )
```

(If `_page_scope` already constructs its HTML via list-of-strings appended into `parts`, the above slot is correct. If it uses a different variable name, adapt — read the function before editing.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report/test_executive_selective.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Run the executive suite**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report/test_executive.py tests/migration/report/test_executive_selective.py -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/report/executive.py tests/migration/report/test_executive_selective.py
git commit -m "feat(migration): selective call handling stat in executive summary

Conditional callout in the scope page when at least one selective
call handling candidate exists. Points readers to appendix AB."
```

---

## Task 10: Integration test — full pipeline produces the advisory

**Files:**
- Create: `tests/migration/transform/test_selective_integration.py`

- [ ] **Step 1: Write the test**

Create `tests/migration/transform/test_selective_integration.py`:

```python
"""End-to-end integration: pipeline detects + reports selective candidates."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline


def _prov(name="t"):
    return Provenance(
        source_system="cucm", source_id="t", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path):
    return MigrationStore(os.path.join(str(tmp_path), "t.db"))


def _seed_vip_environment(store: MigrationStore) -> None:
    # User in HQ with a DN in two partitions, one VIP-named
    user_id = "user:ceo"
    store.upsert_object(
        CanonicalUser(
            canonical_id=user_id,
            provenance=_prov("ceo"),
            status=MigrationStatus.ANALYZED,
            cucm_userid="ceo",
            location_id="loc:hq",
            extension="1000",
        )
    )
    for pt in ("PT_VIP_Direct", "PT_Standard"):
        store.upsert_object(
            MigrationObject(
                canonical_id=f"partition:{pt}",
                provenance=_prov(pt),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"partition_name": pt},
            )
        )
        dn_id = f"dn:1000:{pt}"
        store.add_cross_ref(dn_id, f"partition:{pt}", "dn_in_partition")
        store.add_cross_ref(user_id, dn_id, "user_has_primary_dn")
    for css, partitions in (
        ("CSS_Internal", ["PT_Standard"]),
        ("CSS_VIP", ["PT_VIP_Direct"]),
    ):
        css_id = f"css:{css}"
        store.upsert_object(
            MigrationObject(
                canonical_id=css_id,
                provenance=_prov(css),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"css_name": css, "partitions": []},
            )
        )
        store.add_cross_ref(user_id, css_id, "user_has_css")
        for pt in partitions:
            store.add_cross_ref(css_id, f"partition:{pt}", "css_contains_partition")


class TestSelectiveIntegration:
    def test_full_pipeline_with_vip_pattern(self, tmp_path):
        store = _store(tmp_path)
        _seed_vip_environment(store)

        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        # The selective analyzer ran
        assert "selective_call_handling" in result.stats
        assert result.stats["selective_call_handling"] >= 1

        # And the advisory pattern produced an ARCHITECTURE_ADVISORY decision
        all_decisions = store.get_all_decisions()
        sch_advisory = [
            d for d in all_decisions
            if d.get("type") == "ARCHITECTURE_ADVISORY"
            and (d.get("context", {}) or {}).get("pattern_name")
            == "selective_call_handling_opportunities"
        ]
        assert len(sch_advisory) == 1

    def test_full_pipeline_clean_environment_no_advisory(self, tmp_path):
        store = _store(tmp_path)
        # Empty store: nothing for the analyzer to find
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        all_decisions = store.get_all_decisions()
        sch = [
            d for d in all_decisions
            if (d.get("context", {}) or {}).get("selective_call_handling_pattern")
        ]
        assert sch == []

    def test_pipeline_does_not_break_existing_decisions(self, tmp_path):
        """Adding the new analyzer must not break any other analyzer."""
        store = _store(tmp_path)
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)
        # All analyzers ran without raising
        for name, count in result.stats.items():
            assert count >= 0, f"Analyzer {name} failed (count={count})"
```

- [ ] **Step 2: Run tests**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transform/test_selective_integration.py -v
```

Expected: 3 passed. If the advisory pattern uses a different `pattern_name` field name on `ARCHITECTURE_ADVISORY` decisions in the store, inspect the decision context structure with:

```bash
PYTHONPATH=. python3.11 -c "
from wxcli.migration.store import MigrationStore
import tempfile, os
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
with tempfile.TemporaryDirectory() as d:
    s = MigrationStore(os.path.join(d, 't.db'))
    AnalysisPipeline().run(s)
    for x in s.get_all_decisions():
        print(x.get('type'), x.get('context'))
"
```

Use the actual field name in the assertion.

- [ ] **Step 3: Commit**

```bash
git add tests/migration/transform/test_selective_integration.py
git commit -m "test(migration): integration test for selective call handling pipeline

Verifies the analyzer + advisory chain produces an ARCHITECTURE_ADVISORY
decision when a VIP partition pattern is present."
```

---

## Task 11: Documentation updates — CLAUDE.md, KB, runbook

**Files:**
- Modify: `src/wxcli/migration/transform/CLAUDE.md`
- Modify: `src/wxcli/migration/advisory/CLAUDE.md`
- Modify: `docs/knowledge-base/migration/kb-css-routing.md`
- Modify: `docs/knowledge-base/migration/kb-user-settings.md`
- Modify: `docs/knowledge-base/migration/kb-feature-mapping.md`
- Modify: `docs/runbooks/cucm-migration/operator-runbook.md`
- Modify: `docs/runbooks/cucm-migration/decision-guide.md`

These edits are short and mechanical. The exact heading paths to find are listed below — read each file to confirm location before editing, since the line numbers in this plan are approximate.

- [ ] **Step 1: Update `src/wxcli/migration/transform/CLAUDE.md`**

Find the "13 Analyzers" table (search for `| Analyzer | Decision Types |`). Add a new row at the end:

```markdown
| `SelectiveCallHandlingAnalyzer` | `FEATURE_APPROXIMATION` (with `selective_call_handling_pattern` context key) |
```

Then update the count in the surrounding prose ("13 Analyzers" → "14 Analyzers") and any line that says "13 analyzers" to "14 analyzers". Search for `13 analyzers` and `13 Analyzers` and update each occurrence.

- [ ] **Step 2: Update `src/wxcli/migration/advisory/CLAUDE.md`**

Find the "Tier 4 feature gap patterns:" section. Add a new bullet:

```markdown
31. Selective Call Handling Opportunities — CSS/partition patterns suggesting per-caller routing → Webex Selective Forward / Accept / Reject (admin) or Priority Alert (user-only)
```

Also update any pattern count (search for `30 cross-cutting pattern detectors` or `30 patterns` and bump to `31`).

- [ ] **Step 3: Update `docs/knowledge-base/migration/kb-css-routing.md`**

Append a new section at the end of the file:

```markdown

## Selective Call Handling Detection

Three heuristics in `SelectiveCallHandlingAnalyzer` detect CUCM CSS/partition
patterns that imply per-caller routing differences:

1. **Multi-partition DN** — same DN appears in 2+ partitions reachable via
   different user CSSes. Indicates the operator modelled "internal callers
   reach me directly; external callers hit forwarding rules" by placing the
   DN in two partitions with different CSS scopes.
2. **Low-membership partition** — partition with ≤10 DNs that appears in
   fewer than half of all CSSes. Indicates a VIP/executive bypass pattern
   where only certain CSSes can reach this partition.
3. **Naming convention** — partition name matches `vip`, `executive`,
   `priority`, `direct`, `bypass`, `afterhours`, or `emergency`. Weak
   signal — only LOW severity unless paired with a structural signal.

Each heuristic produces a `FEATURE_APPROXIMATION` decision tagged with
`selective_call_handling_pattern` in the context. The recommendation rule
always suggests `accept` (configure Webex selective forwarding/acceptance/
rejection or Priority Alert post-migration). The pipeline does NOT
auto-create selective rules — phone-number criteria require operator review.

The advisory pattern `detect_selective_call_handling_opportunities` aggregates
all selective decisions into a single cross-cutting `ARCHITECTURE_ADVISORY`.

**Mitigation 1: multi-site false positives.** Multi-partition DNs are
filtered out when the owning users live at different `location_id` values
(this is a multi-site routing pattern, not selective call handling).

**Mitigation 2: weak naming signal.** Naming-only matches stay LOW severity.
A structural confirmation (multi-partition DN OR low-membership subset) is
required for MEDIUM severity.
```

- [ ] **Step 4: Update `docs/knowledge-base/migration/kb-user-settings.md`**

Find the call settings mapping table (search for `| Setting | CUCM` or similar header). Append four rows:

```markdown
| Selective Forward | No direct CUCM equivalent — detected via CSS/partition heuristics | `/telephony/config/people/{personId}/selectiveForward` | Admin-configurable |
| Selective Accept | No direct CUCM equivalent — detected via CSS/partition heuristics | `/telephony/config/people/{personId}/selectiveAccept` | Admin-configurable |
| Selective Reject | No direct CUCM equivalent — detected via CSS/partition heuristics | `/telephony/config/people/{personId}/selectiveReject` | Admin-configurable |
| Priority Alert | No direct CUCM equivalent — detected via CSS/partition heuristics | `/people/me/settings/priorityAlert` | User-only OAuth required |
```

If the existing table has different column counts/headers, adapt the rows to match. Read the existing table format first.

- [ ] **Step 5: Update `docs/knowledge-base/migration/kb-feature-mapping.md`**

Find the feature mapping table. Append rows referencing the heuristic source:

```markdown
| Selective Forward | CSS/partition analysis heuristic | Selective Forward (admin) | Advisory only — operator configures post-migration |
| Selective Accept | CSS/partition analysis heuristic | Selective Accept (admin) | Advisory only — operator configures post-migration |
| Selective Reject | CSS/partition analysis heuristic | Selective Reject (admin) | Advisory only — operator configures post-migration |
| Priority Alert | CSS/partition analysis heuristic | Priority Alert (user-only) | Cannot be configured via admin token |
```

- [ ] **Step 6: Update `docs/runbooks/cucm-migration/operator-runbook.md`**

Find the post-migration verification section. Add a step:

```markdown
- **Review selective call handling advisories.** If the assessment report
  appendix section AB lists candidates, configure Webex Selective Forward,
  Selective Accept, or Selective Reject for each flagged user via
  `wxcli user-settings` or Control Hub. Priority Alert recommendations
  require user-level OAuth — flag those for end-user self-service.
```

- [ ] **Step 7: Update `docs/runbooks/cucm-migration/decision-guide.md`**

Find the "feature_opportunity" / advisory patterns section (search for `### feature-approximation` and look for a sibling section, OR find `## Advisory Patterns`). Add an entry under the appropriate category. Use the existing entries (e.g. `extension-mobility-usage` around line 495) as a template for the format. Insert near the end of the advisory patterns section:

```markdown

#### selective-call-handling-opportunities

**Category:** out_of_scope (advisory only)
**Triggered by:** `advisory_patterns.py` (`detect_selective_call_handling_opportunities`) — fires when 1+ `FEATURE_APPROXIMATION` decisions tagged with `selective_call_handling_pattern` are present in the store. Source decisions come from `src/wxcli/migration/transform/analyzers/selective_call_handling.py:SelectiveCallHandlingAnalyzer`, which runs three heuristics (multi-partition DN, low-membership partition, naming convention).
**Detection signals:**
- Multi-partition DN: same DN in 2+ partitions with different CSS scopes (filtered by location to drop multi-site false positives).
- Low-membership partition: ≤10 DNs in a partition reachable via fewer than half of all CSSes.
- Naming convention: partition name contains a VIP/executive/priority/bypass/afterhours keyword.
**Why/impact:** CUCM operators implement caller-specific routing through CSS/partition manipulation rather than an explicit "selective forward" feature. Webex Calling has four explicit per-person APIs for this — Selective Forward, Selective Accept, Selective Reject, and Priority Alert. The first three are admin-configurable; Priority Alert requires per-user OAuth.
**Recommended action:** Operator manually configures the relevant Webex selective rule per flagged user post-migration. The pipeline cannot auto-create rules because the phone-number criteria require operator review (CUCM CSS semantics don't map 1:1 to "calls from these specific numbers").
**See also:** [`feature-approximation`](#feature-approximation) (the underlying decision type), [`kb-css-routing.md#selective-call-handling-detection`](../../knowledge-base/migration/kb-css-routing.md#selective-call-handling-detection).
```

- [ ] **Step 8: Verify documentation tests still pass**

The transferability test suite enforces that every advisory pattern has a runbook entry. Run:

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/transferability -v --deselect "tests/migration/transferability/test_runbook_cites.py::test_file_line_citations_resolve[operator-runbook.md]"
```

Expected: all pass (the deselected test is the pre-existing failure unrelated to this branch).

If any test fails because the advisory pattern coverage check expects a specific anchor name, read the failing test and update the runbook anchor to match (the function-name-with-`detect_`-stripped convention is enforced).

- [ ] **Step 9: Commit**

```bash
git add src/wxcli/migration/transform/CLAUDE.md src/wxcli/migration/advisory/CLAUDE.md docs/knowledge-base/migration/kb-css-routing.md docs/knowledge-base/migration/kb-user-settings.md docs/knowledge-base/migration/kb-feature-mapping.md docs/runbooks/cucm-migration/operator-runbook.md docs/runbooks/cucm-migration/decision-guide.md
git commit -m "docs(migration): selective call handling advisory pattern

CLAUDE.md analyzer/advisory tables, KB CSS routing detection section,
KB feature/user-setting mappings, runbook post-migration step, and
decision guide entry."
```

---

## Task 12: Final verification — full migration test suite

**Files:** none (verification only)

- [ ] **Step 1: Run the full migration test suite, excluding known pre-existing failures**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration \
    --ignore=tests/migration/report/test_user_notice.py \
    --deselect "tests/migration/transferability/test_runbook_cites.py::test_file_line_citations_resolve[operator-runbook.md]" \
    -v --tb=short
```

Expected: every test passes. The baseline before this branch was 89 migration tests passing (excluding the two pre-existing failures); the new tests add ~22 tests on top.

- [ ] **Step 2: Spot-check the pre-existing failures still behave the same**

```bash
PYTHONPATH=. python3.11 -m pytest tests/migration/report/test_user_notice.py tests/migration/transferability/test_runbook_cites.py -v
```

Expected: same failures as before (1 ERROR + 1 FAIL). If anything else fails in these files, this branch introduced a regression — investigate.

- [ ] **Step 3: Verify the branch is clean and the commits look right**

```bash
git status
git log --oneline main..feat/selective-call-forwarding
```

Expected: working tree clean, ~10 commits on the feature branch.

- [ ] **Step 4: Run the verification-before-completion checklist**

This is a hard gate before reporting success. Re-confirm:
- Every task in this plan has its checkbox ticked
- Every commit lives on `feat/selective-call-forwarding`
- The full migration suite (minus pre-existing failures) is green
- No files outside the worktree were touched
- No merges, no pushes, no edits to other branches

If everything is true, write a one-line completion summary citing the test count and commit count. If anything is false, fix it before claiming done.

---

## Self-Review Notes

**Spec coverage check (against `docs/superpowers/specs/2026-04-10-selective-call-forwarding.md`):**

- §1 Problem statement / scope → addressed via analyzer + advisory + recommendation (Tasks 1-7).
- §2a CSS patterns (multi-partition, VIP partition, time-of-day, calling party transformation) → Task 2 covers multi-partition; Task 3 covers VIP partition; Task 4 covers naming convention. **Time-of-day partition switching is NOT separately implemented** because the spec's own §4a algorithm only lists three heuristics (multi-partition DN, low-membership, naming) and these subsume the time-of-day case via the low-membership heuristic when a time-scoped partition has few members. The advisory text and detection signals call this out.
- §2b "no new AXL extraction" → confirmed; analyzer reads only from store.
- §2c Heuristics → Tasks 2-4.
- §3 Webex target APIs → documented in plan + KB updates (Task 11), no code change needed since reference docs are already complete.
- §4a Analyzer with `FEATURE_APPROXIMATION` decision type and `selective_call_handling_pattern` context key → Tasks 1-5.
- §4b Advisory pattern → Task 6.
- §4c Recommendation rule → Task 7.
- §4d No new canonical objects → confirmed; we only produce decisions.
- §4e No execution operations → confirmed; advisory-only.
- §5a Executive summary stat → Task 9.
- §5b Appendix subsection → Task 8.
- §5c Implementation pointers → Tasks 8 + 9.
- §6 Documentation updates → Task 11.
- §7a-d Tests → Tasks 1-10 cover all 18+ tests called out in the spec test strategy. The exact test names differ slightly but the coverage matches.
- §8 Risks/open questions → mitigations 8a (multi-site filter) and 8b (weak-signal severity floor) are baked into Tasks 2 + 4 with explicit tests. 8c (no direct number mapping) and 8d (Priority Alert limitation) are addressed in advisory detail text and recommendation reasoning. 8e (volume) — large stores: the analyzer is O(N) over DN cross-refs and partitions, no nested loops over user count.

**Placeholder scan:** None. Every step has either complete code or a precise edit instruction.

**Type/name consistency:**
- Class: `SelectiveCallHandlingAnalyzer` (consistent across Tasks 1, 6, 8, 9, 10, 11)
- Module: `src/wxcli/migration/transform/analyzers/selective_call_handling.py`
- Context key: `selective_call_handling_pattern` (consistent)
- Pattern values: `multi_partition_dn`, `low_membership_partition`, `naming_convention` (consistent)
- Advisory function: `detect_selective_call_handling_opportunities` (Tasks 6, 11)
- Pattern name: `selective_call_handling_opportunities` (Tasks 6, 11)
- Appendix section letter: `AB` (Tasks 8, 9, 11)
- Helper functions: `_build_user_css_index`, `_build_css_partition_index`, `_owner_locations`, `_user_css_scopes`, `_scopes_differ`, `_build_options`, `_matches_vip_keyword`, `_matched_keyword` (consistent within Tasks 2-4)

**Known limitations the engineer must NOT try to fix:**
- The existing buggy `store.get_objects("calling_search_space")` calls in `advisory_patterns.py` (used by patterns 1, 11, 21) are out of scope for this branch. Do not "fix" them — they are tracked separately.
- The `test_user_notice.py` `populated_store` fixture is missing on main. Do not add it on this branch.
- The broken `operator-runbook.md` citation to `docs/plans/cucm-migration-roadmap.md` is a pre-existing failure. Do not touch it.













### Recommendation rule signature

```python
def recommend_<type>(context: dict[str, Any], options: list) -> tuple[str, str] | None:
```

Returns `(option_id, reasoning)` or `None`. The dispatch dict is `RECOMMENDATION_DISPATCH` near the bottom of `recommendation_rules.py`. We are NOT adding a new dispatch entry — we are extending the existing `recommend_feature_approximation` function to handle the new context key.

---

