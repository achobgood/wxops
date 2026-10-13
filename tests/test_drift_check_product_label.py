"""Drift gate check 28: a command group whose help names the wrong product.

The group-help label (`typer.Typer(help="…")`) used to be guessed from the
CLI-name prefix — `cc-` -> Contact Center, everything else -> Calling — so
`asset` and `channel` (Contact Center host) said "Manage Webex Calling
asset.", and every admin, device and messaging group (`rooms`, `devices`, …)
announced itself as Webex Calling (findings D07/D08). The label now reads
"Manage Webex <Product>: <group>." from SPEC_PRODUCT for the spec(s) that
render the group.

Rule: per module, the products are SPEC_PRODUCT of every spec that declares
an operation one of the module's command blocks calls. The module fires when
its label is not exactly "Manage Webex <p>: <group>." for some p among them.
A module spanning two specs accepts either product (Review Focus 5). A module
with no matching spec operation (hand-written, alias seam) is skipped and
counted, as is one whose operations live only in a spec SPEC_PRODUCT does not
know, or whose label cannot be read.

Every fire case has a paired no-fire case, written so the check can fail it.
"""

import json

import pytest

from tools import drift_check


BLOCK = '''
@app.command("CMD")
def cmd(
    output: str = typer.Option("json", "--output", "-o"),
):
    """Show a thing."""
    url = f"URL"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    emit(result, output)
'''

HEADER = 'import typer\n\napp = typer.Typer(help="LABEL")\n'

CC_URL = "{cc_base_url}/organization/{org_id}/asset/{id}"
CC_PATH = "/organization/{orgid}/asset/{id}"
CALLING_URL = "https://webexapis.com/v1/zz/things/{id}"
CALLING_PATH = "/zz/things/{id}"


def _module(label, *blocks):
    head = HEADER.replace("LABEL", label) if label is not None else (
        "import typer\n\napp = typer.Typer()\n")
    return head + "".join(blocks)


def _block(url, cmd="show"):
    return BLOCK.replace("CMD", cmd).replace("URL", url)


def _spec(path, method="get"):
    return {"paths": {path: {method: {
        "tags": ["Probe"], "responses": {"200": {"description": "ok"}}}}}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, specs_by_name, module="asset.py", registry=None):
        (cmds / module).write_text(module_src)
        for name, spec in specs_by_name.items():
            (specs / name).write_text(json.dumps(spec))
        if registry is not None:
            (cmds / "_registry.py").write_text(
                "GENERATED_GROUPS = [\n"
                + "".join(f'    ("{m}", "{g}"),\n' for m, g in registry)
                + "]\n")
        return drift_check.check_wrong_product_label(
            commands_dir=cmds, specs_dir=specs)

    return run


CC = "webex-contact-center.json"
CALLING = "webex-cloud-calling.json"
ADMIN = "webex-admin.json"
MESSAGING = "webex-messaging.json"
MEETINGS = "webex-meetings.json"


# ------------------------------------------------- the D07/D08 bug, pre-fix

def test_cc_module_labelled_calling_fires(tree):
    """`asset` before the fix: the CC host, labelled Calling, old format."""
    findings = tree(_module("Manage Webex Calling asset.", _block(CC_URL)),
                    {CC: _spec(CC_PATH)})
    assert findings == [{"group": "asset",
                         "label": "Manage Webex Calling asset.",
                         "expected": ["Contact Center"]}]


def test_correct_label_passes(tree):
    assert tree(_module("Manage Webex Contact Center: asset.", _block(CC_URL)),
                {CC: _spec(CC_PATH)}) == []
    assert drift_check.CHECK_EXAMINED["28"] == {"examined": 1, "skipped": 0}


def test_wrong_product_in_new_format_fires(tree):
    """Not only the old format: a well-formed label naming another product."""
    findings = tree(_module("Manage Webex Calling: asset.", _block(CC_URL)),
                    {CC: _spec(CC_PATH)})
    assert [f["expected"] for f in findings] == [["Contact Center"]]


def test_right_product_old_format_fires(tree):
    """The label is the generator's exact output or it has drifted; the
    pre-fix colon-less form fails even when it names the right product."""
    findings = tree(_module("Manage Webex Contact Center asset.",
                            _block(CC_URL)), {CC: _spec(CC_PATH)})
    assert len(findings) == 1


def test_label_naming_another_group_fires(tree):
    findings = tree(_module("Manage Webex Contact Center: channel.",
                            _block(CC_URL)), {CC: _spec(CC_PATH)})
    assert len(findings) == 1


# ------------------------------------------------ Review Focus 5: two specs

def test_module_spanning_two_specs_accepts_either(tree):
    """`webhooks` is rendered by both the Messaging and the Meetings spec
    (same paths). Check 28 accepts either product; the generator picks one
    deterministically (command_renderer.group_label_spec)."""
    url = "https://webexapis.com/v1/webhooks/{id}"
    path = "/webhooks/{webhookId}"
    specs = {MESSAGING: _spec(path), MEETINGS: _spec(path)}
    for product in ("Messaging", "Meetings"):
        assert tree(_module(f"Manage Webex {product}: webhooks.", _block(url)),
                    specs, module="webhooks.py") == [], product
    findings = tree(_module("Manage Webex Calling: webhooks.", _block(url)),
                    specs, module="webhooks.py")
    assert findings == [{"group": "webhooks",
                         "label": "Manage Webex Calling: webhooks.",
                         "expected": ["Meetings", "Messaging"]}]


def test_products_union_across_blocks(tree):
    """Two blocks, each declared by a different spec: either product passes."""
    src = _module("Manage Webex Admin: asset.",
                  _block(CC_URL), _block(CALLING_URL, cmd="show-thing"))
    assert tree(src, {CC: _spec(CC_PATH), ADMIN: _spec(CALLING_PATH)}) == []


