# WebexOne Lab Proposal — Submission-Ready

---

## 1. Session Title

**From CUCM to Cloud: Build, Migrate, and Operate Webex Calling with AI in 4 Hours**

---

## 2. Abstract

CUCM end-of-life is the most urgent topic in enterprise collaboration, but most migration sessions stop at slides and architecture diagrams. This instructor-led lab goes further: attendees build, migrate, and operate a Webex Calling environment themselves — guided by an AI agent that handles the API mechanics while they focus on the architecture, design decisions, and migration judgment that determine whether a deployment actually works.

The lab opens with a full CUCM-to-Webex migration executed live in under 15 minutes — extraction, analysis, provisioning, verified call flows. Then the instructor asks: "That was fast. But do you trust it? Can you troubleshoot it? Can you explain it to your customer?" The remaining three and a half hours answer those questions.

The platform pairs 828 Webex API endpoints with 16 domain-specific AI skills. Attendees describe what they want in plain language — the AI designs, executes, and verifies. But the lab is not about watching the AI work. It is about the decisions that the AI cannot make: which call flow architecture fits this business, which CUCM patterns to migrate versus rebuild, which conflicts in the decision report actually matter, and what "done" looks like when a customer is counting on this working Monday morning.

Attendees leave with the platform installed, the architectural judgment to use it well, and a migration methodology they can apply immediately. No prior API, CLI, or coding experience is required — just Webex Calling familiarity and the willingness to argue about dial plans.

---

## 3. Detailed Description

Enterprise collaboration teams face a defining moment. CUCM end-of-life timelines are accelerating, and every partner and IT organization needs to answer the same question: how do we get from on-premises to cloud calling — reliably, repeatably, and without rebuilding everything by hand in Control Hub?

The tools to execute fast already exist. What doesn't exist is the judgment layer: knowing what to build, when to deviate from what CUCM had, and which migration decisions will come back to haunt you in six months. This lab teaches both — using an AI agent that eliminates the mechanical barrier so attendees can spend four hours on the thinking that actually matters.

### The Platform

The lab is built on an AI-guided operations platform that combines two layers. The automation layer exposes 828 Webex API endpoints across 100 command groups, covering the full Webex Calling surface: provisioning, call features, person and location settings, call routing, device management, SCIM identity, licensing, audit/compliance, messaging, and real-time call control. The intelligence layer adds 16 domain-specific AI skills — each encoding the operational knowledge, dependency ordering, edge cases, and verification steps required to complete a category of work correctly.

Attendees interact through conversation, not command syntax. They describe what they need, and the AI agent handles execution. But the lab's structure is designed to surface the moments where the AI is fast but the human must be right — the architectural decisions, migration tradeoffs, and design judgments that no automation can make for you.

### Cold Open — The 15-Minute Migration (15 minutes)

The lab opens with a live demonstration: the instructor executes a complete CUCM-to-Webex Calling migration in under 15 minutes. Extract 80 objects from a live CUCM 15.x cluster. Run the analysis pipeline. Accept default decisions. Provision into Webex. Verify call flows. Done.

Then the instructor pauses: "That was the easy part. The hard part is knowing whether those defaults were the right decisions — because three of them weren't. By the end of Act 2, you'll be able to tell me which three and why."

This sets the frame for the entire lab: speed is not the constraint anymore. Judgment is.

### Act 1 — Design and Build a Webex Calling Environment (75 minutes)

Attendees do not start with "create two locations." They start with a business scenario:

*"Contoso Corp has two offices — headquarters (Chicago, 30 staff) and a branch (Austin, 15 staff). They need a main number with business-hours and after-hours routing, a sales queue with 8 agents, a support line that rings three technicians round-robin, and the ability to transfer between offices. The Chicago office handles Spanish-language callers on a separate menu option. Design the call flow architecture, then build it."*

Attendees work with the AI agent to implement their design — but the teaching happens at the decision points the instructor introduces along the way:

