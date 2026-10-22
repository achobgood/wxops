# Webex Connect — Response Codes Reference

<!-- ref-tag: connect-response-codes-v2 -->

The single owner for Webex Connect response codes. Every other file — playbook,
skill or reference — cites this one rather than restating the table.

**Why this file exists.** These codes previously lived only in
`docs/playbooks/webhook-triggers.md` and two skill `reference.md` files. The
three copies drifted: one carried 6 codes while another carried 13 (backlog item
B14), and the two skill copies still disagreed about whether `7010` had been
verified against Cisco. Codes are platform facts Cisco can change, so under
`.claude/rules/doc-placement.md` § The Second Test they cannot be owned by a
skill.

---

## Inbound Webhook / Event API Response Codes

Returned by the inbound webhook endpoint when an external system triggers a flow.
The response confirms the request was **queued** — it does not carry the flow's
output. See `docs/playbooks/webhook-triggers.md` § Response Behavior for what
that means when designing a caller.

| Code | Meaning | Provenance |
|------|---------|------------|
| 1002 | Queued — request accepted | Repo record |
| 7000 | Invalid JSON | Repo record |
| 7001 | Authentication failed | Repo record |
| 7002 | Service Key missing | Repo record |
| 7005 | Internal error | Repo record |
| 7007 | Service inactive | Repo record |
| 7008 | **Inactive profile** — "Returned when the profile is inactive" | Cisco, verified 2026-07-25 |
| 7010 | **Source IP is not in the allowed list** | Cisco, verified 2026-07-25 |
| 7020 | Max transaction limit reached | Repo record |
| 7027 | Invalid XML | Repo record |
| 7028 | Invalid signature | Repo record |
| 7029 | Mandatory Signature Missing | Repo record |
| 430 | Payload too large | Repo record |

### Provenance — read before "correcting" a row

The **Provenance** column is load-bearing. "Repo record" means the meaning came
from this repo's own working notes, not from a Cisco page — it may be an
in-the-wild observation, and it may be wrong. Do not upgrade a row to "Cisco" on
plausibility; upgrade it only after fetching
`https://help.webexconnect.io/docs/references-api-codes` and quoting the string.

- **`7008` carries an unresolved conflict.** Cisco's canonical wording is
  "**Inactive Profile** — Returned when the profile is inactive." [source:
  https://help.webexconnect.io/docs/references-api-codes, fetched 2026-07-25].
  This repo previously recorded it as "Invalid or unsaved event endpoint". Both
  are retained deliberately: Cisco's leads because it is canonical, ours is kept
  because its provenance may be a real observation and a deleted claim cannot
  later be confirmed. **Which applies to inbound webhooks specifically is
  unconfirmed** [backlog § Decisions taken 2026-07-25].
- **`7010` is Cisco-verified.** It reads "Source IP is not in the allowed list"
  on `references-api-codes` (Event section), corroborated by the v6.4.0
  changelog. ⚠ It is **not** listed in `webhook-triggers.md`, and
  `build-notification/reference.md` carried a stale note calling it
  audit-sourced-only; that note was wrong and is corrected. Confirmed live
  2026-07-25 per backlog § 4b (`a534aa3`, `720594f`).
- **`7027` / `7028` / `7029` are NOT on Cisco's `references-api-codes` page** and
  keep playbook-only provenance [backlog § 4b]. Do not cite Cisco for them.

---

## Channel Delivery Error Codes

Returned on a channel node's failure exit path, not by the webhook endpoint.
These are owned by their channel's reference doc, because each is meaningful only
against that channel's delivery model:

| Code | Channel | Owner |
|------|---------|-------|
| 7281 ⚠ | SMS — 10DLC campaign error, sender not registered (⚠ **unverified** — see below) | `connect-sms.md` § Status Codes |
| 7535 | Email — total message size threshold exceeded | `connect-email.md` |
| 7845 | WhatsApp — throughput exceeded | `connect-whatsapp.md` |
| 7865 | WhatsApp — recipient not on WhatsApp | `connect-whatsapp.md` |

⚠ **`7281` is unverified — do not branch on it.** The **US 10DLC registration
requirement itself is confirmed**; the mapping of that rejection to the specific
code `7281` is not. `7281` was **not found on any public help.webexconnect.io
page** [`docs/tests/findings/outbound-sms-findings.md` § Items Not Verifiable
#1]. The owner carries the same ⚠ at `connect-sms.md` § US A2P 10DLC
Registration and § Status Codes. It is listed here rather than dropped because a
deleted claim cannot later be confirmed — but **do not build Branch logic that
matches on `7281`** until you have confirmed it against a real rejected send on
your tenant. Without this note the row read as solid purely by contrast with the
hedged `7845` two lines below.

⚠ **`7845`'s wording is unresolved** — our text says "messaging tier", and no
source for the platform's real error string has been found. Tracked in the
backlog as an open item; do not assert the wording.

### Scoping — the two tables are separate numbering spaces, and they collide

**A code in this section and the same number in the section above are not
necessarily the same code.** Inbound webhook / Event API response codes and
per-channel delivery error codes are **independent numbering spaces** that both
draw on the `7xxx` range, so the same number can carry entirely different
meanings depending on which one you are reading.

The clearest live example: **`7010`**.

| Where | Meaning | Provenance |
|---|---|---|
| § Inbound Webhook / Event API (above) | Source IP is not in the allowed list | Cisco, verified 2026-07-25 |
| `connect-rcs.md` § (RCS delivery codes) | Service provider exception | Channel doc |

**This is a scoping gap, not a contradiction, and neither value should be
"corrected" to the other.** The same pattern already holds for `7281`, `7535`
and `7845`, which exist only as channel-delivery codes. Before acting on any
`7xxx` code, establish **which** table it came from: an endpoint response to a
caller triggering a flow → the table above; a value on a channel node's failure
exit path or in a delivery report → this table and the owning channel doc.

---

## References

- Cisco API codes: https://help.webexconnect.io/docs/references-api-codes
- Webhook trigger procedure: `docs/playbooks/webhook-triggers.md`
- Webhook authentication: `connect-auth.md`

## See Also

- [connect-auth.md](connect-auth.md) — the inbound authentication mechanisms whose failures produce these codes
- [connect-sms.md](connect-sms.md) — SMS delivery status codes
- [webhook-triggers.md](../playbooks/webhook-triggers.md) — the inbound webhook setup that returns these codes
