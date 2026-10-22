# Spec Diagram — Quick Reference

## Layout Constants

| Constant | Value | Notes |
|---|---|---|
| CARD_WIDTH | 230 | All activity cards |
| HORIZONTAL_SPACING | 300 | Between columns (depth levels) |
| VERTICAL_GAP | 80 | Between cards in same column |
| HEADER_HEIGHT | 56 | Top of card with badge + name |
| PORT_ROW_HEIGHT | 30 | Per exit port row |
| SECTION_HEADER_HEIGHT | 30 | "Details" / "Connections" label |
| MIN_DETAILS_CONTENT | 60 | Minimum content area height |
| DETAILS_LINE_HEIGHT | 15 | Per key-value pair in Details |
| MARGIN | 60 | Left/top offset for first card |
| EVENT_CARD_GAP | 40 | Between event handler cards |
| SUMMARY_PAGE_WIDTH | 1654 | DrawIO page width |
| SUMMARY_PAGE_HEIGHT | 1169 | DrawIO page height |

## Category Constants

| Category | Badge BG | Card Fill | Badge Shape | Activities |
|---|---|---|---|---|
| Start | #74E8D1 | #f0fefb | border-radius:3px | Start Flow / NewPhoneContact |
| Event | #74E8D1 | #f0fefb | border-radius:3px | All event handlers (GlobalErrors, AgentOffer, etc.) |
| Action | #E2CAFC | #faf5fe | border-radius:3px | Play Message, Set Variable, HTTP Request, Parse, Queue Contact, Play Music, Record, Collect Digits, Send Digits, Screen Pop, Set Announcement, Set Whisper, Upload Audio, Set Caller ID, Set Contact Priority, Recording Control, Start Media Stream, Wait, Advanced Queue Information, Get Queue Info, BRE Request, Callback, Schedule Callback, Escalate CDG, Queue To Agent, Virtual Agent V2, Virtual Agent (Legacy), Feedback, Feedback V2 |
| Function | #FEBA7F | #fff3e8 | border-radius:3px | Functions |
| Gateway | #FFCE73 | #fff6e6 | border-radius:3px | Condition, Menu, Case, Business Hours, Percentage Allocation |
| Terminating | #FFC7D2 | #fff5f7 | border-radius:50% | Disconnect Contact, Blind Transfer, Bridged Transfer, End Flow, GoTo, Outdial Entry Point |

## Icon Registry

Each activity type maps to an SVG data URI used as the badge background-image. Activities not listed here use their category's default icon.

### Start Category

**ICON_START_FLOW** (default for Start category):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M16%2027C9.925%2027%205%2022.075%205%2016S9.925%205%2016%205s11%204.925%2011%2011-4.925%2011-11%2011m0%202c7.18%200%2013-5.82%2013-13S23.18%203%2016%203%203%208.82%203%2016s5.82%2013%2013%2013M19.5%2016l-5.25%203.031V12.97zm2.5.866a1%201%200%200%200%200-1.732l-8.25-4.763a1%201%200%200%200-1.5.866v9.526a1%201%200%200%200%201.5.866z%22/%3E%3C/svg%3E
```

### Event Category

**ICON_EVENT** (default for Event category — used by all event handlers):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M30%2015.008a5.014%205.014%200%200%200-4.187-4.913%209.998%209.998%200%200%200-19.628-.012%204.996%204.996%200%200%200%20.818%209.925%201%201%200%200%200%201-1.003L8%2012a8%208%200%200%201%2016%200v6a8.01%208.01%200%200%201-5.388%207.553%202.986%202.986%200%201%200%20.332%202.003%2010.03%2010.03%200%200%200%206.865-7.643A5.01%205.01%200%200%200%2030%2015.008M6%2017.837a2.992%202.992%200%200%201%200-5.645zM16%2028a1%201%200%201%201%200-2%201%201%200%200%201%200%202m10-10.195v-5.602a2.96%202.96%200%200%201%200%205.602%22/%3E%3C/svg%3E
```

### Action Category

**ICON_SET_VARIABLE** (Set Variable):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M9.408%2024.337a9.133%209.133%200%200%201-.013-16.674%201%201%200%201%200-.818-1.824%2011.132%2011.132%200%200%200%20.015%2020.324%201%201%200%201%200%20.815-1.826M23.423%205.834a1%201%200%201%200-.818%201.824%209.138%209.138%200%200%201-.013%2016.684%201%201%200%200%200%20.816%201.826%2011.138%2011.138%200%200%200%20.015-20.334M20.707%2011.293a1%201%200%200%200-1.414%200l-2.77%202.77c-1.172-2.224-4.124-2.995-4.28-3.033a1%201%200%200%200-.488%201.94c.031.007%202.868.755%203.21%202.65l-3.672%203.673a1%201%200%201%200%201.414%201.414l2.77-2.77c1.172%202.223%204.125%202.994%204.28%203.032a1%201%200%200%200%20.488-1.939c-.03-.007-2.868-.756-3.21-2.651l3.672-3.672a1%201%200%200%200%200-1.414%22/%3E%3C/svg%3E
```

**ICON_HTTP_REQUEST** (HTTP Request, Custom Connectors, HTTP Connector):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M18.317%209.051a.996.996%200%200%200-1.265.633l-4%2012a1%201%200%200%200%20.632%201.264%201%201%200%200%200%201.264-.631l4-12a1%201%200%200%200-.631-1.266M10.707%209.293a1%201%200%200%200-1.414%200l-6%206a1%201%200%200%200%200%201.414l6%206a1%201%200%200%200%201.414-1.414L5.414%2016l5.293-5.293a1%201%200%200%200%200-1.414M28.707%2015.293l-6-6a1%201%200%201%200-1.414%201.414L26.586%2016l-5.293%205.293a1%201%200%201%200%201.414%201.414l6-6a1%201%200%200%200%200-1.414%22/%3E%3C/svg%3E
```

