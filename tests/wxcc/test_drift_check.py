"""Drift gate — wxcc's drift-check cases, retargeted to tools/drift_check.py
(Plan 2 Task 18). Pure-local, no API calls.

wxcc's gate (wxcc/tools/generator/drift_check.py) had checks 0-5. The plan's
carry-over table maps 0, 1, 3 and 4 to existing wxops checks; wxcc check 2
(emitted URLs map to the spec) is wxops check 1, proven by mutation in
docs/merge/plan-2-decisions.md; wxcc check 5 (dead `wxcc-flow` references) is
check 34 here. Every case below reads the wxops gate, never wxcc's.
"""
import json
import subprocess
import sys
from collections import Counter

from tools import drift_check as D
from tools import generate_commands as gc

SPEC_NAME = "webex-cc-flow-store.json"
# The seven Flow Store groups that hold the fate-(b) manifest commands; the
# eighth Flow Store group, cc-functions, carries the Custom Functions rows.
FLOW_STORE_GROUPS = ("cc-flow-store", "cc-flow-versions", "cc-flow-tracing",
                     "cc-flow-prefs", "cc-flow-templates", "cc-flow-projects",
                     "cc-flow-connectors")


def _flow_store_spec() -> dict:
    return json.loads((D.REPO / "specs" / SPEC_NAME).read_text())


class TestNormPath:
    def test_params_collapse(self):
        assert D.normalize_path("/{orgId}/project/{projectId}/flows/{flowId}") == \
            "/{}/project/{}/flows/{}"

    def test_emitted_placeholders_match_spec(self):
        # A generated module's URL, after parse_module_commands strips its
        # {fs_base_url} base, names its placeholders in snake_case.
        emitted = D.normalize_path("/{org_id}/project/{project_id}/v2/flows/{flow_id}")
        spec = D.normalize_path("/{orgId}/project/{projectId}/v2/flows/{flowId}")
        assert emitted == spec


class TestPartition:
    """Pins the Flow Store spec's coverage math under the one generator."""

    def setup_method(self):
        self.spec = _flow_store_spec()
        self.raw = D.load_operation_overrides()
        self.skip_tags = D.load_overrides()["skip_tags"]

    def _classes(self) -> Counter:
        """One label per spec OPERATION (two trailing-slash duplicates share a
        normalized key, so counting load_spec_ops' keys would read 92)."""
        gaps = D._gap_overrides(self.raw, self.spec, SPEC_NAME)
        out = Counter()
        for path, item in self.spec["paths"].items():
            for method, op in item.items():
                if method not in D.HTTP_METHODS or not isinstance(op, dict):
                    continue
                tag = (op.get("tags") or ["(untagged)"])[0]
                gap = gaps.get((method.upper(), path))
                if gap:
                    out[gap[0]] += 1
                elif D.tag_is_skipped(tag, SPEC_NAME, self.skip_tags):
                    out["skip_tag"] += 1
                else:
                    out["generated"] += 1
        return out

    def test_no_classification_errors(self):
        resolved = gc.resolve_operation_overrides(self.raw, self.spec, SPEC_NAME)
        spec_keys = {(m.upper(), p) for p, item in self.spec["paths"].items()
                     for m in item if m in D.HTTP_METHODS}
        assert set(resolved) - {gc.ALL_OPERATIONS_KEY} <= spec_keys

    def test_93_ops_partition(self):
        c = self._classes()
        assert sum(c.values()) == 93
        assert c == {"generated": 37, "operation_overrides skip": 37,
                     "operation_overrides blocked": 1, "skip_tag": 18}

    def test_manifest_counts(self):
        # The fate table's manifest totals: (a) 18, (b) 40, (c) 2 = 60 rows
        # over 58 operations. The (a) rows cover 16 operations, because wxcc's
        # two manifest extras (search -> findFlows, update -> patchDraft) are
        # rows 5 and 24, clones of rows 4 and 23.
        reasons = [r for kind, r in
                   D._gap_overrides(self.raw, self.spec, SPEC_NAME).values()
                   if kind == "operation_overrides skip"]
        assert sum(r.startswith("fate (a)") for r in reasons) == 16
        assert sum(r.startswith("fate (c)") for r in reasons) == 2
        surface, _ = D.build_cli_surface()
        assert sum(len(surface[g]) for g in FLOW_STORE_GROUPS) == 40

    def test_keep_endpoints_excuses_8_hand_survivors(self):
        # wxcc's 8 hand survivors became 3 cc-flow extension commands and the
        # cc-functions test extension (the rest went to wxcli configure/init,
        # P2-2 and tools/flow_store_spec.py; command map rows H1-H10).
        ext = D.parse_extension_commands()
        assert {(g, c) for g, c in ext if g in ("cc-flow", "cc-functions")} == {
            ("cc-flow", "show-node-template"), ("cc-flow", "show-starter-flow"),
            ("cc-flow", "list-connectors"), ("cc-functions", "test")}
        assert "POST /v1/{orgId}/functions/{id}:test" in \
            D.load_overrides()["keep_endpoints"]


