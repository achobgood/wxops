"""Shared helpers + fixtures for wxcc's live test tiers, retargeted to `wxcli`.

Tier 1 (`-m live`, tests/wxcc/test_live_readonly.py) and Tier 2 (`-m mutation` +
`WXCLI_LIVE_MUTATION=1`, tests/wxcc/test_live_mutation.py) both drive the REAL
installed `wxcli` binary as a subprocess, so they exercise the true command
surface, exit codes, and `-o json` output against live prod. Both tiers
auto-skip when the CLI or a token is unavailable.

Plan 2 Task 20 (2026-10-19): every `wxcc-flow` call these tiers made is
translated through docs/merge/wxcc-flow-command-map.md. The JSON shapes were
first verified live on produs1 (the sandbox org) 2026-07-12 through
`wxcc-flow`, and re-run through `wxcli` in the sandbox tenant 2026-10-19.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


# Keep the whole suite hermetic: the CLI's PyPI update check fires from the
# top-level callback on every in-process CliRunner call and every subprocess
# run_cli call. Disable it session-wide so no test ever reaches out to PyPI.
os.environ.setdefault("WXCC_FLOW_NO_UPDATE_CHECK", "1")
os.environ.setdefault("WXCLI_NO_UPDATE_CHECK", "1")

# wxcc's operation list (60 rows, the fate table's rows 1-60). The live tiers
# still iterate it, so every wxcc operation keeps a live test or a stated reason.
# Frozen copy of wxcc's generated `_manifest.json` (60 operations), kept when
# `wxcc/` was removed (Plan 6).
MANIFEST = json.loads(
    (REPO / "tests" / "wxcc" / "fixtures" / "wxcc_flow_manifest.json").read_text()
)
# The venv running pytest comes first, so the tiers test this checkout's wxcli
# rather than some other install further down PATH.
WXCLI_BIN = shutil.which(
    "wxcli",
    path=os.pathsep.join([str(Path(sys.executable).parent), os.environ.get("PATH", "")]),
)

# Test resources carry this prefix (spec §10.5); the safety sweep deletes only these.
PREFIX = "CLITest_WebexOps_"


@dataclass
class CliResult:
    code: int
    out: str
    err: str
    argv: list

    def json(self):
        return json.loads(self.out)

    @property
    def combined(self) -> str:
        return self.out + self.err


def run_cli(*args, timeout=180) -> CliResult:
    """Invoke the installed `wxcli` binary (which imports the working tree)."""
    argv = [WXCLI_BIN, *[str(a) for a in args]]
    env = {**os.environ, "COLUMNS": "400", "TERM": "dumb"}
    p = subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, cwd=str(REPO), env=env
    )
    return CliResult(p.returncode, p.stdout, p.stderr, argv)


# ---------------------------------------------------------------- skip guards
@pytest.fixture(scope="session")
def live_env():
    """Skip the whole live tier when the CLI or a token is unavailable."""
    if WXCLI_BIN is None:
        pytest.skip("wxcli not on PATH")
    from wxcli.auth import resolve_token

    if not resolve_token():
        pytest.skip("no token (WEBEX_ACCESS_TOKEN / WEBEX_TOKEN / ~/.wxcli/config.json)")
    return True


@pytest.fixture(scope="session")
def mutation_env(live_env):
    """Tier 2 double-gate: `-m mutation` selects it; this adds the env flag."""
    if os.environ.get("WXCLI_LIVE_MUTATION") != "1":
        pytest.skip("mutation tier requires WXCLI_LIVE_MUTATION=1 (+ explicit approval)")
    return True


# --------------------------------------------------------- session discovery
@pytest.fixture(scope="session")
def project_id(live_env):
    """The Flow Designer project ID, read once (P2-2: wxcc looked it up itself)."""
    r = run_cli("cc-flow-projects", "show-user-preferences", "-o", "json")
    assert r.code == 0, r.err
    pid = json.loads(r.out).get("projectId")
    assert pid, f"no projectId in user preferences: {r.out[:200]}"
    return pid


@pytest.fixture(scope="session")
def activities(project_id):
    """Live activity registry — ONE call, reused by registry/doc-home/port tests.
    Each entry: activityName, displayName, group, inputs, outputs, outputPorts."""
    r = run_cli("cc-flow", "list-activities", project_id, "-o", "json")
    assert r.code == 0, r.err
    data = json.loads(r.out)
    assert isinstance(data, list) and data
    return data


@pytest.fixture(scope="session")
def activity_names(activities):
    return sorted(e["activityName"] for e in activities)


@pytest.fixture(scope="session")
def flows(project_id):
    """Full flow list (entries keyed by 'id', 'name', 'status', 'flowType')."""
    r = run_cli("cc-flow", "list", project_id, "--all", "-o", "json")
    assert r.code == 0, r.err
    return json.loads(r.out)


@pytest.fixture(scope="session")
def a_flow_id(flows):
    if not flows:
        pytest.skip("org has no flows")
    return flows[0]["id"]


@pytest.fixture(scope="session")
def pub_version(project_id):
    """(flow_id, version_id) for some PUBLISHED version; skip if project has none."""
    r = run_cli(
        "cc-flow-versions", "list-all", project_id, "--page", "0", "--size", "10", "-o", "json"
    )
    if r.code != 0:
        pytest.skip(f"cc-flow-versions list-all failed: {r.err[:160]}")
    vs = json.loads(r.out)
    if not vs:
        pytest.skip("no published versions in project")
    return vs[0]["flowId"], vs[0]["id"]


@pytest.fixture(scope="session")
def a_template_id(live_env):
    r = run_cli("cc-flow-templates", "list", "--all", "-o", "json")
    if r.code != 0:
        pytest.skip(f"cc-flow-templates list failed: {r.err[:160]}")
    ts = json.loads(r.out)
    if not ts:
        pytest.skip("no templates in project")
    return ts[0]["id"]


# ------------------------------------------------ read-only manifest routing
READ_ONLY = [e for e in MANIFEST if e.get("read_only") is True]
MUTATING = [e for e in MANIFEST if e.get("read_only") is False]

# Each read-only wxcc operation -> the wxcli argv that replaces it, translated
# through docs/merge/wxcc-flow-command-map.md (the comment is the map's row).
# Placeholders: P project, F flow, V published version, T template id.
# Recipes carried from wxcc (verified live 2026-07-12): `check` needs a filter,
# `search` a term, `choices`/`describe` a real activity.
WXCLI_READ = {
    ("flows", "get"): ["cc-flow-store", "show-metadata", "P", "F"],  # 1
    ("flows", "list"): ["cc-flow", "list", "P"],  # 4
    ("flows", "search"): ["cc-flow", "list", "P", "--partial-name-search", "a"],  # 5
    ("flows", "check"): ["cc-flow-store", "list-usages", "P", "--search", "a"],  # 16
    ("flows", "export"): ["cc-legacy-flows", "export-ui", "F", "P"],  # 17
    ("flows", "global-variables"): ["cc-flow-store", "list-global-variables", "P"],  # 18
    ("flows-v2", "get-draft"): ["cc-flow", "show", "P", "F"],  # 21
    ("flows-v2", "validate-id"): [
        "cc-flow", "list-validate", "P", "F", "--version-id", "draft"],  # 25
    ("flows-v2", "export"): ["cc-flow", "export", "P", "F", "--version", "draft"],  # 26
    ("flows-v2", "flow-template"): ["cc-flow-store", "show-flow-template", "P"],  # 27
    ("flows-v2", "event-specifications"): ["cc-flow", "list-event-specifications", "P"],  # 28
    ("flows-v2", "activities"): ["cc-flow", "list-activities", "P"],  # 29
    ("flows-v2", "describe"): ["cc-flow", "show-activity", "P", "cryptographic-hash"],  # 30
    ("flows-v2", "choices"): [
        "cc-flow", "list-activity-choices", "P", "queue-contact", "channelType"],  # 31
    ("versions", "list"): ["cc-flow-versions", "list", "P", "F"],  # 32
    ("versions", "get"): ["cc-flow-versions", "show", "P", "F", "V"],  # 33
    ("versions", "latest"): ["cc-flow-versions", "show-latest", "P", "F"],  # 34
    ("versions", "draft"): ["cc-flow-versions", "show-draft", "P", "F"],  # 35
    ("versions", "all"): ["cc-flow-versions", "list-all", "P"],  # 36
    ("versions", "all-latest"): ["cc-flow-versions", "list-all-latest", "P"],  # 37
    ("tracing", "interaction"): ["cc-flow-tracing", "show-interaction", "P", "F", "V", "I"],  # 38
    ("tracing", "traces"): ["cc-flow-tracing", "list-traces", "P", "F", "V", "I"],  # 39
    ("tracing", "traces-decrypt"): [
        "cc-flow-tracing", "list-traces-decrypted", "P", "F", "V", "I", "--process-id", "V"],  # 40
    ("tracing", "analytics"): ["cc-flow-tracing", "show-analytics", "P", "F", "V"],  # 41
    ("tracing", "interactions"): ["cc-flow-tracing", "list-interactions", "P", "F"],  # 42
    ("prefs", "list"): ["cc-flow-prefs", "list", "P", "F"],  # 43
    ("prefs", "tags"): ["cc-flow-prefs", "list-tags", "P", "F"],  # 47
    ("prefs", "tag-history"): ["cc-flow-prefs", "list-tag-history", "P", "F"],  # 48
    ("templates", "get"): ["cc-flow-templates", "show", "T"],  # 49
    ("templates", "list"): ["cc-flow-templates", "list"],  # 50
    ("resource-collections", "list"): ["cc-flow-projects", "list-resource-collections"],  # 51
    ("connectors", "get"): ["cc-flow-connectors", "show", "P", "CONNECTOR_ID"],  # 52
    ("connectors", "list"): ["cc-flow-connectors", "list", "P"],  # 53
    ("projects", "get"): ["cc-flow-projects", "show", "P"],  # 54
    ("projects", "list"): ["cc-flow-projects", "list"],  # 55
    ("user-prefs", "get"): ["cc-flow-projects", "show-user-preferences"],  # 56
    ("util", "build-info"): ["cc-flow-store", "show-build-info"],  # 58
    ("util", "health"): ["cc-flow-store", "show-health"],  # 59
    ("util", "whoami"): ["cc-flow-store", "show-current-user"],  # 60
}

# Read-only operations that legitimately fail on the system-provisioned project
# (wxcc verified these live 2026-07-12; docs/merge/flow-store-host-map.md
# § Expected service errors re-measured them on 2026-10-19).
API_TOLERATE_404 = {("projects", "get"), ("connectors", "list"), ("connectors", "get")}
# Read-only operations the server may answer with a 500 (validate-id on some
# drafts; all-latest org-wide, host map row 37). wxcc printed a "Warning:"
# banner first; wxcli does not carry it (command map rows 25 and 37), so the
# tests tolerate the server error and assert only that the CLI did not crash.
API_WARN = {("versions", "all-latest"), ("flows-v2", "validate-id")}
API_SKIP_INTERACTION = {
    ("tracing", "analytics"), ("tracing", "interaction"), ("tracing", "interactions"),
    ("tracing", "traces"), ("tracing", "traces-decrypt"),
}
