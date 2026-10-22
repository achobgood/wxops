# Business Rules Engine (BRE) — Platform Reference

<!-- ref-tag: bre-v1 -->

## Overview

The BRE enables organizations to upload datasets (e.g., ANI lists) that WxCC accesses at runtime for routing decisions or agent-visible information. It is a native WxCC component — no external database required.

**Three components:**

| Component | Purpose | Who Uses It |
|-----------|---------|-------------|
| **BRE Utility** | Create domains, attributes, contexts, labels, and rule sets | Flow builders |
| **BRE DataSync** | Upload/manage data (CSV or manual entry) | Full Administrators |
| **Flow Designer BRE Request** | Invoke BRE rule evaluation during call processing | Flow designers |

**Primary use case:** Route calls based on the caller's ANI matching against uploaded lists (e.g., VIP callers → Gold Queue, unknown callers → Silver Queue).

---

## PII Restrictions

**Do not upload any Personally Identifiable Information (PII) to the BRE except ANI data.** ANI (telephone number) is the only permitted PII.

Prohibited data:
- Full names
- Social security numbers
- Email addresses
- Physical addresses
- Financial information (credit card numbers, bank accounts)

---

## Core Concepts

### Attribute

A named variable or data field created within the BRE Utility. Serves as a container for information that the BRE uses to process requests and generate outputs.

| Attribute | Purpose |
|-----------|---------|
| `context` | Specifies the targeted domain for a BRE Request activity. This is the mandatory predefined parameter in the BRE Request. |
| `ani` | The caller's phone number, passed from Flow Designer via `{{NewPhoneContact.ANI}}` or `{{NewContact.ANI}}`. |
| Custom attributes | Any additional data fields your rules need (e.g., `routeInfo`, `priority`). |

### Context

Associates an attribute with a domain. When a flow invokes the BRE Request activity, it tells the BRE which set of rules to evaluate by passing the `context` value.

### Label

A specific type of attribute designed to hold the **output** (result) of a rule's evaluation. After BRE evaluates its rules, it communicates the outcome back to the flow via labels.

### Domain

The table within BRE containing the relevant data. The domain guides BRE to the correct dataset and corresponding rule set. Example domain: `ANILookup`.

### How They Relate

1. Create an **Attribute** (e.g., `context`)
2. Create a **Context** and associate the attribute — this links to a **Domain** (the data table)
3. Create **Labels** (e.g., `routeInfo`) — these hold the rule output
4. Create **Rules** that evaluate incoming data against the domain and set labels
5. In Flow Designer, the **BRE Request** activity passes `context` and `ani` → BRE evaluates rules → returns label values

---

## BRE Utility — Creating Rules

### Access

Log in to the Cisco Webex Contact Center Management Portal:
**Management Portal > Business Rules** to open the BRE Utility.

### Step 1: Create Attributes

Navigate to **Attributes** > click **Add**:

| Field | Value |
|-------|-------|
| Name | `context` (or custom name) |
| Data Type | Text (required — select from dropdown) |

Click **Save**. Repeat for additional attributes (`ani`, `routeInfo`, etc.).

### Step 2: Create Contexts

Select **Contexts** > click **+Add Context**:

| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Context identifier |
| Description | No | Optional explanation |
| Attribute | Yes | Select from dropdown (if multiple attributes exist) |

Click **Save**.

### Step 3: Create Rules

On the Contexts page, click **+Add Rule**:

| Field | Description |
|-------|-------------|
| Name | Rule identifier (e.g., "ANI Match Found") |
| Description | Optional explanation |
| Active | Checkbox — must be checked for the rule to fire |
| Label | Select from dropdown (the output attribute) |
| Priority | Slider 1–100 (100 = highest priority) |
| Conditions | Dropdown selections with attributes/values |

**Best practice:** Create a rule set that covers **all** cases. For example, create rules for both "Match Found" and "Match Not Found" conditions.

### Rule Editor (Drools Syntax)

For complex logic, use the Rule Editor instead of the GUI conditions builder. BRE uses Drools syntax.

**ANI Match Found:**

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

**ANI Match Not Found:**

```drools
when
  c: Contact()
  eval(c.getGlobalValuesManager().getAsString( c.getTenantId(),
    c.getAttribute("context")+"." + c.getAttribute("ani")) == null)
then
  c.putAttribute("routeInfo", "NotFound");
end
```

**Key Drools APIs:**

| Method | Purpose |
|--------|---------|
| `c.getAttribute("name")` | Read an attribute value from the incoming request |
| `c.putAttribute("name", "value")` | Set an attribute (label) value — this is the rule output |
| `c.getGlobalValuesManager().getAsString(tenantId, key)` | Look up a value from the BRE data store |
| `c.getTenantId()` | Get the current tenant identifier |

The lookup key format is `{context}.{ani}` — the context name concatenated with the ANI value, separated by a period.

---

## BRE DataSync — Managing Data

### Prerequisites

- Contact Cisco Customer Service Account Manager to get DataSync access
- **Full Administrator role required** — Partner Admins, External Admins, Agents, and Supervisors cannot access DataSync
- Single Sign-On integration required

### Regional URLs

**DataSync URLs:**

