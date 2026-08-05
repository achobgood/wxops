"""Part E: Regression snapshot — catches unintended generator output changes.

If output changes, test fails with a diff. Developer must review and update snapshot:
    python3.11 -c "
    import json
    from tools.openapi_parser import parse_tag
    from tools.command_renderer import render_command_file
    with open('tests/fixtures/mini-openapi.json') as f:
        spec = json.load(f)
    endpoints, _ = parse_tag('Things', spec, omit_query_params=['orgId'])
    code = render_command_file('Things', endpoints, {})
    open('tests/fixtures/expected_output.py', 'w').write(code)
    "
"""

import json
import difflib
from pathlib import Path

from tools.openapi_parser import parse_tag
from tools.command_renderer import render_command_file


FIXTURES = Path(__file__).parent / "fixtures"


class TestGeneratorRegression:
    def test_generator_output_stable(self):
        """Generate 'Things' tag from fixture spec. Compare against checked-in snapshot."""
        # 1. Load fixture spec
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)

        # 2. Run parser + renderer
        endpoints, _ = parse_tag("Things", spec, omit_query_params=["orgId"])
        actual = render_command_file("Things", endpoints, {})

        # 3. Load expected snapshot
        expected = (FIXTURES / "expected_output.py").read_text()

        # 4. Compare
        if actual != expected:
            diff = list(difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile="expected_output.py",
                tofile="actual_output",
                n=3,
            ))
            diff_text = "".join(diff[:80])  # Cap diff at 80 lines
            raise AssertionError(
                f"Generator output changed. Review the diff and update the snapshot "
                f"if the change is intentional.\n\n{diff_text}"
            )

    def test_fixture_spec_parseable(self):
        """Fixture spec is valid JSON and parseable by the OpenAPI parser."""
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)
        assert "paths" in spec
        assert "components" in spec

    def test_snapshot_is_valid_python(self):
        """The checked-in snapshot file is valid Python."""
        import ast
        code = (FIXTURES / "expected_output.py").read_text()
        ast.parse(code)

    def test_all_fixture_tags_produce_output(self):
        """Every tag in the fixture spec produces at least one endpoint."""
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)

        # Tags with actual operations (not all tags have endpoints)
        tags_with_ops = set()
        for path_obj in spec.get("paths", {}).values():
            for method in ("get", "post", "put", "patch", "delete"):
                op = path_obj.get(method)
                if op:
                    for tag in op.get("tags", []):
                        tags_with_ops.add(tag)

        for tag in tags_with_ops:
            endpoints, _ = parse_tag(tag, spec, omit_query_params=["orgId"])
            assert len(endpoints) > 0, f"Tag '{tag}' produced no endpoints"
