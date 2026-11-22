# Architectural Decisions — wxcli

This document captures the key architectural decisions that shaped the wxcli project. Each entry follows a consistent structure: what was decided, the context that motivated it, alternatives that were considered, rationale for the chosen path, consequences (both enabling and constraining), and current status.

---

## ADR-1: Generated Commands from OpenAPI Specs vs. Hand-Written

### Decision

Generate CLI commands automatically from OpenAPI 3.0 specifications using a custom pipeline (`tools/generate_commands.py` → `openapi_parser.py` → `command_renderer.py`), reserving hand-written commands for cases the generator cannot express.

### Context

The Webex API surface spans 9 OpenAPI specs covering calling, admin, device, messaging, meetings, and contact center — over 800 endpoints. Writing CLI commands by hand for each endpoint would be prohibitively slow, error-prone, and difficult to keep current as APIs evolve. Early development (commits cb7c743–da45f3a) hand-wrote v1 and v2 call feature commands, demonstrating the pattern but also the maintenance burden.

### Alternatives Considered

1. **Fully hand-written commands.** Maximum control, custom UX per endpoint. Unscalable at 800+ endpoints; updates lag behind API changes indefinitely.
2. **Use an existing CLI generator (e.g., AutoRest, openapi-generator-cli).** Lower initial effort. But these tools produce generic clients without the specific UX decisions wxcli needs (output formatting, orgId injection, pagination, table columns). Customization would fight the tool.
3. **Typed SDK wrapper.** A typed Python SDK's API classes already exist upstream. But SDK coverage lags the API by weeks to months, and typed methods cover a subset of the surface. Would create a hard dependency on SDK release cadence.

### Rationale

A custom generator gives full control over the CLI UX (output formatting, pagination, orgId injection) while keeping the API surface area as a "pull from spec" operation. The generator produces 172 command modules — one per OpenAPI tag — following a fixed template, and emits their registration manifest (`_registry.py`, ADR-9). When Cisco updates the spec, `tools/spec_sync.py` re-runs the whole pipeline. The `field_overrides.yaml` layer (ADR-7) handles spec quirks without modifying the generator core.

The hand-written exceptions exist because they require logic that a template cannot express:
- `cleanup.py` — 13-layer dependency ordering, parallel deletion, retry loops
- `converged_recordings_export.py` — file streaming, transcript extraction
- `cucm.py` / `cucm_config.py` — migration pipeline surface
- `configure.py` — config/auth (no REST)
- `update.py` — self-update via git pull

(2026-07-01 correction: `locations.py` and `numbers.py` were listed here as legacy
hand-written, but on-disk they are generator output — the 2026-07-01 spec sync
regenerated them byte-identical. 2026-07-02: `licenses.py`, the last legacy file,
was retired per S3.1 — flag-parity was exact and the generated update path was
live-verified with a reversible license assign/remove round-trip; `licenses` is
now generated, with a one-release `licenses-api` alias.)

### Consequences

**Enables:**
- 804 commands maintained with near-zero marginal cost per endpoint
- Consistent UX across all commands (same output flags, pagination, auth pattern)
- Spec updates produce updated commands in minutes
- Partner multi-org support (orgId injection) applied uniformly to 668 commands

**Forecloses:**
- Per-command UX customization (beyond what `field_overrides.yaml` allows)
- Complex request body handling — deeply nested objects fall through to `--json-body` escape hatch
- Hand-coded commands drift from generator improvements (no auto-inject, no auto-column detection)

**Gotchas:**
- ~~Registration is manual~~ Retired 2026-07-01: the generator emits
  `src/wxcli/commands/_registry.py` and `main.py` mounts it in a loop (ADR-9).
  A generated-but-unregistered module is structurally impossible.
- The `Endpoint`/`EndpointField` dataclass contract between parser and renderer is a stable interface that constrains both sides

### Status

**Active.** 172 generated modules (all manifest-registered), 6 hand-written files (none legacy — every hand file is chartered per A4-style criteria). Generator has been extended incrementally (output formatting, orgId injection, JSON body support, CC specs, registration manifest, name-collision guard) without a rewrite.

---

## ADR-2: Raw HTTP via REST Client vs. Typed SDK Methods

### Decision

Use synchronous `httpx` via a thin `WebexSession` wrapper for all CLI command HTTP calls, rather than a typed Python SDK's API methods (e.g., `api.telephony.auto_attendants.list(...)`). That typed-SDK dependency was subsequently removed entirely from `pyproject.toml`.

### Context

Cisco's official typed Python SDK provides typed methods with Pydantic models for a subset of the Webex API surface. However, the CLI needs to cover the *full* API surface — including endpoints the SDK hasn't implemented yet, Contact Center APIs on a different host, and recently-added endpoints. The SDK also imposes its own auth patterns, pagination logic, and error types that would compete with the CLI's own conventions.

### Alternatives Considered

1. **Typed SDK methods exclusively.** Strong typing, auto-completion, response models. But SDK coverage is incomplete — new endpoints take weeks/months to appear. Would create a hard dependency on SDK release cadence.
2. **Typed SDK for covered endpoints, raw HTTP for the rest.** Gradual migration path. But creates two code paths with different error handling, pagination, and auth — complexity without benefit since the generated command template already handles raw HTTP uniformly.
3. **Raw HTTP via `requests`.** Simpler library, widely known. But `httpx` provides HTTP/2 support, better async story, and is the modern standard.
4. **Raw HTTP via `aiohttp` everywhere.** Better concurrency. But CLI commands are inherently sequential (user waits for output); async adds complexity without benefit for the primary use case. (The migration engine uses `aiohttp` independently — see ADR-5.)

### Rationale

The REST client gives access to every endpoint from day one, whereas typed SDK methods lag behind the API by weeks to months. Using raw HTTP means one code path for all commands — generated and hand-written alike. The generated command template constructs URLs, injects parameters, and formats output without any SDK abstraction in between.

The `WebexSession` wrapper provides five verbs: `rest_get()`, `rest_post()`, `rest_put()`, `rest_patch()` (added 2026-07-01, with `content_type` support for JSON-Patch), `rest_delete()`, plus `follow_pagination()` for list commands — all sharing one bounded-retry request path. This thin surface is a stable interface every command module depends on.

### Consequences

**Enables:**
- Full API coverage on day one — any endpoint in the spec can become a command
- Single error handling path (`WebexError` from HTTP status codes)
- No dependency on SDK release cadence
- Clean `pyproject.toml` — only `typer`, `httpx`, `pyyaml` as runtime deps (for CLI commands)

**Forecloses:**
- Auto-pagination via SDK (must implement `follow_pagination()` ourselves)
- Response typing (all responses are `dict` — no IDE auto-completion on response fields)
- SDK's built-in rate limit handling (must implement retry logic ourselves)

**Gotchas:**
- Two independent HTTP stacks now exist: `httpx` (CLI commands) and `aiohttp` (migration engine). A breaking change in one doesn't affect the other, but bug fixes must be applied independently.
- The stale `requirements.txt` still references the removed typed-SDK package as a transitive dependency — needs cleanup.

### Status

**Active.** The typed-SDK dependency was removed from `pyproject.toml` (commit e4dfb22). All source files use `WebexSession` directly.

---

## ADR-3: SQLite-Backed Project Store for Migration

### Decision

Use a single SQLite database file per migration project as the persistence layer for all pipeline state — objects, cross-references, decisions, execution plans, and audit journals. Complement with a JSON state machine (`state.json`) for phase transitions.

### Context

The CUCM-to-Webex migration pipeline has 11 phases that may run across separate CLI invocations, potentially days apart. Each phase produces structured data that downstream phases consume. The pipeline must support resume/retry after failures, idempotent re-execution, and full audit trails. A typical migration processes hundreds to thousands of objects with complex cross-references.

### Alternatives Considered

1. **Flat JSON files (one per phase).** Simple, human-readable, easy to debug. But cross-phase queries (e.g., "find all decisions affecting objects in location X") require loading entire files into memory and implementing ad-hoc search. No transactional guarantees for partial failures.
2. **PostgreSQL/MySQL.** Full relational power, concurrent access, proven at scale. But requires a running database server — unacceptable for a CLI tool that should work on any laptop with zero infrastructure. Installation friction kills adoption for a tool targeting network engineers, not developers.
3. **In-memory only with JSON export.** Fast, simple. But loses state on crash, requires re-running all upstream phases. Unacceptable for a multi-hour migration pipeline.
4. **pickle/shelve.** Python-native persistence. But not queryable, version-fragile, no concurrency support, opaque to debugging.

### Rationale

*Inferred from code and constraints:* SQLite provides the sweet spot for a CLI tool: zero-config (just a file), ACID transactions (safe against partial failures), SQL queries (cross-phase lookups trivial), WAL mode (concurrent reads during long operations), and human-inspectable (any SQLite browser can examine state). A single `.db` file per project makes backup/copy/share trivial — hand someone the project directory and they have the full state.

The 7-table schema stores structured data as JSON blobs in TEXT columns (not normalized relational). This trades query power on nested fields for schema flexibility — CUCM objects vary wildly by type, and normalizing 38 canonical types into relational tables would create unmanageable schema complexity.

### Consequences

**Enables:**
- Resume/retry: re-running a phase picks up from last committed state
- Cross-phase queries: analyzers can query objects AND decisions in one SQL call
- Audit trail: journal table records every API call with request/response
- Portability: project directory is self-contained, zero external dependencies
- Concurrent reads: WAL mode allows reading state while a phase is writing

**Forecloses:**
- Distributed execution (SQLite is single-writer)
- Rich querying into JSON blob contents (requires loading and parsing in Python)
- Schema evolution is append-only (`ALTER TABLE ADD COLUMN`; tables never removed or renamed)

**Gotchas:**
- The `canonical_id` format (`"type:name"`) is a stable interface — planner, handlers, cross-refs all parse this prefix
- Decision fingerprints (`SHA256(type + context)`) are a stable interface — `merge_decisions()` depends on them for idempotency
- File locking can cause issues if multiple CLI invocations target the same project simultaneously

### Status

**Active.** 7 core tables, WAL mode, schema migrations via `ALTER TABLE ADD COLUMN`. The store is the single source of truth across all 11 pipeline phases.

---

## ADR-4: NetworkX DAG for Dependency Ordering

### Decision

Use NetworkX's `DiGraph` to model execution dependencies between migration operations, with 30 cross-object rules and 3 edge types (`REQUIRES`, `CONFIGURES`, `SOFT`). Use topological sort for execution ordering, level computation for parallelism, and cycle detection/breaking for safety.

### Alternatives Considered

1. **Inline topological sort (no library).** The mapper engine already uses a custom topological sort on `depends_on` fields. Could extend this pattern to execution planning. But the execution graph is significantly more complex: 30 cross-object rules, cycle detection needed, level computation for parallelism. Reimplementing these from scratch is error-prone.
2. **Static tier ordering only (no graph).** Assign each operation to a tier (0–8), execute tiers sequentially. Simpler, already partially implemented via `TIER_ASSIGNMENTS`. But misses intra-tier dependencies (e.g., hunt group forwarding depends on voicemail group creation, both at tier 4–5). Would require manual tier splitting that a graph handles automatically.
3. **Custom DAG implementation.** Full control, no external dependency. But NetworkX provides battle-tested cycle detection, topological sort, and graph algorithms. Reimplementing these correctly is non-trivial, especially cycle breaking.

### Rationale

*Inferred from code:* The execution plan has genuinely complex dependencies — 30 cross-object rules derived from the Webex API's resource model (devices depend on users, users depend on locations, features depend on both). These form a graph that can contain cycles (e.g., hunt group A forwards to call queue B which overflows to hunt group A). NetworkX provides the algorithmic primitives (cycle detection via `find_cycle()`, topological sort, level computation) that would be risky to reimplement.

The dual model — static tiers for coarse ordering PLUS intra-tier DAG for fine-grained dependencies — gives both human-readable structure (tier 0 = infrastructure, tier 2 = users, tier 4 = features) and correctness guarantees (no operation runs before its dependencies complete).

### Consequences

**Enables:**
- Automatic parallel execution of independent operations at the same tier/level
- Cycle detection with actionable error messages (shows the cycle path)
- Safe cycle breaking: `SOFT` edges can be broken, creating tier-7 fixup operations
- Cascade skip: when an operation fails, all hard-dependent operations automatically skip

