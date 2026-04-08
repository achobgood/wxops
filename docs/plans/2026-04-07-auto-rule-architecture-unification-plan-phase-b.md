# Phase B — CLI Integration

> **Parent plan:** [2026-04-07-auto-rule-architecture-unification-plan.md](2026-04-07-auto-rule-architecture-unification-plan.md)
> **Previous phase:** [Phase A — Foundations](2026-04-07-auto-rule-architecture-unification-plan-phase-a.md)
> **Source-of-truth spec:** `docs/superpowers/specs/2026-04-07-auto-rule-architecture-unification-design.md`

Phase B wires the new architecture into the Typer CLI. At the start of Phase B, the `cucm.py decide --apply-auto` and `decisions --export-review` branches still call the old (now-broken) `classify_decisions(store)` single-arg signature. Two existing test files are temporarily broken:

- `tests/migration/test_decision_cli.py` — tests exercise the CLI and break because `classify_decisions` now requires `config`, and the legacy `resolved_by="auto_apply"` assertion will flip to `"auto_rule"`.
- (Nothing else — `tests/migration/transform/test_decision_classify.py` was retired in Task 7.)

**By the end of Phase B, the full `tests/migration/` suite MUST pass.** Phase C only starts after a clean full-suite run.

## Spec-test inventory for Phase B

**In `tests/migration/test_decision_cli.py` (existing, modify + append):**
- Update `test_resolved_by_auto_apply` → assert `resolved_by == "auto_rule"`
- Update `test_resolves_only_auto_decisions` → seed data accounting for the new `is_on_incompatible_device` default rule
- New: `test_decide_apply_auto_runs_config_rules`
- New: `test_decide_apply_auto_picks_up_config_edits`
- New: `test_decide_apply_auto_runs_enrichment`
- New: `test_existing_project_without_new_default_rule_still_runs`
- New: `test_export_review_threads_config_to_classify_decisions`

**In `tests/migration/test_cucm_cli.py` (existing, append class):**
- New class `TestConfigReset` with 5 tests:
  - `test_config_reset_auto_rules_restores_defaults`
  - `test_config_reset_preserves_other_keys`
  - `test_config_reset_refuses_unknown_key`
  - `test_config_reset_refuses_without_key`
  - `test_config_reset_confirmation_prompt`

---

## Task 9: Update `decisions --export-review` CLI branch

