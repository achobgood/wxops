"""tools.flow_store_spec diff (was wxcc-flow spec-diff, Phase D — design § 12). Pure-local, no API."""
import argparse

from tools.flow_store_spec import build_parser, diff_specs as _diff_specs, main, spec_ops as _spec_ops


def _spec(ops):
    """Build a minimal OpenAPI dict from {(method, path): operationId}."""
    paths = {}
    for (method, path), op_id in ops.items():
        paths.setdefault(path, {})[method] = {"operationId": op_id}
    return {"paths": paths}


class TestSpecOps:
    def test_flattens_methods_uppercased(self):
        spec = _spec({("get", "/a"): "getA", ("post", "/a"): "postA"})
        assert set(_spec_ops(spec)) == {("GET", "/a"), ("POST", "/a")}

    def test_ignores_non_operation_keys(self):
        spec = {"paths": {"/a": {"get": {"operationId": "x"}, "parameters": []}}}
        assert set(_spec_ops(spec)) == {("GET", "/a")}

    def test_empty_spec(self):
        assert _spec_ops({}) == {}


class TestDiffSpecs:
    def test_in_sync(self):
        s = _spec({("get", "/a"): "getA"})
        assert _diff_specs(s, s) == ([], [], [])

    def test_added_and_removed(self):
        old = _spec({("get", "/a"): "getA"})
        new = _spec({("post", "/b"): "postB"})
        added, removed, changed = _diff_specs(old, new)
        assert added == [("POST", "/b")]
        assert removed == [("GET", "/a")]
        assert changed == []

    def test_changed_operation_body(self):
        old = _spec({("get", "/a"): "getA"})
        new = _spec({("get", "/a"): "getA"})
        new["paths"]["/a"]["get"]["parameters"] = [{"name": "q"}]
        added, removed, changed = _diff_specs(old, new)
        assert (added, removed) == ([], [])
        assert changed == [("GET", "/a")]


class TestSpecDiffCli:
    def test_missing_snapshot_is_clean_error(self, tmp_path, capsys):
        rc = main(["diff", "--snapshot", str(tmp_path / "nope.json")])
        assert rc == 1
        assert "File not found" in capsys.readouterr().err

    def test_help_lists_exit_code_flag(self):
        # Inspect the registered flags directly rather than the rendered help text.
        sub = next(a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction))
        opts = {o for a in sub.choices["diff"]._actions for o in a.option_strings}
        assert "--exit-code" in opts
