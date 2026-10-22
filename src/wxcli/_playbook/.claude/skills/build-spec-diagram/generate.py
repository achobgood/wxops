#!/usr/bin/env python3
"""Generate .drawio flow diagrams from a JSON flow model.

Usage: python3 generate.py <model.json> <output.drawio>
"""

import sys
import json
from collections import defaultdict, deque
from pathlib import Path

# ─── Category Constants ───────────────────────────────────────────────
CATEGORIES = {
    "Start": {"badge": "#74E8D1", "fill": "#f0fefb", "radius": "border-radius:3px"},
    "Event": {"badge": "#74E8D1", "fill": "#f0fefb", "radius": "border-radius:3px"},
    "Action": {"badge": "#E2CAFC", "fill": "#faf5fe", "radius": "border-radius:3px"},
    "Function": {"badge": "#FEBA7F", "fill": "#fff3e8", "radius": "border-radius:3px"},
    "Gateway": {"badge": "#FFCE73", "fill": "#fff6e6", "radius": "border-radius:3px"},
    "Terminating": {"badge": "#FFC7D2", "fill": "#fff5f7", "radius": "border-radius:50%"},
}

ACTIVITY_CATEGORY = {
    "NewPhoneContact": "Start", "Start Flow": "Start",
    "Play Message": "Action", "Play Music": "Action",
    "Set Variable": "Action", "HTTP Request": "Action",
    "Queue Contact": "Action", "Collect Digits": "Action",
    "Record": "Action", "Screen Pop": "Action",
    "Virtual Agent V2": "Action", "BRE Request": "Action",
    "Callback": "Action", "Schedule Callback": "Action",
    "Get Queue Info": "Action", "Advanced Queue Information": "Action",
    "Parse": "Action", "Send Digits": "Action",
    "Set Announcement": "Action", "Set Whisper": "Action",
    "Upload Audio": "Action", "Set Caller ID": "Action",
    "Set Contact Priority": "Action", "Recording Control": "Action",
    "Start Media Stream": "Action", "Wait": "Action",
    "Feedback": "Action", "Feedback V2": "Action",
    "Escalate CDG": "Action", "Queue To Agent": "Action",
    "Custom Connectors": "Action", "HTTP Connector": "Action",
    "Functions": "Function",
    "Condition": "Gateway", "Menu": "Gateway", "Case": "Gateway",
    "Business Hours": "Gateway", "Percentage Allocation": "Gateway",
    "Disconnect Contact": "Terminating", "Blind Transfer": "Terminating",
    "Bridged Transfer": "Terminating", "End Flow": "Terminating",
    "GoTo": "Terminating", "Outdial Entry Point": "Terminating",
}

ACTIVITY_PORTS = {
    "NewPhoneContact": ["Out"], "Start Flow": ["Out"],
    "Play Message": ["Default", "Error"], "Play Music": ["Default", "Error"],
    "Set Variable": ["Out", "Error"],
    "Queue Contact": [], "Disconnect Contact": [],
    "Condition": ["True", "False", "Error"],
    "HTTP Request": ["Default", "Error"],
    "Parse": ["Default", "Error"],
    "Collect Digits": ["Default", "Error"],
    "Send Digits": ["Default", "Error"],
    "Record": ["Default", "Error"],
    "Functions": ["Default", "Error"],
    "Blind Transfer": ["Failure"],
    "Bridged Transfer": ["Transferred", "Failed", "Error"],
    "GoTo": [], "End Flow": [], "Outdial Entry Point": [],
    "Callback": ["Default", "Error"],
    "Schedule Callback": ["Default", "Error"],
    "Get Queue Info": ["Default", "Error"],
    "Advanced Queue Information": ["Default", "Error"],
    "BRE Request": ["Default", "Error"],
    "Screen Pop": ["Default", "Error"],
    "Set Announcement": ["Default", "Error"],
    "Set Whisper": ["Default", "Error"],
    "Set Caller ID": ["Default", "Error"],
    "Set Contact Priority": ["Default", "Error"],
    "Recording Control": ["Default", "Error"],
    "Start Media Stream": ["Default", "Error"],
    "Upload Audio": ["Default", "Error"],
    "Wait": ["Default", "Error"],
    "Virtual Agent V2": ["Handled", "Escalated", "Error"],
    "Feedback V2": ["Default", "Error"],
    "Feedback": ["Default", "Error"],
    "Escalate CDG": ["Default", "Error"],
    "Queue To Agent": ["Default", "Error"],
    "Custom Connectors": ["Default", "Error"],
    "HTTP Connector": ["Default", "Error"],
    "Business Hours": ["Working Hours", "Holiday", "Default", "Error"],
    "Call Progress Analysis": ["CPA Successful", "Error"],
    "Virtual Agent (Legacy)": ["Handled", "Escalated", "Error"],
    # BYOC + utility activities (ports verified live 2026-07-12; "Default" here is the
    # implicit `out` success port, which the registry omits). Must match build-spec-diagram/reference.md.
    "Cryptographic Hash": ["Default", "Error"],
    "Generate OTP": ["Default", "Error"],
    "Verify OTP": ["Failure", "Resend", "Error"],
    "Receive Message": ["Timeout", "Error"],
    "Send Custom Message": ["Error"],
    "Menu": [],  # dynamic
    "Case": [],  # dynamic
    "Percentage Allocation": [],  # dynamic
}

