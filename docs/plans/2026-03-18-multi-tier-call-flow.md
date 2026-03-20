# Deployment Plan: Multi-Tier Call Flow (HQ)

Created: 2026-03-18
Agent: wxc-calling-builder

---

## 1. Objective

Build a two-tier auto attendant call flow at the HQ location in org `ahobgood-sbx`: a Main Menu AA (ext 1000, DID +14707521443) that routes callers to a Sales Team hunt group (ext 3100), a Support Queue call queue (ext 2100), or a Directory & Options submenu AA (ext 1001) via key-press, with after-hours and holiday routing to voicemail and an external answering service.

---

## 2. Prerequisites

| # | Prerequisite | Verification Method | Status |
|---|-------------|-------------------|--------|
| 1 | HQ location exists | Provided in spec — ID confirmed | CONFIRMED |
| 2 | 6 agent users exist with calling licenses | Provided in spec — IDs confirmed | CONFIRMED |
| 3 | Extension 3100 available at HQ | Verify before HG creation | TO VERIFY |
| 4 | Extension 2100 available at HQ | Verify before CQ creation | TO VERIFY |
| 5 | Extension 1000 available at HQ | Verify before Main Menu AA creation | TO VERIFY |
| 6 | Extension 1001 available at HQ | Verify before Submenu AA creation | TO VERIFY |
| 7 | Phone number +14707521443 available at HQ | Provided in spec as unassigned | CONFIRMED |
| 8 | No existing schedules named "Business Hours" or "US Holidays 2026" at HQ | Verify before schedule creation | TO VERIFY |

**Key IDs (from spec, confirmed live):**

| Resource | ID |
|----------|-----|
| HQ Location | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |
| Sales Agent 1 — Store1 Mobile | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80YzVhMWI2Yy0zMThjLTQyMGEtYTMzYy00ZWI2NjIxZThjZTU` |
| Sales Agent 2 — Store1 Pro | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS82YTc4YzBjMi1kZGRlLTQzZTMtYTE0MS03MTBkMmEwMTc3Yjc` |
| Sales Agent 3 — Store1 DIY | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9iZWI4OWMzYi00OWZiLTQ5YzMtYmE1MC03NTYyM2ViNDA0Nzg` |
| Support Agent 1 — IHG Agent1 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hZmVjNjY0ZC04ZTI4LTQyYWQtYWVmMi1jNDg2Y2I2YjExZWI` |
| Support Agent 2 — Store1 Phone1 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xNGI1YzBiNy00MzJlLTQxM2MtOWI3Mi04Y2M1NmU0NDQ5ZjE` |
| Support Agent 3 — Store1 Phone2 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80ODhhZDc5MS0zYTg0LTQyYTYtOTljYS1jNGY2YjBiOTFkMzQ` |

---

## 3. Execution Steps

Steps must be executed in this exact order due to dependencies.

---

### Step 1 — Verify prerequisites

**Description:** Confirm HQ location is calling-enabled, check for duplicate extensions and schedule names.

```bash
wxcli locations show Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ --output json
wxcli location-call-settings list-schedules Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ --output json
wxcli numbers list --location Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ --output json
```

**Expected result:** HQ confirmed calling-enabled; no existing "Business Hours" or "US Holidays 2026" schedules; +14707521443 shows as unassigned.

**Depends on:** Nothing.

---

### Step 2a — Create "Business Hours" schedule

**Description:** Create a recurring Mon–Fri 08:00–17:00 business hours schedule at HQ.

```bash
wxcli location-call-settings create-schedules \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  --name "Business Hours" \
  --type businessHours
```

Then add the Mon–Fri event:

```bash
wxcli location-call-settings create-schedule-events \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <BUSINESS_HOURS_SCHEDULE_ID> \
  --json-body '{
    "name": "Weekdays",
    "startDate": "2026-01-01",
    "endDate": "2026-12-31",
    "startTime": "08:00",
    "endTime": "17:00",
    "recurrence": {
      "recurWeekly": {
        "monday": true,
        "tuesday": true,
        "wednesday": true,
        "thursday": true,
        "friday": true,
        "saturday": false,
        "sunday": false
      }
    }
  }'
```

