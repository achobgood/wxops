# Postman↔Spec Sync Report: Contact Center — 2026-03-28

## Summary
- Collection analyzed: Webex Contact Center (fork `15086833-a864a970-27a6-41ad-89d4-cf794012bbcc`)
- Total Postman requests: 468
- Total spec operations: 431
- Matched: 48 folders/tags
- Count mismatches: 2 (Journey sub-folders — see notes)
- New in Postman (not in spec): 4 (Journey sub-folders — see notes)
- Missing from Postman: 0

**Day-zero baseline.** The spec was generated from this collection on 2026-03-28. Outside the Journey family, every folder/tag is in perfect 1:1 sync (390 requests = 390 operations). The 37-request delta is entirely within Journey sub-folders whose requests were collapsed into the main `Journey` tag during spec generation.

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

### Count Mismatches (2)

| Folder/Tag | Postman Reqs | Spec Ops | Status | Notes |
|------------|-------------|----------|--------|-------|
| Journey - Customer Identification API | 9 | 1 | COUNT MISMATCH | +8 in Postman; most collapsed into main Journey tag during spec gen. Merges into CC Journey. |
| Journey - Profile Creation & Insights API | 14 | 1 | COUNT MISMATCH | +13 in Postman; most collapsed into main Journey tag during spec gen. Merges into CC Journey. |

### New in Postman (4)

| Folder/Tag | Postman Reqs | Spec Ops | Status | Notes |
|------------|-------------|----------|--------|-------|
| Journey - Data Ingestion API | 1 | 0 | NEW IN POSTMAN | Not in spec; candidate for CC Journey merge |
| Journey - Subscription API | 3 | 0 | NEW IN POSTMAN | Not in spec; candidate for CC Journey merge |
| Journey - Trigger Actions API | 7 | 0 | NEW IN POSTMAN | Not in spec; candidate for CC Journey merge |
| Journey - Workspace management API | 5 | 0 | NEW IN POSTMAN | Not in spec; candidate for CC Journey merge |

### Missing from Postman (0)

None.

## Journey Family Detail

The Journey family accounts for the entire delta between Postman (468) and spec (431).

| Source | Journey Requests/Ops | Non-Journey Requests/Ops |
|--------|---------------------|--------------------------|
| Postman | 78 (across 7 folders) | 390 |
| Spec | 41 (across 3 tags) | 390 |
| Delta | +37 in Postman | 0 |

**Root cause:** During `generateSpecFromCollection`, the Postman-to-OpenAPI converter collapsed 6 Journey sub-folder request bodies into the main `Journey` tag (39 operations), leaving only stub entries (1 op each) for `Journey - Customer Identification API` and `Journey - Profile Creation & Insights API`. The 4 remaining sub-folders (`Data Ingestion API`, `Subscription API`, `Trigger Actions API`, `Workspace management API`) were not converted at all.

**tag_merge in field_overrides.yaml** currently merges 3 tags into `CC Journey`:
- `Journey` (39 ops)
- `Journey - Customer Identification API` (1 op)
- `Journey - Profile Creation & Insights API` (1 op)

This yields **41 CLI commands** in the `cc-journey` group vs **78 requests** in the Postman collection.

## Recommendations

1. **No action needed for non-Journey tags.** All 48 non-Journey folders are in perfect 1:1 sync with the spec. This is expected for a day-zero baseline.
2. **Investigate Journey sub-folder collapse.** Re-run spec generation for the Journey family with `--populate` or manual extraction to recover the 37 missing operations. The converter likely hit nested folder depth limits.
3. **Add 4 missing Journey sub-folders to tag_merge.** Once the missing operations are in the spec, update `field_overrides.yaml` tag_merge for `CC Journey` to include all 7 Journey sub-folders:
   ```yaml
   "CC Journey":
     - "Journey"
     - "Journey - Customer Identification API"
     - "Journey - Profile Creation & Insights API"
     - "Journey - Data Ingestion API"
     - "Journey - Subscription API"
     - "Journey - Trigger Actions API"
     - "Journey - Workspace management API"
   ```
4. **Set this report as the sync baseline.** Future periodic sync reports for the Contact Center collection should diff against this day-zero snapshot.
