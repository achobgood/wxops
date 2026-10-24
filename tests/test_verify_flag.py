"""--verify: opt-in read-back after a write.

A 2xx proves the request was well-formed, not that the config is right —
`docs/reference/devices-core.md` records device-members accepting PRIMARY on
two ports with a 200, both persisting. --verify re-reads and reports the
fields that did not take.

Offered ONLY where a same-path GET exists. A --verify that silently verifies
nothing is worse than no flag at all: it turns an unchecked write into one that
looks checked. Every test here has a control proving the opposite case.
"""
import json

import pytest

from tools.openapi_parser import parse_tag
from tools.command_renderer import render_command_file
from wxcli.common import verify_write


def _spec(paths: dict) -> dict:
    return {"openapi": "3.0.0", "info": {"title": "t", "version": "1"}, "paths": paths}


def _op(summary: str, path_params: tuple[str, ...] = ()) -> dict:
    return {
        "tags": ["Things"],
        "summary": summary,
        "operationId": summary.replace(" ", ""),
        "parameters": [
            {"name": p, "in": "path", "required": True, "schema": {"type": "string"}}
            for p in path_params
        ],
        "responses": {"200": {"description": "ok", "content": {"application/json": {
            "schema": {"type": "object", "properties": {"id": {"type": "string"}}}}}}},
    }


def _item_op(summary: str) -> dict:
    return _op(summary, ("thingId",))


def _render(paths: dict) -> str:
    endpoints, _ = parse_tag("Things", _spec(paths), omit_query_params=["orgId"])
    return render_command_file("Things", endpoints, {})


ITEM = "/v1/things/{thingId}"


def test_put_with_a_same_path_get_offers_verify():
    code = _render({ITEM: {"get": _item_op("Get Thing"), "put": _item_op("Update Thing")}})
    assert '"--verify"' in code
    assert "verify_write(api, url," in code
    assert "from wxcli.common import verify_write" in code


def test_put_without_a_same_path_get_does_not():
    """The control. Nothing proves this endpoint's GET describes the resource."""
    code = _render({ITEM: {"put": _item_op("Update Thing")}})
    assert '"--verify"' not in code
    assert "verify_write" not in code


def test_the_import_is_omitted_when_nothing_in_the_module_can_verify():
    """Keeps 100+ untouched modules out of every regen diff."""
    code = _render({ITEM: {"get": _item_op("Get Thing")}})
    assert "from wxcli.common import verify_write" not in code


def test_a_post_is_not_offered_verify():
    """create returns the new resource already; the read-back adds nothing."""
    code = _render({"/v1/things": {"get": _op("List Things"), "post": _op("Create Thing")}})
    assert '"--verify"' not in code


def test_the_get_path_set_does_not_leak_between_modules():
    """_active_get_paths is module-global; a stale value would offer --verify
    on a module whose own spec has no read-back at all."""
    _render({ITEM: {"get": _item_op("Get Thing"), "put": _item_op("Update Thing")}})
    code = _render({ITEM: {"put": _item_op("Update Thing")}})
    assert '"--verify"' not in code


# ── runtime half: what verify_write actually reports ─────────────────────────

class _FakeSession:
    def __init__(self, result):
        self._result = result

    def rest_get(self, url, params=None):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeApi:
    def __init__(self, result):
        self.session = _FakeSession(result)


def test_verify_reports_a_field_that_did_not_take(capsys):
    api = _FakeApi({"name": "Sales", "enabled": False})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales", "enabled": True})
    err = capsys.readouterr().err
    assert "1 of 2 sent field(s) differ" in err
    assert "enabled: sent True, now False" in err


def test_verify_says_so_when_everything_matches(capsys):
    """Control: 'verified clean' and 'could not verify' must never look alike."""
    api = _FakeApi({"name": "Sales", "enabled": True, "serverOnly": "x"})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales", "enabled": True})
    err = capsys.readouterr().err
    assert "all 2 sent field(s) match" in err
    assert "differ" not in err


def test_verify_ignores_fields_the_caller_did_not_send(capsys):
    """A full-response diff would flag lastModified every call and bury the signal."""
    api = _FakeApi({"name": "Sales", "lastModified": "2026-08-01T00:00:00Z"})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales"})
    assert "all 1 sent field(s) match" in capsys.readouterr().err