**Files:**
- Modify: `src/wxcli/commands/cucm.py` (the `decisions` command's `--export-review` branch; today calls `classify_decisions(store)` at line 1130 and `generate_decision_review(store, project_id)` at line 1124)
- Test: `tests/migration/test_decision_cli.py` (existing `TestExportReview` class, may need minor adjustments to the seeded data so the new default MISSING_DATA rule doesn't unexpectedly fire)

**Why:** This is the smaller of the two CLI branches to update — it only threads `config` through to `classify_decisions` and `generate_decision_review`. The behavior change is that the auto_apply section in the markdown review file now reflects the project's actual `auto_rules` config (including any custom rules), not the hardcoded 3 cases.

**Important fixture prep note (read before touching any tests in this phase):** the existing `_seed_decisions` helper at `tests/migration/test_decision_cli.py:29-70` seeds D004 (`DEVICE_FIRMWARE_CONVERTIBLE`) with options `[{"id": "accept", ...}, {"id": "skip", ...}]`. Under the new default rules introduced in Phase A Task 5, the `DEVICE_FIRMWARE_CONVERTIBLE` default rule has `choice="convert"` — which fails option validation against D004's options because `"convert"` is not in `{"accept", "skip"}`. Left unfixed, D004 stays pending instead of being auto-applied, which breaks both the existing `TestExportReview` assertions (counts) and Task 10's new count expectations. Step 0 below fixes the fixture so the rest of the phase's assertion math holds.

- [ ] **Step 0: Fixture prep — update `_seed_decisions` D004 options**

Edit `tests/migration/test_decision_cli.py`. Find the `_save("D004", ...)` call (around line 66) and change its options list from `[{"id": "accept", ...}, {"id": "skip", ...}]` to `[{"id": "convert", ...}, {"id": "skip", ...}]`:

```python
    # Auto-apply: firmware convertible (matches new DEVICE_FIRMWARE_CONVERTIBLE default rule)
    _save("D004", "DEVICE_FIRMWARE_CONVERTIBLE", "MEDIUM", "7841 can convert",
          {"device_name": "SEP112233", "model": "7841"},
          [{"id": "convert", "label": "Convert"}, {"id": "skip", "label": "Skip"}])
```

The only change is the option `id` (`"accept"` → `"convert"`). The label stays "Convert". The comment is updated from "Needs-input" to "Auto-apply" because with the new default rules, D004 becomes auto-applied.

Run a quick sanity check to confirm the edit took:

```bash
grep -n '"id": "convert"' tests/migration/test_decision_cli.py
```

Expected: one hit on the D004 line inside `_seed_decisions`.

This fixture edit does NOT get its own commit — it's bundled into the Task 9 commit below with the `--export-review` CLI update. That keeps the "fixture matches new default rules" change coupled to the "CLI threads config" change it enables.

**Post-fix expected behavior for the existing `TestExportReview` tests** (which do NOT run enrichment because `--export-review` has no enrichment call):
- D001 `DEVICE_INCOMPATIBLE` → matches default rule (`choice="skip"` valid) → **auto**
- D002 `MISSING_DATA` on `device:CSF001` → needs `is_on_incompatible_device` but enrichment didn't run → **pending**
- D003 `WORKSPACE_LICENSE_TIER` → no rule → **pending**
- D004 `DEVICE_FIRMWARE_CONVERTIBLE` → matches default rule (`choice="convert"` now valid after fixture fix) → **auto**

Auto = 2 (D001, D004). Needs = 2 (D002, D003). That matches the existing assertions `assert "Auto-apply: 2 decisions"` and `assert "Needs input: 2 decisions"` — no existing TestExportReview test needs an assertion update.

- [ ] **Step 1: Write the new integration test first**

Append this test class to `tests/migration/test_decision_cli.py` at the end of the file (after the existing `TestApplyAuto` class):

```python
class TestExportReviewConfigThreading:
    """--export-review must load config.json and thread it through to
    classify_decisions and generate_decision_review, so custom auto_rules
    show up in the markdown review file's Auto-Apply section."""

    def test_export_review_honors_custom_auto_rule(self, tmp_migrations_dir):
        _init_project()

        # Edit config.json to add a custom rule matching DN_AMBIGUOUS
        # decisions with 3-digit DNs.
        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 3},
            "choice": "extension_only",
            "reason": "3-digit extensions are internal",
        })
        config_path.write_text(json.dumps(config, indent=2))

        # Seed one DN_AMBIGUOUS decision with dn_length=3.
        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_DN_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DN_01",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "3-digit DN ambiguous",
            "context": {"dn_length": 3, "dn": "101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app,
            ["decisions", "--export-review", "-o", "json", "-p", "test-project"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)

        auto_ids = {d["decision_id"] for d in data["auto_apply"]}
        assert "D_DN_01" in auto_ids, (
            f"Custom auto_rules rule was not applied by --export-review. "
            f"auto_apply: {data['auto_apply']}"
        )

    def test_export_review_custom_reason_in_markdown(self, tmp_migrations_dir):
        """The custom rule's `reason` must appear in the rendered markdown."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 3},
            "choice": "extension_only",
            "reason": "3-digit extensions are internal per the dial plan",
        })
        config_path.write_text(json.dumps(config, indent=2))

        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_DN_02").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DN_02",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "3-digit DN ambiguous",
            "context": {"dn_length": 3, "dn": "101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        runner.invoke(app, ["decisions", "--export-review", "-p", "test-project"])

        review_path = project_dir / "exports" / "decision-review.md"
        md = review_path.read_text()
        assert "3-digit extensions are internal per the dial plan" in md
```

- [ ] **Step 2: Run the failing tests**

```bash
python3.11 -m pytest tests/migration/test_decision_cli.py::TestExportReviewConfigThreading -v
```

Expected: FAIL. The current CLI branch calls `classify_decisions(store)` (one arg), which will raise `TypeError` against the new signature. The existing `TestExportReview` tests will also fail for the same reason.

- [ ] **Step 3: Update the CLI branch to thread `config`**

Edit `src/wxcli/commands/cucm.py`. Find the `--export-review` block inside the `decisions` command (around line 1115-1144). Update it:

```python
        # --export-review: generate markdown review file + optional JSON
        if export_review:
            import json as json_mod
            from wxcli.migration.transform.decisions import (
                classify_decisions, generate_decision_review,
            )
            project_id = project_dir.name if hasattr(project_dir, "name") else str(project_dir).split("/")[-1]

            # Load config so custom auto_rules in config.json are honored.
            config = load_config(project_dir)

            # Always write the markdown file for admin offline review
            content = generate_decision_review(store, project_id, config)
            exports_dir = project_dir / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            review_path = exports_dir / "decision-review.md"
            review_path.write_text(content)

            auto, needs = classify_decisions(store, config)

            if output == "json":
                # JSON output for agent consumption — structured data
                data = {
                    "review_file": str(review_path),
                    "auto_apply": [_serialize_decision(d) for d in auto],
                    "needs_input": [_serialize_decision(d) for d in needs],
                }
                typer.echo(json_mod.dumps(data, indent=2))
            else:
                console.print(f"[green]Decision review written to:[/green] {review_path}")
                console.print(f"  Auto-apply: {len(auto)} decisions")
                console.print(f"  Needs input: {len(needs)} decisions")
            return
```

Only two lines changed: `config = load_config(project_dir)` is added, and both `generate_decision_review(store, project_id)` and `classify_decisions(store)` gain the `config` argument.

- [ ] **Step 4: Verify existing `TestExportReview` tests still pass**

```bash
python3.11 -m pytest tests/migration/test_decision_cli.py::TestExportReview -v
```

Expected: all 6 existing `TestExportReview` tests PASS with zero assertion updates. Trace (with the Step 0 fixture fix applied):

- D001 `DEVICE_INCOMPATIBLE` → default rule matches (`choice="skip"` valid against D001's options `[skip, manual]`) → **auto**
- D002 `MISSING_DATA` on `device:CSF001` → rule `{is_on_incompatible_device: true}` would match IF enrichment ran, but `decisions --export-review` does NOT call `enrich_cross_decision_context` (enrichment is only called inside `AnalysisPipeline.run()` and inside Phase B Task 10's `decide --apply-auto` rewrite) → field is absent → rule does not match → **pending**
- D003 `WORKSPACE_LICENSE_TIER` → no matching rule → **pending**
- D004 `DEVICE_FIRMWARE_CONVERTIBLE` → default rule matches (`choice="convert"` now valid against D004's updated options `[convert, skip]`) → **auto**

Auto = 2 (D001, D004). Needs = 2 (D002, D003). Matches the existing assertions:
- `test_prints_summary_counts` at line 85: `"Auto-apply: 2 decisions"` and `"Needs input: 2 decisions"` — unchanged, still passes.
- `test_json_output_has_structured_data` at line 92: `len(data["auto_apply"]) == 2` and `len(data["needs_input"]) == 2` — unchanged, still passes.
- `test_json_auto_apply_has_choice_and_reason` at line 109: asserts every auto_apply entry has `auto_choice` and `auto_reason` set. Preview auto-populates these keys, so still passes.
- `test_no_pending_decisions` at line 118: empty project seeds no decisions, so output is "Auto-apply: 0 decisions". Unaffected by the default-rule changes.
- `test_creates_markdown_file` and `test_json_includes_review_file_path`: structural, not count-based. Unaffected.

If any of these tests fail unexpectedly, the most likely cause is that the Step 0 fixture prep was not applied (D004 option IDs are still `accept`/`skip`, so the rule is option-validation-skipped and D004 stays pending). Re-run the Step 0 grep sanity check.

- [ ] **Step 5: Run the new integration tests**

```bash
python3.11 -m pytest tests/migration/test_decision_cli.py::TestExportReviewConfigThreading -v
```

Expected: 2 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/commands/cucm.py tests/migration/test_decision_cli.py
git commit -m "$(cat <<'EOF'
feat(cucm): thread config through decisions --export-review

The --export-review branch now loads config.json and passes it to
classify_decisions and generate_decision_review. Custom auto_rules in
a project's config.json show up in the markdown review file's
Auto-Apply section and in the JSON output.

Adds TestExportReviewConfigThreading with 2 tests (custom rule honored,
custom reason in markdown).

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Rewrite `decide --apply-auto` CLI branch

**Files:**
- Modify: `src/wxcli/commands/cucm.py` (the `decide` command's `if apply_auto:` branch, around lines 1246-1272)
- Test: `tests/migration/test_decision_cli.py` (update `TestApplyAuto.test_resolved_by_auto_apply`; add new tests to the same class or a new class)

**Why:** The `--apply-auto` branch is the other CLI caller of the old `classify_decisions(store)` signature. It also writes `resolved_by="auto_apply"` (the legacy marker we're dropping). After this task, the branch:
1. Loads `config` from disk.
2. Runs `enrich_cross_decision_context(store)` so newly-pending MISSING_DATA decisions get the `is_on_incompatible_device` field.
3. Calls `preview_auto_rules(store, config)` for the confirmation prompt.
4. Calls `apply_auto_rules(store, config)` to actually resolve.

The flag semantic becomes "re-apply current config auto-rules against pending decisions." Edits to `config.json` are picked up without re-running `analyze`.

- [ ] **Step 1: Update the old `TestApplyAuto` tests that assume the legacy marker**

Edit `tests/migration/test_decision_cli.py`. Find `TestApplyAuto.test_resolved_by_auto_apply` (around line 147). Rename it and update the assertion:

```python
    def test_resolved_by_auto_rule(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        store = MigrationStore(str(db_path))
        d1 = store.get_decision("D001")
        # Unified matcher writes the "auto_rule" marker, not the legacy "auto_apply".
        assert d1["resolved_by"] == "auto_rule"
        store.close()
```

Also review `test_resolves_only_auto_decisions` (around line 127). The seeded data contains:
- D001 `DEVICE_INCOMPATIBLE` — new default rule matches → auto-resolved to `skip`
- D002 `MISSING_DATA` with `_affected_objects=["device:CSF001"]` on the same device as D001 — now the enrichment step sets `is_on_incompatible_device=True`, AND the new default rule matches → auto-resolved to `skip`
- D003 `WORKSPACE_LICENSE_TIER` — no default rule → stays pending
- D004 `DEVICE_FIRMWARE_CONVERTIBLE` — new default rule matches → auto-resolved to `convert`

So after the rewrite, 3 decisions are auto-applied (D001, D002, D004), not 2. Update the assertion:

```python
    def test_resolves_only_auto_decisions(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        assert result.exit_code == 0
        # D001 (DEVICE_INCOMPATIBLE), D002 (MISSING_DATA on incompatible device
        # via enrichment), and D004 (DEVICE_FIRMWARE_CONVERTIBLE) all match
        # default auto-rules.
        assert "Auto-applied 3 decisions" in result.output

        # Verify: D001, D002, D004 resolved; D003 still pending.
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        store = MigrationStore(str(db_path))
        d1 = store.get_decision("D001")
        d2 = store.get_decision("D002")
        d3 = store.get_decision("D003")
        d4 = store.get_decision("D004")
        assert d1["chosen_option"] == "skip"
        assert d2["chosen_option"] == "skip"  # via is_on_incompatible_device
        assert d3["chosen_option"] is None     # needs-input, untouched
        assert d4["chosen_option"] == "convert"
        store.close()
```

- [ ] **Step 2: Add the new TestApplyAuto tests**

Append to the existing `TestApplyAuto` class (still in `tests/migration/test_decision_cli.py`):

```python
    def test_decide_apply_auto_runs_config_rules(self, tmp_migrations_dir):
        """--apply-auto runs the project's config auto_rules, not a
        hardcoded list."""
        _init_project()

        # Seed one decision that matches a custom rule.
        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 3},
            "choice": "extension_only",
            "reason": "3-digit extensions are internal",
        })
        config_path.write_text(json.dumps(config, indent=2))

        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_APPLY_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_APPLY_01",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "3-digit DN",
            "context": {"dn_length": 3, "dn": "101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        store = MigrationStore(str(db_path))
        d = store.get_decision("D_APPLY_01")
        assert d["chosen_option"] == "extension_only"
        assert d["resolved_by"] == "auto_rule"
        store.close()

    def test_decide_apply_auto_picks_up_config_edits(self, tmp_migrations_dir):
        """Editing config.json between runs must change what --apply-auto
        resolves — no need to re-run analyze."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        db_path = project_dir / "migration.db"

        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_EDIT_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_EDIT_01",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "5-digit DN",
            "context": {"dn_length": 5, "dn": "10101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        # First run: no matching rule → no resolution.
        result1 = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result1.exit_code == 0

        store = MigrationStore(str(db_path))
        assert store.get_decision("D_EDIT_01")["chosen_option"] is None
        store.close()

        # Edit config.json to add a rule that matches.
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 5},
            "choice": "extension_only",
            "reason": "5-digit internal plan",
        })
        config_path.write_text(json.dumps(config, indent=2))

        # Second run: edit is picked up, D_EDIT_01 resolves.
        result2 = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result2.exit_code == 0

        store = MigrationStore(str(db_path))
        assert store.get_decision("D_EDIT_01")["chosen_option"] == "extension_only"
        store.close()

    def test_decide_apply_auto_runs_enrichment(self, tmp_migrations_dir):
        """--apply-auto must run enrich_cross_decision_context so
        MISSING_DATA-on-incompatible decisions get the is_on_incompatible_device
        field before rules fire, even if analyze ran before enrichment
        was added."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))

        # Seed a DEVICE_INCOMPATIBLE + MISSING_DATA pair on the same device,
        # simulating a project whose analyze ran without enrichment.
        fp_di = hashlib.sha256(b"DEVICE_INCOMPATIBLE:D_DI_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DI_01",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Legacy device",
            "context": {"device_id": "phone:old", "_affected_objects": ["phone:old"]},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Replace"},
            ],
            "chosen_option": None,
            "fingerprint": fp_di,
            "run_id": "test",
        })
        fp_md = hashlib.sha256(b"MISSING_DATA:D_MD_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_MD_01",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:old missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:old",
                "missing_fields": ["mac"],
                # Deliberately no is_on_incompatible_device field.
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "fingerprint": fp_md,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        store = MigrationStore(str(db_path))
        # Both the DI and MD decisions are auto-resolved via default rules
        # (MD requires the enrichment step to have run first).
        assert store.get_decision("D_DI_01")["chosen_option"] == "skip"
        assert store.get_decision("D_MD_01")["chosen_option"] == "skip"
        store.close()

    def test_existing_project_without_new_default_rule_still_runs(
        self, tmp_migrations_dir
    ):
        """Backwards compat: a project whose config.json was seeded before
        the new MISSING_DATA default rule existed must still run without
        crashing. MISSING_DATA-on-incompatible decisions stay pending
        (not auto-resolved) because the rule isn't in the saved config."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"

        # Overwrite config.json with ONLY the old 7 defaults (no new rule).
        legacy_rules = [
            {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert"},
            {"type": "HOTDESK_DN_CONFLICT", "choice": "keep_primary"},
            {"type": "FORWARDING_LOSSY", "choice": "accept_loss"},
            {"type": "SNR_LOSSY", "choice": "accept_loss"},
            {"type": "BUTTON_UNMAPPABLE", "choice": "accept_loss"},
            {"type": "CALLING_PERMISSION_MISMATCH",
             "match": {"assigned_users_count": 0}, "choice": "skip"},
        ]
        config = json.loads(config_path.read_text())
        config["auto_rules"] = legacy_rules
        config_path.write_text(json.dumps(config, indent=2))

        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp_di = hashlib.sha256(b"DEVICE_INCOMPATIBLE:D_DI_L").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DI_L",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Legacy device",
            "context": {"device_id": "phone:old", "_affected_objects": ["phone:old"]},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Replace"},
            ],
            "chosen_option": None,
            "fingerprint": fp_di,
            "run_id": "test",
        })
        fp_md = hashlib.sha256(b"MISSING_DATA:D_MD_L").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_MD_L",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:old missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:old",
                "missing_fields": ["mac"],
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "fingerprint": fp_md,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        store = MigrationStore(str(db_path))
        # D_DI_L resolved via legacy DEVICE_INCOMPATIBLE rule.
        assert store.get_decision("D_DI_L")["chosen_option"] == "skip"
        # D_MD_L stays pending — legacy config has no rule for it.
        assert store.get_decision("D_MD_L")["chosen_option"] is None
        store.close()

    def test_decide_apply_auto_empty_store(self, tmp_migrations_dir):
        """Empty store: --apply-auto prints 'no pending' and exits 0."""
        _init_project()
        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0
        assert "No pending decisions" in result.output or "No auto-resolvable" in result.output
```

- [ ] **Step 2: Run the failing tests**

```bash
python3.11 -m pytest tests/migration/test_decision_cli.py::TestApplyAuto -v
```

Expected: all tests FAIL or error — the `classify_decisions(store)` single-arg signature in the old CLI branch body raises `TypeError`.

- [ ] **Step 3: Rewrite the `--apply-auto` branch**

Edit `src/wxcli/commands/cucm.py`. Find the `decide` command (around line 1229) and replace the entire `if apply_auto:` block body (around lines 1246-1272) with:

```python
        # --apply-auto: re-run config auto-rules against pending decisions.
        if apply_auto:
            from wxcli.migration.transform.analysis_pipeline import (
                enrich_cross_decision_context,
            )
            from wxcli.migration.transform.rules import (
                apply_auto_rules,
                preview_auto_rules,
            )

            config = load_config(project_dir)

            # Refresh cross-decision context so newly-pending decisions
            # get the is_on_incompatible_device field before rules fire.
            try:
                enrich_cross_decision_context(store)
            except Exception as exc:
                logger.warning("Cross-decision enrichment failed: %s", exc)

            # Preview what would resolve, for the confirmation prompt.
            preview = preview_auto_rules(store, config)
            if not preview:
                console.print("No pending decisions match current auto-rules.")
                return

            console.print(
                f"\n[bold]Auto-apply:[/bold] {len(preview)} decisions "
                f"match current rules\n"
            )
            by_type: dict[str, list[dict]] = {}
            for d in preview:
                by_type.setdefault(d.get("type", "UNKNOWN"), []).append(d)
            for t, decs in sorted(by_type.items()):
                chosen = decs[0].get("auto_choice", "")
                console.print(f"  {len(decs)} {t} → {chosen}")

            if not yes and not typer.confirm(
                f"\nApply {len(preview)} auto-resolved decisions?"
            ):
                console.print("Cancelled.")
                return

            resolved = apply_auto_rules(store, config)
            console.print(f"[green]Auto-applied {resolved} decisions.[/green]")
            return
```

**Important:** The rewritten branch calls `apply_auto_rules` with the same `config` that `preview_auto_rules` was called with. Both share `_iter_matching_resolutions` so they cannot drift — the `resolved` count will equal `len(preview)` unless another process mutated the store between the preview call and the apply call (not a concern for single-process CLI usage).

- [ ] **Step 4: Run the failing tests**

```bash
python3.11 -m pytest tests/migration/test_decision_cli.py::TestApplyAuto -v
```

Expected: all PASS (the existing 3 updated tests + the 5 new tests = 8 passing tests in `TestApplyAuto`).

If the existing `test_no_auto_decisions_found` fails (around line 157), it's because the "No auto-resolvable" message text changed. Update the assertion to match the new string: `"No pending decisions match current auto-rules."` or leave an `or` clause that accepts either string.

- [ ] **Step 5: Run the full `test_decision_cli.py` file**

```bash
python3.11 -m pytest tests/migration/test_decision_cli.py -v 2>&1 | tail -40
```

Expected: all PASS. The export-review tests from Task 9 and the apply-auto tests from Task 10 are both green.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/commands/cucm.py tests/migration/test_decision_cli.py
git commit -m "$(cat <<'EOF'
feat(cucm): rewrite decide --apply-auto to use unified matcher

Replaces the hardcoded classify_decisions(store) call with a preview +
apply flow:

  1. Load config.json
  2. Run enrich_cross_decision_context(store) so MD-on-incompatible
     decisions get the is_on_incompatible_device field lazily
  3. preview_auto_rules(store, config) → show what will resolve
  4. Confirm (unless --yes)
  5. apply_auto_rules(store, config) → actually resolve

Semantic: --apply-auto now means "re-apply current config auto-rules
against pending decisions." Edits to config.json are picked up without
re-running analyze. Custom rules work.

The resolved_by marker is now "auto_rule" (was "auto_apply") — the
unified matcher's canonical marker.

New tests:
- test_decide_apply_auto_runs_config_rules (custom rule honored)
- test_decide_apply_auto_picks_up_config_edits (live config reload)
- test_decide_apply_auto_runs_enrichment (MD-on-incompatible fires)
- test_existing_project_without_new_default_rule_still_runs (backcompat)
- test_decide_apply_auto_empty_store (empty-store edge case)

Updated:
- test_resolved_by_auto_apply → test_resolved_by_auto_rule
- test_resolves_only_auto_decisions (3 decisions, not 2)

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Add `wxcli cucm config reset <key>` subcommand (Bug G fix)

**Files:**
- Modify: `src/wxcli/commands/cucm.py` (add `config_reset` command in the CONFIG COMMANDS section near line 551)
- Modify: `src/wxcli/commands/cucm_config.py` (optional — nothing to change; `load_config`/`save_config` are unchanged)
- Test: `tests/migration/test_cucm_cli.py` (append `TestConfigReset` class near the existing `TestConfig` class at line 109)

**Why:** Bug G's fix per spec Approach I: keep `load_config()` literal (no runtime merge), and add a discoverable one-command path to restore a single config key from defaults without clobbering unrelated customizations. The command supports `auto_rules` from day one (the motivating use case) and works for any other key in `DEFAULT_CONFIG` without code changes.

- [ ] **Step 1: Write the failing tests**

Append to `tests/migration/test_cucm_cli.py` after the existing `TestConfig` class (around line 135):

```python
# ===================================================================
# CONFIG RESET
# ===================================================================


class TestConfigReset:
    """Tests for `wxcli cucm config reset <key>` (Bug G fix)."""

    def test_config_reset_auto_rules_restores_defaults(self, tmp_migrations_dir):
        """Removing a default rule then running `config reset auto_rules`
        restores the full default list."""
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES

        runner.invoke(app, ["init", "test-project"])

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"

        # Hand-edit to remove one default rule.
        config = json.loads(config_path.read_text())
        original_count = len(config["auto_rules"])
        config["auto_rules"] = config["auto_rules"][:-1]
        config_path.write_text(json.dumps(config, indent=2))
        assert len(json.loads(config_path.read_text())["auto_rules"]) == original_count - 1

        # Reset auto_rules to defaults.
        result = runner.invoke(
            app, ["config", "reset", "auto_rules", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        restored = json.loads(config_path.read_text())["auto_rules"]
        assert len(restored) == len(DEFAULT_AUTO_RULES)

    def test_config_reset_preserves_other_keys(self, tmp_migrations_dir):
        """Resetting one key must NOT touch other keys."""
        runner.invoke(app, ["init", "test-project"])
        runner.invoke(app, ["config", "set", "country_code", "+44"])

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        assert json.loads(config_path.read_text())["country_code"] == "+44"

        result = runner.invoke(
            app, ["config", "reset", "auto_rules", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        # Custom country_code must still be "+44" after reset.
        config = json.loads(config_path.read_text())
        assert config["country_code"] == "+44"

    def test_config_reset_refuses_unknown_key(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(
            app, ["config", "reset", "bogus_key", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 1
        # Error message should list valid keys.
        assert "auto_rules" in result.output
        assert "country_code" in result.output

    def test_config_reset_refuses_without_key(self, tmp_migrations_dir):
        """No key argument → Typer shows usage / exits non-zero."""
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["config", "reset", "-p", "test-project"])
        assert result.exit_code != 0

    def test_config_reset_confirmation_prompt(self, tmp_migrations_dir):
        """Without -y, the command prompts and aborts on 'n'."""
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES

        runner.invoke(app, ["init", "test-project"])

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"] = []
        config_path.write_text(json.dumps(config, indent=2))

        # Reply "n" to the confirmation prompt.
        result = runner.invoke(
            app,
            ["config", "reset", "auto_rules", "-p", "test-project"],
            input="n\n",
        )
        assert result.exit_code == 0  # Graceful abort, not an error.

        # auto_rules must still be empty (reset was cancelled).
        restored = json.loads(config_path.read_text())["auto_rules"]
        assert restored == []
```

- [ ] **Step 2: Run the failing tests**

```bash
python3.11 -m pytest tests/migration/test_cucm_cli.py::TestConfigReset -v
```

Expected: all FAIL — the `config reset` subcommand doesn't exist yet. Typer reports "No such command 'reset'".

- [ ] **Step 3: Add the `config_reset` command to `cucm.py`**

Edit `src/wxcli/commands/cucm.py`. Find the CONFIG COMMANDS section (lines 546-574) and append a new `config_reset` function after `config_show`:

```python
@config_app.command("reset")
def config_reset(
    key: str = typer.Argument(..., help="Config key to reset (e.g. auto_rules)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Reset a single config key to its DEFAULT_CONFIG value.

    Reads the current config.json, replaces just the named key with its
    default, and writes back. Other keys are preserved.

    Example:

        wxcli cucm config reset auto_rules -p my-project

    WARNING: For ``auto_rules``, reset clobbers any custom rules the
    operator added. Preserve custom rules by hand-editing config.json
    to append the new default instead of running reset.

    Refuses unknown keys with a list of valid keys.
    """
    import copy

    project_dir = _resolve_project_dir(project)

    if key not in DEFAULT_CONFIG:
        console.print(f"[red]Unknown config key:[/red] {key}")
        console.print("\nValid keys:")
        for k in sorted(DEFAULT_CONFIG):
            console.print(f"  {k}")
        raise typer.Exit(code=1)

    config = load_config(project_dir)
    current = config.get(key)
    default = DEFAULT_CONFIG[key]

    console.print(f"[bold]Reset config key:[/bold] {key}")
    console.print(f"  Current: {json.dumps(current)}")
    console.print(f"  Default: {json.dumps(default)}")

    if not yes:
        if not typer.confirm(f"\nReset '{key}' to default?"):
            console.print("Cancelled.")
            return

    config[key] = copy.deepcopy(default)
    save_config(project_dir, config)

    if isinstance(default, list):
        console.print(
            f"[green]Reset config key '{key}' to default "
            f"({len(default)} entries restored).[/green]"
        )
    else:
        console.print(f"[green]Reset config key '{key}' to default.[/green]")
```

**Note on imports:** The function needs `copy` — import it at function scope to avoid polluting the module import list. The file already imports `json` and `typer` at the top and has `DEFAULT_CONFIG`, `load_config`, `save_config` imported from `cucm_config` at line 31-36. No module-level import changes.

- [ ] **Step 4: Verify Typer registered the command**

```bash
python3.11 -c "from wxcli.commands.cucm import app; import typer; \
  from typer.testing import CliRunner; \
  r = CliRunner().invoke(app, ['config', 'reset', '--help']); \
  print(r.output)"
```

Expected: help output for the `reset` command listing `KEY`, `--yes`, `--project`. If Typer reports "No such command", the decorator didn't take effect — re-read the module and the add_typer wiring.

- [ ] **Step 5: Run the new tests**

```bash
python3.11 -m pytest tests/migration/test_cucm_cli.py::TestConfigReset -v
```

Expected: 5 PASS.

- [ ] **Step 6: Run the full `test_cucm_cli.py` to catch regressions**

```bash
python3.11 -m pytest tests/migration/test_cucm_cli.py -v 2>&1 | tail -30
```

Expected: all PASS (new + existing).

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/commands/cucm.py tests/migration/test_cucm_cli.py
git commit -m "$(cat <<'EOF'
feat(cucm): add config reset <key> subcommand (Bug G fix)

Adds `wxcli cucm config reset <key> [-y] [-p PROJECT]` which replaces a
single config key with its DEFAULT_CONFIG value, preserving other keys.
Refuses unknown keys with a helpful list of valid keys.

Motivating use case: operators who edit config.json to remove a default
auto_rule need a discoverable path to restore defaults without hand-
editing. Per the Bug G design decision (spec Approach I), `load_config`
stays literal (no runtime merge) — this reset command is the operator-
facing restoration path.

WARNING (also documented in the command help text): resetting auto_rules
clobbers any custom rules. Preserve custom rules by hand-editing
config.json to append the new default instead.

Tests: TestConfigReset with 5 cases (restore defaults, preserve other
keys, refuse unknown key, refuse without key, confirmation prompt abort).

Part of the auto-rule architecture unification (Bug G). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase B exit verification

Run the full migration test suite. Phase B is complete only when it's clean.

```bash
python3.11 -m pytest tests/migration/ 2>&1 | tail -40
```

Expected: all tests PASS. Counts should be the pre-Plan-2 baseline (1642) + ~25 new tests from Phase A + ~12 new tests from Phase B = ~1679+ passing. Actual numbers depend on how many legacy tests were deleted when `test_decision_classify.py` was retired in Task 7.

```bash
git log --oneline | head -15
```

Expected: 3 new commits from Phase B (Tasks 9, 10, 11) on top of the 8 Phase A commits = 11 total new commits beyond the pre-Plan-2 baseline.

```bash
grep -rn 'resolved_by=["'"'"']auto_apply["'"'"']' src/wxcli/migration/ src/wxcli/commands/cucm.py
```

Expected: empty (zero hits). If any file still writes `resolved_by="auto_apply"`, Phase B wasn't fully applied. Audit the remaining hits in Phase C (Task 12) before deleting the legacy marker from any filter code.

Phase B is complete. Proceed to [Phase C](2026-04-07-auto-rule-architecture-unification-plan-phase-c.md).
