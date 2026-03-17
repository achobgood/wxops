# Auto-Generation Tool Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a code generator that reads Postman collection JSON and produces wxcli Typer command files using raw HTTP via the wxc_sdk session.

**Architecture:** Four components — a Postman JSON parser, a Typer command renderer, a YAML field-override file, and a CLI script that ties them together. Parser normalizes Postman requests into Endpoint dataclasses. Renderer uses string templates to emit `.py` files. Override file encodes required fields and defaults discovered through live testing.

**Tech Stack:** Python 3.11, PyYAML, dataclasses, string formatting (no Jinja — overkill for this).

**Spec:** `docs/superpowers/specs/2026-03-17-auto-gen-tool-design.md`

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tools/__init__.py` | Package marker |
| Create | `tools/postman_parser.py` | Parse Postman JSON → list of Endpoint dataclasses |
| Create | `tools/command_renderer.py` | Render Endpoint list → complete .py command file |
| Create | `tools/field_overrides.yaml` | Known required fields, defaults, skip/column config |
| Create | `tools/generate_commands.py` | CLI entry point: --folder, --all, --dry-run, --list-folders |
| Create | `tests/test_postman_parser.py` | Unit tests for parser |
| Create | `tests/test_command_renderer.py` | Unit tests for renderer |

---

### Task 1: Postman Parser — Data Models

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/postman_parser.py`
- Create: `tests/test_postman_parser.py`

- [ ] **Step 1: Write test for EndpointField and Endpoint dataclasses**

```python
# tests/test_postman_parser.py
from tools.postman_parser import EndpointField, Endpoint

def test_endpoint_field_creation():
    f = EndpointField(
        name="businessSchedule",
        python_name="business-schedule",
        field_type="string",
        description="Business schedule name",
        required=False,
        default=None,
        enum_example=None,
    )
    assert f.name == "businessSchedule"
    assert f.python_name == "business-schedule"
    assert f.field_type == "string"

def test_endpoint_creation():
    ep = Endpoint(
        name="Create a Call Park",
        method="POST",
        url_path="telephony/config/locations/{locationId}/callParks",
        path_vars=["locationId"],
        query_params=[],
        body_fields=[],
        command_type="create",
        command_name="create",
        response_list_key=None,
    )
    assert ep.method == "POST"
    assert ep.command_type == "create"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_postman_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: Create the dataclasses**

```python
# tools/__init__.py
(empty)

# tools/postman_parser.py
from dataclasses import dataclass, field
from typing import Any

@dataclass
class EndpointField:
    name: str
    python_name: str
    field_type: str
    description: str
    required: bool = False
    default: Any = None
    enum_example: str | None = None

@dataclass
class Endpoint:
    name: str
    method: str
    url_path: str
    path_vars: list[str]
    query_params: list[EndpointField]
    body_fields: list[EndpointField]
    command_type: str
    command_name: str
    response_list_key: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_postman_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/ tests/test_postman_parser.py
git commit -m "feat(gen): data models for Endpoint and EndpointField"
```

---

### Task 2: Postman Parser — Body Parsing

**Files:**
- Modify: `tools/postman_parser.py`
- Modify: `tests/test_postman_parser.py`

- [ ] **Step 1: Write test for body field parsing**

```python
# append to tests/test_postman_parser.py
from tools.postman_parser import parse_body_fields

def test_parse_body_string_placeholder():
    body = '{"name": "<string>", "extension": "<string>"}'
    fields = parse_body_fields(body)
    assert len(fields) == 2
    assert fields[0].name == "name"
    assert fields[0].field_type == "string"
    assert fields[0].enum_example is None

def test_parse_body_boolean():
    body = '{"enabled": "<boolean>"}'
    fields = parse_body_fields(body)
    assert fields[0].field_type == "bool"

def test_parse_body_number():
    body = '{"maxAgents": "<number>"}'
    fields = parse_body_fields(body)
    assert fields[0].field_type == "number"

