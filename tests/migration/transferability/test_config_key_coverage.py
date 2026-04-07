"""Verify every key in DEFAULT_CONFIG has an entry in
docs/runbooks/cucm-migration/tuning-reference.md §config.json."""

from __future__ import annotations

from wxcli.commands.cucm_config import DEFAULT_CONFIG
from .conftest import extract_anchors, slugify


def test_every_config_key_has_an_anchor(tuning_reference_path):
    expected = {slugify(k.replace("_", " ")) for k in DEFAULT_CONFIG.keys()}
    actual = extract_anchors(tuning_reference_path)
    missing = expected - actual
    assert not missing, (
        f"tuning-reference.md is missing anchors for config keys: {sorted(missing)}. "
        f"Add a `### <slug>` heading for each."
    )
