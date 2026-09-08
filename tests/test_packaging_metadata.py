import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _project():
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)["project"]


def test_packaging_is_a_dependency():
    deps = _project()["dependencies"]
    assert any(d.split(">=")[0].split("[")[0].strip() == "packaging" for d in deps), deps


def test_readme_is_the_long_description():
    assert _project()["readme"] == "README.md"


def test_author_is_name_only_no_email():
    authors = _project()["authors"]
    assert authors == [{"name": "Adam Hobgood"}], authors


def test_urls_point_at_the_repo():
    urls = _project()["urls"]
    assert urls["Homepage"] == "https://github.com/achobgood/wxops"
    assert urls["Repository"] == "https://github.com/achobgood/wxops"
    assert "Issues" in urls and "Changelog" in urls


def test_keywords_and_classifiers():
    proj = _project()
    assert "webex" in proj["keywords"] and "cli" in proj["keywords"]
    classifiers = proj["classifiers"]
    assert "License :: OSI Approved :: Apache Software License" in classifiers
    assert any(c.startswith("Programming Language :: Python :: 3.11") for c in classifiers)
    assert "Environment :: Console" in classifiers