def test_parse_body_enum_value():
    body = '{"originatorType": "PEOPLE", "action": "EXIT"}'
    fields = parse_body_fields(body)
    assert fields[0].field_type == "string"
    assert fields[0].enum_example == "PEOPLE"
    assert fields[1].enum_example == "EXIT"

def test_parse_body_nested_object():
    body = '{"recall": {"option": "ALERT_PARKING_USER_ONLY"}}'
    fields = parse_body_fields(body)
    assert fields[0].field_type == "object"
    assert fields[0].name == "recall"

def test_parse_body_array():
    body = '{"agents": ["<string>", "<string>"]}'
    fields = parse_body_fields(body)
    assert fields[0].field_type == "array"

def test_parse_body_empty():
    fields = parse_body_fields("")
    assert fields == []
    fields = parse_body_fields(None)
    assert fields == []

def test_camel_to_kebab():
    from tools.postman_parser import camel_to_kebab
    assert camel_to_kebab("businessSchedule") == "business-schedule"
    assert camel_to_kebab("callParkId") == "call-park-id"
    assert camel_to_kebab("name") == "name"
    assert camel_to_kebab("orgId") == "org-id"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_postman_parser.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_body_fields'`

- [ ] **Step 3: Implement parse_body_fields and camel_to_kebab**

Add to `tools/postman_parser.py`:

```python
import json
import re

def camel_to_kebab(name: str) -> str:
    s = re.sub(r'([A-Z])', r'-\1', name).lower().lstrip('-')
    return s

def _infer_type(value: Any) -> tuple[str, str | None]:
    if isinstance(value, str):
        if value == "<string>":
            return "string", None
        if value == "<boolean>":
            return "bool", None
        if value == "<number>":
            return "number", None
        if re.match(r'^[A-Z][A-Z0-9_]+$', value):
            return "string", value
        return "string", None
    if isinstance(value, bool):
        return "bool", None
    if isinstance(value, (int, float)):
        return "number", None
    if isinstance(value, dict):
        return "object", None
    if isinstance(value, list):
        return "array", None
    return "string", None

def parse_body_fields(raw_body: str | None) -> list[EndpointField]:
    if not raw_body:
        return []
    try:
        parsed = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, dict):
        return []
    fields = []
    for key, value in parsed.items():
        field_type, enum_example = _infer_type(value)
        fields.append(EndpointField(
            name=key,
            python_name=camel_to_kebab(key),
            field_type=field_type,
            description="",
            enum_example=enum_example,
        ))
    return fields
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_postman_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/postman_parser.py tests/test_postman_parser.py
git commit -m "feat(gen): body field parser with type inference"
```

---

### Task 3: Postman Parser — Command Type Derivation + Full Endpoint Parsing

**Files:**
- Modify: `tools/postman_parser.py`
- Modify: `tests/test_postman_parser.py`

- [ ] **Step 1: Write tests for command type derivation and full request parsing**

