"""Plan 4 context-layout invariants (default suite; no token needed).

Task 1 pins where wxcc's skills and kept rules live after the move. Tasks 2 and
4 extend this file with the tests that become true in their tasks.
"""
from __future__ import annotations

import re
import subprocess

from tests.wxcc.conftest import REPO

WXCC_SKILLS = (
    "build-action", "build-digital-inbound", "build-flow-designer",
    "build-flow-programmatic", "build-notification", "build-outbound-flow",
    "build-scripted-fulfillment", "build-solution-docs", "build-spec-diagram",
    "configure-ai-agent", "configure-scripted-agent", "design-flow",
    "design-scripted-agent", "wxcc-debug",
)


def _tracked(*roots: str) -> list[str]:
    return subprocess.check_output(
        ["git", "ls-files", *roots], cwd=REPO, text=True).splitlines()


def _frontmatter(text: str) -> str:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def _paths_globs(text: str) -> set[str]:
    return set(re.findall(r'"([^"]+)"', "\n".join(
        ln for ln in _frontmatter(text).splitlines()
        if ln.startswith("paths:") or ln.lstrip().startswith("- "))))


def test_wxcc_skills_live_under_root_claude():
    for name in WXCC_SKILLS:
        assert (REPO / ".claude/skills" / name / "SKILL.md").is_file(), name
    assert not (REPO / "wxcc/.claude/skills").exists()


def test_always_on_rules_are_only_the_batching_rule():
    always_on = set()
    for rel in _tracked(".claude/rules"):
        text = (REPO / rel).read_text(encoding="utf-8")
        if "paths:" not in _frontmatter(text):
            always_on.add(rel.rsplit("/", 1)[-1])
    assert always_on == {"large-operation-batching.md"}


def test_moved_rules_are_path_scoped():
    doc_placement = (REPO / ".claude/rules/doc-placement.md").read_text(
        encoding="utf-8")
    assert {"docs/**", ".claude/skills/**"} <= _paths_globs(doc_placement)
    flowir = (REPO / ".claude/rules/flowir-mcp-verification.md").read_text(
        encoding="utf-8")
    assert {"docs/reference/flow-designer-flowir.md",
            "docs/examples/flowir/**",
            ".claude/skills/build-flow-programmatic/**"} <= _paths_globs(flowir)


# --- Task 2: folder indexes, maintainer-only doc rules, doc-placement pointers

INDEX_FILES = ("docs/reference/INDEX.md", "docs/playbooks/INDEX.md",
               "docs/templates/INDEX.md", "docs/examples/INDEX.md")


def _load_assemble():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "wxcli_assemble_ctx", REPO / "wxcli-dist" / "assemble.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows_under(text: str, heading: str) -> int:
    """Data rows of the first table under `## heading` (header and rule excluded)."""
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, heading
    rows = [ln for ln in m.group(1).splitlines() if ln.startswith("|")]
    return len(rows) - 2


def test_index_links_resolve():
    tracked = set(_tracked("docs"))
    tracked_dirs = {p.rsplit("/", i)[0] for p in tracked for i in range(1, p.count("/") + 1)}
    for rel in INDEX_FILES:
        index = REPO / rel
        assert index.is_file(), rel
        links = re.findall(r"\]\(([^)#\s]+)", index.read_text(encoding="utf-8"))
        assert links, rel
        for link in links:
            target = (index.parent / link).resolve().relative_to(REPO.resolve()).as_posix()
            assert target in tracked or target.rstrip("/") in tracked_dirs, (rel, link)
            assert not target.endswith("CLAUDE.md"), (rel, link)
            assert not target.startswith("docs/reference/archive"), (rel, link)


def test_doc_maintenance_keeps_every_row():
    text = (REPO / ".claude/rules/doc-maintenance.md").read_text(encoding="utf-8")
    assert _rows_under(text, "Sync Checklist") >= 51
    assert _rows_under(text, "Playbook ↔ Reference Doc Pairs") >= 21


