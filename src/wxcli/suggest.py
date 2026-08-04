"""Did-you-mean suggestions that never offer a delete as the fix for a read.

Typer's `TyperGroup.resolve_command` appends `difflib.get_close_matches` results
to a UsageError. Measured over 786,912 generated typos: 32,203 read-intent typos
came back with a destructive suggestion, 170 of them with no safe alternative at
all, and 984 where the top destructive suggestion carries no confirmation prompt.

The consumer here is an LLM, and that inverts the usual trade-off. An agent does
not learn a CLI by mistyping and reading the near-misses — it reads `--help`. So
the discoverability that filtering costs is worth ~nothing, while the risk is
real: an agent acts on error text literally, and `Did you mean 'delete-...'` is
read as an instruction.

Filtering only ever applies when the TYPED string reads as a read. A typo on a
delete still gets delete suggestions, which is what makes this safe to do.
"""

from __future__ import annotations

import click
import typer.core as _typer_core
from typer.core import TyperGroup


def _usage_error_classes() -> tuple[type[BaseException], ...]:
    """Every UsageError class typer might raise, because there is more than one.

    typer 0.26+ VENDORS its own click as `typer._click`, and
    `typer._click.exceptions.UsageError` is a DIFFERENT class object from
    `click.exceptions.UsageError` — same name, same shape, unrelated by
    inheritance. So a bare `except click.UsageError` catches nothing typer
    raises, and the filtering below becomes silently inert: no error, no
    warning, just a safety feature that stops running.

    That is the failure mode this module exists to prevent, one level up. Catch
    both, deduplicated, so the class works whichever click typer resolved.
    """
    classes: list[type[BaseException]] = [click.UsageError]
    shim = getattr(_typer_core, "_click", None)
    vendored = getattr(getattr(shim, "exceptions", None), "UsageError", None)
    if isinstance(vendored, type) and vendored not in classes:
        classes.append(vendored)
    return tuple(classes)


USAGE_ERRORS = _usage_error_classes()

# Verbs an agent types when it wants to READ. `get`/`describe`/`view` are not in
# this CLI's own verb vocabulary, but they are exactly what a model reaches for
# — the detector's A-VERBSWAP typo family is built from that substitution.
READ_VERBS = frozenset({
    "list", "show", "get", "describe", "read", "view", "find", "search", "query",
})

# Name shapes that destroy something. Kept deliberately broad: a false positive
# only costs one suppressed suggestion, a false negative offers a delete.
DESTRUCTIVE_MARKERS = ("delete", "remove", "purge", "destroy", "wipe", "reset")


# The verb itself is usually the part that got mistyped — `lst-handsets`,
# `shw-vendors`. Exact matching missed all of those, which is most of the
# population, so the leading token is matched fuzzily. The cutoff is high enough
# that no destructive verb reads as a read: measured below in READ_VERB_CUTOFF's
# guard test, `delet`/`remov`/`purg`/`reset`/`updat` all stay out.
READ_VERB_CUTOFF = 0.75


def _leading_verb(name: str) -> str:
    return name.split("-", 1)[0].lower()


def is_read_intent(typed: str) -> bool:
    from difflib import get_close_matches

    verb = _leading_verb(typed)
    if verb in READ_VERBS:
        return True
    return bool(get_close_matches(verb, READ_VERBS, n=1, cutoff=READ_VERB_CUTOFF))


def is_destructive(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in DESTRUCTIVE_MARKERS)


def filter_suggestions(typed: str, matches: list[str]) -> list[str]:
    """Drop destructive candidates when the typed string reads as a read."""
    if not is_read_intent(typed):
        return matches
    return [m for m in matches if not is_destructive(m)]


class SafeSuggestGroup(TyperGroup):
    """TyperGroup whose did-you-mean cannot answer a read typo with a delete.

    Replaces Typer's message wholesale rather than editing it, so that when
    filtering removes every candidate the user still gets a literal next command
    (`--help`) instead of a bare "No such command" — the same rule the error
    handler follows everywhere else in this CLI.
    """

    def _resolve_without_typers_suggestion(self, ctx: click.Context, args: list[str]):
        """Plain click resolution, with Typer's own did-you-mean bypassed.

        This class REPLACES that message rather than editing it, so it must reach
        the raw click behaviour — but where that lives moved.

        typer 0.26.0 changed TyperGroup's MRO from `TyperGroup -> Group ->
        Command` to `TyperGroup -> Command -> ABC`: click.Group is no longer
        behind it. The original `super(TyperGroup, self).resolve_command(...)`
        therefore found nothing and raised AttributeError, which took down
        **every** `wxcli <group> <command> --help` on typer >= 0.26 — measured
        exit 1 on people, locations, call-queue and cucm in a clean venv, versus
        exit 0 on typer 0.25.1 from the same source tree. It survived unnoticed
        because a dev machine whose typer was resolved months ago still satisfies
        `typer>=0.9.0`, and pip never upgrades an already-satisfied pin.

        0.26+ exposes the underlying click call as `_click_resolve_command`, so
        prefer it and fall back to the pre-0.26 MRO walk. Binary-searched: 0.25.1
        is the last version taking the fallback, 0.26.0 the first taking the
        branch. Do NOT "simplify" this to `super().resolve_command(...)` — that
        is TyperGroup's own, which appends the suggestion this class exists to
        replace, and would double it.
        """
        base = getattr(self, "_click_resolve_command", None)
        if base is not None:
            return base(ctx, args)
        return super(TyperGroup, self).resolve_command(ctx, args)

    def resolve_command(self, ctx: click.Context, args: list[str]):
        try:
            return self._resolve_without_typers_suggestion(ctx, args)
        except USAGE_ERRORS as e:
            if not (self.suggest_commands and args and self.commands):
                raise
            typed = args[0]
            from difflib import get_close_matches

            matches = filter_suggestions(
                typed, get_close_matches(typed, list(self.commands.keys()))
            )
            base = e.message.rstrip(".")
            if matches:
                names = ", ".join(f"{m!r}" for m in matches)
                e.message = f"{base}. Did you mean {names}?"
            else:
                e.message = f"{base}. Run: {ctx.command_path} --help"
            raise
