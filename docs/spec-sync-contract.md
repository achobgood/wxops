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
git fetch origin --tags && git checkout -B spec-sync/$(date -u +%F) origin/main   # --tags: sync_version reads `git tag --list`; a shallow clone would leave PyPI as the only oracle
python3 -m pip install -e . -q && python3 -m pip install pytest pytest-asyncio aioresponses 'aiohttp<3.14' -q
python3 -m tools.sync_guard enabled            # exit 3 = disabled: stop, output "pipeline disabled", exit 0
```

Interpreter: `python3` — in the cloud sandbox that is Python 3.11.15 (probed 2026-09-09; `python3.12` also exists, `python3.14` does not), the same minor CI uses. Check it with `wxcli --help >/dev/null && python3 -c "import yaml"`. Never check by importing `wxcli` from Python: the repo's Bash hook blocks that (importing the command modules bypasses the confirm prompt) and it fired in the sandbox. Run every `tools/` module as `python3 -m tools.<name>`, never as a script.

## 1. Mechanical steps

| # | Command | What it verifies |
|---|---|---|
| 1 | `python3 tools/update-specs.py` | Exit 0 = specs on disk are current. **Exit 2 = a download failed: regenerate nothing.** Read `docs/spec-sync/last-run.json` on `origin/main`: if its `outcome` is already `failed` with `download` in `notes`, this is the second week — say so in `notes` (the liveness workflow turns a `failed` record on `main` into an issue; the sandbox cannot open one itself, see §4). Either way write the run record (`outcome: failed`, `notes: "download failed: <which>"`), commit **only that file** to `main` (§5 steps 3–4), exit non-zero. The liveness workflow treats `failed` as not-ok, so silence cannot outlast 10 days. Output `OK` on every line and `0 spec(s) updated` = **no-op week**: skip to §5 with `outcome: noop`. |
| 2 | `python3 tools/spec_sync.py --skip-update --run-dir .spec-sync` | Regenerates every tracked spec, refreshes the name lock (additive), captures the check-19 delta to `.spec-sync/spec-delta.txt` before rewriting the snapshot, assembles the playbook, repairs published counts, writes `.spec-sync/gate.txt`. **If the lock refresh refuses (`MOVED` lines), go to §2 rule A.** |
| 3 | `python3 -m tools.sync_classify --base origin/main` | The version verdict. `human` → §4 fail closed. **Exit 2 = the base lock or the diff was unreadable, nothing was classified → §4** (an unreadable base is not an empty one). `none` → commit specs + snapshot only (§5, `outcome: specs-only`), no release. |
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
python3 -m tools.sync_guard diff --base origin/main          # 0 — no forbidden surface in the diff
python3 -m tools.drift_check --enforce                        # 0 — exit 2 means DID NOT RUN, which is a failure
TERM=dumb COLUMNS=400 pytest tests/ -m "not live" -q        # 0 — never skip, mark or delete a failing test
python3 wxcli-dist/assemble.py && test -z "$(git status --porcelain -- src/wxcli/_playbook)"   # no diff
python3 -m tools.sync_classify --base origin/main --fail-on-human   # 0
```

A failing bar gets **two** repair attempts. A repair may touch only: `src/wxcli/commands/**`, `src/wxcli/_playbook/**`, `tools/spec_semantics.json`, `tools/command_name_lock.json` (additively), `docs/**` except this file, `.claude/skills/**`, `CLAUDE.md` except its Out-of-Skill-Scope section, `README.md`, and the two override keys named in §2 A/B. Then re-run the whole bar.

**Fail closed** if any item still fails, or cannot be evaluated: commit nothing to `main`, publish nothing. The sandbox has no `gh` (probed 2026-09-09), so you cannot open the issue yourself; leave the signal where the liveness workflow can find it:

```bash
git checkout -B spec-sync/failed-$(date -u +%F) origin/main      # a clean branch off main: none of the failed regen goes with it
# write docs/spec-sync/last-run.json (outcome: failed, issue: null, version: null, notes: "<one-line reason>")
# write docs/spec-sync/failure.txt — the failing output, verbatim
git add docs/spec-sync/last-run.json docs/spec-sync/failure.txt
git commit -m "spec-sync $(date -u +%F): failed — <one-line reason>"
git push origin HEAD:refs/heads/spec-sync/failed-$(date -u +%F)
```

Then exit non-zero. The run record goes **to that branch only** (not `main`). The GitHub Actions liveness workflow (`.github/workflows/spec-sync-liveness.yml`, Wednesdays 16:00 UTC) opens the `spec-sync` issue from that branch, quoting `failure.txt`. A human deletes the branch when the cause is fixed.

## 5. Land and release

