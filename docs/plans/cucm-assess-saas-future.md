# CUCM Assessment Platform — SaaS Future Plan (Approach C)

**Date:** 2026-03-24
**Status:** Future — build only after Approach B (CLI + PDF report) proves the concept
**Prerequisite:** `cucm-assess` CLI tool shipped, sample reports validated with real customers

---

## Vision

A web platform where partners upload collector output (or enter CUCM credentials), the platform runs the assessment pipeline, and customers get a branded, interactive report. Partners manage multiple customer assessments from a single dashboard.

## Why Wait

Approach C is the right product only after Approach B proves:
1. The complexity score is trusted (calibrated against real environments)
2. The report actually changes customer behavior (they choose Webex over Teams)
3. Partners adopt the CLI tool (validates demand)
4. The collector works reliably across CUCM versions (validates data quality)

Building the platform before proving the report is premature — it's infrastructure for an unvalidated product.

## Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│   Web UI    │────>│   API Server          │────>│  Assessment Engine  │
│  (React)    │     │  (FastAPI)            │     │  (existing pipeline)│
│             │<────│                      │<────│                    │
│  Dashboard  │     │  Auth, multi-tenant   │     │  Report Generator  │
│  Reports    │     │  Job queue, storage   │     │  (existing)        │
└─────────────┘     └──────────────────────┘     └────────────────────┘
                            │
                    ┌───────┴───────┐
                    │   Storage     │
                    │  PostgreSQL   │
                    │  S3 (reports) │
                    └───────────────┘
```

### Key Components

**Web UI (React/Next.js)**
- Partner dashboard: list of customer assessments, status, scores
- Upload flow: drag-and-drop collector file, or enter CUCM credentials for direct connect
- Interactive report viewer: same content as PDF but with expandable sections, sortable tables, filterable inventory
- PDF download: server-generated, identical to CLI output
- Branding: partner uploads their logo, it appears on reports

**API Server (FastAPI)**
- Authentication: partner accounts, API keys
- Multi-tenancy: partner → customer → assessment hierarchy
- Job queue: assessment runs are async (Celery/Redis or similar)
- Storage: PostgreSQL for metadata, S3 for collector files and generated reports
- Webhooks: notify partner when assessment is complete

**Assessment Engine**
- Identical to the CLI pipeline. The API server calls the same Python modules.
- Each assessment gets its own SQLite store (same as CLI), archived to S3 after completion.
- Report generator produces the same HTML, served directly or converted to PDF.

### Multi-Tenancy Model

```
Partner Account (Acme IT Solutions)
├── Customer: Contoso Corp
│   ├── Assessment: 2026-03-24 (Score: 34, Straightforward)
│   └── Assessment: 2026-04-15 (Score: 31, Straightforward) — re-assessed after cleanup
├── Customer: Fabrikam Inc
│   └── Assessment: 2026-03-28 (Score: 48, Moderate)
└── Customer: Woodgrove Bank
    └── Assessment: 2026-04-01 (Score: 22, Straightforward)
```

Partners see all their customers. Customers see only their own assessments (if given access). Assessments are immutable once generated — re-assessment creates a new entry so progression is tracked.

## Business Model Options

| Model | Pricing | Pros | Cons |
|---|---|---|---|
| **Free tier + paid** | Free: 3 assessments/month, PDF only. Paid: unlimited, interactive reports, API access, branding | Drives adoption, monetizes power users | Must support free users |
| **Per-assessment** | $X per assessment | Simple, usage-based, predictable | Discourages re-assessment (bad for customer) |
| **Partner subscription** | $X/month per partner seat | Predictable revenue, unlimited assessments | Harder to sell to small partners |
| **Freemium with execution upsell** | Assessment free, charge for migration execution support | Assessment is the lead gen, execution is the revenue | Need execution product (wxcli already does this) |

**Recommendation:** Free tier + paid. The free tier is the growth engine. Partners who use it for 3 assessments and close deals will pay for unlimited.

## Features Beyond CLI

Things the platform can do that the CLI can't:

1. **Trend tracking** — re-assess the same customer quarterly. Show how cleanup work reduced complexity.
2. **Portfolio view** — partner sees all customers ranked by complexity. Prioritize easy migrations first to build momentum.
3. **Benchmarking** — "Your score of 34 is better than 72% of CUCM environments we've assessed." (Requires anonymized aggregate data.)
4. **Collaboration** — share assessment with customer stakeholders. They can view the report without installing anything.
5. **Direct-to-customer flow** — customer runs collector, uploads to platform themselves, gets report. Partner is CC'd.
6. **API access** — programmatic assessment for partners with automation workflows.

## Technical Considerations

### Security
- Collector files contain CUCM configuration data (user names, extensions, device pools). Must be encrypted at rest and in transit.
- AXL credentials (if direct-connect mode) must never be stored. Used once, discarded.
- SOC 2 compliance likely required for enterprise partners.
- Data residency: customers may require data stays in-region.

### Scale
- Each assessment takes 2-5 minutes of compute (normalize + analyze + report). Job queue handles concurrency.
- SQLite-per-assessment is fine for the engine. PostgreSQL for platform metadata only.
- S3 for durable storage of collector files and reports.

### Migration from CLI
- The CLI tool remains the primary interface. The platform is additive, not replacement.
- Same pipeline code, same report output. Platform wraps it in a web UI and adds multi-tenancy.
- Partners who prefer CLI continue using it. Platform users get the same quality.

## Build Phases (Rough)

| Phase | Scope | Estimate |
|---|---|---|
| 1. API wrapper | FastAPI server wrapping existing pipeline, file upload, async jobs | Medium |
| 2. Basic web UI | Upload → assess → view report. No auth, single-user. | Medium |
| 3. Auth + multi-tenancy | Partner accounts, customer hierarchy, access control | Medium |
| 4. Interactive reports | HTML report with expandable sections, sorting, filtering | Medium |
| 5. Dashboard | Portfolio view, trend tracking, partner branding | Medium |
| 6. Benchmarking | Anonymized aggregate scoring, percentile ranking | Small |
| 7. Production hardening | SOC 2, encryption, monitoring, data residency | Large |

## Decision Gate

Build Approach C only when ALL of the following are true:
- [ ] 10+ real customer assessments completed via CLI tool
- [ ] At least 3 partners using the CLI tool independently
- [ ] Positive feedback on report quality from customer-facing meetings
- [ ] Complexity score calibration validated (scores match intuitive difficulty)
- [ ] Clear demand signal for multi-customer management or web access
