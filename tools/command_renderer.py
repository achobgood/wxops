"""Render Endpoint objects into complete wxcli Typer command .py files."""
import re
from tools.postman_parser import Endpoint, EndpointField, camel_to_snake, camel_to_kebab


BASE_URL = "https://webexapis.com/v1"
BASE_URL_NO_V1 = "https://webexapis.com"
BASE_URL_ANALYTICS = "https://analytics-calling.webexapis.com/v1"

# Path prefixes that use the base URL without /v1
NO_V1_PREFIXES = ("identity/", "Schemas/")

# Paths that use analytics.webexapis.com instead of webexapis.com
ANALYTICS_PREFIXES = ("cdr_feed", "cdr_stream")

# Existing v2 command modules — generate with _generated suffix to avoid collision
V2_MODULES = {
    "auto_attendants", "call_park", "call_pickup", "call_queues",
    "hunt_groups", "operating_modes", "paging", "schedules",
    "voicemail_groups", "locations", "users", "numbers", "licenses",
    "configure",
}


def folder_name_to_module(folder_name: str) -> tuple[str, str]:
    cleaned = re.sub(r"^Features:\s*", "", folder_name).strip()
    cleaned = re.sub(r"\s*\(\d+/\d+\)", "", cleaned).strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_").lower()
    cli_name = slug.replace("_", "-")
    return slug, cli_name


def _path_var_to_param(var: str) -> str:
    return camel_to_snake(var)


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


def _render_url_expr(url_path: str, path_vars: list[str]) -> str:
    # CDR paths use analytics.webexapis.com; SCIM/Schema paths skip /v1 prefix
    if any(url_path.startswith(p) for p in ANALYTICS_PREFIXES):
        base = BASE_URL_ANALYTICS
    elif any(url_path.startswith(p) for p in NO_V1_PREFIXES):
        base = BASE_URL_NO_V1
    else:
        base = BASE_URL
    expr = f"{base}/{url_path}"
    for var in path_vars:
        param = _path_var_to_param(var)
        expr = expr.replace("{" + var + "}", "{" + param + "}")
    return expr


def _render_error_handler(indent: str = "    ") -> str:
    return f'''{indent}except RestError as e:
{indent}    err = str(e)
{indent}    if "25008" in err:
{indent}        typer.echo(f"Error: Missing required field. {{e}}", err=True)
{indent}        typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
{indent}    elif "4003" in err or "Target user not authorized" in err:
{indent}        typer.echo(f"Error: {{e}}", err=True)
{indent}        typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
{indent}    elif "4008" in err:
{indent}        typer.echo(f"Error: {{e}}", err=True)
{indent}        typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
{indent}    elif "25409" in err:
{indent}        typer.echo(f"Error: {{e}}", err=True)
{indent}        typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
{indent}    else:
{indent}        typer.echo(f"Error: {{e}}", err=True)
{indent}    raise typer.Exit(1)'''


def _render_auto_inject_params(ep: Endpoint) -> list[str]:
    """Return lines to inject auto-inject params from config."""
    lines = []
    if "orgId" in getattr(ep, "auto_inject_params", []):
        lines.append("    org_id = get_org_id()")
        lines.append("    if org_id is not None:")
        lines.append('        params["orgId"] = org_id')
    return lines


PYTHON_KEYWORDS = {
    "list", "type", "id", "format", "input", "print", "open", "set", "map", "filter",
    "from", "import", "class", "def", "return", "yield", "for", "while", "if", "else",
    "elif", "try", "except", "finally", "with", "as", "pass", "break", "continue",
    "and", "or", "not", "in", "is", "lambda", "global", "nonlocal", "del", "raise",
    "assert", "True", "False", "None", "async", "await",
}

def _safe_func_name(command_name: str) -> str:
    name = command_name.replace("-", "_")
    if name in PYTHON_KEYWORDS:
        return f"cmd_{name}"
    return name

