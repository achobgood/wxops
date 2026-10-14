"""Two round-4 guards: did-you-mean must not offer a delete for a read typo,
and a single-page fetch that left pages behind must say so.

Imports only stdlib/pytest plus in-repo modules, builds its own CliRunner, and
makes no network call — so it satisfies the .gitignore negation criteria and can
be tracked and run on CI.
"""

from __future__ import annotations

import pytest

from wxcli.suggest import (
    SafeSuggestGroup,
    filter_suggestions,
    is_destructive,
    is_read_intent,
)


# ── the classifier ───────────────────────────────────────────────────────────


class TestClassification:
    @pytest.mark.parametrize("typed", [
        "list-handsets", "show-vendors", "get-customer", "describe-queue",
        "find-user", "query-cdr", "view-settings", "search-tasks",
    ])
    def test_read_verbs_are_read_intent(self, typed):
        assert is_read_intent(typed)

    @pytest.mark.parametrize("typed", [
        "delet-handsets", "delete-dnis-queues", "create-queue",
        "update-access-codes", "purge-recordings",
    ])
    def test_write_verbs_are_not_read_intent(self, typed):
        assert not is_read_intent(typed)

    @pytest.mark.parametrize("typed", ["lst-handsets", "shw-vendors", "gett-user",
                                       "lis-queues", "sho-settings"])
    def test_a_mistyped_read_verb_is_still_read_intent(self, typed):
        """The verb is usually what got mistyped — exact matching missed these,
        which is most of the 32,203 flagged cases."""
        assert is_read_intent(typed)

    @pytest.mark.parametrize("typed", ["delet-x", "remov-x", "purg-x",
                                       "reset-x", "updat-x", "creat-x"])
    def test_mistyped_write_verbs_never_read_as_reads(self, typed):
        """The fuzzy cutoff must not let a destructive verb through — this is
        the guard the whole filter's safety rests on."""
        assert not is_read_intent(typed)

    @pytest.mark.parametrize("name", [
        "delete", "delete-handsets-dect-networks", "delete-person-id",
        "create-purge-inactive-entities", "create-soft-delete",
        "delete-recordings-recycle",
    ])
    def test_destructive_names_detected(self, name):
        assert is_destructive(name)

    @pytest.mark.parametrize("name", ["list", "show", "create", "update-settings"])
    def test_safe_names_not_flagged(self, name):
        assert not is_destructive(name)


class TestFiltering:
    def test_read_typo_drops_every_delete(self):
        """The detector's worst recorded case: all three candidates destroy."""
        out = filter_suggestions("get-handset-dect-networks", [
            "delete-handsets-dect-networks",
            "delete-handsets-dect-networks-1",
            "delete-handsets-dect-networks-bulk",
        ])
        assert out == []

    def test_read_typo_keeps_the_safe_candidate(self):
        out = filter_suggestions("lst-handsets", ["list-handsets", "delete-handsets"])
        assert out == ["list-handsets"]

    def test_delete_typo_still_gets_its_delete(self):
        """The safety of this whole change rests on this case."""
        out = filter_suggestions("delet-handsets", ["delete-handsets"])
        assert out == ["delete-handsets"]


# ── end to end through the click tree ────────────────────────────────────────


def _group():
    import typer

    app = typer.Typer(cls=SafeSuggestGroup)

    @app.command("list-handsets")
    def list_handsets():  # pragma: no cover - never invoked
        ...

    @app.command("delete-handsets")
    def delete_handsets():  # pragma: no cover - never invoked
        ...

    from typer.main import get_command
    return get_command(app)


def _invoke(args):
    # click's runner, not typer's: _group() already returns a built click
    # command, and typer's CliRunner would try to convert it a second time.
    from click.testing import CliRunner
    result = CliRunner().invoke(_group(), args)
    return result


class TestEndToEnd:
    def test_read_typo_never_names_a_delete(self):
        result = _invoke(["get-handsets"])
        assert result.exit_code != 0
        assert "delete-handsets" not in result.output

    def test_read_typo_with_no_safe_option_names_help(self):
        result = _invoke(["get-handsets"])
        assert "--help" in result.output

    def test_close_read_typo_still_suggests_the_read(self):
        result = _invoke(["list-handset"])
        assert "list-handsets" in result.output

    def test_delete_typo_still_suggests_the_delete(self):
        result = _invoke(["delete-handset"])
        assert "delete-handsets" in result.output