ICON_START = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M16%2027C9.925%2027%205%2022.075%205%2016S9.925%205%2016%205s11%204.925%2011%2011-4.925%2011-11%2011m0%202c7.18%200%2013-5.82%2013-13S23.18%203%2016%203%203%208.82%203%2016s5.82%2013%2013%2013M19.5%2016l-5.25%203.031V12.97zm2.5.866a1%201%200%200%200%200-1.732l-8.25-4.763a1%201%200%200%200-1.5.866v9.526a1%201%200%200%200%201.5.866z%22/%3E%3C/svg%3E"
ICON_EVENT = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M30%2015.008a5.014%205.014%200%200%200-4.187-4.913%209.998%209.998%200%200%200-19.628-.012%204.996%204.996%200%200%200%20.818%209.925%201%201%200%200%200%201-1.003L8%2012a8%208%200%200%201%2016%200v6a8.01%208.01%200%200%201-5.388%207.553%202.986%202.986%200%201%200%20.332%202.003%2010.03%2010.03%200%200%200%206.865-7.643A5.01%205.01%200%200%200%2030%2015.008M6%2017.837a2.992%202.992%200%200%201%200-5.645zM16%2028a1%201%200%201%201%200-2%201%201%200%200%201%200%202m10-10.195v-5.602a2.96%202.96%200%200%201%200%205.602%22/%3E%3C/svg%3E"
ICON_SET_VAR = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M9.408%2024.337a9.133%209.133%200%200%201-.013-16.674%201%201%200%201%200-.818-1.824%2011.132%2011.132%200%200%200%20.015%2020.324%201%201%200%201%200%20.815-1.826M23.423%205.834a1%201%200%201%200-.818%201.824%209.138%209.138%200%200%201-.013%2016.684%201%201%200%200%200%20.816%201.826%2011.138%2011.138%200%200%200%20.015-20.334M20.707%2011.293a1%201%200%200%200-1.414%200l-2.77%202.77c-1.172-2.224-4.124-2.995-4.28-3.033a1%201%200%200%200-.488%201.94c.031.007%202.868.755%203.21%202.65l-3.672%203.673a1%201%200%201%200%201.414%201.414l2.77-2.77c1.172%202.223%204.125%202.994%204.28%203.032a1%201%200%200%200%20.488-1.939c-.03-.007-2.868-.756-3.21-2.651l3.672-3.672a1%201%200%200%200%200-1.414%22/%3E%3C/svg%3E"
ICON_HTTP = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M18.317%209.051a.996.996%200%200%200-1.265.633l-4%2012a1%201%200%200%200%20.632%201.264%201%201%200%200%200%201.264-.631l4-12a1%201%200%200%200-.631-1.266M10.707%209.293a1%201%200%200%200-1.414%200l-6%206a1%201%200%200%200%200%201.414l6%206a1%201%200%200%200%201.414-1.414L5.414%2016l5.293-5.293a1%201%200%200%200%200-1.414M28.707%2015.293l-6-6a1%201%200%201%200-1.414%201.414L26.586%2016l-5.293%205.293a1%201%200%201%200%201.414%201.414l6-6a1%201%200%200%200%200-1.414%22/%3E%3C/svg%3E"
ICON_PLAY = ICON_START  # same play-circle icon
ICON_FUNC = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M29%2026H3a1%201%200%200%200%200%202h26a1%201%200%200%200%200-2M3%206h26a1%201%200%201%200%200-2H3a1%201%200%200%200%200%202M17.052%209.684l-4%2012a.997.997%200%200%200%20.63%201.267%201%201%200%200%200%201.266-.635l4-12a.997.997%200%200%200-.63-1.267%201%201%200%200%200-1.266.635M10.707%209.293a1%201%200%200%200-1.414%200l-6%206a1%201%200%200%200%200%201.414l6%206a1%201%200%200%200%201.414-1.414L5.414%2016l5.293-5.293a1%201%200%200%200%200-1.414M21.293%2022.707a1%201%200%200%200%201.414%200l6-6a1%201%200%200%200%200-1.414l-6-6a1%201%200%200%200-1.414%201.414L26.586%2016l-5.293%205.293a1%201%200%200%200%200%201.414%22/%3E%3C/svg%3E"
ICON_COND = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M16%204a2%202%200%201%200%200%204%202%202%200%200%200%200-4m-4%202a4%204%200%201%201%208%200%204%204%200%200%201-8%200m4%205a1%201%200%200%201%201%201v3h12a1%201%200%201%201%200%202h-2v3a1%201%200%201%201-2%200v-3H7v3a1%201%200%201%201-2%200v-3H3a1%201%200%201%201%200-2h12v-3a1%201%200%200%201%201-1M9.707%2023.707a1%201%200%200%200-1.414-1.414L6%2024.586l-2.293-2.293a1%201%200%200%200-1.414%201.414L4.586%2026l-2.293%202.293a1%201%200%201%200%201.414%201.414L6%2027.414l2.293%202.293a1%201%200%200%200%201.414-1.414L7.414%2026zm19.944.052a1%201%200%200%200-1.302-1.518l-6.297%205.397-2.345-2.345a1%201%200%200%200-1.414%201.414l3%203a1%201%200%200%200%201.358.052z%22/%3E%3C/svg%3E"
ICON_MENU = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M12%2011h16a1%201%200%201%200%200-2H12a1%201%200%201%200%200%202M28%2021H12a1%201%200%201%200%200%202h16a1%201%200%201%200%200-2M7.44%2021.825q.45-.64.45-1.4%200-.84-.59-1.39-.65-.61-1.75-.61-.94%200-1.62.49a2.14%202.14%200%200%200-.93%201.53h1.26q.07-.47.38-.76.34-.31.88-.31.49%200%20.8.25.34.29.34.8%200%20.46-.275.87-.276.41-1.165%201.26l-2.04%201.98v1.04h4.67v-1.04H4.78l1.35-1.29q.97-.93%201.31-1.42M5.59%2013.645h1.19v-7H5.6l-1.6.83v1.16l1.59-.81z%22/%3E%3C/svg%3E"
ICON_TRANSFER = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M9.8%2012.533a1%201%200%200%200%201.932-.517l-.646-2.412%206.19%203.537a1%201%200%200%200%201.365-.373l4.728-8.272a1%201%200%200%200-1.737-.992l-4.231%207.404-5.295-3.025%202.377-.636a1%201%200%201%200-.518-1.932L9.242%206.58a1%201%200%200%200-.707%201.225zM16%2017c-9.893%200-14%204.758-14%207.305v1.467A3.23%203.23%200%200%200%205.23%2029h3.57A3.214%203.214%200%200%200%2012%2025.781v-1.636A7%207%200%200%201%2016%2023a7%207%200%200%201%204%201.14v1.65A3.316%203.316%200%200%200%2023.332%2029h3.44A3.23%203.23%200%200%200%2030%2025.771v-1.466C30%2021.758%2025.894%2017%2016%2017m12%208.772A1.23%201.23%200%200%201%2026.772%2027h-3.44A1.31%201.31%200%200%201%2022%2025.79v-1.953C22%2022.308%2018.703%2021%2016%2021c-2.971%200-6%201.435-6%202.843v1.938A1.21%201.21%200%200%201%208.799%2027H5.23A1.23%201.23%200%200%201%204%2025.771v-1.466C4%2022.795%207.57%2019%2016%2019s12%203.795%2012%205.305z%22/%3E%3C/svg%3E"
ICON_DISCONNECT = "data:image/svg+xml,%3Csvg%20fill%3D%22black%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2232%22%20height%3D%2232%22%20viewBox%3D%220%200%2032%2032%22%3E%3Cpath%20d%3D%22M24.002%202a6%206%200%201%200%206%206%206.006%206.006%200%200%200-6-6m0%202a3.995%203.995%200%200%201%203.858%203h-7.716a3.996%203.996%200%200%201%203.858-3m0%208a3.996%203.996%200%200%201-3.858-3h7.716a3.996%203.996%200%200%201-3.858%203M9.107%2022.843c6.996%206.996%2013.264%206.535%2015.065%204.734l1.037-1.037a3.23%203.23%200%200%200%200-4.566l-2.524-2.524a3.214%203.214%200%200%200-4.54.012l-1.157%201.157A7%207%200%200%201%2013.35%2018.6a7%207%200%200%201-2.023-3.634l1.168-1.166a3.317%203.317%200%200%200-.086-4.626L9.976%206.74a3.23%203.23%200%200%200-4.566%200L4.373%207.778c-1.8%201.8-2.261%208.069%204.734%2015.065M6.824%208.155a1.23%201.23%200%200%201%201.738%200l2.433%202.433a1.31%201.31%200%200%201%20.087%201.797l-1.383%201.38c-1.08%201.081.327%204.34%202.237%206.25%202.101%202.1%205.257%203.227%206.253%202.232l1.37-1.371a1.21%201.21%200%200%201%201.712-.012l2.524%202.524a1.23%201.23%200%200%201%200%201.738l-1.037%201.037c-1.068%201.067-6.275%201.227-12.236-4.735C4.56%2015.468%204.72%2010.26%205.786%209.192z%22/%3E%3C/svg%3E"

ICON_FOR_TYPE = {
    "NewPhoneContact": ICON_START, "Start Flow": ICON_START,
    "Set Variable": ICON_SET_VAR,
    "HTTP Request": ICON_HTTP, "Custom Connectors": ICON_HTTP,
    "HTTP Connector": ICON_HTTP, "Parse": ICON_HTTP,
    "Play Message": ICON_PLAY, "Play Music": ICON_PLAY,
    "Functions": ICON_FUNC,
    "Condition": ICON_COND, "Business Hours": ICON_COND,
    "Percentage Allocation": ICON_COND,
    "Menu": ICON_MENU, "Case": ICON_MENU,
    "Blind Transfer": ICON_TRANSFER, "Bridged Transfer": ICON_TRANSFER,
    "Queue To Agent": ICON_TRANSFER,
    "Disconnect Contact": ICON_DISCONNECT, "End Flow": ICON_DISCONNECT,
    "GoTo": ICON_DISCONNECT, "Virtual Agent V2": ICON_EVENT,
    "Collect Digits": ICON_PLAY,
}
ICON_CAT_DEFAULT = {
    "Start": ICON_START, "Event": ICON_EVENT, "Action": ICON_PLAY,
    "Function": ICON_FUNC, "Gateway": ICON_COND, "Terminating": ICON_DISCONNECT,
}

