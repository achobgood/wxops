# OpenAPI Migration: Replace Postman Parser with OpenAPI 3.0 Spec Parser

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Postman collection parser with an OpenAPI 3.0 spec parser to eliminate ~70% of `field_overrides.yaml` workarounds and produce CLI commands with real help text, enum validation, correct response keys, and proper required/optional field marking.

**Architecture:** Adapter pattern — new `openapi_parser.py` produces the same `Endpoint`/`EndpointField` dataclasses (enriched with new fields), existing `command_renderer.py` is upgraded to consume the new metadata. Generated output format stays identical (Typer commands using raw HTTP). ~46 OpenAPI tags become command groups after skipping Beta/Phase tags and merging split tags. Most v2 hand-coded modules are removed; `users.py`, `licenses.py`, and `configure.py` are kept (no OpenAPI tag equivalent — they use wxc_sdk).

**Tech Stack:** Python 3.11, Typer, OpenAPI 3.0 JSON spec (no external OpenAPI parsing libraries — spec is simple enough to parse with stdlib `json`).

---

## Key Design Decisions

### Tag-to-group mapping
The OpenAPI spec has 55 tags. Our skip patterns eliminate Beta/Phase tags (~9), then we merge split tags (`(1/2)` + `(2/2)` for User/Workspace settings). This yields **~46 generated command groups**, plus 3 hand-coded modules (`configure`, `users`, `licenses`) = ~49 total groups. Down from 62 today (which included `_generated` and `-ext` duplicates).

### Command type detection — schema-driven, not heuristic
Instead of `SETTINGS_KEYWORDS` heuristics, we detect command type from the spec.

**CRITICAL: Path check takes priority over schema check for GET.** 59 GET endpoints that end with `{param}` have array properties in their response schemas (e.g., a trunk detail with `locationsUsingTrunk: [...]`). These must be classified as `show`, not `list`. Priority order:

1. **show**: GET + path ends with `{param}` → always `show` (regardless of response schema)
2. **list**: GET + 200 response schema has a property with `type: array` (and path does NOT end with `{param}`)
3. **settings-get**: GET + 200 response is a flat object (no array properties, path does NOT end with `{param}`)
4. **create**: POST (not action)
5. **update**: PUT/PATCH
6. **delete**: DELETE
7. **action**: POST with `actions/invoke` in path

### Multi-tag deduplication
24 operations are tagged with both `Call Controls` AND `External Voicemail`. To prevent duplicate commands, the parser tracks processed `operationId` values globally. If an operation was already parsed for a prior tag, it is skipped.

### Content-type handling
8 endpoints (Converged Recordings, Recording Report) use `application/json;charset=UTF-8` instead of `application/json`. All schema resolution must check both content types.

### Edge cases in response schemas
- **Direct array responses**: One endpoint (`GET /telephony/config/jobs/updateRoutingPrefix`) returns `{"type": "array"}` at the top level (no wrapping object). `extract_response_list_key` returns `None` for these; the list renderer's existing fallback (`result if isinstance(result, list) else []`) handles it.
- **Multiple array properties**: 13 GET endpoints have multiple array properties. For these, prefer the property listed in the schema's `required` array. If ambiguous, use the first array property.
- **`allOf` in response schemas**: 2 endpoints (Call Controls) use `allOf`. Resolution merges all `allOf` items into a single properties dict before analysis.

### Response key extraction — from schema, not URL guessing
For list commands, the response key is the property name with `type: array` in the 200 response schema. Example: `GET /autoAttendants` returns `{"autoAttendants": [...]}` — the schema says `required: ["autoAttendants"]` with `autoAttendants: {type: array}`. No guessing.

### Field metadata from schema
- **Required fields**: from `schema.required` array
- **Enum values**: from `schema.properties[field].enum` array
- **Descriptions**: from `schema.properties[field].description`
- **Nested objects**: still skip for CLI flags (use `--json-body`), but mark in help text

