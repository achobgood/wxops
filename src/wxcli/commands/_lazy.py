"""Lazy mounting for wxcli's command tree.

main.py's root Typer app used to import all 178 generated command-group
modules (plus 5 hand-written ones, 3 aliases, and up to 11 dev-only fs_*
ones) unconditionally at import time, then have Typer walk the whole tree
again to build a click command from it — twice the cost, paid on every
invocation including `wxcli --version`. This module makes that lazy:

- `LazyTyper` (the class `main.py`'s `app` is built from) defers building
  `registered_groups` until something actually reads it. Nothing in this
  file's own machinery reads it eagerly.
- `LazyTyper.__call__` (the real `wxcli` entry point) never reads
  `registered_groups` at all. It builds a small click Group from the root's
  own commands/callback (cheap — 5 hand-written commands) and merges in one
  `_LazyGroupProxy` per group, keyed by name, with a statically-parsed
  (import-free) description. A proxy resolves — imports its module, builds
  the real click command — only the first time something beyond its name/
  description is touched: real dispatch, or that group's own `--help`.
- Anything that reads `app.registered_groups` directly (typer.testing's
  `CliRunner`, or a bare `typer.main.get_command(app)` call — both used
  throughout the test suite) gets the ORIGINAL eager behavior via
  `mount_all()`: every module really imported, every group really
  add_typer'd, in the same order main.py used before lazy-loading. That
  path is unchanged in substance, just deferred from import time to first
  access, so it stays exactly as correct — and exactly as slow — as before.

`GENERATED_GROUPS` (`_registry.py`) is the single source of truth for the
178 generator-owned groups; `tools/drift_check.py`'s `parse_registrations()`
parses it directly and now also parses `HAND_WRITTEN_GROUPS` / `ALIASES` /
`FS_DEV_GROUPS` below the same way — flat tuple literals, no exec needed.
"""
from __future__ import annotations

import ast
import re
import sys
from importlib import import_module
from pathlib import Path

import click
import typer
from typer.main import TyperInfo, get_group_from_info

from wxcli.commands._registry import GENERATED_GROUPS

_COMMANDS_DIR = Path(__file__).parent

# Hand-written (non-generated) command-group modules, mounted the same way
# generated ones are: import the module, `add_typer(module.app, name=group)`.
HAND_WRITTEN_GROUPS = [
    ("update", "update"),
    ("configure", "configure"),
    ("cucm", "cucm"),
    ("cleanup", "cleanup"),
    ("org_health_cli", "org-health"),
]

# A second name for an already-registered group, sharing its Typer app —
# same object, same import, just a different top-level command name.
ALIASES = [
    ("customer-assist", "cx-essentials"),
    ("people", "users"),
    ("licenses", "licenses-api"),
]

# Dev-only Flow Store CLI — gitignored, generated from
# specs/webex-flow-store.json, absent from a fresh clone / the shipped wheel.
FS_DEV_GROUPS = [
    ("fs_flows", "fs-flows"),
    ("fs_resources", "fs-resources"),
    ("fs_templates", "fs-templates"),
    ("fs_tracing", "fs-tracing"),
    ("fs_flows_v2", "fs-flows-v2"),
    ("fs_user_prefs", "fs-user-prefs"),
    ("fs_connectors", "fs-connectors"),
    ("fs_expression_test", "fs-expression-test"),
    ("fs_flow_props", "fs-flow-props"),
    ("fs_flow_versions", "fs-flow-versions"),
    ("fs_projects", "fs-projects"),
]

_GROUP_TO_MODULE = {grp: mod for mod, grp in [*HAND_WRITTEN_GROUPS, *GENERATED_GROUPS]}


_HELP_LITERAL_RE = re.compile(r'help\s*=\s*(".*?"|\'.*?\')')


def _extract_short_help(module_stem: str) -> str:
    """Cheap, import-free description for a command module's Typer app.

    Every one of the 178 generated modules (and the 5 hand-written ones)
    declares `app = typer.Typer(..., help="...")` near the top of the file,
    before any command definitions — so the first `help="..."` in a bounded
    head read is always that one, never a per-option `help=` further down.
    Reading a bounded prefix and regexing it, rather than `ast.parse`-ing
    the whole file, is what makes this cheap: some generated files are
    100+ KB (`call_queue.py` is 126 KB, 27 commands each with several
    options), and full-file `ast.parse` across all 178 measured at ~440ms —
    most of a `wxcli --help` invocation, for one string near the top of
    each file. A module that doesn't match this shape, or can't be read,
    degrades to an empty description rather than raising.
    """
    path = _COMMANDS_DIR / f"{module_stem}.py"
    try:
        with path.open(encoding="utf-8") as f:
            head = f.read(8192)  # comfortably past the deepest observed offset (~2.7 KB)
    except OSError:
        return ""
    match = _HELP_LITERAL_RE.search(head)
    if not match:
        return ""
    try:
        return ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError):
        return ""


