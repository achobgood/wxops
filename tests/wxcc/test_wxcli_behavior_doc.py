"""Task 3 (Plan 4): docs/reference/wxcli-behavior.md and the citations that point at it.

Pure-local, no API calls. Three jobs:
  * the Known Issues list keeps numbers #1-#11 and text unchanged (#2 byte-equal to the
    root CLAUDE.md line at the moment of the copy);
  * every retargeted citation line resolves, and none of the old forms is left anywhere
    in the shipped bundle (case-insensitive);
  * the bundle's known-issue numbers are 1-11 on a line naming wxcli-behavior.md, or the
    generator's own numbering stated as such.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "reference" / "wxcli-behavior.md"
BUNDLE = REPO / "src" / "wxcli" / "_playbook"

ISSUE_2 = "2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Run the command with `--generate-json-body` to print an indented request-body skeleton and exit before authenticating, e.g. `wxcli user-settings update-call-forwarding PERSON_ID --generate-json-body`; edit the printed skeleton and pass it back via `--json-body`. Caveat, verified live: `--generate-json-body` does not bypass required positional arguments — `wxcli call-queue create --generate-json-body` fails with `Missing argument 'LOCATION_ID'`; pass a placeholder positional first, e.g. `wxcli call-queue create dummy-location-id --generate-json-body`. `cc-team`, `cc-skill-profile` and `cc-desktop-profile` `create`/`update` had no `--generate-json-body` (and required a dummy `--team-dto` / `--skill-profile-dto` / `--agent-profile-dto` beside `--json-body`) because the spec declares their body as a query parameter; since the generator fix of 2026-10-13 (ADR-16) they take `--json-body` alone and offer `--generate-json-body`, and the old option is accepted and ignored — Verified live 2026-10-13 on a temporary team, skill profile and desktop profile (create, show, update, delete; the old option on update for teams and desktop profiles; not tried: the old option on create, or on update for skill profiles)."


def _known_issues_section() -> list[str]:
    lines = DOC.read_text().split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## 3. Known Issues"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def test_known_issues_keep_their_numbers():
    section = _known_issues_section()
    numbered = [ln for ln in section if re.match(r"^\d+\. \*\*", ln)]
    assert [int(re.match(r"^(\d+)\.", ln).group(1)) for ln in numbered] == list(range(1, 12))
    assert numbered[1] == ISSUE_2


# (file, text that is on the line before and after the edit, kind)
#   wb:N   -> names wxcli-behavior.md and Known Issue #N
#   wb:CF  -> names wxcli-behavior.md and Common Flags
#   gen:N  -> reads "the generator's known issue #N"
#   unv    -> the unverified-limit callout
PINNED = [
    (".claude/skills/configure-features/SKILL.md", r"an object \(", "wb:2"),
    (".claude/skills/manage-call-settings/SKILL.md", "Every `mode-management` command is a `/people/me/` endpoint", "wb:3"),
    (".claude/skills/manage-call-settings/SKILL.md", "Do NOT confuse with `guestCalling`", "wb:4"),
    (".claude/skills/manage-call-settings/SKILL.md", "404 (error 4008) on any `mode-management` command", "wb:3"),
    (".claude/skills/manage-call-settings/SKILL.md", "404 on `virtual-line-settings` commands", "wb:9"),
    (".claude/skills/org-health/SKILL.md", "before analyzing. See", "wb:CF"),
    ("docs/knowledge-base/migration/kb-identity-numbering.md", r"<!-- Source: .*(claude\.md|wxcli-behavior\.md) known issue", "wb:9"),
    ("docs/knowledge-base/migration/kb-identity-numbering.md", "Virtual extension vs virtual line ID type issue", "wb:9"),
    ("docs/reference/ai-receptionist.md", "`--json-body` (", "wb:2"),
    ("docs/reference/call-control.md", "Known issue #1 \u2014 admin tokens get 400", "wb:1"),
    ("docs/reference/call-control.md", "which is why an admin token on a bare command gets 400", "wb:1"),
    ("docs/reference/contact-center-agent-sdk.md", "**Known Issue #11** was corrected", "wb:11"),
    ("docs/reference/person-call-settings-behavior.md", "for the admin token (", "wb:3"),
    ("docs/reference/person-call-settings-handling.md", "shape documented for the 19 user-only settings", "wb:4"),
    ("docs/reference/webhooks-events.md", "the generator emits no flag for it", "wb:2"),
    ("docs/knowledge-base/migration/kb-feature-mapping.md", r"call-features-additional\.md lines 1344-1422", "wb:7"),
    ("docs/knowledge-base/migration/kb-feature-mapping.md", "CX queues hidden from default list", "wb:7"),
    ("docs/knowledge-base/migration/kb-user-settings.md", r"<!-- Source: self-service-call-settings\.md; ", "wb:4"),
    ("docs/knowledge-base/migration/kb-user-settings.md", r"sec 2 summary table", "wb:4"),
    ("docs/knowledge-base/migration/kb-user-settings.md", r"<!-- Source: [^;]*(claude\.md|wxcli-behavior\.md) known issue #5", "wb:5"),
    ("docs/knowledge-base/migration/kb-user-settings.md", r"matrix completed 2026-03-27\); (claude\.md|wxcli-behavior\.md)", "wb:6"),
    ("docs/knowledge-base/migration/kb-user-settings.md", "Workspace Basic limited to musicOnHold", "wb:6"),
    ("docs/knowledge-base/migration/kb-webex-limits.md", "Call control (user)", "wb:1"),
    ("docs/knowledge-base/migration/kb-webex-limits.md", "/people/me/ settings", "wb:4"),
    ("docs/knowledge-base/migration/kb-webex-limits.md", "Contact Center APIs", "wb:11"),
    ("docs/knowledge-base/migration/kb-webex-limits.md", r"\| Shared line appearances \|", "unv"),
    ("docs/reference/self-service-call-settings.md", "(6 user-only endpoints)", "wb:4"),
    ("docs/reference/self-service-call-settings.md", r"cross-reference:\*\* (claude\.md|\[wxcli-behavior)", "wb:3"),
    ("docs/reference/self-service-call-settings.md", "Mode management requires a calling-licensed user", "wb:3"),
    ("docs/reference/location-recording-advanced.md", "Conference controls require a **user-level OAuth token**", "wb:1"),
    ("docs/reference/location-recording-advanced.md", "the API takes a request body the generator drops", "gen:21"),
    ("docs/reference/location-calling-media.md", "the destructive-PUT shape", "gen:20"),
    ("docs/reference/messaging-spaces.md", "There is no `--files` flag", "wb:2"),
    ("docs/reference/contact-center-analytics.md", "the same class of silent retarget as", "gen:18"),
    (".claude/skills/customer-assist/SKILL.md", "which the generator does not render for DELETE verbs", "gen:21"),
    (".claude/skills/customer-assist/SKILL.md", "Mandatory --help verification", "wb:7"),
    (".claude/skills/device-platform/SKILL.md", "Mandatory --help verification", "wb:10"),
    (".claude/skills/query-live/SKILL.md", "Mandatory --help verification", "wb:5"),
    (".claude/skills/reporting/SKILL.md", "Mandatory --help verification", "wb:5"),
    (".claude/skills/wxc-calling-debug/SKILL.md", "Mandatory --help verification", "wb:5"),
]


def _regex_hit(pattern: str, line: str) -> bool:
    try:
        return re.search(pattern, line, re.I) is not None
    except re.error:
        return False


def _lines_with(path: str, anchor: str) -> list[str]:
    text = (REPO / path).read_text().split("\n")
    hits = [ln for ln in text if anchor.lower() in ln.lower() or _regex_hit(anchor, ln)]
    assert hits, f"{path}: no line contains {anchor!r}"
    return hits


def _satisfies(line: str, kind: str) -> bool:
    low = line.lower()
    if kind.startswith("wb:") and kind != "wb:CF":
        n = kind[3:]
        return "wxcli-behavior.md" in line and re.search(rf"known issues? #{n}\b", low) is not None
    if kind == "wb:CF":
        return "wxcli-behavior.md" in line and "common flags" in low
    if kind.startswith("gen:"):
        n = kind[4:]
        return f"generator's known issue #{n}" in low
    if kind == "unv":
        return "**unverified:** no known issue states this limit" in low
    raise AssertionError(kind)


def test_known_issue_citations_resolve():
    # The 3 code/maintainer lines outside the bundle: the comment in common.py and tools/CLAUDE.md.
    code = (REPO / "src/wxcli/common.py").read_text()
    assert "wxcli-behavior.md" in code and "CLAUDE.md known issue #7" not in code
    tools_md = (REPO / "tools/CLAUDE.md").read_text()
    assert "docs/reference/wxcli-behavior.md" in tools_md and "CLAUDE.md`'s Common Flags section" not in tools_md

    bad = []
    for path, anchor, kind in PINNED:
        for ln in _lines_with(path, anchor):
            if not _satisfies(ln, kind):
                bad.append((path, kind, ln[:140]))
    assert not bad, "\n".join(map(str, bad))


# Root CLAUDE.md / AGENTS.md are Task 4's (it removes the section and retargets its own links);
# wxcli-behavior.md is the home of the numbers and cites them in-file.
_BUNDLE_EXEMPT = {"CLAUDE.md", "AGENTS.md", "docs/reference/wxcli-behavior.md"}


def _bundle_files():
    for p in sorted(BUNDLE.rglob("*")):
        if p.is_file() and p.suffix in {".md", ".txt", ".yaml", ".yml", ".json"}:
            rel = p.relative_to(BUNDLE).as_posix()
            if rel not in _BUNDLE_EXEMPT:
                yield rel, p.read_text().split("\n")


def test_known_issue_citations_resolve_bundle_wide():
    stale = re.compile(r"(?i)claude\.md[^\n|]{0,80}(known issue|common flags)")
    stale2 = re.compile(r"(?i)known issues? in (the )?(root )?.?claude\.md")
    num = re.compile(r"(?i)known issue #(\d+)")
    bad = []
    for rel, lines in _bundle_files():
        for i, ln in enumerate(lines, 1):
            if stale.search(ln) or stale2.search(ln):
                bad.append((rel, i, "old form", ln[:120]))
            for m in num.finditer(ln):
                n = int(m.group(1))
                ok = (1 <= n <= 11 and "wxcli-behavior.md" in ln) or \
                     re.search(rf"(?i)the generator's known issue #{n}\b", ln)
                if not ok:
                    bad.append((rel, i, f"#{n}", ln[:120]))
    assert not bad, "\n".join(map(str, bad))