class TestWiredIntoTheRealTree:
    """The synthetic group above proves the class works; this proves it is
    actually ATTACHED. `_stamped` has to reach both the lazy path and the eager
    `mount_all` that CliRunner triggers, or production and tests disagree.
    """

    @staticmethod
    def _real_dect_group():
        from importlib import import_module
        from typer.main import get_command
        from wxcli.commands._lazy import _stamped

        return get_command(_stamped(import_module("wxcli.commands.dect_devices").app))

    def test_the_detectors_worst_case_no_longer_offers_a_delete(self):
        """Recorded worst case: `get-handset-dect-networks` returned three
        suggestions, all of them deletes, two hidden from --help."""
        from click.testing import CliRunner

        result = CliRunner().invoke(
            self._real_dect_group(), ["get-handset-dect-networks"])

        assert result.exit_code != 0
        assert "delete-handsets-dect-networks" not in result.output
        assert "--help" in result.output

    def test_a_real_delete_typo_still_gets_its_suggestion(self):
        from click.testing import CliRunner

        result = CliRunner().invoke(
            self._real_dect_group(), ["delete-handsets-dect-network"])

        assert "delete-handsets-dect-networks" in result.output


# ── the pagination note ──────────────────────────────────────────────────────


class _Resp:
    content = b"x"   # _warn_if_more_pages guards on this before parsing

    def __init__(self, link="", items=0):
        self.headers = {"Link": link} if link else {}
        self._items = items

    def json(self):
        return {"items": [{"id": i} for i in range(self._items)]}


NEXT = '<https://webexapis.com/v1/x?start=100>; rel="next"'