def test_verify_flags_a_field_absent_from_the_read_back(capsys):
    # Changed by ADR-17: was asserted as "not present in read-back" inside the
    # "differ" list; an absent field is now its own "could not be verified" bucket.
    api = _FakeApi({"name": "Sales"})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales", "extension": "1001"})
    err = capsys.readouterr().err
    assert "not present in the read-back" in err
    assert "could not be verified" in err


def test_a_failed_read_back_is_reported_not_swallowed(capsys):
    """Silence here would read as success — the exact failure --verify prevents."""
    api = _FakeApi(RuntimeError("403 forbidden"))
    verify_write(api, "/v1/queues/x", None, {"name": "Sales"})
    err = capsys.readouterr().err
    assert "could not re-read" in err and "403 forbidden" in err
    assert "match" not in err


# ── subset comparison: the 2026-10-13 false mismatches (ADR-17) ──────────────
#
# Each case below was measured live on 2026-10-13: the write applied (checked
# with `show`), yet --verify printed "differ". The read-back is compared as a
# SUPERSET of what was sent, with str<->number/bool normalisation, and a field
# the read-back does not carry at all is "could not be verified", never "differ".


def _err(capsys, got, sent, url="/v1/x"):
    verify_write(_FakeApi(got), url, None, sent)
    return capsys.readouterr().err


class TestScalarNormalisation:
    """(a) numeric flags are str-typed; the read-back is a number."""

    def test_str_typed_number_matches_the_int_read_back(self, capsys):
        err = _err(capsys, {"messageExpiryEnabled": True, "numberOfDaysForMessageExpiry": 30},
                   {"messageExpiryEnabled": True, "numberOfDaysForMessageExpiry": "30"})
        assert "all 2 sent field(s) match" in err
        assert "field(s) differ" not in err

    def test_int_sent_matches_a_str_read_back(self, capsys):
        """The other direction: normalisation is symmetric."""
        assert "all 1 sent field(s) match" in _err(capsys, {"floorNumber": "3"}, {"floorNumber": 3})

    def test_str_number_matches_a_float_read_back(self, capsys):
        assert "all 1 sent field(s) match" in _err(capsys, {"rate": 2.5}, {"rate": "2.5"})

    def test_a_different_number_still_differs(self, capsys):
        err = _err(capsys, {"nextAssistantNumberOfRings": 3}, {"nextAssistantNumberOfRings": "4"})
        assert "1 of 1 sent field(s) differ" in err
        assert "nextAssistantNumberOfRings: sent '4', now 3" in err

    def test_bool_string_matches_bool_both_directions(self, capsys):
        assert "all 1 sent field(s) match" in _err(capsys, {"enabled": True}, {"enabled": "true"})
        assert "all 1 sent field(s) match" in _err(capsys, {"enabled": "false"}, {"enabled": False})

    def test_bool_is_not_a_number(self, capsys):
        """Python says True == 1; a boolean field reading back 1 is not proof."""
        assert "field(s) differ" in _err(capsys, {"enabled": 1}, {"enabled": True})
        assert "field(s) differ" in _err(capsys, {"enabled": True}, {"enabled": "1"})

    def test_a_non_numeric_string_is_not_coerced(self, capsys):
        assert "field(s) differ" in _err(capsys, {"name": 30}, {"name": "thirty"})

    def test_a_normalised_phone_number_still_differs(self, capsys):
        """Do not guess at E.164 rewriting: report it and let the caller judge."""
        err = _err(capsys, {"phoneNumber": "+1-2094571613"}, {"phoneNumber": "+12094571613"})
        assert "phoneNumber: sent '+12094571613', now '+1-2094571613'" in err


