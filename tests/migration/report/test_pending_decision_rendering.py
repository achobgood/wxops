"""Real-data coverage for the Pending decision rendering path.

The handoff recorded this as untested: "`dcloud-fresh` has zero pending
decisions, so no real-data run exercises the 'Pending' rendering path. Unit
coverage exists ...; no stored project proves it."

The first half is true, the generalisation was not. Measured across all 19
stored projects, five carry pending decisions:

    dcloud-demo            353 pending,   0 resolved, 427 stale
    bridge-live-20260412   129 pending,   6 resolved, 417 stale
    phase10-test            43 pending
    test-setup              32 pending
    phase10-run2            30 pending

The two fixtures below reproduce the measured decision mixes of the first two.
`bridge-live` is the valuable one — it is the only stored project that carries
all three states at once, so it exercises the arithmetic that has to keep
pending, resolved and stale apart. `dcloud-demo` covers the zero-resolved edge,
where a naive "resolved / total" percentage divides by a denominator that is
mostly invalidated rows.
"""

from __future__ import annotations

import pytest

from wxcli.migration.decision_state import count_decisions
from wxcli.migration.report.appendix import _decisions_group
from wxcli.migration.store import MigrationStore

# type -> count, as measured
BRIDGE_LIVE_PENDING = {
    "MISSING_DATA": 61,
    "FORWARDING_LOSSY": 51,
    "ARCHITECTURE_ADVISORY": 13,
    "WORKSPACE_TYPE_UNCERTAIN": 3,
    "WORKSPACE_LICENSE_TIER": 1,
}
DCLOUD_DEMO_PENDING = {
    "MISSING_DATA": 275,
    "FORWARDING_LOSSY": 51,
    "ARCHITECTURE_ADVISORY": 13,
    "BUTTON_UNMAPPABLE": 6,
    "DEVICE_INCOMPATIBLE": 4,
    "WORKSPACE_TYPE_UNCERTAIN": 3,
    "WORKSPACE_LICENSE_TIER": 1,
}


def _seed(
    store: MigrationStore,
    pending: dict[str, int],
    resolved: int,
    stale_active: int,
    stale_retired: int,
):
    n = 0

    def save(dtype: str, chosen, resolved_by=None):
        nonlocal n
        n += 1
        store.save_decision({
            "decision_id": f"D{n:05d}",
            "type": dtype,
            "severity": "MEDIUM",
            "summary": f"{dtype} #{n}",
            "context": {},
            "options": [],
            "chosen_option": chosen,
            "resolved_by": resolved_by,
            "fingerprint": f"fp{n}",
            "run_id": "r1",
        })

    for dtype, count in pending.items():
        for _ in range(count):
            save(dtype, None)
    for _ in range(resolved):
        save("MISSING_DATA", "skip", "user")
    for _ in range(stale_active):
        save("DEVICE_INCOMPATIBLE", "__stale__", "stale")
    # Both projects carry exactly 10 stale rows of the type retired on
    # 2026-04-15. They are not outstanding work and `status` reports them
    # separately — a fixture that lumped them in would not reproduce the
    # rendering being verified.
    for _ in range(stale_retired):
        save("DEVICE_FIRMWARE_CONVERTIBLE", "__stale__", "stale")
    store.conn.commit()


@pytest.fixture
def bridge_live(tmp_path):
    store = MigrationStore(tmp_path / "bridge.db")
    _seed(store, BRIDGE_LIVE_PENDING, resolved=6, stale_active=407, stale_retired=10)
    yield store
    store.close()


@pytest.fixture
def dcloud_demo(tmp_path):
    store = MigrationStore(tmp_path / "demo.db")
    _seed(store, DCLOUD_DEMO_PENDING, resolved=0, stale_active=417, stale_retired=10)
    yield store
    store.close()


class TestCountsKeepTheThreeStatesApart:
    def test_bridge_live_measured_mix(self, bridge_live):
        """Reproduces `wxcli cucm status -p bridge-live-20260412` exactly:

            Decisions: 135 live (6 resolved, 129 pending)
              407 invalidated of 552 total ...
              10 retired ...
        """
        counts = count_decisions(bridge_live.get_all_decisions())
        assert counts.total == 552
        assert counts.pending == 129
        assert counts.resolved == 6
        assert counts.stale_active == 407
        assert counts.stale_retired == 10
        # The live population is what an operator can still act on.
        assert counts.live_total == 135

    def test_dcloud_demo_zero_resolved_edge(self, dcloud_demo):
        """Reproduces `wxcli cucm status -p dcloud-demo` exactly:

            Decisions: 353 live (0 resolved, 353 pending)
              417 invalidated of 780 total ...
              10 retired ...
        """
        counts = count_decisions(dcloud_demo.get_all_decisions())
        assert counts.total == 780
        assert counts.pending == 353
        assert counts.resolved == 0
        assert counts.stale_active == 417
        assert counts.stale_retired == 10
        assert counts.resolved_pct == 0

    def test_percentage_denominator_excludes_invalidated_rows(self, bridge_live):
        """6 of 135 live, not 6 of 552 — the stale rows are not a denominator."""
        counts = count_decisions(bridge_live.get_all_decisions())
        assert counts.resolved_pct == round(6 / 135 * 100)


class TestAppendixRendersPending:
    def test_pending_types_appear_with_their_counts(self, bridge_live):
        html_out = _decisions_group(bridge_live)
        for dtype, count in BRIDGE_LIVE_PENDING.items():
            assert f"({count} decision" in html_out or str(count) in html_out, dtype

    def test_render_does_not_claim_pending_rows_are_resolved(self, bridge_live):
        """The F04 defect: `__stale__` is truthy, so pending/stale read as done."""
        html_out = _decisions_group(bridge_live)
        assert "552 total, 6 auto-resolved" in html_out
        assert "407 invalidated by re-analysis" in html_out
        assert "10 retired" in html_out

    def test_zero_resolved_project_renders(self, dcloud_demo):
        html_out = _decisions_group(dcloud_demo)
        assert html_out
        assert "780 total, 0 auto-resolved" in html_out
        assert "417 invalidated by re-analysis" in html_out
        assert "10 retired" in html_out

    def test_every_pending_type_is_named(self, dcloud_demo):
        html_out = _decisions_group(dcloud_demo)
        # BUTTON_UNMAPPABLE is pending-only on this project — a type that
        # appears nowhere in dcloud-fresh, which is why it went unrendered.
        assert "Button" in html_out or "BUTTON_UNMAPPABLE" in html_out
