# Postman↔Spec Sync Report: Contact Center — 2026-03-28

## Summary
- Collection analyzed: Webex Contact Center (fork `15086833-a864a970-27a6-41ad-89d4-cf794012bbcc`)
- Total Postman requests: 468 (41 unique Journey ops + 390 non-Journey = 431 unique; 37 duplicated across Journey parent + sub-folders)
- Total spec operations: 431
- Matched: 48 folders/tags (all 54 after merge)
- Count mismatches: 0
- New in Postman (not in spec): 0
- Missing from Postman: 0

**Day-zero baseline.** The spec was generated from this collection on 2026-03-28. All folders are in full sync. The Postman collection has 468 requests but 37 are duplicates (same endpoint in both the main Journey folder and a sub-folder). The spec correctly dedupes to 431 unique operations. All 7 Journey sub-folder tags are properly assigned and merged into `cc-journey` via `tag_merge`.

## Staleness Check
| Collection | Postman Updated | Spec Modified | Delta |
|------------|----------------|---------------|-------|
| Webex Contact Center | 2026-03-28T02:42:31Z | 2026-03-28T13:09:09 (local) | Same day (baseline) |

## Contact Center Diff Table

### Matched (48)

| Folder/Tag | Postman Reqs | Spec Ops | Status | Notes |
|------------|-------------|----------|--------|-------|
| AI Assistant | 1 | 1 | MATCHED | |
| AI Feature | 3 | 3 | MATCHED | |
| Address Book | 19 | 19 | MATCHED | |
| Agent Personal Greeting Files | 13 | 13 | MATCHED | |
| Agent Summaries | 2 | 2 | MATCHED | |
| Agent Wellbeing | 5 | 5 | MATCHED | |
| Agents | 11 | 11 | MATCHED | |
| Audio Files | 7 | 7 | MATCHED | |
| Auto CSAT | 8 | 8 | MATCHED | |
| Auxiliary Code | 11 | 11 | MATCHED | |
| Business Hour | 9 | 9 | MATCHED | |
| Call Monitoring | 7 | 7 | MATCHED | |
| Callbacks | 5 | 5 | MATCHED | |
| Campaign Manager | 3 | 3 | MATCHED | |
| Captures | 1 | 1 | MATCHED | |
| Contact List Management | 5 | 5 | MATCHED | |
| Contact Number | 8 | 8 | MATCHED | |
| Contact Service Queue | 23 | 23 | MATCHED | |
| Data Sources / CC Data Sources | 7 | 7 | MATCHED | Renamed: "Data Sources" → "CC Data Sources" |
| Desktop Layout | 9 | 9 | MATCHED | |
| Desktop Profile | 10 | 10 | MATCHED | |
| DNC Management | 3 | 3 | MATCHED | |
| Dial Number | 12 | 12 | MATCHED | |
| Dial Plan | 9 | 9 | MATCHED | |
| Entry Point | 10 | 10 | MATCHED | |
| Estimated Wait Time | 1 | 1 | MATCHED | |
| Flow | 4 | 4 | MATCHED | |
| Generated Summaries | 3 | 3 | MATCHED | |
| Global Variables | 10 | 10 | MATCHED | |
| Holiday List | 9 | 9 | MATCHED | |
| Journey | 39 | 39 | MATCHED | Merges into CC Journey via tag_merge |
| Multimedia Profile | 10 | 10 | MATCHED | |
| Notification | 1 | 1 | MATCHED | |
| Outdial ANI | 16 | 16 | MATCHED | |
| Overrides | 9 | 9 | MATCHED | |
| Queues | 1 | 1 | MATCHED | |
| Realtime | 1 | 1 | MATCHED | |
| Resource Collection | 8 | 8 | MATCHED | |
| Search | 1 | 1 | MATCHED | |
| Site / CC Site | 10 | 10 | MATCHED | Renamed: "Site" → "CC Site" |
| Skill | 10 | 10 | MATCHED | |
| Skill Profile | 9 | 9 | MATCHED | |
| Subscriptions | 12 | 12 | MATCHED | |
| Tasks | 24 | 24 | MATCHED | |
| Team | 10 | 10 | MATCHED | |
| User Profiles | 17 | 17 | MATCHED | |
| Users | 14 | 14 | MATCHED | |
| Work Types | 9 | 9 | MATCHED | |

### Count Mismatches (0)

None. *(Originally 2 — fixed by re-tagging Journey ops from parent to correct sub-folder tags.)*

### New in Postman (0)

None. *(Originally 4 — the "missing" sub-folder ops were present in the spec but mistagged under the parent "Journey" tag. Fixed by re-tagging.)*

### Missing from Postman (0)

None.

## Journey Family Detail

The Journey family accounts for the entire delta between Postman (468) and spec (431).

| Source | Journey Requests/Ops | Non-Journey Requests/Ops |
|--------|---------------------|--------------------------|
| Postman | 78 (37 duplicated across parent + sub-folders) | 390 |
| Spec | 41 unique (across 7 tags, merged into cc-journey) | 390 |
| Delta | 0 (duplicates accounted for) | 0 |

**Root cause of original delta:** The Postman-to-OpenAPI converter collapsed all Journey sub-folder tags into the parent `Journey` tag. The 37 "missing" operations were always present — just mistagged. Fixed by re-tagging operations to their correct sub-folder names using the Postman folder data as the source of truth.

**tag_merge in field_overrides.yaml** merges all 7 tags into `CC Journey`:
- `Journey` (2 ops unique to parent)
- `Journey - Customer Identification API` (9 ops)
- `Journey - Profile Creation & Insights API` (14 ops)
- `Journey - Data Ingestion API` (1 op)
- `Journey - Subscription API` (3 ops)
- `Journey - Trigger Actions API` (7 ops)
- `Journey - Workspace management API` (5 ops)

This yields **41 CLI commands** in the `cc-journey` group — all unique operations accounted for.

## Recommendations

1. **No action needed.** All 54 Postman folders (48 non-Journey + 7 Journey sub-folders, minus the parent) are in full sync with the spec after re-tagging and deduplication.
2. **Future syncs:** The 468→431 Postman-to-spec delta is permanent — it reflects 37 duplicate requests in the Postman collection, not missing spec operations.
4. **Set this report as the sync baseline.** Future periodic sync reports for the Contact Center collection should diff against this day-zero snapshot.
