"""Offer the user a Claude Code auto-mode rule naming the Webex org wxcli targets.

Claude Code's auto mode reads `autoMode` only from the user's
~/.claude/settings.json, managed settings or `--settings`, never from a
project's .claude/ folder, and it refuses Claude's own edit of it as
self-modification. So the one place this rule can come from is a step the user
runs in their own terminal: the end of `wxcli configure` (and `switch-org`).

Every entry wxcli writes starts with MARK, so wxcli recognises and replaces its
own entries and never touches anyone else's. `"$defaults"` heads any list wxcli
creates, which keeps Claude Code's built-in rules.

This guards against accidents. It is not a security boundary: anything that can
type into a real terminal can answer the prompt. The gate hook refusing
`wxcli configure` for every agent, and the CLAUDE.md statement, close the
ordinary paths. Decision record: tools/CLAUDE.md § Decision Record — CLI Surface.
"""
from __future__ import annotations

import copy
import json
import os
import re
import stat
import string
import sys
import tempfile
from pathlib import Path

MARK = "[wxcli]"
DISABLE_ENV = "WXCLI_NO_AUTOMODE_OFFER"
# Any of these means the process runs under an AI agent (CLAUDECODE and
# CLAUDE_CODE_ENTRYPOINT are set in every Claude Code shell, `!` commands
# included). Presence is enough: an agent must never write this file.
AGENT_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "AI_AGENT")
NAME_MAX = 60
KEYS = ("environment", "allow")
# Final review I1 (Adam, 2026-11-11): Claude may still switch or clear the
# target org, but Claude Code must ask the user each time. The classifier
# never sees wxcli's target org (it lives in wxcli's config, not the command
# text), so an ask rule does it: "Content-scoped ask rules ... are evaluated
# before the classifier and always force a permission prompt, even in auto
# mode" (code.claude.com/docs/en/auto-mode-config § Add a human checkpoint).
# A trailing ` *` also matches the bare command, so one rule covers both
# `wxcli clear-org` and `wxcli switch-org <id>` (docs/en/permissions §
# Wildcard patterns). wxcli owns exactly these strings in permissions.ask:
# written with the allow rule, removed with the last [wxcli] allow rule.
ASK_RULES = ("Bash(wxcli switch-org *)", "Bash(wxcli clear-org *)")

# The org id lands in the rule unquoted, so it must look like an id: Webex ids
# are base64 (A-Z a-z 0-9 + / =), Contact Center ids are UUIDs.
_ORG_ID = re.compile(r"^[A-Za-z0-9+/=_-]{1,200}$")
_NAME_CHARS = frozenset(string.ascii_letters + string.digits + " -_")
_NAMED = re.compile(r'Webex org "([^"]*)" \(([^)]*)\)')


def safe_org_name(name: str | None) -> str | None:
    """ASCII letters, digits, spaces, `-` and `_` only; whitespace collapsed; at
    most 60 characters; None if nothing is left (the org id is shown instead).

    A partner's customer names its own org, so the display name is someone
    else's text. No `.`, `:` or quote survives, so it cannot end the rule's
    sentence or its quotes and add prose of its own (recheck N3). ASCII-only,
    because `str.isalnum()` accepts Unicode look-alikes of those characters
    (U+02BA `ʺ`, U+02D0 `ː`, U+A4F8 `ꓸ`, U+1427 `ᐧ`; Task 6 review I1):
    an allow-list closes the whole class, a deny-list would chase code points.
    """
    if not name:
        return None
    kept = "".join(
        c if c in _NAME_CHARS else " " if c.isspace() else ""
        for c in name
    )
    collapsed = " ".join(kept.split())[:NAME_MAX].strip()
    return collapsed or None


def _display(org_name: str | None, org_id: str) -> str:
    return safe_org_name(org_name) or org_id


