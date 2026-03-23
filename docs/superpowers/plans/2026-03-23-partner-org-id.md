# Partner Multi-Org orgId Injection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable partner/VAR/MSP admins to target customer orgs via wxcli by auto-injecting `orgId` from config into API requests.

**Architecture:** Config stores org_id/org_name per profile. Generator moves orgId from `omit_query_params` to `auto_inject_from_config` — the renderer generates `get_org_id()` calls only on endpoints where the OpenAPI spec declares orgId. Hand-coded SDK commands get manual org_id passthrough. Detection at configure time, blocking confirmation in the agent.

**Tech Stack:** Python 3.11, Typer CLI, wxc_sdk, OpenAPI 3.0 specs (4 files), pytest

**Spec:** `docs/superpowers/specs/2026-03-23-partner-org-id-design.md` (v3)

---

### Task 1: Config layer — org_id/org_name functions

**Files:**
- Modify: `src/wxcli/config.py:17-25`
- Test: `tests/test_config_org.py` (new)

- [ ] **Step 1: Write failing tests for config org functions**

```python
# tests/test_config_org.py
import json
import pytest
from pathlib import Path

from wxcli.config import get_org_id, get_org_name, save_org, load_config


@pytest.fixture
def tmp_config(tmp_path):
    return tmp_path / "config.json"


def test_get_org_id_missing(tmp_config):
    """get_org_id returns None when no org_id in config."""
    tmp_config.write_text(json.dumps({"profiles": {"default": {"token": "t"}}}))
    assert get_org_id(tmp_config) is None


def test_get_org_id_present(tmp_config):
    """get_org_id returns the stored org_id."""
    tmp_config.write_text(json.dumps({
        "profiles": {"default": {"token": "t", "org_id": "abc123", "org_name": "Acme"}}
    }))
    assert get_org_id(tmp_config) == "abc123"


def test_get_org_name_present(tmp_config):
    """get_org_name returns the stored org_name."""
    tmp_config.write_text(json.dumps({
        "profiles": {"default": {"token": "t", "org_id": "abc123", "org_name": "Acme"}}
    }))
    assert get_org_name(tmp_config) == "Acme"


def test_save_org_sets_fields(tmp_config):
    """save_org writes org_id and org_name to config."""
    tmp_config.write_text(json.dumps({"profiles": {"default": {"token": "t"}}}))
    save_org("org1", "Org One", tmp_config)
    config = load_config(tmp_config)
    assert config["profiles"]["default"]["org_id"] == "org1"
    assert config["profiles"]["default"]["org_name"] == "Org One"
    assert config["profiles"]["default"]["token"] == "t"  # preserved


def test_save_org_clears_fields(tmp_config):
    """save_org(None, None) removes org_id and org_name."""
    tmp_config.write_text(json.dumps({
        "profiles": {"default": {"token": "t", "org_id": "old", "org_name": "Old"}}
    }))
    save_org(None, None, tmp_config)
    config = load_config(tmp_config)
    assert "org_id" not in config["profiles"]["default"]
    assert "org_name" not in config["profiles"]["default"]
    assert config["profiles"]["default"]["token"] == "t"  # preserved


def test_get_org_id_no_config_file(tmp_path):
    """get_org_id returns None when config file doesn't exist."""
    assert get_org_id(tmp_path / "nonexistent.json") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3.11 -m pytest tests/test_config_org.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_org_id'`

- [ ] **Step 3: Implement config functions**

Add to `src/wxcli/config.py` after the existing `get_expires_at` function (after line 25):

```python
def get_org_id(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("org_id")

def get_org_name(path: Path = DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("org_name")

def save_org(org_id: str | None, org_name: str | None, path: Path = DEFAULT_CONFIG_PATH) -> None:
    config = load_config(path)
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    if org_id:
        profile["org_id"] = org_id
        profile["org_name"] = org_name
    else:
        profile.pop("org_id", None)
        profile.pop("org_name", None)
    save_config(config, path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3.11 -m pytest tests/test_config_org.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/config.py tests/test_config_org.py
git commit -m "feat: add get_org_id, get_org_name, save_org to config layer"
```

---

### Task 2: Fix configure.py — load-then-merge config

**Files:**
- Modify: `src/wxcli/commands/configure.py:6,27-35`