```python
# append to tests/test_postman_parser.py
from tools.postman_parser import derive_command_type, parse_request, derive_response_list_key

def test_derive_command_type_list():
    assert derive_command_type("GET", ["telephony", "config", "locations", ":locationId", "callParks"], "Read the List of Call Parks") == "list"

def test_derive_command_type_show():
    assert derive_command_type("GET", ["telephony", "config", "locations", ":locationId", "callParks", ":callParkId"], "Get Details for a Call Park") == "show"

def test_derive_command_type_create():
    assert derive_command_type("POST", ["telephony", "config", "locations", ":locationId", "callParks"], "Create a Call Park") == "create"

def test_derive_command_type_update():
    assert derive_command_type("PUT", ["telephony", "config", "locations", ":locationId", "callParks", ":callParkId"], "Update a Call Park") == "update"

def test_derive_command_type_delete():
    assert derive_command_type("DELETE", ["telephony", "config", "locations", ":locationId", "callParks", ":callParkId"], "Delete a Call Park") == "delete"

def test_derive_command_type_settings_get():
    assert derive_command_type("GET", ["telephony", "config", "locations", ":locationId", "callParks", ":callParkId", "settings"], "Get Call Park Settings") == "settings-get"

def test_derive_command_type_settings_put():
    assert derive_command_type("PUT", ["telephony", "config", "locations", ":locationId", "callParks", ":callParkId", "settings"], "Update Call Park Settings") == "settings-update"

def test_derive_command_type_action():
    assert derive_command_type("POST", ["telephony", "config", "actions", "testCallRouting", "invoke"], "Test Call Routing") == "action"

def test_derive_response_list_key():
    assert derive_response_list_key(["telephony", "config", "locations", ":locationId", "callParks"]) == "callParks"
    assert derive_response_list_key(["telephony", "config", "autoAttendants"]) == "autoAttendants"

def test_parse_request_basic():
    request_data = {
        "name": "Create a Call Park",
        "request": {
            "method": "POST",
            "url": {
                "raw": "{{baseUrl}}/telephony/config/locations/:locationId/callParks",
                "path": ["telephony", "config", "locations", ":locationId", "callParks"],
                "variable": [{"key": "locationId", "description": "Location ID"}],
                "query": [{"key": "orgId", "value": "<string>", "description": "Org ID"}],
            },
            "body": {
                "mode": "raw",
                "raw": '{"name": "<string>", "recall": {"option": "ALERT_PARKING_USER_ONLY"}}',
            },
        },
    }
    ep = parse_request(request_data, omit_query_params=["orgId"])
    assert ep.name == "Create a Call Park"
    assert ep.method == "POST"
    assert ep.path_vars == ["locationId"]
    assert ep.command_type == "create"
    assert len(ep.body_fields) == 2
    assert len(ep.query_params) == 0  # orgId omitted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_postman_parser.py::test_derive_command_type_list -v`
Expected: FAIL

- [ ] **Step 3: Implement derive_command_type, derive_response_list_key, parse_request**

Add to `tools/postman_parser.py`:

```python
SETTINGS_KEYWORDS = {"settings", "service", "forwarding", "musicOnHold", "nightService",
                     "holidayService", "forcedForward", "strandedCalls"}

def derive_command_type(method: str, path: list[str], name: str) -> str:
    last_seg = path[-1] if path else ""
    is_path_var = last_seg.startswith(":")
    name_lower = name.lower()

    if method == "POST" and ("actions" in path or "invoke" in path):
        return "action"

    last_word = last_seg.lstrip(":")
    if last_word.lower() in {kw.lower() for kw in SETTINGS_KEYWORDS}:
        if method == "GET":
            return "settings-get"
        if method == "PUT":
            return "settings-update"

    if method == "GET":
        return "show" if is_path_var else "list"
    if method == "POST":
        return "create"
    if method in ("PUT", "PATCH"):
        return "update"
    if method == "DELETE":
        return "delete"
    return "action"

def derive_response_list_key(path: list[str]) -> str | None:
    for seg in reversed(path):
        if not seg.startswith(":"):
            return seg
    return None

def _derive_command_name(command_type: str, path: list[str], postman_name: str, seen_types: dict) -> str:
    base = command_type.replace("settings-get", "show").replace("settings-update", "update")
    if base == "action":
        words = postman_name.lower().replace("_", " ").split()
        slug = "-".join(words[:3])
        return slug

    count = seen_types.get(base, 0)
    seen_types[base] = count + 1
    if count == 0:
        return base

    for seg in reversed(path):
        if not seg.startswith(":") and seg not in ("config", "telephony", "locations", "v1"):
            suffix = camel_to_kebab(seg)
            return f"{base}-{suffix}"
    return f"{base}-{count}"

def parse_request(request_data: dict, omit_query_params: list[str] | None = None) -> Endpoint:
    omit = set(omit_query_params or [])
    r = request_data["request"]
    method = r["method"]
    url = r["url"]
    path = url.get("path", [])
    name = request_data.get("name", "")

    path_vars = [v["key"] for v in url.get("variable", [])]

    query_params = []
    seen_qp = set()
    for q in url.get("query", []):
        key = q["key"]
        if key in omit or key in seen_qp:
            continue
        seen_qp.add(key)
        desc = q.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("content", "")
        field_type = "number" if q.get("value") == "<number>" else "string"
        query_params.append(EndpointField(
            name=key, python_name=camel_to_kebab(key),
            field_type=field_type, description=str(desc)[:120],
        ))

    body_fields = []
    body = r.get("body", {})
    if body and body.get("mode") == "raw":
        body_fields = parse_body_fields(body.get("raw", ""))

    url_path = "/".join(seg.replace(":", "{").rstrip("}") + ("}" if seg.startswith(":") else "") for seg in path)
    command_type = derive_command_type(method, path, name)
    response_list_key = derive_response_list_key(path) if command_type == "list" else None

    return Endpoint(
        name=name,
        method=method,
        url_path=url_path,
        path_vars=path_vars,
        query_params=query_params,
        body_fields=body_fields,
        command_type=command_type,
        command_name="",  # set by caller using _derive_command_name
        response_list_key=response_list_key,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3.11 -m pytest tests/test_postman_parser.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add tools/postman_parser.py tests/test_postman_parser.py
git commit -m "feat(gen): command type derivation and full request parsing"
```

