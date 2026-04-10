"""Scenario metadata and paragraph templates for user communication notices.

Each scenario maps to a user-impact category detected from the post-analyze store.
Templates use {variable} placeholders substituted at render time.
"""

from __future__ import annotations

SCENARIO_ORDER: list[str] = [
    "phone_upgrade",
    "webex_app_transition",
    "device_replacement",
    "forwarding_simplified",
    "voicemail_rerecord",
    "layout_changes",
    "exec_assistant",
]

SCENARIOS: dict[str, dict] = {
    "phone_upgrade": {
        "title": "Your Phone Is Being Upgraded",
        "priority": 1,
        "template": (
            "Your desk phone ({cucm_model}) will be upgraded to run Webex Calling "
            "firmware. This is a remote firmware update \u2014 you do not need to do "
            "anything. Your phone will restart once during the migration window. After "
            "the restart, your phone will look slightly different (new menus and icons), "
            "but your extension ({extension}), speed dials, and call behavior will "
            "continue to work. The upgrade typically takes 5\u201310 minutes."
        ),
        "variables": ["cucm_model", "extension", "brand"],
    },
    "webex_app_transition": {
        "title": "You\u2019ll Use Webex App Instead of Jabber",
        "priority": 2,
        "template": (
            "You currently use Cisco Jabber for voice calls. After migration, you\u2019ll "
            "use the <strong>Webex App</strong> instead. The Webex App provides the same "
            "calling features you use today \u2014 plus messaging, meetings, and screen "
            "sharing in one application. Your IT team will install Webex App on your "
            "computer before migration day. Your extension ({extension}) and phone number "
            "will not change."
            "\n\n"
            "<strong>What you need to do:</strong> Sign in to the Webex App when prompted "
            "by your IT team. Your call history will not transfer, but all other settings "
            "(forwarding, voicemail, etc.) will be configured automatically."
        ),
        "variables": ["extension", "brand"],
    },
    "device_replacement": {
        "title": "Your Phone Is Being Replaced",
        "priority": 3,
        "template": (
            "Your current desk phone ({cucm_model}) is not compatible with Webex Calling "
            "and will be replaced with a new phone. Your IT team will coordinate the swap "
            "\u2014 you\u2019ll receive a new phone at your desk before or on migration day. "
            "Your extension ({extension}) and phone number will not change."
            "\n\n"
            "<strong>What you need to do:</strong> When your new phone arrives, it will "
            "already be configured with your line and basic settings. You may want to:"
            "\n<ul>"
            "\n<li>Reconfigure your speed dials and personal ring settings</li>"
            "\n<li>Set your preferred display brightness and ringtone</li>"
            "\n<li>Contact {helpdesk} if you need help with the new phone\u2019s features</li>"
            "\n</ul>"
        ),
        "variables": ["cucm_model", "extension", "helpdesk"],
    },
    "forwarding_simplified": {
        "title": "Your Call Forwarding Has Been Reviewed",
        "priority": 4,
        "template": (
            "Your call forwarding rules have been reviewed and simplified for the new "
            "system. CUCM supported some forwarding configurations that Webex Calling "
            "handles differently. Your IT team has reviewed your specific setup and will "
            "configure the closest equivalent. If you had complex forwarding chains (e.g., "
            "forward to a queue that forwards to voicemail after hours), please verify "
            "your forwarding settings after migration using the Webex App or your desk "
            "phone\u2019s settings menu."
            "\n\n"
            "<strong>What you need to do:</strong> After migration, dial a test call to "
            "verify your forwarding works as expected. If anything needs adjustment, "
            "contact {helpdesk}."
        ),
        "variables": ["helpdesk"],
    },
    "voicemail_rerecord": {
        "title": "Re-record Your Voicemail Greeting",
        "priority": 5,
        "template": (
            "Your voicemail account will be migrated to Webex Calling voicemail. Your "
            "voicemail-to-email settings will be preserved. However, <strong>your personal "
            "voicemail greeting cannot be migrated automatically</strong> \u2014 the old "
            "greeting is stored in Cisco Unity Connection in a format that doesn\u2019t "
            "transfer to Webex."
            "\n\n"
            "<strong>What you need to do:</strong> After migration, record a new voicemail "
            "greeting. You can do this by:"
            "\n<ol>"
            "\n<li>Dialing your voicemail access number and following the prompts</li>"
            "\n<li>Using the Webex App: Settings &gt; Calling &gt; Voicemail &gt; Greeting</li>"
            "\n</ol>"
            "\nUntil you record a new greeting, callers will hear the default system greeting."
        ),
        "variables": [],
    },
    "layout_changes": {
        "title": "Your Phone\u2019s Button Layout May Change",
        "priority": 6,
        "template": (
            "Your phone\u2019s button layout (speed dials and BLF busy lamp indicators) "
            "may look different after migration. Most of your speed dials and BLF keys "
            "will transfer automatically, but some button types that were available in "
            "CUCM don\u2019t have a direct equivalent in Webex Calling."
            "\n\n"
            "<strong>What you need to do:</strong> After migration, review your phone\u2019s "
            "line keys and speed dials. You can reconfigure them using:"
            "\n<ul>"
            "\n<li>The Webex App: Settings &gt; Calling &gt; Line Key Configuration</li>"
            "\n<li>Your phone\u2019s on-screen menu (varies by model)</li>"
            "\n<li>Contact {helpdesk} for assistance</li>"
            "\n</ul>"
            "\nYour IT team will provide a reference of your current button layout if needed."
        ),
        "variables": ["helpdesk"],
    },
    "exec_assistant": {
        "title": "Executive/Assistant Call Handling",
        "priority": 7,
        "template": (
            "Your executive/assistant call handling will continue to work after migration. "
            "Webex Calling supports executive/assistant call filtering, with your assistant "
            "able to answer, screen, and transfer calls on your behalf. The configuration "
            "will be migrated automatically."
            "\n\n"
            "<strong>Note:</strong> If you currently use the Cisco Unified Attendant "
            "Console, your assistant may need to use the Webex Receptionist Client "
            "instead. Your IT team will provide training before migration day."
        ),
        "variables": [],
    },
}