def _ensure_converged_recordings_registered(sub_app: typer.Typer) -> None:
    """`converged_recordings_export.register()` adds hand-written download/
    export commands onto the generated converged-recordings app. Guarded so
    a process that resolves this group through both the lazy proxy path and
    the eager `mount_all` fallback (e.g. a test that does both) can't
    register the same two commands onto the same cached module twice.
    """
    if any(c.name == "download" for c in sub_app.registered_commands):
        return
    from wxcli.commands import converged_recordings_export
    converged_recordings_export.register(sub_app)


class _LazyGroupProxy:
    """Stands in for a not-yet-imported group's click command.

    `.name` / `.help` / `.hidden` / `.deprecated` / `.rich_help_panel` are
    set directly at construction (no import), and `get_short_help_str()` is
    computed from those same attributes — so BOTH help renderers Typer can
    pick (rich, in an interactive terminal; plain click, whenever
    `plain_mode()` is True — piped output, CI, most of what an agent sees)
    can list and describe every group without triggering a resolve. That
    plain-mode path is easy to miss: it calls `cmd.get_short_help_str()`, a
    *method*, not an attribute `__getattr__` could shortcut — without this
    override every `wxcli --help` under a pipe silently resolved (imported)
    all 192 groups just to render the list, which is the exact cost this
    whole module exists to avoid. `.short_help` itself is left unset
    (`None`), matching the real click commands Typer builds for these
    groups — `add_typer()` is never called with an explicit `short_help=`
    here, so the description always lives in `.help`, and click's own
    `get_short_help_str` truncates *from* `.help` only when `.short_help`
    is unset; setting both would have skipped that truncation.
    Anything truly unresolved (real dispatch, or that group's own
    `--help`) falls through `__getattr__`, which resolves the real click
    command on first touch, caches it, and delegates from then on.
    """

    def __init__(self, name: str, short_help: str, loader):
        self.name = name
        self.short_help = None
        self.help = short_help or None
        self.hidden = False
        self.deprecated = False
        self.rich_help_panel = None
        self._loader = loader
        self._resolved = None

    def _resolve(self):
        if self._resolved is None:
            self._resolved = self._loader()
        return self._resolved

    def get_short_help_str(self, limit: int = 45) -> str:
        # Mirrors click.Command.get_short_help_str's `.help`-truncation
        # branch (the only one reachable — see class docstring).
        from click.utils import make_default_short_help
        return make_default_short_help(self.help, limit) if self.help else ""

    def __getattr__(self, item):
        return getattr(self._resolve(), item)


def _to_click_group(sub_app: typer.Typer, name: str, root: typer.Typer) -> click.Command:
    """Convert an already-imported sub-Typer into a click command, exactly
    as `add_typer(sub_app, name=name)` + Typer's own tree-walk would — same
    call, same kwargs, just invoked directly on one group instead of during
    a walk of all of them. `pretty_exceptions_short` / `rich_markup_mode` /
    `suggest_commands` come from the ROOT app, not `sub_app`: Typer threads
    those three down from the top of the walk rather than re-reading them
    per group, so matching that — not `sub_app`'s own declared values — is
    what keeps output identical.
    """
    return get_group_from_info(
        TyperInfo(sub_app, name=name),
        pretty_exceptions_short=root.pretty_exceptions_short,
        rich_markup_mode=root.rich_markup_mode,
        suggest_commands=root.suggest_commands,
    )


def _group_loader(module_stem: str, group_name: str, root: typer.Typer):
    def _load():
        sub_app = import_module(f"wxcli.commands.{module_stem}").app
        if group_name == "converged-recordings":
            _ensure_converged_recordings_registered(sub_app)
        return _to_click_group(sub_app, group_name, root)
    return _load


def _alias_loader(base_group: str, commands: dict):
    def _load():
        return commands[base_group]._resolve()
    return _load