class TestReferenceScanner:
    """Check 34 (i): the wxcc-flow / wxcc-toolkit token scanner."""

    def test_code_spans_yields_fenced_and_inline_only(self):
        text = ("prose wxcc-flow bogus\n"
                "`wxcc-flow list`\n"
                "```bash\n"
                "# comment wxcc-flow ignored\n"
                "wxcc-flow get FLOW_ID\n"
                "```\n")
        spans = [s for _, s in D.code_spans(text)]
        assert spans == ["wxcc-flow list", "wxcc-flow get FLOW_ID"]

    def test_token_ignores_flags_and_placeholders(self):
        m = D.LEGACY_CLI_TOKEN.search("wxcc-flow list --type SUBFLOW")
        assert m.groups() == ("wxcc-flow", "list")
        assert D.LEGACY_CLI_TOKEN.search("wxcc-flow <command>") is None
        assert D.LEGACY_CLI_TOKEN.search("wxcc-flow ACTIVITY") is None
        assert D.LEGACY_CLI_TOKEN.search("wxcc-flow --version") is None

    def test_token_catches_toolkit_and_api_and_skips_paths(self):
        assert D.LEGACY_CLI_TOKEN.search("wxcc-toolkit init").groups() == \
            ("wxcc-toolkit", "init")
        assert D.LEGACY_CLI_TOKEN.search(
            "wxcc-flow api flows-v2 validate FILE").groups() == ("wxcc-flow", "api")
        for not_a_command in ("~/.wxcc-flow/config.json", "pip install wxcc-toolkit",
                              "wxcc-flow-command-map.md", "Bash(wxcc-flow:*)"):
            assert D.LEGACY_CLI_TOKEN.search(not_a_command) is None, not_a_command


def _sample_docs(tmp_path, monkeypatch, text: str):
    (tmp_path / "SAMPLE.md").write_text(text)
    monkeypatch.setattr(D, "REPO", tmp_path)
    # One scan pattern answers; check 2 walks the patterns one by one and
    # would otherwise read the same file once per pattern.
    monkeypatch.setattr(D, "tracked_files", lambda *a: (
        {"SAMPLE.md"} if a == (D.SCAN_PATTERNS[0],) else set()))
    monkeypatch.setattr(D, "load_allowlist", lambda: set())


class TestSubGroupSurface:
    """Hand-written extension commands (`cc-functions test`) are real surface."""

    def test_functions_group_is_discovered(self):
        assert D.parse_registrations()["cc-functions"] == "cc_functions"
        surface, _ = D.build_cli_surface()
        assert "test" in surface["cc-functions"]
        assert {"list", "show", "create", "publish", "export"} <= set(surface["cc-functions"])

    def test_known_subcommand_passes_and_unknown_one_is_dead(self, tmp_path, monkeypatch):
        _sample_docs(tmp_path, monkeypatch,
                     "`wxcli cc-functions test ID`\n`wxcli cc-functions bogus`\n")
        dead, _, _ = D.check_references({"cc-functions": {"test": []}}, set())
        assert [(d["ref"], d["kind"]) for d in dead] == [
            ("wxcli cc-functions bogus", "command")]

    def test_group_name_alone_is_not_dead(self, tmp_path, monkeypatch):
        _sample_docs(tmp_path, monkeypatch, "`wxcli cc-functions`\n")
        dead, _, _ = D.check_references({"cc-functions": {"test": []}}, set())
        assert dead == []