- **Decision point: Auto attendant design.** "Your AA has 6 menu options. Research shows callers abandon after option 4. How do you restructure this?" The room discusses. Designs diverge. Attendees who over-engineer learn why simplicity wins.
- **Decision point: Queue vs. hunt group.** "Your support line rings three people round-robin. Should this be a hunt group or a call queue?" The AI can build either in 30 seconds. The question is which one fits the business need — and the answer depends on whether Contoso needs reporting, overflow handling, and whisper announcements or just round-robin ringing.
- **Decision point: The AI made a suboptimal choice.** The instructor flags a configuration the AI produced that works but creates a maintenance problem or capacity gap. The room diagnoses why. This teaches the most important lesson: the AI is a tool, not an authority.

The checkpoint is concrete: call the main number, navigate the auto attendant, reach the sales queue, transfer to Austin. The call flow works — and every attendee understands why it was designed the way it was, not just that it was built.

### Act 2 — CUCM Migration: Analysis, Judgment, and Execution (90 minutes)

This is the centerpiece. Attendees do not just "run a migration." They analyze a CUCM cluster, understand what the decision report is telling them, make decisions they can defend, and verify the result.

**Act 2a — Extraction & Analysis (20 minutes).** Attendees point the AI agent at the lab CUCM cluster. It extracts 80 objects across 21 types via AXL and runs the full analysis pipeline: pattern conversion, CSS decomposition, device compatibility mapping, conflict detection. The mechanical work takes minutes. The output is what matters: a decision report with 15+ flagged items across 8 categories.

**Act 2b — Decision Review (45 minutes, instructor-led).** This is where the lab earns its differentiation. The instructor walks the room through the decision report category by category:

- **CSS decomposition:** "CUCM has 14 CSSes built from 8 partitions. 6 of them exist only to block international dialing. In Webex, that's a calling permission policy, not a routing object. The pipeline wants to create 14 dial plans. You should create 8 and replace the other 6 with permission policies. Here's how to tell the difference."
- **Hunt pilot reclassification:** "This hunt pilot has queuing enabled, a 20-second RNA timeout, and 12 agents. The pipeline offers Hunt Group or Call Queue. Which one — and why does it matter for the customer's reporting requirements?"
- **Translation pattern triage:** "These 4 translation patterns normalize 7-digit dialing to E.164. Webex handles this natively at the location level. Migrating them creates redundant rules. The right answer is: don't migrate these."
- **Device compatibility:** "23 phones are flagged as incompatible. The pipeline shows replacement options. But the question isn't just which model — it's whether the replacement runs MPP firmware or RoomOS, because that changes your day-2 configuration model entirely."

The instructor reveals the three wrong decisions from the cold open. Attendees see the consequences: a call flow that routes to the wrong queue, a dial plan with redundant patterns, a permission policy that's more restrictive than intended. The point lands: the AI migrated everything correctly. The decisions were wrong.

**Act 2c — Execution & Verification (25 minutes).** Attendees apply their decisions and tell the agent to execute. The AI provisions into the sandbox org in dependency order, handling errors and retrying as needed. Attendees verify: compare CUCM source config against Webex result. Confirm migrated call flows work end to end. The checkpoint is a phone call.

### Act 3 — Day-2 Operations: Troubleshoot, Audit, Expand (30 minutes)

**Act 3a — Diagnose a broken environment (15 minutes).** The instructor has pre-introduced a misconfiguration into each attendee's environment. Calls to the sales queue ring but nobody answers. Attendees use the AI agent to diagnose: pull CDRs, check call queue settings, audit agent assignments, review routing. The AI can query everything instantly — but the attendee has to know what questions to ask. This is the operational superpower: not "the AI fixes it for you" but "the AI gives you X-ray vision into the environment and you interpret what you see."

**Act 3b — Expand and audit (15 minutes).** Onboard a new department: five users, a call queue, per-user call settings. Then run a compliance audit: are all queues recording? Do outbound permission policies match the customer's requirements? The platform that built and migrated the environment is the same platform that operates it.

### What Makes This Different

