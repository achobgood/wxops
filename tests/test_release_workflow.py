from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"


def _load():
    # PyYAML parses the bare `on:` key as boolean True; read it back with that in mind.
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_exists():
    assert WORKFLOW.exists()


def test_triggers_on_tag_push_or_release_branch_push_only():
    """Humans push a tag. The spec-sync sandbox has no `gh` (probed 2026-09-09) and
    its git proxy refuses refs/tags (HTTP 403, run 2026-09-14), so it pushes a
    release/vX.Y.Z branch instead. ONE event: a human `gh release create` also
    creates the tag, so a second `release:` trigger would run the job twice."""
    wf = _load()
    trigger = wf.get("on", wf.get(True))  # 'on' may parse as the boolean True
    assert trigger["push"]["tags"] == ["v*"]
    assert trigger["push"]["branches"] == ["release/v*"]
    # No `release:` trigger: a human `gh release create` also pushes the tag, so it
    # would publish twice. workflow_run is the unattended path (2026-11-02) and is
    # idempotent: `decide` releases nothing once the notes' version is tagged.
    assert set(trigger) == {"push", "workflow_run"}, "a `release:` trigger = two publishes for one gh release create"
    assert trigger["workflow_run"] == {"workflows": ["CI"], "types": ["completed"], "branches": ["main"]}


def test_tag_is_only_set_after_the_ref_is_resolved():
    """A branch ref is not a tag: TAG must never be the raw ref name at job level,
    or the version guard and Release steps would run against `release/vX.Y.Z`."""
    env = _load()["jobs"]["publish"]["env"]
    assert env["REF_NAME"] == "${{ github.ref_name }}"
    assert env["REF_TYPE"] == "${{ github.ref_type }}"
    assert "TAG" not in env
    resolve = next(s for s in _steps() if s.get("name") == "Resolve the release tag")
    assert 'TAG=$REF_NAME" >> "$GITHUB_ENV"' in resolve["run"]
    assert 'TAG=$TAG" >> "$GITHUB_ENV"' in resolve["run"]


def test_release_branch_path_validates_before_it_tags():
    """The branch path must refuse anything a human tag push would not have been:
    a non-vX.Y.Z name, notes written for another version, a commit main lacks, or
    a version whose tag already exists. All four checks precede `git tag -a`."""
    steps = _steps()
    names = [s.get("name", s.get("uses", "")) for s in steps]
    resolve = names.index("Resolve the release tag")
    gate = next(i for i, n in enumerate(names) if "green CI" in n)
    assert gate < resolve < names.index("Build wheel + sdist")
    run = steps[resolve]["run"]
    tag_at = run.index("git tag -a")
    for check in ("v[0-9]+", 'head -1 "$NOTES"', "merge-base --is-ancestor HEAD origin/main",
                  'ls-remote --tags origin "refs/tags/$TAG"'):
        assert -1 < run.index(check) < tag_at, check
    # git's default message cleanup deletes `#` lines, i.e. the notes' `# vX.Y.Z` and
    # `## New commands` headings, from the tag the Release body is built from.
    assert "--cleanup=verbatim" in run[tag_at:run.index("\n", tag_at)]


def test_release_branch_path_pushes_the_tag_before_pypi_and_cleans_up_last():
    steps = _steps()
    names = [s.get("name", s.get("uses", "")) for s in steps]
    push = names.index("Push the tag (release branch only)")
    publish = next(i for i, s in enumerate(steps) if "pypi-publish" in str(s.get("uses", "")))
    delete = names.index("Delete the release branch")
    assert names.index("Version guard (never publish a dirty version)") < push < publish
    assert delete == len(steps) - 1
    assert steps[push]["if"] == "github.ref_type == 'branch'"
    # On workflow_run, ref_type is 'branch' and REF_NAME is `main`: without the
    # event_name guard this step would delete main.
    assert steps[delete]["if"] == "github.event_name == 'push' && github.ref_type == 'branch'"


def test_release_is_created_after_pypi_and_before_upload_and_is_idempotent():
    """PyPI first: a GitHub Release with no package behind it would be a lie;
    if the publish fails the tag is burned (sync_version skips it) and no
    Release exists. `gh release view ||` makes a human's gh release create
    (which already made the Release) a no-op instead of a red X."""
    steps = _steps()
    names = [s.get("name", s.get("uses", "")) for s in steps]
    create = names.index("Create the GitHub Release from the tag")
    publish = next(i for i, s in enumerate(steps) if "pypi-publish" in str(s.get("uses", "")))
    upload = names.index("Attach artifacts to the GitHub Release")
    assert publish < create < upload
    run = steps[create]["run"]
    assert "gh release view" in run and "||" in run, "must be idempotent"
    assert "--notes-from-tag" in run and "--verify-tag" in run
    assert "${{" not in run


