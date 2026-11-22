"""The CUCM pipeline-stage state machine, in one place.

A migration project carries two state records in ``state.json``:

* ``completed_stages`` — which pipeline commands have finished, in order.
  **This is the authoritative one.** Every gate reads it, and re-running an
  earlier stage rolls it back (see :func:`downstream_of`).
* ``state`` — the :class:`~wxcli.migration.state.ProjectState` enum. It only
  moves forward (``VALID_TRANSITIONS`` has no backwards edges), so after a
  re-run it can claim a stage that ``completed_stages`` no longer holds.
  :func:`stage_divergence` detects that; nothing rewrites it (finding F13).

Before this module the stage machine was spread across ``commands/cucm.py``:
two copies of the stage order (``PIPELINE_STAGES``, unused, and
``STAGE_ORDER``), a prerequisite table that left out ``report``,
``user-diff`` and ``user-notice`` (each re-implemented the gate by hand with
its own wording), and no single answer to "what do I run next?". Every rule
the gate, ``status`` and the invalidation step need now lives here as data,
and the functions below are pure so they test without a project on disk.

The transitions, as a diagram (each arrow is "requires"):

.. code-block:: text

    init → discover → normalize → map → analyze → plan → preflight → execute
                                           │
                                           ├→ report
                                           ├→ user-diff
                                           └→ user-notice

Only the commands on the top row are *stages* (they record themselves in
``completed_stages``). ``execute``, ``report``, ``user-diff`` and
``user-notice`` are *gated commands*: they need a stage but record nothing.
"""

from __future__ import annotations

from typing import Iterable

__all__ = [
    "STAGE_ORDER",
    "STAGE_PREREQUISITES",
    "STATE_IMPLIES_STAGE",
    "command_for",
    "downstream_of",
    "missing_prerequisite",
    "next_stage",
    "stage_divergence",
]

#: Pipeline stages in execution order. ``completed_stages`` is a subset of
#: this, and in practice a prefix of it: a stage is gated on its predecessor,
#: and re-running a stage drops everything after it.
STAGE_ORDER: tuple[str, ...] = (
    "init", "discover", "normalize", "map", "analyze", "plan", "preflight",
)

#: The stage each command needs in ``completed_stages`` before it may run.
#: Covers every gated command — stages and non-stage commands alike — so the
#: gate is one function call everywhere instead of four hand-rolled copies.
STAGE_PREREQUISITES: dict[str, str] = {
    "discover": "init",
    "normalize": "discover",
    "map": "normalize",
    "analyze": "map",
    "plan": "analyze",
    "preflight": "plan",
    # `execute` is the only stage that writes to a live customer org, and until
    # 2026-08-05 it was the only stage with no prerequisite at all — every read
    # stage above was gated, and so is `report`, which merely writes an HTML file.
    # The cucm-migrate skill calls preflight "MANDATORY. No override or bypass";
    # that sentence lived in a prompt file and nothing in code enforced it.
    #
    # Safe against the documented recovery loop, traced before enabling: the
    # `execute → retry-failed → execute` cycle touches `completed_stages` at no
    # point, so preflight stays satisfied across every retry pass. The only thing
    # that clears it is `downstream_of` (re-running an earlier stage) — and a
    # re-plan *should* require a fresh preflight.
    "execute": "preflight",
    # The three post-analyze deliverables read the store as `analyze` left it
    # and need neither plan nor preflight (migration/CLAUDE.md, "To generate
    # an assessment report" and the two entries after it).
    "report": "analyze",
    "user-diff": "analyze",
    "user-notice": "analyze",
}

#: The stage each ProjectState claims has completed. Re-running an earlier
#: stage rolls ``completed_stages`` back but cannot roll ``ProjectState`` back,
#: so the two diverge permanently. Used to flag that on read only.
STATE_IMPLIES_STAGE: dict[str, str] = {
    "initialized": "init",
    "connected": "init",  # discover began, did not complete
    "discovered": "discover",
    "analyzed": "analyze",
    "ready": "analyze",
    "blocked": "analyze",
    "planned": "plan",
    "preflight_failed": "plan",
    "preflight": "preflight",
    "snapshotted": "preflight",
    "executing": "preflight",
    "failed": "preflight",
    "validating": "preflight",
    "completed": "preflight",
    "rolled_back": "preflight",
}

#: The literal command that completes each stage. ``init`` and ``discover``
#: need arguments the tool cannot know, so they show their shape.
_STAGE_COMMANDS: dict[str, str] = {
    "init": "wxcli cucm init <project-name>",
    "discover": (
        "wxcli cucm discover --host <cucm-host> --username <axl-user> "
        "--password <axl-password>  (or: --from-file <collector-file>)"
    ),
}


def command_for(stage: str) -> str:
    """The literal command an operator (or agent) runs to complete ``stage``."""
    return _STAGE_COMMANDS.get(stage, f"wxcli cucm {stage}")


def missing_prerequisite(command: str, completed: Iterable[str]) -> str | None:
    """The stage ``command`` needs that ``completed`` lacks, or None if clear.

    Commands with no entry in :data:`STAGE_PREREQUISITES` (``init``, ``status``,
    ``decisions`` …) are never gated.
    """
    required = STAGE_PREREQUISITES.get(command)
    if required is None or required in set(completed):
        return None
    return required


def downstream_of(stage: str) -> list[str]:
    """Stages that re-running ``stage`` invalidates (everything after it).

    Empty for a command that is not a stage.
    """
    if stage not in STAGE_ORDER:
        return []
    return list(STAGE_ORDER[STAGE_ORDER.index(stage) + 1:])


def next_stage(completed: Iterable[str]) -> str | None:
    """The first stage in :data:`STAGE_ORDER` not yet completed, or None."""
    done = set(completed)
    for stage in STAGE_ORDER:
        if stage not in done:
            return stage
    return None


def stage_divergence(project_state: str, completed: Iterable[str]) -> str | None:
    """The stage ``project_state`` claims but ``completed`` denies, or None.

    Unknown states return None rather than raising a false alarm, so a state
    file written by a newer version still reads cleanly.
    """
    implied = STATE_IMPLIES_STAGE.get(project_state)
    if implied is None or implied in set(completed):
        return None
    return implied