This lab inverts the traditional ratio. Most labs spend 80% of the time on mechanics and 20% on understanding. This lab spends 20% on mechanics — the AI handles that — and 80% on the architecture, decisions, and judgment that determine whether a deployment actually serves the business. The AI makes the room faster. The instructor and the decision points make the room smarter.

---

## 4. Learning Objectives

1. **Design** a Webex Calling call flow architecture for a multi-site business scenario — making deliberate choices about auto attendant structure, queue vs. hunt group selection, and inter-site routing — before the AI builds anything.
2. **Analyze** a CUCM migration decision report to distinguish between objects that should be migrated as-is, objects that should be rebuilt using Webex-native patterns, and CUCM workarounds that should be eliminated entirely.
3. **Execute** a CUCM-to-Webex Calling migration end-to-end — AXL extraction, automated analysis, human-decision workflow, AI-orchestrated provisioning, and verification — with the judgment to evaluate whether the result is correct, not just complete.
4. **Diagnose** a Webex Calling misconfiguration using AI-assisted querying — CDRs, call settings, routing audits — and identify the root cause from the data the AI surfaces.
5. **Apply** a repeatable, AI-assisted deployment and migration methodology — including the decision framework for when to migrate, rebuild, or eliminate CUCM objects — to your own customer engagements immediately after the session.

---

## 5. Session Outline

| Time | Module | Description |
|------|--------|-------------|
| 0:00 – 0:15 | **Cold Open — The 15-Minute Migration** | Instructor executes a complete CUCM-to-Webex migration live: extract, analyze, accept defaults, provision, verify call flows. Then: "That was fast. Three of those decisions were wrong. By the end of Act 2, you'll know which three and why." Attendees set up their lab pods during the demo. |
| 0:15 – 0:30 | **Pod Setup & Platform Orientation** | Verify platform installation, authentication, and sandbox access. Orientation to the AI agent: how to describe what you want, how to review the agent's plan, how to approve or modify before execution. |
| 0:30 – 0:55 | **Act 1a — Design the Call Flow** | Business scenario brief: Contoso Corp, two offices, specific routing requirements. Attendees design the architecture with instructor-led decision points: AA menu depth, queue vs. hunt group selection, inter-site transfer routing. The AI doesn't execute yet — attendees design first. |
| 0:55 – 1:25 | **Act 1b — Build and Break** | Tell the AI to build the design. Watch it execute. Then: instructor introduces failure scenarios. "A caller dials extension 0 during after-hours — what happens?" "All 8 sales agents are on calls — where does caller 9 go?" Attendees diagnose gaps in their own designs and fix them. |
| 1:25 – 1:45 | **Act 1c — Verify the Full Call Flow** | End-to-end verification: call the main number, navigate the auto attendant, reach the sales queue, transfer to Austin. The AI flags the suboptimal configuration from the decision point. Room discusses. Checkpoint confirmed. |
| 1:45 – 2:00 | **Break** | 15-minute break. |
| 2:00 – 2:20 | **Act 2a — CUCM Extraction & Analysis** | Point the AI at the CUCM 15.x cluster. Extract 80 objects across 21 types. Run the full analysis pipeline. Output: a decision report with 15+ flagged items. Attendees scan the report and identify the categories of decisions. |
| 2:20 – 3:05 | **Act 2b — Decision Review (Instructor-Led)** | Walk through the decision report category by category: CSS decomposition (migrate vs. replace with permissions), hunt pilot reclassification (HG vs. CQ), translation pattern triage (migrate vs. eliminate), device compatibility (model selection and firmware implications). Instructor reveals the three wrong decisions from the cold open. Room sees the consequences. |
| 3:05 – 3:30 | **Act 2c — Execute and Verify Migration** | Attendees apply their decisions. AI provisions into sandbox in dependency order. Verify: compare CUCM source against Webex result. Confirm call flows work. Checkpoint confirmed. |
| 3:30 – 3:45 | **Act 3 — Diagnose, Expand, Audit** | Pre-broken environment: diagnose the misconfiguration using AI-assisted querying. Then: onboard a new department, run a compliance audit. Same platform handles build, migrate, troubleshoot, and operate. |
| 3:45 – 4:00 | **Wrap-Up & Takeaways** | Recap the decision framework: migrate, rebuild, or eliminate. Install instructions. Resources. Q&A. |

