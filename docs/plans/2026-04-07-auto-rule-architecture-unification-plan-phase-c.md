# Phase C — Cleanup, SKILL.md, Smoke Test

> **Parent plan:** [2026-04-07-auto-rule-architecture-unification-plan.md](2026-04-07-auto-rule-architecture-unification-plan.md)
> **Previous phases:** [Phase A — Foundations](2026-04-07-auto-rule-architecture-unification-plan-phase-a.md), [Phase B — CLI Integration](2026-04-07-auto-rule-architecture-unification-plan-phase-b.md)
> **Source-of-truth spec:** `docs/superpowers/specs/2026-04-07-auto-rule-architecture-unification-design.md`

Phase C closes out the work: the spec-mandated grep audit, SKILL.md Step 1c-fallback updates, a final full-suite regression check, and a manual smoke test on a real test project. No production code paths should change in Phase C beyond cleanup that the grep audit uncovers.

**Prerequisite:** Phase B exit verification must pass (full `tests/migration/` suite clean).

---

## Task 12: Grep audit for legacy `auto_apply` / `_check_auto_apply` references

**Files:**
- Read: every file in the repo (grep target)
- Modify: any file the audit surfaces that still references the legacy marker / function outside of stored-data backwards-compatibility

**Why:** The spec requires this audit before declaring Bug F cleanup complete. It catches any filter/report/audit code that still special-cases the legacy `"auto_apply"` marker and either updates it or documents it as intentionally backwards-compatible.

- [ ] **Step 1: Run the audit commands**

```bash
grep -rn "_check_auto_apply" tests/ src/wxcli/migration/ src/wxcli/commands/ \
    --include="*.py" || echo "clean"
```

Expected: `clean`. If any hit remains, Task 6 in Phase A was incomplete. Delete the residual reference and investigate why it survived.

```bash
grep -rn "auto_apply" tests/ src/wxcli/migration/ src/wxcli/commands/ \
    --include="*.py"
```