---

### Task 4: Postman Parser — Folder Parsing + Override Loading

**Files:**
- Modify: `tools/postman_parser.py`
- Modify: `tests/test_postman_parser.py`
- Create: `tools/field_overrides.yaml`

- [ ] **Step 1: Write test for folder parsing and override application**

```python
# append to tests/test_postman_parser.py
import os
from tools.postman_parser import parse_folder, load_overrides, apply_overrides

COLLECTION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "postman-webex-collections", "webex_cloud_calling.json"
)

def test_load_overrides():
    overrides = load_overrides(os.path.join(os.path.dirname(__file__), "..", "tools", "field_overrides.yaml"))
    assert "skip_folders" in overrides
    assert "omit_query_params" in overrides

def test_parse_folder_call_pickup():
    """Call Pickup is simple — 6 endpoints, clean CRUD."""
    import json
    with open(COLLECTION_PATH) as f:
        data = json.load(f)
    folders = data["collection"]["item"]
    pickup_folder = [f for f in folders if "Call Pickup" in f["name"]][0]
    endpoints = parse_folder(pickup_folder, omit_query_params=["orgId"])
    types = [ep.command_type for ep in endpoints]
    assert "list" in types
    assert "create" in types
    assert "show" in types
    assert "update" in types
    assert "delete" in types

def test_apply_overrides_required_fields():
    field = EndpointField(name="name", python_name="name", field_type="string", description="")
    overrides = {"create": {"required_fields": ["name"]}}
    fields = apply_overrides([field], "create", overrides)
    assert fields[0].required is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_postman_parser.py::test_parse_folder_call_pickup -v`
Expected: FAIL

- [ ] **Step 3: Implement parse_folder, load_overrides, apply_overrides + create field_overrides.yaml**

Add to `tools/postman_parser.py`:

```python
import yaml
from pathlib import Path

def load_overrides(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"skip_folders": [], "omit_query_params": ["orgId"]}
    with open(path) as f:
        return yaml.safe_load(f) or {}

def apply_overrides(fields: list[EndpointField], command_type: str, folder_overrides: dict) -> list[EndpointField]:
    cmd_overrides = folder_overrides.get(command_type, {})
    required = set(cmd_overrides.get("required_fields", []))
    defaults = cmd_overrides.get("defaults", {})
    for field in fields:
        if field.name in required:
            field.required = True
        if field.name in defaults:
            field.default = defaults[field.name]
    return fields

def parse_folder(folder: dict, omit_query_params: list[str] | None = None) -> list[Endpoint]:
    endpoints = []
    seen_types: dict[str, int] = {}
    for req in folder.get("item", []):
        body_mode = req.get("request", {}).get("body", {}).get("mode", "")
        if body_mode == "formdata":
            continue  # skip file upload endpoints
        ep = parse_request(req, omit_query_params=omit_query_params)
        ep.command_name = _derive_command_name(ep.command_type, ep.url_path.split("/"), ep.name, seen_types)
        endpoints.append(ep)
    return endpoints
```

