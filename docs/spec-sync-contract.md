# Spec-Sync Contract

**Pipeline:** enabled

The single definition of "done" for a weekly OpenAPI spec sync. The scheduled
cloud routine's prompt is a pointer at this file; nothing here is duplicated
there. Change the pipeline by changing this file in a reviewed commit. To stop
the pipeline, change the line above to `**Pipeline:** disabled — <reason>`;
the routine checks it first and exits without doing anything.

Design and evidence: `docs/superpowers/specs/2026-09-08-spec-sync-automation-design.md`.

## 0. Preconditions (run first, in this order)

```bash
git fetch origin && git checkout -B spec-sync/$(date -u +%F) origin/main
python -m pip install -e . -q && python -m pip install pytest pytest-asyncio aioresponses 'aiohttp<3.14' -q
python -m tools.sync_guard enabled            # exit 3 = disabled: stop, output "pipeline disabled", exit 0
```

Interpreter: the `python` that has `wxcli` installed (`python -c "import wxcli, yaml"` must succeed). Run every `tools/` module as `python -m tools.<name>`, never as a script.

## 1. Mechanical steps

| # | Command | What it verifies |
|---|---|---|
| 1 | `python tools/update-specs.py` | Exit 0 = specs on disk are current. **Exit 2 = a download failed: regenerate nothing.** Read `docs/spec-sync/last-run.json` on `origin/main`: if its `outcome` is already `failed` with `download` in `notes`, this is the second week — open the §4 issue. Either way write the run record (`outcome: failed`, `notes: "download failed: <which>"`), commit **only that file** to `main` (§5 steps 3–4), exit non-zero. The liveness workflow treats `failed` as not-ok, so silence cannot outlast 10 days. Output `OK` on every line and `0 spec(s) updated` = **no-op week**: skip to §5 with `outcome: noop`. |
| 2 | `python tools/spec_sync.py --skip-update --run-dir .spec-sync` | Regenerates every tracked spec, refreshes the name lock (additive), captures the check-19 delta to `.spec-sync/spec-delta.txt` before rewriting the snapshot, assembles the playbook, repairs published counts, writes `.spec-sync/gate.txt`. **If the lock refresh refuses (`MOVED` lines), go to §2 rule A.** |
| 3 | `python -m tools.sync_classify --base origin/main` | The version verdict. `human` → §4 fail closed. `none` → commit specs + snapshot only (§5, `outcome: specs-only`), no release. |
| 4 | `git diff --stat origin/main -- src/wxcli/commands/_registry.py` | If a module was added: §2 rules B and C apply before the pass bar. |

## 2. Judgement steps (only when triggered)

**A. A locked name moved.** The refusal prints `MOVED <module> <command>  locked <op>  now <op>  (locked op now held by <name>)`. Write a SWAP under `tag_overrides -> <spec> -> "<Tag>" -> command_name_overrides` in `tools/field_overrides.yaml`: the derived name that now holds the locked operation → the locked name; the intruder → a name that says what it does (`update-group-controls`, not `create`). Keys are the derived names the refusal printed. Then re-run step 2. Two attempts; if it still refuses, §4.

**B. A new command group appeared.** Route it: add one row to the Skill Disambiguation table in `CLAUDE.md` and one citation (a table row and one fenced runnable example) in the owning skill's `SKILL.md`. Record the decision as one line per group in `.spec-sync/routing.md` (`- <group> -> <skill> (<why>)`). If no skill fits, that is not a decision the automation makes: §4.

**C. Write its reference-doc coverage** in the sibling `docs/reference/*.md` that covers the same API family, as a numbered section with intro, `### CLI Examples`, `### Raw HTTP`, one gotcha, and a reasoned `## See Also` entry. Then score it against §3.

**D. `naming`, `skip`, `ack`, `allowlist`, `keep`, `authority`, `out-of-scope`** — never. If a check can only be made green by editing one of those, §4.

