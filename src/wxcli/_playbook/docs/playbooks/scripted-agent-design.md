# Scripted Agent Design Playbook

<!-- ref-tag: scripted-agent-design-v1 -->

## Overview

Step-by-step guide for designing a scripted AI agent before building it in AI Agent Studio. This playbook covers intent planning, entity design, response authoring, and context flow mapping. Complete this design phase before opening AI Agent Studio.

**Key principle:** Scripted agents use an intent-entity-response architecture, not a decision tree. Design around what the user wants to do (intents), what data you need to collect (entities), and what the agent says back (responses).

---

## 1. Define the Agent's Purpose

Start with a single sentence:

> This agent helps [who] do [what] on [channel].

Examples:
- "This agent helps patients book, reschedule, and cancel appointments on voice."
- "This agent helps customers track packages on WhatsApp."
- "This agent helps employees submit IT helpdesk requests on live chat."

This becomes the **Agent Goal** in AI Agent Studio.

---

## 2. List All Intents

An intent is a user goal -- something the customer wants to accomplish. List every intent your agent should handle.

### Intent Planning Table

| # | Intent Name | Description | Requires Fulfillment? | Entry Contexts | Exit Contexts |
|---|-------------|-------------|----------------------|----------------|---------------|
| 1 | `book_appointment` | Customer wants to schedule a new appointment | Yes (check availability, create booking) | - | `appointment_booked` |
| 2 | `cancel_appointment` | Customer wants to cancel an existing appointment | Yes (look up + delete booking) | - | `appointment_cancelled` |
| 3 | `check_status` | Customer wants to know their appointment status | Yes (look up booking) | - | - |

### Intent Design Checklist

For each intent, answer:

- [ ] **What does the user say?** List 10+ example utterances with natural variation
- [ ] **What data do you need?** List required entities/slots
- [ ] **Does it call an API?** If yes, which endpoint and what data flows in/out
- [ ] **What comes before it?** Does it require context from a prior intent (entry context)?
- [ ] **What comes after it?** Does it unlock follow-up intents (exit context)?
- [ ] **Does it end the conversation?** Toggle "End conversation" if this is a terminal intent

### Writing Good Utterances

Aim for **10-20 utterances per intent** with natural variation:

```
Intent: book_appointment
- I'd like to book an appointment
- Can I schedule a visit?
- I need to see the doctor
- Book me in for next Tuesday
- I want to make an appointment
- Schedule an appointment please
- I need an appointment
- Can I come in tomorrow?
- I'd like to schedule a checkup
- Make me an appointment for this week
```

**Tips:**
- Vary sentence structure (questions, statements, commands)
- Include colloquial phrasing ("book me in" vs "schedule an appointment")
- Include utterances with and without entity values ("Book me in" vs "Book me in for Tuesday")
- Don't worry about perfect coverage -- Pro 2.0 generates additional patterns automatically

---

## 3. Design Entities

Entities are the data pieces your agent collects from the user.

### Entity Planning Table

| Entity Name | Type | Description | Example Values | Used By Intents |
|-------------|------|-------------|----------------|----------------|
| `appointment_date` | Date (System) | Desired appointment date | "next Tuesday", "March 15" | book_appointment |
| `appointment_time` | Time (System) | Desired appointment time | "2pm", "morning" | book_appointment |
| `appointment_type` | Custom list | Type of appointment | "checkup", "follow-up", "urgent" | book_appointment |
| `phone_number` | Phone (System) | Customer's phone number | "555-123-4567" | cancel_appointment, check_status |

### Entity Type Selection Guide

| Data Pattern | Use This Type |
|-------------|---------------|
| Date ("next Tuesday", "March 15") | System: Date |
| Time ("2pm", "morning") | System: Time |
| Email addresses | System: Email |
| Phone numbers | System: Phone number |
| Dollar amounts ("$50", "fifty dollars") | System: Monetary |
| Fixed set of options ("checkup", "follow-up") | Custom list (with synonyms) |
| Pattern-matched strings ("ABC123456") | Regex |
| Numeric codes of known length ("123456") | Digits |
| Letters and numbers mixed ("ABC1234") | Alphanumeric |
| Any free text ("John Smith") | Free form |
| Location shared on WhatsApp | Map location (WhatsApp) |