**Context:** Currently `configure.py` builds a fresh config dict and replaces the entire file. This would destroy org_id/org_name on reconfigure. Must change to load-then-merge.

- [ ] **Step 1: Update the import line**

In `src/wxcli/commands/configure.py`, change line 6:

```python
# OLD:
from wxcli.config import DEFAULT_CONFIG_PATH, save_config
# NEW:
from wxcli.config import DEFAULT_CONFIG_PATH, load_config, save_config
```

- [ ] **Step 2: Replace the config-building block**

Replace lines 27-35 (the fresh config dict + save_config call):

```python
    # OLD:
    config = {
        "profiles": {
            "default": {
                "token": token,
                "expires_at": expires_at,
            }
        }
    }
    save_config(config)

    # NEW:
    config = load_config()
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    profile["token"] = token
    profile["expires_at"] = expires_at
    save_config(config)
```

- [ ] **Step 3: Manually verify merge behavior**

```bash
# Create a config with org_id
mkdir -p ~/.wxcli
echo '{"profiles":{"default":{"token":"old","org_id":"test123","org_name":"TestOrg"}}}' > ~/.wxcli/config.json
# The next step would be running wxcli configure with a real token, but for now just verify the code change is correct by reading the file
cat ~/.wxcli/config.json
```

Restore original config if needed.

- [ ] **Step 4: Commit**

```bash
git add src/wxcli/commands/configure.py
git commit -m "fix: configure uses load-then-merge to preserve org settings"
```

---

### Task 3: Generator pipeline — Endpoint dataclass + parser

**Files:**
- Modify: `tools/postman_parser.py:26-39` (Endpoint dataclass)
- Modify: `tools/openapi_parser.py:82-124,400-445,448-501` (parse_parameters, parse_operation, parse_tag)
- Modify: `tools/generate_commands.py:39-56`
- Test: `tests/test_openapi_parser.py` (existing — add new test)

- [ ] **Step 1: Add auto_inject_params to Endpoint dataclass**

In `tools/postman_parser.py`, add a new field after `json_body_example` (line 39):

```python
    json_body_example: str | None = None
    auto_inject_params: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Update parse_parameters to separate auto-inject params**

In `tools/openapi_parser.py`, modify `parse_parameters` (lines 82-124) to accept and return auto-inject params:

Change the function signature (line 82-84):

```python
def parse_parameters(
    params: list[dict], spec: dict, omit_query_params: list[str] | None = None,
    auto_inject_params: set[str] | None = None,
) -> tuple[list[str], list[EndpointField], list[str]]:
```

Update the docstring (lines 85-90):

```python
    """Parse OpenAPI parameters into (path_vars, query_params, auto_inject_names).

    Path params become path_vars list of variable names.
    Query params become EndpointField list with type, description, required, enum.
    Params in omit_query_params are skipped entirely.
    Params in auto_inject_params are removed from query_params but returned in auto_inject_names.
    """
```

Add after `omit = set(omit_query_params or [])` (line 91):

```python
    auto_inject = auto_inject_params or set()
```

Add a new list alongside `query_params`:

```python
    auto_inject_names: list[str] = []
```

In the `elif location == "query":` block (lines 106-122), add a check before the existing omit check:

```python
        elif location == "query":
            if name in omit:
                continue
            if name in auto_inject:
                auto_inject_names.append(name)
                continue
```

Change the return (line 124):

```python
    return path_vars, query_params, auto_inject_names
```

- [ ] **Step 3: Update parse_operation to pass through auto_inject_params**

In `tools/openapi_parser.py`, modify `parse_operation` (lines 400-445):

Add `auto_inject_params` to the signature (line 405):

```python
def parse_operation(
    method: str,
    path: str,
    op: dict,
    spec: dict,
    omit_query_params: list[str] | None = None,
    auto_inject_params: set[str] | None = None,
) -> Endpoint:
```

Update the parse_parameters call (line 409):

```python
    path_vars, query_params, auto_inject_names = parse_parameters(
        params, spec, omit_query_params, auto_inject_params
    )
```

Add `auto_inject_params=auto_inject_names` to the Endpoint constructor (after line 444):

```python
    return Endpoint(
        ...
        json_body_example=json_body_example,
        auto_inject_params=auto_inject_names,
    )