CISCO_LOGO = (
    "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAw"
    "MC9zdmciIHdpZHRoPSIyMzciIGhlaWdodD0iNDkiIHZpZXdCb3g9IjAgMCAyMzcgNDki"
    "IGZpbGw9IndoaXRlIj48ZyBjbGlwLXBhdGg9InVybCgjY2xpcF9jaCkiPjxwYXRoIGQ9"
    "Ik02OC41NDk3IDI0LjY4OTVDNjguNTQ5NyAxOC42ODYgNzMuMDc1NCAxNC41NzcxIDc4"
    "LjkxMzYgMTQuNTc3MUM4My4yMDMzIDE0LjU3NzEgODUuNjc4OCAxNi45MjMyIDg3LjA1"
    "NzggMTkuMzU0OUw4My40OTU3IDIxLjExMTFDODMuMDYxMiAyMC4yNzE3IDgyLjQwNiAx"
    "OS41NjQzIDgxLjU5OTQgMTkuMDYzOEM4MC43OTI4IDE4LjU2MzIgNzkuODY0OCAxOC4y"
    "ODgxIDc4LjkxMzYgMTguMjY3NkM3NS4zODE0IDE4LjI2NzYgNzIuODEyOSAyMC45OTI1"
    "IDcyLjgxMjkgMjQuNjg2MkM3Mi44MTI5IDI4LjM3OTkgNzUuMzgxNCAzMS4xMDE2IDc4"
    "LjkxMzYgMzEuMTAxNkM3OS44NjM5IDMxLjA5MTQgODAuNzkzIDMwLjgyMTIgODEuNTk4"
    "NCAzMC4zMjA3QzgyLjQwODMgMjkuODE3MSA4My4wNjQzIDI5LjEwMzkgODMuNDk1NyAy"
    "OC4yNThMODcuMDU3OCAyOS45OTc4Qzg1LjY1NTYgMzIuNDI5NSA4My4yMDMzIDM0Ljgw"
    "MTkgNzguOTEzNiAzNC44MDE5QzczLjA3NTQgMzQuNzk4NiA2OC41NDk3IDMwLjY5NjMg"
    "NjguNTQ5NyAyNC42ODk1WiIvPjxwYXRoIGQ9Ik04OS4zMjQgMzQuNDM2VjE0Ljk1MjZI"
    "OTMuMDk4N1YzNC40MzZIODkuMzI0WiIvPjxwYXRoIGQ9Ik05Ni4xMjI0IDI3LjQ4MzZD"
    "OTYuMTIyNCAyMy41Mjk2IDk4Ljg5MDMgMjAuMTk1MSAxMDMuNDczIDIwLjE5NTFDMTA4"
    "LjA1NSAyMC4xOTUxIDExMC44NTIgMjMuNTM5NSAxMTAuODUyIDI3LjQ4MzZDMTEwLjg1"
    "MiAzMS40Mjc3IDEwOC4wODUgMzQuODAxOCAxMDMuNDczIDM0LjgwMThDOTguODYwNCAz"
    "NC44MDE4IDk2LjEyMjQgMzEuNDcwNiA5Ni4xMjI0IDI3LjQ4MzZaTTEwNy4wNDUgMjcu"
    "NDgzNkMxMDcuMDQ1IDI1LjMyNTQgMTA1Ljc0OSAyMy40NDcyIDEwMy40NzMgMjMuNDQ3"
    "MkMxMDEuMTk2IDIzLjQ0NzIgOTkuOTI3MSAyNS4zMTg4IDk5LjkyNzEgMjcuNDgzNkM5"
    "OS45MjcxIDI5LjY0ODQgMTAxLjE5NiAzMS41NDY0IDEwMy40NzMgMzEuNTQ2NEMxMDUu"
    "NzQ5IDMxLjU0NjQgMTA3LjA0NSAyOS42NzgxIDEwNy4wNDUgMjcuNDgzNloiLz48cGF0"
    "aCBkPSJNMTE3LjMzMiAzNC40MzYyTDExMS42MDcgMjAuNTc3NEgxMTUuNjE3TDExOS4z"
    "MzYgMzAuMjE1M0wxMjMuMDY0IDIwLjU3MDhIMTI3LjEwNEwxMjEuMzY2IDM0LjQzNjJI"
    "MTE3LjMzMloiLz48cGF0aCBkPSJNMTI3Ljg0OSAyNy40ODM2QzEyNy44NDkgMjMuNDQ3"
    "MiAxMzAuODM5IDIwLjE5NTEgMTM1LjEzOSAyMC4xOTUxQzEzOS4zMzkgMjAuMTk1MSAx"
    "NDIuMiAyMy4zMDIzIDE0Mi4yIDI3Ljg1OTJWMjguNjY2NUgxMzEuNzI2QzEzMS45NTkg"
    "MzAuNDIyOCAxMzMuMzg4IDMxLjg5MjMgMTM1Ljc4IDMxLjg5MjNDMTM2Ljk4IDMxLjg5"
    "MjMgMTM4LjY0MSAzMS4zNzE3IDEzOS41NDUgMzAuNTA4NEwxNDEuMTc3IDMyLjg3MDlD"
    "MTM5Ljc3OCAzNC4xMzk1IDEzNy41NjEgMzQuODAxOCAxMzUuMzcyIDM0LjgwMThDMTMx"
    "LjA5MiAzNC44MDg0IDEyNy44NDkgMzEuOTU0OSAxMjcuODQ5IDI3LjQ4MzZaTTEzNS4x"
    "MzkgMjMuMTA3OUMxMzIuODM2IDIzLjEwNzkgMTMxLjgzNiAyNC44MDQ4IDEzMS42NyAy"
    "Ni4xODg3SDEzOC42MTFDMTM4LjUzMiAyNC44NzA3IDEzNy41OTggMjMuMTExMSAxMzUu"
    "MTQ2IDIzLjExMTFMMTM1LjEzOSAyMy4xMDc5WiIvPjxwYXRoIGQ9Ik0xNDQuODQyIDM0"
    "LjQzNjFWMjAuNTQxSDE0OC42VjIyLjQzOUMxNDkuMTU0IDIxLjc2NTggMTQ5Ljg0NyAy"
    "MS4yMTc1IDE1MC42MzIgMjAuODMwNUMxNTEuNDE3IDIwLjQ0MzYgMTUyLjI3NiAyMC4y"
    "MjcgMTUzLjE1MiAyMC4xOTUxVjIzLjc2MDNDMTUyLjgxMSAyMy42OTczIDE1Mi40NjUg"
    "MjMuNjY4NiAxNTIuMTE5IDIzLjY3NDZDMTUwLjg3NiAyMy42NzQ2IDE0OS4yMjEgMjQu"
    "MzY2NSAxNDguNiAyNS4yNTYyVjM0LjQzNjFIMTQ0Ljg0MloiLz48cGF0aCBkPSJNMTY0"
    "LjkzMSAzNC40MzZWMjUuODQyNkMxNjQuOTMxIDIzLjg4ODcgMTYzLjkxMSAyMy4yNzI1"
    "IDE2Mi4zMSAyMy4yNzI1QzE2MS42ODMgMjMuMjg3OCAxNjEuMDY3IDIzLjQ0NjEgMTYw"
    "LjUxMiAyMy43MzUyQzE1OS45NTYgMjQuMDI0NCAxNTkuNDc1IDI0LjQzNjYgMTU5LjEw"
    "NyAyNC45Mzk4VjM0LjQzNkgxNTUuNDE4VjE0Ljk1MjZIMTU5LjExN1YyMi4xNjIxQzE1"
    "OS43MzMgMjEuNDYzOCAxNjAuNDk1IDIwLjkwNjMgMTYxLjM1IDIwLjUyOEMxNjIuMjA0"
    "IDIwLjE0OTcgMTYzLjEzMiAxOS45NTk3IDE2NC4wNjggMTkuOTcwOUMxNjcuMTUxIDE5"
    "Ljk3MDkgMTY4LjYzNiAyMS42NjQ2IDE2OC42MzYgMjQuNDA5M1YzNC40MzZIMTY0Ljkz"
    "MVoiLz48cGF0aCBkPSJNMTcxLjY2IDI3LjQ4MzZDMTcxLjY2IDIzLjUyOTYgMTc0LjQy"
    "NSAyMC4xOTUxIDE3OS4wMSAyMC4xOTUxQzE4My41OTYgMjAuMTk1MSAxODYuMzkgMjMu"
    "NTM5NSAxODYuMzkgMjcuNDgzNkMxODYuMzkgMzEuNDI3NyAxODMuNjIyIDM0LjgwMTgg"
    "MTc5LjAxIDM0LjgwMThDMTc0LjM5OCAzNC44MDE4IDE3MS42NiAzMS40NzA2IDE3MS42NiAy"
    "Ny40ODM2Wk0xODIuNTgyIDI3LjQ4MzZDMTgyLjU4MiAyNS4zMjU0IDE4MS4yODYgMjMu"
    "NDQ3MiAxNzkuMDEgMjMuNDQ3MkMxNzYuNzM0IDIzLjQ0NzIgMTc1LjQ2NSAyNS4zMTg4"
    "IDE3NS40NjUgMjcuNDgzNkMxNzUuNDY1IDI5LjY0ODQgMTc2LjczNCAzMS41NDY0IDE3"
    "OS4wMSAzMS41NDY0QzE4MS4yODYgMzEuNTQ2NCAxODIuNTgyIDI5LjY3ODEgMTgyLjU4"
    "MiAyNy40ODM2WiIvPjxwYXRoIGQ9Ik0xOTkuMjk5IDM0LjQ1NTlWMzIuNzAzQzE5OC42"
    "NjggMzMuMzc4OCAxOTcuOTAxIDMzLjkxNTEgMTk3LjA0NiAzNC4yNzY4QzE5Ni4xOTIg"
    "MzQuNjM4NCAxOTUuMjcgMzQuODE3NCAxOTQuMzQyIDM0LjgwMTlDMTkxLjI0OCAzNC44"
    "MDE5IDE4OS43ODkgMzMuMTM0NyAxODkuNzg5IDMwLjQzMjdWMjAuNTcwOEgxOTMuNTA4"
    "VjI4Ljk5NjFDMTkzLjUwOCAzMC45MjA0IDE5NC41MjggMzEuNTUzIDE5Ni4xMDYgMzEu"
    "NTUzQzE5Ni43MjYgMzEuNTQyNiAxOTcuMzM1IDMxLjM5NTEgMTk3Ljg5IDMxLjEyMTRD"
    "MTk4LjQ0NiAzMC44NDk5IDE5OC45MzMgMzAuNDU2NyAxOTkuMzEzIDI5Ljk3MTRWMjAu"
    "NTcwOEgyMDMuMDIxVjM0LjQ1NTlIMTk5LjI5OVoiLz48cGF0aCBkPSJNMjE2LjE4OSAz"
    "NC40MzYxVjI2LjAzMzhDMjE2LjE4OSAyNC4xMDk1IDIxNS4xMzkgMjMuNDQ3MiAyMTMu"
    "NTMxIDIzLjQ0NzJDMjEyLjg4NyAyMy40NTMzIDIxMi4yNTMgMjMuNjA1NSAyMTEuNjc3"
    "IDIzLjg5MjFDMjExLjEwNyAyNC4xNzMyIDIxMC42MTIgMjQuNTgyOCAyMTAuMjMxIDI1"
    "LjA4ODFWMzQuNDM2MUgyMDYuNDA3VjIwLjU0NDNIMjEwLjIxOFYyMi4zNTMzQzIxMC44"
    "NjIgMjEuNjU4NSAyMTEuNjQ3IDIxLjEwNyAyMTIuNTIyIDIwLjczNUMyMTMuMzk2IDIw"
    "LjM2MjkgMjE0LjM0MSAyMC4xNzg5IDIxNS4yOTIgMjAuMTk1MUMyMTguNDcyIDIwLjE5"
    "NTEgMjIwLjAwNCAyMS45MjE2IDIyMC4wMDQgMjQuNjIzNlYzNC40MzYxSDIxNi4xODla"
    "Ii8+PHBhdGggZD0iTTIzMy4yNTggMzQuNDUyNVYzMi42MzY5QzIzMi43NSAzMy4zMDcx"
    "IDIzMi4wOTMgMzMuODUxMyAyMzEuMzM3IDM0LjIyN0MyMzAuNTgxIDM0LjYwMjYgMjI5"
    "Ljc0OCAzNC43OTkzIDIyOC45MDIgMzQuODAxN0MyMjUuMzM3IDM0LjgwMTcgMjIyLjY0"
    "NSAzMi4xMTMgMjIyLjY0NSAyNy40MDc3QzIyMi42NDUgMjIuNzk0NyAyMjUuMzA0IDE5"
    "Ljk4MDggMjI4LjkwMiAxOS45ODA4QzIyOS43NDcgMTkuOTc3NyAyMzAuNTggMjAuMTcx"
    "OCAyMzEuMzM1IDIwLjU0NzZDMjMyLjA5MiAyMC45MjM4IDIzMi43NTEgMjEuNDY5OCAy"
    "MzMuMjU4IDIyLjE0MjNWMTQuOTUyNkgyMzdWMzQuNDUyNUgyMzMuMjU4Wk0yMzMuMjU4"
    "IDI5Ljg4ODlWMjQuODgwNUMyMzIuNjQ0IDIzLjk0MTQgMjMxLjI5OCAyMy4yNjkyIDIz"
    "MC4wNDIgMjMuMjY5MkMyMjcuOTM5IDIzLjI2OTIgMjI2LjQ3NyAyNC45MzY1IDIyNi40"
    "NzcgMjcuMzk0NkMyMjYuNDc3IDI5Ljg1MjYgMjI3LjkzOSAzMS40OTAzIDIzMC4wNDIg"
    "MzEuNDkwM0MyMzEuMjk4IDMxLjQ5MDMgMjMyLjY0NCAzMC44MTE1IDIzMy4yNTggMjku"
    "ODc5VjI5Ljg4ODlaIi8+PHBhdGggZD0iTTI0LjY0NTIgMEMxOS43NTU4IDAuMDExNyAx"
    "NC45Nzk5IDEuNDYxNyAxMC45MjE5IDQuMTY2NEM2Ljg2NCA2Ljg3MTEgMy43MDY1IDEw"
    "LjcwODggMS44NDkxIDE1LjE5MzhDLTAuMDA4MyAxOS42Nzg5LTAuNDgyIDI0LjYwOTUg"
    "MC40ODc4IDI5LjM2MTZDMS40NTc3IDM0LjExMzggMy44Mjc1IDM4LjQ3MzcgNy4yOTc0"
    "IDQxLjg4OTZDMTAuNzY3MyA0NS4zMDU1IDE1LjE4MTIgNDcuNjIzOCAxOS45ODA0IDQ4"
    "LjU1MUMyNC43Nzk1IDQ5LjQ3ODEgMjkuNzQ4MiA0OC45NzI1IDM0LjI1NzUgNDcuMDk4"
    "MUMzOC43NjY3IDQ1LjIyMzcgNDIuNjEzOCA0Mi4wNjQ4IDQ1LjMxMTcgMzguMDIxM0M0"
    "OC4wMDk3IDMzLjk3NzggNDkuNDM3MiAyOS4yMzE0IDQ5LjQxMzUgMjQuMzgyOUM0OS40"
    "MTM2IDIxLjE2NTkgNDguNzcxNyAxNy45ODA2IDQ3LjUyNDggMTUuMDEwN0M0Ni4yNzc5"
    "IDEyLjA0MDcgNDQuNDUwNiA5LjM0NDggNDIuMTQ4MyA3LjA3ODNDMzkuODQ1OSA0Ljgx"
    "MTggMzcuMTE0MSAzLjAxOTUgMzQuMTEwMSAxLjgwNDZDMzEuMTA2MSAwLjU4OTggMjcu"
    "ODg5My0wLjAyMzYgMjQuNjQ1MiAwWk0yNC4zNzYxIDQ1LjM5NTJDMTkuMzY5OSA0NS4z"
    "MTEyIDE0LjU1NzQgNDMuNDYyNyAxMC44MDA0IDQwLjE4MDdDNy4wNDM0IDM2Ljg5ODcg"
    "NC41ODc0IDMyLjM5NzcgMy44NzIxIDI3LjQ4MzZDMy4xNTY5IDIyLjU2OTUgNC4yMjky"
    "IDE3LjU2MzUgNi44OTY5IDEzLjM2MkM5LjU2NDcgOS4xNjA1IDEzLjY1MzYgNi4wMzc5"
    "IDE4LjQzMTUgNC41NTM2QzI4LjMwMDMgMS41MDkgMzcuODA2OSA2LjExODcgNDEuOTQ3"
    "MSAxMi42MDk5QzQxLjg4NCAxMi42MDk5IDQxLjc4NzYgMTIuNjcyNSA0MS43NjQ0IDEy"
    "LjY0OTRDMzkuODg3IDEwLjY3MjQgMzcuNDQ0NyAxMC4xOTggMzQuODI2MyAxMC43NjhD"
    "MzEuOTYyMSAxMS4zOTczIDI5LjMyNzEgMTIuNTExIDI3LjEzNCAxNC40NjgzQzI0Ljg4"
    "NzggMTYuNDY1IDIyLjA5NjYgMTcuODM5MSAxOS4yOTIyIDE4Ljg3MzdDMTcuNjEwOCAx"
    "OS40OTMyIDE1Ljg4OTYgMjAuMDAwNiAxNC4xNTg0IDIwLjQ3MThDMTMuMjE4IDIwLjcy"
    "NTUgMTIuMjc0NCAyMC45NzkyIDExLjM1NzMgMjEuMjk1NUMxMC4xMDc5IDIxLjcyNzIg"
    "OS45Mjg1IDIyLjYzMzMgMTAuNjkyNyAyMy42OTFDMTEuMDkyNSAyNC4zMTc2IDExLjM4"
    "NDQgMjUuMDA1OCAxMS41NTY2IDI1LjcyNzNDMTIuMjY0NCAyOC4xNjIzIDEzLjUxMDQg"
    "MzAuMDc2NyAxNi4xMzg4IDMwLjgwNDlDMTYuMjc1MiAzMC44NDY2IDE2LjQgMzAuOTE5"
    "MyAxNi41MDMyIDMxLjAxNzFDMTYuNjA2NCAzMS4xMTQ5IDE2LjY4NTMgMzEuMjM1MSAx"
    "Ni43MzM2IDMxLjM2ODRDMTYuOTcyOCAzMi44MjggMTguMDk1OSAzMy4zNzgzIDE5LjI4"
    "ODggMzMuNTM2NUMyMy44ODEgMzQuMTQ5MyAyOC4xODQgMzMuNDgwNCAzMS43OTkyIDMw"
    "LjI5MDlDMzEuODQ5MSAzMC4yNDggMzEuOTM1NSAzMC4yNDggMzIuMDk4MyAzMC4yMDE5"
    "QzMxLjkxODkgMzIuMTc4OSAzMS42NzYzIDM0LjEwMzIgMzEuNjAzMiAzNi4wMjc1QzMx"
    "LjU2MzUgMzcuMjE3NyAzMS42NjI4IDM4LjQwODYgMzEuODk4OSAzOS41NzYyQzMyLjE0"
    "MTUgNDAuODE1MSAzMi43NzYxIDQwLjk5OTYgMzMuNzAzMiA0MC4xNDk1QzM0LjgzMyAz"
    "OS4xMTE2IDM1Ljg1NjQgMzcuOTY0OSAzNi45NTYzIDM2Ljg5MDhDMzguNjY3NSAzNS4y"
    "MTM2IDQwLjM2MjEgMzMuNTIzMyA0Mi4xNDMyIDMxLjk0ODNDNDIuNzQ3OSAzMS40MDc5"
    "IDQzLjU4MiAzMC45NTk4IDQ0LjQ2OTEgMzEuNTg5MUM0Mi44Mzc2IDM3LjQyNzkgMzUu"
    "NDc3NiA0NS42MzkgMjQuMzc2MSA0NS4zOTUyWiIvPjwvZz48ZGVmcz48Y2xpcFBhdGgg"
    "aWQ9ImNsaXBfY2giPjxyZWN0IHdpZHRoPSIyMzciIGhlaWdodD0iNDkiLz48L2NsaXBQ"
    "YXRoPjwvZGVmcz48L3N2Zz4="
)

