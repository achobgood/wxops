"""Webex Calling org health assessment."""

from wxcli.org_health.checks import run_all_checks
from wxcli.org_health.analyze import run_analysis

__all__ = ["run_all_checks", "run_analysis"]
