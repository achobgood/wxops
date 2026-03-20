# Multi-Tier Call Flow -- Mock Data Spec

Complete provisioning spec for a two-tier auto attendant call flow with hunt group and call queue backends. All IDs reference live resources in org `ahobgood-sbx`. All mock values are realistic and copy-pasteable.

---

## 1. Org Context

| Field | Value |
|-------|-------|
| Org ID | `Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi9hOTUyN2Q2MC1lNzhjLTQzMzAtOWM1My04MzMxYTBjNWFhN2I` |
| Admin | `admin@ahobgood.wbx.ai` |
| Domain | `ahobgood-sbx.calls.webex.com` |

---

## 2. Location

Use existing **HQ** location.

| Field | Value |
|-------|-------|
| Name | HQ |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |
| Address | 200 S Dawson St, Raleigh, NC 27601, US |
| Time Zone | America/New_York |
| Preferred Language | en_us |
| Announcement Language | en_us |

---

## 3. Schedules

### 3a. Business Hours Schedule

| Field | Value |
|-------|-------|
| Schedule Name | `Business Hours` |
| Schedule Type | `businessHours` |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |

**Events (recurring weekly):**

| Day | Start Time | End Time |
|-----|-----------|----------|
| Monday | 08:00 | 17:00 |
| Tuesday | 08:00 | 17:00 |
| Wednesday | 08:00 | 17:00 |
| Thursday | 08:00 | 17:00 |
| Friday | 08:00 | 17:00 |
| Saturday | *(closed)* | *(closed)* |
| Sunday | *(closed)* | *(closed)* |

### 3b. Holiday Schedule

| Field | Value |
|-------|-------|
| Schedule Name | `US Holidays 2026` |
| Schedule Type | `holidays` |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |

**Events:**

| Holiday Name | Start Date | End Date | All Day |
|-------------|-----------|----------|---------|
| New Year's Day | 2026-01-01 | 2026-01-01 | true |
| Independence Day | 2026-07-03 | 2026-07-03 | true |
| Thanksgiving | 2026-11-26 | 2026-11-27 | true |
| Christmas Day | 2026-12-25 | 2026-12-25 | true |

---

## 4. Users / Agents

### 4a. Sales Team (Hunt Group Agents)

| Role | First Name | Last Name | Email | Extension | Person ID |
|------|-----------|----------|-------|-----------|-----------|
| Sales Agent 1 | Store1 | Mobile | achobgood+store1@gmail.com | 0932 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80YzVhMWI2Yy0zMThjLTQyMGEtYTMzYy00ZWI2NjIxZThjZTU` |
| Sales Agent 2 | Store1 | Pro | store1pro@aap.com | 88 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS82YTc4YzBjMi1kZGRlLTQzZTMtYTE0MS03MTBkMmEwMTc3Yjc` |
| Sales Agent 3 | Store1 | DIY | store1DIY@aap.com | 102981 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9iZWI4OWMzYi00OWZiLTQ5YzMtYmE1MC03NTYyM2ViNDA0Nzg` |

### 4b. Support Team (Call Queue Agents)

| Role | First Name | Last Name | Email | Extension | Person ID |
|------|-----------|----------|-------|-----------|-----------|
| Support Agent 1 | IHG | Agent1 | achobgood+ihg@gmail.com | 1111 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hZmVjNjY0ZC04ZTI4LTQyYWQtYWVmMi1jNDg2Y2I2YjExZWI` |
| Support Agent 2 | Store1 | Phone1 | st1p1@aap.com | 107899 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xNGI1YzBiNy00MzJlLTQxM2MtOWI3Mi04Y2M1NmU0NDQ5ZjE` |
| Support Agent 3 | Store1 | Phone2 | st1p2@aap.com | 107888 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80ODhhZDc5MS0zYTg0LTQyYTYtOTljYS1jNGY2YjBiOTFkMzQ` |

### 4c. Operator

| Role | First Name | Last Name | Email | Person ID |
|------|-----------|----------|-------|-----------|
| Operator | Store1 | Mobile | achobgood+store1@gmail.com | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80YzVhMWI2Yy0zMThjLTQyMGEtYTMzYy00ZWI2NjIxZThjZTU` |

---

## 5. Hunt Group -- "Sales Team"

| Field | Value |
|-------|-------|
| Name | `Sales Team` |
| Extension | `8100` |
| Phone Number | *(none -- extension only)* |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |
| Call Policy (Ring Pattern) | `CIRCULAR` |
| Number of Rings | `5` |
| No Answer Action | `FORWARD_TO_PHONE_NUMBER` |
| No Answer Forward To | `+19195551234` (external overflow) |
| Enabled | `true` |

**Agents:**

| Agent Name | Person ID | Extension |
|-----------|-----------|-----------|
| Store1 Mobile | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80YzVhMWI2Yy0zMThjLTQyMGEtYTMzYy00ZWI2NjIxZThjZTU` | 0932 |
| Store1 Pro | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS82YTc4YzBjMi1kZGRlLTQzZTMtYTE0MS03MTBkMmEwMTc3Yjc` | 88 |
| Store1 DIY | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9iZWI4OWMzYi00OWZiLTQ5YzMtYmE1MC03NTYyM2ViNDA0Nzg` | 102981 |