# ------------------------------------------------------- skipped, not fired

def test_module_without_spec_ops_skipped(tree):
    """A hand-written seam / alias module whose blocks match no spec op."""
    src = _module("Manage Webex Calling asset.", _block(CALLING_URL))
    findings = tree(src, {CC: _spec(CC_PATH)})
    # Only the BLIND marker (nothing else was examined) — never a label finding.
    assert [f.get("check") for f in findings] == ["28"]
    assert drift_check.CHECK_EXAMINED["28"] == {"examined": 0, "skipped": 1}


def test_module_without_spec_ops_is_not_examined(tree):
    """Paired with the fire case: the same wrong label, but no spec op —
    the only other module is judged, so the run is not BLIND."""
    tree(_module("Manage Webex Contact Center: channel.",
                 _block("{cc_base_url}/organization/{org_id}/channel/{id}")),
         {CC: _spec("/organization/{orgid}/channel/{id}")},
         module="channel.py")
    findings = tree(_module("Manage Webex Calling asset.",
                            _block(CALLING_URL)), {})
    assert findings == []
    assert drift_check.CHECK_EXAMINED["28"] == {"examined": 1, "skipped": 1}


def test_unknown_spec_is_skipped_and_counted_never_raises(tree):
    """A new upstream spec with no SPEC_PRODUCT entry: skipped, counted."""
    src = _module("Manage Webex Calling asset.", _block(CC_URL))
    findings = tree(src, {"webex-newproduct.json": _spec(CC_PATH)})
    assert [f.get("check") for f in findings] == ["28"]     # BLIND: 0 examined
    assert drift_check.CHECK_EXAMINED["28"] == {"examined": 0, "skipped": 1}


def test_unknown_spec_beside_a_known_one_judges_the_known(tree):
    src = _module("Manage Webex Calling asset.", _block(CC_URL))
    findings = tree(src, {"webex-newproduct.json": _spec(CC_PATH),
                          CC: _spec(CC_PATH)})
    assert [f["expected"] for f in findings] == [["Contact Center"]]


def test_module_without_label_skipped(tree):
    """No readable label: never guessed."""
    both = _spec(CC_PATH)
    both["paths"].update(_spec("/organization/{orgid}/channel/{id}")["paths"])
    tree(_module("Manage Webex Contact Center: channel.",
                 _block("{cc_base_url}/organization/{org_id}/channel/{id}")),
         {CC: both}, module="channel.py")
    findings = tree(_module(None, _block(CC_URL)), {CC: both})
    assert findings == []
    assert drift_check.CHECK_EXAMINED["28"] == {"examined": 1, "skipped": 1}


def test_no_spec_ops_anywhere_is_blind(tree):
    findings = tree(_module("Manage Webex Calling asset.", _block(CC_URL)), {})
    assert [f.get("check") for f in findings] == ["28"]


# ------------------------------------------------ registered name vs module

def test_registered_name_is_accepted_and_reported(tree):
    """The label carries the CLI name; if the registry ever registers a module
    under a name other than module-with-dashes, that name is what the label
    holds and what the finding reports."""
    src = _module("Manage Webex Contact Center: cc-asset.", _block(CC_URL))
    assert tree(src, {CC: _spec(CC_PATH)},
                registry=[("asset", "cc-asset")]) == []
    findings = tree(_module("Manage Webex Calling: cc-asset.", _block(CC_URL)),
                    {CC: _spec(CC_PATH)}, registry=[("asset", "cc-asset")])
    assert [f["group"] for f in findings] == ["cc-asset"]


# ------------------------------------------------------------------- safety

def test_odd_input_never_raises(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()
    (cmds / "asset.py").write_text(_module('Manage "odd', _block(CC_URL)))
    (cmds / "_registry.py").write_text("GENERATED_GROUPS = [ (((")
    (cmds / "broken.py").write_bytes(b"\xff\xfe\x00bad")
    (specs / CC).write_text(json.dumps({"paths": {
        CC_PATH: {"get": ["not", "a", "dict"]}, "/x": "nope"}}))
    (specs / ADMIN).write_text("not json")
    findings = drift_check.check_wrong_product_label(
        commands_dir=cmds, specs_dir=specs)
    assert all(isinstance(f, dict) for f in findings)
    missing = drift_check.check_wrong_product_label(
        commands_dir=tmp_path / "nope", specs_dir=tmp_path / "nope")
    assert [f.get("check") for f in missing] == ["28"]


def test_live_tree_is_clean():
    assert drift_check.check_wrong_product_label() == []
    # A floor that catches blindness only (~175 today); zero is BLIND anyway.
    # A tight floor would fail the weekly job when upstream retires groups.
    assert drift_check.CHECK_EXAMINED["28"]["examined"] >= 20


def test_check_28_line_format(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "28",
                        {"examined": 175, "skipped": 9})
    f = {"group": "asset", "label": "Manage Webex Calling asset.",
         "expected": ["Contact Center"]}
    drift_check.print_check_findings("28", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[28] command groups whose help names the wrong product: 1   "
        "(examined 175 command groups, skipped 9)",
        '      wxcli asset  help "Manage Webex Calling asset."  '
        "expected product: Contact Center",
    ]


def test_main_wires_check_28():
    """Gated, under its results key, and printed through CHECK_PRINT."""
    import inspect
    src = inspect.getsource(drift_check.main)
    assert '"28_wrong_product_label": wrong_product_labels' in src
    assert "or wrong_product_labels" in src
    assert 'print_check_findings("28", wrong_product_labels)' in src
    assert "28" in drift_check.CHECK_PRINT
