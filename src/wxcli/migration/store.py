"""SQLite-backed migration store.

Thin wrapper over sqlite3 for migration persistence. Uses WAL mode for
concurrent reads and foreign keys for referential integrity.

Schema from: 01-data-representation.md (objects, cross_refs, decisions, journal)
             07-idempotency-resumability.md (merge_log)
             05-dependency-graph.md (plan_operations, plan_edges)
Query helpers from: 03b-transform-mappers.md shared patterns section
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wxcli.migration.models import (
    CANONICAL_CLASS_TO_TYPE,
    CANONICAL_TYPE_REGISTRY,
    MigrationObject,
    MigrationStatus,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MigrationStore:
    """SQLite-backed store for migration objects, cross-refs, and decisions.

    (from 01-data-representation.md lines 112-136,
     03b-transform-mappers.md shared patterns lines 999-1031)
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        # WAL mode for concurrent reads (from 01-data-representation.md line 118)
        self.conn.execute("PRAGMA journal_mode=WAL")
        # Foreign keys (from 01-data-representation.md line 119)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._run_id: str | None = None
        self._ensure_schema()
        self._decision_counter: int = self._max_decision_number()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> MigrationStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        """Create all tables and indexes if they don't exist.
        (from 01-data-representation.md lines 30-91,
         07-idempotency-resumability.md lines 209-218,
         05-dependency-graph.md lines 304-325)
        """
        self.conn.executescript("""
            -- Core object store (from 01-data-representation.md lines 34-48)
            CREATE TABLE IF NOT EXISTS objects (
                canonical_id   TEXT PRIMARY KEY,
                object_type    TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'discovered',
                location_id    TEXT,
                webex_id       TEXT,
                batch          TEXT,
                tier           INTEGER,
                data           TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_type_status ON objects(object_type, status);
            CREATE INDEX IF NOT EXISTS idx_location ON objects(location_id);
            CREATE INDEX IF NOT EXISTS idx_batch_tier ON objects(batch, tier);

            -- Cross-references (from 01-data-representation.md lines 50-61)
            CREATE TABLE IF NOT EXISTS cross_refs (
                from_id        TEXT NOT NULL,
                to_id          TEXT NOT NULL,
                relationship   TEXT NOT NULL,
                ordinal        INTEGER,
                PRIMARY KEY (from_id, to_id, relationship),
                FOREIGN KEY (from_id) REFERENCES objects(canonical_id),
                FOREIGN KEY (to_id) REFERENCES objects(canonical_id)
            );
            CREATE INDEX IF NOT EXISTS idx_xref_to ON cross_refs(to_id, relationship);

            -- Decisions (from 01-data-representation.md lines 63-77)
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id    TEXT PRIMARY KEY,
                type           TEXT NOT NULL,
                severity       TEXT NOT NULL,
                summary        TEXT NOT NULL,
                context        TEXT NOT NULL,
                options        TEXT NOT NULL,
                chosen_option  TEXT,
                resolved_at    TEXT,
                resolved_by    TEXT,
                fingerprint    TEXT NOT NULL,
                run_id         TEXT NOT NULL,
                UNIQUE(fingerprint)
            );

            -- Execution journal (from 01-data-representation.md lines 79-90)
            CREATE TABLE IF NOT EXISTS journal (
                entry_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp      TEXT NOT NULL,
                entry_type     TEXT NOT NULL,
                canonical_id   TEXT NOT NULL,
                resource_type  TEXT NOT NULL,
                request        TEXT NOT NULL,
                response       TEXT,
                pre_state      TEXT,
                FOREIGN KEY (canonical_id) REFERENCES objects(canonical_id)
            );

            -- Merge log (from 07-idempotency-resumability.md lines 209-218)
            CREATE TABLE IF NOT EXISTS merge_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp      TEXT NOT NULL,
                stage          TEXT NOT NULL,
                run_id         TEXT NOT NULL,
                action         TEXT NOT NULL,
                target_type    TEXT NOT NULL,
                target_id      TEXT NOT NULL,
                details        TEXT
            );

            -- Execution plan DAG (from 05-dependency-graph.md lines 304-325)
            CREATE TABLE IF NOT EXISTS plan_operations (
                node_id        TEXT PRIMARY KEY,
                canonical_id   TEXT NOT NULL,
                op_type        TEXT NOT NULL,
                resource_type  TEXT NOT NULL,
                tier           INTEGER NOT NULL,
                batch          TEXT,
                api_calls      INTEGER DEFAULT 1,
                description    TEXT,
                status         TEXT DEFAULT 'pending',
                -- Phase 12b execution tracking
                webex_id       TEXT,
                error_message  TEXT,
                completed_at   TEXT,
                attempts       INTEGER DEFAULT 0,
                FOREIGN KEY (canonical_id) REFERENCES objects(canonical_id)
            );

            CREATE TABLE IF NOT EXISTS plan_edges (
                from_node      TEXT NOT NULL,
                to_node        TEXT NOT NULL,
                dep_type       TEXT NOT NULL,
                broken         INTEGER DEFAULT 0,
                PRIMARY KEY (from_node, to_node),
                FOREIGN KEY (from_node) REFERENCES plan_operations(node_id),
                FOREIGN KEY (to_node) REFERENCES plan_operations(node_id)
            );
        """)
        self.conn.commit()

        # Schema migration for Phase 12b execution tracking
        for col, col_def in [
            ("webex_id", "TEXT"),
            ("error_message", "TEXT"),
            ("completed_at", "TEXT"),
            ("attempts", "INTEGER DEFAULT 0"),
        ]:
            try:
                self.conn.execute(
                    f"ALTER TABLE plan_operations ADD COLUMN {col} {col_def}"
                )
            except Exception:
                pass  # Column already exists

        # Advisory system schema migration (Phase 13a)
        for col in ["recommendation", "recommendation_reasoning"]:
            try:
                self.conn.execute(f"ALTER TABLE decisions ADD COLUMN {col} TEXT")
            except Exception:
                pass  # Column already exists
        self.conn.commit()

    # ------------------------------------------------------------------
    # Run ID (from 03b-transform-mappers.md line 1025-1026)
    # ------------------------------------------------------------------

    @property
    def current_run_id(self) -> str:
        if self._run_id is None:
            self._run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-") + uuid.uuid4().hex[:8]
        return self._run_id

    def set_run_id(self, run_id: str) -> None:
        self._run_id = run_id

    # ------------------------------------------------------------------
    # Decision ID (from 03b-transform-mappers.md line 1029-1030)
    # ------------------------------------------------------------------

    def next_decision_id(self) -> str:
        self._decision_counter += 1
        return f"D{self._decision_counter:04d}"

    def _max_decision_number(self) -> int:
        """Read the highest existing decision number from the DB so new IDs
        don't collide with decisions from a previous session."""
        row = self.conn.execute(
            "SELECT MAX(CAST(SUBSTR(decision_id, 2) AS INTEGER)) AS n FROM decisions"
        ).fetchone()
        return row["n"] or 0

    # ------------------------------------------------------------------
    # Object CRUD
    # ------------------------------------------------------------------

    def upsert_object(self, obj: MigrationObject) -> None:
        """Insert or update a canonical migration object.
        (from 01-data-representation.md lines 122-128)
        """
        now = _now()
        data_json = obj.model_dump_json()
        object_type = self._object_type_for(obj)
        location_id = getattr(obj, "location_id", None)
        self.conn.execute(
            """
            INSERT INTO objects (canonical_id, object_type, status, location_id,
                                 webex_id, batch, tier, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(canonical_id) DO UPDATE SET
                object_type = excluded.object_type,
                status = excluded.status,
                location_id = excluded.location_id,
                webex_id = excluded.webex_id,
                batch = excluded.batch,
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (
                obj.canonical_id,
                object_type,
                obj.status.value,
                location_id,
                obj.webex_id,
                obj.batch,
                None,  # tier set by planner
                data_json,
                now,
                now,
            ),
        )
        self.conn.commit()

    def get_object(self, canonical_id: str) -> dict[str, Any] | None:
        """Get a single object by canonical_id.
        (from 03b-transform-mappers.md line 1008-1009)
        """
        row = self.conn.execute(
            "SELECT data FROM objects WHERE canonical_id = ?", (canonical_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["data"])

    def get_object_typed(self, canonical_id: str) -> MigrationObject | None:
        """Get a single object deserialized into its Pydantic type."""
        row = self.conn.execute(
            "SELECT object_type, data FROM objects WHERE canonical_id = ?",
            (canonical_id,),
        ).fetchone()
        if row is None:
            return None
        return self._deserialize(row["object_type"], row["data"])

    def get_objects(self, object_type: str) -> list[dict[str, Any]]:
        """Get all objects of a given type as dicts.
        (from 03b-transform-mappers.md line 1005-1006)
        """
        rows = self.conn.execute(
            "SELECT data FROM objects WHERE object_type = ?", (object_type,)
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def query_by_type(self, object_type: str, status: str | None = None) -> list[MigrationObject]:
        """Query objects by type, optionally filtered by status.
        (from 01-data-representation.md line 130-131)
        """
        if status:
            rows = self.conn.execute(
                "SELECT object_type, data FROM objects WHERE object_type = ? AND status = ?",
                (object_type, status),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT object_type, data FROM objects WHERE object_type = ?",
                (object_type,),
            ).fetchall()
        return [self._deserialize(r["object_type"], r["data"]) for r in rows]

    def query_by_status(self, status: str) -> list[MigrationObject]:
        """Query all objects with a given status."""
        rows = self.conn.execute(
            "SELECT object_type, data FROM objects WHERE status = ?", (status,)
        ).fetchall()
        return [self._deserialize(r["object_type"], r["data"]) for r in rows]

    def count_by_type(self, object_type: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM objects WHERE object_type = ?", (object_type,)
        ).fetchone()
        return row["cnt"]

    # ------------------------------------------------------------------
    # Cross-references
    # ------------------------------------------------------------------

    def add_cross_ref(
        self,
        from_id: str,
        to_id: str,
        relationship: str,
        ordinal: int | None = None,
    ) -> None:
        """Add a cross-reference between two objects.
        (from 01-data-representation.md lines 50-61)
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO cross_refs (from_id, to_id, relationship, ordinal)
            VALUES (?, ?, ?, ?)
            """,
            (from_id, to_id, relationship, ordinal),
        )
        self.conn.commit()

    def find_cross_refs(self, canonical_id: str, relationship: str) -> list[str]:
        """Find all target IDs for a source + relationship.
        (from 01-data-representation.md lines 133-135)
        """
        rows = self.conn.execute(
            "SELECT to_id FROM cross_refs WHERE from_id = ? AND relationship = ?",
            (canonical_id, relationship),
        ).fetchall()
        return [r["to_id"] for r in rows]

    def get_cross_refs(
        self,
        from_id: str | None = None,
        to_id: str | None = None,
        relationship: str | None = None,
    ) -> list[dict[str, Any]]:
        """Flexible cross-ref query with optional filters.
        (from 03b-transform-mappers.md lines 1014-1016)
        """
        clauses: list[str] = []
        params: list[Any] = []
        if from_id is not None:
            clauses.append("from_id = ?")
            params.append(from_id)
        if to_id is not None:
            clauses.append("to_id = ?")
            params.append(to_id)
        if relationship is not None:
            clauses.append("relationship = ?")
            params.append(relationship)
        where = " AND ".join(clauses) if clauses else "1=1"
        rows = self.conn.execute(
            f"SELECT from_id, to_id, relationship, ordinal FROM cross_refs WHERE {where}",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def get_cross_ref_targets(self, from_id: str, relationship: str) -> list[str]:
        """Get all target IDs for a given source and relationship type.
        (from 03b-transform-mappers.md lines 1018-1019)
        """
        return self.find_cross_refs(from_id, relationship)

    def resolve_chain(self, start_id: str, *relationships: str) -> str | None:
        """Follow a chain of cross-refs to reach a final target.
        (from 03b-transform-mappers.md lines 1021-1023)

        Example: resolve_chain(dn_id, 'device_has_dn', 'device_in_pool', 'device_pool_to_location')
        """
        current = start_id
        for rel in relationships:
            targets = self.find_cross_refs(current, rel)
            if not targets:
                return None
            current = targets[0]
        return current

    def clear_cross_refs(self) -> None:
        """Delete all cross-refs for rebuild during normalization pass 2.
        (from 07-idempotency-resumability.md lines 183-187)
        """
        self.conn.execute("DELETE FROM cross_refs")
        self.conn.commit()

    # ------------------------------------------------------------------
    # Cleanup (for pipeline re-run safety)
    # ------------------------------------------------------------------

    def clear_all(self) -> dict[str, int]:
        """Delete all data from every table in FK-safe order. Returns counts per table."""
        counts: dict[str, int] = {}
        for table in [
            "plan_edges", "plan_operations", "merge_log",
            "decisions", "journal", "cross_refs", "objects",
        ]:
            cursor = self.conn.execute(f"DELETE FROM {table}")  # noqa: S608
            counts[table] = cursor.rowcount
        self.conn.commit()
        return counts

    def clear_journal(self) -> int:
        """Delete all journal entries. Returns count deleted."""
        cursor = self.conn.execute("DELETE FROM journal")
        self.conn.commit()
        return cursor.rowcount

    def clear_objects(self) -> int:
        """Delete all objects. Must clear cross_refs and journal first (FK constraints)."""
        cursor = self.conn.execute("DELETE FROM objects")
        self.conn.commit()
        return cursor.rowcount

    def clear_objects_by_types(self, types: list[str]) -> int:
        """Delete objects of specific resource types. Returns count deleted."""
        if not types:
            return 0
        placeholders = ",".join("?" for _ in types)
        cursor = self.conn.execute(
            f"DELETE FROM objects WHERE resource_type IN ({placeholders})", types
        )
        self.conn.commit()
        return cursor.rowcount

    def clear_decisions_by_source(self, source: str) -> int:
        """Delete decisions from a specific source (e.g. 'mapper', 'analyzer'). Returns count deleted."""
        cursor = self.conn.execute("DELETE FROM decisions WHERE source = ?", (source,))
        self.conn.commit()
        return cursor.rowcount

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def save_decision(self, decision: dict[str, Any]) -> None:
        """Insert or update a decision (upsert by fingerprint).
        (from 01-data-representation.md lines 63-77)

        On fingerprint conflict the existing ``decision_id`` is preserved
        and the incoming ID is discarded.  This matches the merge algorithm
        in 07-idempotency-resumability.md: existing decisions keep their
        identity across re-analysis runs.
        """
        self.conn.execute(
            """
            INSERT INTO decisions (decision_id, type, severity, summary, context,
                                   options, chosen_option, resolved_at, resolved_by,
                                   fingerprint, run_id,
                                   recommendation, recommendation_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                type = excluded.type,
                severity = excluded.severity,
                summary = excluded.summary,
                context = excluded.context,
                options = excluded.options,
                run_id = excluded.run_id,
                recommendation = excluded.recommendation,
                recommendation_reasoning = excluded.recommendation_reasoning
            """,
            (
                decision["decision_id"],
                decision["type"],
                decision["severity"],
                decision["summary"],
                json.dumps(decision.get("context", {})),
                json.dumps(decision.get("options", [])),
                decision.get("chosen_option"),
                decision.get("resolved_at"),
                decision.get("resolved_by"),
                decision["fingerprint"],
                decision.get("run_id", self.current_run_id),
                decision.get("recommendation"),
                decision.get("recommendation_reasoning"),
            ),
        )
        self.conn.commit()

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

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM decisions WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        if row is None:
            return None
        return self._decision_row_to_dict(row)

    def get_all_decisions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM decisions").fetchall()
        return [self._decision_row_to_dict(r) for r in rows]

    def resolve_decision(
        self, decision_id: str, chosen_option: str, resolved_by: str = "user"
    ) -> None:
        self.conn.execute(
            """
            UPDATE decisions SET chosen_option = ?, resolved_at = ?, resolved_by = ?
            WHERE decision_id = ?
            """,
            (chosen_option, _now(), resolved_by, decision_id),
        )
        self.conn.commit()

    def update_recommendation(self, decision_id: str, recommendation: str | None,
                              recommendation_reasoning: str | None) -> None:
        """Update recommendation fields on an existing decision."""
        self.conn.execute(
            "UPDATE decisions SET recommendation = ?, recommendation_reasoning = ? "
            "WHERE decision_id = ?",
            (recommendation, recommendation_reasoning, decision_id),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Decision merge (from 07-idempotency-resumability.md lines 66-120)
    # ------------------------------------------------------------------

    def merge_decisions(
        self, new_decisions: list[dict[str, Any]],
        decision_types: list[str] | None = None,
        stage: str = "analyze",
    ) -> dict[str, int]:
        """Three-way merge of new analysis results with existing decisions.

        On re-analysis, matches new decisions against existing by fingerprint:
        - Fingerprint in both: keep existing (preserve resolution if resolved)
        - Fingerprint only in new: insert as new decision
        - Fingerprint only in old: mark stale

        If ``decision_types`` is provided, only existing decisions of those
        types are considered for the merge.  This prevents preflight from
        stale-marking analyzer decisions (from 05a-preflight-checks.md
        lines 920-929).

        Returns dict with counts: kept, updated, new, stale, invalidated.
        Logs each action to the merge_log table.

        (from 07-idempotency-resumability.md lines 66-120)
        """
        existing_rows = self.get_all_decisions()
        existing_by_fp: dict[str, dict[str, Any]] = {}
        for d in existing_rows:
            fp = d.get("fingerprint", "")
            # Skip already-stale decisions
            if d.get("chosen_option") == "__stale__":
                continue
            # Scope to specific decision types if provided
            if decision_types is not None and d.get("type") not in decision_types:
                continue
            existing_by_fp[fp] = d

        new_by_fp: dict[str, dict[str, Any]] = {}
        for d in new_decisions:
            fp = d.get("fingerprint", "")
            new_by_fp[fp] = d

        result = {"kept": 0, "updated": 0, "new": 0, "stale": 0, "invalidated": 0}

        existing_fps = set(existing_by_fp.keys())
        new_fps = set(new_by_fp.keys())

        # Case 1: Fingerprint in both old and new — condition still exists
        for fp in existing_fps & new_fps:
            old = existing_by_fp[fp]
            new = new_by_fp[fp]
            if old.get("chosen_option") is not None:
                # Resolved decision, same fingerprint → keep resolution
                # Update display-only fields (summary, options, context)
                # while preserving chosen_option, resolved_at, resolved_by
                self.conn.execute(
                    """UPDATE decisions SET context = ?, summary = ?,
                       options = ?, run_id = ?,
                       recommendation = ?, recommendation_reasoning = ?
                       WHERE decision_id = ?""",
                    (
                        json.dumps(new.get("context", {})),
                        new.get("summary", old.get("summary", "")),
                        json.dumps(new.get("options", [])),
                        new.get("run_id", self.current_run_id),
                        new.get("recommendation"),
                        new.get("recommendation_reasoning"),
                        old["decision_id"],
                    ),
                )
                self.add_merge_log(
                    stage, "kept", "decision", old["decision_id"],
                    {"reason": "resolved, fingerprint unchanged"},
                )
                result["kept"] += 1
            else:
                # Pending decision, same fingerprint → update context
                self.conn.execute(
                    """UPDATE decisions SET context = ?, summary = ?,
                       severity = ?, options = ?, run_id = ?,
                       recommendation = ?, recommendation_reasoning = ?
                       WHERE decision_id = ?""",
                    (
                        json.dumps(new.get("context", {})),
                        new.get("summary", old.get("summary", "")),
                        new.get("severity", old.get("severity", "")),
                        json.dumps(new.get("options", [])),
                        new.get("run_id", self.current_run_id),
                        new.get("recommendation"),
                        new.get("recommendation_reasoning"),
                        old["decision_id"],
                    ),
                )
                self.add_merge_log(
                    stage, "updated", "decision", old["decision_id"],
                    {"reason": "pending, context updated"},
                )
                result["updated"] += 1

        # Case 2: Fingerprint only in new — new decision
        for fp in new_fps - existing_fps:
            self.save_decision(new_by_fp[fp])
            new_id = new_by_fp[fp].get("decision_id", "?")
            self.add_merge_log(
                stage, "new", "decision", new_id,
                {"reason": "new conflict detected"},
            )
            result["new"] += 1

        # Case 3: Fingerprint only in old — condition gone
        for fp in existing_fps - new_fps:
            old = existing_by_fp[fp]
            old_id = old["decision_id"]
            if old.get("chosen_option") is not None:
                # Was resolved, now irrelevant
                self.conn.execute(
                    """UPDATE decisions SET chosen_option = '__stale__',
                       resolved_by = 'stale' WHERE decision_id = ?""",
                    (old_id,),
                )
                self.add_merge_log(
                    stage, "invalidated", "decision", old_id,
                    {"reason": "resolved decision no longer relevant"},
                )
                result["invalidated"] += 1
            else:
                self.conn.execute(
                    """UPDATE decisions SET chosen_option = '__stale__',
                       resolved_by = 'stale' WHERE decision_id = ?""",
                    (old_id,),
                )
                self.add_merge_log(
                    stage, "stale", "decision", old_id,
                    {"reason": "condition no longer exists"},
                )
                result["stale"] += 1

        self.conn.commit()
        return result

    # ------------------------------------------------------------------
    # Journal
    # ------------------------------------------------------------------

    def add_journal_entry(
        self,
        entry_type: str,
        canonical_id: str,
        resource_type: str,
        request: dict[str, Any],
        response: dict[str, Any] | None = None,
        pre_state: dict[str, Any] | None = None,
    ) -> None:
        """Append to the execution journal.
        (from 01-data-representation.md lines 79-90)
        """
        self.conn.execute(
            """
            INSERT INTO journal (timestamp, entry_type, canonical_id, resource_type,
                                 request, response, pre_state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                entry_type,
                canonical_id,
                resource_type,
                json.dumps(request),
                json.dumps(response) if response else None,
                json.dumps(pre_state) if pre_state else None,
            ),
        )
        self.conn.commit()

    def get_journal_count(self, entry_type: str | None = None) -> int:
        """Count journal entries, optionally filtered by entry_type."""
        if entry_type:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM journal WHERE entry_type = ?",
                (entry_type,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM journal"
            ).fetchone()
        return row["cnt"]

    def get_journal_entries(
        self,
        entry_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get journal entries, optionally filtered by entry_type.

        Returns list of dicts with keys: entry_id, timestamp, entry_type,
        canonical_id, resource_type, request, response, pre_state.
        """
        if entry_type:
            sql = "SELECT * FROM journal WHERE entry_type = ?"
            params: tuple[Any, ...] = (entry_type,)
        else:
            sql = "SELECT * FROM journal"
            params = ()
        if limit:
            sql += " LIMIT ?"
            params = (*params, limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Merge log
    # ------------------------------------------------------------------

    def add_merge_log(
        self,
        stage: str,
        action: str,
        target_type: str,
        target_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a merge operation.
        (from 07-idempotency-resumability.md lines 209-218)
        """
        self.conn.execute(
            """
            INSERT INTO merge_log (timestamp, stage, run_id, action, target_type,
                                   target_id, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                stage,
                self.current_run_id,
                action,
                target_type,
                target_id,
                json.dumps(details) if details else None,
            ),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _object_type_for(obj: MigrationObject) -> str:
        """Derive the object_type string from a Pydantic model class (O(1) lookup).

        For canonical subtypes (CanonicalUser, CanonicalDevice, etc.), uses the
        class→type registry. For base MigrationObject instances (intermediate types
        like device_pool, css, partition), extracts the type from the canonical_id
        prefix (e.g., "device_pool:DP-HQ" → "device_pool").
        """
        registered = CANONICAL_CLASS_TO_TYPE.get(type(obj))
        if registered is not None:
            return registered
        # Intermediate types use canonical_id prefix convention: "type:name"
        if type(obj) is MigrationObject and ":" in obj.canonical_id:
            return obj.canonical_id.split(":")[0]
        return obj.__class__.__name__.lower()

    @staticmethod
    def _deserialize(object_type: str, data_json: str) -> MigrationObject:
        """Deserialize JSON data into the correct Pydantic type."""
        cls = CANONICAL_TYPE_REGISTRY.get(object_type, MigrationObject)
        return cls.model_validate_json(data_json)

    @staticmethod
    def _decision_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["context"] = json.loads(d["context"]) if d["context"] else {}
        d["options"] = json.loads(d["options"]) if d["options"] else []
        return d