---

## 6. Call Queue -- "Support Queue"

| Field | Value |
|-------|-------|
| Name | `Support Queue` |
| Extension | `8200` |
| Phone Number | *(none -- extension only)* |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |
| Call Distribution Policy | `SIMULTANEOUS` |
| Queue Size | `15` |
| Max Wait Time (seconds) | `120` |
| Overflow Action | `PERFORM_BUSY_TREATMENT` |
| Overflow Phone Number | *(none -- busy treatment only)* |
| Enabled | `true` |

**Greetings & Messages:**

| Setting | Value |
|---------|-------|
| Welcome Message Enabled | `true` |
| Welcome Message Always Enabled | `false` |
| Welcome Message Audio Source | `DEFAULT` |
| Comfort Message Enabled | `true` |
| Comfort Message Time Between Messages (seconds) | `30` |
| Comfort Message Audio Source | `DEFAULT` |
| Music On Hold Enabled | `true` |
| Music On Hold Audio Source | `DEFAULT` |

**Agents:**

| Agent Name | Person ID | Extension |
|-----------|-----------|-----------|
| IHG Agent1 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS9hZmVjNjY0ZC04ZTI4LTQyYWQtYWVmMi1jNDg2Y2I2YjExZWI` | 1111 |
| Store1 Phone1 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xNGI1YzBiNy00MzJlLTQxM2MtOWI3Mi04Y2M1NmU0NDQ5ZjE` | 107899 |
| Store1 Phone2 | `Y2lzY29zcGFyazovL3VzL1BFT1BMRS80ODhhZDc5MS0zYTg0LTQyYTYtOTljYS1jNGY2YjBiOTFkMzQ` | 107888 |

---

## 7. Auto Attendant (Main) -- "Main Menu"

| Field | Value |
|-------|-------|
| Name | `Main Menu` |
| Extension | `8000` |
| Phone Number | `+14707521443` (unassigned, available at HQ) |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |
| First Name | `Main` |
| Last Name | `Menu` |
| Enabled | `true` |
| Business Hours Schedule | `Business Hours` (schedule created in step 3a) |
| Holiday Schedule | `US Holidays 2026` (schedule created in step 3b) |

### Business Hours Menu

| Setting | Value |
|---------|-------|
| Greeting Type | `DEFAULT` |
| Extension Dialing Enabled | `true` |
| Directory Enabled | `false` |

| Key | Action | Destination |
|-----|--------|-------------|
| 1 | `TRANSFER_TO_HUNT_GROUP` | Sales Team (ext 8100, created in step 5) |
| 2 | `TRANSFER_TO_CALL_QUEUE` | Support Queue (ext 8200, created in step 6) |
| 3 | `TRANSFER_TO_AUTO_ATTENDANT` | Directory & Options (ext 8001, created in step 8) |
| 0 | `TRANSFER_TO_OPERATOR` | Store1 Mobile (`Y2lzY29zcGFyazovL3VzL1BFT1BMRS80YzVhMWI2Yy0zMThjLTQyMGEtYTMzYy00ZWI2NjIxZThjZTU`) |
| # | `REPEAT_MENU` | *(replays greeting)* |

### After-Hours Menu

| Setting | Value |
|---------|-------|
| Greeting Type | `DEFAULT` |
| Extension Dialing Enabled | `false` |
| Directory Enabled | `false` |

| Key | Action | Destination |
|-----|--------|-------------|
| 1 | `TRANSFER_TO_MAILBOX` | Main Menu voicemail |
| 0 | `TRANSFER_TO_PHONE_NUMBER` | `+19195559876` (after-hours answering service) |

### Holiday Menu

| Setting | Value |
|---------|-------|
| Greeting Type | `DEFAULT` |
| Extension Dialing Enabled | `false` |
| Directory Enabled | `false` |

| Key | Action | Destination |
|-----|--------|-------------|
| 1 | `TRANSFER_TO_MAILBOX` | Main Menu voicemail |
| 0 | `TRANSFER_TO_PHONE_NUMBER` | `+19195559876` (after-hours answering service) |

---

## 8. Auto Attendant (Submenu) -- "Directory & Options"

| Field | Value |
|-------|-------|
| Name | `Directory & Options` |
| Extension | `8001` |
| Phone Number | *(none -- extension only, reached via Main Menu key 3)* |
| Location ID | `Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ` |
| First Name | `Directory` |
| Last Name | `Options` |
| Enabled | `true` |
| Business Hours Schedule | `Business Hours` (same schedule as Main Menu) |

### Business Hours Menu

| Setting | Value |
|---------|-------|
| Greeting Type | `DEFAULT` |
| Extension Dialing Enabled | `true` |
| Directory Enabled | `true` |