DEFAULT_EVENTS = [
    ("GlobalErrorHandling", "Global Errors", "OnGlobalError"),
    ("AgentOfferContact", "Agent Offer", "AgentOffered"),
    ("ContactPredial", "Contact Predial", "PreDial"),
    ("ContactOutboundCampaignResult", "Campaign Result", "OutboundCampaignCallResult"),
    ("ContactAniUpdated", "ANI Updated", "ContactAniUpdated"),
    ("ContactCallbackFailed", "Callback Failed", "CallbackFailed"),
    ("ContactEnded", "Contact Ended", "ContactEnded"),
    ("AgentContactAssigned", "Agent Assigned", "AgentContactAssigned"),
    ("ContactReservationStarted", "Reservation Started", "ReservationStarted"),
    ("FCAsk(ContactLastAgentRemoved)", "Last Agent Removed", "LastAgentRemoved"),
]

CARD_WIDTH = 230
HORIZ_SPACING = 300
VERT_GAP = 80
HEADER_HEIGHT = 56
PORT_ROW_HEIGHT = 30
SECTION_HEADER_HEIGHT = 30
MIN_DETAILS_CONTENT = 60
DETAILS_LINE_HEIGHT = 15
EVENT_CARD_GAP = 40

PORT_ALIASES = {
    "Success": "Default", "Error": "Error",
    "TRUE": "True", "FALSE": "False",
    "onSuccess": "Default", "onError": "Error",
    "Timeout": "Error", "NoInput": "Error",
    "Failure": "Failure", "Failed": "Failed",
    "Transferred": "Transferred",
    "True": "Transferred", "False": "Failed",
}