Expected hits (from the spec's analysis, all of which should be unchanged or intentionally legacy-compatible):
- `tests/migration/test_decision_cli.py` — local variable names like `auto, needs = classify_decisions(...)` and the dict key `"auto_apply"` in JSON payloads. These are DIFFERENT from the `resolved_by="auto_apply"` marker — they're the JSON structure of `--export-review --output json` output and the Python variable names. **Do NOT change these.** They're part of the stable CLI output contract and local variable scope.
- `tests/migration/transform/test_classify_decisions.py` — `auto, needs = classify_decisions(...)` local variable. Leave it.
- `src/wxcli/commands/cucm.py:1136` — the string `"auto_apply"` in the JSON output dict key under `--export-review -o json`. **Leave it.** It's the stable output contract — downstream agents/scripts parse this key.
- `src/wxcli/migration/advisory/CLAUDE.md:156` — comment about the advisor agent's internal terminology. Leave it.
- Any historical stored decision rows in test fixtures that still have `resolved_by="auto_apply"`. Leave those — they document the legacy behavior.

```bash
grep -rn 'resolved_by=["'"'"']auto_apply["'"'"']' src/wxcli/ --include="*.py"
```

Expected: `clean`. This is the narrow grep for the legacy MARKER being written by production code. Any hit here is a bug.

- [ ] **Step 2: Update filter/audit code (if any)**

If Step 1 surfaces any filter/report/audit code in `src/wxcli/` that filters on `resolved_by == "auto_apply"`, it needs to match both the legacy and new marker. Update it to:

```python
if d.get("resolved_by") in ("auto_rule", "auto_apply"):
    # ...
```

And add an inline comment: `# auto_apply is legacy (pre-2026-04-07); auto_rule is current`.

If none surface, skip this step.

- [ ] **Step 3: Document the output-contract `auto_apply` key**

The JSON output of `wxcli cucm decisions --export-review -o json` uses an `"auto_apply"` top-level key to group decisions that were auto-matched by rules. This is an intentional output-contract name — it is NOT the same thing as the legacy `resolved_by="auto_apply"` marker.

Add a clarifying comment near `cucm.py:1134-1138` inside the `--export-review` `-o json` branch:

```python
            if output == "json":
                # NOTE: The "auto_apply" key here is the JSON output-contract
                # name for "decisions matched by auto_rules config." It is
                # NOT the legacy `resolved_by="auto_apply"` marker (which
                # the unified matcher replaced with "auto_rule"). Downstream
                # parsers rely on the "auto_apply" key name — do not rename.
                data = {
                    "review_file": str(review_path),
                    "auto_apply": [_serialize_decision(d) for d in auto],
                    "needs_input": [_serialize_decision(d) for d in needs],
                }
```

- [ ] **Step 4: Re-run the full suite**

```bash
python3.11 -m pytest tests/migration/ 2>&1 | tail -20
```

Expected: all PASS. The comment-only edit should not change any test outcome.

- [ ] **Step 5: Commit (only if files changed)**

If Steps 2 or 3 changed any file:

```bash
git add src/wxcli/commands/cucm.py  # plus any other files touched
git commit -m "$(cat <<'EOF'
chore(migration): grep audit cleanup for legacy auto_apply references

Audits tests/ and src/wxcli/ for lingering references to _check_auto_apply
and resolved_by="auto_apply" after the unification. Adds a clarifying
comment in cucm.py's --export-review JSON branch distinguishing the
output-contract key name "auto_apply" from the (legacy) resolved_by
marker. Updates any filter/audit code that checks resolved_by to match
both "auto_rule" (current) and "auto_apply" (legacy) for backwards
compatibility with historical stored decisions.

Part of the auto-rule architecture unification (Bug F) wrap-up. See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

If no files changed, skip the commit — the audit itself is the deliverable.

---

## Task 13: SKILL.md — rewrite Step 1c-fallback "Group 1: Auto-apply" and step 3

**Files:**
- Modify: `.claude/skills/cucm-migrate/SKILL.md` (Step 1c-fallback subsection; current "Group 1: Auto-apply" is around line 214; numbered step 3 "Apply auto-resolvable decisions" is around line 269)

**Why:** The SKILL.md primary path (Step 1c) delegates to the migration-advisor agent, which reads the store at runtime and sees the new auto-applied decisions and the `is_on_incompatible_device` field automatically — no prompt changes required for the primary path. Only the **fallback** path (Step 1c-fallback, used when the advisor agent is unavailable) has static text listing the hardcoded 3 cases. That text is the only thing Phase C needs to update.

**Do NOT touch Step 1c (the primary path).** Do NOT touch `docs/runbooks/cucm-migration/` — that's Plan 3's territory.

- [ ] **Step 1: Read the current fallback text**

```bash
python3.11 -c "
import pathlib
p = pathlib.Path('.claude/skills/cucm-migrate/SKILL.md')
lines = p.read_text().splitlines()
# Print a stable context window around the 1c-fallback Group 1 block.
for i, line in enumerate(lines, 1):
    if 'Group 1: Auto-apply' in line or 'Apply auto-resolvable' in line:
        start = max(0, i - 3)
        end = min(len(lines), i + 20)
        print(f'--- window {start+1}:{end} ---')
        for j in range(start, end):
            print(f'{j+1:4}: {lines[j]}')
        print()
"
```

Record the exact line numbers. They drift over time — don't hardcode them in the edit.

- [ ] **Step 2: Replace "Group 1: Auto-apply (clear-cut decisions)" block**

Find the exact block in `SKILL.md` that starts with:
```
**Group 1: Auto-apply (clear-cut decisions)** — applied via `--apply-auto`:
```
And ends with the bullet:
```
- `CALLING_PERMISSION_MISMATCH` with 0 affected users → skip (orphaned profile)
```

Replace it with:

```
**Group 1: Auto-apply (matched by `auto_rules` config)** — applied via `--apply-auto`.
By default this covers 8 rule types: incompatible devices, convertible devices,
hotdesk DN conflicts, lossy forwarding, lossy SNR, unmappable buttons, orphaned
permission profiles (`assigned_users_count == 0`), and missing data on devices
that are already incompatible. Custom rules in `<project>/config.json` extend
this set. Edits to `config.json` are picked up the next time `--apply-auto`
runs — no need to re-run `analyze` first.
```

- [ ] **Step 3: Replace step 3 "Apply auto-resolvable decisions"**

Find the numbered step 3 in the Step 1c-fallback section. It currently reads (paraphrased):

```
3. **Apply auto-resolvable decisions:**
   After the admin has resolved all needs-input decisions, show what will be
   auto-applied (read from the Auto-Apply section of the review file):
   ```
   AUTO-APPLYING (N decisions — clear-cut):
     - N incompatible devices → skip (no MPP migration path)
     - N missing data on incompatible devices → skip
     - N orphaned permission profiles → skip
   ```
   Then apply:
   ```bash
   wxcli cucm decide --apply-auto -y -p <project>
   ```
```

Replace the entire numbered step with:

````
3. **Apply auto-resolvable decisions:**
   After the admin has resolved all needs-input decisions, show what will be
   auto-applied (read from the Auto-Apply section of the review file —
   the section reflects the project's current `auto_rules` config, including
   any custom rules):
   ```
   AUTO-APPLYING (N decisions — matched by current auto-rules):
     <count> <type> → <choice>
     ...
   ```
   Then apply:
   ```bash
   wxcli cucm decide --apply-auto -y -p <project>
   ```
   This re-runs the rules in `<project>/config.json` against any pending
   decisions and resolves matches. Safe to re-run.

   If the admin has hand-edited `config.json` and wants to restore the
   default rule set, run: `wxcli cucm config reset auto_rules -p <project>`.
   This restores defaults but clobbers any custom rules in `auto_rules`.
````

- [ ] **Step 4: Verify SKILL.md reads cleanly**

```bash
python3.11 -c "
import pathlib
txt = pathlib.Path('.claude/skills/cucm-migrate/SKILL.md').read_text()
# New text must be present.
assert 'Group 1: Auto-apply (matched by' in txt, 'Group 1 update missing'
assert 'matched by current auto-rules' in txt, 'Step 3 update missing'
assert 'wxcli cucm config reset auto_rules' in txt, 'config reset reference missing'
# Old bullets must be gone. The real SKILL.md text uses backticks around
# the decision type, so assert on the unique trailing phrase instead.
assert '0 affected users → skip (orphaned profile)' not in txt, \
    'Old CALLING_PERMISSION_MISMATCH bullet still present — update incomplete'
assert 'missing data on incompatible devices → skip' not in txt.lower(), \
    'Old MISSING_DATA bullet still present — update incomplete'
print('SKILL.md updated cleanly')
"
```

Expected: `SKILL.md updated cleanly`. If any assertion fails, re-open the file and fix the leftover text.

The two "must be gone" assertions target phrases that are unique to the fallback section's Group 1 block (verified against the pre-edit SKILL.md — no other occurrence in the file). They are reliable signals: if either is still present after the edit, the Group 1 block was not fully replaced. There is no risk of a false positive from Step 1c's primary path because the primary path delegates to the migration-advisor agent and does NOT list hardcoded decision-resolution bullets.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cucm-migrate/SKILL.md
git commit -m "$(cat <<'EOF'
docs(cucm-migrate): update SKILL.md Step 1c-fallback for unified auto-rules

Updates Step 1c-fallback (the static decision review path used when the
migration-advisor agent is unavailable) to reflect the unified
config-driven auto-rule architecture:

- "Group 1: Auto-apply" no longer lists a hardcoded 3 bullets. It now
  describes the 8 default rules and notes that custom rules in
  <project>/config.json extend the set.
- Numbered step 3 "Apply auto-resolvable decisions" describes the
  preview output as "matched by current auto-rules" and notes that
  config edits are picked up without re-running analyze.
- Adds a one-liner pointing at `wxcli cucm config reset auto_rules` as
  the path to restore defaults (with the clobber caveat).

Step 1c (the primary path that delegates to the migration-advisor
agent) is unchanged — the agent reads the store at runtime and sees
the new behavior automatically.

Wave 3 runbook rewrites under docs/runbooks/cucm-migration/ are Plan
3's responsibility — not touched here.

Part of the auto-rule architecture unification (Bug F). See
docs/plans/2026-04-07-auto-rule-architecture-unification-plan.md.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Final full-suite verification

**Files:**
- Verify: `tests/migration/` (full suite) + `tests/commands/` if that directory exists

- [ ] **Step 1: Run the full migration test suite**

```bash
python3.11 -m pytest tests/migration/ -v 2>&1 | tail -60
```

Expected: all PASS. No skipped tests beyond the pre-Plan-2 baseline.

- [ ] **Step 2: Run any repo-wide tests outside `tests/migration/` that touch the migration module**

```bash
python3.11 -m pytest tests/ -k "migration or cucm" 2>&1 | tail -20
```

Expected: all PASS. If any test outside `tests/migration/` fails because it imported from the old `_check_auto_apply` or the old `classify_decisions(store)` signature, fix it now (it was missed in the Phase A/B task coverage).

- [ ] **Step 3: Confirm the test count delta matches the plan**

Count new tests added by this plan:
- Phase A Task 1 (store): 3 tests
- Phase A Task 2 (enrichment): 7 tests
- Phase A Task 3 (pipeline wiring): 1 cascade test (+ 1 seeded helper test, may overlap)
- Phase A Task 4 (rules.py): 11 tests in `TestPreviewAutoRules`
- Phase A Task 5 (default rule): 1 test in `TestDefaultAutoRulesMissingDataEntry`
- Phase A Task 7 (classify_decisions): 6 tests (new file replaces the old `test_decision_classify.py` which had ~12 tests)
- Phase A Task 8 (field-alignment): 2-3 parametrized tests
- Phase B Task 9 (export-review): 2 tests
- Phase B Task 10 (apply-auto): 5 new tests + 2 updated
- Phase B Task 11 (config reset): 5 tests

Total new: ~42. Deleted (old test_decision_classify.py): ~12. Net: ~+30 tests. Baseline 1642 → expected ~1672.

```bash
python3.11 -m pytest tests/migration/ --collect-only -q 2>&1 | tail -5
```

The last lines print the collected count. Compare against the expected range. If it's lower than expected, some tests were skipped or a file didn't collect — investigate before declaring victory.

- [ ] **Step 4: No commit in this task**

Task 14 is verification only. Move to Task 15 (smoke test).

---

## Task 15: Manual smoke test against a real test project

**Files:**
- Verify: a test migration project under `~/.wxcli/migrations/` (create a scratch project for this task)

**Why:** Pytest covers the unit and CLI integration layers, but the spec mandates a manual smoke test against a real test project to verify the end-to-end operator flow — specifically, that edits to `config.json` are picked up by the next `decide --apply-auto` run without re-running `analyze`, and that `config reset auto_rules` restores defaults without clobbering unrelated keys.

This task is **manual**. The executor runs commands in a terminal and verifies outputs visually. The plan lists exact commands and expected outputs.

- [ ] **Step 1: Create a scratch test project**

```bash
wxcli cucm init phase2-smoke
```

Expected: `Initialized project 'phase2-smoke' at ~/.wxcli/migrations/phase2-smoke`.

If the project already exists from a prior run, delete it first:
```bash
rm -rf ~/.wxcli/migrations/phase2-smoke
wxcli cucm init phase2-smoke
```

- [ ] **Step 2: Seed a handful of decisions via Python**

Run this one-liner to seed 4 decisions directly into the test project's store (bypasses the full `discover/normalize/map/analyze` pipeline for speed):

```bash
python3.11 <<'PY'
import hashlib
from pathlib import Path
from wxcli.migration.store import MigrationStore

db = Path.home() / ".wxcli" / "migrations" / "phase2-smoke" / "migration.db"
store = MigrationStore(str(db))

def _save(did, dtype, ctx, opts):
    fp = hashlib.sha256(f"{dtype}:{did}".encode()).hexdigest()[:16]
    store.save_decision({
        "decision_id": did, "type": dtype, "severity": "MEDIUM",
        "summary": f"{dtype} {did}", "context": ctx, "options": opts,
        "chosen_option": None, "fingerprint": fp, "run_id": "smoke",
    })

# Device-incompatible phone (matches default rule).
_save("SMK001", "DEVICE_INCOMPATIBLE",
      {"device_id": "phone:legacy", "_affected_objects": ["phone:legacy"]},
      [{"id": "skip", "label": "Skip"}, {"id": "manual", "label": "Manual"}])

# MISSING_DATA on the same phone (will match after enrichment runs).
_save("SMK002", "MISSING_DATA",
      {"object_type": "device", "canonical_id": "phone:legacy",
       "missing_fields": ["mac"]},
      [{"id": "skip", "label": "Skip"},
       {"id": "provide_data", "label": "Provide"}])

# DN_AMBIGUOUS that NO default rule matches (will be the custom-rule test).
_save("SMK003", "DN_AMBIGUOUS",
      {"dn_length": 3, "dn": "101"},
      [{"id": "extension_only", "label": "Extension"},
       {"id": "skip", "label": "Skip"}])

# WORKSPACE_LICENSE_TIER — no rule, should stay pending.
_save("SMK004", "WORKSPACE_LICENSE_TIER",
      {"workspace_name": "Lobby"},
      [{"id": "workspace", "label": "Basic"},
       {"id": "professional", "label": "Professional"},
       {"id": "skip", "label": "Skip"}])

store.close()
print("Seeded 4 decisions into phase2-smoke project.")
PY
```

Expected: `Seeded 4 decisions into phase2-smoke project.`

- [ ] **Step 3: Run `decide --apply-auto` (first pass)**

```bash
wxcli cucm decide --apply-auto -y -p phase2-smoke
```

Expected output includes lines like:
```
Auto-apply: 2 decisions match current rules
  1 DEVICE_INCOMPATIBLE → skip
  1 MISSING_DATA → skip
Auto-applied 2 decisions.
```

SMK001 is auto-skipped by the DEVICE_INCOMPATIBLE default rule. SMK002 is auto-skipped by the new MISSING_DATA/is_on_incompatible_device default rule (via enrichment). SMK003 and SMK004 stay pending.

Verify:
```bash
wxcli cucm decisions --status pending -p phase2-smoke
```

Expected: 2 pending decisions — SMK003 and SMK004.

**If the output shows "No pending decisions match current auto-rules"** instead of the above, the enrichment step didn't fire. Investigate: was Task 3 (wiring) actually applied? Check `grep -n "enrich_cross_decision_context" src/wxcli/commands/cucm.py` — the `decide --apply-auto` branch must call it.

- [ ] **Step 4: Edit `config.json` to add a custom rule**

Open the project's config file in an editor:
```bash
${EDITOR:-nano} ~/.wxcli/migrations/phase2-smoke/config.json
```

In the `auto_rules` array, append this new rule (before the closing `]`):
```json
{
  "type": "DN_AMBIGUOUS",
  "match": {"dn_length_lte": 3},
  "choice": "extension_only",
  "reason": "Smoke test: 3-digit extensions are internal"
}
```

Save and close.

- [ ] **Step 5: Run `decide --apply-auto` again (picks up the config edit)**

```bash
wxcli cucm decide --apply-auto -y -p phase2-smoke
```

Expected: the new custom rule fires, and SMK003 is resolved. Output includes:
```
Auto-apply: 1 decisions match current rules
  1 DN_AMBIGUOUS → extension_only