class TestSupersetReadBack:
    """(b) the server returns more than was sent: defaults, ids on nested objects."""

    def test_extra_nested_keys_are_ignored(self, capsys):
        got = {"callForwarding": {"always": {"enabled": True, "destination": "1001",
                                             "ringReminderEnabled": False},
                                  "busy": {"enabled": False}}}
        sent = {"callForwarding": {"always": {"enabled": True, "destination": "1001"}}}
        err = _err(capsys, got, sent)
        assert "all 1 sent field(s) match" in err

    def test_server_added_id_and_empty_arrays_are_ignored(self, capsys):
        """cc-desktop-profile viewableStatistics."""
        got = {"viewableStatistics": {"id": "abc", "agentStats": True, "queues": [], "teams": []}}
        sent = {"viewableStatistics": {"agentStats": True}}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_a_nested_value_that_did_not_take_is_named_by_path(self, capsys):
        got = {"callForwarding": {"always": {"enabled": False, "destination": "1001"}}}
        sent = {"callForwarding": {"always": {"enabled": True, "destination": "1001"}}}
        err = _err(capsys, got, sent)
        assert "1 of 1 sent field(s) differ" in err
        assert "callForwarding.always.enabled: sent True, now False" in err

    def test_list_of_dicts_matches_elements_carrying_extra_keys(self, capsys):
        """device-settings members: each member reads back with added fields."""
        got = {"members": [{"id": "B", "port": 2, "lineType": "SHARED_CALL_APPEARANCE", "x": 1},
                           {"id": "A", "port": 1, "lineType": "PRIMARY", "y": 2}]}
        sent = {"members": [{"id": "A", "port": "1"}, {"id": "B", "port": 2}]}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_one_read_back_element_cannot_satisfy_two_sent_elements(self, capsys):
        got = {"members": [{"id": "A", "port": 1}, {"id": "C", "port": 3}]}
        sent = {"members": [{"id": "A"}, {"id": "A"}]}
        assert "field(s) differ" in _err(capsys, got, sent)

    def test_matching_is_not_greedy(self, capsys):
        """A first-fit match would bind {} to A and leave {id:A} unmatched."""
        got = {"members": [{"id": "A"}, {"id": "B"}]}
        sent = {"members": [{}, {"id": "A"}]}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_a_shorter_list_in_the_read_back_is_a_real_mismatch(self, capsys):
        """person-call-settings-behavior.md: a second HOTDESKING_GUEST member was
        accepted with 200 and silently dropped."""
        got = {"members": [{"id": "OWNER", "port": 1}]}
        sent = {"members": [{"id": "OWNER", "port": 1}, {"id": "GUEST", "port": 2}]}
        err = _err(capsys, got, sent)
        assert "1 of 1 sent field(s) differ" in err
        assert "members: sent" in err

    def test_a_missing_nested_key_is_unverifiable_not_a_match(self, capsys):
        got = {"callForwarding": {"always": {"enabled": True}}}
        sent = {"callForwarding": {"always": {"enabled": True, "destination": "1001"}}}
        err = _err(capsys, got, sent)
        assert "all 1 sent field(s) match" not in err
        assert "field(s) differ" not in err
        assert "callForwarding.always.destination" in err
        assert "could not be verified" in err


class TestReorderedLists:
    """(c) arrays the server returns in a different order."""

    def test_scalar_list_in_another_order_matches(self, capsys):
        got = {"workingHours": [{"days": ["TUE", "THU", "FRI", "MON", "WED"],
                                 "startTime": "09:00", "endTime": "18:00"}]}
        sent = {"workingHours": [{"days": ["MON", "TUE", "WED", "THU", "FRI"],
                                  "startTime": "09:00", "endTime": "18:00"}]}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_dict_list_in_another_order_matches(self, capsys):
        """cc-skill-profile activeSkills."""
        got = {"activeSkills": [{"id": "2", "skillId": "s2", "proficiencyValue": 5},
                                {"id": "1", "skillId": "s1", "proficiencyValue": 8}]}
        sent = {"activeSkills": [{"skillId": "s1", "proficiencyValue": "8"},
                                 {"skillId": "s2", "proficiencyValue": 5}]}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_scalar_multiset_counts_duplicates(self, capsys):
        assert "field(s) differ" in _err(capsys, {"days": ["MON", "TUE"]}, {"days": ["MON", "MON"]})

    def test_a_scalar_list_with_an_extra_element_differs(self, capsys):
        """For a scalar list the list IS the value: an extra entry is a difference."""
        assert "field(s) differ" in _err(capsys, {"days": ["MON", "TUE", "WED"]}, {"days": ["MON", "TUE"]})


