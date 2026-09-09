"""Version rule (spec §6), ordered: first matching row wins. An earlier draft
classified rename/removal/repurpose as PATCH and a group decrease as MINOR;
adversarial review showed the pending regen — two silent repurposings and a
removal — would have shipped as routine. Every row is pinned here, and the
blast-radius cap (row 31) sits above 'green'.
"""
from pathlib import Path

from tools import sync_classify as sc

OLD = {"modules": {"meetings": {"create": ["POST /meetings"], "list": ["GET /meetings"]},
                   "cc_skill": {"create": ["POST /organization/{}/skill"]}}}


def _new(**mods):
    return {"modules": mods}


def test_retarget_is_human():
    v = sc.classify(OLD, _new(meetings={"create": ["POST /group/meetings/controls"], "list": ["GET /meetings"]},
                              cc_skill=OLD["modules"]["cc_skill"]), commands_changed=True)
    assert v["verdict"] == "human" and v["retargeted"] == ["meetings create"]


def test_removed_command_is_human():
    v = sc.classify(OLD, _new(meetings={"list": ["GET /meetings"]}, cc_skill=OLD["modules"]["cc_skill"]), True)
    assert v["verdict"] == "human" and v["removed"] == ["meetings create"]


def test_removed_module_is_human():
    v = sc.classify(OLD, _new(meetings=OLD["modules"]["meetings"]), True)
    assert v["verdict"] == "human" and v["modules_removed"] == ["cc_skill"]


def test_new_module_is_minor():
    v = sc.classify(OLD, _new(**OLD["modules"], cc_search_metadata={"list": ["GET /search/v2/meta"]}), True)
    assert v["verdict"] == "minor" and v["modules_added"] == ["cc_search_metadata"]


def test_new_command_in_existing_group_is_patch():
    v = sc.classify(OLD, _new(meetings={**OLD["modules"]["meetings"], "list-group": ["GET /group/meetings"]},
                              cc_skill=OLD["modules"]["cc_skill"]), True)
    assert v["verdict"] == "patch" and v["added"] == ["meetings list-group"]


def test_prose_only_regen_is_patch_and_no_regen_is_none():
    assert sc.classify(OLD, OLD, commands_changed=True)["verdict"] == "patch"
    assert sc.classify(OLD, OLD, commands_changed=False)["verdict"] == "none"


def test_blast_radius_overrides_green():
    big = {**OLD["modules"]["meetings"], **{f"cmd-{i}": [f"GET /x/{i}"] for i in range(sc.BLAST_RADIUS_MAX_COMMANDS + 1)}}
    v = sc.classify(OLD, _new(meetings=big, cc_skill=OLD["modules"]["cc_skill"]), True)
    assert v["verdict"] == "human" and any("blast radius" in r for r in v["reasons"])


def test_release_notes_carry_the_spec_delta_and_routing(tmp_path):
    (tmp_path / "spec-delta.txt").write_text("spec-snapshot refresh: 2 structural, 1 ID-kind flip(s), 5 prose delta(s)\n  STRUCTURAL   field_added  x\n")
    (tmp_path / "routing.md").write_text("- cc-search-metadata -> reporting-cc (metadata describes the search surface)\n")
    v = sc.classify(OLD, _new(**OLD["modules"], cc_search_metadata={"list": ["GET /search/v2/meta"]}), True)
    notes = sc.release_notes(v, tmp_path, "v1.7.0")
    assert "v1.7.0" in notes and "minor" in notes
    assert "cc_search_metadata" in notes and "reporting-cc" in notes
    assert "1 ID-kind flip" in notes and "STRUCTURAL" in notes