def automode_rules(org_name: str | None, org_id: str) -> dict[str, list[str]]:
    """The two entries, `{"environment": [ENV], "allow": [ALLOW]}`."""
    name = _display(org_name, org_id)
    env = (
        f'{MARK} Webex org "{name}" ({org_id}): the Webex organization this user '
        "administers with the wxcli CLI. Configuring it is the purpose of the "
        "Webex Ops project."
    )
    allow = (
        f"{MARK} Creating, changing and deleting resources in the Webex org "
        f'"{name}" ({org_id}) with wxcli, run directly or through the wxops '
        "subagent, is allowed: the user set up wxcli to administer this org and "
        "approved this rule when they ran wxcli configure. This does not cover "
        "changing which org wxcli targets (switch-org, configure, clear-org, or "
        "--org-id naming another org)."
    )
    return {"environment": [env], "allow": [allow]}


def _validate(settings, keys) -> None:
    """ValueError unless settings, `autoMode` and each named list have the
    shapes Claude Code reads. Runs before anything is changed."""
    if not isinstance(settings, dict):
        raise ValueError("the top level is not a JSON object")
    perms = settings.get("permissions")
    if perms is not None:
        if not isinstance(perms, dict):
            raise ValueError('"permissions" is not a JSON object')
        ask = perms.get("ask")
        if ask is not None and (not isinstance(ask, list)
                                or not all(isinstance(e, str) for e in ask)):
            raise ValueError('"permissions.ask" is not a list of strings')
    mode = settings.get("autoMode")
    if mode is None:
        return
    if not isinstance(mode, dict):
        raise ValueError('"autoMode" is not a JSON object')
    for key in keys:
        entries = mode.get(key)
        if entries is None:
            continue
        if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
            raise ValueError(f'"autoMode.{key}" is not a list of strings')


def _ours(entry: str) -> bool:
    return entry.startswith(MARK)


def merge_automode(settings: dict, rules: dict[str, list[str]]) -> bool:
    """Put `rules` into `settings["autoMode"]`, replacing any earlier MARK
    entries and keeping everyone else's. Returns whether anything changed."""
    _validate(settings, rules.keys())
    before = copy.deepcopy(settings.get("autoMode"))
    mode = settings.setdefault("autoMode", {})
    for key, new in rules.items():
        entries = mode.get(key)
        if entries is None:
            mode[key] = ["$defaults", *new]
        else:
            mode[key] = [e for e in entries if not _ours(e)] + list(new)
    changed = settings.get("autoMode") != before
    if "allow" in rules:
        changed = _add_ask(settings) or changed
    return changed


def _missing_ask(settings: dict) -> list[str]:
    perms = settings.get("permissions")
    ask = perms.get("ask") if isinstance(perms, dict) else None
    have = ask if isinstance(ask, list) else []
    return [r for r in ASK_RULES if r not in have]


def _add_ask(settings: dict) -> bool:
    """Append the ASK_RULES not already present. Touches nothing else."""
    missing = _missing_ask(settings)
    if missing:
        settings.setdefault("permissions", {}).setdefault("ask", []).extend(missing)
    return bool(missing)


def _drop_ask(settings: dict) -> bool:
    """Remove exactly the ASK_RULES strings; drop the list, then the object,
    only if that removal left them empty."""
    perms = settings.get("permissions")
    if not isinstance(perms, dict) or not isinstance(perms.get("ask"), list):
        return False
    kept = [e for e in perms["ask"] if e not in ASK_RULES]
    if kept == perms["ask"]:
        return False
    if kept:
        perms["ask"] = kept
    else:
        del perms["ask"]
        if not perms:
            del settings["permissions"]
    return True


def remove_automode(settings: dict) -> bool:
    """Drop every MARK entry, and with the last MARK allow entry the
    ASK_RULES. Creates nothing. Returns whether anything changed."""
    _validate(settings, KEYS)
    mode = settings.get("autoMode")
    if not isinstance(mode, dict):
        return False
    changed = False
    for key in KEYS:
        entries = mode.get(key)
        if entries is None:
            continue
        kept = [e for e in entries if not _ours(e)]
        if kept != entries:
            mode[key] = kept
            changed = True
            if key == "allow":
                _drop_ask(settings)
    return changed


