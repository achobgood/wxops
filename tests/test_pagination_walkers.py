"""The two page-walkers `follow_pagination` could never see, plus the guarantee
that adding them changed no command's default.

Contact Center (`page`/`pageSize`) and SCIM (`startIndex`/`count`) send no
`Link` header, so the existing Link walker returns their first page and stops —
96 and 5 of the 210 single-fetch list commands respectively. These back `--all`.

No network: a fake session records the params of every request and replays
canned pages. Imports only stdlib/pytest and in-repo modules, and builds nothing
from conftest, so it satisfies the .gitignore negation criteria.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from wxcli.auth import WebexSession, _items_of

REPO = Path(__file__).resolve().parent.parent


class FakeSession(WebexSession):
    """A WebexSession whose _request replays pages and records what was asked."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls: list[dict] = []

    def _request(self, method, url, params=None, **kw):  # type: ignore[override]
        self.calls.append(dict(params or {}))
        body = self.pages[len(self.calls) - 1] if len(self.calls) <= len(self.pages) else {}

        class _R:
            is_success = True
            content = b"x"
            headers: dict = {}

            def json(self_inner):
                return body

        return _R()


def page(key, n, start=0):
    return {key: [{"id": start + i} for i in range(n)]}


# ── Contact Center: page / pageSize ──────────────────────────────────────────


class TestFollowPageParam:
    def test_walks_until_a_short_page(self):
        s = FakeSession([page("data", 200), page("data", 200, 200), page("data", 7, 400)])
        out = list(s.follow_page_param("u", item_key="data", page_size=200))
        assert len(out) == 407
        assert [c["page"] for c in s.calls] == [0, 1, 2]

    def test_a_single_short_page_makes_one_request(self):
        s = FakeSession([page("data", 3)])
        assert len(list(s.follow_page_param("u", item_key="data", page_size=200))) == 3
        assert len(s.calls) == 1

    def test_an_exactly_full_final_page_costs_one_empty_request(self):
        """Documented cost of terminating on a short page rather than a total."""
        s = FakeSession([page("data", 200), page("data", 0, 200)])
        assert len(list(s.follow_page_param("u", item_key="data", page_size=200))) == 200
        assert len(s.calls) == 2

    def test_it_sends_the_page_size_it_walks_by(self):
        """If the request size and the termination test disagree, the walk stops
        early on the first page and silently truncates."""
        s = FakeSession([page("data", 50)])
        list(s.follow_page_param("u", item_key="data", page_size=50))
        assert s.calls[0]["pageSize"] == 50

    def test_a_caller_supplied_page_size_is_respected(self):
        s = FakeSession([page("data", 10), page("data", 2, 10)])
        out = list(s.follow_page_param("u", params={"pageSize": 10}, item_key="data"))
        assert len(out) == 12
        assert all(c["pageSize"] == 10 for c in s.calls)

    def test_caller_params_survive_every_page(self):
        s = FakeSession([page("data", 5), page("data", 1, 5)])
        list(s.follow_page_param("u", params={"orgId": "abc", "pageSize": 5},
                                 item_key="data"))
        assert all(c["orgId"] == "abc" for c in s.calls)

    def test_empty_first_page_terminates(self):
        s = FakeSession([{"data": []}])
        assert list(s.follow_page_param("u", item_key="data")) == []
        assert len(s.calls) == 1


# ── SCIM: startIndex / count ─────────────────────────────────────────────────


class TestFollowScim:
    def test_start_index_is_one_based_and_advances(self):
        s = FakeSession([page("Resources", 100), page("Resources", 4, 100)])
        out = list(s.follow_scim("u", count=100))
        assert len(out) == 104
        assert [c["startIndex"] for c in s.calls] == [1, 101]

    def test_total_results_ends_the_walk(self):
        pages = [{"Resources": [{"id": i} for i in range(2)], "totalResults": 2}]
        s = FakeSession(pages)
        assert len(list(s.follow_scim("u", count=2))) == 2
        assert len(s.calls) == 1

    def test_a_server_that_omits_total_results_still_terminates(self):
        s = FakeSession([page("Resources", 2), page("Resources", 1, 2)])
        assert len(list(s.follow_scim("u", count=2))) == 3
        assert len(s.calls) == 2


# ── the wrapper-shape extractor ──────────────────────────────────────────────


class TestItemsOf:
    @pytest.mark.parametrize("body,expected", [
        ({"items": [1, 2]}, [1, 2]),
        ({"data": [1]}, [1]),
        ({"Resources": [1, 2, 3]}, [1, 2, 3]),
        ([1, 2], [1, 2]),
        ({"meta": {}, "data": []}, []),
        ({"nothing": 1}, []),
        (None, []),
    ])
    def test_shapes(self, body, expected):
        assert _items_of(body, "items") == expected


# ── the guarantee: no command's DEFAULT changed ──────────────────────────────


class TestDefaultsUnchanged:
    """--all is opt-in. Adding it must not move a single command into the
    fetch-everything-by-default branch — that branch is gated on the spec
    declaring a Link header, exactly as it was before.
    """

    @staticmethod
    def _count(pattern: str, tree: str | None = None) -> int:
        cmds = REPO / "src/wxcli/commands"
        total = 0
        if tree is None:
            for f in sorted(cmds.glob("*.py")):
                total += len(re.findall(pattern, f.read_text()))
            return total
        files = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", tree, "src/wxcli/commands/"],
            capture_output=True, text=True, cwd=REPO).stdout.split()
        for f in files:
            if not f.endswith(".py"):
                continue
            src = subprocess.run(["git", "show", f"{tree}:{f}"],
                                 capture_output=True, text=True, cwd=REPO).stdout
            total += len(re.findall(pattern, src))
        return total

    def test_the_default_walk_all_branch_did_not_grow(self):
        before = self._count(
            r"if limit > 0:\n            result = api\.session\.rest_get", tree="HEAD")
        after = self._count(r"if limit > 0 and not all_pages:")
        assert before == after, (
            f"{after - before} commands changed what they return by DEFAULT — "
            "--all is supposed to be opt-in")

    def test_every_generated_list_command_accepts_all(self):
        """A flag on most list commands but not all teaches a rule that breaks
        unpredictably; that is why --output was made uniform.

        Counted on the generated PAGING limit specifically — its help string is
        emitted by exactly one renderer site. A bare `"--limit"` count is the
        wrong denominator three ways: `licenses show` declares a spec parameter
        genuinely named `limit` (a cap on users returned, nothing to do with
        paging), `converged-recordings export` is hand-written, and the eleven
        dev-only `fs_*` modules are gitignored and absent from the wheel.
        """
        cmds = REPO / "src/wxcli/commands"
        paging_limit = all_flag = 0
        for f in sorted(cmds.glob("*.py")):
            if f.name.startswith("fs_"):
                continue
            src = f.read_text()
            paging_limit += src.count(
                'help="Max results (0=all for paginated endpoints')
            all_flag += src.count('"--all", help="Fetch every page')
        assert paging_limit > 400, "denominator collapsed — the marker moved"
        assert all_flag == paging_limit