class TestPageNote:
    def _note(self, capsys, resp, params=None, monkeypatch=None):
        from wxcli.auth import _warn_if_more_pages
        if monkeypatch is not None:
            monkeypatch.delenv("WXCLI_NO_PAGE_WARN", raising=False)
        # Remedies are required since ADR-18; these cases test a list that
        # offers both, the shape whose wording predates that ADR.
        _warn_if_more_pages(resp, params, ("all", "offset"))
        return capsys.readouterr()

    def test_silent_when_there_is_no_next_page(self, capsys, monkeypatch):
        out = self._note(capsys, _Resp(items=5), monkeypatch=monkeypatch)
        assert out.err == "" and out.out == ""

    def test_notes_on_stderr_only(self, capsys, monkeypatch):
        out = self._note(capsys, _Resp(NEXT, 100), monkeypatch=monkeypatch)
        assert "more pages" in out.err
        assert out.out == "", "stdout must stay clean for -o json consumers"

    def test_names_all_first_then_offset(self, capsys, monkeypatch):
        """--all is the cheap remedy — one call. Paging by hand with --offset
        drags every page through the agent's context, so it comes second."""
        out = self._note(capsys, _Resp(NEXT, 100), monkeypatch=monkeypatch)
        assert "--all" in out.err
        assert "--offset 100" in out.err
        assert out.err.index("--all") < out.err.index("--offset")

    def test_contact_center_gets_a_note_despite_having_no_link_header(
            self, capsys, monkeypatch):
        """CC sends no Link header — a header-only check is blind to the 96
        commands --all exists for."""
        resp = _Resp(items=50)
        resp.json = lambda: {"data": [{"id": i} for i in range(50)],
                             "totalResources": 400, "pageNumber": 0}
        out = self._note(capsys, resp, monkeypatch=monkeypatch)
        assert "more pages" in out.err and "--all" in out.err

    def test_a_complete_response_carrying_a_total_stays_silent(
            self, capsys, monkeypatch):
        """total == returned means nothing is missing. Warning here would fire
        on every complete small response."""
        resp = _Resp(items=3)
        resp.json = lambda: {"data": [{"id": i} for i in range(3)],
                             "totalResources": 3}
        out = self._note(capsys, resp, monkeypatch=monkeypatch)
        assert out.err == ""

    def test_offset_accumulates_from_the_current_page(self, capsys, monkeypatch):
        out = self._note(capsys, _Resp(NEXT, 50), {"start": 100}, monkeypatch=monkeypatch)
        assert "--offset 150" in out.err

    def test_never_advises_limit_zero(self, capsys, monkeypatch):
        """On the 210 commands this fires for, --limit 0 is already the default
        and fetches no more — naming it would be an unrunnable next step."""
        out = self._note(capsys, _Resp(NEXT, 100), monkeypatch=monkeypatch)
        assert "--limit 0" not in out.err

    def test_flows_page_info_fires_and_names_absolute_offset(self, capsys, monkeypatch):
        """cc-flow list: 10 of 56 came back with no note at all (live,
        2026-10-13). The total lives under `pageInfo`. The remedy is the
        ABSOLUTE `--offset` of the next record: page-numbered commands translate
        it to page/pageSize (fetch_from_offset), and unlike `--page` it exists
        on every list command — `cc-tasks list` has no `--page` flag."""
        resp = _Resp(items=10)
        resp.json = lambda: {"data": [{"id": i} for i in range(10)],
                             "pageInfo": {"currentPage": 0, "totalRecords": 56,
                                          "pageSize": 10, "totalPages": 6}}
        out = self._note(capsys, resp, monkeypatch=monkeypatch)
        assert "more pages" in out.err
        assert "--offset 10 " in out.err and "--page" not in out.err

    def test_last_numbered_page_stays_silent(self, capsys, monkeypatch):
        """Comparing the collection total with THIS page's count fired on every
        page after the first, the last one included."""
        resp = _Resp(items=6)
        resp.json = lambda: {"data": [{"id": i} for i in range(6)],
                             "pageInfo": {"currentPage": 5, "totalRecords": 56,
                                          "pageSize": 10, "totalPages": 6}}
        assert self._note(capsys, resp, monkeypatch=monkeypatch).err == ""

    def test_cc_meta_page_names_the_next_records_offset(self, capsys, monkeypatch):
        resp = _Resp(items=5)
        resp.json = lambda: {"data": [{"id": i} for i in range(5)],
                             "meta": {"page": 2, "pageSize": 5,
                                      "totalPages": 5, "totalRecords": 21}}
        out = self._note(capsys, resp, monkeypatch=monkeypatch)
        assert "--offset 15 " in out.err   # (page 2 + 1) * pageSize 5

    def test_a_page_numbered_link_names_its_offset(self, capsys, monkeypatch):
        """CC v1 lists and /v1/tasks send a Link header whose next URL pages by
        number (live 2026-10-13: `/v1/tasks?from=…&page=1&pageSize=100`)."""
        link = '</v1/tasks?from=1&page=2&pageSize=100>; rel="next"'
        out = self._note(capsys, _Resp(link, 100), monkeypatch=monkeypatch)
        assert "--offset 200 " in out.err and "--page" not in out.err

    def test_request_page_without_body_position(self, capsys, monkeypatch):
        """No page metadata in the body: the request's own page/pageSize."""
        resp = _Resp(items=5)
        resp.json = lambda: {"data": [{"id": i} for i in range(5)],
                             "totalRecords": 40}
        out = self._note(capsys, resp, {"page": 3, "pageSize": 5}, monkeypatch=monkeypatch)
        assert "--offset 20 " in out.err

    def test_bulk_export_counts_resources_and_trusts_rel(self, capsys, monkeypatch):
        """CC bulk-export (`cc-global-vars list`) wraps records in `resources`.
        Counting `items`/`data` saw 0 of 6 and printed the note on a complete
        response (live 2026-10-13). `rel` says whether pages remain; its
        `pageNumber` does not track the page served (page=0 -> 1, page=1 -> 2,
        page=2 -> 2, live), so the offset comes from the request."""
        resp = _Resp(items=9)
        resp.json = lambda: {"totalResources": 9, "pageNumber": 0, "pageSize": 50,
                             "rel": "last", "resources": [{"id": i} for i in range(9)]}
        assert self._note(capsys, resp, monkeypatch=monkeypatch).err == ""
        resp.json = lambda: {"totalResources": 9, "pageNumber": 1, "pageSize": 4,
                             "rel": "next", "resources": [{"id": i} for i in range(4)]}
        err = self._note(capsys, resp, {"page": 0, "pageSize": 4}, monkeypatch=monkeypatch).err
        assert "4 records returned" in err and "--offset 4 " in err
        resp.json = lambda: {"totalResources": 9, "pageNumber": 2, "pageSize": 4,
                             "rel": "next", "resources": [{"id": i} for i in range(4)]}
        err = self._note(capsys, resp, {"page": 1, "pageSize": 4}, monkeypatch=monkeypatch).err
        assert "--offset 8 " in err
        resp.json = lambda: {"totalResources": 9, "pageNumber": 2, "pageSize": 4,
                             "rel": "last", "resources": [{"id": 8}]}
        assert self._note(capsys, resp, {"page": 2, "pageSize": 4}, monkeypatch=monkeypatch).err == ""

    def test_env_var_silences_it(self, capsys, monkeypatch):
        monkeypatch.setenv("WXCLI_NO_PAGE_WARN", "1")
        from wxcli.auth import _warn_if_more_pages
        _warn_if_more_pages(_Resp(NEXT, 100), None, ("all", "offset"))
        assert capsys.readouterr().err == ""