def test_maintainer_rules_not_shipped():
    A = _load_assemble()
    bundle = REPO / "src/wxcli/_playbook"
    for rel in (".claude/rules/doc-maintenance.md", ".claude/rules/repo-development.md"):
        assert rel in A.EXCLUDE_FILES, rel
        assert not (bundle / rel).exists(), rel
    for rel in ("docs/reference/INDEX.md", "docs/playbooks/INDEX.md"):
        assert (bundle / rel).is_file(), rel


def test_doc_placement_points_at_new_homes():
    text = (REPO / ".claude/rules/doc-placement.md").read_text(encoding="utf-8")
    assert "File Map" not in text
    assert "Sync Checklist row in `CLAUDE.md`" not in text
    assert "INDEX.md" in text


# --- Task 4: the merged root CLAUDE.md (guard, doctrine, routing table, budgets)
#
# 4A (session 1) commits only the tests its own steps make pass; the rest carry
# @pytest.mark.skip(reason="Task 4B") and 4B removes each skip in the step that
# makes it pass, so every commit on the branch leaves the suite green.

import pytest  # noqa: E402

ROOT_MD = REPO / "CLAUDE.md"

CITED_HEADINGS = (
    "## Mandatory Grounding Rule", "## Answering platform questions",
    "## Source of Truth Precedence", "## Discovery-First Rule",
    "## Plain-English Communication Rule", "### Agent Invocation Pattern",
    "### Agent Model Selection",
    "### Agent Orchestration — Long-Running Work & Silence Detection",
    "## Routing Table", "### Multi-Skill Workflows",
    "## Out-of-Skill-Scope Command Groups",
)
# Headings 4A does not write. Task 4B Step 5 empties this set.
_HEADINGS_NOT_YET_WRITTEN: set[str] = set()

GUARD_DOCTRINE = (
    "I don't have that documented", "Value question", "Procedure question",
    "[source: filename § section heading]", "<!-- ref-tag:", "Docs consulted:",
    "docs/plans/2026-07-25-documentation-remediation-backlog.md",
    ".claude/rules/doc-placement.md",
)

OUT_OF_SCOPE_GROUPS = {
    "broadworks-billing-reports", "broadworks-enterprises", "broadworks-subscribers",
    "broadworks-workspaces", "wholesale-billing-reports", "wholesale-provisioning",
    "partner-admins", "partner-tags", "hybrid-clusters", "hybrid-connectors",
    "ucm-profile",
}

OVERLOADED_WORDS = (
    "queue", "flow", "agent", "action", "fulfillment", "team", "site", "dial plan",
    "recording", "desktop", "workspace", "business hours", "IVR", "SMS", "webhook",
    "debug", "wrap-up",
)

CC_TOPICS = ("dial number", "audio", "skill profile", "desktop layout", "outdial",
             "callback", "campaign", "subscription")

QUESTION_RULE_TARGETS = (
    "docs/reference/flow-designer-essentials.md",
    "docs/reference/flow-designer-activities/_index.md",
    "docs/reference/flow-designer-patterns.md",
    "docs/reference/flow-designer-flowir.md",
    "docs/reference/wxcc-platform.md", "docs/playbooks/wxcc-setup.md",
    "docs/playbooks/webex-api-auth.md", "docs/playbooks/cjds-integration.md",
    "docs/reference/ai-agent-studio-scripted.md",
    "docs/playbooks/scripted-agent-design.md", "docs/playbooks/scripted-agent-build.md",
    "docs/reference/ai-agent-studio.md", "docs/reference/webex-connect.md",
    "docs/playbooks/connect-flows.md", "docs/reference/ai-agent-studio-import-json.md",
    "docs/reference/digital-inbound.md", "docs/playbooks/digital-inbound-agent.md",
    "docs/playbooks/cross-channel-escalation.md", "docs/reference/db-integration.md",
    "docs/playbooks/supabase.md", "docs/reference/bre.md", "docs/playbooks/bre-setup.md",
    "docs/reference/webex-connect-advanced.md", "docs/reference/connect-sms.md",
    "docs/reference/connect-email.md", "docs/reference/connect-rcs.md",
    "docs/reference/connect-apple-messages.md", "docs/reference/connect-whatsapp.md",
    "docs/reference/connect-multi-channel.md",
)

