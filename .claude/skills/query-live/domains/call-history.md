# Call History Domain

**Covers:** Recent call history, call volume, missed calls, busiest hours, voicemail-bound calls.

**This is a delegation module.** For call history and CDR questions, load the `reporting` skill and use its CDR recipe composition guide. The reporting skill has 75 pre-built recipes covering volume analysis, location breakdowns, hourly trends, agent performance, and threshold detection.

## When to Delegate

Any question about **past calls** or **call patterns** should use the reporting skill:
- "How many calls did we get yesterday?"
- "Show me missed calls from this morning"
- "What's our busiest hour for incoming calls?"
- "How many calls went to voicemail last week?"
- "What's our average call duration?"
- "Which agent handled the most calls?"

## How to Delegate

Load the reporting skill:

```
Skill: reporting
```

The reporting skill will:
1. Verify the token has `spark-admin:calling_cdr_read` scope
2. Check for cached CDR data at `/tmp/cdr-session.json`
3. Pull CDR data for the requested time range
4. Run the appropriate recipe or compose a custom query
5. Format the results

## Constraints to Communicate

When answering CDR-related questions, note these limits if relevant:
- **30-day retention window** — CDR data is only available for the last 30 days
- **12-hour max query window** — each API request covers at most 12 hours; the skill handles splitting automatically
- **~15 minute delay** — very recent calls (last 15 minutes) may not appear yet

## Not CDR — Handle Inline

These look like call history but are actually config queries handled by other domains:
- "Is call recording enabled for John?" → people-and-settings domain (wxcli user-settings show-call-recording)
- "What's the call queue overflow setting?" → features domain (wxcli call-queue show)
- "Show me the after-hours routing" → call-flow-trace domain