def _marked(settings: dict) -> list[str]:
    mode = settings.get("autoMode") if isinstance(settings, dict) else None
    if not isinstance(mode, dict):
        return []
    return [e for key in KEYS for e in (mode.get(key) or [])
            if isinstance(e, str) and _ours(e)]


def _has_rule_for(settings: dict, org_id: str) -> bool:
    return any(f"({org_id})" in e for e in _marked(settings))


def _is_already(settings: dict, rules: dict[str, list[str]]) -> bool:
    mode = settings.get("autoMode")
    if not isinstance(mode, dict):
        return False
    return (not _missing_ask(settings)
            and all([e for e in (mode.get(key) or []) if _ours(e)] == new
                    for key, new in rules.items()))


def _rule_org_names(settings: dict, skip_id: str | None = None) -> list[str]:
    """The org names wxcli's existing entries carry, except those naming
    `skip_id`. Without it, this org's are included: answering n removes them
    all (final review T6.5)."""
    names: list[str] = []
    for entry in _marked(settings):
        match = _NAMED.search(entry)
        if match:
            if skip_id and match.group(2) == skip_id:
                continue
            name = match.group(1)
            if name not in names:
                names.append(name)
        elif not match and "another org" not in names:
            names.append("another org")
    return names


def default_settings_path() -> Path:
    """~/.claude/settings.json: the only user-level file auto mode reads."""
    return Path.home() / ".claude" / "settings.json"


def _in_agent() -> bool:
    return any(name in os.environ for name in AGENT_ENV)


def _disabled() -> bool:
    val = os.environ.get(DISABLE_ENV, "").strip().lower()
    return bool(val) and val not in ("0", "false", "no", "off")


def _interactive() -> bool:
    # Read at call time, never bound at import: tests and pipes swap them.
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


def _say(text: str = "") -> None:
    print(text, file=sys.stderr, flush=True)


def _read(path: Path) -> tuple[dict, bytes | None]:
    """(settings, original bytes). A missing file is `{}`, None. Raises
    ValueError on invalid JSON or a wrong shape, OSError if unreadable."""
    if not path.exists():
        return {}, None
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"it is not valid JSON ({exc})") from exc
    _validate(data, KEYS)
    return data, raw


