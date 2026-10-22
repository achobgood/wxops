# Webex Connect — Inbound Authentication Reference

<!-- ref-tag: connect-auth-v2 -->

The single owner for how an **external caller authenticates to Webex Connect** —
service keys, JWT tokens, HMAC signature validation, IP allowlisting, credential
rotation, and the per-trigger-type rules that govern them.

**Scope boundary.** This file covers traffic coming *into* Connect. For Connect
authenticating *outward* to someone else's API (Custom Connectors, OAuth, Service
Apps), see `webex-connect.md` § Custom Connectors and
`docs/playbooks/webex-api-auth.md`. Response codes returned by these mechanisms
are owned by `connect-response-codes.md`.

---

## Authentication Is Optional — Except Where It Is Not

Cisco states that for **inbound webhooks** "authentication is not mandatory", but
that it should be selected "as a security best practice"
[source: https://help.webexconnect.io/docs/inbound-webhooks].

That is **not** true of every trigger type:

| Trigger type | Authentication | Notes |
|---|---|---|
| Inbound Webhook | **Optional** (service key, JWT, or signature) | Cisco recommends enabling it |
| Custom Event (v1) | **Mandatory** — service key | "A Service Key must be passed with every API request" |
| AI Agent Event | **Automatic** — Webex CI | Nothing to configure |

---

## Service Key

Passed in the request header:

```
key: {your_service_key}
```

Located at **Service dashboard > API tab**. Masked by default — click the eye
icon to reveal.

## JWT Token

Signed with **HMACSHA256** using the Base64-encoded Service Secret.

| Claim | Required | Value |
|---|---|---|
| `iss` | Yes | Service ID, as issuer |
| `iat` | Yes | Issued-at timestamp |
| `exp` | No | Expiry. Tokens expire after **60 minutes** regardless |

Passed in the same header as the service key: `key: {jwt_token}`.

| Fact | Official text | Source |
|---|---|---|
| **JWT lifetime** | *"The JWT token expires after 60 minutes from the time that you have generated the token."* | https://help.webexconnect.io/docs/service-key-and-jwt-authentication-tokens |
| **JWT wins over Service Key** | *"If you pass both JWT Authentication and Service Key in an API request, the JWT Authentication takes priority."* | same |
| **Rotation rule** | A second service key or JWT pair can be created for rotation, but *"At any point, you can have only one service key in Inactive status."* | same |

⚠ **If both a service key and a JWT are passed, the JWT takes priority.** A stale
JWT therefore silently overrides a correct service key.

## Signature Validation (HMAC)

- Optional signature validation on the **request body**. SHA-256 or SHA-512 per
  the API reference; the specific algorithms are **not** listed on the help pages
- Cisco describes these as "signatures within headers" that "help prevent
  man-in-the-middle type attacks"
  [source: https://help.webexconnect.io/docs/inbound-webhooks]
- Configured on the webhook definition, **independent** of service key / JWT —
  it is a third layer, not an alternative to the first two; the *location* of
  that setting is **not** described on the help pages
  [source: https://help.webexconnect.io/docs/inbound-webhooks]
- Failures return HTTP 400 with code `7029` (Mandatory Signature Missing) or
  `7028` (Invalid signature) [`connect-response-codes.md`]

## IP Allowlisting

The feature exists — code `7010` "Source IP is not in the allowed list" confirms
it [`connect-response-codes.md`]. **Configuration steps are not documented on any
official Cisco help page.** Do not invent them; ask the platform owner.

## Credential Rotation

To rotate without downtime: create a second service key or JWT key pair, migrate
callers to it, then retire the old one.

⚠ **The constraint that makes this fiddly:** "At any point, you can have only one
service key in Inactive status."
[source: https://help.webexconnect.io/docs/service-key-and-jwt-authentication-tokens].
You cannot stage several retired keys.

---

## Custom Event Authentication Rules

| Fact | Official text | Source |
|---|---|---|
| **Group scoping fails silently** | *"Custom events belonging to a specific group must use only that group's JWT Token or Service Key. Using different group credentials means the request is accepted, but the relevant flow won't trigger."* | https://help.webexconnect.io/docs/custom-events |
| **`evtid` is auto-generated** | *"An event ID (`evtid`) is auto-generated upon saving"* a custom event | same |
| **Service Key is mandatory** | *"A Service Key must be passed with every API request."* | same |

In plain terms
[source: https://help.webexconnect.io/docs/custom-events]:

1. **Event ID is auto-generated.** "An event ID (`evtid`) is auto-generated upon
   saving" the custom event. You do not choose it.
2. **Service Key is mandatory.** "A Service Key must be passed with every API
   request." Unlike inbound webhooks, authentication is not optional here.
3. **⚠ Group-scoped credentials fail silently.** "Custom events belonging to a
   specific group must use only that group's JWT Token or Service Key. Using
   different group credentials means the request is accepted, but the relevant
   flow won't trigger."

Rule 3 is the highest-value line in this file. The request returns a **success /
queued response** and the flow **never executes**. There is no error anywhere to
debug. If a custom event returns queued but the flow never runs, check that the
credential belongs to the same group as the event **before looking anywhere
else** — every other hypothesis is cheaper to test and all of them are wrong.

---

## References

- Inbound Webhooks: https://help.webexconnect.io/docs/inbound-webhooks
- API Settings (Service Key / JWT): https://help.webexconnect.io/docs/api-settings
- Service Key and JWT Authentication Tokens: https://help.webexconnect.io/docs/service-key-and-jwt-authentication-tokens
- Custom Events: https://help.webexconnect.io/docs/custom-events
- Response codes: `connect-response-codes.md`
- Build procedure: `docs/playbooks/webhook-triggers.md`

## See Also

- [connect-response-codes.md](connect-response-codes.md) — the response codes returned when inbound authentication fails
- [webex-connect.md](webex-connect.md) — the Connect flows these authentication rules protect
- [webhook-triggers.md](../playbooks/webhook-triggers.md) — setting up an inbound webhook that uses these mechanisms
- [webex-api-auth.md](../playbooks/webex-api-auth.md) — outbound authentication to Webex APIs, the other direction