Auto-applied 1 decisions.
```

Verify:
```bash
wxcli cucm decisions --status pending -p phase2-smoke
```

Expected: 1 pending decision — SMK004. SMK003 is now resolved with `extension_only`.

If SMK003 is still pending, the config edit wasn't picked up. That means `decide --apply-auto` isn't calling `load_config(project_dir)` — Task 10 wasn't fully applied.

- [ ] **Step 6: Test `wxcli cucm config reset`**

Set a custom country_code first:
```bash
wxcli cucm config set country_code "+44" -p phase2-smoke
```

Confirm it stuck:
```bash
wxcli cucm config show -p phase2-smoke | grep country_code
```

Expected: `country_code                   "+44"`.

Now run reset on `auto_rules`:
```bash
wxcli cucm config reset auto_rules -y -p phase2-smoke
```

Expected:
```
Reset config key: auto_rules
  Current: [... your custom rule plus 8 defaults ...]
  Default: [... 8 defaults ...]
Reset config key 'auto_rules' to default (8 entries restored).
```

Verify:
- `country_code` is still `"+44"`:
  ```bash
  wxcli cucm config show -p phase2-smoke | grep country_code
  ```
  Expected: `country_code                   "+44"`.
- `auto_rules` no longer contains the smoke-test custom rule:
  ```bash
  python3.11 -c "
  import json, pathlib
  cfg = json.loads(pathlib.Path.home().joinpath('.wxcli/migrations/phase2-smoke/config.json').read_text())
  rules = cfg['auto_rules']
  print(f'auto_rules count: {len(rules)}')
  for r in rules:
      print(f'  {r[\"type\"]} → {r[\"choice\"]}')
  assert len(rules) == 8, f'Expected 8 default rules, got {len(rules)}'
  assert not any(r.get('reason', '').startswith('Smoke test') for r in rules), \
      'Custom rule was not cleared'
  print('config reset verified')
  "
  ```
  Expected: `auto_rules count: 8` followed by 8 type/choice lines and `config reset verified`.

- [ ] **Step 7: Test `config reset` refuses unknown keys**

```bash
wxcli cucm config reset bogus_key -y -p phase2-smoke
```

Expected: exit code non-zero, output lists valid keys including `auto_rules`, `country_code`, etc.

- [ ] **Step 8: Tear down the test project (optional)**

```bash
rm -rf ~/.wxcli/migrations/phase2-smoke
```

The scratch project has served its purpose.

- [ ] **Step 9: No commit in this task**

Task 15 is a manual verification. Nothing to commit. Record the manual-test result as part of the plan execution log.

---

## Phase C exit verification

- [ ] **Check 1: grep audit is clean**

```bash
grep -rn '_check_auto_apply' src/wxcli/ tests/ --include="*.py"
```
Expected: empty.

```bash
grep -rn 'resolved_by=["'"'"']auto_apply["'"'"']' src/wxcli/ --include="*.py"
```
Expected: empty.

- [ ] **Check 2: SKILL.md is updated**

```bash
grep -n 'matched by current auto-rules\|Group 1: Auto-apply (matched by' .claude/skills/cucm-migrate/SKILL.md
```
Expected: at least 2 hits (one for Group 1, one for step 3).

- [ ] **Check 3: Full test suite is clean**

```bash
python3.11 -m pytest tests/migration/ 2>&1 | tail -5
```
Expected: 0 failures.

- [ ] **Check 4: Smoke test was run**

The manual smoke test (Task 15) has no automated artifact. The executor confirms completion by checking the plan's task list.

- [ ] **Check 5: Git log reflects all Phase C commits**

```bash
git log --oneline | head -15
```

Expected commit sequence (top = most recent):
- `docs(cucm-migrate): update SKILL.md Step 1c-fallback for unified auto-rules` (Task 13)
- `chore(migration): grep audit cleanup for legacy auto_apply references` (Task 12, OPTIONAL — only if files changed)
- [Phase B commits from Tasks 9-11]
- [Phase A commits from Tasks 1-8]

The cleanup and smoke-test tasks may have zero commits if nothing needed to change.

---

## Plan completion summary

Plan 2 is complete when:
1. All tasks across Phases A, B, and C are checked off.
2. The grep audit finds zero references to `_check_auto_apply` and zero production writes of `resolved_by="auto_apply"`.
3. SKILL.md Step 1c-fallback Group 1 and numbered step 3 no longer reference the hardcoded 3 cases.
4. The full `tests/migration/` suite passes (baseline 1642 + net ~30 new tests).
5. The manual smoke test confirms that `wxcli cucm decide --apply-auto` picks up edits to `config.json` and that `wxcli cucm config reset auto_rules` restores defaults without clobbering unrelated keys.

The architectural decision this plan implements:
- **Bug F:** Unify on `apply_auto_rules` as the sole matcher via `_iter_matching_resolutions`. Delete `_check_auto_apply`. Rewrite `classify_decisions` as a pure preview wrapper. Add `enrich_cross_decision_context` between merge and rule application in `AnalysisPipeline.run()` and at the end of `resolve_and_cascade()`'s save loop. Add a MISSING_DATA default rule that matches `is_on_incompatible_device`. Kill the silent CALLING_PERMISSION_MISMATCH skip bug.
- **Bug G:** Keep `load_config` semantics literal (no runtime merge). Add `wxcli cucm config reset <key>` to restore a single config key from `DEFAULT_CONFIG` while preserving other keys.

The unified architecture is a strict superset of the pre-Plan-2 behavior for the `analyze` path and fixes the silent data-loss bug in the `decide --apply-auto` path. Operator-visible changes are: (1) custom `auto_rules` in `config.json` now fire during `--apply-auto` (previously they were ignored), (2) `--apply-auto` shows "N decisions match current rules" instead of the hardcoded 3-case breakdown, (3) a new `config reset` subcommand, and (4) SKILL.md fallback text reflects the new behavior. Existing projects continue to work with their legacy `config.json` files; operators who want the new MISSING_DATA default rule must hand-edit or run `config reset auto_rules`.

End of Phase C.