**Expected result:** Schedule created; returns schedule ID. Event added successfully.

**Depends on:** Step 1.

---

### Step 2b — Create "US Holidays 2026" schedule

**Description:** Create a holiday schedule with 4 holiday events at HQ.

```bash
wxcli location-call-settings create-schedules \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  --name "US Holidays 2026" \
  --type holidays
```

Then add 4 holiday events (one at a time):

```bash
# New Year's Day
wxcli location-call-settings create-schedule-events \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <HOLIDAY_SCHEDULE_ID> \
  --json-body '{"name": "New Years Day", "startDate": "2026-01-01", "endDate": "2026-01-01", "allDayEnabled": true}'

# Independence Day
wxcli location-call-settings create-schedule-events \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <HOLIDAY_SCHEDULE_ID> \
  --json-body '{"name": "Independence Day", "startDate": "2026-07-03", "endDate": "2026-07-03", "allDayEnabled": true}'

# Thanksgiving (2 days)
wxcli location-call-settings create-schedule-events \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <HOLIDAY_SCHEDULE_ID> \
  --json-body '{"name": "Thanksgiving", "startDate": "2026-11-26", "endDate": "2026-11-27", "allDayEnabled": true}'

# Christmas
wxcli location-call-settings create-schedule-events \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <HOLIDAY_SCHEDULE_ID> \
  --json-body '{"name": "Christmas Day", "startDate": "2026-12-25", "endDate": "2026-12-25", "allDayEnabled": true}'
```

**Expected result:** Schedule created; 4 events added successfully.

**Depends on:** Step 1.

---

### Step 3 — Create Hunt Group "Sales Team"

**Description:** Create a circular hunt group at ext 3100 with 3 sales agents, configured to forward to +19195551234 after 5 no-answer rings.

```bash
wxcli hunt-groups create \
  --location Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  --name "Sales Team" \
  --extension 3100
```

Then add 3 agents:

```bash
wxcli hunt-groups add-agent \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SALES_HG_ID> \
  Y2lzY29zcGFyazovL3VzL1BFT1BMRS80YzVhMWI2Yy0zMThjLTQyMGEtYTMzYy00ZWI2NjIxZThjZTU

wxcli hunt-groups add-agent \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SALES_HG_ID> \
  Y2lzY29zcGFyazovL3VzL1BFT1BMRS82YTc4YzBjMi1kZGRlLTQzZTMtYTE0MS03MTBkMmEwMTc3Yjc

wxcli hunt-groups add-agent \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SALES_HG_ID> \
  Y2lzY29zcGFyazovL3VzL1BFT1BMRS9iZWI4OWMzYi00OWZiLTQ5YzMtYmE1MC03NTYyM2ViNDA0Nzg
```

Then update to set CIRCULAR ring policy and no-answer forward behavior:

```bash
wxcli hunt-groups update \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SALES_HG_ID> \
  --json-body '{
    "callPolicies": {
      "policy": "CIRCULAR",
      "noAnswer": {
        "nextAgentEnabled": true,
        "numberOfRings": 5,
        "forwardEnabled": true,
        "destination": "+19195551234",
        "systemMaxNumberOfRings": 5
      }
    }
  }'
```

**Expected result:** Hunt group created with ID; 3 agents added; policy set to CIRCULAR with 5-ring overflow to +19195551234.

**Depends on:** Step 1 (location), agent IDs confirmed in spec.

---

### Step 4 — Create Call Queue "Support Queue"

**Description:** Create a SIMULTANEOUS call queue at ext 2100 with 15-slot queue, 120s max wait, welcome and comfort messages, music on hold, and 3 support agents.