Create `tools/field_overrides.yaml`:
```yaml
# Known required fields and defaults discovered during v2 live testing

"Features:  Auto Attendant":
  create:
    required_fields: [name, extension, businessHoursMenu, afterHoursMenu, businessSchedule]
    defaults:
      businessHoursMenu:
        greeting: DEFAULT
        extensionEnabled: true
        keyConfigurations:
          - key: "0"
            action: EXIT
      afterHoursMenu:
        greeting: DEFAULT
        extensionEnabled: true
        keyConfigurations:
          - key: "0"
            action: EXIT
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Extension", "extension"]
      - ["Enabled", "enabled"]

"Features:  Call Queue":
  create:
    required_fields: [name, callPolicies]
    defaults:
      callPolicies:
        routingType: PRIORITY_BASED
        policy: CIRCULAR
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Extension", "extension"]
      - ["Enabled", "enabled"]

"Features:  Call Park":
  create:
    required_fields: [name, recall]
    defaults:
      recall:
        option: ALERT_PARKING_USER_ONLY
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]

"Features:  Hunt Group":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Extension", "extension"]
      - ["Enabled", "enabled"]

"Features:  Call Pickup":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]

"Features:  Paging Group":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Extension", "extension"]
      - ["Enabled", "enabled"]

# Global settings
skip_folders:
  - "Beta *"
  - "* (2/2)"
  - "* Phase2"
  - "* Phase3"
  - "* Phase4"
  - "Call Settings For Me *"
  - "Read the Contact Center Extensions"

omit_query_params:
  - orgId
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3.11 -m pytest tests/test_postman_parser.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add tools/postman_parser.py tools/field_overrides.yaml tests/test_postman_parser.py
git commit -m "feat(gen): folder parsing, override loading, field_overrides.yaml"
```

---

### Task 5: Command Renderer

**Files:**
- Create: `tools/command_renderer.py`
- Create: `tests/test_command_renderer.py`

- [ ] **Step 1: Write test for rendering a complete command file**