Entity type names are verbatim from Cisco [`ai-agent-studio-scripted.md` § Entities]. Note `Digits`, not "Fixed-length digits" — that phrase is from Cisco's *description*, not the label. Cisco's prebuilt/system entity list is `Monetary units`, not "Monetary".

### Slot Design Per Intent

For each intent, define how slots are collected:

| Intent | Slot | Required? | Retries | Prompt |
|--------|------|-----------|---------|--------|
| `book_appointment` | `appointment_date` | Yes | 3 | "What date would you like your appointment?" |
| `book_appointment` | `appointment_time` | Yes | 3 | "What time works best for you?" |
| `book_appointment` | `appointment_type` | Yes | 2 | "Is this a checkup, follow-up, or urgent visit?" |

---

## 4. Map Context Flows

Context management controls which intents are reachable at each point in the conversation. Draw the flow as a context chain.

### Context Flow Diagram

```
[greeting] ──(exit: "greeted")──→ [book_appointment] ──(exit: "appt_booked")──→ [confirm_booking]
                                  [cancel_appointment]
                                  [check_status]

[cancel_appointment] ──(exit: "appt_cancelled")──→ [rebook_prompt]
```

### Context Planning Table

| Intent | Entry Contexts | Exit Contexts | Duration |
|--------|---------------|---------------|----------|
| `greeting` | (none) | `greeted` | 5 turns |
| `book_appointment` | (none -- available anytime) | `appt_booked` | 3 turns |
| `confirm_booking` | `appt_booked` | (none) | - |
| `cancel_appointment` | (none) | `appt_cancelled` | 3 turns |
| `rebook_prompt` | `appt_cancelled` | (none) | - |

### Context Design Rules

- **No entry context** = intent is always available (good for top-level actions)
- **Entry context required** = intent only matches after a prerequisite intent fires
- **Duration** = how many turns the context stays active (set generously; too short breaks the chain)
- Max 5 entry contexts, 15 exit contexts per intent

---

## 5. Design Responses

Plan what the agent says at each step. Remember: responses are pre-authored, not LLM-generated.

### Response Planning Table

| Template Key | Intent/Slot | Channel | Response Text |
|-------------|-------------|---------|---------------|
| `welcome` | (system) | All | "Welcome to Acme Health! I can help you book, reschedule, or cancel an appointment. What would you like to do?" |
| `ask_date` | book_appointment / date slot | All | "What date would you like your appointment?" |
| `ask_time` | book_appointment / time slot | All | "What time works best for you?" |
| `booking_confirmed` | book_appointment completion | All | "Your appointment is confirmed for ${entity.appointment_date} at ${entity.appointment_time}. Anything else I can help with?" |
| `booking_confirmed` | book_appointment completion | WhatsApp | (Quick Reply with "Yes" / "No, thanks") |

### Channel-Specific Response Design

Plan different response formats per channel:

| Channel | Best Response Types | Notes |
|---------|-------------------|-------|
| **Voice** | Text (spoken), Custom Event | Keep short (1-2 sentences). Use Custom Event for fulfillment |
| **WhatsApp** | Reply Button, List Message, Numbered List | Use buttons for yes/no, lists for multiple options |
| **Web Chat** | Carousel, Quick Reply | Rich UI elements supported |
| **SMS** | Text only | Keep under 160 chars per message |
| **Apple Messages** | List Picker, Time Picker, Form | Native UI widgets available |

### Conditional Response Design

If responses need to vary based on data:

| Template Key | Condition | Response |
|-------------|-----------|----------|
| `booking_result` | IF `${entity.appointment_type}` = "urgent" | "I've flagged this as urgent. A nurse will follow up within the hour." |
| `booking_result` | ELSE | "You're all set! We'll see you on ${entity.appointment_date}." |