**ICON_PLAY_MESSAGE** (Play Message, Play Music — same play-circle icon as Start but in Action color):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M16%2027C9.925%2027%205%2022.075%205%2016S9.925%205%2016%205s11%204.925%2011%2011-4.925%2011-11%2011m0%202c7.18%200%2013-5.82%2013-13S23.18%203%2016%203%203%208.82%203%2016s5.82%2013%2013%2013M19.5%2016l-5.25%203.031V12.97zm2.5.866a1%201%200%200%200%200-1.732l-8.25-4.763a1%201%200%200%200-1.5.866v9.526a1%201%200%200%200%201.5.866z%22/%3E%3C/svg%3E
```

### Function Category

**ICON_FUNCTIONS** (Functions activity):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M29%2026H3a1%201%200%200%200%200%202h26a1%201%200%200%200%200-2M3%206h26a1%201%200%201%200%200-2H3a1%201%200%200%200%200%202M17.052%209.684l-4%2012a.997.997%200%200%200%20.63%201.267%201%201%200%200%200%201.266-.635l4-12a.997.997%200%200%200-.63-1.267%201%201%200%200%200-1.266.635M10.707%209.293a1%201%200%200%200-1.414%200l-6%206a1%201%200%200%200%200%201.414l6%206a1%201%200%200%200%201.414-1.414L5.414%2016l5.293-5.293a1%201%200%200%200%200-1.414M21.293%2022.707a1%201%200%200%200%201.414%200l6-6a1%201%200%200%200%200-1.414l-6-6a1%201%200%200%200-1.414%201.414L26.586%2016l-5.293%205.293a1%201%200%200%200%200%201.414%22/%3E%3C/svg%3E
```

### Gateway Category

**ICON_CONDITION** (Condition, Business Hours, Percentage Allocation):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M16%204a2%202%200%201%200%200%204%202%202%200%200%200%200-4m-4%202a4%204%200%201%201%208%200%204%204%200%200%201-8%200m4%205a1%201%200%200%201%201%201v3h12a1%201%200%201%201%200%202h-2v3a1%201%200%201%201-2%200v-3H7v3a1%201%200%201%201-2%200v-3H3a1%201%200%201%201%200-2h12v-3a1%201%200%200%201%201-1M9.707%2023.707a1%201%200%200%200-1.414-1.414L6%2024.586l-2.293-2.293a1%201%200%200%200-1.414%201.414L4.586%2026l-2.293%202.293a1%201%200%201%200%201.414%201.414L6%2027.414l2.293%202.293a1%201%200%200%200%201.414-1.414L7.414%2026zm19.944.052a1%201%200%200%200-1.302-1.518l-6.297%205.397-2.345-2.345a1%201%200%200%200-1.414%201.414l3%203a1%201%200%200%200%201.358.052z%22/%3E%3C/svg%3E
```

**ICON_MENU** (Menu, Case):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M12%2011h16a1%201%200%201%200%200-2H12a1%201%200%201%200%200%202M28%2021H12a1%201%200%201%200%200%202h16a1%201%200%201%200%200-2M7.44%2021.825q.45-.64.45-1.4%200-.84-.59-1.39-.65-.61-1.75-.61-.94%200-1.62.49a2.14%202.14%200%200%200-.93%201.53h1.26q.07-.47.38-.76.34-.31.88-.31.49%200%20.8.25.34.29.34.8%200%20.46-.275.87-.276.41-1.165%201.26l-2.04%201.98v1.04h4.67v-1.04H4.78l1.35-1.29q.97-.93%201.31-1.42M5.59%2013.645h1.19v-7H5.6l-1.6.83v1.16l1.59-.81z%22/%3E%3C/svg%3E
```

### Terminating Category

**ICON_BLIND_TRANSFER** (Blind Transfer, Bridged Transfer):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M9.8%2012.533a1%201%200%200%200%201.932-.517l-.646-2.412%206.19%203.537a1%201%200%200%200%201.365-.373l4.728-8.272a1%201%200%200%200-1.737-.992l-4.231%207.404-5.295-3.025%202.377-.636a1%201%200%201%200-.518-1.932L9.242%206.58a1%201%200%200%200-.707%201.225zM16%2017c-9.893%200-14%204.758-14%207.305v1.467A3.23%203.23%200%200%200%205.23%2029h3.57A3.214%203.214%200%200%200%2012%2025.781v-1.636A7%207%200%200%201%2016%2023a7%207%200%200%201%204%201.14v1.65A3.316%203.316%200%200%200%2023.332%2029h3.44A3.23%203.23%200%200%200%2030%2025.771v-1.466C30%2021.758%2025.894%2017%2016%2017m12%208.772A1.23%201.23%200%200%201%2026.772%2027h-3.44A1.31%201.31%200%200%201%2022%2025.79v-1.953C22%2022.308%2018.703%2021%2016%2021c-2.971%200-6%201.435-6%202.843v1.938A1.21%201.21%200%200%201%208.799%2027H5.23A1.23%201.23%200%200%201%204%2025.771v-1.466C4%2022.795%207.57%2019%2016%2019s12%203.795%2012%205.305z%22/%3E%3C/svg%3E
```

**ICON_DISCONNECT** (Disconnect Contact, End Flow, GoTo):
```
data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M24.002%202a6%206%200%201%200%206%206%206.006%206.006%200%200%200-6-6m0%202a3.995%203.995%200%200%201%203.858%203h-7.716a3.996%203.996%200%200%201%203.858-3m0%208a3.996%203.996%200%200%201-3.858-3h7.716a3.996%203.996%200%200%201-3.858%203M9.107%2022.843c6.996%206.996%2013.264%206.535%2015.065%204.734l1.037-1.037a3.23%203.23%200%200%200%200-4.566l-2.524-2.524a3.214%203.214%200%200%200-4.54.012l-1.157%201.157A7%207%200%200%201%2013.35%2018.6a7%207%200%200%201-2.023-3.634l1.168-1.166a3.317%203.317%200%200%200-.086-4.626L9.976%206.74a3.23%203.23%200%200%200-4.566%200L4.373%207.778c-1.8%201.8-2.261%208.069%204.734%2015.065M6.824%208.155a1.23%201.23%200%200%201%201.738%200l2.433%202.433a1.31%201.31%200%200%201%20.087%201.797l-1.383%201.38c-1.08%201.081.327%204.34%202.237%206.25%202.101%202.1%205.257%203.227%206.253%202.232l1.37-1.371a1.21%201.21%200%200%201%201.712-.012l2.524%202.524a1.23%201.23%200%200%201%200%201.738l-1.037%201.037c-1.068%201.067-6.275%201.227-12.236-4.735C4.56%2015.468%204.72%2010.26%205.786%209.192z%22/%3E%3C/svg%3E
```

### Icon Selection Logic

```
1. Look up activity type in ICON_REGISTRY by exact name
2. If not found, use the category default:
   - Start → ICON_START_FLOW
   - Event → ICON_EVENT
   - Action → ICON_PLAY_MESSAGE (play circle — generic action icon)
   - Function → ICON_FUNCTIONS
   - Gateway → ICON_CONDITION
   - Terminating → ICON_DISCONNECT
