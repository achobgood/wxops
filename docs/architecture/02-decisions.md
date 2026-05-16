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
3. **Typed SDK wrapper (wxc_sdk's API classes).** Already exists upstream. But SDK coverage lags the API by weeks to months, and typed methods cover a subset of the surface. Would create a hard dependency on SDK release cadence.

### Rationale

A custom generator gives full control over the CLI UX (output formatting, pagination, orgId injection) while keeping the API surface area as a "pull from spec" operation. The generator produces 208 command files — one per OpenAPI tag — following a fixed template. When Cisco updates the spec, re-running the generator updates all commands. The `field_overrides.yaml` layer (ADR-7) handles spec quirks without modifying the generator core.

The 8 hand-written exceptions exist because they require logic that a template cannot express:
- `cleanup.py` — 13-layer dependency ordering, parallel deletion, retry loops
- `converged_recordings_export.py` — file streaming, transcript extraction
- `cucm.py` — 16-command migration pipeline surface
- `configure.py`, `locations.py`, `numbers.py`, `licenses.py` — predate the generator (legacy)
- `update.py` — self-update via git pull

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
- Registration is manual: each generated file must be added to `main.py` via `app.add_typer()`
- The `Endpoint`/`EndpointField` dataclass contract between parser and renderer is a stable interface that constrains both sides

### Status

**Active.** 208 generated files, 8 hand-written. Generator has been extended incrementally (output formatting, orgId injection, JSON body support, CC specs) without a rewrite.

---

## ADR-2: Raw HTTP via REST Client vs. Typed SDK Methods

### Decision

Use synchronous `httpx` via a thin `WebexSession` wrapper for all CLI command HTTP calls, rather than wxc_sdk's typed API methods (e.g., `api.telephony.auto_attendants.list(...)`). The SDK dependency was subsequently removed entirely from `pyproject.toml`.

### Context

wxc_sdk (Cisco's official Python SDK) provides typed methods with Pydantic models for a subset of the Webex API surface. However, the CLI needs to cover the *full* API surface — including endpoints the SDK hasn't implemented yet, Contact Center APIs on a different host, and recently-added endpoints. The SDK also imposes its own auth patterns, pagination logic, and error types that would compete with the CLI's own conventions.

### Alternatives Considered

1. **Typed SDK methods exclusively.** Strong typing, auto-completion, response models. But SDK coverage is incomplete — new endpoints take weeks/months to appear. Would create a hard dependency on SDK release cadence.
2. **Typed SDK for covered endpoints, raw HTTP for the rest.** Gradual migration path. But creates two code paths with different error handling, pagination, and auth — complexity without benefit since the generated command template already handles raw HTTP uniformly.
3. **Raw HTTP via `requests`.** Simpler library, widely known. But `httpx` provides HTTP/2 support, better async story, and is the modern standard.
4. **Raw HTTP via `aiohttp` everywhere.** Better concurrency. But CLI commands are inherently sequential (user waits for output); async adds complexity without benefit for the primary use case. (The migration engine uses `aiohttp` independently — see ADR-5.)

### Rationale

From `docs/reference/wxc-sdk-patterns.md`: "The REST client gives us access to every endpoint from day one. Typed methods lag behind the API by weeks to months." Using raw HTTP means one code path for all commands — generated and hand-written alike. The generated command template constructs URLs, injects parameters, and formats output without any SDK abstraction in between.

The `WebexSession` wrapper provides just four methods: `rest_get()`, `rest_post()`, `rest_put()`, `rest_delete()`, plus `follow_pagination()` for list commands. This thin surface is a stable interface that 208+ command files depend on.

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
- The stale `requirements.txt` still references `wxc-sdk` as a transitive dependency — needs cleanup.

### Status

**Active.** The `wxc-sdk` dependency was removed from `pyproject.toml` (commit e4dfb22). All source files use `WebexSession` directly. Reference docs still describe wxc_sdk patterns for educational purposes.

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

---

## Open Questions

These gaps remain where rationale is genuinely unclear and should be confirmed with the original author:

1. **Why Typer over Click directly?** The codebase uses Typer (which wraps Click). The generator produces Typer commands. But Click would work equally well and is more widely known. Was Typer chosen for its auto-help generation, type annotation support, or another reason? *Inferred: likely the type annotation support — generated commands use typed function signatures that Typer converts to CLI options automatically.*

2. **Why Python 3.14 minimum?** `pyproject.toml` requires Python >= 3.14 (beta as of May 2026). The codebase uses `str | None` union syntax (available since 3.10) and possibly `type` statement syntax. Was 3.14 chosen for a specific language feature, or is it simply "latest stable at development time"? *This is a significant constraint that limits adoption.*

3. **Why default concurrency of 20 for migration vs. 5 for cleanup?** The migration engine defaults to 20 concurrent API calls, while `cleanup.py` uses ThreadPoolExecutor with a lower concurrency. Was 20 determined empirically against Webex rate limits, or is it arbitrary? *The 429 retry logic suggests it was tuned to push rate limits and back off dynamically rather than staying conservatively below them.*

4. **Why no shared HTTP infrastructure between CLI and migration?** The "two independent HTTP stacks" seam is documented but the rationale is inferred ("breaking change in one doesn't affect the other"). Was this an intentional decoupling decision from the start, or did it emerge organically as the migration engine's requirements diverged from CLI commands? *Git history suggests the migration engine was built after the CLI was stable, using aiohttp because async was needed — not as a deliberate architectural choice to avoid the existing stack.*