1. `python3 -m tools.sync_version --level <patch|minor from step 3>` → `vX.Y.Z`. Exit 2 (PyPI unreachable) = §4; exit 1 (no version found anywhere, or a collision) = §4.
2. Write `docs/spec-sync/last-run.json`: `{"date","outcome","sha","version","groups","commands","issue","notes"}`. `date` = `date -u +%F`. `sha` = `git rev-parse origin/main` as fetched in §0 — the tree this run verified and built on (the record's own commit is the one that contains it, and a tag names a released commit; no amend needed). `groups` and `commands` = the two numbers on the **first line** of `python3 -m tools.drift_check --enforce` output — `drift-check: <groups> command sets (…), <commands> commands, …` — and nowhere else (the same line is the first line of `.spec-sync/gate.txt` after step 2; on a `noop` week run the gate once to read it). For `noop`/`specs-only` set `version: null`; `issue` is always `null` (you cannot open one).
3. One commit: `chore(specs): sync + regen (<date>) — <verdict>, <N> groups / <M> commands`. Stage by path: `git add -u specs src/wxcli/commands src/wxcli/_playbook tools/spec_semantics.json tools/command_name_lock.json tools/field_overrides.yaml docs/arch/deliberate-gaps.md docs/spec-sync/last-run.json CLAUDE.md README.md docs/reference .claude/skills`. Never `git add -A`.
4. `git push origin HEAD:main`. If rejected (non-fast-forward): `git rebase origin/main`, re-run §4, push again. **Never `--force`.**
5. **Wait for CI on that SHA** — the repo is public, so the Actions API answers unauthenticated reads (60/hour; this uses at most 21). Poll every 60 s, at most 20 times, then judge the newest run once:

   ```bash
   for i in $(seq 1 20); do curl -sS -m 20 "https://api.github.com/repos/achobgood/wxops/actions/workflows/ci.yml/runs?head_sha=$(git rev-parse HEAD)&per_page=1" | jq -e '.workflow_runs[0].status == "completed"' >/dev/null && break; sleep 60; done
   curl -sS -m 20 "https://api.github.com/repos/achobgood/wxops/actions/workflows/ci.yml/runs?head_sha=$(git rev-parse HEAD)&per_page=1" | jq -e '.workflow_runs[0].conclusion == "success"'
   ```

   Exit 0 = green. Anything else (red, still running after 20 min, no run at all) = §4, no release; `main` stays as pushed. **Run this loop as one ordinary foreground Bash call and wait for it** — never background it, hand it to a monitor, or end your turn while it runs: the session ends when you stop, nothing resumes it, and a release week would end with `main` pushed and no tag. On a `noop`/`specs-only` week nothing depends on CI, so skip the wait after pushing.
6. Verdict `patch`/`minor` only: `python3 -m tools.sync_classify --base <sha-before-push> --notes .spec-sync --version vX.Y.Z > .spec-sync/notes.md` then `git tag -a vX.Y.Z -F .spec-sync/notes.md && git push origin vX.Y.Z`. `release.yml` runs on the tag push, re-checks CI on the SHA, publishes to PyPI and creates the GitHub Release from the tag message. Confirm with the same poll as step 5 against `workflows/release.yml/runs?head_sha=…` (a run appears within a minute; wait for `completed`, require `success`); a failed publish = §4 (the tag is burned; next week's `sync_version` skips it automatically).

## 6. What must reach a human (each is an issue with label `spec-sync`, opened by the liveness workflow — never by you, the sandbox has no `gh`)

Pass bar failed after two repairs · a locked name still moved after two pin attempts · a command or group removed upstream · blast radius over 40 · a download failed two weeks running · no successful run in 10 days.

## Cloud environment (probed 2026-09-09)

One-time read-only routine `spec-sync-environment-probe` (session `cse_01PK6oxsaJsp86bTLVCs3QGU`, model claude-sonnet-5, environment `Default`), 145 s, nothing committed, pushed, tagged or released. Every row below is measured, not assumed.

| Capability | Works | Evidence |
|---|---|---|
| `python3` | yes — 3.11.15 | `which -a`: `/usr/local/bin/python3`, `/usr/bin/python3.12`; no `python3.14` |
| `pip install -e .` | yes — 20 s | exit 0; `wxcli --help` prints usage |
| `python3 -c "import wxcli"` | **blocked by the repo's Bash hook** | "Importing wxcli from Python bypasses this gate…" — the probe's one permission denial; hooks fire in the sandbox |
| pytest + pytest-asyncio + aioresponses + `aiohttp<3.14` | yes | `pytest 9.1.1` |
| `gh` | **no — not installed** | `gh: command not found`, exit 127, for `--version`, `auth status`, `issue list`, `release list` |
| `git push` to `origin` | yes | `git push --dry-run origin HEAD:refs/heads/spec-sync-probe-dry-run` → `* [new branch]`; no branch created |
| `jq` | yes — 1.7 | `/usr/bin/jq` |
| `python3 -m tools.drift_check --enforce` | yes — 17 s | `[22] … 0 moved, 0 removed, 0 groups gone, 0 unlocked`, `result: PASS` |
| PyPI (`pypi.org/pypi/wxcli/json`) | yes | HTTP 200 |
| Upstream specs (`raw.githubusercontent.com/webex/webex-openapi-specs`) | yes | HTTP 200 |
| GitHub Actions API, unauthenticated read | yes (measured from outside the sandbox, same public repo) | `…/actions/workflows/ci.yml/runs?head_sha=4a0d649…` → `completed/success`, `x-ratelimit-remaining: 58` |

Release gate, negative proofs (both refused with `No CI run found for <sha>`, nothing built or published, probe tags deleted): 2026-09-09 via `gh release create` on `v0.0.0-gate-probe` (run 34307687281, the `release: published` trigger); 2026-09-09 via annotated tag push `v0.0.0-gate-probe-2` (run 34309266293, the `push: tags` trigger that replaced it). Positive proof of the tag-push path is the next real release — expect exactly one Release run per tag.

Consequences applied above: every command is `python3`; the interpreter check does not import `wxcli`; §4 signals failure by pushing a `spec-sync/failed-<date>` branch instead of `gh issue create`; §5.5 waits for CI with `curl`+`jq` instead of `gh run watch`; §5.6 releases by annotated tag push instead of `gh release create` (`release.yml` triggers on `push: tags` since 2026-09-09 and creates the GitHub Release itself).