class TestAbsentFromReadBack:
    """(d) write/read key asymmetry: not fixable generically, so not a failure claim."""

    def test_absent_field_is_its_own_bucket(self, capsys):
        got = {"callParkNotificationEnabled": True, "monitoredElements": []}
        sent = {"enableCallParkNotification": True}
        err = _err(capsys, got, sent)
        assert "field(s) differ" not in err
        assert "all 1 sent field(s) match" not in err
        assert "0 matched, 1 could not be verified" in err
        assert ("enableCallParkNotification: could not be verified — not present in the "
                "read-back (the endpoint may name it differently)") in err

    def test_summary_never_says_all_match_when_one_is_unverifiable(self, capsys):
        err = _err(capsys, {"name": "Sales"}, {"name": "Sales", "extension": "1001"})
        assert "1 matched, 1 could not be verified" in err
        assert "all 2" not in err

    def test_a_real_difference_and_an_unverifiable_field_are_both_reported(self, capsys):
        err = _err(capsys, {"name": "Other"}, {"name": "Sales", "extension": "1001"})
        assert "1 of 2 sent field(s) differ" in err
        assert "name: sent 'Sales', now 'Other'" in err
        assert "1 sent path(s) could not be verified" in err  # round 2 (F4): counted in paths
        assert "extension: could not be verified" in err

    def test_sent_null_and_omitted_from_read_back_is_a_match(self, capsys):
        """A cleared field is omitted from the read-back (preferredAnswerEndpointId,
        person-call-settings-behavior.md); that is the cleared state, not a gap."""
        err = _err(capsys, {"other": 1}, {"preferredAnswerEndpointId": None})
        assert "all 1 sent field(s) match" in err


def test_verify_never_raises_or_exits(capsys):
    """The exit code is untouched in every outcome — verify_write returns None."""
    for got, sent in [({"a": 1}, {"a": 2}), ({}, {"a": 1}), ({"a": 1}, {"a": 1})]:
        assert verify_write(_FakeApi(got), "/v1/x", None, sent) is None


# ── round 2: reviewer D findings (F1-F5) ─────────────────────────────────────


class TestListLengthIsExact:
    """F1: a PUT that replaces a list must not read as applied when the server
    kept an element you removed."""

    def test_an_extra_object_in_the_read_back_differs(self, capsys):
        err = _err(capsys, {"agents": [{"id": "A"}, {"id": "B"}]}, {"agents": [{"id": "A"}]})
        assert "all 1 sent field(s) match" not in err
        assert "1 of 1 sent field(s) differ" in err

    def test_an_extra_nested_list_element_differs(self, capsys):
        assert "field(s) differ" in _err(capsys, {"x": [[2, 1], [3]]}, {"x": [[1, 2]]})

    def test_a_mixed_list_with_an_extra_element_differs(self, capsys):
        assert "field(s) differ" in _err(capsys, {"x": [1, {"id": "A"}, 99]}, {"x": [1, {"id": "A"}]})

    def test_a_three_step_reassignment_is_found(self, capsys):
        """Only a chain of reassignments matches all three; first-fit cannot."""
        sent = {"x": [{"a": 1}, {"a": 1, "b": 1}, {"a": 1, "b": 1, "c": 1}]}
        got = {"x": [{"a": 1, "b": 1, "c": 1}, {"a": 1, "b": 1}, {"a": 1}]}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_measured_hunt_group_agents_superset_still_matches(self, capsys):
        """(b) live: each agent reads back with fields the caller did not send."""
        got = {"agents": [{"id": "P2", "firstName": "B", "weight": "50", "type": "PEOPLE"},
                          {"id": "P1", "firstName": "A", "weight": "50", "type": "PEOPLE"}],
               "enabled": True}
        sent = {"agents": [{"id": "P1"}, {"id": "P2"}], "enabled": True}
        assert "all 2 sent field(s) match" in _err(capsys, got, sent)

    def test_measured_multimedia_profile_superset_still_matches(self, capsys):
        """(b) live: manuallyAssignable gains workItem/customMessaging."""
        got = {"manuallyAssignable": {"telephony": 0, "chat": 0, "email": 0, "social": 0,
                                      "workItem": 0, "customMessaging": 0}}
        sent = {"manuallyAssignable": {"telephony": 0, "chat": 0, "email": 0, "social": 0}}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)