def test_declares_oidc_and_contents_permissions():
    text = WORKFLOW.read_text()
    assert "id-token: write" in text
    assert "contents: write" in text


def test_checkout_uses_full_history():
    text = WORKFLOW.read_text()
    assert "fetch-depth: 0" in text


def test_has_version_guard_and_trusted_publish_and_asset_upload():
    text = WORKFLOW.read_text()
    assert "pypa/gh-action-pypi-publish" in text
    assert "gh release upload" in text
    # version guard fails on a dirty/mismatched version
    assert ".dev" in text and "Version" in text


def test_builds_on_python_311():
    text = WORKFLOW.read_text()
    assert "3.11" in text


def _steps():
    wf = _load()
    return wf["jobs"]["publish"]["steps"]


def test_ci_gate_runs_before_anything_is_built():
    """The gate must be the first `run:` step: a failed build step would
    otherwise mask a missing-CI failure with a different red X."""
    steps = _steps()
    names = [s.get("name", s.get("uses", "")) for s in steps]
    gate = next(i for i, n in enumerate(names) if "green CI" in n)
    assert all("run" not in s for s in steps[:gate]), "only checkout/setup may precede the gate"
    assert gate < names.index("Playbook bundle freshness guard")


def test_ci_gate_fails_closed_on_no_run_and_on_non_success():
    text = WORKFLOW.read_text()
    assert "actions/workflows/ci.yml/runs?head_sha=" in text, "must query CI runs for the release SHA"
    assert "No CI run found" in text, "absence of evidence must fail, not pass"
    assert '"completed"' in text and '"success"' in text
    assert "newest" in text.lower() and ".[0]" in text, "judge the NEWEST run, so a re-run that went green counts and a re-run that went red counts too"


def test_ci_gate_uses_the_checked_out_sha_not_the_event_payload():
    text = WORKFLOW.read_text()
    assert "git rev-parse HEAD" in text


def test_no_expression_is_interpolated_into_a_run_body():
    """`${{ }}` is substituted textually before bash parses the script, so a
    release tag carrying `;`/`$(...)`/backticks executes — in the one job holding
    `id-token: write`, before the CI gate has concluded anything. The tag reaches
    every shell line through a job-level `env:` var instead; `$TAG` expands to a
    value and command substitution inside a value is not re-evaluated."""
    for step in _steps():
        run = step.get("run")
        if run is None:
            continue
        assert "${{" not in run, (
            f"step {step.get('name', step.get('uses'))!r} interpolates an expression "
            "into its run: body — pass it through env: instead"
        )


def test_publish_job_grants_actions_read_for_the_ci_gate():
    """An explicit `permissions:` block sets every unlisted scope to none, so the
    gate's `gh api .../actions/workflows/ci.yml/runs` 403s without `actions: read`.
    Asserted on the parsed job so the scope cannot be dropped silently later."""
    permissions = _load()["jobs"]["publish"]["permissions"]
    assert permissions.get("actions") == "read", (
        "the CI gate reads workflow runs; without actions:read every release 403s"
    )


def test_workflow_run_path_releases_only_an_untagged_version_from_green_main():
    """The spec-sync sandbox may not push a release ref (auto-mode classifier,
    2026-11-02), so a green CI run on main releases the version the notes name.
    `decide` must require success on a push to main, read the `# vX.Y.Z ` header,
    and name nothing when the tag exists, so every later main commit is a no-op."""
    jobs = _load()["jobs"]
    decide = jobs["decide"]
    assert "github.event.workflow_run.conclusion == 'success'" in decide["if"]
    assert "github.event.workflow_run.event == 'push'" in decide["if"]
    assert decide["permissions"] == {"contents": "read"}
    checkout = decide["steps"][0]
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"
    run = decide["steps"][1]["run"]
    assert "${{" not in run
    assert "release-notes.md" in run and 'ls-remote --tags origin "refs/tags/$TAG"' in run
    assert run.index("ls-remote") < run.index('tag=$TAG" >> "$GITHUB_OUTPUT"')
    publish = jobs["publish"]
    assert publish["needs"] == "decide"
    assert "!cancelled()" in publish["if"] and "needs.decide.outputs.tag != ''" in publish["if"]
    assert publish["env"]["AUTO_TAG"] == "${{ needs.decide.outputs.tag }}"
    pub_checkout = _steps()[0]
    assert pub_checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha || github.sha }}"
    resolve = next(s for s in _steps() if s.get("name") == "Resolve the release tag")["run"]
    # The auto tag goes through the same four checks as a release/v* branch.
    assert resolve.index('TAG="$AUTO_TAG"') < resolve.index('head -1 "$NOTES"')
    assert _load()["concurrency"] == {"group": "release", "cancel-in-progress": False}