def _default_port(act, fallback="Default"):
    """Return the first exit port of an activity, or fallback."""
    return act["ports"][0] if act["ports"] else fallback


# ─── Layout Engine ───────────────────────────────────────────────────


def compute_card_height(act):
    """Compute total card height based on details lines and port count."""
    details_text = act.get("details", "")
    if details_text.strip():
        line_count = len(details_text.split("\n"))
        details_content_h = max(MIN_DETAILS_CONTENT, line_count * DETAILS_LINE_HEIGHT)
        details_h = SECTION_HEADER_HEIGHT + details_content_h
    else:
        details_h = SECTION_HEADER_HEIGHT  # collapsed

    port_count = len(act["ports"])
    connections_h = SECTION_HEADER_HEIGHT + (port_count * PORT_ROW_HEIGHT)

    total = HEADER_HEIGHT + details_h + connections_h
    act["_details_h"] = details_h
    act["_connections_h"] = connections_h
    act["_total_h"] = total
    act["_details_content_h"] = details_h - SECTION_HEADER_HEIGHT if details_text.strip() else 0
    act["_has_details"] = bool(details_text.strip())
    return total


def layout_activities(activities, edges):
    """BFS layout: assign x,y to each activity."""
    adj = defaultdict(list)
    for src, port, tgt in edges:
        adj[src].append(tgt)

    # Find start node
    start = None
    for a in activities:
        if a["type"] in ("NewPhoneContact", "Start Flow"):
            start = a["id"]
            break
    if not start and activities:
        start = activities[0]["id"]

    # BFS for depth assignment
    depths = {}
    bfs_queue = deque([start])
    depths[start] = 0
    visited = {start}
    while bfs_queue:
        current = bfs_queue.popleft()
        for nxt in adj.get(current, []):
            if nxt not in visited:
                visited.add(nxt)
                depths[nxt] = depths[current] + 1
                bfs_queue.append(nxt)

    # Assign depth to unvisited nodes
    max_depth = max(depths.values()) if depths else 0
    for a in activities:
        if a["id"] not in depths:
            max_depth += 1
            depths[a["id"]] = max_depth

    # Group by depth, assign lane (y position)
    depth_groups = defaultdict(list)
    for a in activities:
        depth_groups[depths[a["id"]]].append(a)

    for depth, group in depth_groups.items():
        col_max_h = max(a["_total_h"] for a in group)
        for lane, a in enumerate(group):
            a["_x"] = 60 + depth * HORIZ_SPACING
            a["_y"] = 60 + lane * (col_max_h + VERT_GAP)

