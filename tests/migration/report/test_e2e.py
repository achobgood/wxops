"""End-to-end test: collector file -> pipeline -> report."""


class TestEndToEnd:
    def test_full_pipeline_from_collector_file(self, tmp_path, sample_collector_file):
        """Ingest -> normalize -> map -> analyze -> report should produce valid HTML."""
        from wxcli.migration.report.ingest import ingest_collector_file
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.pipeline import normalize_discovery
        from wxcli.migration.transform.engine import TransformEngine
        from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline

        # 1. Ingest collector file
        raw_data, _metadata = ingest_collector_file(sample_collector_file)

        # 2. Store + normalize (pass 1 + pass 2)
        store = MigrationStore(tmp_path / "e2e.db")
        normalize_discovery(raw_data, store)

        # 3. Map (creates canonical objects with compatibility_tier, etc.)
        TransformEngine().run(store)

        # 4. Analyze
        AnalysisPipeline().run(store)

        # 5. Generate report
        from wxcli.migration.report.assembler import assemble_report

        html = assemble_report(
            store, brand="E2E Test Corp", prepared_by="Test SE"
        )

        assert "<!DOCTYPE html>" in html
        assert "E2E Test Corp" in html
        assert "complexity" in html.lower() or "straightforward" in html.lower()

        # Write and verify file
        out = tmp_path / "e2e-report.html"
        out.write_text(html)
        assert out.stat().st_size > 2000

    def test_report_from_populated_fixture(self, populated_store, tmp_path):
        """Report from test fixture should have all expected sections."""
        from wxcli.migration.report.assembler import assemble_report

        html = assemble_report(
            populated_store, brand="Fixture Corp", prepared_by="Fixture SE"
        )

        out = tmp_path / "fixture-report.html"
        out.write_text(html)

        # Executive sections
        assert "Migration Complexity" in html or "Complexity Score" in html
        assert "<svg" in html  # charts present
        assert "Fixture Corp" in html

        # Appendix sections
        assert "Object Inventory" in html
        assert "Decision Detail" in html
        assert "Device Inventory" in html