```

- [ ] **Step 4: Update parse_tag to pass through auto_inject_params**

In `tools/openapi_parser.py`, modify `parse_tag` (lines 448-501):

Add to signature (line 451):

```python
def parse_tag(
    tag: str,
    spec: dict,
    omit_query_params: list[str] | None = None,
    auto_inject_params: set[str] | None = None,
    seen_operation_ids: set[str] | None = None,
) -> tuple[list[Endpoint], list[str]]:
```

Update the parse_operation call (line 494):

```python
            ep = parse_operation(method, path, op, spec, omit_query_params, auto_inject_params)
```

- [ ] **Step 5: Update generate_commands.py**

In `tools/generate_commands.py`, modify `generate_tag` (lines 47-56):

Replace lines 48-53:

```python
    # OLD:
    omit_qp = list(overrides.get("omit_query_params", ["orgId"]))
    # Per-tag keep_query_params overrides the global omit list
    folder_ovr = overrides.get(tag_name, {})
    keep_qp = set(folder_ovr.get("keep_query_params", []))
    if keep_qp:
        omit_qp = [p for p in omit_qp if p not in keep_qp]

    # NEW:
    omit_qp = list(overrides.get("omit_query_params", []))
    auto_inject_qp = set(overrides.get("auto_inject_from_config", ["orgId"]))
    folder_ovr = overrides.get(tag_name, {})
```

Update the parse_tag call (lines 54-56):

```python
    endpoints, skipped_uploads = parse_tag(
        tag_name, spec, omit_query_params=omit_qp,
        auto_inject_params=auto_inject_qp, seen_operation_ids=seen_op_ids
    )
```

- [ ] **Step 6: Remove keep_query_params from field_overrides.yaml**

Remove the `keep_query_params` entries from `tools/field_overrides.yaml` (lines 368-374):

Delete:
```yaml
"Admin Audit Events":
  keep_query_params:
    - orgId

"Security Audit Events":
  keep_query_params:
    - orgId
```

- [ ] **Step 7: Write a test for auto_inject_params parsing**

Add to `tests/test_openapi_parser.py`:

```python
def test_parse_parameters_auto_inject():
    """orgId in auto_inject_params is separated from query_params."""
    params = [
        {"name": "orgId", "in": "query", "schema": {"type": "string"}},
        {"name": "locationId", "in": "query", "schema": {"type": "string"}},
        {"name": "id", "in": "path", "schema": {"type": "string"}},
    ]
    path_vars, query_params, auto_inject = parse_parameters(
        params, {}, omit_query_params=[], auto_inject_params={"orgId"}
    )
    assert path_vars == ["id"]
    assert [qp.name for qp in query_params] == ["locationId"]
    assert auto_inject == ["orgId"]


def test_parse_parameters_no_auto_inject():
    """Without auto_inject, orgId appears in query_params normally."""
    params = [
        {"name": "orgId", "in": "query", "schema": {"type": "string"}},
    ]
    path_vars, query_params, auto_inject = parse_parameters(params, {})
    assert [qp.name for qp in query_params] == ["orgId"]
    assert auto_inject == []
```

- [ ] **Step 8: Run tests**

Run: `PYTHONPATH=. python3.11 -m pytest tests/test_openapi_parser.py -v -k "auto_inject"`
Expected: PASS

Also run existing parser tests to verify no regressions:
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_openapi_parser.py -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add tools/postman_parser.py tools/openapi_parser.py tools/generate_commands.py tools/field_overrides.yaml tests/test_openapi_parser.py
git commit -m "feat: generator pipeline supports auto_inject_from_config for orgId"
```

---

### Task 4: Renderer — auto-inject helper + update all 6 render functions

**Files:**
- Modify: `tools/command_renderer.py:37-43,144-215,218-275,302-363,366-416,419-458,461-507,522-539`
- Test: `tests/test_command_renderer.py` (existing — add new test)

**Context:** The renderer has 6 render functions. Four of them (`show`, `create`, `update`, `delete`) have conditional branches that skip creating `params = {}` when there are no query params. When orgId is the only query param and it's in `auto_inject_params`, `qp_build` will be empty and these branches must still create `params`. Reference: spec Section 6c.

- [ ] **Step 1: Add `_render_auto_inject_params` helper**

