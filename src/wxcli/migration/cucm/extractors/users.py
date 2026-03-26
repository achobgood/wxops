"""Users extractor — End Users.

Extracts CUCM End Users with associated device references, directory info,
and voicemail associations. Feeds user_mapper (03b §2), css_mapper
(cross-ref #18), and voicemail_mapper (cross-ref #26).

Sources:
- 02b-cucm-extraction.md §2.2 (users extractor spec)
- 03b-transform-mappers.md §2 (user_mapper field mapping)
- 02-normalization-architecture.md cross-ref #3, #4, #18, #26
"""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value, to_list

logger = logging.getLogger(__name__)
console = Console()

# --- returnedTags constants (from 02b §2.2) ---

USER_LIST_RETURNED_TAGS = {
    'firstName': '',
    'lastName': '',
    'userid': '',
    'mailid': '',
}

USER_GET_RETURNED_TAGS = {
    'firstName': '',                     # Maps to Webex firstName
    'lastName': '',                      # Maps to Webex lastName
    'mailid': '',                        # Maps to Webex emails[] primary
    'userid': '',                        # Fallback for emails[] if mailid empty
    'telephoneNumber': '',               # User's primary phone number
    'department': '',                    # Maps to Webex department
    'title': '',                         # Maps to Webex title
    'manager': '',                       # Maps to Webex manager/managerId
    'directoryUri': '',                  # Informational — "Webex auto-assigns SIP address"
    'userLocale': '',                    # Informational — "Not a People API field"
    'selfService': '',                   # Voicemail pilot — "Mapped by voicemail_mapper"
    'associatedDevices': '',             # Cross-ref #3: user_has_device
    'enableCti': '',                     # CTI-enabled flag
    'primaryExtension': '',              # Cross-ref #4: user_has_primary_dn
    'callingSearchSpaceName': '',        # Cross-ref #18: user_has_css
    'voiceMailProfile': '',              # Cross-ref #26: user_has_voicemail_profile
}