---

## 6. Target Audience

### Primary Audience
- **Partners and VARs** managing CUCM-to-Webex Calling migrations for customers — especially those who need to move faster without sacrificing migration quality.
- **Enterprise collaboration engineers and IT administrators** responsible for deploying, migrating, or operating Webex Calling environments — including those with no API or coding experience.
- **Cisco SEs and consulting engineers** who advise customers on migration strategy and need hands-on depth with both the technology and the decision framework.

### Secondary Audience
- **Automation-curious collaboration professionals** who want to see what AI-assisted infrastructure operations look like in practice — and understand the human judgment layer that makes automation trustworthy.

### Prerequisites
- Basic familiarity with Webex Calling concepts (locations, users, call features, PSTN connectivity). No hands-on deployment experience required.
- General understanding of CUCM components (devices, directory numbers, CSSes, route patterns) for Act 2. Deep CUCM expertise is not required — the analysis pipeline and instructor-led walkthrough make the decision report accessible.
- **No prior API, CLI, coding, or AI experience required.** The interaction model is conversational — attendees describe what they want in plain language. The platform is pre-installed and pre-authenticated in each lab pod.

### Who Should NOT Attend
- Attendees looking for a CUCM deep-dive or troubleshooting session — this lab focuses on the migration *out* of CUCM, not administration of it.
- Attendees seeking a Control Hub walkthrough — this lab operates programmatically, not through the Control Hub UI.

---

## 7. Why Attend This Session

- **Speed is no longer the hard part — judgment is.** AI can migrate a CUCM cluster in 15 minutes. But a migration that's fast and wrong is worse than one that's slow and right. This lab teaches you to evaluate, decide, and verify — with the AI handling execution so you can focus entirely on the decisions that determine whether the migration actually works.

- **You will make real migration decisions and see the consequences.** The CUCM lab cluster has intentional complexity: overlapping CSSes, hunt pilots that should be call queues, translation patterns that are CUCM workarounds with no Webex equivalent, and devices that require firmware-model tradeoffs. The instructor reveals what happens when you get these wrong. No other session at WebexOne teaches migration judgment by showing failure.

- **The AI handles the mechanics; you learn the architecture.** You do not need to know API syntax, CLI flags, or dependency ordering. The 16 domain skills encode that knowledge. Four hours of your time goes to call flow design, migration decision-making, and operational troubleshooting — not fighting with API calls.

- **You leave with tools and a decision framework.** The platform installs on your own machine. But more importantly, you leave with a methodology: when to migrate as-is, when to rebuild using Webex-native patterns, and when to eliminate CUCM workarounds entirely. That framework applies to every migration engagement you run, with or without the tool.

- **Built by a practitioner, not a product team.** This platform was built by a Cisco SE who runs these engagements with real customers and partners. The decision framework taught in this lab comes from production migrations — including the mistakes.

---

## 8. Presenter Bio

Adam Hobgood is a Collaboration Presales Solutions Engineer at Cisco Systems, where he works directly with enterprise customers and partners planning Webex Calling deployments and CUCM-to-cloud migrations. Frustrated by the manual, error-prone processes that defined these engagements, Adam built an AI-guided operations platform that combines 828 Webex API endpoints across 100 command groups with 16 domain-specific AI skills — making the full Webex Calling surface accessible to anyone who can describe what they want in plain language. The platform includes a complete CUCM-to-Webex migration pipeline with AXL extraction, automated analysis, human-decision workflows, and AI-orchestrated provisioning. It has been tested against production Webex environments and a live CUCM 15.x cluster with 80 provisioned objects across 21 configuration types. Adam brings the perspective of a practitioner who builds the tools he wishes existed — grounded in real customer engagements, not lab-only scenarios.

---

## 9. Technical Requirements