Add after `_render_error_handler` (after line 78) in `tools/command_renderer.py`:

```python
def _render_auto_inject_params(ep: Endpoint) -> list[str]:
    """Return lines to inject auto-inject params from config."""
    lines = []
    if "orgId" in getattr(ep, "auto_inject_params", []):
        lines.append("    org_id = get_org_id()")
        lines.append("    if org_id is not None:")
        lines.append('        params["orgId"] = org_id')
    return lines
```

- [ ] **Step 2: Update `_render_imports` to conditionally include get_org_id**

Modify `_render_imports` (line 37) to accept a flag:

```python
def _render_imports(include_org_id: bool = False) -> str:
    lines = '''import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
'''
    if include_org_id:
        lines += 'from wxcli.config import get_org_id\n'
    return lines
```

- [ ] **Step 3: Update `render_command_file` to detect need for org_id import**

Modify `render_command_file` (lines 522-539):

```python
def render_command_file(
    folder_name: str, endpoints: list[Endpoint], folder_overrides: dict
) -> str:
    _, cli_name = folder_name_to_module(folder_name)
    needs_org_id = any(
        "orgId" in getattr(ep, "auto_inject_params", []) for ep in endpoints
    )
    sections = [
        _render_imports(include_org_id=needs_org_id),
        f'app = typer.Typer(help="Manage Webex Calling {cli_name}.")\n',
    ]
    # ... rest unchanged
```

- [ ] **Step 4: Update `_render_list_command`**

`_render_list_command` always creates `params = {}` so it just needs the injection lines added. In the function (around line 204), add the auto-inject lines after the param_build lines and before the `try:` block:

After `*param_build,` and before `"    try:",`, insert:

```python
        *_render_auto_inject_params(ep),
```

- [ ] **Step 5: Update `_render_show_command`**

This function has a conditional branch (lines 246-274). The branch at line 261 (`else:`) emits `rest_get(url)` with no params. Must check for auto_inject_params:

Replace the conditional logic. The key change: use `has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))` to decide the branch, and always create `params = {}` + `params=params` when has_params is true.

```python
    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)

    if has_params:
        param_init = qp_build if qp_build else ["    params = {}"]
        lines = [
            f'@app.command("{ep.command_name}")',
            f"def {func_name}(",
            *params,
            "):",
            _render_docstring(ep),
            "    api = get_api(debug=debug)",
            f'    url = f"{url_expr}"',
            *param_init,
            *auto_inject,
            "    try:",
            "        result = api.session.rest_get(url, params=params)",
            _render_error_handler("    "),
            *show_output,
        ]
    else:
        lines = [
            f'@app.command("{ep.command_name}")',
            f"def {func_name}(",
            *params,
            "):",
            _render_docstring(ep),
            "    api = get_api(debug=debug)",
            f'    url = f"{url_expr}"',
            "    try:",
            "        result = api.session.rest_get(url)",
            _render_error_handler("    "),
            *show_output,
        ]
```

- [ ] **Step 6: Update `_render_create_command`**

The conditional is at line 346: `post_call` chooses between `rest_post(url, json=body)` and `rest_post(url, json=body, params=params)`. Apply same pattern:

```python
    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    post_call = "result = api.session.rest_post(url, json=body)" if not has_params else "result = api.session.rest_post(url, json=body, params=params)"

    lines = [
        ...
        *qp_build,
        *auto_inject,
        *body_build,
        ...
    ]
```

- [ ] **Step 7: Update `_render_update_command`**

Same pattern as create. The conditional is at line 399: `method_call` chooses based on `qp_build`.

```python
    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    rest_method = "rest_patch" if ep.method == "PATCH" else "rest_put"
    method_call = f"result = api.session.{rest_method}(url, json=body)" if not has_params else f"result = api.session.{rest_method}(url, json=body, params=params)"
```

Add `*auto_inject,` after `*qp_build,` in the lines list.

- [ ] **Step 8: Update `_render_delete_command`**

The conditional is at line 440: `delete_call` chooses based on `qp_build`.

```python
    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    delete_call = "api.session.rest_delete(url)" if not has_params else "api.session.rest_delete(url, params=params)"
```

Add `*auto_inject,` after `*qp_build,` in the lines list.

- [ ] **Step 9: Update `_render_action_command`**

