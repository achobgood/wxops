"""Shared fixtures for transferability coverage tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_DIR = REPO_ROOT / "docs" / "runbooks" / "cucm-migration"
KB_DIR = REPO_ROOT / "docs" / "knowledge-base" / "migration"
ADVISOR_AGENT_PATH = REPO_ROOT / ".claude" / "agents" / "migration-advisor.md"
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "cucm-migrate" / "SKILL.md"

ANCHOR_RE = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.MULTILINE)
SLUG_RE = re.compile(r"[^a-z0-9-]")


def slugify(heading: str) -> str:
    """Convert a markdown heading to its GFM anchor slug.

    Mirrors GitHub's algorithm closely enough for our purposes:
    lowercase, replace spaces with hyphens, drop non-[a-z0-9-] chars.
    """
    text = heading.lower().strip()
    text = text.replace(" ", "-")
    return SLUG_RE.sub("", text)


@pytest.fixture
def operator_runbook_path() -> Path:
    return RUNBOOK_DIR / "operator-runbook.md"


@pytest.fixture
def decision_guide_path() -> Path:
    return RUNBOOK_DIR / "decision-guide.md"


@pytest.fixture
def tuning_reference_path() -> Path:
    return RUNBOOK_DIR / "tuning-reference.md"


@pytest.fixture
def advisor_agent_path() -> Path:
    return ADVISOR_AGENT_PATH


@pytest.fixture
def kb_dir() -> Path:
    return KB_DIR


def extract_anchors(path: Path) -> set[str]:
    """Return the set of slug-form anchors in a markdown file."""
    text = path.read_text(encoding="utf-8")
    return {slugify(m.group(1)) for m in ANCHOR_RE.finditer(text)}
