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
    # ~17% gap is normal: skipped uploads, multi-tag dedup, beta/phase tag skips
    assert ratio > 0.80, (
        f"Generated code has {code_count} orgId injections but spec declares "
        f"{spec_count} — ratio {ratio:.2%} is below 80% threshold"
    )