# ─── XML Generation ──────────────────────────────────────────────────

def _esc(text):
    """Entity-encode for XML attributes: & first, then < > \"."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text


def _type_slug(atype):
    return atype.lower().replace(" ", "-")


def _get_icon(atype, cat):
    return ICON_FOR_TYPE.get(atype, ICON_CAT_DEFAULT.get(cat, ICON_PLAY))


def make_header_html(act):
    """Build the HTML table for the card header, then entity-encode it."""
    cat_info = CATEGORIES.get(act["category"], CATEGORIES["Action"])
    icon = _get_icon(act["type"], act["category"])
    slug = _type_slug(act["type"])
    raw = (
        f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;font-family:Helvetica Neue,Arial,sans-serif;">'
        f'<tr><td width="46" valign="middle" style="padding-left:10px;">'
        f'<div style="width:36px;height:36px;{cat_info["radius"]};'
        f'background-color:{cat_info["badge"]};'
        f"background-image:url('{icon}');"
        f'background-size:22px 22px;background-position:center center;'
        f'background-repeat:no-repeat;"></div></td>'
        f'<td valign="middle" style="padding-left:8px;">'
        f'<b style="font-size:13px;color:#111827;">{act["name"]}</b><br/>'
        f'<span style="font-size:11px;color:#6b7280;">{slug}</span>'
        f'</td></tr></table>'
    )
    return _esc(raw)


def gen_card_xml(act):
    """Generate all mxCell elements for one activity card."""
    cells = []
    aid = act["id"]
    cat_info = CATEGORIES.get(act["category"], CATEGORIES["Action"])
    entry_y = round(28.0 / act["_total_h"], 4)
    header_val = make_header_html(act)

    # Root card
    cells.append(
        f'        <mxCell id="{aid}" value="{header_val}" '
        f'style="swimlane;fontStyle=0;childLayout=stackLayout;horizontal=1;'
        f'startSize=56;horizontalStack=0;resizeParent=1;resizeParentMax=0;'
        f'resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;'
        f'shadow=1;rounded=1;arcSize=3;align=left;'
        f'fillColor={cat_info["fill"]};strokeColor=#d1d5db;'
        f'swimlaneFillColor=#ffffff;points=[[0,{entry_y}]];'
        f'portConstraint=east;" vertex="1" parent="1">'
        f'<mxGeometry x="{act["_x"]}" y="{act["_y"]}" '
        f'width="{CARD_WIDTH}" height="{act["_total_h"]}" as="geometry"/>'
        f'</mxCell>'
    )

    # Details section
    details_y = HEADER_HEIGHT
    if act["_has_details"]:
        cells.append(
            f'        <mxCell id="{aid}_s0" '
            f'value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Details" '
            f'style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;'
            f'horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;'
            f'resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;'
            f'whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;'
            f'swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" '
            f'vertex="1" parent="{aid}">'
            f'<mxGeometry x="0" y="{details_y}" width="{CARD_WIDTH}" '
            f'height="{act["_details_h"]}" as="geometry"/>'
            f'</mxCell>'
        )
        # Details content
        escaped_details = _esc(act["details"])
        cells.append(
            f'        <mxCell id="{aid}_s0_p0" '
            f'value="{escaped_details}" '
            f'style="text;strokeColor=#d1d5db;fillColor=none;align=left;'
            f'verticalAlign=top;spacingLeft=8;spacingRight=8;'
            f'spacingTop=6;fontSize=8;rotatable=0;fontColor=#000000;html=0;'
            f'whiteSpace=wrap;overflow=hidden;connectable=0;" '
            f'vertex="1" parent="{aid}_s0">'
            f'<mxGeometry x="0" y="30" width="{CARD_WIDTH}" '
            f'height="{act["_details_content_h"]}" as="geometry"/>'
            f'</mxCell>'
        )
    else:
        # Collapsed details
        cells.append(
            f'        <mxCell id="{aid}_s0" '
            f'value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Details" '
            f'style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;'
            f'horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;'
            f'resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;'
            f'whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;'
            f'swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" '
            f'collapsed="1" vertex="1" parent="{aid}">'
            f'<mxGeometry x="0" y="{details_y}" width="{CARD_WIDTH}" '
            f'height="30" as="geometry">'
            f'<mxRectangle x="0" y="{details_y}" width="{CARD_WIDTH}" '
            f'height="90" as="alternateBounds"/>'
            f'</mxGeometry></mxCell>'
        )

    # Connections section
    conn_y = details_y + act["_details_h"]
    cells.append(
        f'        <mxCell id="{aid}_s1" '
        f'value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Connections" '
        f'style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;'
        f'horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;'
        f'resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;'
        f'whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;'
        f'swimlaneFillColor=#ffffff;align=left;points=[];" '
        f'vertex="1" parent="{aid}">'
        f'<mxGeometry x="0" y="{conn_y}" width="{CARD_WIDTH}" '
        f'height="{act["_connections_h"]}" as="geometry"/>'
        f'</mxCell>'
    )

    # Port rows
    for n, port_name in enumerate(act["ports"]):
        port_y = SECTION_HEADER_HEIGHT + n * PORT_ROW_HEIGHT
        cells.append(
            f'        <mxCell id="{aid}_s1_p{n}" value="{port_name}" '
            f'style="text;strokeColor=none;fillColor=none;align=left;'
            f'verticalAlign=middle;spacingLeft=8;spacingRight=4;fontSize=11;'
            f'rotatable=0;points=[[1,0.5]];portConstraint=east;" '
            f'vertex="1" parent="{aid}_s1">'
            f'<mxGeometry x="0" y="{port_y}" width="{CARD_WIDTH}" '
            f'height="30" as="geometry"/>'
            f'</mxCell>'
        )

    return "\n".join(cells)


def gen_edge_xml(edges, activities):
    """Generate edge mxCell elements."""
    id_to_act = {a["id"]: a for a in activities}
    cells = []
    edge_counter = 0

    for src_id, port_name, tgt_id in edges:
        src_act = id_to_act.get(src_id)
        tgt_act = id_to_act.get(tgt_id)
        if not src_act or not tgt_act:
            continue

        # Find source port cell ID, with fallback through PORT_ALIASES
        port_idx = None
        effective_port = port_name
        for candidate in (port_name, PORT_ALIASES.get(port_name)):
            if candidate is None:
                continue
            for i, p in enumerate(src_act["ports"]):
                if p == candidate:
                    port_idx = i
                    effective_port = candidate
                    break
            if port_idx is not None:
                break
        if port_idx is None:
            if not src_act["ports"]:
                continue
            port_idx = 0
            effective_port = _default_port(src_act, port_name)

        source_port_id = f"{src_id}_s1_p{port_idx}"
        target_entry_y = round(28.0 / tgt_act["_total_h"], 4)
        edge_counter += 1
        edge_id = f"edge_{edge_counter:03d}"

        cells.append(
            f'        <mxCell id="{edge_id}" value="{effective_port}" '
            f'style="edgeStyle=orthogonalEdgeStyle;curved=1;html=1;rounded=0;'
            f'strokeColor=#6b7280;fontSize=10;fontColor=#374151;'
            f'exitX=1;exitY=0.5;exitDx=0;exitDy=0;'
            f'entryX=0;entryY={target_entry_y};entryDx=0;entryDy=0;" '
            f'edge="1" source="{source_port_id}" target="{tgt_id}" parent="1">'
            f'<mxGeometry relative="1" as="geometry"/>'
            f'</mxCell>'
        )
    return "\n".join(cells)


def gen_summary_xml(model, event_count):
    """Generate Summary tab cells."""
    flow_name = model["flow_name"]
    variables = model["variables"]
    main_count = len(model["activities"])
    var_count = len(variables)

    # Brand logo
    cells = [
        f'        <mxCell id="sum_brand" value="{_esc(f"""<img src="{CISCO_LOGO}" height="28" style="display:block"/>""")}" '
        f'style="text;html=1;align=center;verticalAlign=middle;fillColor=#218381;strokeColor=none;rounded=1;" '
        f'vertex="1" parent="1"><mxGeometry x="20" y="20" width="820" height="52" as="geometry"/></mxCell>',
    ]
    # Title
    cells.append(
        f'        <mxCell id="sum_title" value="{_esc(flow_name)}" '
        f'style="text;html=1;fontSize=22;fontStyle=1;align=left;verticalAlign=middle;'
        f'fillColor=#0e7490;fontColor=#ffffff;strokeColor=none;rounded=1;spacingLeft=16;" '
        f'vertex="1" parent="1"><mxGeometry x="20" y="82" width="820" height="54" as="geometry"/></mxCell>'
    )
    # Metadata table
    meta_html = (
        '<table style="border-collapse:collapse;width:100%">'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Flow Name</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{flow_name}</td></tr>'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Author</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{model["author"]}</td></tr>'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Created</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{model["date"]}</td></tr>'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Description</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{model.get("description", flow_name)}</td></tr>'
        '</table>'
    )
    cells.append(
        f'        <mxCell id="sum_meta" value="{_esc(meta_html)}" '
        f'style="text;html=1;fontSize=11;align=left;verticalAlign=top;fillColor=#ffffff;strokeColor=#d1d5db;rounded=1;spacingLeft=0;spacingTop=0;" '
        f'vertex="1" parent="1"><mxGeometry x="20" y="146" width="405" height="142" as="geometry"/></mxCell>'
    )
    # Stats table
    stats_html = (
        '<table style="border-collapse:collapse;width:100%">'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Main Flow Nodes</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{main_count}</td></tr>'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Event Flow Nodes</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{event_count}</td></tr>'
        f'<tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold;width:46%;border-bottom:1px solid #e5e7eb">Total Variables</td><td style="padding:4px 10px;border-bottom:1px solid #e5e7eb">{var_count}</td></tr>'
        '</table>'
    )
    cells.append(
        f'        <mxCell id="sum_stats" value="{_esc(stats_html)}" '
        f'style="text;html=1;fontSize=11;align=left;verticalAlign=top;fillColor=#ffffff;strokeColor=#d1d5db;rounded=1;spacingLeft=0;spacingTop=0;" '
        f'vertex="1" parent="1"><mxGeometry x="435" y="146" width="405" height="142" as="geometry"/></mxCell>'
    )
    # Variables
    if variables:
        cells.append(
            '        <mxCell id="sum_varlabel" value="Flow Variables" '
            'style="text;html=1;fontSize=13;fontStyle=1;align=left;verticalAlign=middle;'
            'fillColor=#f3f4f6;strokeColor=#d1d5db;rounded=0;spacingLeft=10;" '
            'vertex="1" parent="1"><mxGeometry x="20" y="304" width="820" height="28" as="geometry"/></mxCell>'
        )
        var_rows = (
            '<tr style="background:#0e7490;color:#fff">'
            '<th style="padding:5px 10px;text-align:left">Name</th>'
            '<th style="padding:5px 10px;text-align:left">Type</th>'
            '<th style="padding:5px 10px;text-align:left">Default Value</th>'
            '<th style="padding:5px 10px;text-align:left">Description</th></tr>'
        )
        for v in variables:
            var_rows += (
                f'<tr style="border-bottom:1px solid #e5e7eb">'
                f'<td style="padding:4px 10px;font-weight:bold">{v["name"]}</td>'
                f'<td style="padding:4px 10px;color:#6b7280">{v["type"]}</td>'
                f'<td style="padding:4px 10px">{v["default"]}</td>'
                f'<td style="padding:4px 10px;color:#6b7280">{v["desc"]}</td></tr>'
            )
        var_html = f'<table style="border-collapse:collapse;width:100%">{var_rows}</table>'
        var_h = 28 + len(variables) * 28
        cells.append(
            f'        <mxCell id="sum_vars" value="{_esc(var_html)}" '
            f'style="text;html=1;fontSize=11;align=left;verticalAlign=top;fillColor=#ffffff;strokeColor=#d1d5db;rounded=1;spacingLeft=0;spacingTop=0;" '
            f'vertex="1" parent="1"><mxGeometry x="20" y="332" width="820" height="{var_h}" as="geometry"/></mxCell>'
        )
    return "\n".join(cells)


def gen_event_flow_xml(events=None):
    """Generate Event Flow tab cells for event handlers."""
    event_list = events if events else DEFAULT_EVENTS
    cells = []
    y = 60
    cat_info = CATEGORIES["Event"]
    icon = ICON_EVENT

    for display_name, event_type, event_name in event_list:
        aid = f"evt_{event_name}"
        ports = ["Out"]
        port_count = len(ports)
        details_text = f"Event Type: {event_type}\nEvent Name: {event_name}"
        detail_lines = len(details_text.split("\n"))
        details_content_h = max(MIN_DETAILS_CONTENT, detail_lines * DETAILS_LINE_HEIGHT)
        details_h = SECTION_HEADER_HEIGHT + details_content_h
        connections_h = SECTION_HEADER_HEIGHT + port_count * PORT_ROW_HEIGHT
        total_h = HEADER_HEIGHT + details_h + connections_h
        entry_y = round(28.0 / total_h, 4)

        slug = "event-handler"
        raw_header = (
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-collapse:collapse;font-family:Helvetica Neue,Arial,sans-serif;">'
            f'<tr><td width="46" valign="middle" style="padding-left:10px;">'
            f'<div style="width:36px;height:36px;{cat_info["radius"]};'
            f'background-color:{cat_info["badge"]};'
            f"background-image:url('{icon}');"
            f'background-size:22px 22px;background-position:center center;'
            f'background-repeat:no-repeat;"></div></td>'
            f'<td valign="middle" style="padding-left:8px;">'
            f'<b style="font-size:13px;color:#111827;">{display_name}</b><br/>'
            f'<span style="font-size:11px;color:#6b7280;">{slug}</span>'
            f'</td></tr></table>'
        )

        cells.append(
            f'        <mxCell id="{aid}" value="{_esc(raw_header)}" '
            f'style="swimlane;fontStyle=0;childLayout=stackLayout;horizontal=1;'
            f'startSize=56;horizontalStack=0;resizeParent=1;resizeParentMax=0;'
            f'resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;'
            f'shadow=1;rounded=1;arcSize=3;align=left;'
            f'fillColor={cat_info["fill"]};strokeColor=#d1d5db;'
            f'swimlaneFillColor=#ffffff;points=[[0,{entry_y}]];'
            f'portConstraint=east;" vertex="1" parent="1">'
            f'<mxGeometry x="60" y="{y}" '
            f'width="{CARD_WIDTH}" height="{total_h}" as="geometry"/>'
            f'</mxCell>'
        )
        # Details section
        cells.append(
            f'        <mxCell id="{aid}_s0" '
            f'value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Details" '
            f'style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;'
            f'horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;'
            f'resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;'
            f'whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;'
            f'swimlaneFillColor=#ffffff;align=left;points=[];connectable=0;" '
            f'vertex="1" parent="{aid}">'
            f'<mxGeometry x="0" y="{HEADER_HEIGHT}" width="{CARD_WIDTH}" '
            f'height="{details_h}" as="geometry"/>'
            f'</mxCell>'
        )
        cells.append(
            f'        <mxCell id="{aid}_s0_p0" '
            f'value="{_esc(details_text)}" '
            f'style="text;strokeColor=#d1d5db;fillColor=none;align=left;'
            f'verticalAlign=top;spacingLeft=8;spacingRight=8;'
            f'spacingTop=6;fontSize=8;rotatable=0;fontColor=#000000;html=0;'
            f'whiteSpace=wrap;overflow=hidden;connectable=0;" '
            f'vertex="1" parent="{aid}_s0">'
            f'<mxGeometry x="0" y="30" width="{CARD_WIDTH}" '
            f'height="{details_content_h}" as="geometry"/>'
            f'</mxCell>'
        )
        # Connections section
        conn_y = HEADER_HEIGHT + details_h
        cells.append(
            f'        <mxCell id="{aid}_s1" '
            f'value="&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;Connections" '
            f'style="swimlane;fontStyle=1;fontSize=11;childLayout=stackLayout;'
            f'horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;'
            f'resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;'
            f'whiteSpace=wrap;html=1;fillColor=#f3f4f6;strokeColor=none;'
            f'swimlaneFillColor=#ffffff;align=left;points=[];" '
            f'vertex="1" parent="{aid}">'
            f'<mxGeometry x="0" y="{conn_y}" width="{CARD_WIDTH}" '
            f'height="{connections_h}" as="geometry"/>'
            f'</mxCell>'
        )
        cells.append(
            f'        <mxCell id="{aid}_s1_p0" value="Out" '
            f'style="text;strokeColor=none;fillColor=none;align=left;'
            f'verticalAlign=middle;spacingLeft=8;spacingRight=4;fontSize=11;'
            f'rotatable=0;points=[[1,0.5]];portConstraint=east;" '
            f'vertex="1" parent="{aid}_s1">'
            f'<mxGeometry x="0" y="30" width="{CARD_WIDTH}" '
            f'height="30" as="geometry"/>'
            f'</mxCell>'
        )
        y += total_h + EVENT_CARD_GAP

    return "\n".join(cells)


def assemble_drawio(model):
    """Assemble the full .drawio XML from the model."""
    activities = model["activities"]
    edges = model["edges"]
    events = model.get("events") or None

    # Compute heights and layout
    for a in activities:
        compute_card_height(a)
    layout_activities(activities, edges)

    # Main flow cells
    main_cards = []
    for a in activities:
        main_cards.append(gen_card_xml(a))

    edge_xml = gen_edge_xml(edges, activities)

    # Logo in top-right of main flow
    max_x = max((a["_x"] for a in activities), default=60) + HORIZ_SPACING
    logo_cell = (
        f'        <mxCell id="main_logo" '
        f'value="{_esc(f"""<img src="{CISCO_LOGO}" height="33" style="display:block"/>""")}" '
        f'style="text;html=1;align=center;verticalAlign=middle;'
        f'fillColor=none;strokeColor=none;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{max_x}" y="20" width="160" height="33" as="geometry"/>'
        f'</mxCell>'
    )

    main_flow_content = "\n".join(main_cards) + "\n" + edge_xml + "\n" + logo_cell
    event_list = events if events else DEFAULT_EVENTS
    summary_content = gen_summary_xml(model, len(event_list))
    event_content = gen_event_flow_xml(events)

    gm_attrs = (
        'dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="1654" pageHeight="1169" math="0" shadow="0"'
    )

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram id="summary" name="Summary">
    <mxGraphModel {gm_attrs}>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{summary_content}
      </root>
    </mxGraphModel>
  </diagram>
  <diagram id="main-flow" name="Main Flow">
    <mxGraphModel {gm_attrs}>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{main_flow_content}
      </root>
    </mxGraphModel>
  </diagram>
  <diagram id="event-flow" name="Event Flow">
    <mxGraphModel {gm_attrs}>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{event_content}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    return xml


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 generate.py <model.json> <output.drawio>")
        sys.exit(1)

    model = json.loads(Path(sys.argv[1]).read_text())
    out_path = Path(sys.argv[2])

    # Validate
    if not model.get("flow_name"):
        print("Error: flow_name is required", file=sys.stderr)
        sys.exit(1)

    if not model.get("activities"):
        print("Error: at least one activity required", file=sys.stderr)
        sys.exit(1)

    for i, a in enumerate(model["activities"]):
        for key in ("id", "name", "type"):
            if key not in a:
                print(f"Error: activity[{i}] missing required key '{key}'", file=sys.stderr)
                sys.exit(1)

    act_ids = {a["id"] for a in model["activities"]}
    for i, e in enumerate(model.get("edges", [])):
        for key in ("source", "port", "target"):
            if key not in e:
                print(f"Error: edge[{i}] missing required key '{key}'", file=sys.stderr)
                sys.exit(1)
        if e["source"] not in act_ids:
            print(f"Error: edge source '{e['source']}' not found in activities", file=sys.stderr)
            sys.exit(1)
        if e["target"] not in act_ids:
            print(f"Error: edge target '{e['target']}' not found in activities", file=sys.stderr)
            sys.exit(1)

    # Enrich activities with category and ports from type
    for act in model["activities"]:
        act["category"] = ACTIVITY_CATEGORY.get(act["type"], "Action")
        act["ports"] = list(ACTIVITY_PORTS.get(act["type"], ["Default", "Error"]))
        if act["type"] not in ACTIVITY_CATEGORY:
            print(f"  WARN: activity type '{act['type']}' not recognized, defaulting to Action", file=sys.stderr)

    # Populate dynamic ports for Menu/Case/Percentage Allocation from edges
    dynamic_types = {t for t, ports in ACTIVITY_PORTS.items() if not ports}
    act_by_id = {a["id"]: a for a in model["activities"]}
    for e in model.get("edges", []):
        src = act_by_id.get(e["source"])
        if src and src["type"] in dynamic_types and e["port"] not in src["ports"]:
            src["ports"].append(e["port"])

    # Default missing top-level fields
    model.setdefault("variables", [])
    model.setdefault("edges", [])
    model.setdefault("author", "Unknown")
    model.setdefault("date", "")
    model.setdefault("description", model.get("flow_name", ""))

    # Convert event dicts to tuples matching DEFAULT_EVENTS format
    if model.get("events"):
        model["events"] = [(e["name"], e["event_type"], e["event_name"]) for e in model["events"]]

    # Convert edge dicts to tuples for internal use
    model["edges"] = [(e["source"], e["port"], e["target"]) for e in model["edges"]]

    xml = assemble_drawio(model)
    out_path.write_text(xml, encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  Activities: {len(model['activities'])}")
    print(f"  Edges: {len(model['edges'])}")
    print(f"  Variables: {len(model['variables'])}")


if __name__ == "__main__":
    main()
