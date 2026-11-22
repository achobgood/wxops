"""Drift check 35 — a documented command's request surface the docs never mention.

Check 19 notices when Cisco adds a field or an allowed value to an operation; check 20
notices a whole command group with no reference doc. Nothing noticed the middle case:
a command the reference docs already document gains a body field, a query parameter or
an enum value, the generator renders it, the weekly spec-sync releases it, and no doc
ever says it exists. Measured 2026-11-02: `channel create` gained `CUSTOM_MESSAGING`
(and its required `messagingPolicy`) by the 2026-10-13 sync, and
`contact-center-routing.md` § 15 still listed only telephony, email, chat and social.

**What a finding is.** For every command a `docs/reference/` file cites (a fenced or
inline `wxcli <group> <command>` the shared `command_heads` reader sees), the spec
operation it renders is read and its request surface is listed:

  * `body:<name>`  — a top-level request-body property (allOf/oneOf/anyOf merged,
                     readOnly dropped; a query parameter the generator lifts into the
                     body, ADR-16, counts as the body);
  * `query:<name>` — a query parameter, minus org-id and paging names the CLI owns;
  * `enum:<field>=<value>` — an allowed value of one of those fields.

An item is covered when its name (or, for a field, its `--kebab-flag` form) appears
in a `## ` section of a reference doc that cites the command. Substring match, case-sensitive:
generous on purpose, because a false finding blocks the unattended weekly run.

**The baseline is a debt snapshot, not an ack list.** `tools/doc_gap_baseline.json`
records every gap that existed when the check landed (2026-11-02), so old debt does not
block every commit while new debt does. Gated: a gap NOT in the baseline. Advisory: a
baseline entry that is no longer a gap (closed by a doc edit, or the field left the
spec) — `--refresh-doc-gap-baseline` drops those, and refuses to ADD an entry unless
`--force` is passed, so the baseline only ever shrinks. The weekly routine may not edit
the baseline (`tools/sync_guard.py` FORBIDDEN_PATHS); it clears a new gap by writing
the doc (`docs/spec-sync-contract.md` § 2 E).

Keyed on `<METHOD> <normalized path> <item>`, never on a spec file, so an operation two
specs declare is one entry and a spec reshuffle does not churn the baseline.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "tools" / "doc_gap_baseline.json"

# Query names the CLI supplies or translates itself; a doc need not name them.
_CLI_OWNED_QUERY = frozenset({
    "orgId", "orgid", "start", "max", "offset", "limit", "page", "pageSize", "size",
    "startIndex", "count", "includePagination",
})
_ENUM_MIN_LEN = 2
# Server-managed body properties Cisco's specs often forget to mark readOnly.
_SERVER_OWNED_BODY = frozenset({"createdTime", "lastUpdatedTime", "createdAt", "updatedAt",
                                "lastModifiedTime", "links", "_links"})
_READ_ONLY_PROSE = re.compile(r"read[- ]only|populated by the server", re.I)


def _kebab(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", name)
    return "--" + re.sub(r"[_\s]+", "-", s).lower()


def _resolve(dc, spec: dict, node, depth: int = 0) -> dict:
    """$ref + allOf/oneOf/anyOf merged into one dict (drift_check._resolve_schema),
    keeping `enum` and `items`."""
    return dc._resolve_schema(spec, node, depth) if isinstance(node, dict) else {}


def _enum_values(dc, spec: dict, prop) -> list[str]:
    node = _resolve(dc, spec, prop)
    vals = node.get("enum") or []
    if not vals and node.get("type") == "array":
        vals = _resolve(dc, spec, node.get("items") or {}).get("enum") or []
    return [v for v in vals if isinstance(v, str) and len(v) >= _ENUM_MIN_LEN]


def request_surface(dc, sop) -> set[str]:
    """`body:` / `query:` / `enum:` items one spec operation accepts."""
    spec, op = sop.spec, sop.op
    items: set[str] = set()
    raw = dc._raw_body_schema(op, spec)
    lifted = dc.query_body_param(op, spec)
    if raw is not None:
        body = _resolve(dc, spec, raw)
        props = body.get("properties") or {}
        # A bulk wrapper ({"items": [ {...} ]}, `channel create`) carries the real
        # request one level down; judge the element, not the envelope.
        if len(props) == 1:
            only = _resolve(dc, spec, next(iter(props.values())))
            if only.get("type") == "array":
                element = _resolve(dc, spec, only.get("items") or {})
                eprops = element.get("properties") or {}
                # Contact Center bulk-save element: {itemIdentifier, requestAction,
                # item: <the DTO>} (32 operations, 2026-11-02). The DTO is the request.
                if "requestAction" in eprops and "item" in eprops:
                    element = _resolve(dc, spec, eprops["item"])
                if element.get("properties"):
                    body = element
        for name, prop in (body.get("properties") or {}).items():
            if not isinstance(prop, dict):
                continue
            resolved = _resolve(dc, spec, prop)
            if (prop.get("readOnly") or resolved.get("readOnly") or name in _SERVER_OWNED_BODY
                    or _READ_ONLY_PROSE.search(str(prop.get("description") or
                                                   resolved.get("description") or ""))):
                continue
            items.add(f"body:{name}")
            items.update(f"enum:{name}={v}" for v in _enum_values(dc, spec, prop))
    for p in op.get("parameters") or []:
        if "$ref" in p:
            p = dc._ref(spec, p)
        if not isinstance(p, dict) or p.get("in") != "query":
            continue
        name = p.get("name")
        if not name or name in _CLI_OWNED_QUERY or (lifted and name == lifted[0]):
            continue
        items.add(f"query:{name}")
        items.update(f"enum:{name}={v}" for v in _enum_values(dc, spec, p.get("schema") or {}))
    return items


def _covered(item: str, text: str) -> bool:
    kind, _, rest = item.partition(":")
    if kind == "enum":
        return rest.split("=", 1)[1] in text
    return rest in text or _kebab(rest) in text


_H2 = re.compile(r"^## ", re.M)


def _sections(text: str) -> list[tuple[int, int]]:
    """(first line, last line), 1-based, of each `## ` section; the preamble is one."""
    starts = [1] + [text.count("\n", 0, m.start()) + 1 for m in _H2.finditer(text)]
    starts = sorted(set(starts))
    total = text.count("\n") + 1
    return [(a, (starts[i + 1] - 1) if i + 1 < len(starts) else total)
            for i, a in enumerate(starts)]


def cited_commands(dc, reference_dir: Path) -> dict[tuple[str, str], dict[str, str]]:
    """{(module, command): {"<doc>#<first line>": text of the ## section citing it}}.

    Coverage is judged per SECTION: a value the same file lists for a different
    command (CUSTOM_MESSAGING under Assets, not under Channels) does not count."""
    registrations = dc.parse_registrations()
    cited: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(reference_dir.rglob("*.md")):
        text = path.read_text(errors="replace")
        lines = text.split("\n")
        bounds = _sections(text)
        rel = path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.name
        for line, span in dc.code_spans(text):
            for group, command, _rest, _prefixless in dc.command_heads(span):
                module = registrations.get(group)
                if not (module and command):
                    continue
                a, b = next(((a, b) for a, b in bounds if a <= line <= b), (1, len(lines)))
                cited.setdefault((module, command), {})[f"{rel}#{a}"] = \
                    "\n".join(lines[a - 1:b])
    return cited


def current_gaps(dc=None, reference_dir: Path | None = None) -> tuple[dict, int, int]:
    """({gap key: {"cmd", "docs"}}, commands examined, commands skipped).

    Skipped = cited commands with no URL-bearing block (a hidden alias name) or no
    spec operation (a hand-written or CLI-ahead command): nothing to judge."""
    if dc is None:
        from tools import drift_check as dc  # noqa: PLC0415 — avoid an import cycle
    reference_dir = reference_dir or dc.REFERENCE_DIR
    blocks = {(b.module, b.command): b for b in dc.iter_command_blocks()}
    ops = dc.spec_ops_by_key()
    gaps: dict[str, dict] = {}
    examined = skipped = 0
    for (module, command), sections in sorted(cited_commands(dc, reference_dir).items()):
        block = blocks.get((module, command))
        sops = ops.get((block.method, block.npath)) if block else None
        if not sops:
            skipped += 1
            continue
        examined += 1
        doc_text = "\n".join(sections[k] for k in sorted(sections))
        docs = sorted({k.rsplit("#", 1)[0] for k in sections})
        surface: set[str] = set()
        for sop in sops:
            surface |= request_surface(dc, sop)
        for item in sorted(surface):
            if _covered(item, doc_text):
                continue
            key = f"{block.method} {block.npath} {item}"
            entry = gaps.setdefault(key, {"cmd": f"{module.replace('_', '-')} {command}",
                                          "docs": set()})
            entry["docs"].update(docs)
    return gaps, examined, skipped


def load_baseline(path: Path = BASELINE) -> set[str]:
    try:
        return set(json.loads(path.read_text()).get("gaps") or [])
    except FileNotFoundError:
        return set()


def check_doc_gaps(dc, baseline: set[str] | None = None,
                   reference_dir: Path | None = None) -> tuple[list[dict], list[str]]:
    """(gated findings: new gaps, advisory: baseline entries no longer a gap)."""
    gaps, examined, skipped = current_gaps(dc, reference_dir)
    baseline = load_baseline() if baseline is None else baseline
    new = [{"key": k, "cmd": v["cmd"], "docs": sorted(v["docs"])}
           for k, v in sorted(gaps.items()) if k not in baseline]
    stale = sorted(baseline - set(gaps))
    findings = dc.record_examined("35", new, examined, skipped, "documented commands")
    return findings, stale


def refresh_baseline(force: bool = False, path: Path = BASELINE) -> int:
    """Shrink the baseline to the gaps that still exist. Adding an entry needs --force:
    a new gap is cleared by writing the doc, not by recording it."""
    gaps, _examined, _skipped = current_gaps()
    old = load_baseline(path)
    added = sorted(set(gaps) - old)
    if old and added and not force:
        print(f"doc-gap baseline: REFUSED — {len(added)} new gap(s) would be added. "
              "Document them (docs/reference/), or pass --force for a deliberate reset:")
        for k in added[:30]:
            print(f"  + {k}   ({gaps[k]['cmd']})")
        return 1
    keep = sorted(set(gaps) if (force or not old) else (old & set(gaps)))
    path.write_text(json.dumps({
        "_about": "Drift check 35 debt snapshot (tools/doc_gap.py). Shrink-only: "
                  "`python -m tools.drift_check --refresh-doc-gap-baseline` drops closed "
                  "gaps and refuses to add one without --force. Never hand-edit.",
        "gaps": keep,
    }, indent=1) + "\n")
    print(f"doc-gap baseline: {len(old)} -> {len(keep)} gap(s); "
          f"{len(old - set(keep))} closed, {len(added) if (force or not old) else 0} added")
    return 0