```python
# tests/test_command_renderer.py
from tools.postman_parser import Endpoint, EndpointField
from tools.command_renderer import render_command_file, folder_name_to_module

def test_folder_name_to_module():
    assert folder_name_to_module("Features:  Call Park") == ("call_park", "call-park")
    assert folder_name_to_module("Call Routing") == ("call_routing", "call-routing")
    assert folder_name_to_module("DECT Devices Settings") == ("dect_devices_settings", "dect-devices-settings")

def test_render_minimal_file():
    endpoints = [
        Endpoint(
            name="List Call Parks",
            method="GET",
            url_path="telephony/config/locations/{locationId}/callParks",
            path_vars=["locationId"],
            query_params=[
                EndpointField(name="name", python_name="name", field_type="string", description="Filter by name"),
            ],
            body_fields=[],
            command_type="list",
            command_name="list",
            response_list_key="callParks",
        ),
    ]
    code = render_command_file("Test Group", endpoints, {})
    assert "import typer" in code
    assert "from wxcli.auth import get_api" in code
    assert '@app.command("list")' in code
    assert "rest_get" in code
    assert "callParks" in code
    assert "def list_items(" in code or "def list_call_parks(" in code

def test_render_create_with_defaults():
    endpoints = [
        Endpoint(
            name="Create a Call Park",
            method="POST",
            url_path="telephony/config/locations/{locationId}/callParks",
            path_vars=["locationId"],
            query_params=[],
            body_fields=[
                EndpointField(name="name", python_name="name", field_type="string", description="Name", required=True),
                EndpointField(name="recall", python_name="recall", field_type="object", description="Recall", required=True, default={"option": "ALERT_PARKING_USER_ONLY"}),
            ],
            command_type="create",
            command_name="create",
            response_list_key=None,
        ),
    ]
    code = render_command_file("Test", endpoints, {})
    assert "typer.Option(...," in code  # required field
    assert "ALERT_PARKING_USER_ONLY" in code  # default applied
    assert "rest_post" in code
    assert "--json-body" in code

def test_render_delete_has_force():
    endpoints = [
        Endpoint(
            name="Delete a Call Park",
            method="DELETE",
            url_path="telephony/config/locations/{locationId}/callParks/{callParkId}",
            path_vars=["locationId", "callParkId"],
            query_params=[],
            body_fields=[],
            command_type="delete",
            command_name="delete",
            response_list_key=None,
        ),
    ]
    code = render_command_file("Test", endpoints, {})
    assert "--force" in code
    assert "rest_delete" in code
    assert "typer.confirm" in code

def test_rendered_file_is_valid_python():
    """The rendered file should be syntactically valid Python."""
    endpoints = [
        Endpoint(name="List Items", method="GET",
                 url_path="telephony/config/locations/{locationId}/items",
                 path_vars=["locationId"], query_params=[], body_fields=[],
                 command_type="list", command_name="list", response_list_key="items"),
        Endpoint(name="Create Item", method="POST",
                 url_path="telephony/config/locations/{locationId}/items",
                 path_vars=["locationId"], query_params=[],
                 body_fields=[EndpointField(name="name", python_name="name", field_type="string", description="", required=True)],
                 command_type="create", command_name="create", response_list_key=None),
        Endpoint(name="Delete Item", method="DELETE",
                 url_path="telephony/config/locations/{locationId}/items/{itemId}",
                 path_vars=["locationId", "itemId"], query_params=[], body_fields=[],
                 command_type="delete", command_name="delete", response_list_key=None),
    ]
    code = render_command_file("Test Items", endpoints, {})
    compile(code, "<test>", "exec")  # raises SyntaxError if invalid
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_command_renderer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement render_command_file**

Create `tools/command_renderer.py` — this is the largest component. It uses string concatenation (not Jinja) to build each command function, then assembles the full file with imports and app setup.

Key implementation details:
- Path vars like `{locationId}` → function param `location_id: str = typer.Argument(help="Location ID")`
- camelCase path vars converted to snake_case for Python params
- Body fields: required → `typer.Option(..., ...)`, optional → `typer.Option(None, ...)`
- Object/array fields with defaults → `body.setdefault("key", default_dict)`
- All commands get `--debug` option
- list/show get `--output` option
- create gets `--json-body` escape hatch
- delete gets `--force`
- Error handling wrapper around every API call

Full implementation is ~200 lines of string building. The key function signatures:

```python
def folder_name_to_module(folder_name: str) -> tuple[str, str]:
    """Returns (python_module_name, cli_group_name)."""