class TestLegacyCliCheck:
    """Check 34: no wxcc-flow/wxcc-toolkit command in scanned docs, and every
    command-map row resolves. Each half: a planted fixture fires, a clean
    control does not."""

    def test_wxcc_flow_token_in_docs_fires(self, tmp_path, monkeypatch):
        _sample_docs(tmp_path, monkeypatch,
                     "Run `wxcc-flow list` first.\n"
                     "```bash\n"
                     "wxcc-toolkit init\n"
                     "```\n")
        found = D.check_legacy_cli_tokens()
        assert [(f["file"], f["line"], f["ref"]) for f in found] == [
            ("SAMPLE.md", 1, "wxcc-flow list"), ("SAMPLE.md", 3, "wxcc-toolkit init")]
        assert D.CHECK_EXAMINED["34i"]["examined"] == 2

    def test_check34_scans_playbooks_templates_examples(self, tmp_path, monkeypatch):
        import fnmatch
        files = ["docs/playbooks/a.md", "docs/templates/b.md", "docs/examples/c.md"]
        for rel in files:
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / rel).write_text("Run `wxcc-flow list` first.\n")
        monkeypatch.setattr(D, "REPO", tmp_path)
        monkeypatch.setattr(D, "tracked_files", lambda pat: {
            f for f in files if fnmatch.fnmatch(f, pat)})
        found = D.check_legacy_cli_tokens()
        assert sorted(f["file"] for f in found) == sorted(files)

    def test_scan_patterns_include_playbooks(self):
        assert "docs/playbooks/**" in D.SCAN_PATTERNS
        assert "docs/playbooks/**" in D.LEGACY_SCAN_PATTERNS
        assert {"docs/templates/**", "docs/examples/**"} <= set(D.LEGACY_SCAN_PATTERNS)
        # Plan 4 Task 3: templates joined SCAN_PATTERNS (was: not in); examples stay check-34-only.
        assert "docs/templates/**" in D.SCAN_PATTERNS

    def test_wxcc_flow_token_clean_control(self, tmp_path, monkeypatch):
        _sample_docs(tmp_path, monkeypatch,
                     "The old wxcc-flow list command is gone.\n"
                     "`wxcli cc-flow list P --all`\n"
                     "Config lived in `~/.wxcc-flow/config.json`.\n"
                     "```bash\n"
                     "# wxcc-flow list (a comment, not a command)\n"
                     "pip install wxcc-toolkit\n"
                     "```\n")
        assert D.check_legacy_cli_tokens() == []
        assert D.CHECK_EXAMINED["34i"]["examined"] == 3

    MAP = ("| Row | Old | New command | What changed |\n"
           "|---|---|---|---|\n"
           "| 1 | `list` | `wxcli cc-flow list P --all [--force yes\\|no]` | x |\n"
           "| 2 | `get F` | `wxcli cc-flow nope P F` | x |\n"
           "| H1 | `configure` | `wxcli configure` | x |\n"
           "| H2 | `set-project` | none | x |\n"
           "| F11 | `functions test` | `wxcli cc-functions test ID` | x |\n")
    SURFACE = {"cc-flow": {"list": []}, "cc-functions": {"test": []}}

    def _map(self, tmp_path, text):
        path = tmp_path / "map.md"
        path.write_text(text)
        return path

    def test_command_map_row_must_resolve(self, tmp_path):
        path = self._map(tmp_path, self.MAP)
        found = D.check_command_map(self.SURFACE, {"configure"}, path=path,
                                    expected_rows={"1", "2", "H1", "H2", "F11", "H3"})
        assert sorted((f["row"], f["problem"]) for f in found) == [
            ("2", "command 'nope' is not registered in group 'cc-flow'"),
            ("H3", "row missing from the map")]
        assert D.CHECK_EXAMINED["34ii"] == {"examined": 4, "skipped": 1}

    def test_command_map_clean_control(self, tmp_path):
        path = self._map(tmp_path, self.MAP.replace("cc-flow nope", "cc-flow list"))
        assert D.check_command_map(self.SURFACE, {"configure"}, path=path,
                                   expected_rows={"1", "2", "H1", "H2", "F11"}) == []

    def test_missing_map_is_blind(self, tmp_path):
        found = D.check_command_map(self.SURFACE, set(), path=tmp_path / "absent.md")
        assert [f.get("check") for f in found] == ["34ii"]


class TestGateGreen:
    """The full wxops drift gate passes, with check 34 examining real input."""

    def test_all_checks_clean(self):
        out = subprocess.run([sys.executable, "-m", "tools.drift_check", "--enforce"],
                             capture_output=True, text=True, cwd=D.REPO)
        assert out.returncode == 0, out.stdout[-3000:]
        lines = [ln for ln in out.stdout.splitlines() if ln.startswith("[34]")]
        assert len(lines) == 2, lines
        if (D.REPO / D.COMMAND_MAP).is_file():
            assert all(": 0 " in ln for ln in lines), lines
        else:   # the public tree ships without docs/merge/: half (ii) says so
            assert ": 0 " in lines[0] and "not checked" in lines[1], lines
        assert "(examined 0 " not in "\n".join(lines)
        assert out.stdout.rstrip().endswith("result: PASS")


def test_scan_patterns_include_templates():
    # Plan 4 Task 3 (Plan 3 P3-4 follow-up): templates join the scan set that
    # checks 2, 6, 7, 10, 11a, 29 and 30 read; examples stay check-34-only.
    assert "docs/templates/**" in D.SCAN_PATTERNS
    assert D.LEGACY_SCAN_PATTERNS == D.SCAN_PATTERNS + ("docs/examples/**",)