INTRO_TEMPLATE: str = (
    "<strong>Your phone system is being upgraded</strong>"
    "\n\n"
    "{brand} is upgrading from Cisco Unified Communications Manager (CUCM) to "
    "Webex Calling. This upgrade brings a modern, cloud-managed phone system with "
    "the same reliability you expect, plus new features like the Webex App for "
    "calling, messaging, and meetings from any device."
    "\n\n"
    "<strong>Migration date:</strong> {migration_date}"
    "\n\n"
    "Below is a summary of what this means for you specifically, based on your "
    "current phone and settings."
)

TIMELINE_TEMPLATE: str = (
    "<strong>What to expect on {migration_date}:</strong>"
    "\n<ul>"
    "\n<li><strong>Before the migration window:</strong> Everything works normally. "
    "No action needed.</li>"
    "\n<li><strong>During the migration window:</strong> Your phone may restart once. "
    "Calls will not be available for 5\u201315 minutes during this restart.</li>"
    "\n<li><strong>After migration:</strong> Your phone (or Webex App) will be "
    "operational on the new system. Your extension and phone number are unchanged. "
    "Test a call to verify.</li>"
    "\n</ul>"
    "\nIf you experience any issues after migration, contact {helpdesk}."
)

FOOTER_TEMPLATE: str = (
    "<strong>Questions or issues?</strong>"
    "\n\n"
    "Contact {helpdesk} for assistance with any migration-related questions."
    "\n\n"
    "Additional resources:"
    "\n<ul>"
    '\n<li>Webex App quick start guide: <a href="https://help.webex.com">'
    "help.webex.com/getting-started</a></li>"
    '\n<li>Voicemail setup: <a href="https://help.webex.com">'
    "help.webex.com/voicemail</a></li>"
    "\n</ul>"
    "\n<em>Prepared by {prepared_by} on behalf of {brand}.</em>"
)

AUDIENCE_FILTERS: dict[str, set[str]] = {
    "all": set(),
    "phone-upgrade": {"phone_upgrade", "device_replacement"},
    "webex-app": {"webex_app_transition"},
    "general": set(),
}
