"""handle_rest_error: does every failure name a literal next command?

Constructs WebexError directly — nothing here touches the network, imports a
generated command module, or shells out to wxcli.
"""

import pytest
import typer

from wxcli.errors import (
    _ERROR_TIPS,
    _MESSAGE_TIPS,
    _STATUS_TIPS,
    WebexError,
    handle_rest_error,
)


def run(err, *, status=None, argv=None, monkeypatch=None):
    """Invoke the handler, assert it exits 1, return captured stderr."""
    if argv is not None:
        monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(typer.Exit) as exc:
        handle_rest_error(WebexError(err, status_code=status))
    assert exc.value.exit_code == 1


def body(code=None, message="err"):
    import json as _json
    payload = {"message": message}
    if code is not None:
        payload["errors"] = [{"errorCode": code}]
    return _json.dumps(payload)


# ── every existing tip still fires ───────────────────────────────────────────


class TestExistingTipsStillFire:
    def test_4008_names_a_command(self, capsys):
        run(body(4008))
        err = capsys.readouterr().err
        assert "Webex Calling license" in err
        assert "wxcli people show" in err

    def test_9601_names_a_command(self, capsys):
        run(body(9601))
        err = capsys.readouterr().err
        assert "user-level OAuth" in err
        assert "wxcli configure" in err

    def test_25008_still_names_json_body(self, capsys):
        run(body(25008))
        assert "--json-body" in capsys.readouterr().err

    def test_25409_still_names_professional_license(self, capsys):
        run(body(25409))
        assert "Professional license" in capsys.readouterr().err

    def test_28018_still_names_the_flag(self, capsys):
        run(body(28018))
        assert "--has-cx-essentials true" in capsys.readouterr().err

    def test_message_tip_fires_and_names_a_command(self, capsys):
        run(body(message="Target user not authorized"))
        err = capsys.readouterr().err
        assert "user-level OAuth" in err
        assert "wxcli configure" in err

    def test_every_tip_table_entry_names_a_command_or_flag(self):
        """No tip may state a cause without naming something to type."""
        literals = ("wxcli ", "--", "-o ", "WXCLI_", "developer.webex.com")
        for table in (_ERROR_TIPS, _MESSAGE_TIPS, _STATUS_TIPS):
            for key, tip in table.items():
                assert any(lit in tip for lit in literals), f"{key} names no action: {tip}"


# ── the status-code fallback ─────────────────────────────────────────────────


class TestStatusFallback:
    def test_400_names_generate_json_body(self, capsys):
        run(body(message="displayName cannot be null."), status=400)
        assert "--generate-json-body" in capsys.readouterr().err

    def test_405_points_at_licensing_not_the_verb(self, capsys):
        """Live probe 8: the 'PUT is not supported' body was misleading."""
        run(body(message="The requested resource only allows certain HTTP request "
                         "methods. 'PUT' is not supported."), status=405)
        err = capsys.readouterr().err
        assert "wxcli people show" in err
        assert "--calling-data true" in err

    def test_401_names_configure(self, capsys):
        run("Unauthorized", status=401)
        assert "wxcli configure" in capsys.readouterr().err

    def test_401_org_access_points_at_the_org_id_not_the_token(self, capsys):
        """Live 2026-10-13: the CC host rejected the base64 org id with this
        body. The generic 401 tip sent you to replace a perfectly good token."""
        live = ('{"trackingId":"GTWY_x","error":{"key":401,"message":[{"description":'
                '"Token does not have access to OrgId:Y2lzY29zcGFyazovL3VzL09SR0FO"}]}}')
        run(live, status=401)
        err = capsys.readouterr().err
        assert "bare UUID" in err and "wxcli whoami" in err
        assert "expired, or revoked" not in err

    def test_403_names_whoami(self, capsys):
        run("HTTP Status 403 - Forbidden", status=403)
        err = capsys.readouterr().err
        assert "wxcli whoami" in err
        assert "wxcli switch-org" in err

    def test_404_names_whoami_and_list(self, capsys):
        run(body(message="Person not found"), status=404)
        err = capsys.readouterr().err
        assert "list subcommand" in err
        assert "wxcli whoami" in err

    def test_409_names_cleanup(self, capsys):
        run(body(50003, "Location is being referenced, cannot be deleted"), status=409)
        assert "wxcli cleanup run" in capsys.readouterr().err

    def test_429_names_the_env_var(self, capsys):
        run("Too Many Requests", status=429)
        assert "WXCLI_MAX_ATTEMPTS" in capsys.readouterr().err

    def test_untipped_error_code_still_reaches_the_status_fallback(self, capsys):
        """25024 has no _ERROR_TIPS entry — the status tip must still land."""
        run(body(25024, "Invalid field value: location"), status=400)
        err = capsys.readouterr().err
        assert "Invalid field value: location" in err
        assert "--generate-json-body" in err

    def test_unmapped_status_prints_body_only(self, capsys):
        """A status with no tip still prints the body, and still exits 1."""
        run(body(message="Internal Server Error"), status=500)
        err = capsys.readouterr().err
        assert "Internal Server Error" in err
        assert "Tip:" not in err

    def test_unmatched_error_with_no_status_prints_body_only(self, capsys):
        run("some unknown error")
        err = capsys.readouterr().err
        assert "some unknown error" in err
        assert "Tip:" not in err

    def test_specific_code_beats_the_status_fallback(self, capsys):
        """A known errorCode on a 404 gets its own tip, not the generic one."""
        run(body(4008), status=404)
        err = capsys.readouterr().err
        assert "Webex Calling license" in err
        assert "wxcli switch-org" not in err


