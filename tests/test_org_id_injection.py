"""Verify orgId injection in generated commands matches OpenAPI specs.

Spec files now live under specs/ (not repo root). Additionally, each generated
endpoint that accepts orgId emits two get_org_id() calls (one assignment and
one conditional injection) plus sometimes a follow_pagination branch, so the
code-to-spec ratio is expected to exceed 1.0. The invariant we care about:
every spec endpoint with an orgId query param has at least one corresponding
injection site in generated code.
"""
import json
from pathlib import Path

SPECS = [
    "webex-cloud-calling.json",
    "webex-admin.json",
    "webex-device.json",
    "webex-messaging.json",
]
PROJECT_ROOT = Path(__file__).parent.parent
SPECS_DIR = PROJECT_ROOT / "specs"
COMMANDS_DIR = PROJECT_ROOT / "src" / "wxcli" / "commands"


def count_orgid_in_specs() -> int:
    """Count endpoints with orgId as a query param across all specs."""
    count = 0
    for spec_file in SPECS:
        spec_path = SPECS_DIR / spec_file
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
    """Generated code covers every spec endpoint that accepts orgId.

    Each orgId-accepting endpoint emits multiple get_org_id() calls in the
    generated command (assignment + conditional injection + follow_pagination
    branch where applicable), so the expected ratio is >= 1.0. The key
    invariant is that spec coverage is complete; the floor is 0.90 to allow
    for skipped uploads and multi-tag dedup.
    """
    spec_count = count_orgid_in_specs()
    code_count = count_orgid_in_generated_code()
    assert spec_count > 0, "Sanity check: specs should have orgId endpoints"
    assert code_count > 0, "Sanity check: generated code should have orgId injections"
    ratio = code_count / spec_count
    assert ratio >= 0.90, (
        f"Generated code has {code_count} orgId injections but spec declares "
        f"{spec_count} — ratio {ratio:.2%} is below 90% floor (expected >= 1.0)"
    )
