# wxops — The Webex Calling Playbook

## Elevator pitch

**wxops turns a terminal into a guided Webex expert.** You describe what you want to build — provision a site, stand up an auto attendant, migrate a legacy phone system — in plain English, and an AI playbook interviews you, designs a step-by-step deployment plan, executes it through a tested command-line tool, and reads every resource back to confirm it matches your intent. It spans the entire Webex platform — calling, admin, devices, messaging, meetings, and contact center — and it is engineered so the AI never guesses: facts come from authoritative docs, procedure from encoded skills, and execution from a tested CLI.

## Suggested video arc

This deck is the narration spine. A natural order for the video:

1. **The problem** — configuring Webex at scale is sprawling and error-prone (this doc).
2. **The platform at a glance** — the breadth and the three-layer architecture (doc 02).
3. **How it works** — the interview-to-verify pipeline, traced through one real request (doc 03).
4. **Why it's different** — grounded so it can't hallucinate, and far cheaper than the alternative (doc 04).
5. **The hero use case + impact** — automated CUCM-to-Webex migration, org health, and why it wins (doc 05).

## The problem it solves

The Webex platform spans **thousands of API endpoints** across calling, admin/identity, device management, messaging, meetings, and contact center. Building anything non-trivial means coordinating resources in exactly the right dependency order, across multiple API domains, with the right resource IDs, OAuth scopes, and token types.

Doing this by hand — clicking through Control Hub or hand-rolling raw API calls — is slow and unforgiving:

- A hunt group needs a **calling-enabled location first**. Miss the order and the call fails silently.
- The word **"queue" means three different things** across Webex Calling, Contact Center, and Customer Assist — each a different API, different entity, different skill.
- Deeply nested settings, license-tier gaps, and token-scope mismatches produce cryptic 400s and 403s.

**And handing a raw OpenAPI spec to an AI doesn't fix it.** Across hundreds of endpoints a language model malforms request bodies, hallucinates field names and license tiers, and — worst — doesn't know the dependency order. Specs describe *endpoints*; they don't describe *outcomes*.

## What wxops is

A guided AI assistant that walks Webex configuration end-to-end. Think of it as a Webex Calling expert sitting next to you in the terminal. It:

- **Interviews you** one question at a time to pin down the objective, scope, and constraints.
- **Designs a deployment plan** with real resource IDs from your live org, actual commands, dependency ordering, and a rollback plan — shown to you *before* anything runs.
- **Executes** through `wxcli`, a tested command-line tool covering the full Webex API surface.
- **Verifies** by reading every created resource back and comparing it to the plan.

It also runs standalone workflows — a read-only natural-language query mode ("who has call forwarding on?"), an 18-check org health audit, and a full CUCM-to-Webex migration pipeline.

## Who it's for

Webex administrators, Cisco Sales Engineers, and partners/VARs/MSPs who manage Webex Calling for one or many organizations — anyone who needs to provision, configure, migrate, or audit Webex at speed without memorizing hundreds of endpoints or fearing a mis-ordered build.
