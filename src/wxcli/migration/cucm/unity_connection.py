"""CUPI REST client for Cisco Unity Connection.

Retrieves per-user voicemail settings that are not available via CUCM AXL.

Sources:
- 02b-cucm-extraction.md §2.6 (CUPI connection setup, endpoints, field mapping)
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class UnityConnectionError(Exception):
    """Raised when the Unity Connection client cannot connect or authenticate."""


class UnityConnectionClient:
    """CUPI REST client for Unity Connection per-user voicemail settings.

    (from 02b §2.6: CUPI connection setup)

    Args:
        host: Unity Connection hostname or IP.
        username: Admin username.
        password: Admin password.
        verify_ssl: Whether to verify SSL certificates (default False).
        timeout: Request timeout in seconds (default 30).
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        timeout: int = 30,
    ) -> None:
        self.base_url = f"https://{host}/vmrest"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = verify_ssl
        self.session.timeout = timeout
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # User lookup
    # ------------------------------------------------------------------

    def get_user_by_alias(self, alias: str) -> dict[str, Any] | None:
        """Look up UC user by CUCM userid/alias.

        (from 02b §2.6: CUPI user lookup)

        """
        try:
            resp = self.session.get(
                f"{self.base_url}/users",
                params={"query": f"(alias is {alias})"},
            )
            if resp.status_code == 200:
                data = resp.json()
                users = data.get("User", [])
                if isinstance(users, dict):
                    users = [users]
                return users[0] if users else None
        except Exception as exc:
            logger.warning("CUPI user lookup failed for %s: %s", alias, exc)
        return None

    # ------------------------------------------------------------------
    # Per-user voicemail settings
    # ------------------------------------------------------------------

    def get_notification_devices(self, object_id: str) -> list[dict[str, Any]]:
        """Get notification devices for a user.

        (from 02b §2.6: notifications.enabled, notifications.destination)

        """
        return self._get_list(
            f"/users/{object_id}/notificationdevices",
            "NotificationDevice",
        )

    def get_call_handler(self, handler_id: str) -> dict[str, Any] | None:
        """Get call handler (greeting/transfer rules).

        (from 02b §2.6: sendAllCalls, sendBusyCalls, sendUnansweredCalls)

        """
        return self._get(f"/handlers/callhandlers/{handler_id}")

    def get_message_store_settings(
        self, object_id: str
    ) -> dict[str, Any] | None:
        """Get message store settings for a user.

        (from 02b §2.6: storageType, mwiEnabled, externalEmail)

        """
        return self._get(f"/users/{object_id}/messagestoresettings")

    def get_transfer_rule_zero(self, object_id: str) -> dict[str, Any] | None:
        """Get transfer-to-zero rule for a user.

        (from 02b §2.6: transferToNumber settings)

        """
        return self._get(f"/users/{object_id}/transferrules/transferzero")

    def get_fax_settings(self, object_id: str) -> dict[str, Any] | None:
        """Get fax server settings for a user.

        (from 02b §2.6: fax message settings)

        """
        return self._get(f"/users/{object_id}/faxserversettings")

    # ------------------------------------------------------------------
    # Aggregate extraction
    # ------------------------------------------------------------------

    def extract_user_vm_settings(
        self, cucm_userid: str
    ) -> dict[str, Any] | None:
        """Extract all voicemail settings for one user.

        Looks up the user by alias, then fetches all per-user settings.
        Returns a consolidated dict, or None if user not found in UC.

        (from 02b §2.6: extraction flow steps 3-4)
        """
        uc_user = self.get_user_by_alias(cucm_userid)
        if uc_user is None:
            return None

        object_id = uc_user.get("ObjectId", "")
        call_handler_id = uc_user.get("CallhandlerObjectId", "")

        result: dict[str, Any] = {
            "uc_object_id": object_id,
            "vm_enabled": True,
            "call_handler_id": call_handler_id,
        }

        # Notification devices
        notif_devices = self.get_notification_devices(object_id)
        result["notification_enabled"] = any(
            d.get("Enabled", False) for d in notif_devices
        )
        email_devices = [
            d for d in notif_devices if d.get("SmtpAddress")
        ]
        result["notification_destination"] = (
            email_devices[0].get("SmtpAddress") if email_devices else None
        )

        # Call handler transfer rules
        if call_handler_id:
            handler = self.get_call_handler(call_handler_id)
            if handler:
                result["send_all_calls"] = _to_bool(
                    handler.get("PlayTransferPrompt")
                )
                result["send_busy_calls"] = _to_bool(
                    handler.get("SendBusyCalls")
                )
                result["send_unanswered_calls"] = _to_bool(
                    handler.get("SendUnansweredCalls")
                )
                result["unanswered_rings"] = handler.get("RingsToWait")
                result["busy_greeting_type"] = (
                    "CUSTOM"
                    if handler.get("PlayPostGreetingRecording")
                    else "DEFAULT"
                )

        # Message store settings
        msg_store = self.get_message_store_settings(object_id)
        if msg_store:
            result["storage_type"] = msg_store.get("StorageType", "INTERNAL")
            result["mwi_enabled"] = _to_bool(msg_store.get("MwiEnabled"))
            result["external_email"] = msg_store.get("ExternalEmail")
            result["email_copy_enabled"] = _to_bool(
                msg_store.get("SendCopyToEmail")
            )

        # Transfer to zero
        t_zero = self.get_transfer_rule_zero(object_id)
        if t_zero:
            result["transfer_to_zero_enabled"] = _to_bool(
                t_zero.get("Enabled")
            )
            result["transfer_to_zero_destination"] = t_zero.get(
                "Extension"
            ) or t_zero.get("PhoneNumber")

        # Fax settings
        fax = self.get_fax_settings(object_id)
        if fax:
            result["fax_enabled"] = _to_bool(fax.get("Enabled"))
            result["fax_number"] = fax.get("FaxNumber")

        return result

    # ------------------------------------------------------------------
    # Shared/group mailbox discovery
    # ------------------------------------------------------------------

    def extract_shared_mailboxes(self) -> list[dict[str, Any]]:
        """Extract Unity Connection shared/group call handlers.

        Queries /vmrest/handlers/callhandlers and filters to non-primary
        handlers (IsPrimary=false). Primary handlers are per-user mailboxes
        already covered by extract_user_vm_settings. Non-primary handlers
        are shared/group mailboxes (sales@, support@, etc.).

        Returns an empty list on error or when CUPI is unreachable —
        callers should treat absence as "Unity Connection not available"
        rather than "no shared mailboxes exist".
        """
        try:
            resp = self.session.get(
                f"{self.base_url}/handlers/callhandlers",
            )
        except Exception as exc:
            logger.warning("CUPI shared-mailbox query failed: %s", exc)
            return []

        if resp.status_code != 200:
            logger.warning(
                "CUPI shared-mailbox query returned %s", resp.status_code
            )
            return []

        data = resp.json() if callable(getattr(resp, "json", None)) else {}
        handlers = data.get("Callhandler", [])
        # CUPI returns a bare dict when exactly one handler exists.
        if isinstance(handlers, dict):
            handlers = [handlers]

        # Filter out primary (per-user) handlers — we only want shared ones.
        shared: list[dict[str, Any]] = []
        for h in handlers:
            if not isinstance(h, dict):
                continue
            is_primary = str(h.get("IsPrimary", "false")).lower() == "true"
            if is_primary:
                continue
            shared.append(h)

        logger.info(
            "Extracted %d Unity Connection shared mailbox(es)", len(shared)
        )
        return shared

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> dict[str, Any] | None:
        """GET a single CUPI resource."""
        try:
            resp = self.session.get(f"{self.base_url}{path}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.warning("CUPI GET %s failed: %s", path, exc)
        return None

    def _get_list(
        self, path: str, key: str
    ) -> list[dict[str, Any]]:
        """GET a CUPI collection resource."""
        data = self._get(path)
        if data is None:
            return []
        items = data.get(key, [])
        if isinstance(items, dict):
            items = [items]
        return items


def _to_bool(value: Any) -> bool | None:
    """Convert CUPI response values to bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)
