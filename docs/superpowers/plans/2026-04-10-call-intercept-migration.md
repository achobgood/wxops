# Call Intercept Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect CUCM intercept-like configurations (blocked partitions, CFA-to-voicemail) and surface them as advisory findings in the assessment report, enabling operators to manually configure Webex call intercept post-migration.

**Architecture:** Extends 4 existing files (tier4 extractor, normalizers, cross-references, call settings mapper) and adds 1 new advisory pattern function + 1 new report section. No new files for core pipeline — tests in 5 new test files. Heuristic detection only, no auto-execution.

**Tech Stack:** Python 3.11, pytest, SQLite (MigrationStore), AXL SQL queries via `conn.execute_sql()`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/wxcli/migration/cucm/extractors/tier4.py` | Add `_extract_intercept_candidates()` method using SQL queries |
| Modify | `src/wxcli/migration/transform/normalizers.py` | Add `normalize_intercept_candidate()` + register in `NORMALIZER_REGISTRY` + `RAW_DATA_MAPPING` |
| Modify | `src/wxcli/migration/transform/cross_reference.py` | Add `_build_intercept_refs()` method to `CrossReferenceBuilder` |
| Modify | `src/wxcli/migration/transform/mappers/call_settings_mapper.py` | Add intercept detection in `map()` using cross-refs |
| Modify | `src/wxcli/migration/advisory/advisory_patterns.py` | Add `detect_call_intercept_candidates()` pattern #27 + register |
| Modify | `src/wxcli/migration/report/appendix.py` | Add section W: Call Intercept Candidates |
| Modify | `src/wxcli/migration/report/executive.py` | Add conditional intercept stat card in People section |
| Create | `tests/migration/cucm/test_intercept_extractor.py` | Extractor unit tests |
| Create | `tests/migration/transform/test_normalizers_intercept.py` | Normalizer unit tests |
| Create | `tests/migration/transform/mappers/test_call_settings_mapper_intercept.py` | Mapper extension tests |
| Create | `tests/migration/advisory/test_advisory_intercept.py` | Advisory pattern tests |
| Create | `tests/migration/transform/test_intercept_integration.py` | Integration test: extract→normalize→map→analyze with intercept |

---

### Task 1: Tier 4 Extractor — Intercept Candidate SQL Queries

**Files:**
- Modify: `src/wxcli/migration/cucm/extractors/tier4.py`
- Create: `tests/migration/cucm/test_intercept_extractor.py`

Unlike the other tier4 extractions that use `paginated_list()` (AXL SOAP), intercept candidates use `self.conn.execute_sql()` (direct SQL) because we're doing heuristic detection across multiple tables. This follows the same pattern as `extractors/templates.py` (softkey templates).

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/cucm/test_intercept_extractor.py`:

```python
"""Tests for Tier 4 intercept candidate extraction."""
from unittest.mock import MagicMock

from wxcli.migration.cucm.extractors.tier4 import Tier4Extractor


def _make_extractor():
    conn = MagicMock()
    conn.paginated_list.return_value = []  # stub other extractions
    conn.execute_sql.return_value = []
    return Tier4Extractor(conn), conn


class TestExtractInterceptCandidates:
    def test_extract_blocked_partition_candidates(self):
        """DNs in partitions named like '%intercept%' or '%block%' are detected."""
        ext, conn = _make_extractor()

        # execute_sql is called twice: once for blocked partitions, once for CFA-to-voicemail
        conn.execute_sql.side_effect = [
            # Blocked partition query
            [
                {"dnorpattern": "1001", "partition_name": "Blocked_PT",
                 "userid": "jsmith"},
            ],
            # CFA-to-voicemail query
            [],
        ]

        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 1
        assert candidates[0]["dn"] == "1001"
        assert candidates[0]["partition"] == "Blocked_PT"
        assert candidates[0]["signal_type"] == "blocked_partition"
        assert candidates[0]["userid"] == "jsmith"

    def test_extract_cfa_voicemail_candidates(self):
        """Users with CFA to voicemail + no device are detected."""
        ext, conn = _make_extractor()

        conn.execute_sql.side_effect = [
            # Blocked partition query
            [],
            # CFA-to-voicemail query
            [
                {"dnorpattern": "2001", "partition_name": "Internal_PT",
                 "cfadestination": "+14155550000", "userid": "jdoe"},
            ],
        ]

        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 1
        assert candidates[0]["signal_type"] == "cfa_voicemail"
        assert candidates[0]["forward_destination"] == "+14155550000"

    def test_extract_no_candidates(self):
        """Clean environment produces empty list."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = [[], []]

        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 0

    def test_partition_name_matching(self):
        """Various partition naming conventions are detected."""
        ext, conn = _make_extractor()

        conn.execute_sql.side_effect = [
            [
                {"dnorpattern": "1001", "partition_name": "Intercept_PT", "userid": "u1"},
                {"dnorpattern": "1002", "partition_name": "OOS_PT", "userid": "u2"},
                {"dnorpattern": "1003", "partition_name": "out_of_service_PT", "userid": "u3"},
            ],
            [],
        ]

        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 3
        assert all(c["signal_type"] == "blocked_partition" for c in candidates)

    def test_sql_failure_returns_empty(self):
        """SQL query failure logs warning, returns empty list."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = Exception("connection lost")

        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 0
        assert any("intercept" in e.lower() for e in result.errors)

    def test_deduplicates_across_queries(self):
        """Same DN appearing in both queries is not duplicated."""
        ext, conn = _make_extractor()

        conn.execute_sql.side_effect = [
            [{"dnorpattern": "1001", "partition_name": "Blocked_PT", "userid": "jsmith"}],
            [{"dnorpattern": "1001", "partition_name": "Blocked_PT",
              "cfadestination": "+14155550000", "userid": "jsmith"}],
        ]

        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        # blocked_partition takes precedence (stronger signal)
        assert len(candidates) == 1
        assert candidates[0]["signal_type"] == "blocked_partition"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/cucm/test_intercept_extractor.py -v`