def _write(path: Path, settings: dict, original: bytes | None) -> None:
    """Temp file in the same directory, then os.replace. Keeps the file mode;
    on the first change keeps one backup beside the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if original is not None else 0o644
    if original is not None:
        backup = path.with_name(path.name + ".wxcli-backup")
        if not backup.exists():
            backup.write_bytes(original)
            os.chmod(backup, mode)
    text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def ask_yes_no(question: str) -> bool:
    """Ask on stderr until the user types y or n. There is no default, because
    deletes are in scope. End of input raises EOFError."""
    while True:
        print(f"{question} ", end="", file=sys.stderr, flush=True)
        line = sys.stdin.readline()
        if line == "":
            raise EOFError
        answer = line.strip().lower()
        if answer in ("y", "n"):
            return answer == "y"
        _say("Please type y or n.")


def _say_stale(names: list[str], target: str) -> None:
    _say(f"Claude Code's auto-mode rule still names {', '.join(names)}; wxcli now "
         f'targets {target}. Run "wxcli configure" in your own terminal to update it.')


def _not_changed(path: Path, why) -> str:
    _say(f"Not changing {path}: {why}. Claude Code auto mode was left as it was.")
    return "invalid"


def offer_automode(org_name: str | None, org_id: str | None, *,
                   token_org_id: str | None = None,
                   settings_path: Path | None = None,
                   confirm=None,
                   confirmed: bool = True) -> str:
    """Offer to write the auto-mode rule for `org_id`. Never raises for a
    settings problem: the caller's own work (a saved token) is already done.

    `confirmed=False` means the caller could not look the org up with this
    token (`switch-org <id>`), which is when the id is most likely wrong, so
    nothing is offered (final review T6.8).

    Returns "disabled", "no-org", "in-agent", "unconfirmed",
    "non-interactive", "already", "declined", "written" or "invalid".
    """
    if _disabled():
        return "disabled"
    if not org_id or not _ORG_ID.match(org_id):
        return "no-org"
    name = _display(org_name, org_id)
    path = (settings_path or default_settings_path()).resolve()

    if _in_agent():
        # Never write here. But an agent may switch orgs (CLAUDE.md documents
        # `switch-org <orgId>` in automation), and auto mode's classifier reads
        # commands, not their output or wxcli's config, so say on stderr when
        # the rule still names another org (final review I1).
        try:
            current = _read(path)[0]
        except (OSError, ValueError):
            current = {}
        has_rule = _has_rule_for(current, org_id)
        stale = _rule_org_names(current, skip_id=org_id)
        if stale:
            _say_stale(stale, name)
        elif not has_rule and confirmed:
            _say(f'To let Claude Code work in {name} without stopping to ask, run '
                 '"wxcli configure" once in your own terminal, outside Claude Code.')
        return "in-agent"
    if not confirmed:
        _say("Not offering the Claude Code auto-mode rule: wxcli could not confirm "
             f"org {org_id} with this token.")
        return "unconfirmed"
    if not _interactive():
        return "non-interactive"

    try:
        settings, original = _read(path)
    except (OSError, ValueError) as exc:
        return _not_changed(path, exc)
    rules = automode_rules(org_name, org_id)
    if _is_already(settings, rules):
        return "already"
    others = _rule_org_names(settings)

    _say()
    if token_org_id and token_org_id != org_id:
        _say(f"Note: wxcli targets {name}, not the org your token belongs to.")
    _say(f"Claude Code auto mode: answering y adds these entries to {path}")
    for key in KEYS:
        for entry in rules[key]:
            _say(f"  autoMode.{key}: {entry}")
    asks = _missing_ask(settings)
    for entry in asks:
        _say(f"  permissions.ask: {entry}")
    if asks:
        _say("  (Claude may still switch or clear the target org; the "
             "permissions.ask lines make Claude Code ask you each time.)")
    if others:
        _say(f"Answering n also removes the rule for {', '.join(others)}.")
    question = (f"Let Claude Code create, change and delete things in {name} "
                "without stopping to ask? [y/n]")
    try:
        yes = bool((confirm or ask_yes_no)(question))
    except (EOFError, KeyboardInterrupt):
        _say()
        yes = False

    # Read again: the question can wait a long time, and an open Claude Code
    # session (/permissions) may have changed the file meanwhile. Merging onto
    # the copy read before the question would drop that change (final review
    # T6.3). Same validation as the first read.
    try:
        settings, original = _read(path)
        if yes:
            if merge_automode(settings, rules):
                _write(path, settings, original)
            _say("Added. Change it later in Claude Code with /permissions → Auto mode.")
            return "written"
        removed = _rule_org_names(settings)
        if remove_automode(settings):
            _write(path, settings, original)
            _say(f"Removed the rule for {', '.join(removed)}.")
        return "declined"
    except (OSError, ValueError) as exc:
        return _not_changed(path, exc)


def clear_automode(*, settings_path: Path | None = None) -> str:
    """Remove every MARK entry (`wxcli clear-org`). Only in a terminal outside
    an agent, like the offer. Returns "disabled", "in-agent",
    "non-interactive", "invalid", "already" or "removed"."""
    if _disabled():
        return "disabled"
    path = (settings_path or default_settings_path()).resolve()
    if _in_agent():
        # Never write here; but say when a rule outlives the org (final
        # review I1), as the offer does after an agent's switch-org.
        try:
            stale = _rule_org_names(_read(path)[0])
        except (OSError, ValueError):
            stale = []
        if stale:
            _say_stale(stale, "no saved org")
        return "in-agent"
    if not _interactive():
        return "non-interactive"
    try:
        settings, original = _read(path)
        if not remove_automode(settings):
            return "already"
        _write(path, settings, original)
    except (OSError, ValueError) as exc:
        return _not_changed(path, exc)
    _say(f"Removed wxcli's Claude Code auto-mode rules from {path}.")
    return "removed"