**Forecloses:**
- Simple linear execution ordering (the graph adds complexity to debugging)
- Runtime modification of the graph during execution (it's built once at plan time)

**Gotchas:**
- `networkx` is NOT declared in `pyproject.toml` — it must be installed manually or added as a dependency. Clean installs fail at `import networkx` time.
- Tier assignments are a stable interface: changing a tier number can violate DAG edge constraints
- The 30 cross-object rules in `_CROSS_OBJECT_RULES` encode assumptions about the Webex API's resource model — if the API changes dependency requirements, rules must be updated manually

### Status

**Active.** Used in `execute/dependency.py` and `execute/batch.py`. Undeclared dependency issue documented in `01-structural-map.md` §5 as a known gap.

---

## ADR-5: Async Execution Engine with Configurable Concurrency

### Decision

Implement the migration execution engine as an async `aiohttp`-based executor with semaphore-gated concurrency (default 20), separate from the synchronous `httpx`-based CLI commands. Execute operations in tier-then-DAG order, with 429 retry, 409 auto-recovery, and cascade skip on failure.

### Context

Migration execution must create hundreds to thousands of Webex resources (users, devices, features, routing) via API calls. Sequential execution would take hours. But the Webex API has per-org rate limits (~300 req/min typical), and resources have dependency ordering that prevents fully parallel execution. The engine must balance throughput against rate limits while respecting the dependency graph.

### Alternatives Considered

1. **Synchronous sequential execution.** Simplest implementation — just loop through operations in topological order. Safe and debuggable. But at 1000+ operations with API latency of 200–500ms each, a full migration would take 30+ minutes even without rate limiting. Unacceptable for operator experience.
2. **`ThreadPoolExecutor` with synchronous HTTP.** Already used in `cleanup.py`. Familiar, works with existing `WebexSession`. But thread-based concurrency at 20+ workers creates contention on the GIL-bound JSON parsing, and thread stacks consume memory. Also harder to implement cooperative rate limiting (threads can't easily yield on 429).
3. **Extend `WebexSession` with async support.** Single HTTP client for everything. But would require rewriting 208 generated command files to handle both sync and async patterns, adding complexity to the generator for no benefit (CLI commands don't need async).
4. **External job queue (Celery, RQ).** Battle-tested distributed execution. But requires Redis/RabbitMQ infrastructure — unacceptable for a CLI tool (same objection as PostgreSQL in ADR-3).

### Rationale

*Inferred from code and the two-HTTP-stacks seam documented in 01-structural-map.md:* Async `aiohttp` with a semaphore is the natural fit for I/O-bound bulk API calls: cooperative multitasking means 429 responses can pause one coroutine without blocking others, the semaphore provides precise concurrency control, and `asyncio.gather()` parallelizes independent operations within a tier/batch naturally.

Keeping this as a completely separate HTTP stack from the CLI commands isolates complexity: the migration engine can implement retry, auto-recovery, audit logging, and cascade logic without affecting the simple request-response pattern of CLI commands. "A breaking change in one doesn't affect the other."

### Consequences

**Enables:**
- 20x throughput improvement over sequential execution
- Cooperative rate limiting: 429 responses pause the affected coroutine while others continue
- 409 auto-recovery: search for existing resource by name/email (supported for 7 resource types), use existing ID instead of failing
- Cascade skip: failed hard-dependency operations automatically skip all dependents
- Cascade undo: if a retried operation succeeds, cascade-skipped dependents reset to `pending`
- Configurable via `--concurrency` flag: operators can tune based on org rate limits

**Forecloses:**
- Shared error handling between CLI and migration (different error types: `WebexError` vs aiohttp exceptions)
- Shared auth/session management (migration engine manages its own token lifecycle)
- Simple debugging (async stack traces are harder to read than sync)

**Gotchas:**
- `aiohttp` is NOT declared in `pyproject.toml` — installed transitively via stale `wxc-sdk` in the environment
- The 10-minute Bash tool timeout in Claude Code can kill long-running executions — documented in CLAUDE.md's "Long-Running Work" protocol
- Bulk job operations (100+ devices) switch from per-resource calls to Webex bulk job submission with polling — a different execution path within the same engine

### Status

**Active.** Default concurrency 20, configurable via CLI. 429 retry (5 attempts with Retry-After), 409 auto-recovery (7 resource types), cascade skip/undo. Batch execution respects both tier ordering and DAG edges.

---

## ADR-6: Pipeline Split — Normalizers, Mappers, Analyzers, Advisors

### Decision

Decompose the CUCM-to-Webex transformation into four distinct layers with well-defined interfaces:
- **Normalizers** (42 functions): raw CUCM dicts → canonical Pydantic models (stateless, parallel-safe)
- **Mappers** (26 classes): canonical CUCM objects → Webex target objects + decisions (topological order)
- **Analyzers** (14 classes): sweep mapped objects for conflicts → produce decisions with fingerprints
- **Advisors** (36 patterns + 25 rules): cross-cutting architectural analysis → recommendations

Further split normalization into two passes: Pass 1 (object creation, stateless) and Pass 2 (cross-reference building, requires full inventory).

### Context

A CUCM environment contains deeply interdependent objects: users own devices, devices have lines, lines belong to partitions, partitions compose into calling search spaces, hunt groups reference users, etc. Transforming this into Webex Calling's flatter model requires understanding relationships, detecting conflicts, making judgment calls about lossy mappings, and explaining recommendations to operators. A monolithic transformer would be untestable and unmaintainable at this scale.

### Alternatives Considered

1. **Single-pass transform (CUCM object → Webex object directly).** Simplest conceptually. But CUCM objects reference each other by name — resolving these references requires the full inventory in memory. Also conflates "what is this?" (normalization) with "what should it become?" (mapping) with "is there a problem?" (analysis). Testing and debugging each concern independently becomes impossible.
2. **Two-layer model (normalize + execute).** Merge mapping and analysis into a single "plan" step. Simpler pipeline. But mapping produces objects AND decisions (conflicts), while analysis only produces decisions. Merging them makes it impossible to re-run analysis independently (e.g., after resolving some decisions and wanting to see cascading effects).
3. **Event-sourced pipeline.** Each transformation emits events, downstream consumers react. Maximum decoupling. But overkill for a batch pipeline — adds infrastructure complexity (event store, replay logic) for a tool that processes data in a known sequence.
4. **No advisor layer (analysis only).** Let analyzers produce all decisions, skip the cross-cutting advisory step. Simpler. But individual analyzers can only see their own domain — they miss cross-cutting patterns (e.g., "this migration has 15 shared lines AND 30 incompatible devices AND a complex CSS structure — the combination suggests a phased migration approach"). The advisor layer detects patterns that emerge from the totality of decisions.

### Rationale

*Inferred from code structure and the two-pass normalization documented in 01-structural-map.md:*

The four-layer split maps to four distinct concerns:
1. **Normalizers** answer: "What does this CUCM object mean in canonical terms?" Pure functions, no cross-references, parallelizable. Testable in isolation with a single raw dict as input.
2. **Mappers** answer: "What Webex resource should this become, and what decisions arise?" Can query cross-references (Pass 2 output). Ordered by `depends_on` (e.g., location mapper must run before user mapper). Produce both objects and decisions.
3. **Analyzers** answer: "Looking at the full mapped inventory, what conflicts exist?" Linter-pattern: independent sweeps, each produces decisions with fingerprints for idempotency. Can be added/removed without affecting others.
4. **Advisors** answer: "Looking at all decisions together, what cross-cutting patterns emerge?" Runs after merge, sees the full decision landscape. Produces `ARCHITECTURE_ADVISORY` decisions that the Opus migration-advisor agent expands during interactive review.

The two-pass normalization split exists because Pass 1 must be parallel-safe (no dependencies between normalizers) while Pass 2 (cross-reference building) needs the full inventory loaded into the store to resolve relationships.

### Consequences

**Enables:**
- Each layer is independently testable (2,778 tests total)
- Re-runnable phases: re-run analysis after resolving decisions to see cascade effects
- Pluggable: add a new normalizer/mapper/analyzer without touching others
- Clear debugging: "is this a normalization bug, a mapping bug, or an analysis bug?"
- Advisor layer enables AI-assisted review without coupling it to deterministic analysis

**Forecloses:**
- Early cross-reference resolution (normalizers can't look up related objects)
- Streaming/incremental processing (each phase must complete before the next starts)
- Direct feedback loops (an analyzer can't ask a mapper to re-map based on a conflict)

**Gotchas:**
- The `depends_on` declarations on mappers are a manual coordination mechanism — adding a new mapper requires understanding existing dependency chains
- The fingerprint-based decision merge in analysis is critical for idempotency but opaque — if the fingerprint algorithm changes, all existing decisions in SQLite become unmatchable
- Advisory patterns tend toward generic recommendations ("accept approximation") — the Opus layer via the migration-advisor agent adds the judgment that static patterns lack

### Status

**Active.** 42 normalizers, 26 mappers, 14 analyzers, 36 advisory patterns, 25 recommendation rules. The pipeline was built bottom-up over ~2 weeks (store → discovery → normalization → mapping → analysis → planning → execution), with each layer's tests written alongside the implementation.

---

## ADR-7: The `field_overrides.yaml` Pattern

### Decision

Maintain a YAML configuration file (`tools/field_overrides.yaml`) that customizes generated command output without modifying the OpenAPI specs, the parser, or the renderer. Overrides control: table columns, command name mappings, response list keys, parameters to skip/auto-inject, tag merging, and body defaults.

### Context

OpenAPI specs are maintained by Cisco and periodically updated. They contain inconsistencies: non-standard response wrapper keys, confusing parameter names, missing defaults, split tags that should be one group (e.g., "User Call Settings (1/2)" and "(2/2)"), and enum values that differ between spec versions. The generator needs to handle these quirks, but modifying the specs directly would create merge conflicts on every update, and encoding fixes in the parser would make it spec-version-dependent.

### Alternatives Considered

1. **Fork and patch the specs.** Direct fix at the source. But Cisco publishes spec updates regularly — maintaining a patched fork creates ongoing merge conflicts. The patches would also be opaque (a patched spec looks identical to an unpatched one; you can't tell what was changed).
2. **Encode fixes in the parser/renderer.** Conditional logic for specific tags/endpoints. But this couples the generator to specific API versions — a parser that special-cases "User Call Settings" breaks when Cisco renames it. Also makes the parser increasingly complex over time.
3. **Post-process generated Python files.** Run a fixer script on generated output. But modifying generated code makes re-generation destructive (loses manual fixes). The "never touch generated files" principle breaks.
4. **No overrides — accept spec quirks.** Users deal with non-standard output formats, confusing names, etc. Simplest for maintainers. But unacceptable UX: table output with wrong columns, commands with unintuitive names, auto-complete showing internal IDs.

### Rationale

*Inferred from the generation pipeline structure:* The override file sits between parsing and rendering — it's applied to `Endpoint` objects before they're rendered to Python. This means:
- Specs can be updated from upstream without conflicts (overrides re-apply automatically)
- The parser stays generic (no spec-version conditionals)
- The renderer stays template-driven (no special-case logic)
- Fixes are explicit and auditable (diff the YAML to see what's customized)
- New quirks are fixed by adding a YAML entry, not modifying code

The override categories map to specific UX problems:
- `table_columns`: "which fields should `list` commands show?"
- `command_name_overrides`: "this operationId is confusing — rename it"
- `response_list_keys`: "the response wraps items in a non-standard key"
- `auto_inject_from_config`: "inject orgId from config, hide from --help"
- `tag_merge`: "merge split tags into one command group"
- `skip_tags`: "don't generate commands for this tag"

### Consequences

**Enables:**
- Spec updates without merge conflicts — re-run generator, overrides re-apply
- Per-tag customization without touching shared code
- Explicit audit trail of all customizations (one YAML file, diffable)
- Iterative improvement: discover a new quirk → add one YAML entry → re-generate

**Forecloses:**
- Structural changes to command logic (overrides only adjust display/naming, not behavior)
- Per-endpoint override granularity below the tag level (overrides are per-tag, not per-command, for most settings)

**Gotchas:**
- Overrides are fragile on spec restructuring: if Cisco renames a tag or changes a response key, the override entry becomes orphaned (silently ignored). No validation against the current spec.
- The file grows monotonically — ~750 lines currently. No mechanism to prune overrides that are no longer needed.
- `table_columns` use dot-notation accessors (`"field.subfield"`) — if the response structure changes, columns break silently (show empty values).

### Status

**Active.** ~750 lines covering all 173 command groups. Grows as new API spec bugs are discovered during live testing. Introduced after the generator was mature (commit f2e3a4b), not as part of the initial design.

---

## ADR-8: Claude Code Playbook Structure (Builder Agent + Skills + Reference Docs)

### Decision

Structure the Claude Code integration as a three-layer system:
1. **Builder agent** (`wxc-calling-builder.md`): orchestrates interactive sessions, detects intent, interviews the user, delegates to skills
2. **Domain skills** (26 total in `.claude/skills/`): encode step-by-step procedures for specific Webex Calling domains (provisioning, routing, devices, features, etc.)
3. **Reference docs** (46 in `docs/reference/`): grounded API documentation that agents and skills consult at runtime

Operate the builder agent in a **phase-per-invocation** pattern: spawn a fresh agent for each major workflow phase rather than maintaining a single long-running conversation.

### Context

Webex Calling configuration is complex: 173 API command groups, dozens of interdependent features, multiple auth types, partner/multi-org scenarios, and a 2,778-test migration pipeline. A Claude Code user facing this surface area needs guided assistance — not just raw CLI access. But encoding all domain knowledge in a single prompt would exceed context windows, and a single long-running agent loses context on complex multi-phase workflows.

### Alternatives Considered

1. **Single monolithic agent prompt.** Put everything in one large agent definition. Simple to maintain. But exceeds practical context windows — the builder agent's base context is already ~40k tokens. Adding all skill knowledge would push past limits and degrade response quality.
2. **No agent — just CLAUDE.md instructions.** Let the user drive, CLAUDE.md provides reference. Lower overhead. But Webex Calling has too many non-obvious workflows (e.g., "you must enable calling on a location before assigning users" or "Customer Assist queues are hidden from default list commands"). Without guided procedures, users hit errors that require deep API knowledge to debug.
3. **Single long-running agent for entire workflows.** Start once, do everything. Avoids context loss between phases. But complex migrations can span 11 phases over multiple sessions — no context window can hold the full state. Also, a single agent accumulating tokens becomes expensive and slow.
4. **Skills without an orchestrating agent.** Users invoke skills directly (e.g., `/provision-calling`). Maximum user control. But loses the interview/intent-detection layer — users must know which skill to invoke, which requires understanding the domain structure they're trying to learn.

### Rationale

*Documented explicitly in CLAUDE.md:* The three-layer decomposition maps to three concerns:
- **Builder agent** = interaction design (interview, intent detection, error recovery)
- **Skills** = procedural knowledge (step-by-step for each domain)
- **Reference docs** = factual knowledge (API surface, gotchas, examples)

The phase-per-invocation pattern exists because "each major phase runs as a fresh agent invocation — do NOT resume agents via SendMessage for multi-phase workflows." This prevents context exhaustion and allows each phase to start with a clean, focused context. State persistence happens via the filesystem (SQLite store for migration, config files for provisioning), not via agent memory.

The mandatory grounding rule ("Never answer any question about Webex Calling from training data alone") exists because "product tiers get conflated, feature names change, and capabilities vary by license." Reference docs are the authoritative source; training data about Cisco products is unreliable.

### Consequences

**Enables:**
- Complex multi-phase workflows (CUCM migration, org health audit) without context exhaustion
- Domain expertise scales by adding skills without modifying the builder agent
- Reference docs can be updated independently of skills (API changes don't require skill rewrites if the procedure is unchanged)
- Different agent model selection per task complexity (Haiku for cleanup, Sonnet for standard, Opus for migration advisory)
- Interactive decision review via the migration-advisor agent (Opus-level reasoning on cross-cutting patterns)

**Forecloses:**
- Seamless multi-phase continuity (each phase starts fresh — must pass context explicitly)
- Skill composition (skills don't invoke other skills; the builder agent orchestrates)
- Offline operation (skills and reference docs assume live API access)

**Gotchas:**
- Skills encode assumptions about command names and flags — when a command changes, the corresponding skill must be checked
- The builder agent has a blocking org confirmation step for partner tokens that can confuse users on single-org accounts
- The phase-per-invocation pattern requires the parent to pass state context explicitly in the spawn prompt — if context is omitted, the fresh agent starts blind
- Agent model selection matters: "Never use Haiku for implementation subagents — it misses details and produces rework" (from memory/feedback)

### Status

**Active.** 2 agents, 26 skills, 46 reference docs. The structure grew incrementally as new Webex Calling domains were covered by the CLI. Skills are the primary interface for all operations — the CLAUDE.md "Quick Start" section routes everything through the builder agent or specific skills.

---

## ADR-9: Atomic Spec Sync, Generator-Owned Registration, and the Drift Gate

### Decision

Treat "spec refresh → regeneration → registration → coherence check" as one atomic operation (`tools/spec_sync.py`, landed as a single commit), make the generator own registration end-to-end (`src/wxcli/commands/_registry.py` manifest mounted by a loop in `main.py`), and enforce coherence mechanically via `tools/drift_check.py` (spec↔CLI parity, skill/doc reference existence, published counts, unreferenced-groups-vs-declared-list).

### Context

The 2026-07-01 coherence audit (docs/arch/) found: specs refreshed twice without regeneration (57 stale ops, 13 CLI-ahead commands), 34 orphaned generated modules that were never registered (manual-registration seam), ~45 dead command references across 14 skills, and stale published counts. All four failure modes were process gaps, not code bugs.

### Rationale

- One atomic sync makes "specs updated, regen forgotten" impossible to commit silently.
- A generator-emitted manifest makes "generated but unregistered" structurally impossible; a stale manifest entry fails import loudly at startup instead of silently at runtime. Explicit literal `(module, group)` lines keep it greppable (adversarial critique R2).
- Dev-only specs (flow-store) are excluded from the manifest (`--dev-only`, auto-detected) so local regens can't break fresh clones (critique R9a). *Superseded 2026-10-13 by ADR-11: the flow-store spec and its `fs-*` groups were retired, and `--dev-only` was removed with them.*
- Deliberate gaps (skip_tags, multipart uploads, untagged ops, keep_endpoints) are emitted to `docs/arch/deliberate-gaps.md` so "no CLI" is always classifiable as deliberate vs drift.

### Consequences

**Enables:** drift is a CI failure, not an archaeology project; the skills layer can be held to "only teach what the built CLI resolves".
**Forecloses:** hand-editing registration; keeping CLI-ahead commands without a recorded `keep_endpoints` decision (regen rebuilds modules wholesale from the spec).
**Gotchas:** spec churn can silently rename commands when new ops win name races within a tag — pin operator-facing names with `tag_overrides` `command_name_overrides` (see the call-queue show/update case, 2026-07-01); the reference gate (check 2) validates names, not argument semantics.

### Status

**Active** since 2026-07-01. Gate is report-only; flips to enforcing at refactor-plan S4.5.

---

## ADR-10: PyPI Distribution; Git-Pull Update Retired

### Decision

Distribute wxcli as a versioned package on **public PyPI**, built and published by a `release: published`-triggered GitHub Actions workflow using **Trusted Publishing (OIDC)**, with wheel + sdist also attached to each GitHub Release. `wxcli update` checks the PyPI JSON API and upgrades in place via pipx/pip; the git-pull update model is retired for managed installs but retained for source/dev (editable) checkouts. The first real release, **v1.2.0**, doubles as the migration bridge.

### Context

Install was `git clone && pip install -e .`; the working tree **was** the running CLI, and `wxcli update` ran `git pull origin main` → `pip install -e .`. Any edit to a checkout file changed CLI behavior, updating required git literacy and a clean tree, and there was no release artifact — `origin/main` was the shipped state at all times. Unsafe for non-developer end users.

### Rationale

- Public PyPI gives the simplest end-user path (`pipx install wxcli`) and reliable enterprise reach.
- Trusted Publishing needs no stored secret; a *pending publisher* bootstraps the brand-new name.
- A PyPI-JSON version check + in-place pipx/pip upgrade removes all git operations from end-user machines.
- Opt-in `--migrate` makes the cutover explicit and safe; no one is stranded — the old git-pull path keeps working until the user chooses to migrate.
- The repo clone is retained (not removed) because it delivers the Claude Code playbook; PyPI distribution is CLI-only.

### Consequences

**Enables:** safe distribution to non-developers; in-place upgrades; release notes + artifact + PyPI tied to one `release: published` event.
**Forecloses:** "the checkout is the product" (edits silently changing behavior); shipping straight off `origin/main` with no artifact.
**Gotchas:** setuptools-scm needs `fetch-depth: 0` **and** the version guard, or CI publishes a dirty (`.dev`/`+local`) version — the one classic footgun. Enterprise networks blocking PyPI use `WXCLI_UPDATE_INDEX_URL`.

### Status

**Active** since 2026-07-06 (implementation). First bridge release: v1.2.0.

---

## ADR-11: Retire the WxCC Flow Store CLI (`fs-*`); Delete Its Spec

### Decision

Remove the 11 Flow Store command groups (`fs-flows`, `fs-resources`, `fs-templates`, `fs-tracing`, `fs-flows-v2`, `fs-user-prefs`, `fs-connectors`, `fs-expression-test`, `fs-flow-props`, `fs-flow-versions`, `fs-projects`) and **delete** `specs/webex-flow-store.json`, together with every piece of machinery that existed only for them: the `FS_DEV_GROUPS` mount in `_lazy.py`, the `get_fs_base_url` / `get_fs_project_id` / `save_fs_datacenter` / `FS_DATACENTERS` config helpers, the generator's `--dev-only` flag and flow-store base-URL branch, the renderer's `BASE_URL_FS` path, the drift gate's `FS_MODULES` audit, and the spec's `field_overrides.yaml` sections. The supported flow surface is `cc-flow` (plus `cc-legacy-flows` export) on the Contact Center API host; neither is touched.

### Context

Verified live 2026-10-13: the CLI's default Flow Store host, `flow-store.intgus1.ciscoccservice.com`, is Cisco's **integration** environment and returns 401 `FAIL_VALIDATE_TOKEN` for production tokens; the alternative `flow-store.us1.ciscoccservice.com` does not resolve in DNS. The groups were old, could not work against a customer org, and must not be exposed. They were already gitignored and absent from the shipped wheel, but any source checkout holding the local spec and modules mounted all 11 in `wxcli --help`.

The weekly spec-sync never touched this spec — `update-specs.py` does not download it and `spec_sync.py` regenerates only git-tracked specs — so the realistic way back is a local copy, not the cloud routine.

### Alternatives Considered

- **Keep the spec on disk but stop generating from it** (a skip list or exclusion in the generator). *Rejected:* it keeps the file plus new exclusion code that must be maintained forever, all to preserve a surface that cannot be used. More machinery, same outcome.
- **Delete the spec, chosen.** No new code. The guard already exists: `command_renderer.SPEC_PRODUCT` must name every spec on disk or `build_producer_index` raises `UnknownSpecProductError`, and every regen builds that index. Leaving `webex-flow-store.json` *out* of `SPEC_PRODUCT` (it used to map to `None`) turns that existing check into the tripwire: a copy dropped back into `specs/` fails every regen and `tests/test_command_naming_residue.py`. Mutation-proven on 2026-10-13 (planted spec → regen raised, 4 tests failed; removed → green).

### Rationale

- Least machinery: removal plus one deleted dict entry; no allow/deny lists to rot.
- `.gitignore` keeps both patterns (`specs/webex-flow-store.json`, `src/wxcli/commands/fs_*.py`) so a stale local copy can never be committed or counted, and the CLI no longer contains any code that would mount one.
- The CC spec's own `/flow-store/...` tags (`Activities`, `Templates`, `Events`) remain in `skip_tags`, so spec-sync cannot reintroduce the surface through the tracked CC spec either.
- `cc-legacy-flows` was checked and is unaffected: it calls `{cc_base_url}/flow-store/...:export` on the Contact Center host via `get_cc_base_url`, never the Flow Store host or `get_fs_*`.

### Consequences

**Enables:** no unusable groups in `wxcli --help`; one fewer special case in the generator, renderer, config and drift gate.
**Forecloses:** using the Flow Store API from wxcli. Reviving it needs a new decision, a production-reachable host, and a `SPEC_PRODUCT` entry — not a revert of the mount.
**Gotchas:** source checkouts that still hold the old untracked files must delete them by hand (`specs/webex-flow-store.json`, `src/wxcli/commands/fs_*.py`); until then the spec makes every regen raise, by design. Published group counts do not change — the `fs-*` groups were never counted.

### Amendment, 2026-10-13 — the activity catalog is carved out

**What changed.** Of the three Flow Store tags embedded in the tracked CC spec, `Activities` (3 ops) and `Events` (1 op) are no longer skipped; they render into `cc-flow` through a per-spec `tag_merge` (`Flows` ← `Activities`, `Events`). `Templates` (2 ops) stays in `skip_tags`. New commands: `cc-flow list-activities`, `show-activity`, `list-activity-choices`, `list-event-specifications`.

**Why the retirement reasoning does not apply to them.** ADR-11 retired a surface that *could not work*: the Flow Store host rejects production tokens. These four operations are not on that host. Their spec paths (`/{orgId}/project/{projectId}/v2/activities…`, `…/v2/event-specifications`) resolve against the Contact Center API host, and all four returned 200 with a production full-admin token, read-only, on 2026-10-13 (54 activities; `show-activity queue-contact` with 16 inputs; `list-activity-choices … queue-contact channelType` → 4 choices, `… destination --parent-input-name channelType --parent-value TELEPHONY` → 11 queues; 20 event specifications). They are the catalog a flow author needs, which is why they belong in `cc-flow` rather than in a group of their own. `…/v2/activities/{name}/schema` 404s live, and it is not in the spec.

**Alternatives considered.**
- *An operation-level allowlist inside the generator.* Rejected: drift check 1, the gaps doc and the check-19 snapshot all read the spec's raw `tags[0]` against `skip_tags`, so a per-operation carve-out would need the same rule taught to four places. The tag merge is already understood by all of them.
- *Leave them skipped.* Rejected: the skip was justified by an unreachable host, and that justification is false for these four.

**How the narrowness is kept.** A whole-tag merge would silently absorb anything Cisco adds to these two tags. `tests/test_generate_commands.py::TestActivityCatalogCarveOut` pins the exact operationIds each tag carries, so an addition fails CI and forces a read-only live check first. Their paths sort before `/flows`, so unpinned they would have taken the bare `list`/`show` from the flow commands; `tag_overrides` → `Flows` → `command_name_overrides` swaps the names back (measured with `--dry-run` before regenerating; check 22: 0 moved, 4 locked).

### Status

**Active** since 2026-10-13. Supersedes ADR-9's dev-only-spec bullet. Amended the same day (activity-catalog carve-out, above). **Amended by ADR-19 (2026-10-19):** the Flow Store returns as eight `cc-*` groups from `flow-store.produs1.ciscoccservice.com`; the `fs-*` groups and `webex-flow-store.json` stay retired.

---

## ADR-12: `--limit` / `--offset` Stay on Every List Command and Are Translated on Page-Numbered Endpoints

### Decision

Keep `--limit` and `--offset` on all list commands, including the 105 page-numbered ones (measured on the regenerated tree, 2026-10-13: Contact Center `page`/`pageSize`, the Flows `page`/`size`, and `/v1/tasks`, which declares only `pageSize`). On those commands the generator no longer sends them as `max`/`start`: `--limit N` is sent as the endpoint's own page-size parameter (unless the explicit page-size flag is given, and never with `--all`), and `--offset N` is served by a runtime helper, `WebexSession.fetch_from_offset`, that returns records N … N+count **record-exactly** — page `N // size`, skip `N % size`, continue onto the next page when the window spans two. The truncation note names `--offset <absolute next record>` on every command, page-numbered or not. *(Narrowed by ADR-18: only where `--offset` is offered and not measured to be ignored.)*

### Context

Verified live 2026-10-13 on the sandbox tenant: `cc-queue list --limit 2` sent `?max=2` and returned 17 records; `cc-flow list --offset 10` sent `start=10` and returned page 0 again. Both exit 0 — a wrong answer delivered confidently. The previous fix had pointed the truncation note at `--page N` instead, but `cc-tasks list` has no `--page` flag (its spec declares `pageSize` only, although the server pages by `page` and says so in a `Link` header), so the note named a flag that does not exist there.

### Alternatives Considered

- **Stop offering `--offset`/`--limit` on page-numbered commands.** *Rejected:* it breaks the uniform-flag rule the renderer already applies to `--all` and `--output` ("an option present on most commands but not all teaches a rule that breaks unpredictably, which costs an agent a failed call plus a `--help` round trip each time"). An agent that learned `--offset` on `people list` would get "No such option" on `cc-queue list`.
- **Keep them and refuse loudly (exit 2, "use --page").** *Rejected:* the flag would still be present but never work, `cc-tasks` has no `--page` to point at, and the translation is cheap.
- **Translate `--offset` to `page = N // size` only when N is a multiple of the page size.** *Rejected:* half-working; the note would have to know the page size the user will pass next time.
- **Translate record-exactly, chosen.** At most one extra request when the window straddles a page boundary, plus one look-ahead record when the body declares no total (`/v1/tasks`). A server that caps the page size below the one asked for is detected (short page, declared total says more) and re-planned once with the size it actually serves.

### Rationale

- `--offset N` now means the same thing on every list command: skip N records. The note's remedy is the same flag everywhere.
- `--limit N` now means the same thing everywhere: at most N records fetched — on link endpoints that was already `max`, the page size.
- `--page`/`--page-size` stay as the endpoint's own controls; an explicit `--page-size` wins over `--limit`, and `--offset` overrides `--page`.

### Consequences

**Enables:** one paging vocabulary across all 543 list commands; `cc-tasks list --offset` reaches page 2 although the command has no `--page`.
**Forecloses:** nothing — the native flags are untouched.
**Gotchas:** the default window when neither `--limit` nor a page size is given is 100 (`DEFAULT_OFFSET_WINDOW`, the declared default of 94 of the 113 CC page-size parameters). CC bulk-export bodies carry a `pageNumber` that does **not** track the page served (live: page=0 → 1, page=1 → 2, page=2 → 2), so the note reads their `rel` (`next`/`last`) and takes the page index from the request, never from `pageNumber`. Unit-tested in `tests/test_pagination_walkers.py::TestFetchFromOffset` against a fake server that, like CC, ignores `start`/`max`.

### Status

**Active** since 2026-10-13 (uncommitted at time of writing). Live-verified read-only: `cc-flow list --offset 25 --limit 10` = flows 25–34 of the `--all` order; `cc-queue list --offset 15 --limit 5` = queues 15–16 of 17; `cc-tasks list --offset 100 --limit 5` = tasks 100–104 of 226; `cc-global-vars list --offset 4 --limit 4` = 4 of 9 with the note naming `--offset 8`.

---

## ADR-13: Eight Gated Static Drift Checks (23-30) for the Bug Classes Found Live on 2026-10-13

### Decision

Add eight gated checks, numbered 23-30, to `tools/drift_check.py`. The weekly spec-sync routine already runs `python3 -m tools.drift_check --enforce` in its pass bar (`docs/spec-sync-contract.md` §4), so every new check runs weekly with no change to the routine. On a hit the routine **fails closed**: it commits nothing, and the liveness workflow opens a `spec-sync` issue. For checks 23-28 it never repairs, because the fixes live in generator code or override keys, which `tools/sync_guard.py` keeps out of an unattended job (`FORBIDDEN_PATHS`, `yaml_key_findings`). For the doc checks 29/30 it may spend its §4 repair attempts on a finding ONLY when the finding's `file:line` is inside a pure-addition hunk of `git diff origin/main -- <file>` — a hunk whose changed lines are all `+`, with no `-` line — i.e. text this run wrote fresh for new-group coverage (§2 B/C). A `+` line that shares a hunk with a `-` line is an edited pre-existing line and does NOT qualify, even if this run made that edit earlier. Otherwise it fails closed for a human. The spec is often wrong against live behaviour (2026-10-13: the FlowV2 import shape; `cc-dial-number create` needing `location`/`regionId` the spec calls optional), so an unattended edit of an existing doc "to match the spec" could silently replace a live-verified example (contract §6).

| # | Detects | 2026-10-13 instance |
|---|---|---|
| 23 | `--offset`/`--limit` written to a query param the spec op does not declare, where the op declares its own name for that concept (and no `fetch_from_offset`) | 105 CC list commands sent `start`/`max` to page-numbered endpoints |
| 24 | a page walker whose page/size param name the spec op does not declare, where it declares another | `cc-flow list --all` walked with `pageSize`; the op takes `size` |
| 25 | a GET on a single resource (`…/{id}` or `…/{id}:<action>`) rendered through the list extractor, dropping a declared field | `cc-flow export`, `list-validate`, `cc-legacy-flows list` |
| 26 | a CC-host command that sends `orgId` from `get_org_id()` (base64) instead of `get_cc_org_id()` | 14 commands in 6 CC analytics modules → 401 |
| 27 | a list command whose extractor key chain reaches none of the 200 response's array properties (any media type, incl. `*/*`), or whose response is one object with no array | 7 bulk-export lists printed 0 rows (`resources`) |
| 28 | a group help label naming a product other than the owning spec's `SPEC_PRODUCT` | `asset`/`channel` labelled "Webex Calling" |
| 29 | a documented flag or `--json-body` value whose type contradicts the spec | `cc-agents list-activities --from "2026-03-01T00:00:00Z"` |
| 30 | a documented `--json-body` whose top-level keys are not properties of the op's closed request schema | `cc-captures create` `{from,to,filters}`; `cc-dial-number create` `dialNumber` |

The same work moved checks 6, 10, 11a and 11b off the first `@app.command` decorator onto every decorator name, and made check 9 label its findings by the visible name. On the ~102 renamed commands the first decorator is the hidden alias, so documented calls of the visible name had never been checked.

### Context

A live session on 2026-10-13 (commits `e5e85fe`, `dc91c40`) found about 15 defects in the Contact Center surface. All of them predate the weekly routine (live since 2026-09-09), and the oldest date to 2026-03-28. The routine missed them by design. It never calls the live API (contract §3), it only writes docs for *new* groups, it may not edit the generator, and it runs on a clean clone, so gitignored local files never reach it. About half the defects can be detected **statically**, from the specs, the rendered command modules and the docs. Those became gated checks.

### Alternatives Considered

- **Let the routine repair these.** *Rejected:* the repairs live in the generator, and an unattended generator edit is how a bad release ships.
- **Live verification inside the cloud routine.** *Rejected for now:* PATs expire in 12 h, so it would need a long-lived Service App credential stored in the routine. Adam's call, later.
- **Advisory (non-gating) checks.** *Rejected:* an advisory line in an unattended log is read by no one, and each rule here is mechanical, not a judgement call.
- **An ack / allowlist key per check.** *Rejected:* an escape hatch the unattended routine could reach would defeat the point. A finding at HEAD is either a true positive (fix the doc, or fix the generator and regen) or a false positive (tighten the rule).

### Rationale

- **Every check is gated and has no exemption key.** Where a literal rule produced false positives at HEAD, the rule was tightened, with tests on both sides, rather than acked. Check 23's literal form reported 594 at HEAD; check 24's flagged `cc-tasks list`, which works live; check 30's first run had 7 false positives (5 where the spec's own request example contradicts its schema, 1 "Patchable fields:" list, 1 catch-all `JsonValue` body).
- **A blind check fails.** Each check records what it examined (`record_examined` → `CHECK_EXAMINED`) and prints `(examined N …, skipped K)` beside its count. A run that examined nothing produces a gated `BLIND` finding, not a quiet 0. What the shared readers could not parse (`HELPER_SKIPS`, summed by `helper_skip_count`) is counted as skipped. `print_check_findings` (via the `CHECK_PRINT` registry) never raises: a formatter error prints `FORMAT-ERROR <repr>`, because a crash exits 2 and fails the routine. `tests/test_drift_check_static_helpers.py::test_live_tree_helpers_are_not_blind` is the tripwire for the shared block parser. Each check's live-tree test asserts only a loose examined floor, so it catches blindness, not a regression.
- **New upstream input never crashes a check.** A spec missing from `SPEC_PRODUCT`, an odd schema or an unreadable module is skipped and counted. The checks are static only: no network, no `import wxcli`, and no syntax newer than Python 3.11 (the cloud interpreter).

### Proof — each check is 0 at HEAD and fires on the pre-fix tree

HEAD is this branch's final tree, measured with `--enforce`. "Pre-fix" is the same check code run against a worktree of `1fa94dc` (the tree before the 2026-10-13 fixes, at `/tmp/dc-pre`), by pointing the module's `REPO`/`SPECS_DIR`/`COMMANDS_DIR`/`MAIN_PY` at it. The pre-fix proof is a manual step: no test references that tree, git or `1fa94dc`, so the suite passes in a clean clone.

| Check | HEAD (examined) | Pre-fix (examined) | Named pre-fix instances |
|---|---|---|---|
| 23 | 0 (540 list cmds) | **220** (545) | 105 CC page-numbered lists + 5 SCIM-style lists: `cc-queue list` (`--offset`→`start`, `--limit`→`max`), `cc-queue list-incoming-references`, `asset list-asset`, `cc-address-book list`, `cc-tasks list` (`--offset`→`start`) |
| 24 | 0 (110 walkers) | **2** (110) | `cc-flow list`, `cc-flow list-search` (walked with `pageSize`; spec declares `size`) |
| 25 | 0 (231 GETs) | **3** (230) | `cc-flow export`, `cc-flow list-validate`, `cc-legacy-flows list` |
| 26 | 0 (467 CC cmds) | **14** (463) | `cc-agents list-activities`/`list-statistics`, `cc-ewt show`, `cc-queue-stats list`, `cc-search create`, `cc-tasks list`, `cc-subscriptions` ×8 |
| 27 | 0 (533 list cmds) | **12** (538) | `cc-global-vars list` + 6 CC `list-bulk-export` (extract `items`, spec array `resources`); `cc-user-profiles list-acl`; `user-settings`/`virtual-line-settings`/`workspace-settings list-outbound-billing-plan`; `guest-management list` |
| 28 | 0 (186 groups) | **186** (186) | 59 name a wrong product (`asset`, `channel` → Contact Center; `rooms` → Messaging); 127 the pre-colon format (`devices`, every `cc-*`) |
| 29 | 0 (4754 doc invocations) | **8** (4600) | `contact-center-core.md`:118/121/626/629: `cc-agents list-activities`, `list-statistics`, `cc-queue-stats list` with ISO `--from`/`--to`; spec says int64 epoch ms |
| 30 | 0 (467 bodies; 61 unparseable) | **68** (470; 58 unparseable) | `contact-center-routing.md:644` `cc-captures create` `{filters,from,to}`; `contact-center-analytics.md:291` and `reporting-cc` SKILL `cc-agent-summaries create`; `cc-dial-number create` `dialNumber` (routing doc :149, contact-center SKILL :586). Measured 75 before the SCIM case-folding rule; the 7 RFC-cased `Operations` bodies no longer count |
| **23-30 total** | **0** | **513** | |
| 6 (widened) | 0 | 0 | No pre-fix instance. 197 citations of 75 renamed commands are checked for the first time. Live-tree mutation: adding `--bogus-flag` to `contact-center-core.md:121` → 1 with the widening, 0 without |
| 9 (relabelled) | 0 | 0 | Label-only change (visible name instead of hidden alias) |
| 10 (widened) | 0 | **2** | `contact-center` SKILL `cc-users update-dynamic-skill` (missing `SKILL_ID`); `org-health` SKILL `call-queue show` (missing `LOCATION_ID`) |
| 11a (widened) | 0 | 0 | No pre-fix instance. Live-tree mutation: removing `--from` from `contact-center-core.md:121` → 1 with the widening, 0 without |
| 11b (widened) | 0 | 0 | No instance in either tree; pinned by tests |

Check 10 was widened as a side effect of check 29: `parse_module_signatures`, which both read, now records every decorator name.

### Real defects these checks surfaced, fixed on this branch

The 2026-10-13 instances (checks 23-26, 28 and 29, and check 27's first 8) were fixed on `main` in `e5e85fe`/`dc91c40`, before this work. Building the checks also turned up defects still present on `main` at `dc91c40`. All are fixed on this branch:

1. **5 SCIM-style lists ignored `--offset`/`--limit`** (check 23). `groups list`, `groups list-members`, `scim-groups list`, `scim-groups list-members` and `scim-users list` sent `max`/`start` to endpoints that page by `startIndex`/`count`. The generator now sends `count` and a 1-based `startIndex = offset + 1` (`4dec4b0`). Verified live on `groups list`; `scim-users` returns 403 for a PAT.
2. **4 flat-object GETs printed `[]`** (check 27, widened). `user-settings`, `virtual-line-settings` and `workspace-settings list-outbound-billing-plan`, plus `guest-management list` (`/guests/count`), were rendered as lists, so the extractor dropped the whole object. The parser now renders them as `show`; names are unchanged (`ba49ccf`). The flags are not: as single-object reads, all four lost `--limit`, `--offset` and `--all`, and `--output` now defaults to `json` instead of `table`. Nothing is lost by dropping those flags. `--limit`/`--offset` went out as `max`/`start`, which none of the four endpoints declares, and there is no page of one object to cut short. `--all` was the inert no-paging branch. Verified live: `user-settings list-outbound-billing-plan` now prints `{"enabled": true}`. `guest-management list` returns 403 for this PAT and is **unverified** live. *Superseded the same day by ADR-14's amendment: the three flags are accepted again on all four, hidden and ignored.*
3. **Group-help labels depended on render order** (check 28). The label of a group that two specs render (7 groups) named whichever spec rendered last, so a one-spec regen and a full regen disagreed. `command_renderer.group_label_spec` now picks deterministically. A forward-order and a reverse-order regen are byte-identical, and the rule changed one committed label: `locations`, Devices → Calling (`306edb7`).
4. **65 request-body errors found in docs** (check 30): 22 in 5 skills, 43 in 11 reference docs. 58 were fixed, from the spec or from a live call where one existed (e.g. the `reporting-cc` `cc-agent-summaries` body), and marked `> **Unverified:**` unless tested live (`8818243`, `bd862cf`). The other 7 were the SCIM bulk bodies. They were reverted to RFC 7644 `Operations` under `> **Unverified:**` notes, and check 30 now compares SCIM keys case-insensitively (`bd862cf`). That rule is why check 30's pre-fix count is 68, not 75.
5. **2 positional-argument doc bugs** (check 10, widened). `cc-users update-dynamic-skill` was missing `SKILL_ID` (its body was rebuilt from the spec and labelled Unverified), and `call-queue show` was missing `LOCATION_ID` (`07e0e20`, `bb71a49`).
6. **Flags silently dropped beside `--json-body`.** This was found while editing the docs, not by a check. The `admin-apps-data` recordings-share example passed `--host-email`/`--send-email` alongside `--json-body`, which replaces the whole body. The fields moved into the JSON (`aca40bd`).

### Consequences

**Enables:** the eight 2026-10-13 bug classes cannot come back, in the forms these checks detect, through a regen or a doc edit without failing the weekly job and the CI gate. CI asserts the gate printed `[30]`, the last check, so a run that dies early is caught.
**Forecloses:** acking a finding. The way out is a doc fix, a generator fix plus regen, or the existing per-tag overrides (`command_type_overrides: show`, `response_list_keys`) plus regen. `tools/CLAUDE.md` ("GATED SINCE 2026-10-13") says, check by check, how a human clears a finding.
**Gotchas — the no-ack trade-off, accepted on purpose:** checks 29 and 30 use the spec as the oracle. An upstream refresh that drops a key, or retypes a value, that the live API still accepts fails the gate, and the weekly release stays blocked until a human edits the doc. Known future false positives for check 29: the spec types Meetings registrants `zipCode` and voicemail-group `extension` as `number`, so a doc showing a ZIP+4 or a non-numeric extension would fire. No doc does today. Check 30 deliberately admits a few keys it should not (a measured false-negative hole, documented in `tools/CLAUDE.md` under "Check 30 — what it accepts beyond the schema"), so that a spec contradiction cannot block the routine.
**Not covered:** the 42 Link-cursor lists that send `--offset` as `start` while declaring only `max` (whether the server honours it cannot be decided statically); `/v1/tasks` paging by an undeclared `page` (verified working live); and the other half of the 2026-10-13 defects, which only a live call can see.

### Status

**Active** since 2026-10-13 on branch `feat/static-drift-checks`. Gate `--enforce` PASS at HEAD, every check 0. Design spec (local-only, gitignored): `docs/superpowers/specs/2026-10-13-static-drift-checks-design.md`. The Decision and Alternatives sections above reproduce it, so this ADR is the tracked record.

---

## ADR-14: A List GET That Returns One Object Renders as a Single-Object Read; Drift Check 31 Gates It

### Decision

A GET the parser classifies `list` is re-rendered as `show` — after its name is derived, so no name moves — when the spec declares **no paging** for it (no `Link` header, no paging query parameter: `ep.paginates` false and `pagination_style == "none"`) and, in every media type its 200 declares, the response is an object whose properties, paging metadata aside, are something other than exactly one array: one array plus a scalar, or two arrays (`openapi_parser._drops_object_fields`). This extends ADR-13 item 2 (`_declares_single_object`, flat objects with no array) to objects that carry an array. Paging metadata is a measured set, `_LIST_ENVELOPE_KEYS` (`meta`, the totals, `pageNumber`/`pageSize`/`rel`, SCIM `schemas`/`itemsPerPage`/`startIndex`, `count`, `pageInfo`, `links`, and the `start`/`limit` window echo of `/contacts/organizations/{orgId}/contacts/search`), held identically in the parser and in `drift_check.py`.

Two companion changes:

- **The list key is the array of records.** `extract_response_list_key` never picks an envelope array, and prefers an array of objects over an array of scalars; only then do `required` and spec order decide. That moved two keys on commands that stay lists: `device-dynamic-settings list` (`upgradeChannelList` → `devices`) and `archive-users list` (`schemas` → `Resources`).
- **Drift check 31 gates the class**, with no ack key (ADR-13's rules: static, `record_examined`/`BLIND`, `CHECK_PRINT`, never raises). A list command with no page walker fires when every declaring spec describes an object from which the extractor emits one property and drops another non-envelope one. A paged command fires only when it extracts an array of scalars while dropping an array of objects. CI's completion assertion now greps `^\[31\]`.

Result, measured by a full `spec_sync.py --skip-update` regen: **109 commands changed**, exactly the 109 that check 31 reports on the pre-fix tree — 107 render as single-object reads (names unchanged; `--output` defaults to `json`; `--limit`, `--offset` and `--all` are still accepted, hidden and ignored — see the amendment below), and the 2 key moves above. No other command changed *in that first pass*; a second regen produced no diff. (The amendment below later touched 8 more commands, so the final count is 115.)

| Group | Commands now single-object reads |
|---|---|
| `user-settings` (18) | `list`, `list-assistant`, `list-call-filtering`, `list-digit-patterns`, `list-members-applications`, `list-members-applications-1`, `list-members-hot-desking`, `list-ms-teams`, `list-numbers`, `list-outgoing-permission`, `list-preferred-answer-endpoint`, `list-privacy`, `list-push-to-talk`, `list-reception`, `list-selective-accept`, `list-selective-forward`, `list-selective-reject`, `list-simultaneous-ring` |
| `my-call-settings` (17) | `list-assistant`, `list-call-notify`, `list-call-park-secondary-lines`, `list-call-park-settings`, `list-call-pickup-group-secondary-lines`, `list-call-pickup-group-settings`, `list-monitoring`, `list-priority-alert`, `list-queues-secondary-lines`, `list-queues-settings`, `list-selective-accept`, `list-selective-forward`, `list-selective-reject`, `list-sequential-ring`, `list-simultaneous-ring`, `list-single-number-reach`, `list-speed-dials` |
| `workspace-settings` (13) | `list`, `list-digit-patterns`, `list-monitoring`, `list-numbers`, `list-outgoing-permission`, `list-priority-alert`, `list-privacy`, `list-push-to-talk`, `list-selective-accept`, `list-selective-forward`, `list-selective-reject`, `list-sequential-ring`, `list-simultaneous-ring` |
| `video-mesh` (12) | `list-media-health-monitor-test`, `list-clusters-media-health-monitor-test`, `list-nodes-media-health-monitor-test`, `list-reachability-test`, `list-clusters-reachability-test`, `list-nodes-reachability-test`, `list-network-test`, `list-clusters-network-test`, `list-nodes-network-test`, `list-test-status`, `list-test-results`, `list-event-thresholds` |
| `virtual-line-settings` (6) | `list-caller-id`, `list-devices`, `list-digit-patterns`, `list-outgoing-permission`, `list-privacy`, `list-push-to-talk` |
| `hds` (5) | `list-alarms`, `list-availability`, `list-network-test`, `list-resource-usage`, `list-tenants` |
| `call-queue` (4) | `list-forced-forward`, `list-holiday-service`, `list-night-service`, `list-stranded-calls` |
| `device-settings` (4) | `list`, `list-devices-people`, `list-devices-workspaces`, `list-layout` |
| `conference` (3), `meeting-preferences` (3) | `list`, `list-conference-me`, `list-conference-members`; `list`, `list-personal-meeting-room`, `list-scheduling-options` |
| 2 each | `cc-contact-list` `list`, `list-contact-lists`; `cc-flow` `list-activity-choices`, `list-event-specifications`; `meetings` `list-registration`, `list-survey`; `workspace-metrics` `list`, `list-workspace-duration-metrics` |
| 1 each | `activation-email list`, `ai-receptionist list-templates`, `announcement-playlists list-playlists`, `call-recording list-vendors`, `client-settings list`, `cq-playlists list`, `customer-assist list-settings`, `dect-devices list-handsets`, `device-dynamic-settings list-settings-groups`, `hot-desking-members list-members`, `meeting-tracking-codes list-tracking-codes`, `person-call-settings list`, `single-number-reach list-single-number-reach`, `webhook-interest-registrations list` |

### Context

Live 2026-10-13: `call-queue list-night-service LOC QUEUE -o json` printed `[]` while the server answered HTTP 200 with 236 bytes — the night-service switch, its action and schedule. `[]` reads as "service off", a false negative on a setting. `user-settings list-simultaneous-ring` and `list-privacy` printed `[]` for `{"enabled":false,"doNotRingIfOnCallEnabled":true,"phoneNumbers":[],"criteriasEnabled":false,"criteria":[]}`-shaped objects. Cause: `detect_command_type` calls a GET a list as soon as its 200 declares any array property, and the list extractor emits that one array. Check 27 passed every case, because it only asks whether the key reaches *some* declared array. Check 25 only covers `{id}`-tailed GETs.

### Alternatives Considered

- **Make the runtime extractor return the whole object when the response has siblings.** *Rejected.* The output type would then depend on what one response happened to contain: a list on one call, an object on the next, so an agent's `--fields '[].id'` or a table breaks unpredictably. The runtime has no schema, so it cannot tell paging metadata (`meta`, totals) from data. A table cannot render the object either, because its columns come from the item schema. `--limit`, `--offset` and `--all` would stay on commands where they mean nothing. And the gate reads the rendered command: a runtime patch leaves the generated code wrong-looking, so check 31 could not tell fixed from broken. The shape is known when the code is generated, so that is where it is decided — the same call ADR-13 item 2 made.
- **Apply the rule to paged endpoints too.** *Rejected.* A spec that declares paging declares a collection; rendering it as one object would remove `--all` from commands that really page. `people list` drops `notFoundIds` that way on purpose. Paged commands are judged only for the wrong-array case.
- **Treat echoed request fields (`orgId`, `from`, `to`, HDS `context`/`timeRange`) as metadata,** to keep tables on `video-mesh`/`hds`/`workspace-metrics`. *Rejected:* "echo or data" is a judgement per field, not a measured rule, and a single-object read is a superset of what the table showed. The video-mesh skill already directs operators to `-o json`.
- **109 `command_type_overrides: show` pins.** *Rejected:* the next upstream operation of this shape would ship broken. A rule in the parser, as ADR-13 item 2 did.
- **An ack or allowlist key for check 31.** *Rejected*, as for checks 23-30 (ADR-13).

### Proof — 0 at HEAD, fires on the pre-fix tree

HEAD is this change's regenerated tree, measured with `--enforce`. Pre-fix is the new check-31 code run against a worktree of `71856a6`, by passing its `src/wxcli/commands` and `specs` (and pointing `REPO`/`SPECS_DIR`/`COMMANDS_DIR`/`MAIN_PY` at it, as ADR-13 describes). Manual step; no test references that tree.

| Check | HEAD (examined, skipped) | Pre-fix 71856a6 (examined, skipped) | Named pre-fix instances |
|---|---|---|---|
| 31 | **0** (426 list commands, 8) | **109** (533 list commands, 8) | `call-queue list-night-service` (extracts `audioFiles`, drops the switch, action, schedules), `user-settings list-privacy`, `user-settings list-simultaneous-ring`, `person-call-settings list` (drops `callParkNotificationEnabled`, `availableEntriesCount`), `device-dynamic-settings list` (extracts `upgradeChannelList`, drops `devices`), `archive-users list` (extracts `schemas`, drops `Resources`) |

The 109 pre-fix findings and the 109 commands the regen changed are the same set (compared by group and command name). The gate's first line is unchanged (`192 command sets (195 registered names incl. aliases), 2164 commands, 1991 non-skipped spec ops (152 deliberately skipped)`); checks 23 and 27 examine 107 fewer list commands, because those are no longer lists. Mutation: dropping the envelope subtraction fails 8 of the 36 check-31 tests, judging paged blocks as non-paged fails 8, and ignoring a clean media type fails 20.

### Consequences

**Enables:** these reads return the whole object, so `[]` no longer stands in for a populated setting.
**Changes for users:** the 107 commands print the whole object, as JSON by default (`-o table` is still accepted). They still accept `--limit`, `--offset` and `--all`, which are hidden from `--help` and ignored (amendment below). Whether any of these endpoints pages without declaring it is **not known**: no paging is declared in the spec (no `Link` header, no paging query parameter), but an undeclared parameter is not proof the server ignores it — ADR-12's `/v1/tasks` pages by an undeclared `page`. If one ever returns `Link: rel="next"`, `rest_get`'s truncation note will say "Re-run with --all", and `--all` is accepted there but walks nothing. *(Superseded by ADR-18: the note on these commands now names no remedy.)*
**`dect-devices list-handsets` now prints `accessCode` by default — kept, recorded here.** Before, the default was a table (ID / Display Name / Index / Primary) whose override existed to keep the handset pairing code out of a default table; `-o json` always printed it. Now the default is the whole object as JSON, `accessCode` included. This is not new exposure in kind: the single-handset read, `dect-devices show-handsets`, already defaults to JSON, and its spec schema (`DECTHandsetGet`) declares `accessCode` (verified in `specs/webex-cloud-calling.json`). It does reverse that override's intent; nobody has decided otherwise.
**Config retired:** 13 `table_columns` entries became inert (a single-object read draws no table) and were deleted, among them the live-verified monitoredElements union (the fact it encoded is kept in a comment and in `tools/CLAUDE.md`). `generate_tag` now refuses a `table_columns`/`response_list_keys` entry on a command that renders no list, so the next one cannot rot silently. `build_producer_index` keeps a `list-*`-named single-object read as an ID producer, so 14 argument-help pointers (`from: wxcli dect-devices list-handsets`, …) survive.
**Verified live 2026-10-13 (read-only, after the regen):** `call-queue list-night-service`, `list-holiday-service`, `list-forced-forward` and `list-stranded-calls` return multi-key JSON objects (HTTP 200); `user-settings list-simultaneous-ring`, `list-privacy` and `list-outgoing-permission` return the full objects; `device-dynamic-settings list` returns 136 device-model records. **Not re-run live:** the other 101 converted commands and `archive-users list`. The doc and skill passages that described the pre-fix output ("prints `[]`", "prints only the `types` array") were rewritten the same day: those for the live-verified commands say so; every other one says the command now prints the whole response object and was not re-run live.
**Side effect of adding `start`/`limit` to the shared paging-metadata set** (`_LIST_ENVELOPE_KEYS`, read by the parser, by check 25 and by check 31; checks 23, 24 and 26-30 do not read it). Measured by removing the two keys from both copies in-process and re-running: of 2233 parsed operations across the 9 specs, exactly one changes — `GET /contacts/organizations/{orgId}/contacts/search` (`org-contacts`) would become a single-object read instead of a list on `result`; check 31 then reports 1 instead of 0 against today's rendered tree; check 25 stays 0 with the same 231 examined. So today the two keys protect that one list and change nothing else. The cost is a future false negative, never a false failure: `start` is real data (a timestamp or object) in the 200 of `/meetings/{meetingId}`, `/admin/meetings/{meetingId}`, `/recordingReport/meetingArchives/{archiveId}` and the call-recording announcements reads, so a future object shaped `{items: […], start: <timestamp>}` would be judged a clean collection and its `start` dropped without a finding.

### Amendment, 2026-10-13 — the paging flags stay, hidden and inert

**Decision (Adam, 2026-10-13).** Every `list*`-named command rendered as a single-object read keeps `--all`, `--limit` and `--offset` as **hidden options that do nothing**: absent from `--help`, never written to `params`, no effect on output (`command_renderer._render_inert_list_flags`, called from `_render_show_command`). This **supersedes** the "flags dropped" outcome of this ADR as first written and of ADR-13 item 2.

**Why.** The flag is uniform on every list command by design (root `CLAUDE.md` Common Flags; ADR-12's rejected alternative): an option present on most list commands but not all costs an agent a failed call plus a `--help` round trip, and a script that learned `--all` on one `list*` command would have got "No such option" on the 111 that ADR-13 item 2 and this ADR converted. The names were kept on purpose, so these still read as list commands. With the hidden flags, root `CLAUDE.md`'s "`--all` on every `list` command" is true again; one sentence there now says the flags are accepted and ignored on single-object `list*` commands.

**Scope, keyed on the visible name.** 115 commands carry them: the 107 above, the 4 from ADR-13 item 2 (`user-settings`/`virtual-line-settings`/`workspace-settings list-outbound-billing-plan`, `guest-management list`), and 4 older `list*`-named single-object reads that had also lost them (`cc-flow list-validate`, `cc-legacy-flows list`, `cc-user-profiles list-acl`, `pstn list-connection`). `cc-flow export` (hidden alias `list-export`) is not a list and gets none. A flag whose name the spec already claims on a command is skipped, so a real spec `--limit` is never shadowed. Non-`list*` commands (`show`, `create`, …) and real lists are unchanged; the 2 re-keyed lists (`device-dynamic-settings list`, `archive-users list`) keep their visible flags.

**Gate effect:** check 23 examines every GET carrying `--offset`/`--limit` text, so its examined count rose from 433 to 548 list commands, still 0 findings (the hidden flags feed no `params`). Check 16 (`--all` inert on a paging endpoint) reads these blocks too and stays 0. Command names, the name lock, `_registry.py` and `tools/spec_semantics.json` did not change. Pinned by `tests/test_inert_list_flags.py` (synthetic fixtures; the behavioural cases exec the rendered module with stubbed `wxcli` imports and prove `--help` omits the flags, that passing them changes neither the request nor the output, and that `show … --all` still exits 2).

### Known gap / follow-up — not built

The weekly spec-sync can silently flip a command between list and single-object read. `_drops_object_fields` decides from the 200 schema, so an upstream refresh that adds one scalar to a non-paged list's response (an echo field such as `orgId` is the realistic case) re-renders it as a single-object read: `-o json` changes from an array to an object, so `--fields '[].id'` and `jq '.[]'` break, and the default output changes from a table to JSON. The reverse happens when upstream removes the last scalar sibling. No gate sees it: check 22 and `tools/sync_classify.py` compare names and operations only (`command_name_lock.json` stores no command type), and check 31 is satisfied by the flip. Where the command carries a `table_columns` override, the same benign upstream change instead stops the regen at `generate_tag`'s guard (fail-closed), which `docs/spec-sync-contract.md` §6 does not list. **Exposure today: 136 list commands** call no page walker and have an object-wrapped 200 (review count, e.g. `call-controls list`, `authorizations list`, `call-queue list-dnis`, `call-recording list`, `cc-agents list-statistics`). **Proposed follow-up:** record each command's type (list or single-object) in the name lock, and make `sync_classify` route a list↔single-object change on an existing name to a human as breaking. **Adam has not approved building it.**

### Status

**Active** since 2026-10-13. Gate `--enforce` PASS, check 31 at 0.

---

## ADR-15: `POST` and `PATCH` Are Retried on 429 Only, Never on 5xx

### Decision

`WebexSession._request` (`src/wxcli/auth.py`) keeps its bounded retry (4 attempts, `Retry-After` honoured up to 30 s, jittered backoff) on 429/500/502/503/504 for `GET`, `PUT` and `DELETE`, but retries `POST` and `PATCH` on **429 only** (`NON_IDEMPOTENT_METHODS`). The one-shot connect-error retry is unchanged and applies to every method.

### Context

A 2026-10-13 live spot-check sent `cc-team create` without `teamType`; the server answered 500 and the CLI sent the request four times (three retries). No ghost team was created that time, but a 5xx on a create can mean the server half-processed it, and a resend could create a second resource. A 429 is different: the request was rejected before any work was done, so resending is safe. `GET`, `PUT` and `DELETE` are idempotent by contract, so retrying them on 5xx cannot duplicate anything. Evidence is one observed case; the rule rests on HTTP semantics, not on a measured duplicate.

### Alternatives Considered

- **Keep retrying everything (status quo).** *Rejected:* the downside is an unrecoverable duplicate resource, the upside is saving a manual re-run.
- **Exempt `/search` and `/query` POSTs, which only read.** *Rejected:* a path heuristic is fragile. The three read-only POSTs that lose their 5xx retry (`cc-search create`, and the meetings registrant and participant `/query` endpoints) cost one manual re-run.
- **Retry `POST` only when the body carries an idempotency key.** *Rejected:* Webex does not document one for these endpoints.

### Consequences

A create that hits a flaky 5xx now fails on the first response instead of recovering by itself; the operator re-runs it after checking whether the resource exists. `WXCLI_RETRY_MODE=off` is unchanged. Tests: `tests/test_auth.py` (`test_non_idempotent_write_is_not_retried_on_5xx`, `..._still_retried_on_429`, `test_idempotent_methods_are_still_retried_on_5xx`); documented in `docs/reference/authentication.md`.

### Status

**Active** since 2026-10-13.

---

## ADR-16: A Request Body the Spec Declares as a Query Parameter Is Rendered as the Body; Drift Check 32 Gates It

### Decision

`openapi_parser.parse_operation` first calls `_lift_query_body`. On a POST, PUT or PATCH that declares **no `requestBody`** and **exactly one** query parameter whose schema is an object (a `$ref` to one, `type: object`, or untyped with `properties`; `style: deepObject` excluded, because that is a real exploded query parameter), the parameter's schema becomes the operation's JSON request body and the parameter leaves the query. It is not rendered as a visible option, not required, and never sent. `--json-body` is the body, `--generate-json-body` prints the schema's skeleton, and body flags come from the schema like any other body. Required DTO fields follow the ordinary body rule: on `create` they are checked at runtime only when `--json-body` is absent (exit 1, `Missing required fields`), never as a required Click option, so `--json-body` alone always runs. The op is copied, so the spec is never mutated.

The old option (`--team-dto`, `--skill-profile-dto`, `--agent-profile-dto`) is kept as a **hidden option that is accepted and ignored** (`Endpoint.lifted_query_params` → `command_renderer._render_lifted_query_flags`, on create/update/action/delete). Scripts, and the 2026-10-13 docs' workaround `--team-dto x --json-body '{…}'`, keep working instead of hitting "No such option". This is the policy Adam approved for the hidden paging flags (ADR-14 amendment).

**Drift check 32 gates the class**, with ADR-13's rules: static, `record_examined`/`BLIND`, `CHECK_PRINT`, never raises, no ack key. For every POST/PUT/PATCH command with a spec op, it fires when the op declares its body as a query parameter and the command still treats it as one: it writes the parameter into `params`, declares the option required, sends no body, or (for one parameter with properties) offers no `--generate-json-body`. Examined is every write command with a spec op, not just the six, so an upstream spec that fixes the error reads a clean 0, never `BLIND`. The gate prints how many spec ops are in the class beside the count. CI's completion assertion now greps `^\[32\]`.

The gate keeps its **own copy** of the rule (`drift_check.query_body_params`), so it is an oracle for the generator and not a restatement of it; `tests/test_drift_check_query_body.py` pins the two copies to the same answers. Its body readers (`_raw_body_schema`, `body_schema`, `required_query_params`, when given the spec) now treat a lifted parameter as the body, so checks 13, 14, 29 and 30 judge the body the command actually sends. Check 19 (`tools/spec_semantics.json`) still reads the raw spec, so its snapshot did not change.

### Context

`specs/webex-contact-center.json` declares the DTO of six writes as a **required query parameter** whose schema is a `$ref` object, with no `requestBody`: POST/PUT `/organization/{orgid}/team[/{id}]` (`teamDTO` → `TeamDTO`), `/skill-profile[/{id}]` (`skillProfileDTO`), `/agent-profile[/{id}]` (`agentProfileDTO`). A scan of all 9 specs (2198 operations, 3076 query parameters) finds no other object-typed query parameter, on any method. Rendered literally, the six commands were broken. **Verified live 2026-10-13** by a sandbox agent, 6+ reproductions:

- `cc-team create --json-body '{…}'` exited 2: `Error: Missing option '--team-dto'.`
- The option's value went out as a query string (`POST …/team?teamDTO=%7B%22name%22…`) and the body was empty, so passing the real JSON only through `--team-dto` returned 400 `[siteId: should not be null or blank., active: should be either true or false.]`.
- `--team-dto x --json-body '{…}'` worked, so the DTO really is the request body.
- `--generate-json-body` was "No such option" on all six, although the 400 tip and root `CLAUDE.md` Known Issue #2 point users at it.

Live-found facts about the bodies, kept in `docs/reference/contact-center-core.md` §9/§11/§14:

- **An update needs `id` in the body**, equal to the URL id (`400 "Invalid id: id in payload and URL should be same"`). The spec does not mark `id` required.
- **A team create needs `active`, `teamType` and `teamStatus` besides `name` and `siteId`.** Without `active` the server returns 400; without `teamType`, 500; without `teamStatus`, 409. The spec's `TeamDTO.required` lists all five, plus `rankQueuesForTeam`, which the live-verified body omits. So the generated flag path demands `--rank-queues-for-team` and the live-verified `--json-body` does not. Whether the server needs it is **unverified**. (The brief this ADR was written from said the spec marks only some of the five. Measured against the spec, it marks all five.)

### Alternatives Considered

- **A spec overlay that adds `requestBody` and removes the query parameter.** *Rejected.* Overlays are additive only: `spec_overlay.merge_overlay` can add paths but cannot remove a parameter, and `apply_overlay` raises when an overlay path collides with an upstream path, which these six do. Check 5 exists to delete overlays once upstream publishes a path. An overlay would also fix only these six; the next upstream spec could repeat the error on a new operation.
- **Six `field_overrides.yaml` pins (`omit_query_params` plus a body override).** *Rejected* for the same reason ADR-14 rejected 109 pins: the next operation of this shape would ship broken. A parser rule, gated by check 32, covers it.
- **Drop the old option outright.** *Rejected.* The 2026-10-13 docs taught `--team-dto x --json-body …`, and "No such option" would break every script that learned it. The hidden option costs nothing: it is not in `--help`, not sent, and not required.
- **Guess the body when two object query parameters exist.** *Rejected.* There is no rule for which one is the body. The parser leaves both in the query and check 32 fails, so a human decides.
- **An ack or allowlist key for check 32.** *Rejected*, as for checks 23-31 (ADR-13).

### Proof — 0 at HEAD, fires on the pre-fix tree

HEAD is this change's regenerated tree, measured with `--enforce`. Pre-fix is the new check-32 code run against a worktree of `5f6550b`, with `REPO`/`SPECS_DIR`/`COMMANDS_DIR`/`MAIN_PY` pointed at it (ADR-13's method). This is a manual step; no test references that tree.

| Check | HEAD (examined, skipped) | Pre-fix 5f6550b (examined, skipped) | Named pre-fix instances |
|---|---|---|---|
| 32 | **0** (869 write commands, 3) | **6** (869 write commands, 3) | `cc-team create`/`update` (`teamDTO`), `cc-skill-profile create`/`update` (`skillProfileDTO`), `cc-desktop-profile create`/`update` (`agentProfileDTO`): each "sent as query param, required option, no --generate-json-body" |

The 3 skipped are `cc-ai-assistant create` (`POST /event`, in no spec) and the 2 hand-written blocks `HELPER_SKIPS` names (`cleanup run`, `cucm execute`). Both runs print `(6 spec ops declare their body as a query param)`.

The regen changed exactly 3 modules (`cc_team.py`, `cc_skill_profile.py`, `cc_desktop_profile.py`), and only the six commands in them. A second and a third regen produced byte-identical `git diff -- src/ tools/` and `git status`. The name lock, `_registry.py` and `tools/spec_semantics.json` did not change, and the gate's first line is unchanged (`192 command sets (195 registered names incl. aliases), 2164 commands, 1991 non-skipped spec ops (152 deliberately skipped)`).

**Doc defects the widened body readers surfaced.** Check 30 had never judged these six commands' `--json-body` examples, because their ops declared no body. With the lifted body it found 3 wrong bodies in the `contact-center` skill: `cc-team create` sent `multimediaProfileId` (the schema spells it `multiMediaProfileId`), `cc-skill-profile create` sent `skills` (live 400; the field is `activeSkills`), and `cc-desktop-profile create` sent `{name, desktopLayoutId}` (live: that body is rejected, and a profile has no `desktopLayoutId`; a PUT carrying one is accepted and silently drops it). All 3 were rewritten to the bodies that `contact-center-core.md` records as verified live 2026-10-13.

### Consequences

**Enables:** `cc-team`, `cc-skill-profile` and `cc-desktop-profile` `create`/`update` take `--json-body` alone, or the body flags, and offer `--generate-json-body`. The DTO is sent as the request body. Docs and the skill now show `--json-body` with no DTO option. That form is a **generator fix 2026-10-13 (ADR-16), Verified live 2026-10-13** on a temporary team, skill profile and desktop profile in the sandbox: create, show, update (with `--verify`) and delete all worked with `--json-body` alone, and the old option was accepted and ignored on `update` for teams and desktop profiles.
**Changes for users:** the six commands gain body flags (`cc-team create` has 18) and a generated `Example:` line built from the spec's required fields. Numeric DTO fields (`capacity`, `version`) are string-typed flags, the generator's existing behaviour for every body, so prefer `--json-body` for them.
**Known gaps, not built:** the generated `update` `Example:` lines carry no `id` in the body, though the server requires it, so an agent copying one verbatim gets `400 "Invalid id"`. All three updates render an `--id` body flag (it writes `body["id"]`; the path argument is `ID`), but `--json-body` replaces the whole body, so with `--json-body` the `id` must be inside the JSON. The docs' Update bullets say the body must carry `id`. Teaching the generator that a CC update's body needs the URL id is a separate change. Two more small gaps found in review: the generated `--help` example for `cc-desktop-profile create` omits `loginVoiceOptions`, which `contact-center-core.md` §14 records as required live; and a body supplied only through the hidden DTO option (`--team-dto '{...}'` alone) is silently dropped, so `update` sends a PUT with an empty body and `create` exits 1 with a "Missing required fields" error that does not mention the ignored option. Neither is a regression (the old behaviour also sent an empty body); a stderr note when the hidden option carries JSON would help.

### Status

**Active** since 2026-10-13. Gate `--enforce` PASS, check 32 at 0.

---

## ADR-17: `--verify` Checks That the Read-Back Contains What Was Sent; a Field the Read-Back Lacks Is "Could Not Be Verified"

### Decision

`verify_write` (`src/wxcli/common.py`) still compares **only the fields you sent** and still **never changes the exit code**. What changed is how one sent field is judged against the read-back:

- **Scalars** are equal after one normalisation: a string that spells the number (`'30'` vs `30`, `'2.5'` vs `2.5`) or the boolean (`'true'`/`'false'`, either case, vs `True`/`False`) is equal to it, in both directions. A boolean is never equal to a number (Python says `True == 1`; a boolean field reading back `1` proves nothing). `'030'` is not `30`. A rewritten value (an E.164 phone number `+15559876543` read back as `+1-5559876543`) still differs: there is no safe rule for it.
- **Objects** match when every sent key matches, recursively; keys only the read-back has (defaults, server-added ids, empty arrays) are ignored. A nested difference is reported by its path: `callForwarding.always.enabled: sent True, now False`.
- **Lists of scalars** compare as multisets: order is ignored, duplicates count, and an extra or missing element is a difference.
- **Lists of objects** must also come back with **exactly as many elements** as were sent, and each sent element must be matched by a **distinct** read-back element under the object rule, so extra keys *inside* an element are ignored. Same order is tried first; otherwise iterative augmenting-path matching runs, so a first-fit choice cannot block a real match and no input recurses deeply. Above 1,000 elements an out-of-order list is not matched (that is n² element compares). It raises `ListTooLongToMatch` and is reported as described below.
- **Nothing in the compare can change the exit code.** The compare runs after the write succeeded and before its result is printed, so it is wrapped. Any exception prints `Note: --verify could not compare the read-back (<ExceptionType>)` and returns.
- **A sent key absent from the read-back**, at any depth **outside a list element**, is not reported as differing. It goes in a separate bucket: `<path>: could not be verified — not present in the read-back (the endpoint may name it differently)`, under a summary of `N matched, M could not be verified`. The summary never says "all … match" while that bucket is non-empty. When a difference is also printed, the bucket's count is in paths (`K sent path(s) could not be verified`), so it always equals the lines listed under it. Two edge cases:
  - **Missing key inside a list element.** The element simply does not match, so the list is reported as differing (the safe direction). Once order is free, there is no single element path to call unverifiable.
  - **Sent `null` with the key omitted from the read-back.** This counts as matched, and is stated in root `CLAUDE.md` as the one exception to "never all match". Omitting a cleared field is how these endpoints read it back (`preferredAnswerEndpointId`). If the server had ignored the clear, the old value would come back present and show as differing, which is pinned by test `TestSentNull`. The cost: a `null` sent for a field the endpoint never returns (case d) reads as matched.

The message for a real difference is unchanged: `Note: --verify re-read <url> and D of N sent field(s) differ. …` followed by `  <path>: sent X, now Y`.

### Context

Measured live 2026-10-13 by five agents, 8+ cases. Each write had applied (checked with `show`), yet `--verify` printed "differ", because it compared each top-level field with `!=`:

- (a) **String-typed numeric flags.** `calling-service update --number-of-days-for-message-expiry 30` printed `numberOfDaysForMessageExpiry: sent '30', now 30`; also `workspace-locations update-floors --floor-number 3` and `update-alert --next-assistant-number-of-rings 4`. The generator types body numbers as `str`.
- (b) **The read-back is a superset.** `call-queue update-call-forwarding`, `hunt-group update`, `location-call-handling update-outgoing-permission`, `device-settings` member updates, `cc-multimedia-profile update` (adds `workItem`/`customMessaging`), `cc-desktop-profile update` (`viewableStatistics` gains an `id` and empty arrays).
- (c) **Reordered arrays.** `cc-business-hour` `days`, `cc-skill-profile` `activeSkills`.
- (d) **Write and read keys differ.** `update-monitoring` writes `enableCallParkNotification` and reads `callParkNotificationEnabled`; `virtual-line-settings update-virtual-lines --extension` reads back under `number.extension`; `device-settings update-devices-workspaces` re-reads an endpoint with no hoteling field. These printed `now '<not present in read-back>'` in the same list as real failures.

A check that cries wolf on most writes trains its reader to ignore it, which removes the one thing `--verify` exists for: the silent drop (a second `HOTDESKING_GUEST` member accepted with 200 and discarded, `person-call-settings-behavior.md`).

### Alternatives Considered

- **Keep `!=` and document the false alarms per command (status quo).** *Rejected:* eight documented exceptions and growing; every caveat was a reader told to ignore the tool.
- **Per-command key maps for case (d)** (`enableCallParkNotification` → `callParkNotificationEnabled`). *Rejected:* hand-maintained pins that drift on regen, and the measured cases are not one pattern (a rename, a move under `number.`, an endpoint without the field). Naming the field as unverifiable is honest and needs no map.
- **Type the generated numeric flags as `int`.** *Not chosen here:* it is a generator change (another implementer's files this round) and would not fix (b), (c) or (d). The normalisation stays correct after such a change.
- **Ignore extra elements in a read-back object list (round 1).** *Reversed in round 2.* Reviewer D showed `sent {"agents":[{"id":"A"}]}` against `[{"id":"A"},{"id":"B"}]` printing "all 1 sent field(s) match". A PUT replaces the list, so that is a removal the server ignored, which is the "accepted, not applied" failure the flag exists for. None of the measured cases needed extras ignored: (b) adds keys *inside* elements, and (c) reorders lists of the same length.
- **Keep recursive matching and add only a try/except.** *Rejected.* About 1,100 interchangeable elements hit `RecursionError`. Catching it would have turned a correct answer into "could not compare" for ordinary long lists, so the matching was made iterative as well.
- **Count an unverifiable field as matched, or as differing.** *Rejected* both: either reads as a verdict the tool did not reach.

### Consequences

The measured (a), (b) and (c) cases now print `Verified: … all N sent field(s) match.`; (d) prints `N matched, M could not be verified` with the field named. Real differences, lists of a different length and rewritten values still print as before, with nested paths instead of whole top-level objects. Residual blind spots, both in the safe direction:
- A sent list of id strings read back as a list of objects (`monitoredElements`) still reads as differing, because the comparison does not guess across shapes.
- `{"assistantIds": null}` read back as `[]` reads as differing.

Tests in `tests/test_verify_flag.py`:
- Round 1: `TestScalarNormalisation`, `TestSupersetReadBack`, `TestReorderedLists`, `TestAbsentFromReadBack`. One pre-existing test (`test_verify_flags_a_field_absent_from_the_read_back`) was updated for the new wording.
- Round 2: `TestListLengthIsExact`, `TestSentNull`, `TestCompareCannotEscape` (5,000-element inputs), `TestSummaryCountsAgree`, `TestAbsentKeyInsideAListElement`. Unit-tested only; not re-run live. Root `CLAUDE.md` ("Common Flags"), the affected reference docs and skills now describe this behaviour.

### Live verification

Verified live 2026-10-13 against the sandbox (change-and-restore; read back): `calling-service update --message-expiry-enabled --number-of-days-for-message-expiry 30 --verify` printed `Verified: ... all 2 sent field(s) match.` (it printed `sent '30', now 30` before), and the restore did the same with the voicemail settings reading back identical to the original. `user-settings update-call-recording --enabled --record Always` returned the Dubber terms-of-service body and a Tip naming `termsOfServiceUrl` (no "still referenced ... wxcli cleanup run"; the numeric status is not printed). `user-settings update-reception ... receptionEnabled:true` returned an empty 400 and the CLI printed `Error: HTTP 400 with an empty response body (trackingId: ROUTERGW_...)` instead of a bare `Error: `. `people list --location-id LOC` without `--calling-data` now tips `--calling-data true`. The round-2 list-length, null and 5,000-element cases remain unit-tested only.

### Status

**Active** since 2026-10-13.

---

## ADR-18: The Truncation Note Names Only the Flags the Command Offers; a Measured Set Refuses `--offset`; Drift Check 33 Gates the Advice

### Decision

1. **The note's remedies are declared by the caller.** `WebexSession.rest_get` and `fetch_from_offset` (`src/wxcli/auth.py`) take a keyword-only `remedies` (default `()`); the private helpers that print the note (`_warn_if_more_pages`, `_more_pages_note`) take it with no default, so a future direct caller cannot silently bring back the old advice, which check 33 would not see. The note names `--all` only when `"all"` is passed and `--offset N` only when `"offset"` is passed. With `("all", "offset")` the wording is unchanged (`Re-run with --all to fetch every page, or --offset N for just the next one.`); with `("all",)` it says `Re-run with --all … (this endpoint ignores --offset; slice the --all output instead, e.g. --fields '[100:200]').`; with nothing it says `This command does not walk pages; see its --help for a cursor or paging option.`
2. **The generator passes what each shape offers** (`command_renderer._render_list_command`): a list that calls a page walker (`paginates`, or `link`/`page`/`scim` paging) passes `("all", "offset")` on every `rest_get`/`fetch_from_offset` call; a list in the `offset_ignored` set passes `("all",)`; everything else passes nothing — show commands, the hidden-flag single-object `list*` reads (ADR-14 amendment), lists the spec says do not page (their visible `--all` walks nothing), hand-written commands, `verify_write`, raw-Python callers.
3. **A declared, measured set refuses `--offset`.** New per-tag, command-keyed override `offset_ignored: {command: evidence}` in `tools/field_overrides.yaml`, today exactly `People: list` and `Licenses: list`, each with its measurement in a comment. On those commands `--offset N` with N > 0 exits 2 before authentication, `--offset` is no longer written to `params`, and its help says so. `--offset 0` still runs. The message is worded by shape. On a walker list (`people list`): `Error: this endpoint ignores --offset: it returns the first page again whatever offset is sent (measured live, ADR-18). Drop --offset and slice every page instead, e.g. --all --fields '[2:5]'.`, or `… slice the --all output instead, e.g. --fields '[2:5]'.` when `--all` was already passed (refusing `--all --offset 2` is deliberate: honouring `--all` would silently start at record 0). On an unpaged list (`licenses list`, whose `--all` walks nothing and whose endpoint returns every row): `… it returns the same records whatever offset is sent … Drop --offset and slice the output instead, e.g. --fields '[2:5]'.`, never naming `--all`. The generator validates the key like every command-keyed override (`COMMAND_KEYED_OVERRIDES`, so gate check 15 re-checks it), exits 1 when it names a command that renders no list, and exits 1 with `ERROR: offset_ignored names …` (`OffsetIgnoredError`, caught in `generate_tag`) when it names a page-numbered or SCIM list, whose `--offset` is translated and works by construction — the shape a declared list takes if upstream adds page or `startIndex` paging. Both are human fixes (`docs/spec-sync-contract.md` §6).
4. **`licenses list` `--limit`** (the endpoint ignores `max` too) is unchanged: still sent as `max`, still ignored by the server. It caps the printed rows in `-o table` only; `-o json` prints every license. No client-side slicing was built.
5. **Drift check 33 gates the advice** (ADR-13 rules: static, `record_examined`/`BLIND`, `CHECK_PRINT`, never raises, no ack key). Every block that calls `rest_get`/`fetch_from_offset` is examined; the remedies each call names are its literal `remedies=`, else the default read from `auth.py`'s own signature (a runtime with no such parameter is the pre-fix one, which named both on every call). A block fires when a call names `--all` and the block has no visible `--all` that reaches a page walker, or names `--offset` and the block has no visible `--offset` or refuses it. CI's completion assertion now greps `^\[33\]`; `docs/spec-sync-contract.md` lists 33 with the generator checks the routine never repairs.

### Context

Measured live 2026-10-13 (read-only CLI; the controller reproduced the first two):

| Command | `--offset 2 --limit 3` vs items 2–4 of `--all` | Verdict |
|---|---|---|
| `devices list` | equal | honours `start` |
| `workspaces list` | equal | honours `start` |
| `numbers list` (`/telephony/config/numbers`) | equal | honours `start` |
| `hunt-group list` | equal | honours `start` |
| `people list` | returned items 0–2; `GET /v1/people?max=3&start=2` = the first page; Link pages by `cursor=` | **ignores `start`** (honours `max`) |
| `licenses list` | `-o json --limit 3 --offset 3` (`?max=3&start=3`) returned all 18 rows (`docs/reference/admin-licensing.md`); `--limit 3` alone also returned all 18, no Link header, stderr empty | **ignores `start` and `max`** |

The `people list` note nonetheless said `… or --offset 5 for just the next one`, so following it looped back to page one. Separately, `licenses show ID --include-assigned-to user --limit 2` printed `Re-run with --all to fetch every page`, and `licenses show … --all` is `No such option: --all`: every generated command calls `rest_get`, which printed the same advice whatever the command offered. Adam's decision, 2026-10-13: stop printing the hint for endpoints that ignore `start`; say so clearly instead of looping.

**What the spec says about the six (static, measured 2026-10-13 against `specs/`).** The four that honour `start` all declare it (`GET /devices`, `/workspaces`, `/telephony/config/numbers`, `/telephony/config/huntGroups` declare `max` and `start`); `GET /people` declares only `max` (every spec that carries it), and `GET /licenses` declares no paging parameter at all. On the regenerated tree, **48 walker lists** send `--offset` as a `start` their spec does not declare — `people list`'s shape (`locations list`, `memberships list`, `messages list`, `rooms list`, `webhooks list`, `cdr list`, the meetings and recording-report lists, …) — and **110 more** declare `start` but were not sampled. (The brief this ADR was written from estimated "about 36" untested; the static count is 48 + 110.) All of them keep `("all", "offset")`: an undeclared `start` is not proof the server ignores it (ADR-12: `/v1/tasks` pages by an undeclared `page`), so none joins the set without a live measurement. The 152 lists that send an undeclared `start` and call no walker now print no remedy at all (decision 2), whatever their `start` does.

### Alternatives Considered

- **A blanket client-side skip** (fetch from the start and drop N records) on every Link-cursor list. *Rejected:* 4 of the 6 sampled endpoints honour `start`, so it would re-walk N records on commands that work, to fix two that do not. The set is declared from measurements instead, and grows only by measurement.
- **Detect "ignored" at runtime** (compare the first record with and without `start`). *Rejected:* an extra request on every `--offset` call, and an empty or one-page collection cannot tell the two apart (the "probe on an empty dataset proves nothing" lesson).
- **Remove or hide `--offset` on the two commands.** *Rejected:* the uniform-flag rule (ADR-12, ADR-14 amendment); "No such option" teaches nothing. Exit 2 with the reason and the workaround does.
- **Keep sending `start` and only change the note.** *Rejected:* `--offset 2` would still return page one with exit 0 — a confident wrong answer.
- **Keep the old default (both remedies) for callers that pass nothing.** *Rejected:* the 514 show and single-object blocks would keep advising `--all`. The safe default names nothing.
- **Choose the remedies in `auth.py` by URL.** *Rejected:* special-casing by URL; the generator already knows each command's shape.
- **Derive the set from the spec ("no declared `start`" = ignored).** *Rejected:* it matches the six samples (the four that honour `start` declare it; `people` and `licenses` do not), but six is a sample, not a rule, and an undeclared paging parameter is honoured elsewhere (`/v1/tasks`, ADR-12). It would refuse `--offset` on 48 untested commands at once. Check 33 therefore gates only the advice against the code; the `offset_ignored` set carries the live facts, and the spec correlation is the place to probe first.

### Proof — 0 at HEAD, fires on the pre-fix tree

HEAD is this change's regenerated tree, measured with `--enforce`. Pre-fix is the new check-33 code run against a worktree of `e31faef`, with `commands_dir` and `auth_py` pointed at it (ADR-13's method; manual step, no test references that tree).

| Check | HEAD (examined, skipped) | Pre-fix e31faef (examined, skipped) | Named pre-fix instances |
|---|---|---|---|
| 33 | **0** (946 note-printing commands, 2) | **667** (946, 2) | 514 call sites that would advise `--all` and `--offset` with neither offered — show and single-object reads: `licenses show`, `call-queue list-night-service`, `user-settings list-privacy`; 153 that would advise an `--all` whose visible flag walks nothing — unpaged lists: `licenses list`. "Would": the note prints only when a response carries `Link: rel="next"` or a body total, which some of these (a single settings object) are unlikely ever to do |

The 2 skipped are the hand-written blocks `HELPER_SKIPS` names. `people list` does **not** fire on the pre-fix tree: its code offered a visible `--offset` that it sent as `start`, and that the server ignores it is a live fact no static rule can see (Alternatives). It is pinned instead by `tests/test_paging_remedies.py` (renders the refusal and `remedies=("all",)`; execs the rendered module: `--offset 2` exits 2 and sends nothing) and by a check-33 test that fires when a refusing block still advises `--offset`.

The regen changed 105 command modules and nothing else under `src/wxcli/commands`: 384 note-printing calls gained `remedies=` (278 `rest_get` and 105 `fetch_from_offset` with `("all", "offset")`, 1 `rest_get` with `("all",)` on `people list`), and `people list`/`licenses list` each gained the refusal, lost `params["start"] = offset`, and changed their `--offset` help. A second regen produced a byte-identical `git diff -- src/wxcli/commands tools src/wxcli/auth.py` and `git status --porcelain` (md5 `5898ff7f…` / `abf398da…` both times; after the review round that reworded the refusal by shape, again two identical regens, `1488ddd2…` / `35a7107f…`). The name lock, `_registry.py` and `tools/spec_semantics.json` did not change, and the gate's first line is unchanged (`192 command sets (195 registered names incl. aliases), 2164 commands, 1991 non-skipped spec ops (152 deliberately skipped)`).

### Consequences

**Changes for users.** **Verified live 2026-10-13** (by the controller, after the first regen): `people list --offset 2 --limit 3` exits 2 and names `--all`; `people list --all --fields '[2:5].id'` returns the 3 items; `hunt-group list --offset 2 --limit 3` still equals items [2:5] of `--all` (7 records), so a walker list that honours `start` is untouched. **Unit-tested; not re-run live:** the shape-specific refusal wording (reworded after that live run), `licenses list --offset N` exiting 2, the `people list` note naming `--all` only, and the note on a show command, single-object `list*` read or unpaged list naming neither flag — the `licenses show` case did not reproduce on the license the controller tried, so that note is not live-verified. Lists with a page walker print exactly what they printed before.
**Blind spot of check 33:** it sees advice that names a flag the command does not offer, never advice that went missing. If the renderer stopped passing `remedies=` to walker lists, they would lose their `--all`/`--offset` advice and the gate would stay green (measured: pre-fix commands against the new runtime read 0). The renderer tests in `tests/test_paging_remedies.py` (`test_paginating_list_offers_both`, `test_link_walker_list_offers_both`, `test_page_numbered_list_offers_both_on_both_calls`) are what catch a lost remedy; that file is tracked and runs in CI.
**Not covered:** the 48 walker lists that send an undeclared `start`, and the 110 that declare it, are unmeasured; if one ignores `start`, its note still names `--offset` and loops. **Follow-up, not built:** probe them live (`--offset 2 --limit 3` vs items 2–4 of `--all`) when the sandbox has more than 5 records per collection, starting with the 48, and add each measured offender to `offset_ignored`. The note's wording for the no-remedy case points at `--help`; `licenses show` has a `--next` cursor there, which was not exercised.
**Supersedes:** ADR-12's "the truncation note names `--offset <absolute next record>` on every command" (now: on every command that offers a working `--offset`), and ADR-14's consequence that a converted single-object read would print "Re-run with --all" (it now names no remedy).

### Amendment — 2026-10-14: the 158 unmeasured walker lists probed

Every walker list that sent `--offset` as `start` (162 on the tree, minus the 4 measured above) was probed live, read-only, on the sandbox tenant with the test from Decision 3: `--offset 2 --limit 3` against items 2–4 of `--all` and against `--limit 3`. Results, per command, in `docs/architecture/offset-probe-2026-10-14.tsv`:

| Verdict | Count | Meaning |
|---|---|---|
| honours `start` | 28 | B = items 2–4 of `--all`, and differs from the first 3 |
| **ignores `start`** | **3** | `device-dynamic-settings list`, `resource-group-memberships list`, `resource-group-memberships list-v2` |
| not enough data | 74 | fewer than 5 records in the sandbox (no call queues, auto attendants, workspaces, rooms, meetings, trunks, route groups) |
| needs input | 36 | no usable parent ID or date window found |
| error | 17 | 403 / missing licence or scope (`cdr`, `security-audit`, `partner-tags`, `my-call-settings`, some meetings and recording lists) |

- `device-dynamic-settings list` (`GET /telephony/config/supportedDevices`): `--all`, `--offset 2 --limit 3` and `--limit 3` each returned all 136 records — `start` and `max` both ignored, the `licenses list` behaviour. Its spec declares neither, only a Link header.
- `resource-group-memberships list` / `list-v2`: on 84 records, `--offset 2 --limit 3` returned the same 3 records as `--limit 3`, on repeated runs; `max` is honoured. The spec declares `max`, not `start` — the `people list` shape.

All three joined `offset_ignored` and were regenerated: `--offset 2` exits 2 with the walker-list message, the note names `--all` only, `--all` still returns 136 / 84 / 84 (verified live after the regen).

**A probe defect, caught before it counted.** The first pass compared records on a key that turned out to be identical on every record (the tail of a `…: false}` field on available-number lists; a shared ID suffix on `call-park list-available-recall-hunt-groups`), so A, B and C all matched and 16 commands read "honours" without evidence. All 16 were re-run comparing `phoneNumber` / `name`; all 16 do honour `start` (e.g. `--offset 2` → `+12094571618, …620, …622`; `--limit 3` → `…615, …616, …618`). When probing, check that the comparison key differs between A and C, or the test cannot fail.

**Spec correlation after phase 1, 37 of 37.** All 5 measured "ignores" endpoints omitted `start` from their spec; all 32 measured "honours" endpoints (the 4 above plus these 28) declare it — two of them (`hot-desking-members list`, `user-settings list-available-members-hot-desking`) only through a `$ref` to `#/components/parameters/start`, which a name-only scan misses.

**Phase 2, same day: the risky half, on temporary data.** Of the 127 unmeasured, 82 declare `start` and 45 do not. For the 11 of those 45 that the admin token could feed, temporary data was created (5 spaces with messages, members and tabs; 5 teams with members; 5 webhooks; 2 locations; 5 scheduled meetings with invitees and registrants), measured, and deleted — re-listing confirmed nothing left. Every comparison had A ≠ C, so each test could fail. **All 11 ignore `start`:** `locations list`, `webhooks list`, `rooms list`, `messages list`, `memberships list`, `room-tabs list` (ignores `max` too), `teams list`, `team-memberships list`, `meetings list-meetings`, `meeting-invitees list`, `meetings list-registrants`. They joined `offset_ignored` (the messaging `Messages` entry under `tag_overrides: webex-messaging.json`, because the meetings spec has its own `Messages` tag with no `list`). **Correlation now 48 of 48:** 32 declare `start` and honour it; 16 do not and ignore it.

**Decision (Adam, 2026-10-14): the spec rule, reversing the "derive the set from the spec" alternative above.** That alternative was rejected on six samples; it now rests on 48 with no exception, and the remaining 34 (meeting participants/Q&A/polls/transcripts/reports, recordings, `cdr`, `security-audit`, `events`, partner/wholesale/BroadWorks lists, job-error lists) cannot be measured with an admin token in the sandbox — they need held meetings, licences or scopes. The asymmetry decides it: a wrong refusal prints "use `--all`", which returns the right data; a wrong pass returns page one with exit 0. **The rule (`command_renderer._render_list_command`, `offset_spec_absent`):** a page-walking list (`paginates`, or `link` paging) that is not translated (page-numbered / SCIM) and whose spec declares neither `start` nor `offset` (`$ref` parameters resolved by the parser) refuses `--offset` exactly as a measured entry does, with its own wording — help: `ignores it, inferred from its spec, which declares no offset parameter`; error: `its spec declares no offset parameter, and every such endpoint measured returned the first page again (ADR-18)` — so it never claims a measurement. A measured `offset_ignored` entry keeps the "measured live" wording. **Scope:** page-walking lists only; the regen refused exactly the 34 expected (no other module changed behaviour), plus the 16 measured. Unpaged lists that send an undeclared `start` (no walker) are untouched, as is `licenses list` (measured). It is also the rule a new upstream endpoint gets automatically, so the weekly sync cannot add a silent offset. **If the rule is ever wrong for an endpoint** (it honours an undeclared `start`), the fix is a per-tag override that opts it back in — not built; no case exists. Verified live 2026-10-14: `admin-recordings list --offset 2` exits 2 with the spec wording; `locations list --offset 2` exits 2 with the measured wording and `--all` returns 3; `call-park list-available-users` and `hunt-group list` (declare `start`) still return items 2–4 for `--offset 2 --limit 3`. Pinned by `tests/test_paging_remedies.py` (`test_walker_without_spec_start_refuses_offset_by_spec`, `test_spec_rule_skips_unpaged_lists`, `test_spec_rule_skips_translated_lists`, `test_spec_rule_accepts_offset_named_offset`) and the generator snapshot (`tests/fixtures/expected_output.py`, whose `/things` declares only `max`).

**Still unmeasured:** the 82 that declare `start` (by correlation, expected to honour it) and the 34 refused by the rule. **Follow-up:** measure them on an org with data, the licences (CDR, Pro Pack) and the scopes they need; an "honours" result among the 34 would be the first exception and would need the opt-out override.

### Status

**Active** since 2026-10-13. Gate `--enforce` PASS, check 33 at 0.

---

## ADR-19: The Flow Store Surface Returns, from a Production-Reachable Host

### Decision

Revive the Flow Store as eight new Contact Center command groups — `cc-flow-store`, `cc-flow-versions`, `cc-flow-tracing`, `cc-flow-prefs`, `cc-flow-templates`, `cc-flow-projects`, `cc-flow-connectors` and `cc-functions` — generated from a new tracked spec, `specs/webex-cc-flow-store.json` (the snapshot of the service's own `GET /v3/api-docs`), plus hand-written extensions mounted through `_lazy.GROUP_EXTENSIONS` (`cc-flow` authoring commands, `cc-functions test`). The default Flow Store base is `https://flow-store.produs1.ciscoccservice.com/flow-store` (`FLOW_STORE_DEFAULT_URL`, `src/wxcli/config.py`), overridable with the `flow_store_url` profile setting or `WXCLI_FLOW_STORE_URL`. Where an existing `cc-flow` or `cc-legacy-flows` command already performs the same operation and a live test showed the same result, that command wins and the Flow Store copy is not generated (P2-1). The old `webex-flow-store.json` and the `fs-*` groups stay retired and forbidden.

### Context

Three Flow Store hostnames have been tried. ADR-11 measured two: `flow-store.intgus1.ciscoccservice.com` is Cisco's integration environment and rejects production tokens (401 `FAIL_VALIDATE_TOKEN`), and `flow-store.us1.ciscoccservice.com` does not resolve. The third, `flow-store.produs1.ciscoccservice.com`, answered a production token on 2026-10-18 (merge spec §10.5), and `docs/merge/flow-store-host-map.md` (Plan 2 Task 3, read-only, the sandbox tenant, 2026-10-19) measured it against every GET the spec declares: all 47 were `ROUTED` or `ERRORED` by the service itself, and the 5 `AUTH` cells are `/admin/*` and `/metrics`, service-admin surfaces outside the revival. The same run measured the Contact Center gateway (`api.wxcc-us1.cisco.com`, with and without `/flow-store`): it routes 14 of the 47 GETs, answers `/metrics` with 403, and returns an empty-body 404 from `istio-envoy` for the other 32. ADR-11's two hosts were re-probed in that run (intgus1: 404 on the path tried; us1: DNS failure). So both statements hold: ADR-11's facts stay true; its reasoning never reached `produs1`.

### Alternatives Considered

- **Keep `wxcc_flow` as a second package** that owns this surface. *Rejected:* two generators, two sign-ins and two `init` commands to maintain; the merge spec (§10.3) calls for one package and one command.
- **A host per operation** (gateway where it routes, Flow Store host elsewhere). *Rejected:* the host map shows the Flow Store host answers every operation, so a second host would add a code path with no operation that needs it.
- **Make the gateway the only surface** (`{cc_base_url}/flow-store`, the default P2-8 allowed if the gateway handled every operation). *Rejected:* 32 of 47 GETs have no route on it. Task 5 Step 2b (three non-persisting gateway write probes) was **not run**: it was conditional on the gateway covering every read, and 24 of the 29 reads wxcc's fate table moves into wxcli are `UNROUTED` there. The seven persisting writes (fate-table rows 9, 10, 11, 13, 44–46) were never probed on any host.
- **Re-add the old `webex-flow-store.json`.** *Rejected:* its name is the tripwire ADR-11 built; the new snapshot has its own name (P2-5), which matches the generator's `webex-*.json` glob.

### Rationale

- ADR-11 named three conditions for reviving the surface: a new decision (this ADR), a production-reachable host (the host map), and a `SPEC_PRODUCT` entry (`"webex-cc-flow-store.json": "Contact Center"`, `tools/command_renderer.py`). All three now hold.
- One host that answers everything is the smallest thing that works, and it is the one Adam chose (P2-8, 2026-10-19).
- The overlap rule keeps one command per operation (merge spec §7.4), so the new groups carry only what `cc-flow` and `cc-legacy-flows` did not already do.

### Consequences

**Enables:** every Flow Store read and write wxcc offered, from `wxcli`, with one sign-in; `docs/merge/wxcc-flow-command-map.md` maps each old command to its new one.
**Needs a human:** `tools/update-specs.py` downloads seven named specs and never this one, so the weekly routine does not refresh it. `tools/spec_sync.py` still re-renders it, because it is tracked, but from the committed snapshot. Refresh it by hand with `python -m tools.flow_store_spec diff --exit-code`, then `pull`, then regenerate (`tools/CLAUDE.md` § Flow Store spec).
**Region:** the default host is a US host. A tenant outside the US sets `flow_store_url` (or `WXCLI_FLOW_STORE_URL`) to its region's Flow Store base. The value `"{cc_base_url}/flow-store"` follows the saved CC region (`wxcli set-cc-region`), but it reaches only the 14 operations the gateway routes; do not use it as a general default.
**Forecloses:** nothing new. `webex-flow-store.json` stays forbidden: `.gitignore` keeps both ADR-11 patterns, and `tests/test_command_naming_residue.py` still fails on a copy.
**Gotchas:** the Flow Store service returned JSON 500 for `cc-flow-versions show-draft` (a flow never edited since publishing) and `list-all-latest`, and JSON 404 for `cc-flow-projects show` and `cc-flow-connectors list` on the system-provisioned project (host map). These are service answers, not routing failures.

### Status

**Active** since 2026-10-19. **Amends ADR-11** (its "Forecloses: using the Flow Store API from wxcli" no longer holds; its host findings do). Gate `--enforce` result is recorded in `docs/merge/plan-2-decisions.md`.

---

## Decision Cross-Reference

| ADR | Interacts With | Nature of Interaction |
|-----|---------------|----------------------|
| ADR-1 (Generated commands) | ADR-2 (Raw HTTP) | Generated commands use `WebexSession` — the raw HTTP client is the execution layer for generated code |
| ADR-1 (Generated commands) | ADR-7 (Field overrides) | Overrides customize generated output without modifying the generation template |
| ADR-2 (Raw HTTP) | ADR-5 (Async engine) | Two independent HTTP stacks: sync `httpx` for CLI, async `aiohttp` for migration execution |
| ADR-3 (SQLite store) | ADR-4 (NetworkX DAG) | DAG is persisted to SQLite (`plan_operations` + `plan_edges` tables) |
| ADR-3 (SQLite store) | ADR-6 (Pipeline split) | Each pipeline layer reads/writes through the store — it's the integration point |
| ADR-4 (NetworkX DAG) | ADR-5 (Async engine) | DAG determines execution order; engine executes in that order with concurrency |
| ADR-6 (Pipeline split) | ADR-8 (Playbook) | Advisory layer produces decisions that the Opus migration-advisor agent expands interactively |
| ADR-8 (Playbook) | ADR-1 (Generated commands) | Skills reference specific `wxcli` commands — coupling between prompt layer and CLI surface |
| ADR-9 (Spec sync + drift gate) | ADR-1 (Generated commands) | Retires ADR-1's "registration is manual" gotcha; regen becomes one atomic operation |
| ADR-9 (Spec sync + drift gate) | ADR-8 (Playbook) | Gate check 2 enforces that skills only cite commands the built CLI resolves |
| ADR-10 (PyPI distribution) | ADR-1 (Generated commands) | setuptools-scm stamps the built wheel; the release workflow's version guard protects that stamp |
| ADR-10 (PyPI distribution) | ADR-8 (Playbook) | The playbook stays repo-hosted, so the `git clone` source install is retained alongside the PyPI CLI install |
| ADR-11 (Flow Store retired) | ADR-9 (Spec sync + drift gate) | Removes the dev-only spec exemption (`--dev-only`, the fs audit); `SPEC_PRODUCT`'s unknown-spec raise is what keeps the retired spec out of every regen |
| ADR-12 (Paging flags translated) | ADR-1 (Generated commands) | The translation is emitted by the renderer per endpoint paging style; the runtime half lives in `auth.py` so a regen cannot drift from it |
| ADR-13 (Static checks 23-30) | ADR-9 (Spec sync + drift gate) | Eight more gated checks in the gate the weekly routine already runs; a hit fails closed, since the fixes sit in generator paths the routine may not edit |
| ADR-13 (Static checks 23-30) | ADR-12 (Paging flags translated) | Check 23 gates the paging translation: a list flag sent under a name the endpoint does not declare fails the build |
| ADR-14 (Single-object list GETs) | ADR-13 (Static checks 23-30) | Extends ADR-13 item 2 from flat objects to objects carrying an array; check 31 gates what check 27 could not see (a key that reaches one array of an object) |
| ADR-15 (POST/PATCH not retried on 5xx) | ADR-2 (Raw HTTP) | The retry loop lives in the sync `WebexSession` that ADR-2 keeps as the CLI's execution layer; the rule is by HTTP method, not by endpoint |
| ADR-14 (Single-object list GETs) | ADR-12 (Paging flags translated) | Only GETs with no declared paging are re-rendered, so no command that ADR-12's translation serves loses `--offset`/`--limit`/`--all` |
| ADR-16 (Query-declared body lifted) | ADR-13 (Static checks 23-30) | Check 32 follows ADR-13's rules (static, `BLIND`, no ack); the gate's body readers now see the lifted body, so check 30 judges these six commands' doc bodies for the first time |
| ADR-16 (Query-declared body lifted) | ADR-14 (Single-object list GETs) | Same policy as the ADR-14 amendment: an option the regen made meaningless (`--team-dto`) stays accepted, hidden and ignored rather than becoming "No such option" |
| ADR-17 (`--verify` subset compare) | ADR-1 (Generated commands) | The generator types numeric body flags as `str`; `verify_write` normalises `'30'`/`30` rather than depending on that typing, so it stays correct if the generator changes |
| ADR-18 (Note names offered remedies; check 33) | ADR-12 (Paging flags translated) | Narrows ADR-12's "the note names `--offset` everywhere" to commands whose `--offset` works; the translated page-numbered/SCIM `--offset` cannot be declared ignored |
| ADR-18 (Note names offered remedies; check 33) | ADR-14 (Single-object list GETs) | The hidden inert `--all` on single-object `list*` reads counts as not offered, so their note names no remedy |
| ADR-18 (Note names offered remedies; check 33) | ADR-13 (Static checks 23-30) | Check 33 follows ADR-13's rules (static, `BLIND`, no ack); the live-only half (which servers ignore `start`) is a declared, measured override set instead |
| ADR-19 (Flow Store returns) | ADR-11 (Flow Store retired) | Amends it: ADR-11's revival conditions (new decision, production-reachable host, `SPEC_PRODUCT` entry) are met; the `fs-*` groups and `webex-flow-store.json` stay retired |
| ADR-19 (Flow Store returns) | ADR-9 (Spec sync + drift gate) | `spec_sync.py` re-renders the new tracked snapshot, but `update-specs.py` never downloads it; refresh is by hand with `tools/flow_store_spec.py` |

---

## Open Questions

1. **Why Typer over Click directly?** The codebase uses Typer (which wraps Click). The generator produces Typer commands. But Click would work equally well and is more widely known. Was Typer chosen for its auto-help generation, type annotation support, or another reason? *Inferred: likely the type annotation support — generated commands use typed function signatures that Typer converts to CLI options automatically.*

### Resolved Questions

2. **~~Why Python 3.14 minimum?~~** Resolved 2026-05-27. No 3.14-specific features were used — the constraint was simply "latest stable at development time." Relaxed to `>=3.11` in `pyproject.toml`.

3. **~~Why default concurrency of 20 for migration vs. 5 for cleanup?~~** Resolved 2026-05-27. Intentional: the migration engine uses async `aiohttp` with a semaphore, so 20 concurrent calls are cheap and the 429 retry logic handles backoff dynamically. Cleanup uses a synchronous `ThreadPoolExecutor` where 5 threads is the practical ceiling. Different execution models justify different defaults.

4. **~~Why no shared HTTP infrastructure between CLI and migration?~~** Resolved 2026-05-27. Intentional divergence driven by requirements: CLI commands are sequential user-facing operations (sync `httpx` is sufficient), while the migration engine runs hundreds of concurrent API calls (async `aiohttp` with cooperative rate limiting is necessary). The migration engine was built after the CLI was stable, and sharing HTTP infrastructure would have forced unnecessary async complexity into the CLI or unnecessary sync constraints into the migration engine. Isolation is a feature — a breaking change in one doesn't affect the other.