Expected: FAIL — `_extract_intercept_candidates` method doesn't exist, `intercept_candidates` key not in results.

- [ ] **Step 3: Implement the extractor method**

In `src/wxcli/migration/cucm/extractors/tier4.py`, add SQL constants after `DEVICE_PROFILE_TAGS` (line 30):

```python
# SQL for intercept candidate detection (heuristic — no direct CUCM equivalent)
_BLOCKED_PARTITION_SQL = """\
SELECT n.dnorpattern, rp.name as partition_name, eu.userid
FROM numplan n
JOIN routepartition rp ON rp.pkid = n.fkroutepartition
LEFT JOIN devicenumplanmap dnpm ON dnpm.fknumplan = n.pkid
LEFT JOIN device d ON d.pkid = dnpm.fkdevice
LEFT JOIN enduser eu ON eu.pkid = d.fkenduser
WHERE LOWER(rp.name) LIKE '%intercept%'
   OR LOWER(rp.name) LIKE '%block%'
   OR LOWER(rp.name) LIKE '%out_of_service%'
   OR LOWER(rp.name) LIKE '%oos%'
"""

_CFA_VOICEMAIL_SQL = """\
SELECT n.dnorpattern, rp.name as partition_name,
       cfwd.cfadestination, eu.userid
FROM numplan n
LEFT JOIN routepartition rp ON rp.pkid = n.fkroutepartition
JOIN callforwarddynamic cfwd ON cfwd.fknumplan = n.pkid
LEFT JOIN devicenumplanmap dnpm ON dnpm.fknumplan = n.pkid
LEFT JOIN device d ON d.pkid = dnpm.fkdevice
LEFT JOIN enduser eu ON eu.pkid = d.fkenduser
WHERE cfwd.cfadestination IS NOT NULL
  AND cfwd.cfadestination != ''
  AND cfwd.cfavoicemailenabled = 't'
  AND NOT EXISTS (
      SELECT 1 FROM device d2
      JOIN devicenumplanmap dnpm2 ON dnpm2.fkdevice = d2.pkid
      WHERE dnpm2.fknumplan = n.pkid
        AND d2.tkclass = 1
        AND d2.tkstatus_registrationstate = 2
  )
"""
```

Add the new method to `Tier4Extractor` class (after `_extract_type` method):

```python
    def _extract_intercept_candidates(self, result: ExtractionResult) -> int:
        """Detect intercept-like configurations via SQL heuristics.

        Two signals:
        1. DNs in partitions named like 'intercept', 'block', 'oos', 'out_of_service'
        2. DNs with CFA-to-voicemail enabled AND no registered device

        Deduplicates by DN — blocked_partition takes precedence (stronger signal).
        """
        seen: dict[str, dict[str, Any]] = {}  # dn -> candidate dict

        # Signal 1: Blocked partitions
        try:
            rows = self.conn.execute_sql(_BLOCKED_PARTITION_SQL)
            for row in rows:
                dn = row.get("dnorpattern", "")
                if not dn:
                    continue
                seen[dn] = {
                    "userid": row.get("userid") or "",
                    "dn": dn,
                    "partition": row.get("partition_name") or "",
                    "signal_type": "blocked_partition",
                    "forward_destination": "",
                    "voicemail_enabled": False,
                }
        except Exception as exc:
            msg = f"Intercept blocked-partition SQL failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)

        # Signal 2: CFA-to-voicemail with no registered device
        try:
            rows = self.conn.execute_sql(_CFA_VOICEMAIL_SQL)
            for row in rows:
                dn = row.get("dnorpattern", "")
                if not dn or dn in seen:
                    continue  # blocked_partition takes precedence
                seen[dn] = {
                    "userid": row.get("userid") or "",
                    "dn": dn,
                    "partition": row.get("partition_name") or "",
                    "signal_type": "cfa_voicemail",
                    "forward_destination": row.get("cfadestination") or "",
                    "voicemail_enabled": True,
                }
        except Exception as exc:
            msg = f"Intercept CFA-voicemail SQL failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)

        candidates = list(seen.values())
        self.results["intercept_candidates"] = candidates
        logger.info("[%s] intercept_candidates: %d objects", self.name, len(candidates))
        return len(candidates)
```

In the `extract()` method, add the call after the device_profiles extraction (after line 74, before `result.total = total`):

```python
        total += self._extract_intercept_candidates(result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/cucm/test_intercept_extractor.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Run existing tier4 tests to verify no regressions**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/cucm/ -v -k tier4`
Expected: All existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/migration/cucm/test_intercept_extractor.py src/wxcli/migration/cucm/extractors/tier4.py
git commit -m "feat(migration): add intercept candidate SQL extraction to tier4 extractor"
```

---

### Task 2: Normalizer — `normalize_intercept_candidate`

**Files:**
- Modify: `src/wxcli/migration/transform/normalizers.py:1607` (after `normalize_info_device_profile`)
- Modify: `src/wxcli/migration/transform/normalizers.py:1690` (`NORMALIZER_REGISTRY`)
- Modify: `src/wxcli/migration/transform/normalizers.py:1739` (`RAW_DATA_MAPPING`)
- Create: `tests/migration/transform/test_normalizers_intercept.py`

Follows the exact same pattern as `normalize_recording_profile` (line 1521) — pure function, no store access, returns `MigrationObject` with `pre_migration_state`.

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/transform/test_normalizers_intercept.py`:

```python
"""Tests for intercept candidate normalizer."""
from wxcli.migration.transform.normalizers import normalize_intercept_candidate


class TestNormalizeInterceptCandidate:
    def test_blocked_partition_candidate(self):
        """Blocked partition signal normalizes to MigrationObject."""
        raw = {
            "userid": "jsmith",
            "dn": "1001",
            "partition": "Blocked_PT",
            "signal_type": "blocked_partition",
            "forward_destination": "",
            "voicemail_enabled": False,
        }
        obj = normalize_intercept_candidate(raw)
        assert obj.canonical_id == "intercept_candidate:1001:Blocked_PT"
        assert obj.pre_migration_state["signal_type"] == "blocked_partition"
        assert obj.pre_migration_state["userid"] == "jsmith"
        assert obj.pre_migration_state["dn"] == "1001"

    def test_cfa_voicemail_candidate(self):
        """CFA-to-voicemail signal normalizes with forward destination."""
        raw = {
            "userid": "jdoe",
            "dn": "2001",
            "partition": "Internal_PT",
            "signal_type": "cfa_voicemail",
            "forward_destination": "+14155550000",
            "voicemail_enabled": True,
        }
        obj = normalize_intercept_candidate(raw)
        assert obj.canonical_id == "intercept_candidate:2001:Internal_PT"
        assert obj.pre_migration_state["signal_type"] == "cfa_voicemail"
        assert obj.pre_migration_state["forward_destination"] == "+14155550000"
        assert obj.pre_migration_state["voicemail_enabled"] is True

    def test_no_partition(self):
        """DN without partition uses '<None>' in canonical_id."""
        raw = {
            "userid": "u1",
            "dn": "3001",
            "partition": "",
            "signal_type": "blocked_partition",
            "forward_destination": "",
            "voicemail_enabled": False,
        }
        obj = normalize_intercept_candidate(raw)
        assert obj.canonical_id == "intercept_candidate:3001:<None>"

    def test_registry_contains_intercept_candidate(self):
        """Normalizer is registered in NORMALIZER_REGISTRY."""
        from wxcli.migration.transform.normalizers import NORMALIZER_REGISTRY
        assert "intercept_candidate" in NORMALIZER_REGISTRY

    def test_raw_data_mapping_contains_intercept(self):
        """RAW_DATA_MAPPING routes tier4.intercept_candidates correctly."""
        from wxcli.migration.transform.normalizers import RAW_DATA_MAPPING
        matches = [t for t in RAW_DATA_MAPPING if t[1] == "intercept_candidates"]
        assert len(matches) == 1
        assert matches[0] == ("tier4", "intercept_candidates", "intercept_candidate")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/test_normalizers_intercept.py -v`
Expected: FAIL — `normalize_intercept_candidate` not found in module.

- [ ] **Step 3: Implement the normalizer**

In `src/wxcli/migration/transform/normalizers.py`, add the function after `normalize_info_device_profile` (after line 1606):

```python
def normalize_intercept_candidate(
    raw: dict[str, Any],
    cluster: str = "unknown",
) -> MigrationObject:
    """Normalize a CUCM intercept candidate signal (heuristic detection).

    Intercept candidates are detected via SQL heuristics (blocked partitions,
    CFA-to-voicemail). They produce informational objects for advisory/report
    use — no auto-execution.
    """
    dn = raw.get("dn") or ""
    partition = raw.get("partition") or "<None>"
    return MigrationObject(
        canonical_id=f"intercept_candidate:{dn}:{partition}",
        provenance=_make_provenance(raw, cluster),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": raw.get("userid") or "",
            "dn": dn,
            "partition": partition if partition != "<None>" else "",
            "signal_type": raw.get("signal_type") or "unknown",
            "forward_destination": raw.get("forward_destination") or "",
            "voicemail_enabled": raw.get("voicemail_enabled", False),
        },
    )
```

Add to `NORMALIZER_REGISTRY` (after the `"info_device_profile"` entry, ~line 1690):

```python
    "intercept_candidate": normalize_intercept_candidate,
```

Add to `RAW_DATA_MAPPING` (after the `"device_profiles"` tier4 entry, ~line 1739):

```python
    ("tier4", "intercept_candidates", "intercept_candidate"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/test_normalizers_intercept.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Run existing normalizer tests for regressions**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/test_normalizers.py -v --timeout=30`
