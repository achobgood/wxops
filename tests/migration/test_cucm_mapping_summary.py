"""F12 — `map` ran 26 mappers and named none of them.

The whole output was `Mapping complete in 4.3s` and `Decisions: 871`. There
were no per-mapper stats to print: `TransformResult` carried only `decisions`
and `errors`, while the engine had `objects_created` / `objects_updated` /
decision counts in scope per mapper and threw them away.

These tests cover both halves — the engine populating `TransformResult.stats`,
and the CLI itemising it.
"""

from __future__ import annotations

import re

from wxcli.commands import cucm as cucm_cli
from wxcli.migration.models import MapperError, MapperStats, TransformResult


def _render(result: TransformResult) -> str:
    with cucm_cli.console.capture() as cap:
        cucm_cli._print_mapping_summary(result)
    return " ".join(cap.get().split())


class TestEveryMapperIsNamed:
    def test_mapper_that_produced_nothing_still_gets_a_row(self):
        result = TransformResult(stats={
            "location_mapper": MapperStats(objects_created=12, decisions=3),
            "dect_mapper": MapperStats(),
        })
        text = _render(result)
        assert "location_mapper 12 created 0 updated 3 decisions" in text
        assert "dect_mapper 0 created 0 updated 0 decisions" in text

    def test_all_26_mappers_appear_when_all_are_clean(self):
        names = [f"mapper_{i:02d}" for i in range(26)]
        result = TransformResult(stats={n: MapperStats() for n in names})
        text = _render(result)
        for name in names:
            assert f"{name} 0 created 0 updated 0 decisions" in text

    def test_failed_mapper_is_named_and_marks_the_headline_incomplete(self):
        result = TransformResult(
            stats={
                "location_mapper": MapperStats(objects_created=12, decisions=3),
                "css_mapper": MapperStats(failed=True),
            },
            errors=[MapperError(mapper_name="css_mapper", error_message="boom")],
        )
        text = _render(result)
        assert "css_mapper FAILED" in text
        assert "1 of 2 mappers FAILED" in text
        assert "Mapper errors: 1" in text
        assert "css_mapper: boom" in text

    def test_no_failures_means_no_incomplete_caveat(self):
        result = TransformResult(stats={"location_mapper": MapperStats(objects_created=1)})
        text = _render(result)
        assert "incomplete" not in text
        assert "FAILED" not in text


class TestHeadlineAgreesWithItemisation:
    def test_totals_are_the_sum_of_the_rows(self):
        result = TransformResult(stats={
            "location_mapper": MapperStats(objects_created=12, objects_updated=2, decisions=3),
            "user_mapper": MapperStats(objects_created=300, objects_updated=10, decisions=45),
            "dect_mapper": MapperStats(),
        })
        text = _render(result)
        assert "Objects: 312 created, 12 updated — 48 decisions raised" in text

        created = sum(int(n) for n in re.findall(r"(\d+) created", text)[1:])
        updated = sum(int(n) for n in re.findall(r"(\d+) updated", text)[1:])
        decisions = sum(int(n) for n in re.findall(r"(\d+) decisions", text)[1:])
        assert (created, updated, decisions) == (312, 12, 48)


class TestEnginePopulatesStats:
    def test_engine_records_a_row_for_every_mapper_it_ran(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.engine import MAPPER_ORDER, TransformEngine

        store = MigrationStore(tmp_path / "migration.db")
        try:
            result = TransformEngine(config={}).run(store)
        finally:
            store.close()

        assert len(result.stats) == len(MAPPER_ORDER)
        # Sum of per-mapper decision counts must equal the aggregated list.
        assert sum(s.decisions for s in result.stats.values()) == len(result.decisions)

    def test_failed_mapper_gets_a_stats_row_rather_than_vanishing(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform import engine as engine_mod

        store = MigrationStore(tmp_path / "migration.db")
        target = engine_mod.MAPPER_ORDER[0]
        original = target.map

        def _boom(self, store):  # noqa: ANN001
            raise RuntimeError("planted")

        target.map = _boom
        try:
            result = engine_mod.TransformEngine(config={}).run(store)
        finally:
            target.map = original
            store.close()

        name = target.name or target.__name__
        assert result.stats[name].failed is True
        assert len(result.stats) == len(engine_mod.MAPPER_ORDER)
        assert any(e.mapper_name == name for e in result.errors)
