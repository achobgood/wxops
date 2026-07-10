import json
from typer.testing import CliRunner
from wxcli.commands.org_health_cli import app

runner = CliRunner()


def test_analyze_writes_results(collected_dir, tmp_path):
    out = tmp_path / "results"
    r = runner.invoke(app, ["analyze", str(collected_dir), "--output", str(out)])
    assert r.exit_code == 0, r.output
    data = json.loads((out / "results.json").read_text())
    assert "findings" in data and "categories" in data


def test_analyze_invalid_collection_exits_1(tmp_path):
    r = runner.invoke(app, ["analyze", str(tmp_path), "--output", str(tmp_path / "r")])
    assert r.exit_code == 1


def test_report_generates_html(collected_dir, tmp_path):
    results = tmp_path / "results"
    runner.invoke(app, ["analyze", str(collected_dir), "--output", str(results)])
    r = runner.invoke(app, ["report", str(results), "--brand", "Acme", "--prepared-by", "SE"])
    assert r.exit_code == 0, r.output
    html = (results.parent / "report" / "org-health-report.html").read_text()
    assert "Acme" in html


def test_report_missing_results_exits_1(tmp_path):
    r = runner.invoke(app, ["report", str(tmp_path), "--brand", "A", "--prepared-by", "B"])
    assert r.exit_code == 1