| Key | Action | Destination |
|-----|--------|-------------|
| 1 | `TRANSFER_TO_NAME_DIALING` | Dial by name directory |
| 2 | `TRANSFER_TO_EXTENSION_DIALING` | Dial by extension |
| 0 | `TRANSFER_TO_AUTO_ATTENDANT` | Main Menu (ext 8000, created in step 7) |
| # | `REPEAT_MENU` | *(replays greeting)* |

### After-Hours Menu

Falls through to Main Menu after-hours behavior. If the submenu is reached during after-hours (shouldn't happen since Main Menu won't route there), default to:

| Key | Action | Destination |
|-----|--------|-------------|
| 0 | `TRANSFER_TO_AUTO_ATTENDANT` | Main Menu (ext 8000) |

---

## 9. Dependency Order

Resources must be created in this exact sequence. Each step depends on the steps above it.

```
Step 1: Location
         HQ already exists -- no action needed.

Step 2: Schedules (no dependencies beyond location)
    2a:  Business Hours schedule at HQ
    2b:  US Holidays 2026 schedule at HQ

Step 3: Users / Agents
         All 6 users already exist -- no action needed.
         Verify calling licenses are assigned (confirmed above).

Step 4: Hunt Group -- "Sales Team"
         Depends on: Location (step 1), Sales agents (step 3)
         Creates: Hunt group at ext 8100

Step 5: Call Queue -- "Support Queue"
         Depends on: Location (step 1), Support agents (step 3)
         Creates: Call queue at ext 8200

Step 6: Auto Attendant (Submenu) -- "Directory & Options"
         Depends on: Location (step 1), Business Hours schedule (step 2a)
         Creates: AA at ext 8001
         NOTE: Create BEFORE Main Menu so Main Menu can reference it.
               The submenu's key-0 back-link to Main Menu must be
               configured AFTER Main Menu exists (step 7, then update).

Step 7: Auto Attendant (Main) -- "Main Menu"
         Depends on: Location (step 1), Business Hours schedule (step 2a),
                     Holiday schedule (step 2b), Hunt Group (step 4),
                     Call Queue (step 5), Submenu AA (step 6),
                     Operator user (step 3)
         Creates: AA at ext 8000, phone number +14707521443

Step 8: Update Submenu AA Key 0
         Depends on: Main Menu AA (step 7)
         Updates: Directory & Options submenu key 0 to point to Main Menu AA
         This resolves the circular reference between the two AAs.
```

### Circular Reference Resolution

The Main Menu (key 3) routes to the Submenu, and the Submenu (key 0) routes back to the Main Menu. This is a circular dependency. The resolution strategy is:

1. Create the Submenu first **without** key 0 configured (or with key 0 temporarily set to `REPEAT_MENU`).
2. Create the Main Menu with key 3 pointing to the Submenu.
3. Update the Submenu to set key 0 to `TRANSFER_TO_AUTO_ATTENDANT` targeting the Main Menu.

---

## 10. Call Flow Diagram

```
Inbound Call (+14707521443)
         |
         v
  +--------------+
  |  Main Menu   |  ext 8000
  |  (AA)        |  +14707521443
  +--------------+
   |  |  |  |  |
   1  2  3  0  #
   |  |  |  |  |
   |  |  |  |  +---> Repeat Greeting
   |  |  |  |
   |  |  |  +-------> Operator (Store1 Mobile, ext 0932)
   |  |  |
   |  |  +----------> Directory & Options (AA, ext 8001)
   |  |                  |  |  |  |
   |  |                  1  2  0  #
   |  |                  |  |  |  +---> Repeat Greeting
   |  |                  |  |  +------> Back to Main Menu
   |  |                  |  +---------> Dial by Extension
   |  |                  +------------> Dial by Name
   |  |
   |  +--------------> Support Queue (CQ, ext 8200)
   |                      Agents: IHG Agent1, Store1 Phone1, Store1 Phone2
   |                      Simultaneous ring, 15 queue slots, 120s max wait
   |
   +-----------------> Sales Team (HG, ext 8100)
                          Agents: Store1 Mobile, Store1 Pro, Store1 DIY
                          Circular ring, 5 rings, overflow to +19195551234

After Hours / Holidays:
   1 ---> Voicemail
   0 ---> +19195559876 (answering service)
```

---

## 11. Validation Checklist

After all resources are provisioned, verify:

- [ ] Call `+14707521443` -- hear Main Menu greeting
- [ ] Press 1 -- rings Sales Team agents in circular pattern
- [ ] Press 2 -- enters Support Queue, hear welcome message
- [ ] Press 3 -- hear Directory & Options submenu
- [ ] Press 3, then 1 -- dial by name directory
- [ ] Press 3, then 0 -- returns to Main Menu
- [ ] Press 0 -- transfers to Store1 Mobile (operator)
- [ ] Press # -- greeting replays
- [ ] Call after 5 PM -- hear after-hours greeting
- [ ] Press 1 after hours -- goes to voicemail
- [ ] Press 0 after hours -- transfers to +19195559876
- [ ] Call on 2026-01-01 -- hear holiday greeting
