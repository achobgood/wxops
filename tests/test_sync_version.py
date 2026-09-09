"""A burned PyPI version can never be reused (spec row 29). The next version
is computed over the MAX of git tags and PyPI releases, so a tag whose publish
failed is skipped rather than retried."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import sync_version as sv

REPO = Path(__file__).resolve().parent.parent


def _run(level, pypi_json):
    """Drive the real CLI offline. `python -m` puts cwd on sys.path, so cwd=REPO
    resolves `tools.*` to this checkout without touching PYTHONPATH."""
    return subprocess.run([sys.executable, "-m", "tools.sync_version",
                           "--level", level, "--pypi-json", str(pypi_json)],
                          cwd=REPO, capture_output=True, text=True)


def test_bump():
    assert sv.bump("1.6.0", "patch") == "1.6.1"
    assert sv.bump("1.6.3", "minor") == "1.7.0"
    with pytest.raises(ValueError):
        sv.bump("1.6.0", "major")   # never automatic (spec §6)


def test_next_skips_a_burned_tag():
    # v1.6.1 was tagged but its publish failed; PyPI never saw it. Next patch is 1.6.2.
    assert sv.next_version("patch", tags=["v1.6.0", "v1.6.1"], pypi=["1.6.0"]) == "v1.6.2"


def test_next_skips_a_pypi_only_version():
    assert sv.next_version("patch", tags=["v1.6.0"], pypi=["1.6.0", "1.6.1"]) == "v1.6.2"


def test_ignores_non_release_tags():
    assert sv.next_version("minor", tags=["v1.6.0", "v0.0.0-gate-probe", "junk"], pypi=[]) == "v1.7.0"


def test_main_refuses_when_pypi_metadata_is_unreadable(tmp_path):
    """A PyPI payload we cannot read is a refusal, never a guess (spec §7 rule 4).
    The tags are this repo's real ones, so assert the shape of the version rather
    than a literal that moves every release."""
    # 1. Readable metadata -> exit 0 and a v-prefixed version past the max we fed it.
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"releases": {"1.6.0": []}}))
    ok = _run("patch", good)
    assert ok.returncode == 0, ok.stderr
    printed = ok.stdout.strip()
    assert printed.startswith("v")
    assert sv._parse(printed) > (1, 6, 0)

    # 2. A 200 that parses but has no `releases` key must NOT degrade to git tags alone.
    no_key = tmp_path / "no_releases.json"
    no_key.write_text(json.dumps({"info": {}}))
    missing = _run("patch", no_key)
    assert missing.returncode == 2
    assert "refusing to choose a version blind" in missing.stderr
    assert missing.stdout.strip() == ""

    # 3. Unreadable file -> the same refusal.
    gone = _run("patch", tmp_path / "nope.json")
    assert gone.returncode == 2
    assert "refusing to choose a version blind" in gone.stderr
    assert gone.stdout.strip() == ""