### Per-Pod Infrastructure (30 pods)
- Webex sandbox organization pre-provisioned with Webex Calling licenses (sufficient for 15+ users, 2+ locations per pod)
- Lab workstation or virtual desktop with terminal access
- Python 3.11+ pre-installed
- Platform (`wxcli` + AI skills) pre-installed with all dependencies
- Claude Code pre-installed and authenticated (AI agent runtime)
- Pre-configured Webex authentication tokens (admin-level OAuth) with appropriate scopes
- Network connectivity to Webex APIs (`webexapis.com`), Anthropic APIs (AI agent), and the shared CUCM cluster

### Shared Infrastructure
- CUCM 15.x lab cluster with 80 pre-provisioned objects across 21 types (devices, end users, directory numbers, CSSes, partitions, route patterns, translation patterns, trunks, route lists, route groups, hunt pilots, hunt lists, line groups, voicemail profiles, CTI route points, device pools, regions, locations, phone button templates, softkey templates, service parameters)
- AXL API access enabled on the CUCM cluster for all pods (read-only for extraction)
- Fallback: pre-extracted CUCM data sets per pod (JSON), in case AXL connectivity is constrained during the session
- Pre-broken environment state per pod for Act 3 troubleshooting exercise

### Proctor Support
- 2-3 proctors for a 30-person lab (one proctor per ~10-12 attendees)
- Proctors should have familiarity with Webex Calling administration and basic experience with the AI agent platform

### Room Requirements
- Standard lab room with one workstation per attendee
- Projector/display for instructor screen sharing during walkthroughs and checkpoints
- Wired network connectivity preferred (API-intensive workload; Wi-Fi acceptable if bandwidth supports 30 concurrent pods)

---

## 10. Differentiators

*For the review committee — what makes this session unlike anything else in the catalog.*

### 1. Teaches migration judgment, not just migration mechanics.
Most migration sessions are architectural overviews or tool demos. This lab puts attendees in front of a real CUCM decision report and asks: which objects should be migrated as-is, which should be rebuilt using Webex-native patterns, and which are CUCM workarounds that should be eliminated? The instructor reveals consequences of wrong decisions using the cold-open migration. No other session teaches this.

### 2. AI handles execution so the lab can focus on architecture.
Traditional API-driven labs spend 80% of time on mechanics (typing commands, fixing errors, debugging auth) and 20% on understanding. This lab inverts that ratio. The AI agent handles provisioning, dependencies, and verification. Four hours of attendee time goes to call flow design, migration decision-making, and operational troubleshooting.

### 3. Business scenarios, not task lists.
Attendees don't follow a script of "create location A, then create user B." They receive a business scenario (multi-site company with specific routing requirements) and design a solution — with instructor-led decision points that surface real architectural tradeoffs. The AI builds whatever they design, which means their design decisions have visible consequences.

### 4. 828 endpoints, 100 command groups — broadest Webex Calling automation coverage in any session.
The platform covers the full Webex Calling API surface: provisioning, all call feature types, person and location call settings, call routing, device management, SCIM identity, licensing, audit/compliance, messaging, and real-time call control. This breadth means the lab can span from green-field deployment to migration to day-2 operations without switching tools.

### 5. Built by a field SE, not a product team.
The platform was built by a presales SE who runs these engagements with real customers and partners. The decision framework taught in this lab — migrate, rebuild, or eliminate — comes from production migration experience, including documented edge cases (11 categories of API behaviors with workarounds) that product demos don't surface.

### 6. Attendees take home tools and a methodology.
The platform installs on attendees' own machines. But the deeper takeaway is the decision framework: the categories of CUCM objects that should be rethought rather than converted, the Webex-native patterns that replace CUCM workarounds, and the verification methodology that confirms a migration actually works. Tools without methodology produce fast, wrong results.

### 7. No overlap with Cisco product team sessions.
Product team sessions cover Control Hub workflows, roadmap, and feature announcements. This session is AI-first, decision-focused, and practitioner-built. Zero content overlap with the Webex Calling product team, migration services team, or partner enablement team.