Expected: All existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/migration/transform/test_normalizers_intercept.py src/wxcli/migration/transform/normalizers.py
git commit -m "feat(migration): add intercept_candidate normalizer + registry entries"
```

---

### Task 3: Cross-References — `user_has_intercept_signal`

**Files:**
- Modify: `src/wxcli/migration/transform/cross_reference.py:191` (add to `build()` method list)
- Modify: `src/wxcli/migration/transform/cross_reference.py` (add `_build_intercept_refs` method after `_build_remote_destination_refs` at line 824)

Follows the same pattern as `_build_remote_destination_refs` (line 809-824) — iterate intercept candidates, resolve userid to `user:{userid}`, add cross-ref.

- [ ] **Step 1: Write the failing test**

This test goes into the integration test file (Task 7). For now, verify the cross-ref method works via a focused unit test. Add to `tests/migration/transform/test_normalizers_intercept.py`:

```python
class TestInterceptCrossRefs:
    def test_user_has_intercept_signal_cross_ref(self):
        """CrossReferenceBuilder links users to their intercept candidates."""
        import os
        from datetime import datetime, timezone
        from wxcli.migration.models import (
            CanonicalUser, MigrationObject, MigrationStatus, Provenance,
        )
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.cross_reference import CrossReferenceBuilder

        store = MigrationStore(":memory:")
        prov = Provenance(
            source_system="cucm", source_id="test", source_name="test",
            extracted_at=datetime.now(timezone.utc),
        )

        # Store a user
        store.upsert_object(CanonicalUser(
            canonical_id="user:jsmith", provenance=prov,
            status=MigrationStatus.NORMALIZED,
            emails=["jsmith@test.com"], cucm_userid="jsmith",
        ))

        # Store an intercept candidate for that user
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=prov,
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "jsmith",
                "dn": "1001",
                "partition": "Blocked_PT",
                "signal_type": "blocked_partition",
                "forward_destination": "",
                "voicemail_enabled": False,
            },
        ))

        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs("user:jsmith", "user_has_intercept_signal")
        assert len(refs) == 1
        assert refs[0] == "intercept_candidate:1001:Blocked_PT"

    def test_no_cross_ref_for_unknown_user(self):
        """Intercept candidates for non-existent users don't create cross-refs."""
        from datetime import datetime, timezone
        from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.cross_reference import CrossReferenceBuilder

        store = MigrationStore(":memory:")
        prov = Provenance(
            source_system="cucm", source_id="test", source_name="test",
            extracted_at=datetime.now(timezone.utc),
        )

        # Intercept candidate with no matching user in store
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:9999:OOS_PT",
            provenance=prov,
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "ghost_user",
                "dn": "9999",
                "partition": "OOS_PT",
                "signal_type": "blocked_partition",
            },
        ))

        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs("user:ghost_user", "user_has_intercept_signal")
        assert len(refs) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/test_normalizers_intercept.py::TestInterceptCrossRefs -v`
Expected: FAIL — `_build_intercept_refs` doesn't exist (or `user_has_intercept_signal` relationship never created).

- [ ] **Step 3: Implement the cross-reference method**

In `src/wxcli/migration/transform/cross_reference.py`, add a new method after `_build_remote_destination_refs` (after line 824):

```python
    def _build_intercept_refs(self) -> dict[str, int]:
        """Build user → intercept_candidate cross-refs.

        Links users to their heuristically-detected intercept signals
        (blocked partitions, CFA-to-voicemail). Used by CallSettingsMapper
        to enrich user objects and by the advisory pattern to list affected users.
        """
        count = 0
        for ic in self.store.get_objects("intercept_candidate"):
            state = ic.get("pre_migration_state") or {}
            userid = state.get("userid") or ""
            if not userid:
                continue
            user_cid = f"user:{userid}"
            if self.store.get_object(user_cid):
                self.store.add_cross_ref(user_cid, ic["canonical_id"], "user_has_intercept_signal")
                count += 1
        return {"user_has_intercept_signal": count}
```

Register it in the `build()` method's list (line 191, after `self._build_remote_destination_refs`):

```python
                self._build_intercept_refs,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/test_normalizers_intercept.py::TestInterceptCrossRefs -v`
Expected: Both tests PASS.

- [ ] **Step 5: Run existing cross-reference tests for regressions**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/ -v -k cross_ref --timeout=30`
Expected: All existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/transform/cross_reference.py tests/migration/transform/test_normalizers_intercept.py
git commit -m "feat(migration): add user_has_intercept_signal cross-reference"
```

---

### Task 4: CallSettingsMapper — Intercept Detection

**Files:**
- Modify: `src/wxcli/migration/transform/mappers/call_settings_mapper.py`
- Create: `tests/migration/transform/mappers/test_call_settings_mapper_intercept.py`

The existing mapper iterates phones, resolves owner users, and enriches them with call settings. We add intercept detection as a second pass that iterates users directly, checking for `user_has_intercept_signal` cross-refs. This avoids coupling intercept to the phone iteration loop (since intercept candidates are per-DN, not per-phone).

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/transform/mappers/test_call_settings_mapper_intercept.py`:

```python
"""Tests for CallSettingsMapper intercept detection extension."""
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.call_settings_mapper import CallSettingsMapper


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _setup_user_with_intercept(store, userid="jsmith", signal_type="blocked_partition"):
    """Create a user + intercept candidate + cross-ref in the store."""
    store.upsert_object(CanonicalUser(
        canonical_id=f"user:{userid}", provenance=_prov(userid),
        status=MigrationStatus.ANALYZED,
        emails=[f"{userid}@test.com"], cucm_userid=userid,
    ))
    store.upsert_object(MigrationObject(
        canonical_id=f"intercept_candidate:1001:Blocked_PT",
        provenance=_prov("ic"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": userid,
            "dn": "1001",
            "partition": "Blocked_PT",
            "signal_type": signal_type,
            "forward_destination": "+14155550000",
            "voicemail_enabled": signal_type == "cfa_voicemail",
        },
    ))
    store.add_cross_ref(
        f"user:{userid}",
        "intercept_candidate:1001:Blocked_PT",
        "user_has_intercept_signal",
    )


class TestInterceptDetection:
    def test_intercept_detection_blocked_partition(self):
        """User with intercept cross-ref gets call_settings.intercept populated."""
        store = MigrationStore(":memory:")
        _setup_user_with_intercept(store, "jsmith", "blocked_partition")

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:jsmith")
        assert user_data is not None
        intercept = user_data.get("call_settings", {}).get("intercept")
        assert intercept is not None
        assert intercept["detected"] is True
        assert intercept["signal_type"] == "blocked_partition"

    def test_intercept_detection_cfa_voicemail(self):
        """CFA-to-voicemail signal detected."""
        store = MigrationStore(":memory:")
        _setup_user_with_intercept(store, "jdoe", "cfa_voicemail")

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:jdoe")
        intercept = user_data.get("call_settings", {}).get("intercept")
        assert intercept is not None
        assert intercept["signal_type"] == "cfa_voicemail"
        assert intercept["forward_destination"] == "+14155550000"
        assert intercept["voicemail_enabled"] is True

    def test_no_intercept_signal(self):
        """User without intercept cross-ref has no intercept in call_settings."""
        store = MigrationStore(":memory:")
        store.upsert_object(CanonicalUser(
            canonical_id="user:clean", provenance=_prov("clean"),
            status=MigrationStatus.ANALYZED,
            emails=["clean@test.com"], cucm_userid="clean",
        ))

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:clean")
        call_settings = user_data.get("call_settings") or {}
        assert "intercept" not in call_settings

    def test_intercept_does_not_override_other_settings(self):
        """Intercept detection coexists with DND, call waiting, etc."""
        store = MigrationStore(":memory:")
        _setup_user_with_intercept(store, "jsmith", "blocked_partition")

        # Also add a phone with DND enabled for the same user
        store.upsert_object(MigrationObject(
            canonical_id="phone:SEP001",
            provenance=_prov("SEP001"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SEP001",
                "dndStatus": "true",
                "dndOption": "Call Reject",
                "lines": [{"index": "1", "dirn": {"pattern": "1001"}}],
            },
        ))
        store.add_cross_ref("phone:SEP001", "user:jsmith", "device_owned_by_user")

        mapper = CallSettingsMapper()
        mapper.map(store)

        user_data = store.get_object("user:jsmith")
        call_settings = user_data.get("call_settings", {})
        # Both DND and intercept should be present
        assert "doNotDisturb" in call_settings
        assert call_settings["doNotDisturb"]["enabled"] is True
        assert "intercept" in call_settings
        assert call_settings["intercept"]["detected"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/mappers/test_call_settings_mapper_intercept.py -v`