---

## 6. Plan Fulfillment

For each intent that calls an external API:

### Fulfillment Planning Table

| Intent | API Endpoint | Method | Input (from entities) | Output (to response) | Channel Pattern |
|--------|-------------|--------|----------------------|---------------------|----------------|
| `book_appointment` | `/appointments` | POST | date, time, type, phone | confirmation_number | Digital: Branch on template_key → HTTP → send response. Voice: Custom Event → Flow Designer HTTP → state_update |
| `check_status` | `/appointments?phone=X` | GET | phone | status, date, time | Same pattern |

### Digital Fulfillment Flow Sketch

```
AI Agent node
  → Data Parser (extract template_key from SessionMetadata)
  → Branch:
    → template_key = "booking_confirmed" → HTTP POST /appointments → Evaluate → Send confirmation → Append → Receive → loop
    → template_key = "status_result" → HTTP GET /appointments → Evaluate → Send status → Append → Receive → loop
    → default → Send agent TextResponse → Receive → loop
```

### Voice Fulfillment Flow Sketch

```
Virtual Agent V2
  → Custom Event path → Parse event data (entity values)
    → HTTP Request → Condition (success/fail)
      → Success: state_update event {slots: {confirmation: "ABC123"}}
      → Fail: state_update event {slots: {time: ""}} (re-prompt)
  → Handled path → Queue Contact (if needed)
  → Escalated path → Queue Contact
```

---

## 7. Design Checklist

Before building in AI Agent Studio, verify:

- [ ] **Agent Goal**: One sentence, clear purpose
- [ ] **All intents listed**: Every user goal covered
- [ ] **Utterances drafted**: 10+ per intent with natural variation
- [ ] **Entities defined**: Every data element typed and described
- [ ] **Slots mapped**: Per-intent slot linkage with prompts and retries
- [ ] **Context flow mapped**: Entry/exit contexts create logical conversation paths
- [ ] **Responses authored**: Per-channel, with conditional variants where needed
- [ ] **Fulfillment planned**: API endpoints, input/output, error handling
- [ ] **Fallback message written**: What the agent says when it doesn't understand
- [ ] **Escalation path defined**: When and how to transfer to a human
- [ ] **Small talk customized**: Greetings, thank you, goodbye responses

---

## 8. Common Design Patterns

### Pattern 1: Slot-Filling Form Collection
Best for: appointment booking, order placement, service requests

```
Intent → collect slot 1 → collect slot 2 → collect slot 3 → fulfillment → confirmation
```

### Pattern 2: Lookup + Response
Best for: order tracking, status checks, account inquiries

```
Intent → collect identifier (order number, phone) → fulfillment → display result
```

### Pattern 3: Menu-Driven Routing
Best for: IVR replacement, department routing

```
Welcome → user states intent → NLU classifies → route to correct intent
  Each intent may have its own slot-filling sub-flow
```

### Pattern 4: Context-Chained Multi-Step
Best for: complex workflows (book → confirm → reschedule if needed)

```
Intent A (exit: "a_done") → Intent B (entry: "a_done", exit: "b_done") → Intent C (entry: "b_done")
```

---

## References

- `docs/reference/ai-agent-studio-scripted.md` — comprehensive scripted agent reference
- `docs/playbooks/scripted-agent-build.md` — companion build playbook (step-by-step AI Agent Studio configuration)
- [Webex AI Agent Studio Administration Guide](https://help.webex.com/en-us/article/ncs9r37/Webex-AI-Agent-Studio-Administration-guide)
- [Understand intents, entities, and responses](https://help.webex.com/en-us/article/sz02k8/Understand-intents,-entities,-and-responses-in-AI-Agent-Studio)
- [Configure fulfillment for scripted AI agents](https://help.webex.com/en-us/article/mzpuseb/Configure-fulfillment-for-scripted-AI-agents)
- [Guidelines and best practices](https://help.webex.com/en-us/article/nelkmxk/Guidelines-and-best-practices-for-automating-with-AI-agent)