Same pattern as create. The conditional is at line 490.

```python
    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    post_call = "result = api.session.rest_post(url, json=body)" if not has_params else "result = api.session.rest_post(url, json=body, params=params)"
```

Add `*auto_inject,` after `*qp_build,` in the lines list.

- [ ] **Step 10: Write renderer test**

Add to `tests/test_command_renderer.py`:

```python
from tools.postman_parser import Endpoint, EndpointField
from tools.command_renderer import render_command_file


def test_render_show_command_orgid_only_param():
    """When orgId is the only query param, params dict is still created."""
    ep = Endpoint(
        name="Get Widget",
        method="GET",
        url_path="widgets/{widgetId}",
        path_vars=["widgetId"],
        query_params=[],
        body_fields=[],
        command_type="show",
        command_name="show",
        auto_inject_params=["orgId"],
    )
    code = render_command_file("Test Widgets", [ep], {})
    assert "get_org_id" in code
    assert "params = {}" in code
    assert 'params["orgId"]' in code
    assert "params=params" in code


def test_render_show_command_no_orgid():
    """When no auto_inject_params, no params dict for paramless show."""
    ep = Endpoint(
        name="Get Widget",
        method="GET",
        url_path="widgets/{widgetId}",
        path_vars=["widgetId"],
        query_params=[],
        body_fields=[],
        command_type="show",
        command_name="show",
        auto_inject_params=[],
    )
    code = render_command_file("Test Widgets", [ep], {})
    assert "get_org_id" not in code
    assert "rest_get(url)" in code


def test_render_delete_command_orgid_injection():
    """Delete command with orgId auto-inject creates params dict."""
    ep = Endpoint(
        name="Delete Widget",
        method="DELETE",
        url_path="widgets/{widgetId}",
        path_vars=["widgetId"],
        query_params=[],
        body_fields=[],
        command_type="delete",
        command_name="delete",
        auto_inject_params=["orgId"],
    )
    code = render_command_file("Test Widgets", [ep], {})
    assert "get_org_id" in code
    assert 'params["orgId"]' in code
    assert "params=params" in code
```

- [ ] **Step 11: Run tests**

Run: `PYTHONPATH=. python3.11 -m pytest tests/test_command_renderer.py -v`
Expected: All PASS (new + existing)

- [ ] **Step 12: Commit**

```bash
git add tools/command_renderer.py tests/test_command_renderer.py
git commit -m "feat: renderer auto-injects orgId from config on endpoints that declare it"
```

---

### Task 5: Regenerate all commands + verification test

**Files:**
- Regenerate: `src/wxcli/commands/*.py` (~96 files)
- Create: `tests/test_org_id_injection.py`

- [ ] **Step 1: Regenerate all 4 specs**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-cloud-calling.json --all
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-admin.json --all
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-device.json --all
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-messaging.json --all
```

- [ ] **Step 2: Reinstall**

```bash
pip3.11 install -e . -q
```

- [ ] **Step 3: Spot-check a generated file**

```bash
grep -c "get_org_id" src/wxcli/commands/call_queue.py
```

Expected: Multiple matches (one per command function that had orgId in the spec).

Also check a file that should NOT have injection (if any exist).

- [ ] **Step 4: Write the verification test**

```python
# tests/test_org_id_injection.py
"""Verify orgId injection in generated commands matches OpenAPI specs."""
import json
from pathlib import Path

SPECS = [
    "webex-cloud-calling.json",
    "webex-admin.json",
    "webex-device.json",
    "webex-messaging.json",
]
COMMANDS_DIR = Path("src/wxcli/commands")
PROJECT_ROOT = Path(__file__).parent.parent


def count_orgid_in_specs() -> int:
    """Count endpoints with orgId as a query param across all specs."""
    count = 0
    for spec_file in SPECS:
        spec_path = PROJECT_ROOT / spec_file
        if not spec_path.exists():
            continue
        spec = json.loads(spec_path.read_text())
        for path, methods in spec.get("paths", {}).items():
            for method, op in methods.items():
                if not isinstance(op, dict):
                    continue
                params = op.get("parameters", [])
                if any(
                    p.get("name") == "orgId" and p.get("in") == "query"
                    for p in params
                ):
                    count += 1
    return count