Expected: FAIL — intercept detection not implemented yet.

- [ ] **Step 3: Implement intercept detection in CallSettingsMapper**

In `src/wxcli/migration/transform/mappers/call_settings_mapper.py`, add a second pass after the existing phone iteration loop. Modify the `map()` method to add intercept detection after the phone loop (after line 70, before `return result`):

```python
        # --- Pass 2: Intercept candidate detection ---
        # Iterate users with intercept cross-refs (independent of phone ownership)
        for user_data in store.get_objects("user"):
            user_id = user_data["canonical_id"]
            intercept_refs = store.find_cross_refs(user_id, "user_has_intercept_signal")
            if not intercept_refs:
                continue
            candidate = store.get_object(intercept_refs[0])
            if not candidate:
                continue
            pre = candidate.get("pre_migration_state") or {}
            intercept_settings = {
                "detected": True,
                "signal_type": pre.get("signal_type", "unknown"),
                "forward_destination": pre.get("forward_destination"),
                "voicemail_enabled": pre.get("voicemail_enabled", False),
            }
            # Merge into existing call_settings (may already have DND, etc.)
            existing_settings = user_data.get("call_settings") or {}
            existing_settings["intercept"] = intercept_settings
            enrich_user(store, user_id, call_settings=existing_settings)
            result.objects_updated += 1
            logger.debug(
                "Enriched user %s with intercept signal from %s",
                user_id, intercept_refs[0],
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/mappers/test_call_settings_mapper_intercept.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Run existing call settings mapper tests for regressions**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/mappers/test_call_settings_mapper.py -v`
Expected: All 7 existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/migration/transform/mappers/test_call_settings_mapper_intercept.py src/wxcli/migration/transform/mappers/call_settings_mapper.py
git commit -m "feat(migration): add intercept detection to CallSettingsMapper"
```

---

### Task 5: Advisory Pattern — `detect_call_intercept_candidates`

**Files:**
- Modify: `src/wxcli/migration/advisory/advisory_patterns.py` (add pattern function + register in `ALL_ADVISORY_PATTERNS`)
- Create: `tests/migration/advisory/test_advisory_intercept.py`

Pattern #28 (the CLAUDE.md shows 27 patterns after the voicemail greeting pattern was added). Category: `out_of_scope`. Severity: `MEDIUM`. Groups candidates by signal type. Includes location-level detection (>80% of users in a location → recommend location-level intercept).

- [ ] **Step 1: Write the failing tests**

Create `tests/migration/advisory/test_advisory_intercept.py`:

```python
"""Tests for call intercept candidates advisory pattern."""
import os
from datetime import datetime, timezone

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm", source_id="test", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name="t.db"):
    return MigrationStore(os.path.join(str(tmp_path), name))


class TestDetectCallInterceptCandidates:
    def test_pattern_fires_with_candidates(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "jsmith", "dn": "1001", "partition": "Blocked_PT",
                "signal_type": "blocked_partition",
            },
        ))
        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 1
        assert "1" in findings[0].summary
        assert findings[0].severity == "MEDIUM"
        assert findings[0].category == "out_of_scope"

    def test_pattern_silent_no_candidates(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 0

    def test_pattern_groups_by_signal_type(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        # 2 blocked partition + 1 CFA-to-voicemail
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u1", "dn": "1001",
                                 "signal_type": "blocked_partition"},
        ))
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1002:OOS_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u2", "dn": "1002",
                                 "signal_type": "blocked_partition"},
        ))
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:2001:Internal_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u3", "dn": "2001",
                                 "signal_type": "cfa_voicemail"},
        ))

        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 1
        assert "3" in findings[0].summary
        # Detail should mention both signal types
        assert "blocked partition" in findings[0].detail.lower()
        assert "cfa" in findings[0].detail.lower()

    def test_pattern_recommendation_accept(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates

        store = _store(tmp_path)
        store.upsert_object(MigrationObject(
            canonical_id="intercept_candidate:1001:Blocked_PT",
            provenance=_prov(), status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "u1", "dn": "1001",
                                 "signal_type": "blocked_partition"},
        ))
        findings = detect_call_intercept_candidates(store)
        assert findings[0].recommendation == "accept"

    def test_pattern_registered(self):
        from wxcli.migration.advisory.advisory_patterns import ALL_ADVISORY_PATTERNS, detect_call_intercept_candidates
        assert detect_call_intercept_candidates in ALL_ADVISORY_PATTERNS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/advisory/test_advisory_intercept.py -v`
Expected: FAIL — `detect_call_intercept_candidates` not found.

- [ ] **Step 3: Implement the advisory pattern**

In `src/wxcli/migration/advisory/advisory_patterns.py`, add the pattern function before `ALL_ADVISORY_PATTERNS` (before line 1764):

```python
def detect_call_intercept_candidates(store: MigrationStore) -> list[AdvisoryFinding]:
    """Users with intercept-like CUCM configurations need manual Webex intercept setup.

    Scans for intercept_candidate objects (heuristically detected via blocked
    partitions and CFA-to-voicemail with no registered device). Groups by
    signal type for a structured summary.
    """
    candidates = store.get_objects("intercept_candidate")
    if not candidates:
        return []

    # Group by signal type
    by_type: dict[str, list[str]] = defaultdict(list)
    ids = []
    for ic in candidates:
        pre = ic.get("pre_migration_state", {}) or {}
        signal = pre.get("signal_type", "unknown")
        userid = pre.get("userid", "")
        by_type[signal].append(userid)
        ids.append(ic.get("canonical_id", ""))

    total = len(candidates)
    type_parts = []
    for signal, users in sorted(by_type.items()):
        label = signal.replace("_", " ")
        type_parts.append(f"{len(users)} via {label}")
    type_summary = ", ".join(type_parts)

    detail = (
        f"{total} user{'s' if total != 1 else ''} ha{'ve' if total != 1 else 's'} "
        f"intercept-like configurations in CUCM ({type_summary}). "
        f"Webex Calling has a native call intercept feature (per-person incoming/outgoing "
        f"intercept with announcements and redirect options) that should be configured "
        f"manually post-migration for these users. "
        f"The CUCM configurations are heuristic detections \u2014 verify each user\u2019s "
        f"intended intercept behavior before enabling Webex intercept. Auto-enabling "
        f"intercept would block calls to these users, which may not be the intended "
        f"post-migration state."
    )

    return [AdvisoryFinding(
        pattern_name="call_intercept_candidates",
        severity="MEDIUM",
        summary=f"{total} users with intercept-like configurations \u2014 manual Webex intercept setup required",
        detail=detail,
        affected_objects=ids,
        category="out_of_scope",
    )]
