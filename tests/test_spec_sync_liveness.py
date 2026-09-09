"""Row 33: the cron silently stopping is the most dangerous failure because it
produces no signal. This workflow is GitHub Actions, not the Claude routine, so
it cannot die with the thing it watches."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "spec-sync-liveness.yml"


def test_exists_and_is_scheduled_off_the_routine_day():
    wf = yaml.safe_load(WF.read_text())
    trig = wf.get("on", wf.get(True))
    crons = [s["cron"] for s in trig["schedule"]]
    assert crons == ["0 16 * * 3"], crons   # Wednesday; the routine is Monday
    assert "workflow_dispatch" in trig


def test_reads_the_run_record_and_can_open_an_issue():
    text = WF.read_text()
    assert "docs/spec-sync/last-run.json" in text
    assert "issues: write" in text
    assert "gh issue create" in text and "--label" in text and "spec-sync" in text
    assert "10" in text  # the staleness threshold in days
    assert "gh issue list" in text, "must not open a duplicate when one is already open"


def _judge_script():
    """Extract the judge's Python out of the workflow's heredoc.

    The `>> "$GITHUB_OUTPUT"` redirect lives on the shell line, not inside the
    heredoc, so the extracted script prints its verdict to stdout.
    """
    wf = yaml.safe_load(WF.read_text())
    steps = wf["jobs"]["check"]["steps"]
    step = next(s for s in steps if s.get("name") == "Judge the run record")
    lines = step["run"].splitlines()
    start = next(i for i, ln in enumerate(lines) if "<<'PY'" in ln)
    end = next(i for i, ln in enumerate(lines) if i > start and ln.strip() == "PY")
    return "\n".join(lines[start + 1:end]) + "\n"


def _run_judge(script, cwd):
    return subprocess.run(
        [sys.executable, "-"], input=script, cwd=cwd, capture_output=True, text=True
    )


def test_judge_script_fails_closed_on_stale_missing_and_corrupt_records(tmp_path):
    script = _judge_script()
    assert "MAX_AGE_DAYS = 10" in script
    rec_dir = tmp_path / "docs" / "spec-sync"
    rec_dir.mkdir(parents=True)
    rec = rec_dir / "last-run.json"

    # 1. A record written today with a good outcome is fresh.
    rec.write_text(json.dumps(
        {"date": datetime.date.today().isoformat(), "outcome": "specs-only"}
    ))
    r = _run_judge(script, tmp_path)
    assert r.returncode == 0, r.stderr
    assert "stale=false" in r.stdout, r.stdout

    # 2. The cheap mutation: the same fresh record judged with a -1 day budget.
    r = _run_judge(script.replace("MAX_AGE_DAYS = 10", "MAX_AGE_DAYS = -1"), tmp_path)
    assert r.returncode == 0, r.stderr
    assert "stale=true" in r.stdout, r.stdout

    # 3. An unreadable record must alarm, not crash the step and skip the issue.
    rec.write_text("{not json")
    r = _run_judge(script, tmp_path)
    assert r.returncode == 0, r.stderr
    assert "stale=true" in r.stdout, r.stdout
    assert "since=unreadable record" in r.stdout, r.stdout

    # 4. An outcome outside the ok-set is stale even when the date is today, and
    #    the record is untrusted input: it must never reach $GITHUB_OUTPUT (or,
    #    through it, a shell line) as more than one line.
    rec.write_text(json.dumps({
        "date": datetime.date.today().isoformat(),
        "outcome": "failed\nsecond line $(id)",
    }))
    r = _run_judge(script, tmp_path)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert len(lines) == 2, r.stdout
    assert "stale=true" in lines[0], r.stdout
    since = next(ln for ln in lines if ln.startswith("since="))
    assert "failed second line $(id)" in since, since
    assert "\n" not in since

    # 5. No record at all — the routine has never run, or the file was lost.
    rec.unlink()
    r = _run_judge(script, tmp_path)
    assert r.returncode == 0, r.stderr
    assert "stale=true" in r.stdout, r.stdout
    assert "since=never" in r.stdout, r.stdout


def test_reads_failed_branches_and_never_interpolates_agent_content():
    """Contract §4 (the sandbox has no gh): a fail-closed run pushes
    spec-sync/failed-<date> with the record and failure.txt; this workflow —
    not the agent — turns that into the issue. Branch name, record and output
    are all agent-written: pattern-match the name, read the files, never
    interpolate any of it into a shell line."""
    wf = yaml.safe_load(WF.read_text())
    steps = wf["jobs"]["check"]["steps"]
    names = [s.get("name") for s in steps]
    assert names.index("Look for a failed-run branch") > names.index("Judge the run record"), \
        "the branch judge needs stale= from the record judge to ignore superseded branches"
    failed = steps[names.index("Look for a failed-run branch")]
    assert failed.get("id") == "failed"
    assert "spec-sync/failed-" in failed["run"]
    assert "[0-9]{4}-[0-9]{2}-[0-9]{2}" in failed["run"], "branch names are agent-chosen: pattern-match them"
    assert "docs/spec-sync/failure.txt" in failed["run"] and "docs/spec-sync/last-run.json" in failed["run"]
    issue = steps[names.index("Open an issue if stale or a run failed closed, and none is open")]
    assert "steps.failed.outputs.branch" in issue["if"] and "steps.judge.outputs.stale" in issue["if"]
    assert "--body-file" in issue["run"], "the failing output is data — a file, never an argument"
    assert "gh issue list" in issue["run"], "still no duplicate while one is open"
    for s in steps:
        assert "${{" not in (s.get("run") or ""), s.get("name")
