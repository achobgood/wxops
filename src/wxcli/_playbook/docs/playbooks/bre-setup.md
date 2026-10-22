# Business Rules Engine (BRE) Setup Playbook

## Overview

This playbook walks through setting up the BRE from scratch: getting DataSync access, creating rules in the BRE Utility, uploading data, and wiring a BRE Request activity into a Flow Designer flow.

> Platform reference: `docs/reference/bre.md` — covers BRE architecture, Drools syntax, DataSync regional URLs, sizing limits, and PII restrictions.

---

## 1. Get DataSync Access

1. Contact your **Cisco Customer Service Account Manager** to request BRE DataSync access
2. You will receive access to the DataSync portal at your region's URL
3. Requires **Full Administrator** role — Partner Admins, External Admins, Agents, and Supervisors cannot access DataSync
4. SSO integration required

**Regional DataSync URLs:** See `docs/reference/bre.md` § BRE DataSync — Managing Data > Regional URLs.

---

## 2. Create Attributes in BRE Utility

Open the BRE Utility: **Management Portal > Business Rules**

### 2.1 Create the `context` Attribute

1. Navigate to **Attributes** > click **Add**
2. Name: `context`
3. Data Type: **Text**
4. Click **Save**

### 2.2 Create Additional Attributes

Repeat for each attribute your rules need:

| Attribute | Data Type | Purpose |
|-----------|-----------|---------|
| `ani` | Text | Caller's phone number (input) |
| `routeInfo` | Text | Rule output — routing decision (label) |

---

## 3. Create a Context

1. Select **Contexts** > click **+Add Context**
2. Name: e.g., `ANILookup`
3. Description: (optional) e.g., "Routes calls based on ANI match"
4. Attribute: select `context` from dropdown
5. Click **Save**

---

## 4. Create Rules

On the Contexts page, click **+Add Rule** for each rule:

### 4.1 Rule: ANI Match Found

| Field | Value |
|-------|-------|
| Name | `ANI Match Found` |
| Active | Checked |
| Label | `routeInfo` |
| Priority | 100 (highest) |

**Rule Editor code:**

```drools
when
  c: Contact()
  eval(c.getGlobalValuesManager().getAsString( c.getTenantId(),
    c.getAttribute("context")+"."+
    c.getAttribute("ani")) != null)
then
  c.putAttribute("routeInfo",
    c.getGlobalValuesManager().getAsString(c.getTenantId(),
    c.getAttribute("context")+"." + c.getAttribute("ani")));
end
```

### 4.2 Rule: ANI Match Not Found

| Field | Value |
|-------|-------|
| Name | `ANI No Match` |
| Active | Checked |
| Label | `routeInfo` |
| Priority | 50 (lower than match rule) |

**Rule Editor code:**

```drools
when
  c: Contact()
  eval(c.getGlobalValuesManager().getAsString( c.getTenantId(),
    c.getAttribute("context")+"." + c.getAttribute("ani")) == null)
then
  c.putAttribute("routeInfo", "NotFound");
end
```

---

## 5. Upload Data via DataSync

### 5.1 Prepare the CSV

Create a CSV file with three columns: Key, Value, Action.

```csv
7251600011,GoldQueue,Add
7251600012,SilverQueue,Add
7251600013,GoldQueue,Add
```

**Format rules:**
- Actions: `Add`, `Update`, `Delete` (case-insensitive)
- For Delete: leave Value empty (e.g., `725160001,,Delete`)
- Key max length: 200 characters
- Value max length: 500 characters
- File size limit: 10 MB
- Max 100,000 rows per Lookup Type

### 5.2 Upload

1. Log in to your region's DataSync URL
2. Click **Upload BRE CSV Data**
3. Select your **Organization Name** from the dropdown
4. Select the **BRE Lookup Type** from the dropdown
5. Click **Upload** → browse for your CSV file
6. Click **Submit**

### 5.3 Verify

After upload, select **BRE Data List** to confirm your data appears correctly.

---

## 6. Wire BRE Request into Flow Designer

### 6.1 Create Flow Variables

In **Flow Settings > Custom Variables**, create:

| Variable | Type | Purpose |
|----------|------|---------|
| `routeInfo` | String | Holds the BRE rule output |

### 6.2 Add BRE Request Activity

1. Drag **BRE Request** from the Activity Library onto the canvas
2. Configure:

| Field | Value |
|-------|-------|
| Activity Label | `BRERequest1` |
| context (Query Parameter) | `ANILookup` (must match your Context name exactly) |
| ani (Query Parameter) | `{{NewPhoneContact.ANI}}` (or `{{NewContact.ANI}}` for newer flows) |
| Response Timeout | `2000` (default — increase if BRE data set is large) |

3. In **Parse Settings**:

| Response Variable | Path Expression |
|-------------------|-----------------|
| `routeInfo` | `$.routeInfo` |

### 6.3 Branch on Result

Wire the BRE Request output to a **Condition** or **Case** activity:

```
NewPhoneContact
  → BRE Request (context: "ANILookup", ani: {{NewPhoneContact.ANI}})
  → Condition: {{routeInfo == "NotFound"}}
      → TRUE: Queue Contact (Default_Queue)
      → FALSE: Case ({{routeInfo}})
          ├── "GoldQueue": Queue Contact (Gold_Queue)
          ├── "SilverQueue": Queue Contact (Silver_Queue)
          └── default: Queue Contact (Default_Queue)
```

### 6.4 Publish

1. Click **Validate** — fix any errors
2. Click **Publish**
3. Link the flow to your Entry Point in Control Hub

---

## 7. Test End-to-End

1. Dial the PSTN number assigned to your Entry Point
2. The flow invokes BRE with the caller's ANI
3. BRE evaluates rules:
   - If the ANI is in the dataset → returns the associated queue name
   - If the ANI is not found → returns "NotFound"
4. The flow routes to the appropriate queue

**Debugging:**
- Check the BRE Data List in DataSync to confirm data was uploaded
- In Flow Designer, use **Flow Debug** to trace the BRE Request activity execution
- Verify the `context` parameter value matches your BRE Context name exactly (case-sensitive)
- Verify the ANI format matches your uploaded data format (with or without country code prefix)

---

## Common Patterns

### VIP Caller Routing

Upload a list of VIP ANIs with queue assignments. The BRE returns the queue name for known callers, routes unknowns to a default queue.

### Regional Routing

Upload ANIs grouped by region (area code ranges). BRE returns a region code, and the flow routes to the region-specific queue.

### Time-Limited Campaigns

Upload ANIs for a campaign, then bulk-delete via CSV when the campaign ends. No flow changes needed — just update the data.