```

Register it in `ALL_ADVISORY_PATTERNS` (after the last entry, before the closing `]`):

```python
    detect_call_intercept_candidates,        # Pattern 28 (Tier 4: intercept candidates)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/advisory/test_advisory_intercept.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Run existing advisory tests for regressions**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/advisory/ -v --timeout=30`
Expected: All existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/migration/advisory/test_advisory_intercept.py src/wxcli/migration/advisory/advisory_patterns.py
git commit -m "feat(migration): add call intercept candidates advisory pattern #28"
```

---

### Task 6: Report — Appendix Section W + Executive Stat Card

**Files:**
- Modify: `src/wxcli/migration/report/appendix.py` (add section W after line 1523)
- Modify: `src/wxcli/migration/report/appendix.py:51` (add "W" entry to `sections` list)
- Modify: `src/wxcli/migration/report/executive.py:222` (add conditional intercept stat card)

Follows the same `<details>` pattern as section V (Extension Mobility, line 1487-1523). The executive stat card follows the conditional pattern at line 218-222.

- [ ] **Step 1: Add section W to appendix.py**

In `src/wxcli/migration/report/appendix.py`, add the function after `_extension_mobility_group` (after line 1523):

```python
def _intercept_candidates(store: MigrationStore) -> str:
    """W. Call Intercept Candidates -- heuristically detected."""
    candidates = store.get_objects("intercept_candidate")
    if not candidates:
        return ""

    summary = f"{len(candidates)} intercept candidate{'s' if len(candidates) != 1 else ''}"

    parts = [
        '<details id="intercept-candidates">',
        f'<summary>W. Call Intercept Candidates <span class="summary-count">'
        f'\u2014 {summary}</span></summary>',
        '<div class="details-content">',
        '<div class="callout warning">',
        '<p><strong>These users may need Webex call intercept configured post-migration.</strong> '
        'Detected via heuristics (blocked partitions, CFA-to-voicemail with no registered device). '
        'Verify each user\u2019s intended state before enabling intercept \u2014 auto-enabling '
        'would block all calls to/from the user.</p>',
        '</div>',
        '<table>',
        '<thead><tr><th>User</th><th>DN</th><th>Partition</th>'
        '<th>Signal Type</th><th>Forward Destination</th></tr></thead>',
        '<tbody>',
    ]

    em_dash = "\u2014"
    for ic in sorted(candidates, key=lambda c: c.get("pre_migration_state", {}).get("userid", "")):
        pre = ic.get("pre_migration_state", {}) or {}
        userid = pre.get("userid") or em_dash
        dn = pre.get("dn") or em_dash
        partition = pre.get("partition") or em_dash
        signal = (pre.get("signal_type") or "unknown").replace("_", " ").title()
        fwd = pre.get("forward_destination") or em_dash
        parts.append(
            f'<tr><td>{html.escape(userid)}</td>'
            f'<td>{html.escape(dn)}</td>'
            f'<td>{html.escape(partition)}</td>'
            f'<td>{html.escape(signal)}</td>'
            f'<td>{html.escape(fwd)}</td></tr>'
        )

    parts.append('</tbody></table>')
    parts.append('</div></details>')
    return "\n".join(parts)
```

Register in the `generate_appendix` `sections` list (after the "V" entry at line 73):

```python
        ("W", _intercept_candidates(store)),
```

- [ ] **Step 2: Add conditional stat card to executive.py**

In `src/wxcli/migration/report/executive.py`, add after the `if line_count:` block (after line 222, before `parts.append('</div>')`):

```python
    intercept_count = store.count_by_type("intercept_candidate")
    if intercept_count:
        parts.append(_stat_card(str(intercept_count), "Intercept Candidates"))
```

- [ ] **Step 3: Run existing report tests to verify no regressions**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/report/ -v --timeout=60`
Expected: All existing tests PASS. The new section won't appear in existing tests (no intercept_candidate objects in test stores).

