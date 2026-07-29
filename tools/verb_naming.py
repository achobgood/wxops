"""Command-name-vs-behaviour classification, promoted from the d3 detector.

Two defect classes the generator cannot decide on its own, both listed in
tools/CLAUDE.md § "When Cisco ships new endpoints" as NOT GATED:

  B  numeric-suffix names   — `_dedup_command_names` resolved a collision by
                              appending `-1`/`-2`, which carries no meaning.
  C  resource mismatches    — a bare verb whose URL targets something other
                              than the group's headline resource. The obvious
                              name runs, exits 0, and answers a different
                              question; tools/CLAUDE.md calls this "the single
                              most expensive defect shape in the tool".

`docs/superpowers/quality-loop/artifacts/detectors/d3-verbs/detector.py` found
both, was run once as a script, and was never wired in. A detector you run once
is a cleanup; a detector in the gate is a ratchet. This module is the ratchet —
drift_check.py check 12 consumes it, and spec_sync.py runs the drift gate after
every regeneration, so a newly-generated `-N` cannot land unnoticed.

Read-only and static: nothing here imports or invokes a generated command.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO / "src" / "wxcli" / "commands"

CANON_VERBS = ("list", "show", "create", "update", "delete")

REST_METHOD = {
    "rest_get": "GET", "rest_post": "POST", "rest_put": "PUT",
    "rest_delete": "DELETE", "rest_patch": "PATCH",
    "follow_pagination": "GET",
}

BULK_RE = re.compile(r"\b(bulk|multiple|all|batch|several)\b", re.I)

# path segments naming an ACTION, not the resource being returned
ACTION_SEG = {
    "query", "search", "actions", "action", "bulk", "reload", "validate",
    "test", "export", "import", "preview", "count", "login", "logout",
    "refresh", "sync", "verify", "activate", "deactivate", "start", "stop",
    "publish", "unpublish", "restore", "reset", "apply", "generate",
    "batch", "me", "config", "settings", "details", "status",
}
SKIP_SEG = {"v1", "v2", "v3", "v4", "api", "telephony", "config",
            "organizations", "admin", "webexapis.com", "https:", "",
            "{cc_base_url}"}

SYNONYM = {
    "person": "people", "people": "people", "user": "people", "member": "people",
    "workspace": "workspace", "location": "location", "site": "location",
    "device": "device", "phone": "device", "recording": "recording",
    "queue": "queue", "agent": "agent", "number": "number", "call": "call",
    "setting": "setting", "feature": "feature",
}


@dataclass
class Cmd:
    group: str
    module: str
    name: str
    lineno: int
    summary: str
    url: str
    method: str
    hidden: bool = False
    positionals: list[str] = field(default_factory=list)

    @property
    def base(self) -> str:
        return re.sub(r"-\d+$", "", self.name)

    @property
    def verb(self) -> str | None:
        head = self.name.split("-")[0]
        return head if head in CANON_VERBS else None

    @property
    def op_key(self) -> str:
        """`METHOD /path` — the ack key. Stable across renames on purpose: an
        ack names the OPERATION it excuses, and records the command name it was
        written for, so renaming the command makes the ack stale rather than
        silently carrying it to a name nobody reviewed."""
        path = re.sub(r"^https?://[^/]+", "", self.url) or self.url
        return f"{self.method} {path}"


# --------------------------------------------------------------- token tools

def split_camel(tok: str) -> list[str]:
    return [p.lower() for p in
            re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+", tok)]


def singular(w: str) -> str:
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("sses", "shes", "ches")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def norm_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for raw in re.split(r"[-_/\s]+", text):
        for t in split_camel(raw):
            s = singular(t)
            out.add(s)
            out.add(SYNONYM.get(s, s))
    return {t for t in out if t and t not in SKIP_SEG}


def url_path(url: str) -> list[str]:
    p = re.sub(r"^https?://[^/]+", "", url)
    p = p.replace("{cc_base_url}", "").replace("{base_url}", "")
    return [s for s in p.split("/") if s]


def is_action_seg(seg: str) -> bool:
    low = seg.lower()
    if low in ACTION_SEG:
        return True
    parts = (split_camel(seg) if "-" not in seg
             else [p.lower() for p in seg.split("-")])
    return bool(parts) and parts[-1] in ACTION_SEG


def url_resource(url: str) -> str:
    """The resource segment the URL actually returns, ignoring trailing action
    and boilerplate segments (`/query`, `/settings`, `/v1`)."""
    segs = [s for s in url_path(url) if not s.startswith("{")]
    while segs and is_action_seg(segs[-1]):
        segs.pop()
    while segs and segs[-1].lower() in SKIP_SEG:
        segs.pop()
    return segs[-1] if segs else ""


def tok_match(a: set[str], b: set[str]) -> bool:
    """Token overlap with a prefix fallback (vars <-> variable, num <-> number)."""
    if a & b:
        return True
    return any(len(x) >= 3 and len(y) >= 3 and (x.startswith(y) or y.startswith(x))
               for x in a for y in b)


# ---------------------------------------------------------------- extraction

def _join(node) -> str:
    """Flatten an f-string/concat URL assignment into a literal-ish path."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = ""
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                out += v.value
            elif isinstance(v, ast.FormattedValue):
                inner = v.value
                name = (inner.id if isinstance(inner, ast.Name)
                        else getattr(inner, "attr", "x"))
                out += "{" + name + "}"
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _join(node.left) + _join(node.right)
    return ""