```bash
wxcli call-queues create \
  --location Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  --name "Support Queue" \
  --extension 2100
```

Then add 3 agents:

```bash
wxcli call-queues add-agent \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SUPPORT_CQ_ID> \
  Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hZmVjNjY0ZC04ZTI4LTQyYWQtYWVmMi1jNDg2Y2I2YjExZWI

wxcli call-queues add-agent \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SUPPORT_CQ_ID> \
  Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xNGI1YzBiNy00MzJlLTQxM2MtOWI3Mi04Y2M1NmU0NDQ5ZjE

wxcli call-queues add-agent \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SUPPORT_CQ_ID> \
  Y2lzY29zcGFyazovL3VzL1BFT1BMRS80ODhhZDc5MS0zYTg0LTQyYTYtOTljYS1jNGY2YjBiOTFkMzQ
```

Then update queue settings (distribution policy, queue size, overflow, announcements):

```bash
wxcli call-queues update \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SUPPORT_CQ_ID> \
  --json-body '{
    "callPolicies": {
      "policy": "SIMULTANEOUS",
      "waitSettings": {
        "queueSize": 15,
        "waitTimeEnabled": true,
        "maxWaitTime": 120
      }
    },
    "allowAgentJoinEnabled": true,
    "queueSettings": {
      "overflow": {
        "action": "PERFORM_BUSY_TREATMENT"
      }
    },
    "welcomeMessage": {
      "enabled": true,
      "alwaysEnabled": false
    },
    "comfortMessage": {
      "enabled": true,
      "timeBetweenMessages": 30
    },
    "musicOnHold": {
      "enabled": true
    }
  }'
```

**Expected result:** Call queue created; 3 agents added; SIMULTANEOUS distribution, 15 slots, 120s max wait, welcome + comfort messages + MoH enabled.

**Depends on:** Step 1 (location), agent IDs confirmed in spec.

---

### Step 5 — Create AA Submenu "Directory & Options"

**Description:** Create the submenu AA at ext 1001 with business hours schedule. Key 0 is set to REPEAT_MENU temporarily (circular reference to Main Menu resolved in Step 7).

```bash
wxcli auto-attendants create \
  --location Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  --name "Directory & Options" \
  --extension 1001 \
  --business-schedule "Business Hours"
```

Then update to configure the business hours menu (dial by name, dial by extension, repeat):

```bash
wxcli auto-attendants update \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SUBMENU_AA_ID> \
  --json-body '{
    "businessHoursMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": true,
      "directoryEnabled": true,
      "keyConfigurations": [
        {
          "key": "1",
          "action": "NAME_DIALING"
        },
        {
          "key": "2",
          "action": "EXTENSION_DIALING"
        },
        {
          "key": "0",
          "action": "REPEAT_MENU"
        },
        {
          "key": "#",
          "action": "REPEAT_MENU"
        }
      ]
    },
    "afterHoursMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": false,
      "directoryEnabled": false,
      "keyConfigurations": [
        {
          "key": "0",
          "action": "REPEAT_MENU"
        }
      ]
    }
  }'
```

**Expected result:** Submenu AA created at ext 1001; business hours menu has keys 1 (name dialing), 2 (extension dialing), 0 (repeat placeholder), # (repeat).

**Depends on:** Step 2a (Business Hours schedule).

---

### Step 6 — Create AA Main Menu "Main Menu"

**Description:** Create the top-level AA at ext 1000, assign DID +14707521443, configure all three menus (business hours, after-hours, holiday) with key routing to HG, CQ, Submenu, operator, and answering service.

```bash
wxcli auto-attendants create \
  --location Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  --name "Main Menu" \
  --extension 1000 \
  --phone-number "+14707521443" \
  --business-schedule "Business Hours" \
  --holiday-schedule "US Holidays 2026"
```

Then update to configure the three menus:

```bash
wxcli auto-attendants update \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <MAIN_AA_ID> \
  --json-body '{
    "businessHoursMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": true,
      "directoryEnabled": false,
      "keyConfigurations": [
        {
          "key": "1",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "3100"
        },
        {
          "key": "2",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "2100"
        },
        {
          "key": "3",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "1001"
        },
        {
          "key": "0",
          "action": "TRANSFER_TO_OPERATOR"
        },
        {
          "key": "#",
          "action": "REPEAT_MENU"
        }
      ]
    },
    "afterHoursMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": false,
      "directoryEnabled": false,
      "keyConfigurations": [
        {
          "key": "1",
          "action": "TRANSFER_TO_MAILBOX"
        },
        {
          "key": "0",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "+19195559876"
        }
      ]
    },
    "holidayMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": false,
      "directoryEnabled": false,
      "keyConfigurations": [
        {
          "key": "1",
          "action": "TRANSFER_TO_MAILBOX"
        },
        {
          "key": "0",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "+19195559876"
        }
      ]
    }
  }'
```

**Expected result:** Main Menu AA created at ext 1000 with DID +14707521443; all three menus configured.

**Depends on:** Step 2a (Business Hours), Step 2b (US Holidays 2026), Step 3 (Sales Team HG — for ext 3100), Step 4 (Support Queue — for ext 2100), Step 5 (Submenu AA — for ext 1001).

---

### Step 7 — Update Submenu AA Key 0 (resolve circular reference)

**Description:** Update the Directory & Options submenu to change key 0 from REPEAT_MENU to TRANSFER_TO_AUTO_ATTENDANT pointing at Main Menu (ext 1000).

```bash
wxcli auto-attendants update \
  Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ \
  <SUBMENU_AA_ID> \
  --json-body '{
    "businessHoursMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": true,
      "directoryEnabled": true,
      "keyConfigurations": [
        {
          "key": "1",
          "action": "NAME_DIALING"
        },
        {
          "key": "2",
          "action": "EXTENSION_DIALING"
        },
        {
          "key": "0",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "1000"
        },
        {
          "key": "#",
          "action": "REPEAT_MENU"
        }
      ]
    },
    "afterHoursMenu": {
      "greeting": "DEFAULT",
      "extensionEnabled": false,
      "directoryEnabled": false,
      "keyConfigurations": [
        {
          "key": "0",
          "action": "TRANSFER_WITHOUT_PROMPT",
          "transferPhoneNumber": "1000"
        }
      ]
    }
  }'
```

**Expected result:** Submenu key 0 now routes to Main Menu ext 1000 in both menus.

**Depends on:** Step 5 (Submenu AA ID), Step 6 (Main Menu AA — confirms ext 1000 exists).

---

## 4. Resources to Create / Modify

| # | Resource Type | Name | Action | Key Parameters |
|---|--------------|------|--------|---------------|
| 1 | Schedule | Business Hours | Create | Mon–Fri 08:00–17:00, recurring, HQ |
| 2 | Schedule Event | Weekdays | Create | Within Business Hours schedule |
| 3 | Schedule | US Holidays 2026 | Create | Holiday type, HQ |
| 4 | Schedule Event | New Year's Day | Create | 2026-01-01 all day |
| 5 | Schedule Event | Independence Day | Create | 2026-07-03 all day |
| 6 | Schedule Event | Thanksgiving | Create | 2026-11-26 to 2026-11-27 all day |
| 7 | Schedule Event | Christmas Day | Create | 2026-12-25 all day |
| 8 | Hunt Group | Sales Team | Create | Ext 3100, CIRCULAR, 3 agents, overflow +19195551234 |
| 9 | Call Queue | Support Queue | Create | Ext 2100, SIMULTANEOUS, 15 slots, 3 agents |
| 10 | Auto Attendant | Directory & Options | Create | Ext 1001, name/ext dialing submenu |
| 11 | Auto Attendant | Main Menu | Create | Ext 1000, DID +14707521443, 3-menu config |
| 12 | Auto Attendant | Directory & Options | Update | Resolve circular ref: key 0 -> Main Menu |