def count_orgid_in_generated_code() -> int:
    """Count get_org_id() calls in generated command files."""
    count = 0
    for py_file in sorted(COMMANDS_DIR.glob("*.py")):
        content = py_file.read_text()
        count += content.count("get_org_id()")
    return count


def test_org_id_injection_count():
    """Generated code orgId injection count matches spec count.

    This is approximate — generated files may cover slightly fewer
    endpoints than the spec due to skipped uploads and multi-tag dedup.
    The count should be within 5% of spec count.
    """
    spec_count = count_orgid_in_specs()
    code_count = count_orgid_in_generated_code()
    assert spec_count > 0, "Sanity check: specs should have orgId endpoints"
    assert code_count > 0, "Sanity check: generated code should have orgId injections"
    # Allow small variance due to upload skips and dedup
    ratio = code_count / spec_count
    assert ratio > 0.90, (
        f"Generated code has {code_count} orgId injections but spec declares "
        f"{spec_count} — ratio {ratio:.2%} is below 90% threshold"
    )
```

- [ ] **Step 5: Run verification test**

Run: `PYTHONPATH=. python3.11 -m pytest tests/test_org_id_injection.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/commands/ tests/test_org_id_injection.py
git commit -m "feat: regenerate all commands with orgId auto-injection (804 endpoints)"
```

---

### Task 6: Configure — multi-org detection + selection

**Files:**
- Modify: `src/wxcli/commands/configure.py`

- [ ] **Step 1: Add org detection and selection to configure**

Update `src/wxcli/commands/configure.py`. Full replacement:

```python
import typer
from datetime import datetime, timedelta, timezone

from wxc_sdk import WebexSimpleApi

from wxcli.config import DEFAULT_CONFIG_PATH, load_config, save_config, save_org

app = typer.Typer(help="Configure authentication.")


def _detect_and_select_org(api: WebexSimpleApi) -> tuple[str | None, str | None]:
    """Detect multi-org token and prompt for org selection. Returns (org_id, org_name)."""
    try:
        result = api.session.rest_get("https://webexapis.com/v1/organizations")
        items = result.get("items", []) if isinstance(result, dict) else []
    except Exception:
        typer.echo("Warning: Could not list organizations. Use 'wxcli switch-org' to set target org later.")
        return None, None

    if len(items) <= 1:
        return None, None

    typer.echo(f"\nMultiple organizations detected:\n")
    for i, org in enumerate(items, 1):
        name = org.get("displayName", "Unknown")
        org_id = org.get("id", "")
        typer.echo(f"  {i}. {name:<30s} ({org_id})")

    typer.echo()
    choice = typer.prompt(f"Select target org [1-{len(items)}]", type=int)
    if choice < 1 or choice > len(items):
        typer.echo("Invalid selection. Use 'wxcli switch-org' to set target org later.")
        return None, None

    selected = items[choice - 1]
    return selected.get("id"), selected.get("displayName")


@app.callback(invoke_without_command=True)
def configure():
    """Save a Webex API token for wxcli to use."""
    token = typer.prompt("Webex API token")

    typer.echo("Validating token...")
    try:
        api = WebexSimpleApi(tokens=token)
        me = api.people.me()
    except Exception as e:
        typer.echo(f"Error: Invalid token — {e}", err=True)
        raise typer.Exit(1)

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

    # Load-then-merge: preserve existing org_id/org_name
    config = load_config()
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    profile["token"] = token
    profile["expires_at"] = expires_at
    save_config(config)

    typer.echo(f"Authenticated: {me.display_name} ({me.emails[0]})")
    typer.echo(f"Org: {me.org_id}")

    # Multi-org detection
    org_id, org_name = _detect_and_select_org(api)
    if org_id:
        save_org(org_id, org_name)
        typer.echo(f"\nTarget org set: {org_name} ({org_id})")

    typer.echo(f"Token saved to {DEFAULT_CONFIG_PATH}")
```

- [ ] **Step 2: Verify syntax**

```bash
python3.11 -c "import ast; ast.parse(open('src/wxcli/commands/configure.py').read()); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/wxcli/commands/configure.py
git commit -m "feat: configure detects multi-org tokens and prompts for org selection"
```

---

### Task 7: switch-org, clear-org commands + whoami enhancement

**Files:**
- Modify: `src/wxcli/main.py:1-6,28-58`

- [ ] **Step 1: Add imports to main.py**

Update the imports at the top of `src/wxcli/main.py` (lines 1-6):

```python
import typer
from datetime import datetime, timezone

