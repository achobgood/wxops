# Playbook Review — Multi-Agent Evaluation

## Overview

4 parallel review agents evaluate the Webex Calling playbook from different angles, then findings are synthesized into a single prioritized punch list.

## Reviewers

| Reviewer | Files | Lens |
|----------|-------|------|
| Agent Architecture | Agent workflow + 4 skills | Decision logic, error handling, workflow gaps |
| CLI Integration | Agent + skills + live wxcli --help | Command names, flags, syntax correctness |
| Reference Doc Quality | 4 spot-check docs | URLs, response keys, required fields, markdown |
| Developer Experience | README, CLAUDE.md, pyproject.toml | Clone-to-working, auth, first-run |

## Output

Per reviewer: table of findings with file, issue, fix, severity.
Synthesis: merged, deduplicated, sorted by severity, top 5 executive summary.