def parse_module(module: str, group: str,
                 commands_dir: Path = COMMANDS_DIR) -> list[Cmd]:
    path = commands_dir / f"{module}.py"
    if not path.exists():
        return []
    cmds: list[Cmd] = []
    for node in ast.parse(path.read_text()).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not (isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr == "command"
                    and dec.args and isinstance(dec.args[0], ast.Constant)):
                continue
            cname = dec.args[0].value
            hidden = any(kw.arg == "hidden"
                         and isinstance(kw.value, ast.Constant)
                         and kw.value.value is True for kw in dec.keywords)
            doc = ast.get_docstring(node) or ""
            pos = []
            defaults = node.args.defaults
            offset = len(node.args.args) - len(defaults)
            for i, a in enumerate(node.args.args):
                if i < offset:
                    continue
                d = defaults[i - offset]
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                        and d.func.attr == "Argument"):
                    pos.append(a.arg)
            url, method = "", ""
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign) and not url:
                    for t in sub.targets:
                        if isinstance(t, ast.Name) and t.id == "url":
                            url = _join(sub.value)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    m = REST_METHOD.get(sub.func.attr)
                    if m and (not method or method == "GET"):
                        method = m
            cmds.append(Cmd(group, module, cname, node.lineno,
                            doc.split("\n")[0].strip(), url, method or "?",
                            hidden, pos))
    return cmds


# ------------------------------------------------------------ classification

def numeric_suffix_findings(cmds: list[Cmd]) -> list[dict]:
    """Every VISIBLE command whose generated name ends in `-N`.

    Severity-independent by decision (Adam, 2026-07-28): a `-N` name carries no
    meaning at all, so it is always a naming call a human never made. Hidden
    commands are excluded — those are rename aliases kept for compatibility,
    which is the FIX for this defect, not an instance of it.
    """
    return [
        {"group": c.group, "command": c.name, "op": c.op_key,
         "summary": c.summary, "url": c.url, "loc": f"{c.module}.py:{c.lineno}",
         "kind": "numeric-suffix", "severity": "HIGH",
         "proposed": f"{c.base}-<what makes it different>"}
        for c in cmds if re.search(r"-\d+$", c.name) and not c.hidden
    ]


TENANT = {"customer", "organization", "org", "person", "people",
          "user", "account", "tenant", "subscriber"}


def resource_mismatch_findings(cmds: list[Cmd]) -> list[dict]:
    """A command whose group AND name both fail to name the resource its URL
    targets. Ported from d3's List C, severities unchanged.

    CRITICAL — a bare destructive verb that destroys MORE than the name implies
               (bulk wording, or a tenant-level resource).
    HIGH     — a bare `list/show/create/update/delete` pointing somewhere else.
    MEDIUM   — non-bare name that still never says what the path targets.
    """
    by_group: dict[str, list[Cmd]] = {}
    for c in cmds:
        by_group.setdefault(c.group, []).append(c)
    # Does ANY command in the group address the group's own headline resource?
    # If not, the bare list/show is maximally deceptive — the thing the group is
    # named after is unreachable from the CLI entirely.
    reachable = {
        g: any(tok_match(norm_tokens(g), norm_tokens(url_resource(x.url)))
               for x in cs if x.url)
        for g, cs in by_group.items()
    }
    out: list[dict] = []
    for c in cmds:
        if c.verb is None or c.hidden or not c.url:
            continue
        res = url_resource(c.url)
        if not res:
            continue
        gtok, ntok, rtok = (norm_tokens(c.group), norm_tokens(c.name),
                            norm_tokens(res))
        if tok_match(gtok, rtok) or tok_match(ntok - set(CANON_VERBS), rtok):
            continue
        bare = re.fullmatch(r"(list|show|create|update|delete)(-\d+)?",
                            c.name) is not None
        slug = "-".join(split_camel(res)) if "-" not in res else res.lower()
        if bare:
            escalates = c.verb == "delete" and (bool(BULK_RE.search(c.summary))
                                                or bool(rtok & TENANT))
            sev = "CRITICAL" if escalates else "HIGH"
            why = (f"bare '{c.name}' in group '{c.group}' targets '{slug}' — "
                   f"the name gives the caller no hint that the resource "
                   f"differs from the group")
            if not reachable.get(c.group, True):
                why += (f"; AND no command in this group addresses "
                        f"'{c.group}' itself — the headline resource is "
                        f"UNREACHABLE, so the wrong answer is silent")
        else:
            sev = "MEDIUM"
            why = (f"neither the group '{c.group}' nor the command name names "
                   f"'{slug}', which is what the path targets")
        out.append({"group": c.group, "command": c.name, "op": c.op_key,
                    "summary": c.summary, "url": c.url,
                    "loc": f"{c.module}.py:{c.lineno}",
                    "kind": "resource-mismatch", "severity": sev,
                    "why": why, "proposed": f"{c.verb}-{slug}"})
    return out