**Total: 12 creation/modification operations across 8 CLI create commands + 4 update commands.**

---

## 5. Rollback Plan

| Trigger | Rollback Action |
|---------|----------------|
| Step 2a fails | No rollback needed (nothing created) |
| Step 2b fails | Delete Business Hours schedule |
| Step 3 fails | Delete Business Hours and Holiday schedules |
| Step 4 fails | Delete Sales Team HG + schedules |
| Step 5 fails | Delete Support Queue CQ + HG + schedules |
| Step 6 fails | Delete Submenu AA + CQ + HG + schedules |
| Step 7 fails | Delete Main Menu AA + Submenu AA + CQ + HG + schedules (or leave Submenu without back-link) |

**Rollback strategy:** Stop on failure, ask user whether to (A) fix and retry, (B) skip this step, or (C) rollback completed steps.

**Rollback commands (if needed):**

```bash
# Delete Main Menu AA
wxcli auto-attendants delete Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <MAIN_AA_ID>

# Delete Submenu AA
wxcli auto-attendants delete Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <SUBMENU_AA_ID>

# Delete Support Queue
wxcli call-queues delete Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <SUPPORT_CQ_ID>

# Delete Sales Team HG
wxcli hunt-groups delete Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <SALES_HG_ID>

# Delete US Holidays 2026 schedule
wxcli location-call-settings delete-schedules Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <HOLIDAY_SCHEDULE_ID>

# Delete Business Hours schedule
wxcli location-call-settings delete-schedules Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <BUSINESS_HOURS_SCHEDULE_ID>
```

---

## 6. Verification Steps

After all steps complete, verify each resource:

```bash
# Schedules
wxcli location-call-settings list-schedules Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ --output json

# Hunt Group
wxcli hunt-groups show Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <SALES_HG_ID> --output json

# Call Queue
wxcli call-queues show Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <SUPPORT_CQ_ID> --output json

# Submenu AA
wxcli auto-attendants show Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <SUBMENU_AA_ID> --output json

# Main Menu AA
wxcli auto-attendants show Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ <MAIN_AA_ID> --output json
```

**Functional validation checklist** (from spec section 11):

- [ ] Call +14707521443 — hear Main Menu greeting
- [ ] Press 1 — rings Sales Team agents (Store1 Mobile, Pro, DIY) in circular pattern
- [ ] Press 2 — enters Support Queue, hear welcome message and comfort message
- [ ] Press 3 — hear Directory & Options submenu
- [ ] Press 3, then 1 — dial by name directory
- [ ] Press 3, then 2 — dial by extension
- [ ] Press 3, then 0 — returns to Main Menu
- [ ] Press 0 — transfers to Store1 Mobile (operator, ext 0932)
- [ ] Press # — greeting replays
- [ ] Call after 5 PM ET — hear after-hours greeting
- [ ] Press 1 after hours — goes to voicemail
- [ ] Press 0 after hours — transfers to +19195559876
- [ ] Call on 2026-01-01 — hear holiday greeting

---

## 7. Estimated Execution

- **Mode:** Synchronous (sequential CLI commands)
- **Estimated time:** 10–15 minutes
- **Steps:** 7 major steps (8 create commands + 4 update commands)
- **Risk items:**
  - AA key action field names must match exactly what the API expects (`TRANSFER_WITHOUT_PROMPT` vs `TRANSFER_TO_HUNT_GROUP` — will confirm actual field names live; may need `--debug` on first AA update)
  - Hunt group `callPolicies.noAnswer` object structure needs verification — will use `--debug` flag if rejected
  - CQ queue settings JSON body depth — will verify with `--output json` read-back

---

## 8. Approval

- [ ] I approve this plan. Proceed with execution.
- [ ] I need changes. [Describe modifications]
- [ ] Cancel.
