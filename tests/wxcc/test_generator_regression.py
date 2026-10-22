"""Golden-file regression test for the generator.

Renders the mini Flow Store fixture's Widgets group with wxops' one generator
(`tools/generate_commands.py` + `tools/command_renderer.py`, Plan 2 Task 17) and
byte-compares it against tests/wxcc/fixtures/expected_widgets.py. A diff means
the emitter changed — inspect, then regenerate the golden if the change is
intended:

    PYTHONPATH=. .venv/bin/python -c "from tests.wxcc.test_generator_regression import render_widgets; \
        open('tests/wxcc/fixtures/expected_widgets.py','w').write(render_widgets())"
"""
import ast
import difflib
import json
import sys
import tempfile
from pathlib import Path

import yaml

from tools import generate_commands as gc

FIXTURE = Path(__file__).parent / "fixtures" / "mini_flow_store.json"
GOLDEN = Path(__file__).parent / "fixtures" / "expected_widgets.py"
SPEC_NAME = "webex-cc-flow-store.json"

# wxcc's golden overrides in wxops form; the mapping per key is in
# test_generator.mini_overrides().
_OVERRIDES = {
    "auto_inject_from_config": ["orgId"],
    "skip_tags": {SPEC_NAME: ["admin-widget-controller"]},
    "operation_overrides": {SPEC_NAME: {
        "mergeWidget": {"blocked": "no-op; use update"},
        "refreshWidgets": {"warn": "may be slow on big orgs"},
        "importWidget": {"multipart": True},
    }},
    "tag_overrides": {SPEC_NAME: {"Widgets": {"command_name_overrides": {
        "show-widgets": "get", "update": "merge-patch",
        "create-import": "import", "create-refresh": "refresh",
    }}}},
}


def render_widgets() -> str:
    """The Widgets module main() writes for the fixture, saved under the Flow
    Store spec name so the Flow Store base URL applies."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        spec_path = work / SPEC_NAME
        spec_path.write_text(json.dumps(json.loads(FIXTURE.read_text())))
        ovr_path = work / "overrides.yaml"
        ovr_path.write_text(yaml.safe_dump(_OVERRIDES))
        saved = sys.argv
        sys.argv = ["generate_commands", "--spec", str(spec_path), "--overrides",
                    str(ovr_path), "--output", str(work / "out"), "--tag", "Widgets"]
        try:
            gc.main()
        finally:
            sys.argv = saved
        return (work / "out" / "widgets.py").read_text()


def test_golden_matches():
    actual = render_widgets()
    expected = GOLDEN.read_text()
    if actual != expected:
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), actual.splitlines(),
            fromfile="expected_widgets.py", tofile="rendered", lineterm=""))
        raise AssertionError("Generated output drifted from the golden:\n" + diff)


def test_golden_is_valid_python():
    ast.parse(GOLDEN.read_text())


def test_rendered_is_valid_python():
    ast.parse(render_widgets())