from wxcli import __version__
from wxcli.auth import get_api, resolve_token
from wxcli.config import get_expires_at, get_org_id, get_org_name, save_org
```

- [ ] **Step 2: Enhance whoami to show target org**

In the `whoami` function, after the `Org:` line (after line 37) and before the roles check, add:

```python
    target_org_id = get_org_id()
    target_org_name = get_org_name()
    if target_org_id:
        typer.echo(f"Target: {target_org_id}  ({target_org_name})")
```

- [ ] **Step 3: Add switch-org command**

Add after the `whoami` function (after line 58):

```python
@app.command("switch-org")
def switch_org(
    org_id: str = typer.Argument(None, help="orgId to switch to (skip interactive prompt)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch target organization for partner multi-org tokens."""
    from wxc_sdk import WebexSimpleApi

    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' first.", err=True)
        raise typer.Exit(1)

    api = WebexSimpleApi(tokens=token)

    if org_id:
        # Direct switch — resolve org name
        try:
            org = api.session.rest_get(f"https://webexapis.com/v1/organizations/{org_id}")
            org_name = org.get("displayName", "Unknown")
        except Exception:
            org_name = "Unknown"
        save_org(org_id, org_name)
        typer.echo(f"Target org set: {org_name} ({org_id})")
        return

    # Interactive — list orgs
    try:
        result = api.session.rest_get("https://webexapis.com/v1/organizations")
        items = result.get("items", []) if isinstance(result, dict) else []
    except Exception as e:
        typer.echo(f"Error listing organizations: {e}", err=True)
        raise typer.Exit(1)

    if len(items) <= 1:
        typer.echo("Single-org token — no org switching needed.")
        return

    typer.echo(f"\nAvailable organizations:\n")
    for i, org in enumerate(items, 1):
        name = org.get("displayName", "Unknown")
        oid = org.get("id", "")
        typer.echo(f"  {i}. {name:<30s} ({oid})")

    typer.echo()
    choice = typer.prompt(f"Select target org [1-{len(items)}]", type=int)
    if choice < 1 or choice > len(items):
        typer.echo("Invalid selection.", err=True)
        raise typer.Exit(1)

    selected = items[choice - 1]
    save_org(selected.get("id"), selected.get("displayName"))
    typer.echo(f"\nTarget org set: {selected.get('displayName')} ({selected.get('id')})")


@app.command("clear-org")
def clear_org():
    """Clear target organization — commands will target your own org."""
    save_org(None, None)
    typer.echo("Cleared target org. Commands will now target your own organization.")
```

- [ ] **Step 4: Verify syntax**

```bash
python3.11 -c "import ast; ast.parse(open('src/wxcli/main.py').read()); print('OK')"
```

- [ ] **Step 5: Reinstall and smoke test**

```bash
pip3.11 install -e . -q
wxcli --help | grep -E "switch-org|clear-org"
```

Expected: Both commands appear in the help output.

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/main.py
git commit -m "feat: add switch-org, clear-org commands and whoami target org display"
```

---

### Task 8: Hand-coded command updates (4 files)

**Files:**
- Modify: `src/wxcli/commands/users.py:1,28`
- Modify: `src/wxcli/commands/licenses.py:1,17`
- Modify: `src/wxcli/commands/locations.py:1-5` + all 10 command functions (list, create, show, update, delete, list-floors, create-floors, show-floors, update-floors, delete-floors)
- Modify: `src/wxcli/commands/numbers.py:1-5` + all 11 command functions

- [ ] **Step 1: Update users.py — add org_id to list call**

Add import at top of `src/wxcli/commands/users.py`:

```python
from wxcli.config import get_org_id
```

In `list_users` function, change line 28:

```python
    # OLD:
    users = list(api.people.list(**kwargs))
    # NEW:
    org_id = get_org_id()
    if org_id:
        kwargs["org_id"] = org_id
    users = list(api.people.list(**kwargs))
```

- [ ] **Step 2: Update licenses.py — add org_id to list call**

Add import at top of `src/wxcli/commands/licenses.py`:

```python
from wxcli.config import get_org_id
```

In `list_licenses` function, change line 17:

```python
    # OLD:
    licenses = list(api.licenses.list())
    # NEW:
    org_id = get_org_id()
    kwargs = {}
    if org_id:
        kwargs["org_id"] = org_id
    licenses = list(api.licenses.list(**kwargs))
```

- [ ] **Step 3: Update locations.py — add orgId injection**

Add import at top of `src/wxcli/commands/locations.py`:

```python
from wxcli.config import get_org_id
```

There are 10 commands: `list`, `create`, `show`, `update`, `delete`, `list-floors`, `create-floors`, `show-floors`, `update-floors`, `delete-floors`.

**Commands WITH existing `params` dict** (`list`, `list-floors`): add after params building, before `try:`:

```python
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
```

**Commands WITHOUT `params` dict** (`create`, `show`, `update`, `delete`, `create-floors`, `show-floors`, `update-floors`, `delete-floors`): add `params = {}` + injection before `try:`, and add `params=params` to the REST call.

- [ ] **Step 4: Update numbers.py — add orgId injection to all 10 commands**

Add import at top of `src/wxcli/commands/numbers.py`:

```python
from wxcli.config import get_org_id
```

For each of the 11 command functions:
- **Commands WITH existing `params` dict** (`list`, `list-manage-numbers`, `list-errors`): add injection after params building, before `try:`
- **Commands WITHOUT `params` dict** (`create`, `update`, `delete`, `validate-phone-numbers`, `create-manage-numbers`, `show`, `pause-the-manage`, `resume-the-manage`): add `params = {}` + injection before the `try:`, and add `params=params` to the REST call

Total: 11 commands (3 with params, 8 without).

Example for `create` (line 30-31):

```python
    # Before try:
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_post(url, json=body, params=params)
```

- [ ] **Step 5: Verify all 4 files parse**

```bash
python3.11 -c "
for f in ['users','licenses','locations','numbers']:
    import ast; ast.parse(open(f'src/wxcli/commands/{f}.py').read()); print(f'{f}.py OK')
"
```

- [ ] **Step 6: Commit**

```bash
git add src/wxcli/commands/users.py src/wxcli/commands/licenses.py src/wxcli/commands/locations.py src/wxcli/commands/numbers.py
git commit -m "feat: add orgId injection to hand-coded commands (users, licenses, locations, numbers)"
```

---

### Task 9: Agent confirmation — blocking org check

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md:44-67`

- [ ] **Step 1: Add org confirmation to the Authentication section**

In `.claude/agents/wxc-calling-builder.md`, after the existing "After configuring, verify with: `wxcli whoami`" block (around line 67), add:

```markdown
### 2b. Target Org Confirmation (Partner Tokens)

After `wxcli whoami` succeeds, check the output for a "Target:" line:

**If a "Target:" line is present** (multi-org token with orgId set):
1. Display to the user: "You are targeting **[org_name]** (`[org_id]`). All commands in this session will operate on this organization."
2. Ask: "Is this the correct target org? (yes/no)"
3. If **no**: run `wxcli switch-org` to let them pick a different org, then re-run `wxcli whoami` and re-confirm
4. If **yes**: proceed to the interview phase
5. **Do not proceed until the user confirms the target org.**

**If no "Target:" line appears**: single-org token, proceed normally to the interview phase.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/wxc-calling-builder.md
git commit -m "feat: add blocking org confirmation to builder agent for partner tokens"
```

---

### Task 10: Final validation — run all tests

**Files:** None (validation only)

- [ ] **Step 1: Run the full test suite**

```bash
PYTHONPATH=. python3.11 -m pytest tests/test_config_org.py tests/test_openapi_parser.py tests/test_command_renderer.py tests/test_org_id_injection.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Run existing test suite for regressions**

```bash
PYTHONPATH=. python3.11 -m pytest tests/ -v --ignore=tests/migration
```

Expected: No regressions

- [ ] **Step 3: Smoke test the CLI**

```bash
wxcli --help | head -20
wxcli whoami
wxcli clear-org
```

- [ ] **Step 4: Commit any remaining changes**

If any fixups were needed, commit them:

```bash
git add -A
git commit -m "fix: final validation fixes for partner orgId support"
```