3. If category unknown, use ICON_PLAY_MESSAGE
```

Activity-to-icon overrides:

| Activity Type | Icon |
|---|---|
| Start Flow / NewPhoneContact | ICON_START_FLOW |
| Set Variable | ICON_SET_VARIABLE |
| HTTP Request | ICON_HTTP_REQUEST |
| Custom Connectors | ICON_HTTP_REQUEST |
| HTTP Connector | ICON_HTTP_REQUEST |
| Parse | ICON_HTTP_REQUEST |
| Play Message | ICON_PLAY_MESSAGE |
| Play Music | ICON_PLAY_MESSAGE |
| Functions | ICON_FUNCTIONS |
| Condition | ICON_CONDITION |
| Business Hours | ICON_CONDITION |
| Percentage Allocation | ICON_CONDITION |
| Menu | ICON_MENU |
| Case | ICON_MENU |
| Blind Transfer | ICON_BLIND_TRANSFER |
| Bridged Transfer | ICON_BLIND_TRANSFER |
| Queue To Agent | ICON_BLIND_TRANSFER |
| Disconnect Contact | ICON_DISCONNECT |
| End Flow | ICON_DISCONNECT |
| GoTo | ICON_DISCONNECT |
| Virtual Agent V2 | ICON_EVENT |
| All event handlers | ICON_EVENT |

## Port Definitions

Exit ports per activity type. These determine the rows in the Connections section of each card.

**Error port convention:** Error and Undefined Error ports auto-route to OnGlobalError. They MUST still appear as rows in the card's Connections section (so the card shows the port exists), but they do NOT generate edge cells in the diagram. Only generate an Error port edge if the design doc explicitly routes that Error port to a specific activity other than OnGlobalError.

| Activity Type | Exit Ports |
|---|---|
| Start Flow / NewPhoneContact | Out |
| Play Message | Default, Error (auto-handled — no edge) |
| Play Music | Default, Error (auto-handled — no edge) |
| Set Variable | Out, Error (auto-handled — no edge) |
| Queue Contact | Default, Failure — Default is the continuation path (hold treatment, e.g. Play Music, follows Queue Contact); `failure` is the only port in the live registry. See the Queue Contact note below |
| Disconnect Contact | (none — terminal) |
| Condition | True, False, Error (auto-handled — no edge) |
| Menu | (dynamic: one port per digit option + No-Input Timeout, Unmatched Entry, Undefined Error (auto-handled — no edge)) |
| Case | (dynamic: one port per case value + Default, Error (auto-handled — no edge)) |
| Business Hours | Overrides, Holidays, Working Hours, Default, Error (auto-handled — no edge) |
| Percentage Allocation | (dynamic: one port per percentage path + Error (auto-handled — no edge)) |
| HTTP Request | Default, Error (auto-handled — no edge) |
| Parse | Default, Error (auto-handled — no edge) |
| Collect Digits | Default, Error (auto-handled — no edge) |
| Send Digits | Default, Error (auto-handled — no edge) |
| Record | Default, Error (auto-handled — no edge) |
| Functions | Default, Error (auto-handled — no edge) |
| Blind Transfer | Failure |
| Bridged Transfer | Failure — the only port in the live registry; Cisco documents no output ports for this activity. See the Bridged Transfer note below |
| GoTo | (none — terminal) |
| End Flow | (none — terminal) |
| Callback | Default, Error (auto-handled — no edge) |
| Schedule Callback | Default, Error (auto-handled — no edge) |
| Get Queue Info | Default, Error (auto-handled — no edge) |
| Advanced Queue Information | Default, Error (auto-handled — no edge) |
| BRE Request | Default, Error (auto-handled — no edge) |
| Screen Pop | Default, Error (auto-handled — no edge) |
| Set Announcement | Default, Error (auto-handled — no edge) |
| Set Whisper | Default, Error (auto-handled — no edge) |
| Set Caller ID | Default, Error (auto-handled — no edge) |
| Set Contact Priority | Default, Error (auto-handled — no edge) |
| Recording Control | Default, Error (auto-handled — no edge) |
| Start Media Stream | Default, Error (auto-handled — no edge) |
| Upload Audio | Default, Error (auto-handled — no edge) |
| Wait | Default, Error (auto-handled — no edge) |
| Virtual Agent V2 | Handled, Escalated, Error (auto-handled — no edge) |
| Virtual Agent (Legacy) | Handled, Escalated, Error (auto-handled — no edge) |
| Feedback V2 | Default, Error (auto-handled — no edge) |
| Feedback | Default, Error (auto-handled — no edge) |
| Escalate CDG | Default, Error (auto-handled — no edge) |
| Queue To Agent | Default, Error (auto-handled — no edge) |
| Custom Connectors | Default, Error (auto-handled — no edge) |
| HTTP Connector | Default, Error (auto-handled — no edge) |
| Outdial Entry Point | (none — restricted context) |
| Call Progress Analysis | CPA Successful, Error (auto-handled — no edge) |
| Receive Message | Timeout, Error (auto-handled — no edge) — BYOC custom messaging; ports from live registry, no success port listed |
| Send Custom Message | Error (auto-handled — no edge) — BYOC custom messaging; ports from live registry, no success port listed |
| Cryptographic Hash | Default, Error (auto-handled — no edge) — Default is the implicit `out` port (registry lists only error) |
| Generate OTP | Default, Error (auto-handled — no edge) — Default is the implicit `out` port (registry lists only error) |
| Verify OTP | Failure, Resend, Error (auto-handled — no edge) — no success port verified; ports from live registry |
| Event handlers (all) | Out |

**Queue Contact — UNRESOLVED:** Cisco's error-code table lists "FC1014 — Queue Contact must stop flow. The output link can only connect to an End Flow activity," but unlike its neighbours FC1012 and FC1013 it does not state its scope, so "terminal" may hold inside an Event Flow and not in a main flow.

**Bridged Transfer — UNRESOLVED:** Cisco states the flow "retains control of the call" and "the call flow continues and reengages as required" after the third party hangs up, yet the live registry exposes no success port — both may be true if the continuation is implicit, and only a live call settles it.

## XML Templates

### mxfile Envelope

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram id="summary" name="Summary">
    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{SUMMARY_CELLS}
      </root>
    </mxGraphModel>
  </diagram>
  <diagram id="main-flow" name="Main Flow">
    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{MAIN_FLOW_CELLS}
      </root>
    </mxGraphModel>
  </diagram>
  <diagram id="event-flow" name="Event Flow">
    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{EVENT_FLOW_CELLS}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Activity Card — Root Cell

```xml
<mxCell id="{ID}" value="{HEADER_HTML}" style="swimlane;fontStyle=0;childLayout=stackLayout;horizontal=1;startSize=56;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;shadow=1;rounded=1;arcSize=3;align=left;fillColor={CARD_FILL};strokeColor=#d1d5db;swimlaneFillColor=#ffffff;points=[[0,{ENTRY_PORT_Y}]];portConstraint=east;" vertex="1" parent="1"><mxGeometry x="{X}" y="{Y}" width="230" height="{TOTAL_HEIGHT}" as="geometry"/></mxCell>
```

### Activity Card — Header HTML (value attribute)

The `{HEADER_HTML}` is an HTML-entity-encoded string. Before encoding, the raw HTML is:

```html
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;font-family:Helvetica Neue,Arial,sans-serif;"><tr><td width="46" valign="middle" style="padding-left:10px;"><div style="width:36px;height:36px;{BADGE_BORDER_RADIUS};background-color:{BADGE_COLOR};background-image:url('{ICON_SVG_URI}');background-size:22px 22px;background-position:center center;background-repeat:no-repeat;"></div></td><td valign="middle" style="padding-left:8px;"><b style="font-size:13px;color:#111827;">{ACTIVITY_NAME}</b><br/><span style="font-size:11px;color:#6b7280;">{ACTIVITY_TYPE_SLUG}</span></td></tr></table>
```

Where:
- `{BADGE_BORDER_RADIUS}` = `border-radius:3px` for non-terminating, `border-radius:50%` for terminating
- `{BADGE_COLOR}` = badge background color from Category Constants
- `{ICON_SVG_URI}` = SVG data URI from Icon Registry
- `{ACTIVITY_NAME}` = display name of the activity
- `{ACTIVITY_TYPE_SLUG}` = kebab-case activity type (e.g., `play-message`, `set-variable`, `condition`, `http-request`, `queue-contact`, `disconnect-contact`). Convert the canonical activity type name to lowercase and replace spaces with hyphens.

**Encode the entire HTML string for the value attribute:** replace `<` with `&lt;`, `>` with `&gt;`, `"` with `&quot;`, `&` with `&amp;`. Order matters: encode `&` first, then the rest.

