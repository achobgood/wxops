from pathlib import Path

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()


def test_trademark_disclaimer_present():
    assert "Unofficial community CLI — not affiliated with or endorsed by Cisco." in README


def test_pipx_install_is_the_lead():
    assert "pipx install wxcli" in README
    assert "pip install wxcli" in README


# test_from_source_subsection_retained removed: f28624b deliberately dropped the
# "From source" clone section so pipx install -> wxcli init is the only onramp.
# The test asserted the section was *retained*; its premise was reversed on
# purpose, so there is nothing left for it to guard.


def test_updating_section_exists():
    assert "## Updating" in README
    assert "wxcli update" in README
    assert "--check" in README
    # --migrate is intentionally undocumented here: it migrates a source/clone
    # install to pipx, and f28624b removed the source path from the README. The
    # flag still exists in update.py for anyone who already has a clone.