## 3. The doc rubric (self-score every new section; all four must be yes)

1. Does the intro say what the surface is **NOT**?
2. Does every gotcha lead with a bold claim sentence, then explain?
3. Is every claim either dated-and-labelled as verified (`Verified live, YYYY-MM-DD:`) or marked `**Unverified:**`? (Unattended runs cannot verify live — label everything unverified.)
4. Does every cross-reference state **why** you would go there?

## 4. The pass bar — all must hold, no exceptions

```bash
python -m tools.sync_guard diff --base origin/main          # 0 — no forbidden surface in the diff
python -m tools.drift_check --enforce                        # 0 — exit 2 means DID NOT RUN, which is a failure
TERM=dumb COLUMNS=400 pytest tests/ -m "not live" -q        # 0 — never skip, mark or delete a failing test
python wxcli-dist/assemble.py && test -z "$(git status --porcelain -- src/wxcli/_playbook)"   # no diff
python -m tools.sync_classify --base origin/main --fail-on-human   # 0
```

A failing bar gets **two** repair attempts. A repair may touch only: `src/wxcli/commands/**`, `src/wxcli/_playbook/**`, `tools/spec_semantics.json`, `tools/command_name_lock.json` (additively), `docs/**` except this file, `.claude/skills/**`, `CLAUDE.md` except its Out-of-Skill-Scope section, `README.md`, and the two override keys named in §2 A/B. Then re-run the whole bar.

**Fail closed** if any item still fails, or cannot be evaluated: commit nothing to `main`, publish nothing, run

```bash
gh issue create --label spec-sync --title "spec-sync $(date -u +%F): <one-line reason>" --body-file <the failing output>
```

write the run record with `outcome: failed` and the issue URL **to the branch only** (not `main`), and exit non-zero. The GitHub Actions liveness check will alarm if this repeats.

## 5. Land and release

1. `python -m tools.sync_version --level <patch|minor from step 3>` → `vX.Y.Z`. Exit 2 (PyPI unreachable) = §4.
2. Write `docs/spec-sync/last-run.json`: `{"date","outcome","sha","version","groups","commands","issue","notes"}` (`sha` = the commit you are about to push, filled after commit with `git rev-parse HEAD`; for `noop`/`specs-only` set `version: null`).
3. One commit: `chore(specs): sync + regen (<date>) — <verdict>, <N> groups / <M> commands`. Stage by path: `git add -u specs src/wxcli/commands src/wxcli/_playbook tools/spec_semantics.json tools/command_name_lock.json tools/field_overrides.yaml docs/arch/deliberate-gaps.md docs/spec-sync/last-run.json CLAUDE.md README.md docs/reference .claude/skills`. Never `git add -A`.
4. `git push origin HEAD:main`. If rejected (non-fast-forward): `git rebase origin/main`, re-run §4, push again. **Never `--force`.**
5. **Wait for CI on that SHA**: `gh run watch --exit-status $(gh run list --commit $(git rev-parse HEAD) --workflow CI --json databaseId --jq '.[0].databaseId')` (poll `gh run list --commit` every 60 s until a run exists, up to 10 min). Red CI = §4 issue, no release; `main` stays as pushed.
6. Verdict `patch`/`minor` only: `python -m tools.sync_classify --base <sha-before-push> --notes .spec-sync --version vX.Y.Z > .spec-sync/notes.md` then `gh release create vX.Y.Z --target main --title vX.Y.Z --notes-file .spec-sync/notes.md`. `release.yml` re-checks CI on the SHA and publishes to PyPI. Confirm with `gh run watch` on the Release workflow; a failed publish = §4 issue (the tag is burned; next week's `sync_version` skips it automatically).

## 6. What must reach a human (each is an issue with label `spec-sync`)

Pass bar failed after two repairs · a locked name still moved after two pin attempts · a command or group removed upstream · blast radius over 40 · a download failed two weeks running · no successful run in 10 days (opened by the liveness workflow, not by you).