def _safe_param_name(name: str) -> str:
    snake = name.replace("-", "_")
    if snake in PYTHON_KEYWORDS:
        return f"{snake}_param"
    return snake

def _escape_help(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _render_docstring(ep) -> str:
    """Render docstring with optional --json-body example."""
    doc = ep.name
    if ep.json_body_example:
        doc += f"\\n\\nExample --json-body:\\n  '{ep.json_body_example}'"
    return f'    """{doc}."""'


def _enum_help(field: EndpointField, max_desc: int = 60) -> str:
    """Build help text for a field, showing enum choices if available."""
    if field.enum_values and len(field.enum_values) <= 8:
        return _escape_help(f"Choices: {', '.join(field.enum_values)}")
    elif field.enum_values:
        return _escape_help(f"{field.description[:max_desc]} (use --help for choices)")
    return _escape_help(field.description[:max_desc])


def _render_query_params(ep: Endpoint) -> tuple[list[str], list[str]]:
    """Render query param options and param-building lines for non-list commands.

    Returns (param_defs, param_build_lines). Skips rendering if no query params.
    """
    if not ep.query_params:
        return [], []
    param_defs = []
    for qp in ep.query_params:
        param = _safe_param_name(qp.python_name)
        help_text = _enum_help(qp)
        if qp.required:
            param_defs.append(f'    {param}: str = typer.Option(..., "--{qp.python_name}", help="{help_text}"),')
        else:
            param_defs.append(f'    {param}: str = typer.Option(None, "--{qp.python_name}", help="{help_text}"),')
    param_build = ["    params = {}"]
    for qp in ep.query_params:
        param = _safe_param_name(qp.python_name)
        param_build.append(f'    if {param} is not None:\n        params["{qp.name}"] = {param}')
    return param_defs, param_build


def _render_list_command(ep: Endpoint, folder_overrides: dict) -> str:
    func_name = _safe_func_name(ep.command_name)
    folder_overrides = folder_overrides or {}
    params = []

    for var in ep.path_vars:
        param = _path_var_to_param(var)
        params.append(f'    {param}: str = typer.Argument(help="{var}"),')

    for qp in ep.query_params:
        param = _safe_param_name(qp.python_name)
        help_text = _enum_help(qp)
        if qp.required:
            params.append(f'    {param}: str = typer.Option(..., "--{qp.python_name}", help="{help_text}"),')
        else:
            params.append(f'    {param}: str = typer.Option(None, "--{qp.python_name}", help="{help_text}"),')

    # Track query param names to avoid duplicating generic pagination params
    query_param_names = {_safe_param_name(qp.python_name) for qp in ep.query_params}

    params.append('    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),')
    if "limit" not in query_param_names:
        params.append('    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),')
    if "offset" not in query_param_names:
        params.append('    offset: int = typer.Option(0, "--offset", help="Start offset"),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars)

    param_build = []
    param_build.append("    params = {}")
    for qp in ep.query_params:
        param = _safe_param_name(qp.python_name)
        param_build.append(f'    if {param} is not None:\n        params["{qp.name}"] = {param}')
    if "limit" not in query_param_names:
        param_build.append('    if limit > 0:\n        params["max"] = limit')
    if "offset" not in query_param_names:
        param_build.append('    if offset > 0:\n        params["start"] = offset')

    list_key = ep.response_list_key or "items"

    # Per-command columns take precedence over folder-level list.table_columns
    per_cmd = folder_overrides.get("table_columns", {}).get(ep.command_name)
    if per_cmd:
        col_str = repr([(c[0], c[1]) for c in per_cmd])
    else:
        columns = folder_overrides.get("list", {}).get("table_columns", None)
        if columns:
            col_str = repr([(c[0], c[1]) for c in columns])
        else:
            col_str = '[("ID", "id"), ("Name", "name")]'

    lines = [
        f'@app.command("{ep.command_name}")',
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        "    api = get_api(debug=debug)",
        f'    url = f"{url_expr}"',
        *param_build,
        *_render_auto_inject_params(ep),
        "    try:",
        "        result = api.session.rest_get(url, params=params)",
        _render_error_handler("    "),
        f'    result = result or []',
    f'    items = result.get("{list_key}", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])',
        '    if output == "json":',
        "        print_json(items)",
        "    else:",
        f"        print_table(items, columns={col_str}, limit={'limit' if 'limit' not in query_param_names else '0'})",
    ]
    return "\n".join(lines)


def _render_show_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    func_name = _safe_func_name(ep.command_name)
    params = []
    for var in ep.path_vars:
        param = _path_var_to_param(var)
        params.append(f'    {param}: str = typer.Argument(help="{var}"),')
    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)
    params.append('    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars)

    # Show/settings-get commands: support --output for table rendering
    # Empty-string accessors intentionally trigger print_table's auto-detect fallback,
    # which derives columns from the response dict's actual keys.
    show_output = [
        '    if output == "json":',
        "        print_json(result)",
        "    else:",
        '        if isinstance(result, dict):',
        '            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)',
        '        elif isinstance(result, list):',
        '            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)',
        '        else:',
        '            print_json(result)',
    ]

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
    return "\n".join(lines)


def _render_create_id_extraction(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    # Prefer schema-derived response_id_key, fall back to folder overrides
    id_key = ep.response_id_key or (folder_overrides or {}).get("create", {}).get("id_key")
    if id_key and id_key != "id":
        return (
            f'    if isinstance(result, dict) and "{id_key}" in result:\n'
            f'        typer.echo(f"Created: {{result[\'{id_key}\']}}")\n'
            f'    elif isinstance(result, dict) and "id" in result:\n'
            f'        typer.echo(f"Created: {{result[\'id\']}}")\n'
            f'    elif not result or result == {{}}:\n'
            f'        typer.echo("Created.")\n'
            f'    else:\n'
            f'        print_json(result)'
        )
    return (
        '    if isinstance(result, dict) and "id" in result:\n'
        '        typer.echo(f"Created: {result[\'id\']}")\n'
        '    elif not result or result == {}:\n'
        '        typer.echo("Created.")\n'
        '    else:\n'
        '        print_json(result)'
    )


def _render_create_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    func_name = _safe_func_name(ep.command_name)
    folder_overrides = folder_overrides or {}
    params = []
    for var in ep.path_vars:
        param = _path_var_to_param(var)
        params.append(f'    {param}: str = typer.Argument(help="{var}"),')

    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)

    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type == "object" or bf.field_type == "array":
            continue
        help_text = _enum_help(bf)
        if bf.required:
            if bf.field_type == "bool":
                params.append(f'    {param}: bool = typer.Option(..., "--{bf.python_name}", help="{help_text}"),')
            else:
                params.append(f'    {param}: str = typer.Option(..., "--{bf.python_name}", help="{help_text}"),')
        else:
            if bf.field_type == "bool":
                params.append(f'    {param}: bool = typer.Option(None, "--{bf.python_name}/--no-{bf.python_name}", help="{help_text}"),')
            else:
                params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')

    params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars)

    body_build = ["    if json_body:", "        body = json.loads(json_body)", "    else:", "        body = {}"]
    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array"):
            if bf.default is not None:
                body_build.append(f"        body.setdefault({bf.name!r}, {bf.default!r})")
            continue
        if bf.field_type == "bool":
            body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')
        else:
            body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    post_call = "result = api.session.rest_post(url, json=body)" if not has_params else "result = api.session.rest_post(url, json=body, params=params)"

    lines = [
        f'@app.command("{ep.command_name}")',
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        "    api = get_api(debug=debug)",
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        "    try:",
        f"        {post_call}",
        _render_error_handler("    "),
        _render_create_id_extraction(ep, folder_overrides),
    ]
    return "\n".join(lines)


def _render_update_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    func_name = _safe_func_name(ep.command_name)
    params = []
    for var in ep.path_vars:
        param = _path_var_to_param(var)
        params.append(f'    {param}: str = typer.Argument(help="{var}"),')

    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)

    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array"):
            continue
        help_text = _enum_help(bf)
        if bf.field_type == "bool":
            params.append(f'    {param}: bool = typer.Option(None, "--{bf.python_name}/--no-{bf.python_name}", help="{help_text}"),')
        else:
            params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')

    params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars)

    body_build = ["    if json_body:", "        body = json.loads(json_body)", "    else:", "        body = {}"]
    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array"):
            continue
        body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    rest_method = "rest_patch" if ep.method == "PATCH" else "rest_put"
    method_call = f"result = api.session.{rest_method}(url, json=body)" if not has_params else f"result = api.session.{rest_method}(url, json=body, params=params)"

    lines = [
        f'@app.command("{ep.command_name}")',
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        "    api = get_api(debug=debug)",
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        "    try:",
        f"        {method_call}",
        _render_error_handler("    "),
        '    typer.echo(f"Updated.")',
    ]
    return "\n".join(lines)


