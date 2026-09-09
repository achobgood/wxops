"""A burned PyPI version can never be reused (spec row 29). The next version
is computed over the MAX of git tags and PyPI releases, so a tag whose publish
failed is skipped rather than retried."""
import pytest

from tools import sync_version as sv


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
