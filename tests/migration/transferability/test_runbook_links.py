"""Markdown link checker for runbook + kb-* extensions.

Wave 1 Phase A: skeleton only — collects link candidates and asserts they parse.
Wave 4 Phase G: full resolution against real anchors and file paths.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import RUNBOOK_DIR

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@pytest.mark.parametrize(
    "doc_name",
    ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"],
)
def test_links_parse_cleanly(doc_name):
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")
    links = LINK_RE.findall(text)
    # Phase A bar: every link target is non-empty.
    for label, target in links:
        assert target.strip(), f"{doc_name}: empty link target for label '{label}'"