| Region | URL |
|--------|-----|
| US | `https://bre-datasync.produs1.ciscoccservice.com/datasync/` |
| EU1 | `https://bre-datasync.prodeu1.ciscoccservice.com/datasync/` |
| EU2 | `https://bre-datasync.prodeu2.ciscoccservice.com/datasync/` |
| ANZ | `https://bre-datasync.prodanz1.ciscoccservice.com/datasync/` |
| Canada | `https://bre-datasync.prodca1.ciscoccservice.com/datasync/` |
| Japan | `https://bre-datasync.prodjp1.ciscoccservice.com/datasync/` |
| Singapore | `https://bre-datasync.prodsg1.ciscoccservice.com/datasync/` |

**BRE Admin UI URLs:**

| Region | URL |
|--------|-----|
| US | `https://bre.produs1.ciscoccservice.com/bre/` |
| EU1 | `https://bre.prodeu1.ciscoccservice.com/bre/` |
| EU2 | `https://bre.prodeu2.ciscoccservice.com/bre/` |
| ANZ | `https://bre.prodanz1.ciscoccservice.com/bre/` |
| Canada | `https://bre.prodca1.ciscoccservice.com/bre/` |
| Japan | `https://bre.prodjp1.ciscoccservice.com/bre/` |
| Singapore | `https://bre.prodsg1.ciscoccservice.com/bre/` |

### Adding Data Manually

1. Login via your region's DataSync URL
2. Select **BRE Data List** to view tenant org info
3. Click **Add BRE Data**
4. Select **Organization Name** from TenantName dropdown
5. Select **BRE Lookup Type** from dropdown
6. Click **Add Data** → enter Key/Value pairs
7. Click **Submit**

### Uploading CSV Data

1. Click **Upload BRE CSV Data**
2. Select **Organization Name** from dropdown
3. Select **BRE Lookup Type** from dropdown
4. Click **Upload** to browse for the CSV file
5. Click **Submit**

**CSV format:** Three columns — Key, Value, Action

```csv
7251600011,GoldQueue,Add
7251600012,SilverQueue,Add
7251600013,GoldQueue,Update
725160001,,Delete
```

Actions (case-insensitive): `Add`, `Update`, `Delete`. For Delete, leave the Value column empty.

### Sizing Limits

| Constraint | Limit |
|-----------|-------|
| BRE Lookup Type (key) | VARCHAR(200) max |
| Value field | VARCHAR(500) max |
| Lookup Types per org | 100 |
| Rows per Lookup Type | 100,000 |
| CSV file size | 10 MB |

---

## BRE Request Activity (Flow Designer)

The BRE Request activity invokes BRE rule evaluation during call processing. It is a native Flow Designer activity — drag it from the Activity Library onto the canvas.

### General Settings

| Field | Description |
|-------|-------------|
| Activity Label | Name for the activity (e.g., "BRERequest1") |
| Activity Description | Optional description |

### Query Parameters

| Parameter | Required | Editable | Default Value | Description |
|-----------|----------|----------|---------------|-------------|
| `context` | Yes | No (cannot edit/delete) | — | Must match the Context name in BRE Utility. Tells BRE which domain/rule set to evaluate. |
| `ani` | No | Yes (can edit/delete) | `{{NewPhoneContact.ANI}}` | Caller's phone number. Default param — can be renamed or removed. |

Click **Add New** to add custom key-value parameter rows beyond `context` and `ani`.

### Response Settings

| Field | Default | Description |
|-------|---------|-------------|
| Response Timeout | 2000 ms | How long to wait for BRE response before timing out |
| Number of Retries | — | Retry attempts after failure (retries only on 5xx status codes) |

### Parse Settings

Extract values from the BRE response into flow variables:

| Field | Description |
|-------|-------------|
| Response Variable | Custom flow variable to receive the parsed value (select from dropdown) |
| Path Expression | JSONPath expression for extraction — **always JSONPath regardless of response content type** |

BRE normalizes all response content types (XML, TOML, YAML, JSON) to JSON before parsing. Use JSONPath expressions in all cases.

**Content type examples:**

| Source Format | JSONPath Example | Returns |
|---------------|-----------------|---------|
| XML `<note><from>Jani</from></note>` | `$.note.from` | `"Jani"` |
| TOML `[owner] name = "Tom"` | `$.owner.name` | `"Tom"` |
| YAML `martin: job: Developer` | `$.martin.job` | `"Developer"` |
| JSON `{"martin": {"job": "Developer"}}` | `$.martin.job` | `"Developer"` |

### Decryption Settings

Toggle **Enable decryption** to control whether users with debug decryption access can view unmasked output values in flow debug logs. Only appears if decryption is enabled at the flow level.

### Output Variables

| Variable | Description |
|----------|-------------|
| `BRERequest1.httpResponseBody` | Full response body from BRE |
| `BRERequest1.httpStatusCode` | HTTP status code |

Status code ranges: 1xx (informational), 2xx (success), 3xx (redirect), 4xx (client error), 5xx (server error — triggers retries).

### Wiring Pattern

```
NewPhoneContact
  → BRE Request (context: "ANILookup", ani: {{NewPhoneContact.ANI}})
  → Condition: {{routeInfo}} == "NotFound"
      → TRUE: Queue Contact (default queue)
      → FALSE: Case ({{routeInfo}})
          ├── "GoldQueue": Queue Contact (Gold Queue)
          ├── "SilverQueue": Queue Contact (Silver Queue)
          └── default: Queue Contact (default queue)
```

## See Also

- [db-integration.md](db-integration.md) — the other way to fetch customer data into a flow
- [bre-setup.md](../playbooks/bre-setup.md) — the setup steps (attributes, contexts, rules, DataSync upload) that pair with this reference
- [flow-designer-essentials.md](flow-designer-essentials.md) — the Flow Designer activities the BRE Request activity sits among