# ── error code 4003: the removed table entry ─────────────────────────────────


class TestCode4003:
    def test_4003_is_not_in_the_code_table(self):
        assert 4003 not in _ERROR_TIPS

    def test_4003_with_the_auth_message_still_gets_the_oauth_tip(self, capsys):
        """The path the old _ERROR_TIPS[4003] entry served — now via _MESSAGE_TIPS."""
        run(body(4003, "Target user not authorized"), status=400)
        err = capsys.readouterr().err
        assert "user-level OAuth" in err
        assert "wxcli configure" in err
        # The message tip wins over the generic 400 tip.
        assert "--generate-json-body" not in err

    def test_4003_user_not_found_gets_no_oauth_tip(self, capsys):
        """4003 also means 'User Not Found' — must not claim a token problem."""
        run(body(4003, "User Not Found"), status=404)
        err = capsys.readouterr().err
        assert "user-level OAuth" not in err
        assert "wxcli whoami" in err


# ── CC 403 ───────────────────────────────────────────────────────────────────


class TestContactCenter403:
    def test_cc_403_from_argv_gets_the_scope_tip(self, capsys, monkeypatch):
        run("Forbidden", status=403, argv=["wxcli", "cc-queue", "list"], monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "cjp:config_read" in err
        assert "wxcli configure" in err
        # The April 2026 "PATs always get 403" claim was disproven live on
        # 2026-10-13 (full-admin PAT: 200 on cc-flow/cc-queue/cc-entry-point/
        # cc-global-vars). The tip must not repeat it.
        assert "always gets 403" not in err
        assert "full-admin personal access token carries them" in err

    def test_cc_403_survives_a_leading_global_flag(self, capsys, monkeypatch):
        run("Forbidden", status=403,
            argv=["wxcli", "--no-update-check", "cc-agents", "list"], monkeypatch=monkeypatch)
        assert "cjp:config_read" in capsys.readouterr().err

    def test_cc_403_from_the_body_naming_the_host(self, capsys, monkeypatch):
        run("api.wxcc-us1.cisco.com: forbidden", status=403,
            argv=["wxcli", "people", "list"], monkeypatch=monkeypatch)
        assert "cjp:config_read" in capsys.readouterr().err

    def test_the_old_body_only_shape_no_longer_needs_403_in_the_text(self, capsys, monkeypatch):
        """Regression: the old branch needed the literal '403' inside the body."""
        run("wxcc denied", status=403, argv=["wxcli", "people", "list"], monkeypatch=monkeypatch)
        assert "cjp:config_read" in capsys.readouterr().err

    def test_non_cc_403_gets_the_generic_tip_not_the_scope_tip(self, capsys, monkeypatch):
        run("Forbidden", status=403, argv=["wxcli", "people", "list"], monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "cjp:config_read" not in err
        assert "wxcli whoami" in err

    def test_cc_403_carrying_a_known_error_code_takes_the_code_branch(self, capsys, monkeypatch):
        """Documented ordering: a specific errorCode outranks the generic scope tip."""
        run(body(28018), status=403,
            argv=["wxcli", "cc-queue", "list"], monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "--has-cx-essentials true" in err
        assert "cjp:config_read" not in err

    def test_cc_404_is_not_treated_as_a_scope_problem(self, capsys, monkeypatch):
        run("Not found", status=404, argv=["wxcli", "cc-queue", "list"], monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "cjp:config_read" not in err
        assert "wxcli whoami" in err


# ── exit status ──────────────────────────────────────────────────────────────


def test_every_handled_error_exits_non_zero(monkeypatch):
    """No path through handle_rest_error may report success."""
    monkeypatch.setattr("sys.argv", ["wxcli", "cc-queue", "list"])
    for err, status in [
        (body(4008), None), (body(message="Target user not authorized"), 400),
        ("Forbidden", 403), ("boom", 500), ("boom", None),
    ]:
        with pytest.raises(typer.Exit) as exc:
            handle_rest_error(WebexError(err, status_code=status))
        assert exc.value.exit_code == 1


# ── whoami: the command every auth tip points at ─────────────────────────────


class TestWhoamiRoutesThroughTheHandler:
    """`whoami` used to call rest_get bare, so a bad token produced a traceback.

    Five tips in this module end with "confirm it works with: wxcli whoami", so
    it is the command an agent runs when auth is ALREADY broken. Asserting only
    on the exit code would not catch a regression — CliRunner reports exit 1 for
    an uncaught exception too, which is exactly what the bug looked like.
    """

    # CliRunner is built here rather than taken from the `runner` fixture: the
    # .gitignore negation for a tracked test requires no dependency on the
    # untracked tests/conftest.py.
    @staticmethod
    def _runner():
        from typer.testing import CliRunner
        return CliRunner()

    @staticmethod
    def _out(result):
        return result.output + (getattr(result, "stderr", "") or "")

    @staticmethod
    def _patch(monkeypatch, exc):
        class _Session:
            def rest_get(self, *a, **kw):
                raise exc

        class _Api:
            session = _Session()

        monkeypatch.setattr("wxcli.main.get_api", lambda **kw: _Api())

    def test_expired_token_gives_a_tip_not_a_traceback(self, monkeypatch):
        from wxcli.main import app
        self._patch(monkeypatch, WebexError(
            '{"message":"The request requires a valid access token."}',
            status_code=401))

        result = self._runner().invoke(app, ["whoami"])

        assert result.exit_code == 1
        assert not isinstance(result.exception, WebexError), (
            "WebexError escaped whoami — this is the original bug")
        out = self._out(result)
        assert "Tip:" in out and "wxcli configure" in out
        assert "Traceback" not in out

    def test_transport_failure_gives_a_tip_not_a_traceback(self, monkeypatch):
        from wxcli.main import app
        self._patch(monkeypatch, TimeoutError("read timed out"))

        result = self._runner().invoke(app, ["whoami"])

        assert result.exit_code == 1
        assert not isinstance(result.exception, TimeoutError)
        out = self._out(result)
        assert "Tip:" in out
        assert "Traceback" not in out


# ── tips that named the wrong cause, measured live 2026-10-13 ────────────────


def run_full(err, *, status, headers=None, argv=None, monkeypatch=None):
    """Like run(), but builds WebexError the way auth.py does (status + body)."""
    import json as _json
    if argv is not None:
        monkeypatch.setattr("sys.argv", argv)
    try:
        parsed = _json.loads(err) if err else None
    except ValueError:
        parsed = None
    kwargs = {"status_code": status, "body": parsed}
    if headers is not None:
        kwargs["headers"] = headers
    with pytest.raises(typer.Exit) as exc:
        handle_rest_error(WebexError(err, **kwargs))
    assert exc.value.exit_code == 1


class TestLiveMisdirectedTips:
    def test_409_recording_vendor_terms_not_accepted(self, capsys, monkeypatch):
        """user-settings / virtual-line-settings update-call-recording."""
        live = ('{"vendorId":"fecb634e-...","vendorName":"Dubber",'
                '"termsOfServiceUrl":"https://www.dubber.net/terms"}')
        run_full(live, status=409, argv=["wxcli", "user-settings", "update-call-recording"],
                 monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "terms of service" in err
        assert "Dubber" in err and "https://www.dubber.net/terms" in err
        assert "wxcli call-recording update-terms-of-service fecb634e-..." in err
        assert "wxcli cleanup run" not in err
        assert "Delete the dependents" not in err

    def test_409_same_type_job_already_running(self, capsys):
        """location-settings create-delete-calling-location, second job."""
        live = ('{"message":"Customer has job of same type already running.",'
                '"errors":[{"description":"Customer has job of same type already running.",'
                '"errorCode":"BATCH-1001004"}]}')
        run_full(live, status=409)
        err = capsys.readouterr().err
        assert "still running" in err
        assert "wxcli location-settings show-delete-calling-location" in err
        assert "wxcli cleanup run" not in err

    def test_409_job_running_keyed_on_the_code_alone(self, capsys):
        run_full('{"errors":[{"errorCode":"BATCH-1001004"}]}', status=409)
        err = capsys.readouterr().err
        assert "still running" in err and "wxcli cleanup run" not in err

    def test_409_still_referenced_keeps_the_cleanup_tip(self, capsys):
        """Control: the dependents tip is still right for a real reference."""
        run_full('{"message":"Location is being referenced, cannot be deleted",'
                 '"errors":[{"errorCode":50003}]}', status=409)
        assert "wxcli cleanup run" in capsys.readouterr().err

    def test_400_calling_flag_not_set_names_calling_data(self, capsys, monkeypatch):
        # Live: the message text is exact; the surrounding envelope is the
        # standard Webex error shape, reconstructed.
        run_full('{"message":"Calling flag not set","errors":[{"description":"Calling flag not set"}]}',
                 status=400, argv=["wxcli", "people", "list", "--location-id", "LOC"],
                 monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "--calling-data true" in err
        assert "not an admin" not in err
        assert "--generate-json-body" not in err

    def test_403_bifrost_b10005_is_an_entitlement_not_a_token(self, capsys, monkeypatch):
        # Live: a 403 whose body carried BIFROST-B10005; the envelope is reconstructed.
        live = ('{"message":"BIFROST-B10005: Forbidden","errors":'
                '[{"description":"BIFROST-B10005: Forbidden"}]}')
        run_full(live, status=403, argv=["wxcli", "ai-receptionist", "create"],
                 monkeypatch=monkeypatch)
        err = capsys.readouterr().err
        assert "entitle" in err
        assert "usually" in err
        assert "is not an admin of the target org" not in err

    def test_empty_body_is_never_a_bare_error(self, capsys):
        run_full("", status=400, headers={"Trackingid": "ROUTER_abc123"})
        err = capsys.readouterr().err
        first = err.splitlines()[0]
        assert first != "Error: "
        assert "HTTP 400 with an empty response body" in first
        assert "ROUTER_abc123" in err

    def test_empty_body_tracking_id_header_is_case_insensitive(self, capsys):
        run_full("  ", status=500, headers={"TrackingID": "WEBEX_x"})
        err = capsys.readouterr().err
        assert "HTTP 500 with an empty response body" in err and "WEBEX_x" in err

    def test_empty_body_without_headers(self, capsys):
        run_full("", status=400)
        err = capsys.readouterr().err
        assert "HTTP 400 with an empty response body" in err
        assert "trackingId" not in err
