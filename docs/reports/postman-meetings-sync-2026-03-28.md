# Postman↔Spec Sync Report — Meetings — 2026-03-28

## Summary
- Collections analyzed: 1 (Webex Meetings)
- Total Postman requests: 167
- Total spec operations: 149 (in spec file), 139 generated (17 tags)
- Cross-spec skipped: 5 tags (28 ops) — already generated from other specs
- Count mismatches: 0
- Missing from Postman: 0

## Staleness Check

| Collection | Postman Updated | Spec Created | Delta |
|------------|----------------|--------------|-------|
| Meetings | 2026-03-28 | 2026-03-28 | 0 days (day-zero baseline) |

## Meetings Collection

### Matched (17 tags — all generated into CLI groups)

| Folder/Tag | Postman Reqs | Spec Ops | CLI Group | Status |
|------------|-------------|----------|-----------|--------|
| Chats | 2 | 2 | `meeting-chats` | MATCHED |
| Closed Captions | 3 | 3 | `meeting-captions` | MATCHED |
| Invitees | 6 | 6 | `meeting-invitees` | MATCHED |
| Meeting Polls | 3 | 3 | `meeting-polls` | MATCHED |
| Meeting Q and A | 2 | 2 | `meeting-qa` | MATCHED |
| Meetings | 46 | 46 | `meetings` | MATCHED |
| Meetings Summary Report | 2 | 2 | `meeting-reports` | MATCHED |
| Messages | 1 | 1 | `meeting-messages` | MATCHED (tag renamed to "Meeting Messages" in spec) |
| Participants | 7 | 7 | `meeting-participants` | MATCHED |
| Preferences | 14 | 14 | `meeting-preferences` | MATCHED |
| Session Types | 3 | 3 | `meeting-session-types` | MATCHED |
| Site | 2 | 2 | `meeting-site` | MATCHED |
| Slido Secure Premium | 1 | 1 | `meeting-slido` | MATCHED |
| Summaries | 3 | 3 | `meeting-summaries` | MATCHED |
| Tracking Codes | 7 | 7 | `meeting-tracking-codes` | MATCHED |
| Transcripts | 7 | 7 | `meeting-transcripts` | MATCHED |
| Video Mesh | 30 | 30 | `video-mesh` | MATCHED |

### Cross-Spec Skipped (5 tags — intentionally excluded)

| Folder | Postman Reqs | Reason | Already In |
|--------|-------------|--------|-----------|
| People | 6 | In spec but auto-skipped via `skip_tags` | Admin spec → `people` |
| Recording Report | 4 | In spec but auto-skipped via `skip_tags` | Calling/Admin spec → `recording-report` |
| Recordings | 12 | Removed from spec (100% path overlap) | Admin spec → `admin-recordings` |
| Webhooks | 5 | Removed from spec (100% path overlap) | Messaging spec → `webhooks` |
| Meeting Qualities | 1 | Removed from spec (100% path overlap) | Admin spec → `meeting-qualities` |

## Recommendations

None — this is a day-zero baseline. All 22 Postman folders are accounted for (17 matched + 5 cross-spec skipped). Zero count mismatches. Future sync reports should compare against this baseline.