def build_lazy_commands(root: typer.Typer) -> dict[str, object]:
    """The full lazy `{name: command-or-proxy}` map for every group this CLI
    registers beyond the root's own hand-written commands: proxies for the
    178 generated + 5 hand-written groups, plus the 3 aliases, plus (if
    present — dev-only, gitignored) the fs_* Flow Store groups.
    """
    commands: dict[str, object] = {}
    for module, group in [*HAND_WRITTEN_GROUPS, *GENERATED_GROUPS]:
        commands[group] = _LazyGroupProxy(
            group, _extract_short_help(module), _group_loader(module, group, root)
        )
    for base, alias in ALIASES:
        commands[alias] = _LazyGroupProxy(
            alias, _extract_short_help(_GROUP_TO_MODULE[base]), _alias_loader(base, commands)
        )
    for module, group in FS_DEV_GROUPS:
        if not (_COMMANDS_DIR / f"{module}.py").exists():
            continue  # dev-only, gitignored — absent on a fresh clone/wheel
        commands[group] = _LazyGroupProxy(
            group, _extract_short_help(module), _group_loader(module, group, root)
        )
    return commands


def mount_all(root: typer.Typer) -> None:
    """Original, fully-eager mount: import every module, `add_typer` every
    group, in the same order main.py used before lazy-loading. This is the
    fallback used the moment anything reads `root.registered_groups`
    directly — `typer.testing.CliRunner`, or a bare `typer.main.get_command
    (app)` call — so those paths see EXACTLY what they saw before, just
    populated on first read instead of at import time.
    """
    generated_apps = {}
    for module, group in HAND_WRITTEN_GROUPS:
        root.add_typer(import_module(f"wxcli.commands.{module}").app, name=group)
    for module, group in GENERATED_GROUPS:
        sub_app = import_module(f"wxcli.commands.{module}").app
        generated_apps[group] = sub_app
        root.add_typer(sub_app, name=group)

    _ensure_converged_recordings_registered(generated_apps["converged-recordings"])

    for base, alias in ALIASES:
        root.add_typer(generated_apps[base], name=alias)

    try:
        for module, group in FS_DEV_GROUPS:
            root.add_typer(import_module(f"wxcli.commands.{module}").app, name=group)
    except ImportError:
        pass


class LazyTyper(typer.Typer):
    """Root app class. `registered_groups` mounts everything (real imports,
    real add_typer calls) the first time anything reads it — but `__call__`
    (the real `wxcli` entry point) never reads it; it builds a small click
    Group from the root's own commands/callback and merges in lazy proxies
    for every group instead. See the module docstring for the full split.
    """

    def __init__(self, *args, **kwargs):
        self.__dict__["_groups_mounted"] = False
        self.__dict__["_registered_groups_store"] = []
        super().__init__(*args, **kwargs)

    @property
    def registered_groups(self):
        if not self._groups_mounted:
            self._groups_mounted = True
            mount_all(self)
        return self._registered_groups_store

    @registered_groups.setter
    def registered_groups(self, value):
        self._registered_groups_store = value

    def __call__(self, *args, **kwargs):
        try:
            from typer.main import (
                DeveloperExceptionConfig,
                _typer_developer_exception_attr_name,
                except_hook,
            )
            if sys.excepthook != except_hook:
                sys.excepthook = except_hook
        except ImportError:  # pragma: no cover — typer internals moved
            DeveloperExceptionConfig = None

        try:
            return self._fast_command()(*args, **kwargs)
        except Exception as e:
            if DeveloperExceptionConfig is not None:
                setattr(
                    e,
                    _typer_developer_exception_attr_name,
                    DeveloperExceptionConfig(
                        pretty_exceptions_enable=self.pretty_exceptions_enable,
                        pretty_exceptions_show_locals=self.pretty_exceptions_show_locals,
                        pretty_exceptions_short=self.pretty_exceptions_short,
                    ),
                )
            raise e

    def _fast_command(self) -> click.Command:
        """Build the real entry-point command without ever touching
        `registered_groups` (which would trigger `mount_all`): fake the
        "already mounted" flag for the one call that would read it, so
        Typer's own tree-walk sees it as empty, then merge in the lazy
        proxies afterward by mutating the resulting click Group's plain
        `.commands` dict.
        """
        from typer.main import get_command

        saved = self._groups_mounted
        self._groups_mounted = True  # registered_groups reads as [] below
        try:
            cmd = get_command(self)
        finally:
            self._groups_mounted = saved
        cmd.commands.update(build_lazy_commands(self))
        return cmd