- [ ] **Step 4: Commit**

```bash
git add src/wxcli/migration/report/appendix.py src/wxcli/migration/report/executive.py
git commit -m "feat(migration): add intercept candidates to assessment report (section W + stat card)"
```

---

### Task 7: Integration Test — Full Pipeline with Intercept

**Files:**
- Create: `tests/migration/transform/test_intercept_integration.py`

End-to-end test: raw_data with intercept candidates → normalize → cross-refs → map → analyze → verify advisory + report section present.

- [ ] **Step 1: Write the integration test**

Create `tests/migration/transform/test_intercept_integration.py`:

```python
"""Integration test: intercept candidates through the full pipeline."""
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser, MigrationObject, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.normalizers import NORMALIZER_REGISTRY
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder
from wxcli.migration.transform.mappers.call_settings_mapper import CallSettingsMapper
from wxcli.migration.advisory.advisory_patterns import detect_call_intercept_candidates
from wxcli.migration.report.appendix import generate_appendix
from wxcli.migration.report.executive import _page_environment


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _build_store_with_intercept():
    """Build a store with a user + intercept candidate, simulating the full pipeline."""
    store = MigrationStore(":memory:")

    # 1. Simulate normalized user
    store.upsert_object(CanonicalUser(
        canonical_id="user:jsmith", provenance=_prov("jsmith"),
        status=MigrationStatus.NORMALIZED,
        emails=["jsmith@test.com"], cucm_userid="jsmith",
    ))

    # 2. Simulate normalized intercept candidate (as normalize_discovery would produce)
    raw_candidate = {
        "userid": "jsmith",
        "dn": "1001",
        "partition": "Blocked_PT",
        "signal_type": "blocked_partition",
        "forward_destination": "",
        "voicemail_enabled": False,
    }
    normalizer = NORMALIZER_REGISTRY["intercept_candidate"]
    obj = normalizer(raw_candidate)
    store.upsert_object(obj)

    # 3. Build cross-references
    builder = CrossReferenceBuilder(store)
    builder.build()

    # 4. Run CallSettingsMapper
    mapper = CallSettingsMapper()
    mapper.map(store)

    return store


class TestInterceptFullPipeline:
    def test_full_pipeline_with_intercept(self):
        """Intercept candidate flows through normalize → cross-ref → map → analyze."""
        store = _build_store_with_intercept()

        # Verify cross-ref was built
        refs = store.find_cross_refs("user:jsmith", "user_has_intercept_signal")
        assert len(refs) == 1

        # Verify user was enriched with intercept settings
        user_data = store.get_object("user:jsmith")
        assert user_data is not None
        call_settings = user_data.get("call_settings", {})
        assert "intercept" in call_settings
        assert call_settings["intercept"]["detected"] is True
        assert call_settings["intercept"]["signal_type"] == "blocked_partition"

        # Verify advisory pattern fires
        findings = detect_call_intercept_candidates(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "call_intercept_candidates"
        assert findings[0].severity == "MEDIUM"
        assert findings[0].category == "out_of_scope"

    def test_report_includes_intercept(self):
        """Assessment report appendix includes intercept candidates section."""
        store = _build_store_with_intercept()

        appendix_html = generate_appendix(store)
        assert "intercept-candidates" in appendix_html
        assert "Call Intercept Candidates" in appendix_html
        assert "jsmith" in appendix_html
        assert "Blocked Partition" in appendix_html
```

- [ ] **Step 2: Run the integration test**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/transform/test_intercept_integration.py -v`
Expected: Both tests PASS (if Tasks 1-6 are all implemented).

- [ ] **Step 3: Run the full migration test suite**

Run: `cd /Users/ahobgood/Documents/webexCalling && python3.11 -m pytest tests/migration/ -v --timeout=120 -x`
Expected: All tests PASS including the new ones.

- [ ] **Step 4: Commit**

```bash
git add tests/migration/transform/test_intercept_integration.py
git commit -m "test(migration): add intercept candidate integration test"
```

---

### Task 8: Documentation Updates

**Files:**
- Modify: `src/wxcli/migration/cucm/CLAUDE.md` — add `intercept_candidates` to raw_data structure
- Modify: `src/wxcli/migration/transform/CLAUDE.md` — add normalizer + cross-ref
- Modify: `src/wxcli/migration/transform/mappers/CLAUDE.md` — note intercept detection
- Modify: `src/wxcli/migration/advisory/CLAUDE.md` — add pattern 28
- Modify: `src/wxcli/migration/report/CLAUDE.md` — add section W to appendix listing

- [ ] **Step 1: Update cucm/CLAUDE.md**

In `src/wxcli/migration/cucm/CLAUDE.md`, in the `raw_data Structure` section, add after the existing tier4 description:

```markdown
- `tier4.intercept_candidates` — heuristically detected intercept-like configurations (blocked partition DNs, CFA-to-voicemail with no registered device). Uses SQL queries, not AXL list operations.
```

In the `extractors/tier4.py` row of the Files table, update the Purpose:

```markdown
| `extractors/tier4.py` | Tier 4 feature gaps: recording profiles, remote destinations, transformation patterns, EM device profiles, intercept candidates (SQL heuristic) |
```

- [ ] **Step 2: Update transform/CLAUDE.md**

In `src/wxcli/migration/transform/CLAUDE.md`, in the `Pass 1: Normalizers` section, add to the key normalizers list:

```markdown
- `normalize_intercept_candidate` → `MigrationObject` (Tier 4 informational — intercept-like signals from CUCM)
```

In the `Pass 2: CrossReferenceBuilder` table, add a row:

```markdown
| `_build_intercept_refs` | user_has_intercept_signal |
```

Update the relationship count from "30 relationships" to "31 relationships" in the header.

- [ ] **Step 3: Update transform/mappers/CLAUDE.md**

In `src/wxcli/migration/transform/mappers/CLAUDE.md`, in the `CallSettingsMapper` description (Tier 3 table), add a note:

After the existing description, add: `Also detects intercept candidates via user_has_intercept_signal cross-ref (Pass 2 — independent of phone iteration).`

- [ ] **Step 4: Update advisory/CLAUDE.md**

In `src/wxcli/migration/advisory/CLAUDE.md`, update:

1. Pattern count from "27 pattern detector functions" to "28 pattern detector functions" (line 26/73)
2. Add to the Tier 4 feature gap patterns list:
```markdown
28. Call Intercept Candidates — heuristically detected blocked partitions + CFA-to-voicemail → manual Webex intercept setup
```
3. Update test count to include new tests

- [ ] **Step 5: Update report/CLAUDE.md**

In `src/wxcli/migration/report/CLAUDE.md`, update the `appendix.py` description to include "W. Call Intercept Candidates" in the section listing. Change "22 lettered sections A-V" to "23 lettered sections A-W".

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/migration/cucm/CLAUDE.md src/wxcli/migration/transform/CLAUDE.md src/wxcli/migration/transform/mappers/CLAUDE.md src/wxcli/migration/advisory/CLAUDE.md src/wxcli/migration/report/CLAUDE.md
git commit -m "docs(migration): update CLAUDE.md files for intercept candidate feature"
```

