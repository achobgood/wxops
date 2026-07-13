"""Best-effort PyPI update check for the wxcli CLI.

Runs once per invocation from the top-level Typer callback, and from the
`wxcli update --hook` session-start path. It must NEVER block or break a real
command, so every path here is defensive:

* a short (1s) network timeout,
* a 24h on-disk cache next to the config (``~/.wxcli/update-check.json``),
* every exception (no network, PyPI outage, bad JSON, unwritable cache)
  swallowed — a failure prints nothing and returns ``None``.

The notice is printed to stderr so it never corrupts JSON output on stdout. It
is silenced by ``--no-update-check``, by ``WXCLI_NO_UPDATE_CHECK``, under ``CI``
(so pipelines/tests stay hermetic), and on editable/source installs (developers
update with git).
"""
import json
import os
import sys
import time
from pathlib import Path

import httpx
from packaging.version import InvalidVersion, Version

from wxcli.commands.update import detect_install_method

PACKAGE = "wxcli"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE}/json"
CACHE_PATH = Path.home() / ".wxcli" / "update-check.json"
CACHE_TTL_SECONDS = 24 * 60 * 60  # re-check PyPI at most once a day
REQUEST_TIMEOUT_SECONDS = 1.0
ENV_DISABLE = "WXCLI_NO_UPDATE_CHECK"


def _is_newer(latest, current):
    """True iff ``latest`` is a strictly newer *stable* release than ``current``.

    Uses packaging.Version (already a runtime dep). Unparseable/empty latest ->
    not newer; a prerelease latest never nags; unparseable current -> treat as behind.
    """
    try:
        lat = Version(latest)
    except (InvalidVersion, TypeError):
        return False
    if lat.is_prerelease:
        return False
    try:
        cur = Version(current)
    except (InvalidVersion, TypeError):
        return True
    return lat > cur


def _env_truthy(name):
    val = os.environ.get(name, "").strip().lower()
    return bool(val) and val not in ("0", "false", "no", "off")


def _read_cache(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(path, latest, now):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"pkg": PACKAGE, "latest": latest, "last_check": now}, f)
    except Exception:
        pass


def _fetch_latest(timeout):
    resp = httpx.get(PYPI_JSON_URL, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["info"]["version"]


def check_for_update(current_version, *, now=None, cache_path=CACHE_PATH,
                     ttl=CACHE_TTL_SECONDS, timeout=REQUEST_TIMEOUT_SECONDS,
                     force=False):
    """Return the latest PyPI version string if newer than ``current_version``.

    Returns ``None`` when already up to date OR on any failure. Only hits PyPI
    when the cache is missing/stale or ``force=True``; a fresh cache answers offline.
    """
    try:
        if now is None:
            now = time.time()
        cache = _read_cache(cache_path)
        cache_fresh = (
            not force and cache
            and isinstance(cache.get("last_check"), (int, float))
            and now - cache["last_check"] < ttl
        )
        if cache_fresh:
            latest = cache.get("latest")
        else:
            try:
                latest = _fetch_latest(timeout)
            except Exception:
                # Negative-cache the failure so an offline / firewalled machine
                # doesn't re-hit PyPI (and eat the timeout) on every command.
                # Preserve the last known-good latest so a previously-seen
                # update still notifies.
                latest = cache.get("latest") if cache else None
            _write_cache(cache_path, latest, now)
        if latest and _is_newer(latest, current_version):
            return latest
        return None
    except Exception:
        return None


def maybe_notify_update(current_version, *, disabled=False, stream=None,
                        install_method=None, **kwargs):
    """Print a one-line upgrade notice to stderr if a newer release exists.

    Silent when disabled (flag, ``WXCLI_NO_UPDATE_CHECK``, or ``CI``), on
    editable/source installs, and on any failure. Returns the latest version if
    a notice was printed, else ``None``. Extra kwargs pass to check_for_update.
    """
    if disabled or _env_truthy(ENV_DISABLE) or _env_truthy("CI"):
        return None
    if install_method is None:
        try:
            install_method = detect_install_method()
        except Exception:
            install_method = "pip"
    if install_method == "editable":
        return None
    latest = check_for_update(current_version, **kwargs)
    if not latest:
        return None
    try:
        (stream or sys.stderr).write(
            f"wxcli {latest} available (you have {current_version}) — run: wxcli update\n"
        )
    except Exception:
        return None
    return latest
