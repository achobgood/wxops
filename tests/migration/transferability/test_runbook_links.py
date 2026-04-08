"""Markdown link checker for runbook + kb-* extensions."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

from .conftest import RUNBOOK_DIR, REPO_ROOT, KB_DIR, slugify

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
ANCHOR_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def _extract_anchors(path: Path) -> set[str]:
    """All slug-form anchors in a markdown file."""
    text = path.read_text(encoding="utf-8")
    return {slugify(m.group(1)) for m in ANCHOR_RE.finditer(text)}


def _resolve_link(source_path: Path, target: str) -> tuple[Path | None, str | None]:
    """Resolve a markdown link target to (file_path, anchor) tuple.

    Returns (None, None) for external URLs (we don't validate those).
    """
    parsed = urlparse(target)
    if parsed.scheme in ("http", "https", "mailto"):
        return None, None  # External — skip
    # Split file part and anchor
    if "#" in target:
        file_part, anchor = target.split("#", 1)
    else:
        file_part, anchor = target, None
    if file_part:
        target_path = (source_path.parent / file_part).resolve()
    else:
        target_path = source_path  # Anchor-only link
    return target_path, anchor


@pytest.mark.parametrize(
    "doc_name",
    ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"],
)
def test_runbook_links_resolve(doc_name):
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")
    failures = []

    for label, target in LINK_RE.findall(text):
        target_path, anchor = _resolve_link(path, target.strip())
        if target_path is None:
            continue  # External URL
        if not target_path.exists():
            failures.append(f"{doc_name}: link to '{target}' (label '{label}') — file not found")
            continue
        if anchor:
            anchors = _extract_anchors(target_path)
            if slugify(anchor) not in anchors:
                failures.append(
                    f"{doc_name}: link to '{target}' (label '{label}') — anchor '{anchor}' not found in {target_path.name}"
                )

    assert not failures, "Broken links:\n  " + "\n  ".join(failures)


def test_kb_dissent_trigger_links_resolve():
    """Every dt-{domain}-NNN reference in the runbook docs must resolve to a kb-* doc."""
    failures = []
    for doc_name in ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"]:
        path = RUNBOOK_DIR / doc_name
        text = path.read_text(encoding="utf-8")
        for label, target in LINK_RE.findall(text):
            if "dt-" not in target.lower():
                continue
            target_path, anchor = _resolve_link(path, target.strip())
            if target_path is None or not target_path.exists():
                failures.append(f"{doc_name}: dissent-trigger link '{target}' → {target_path}")
                continue
            if anchor and slugify(anchor) not in _extract_anchors(target_path):
                failures.append(f"{doc_name}: DT anchor '#{anchor}' missing in {target_path.name}")

    assert not failures, "Broken DT links:\n  " + "\n  ".join(failures)
