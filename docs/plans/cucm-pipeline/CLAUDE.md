# CUCM Pipeline Architecture Specs

This directory contains the 8 authoritative architecture specs for the CUCM-to-Webex migration tool. These docs define the SQLite data store, two-pass ELT normalization, conflict detection (12 linter-pattern analyzers), field-level transform mappers (9 mappers), CSS decomposition algorithm, NetworkX dependency graph, interactive decision workflow, and idempotency/resumability. **Where these docs and the summary in `cucm-pipeline-architecture.md` conflict, these docs are authoritative.**

## Production Sequence

Q1-Q7 architecture docs first, then 03b mapper design (5 review rounds, 1016 lines), then synthesis review.

## Key Cross-References

- **02 -> 03b**: The cross-reference manifest (27 rows) in `02-normalization-architecture.md` feeds the mappers in `03b-transform-mappers.md`. Mappers consume resolved canonical objects post-normalization.
- **04 -> 03b**: The CSS decomposition algorithm in `04-css-decomposition.md` is implemented by `css_mapper` (mapper 8) in `03b-transform-mappers.md`.
- **03 <-> 03b**: Analyzers in `03-conflict-detection-engine.md` run AFTER mappers. Mappers produce per-object decisions; analyzers produce cross-object sweep decisions and skip objects that already have mapper-produced decisions of the same type.
- **05 -> all**: `05-dependency-graph.md` defines the execution order (static tiers + intra-tier DAG) that `engine.py` follows when running mappers and analyzers.

## Gap Design Docs (Phase 3a) — All Complete

- `02b-cucm-extraction.md` -- AXL + CUPI extraction design (8 extractors + Unity Connection REST client, returnedTags, zeep→canonical mappings, 27 cross-ref sources; AXL fields validated against live CUCM 15.0 in Phase 03; 4 CUPI paths remain unverified)
- `05a-preflight-checks.md` -- Preflight check design (7 checks, NUMBER_CONFLICT + DUPLICATE_USER algorithms, decision integration, performance budget)
- `05b-executor-api-mapping.md` -- Executor API mapping design (30+ operations, per-operation request builders, snapshot/rollback spec, PSTN coexistence, dry-run format)

## Verification Status

**02b-cucm-extraction.md:** Originally 29 unverified fields. After live CUCM 15.0 validation (2026-03-23), many resolved in code but the spec doc itself was not updated (implementation diverged from spec where live data contradicted it). Key resolutions:
- `listLocation` confirmed (method name)
- `timeZone` field name confirmed on DateTimeGroup
- `listSipTrunk` confirmed
- CSS member `index` field confirmed (not `sortOrder`)
- SIP trunk uses `destinations.destination[]` array (not flat fields)
- Route pattern `destination` not a valid list returnedTag
- Gateway `devicePoolName` not in list response (requires getGateway)
- AXL list schemas are restricted — many fields only available via get operations
- `listEndUser` blocked on test cluster (EPR/WSDL binding issue) — SQL fallback built

Remaining unverified: CUPI endpoint paths (4), some hunt pilot nested field structures, CTI RP schedule reference, calendar integration field on Phone. These are documented in the spec and in `future/expansion-scope.md`.

4 open questions in `05a-preflight-checks.md` — unchanged. All other docs clean.

## Future Expansion

`future/expansion-scope.md` — 8 Tier 2 canonical types + 18 Tier 3 informational types deferred from Phase 03. Build after current 20 canonical types are through Phase 05 (mappers).