def _root_text() -> str:
    return ROOT_MD.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """From `heading` to the next heading of the same or a higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    start = lines.index(heading)
    end, fenced = len(lines), False
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("```"):
            fenced = not fenced
        m = re.match(r"(#+) ", lines[i])
        if m and not fenced and len(m.group(1)) <= level:
            end = i
            break
    return "\n".join(lines[start:end])


def _routing_section() -> str:
    """`## Routing Table` up to the next `## ` heading (### Multi-Skill Workflows included)."""
    return _section(_root_text(), "## Routing Table")


def _cells(row: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def _routing_rows() -> list[list[str]]:
    rows = []
    for ln in _routing_section().splitlines():
        if not ln.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", ln.strip()):
            continue
        rows.append(_cells(ln))
    return rows


def _backticked(text: str) -> list[str]:
    return re.findall(r"`([^`\n]+)`", text)


def _whole_word(word: str, text: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text, re.I) is not None


def _skill_frontmatter(path) -> dict:
    import yaml
    fm = yaml.safe_load(_frontmatter(path.read_text(encoding="utf-8"))) or {}
    return fm


def _tracked_skill_listing_chars(root=REPO) -> int:
    total = 0
    for rel in _tracked_in(root, ".claude/skills/*/SKILL.md"):
        fm = _skill_frontmatter(root / rel)
        name = fm.get("name") or rel.split("/")[2]
        total += len(name) + len(_one_line(fm.get("description", ""))) + 4
    return total


def _one_line(desc) -> str:
    """A block-scalar description as the listing shows it: lines joined with single spaces."""
    return " ".join(ln.strip() for ln in str(desc).splitlines() if ln.strip())


def _tracked_in(root, pattern: str) -> list[str]:
    """Tracked files matching `pattern` (a `git archive` export holds only tracked files)."""
    if (root / ".git").exists():
        return subprocess.check_output(["git", "ls-files", pattern], cwd=root,
                                       text=True).splitlines()
    return sorted(p.relative_to(root).as_posix() for p in root.glob(pattern))


def _start_load_proxy(root=REPO) -> int:
    total = len((root / "CLAUDE.md").read_bytes())
    for rel in _tracked_in(root, ".claude/rules/*.md"):
        text = (root / rel).read_text(encoding="utf-8")
        if "paths:" not in _frontmatter(text):
            total += len((root / rel).read_bytes())
    total += _tracked_skill_listing_chars(root)
    for rel in _tracked_in(root, ".claude/agents/*.md"):
        total += len(_one_line(_skill_frontmatter(root / rel).get("description", "")))
    return total


def _load_drift_check():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "drift_check_ctx", REPO / "tools" / "drift_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_root_claude_md_size_cap():
    # Plan 4 decision P4-14 (was 36,000 under P4-11): AGENTS.md is root minus the
    # Codex overlay savings and must stay under assemble.py's 44,000-byte cap.
    assert len(ROOT_MD.read_bytes()) <= 48_000


def test_skill_listing_within_budget():
    # The /context Skills row is the measure; this pins the input the byte proxy
    # below would otherwise hide inside its total (Plan 4 decision P4-10). 19,850, not the
    # plan's 21,300: Task 5 measured the /context Skills row at 9.1k of a ~10k budget at
    # 20,770 characters, short of the 1.2k headroom P4-10 requires; ~900 more were cut.
    assert _tracked_skill_listing_chars() <= 19_850


def test_start_load_proxy_within_baseline():
    # 75,549 is fea5d5a's value (the pre-merge commit), measured 2026-10-20; method in
    # docs/merge/plan-4-context.md. A ratchet at 4 bytes per token, not a measurement
    # (this markdown runs ~2.7 bytes per token); the /context rows are the measurement.
    assert _start_load_proxy(REPO) <= 75_549


def test_moved_skills_name_no_unspawnable_agent():
    # P4-9: wxcc-agent-builder cannot be spawned from the root until Plan 5;
    # since Plan 5, no skill names a retired agent (Plan 5).
    for name in WXCC_SKILLS:
        text = (REPO / ".claude/skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "wxcc-agent-builder" not in text, name


def test_root_keeps_cited_headings():
    heads = {ln for ln in _root_text().splitlines() if ln.startswith("#")}
    for heading in CITED_HEADINGS:
        if heading in _HEADINGS_NOT_YET_WRITTEN:
            continue
        assert heading in heads, heading


def test_question_guard_doctrine_present():
    section = _section(_root_text(), "## Answering platform questions")
    for s in GUARD_DOCTRINE:
        assert s in section, s
    assert "never from a playbook alone" in section.lower()


def test_agents_md_keeps_guard_and_wxcc_route():
    A = _load_assemble()
    agents = A.build_agents_md(_root_text())
    assert A.GROUNDING_MARKER in agents
    for s in GUARD_DOCTRINE:
        assert A.apply_phrase_map(s) in agents, s
    assert "never from a playbook alone" in agents.lower()   # case-insensitive, as above
    assert "build-action" in agents
    assert "design-ai-agent" in agents
    assert "docs/reference/INDEX.md" in agents
    assert "docs/reference/AGENTS.md" not in agents


def test_routing_table_disambiguates_overloaded_words():
    rows = _routing_rows()
    for word in OVERLOADED_WORDS:
        hits = [r for r in rows if _whole_word(word, r[0])
                and len(set(_backticked(" | ".join(r[1:])))) >= 2]
        assert hits, word


def test_routing_table_has_cc_topic_rows():
    rows = _routing_rows()
    for topic in CC_TOPICS:
        hits = [r for r in rows if topic in r[0].lower()
                and ("contact-center" in _backticked(" | ".join(r[1:]))
                     or "docs/reference/contact-center-" in " | ".join(r[1:]))]
        assert hits, topic


def test_every_tracked_skill_is_routed():
    names = [p.split("/")[2] for p in _tracked(".claude/skills/*/SKILL.md")]
    assert len(names) >= 38
    routed = set(_backticked(_routing_section()))
    for name in names:
        assert name in routed, name


def test_question_rule_lookup_targets_are_routed():
    section = _routing_section()
    for path in QUESTION_RULE_TARGETS:
        assert path in section, path


def test_routing_table_targets_exist():
    tracked = set(_tracked())
    tracked_dirs = {p.rsplit("/", i)[0] for p in tracked for i in range(1, p.count("/") + 1)}
    skills_on_disk = {p.name for p in (REPO / ".claude/skills").iterdir() if p.is_dir()}
    for token in set(_backticked(_routing_section())):
        assert not token.endswith("CLAUDE.md"), token
        if token in skills_on_disk:
            assert f".claude/skills/{token}/SKILL.md" in tracked, token
        elif token.endswith(".md"):
            assert token in tracked, token
        elif token.endswith("/"):
            assert token.rstrip("/") in tracked_dirs, token


def test_out_of_scope_declaration_unchanged():
    assert _load_drift_check().declared_out_of_scope() == OUT_OF_SCOPE_GROUPS


def test_folder_indexes_list_every_file():
    excluded = {"CLAUDE.md", "TODO.md", "migration-spec-template.md", "INDEX.md"}
    for rel in INDEX_FILES:
        folder = rel.rsplit("/", 1)[0]
        index = REPO / rel
        linked = {(index.parent / link).resolve().relative_to(REPO.resolve()).as_posix()
                  for link in re.findall(r"\]\(([^)#\s]+)", index.read_text(encoding="utf-8"))}
        expected = {p for p in _tracked(folder) if p.count("/") == folder.count("/") + 1
                    and p.rsplit("/", 1)[-1] not in excluded}
        if folder == "docs/reference":
            expected = {p for p in expected if p.endswith(".md")}
            expected.add("docs/reference/flow-designer-activities/_index.md")
        missing = expected - linked
        assert not missing, (rel, sorted(missing))


# ---- Plan 5 Task 2: the agent bodies' detail, moved out (A1) -----------------------

PLAN5_SOURCES = REPO / "tests/wxcc/fixtures/plan5_agent_sources.md"
DESIGN_AI_AGENT = REPO / ".claude/skills/design-ai-agent"
PLAN5_FATES = {"body", "moved", "already-in", "not-carried"}


def _plan5_sources() -> dict[str, list[str]]:
    """The fixture's sections, keyed by their `=== ` marker line (without `=== `)."""
    sections: dict[str, list[str]] = {}
    current = None
    for ln in PLAN5_SOURCES.read_text(encoding="utf-8").splitlines()[1:]:
        if ln.startswith("=== "):
            current = ln[4:]
            sections[current] = []
        else:
            sections[current].append(ln)
    return sections


def _plan5_headings() -> list[tuple[str, int, str]]:
    out = []
    for key, lines in _plan5_sources().items():
        if key.startswith("headings "):
            path = key.split(" ", 1)[1]
            out += [(path, int(n), text) for n, text in (ln.split("\t", 1) for ln in lines)]
    return out


def test_design_ai_agent_carries_shared_questions_intact():
    skill = (DESIGN_AI_AGENT / "SKILL.md").read_text(encoding="utf-8")
    blocks = {k: v for k, v in _plan5_sources().items() if k.startswith("block ")}
    assert [k.split()[1] for k in blocks] == ["Q3", "Q6", "Q7", "Q8"]
    for key, lines in blocks.items():
        assert lines[0].startswith("<!-- SYNC:") and lines[1].startswith("### Question"), key
        assert not any(ln.startswith(("<!-- SYNC:", "### ", "## ")) or ln.strip() == "---"
                       for ln in lines[2:]), key
        assert "\n".join(lines) + "\n" in skill, key


def test_wxcc_critical_rules_carried():
    rules = next(v for k, v in _plan5_sources().items() if k.startswith("critical-rules "))
    assert len(rules) == 19
    lines = (DESIGN_AI_AGENT / "build-sequence.md").read_text(encoding="utf-8").splitlines()
    positions = [lines.index(rule) for rule in rules]
    assert positions == sorted(positions)


def test_calling_build_playbook_carries_interview():
    questions = [text for path, _, text in _plan5_headings()
                 if path.endswith("wxc-calling-builder.md") and text.startswith("### Question ")]
    assert len(questions) == 5
    lines = (REPO / "docs/playbooks/calling-build.md").read_text(encoding="utf-8").splitlines()
    for question in questions:
        assert question in lines, question


def test_cucm_migrate_carries_pipeline_walkthrough():
    text = (REPO / ".claude/skills/cucm-migrate/SKILL.md").read_text(encoding="utf-8")
    for needle in ("Create the project", "Connect to CUCM", "Run analysis", "--from-file",
                   "Standard AXL API Access"):
        assert needle in text, needle
    assert sum(1 for ln in text.splitlines() if ln.startswith("## Step 1")) == 1




def test_skill_listing_net_zero_plan5():
    # P5-4: design-ai-agent joins the listing at no net cost (19,771 = the pre-Plan-5 total).
    assert _tracked_skill_listing_chars() <= 19_771


# ---- Plan 5 Task 3: the short agent body and the root's agent sections ------------

AGENT_BODY_HEADINGS = (
    "# Webex Ops agent", "## Your job", "## 1. Understand", "## 2. Plan", "## 3. Run",
    "## 4. Verify", "## 5. Report", "## After a context reset",
)


def _builder_agent_file():
    files = [rel for rel in _tracked(".claude/agents")
             if rel.endswith(".md") and not rel.endswith("/migration-advisor.md")]
    assert len(files) == 1, files
    return REPO / files[0]


def _agent_body(text: str) -> str:
    m = re.match(r"---\n.*?\n---\n", text, re.S)
    assert m
    return text[m.end():]


def _headings(text: str) -> list[str]:
    out, fenced = [], False
    for ln in text.splitlines():
        if ln.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#+ ", ln):
            out.append(ln)
    return out


def test_agent_body_is_short():
    path = _builder_agent_file()
    text = path.read_text(encoding="utf-8")
    body = _agent_body(text)
    assert len(body.encode("utf-8")) <= 8_192
    fm = _skill_frontmatter(path)
    assert len(_one_line(fm["description"])) <= 315
    assert "skills" not in fm
    assert _headings(body) == list(AGENT_BODY_HEADINGS)


def test_agent_body_names_its_homes():
    body = _agent_body(_builder_agent_file().read_text(encoding="utf-8"))
    for home in ("design-ai-agent", "docs/playbooks/calling-build.md", "cucm-migrate",
                 "query-live", "reporting", "org-health", "design-flow",
                 "docs/templates/execution-report.md", "docs/plans/session-state.md"):
        assert home in body, home


def test_root_agent_rule():
    section = _section(_root_text(), "### Agent Invocation Pattern")
    low = section.lower()
    assert "SendMessage" in section
    assert "in parallel" in low
    assert "one agent per job" in low
    for ln in section.splitlines():
        if "phase-per-invocation" in ln.lower():
            assert "CUCM" in ln, ln


def test_root_quick_start_has_no_user_agents_step():
    assert "/agents" not in _section(_root_text(), "## Quick Start")


# ---- Plan 5 Task 4: the rename (Appendix D) ---------------------------------------

# Appendix D § Kept: the only tracked files that may still name an old agent. A
# path ending in "/" is a folder. Each entry's reason is in the plan's table.
OLD_AGENT_NAMES_KEPT = (
    "docs/architecture/",                               # dated decision records, not shipped
    "docs/runbooks/cucm-migration/self-review-findings.md",  # a quoted review, not shipped
    "tests/wxcc/fixtures/context_dry_merge.md",         # a captured /context output
    "tests/wxcc/fixtures/plan5_agent_sources.md",       # Task 2's snapshot of the old bodies
    "tools/context_probe.py",                           # synthetic selftest streams
    "wxcli-dist/assemble.py",                           # the Codex guard's patterns; repo name
    "tests/wxcc/test_assemble.py",                      # the Codex guard's test inputs
    "tests/wxcc/test_init_playbook.py",                 # synthetic bundle file names
    "tests/wxcc/test_context_layout.py",                # this test
    "tests/test_init_playbook.py",                      # asserts the old agent files go
    ".claude/hooks/wxcli-gate.test.sh",                 # asserts the old type is denied
    ".claude/rules/repo-development.md",                # repo name
    "docs/CLAUDE.md",                                   # repo name
    "docs/reference/CLAUDE.md",                         # repo name
    "tools/merge_ledger.py",                            # repo name
    "tools/field_overrides.yaml",                       # repo name
)
OLD_WXCC_AGENT = re.compile(
    r"(?<![\w-])/wxcc-agent-builder\b|wxcc-agent-builder\.(md|toml)|wxcc-agent-builder\*{0,2} agent")


def _kept(path: str) -> bool:
    return any(path == k or (k.endswith("/") and path.startswith(k)) for k in OLD_AGENT_NAMES_KEPT)


def test_old_agent_names_only_in_records():
    """Spec §6: the rename lands in every file at once. Text describing the
    current system names `wxops`; only records keep the old names (P5-9)."""
    hits = subprocess.run(["git", "grep", "-l", "-F", "wxc-calling-builder"], cwd=REPO,
                          capture_output=True, text=True).stdout.split()
    assert [p for p in hits if not _kept(p)] == []

    tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.splitlines()
    stray = []
    for rel in tracked:
        if _kept(rel):
            continue
        path = REPO / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        stray += [f"{rel}:{n}" for n, ln in enumerate(text.splitlines(), 1)
                  if OLD_WXCC_AGENT.search(ln)]
    assert stray == []


def test_root_states_mcp_rule():
    """Spec §8 (Plan 6, P6-3): the MCP rule is in root and reaches AGENTS.md."""
    rule = "MCP only when it does the whole job."
    assert rule in ROOT_MD.read_text(encoding="utf-8")
    assert rule in (REPO / "src/wxcli/_playbook/AGENTS.md").read_text(encoding="utf-8")