### Activity Card — Details Section

When the Details section has content (config key-value pairs):

```xml
<mxCell id="{ID}_s0" value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Details" style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" vertex="1" parent="{ID}"><mxGeometry x="0" y="56" width="230" height="{DETAILS_HEIGHT}" as="geometry"/></mxCell>
```

When the Details section is **empty** (no config pairs), collapse it by default:

```xml
<mxCell id="{ID}_s0" value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Details" style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" collapsed="1" vertex="1" parent="{ID}"><mxGeometry x="0" y="56" width="230" height="30" as="geometry"><mxRectangle x="0" y="56" width="230" height="90" as="alternateBounds"/></mxGeometry></mxCell>
```

When collapsed: `height="30"` (section header only), the `mxRectangle alternateBounds` stores the expanded height so the user can expand it in draw.io. The collapsed details section has NO details content child cell.

### Activity Card — Details Content

```xml
<mxCell id="{ID}_s0_p0" value="{DETAILS_TEXT}" style="text;strokeColor=#d1d5db;fillColor=none;align=left;verticalAlign=top;spacingLeft=8;spacingRight=8;spacingTop=6;fontSize=8;rotatable=0;fontColor=#000000;html=0;whiteSpace=wrap;overflow=hidden;connectable=0;" vertex="1" parent="{ID}_s0"><mxGeometry x="0" y="30" width="230" height="{DETAILS_CONTENT_HEIGHT}" as="geometry"/></mxCell>
```

Where `{DETAILS_TEXT}` is **plain text** (not HTML): `key: value\nkey: value\n...` for each config pair. Use `html=0` so draw.io renders the value as plain text (no `<b>` tags needed). **XML entity encoding is still required** — the value is inside an XML attribute, so `&`, `<`, `>`, `"` must be encoded as `&amp;`, `&lt;`, `&gt;`, `&quot;` regardless of the `html` flag.

### Activity Card — Connections Section

```xml
<mxCell id="{ID}_s1" value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Connections" style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" vertex="1" parent="{ID}"><mxGeometry x="0" y="{CONNECTIONS_Y}" width="230" height="{CONNECTIONS_HEIGHT}" as="geometry"/></mxCell>
```

Where `{CONNECTIONS_Y}` = 56 + `{DETAILS_HEIGHT}`.

### Activity Card — Port Row

```xml
<mxCell id="{ID}_s1_p{N}" value="{PORT_NAME}" style="text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=8;spacingRight=4;fontSize=11;rotatable=0;points=[[1,0.5]];portConstraint=east;" vertex="1" parent="{ID}_s1"><mxGeometry x="0" y="{PORT_Y}" width="230" height="30" as="geometry"/></mxCell>
```

Where `{PORT_Y}` = 30 + (N * 30), N is the 0-based port index.

### Menu / Case — Split Sections

Menu and Case activities use **two** separate port sections instead of one "Connections" section:

1. **Options section** (`_s1`) — contains digit/value choice ports (e.g., "Option 0", "Option 1 - Sales", "Option 2 - Spanish")
2. **Error handling section** (`_s2`) — contains error-condition ports (e.g., "No-Input Timeout", "Unmatched Entry", "Undefined Error" for Menu; "Default", "Error" for Case)

```xml
<!-- Options section -->
<mxCell id="{ID}_s1" value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Options" style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" vertex="1" parent="{ID}"><mxGeometry x="0" y="{OPTIONS_Y}" width="230" height="{OPTIONS_HEIGHT}" as="geometry"/></mxCell>
<!-- Port rows for each digit/value option, parented to _s1 -->

<!-- Error handling section -->
<mxCell id="{ID}_s2" value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Error handling" style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" vertex="1" parent="{ID}"><mxGeometry x="0" y="{ERROR_Y}" width="230" height="{ERROR_HEIGHT}" as="geometry"/></mxCell>
<!-- Port rows for error conditions, parented to _s2 -->
```

Where:
- `{OPTIONS_Y}` = 56 + `{DETAILS_HEIGHT}`
- `{OPTIONS_HEIGHT}` = 30 + (option_port_count * 30)
- `{ERROR_Y}` = `{OPTIONS_Y}` + `{OPTIONS_HEIGHT}`
- `{ERROR_HEIGHT}` = 30 + (error_port_count * 30)
- Option port IDs use `{ID}_s1_p{N}`, error port IDs use `{ID}_s2_p{N}`
- Total card height = 56 + details_height + options_height + error_height