---

### Task 9: Knowledge Base + Runbook Updates

**Files:**
- Modify: `docs/knowledge-base/migration/kb-user-settings.md`
- Modify: `docs/knowledge-base/migration/kb-feature-mapping.md`
- Modify: `docs/knowledge-base/migration/kb-webex-limits.md`
- Modify: `docs/runbooks/cucm-migration/operator-runbook.md`
- Modify: `docs/runbooks/cucm-migration/decision-guide.md`
- Modify: `docs/runbooks/cucm-migration/tuning-reference.md`

These are documentation-only changes. Read each file first to find the exact insertion points.

- [ ] **Step 1: Update kb-user-settings.md**

Read the file, find the call settings mapping table, and add a row:

```markdown
| Call Intercept | No CUCM equivalent | Detect via CFA/partition heuristics; manual Webex config | Advisory only |
```

- [ ] **Step 2: Update kb-feature-mapping.md**

Read the file, find the feature mapping table, and add:

```markdown
| Call Intercept | — (Webex-native, no CUCM 1:1 source) | Manual | Detection heuristics identify candidates; operator configures Webex intercept per-user |
```

- [ ] **Step 3: Update kb-webex-limits.md**

Read the file, find the feature availability section, and add:

```markdown
- **Call Intercept:** Requires Professional license (same as other person-level telephony settings). Available per-person, per-workspace, per-virtual-line, and per-location.
```

- [ ] **Step 4: Update operator-runbook.md**

Read the file, find the post-migration verification section, and add a step:

```markdown
- **Review intercept candidates:** Check the assessment report's "Call Intercept Candidates" section (Appendix W). For each flagged user, verify their intended intercept state and configure Webex intercept via Control Hub or `wxcli user-settings update-intercept`.
```

- [ ] **Step 5: Update decision-guide.md**

Read the file, find the advisory patterns section, and add:

```markdown
### `call_intercept_candidates` (Pattern 28)

**Category:** out_of_scope | **Severity:** MEDIUM | **Recommendation:** accept

**What it detects:** Users with intercept-like CUCM configurations — DNs in partitions named "intercept", "block", "oos", or "out_of_service", plus DNs with CFA-to-voicemail enabled and no registered device.

**What to do:** Review each flagged user. Determine if they should have Webex call intercept enabled post-migration. Configure manually — auto-enabling intercept would block all calls to/from the user.

**Override criteria:** If the blocked-partition naming convention in the customer's CUCM doesn't match the default patterns (`%intercept%`, `%block%`, `%oos%`, `%out_of_service%`), tune the SQL queries or ignore false positives.
```

- [ ] **Step 6: Update tuning-reference.md**

Read the file, find the Tier 4 feature gaps section, and add:

```markdown
**Intercept candidate detection heuristics:**
- Blocked partition patterns: `%intercept%`, `%block%`, `%out_of_service%`, `%oos%` (case-insensitive LIKE match)
- CFA-to-voicemail: requires `cfavoicemailenabled = 't'` AND no registered device on that DN
- To reduce false positives: review the customer's partition naming conventions before running discovery
- Blocked-partition signal takes precedence over CFA-voicemail when both match the same DN
```

- [ ] **Step 7: Commit**

```bash
git add docs/knowledge-base/migration/kb-user-settings.md docs/knowledge-base/migration/kb-feature-mapping.md docs/knowledge-base/migration/kb-webex-limits.md docs/runbooks/cucm-migration/operator-runbook.md docs/runbooks/cucm-migration/decision-guide.md docs/runbooks/cucm-migration/tuning-reference.md
git commit -m "docs(migration): add call intercept to knowledge base, runbooks, and tuning reference"
```

---

## Summary

| Task | Component | Tests | Est. Lines |
|------|-----------|-------|------------|
| 1 | Tier4 extractor (SQL queries) | 6 | ~90 impl + ~100 test |
| 2 | Normalizer + registry | 5 | ~25 impl + ~60 test |
| 3 | Cross-reference builder | 2 | ~15 impl + ~60 test |
| 4 | CallSettingsMapper extension | 4 | ~30 impl + ~90 test |
| 5 | Advisory pattern #28 | 5 | ~45 impl + ~80 test |
| 6 | Report appendix W + exec stat | 0 (covered by Task 7) | ~50 impl |
| 7 | Integration test | 2 | ~70 test |
| 8 | CLAUDE.md updates (5 files) | 0 | ~50 docs |
| 9 | KB + runbook updates (6 files) | 0 | ~80 docs |
| **Total** | | **24 tests** | **~845 lines** |