class TestSentNull:
    """F2: a sent null is the one absence that counts as matched."""

    def test_null_whose_key_is_omitted_matches(self, capsys):
        assert "all 1 sent field(s) match" in _err(capsys, {"bar": 1}, {"foo": None})

    def test_null_when_the_old_value_is_still_present_differs(self, capsys):
        """If the server had ignored the clear, the old value comes back present."""
        err = _err(capsys, {"preferredAnswerEndpointId": "OLD"}, {"preferredAnswerEndpointId": None})
        assert "preferredAnswerEndpointId: sent None, now 'OLD'" in err

    def test_nested_null_follows_the_same_rule(self, capsys):
        assert "all 1 sent field(s) match" in _err(capsys, {"a": {"b": 1}}, {"a": {"c": None}})
        assert "a.c: sent None, now 2" in _err(capsys, {"a": {"c": 2}}, {"a": {"c": None}})


class TestCompareCannotEscape:
    """F3: the compare runs after a successful write and before its output;
    no input may turn it into a traceback and a non-zero exit."""

    def test_5000_identical_scalars(self, capsys):
        days = ["MONDAY"] * 5000
        assert "all 1 sent field(s) match" in _err(capsys, {"days": days}, {"days": list(days)})

    def test_5000_identical_objects_with_extra_keys(self, capsys):
        got = {"m": [{"enabled": True, "id": str(i)} for i in range(5000)]}
        assert "all 1 sent field(s) match" in _err(capsys, got, {"m": [{"enabled": True}] * 5000})

    def test_5000_identical_objects_shuffled_against_one_odd_one(self, capsys):
        """Forces the out-of-order path on a long list of interchangeable
        elements — the input that hit RecursionError at ~1,100."""
        sent = {"m": [{"enabled": True}] * 4999 + [{"enabled": False}]}
        got = {"m": [{"enabled": False}] + [{"enabled": True}] * 4999}
        err = _err(capsys, got, sent)
        assert "all 1 sent field(s) match" in err or "could not compare the read-back" in err
        assert "field(s) differ" not in err

    def test_5000_distinct_objects_reversed_never_raises(self, capsys):
        sent = {"m": [{"id": str(i)} for i in range(5000)]}
        got = {"m": list(reversed(sent["m"]))}
        err = _err(capsys, got, sent)
        assert "all 1 sent field(s) match" in err or "could not compare the read-back" in err
        assert "field(s) differ" not in err

    def test_a_reordered_list_at_the_limit_is_still_matched(self, capsys):
        sent = {"m": [{"id": str(i)} for i in range(1000)]}
        got = {"m": [dict(e, extra=1) for e in reversed(sent["m"])]}
        assert "all 1 sent field(s) match" in _err(capsys, got, sent)

    def test_an_exception_inside_the_compare_is_reported(self, capsys, monkeypatch):
        def boom(*a, **k):
            raise RecursionError("deep")
        monkeypatch.setattr("wxcli.common._compare", boom)
        err = _err(capsys, {"a": 1}, {"a": 1})
        assert "could not compare the read-back (RecursionError)" in err
        assert "match" not in err


class TestSummaryCountsAgree:
    """F4: the count line must describe exactly the items listed under it."""

    def test_absent_path_under_a_differing_field_is_counted(self, capsys):
        err = _err(capsys, {"c": {"d": 1}}, {"c": {"d": 9, "e": 2}})
        assert "c.d: sent 9, now 1" in err
        assert "0 could not be verified" not in err
        assert "1 sent path(s) could not be verified" in err
        assert "c.e: could not be verified" in err

    def test_two_absent_paths_in_one_field_are_both_counted(self, capsys):
        err = _err(capsys, {"c": {}}, {"c": {"d": 1, "e": 2}})
        assert "0 matched, 1 could not be verified (2 sent path(s) below)" in err


class TestAbsentKeyInsideAListElement:
    """F5, decided: a list element is matched as a whole, so a sent key the
    read-back element lacks makes the LIST differ (the safe direction). Once
    order is free there is no single element path to call unverifiable."""

    def test_reports_the_list_as_differing(self, capsys):
        err = _err(capsys, {"members": [{"id": "A"}]}, {"members": [{"id": "A", "newKey": 1}]})
        assert "1 of 1 sent field(s) differ" in err
        assert "could not be verified" not in err