**Menu option ports**: Named "Option 0", "Option 1", "Option 2 - Spanish", etc. matching the actual digit choices from the plan.
**Menu error ports**: "No-Input Timeout", "Unmatched Entry", "Undefined Error" (always these three).
**Case option ports**: One per case value, matching the actual branch values from the plan.
**Case error ports**: "Default", "Error".

### Edge Cell

```xml
<mxCell id="{EDGE_ID}" value="{PORT_NAME}" style="edgeStyle=orthogonalEdgeStyle;curved=1;html=1;rounded=0;strokeColor=#6b7280;fontSize=10;fontColor=#374151;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY={TARGET_ENTRY_Y};entryDx=0;entryDy=0;" edge="1" source="{SOURCE_PORT_ID}" target="{TARGET_CARD_ID}" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
```

Where:
- `{PORT_NAME}` = the source port's display name (e.g., `Default`, `Error`, `True`, `False`). This renders as a label on the edge.
- `{SOURCE_PORT_ID}` = the port cell ID (e.g., `PlayMessage_001_s1_p0`)
- `{TARGET_CARD_ID}` = the root card cell ID (e.g., `Condition_001`)
- `{TARGET_ENTRY_Y}` = the entry port Y fraction of the target card

### Summary Tab — Brand Logo Cell

```xml
<mxCell id="sum_brand" value="&lt;img src=&quot;{CISCO_WEBEX_LOGO}&quot; height=&quot;28&quot; style=&quot;display:block&quot;/&gt;" style="text;html=1;align=center;verticalAlign=middle;fillColor=#218381;strokeColor=none;rounded=1;" vertex="1" parent="1"><mxGeometry x="20" y="20" width="820" height="52" as="geometry"/></mxCell>
```

### Summary Tab — Title Cell

```xml
<mxCell id="sum_title" value="{FLOW_NAME}" style="text;html=1;fontSize=22;fontStyle=1;align=left;verticalAlign=middle;fillColor=#0e7490;fontColor=#ffffff;strokeColor=none;rounded=1;spacingLeft=16;" vertex="1" parent="1"><mxGeometry x="20" y="82" width="820" height="54" as="geometry"/></mxCell>
```

### Summary Tab — Metadata Table Cell

```xml
<mxCell id="sum_meta" value="{METADATA_TABLE_HTML}" style="text;html=1;fontSize=11;align=left;verticalAlign=top;fillColor=#ffffff;strokeColor=#d1d5db;rounded=1;spacingLeft=0;spacingTop=0;" vertex="1" parent="1"><mxGeometry x="20" y="146" width="405" height="142" as="geometry"/></mxCell>
```

Metadata table HTML (before entity encoding):
```html
<table style="border-collapse:collapse;width:100%">
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Flow Name</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{FLOW_NAME}</td></tr>
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Author</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{AUTHOR}</td></tr>
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Created</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{DATE}</td></tr>
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Description</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{DESCRIPTION}</td></tr>
</table>
```

### Summary Tab — Stats Table Cell

```xml
<mxCell id="sum_stats" value="{STATS_TABLE_HTML}" style="text;html=1;fontSize=11;align=left;verticalAlign=top;fillColor=#ffffff;strokeColor=#d1d5db;rounded=1;spacingLeft=0;spacingTop=0;" vertex="1" parent="1"><mxGeometry x="435" y="146" width="405" height="142" as="geometry"/></mxCell>
```

Stats table HTML (before entity encoding):
```html
<table style="border-collapse:collapse;width:100%">
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Main Flow Nodes</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{MAIN_COUNT}</td></tr>
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Event Flow Nodes</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{EVENT_COUNT}</td></tr>
<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Total Variables</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{VAR_COUNT}</td></tr>
</table>
```

### Summary Tab — Variable Label + Table

```xml
<mxCell id="sum_varlabel" value="Flow Variables" style="text;html=1;fontSize=13;fontStyle=1;align=left;verticalAlign=middle;fillColor=#f3f4f6;strokeColor=#d1d5db;rounded=0;spacingLeft=10;" vertex="1" parent="1"><mxGeometry x="20" y="304" width="820" height="28" as="geometry"/></mxCell>
<mxCell id="sum_vars" value="{VARIABLES_TABLE_HTML}" style="text;html=1;fontSize=11;align=left;verticalAlign=top;fillColor=#ffffff;strokeColor=#d1d5db;rounded=1;spacingLeft=0;spacingTop=0;" vertex="1" parent="1"><mxGeometry x="20" y="332" width="820" height="{VARS_TABLE_HEIGHT}" as="geometry"/></mxCell>
```

Variables table HTML (before entity encoding):
```html
<table style="border-collapse:collapse;width:100%">
<tr style="background:#0e7490;color:#fff"><th style="padding:5px 10px;text-align:left">Name</th><th style="padding:5px 10px;text-align:left">Type</th><th style="padding:5px 10px;text-align:left">Default Value</th><th style="padding:5px 10px;text-align:left">Description</th></tr>
<tr style="border-bottom:1px solid #e5e7eb"><td style="padding:4px 10px;font-weight:bold">{NAME}</td><td style="padding:4px 10px;color:#6b7280">{TYPE}</td><td style="padding:4px 10px">{DEFAULT}</td><td style="padding:4px 10px;color:#6b7280">{DESCRIPTION}</td></tr>
<!-- repeat for each variable -->
</table>
```

Height = 28 + (variable_count * 28).

### Main Flow Tab — Logo Cell (top-right corner)

```xml
<mxCell id="main_logo" value="&lt;img src=&quot;{CISCO_WEBEX_LOGO}&quot; height=&quot;33&quot; style=&quot;display:block&quot;/&gt;" style="text;html=1;align=center;verticalAlign=middle;fillColor=none;strokeColor=none;" vertex="1" parent="1"><mxGeometry x="{LOGO_X}" y="20" width="160" height="33" as="geometry"/></mxCell>
```

Where `{LOGO_X}` is positioned to the right of the rightmost activity card.

## Cisco Webex Brand Logo

Base64-encoded SVG logo used in Summary and Main Flow tabs:

```
data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMzciIGhlaWdodD0iNDkiIHZpZXdCb3g9IjAgMCAyMzcgNDkiIGZpbGw9IndoaXRlIj48ZyBjbGlwLXBhdGg9InVybCgjY2xpcF9jaCkiPjxwYXRoIGQ9Ik02OC41NDk3IDI0LjY4OTVDNjguNTQ5NyAxOC42ODYgNzMuMDc1NCAxNC41NzcxIDc4LjkxMzYgMTQuNTc3MUM4My4yMDMzIDE0LjU3NzEgODUuNjc4OCAxNi45MjMyIDg3LjA1NzggMTkuMzU0OUw4My40OTU3IDIxLjExMTFDODMuMDYxMiAyMC4yNzE3IDgyLjQwNiAxOS41NjQzIDgxLjU5OTQgMTkuMDYzOEM4MC43OTI4IDE4LjU2MzIgNzkuODY0OCAxOC4yODgxIDc4LjkxMzYgMTguMjY3NkM3NS4zODE0IDE4LjI2NzYgNzIuODEyOSAyMC45OTI1IDcyLjgxMjkgMjQuNjg2MkM3Mi44MTI5IDI4LjM3OTkgNzUuMzgxNCAzMS4xMDE2IDc4LjkxMzYgMzEuMTAxNkM3OS44NjM5IDMxLjA5MTQgODAuNzkzIDMwLjgyMTIgODEuNTk4NCAzMC4zMjA3QzgyLjQwODMgMjkuODE3MSA4My4wNjQzIDI5LjEwMzkgODMuNDk1NyAyOC4yNThMODcuMDU3OCAyOS45OTc4Qzg1LjY1NTYgMzIuNDI5NSA4My4yMDMzIDM0LjgwMTkgNzguOTEzNiAzNC44MDE5QzczLjA3NTQgMzQuNzk4NiA2OC41NDk3IDMwLjY5NjMgNjguNTQ5NyAyNC42ODk1WiIvPjxwYXRoIGQ9Ik04OS4zMjQgMzQuNDM2VjE0Ljk1MjZIOTMuMDk4N1YzNC40MzZIODkuMzI0WiIvPjxwYXRoIGQ9Ik05Ni4xMjI0IDI3LjQ4MzZDOTYuMTIyNCAyMy41Mjk2IDk4Ljg5MDMgMjAuMTk1MSAxMDMuNDczIDIwLjE5NTFDMTA4LjA1NSAyMC4xOTUxIDExMC44NTIgMjMuNTM5NSAxMTAuODUyIDI3LjQ4MzZDMTEwLjg1MiAzMS40Mjc3IDEwOC4wODUgMzQuODAxOCAxMDMuNDczIDM0LjgwMThDOTguODYwNCAzNC44MDE4IDk2LjEyMjQgMzEuNDcwNiA5Ni4xMjI0IDI3LjQ4MzZaTTEwNy4wNDUgMjcuNDgzNkMxMDcuMDQ1IDI1LjMyNTQgMTA1Ljc0OSAyMy40NDcyIDEwMy40NzMgMjMuNDQ3MkMxMDEuMTk2IDIzLjQ0NzIgOTkuOTI3MSAyNS4zMTg4IDk5LjkyNzEgMjcuNDgzNkM5OS45MjcxIDI5LjY0ODQgMTAxLjE5NiAzMS41NDY0IDEwMy40NzMgMzEuNTQ2NEMxMDUuNzQ5IDMxLjU0NjQgMTA3LjA0NSAyOS42NzgxIDEwNy4wNDUgMjcuNDgzNloiLz48cGF0aCBkPSJNMTE3LjMzMiAzNC40MzYyTDExMS42MDcgMjAuNTc3NEgxMTUuNjE3TDExOS4zMzYgMzAuMjE1M0wxMjMuMDY0IDIwLjU3MDhIMTI3LjEwNEwxMjEuMzY2IDM0LjQzNjJIMTE3LjMzMloiLz48cGF0aCBkPSJNMTI3Ljg0OSAyNy40ODM2QzEyNy44NDkgMjMuNDQ3MiAxMzAuODM5IDIwLjE5NTEgMTM1LjEzOSAyMC4xOTUxQzEzOS4zMzkgMjAuMTk1MSAxNDIuMiAyMy4zMDIzIDE0Mi4yIDI3Ljg1OTJWMjguNjY2NUgxMzEuNzI2QzEzMS45NTkgMzAuNDIyOCAxMzMuMzg4IDMxLjg5MjMgMTM1Ljc4IDMxLjg5MjNDMTM2Ljk4IDMxLjg5MjMgMTM4LjY0MSAzMS4zNzE3IDEzOS41NDUgMzAuNTA4NEwxNDEuMTc3IDMyLjg3MDlDMTM5Ljc3OCAzNC4xMzk1IDEzNy41NjEgMzQuODAxOCAxMzUuMzcyIDM0LjgwMThDMTMxLjA5MiAzNC44MDg0IDEyNy44NDkgMzEuOTU0OSAxMjcuODQ5IDI3LjQ4MzZaTTEzNS4xMzkgMjMuMTA3OUMxMzIuODM2IDIzLjEwNzkgMTMxLjgzNiAyNC44MDQ4IDEzMS42NyAyNi4xODg3SDEzOC42MTFDMTM4LjUzMiAyNC44NzA3IDEzNy41OTggMjMuMTExMSAxMzUuMTQ2IDIzLjExMTFMMTM1LjEzOSAyMy4xMDc5WiIvPjxwYXRoIGQ9Ik0xNDQuODQyIDM0LjQzNjFWMjAuNTQxSDE0OC42VjIyLjQzOUMxNDkuMTU0IDIxLjc2NTggMTQ5Ljg0NyAyMS4yMTc1IDE1MC42MzIgMjAuODMwNUMxNTEuNDE3IDIwLjQ0MzYgMTUyLjI3NiAyMC4yMjcgMTUzLjE1MiAyMC4xOTUxVjIzLjc2MDNDMTUyLjgxMSAyMy42OTczIDE1Mi40NjUgMjMuNjY4NiAxNTIuMTE5IDIzLjY3NDZDMTUwLjg3NiAyMy42NzQ2IDE0OS4yMjEgMjQuMzY2NSAxNDguNiAyNS4yNTYyVjM0LjQzNjFIMTQ0Ljg0MloiLz48cGF0aCBkPSJNMTY0LjkzMSAzNC40MzZWMjUuODQyNkMxNjQuOTMxIDIzLjg4ODcgMTYzLjkxMSAyMy4yNzI1IDE2Mi4zMSAyMy4yNzI1QzE2MS42ODMgMjMuMjg3OCAxNjEuMDY3IDIzLjQ0NjEgMTYwLjUxMiAyMy43MzUyQzE1OS45NTYgMjQuMDI0NCAxNTkuNDc1IDI0LjQzNjYgMTU5LjEwNyAyNC45Mzk4VjM0LjQzNkgxNTUuNDE4VjE0Ljk1MjZIMTU5LjExN1YyMi4xNjIxQzE1OS43MzMgMjEuNDYzOCAxNjAuNDk1IDIwLjkwNjMgMTYxLjM1IDIwLjUyOEMxNjIuMjA0IDIwLjE0OTcgMTYzLjEzMiAxOS45NTk3IDE2NC4wNjggMTkuOTcwOUMxNjcuMTUxIDE5Ljk3MDkgMTY4LjYzNiAyMS42NjQ2IDE2OC42MzYgMjQuNDA5M1YzNC40MzZIMTY0LjkzMVoiLz48cGF0aCBkPSJNMTcxLjY2IDI3LjQ4MzZDMTcxLjY2IDIzLjUyOTYgMTc0LjQyNSAyMC4xOTUxIDE3OS4wMSAyMC4xOTUxQzE4My41OTYgMjAuMTk1MSAxODYuMzkgMjMuNTM5NSAxODYuMzkgMjcuNDgzNkMxODYuMzkgMzEuNDI3NyAxODMuNjIyIDM0LjgwMTggMTc5LjAxIDM0LjgwMThDMTc0LjM5OCAzNC44MDE4IDE3MS42NiAzMS40NzA2IDE3MS42NiAyNy40ODM2Wk0xODIuNTgyIDI3LjQ4MzZDMTgyLjU4MiAyNS4zMjU0IDE4MS4yODYgMjMuNDQ3MiAxNzkuMDEgMjMuNDQ3MkMxNzYuNzM0IDIzLjQ0NzIgMTc1LjQ2NSAyNS4zMTg4IDE3NS40NjUgMjcuNDgzNkMxNzUuNDY1IDI5LjY0ODQgMTc2LjczNCAzMS41NDY0IDE3OS4wMSAzMS41NDY0QzE4MS4yODYgMzEuNTQ2NCAxODIuNTgyIDI5LjY3ODEgMTgyLjU4MiAyNy40ODM2WiIvPjxwYXRoIGQ9Ik0xOTkuMjk5IDM0LjQ1NTlWMzIuNzAzQzE5OC42NjggMzMuMzc4OCAxOTcuOTAxIDMzLjkxNTEgMTk3LjA0NiAzNC4yNzY4QzE5Ni4xOTIgMzQuNjM4NCAxOTUuMjcgMzQuODE3NCAxOTQuMzQyIDM0LjgwMTlDMTkxLjI0OCAzNC44MDE5IDE4OS43ODkgMzMuMTM0NyAxODkuNzg5IDMwLjQzMjdWMjAuNTcwOEgxOTMuNTA4VjI4Ljk5NjFDMTkzLjUwOCAzMC45MjA0IDE5NC41MjggMzEuNTUzIDE5Ni4xMDYgMzEuNTUzQzE5Ni43MjYgMzEuNTQyNiAxOTcuMzM1IDMxLjM5NTEgMTk3Ljg5IDMxLjEyMTRDMTk4LjQ0NiAzMC44NDk5IDE5OC45MzMgMzAuNDU2NyAxOTkuMzEzIDI5Ljk3MTRWMjAuNTcwOEgyMDMuMDIxVjM0LjQ1NTlIMTk5LjI5OVoiLz48cGF0aCBkPSJNMjE2LjE4OSAzNC40MzYxVjI2LjAzMzhDMjE2LjE4OSAyNC4xMDk1IDIxNS4xMzkgMjMuNDQ3MiAyMTMuNTMxIDIzLjQ0NzJDMjEyLjg4NyAyMy40NTMzIDIxMi4yNTMgMjMuNjA1NSAyMTEuNjc3IDIzLjg5MjFDMjExLjEwNyAyNC4xNzMyIDIxMC42MTIgMjQuNTgyOCAyMTAuMjMxIDI1LjA4ODFWMzQuNDM2MUgyMDYuNDA3VjIwLjU0NDNIMjEwLjIxOFYyMi4zNTMzQzIxMC44NjIgMjEuNjU4NSAyMTEuNjQ3IDIxLjEwNyAyMTIuNTIyIDIwLjczNUMyMTMuMzk2IDIwLjM2MjkgMjE0LjM0MSAyMC4xNzg5IDIxNS4yOTIgMjAuMTk1MUMyMTguNDcyIDIwLjE5NTEgMjIwLjAwNCAyMS45MjE2IDIyMC4wMDQgMjQuNjIzNlYzNC40MzYxSDIxNi4xODlaIi8+PHBhdGggZD0iTTIzMy4yNTggMzQuNDUyNVYzMi42MzY5QzIzMi43NSAzMy4zMDcxIDIzMi4wOTMgMzMuODUxMyAyMzEuMzM3IDM0LjIyN0MyMzAuNTgxIDM0LjYwMjYgMjI5Ljc0OCAzNC43OTkzIDIyOC45MDIgMzQuODAxN0MyMjUuMzM3IDM0LjgwMTcgMjIyLjY0NSAzMi4xMTMgMjIyLjY0NSAyNy40MDc3QzIyMi42NDUgMjIuNzk0NyAyMjUuMzA0IDE5Ljk4MDggMjI4LjkwMiAxOS45ODA4QzIyOS43NDcgMTkuOTc3NyAyMzAuNTggMjAuMTcxOCAyMzEuMzM1IDIwLjU0NzZDMjMyLjA5MiAyMC45MjM4IDIzMi43NTEgMjEuNDY5OCAyMzMuMjU4IDIyLjE0MjNWMTQuOTUyNkgyMzdWMzQuNDUyNUgyMzMuMjU4Wk0yMzMuMjU4IDI5Ljg4ODlWMjQuODgwNUMyMzIuNjQ0IDIzLjk0MTQgMjMxLjI5OCAyMy4yNjkyIDIzMC4wNDIgMjMuMjY5MkMyMjcuOTM5IDIzLjI2OTIgMjI2LjQ3NyAyNC45MzY1IDIyNi40NzcgMjcuMzk0NkMyMjYuNDc3IDI5Ljg1MjYgMjI3LjkzOSAzMS40OTAzIDIzMC4wNDIgMzEuNDkwM0MyMzEuMjk4IDMxLjQ5MDMgMjMyLjY0NCAzMC44MTE1IDIzMy4yNTggMjkuODc5VjI5Ljg4ODlaIi8+PHBhdGggZD0iTTI0LjY0NTIgMEMxOS43NTU4IDAuMDExNyAxNC45Nzk5IDEuNDYxNyAxMC45MjE5IDQuMTY2NEM2Ljg2NCA2Ljg3MTEgMy43MDY1IDEwLjcwODggMS44NDkxIDE1LjE5MzhDLTAuMDA4MyAxOS42Nzg5LTAuNDgyIDI0LjYwOTUgMC40ODc4IDI5LjM2MTZDMS40NTc3IDM0LjExMzggMy44Mjc1IDM4LjQ3MzcgNy4yOTc0IDQxLjg4OTZDMTAuNzY3MyA0NS4zMDU1IDE1LjE4MTIgNDcuNjIzOCAxOS45ODA0IDQ4LjU1MUMyNC43Nzk1IDQ5LjQ3ODEgMjkuNzQ4MiA0OC45NzI1IDM0LjI1NzUgNDcuMDk4MUMzOC43NjY3IDQ1LjIyMzcgNDIuNjEzOCA0Mi4wNjQ4IDQ1LjMxMTcgMzguMDIxM0M0OC4wMDk3IDMzLjk3NzggNDkuNDM3MiAyOS4yMzE0IDQ5LjQxMzUgMjQuMzgyOUM0OS40MTM2IDIxLjE2NTkgNDguNzcxNyAxNy45ODA2IDQ3LjUyNDggMTUuMDEwN0M0Ni4yNzc5IDEyLjA0MDcgNDQuNDUwNiA5LjM0NDggNDIuMTQ4MyA3LjA3ODNDMzkuODQ1OSA0LjgxMTggMzcuMTE0MSAzLjAxOTUgMzQuMTEwMSAxLjgwNDZDMzEuMTA2MSAwLjU4OTggMjcuODg5My0wLjAyMzYgMjQuNjQ1MiAwWk0yNC4zNzYxIDQ1LjM5NTJDMTkuMzY5OSA0NS4zMTEyIDE0LjU1NzQgNDMuNDYyNyAxMC44MDA0IDQwLjE4MDdDNy4wNDM0IDM2Ljg5ODcgNC41ODc0IDMyLjM5NzcgMy44NzIxIDI3LjQ4MzZDMy4xNTY5IDIyLjU2OTUgNC4yMjkyIDE3LjU2MzUgNi44OTY5IDEzLjM2MkM5LjU2NDcgOS4xNjA1IDEzLjY1MzYgNi4wMzc5IDE4LjQzMTUgNC41NTM2QzI4LjMwMDMgMS41MDkgMzcuODA2OSA2LjExODcgNDEuOTQ3MSAxMi42MDk5QzQxLjg4NCAxMi42MDk5IDQxLjc4NzYgMTIuNjcyNSA0MS43NjQ0IDEyLjY0OTRDMzkuODg3IDEwLjY3MjQgMzcuNDQ0NyAxMC4xOTggMzQuODI2MyAxMC43NjhDMzEuOTYyMSAxMS4zOTczIDI5LjMyNzEgMTIuNTExIDI3LjEzNCAxNC40NjgzQzI0Ljg4NzggMTYuNDY1IDIyLjA5NjYgMTcuODM5MSAxOS4yOTIyIDE4Ljg3MzdDMTcuNjEwOCAxOS40OTMyIDE1Ljg4OTYgMjAuMDAwNiAxNC4xNTg0IDIwLjQ3MThDMTMuMjE4IDIwLjcyNTUgMTIuMjc0NCAyMC45NzkyIDExLjM1NzMgMjEuMjk1NUMxMC4xMDc5IDIxLjcyNzIgOS45Mjg1IDIyLjYzMzMgMTAuNjkyNyAyMy42OTFDMTEuMDkyNSAyNC4zMTc2IDExLjM4NDQgMjUuMDA1OCAxMS41NTY2IDI1LjcyNzNDMTIuMjY0NCAyOC4xNjIzIDEzLjUxMDQgMzAuMDc2NyAxNi4xMzg4IDMwLjgwNDlDMTYuMjc1MiAzMC44NDY2IDE2LjQgMzAuOTE5MyAxNi41MDMyIDMxLjAxNzFDMTYuNjA2NCAzMS4xMTQ5IDE2LjY4NTMgMzEuMjM1MSAxNi43MzM2IDMxLjM2ODRDMTYuOTcyOCAzMi44MjggMTguMDk1OSAzMy4zNzgzIDE5LjI4ODggMzMuNTM2NUMyMy44ODEgMzQuMTQ5MyAyOC4xODQgMzMuNDgwNCAzMS43OTkyIDMwLjI5MDlDMzEuODQ5MSAzMC4yNDggMzEuOTM1NSAzMC4yNDggMzIuMDk4MyAzMC4yMDE5QzMxLjkxODkgMzIuMTc4OSAzMS42NzYzIDM0LjEwMzIgMzEuNjAzMiAzNi4wMjc1QzMxLjU2MzUgMzcuMjE3NyAzMS42NjI4IDM4LjQwODYgMzEuODk4OSAzOS41NzYyQzMyLjE0MTUgNDAuODE1MSAzMi43NzYxIDQwLjk5OTYgMzMuNzAzMiA0MC4xNDk1QzM0LjgzMyAzOS4xMTE2IDM1Ljg1NjQgMzcuOTY0OSAzNi45NTYzIDM2Ljg5MDhDMzguNjY3NSAzNS4yMTM2IDQwLjM2MjEgMzMuNTIzMyA0Mi4xNDMyIDMxLjk0ODNDNDIuNzQ3OSAzMS40MDc5IDQzLjU4MiAzMC45NTk4IDQ0LjQ2OTEgMzEuNTg5MUM0Mi44Mzc2IDM3LjQyNzkgMzUuNDc3NiA0NS42MzkgMjQuMzc2MSA0NS4zOTUyWiIvPjwvZz48ZGVmcz48Y2xpcFBhdGggaWQ9ImNsaXBfY2giPjxyZWN0IHdpZHRoPSIyMzciIGhlaWdodD0iNDkiLz48L2NsaXBQYXRoPjwvZGVmcz48L3N2Zz4=
```

## Event Handler Default Set

When the spec doesn't specify event handlers, generate cards for these 10 standard events:

| Display Name | Event Type | Event Name |
|---|---|---|
| GlobalErrorHandling | Global Errors | OnGlobalError |
| AgentOfferContact | Agent Offer | AgentOffered |
| ContactPredial | Contact Predial | PreDial |
| ContactOutboundCampaignResult | Campaign Result | OutboundCampaignCallResult |
| ContactAniUpdated | ANI Updated | ContactAniUpdated |
| ContactCallbackFailed | Callback Failed | CallbackFailed |
| ContactEnded | Contact Ended | ContactEnded |
| AgentContactAssigned | Agent Assigned | AgentContactAssigned |
| ContactReservationStarted | Reservation Started | ReservationStarted |
| FCAsk(ContactLastAgentRemoved) | Last Agent Removed | LastAgentRemoved |

All use the Event category colors and ICON_EVENT icon. Each has a single "Out" port.