class UserExtractor(BaseExtractor):
    """Extract CUCM End Users.

    Two-step extraction:
    1. listEndUser discovers all user PKIDs (summary fields only)
    2. getEndUser per user retrieves the full field set including
       associatedDevices, primaryExtension, CSS, and voicemail profile

    Results stored in self.results['users'].

    (from 02b §2.2)
    """

    name = "users"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {
            'users': [],
        }

    def extract(self) -> ExtractionResult:
        """Discover users via AXL listEndUser, then get full detail.

        Falls back to executeSQLQuery if listEndUser is blocked (EPR error).
        This happens on cloud-connected CUCMs and some LDAP-synced deployments.
        """
        try:
            return self._extract_via_axl()
        except Exception as exc:
            exc_str = str(exc)
            # EPR errors: cloud-connected CUCM or service not fully activated
            # AttributeError: WSDL doesn't define EndUser operations (thin AXL)
            # Fault: AXL service rejects the method
            if any(s in exc_str for s in ("EPR", "Operation not found", "has no operation")):
                logger.warning(
                    "listEndUser AXL unavailable (%s) — falling back to SQL",
                    exc,
                )
                return self._extract_via_sql()
            raise

    def _extract_via_axl(self) -> ExtractionResult:
        """Standard AXL extraction: listEndUser → getEndUser."""
        errors: list[str] = []
        failed = 0

        summary_list = self.paginated_list(
            "listEndUser",
            search_criteria={"firstName": "%"},
            returned_tags=USER_LIST_RETURNED_TAGS,
        )
        total = len(summary_list)
        logger.info("Found %d end users via listEndUser", total)

        for i, user_summary in enumerate(summary_list, 1):
            if i % 200 == 0:
                console.print(f"    users: {i}/{total}...")
            userid = user_summary.get("userid", "<unknown>")
            try:
                raw = self.get_detail("getEndUser", userid=userid)
                if raw is None:
                    failed += 1
                    errors.append(f"getEndUser returned None for '{userid}'")
                    continue
                raw["associatedDevices"] = to_list(
                    raw.get("associatedDevices"), "device"
                )
                self.results["users"].append(raw)
            except Exception as exc:
                failed += 1
                errors.append(f"getEndUser failed for '{userid}': {exc}")

        return ExtractionResult(
            extractor=self.name, total=total, failed=failed, errors=errors,
        )

    def _extract_via_sql(self) -> ExtractionResult:
        """SQL fallback when AXL EndUser operations are blocked.

        Uses executeSQLQuery to read the enduser table directly. Joins to
        enduserdevicemap + device for associatedDevices, and numplan for
        primaryExtension. Produces dicts matching the AXL getEndUser shape
        so downstream normalizers work identically.

        Verified against live CUCM 15.0 (2026-03-23): executeSQLQuery works
        even when listEndUser/getEndUser return EPR errors.
        """
        errors: list[str] = []

        # Step 1: Get all active end users (exclude system/token users)
        user_rows = self.conn.execute_sql(
            "SELECT eu.pkid, eu.userid, eu.firstname, eu.lastname, "
            "eu.mailid, eu.telephonenumber, eu.department, eu.title, "
            "eu.manager, eu.directoryuri, eu.allowcticontrolflag "
            "FROM enduser eu "
            "WHERE eu.status = 1 AND eu.userid NOT LIKE 'Token_User_%'"
        )
        logger.info("Found %d end users via SQL", len(user_rows))

        # Step 2: Get device associations (user → phone name)
        # Try enduserdevicemap first (explicit associations), then fall back
        # to device.fkenduser (ownerUserName). Both represent user→device links
        # but enduserdevicemap is only populated when devices are added to a
        # user's "Controlled Devices" list via GUI/updateEndUser.
        device_rows = self.conn.execute_sql(
            "SELECT eu.userid, d.name AS device_name "
            "FROM enduser eu "
            "JOIN device d ON d.fkenduser = eu.pkid "
            "WHERE eu.status = 1 "
            "UNION "
            "SELECT eu.userid, d.name AS device_name "
            "FROM enduser eu "
            "JOIN enduserdevicemap edm ON eu.pkid = edm.fkenduser "
            "JOIN device d ON edm.fkdevice = d.pkid "
            "WHERE eu.status = 1"
        )
        user_devices: dict[str, list[str]] = {}
        for row in device_rows:
            uid = row.get("userid", "")
            dname = row.get("device_name", "")
            if uid and dname:
                user_devices.setdefault(uid, []).append(dname)

        # Step 3: Get primary extensions (line 1 of first physical phone)
        # Uses device.fkenduser (ownerUserName) — same as step 2.
        # Prefers physical phones (SEP*) over softphones (CSF*) for primary DN.
        primary_dn_rows = self.conn.execute_sql(
            "SELECT eu.userid, np.dnorpattern AS pattern, rp.name AS partition "
            "FROM enduser eu "
            "JOIN device d ON d.fkenduser = eu.pkid "
            "JOIN devicenumplanmap dnmap ON d.pkid = dnmap.fkdevice "
            "JOIN numplan np ON dnmap.fknumplan = np.pkid "
            "LEFT JOIN routepartition rp ON np.fkroutepartition = rp.pkid "
            "WHERE eu.status = 1 AND dnmap.numplanindex = 1 "
            "AND d.name NOT LIKE 'CSF%'"
        )
        user_primary_dn: dict[str, dict[str, str | None]] = {}
        for row in primary_dn_rows:
            uid = row.get("userid", "")
            if uid and uid not in user_primary_dn:
                user_primary_dn[uid] = {
                    "pattern": row.get("pattern"),
                    "routePartitionName": row.get("partition"),
                }

        # Step 4: Build user dicts matching AXL getEndUser shape
        for row in user_rows:
            userid = row.get("userid", "")
            user_dict: dict[str, Any] = {
                "pkid": row.get("pkid"),
                "firstName": row.get("firstname"),
                "lastName": row.get("lastname"),
                "mailid": row.get("mailid"),
                "userid": userid,
                "telephoneNumber": row.get("telephonenumber"),
                "department": row.get("department"),
                "title": row.get("title"),
                "manager": row.get("manager"),
                "directoryUri": row.get("directoryuri"),
                "enableCti": row.get("allowcticontrolflag"),
                "associatedDevices": user_devices.get(userid, []),
                "primaryExtension": user_primary_dn.get(userid),
                # These require AXL EndUser object — not available via SQL
                "callingSearchSpaceName": None,
                "voiceMailProfile": None,
                "selfService": None,
                "userLocale": None,
                "_extracted_via": "sql",
            }
            self.results["users"].append(user_dict)

        logger.info(
            "End users via SQL: %d extracted, %d with devices, %d with primary DN",
            len(user_rows),
            sum(1 for u in self.results["users"] if u["associatedDevices"]),
            sum(1 for u in self.results["users"] if u["primaryExtension"]),
        )

        return ExtractionResult(
            extractor=self.name,
            total=len(user_rows),
            failed=0,
            errors=errors,
        )