### What stays in `field_overrides.yaml`
Only things the OpenAPI spec can't express:
- `table_columns` (display preference, not API metadata)
- `skip_tags` (replaces `skip_folders`)
- `tag_merge` (merge split tags like `(1/2)` + `(2/2)`)
- `cli_name_overrides` (when auto-derived CLI names are ugly)
- API behavior quirks (e.g., CDR URL prefix, user-level OAuth notes)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/openapi_parser.py` | **Create** | Parse OpenAPI 3.0 spec → `Endpoint`/`EndpointField` objects |
| `tools/postman_parser.py` | **Modify** | Keep dataclasses (`Endpoint`, `EndpointField`, helpers), remove Postman parsing functions |
| `tools/command_renderer.py` | **Modify** | Add enum `choices` to options, use real descriptions, auto-detect response keys |
| `tools/generate_commands.py` | **Modify** | Read OpenAPI spec instead of Postman, group by tags, handle tag merging |
| `tools/field_overrides.yaml` | **Rewrite** | Remove response_list_keys, required_fields, command_type_overrides; keep table_columns |
| `src/wxcli/main.py` | **Rewrite** | Clean registration of all groups, remove v2/v3/ext split |
| `src/wxcli/commands/*.py` | **Regenerate** | All generated files replaced by new generator output |
| `src/wxcli/commands/{v2 hand-coded}.py` | **Delete** (10) / **Keep** (3) | Remove 10 v2 modules with OpenAPI replacements; keep `users.py`, `licenses.py`, `configure.py` |
| `tests/tools/test_openapi_parser.py` | **Create** | Unit tests for the new parser |
| `tests/tools/test_command_renderer.py` | **Create** | Unit tests for renderer upgrades |

---

## Task 1: Create `openapi_parser.py` — Core Parsing

**Files:**
- Create: `tools/openapi_parser.py`
- Modify: `tools/postman_parser.py` (add new fields to dataclasses)
- Create: `tests/tools/test_openapi_parser.py`

### Step 1.1: Enrich the dataclasses

- [ ] **Add new fields to `EndpointField` in `tools/postman_parser.py`**

```python
@dataclass
class EndpointField:
    name: str
    python_name: str
    field_type: str          # "string", "bool", "number", "integer", "object", "array"
    description: str         # NEW: real description from spec
    required: bool = False
    default: Any = None
    enum_values: list[str] | None = None  # CHANGED: full list, not just one example
```

- [ ] **Add new fields to `Endpoint` in `tools/postman_parser.py`**

```python
@dataclass
class Endpoint:
    name: str                    # operationId from spec
    method: str
    url_path: str
    path_vars: list[str]
    query_params: list[EndpointField]
    body_fields: list[EndpointField]
    command_type: str
    command_name: str
    raw_path: list[str] = field(default_factory=list)
    response_list_key: str | None = None
    response_id_key: str | None = None     # NEW: for create responses (e.g., "dectNetworkId")
    deprecated: bool = False               # NEW: from spec
```

### Step 1.2: Write the OpenAPI parser

- [ ] **Create `tools/openapi_parser.py`** with these functions:

```python
def load_spec(path: str) -> dict:
    """Load and return the OpenAPI 3.0 spec JSON."""

def resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref like '#/components/schemas/FooObject' to its schema dict."""

def get_tags(spec: dict) -> list[str]:
    """Return sorted list of unique tags used across all operations."""

def parse_parameters(params: list[dict], spec: dict) -> tuple[list[str], list[EndpointField]]:
    """Parse OpenAPI parameters into (path_vars, query_params).
    - path params: extract name as path_var
    - query params: convert to EndpointField with type, description, required, enum
    - Skip 'orgId' parameter (global override)
    """

def parse_request_body(op: dict, spec: dict) -> list[EndpointField]:
    """Parse request body schema into flat list of EndpointField.
    - Resolve $ref to component schema
    - Extract top-level properties only (skip nested objects/arrays for CLI flags)
    - Set required=True for fields in schema's 'required' array
    - Extract enum values, descriptions, types
    """

def detect_command_type(method: str, path: str, op: dict, spec: dict) -> str:
    """Determine command type from HTTP method + response schema structure.
    - GET: check 200 response schema for array property → list, else check path for {param} → show, else settings-get
    - POST: check for 'actions/invoke' in path → action, else create
    - PUT/PATCH: update
    - DELETE: delete
    """

def extract_response_list_key(op: dict, spec: dict) -> str | None:
    """For list commands: find the property with type=array in the 200 response schema.
    Returns the property name (e.g., 'autoAttendants', 'phoneNumbers', 'items').
    """

def extract_response_id_key(op: dict, spec: dict) -> str | None:
    """For create commands: find the ID field name in the 201 response schema.
    Returns the property name (usually 'id', sometimes 'dectNetworkId' etc).
    """

def parse_operation(method: str, path: str, op: dict, spec: dict) -> Endpoint:
    """Convert one OpenAPI operation into an Endpoint dataclass."""

def parse_tag(tag: str, spec: dict, omit_query_params: list[str] | None = None, seen_operation_ids: set[str] | None = None) -> tuple[list[Endpoint], list[str]]:
    """Parse all operations for a given tag into Endpoint list.
    Returns (endpoints, skipped_uploads).
    - Collects all operations tagged with this tag
    - Skips operations whose operationId is already in seen_operation_ids (dedup for multi-tag ops)
    - Calls parse_operation for each
    - Derives command names (reusing _derive_command_name from postman_parser)
    - Deduplicates command names (reusing _dedup_command_names)
    - Skips formdata/multipart operations (uploads)
    - Adds processed operationIds to seen_operation_ids
    """
```

Key implementation details:

**`resolve_ref`**: Simple — split by `/`, walk the dict:
```python
def resolve_ref(spec: dict, ref: str) -> dict:
    parts = ref.lstrip("#/").split("/")
    result = spec
    for part in parts:
        result = result[part]
    return result
```

**`detect_command_type`**: The core improvement over the heuristic approach. **CRITICAL: path-ending check BEFORE schema check** to avoid misclassifying 59 show endpoints that have array properties:
```python
def detect_command_type(method: str, path: str, op: dict, spec: dict) -> str:
    if method == "POST":
        if "actions" in path and "invoke" in path:
            return "action"
        return "create"
    if method in ("PUT", "PATCH"):
        return "update"
    if method == "DELETE":
        return "delete"
    # GET — PRIORITY: path ending first, then schema analysis
    if method == "GET":
        # Path ending with {param} is ALWAYS show (even if response has arrays)
        if path.rstrip("/").endswith("}"):
            return "show"
        # For non-param paths, check response schema
        schema = _get_response_schema(op, spec, "200")
        if schema is None:
            return "list"
        has_array = any(
            prop.get("type") == "array"
            for prop in schema.get("properties", {}).values()
        )
        if has_array:
            return "list"
        return "settings-get"
    return "action"
```

**`_get_response_schema`**: Must handle `$ref`, `allOf`, and alternate content types:
```python
def _get_response_schema(op: dict, spec: dict, status_code: str = "200") -> dict | None:
    resp = op.get("responses", {}).get(status_code, {})
    content = resp.get("content", {})
    # Handle both content-type variants
    json_content = content.get("application/json") or content.get("application/json;charset=UTF-8", {})
    schema = json_content.get("schema", {})
    if not schema:
        return None
    # Resolve $ref
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])
    # Resolve allOf (merge all items into one properties dict)
    if "allOf" in schema:
        merged_props = {}
        merged_required = []
        for item in schema["allOf"]:
            if "$ref" in item:
                resolved = resolve_ref(spec, item["$ref"])
                merged_props.update(resolved.get("properties", {}))
                merged_required.extend(resolved.get("required", []))
            else:
                merged_props.update(item.get("properties", {}))
                merged_required.extend(item.get("required", []))
        schema = {"type": "object", "properties": merged_props, "required": merged_required}
    return schema
```

**`extract_response_list_key`**: Find the array property name in the 200 response. Handle direct array responses and multi-array ambiguity:
```python
def extract_response_list_key(op: dict, spec: dict) -> str | None:
    schema = _get_response_schema(op, spec, "200")
    if schema is None:
        return None
    # Direct array response (no wrapping object) — return None, renderer handles raw list
    if schema.get("type") == "array":
        return None
    # Find array properties
    required = set(schema.get("required", []))
    array_props = [
        (name, name in required)
        for name, prop in schema.get("properties", {}).items()
        if prop.get("type") == "array"
    ]
    if not array_props:
        return None
    # Prefer required array property; otherwise first one
    for name, is_required in array_props:
        if is_required:
            return name
    return array_props[0][0]
```

**`parse_request_body`**: Extract top-level fields, mark required, capture enums. Handle both content-type variants:
```python
def parse_request_body(op: dict, spec: dict) -> list[EndpointField]:
    rb = op.get("requestBody", {})
    content = rb.get("content", {})
    json_content = content.get("application/json") or content.get("application/json;charset=UTF-8", {})
    schema = json_content.get("schema", {})
    # Resolve $ref
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])
    required_fields = set(schema.get("required", []))
    fields = []
    for name, prop in schema.get("properties", {}).items():
        field_type = prop.get("type", "string")
        # Resolve $ref for nested objects
        if "$ref" in prop:
            field_type = "object"
        enum_values = prop.get("enum")
        fields.append(EndpointField(
            name=name,
            python_name=camel_to_kebab(name),
            field_type=field_type,
            description=prop.get("description", "")[:120],
            required=name in required_fields,
            enum_values=enum_values,
        ))
    return fields
```

**`parse_operation`**: Must populate `raw_path` by converting OpenAPI `{param}` syntax to `:param` syntax for compatibility with `_derive_command_name`:
```python
def parse_operation(method: str, path: str, op: dict, spec: dict) -> Endpoint:
    segments = path.strip("/").split("/")
    raw_path = [":" + s[1:-1] if s.startswith("{") and s.endswith("}") else s for s in segments]
    # ... rest of parsing
```

Note: `_build_url_path` from `postman_parser.py` is NOT needed — OpenAPI paths already use `{param}` format which matches the renderer's expected format.

### Step 1.3: Write unit tests

- [ ] **Create `tests/tools/test_openapi_parser.py`**

Test cases using a minimal inline OpenAPI spec fixture:

```python
def test_resolve_ref():
    """$ref resolution walks components/schemas correctly."""

def test_detect_command_type_list():
    """GET with array in response schema → list."""

def test_detect_command_type_singleton():
    """GET with flat object response, no {param} → settings-get."""

def test_detect_command_type_show():
    """GET with path ending in {param} → show."""

def test_detect_command_type_create():
    """POST → create."""

def test_detect_command_type_action():
    """POST with actions/invoke in path → action."""

def test_extract_response_list_key():
    """Extracts correct array property name from response schema."""

def test_extract_response_id_key():
    """Extracts 'id' or custom key from 201 response."""

def test_parse_request_body_required_fields():
    """Required fields marked correctly from schema."""

def test_parse_request_body_enums():
    """Enum values extracted as list."""

def test_parse_request_body_descriptions():
    """Descriptions populated from schema."""

def test_parse_request_body_nested_objects_skipped():
    """Object/array fields included but typed as 'object'/'array'."""

def test_parse_parameters():
    """Path params and query params parsed with types and descriptions."""

def test_parse_tag_full_integration():
    """Parse all operations for a tag against the real spec file."""
```

- [ ] **Run tests**

```bash
PYTHONPATH=. python3.11 -m pytest tests/tools/test_openapi_parser.py -v
```

- [ ] **Commit**

```bash
git add tools/openapi_parser.py tools/postman_parser.py tests/tools/test_openapi_parser.py
git commit -m "feat: add OpenAPI 3.0 spec parser with schema-driven command type detection"
```

---

## Task 2: Upgrade `command_renderer.py` — Use New Metadata

**Files:**
- Modify: `tools/command_renderer.py`
- Create: `tests/tools/test_command_renderer.py`

### Step 2.1: Add enum choices to option rendering

- [ ] **Modify option rendering in all command type renderers** to use `enum_values` when available:

For create/update/action commands, change option rendering from:
```python
help_text = bf.description[:60]
if bf.enum_example:
    help_text = f"e.g. {bf.enum_example}"
params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')
```

To:
```python
help_text = _escape_help(bf.description[:80])
if bf.enum_values:
    # Render as Typer enum with choices
    choices = bf.enum_values
    if len(choices) <= 6:
        params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')
        # Add callback validation in the function body instead
    else:
        params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')
else:
    params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')
```

Actually, keep it simple — just embed the enum values in the help text for now. **IMPORTANT: always pass through `_escape_help`** to prevent syntax errors from special characters:
```python
help_text = _escape_help(bf.description[:80])
if bf.enum_values and len(bf.enum_values) <= 8:
    help_text = _escape_help(f"Choices: {', '.join(bf.enum_values)}")
elif bf.enum_values:
    help_text = _escape_help(f"{bf.description[:60]} (use --help for choices)")
```

### Step 2.2: Use real descriptions in help text

- [ ] **Update all renderers** to use `bf.description` as help text instead of empty strings.

This is already handled by step 2.1 since we now populate descriptions from the OpenAPI spec.

### Step 2.3: Use response_id_key for create commands

- [ ] **Modify `_render_create_id_extraction`** to use `ep.response_id_key` when set:

```python
def _render_create_id_extraction(ep: Endpoint) -> str:
    id_key = ep.response_id_key or "id"
    return (
        f'    if isinstance(result, dict) and "{id_key}" in result:\n'
        f'        typer.echo(f"Created: {{result[\'{id_key}\']}}")\n'
        f'    elif isinstance(result, dict) and "id" in result:\n'
        f'        typer.echo(f"Created: {{result[\'id\']}}")\n'
        f'    else:\n'
        f'        print_json(result)'
    )
```

### Step 2.4: Update renderer signatures

- [ ] **Update `_render_create_command`** to accept `Endpoint` instead of `folder_overrides`:

The renderer currently takes `folder_overrides` to find `id_key`. Now the `Endpoint` carries `response_id_key` directly. Update the signature and the call in `render_command_file`.

- [ ] **Update `_render_list_command`** — the response list key now comes from `ep.response_list_key` (already does, but verify no more folder_override fallback needed for this).

- [ ] **Update `render_command_file`** — simplify the dispatch since overrides are now minimal. Pass `folder_overrides` only for `table_columns`.

### Step 2.5: Write tests

- [ ] **Create `tests/tools/test_command_renderer.py`**

```python
def test_render_list_with_response_key():
    """List command uses ep.response_list_key from schema."""

def test_render_create_with_custom_id_key():
    """Create command extracts correct ID from response using ep.response_id_key."""

def test_render_option_with_enum_choices():
    """Options with enum_values show choices in help text."""

def test_render_option_with_description():
    """Options show description from spec in help text."""

def test_render_required_option():
    """Required fields render as typer.Option(...)."""

def test_render_settings_get():
    """settings-get commands render like show commands."""
```

- [ ] **Run tests**

```bash
PYTHONPATH=. python3.11 -m pytest tests/tools/test_command_renderer.py -v
```

- [ ] **Commit**

```bash
git add tools/command_renderer.py tests/tools/test_command_renderer.py
git commit -m "feat: upgrade renderer with enum choices, descriptions, schema-driven response keys"
```

---

## Task 3: Update `generate_commands.py` — OpenAPI Input

**Files:**
- Modify: `tools/generate_commands.py`

### Step 3.1: Switch input source

- [ ] **Update `generate_commands.py`** to read OpenAPI spec instead of Postman collection:

```python
DEFAULT_SPEC = Path(__file__).parent.parent / "webex-cloud-calling.json"

# In main():
with open(args.spec) as f:
    spec = json.load(f)

# Get all tags
all_tags = get_tags(spec)  # from openapi_parser
```

### Step 3.2: Add tag merging

- [ ] **Implement tag merging** in overrides:

```yaml
# field_overrides.yaml
tag_merge:
  "User Call Settings":
    - "User Call Settings (1/2)"
    - "User Call Settings (2/2)"
  "Workspace Call Settings":
    - "Workspace Call Settings (1/2)"
    - "Workspace Call Settings (2/2)"
```

In the generator, merge operations from both tags before generating:
```python
def merge_tags(spec: dict, merge_map: dict) -> dict:
    """Merge split tags' operations into a single tag."""
    # Rewrite op tags in-place so parse_tag sees all ops under merged name
```

### Step 3.3: Skip tag patterns

- [ ] **Update skip logic** from folder name matching to tag matching:

```yaml
skip_tags:
  - "Beta *"
  - "Call Settings For Me*"
  - "* Phase*"
```

### Step 3.4: CLI name overrides

- [ ] **Add `cli_name_overrides`** for tags with ugly auto-derived names:

```yaml
cli_name_overrides:
  "Features:  Auto Attendant": "auto-attendant"
  "Features:  Call Queue": "call-queue"
  "Features:  Hunt Group": "hunt-group"
  "Features:  Call Park": "call-park"
  "Features:  Call Pickup": "call-pickup"
  "Features:  Paging Group": "paging-group"
  "Features: Announcement Playlist": "announcement-playlists"
  "Features: Announcement Repository": "announcements"
  "Features: Call Recording": "call-recording"
  "Features: Customer Experience Essentials": "cx-essentials"
  "Features: Hot Desking Sign-in via Voice Portal": "hot-desking-portal"
  "Features: Operating Modes": "operating-modes"
  "Features: Single Number Reach": "single-number-reach"
  "Features: Virtual Extensions": "virtual-extensions"
  "Location Call Settings:  Schedules": "location-schedules"
  "Location Call Settings:  Voicemail": "location-voicemail"
  "Location Call Settings: Call Handling": "location-call-handling"
  "Reports: Detailed Call History": "cdr"
  "User Call Settings": "user-settings"
  "Workspace Call Settings": "workspace-settings"
  "DECT Devices Settings": "dect-devices"
  "Device Call Settings": "device-settings"
  "Emergency Services Settings": "emergency-services"
  "Calling Service Settings": "calling-service"
  "Caller Reputation Provider": "caller-reputation"
  "Call Queue Settings with Playlist Settings": "cq-playlists"
  "Device Call Settings With Device Dynamic Settings": "device-dynamic-settings"
  "Partner Reports/Templates": "partner-reports"
  "Recording Report": "recording-report"
  "Conference Controls": "conference"
  "Converged Recordings": "recordings"
  "External Voicemail": "external-voicemail"
  "Client Call Settings": "client-settings"
  "Virtual Line Call Settings": "virtual-line-settings"
  "Mode Management": "mode-management"
  "Hot Desk": "hot-desk"
  "Location Call Settings": "location-settings"
  "Call Routing": "call-routing"
  "Call Controls": "call-controls"
```

### Step 3.5: Generate `main.py` registration block

- [ ] **Add auto-generation of main.py registration** — after generating all command files, output the registration block:

```python
def generate_main_py_registrations(generated_modules: list[tuple[str, str]]) -> str:
    """Generate the import + add_typer lines for main.py."""
    lines = ["# Auto-generated command registrations"]
    for module_name, cli_name in generated_modules:
        var = f"{module_name}_app"
        lines.append(f"from wxcli.commands.{module_name} import app as {var}")
        lines.append(f'app.add_typer({var}, name="{cli_name}")')
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Commit**

```bash
git add tools/generate_commands.py
git commit -m "feat: switch generator to OpenAPI spec input with tag merging and cli name overrides"
```

---

## Task 4: Rewrite `field_overrides.yaml` — Keep Only What's Needed

**Files:**
- Rewrite: `tools/field_overrides.yaml`

### Step 4.1: Analyze what OpenAPI eliminates

The following override types are NO LONGER NEEDED (OpenAPI spec provides this data):
- `response_list_keys` — schema defines the array property name
- `command_type_overrides` — schema-driven detection replaces heuristics
- `create.required_fields` — schema's `required` array
- `create.defaults` — not needed (CLI doesn't set defaults for complex objects)
- `create.id_key` — `response_id_key` from 201 response schema

What STAYS:
- `table_columns` — display preference, not API metadata
- `skip_tags` — replaces `skip_folders`
- `tag_merge` — merge split tags
- `cli_name_overrides` — human-friendly CLI group names
- `omit_query_params` — still skip `orgId`
- `url_overrides` — only if spec has wrong URLs (check CDR endpoints)

### Step 4.2: Write the new overrides file

- [ ] **Rewrite `field_overrides.yaml`** with only the necessary overrides:

```yaml
# field_overrides.yaml — OpenAPI-driven generator
# Only overrides that the spec can't express

# Tags to skip (beta, user-level, split duplicates before merge)
skip_tags:
  - "Beta *"
  - "Call Settings For Me*"
  - "* Phase*"

# Merge split tags into one command group
tag_merge:
  "User Call Settings":
    - "User Call Settings (1/2)"
    - "User Call Settings (2/2)"
  "Workspace Call Settings":
    - "Workspace Call Settings (1/2)"
    - "Workspace Call Settings (2/2)"

# CLI group name overrides (when auto-derived name is ugly)
cli_name_overrides:
  # ... (from Task 3.4 above)

# Global
omit_query_params:
  - orgId

# Per-group table column overrides (display preference only)
"Features:  Auto Attendant":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Extension", "extension"]
      - ["Enabled", "enabled"]

# ... (preserve all existing table_columns sections)
```

- [ ] **Commit**

```bash
git add tools/field_overrides.yaml
git commit -m "refactor: simplify field_overrides.yaml — remove response keys, required fields, command type overrides"
```

---

## Task 5: Delete V2 Modules + Regenerate Everything

**Files:**
- Delete: 14 v2 hand-coded command files
- Regenerate: all command files from OpenAPI
- Rewrite: `src/wxcli/main.py` (registration block)

### Step 5.1: Delete v2 modules

- [ ] **Delete the v2 hand-coded command files that have OpenAPI replacements:**

```
src/wxcli/commands/auto_attendants.py
src/wxcli/commands/call_park.py
src/wxcli/commands/call_pickup.py
src/wxcli/commands/call_queues.py
src/wxcli/commands/hunt_groups.py
src/wxcli/commands/operating_modes.py
src/wxcli/commands/paging.py
src/wxcli/commands/voicemail_groups.py
src/wxcli/commands/schedules.py
src/wxcli/commands/numbers.py
```

**KEEP these hand-coded modules** (no OpenAPI tag equivalent — they use wxc_sdk Python methods):
```
src/wxcli/commands/configure.py    — auth/config command
src/wxcli/commands/users.py        — uses wxc_sdk PeopleApi (no "Users" tag in spec)
src/wxcli/commands/licenses.py     — uses wxc_sdk LicensesApi (no "Licenses" tag in spec)
src/wxcli/commands/locations.py    — uses wxc_sdk LocationsApi (OpenAPI "Locations" tag covers it BUT keep for now as it has richer filtering — revisit after regen)
```

Note: `send_activation_email.py` was generated from a Postman-only folder with no OpenAPI equivalent. Check if there's a matching endpoint in the spec; if not, keep the existing generated version or remove if unused.

Also delete the `_generated` and `-ext` duplicates since OpenAPI generates canonical versions:
```
src/wxcli/commands/auto_attendant.py (was auto-attendant-ext)
src/wxcli/commands/call_park_generated.py
src/wxcli/commands/call_pickup_generated.py
src/wxcli/commands/call_queue.py (was call-queue-ext)
src/wxcli/commands/hunt_group.py (was hunt-group-ext)
src/wxcli/commands/locations_generated.py
src/wxcli/commands/numbers_generated.py
src/wxcli/commands/operating_modes_generated.py
src/wxcli/commands/paging_group.py
```

### Step 5.2: Regenerate all commands

- [ ] **Run the updated generator:**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --all --spec webex-cloud-calling.json
```

- [ ] **Verify output** — check a few generated files for:
  - Enum choices in help text
  - Real descriptions
  - Correct response list keys
  - Required fields marked with `typer.Option(...)`

### Step 5.3: Update `main.py`

- [ ] **Rewrite `src/wxcli/main.py`** registration block using the generator output. Keep the preamble (version, whoami, configure) and replace everything after with the auto-generated registrations.

### Step 5.4: Verify the CLI loads

- [ ] **Run smoke test:**

```bash
pip3.11 install -e . -q
wxcli --help
wxcli auto-attendant --help
wxcli call-queue --help
wxcli user-settings --help
wxcli cdr --help
```

- [ ] **Commit**

```bash
git add -A src/wxcli/commands/ src/wxcli/main.py
git commit -m "feat: regenerate all CLI commands from OpenAPI spec — remove v2 modules, unified groups"
```

---

## Task 6: Spot-Test Against Live API

**Files:** None (testing only)

### Step 6.1: Test 5-6 representative groups

- [ ] **Test list commands** (verify response keys are correct):

```bash
wxcli auto-attendant list --limit 2
wxcli call-queue list --limit 2
wxcli user-settings list --limit 2
wxcli numbers list --limit 2
wxcli people list --limit 2
wxcli workspaces list --limit 2
```

- [ ] **Test show commands** (verify singleton detection):

```bash
wxcli location-settings show <location_id>  # should be settings-get
wxcli emergency-services show               # should be settings-get
```

- [ ] **Test enum help text** (verify choices display):

```bash
wxcli auto-attendant create --help  # Should show extensionDialing choices: ENTERPRISE, GROUP
wxcli call-queue create --help      # Should show routing choices
```

- [ ] **Document any issues found** and fix in `field_overrides.yaml` or parser

- [ ] **Final commit**

```bash
git add -A
git commit -m "fix: address issues found during live testing of OpenAPI-generated commands"
```

---

## Task 7: Cleanup and Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `tools/postman_parser.py` (remove dead Postman-specific code)
- Delete: stale `__pycache__` directories

### Step 7.1: Remove dead code from `postman_parser.py`

- [ ] **Remove Postman-specific functions** that are no longer called:
  - `parse_body_fields` (replaced by `parse_request_body` in openapi_parser)
  - `_infer_type` (no longer needed — OpenAPI has explicit types)
  - `SETTINGS_KEYWORDS` and `SETTINGS_NAME_KEYWORDS` (no longer needed — schema-driven)
  - `derive_command_type` (replaced by `detect_command_type` in openapi_parser)
  - `derive_response_list_key` (replaced by `extract_response_list_key`)
  - `parse_request` (replaced by `parse_operation`)
  - `parse_folder` (replaced by `parse_tag`)
  - `apply_overrides` (simplified — only table_columns remain)
  - `apply_endpoint_overrides` (most overrides eliminated)

Keep: `Endpoint`, `EndpointField`, `camel_to_kebab`, `camel_to_snake`, `_derive_command_name`, `_dedup_command_names`, `_build_url_path`

Consider renaming `postman_parser.py` → `models.py` since it now just holds shared dataclasses and utilities.

### Step 7.2: Update `CLAUDE.md`

- [ ] **Update the CLI status section** to reflect:
  - Generator now uses OpenAPI 3.0 spec (not Postman collection)
  - `field_overrides.yaml` is simplified — only table_columns and skip patterns
  - v2 modules removed — all commands are OpenAPI-generated
  - Regenerate command: `PYTHONPATH=. python3.11 tools/generate_commands.py --all --spec webex-cloud-calling.json`
  - Known issues section updated

### Step 7.3: Commit

```bash
git add tools/postman_parser.py CLAUDE.md
git commit -m "refactor: remove dead Postman parsing code, update CLAUDE.md for OpenAPI workflow"
```

---

## Parallelization Guide

For subagent-driven execution:

| Wave | Tasks | Notes |
|------|-------|-------|
| Wave 1 | Task 1 (parser) + Task 4 (overrides analysis) | Fully independent |
| Wave 2 | Task 2 (renderer) + Task 3 (generator) | Depend on Task 1 dataclass changes |
| Wave 3 | Task 5 (delete + regenerate) | Depends on Tasks 1-4 complete |
| Wave 4 | Task 6 (live test) + Task 7 (cleanup) | Depends on Task 5 |

Tasks 1 and 4 can run in parallel. Tasks 2 and 3 can run in parallel after Task 1. Tasks 6 and 7 are sequential.

---

## Success Criteria

1. `wxcli --help` shows ~49 command groups (~46 generated + 3 hand-coded, down from 62 with duplicates)
2. `wxcli <group> <command> --help` shows real descriptions and enum choices
3. `wxcli <group> list` returns correct data (no response key bugs)
4. `field_overrides.yaml` is <250 lines (down from 531) — only table_columns, skip/merge config, and cli names remain
5. No `SETTINGS_KEYWORDS` heuristic — all command types are schema-driven
6. All tests pass: `PYTHONPATH=. python3.11 -m pytest tests/tools/ -v`
7. No duplicate commands from multi-tag operations (24 shared Call Controls/External Voicemail ops appear in only one group)