def _render_delete_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    func_name = _safe_func_name(ep.command_name)
    params = []
    for var in ep.path_vars:
        param = _path_var_to_param(var)
        params.append(f'    {param}: str = typer.Argument(help="{var}"),')
    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)
    params.append('    force: bool = typer.Option(False, "--force", help="Skip confirmation"),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars)

    if ep.path_vars:
        id_var = _path_var_to_param(ep.path_vars[-1])
        confirm_line = f'        typer.confirm(f"Delete {{{id_var}}}?", abort=True)'
        echo_line = f'    typer.echo(f"Deleted: {{{id_var}}}")'
    else:
        confirm_line = '        typer.confirm("Delete this resource?", abort=True)'
        echo_line = '    typer.echo("Deleted.")'

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    delete_call = "api.session.rest_delete(url)" if not has_params else "api.session.rest_delete(url, params=params)"

    lines = [
        f'@app.command("{ep.command_name}")',
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        "    if not force:",
        confirm_line,
        "    api = get_api(debug=debug)",
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        "    try:",
        f"        {delete_call}",
        _render_error_handler("    "),
        echo_line,
    ]
    return "\n".join(lines)


def _render_action_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    func_name = _safe_func_name(ep.command_name)
    params = []
    for var in ep.path_vars:
        param = _path_var_to_param(var)
        params.append(f'    {param}: str = typer.Argument(help="{var}"),')

    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)

    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array"):
            continue
        help_text = _enum_help(bf)
        params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')

    params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars)

    body_build = ["    if json_body:", "        body = json.loads(json_body)", "    else:", "        body = {}"]
    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array"):
            continue
        body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    post_call = "result = api.session.rest_post(url, json=body)" if not has_params else "result = api.session.rest_post(url, json=body, params=params)"

    lines = [
        f'@app.command("{ep.command_name}")',
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        "    api = get_api(debug=debug)",
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        "    try:",
        f"        {post_call}",
        _render_error_handler("    "),
        "    print_json(result)",
    ]
    return "\n".join(lines)


RENDERERS = {
    "list": _render_list_command,
    "show": _render_show_command,
    "create": _render_create_command,
    "update": _render_update_command,
    "delete": _render_delete_command,
    "settings-get": _render_show_command,
    "settings-update": _render_update_command,
    "action": _render_action_command,
}


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

    for ep in endpoints:
        renderer = RENDERERS.get(ep.command_type)
        if renderer is None:
            sections.append(f"# SKIPPED: {ep.name} — unknown command type {ep.command_type}\n")
            continue
        sections.append(renderer(ep, folder_overrides))
        sections.append("")

    return "\n\n".join(sections) + "\n"
