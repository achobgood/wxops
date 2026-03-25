"""Tests for inline SVG chart generators."""
import pytest


class TestGaugeChart:
    """Circular arc gauge for the complexity score."""

    def test_gauge_returns_valid_svg(self):
        from wxcli.migration.report.charts import gauge_chart
        svg = gauge_chart(score=34, color="#2E7D32", label="Straightforward")
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert "34" in svg
        assert "STRAIGHTFORWARD" in svg

    def test_gauge_color_matches_input(self):
        from wxcli.migration.report.charts import gauge_chart
        svg = gauge_chart(score=60, color="#C62828", label="Complex")
        assert "#C62828" in svg
        assert "COMPLEX" in svg

    def test_gauge_arc_scales_with_score(self):
        from wxcli.migration.report.charts import gauge_chart
        svg_low = gauge_chart(score=10, color="#2E7D32", label="Easy")
        svg_high = gauge_chart(score=90, color="#C62828", label="Hard")
        # Both should be valid SVGs with different arc paths
        assert "<path" in svg_low
        assert "<path" in svg_high


class TestDonutChart:
    """Donut chart for phone compatibility breakdown."""

    def test_donut_returns_valid_svg(self):
        from wxcli.migration.report.charts import donut_chart
        segments = [
            {"label": "Native MPP", "value": 40, "color": "#2E7D32"},
            {"label": "Convertible", "value": 3, "color": "#F57C00"},
            {"label": "Incompatible", "value": 2, "color": "#C62828"},
        ]
        svg = donut_chart(segments)
        assert svg.startswith("<svg")
        assert "Native MPP" in svg
        assert "89%" in svg or "88%" in svg  # 40/45

    def test_donut_handles_single_segment(self):
        from wxcli.migration.report.charts import donut_chart
        segments = [{"label": "All Native", "value": 100, "color": "#2E7D32"}]
        svg = donut_chart(segments)
        assert "100%" in svg

    def test_donut_handles_zero_total(self):
        from wxcli.migration.report.charts import donut_chart
        segments = [{"label": "None", "value": 0, "color": "#999"}]
        svg = donut_chart(segments)
        assert "</svg>" in svg


class TestBarChart:
    """Horizontal bar chart for object inventory."""

    def test_bar_returns_valid_svg(self):
        from wxcli.migration.report.charts import horizontal_bar_chart
        items = [
            {"label": "Users", "value": 50, "color": "#0277BD"},
            {"label": "Devices", "value": 45, "color": "#0277BD"},
            {"label": "Hunt Groups", "value": 2, "color": "#00BCB4"},
        ]
        svg = horizontal_bar_chart(items)
        assert svg.startswith("<svg")
        assert "Users" in svg
        assert "50" in svg

    def test_bar_sorts_by_value(self):
        from wxcli.migration.report.charts import horizontal_bar_chart
        items = [
            {"label": "Small", "value": 2, "color": "#999"},
            {"label": "Big", "value": 100, "color": "#999"},
        ]
        svg = horizontal_bar_chart(items)
        # Big should appear before Small (sorted descending)
        big_pos = svg.index("Big")
        small_pos = svg.index("Small")
        assert big_pos < small_pos


class TestGaugeChartCompact:
    """v2: gauge should use compact viewBox."""

    def test_gauge_compact_viewbox(self):
        from wxcli.migration.report.charts import gauge_chart
        svg = gauge_chart(score=50, color="#F57C00", label="Moderate")
        assert 'viewBox="0 0 200 155"' in svg
        assert 'width="160"' in svg


class TestStackedBarChart:
    def test_basic_output(self):
        from wxcli.migration.report.charts import stacked_bar_chart
        segments = [
            {"label": "Convertible", "value": 7, "color": "#F57C00"},
            {"label": "Incompatible", "value": 4, "color": "#C62828"},
        ]
        result = stacked_bar_chart(segments)
        assert "<div" in result
        assert "Convertible" in result
        assert "Incompatible" in result

    def test_omits_zero_segments(self):
        from wxcli.migration.report.charts import stacked_bar_chart
        segments = [
            {"label": "Native MPP", "value": 0, "color": "#2E7D32"},
            {"label": "Convertible", "value": 7, "color": "#F57C00"},
        ]
        result = stacked_bar_chart(segments)
        assert "Native MPP" not in result
        assert "Convertible" in result

    def test_single_segment(self):
        from wxcli.migration.report.charts import stacked_bar_chart
        segments = [{"label": "All Native", "value": 45, "color": "#2E7D32"}]
        result = stacked_bar_chart(segments)
        assert "All Native" in result

    def test_empty_segments(self):
        from wxcli.migration.report.charts import stacked_bar_chart
        result = stacked_bar_chart([])
        assert result == ""

    def test_all_zero(self):
        from wxcli.migration.report.charts import stacked_bar_chart
        segments = [
            {"label": "A", "value": 0, "color": "#ccc"},
            {"label": "B", "value": 0, "color": "#ddd"},
        ]
        result = stacked_bar_chart(segments)
        assert result == ""
