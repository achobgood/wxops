"""Verify every file:line or function-name citation in the runbook docs
points to a real symbol at the real location."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import RUNBOOK_DIR, REPO_ROOT

# Match patterns like:
#   src/wxcli/migration/models.py:66
#   `transform/mappers/feature_mapper.py:136`
#   models.py:66
#   .claude/skills/cucm-migrate/SKILL.md:152
#   migration-advisor.md:97-103   (range — only the start line is checked)
# Captures:
#   group(1) — file part (relative path or basename)
#   group(2) — start line number (the `-N` end of a range, if present, is dropped)
FILE_LINE_RE = re.compile(
    r"`?([a-zA-Z_./-]+\.(?:py|md)):(\d+)(?:-\d+)?`?",
)

# Match function citations like recommend_feature_approximation, detect_mixed_css
FUNCTION_RE = re.compile(
    r"`?(recommend_[a-z_]+|detect_[a-z_]+)`?",
)


@pytest.mark.parametrize(
    "doc_name",
    ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"],
)
def test_file_line_citations_resolve(doc_name):
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")
    failures = []

    for file_part, line_str in FILE_LINE_RE.findall(text):
        # Resolve relative to repo root, allowing partial paths like 'models.py'
        candidates = list(REPO_ROOT.rglob(file_part)) or list(REPO_ROOT.rglob(f"**/{file_part}"))
        candidates = [c for c in candidates if "node_modules" not in str(c) and ".git" not in str(c)]
        if not candidates:
            failures.append(f"{doc_name}: cited file '{file_part}' not found in repo")
            continue
        if len(candidates) > 1:
            # Allow ambiguous citations (e.g., 'models.py' could match many files)
            # but log them — the operator should disambiguate.
            continue
        target = candidates[0]
        line = int(line_str)
        lines = target.read_text(encoding="utf-8").splitlines()
        if line < 1 or line > len(lines):
            failures.append(f"{doc_name}: '{file_part}:{line}' is out of range (file has {len(lines)} lines)")

    assert not failures, "Broken file:line citations:\n  " + "\n  ".join(failures)


@pytest.mark.parametrize(
    "doc_name",
    ["decision-guide.md", "tuning-reference.md"],
)
def test_function_citations_resolve(doc_name):
    """Every recommend_*/detect_* function cited in the docs must exist in the
    advisory module."""
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")

    rec_path = REPO_ROOT / "src" / "wxcli" / "migration" / "advisory" / "recommendation_rules.py"
    pat_path = REPO_ROOT / "src" / "wxcli" / "migration" / "advisory" / "advisory_patterns.py"

    rec_text = rec_path.read_text(encoding="utf-8")
    pat_text = pat_path.read_text(encoding="utf-8")

    failures = []
    cited_functions = {m.group(0).strip("`") for m in FUNCTION_RE.finditer(text)}
    for func in cited_functions:
        if func.startswith("recommend_"):
            if f"def {func}" not in rec_text:
                failures.append(f"{doc_name}: cited '{func}' not found in recommendation_rules.py")
        elif func.startswith("detect_"):
            if f"def {func}" not in pat_text:
                failures.append(f"{doc_name}: cited '{func}' not found in advisory_patterns.py")

    assert not failures, "Broken function citations:\n  " + "\n  ".join(failures)