def render_command_file(folder_name: str, endpoints: list[Endpoint], folder_overrides: dict) -> str:
    """Returns complete Python source code for the command file."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3.11 -m pytest tests/test_command_renderer.py -v`
Expected: ALL PASS (especially `test_rendered_file_is_valid_python`)

- [ ] **Step 5: Commit**

```bash
git add tools/command_renderer.py tests/test_command_renderer.py
git commit -m "feat(gen): command renderer — generates valid Typer command files"
```

---

### Task 6: Main Generator Script

**Files:**
- Create: `tools/generate_commands.py`

- [ ] **Step 1: Write the CLI script**

```python
# tools/generate_commands.py
"""Generate wxcli command files from Postman collection JSON."""
import argparse
import json
import fnmatch
import sys
from pathlib import Path

from tools.postman_parser import parse_folder, load_overrides, apply_overrides
from tools.command_renderer import render_command_file, folder_name_to_module

DEFAULT_COLLECTION = Path(__file__).parent.parent.parent / "postman-webex-collections" / "webex_cloud_calling.json"
DEFAULT_OVERRIDES = Path(__file__).parent / "field_overrides.yaml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "src" / "wxcli" / "commands"

def should_skip(folder_name: str, skip_patterns: list[str]) -> bool:
    for pattern in skip_patterns:
        if fnmatch.fnmatch(folder_name, pattern):
            return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Generate wxcli commands from Postman collection")
    parser.add_argument("--folder", help="Generate for a specific folder name")
    parser.add_argument("--all", action="store_true", help="Generate for all non-skipped folders")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--list-folders", action="store_true", help="List all folders")
    parser.add_argument("--collection", default=str(DEFAULT_COLLECTION))
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    with open(args.collection) as f:
        data = json.load(f)
    folders = data["collection"]["item"]
    overrides = load_overrides(args.overrides)
    skip_patterns = overrides.get("skip_folders", [])
    omit_qp = overrides.get("omit_query_params", ["orgId"])

    if args.list_folders:
        for i, folder in enumerate(folders):
            name = folder["name"]
            count = len(folder.get("item", []))
            skip = " [SKIP]" if should_skip(name, skip_patterns) else ""
            print(f"{i:2d}. {name} ({count} endpoints){skip}")
        return

    targets = []
    if args.folder:
        targets = [f for f in folders if f["name"] == args.folder]
        if not targets:
            print(f"Folder not found: {args.folder}", file=sys.stderr)
            sys.exit(1)
    elif args.all:
        targets = [f for f in folders if not should_skip(f["name"], skip_patterns)]
    else:
        parser.print_help()
        return

    for folder in targets:
        folder_name = folder["name"]
        module_name, cli_name = folder_name_to_module(folder_name)
        endpoints = parse_folder(folder, omit_query_params=omit_qp)

        folder_ovr = overrides.get(folder_name, {})
        for ep in endpoints:
            ep.body_fields = apply_overrides(ep.body_fields, ep.command_type, folder_ovr)

        code = render_command_file(folder_name, endpoints, folder_ovr)
        out_path = Path(args.output) / f"{module_name}.py"

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"  {folder_name} → {out_path.name}")
            print(f"  {len(endpoints)} commands")
            print(f"{'='*60}")
            for ep in endpoints:
                req_fields = [f.name for f in ep.body_fields if f.required]
                print(f"  {ep.command_name:25s} {ep.method:6s} required={req_fields}")
        else:
            out_path.write_text(code)
            print(f"Generated: {out_path} ({len(endpoints)} commands)")
            print(f"  Register: from wxcli.commands.{module_name} import app as {module_name}_app")
            print(f"  Register: app.add_typer({module_name}_app, name=\"{cli_name}\")")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test --list-folders**

Run: `python3.11 tools/generate_commands.py --list-folders 2>&1 | head -20`
Expected: Numbered list of folders with `[SKIP]` on beta/duplicate folders

- [ ] **Step 3: Test --dry-run for a known folder**

Run: `python3.11 tools/generate_commands.py --folder "Features:  Call Pickup" --dry-run`
Expected: Shows 6 commands (list, create, show, update, delete, plus maybe one more)

- [ ] **Step 4: Test actual generation for Call Pickup**

Run: `python3.11 tools/generate_commands.py --folder "Features:  Call Pickup" --output /tmp/wxcli_gen_test/`
Then: `python3.11 -c "exec(open('/tmp/wxcli_gen_test/call_pickup.py').read())"` — should not raise SyntaxError

- [ ] **Step 5: Commit**

```bash
git add tools/generate_commands.py
git commit -m "feat(gen): main generator script with --folder, --all, --dry-run, --list-folders"
```

---

### Task 7: Integration Test — Generate + Verify Against Live API

**Files:**
- No new files — uses the generator to produce a command file, then tests it live

- [ ] **Step 1: Generate Call Routing commands (a new v3 group)**

Run: `python3.11 tools/generate_commands.py --folder "Call Routing" --output src/wxcli/commands/`

- [ ] **Step 2: Verify the generated file is importable**

Run: `python3.11 -c "from wxcli.commands.call_routing import app; print(f'{len(app.registered_commands)} commands')"` (or similar introspection)

- [ ] **Step 3: Register in main.py and test list command against live API**

Add to `src/wxcli/main.py`:
```python
from wxcli.commands.call_routing import app as call_routing_app
app.add_typer(call_routing_app, name="call-routing")
```

Run: `wxcli call-routing list` (or the generated list command)
Expected: Returns data from the live API

- [ ] **Step 4: Fix any issues, update field_overrides.yaml if needed**

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/commands/call_routing.py src/wxcli/main.py tools/field_overrides.yaml
git commit -m "feat(v3): call-routing commands — auto-generated from Postman collection"
```
