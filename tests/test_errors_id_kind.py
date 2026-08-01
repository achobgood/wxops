"""ID-kind detection: a wrong id KIND reports as 'not found', which misdiagnoses.

`device-settings` needs the callingDeviceId (kind CALLING_DEVICE). Given a
plain DEVICE id it returns 400 - 27123 - "Group access device not found",
which reads as though the phone does not exist and sends you to the wrong
problem. The kind is decodable locally, so the CLI can say what was passed.

Deliberately an allowlist: 79 CLI arguments declare a kind their own name
contradicts, so a general "declared != passed" check would fire on correct
calls. Every test below has a paired control.
"""
import base64
import sys

import pytest
import typer

from wxcli.errors import WebexError, decode_id_kind, handle_rest_error

UUID = "6176ab3b-b2c3-452f-b9c5-cf858236a2df"


def _id(kind: str) -> str:
    return base64.b64encode(f"ciscospark://us/{kind}/{UUID}".encode()).decode().rstrip("=")


def test_decodes_the_kind_out_of_a_webex_id():
    assert decode_id_kind(_id("DEVICE")) == "DEVICE"
    assert decode_id_kind(_id("CALLING_DEVICE")) == "CALLING_DEVICE"
    assert decode_id_kind(_id("PEOPLE")) == "PEOPLE"


def test_non_webex_tokens_decode_to_nothing():
    """Flags, values and random base64 must never be read as ids."""
    for junk in ["", "abc", "--calling-data", "true", "a" * 40, "Y2lzY29zcGFyay1ub3Q="]:
        assert decode_id_kind(junk) is None


def test_allowlisted_pair_gives_the_precise_remedy(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["wxcli", "device-settings", "show", _id("DEVICE")])
    with pytest.raises(typer.Exit):
        handle_rest_error(WebexError('{"errors":[{"errorCode":27123}]}', status_code=400))
    err = capsys.readouterr().err
    assert "callingDeviceId" in err
    assert "CALLING_DEVICE" in err
    assert "= DEVICE" in err


def test_the_correct_kind_gets_no_mismatch_tip(monkeypatch, capsys):
    """Control for the test above, which would otherwise pass on any 400."""
    monkeypatch.setattr(sys, "argv", ["wxcli", "device-settings", "show", _id("CALLING_DEVICE")])
    with pytest.raises(typer.Exit):
        handle_rest_error(WebexError('{"errors":[{"errorCode":27123}]}', status_code=400))
    err = capsys.readouterr().err
    assert "callingDeviceId" not in err
    assert "= CALLING_DEVICE" in err


def test_the_same_kind_on_an_unproven_group_stays_silent(monkeypatch, capsys):
    """Allowlist scoping: a DEVICE id is the correct id almost everywhere else."""
    monkeypatch.setattr(sys, "argv", ["wxcli", "devices", "show", _id("DEVICE")])
    with pytest.raises(typer.Exit):
        handle_rest_error(WebexError("nope", status_code=404))
    assert "callingDeviceId" not in capsys.readouterr().err


def test_decoded_ids_are_not_printed_on_unrelated_statuses(monkeypatch, capsys):
    """403 is an auth problem; listing ids there is noise, not a diagnosis."""
    monkeypatch.setattr(sys, "argv", ["wxcli", "devices", "show", _id("DEVICE")])
    with pytest.raises(typer.Exit):
        handle_rest_error(WebexError("forbidden", status_code=403))
    assert "decoded" not in capsys.readouterr().err
