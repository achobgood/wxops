"""AXL SOAP client via zeep.

Provides the AXL connection, version detection, and pagination helper
that all extractors use.

Sources:
- cucm-wxc-migration.md lines 301-309 (WSDL, auth, pagination)
- 02b-cucm-extraction.md §1 (connection setup, pagination strategy)
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.helpers import serialize_object
from zeep.transports import Transport

logger = logging.getLogger(__name__)


class AXLConnectionError(Exception):
    """Raised when the AXL connection cannot be established."""


class AXLConnection:
    """AXL SOAP client using zeep.

    (from 02b §1: connection setup)

    Args:
        host: CUCM hostname or IP address.
        username: AXL admin username.
        password: AXL admin password.
        version: CUCM AXL schema version (default "14.0").
        verify_ssl: Whether to verify SSL certificates (default False —
            CUCM typically uses self-signed certs).
        timeout: SOAP request timeout in seconds (default 30).
        wsdl_path: Path to a local AXL WSDL file. If provided, zeep loads
            the schema locally instead of fetching from the CUCM server.
            Download from CUCM Admin > Application > Plugins > "Cisco AXL Toolkit".
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        version: str = "14.0",
        verify_ssl: bool = False,
        timeout: int = 30,
        wsdl_path: str | None = None,
    ) -> None:
        self.host = host
        self.version = version

        session = Session()
        session.auth = HTTPBasicAuth(username, password)
        session.verify = verify_ssl
        transport = Transport(session=session, timeout=timeout)

        # Use local WSDL if provided, otherwise fetch from CUCM
        if wsdl_path:
            self.wsdl_url = wsdl_path
        else:
            self.wsdl_url = f"https://{host}:8443/axl/AXLAPIService?wsdl"

        # strict=False: CUCM responses may contain elements not in the WSDL
        # (e.g. isAnonymous in getSipTrunk on CUCM 15.0). Without this,
        # zeep raises XMLSyntaxError for any unexpected element.
        settings = Settings(strict=False, xml_huge_tree=True)

        try:
            self.client = Client(
                self.wsdl_url, transport=transport, settings=settings,
            )
        except Exception as exc:
            raise AXLConnectionError(
                f"Failed to load WSDL from {self.wsdl_url}: {exc}"
            ) from exc

        # When using a local WSDL, zeep needs the service address pointed at the real CUCM
        service_url = f"https://{host}:8443/axl/"
        self.service = self.client.create_service(
            "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
            service_url,
        )

    def get_version(self) -> str:
        """Detect CUCM version via getCCMVersion().

        (from cucm-wxc-migration.md line 309)
        """
        response = self._serialize(self.service.getCCMVersion())
        version_info = response.get("return", {})
        if isinstance(version_info, dict):
            comp = version_info.get("componentVersion", {})
            if isinstance(comp, dict):
                return comp.get("version", self.version)
            return str(comp) if comp else self.version
        return self.version

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------

    def paginated_list(
        self,
        method_name: str,
        search_criteria: dict[str, str],
        returned_tags: dict[str, str],
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        """Generic paginated AXL list operation.

        (from 02b §1: pagination strategy)

        Args:
            method_name: AXL method (e.g. 'listEndUser').
            search_criteria: Filter dict (e.g. {'firstName': '%'} for all).
            returned_tags: Fields to return (AXL only returns requested fields).
            page_size: Rows per page (default 200, AXL max for most methods).
        """
        all_results: list[dict[str, Any]] = []
        skip = 0
        while True:
            raw = getattr(self.service, method_name)(
                searchCriteria=search_criteria,
                returnedTags=returned_tags,
                first=str(page_size),
                skip=str(skip),
            )
            response = self._serialize(raw)
            batch = self._extract_rows(response)
            if not batch:
                break
            all_results.extend(batch)
            if len(batch) < page_size:
                break  # Last page
            skip += page_size
        return all_results

    def get_detail(
        self, method_name: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Single-object get operation (e.g. getPhone by name or UUID).

        Returns the inner result dict, or None on error.
        """
        try:
            raw = getattr(self.service, method_name)(**kwargs)
            response = self._serialize(raw)
            ret = response.get("return", {})
            # get responses wrap the object under a single key
            if isinstance(ret, dict):
                for key, value in ret.items():
                    if key != "_value_1" and value is not None:
                        return self._serialize(value)
            return ret
        except Exception as exc:
            logger.warning("[%s] %s", method_name, exc)
            return None

    def execute_sql(self, query: str) -> list[dict[str, Any]]:
        """Run an executeSQLQuery against CUCM's informix database.

        (from 02b §5: performance considerations for large clusters)

        Returns list of row dicts. Each row is a dict mapping column name → value.
        """
        raw = self.service.executeSQLQuery(sql=query)
        response = self._serialize(raw)
        rows = self._extract_rows(response)
        # SQL rows may come back as lxml Elements (when using WSDL + zeep).
        # Convert each row to a plain dict.
        result: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                result.append(row)
            elif isinstance(row, list):
                # List of lxml Elements: each has .tag and .text
                row_dict: dict[str, Any] = {}
                for elem in row:
                    tag = getattr(elem, "tag", None)
                    if tag:
                        # Strip namespace if present
                        tag = tag.split("}")[-1] if "}" in tag else tag
                    text = getattr(elem, "text", None)
                    if tag:
                        row_dict[tag] = text
                result.append(row_dict)
            elif hasattr(row, "__dict__"):
                result.append(dict(row.__dict__))
            else:
                result.append({"_raw": str(row)})
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(obj: Any) -> dict[str, Any]:
        """Convert zeep typed objects to plain Python dicts.

        Zeep with a local WSDL returns typed objects (e.g. GetPhoneRes)
        instead of plain dicts. ``serialize_object`` converts them to
        OrderedDicts recursively. We convert to regular dicts for consistency.
        """
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        serialized = serialize_object(obj, dict)
        if isinstance(serialized, dict):
            return serialized
        return {"_raw": serialized}

    @staticmethod
    def _extract_rows(response: Any) -> list[dict[str, Any]]:
        """Extract the row list from an AXL list/SQL response.

        AXL responses: {'return': {'{objectType}': [rows...]}}
        Zeep converts this to a dict with one key matching the object type.
        (from 02b §3: base extractor _extract_rows)
        """
        if response is None:
            return []
        # Extract the 'return' value from the response.
        # Zeep response objects support dict-like access.
        ret: Any = None
        if hasattr(response, "get"):
            ret = response.get("return")
        elif hasattr(response, "__getitem__"):
            try:
                ret = response["return"]
            except (KeyError, TypeError):
                return []
        else:
            return []
        if not ret:
            return []
        if isinstance(ret, dict):
            for key, value in ret.items():
                if key != "_value_1" and value is not None:
                    if isinstance(value, list):
                        return value
                    return [value]
        return []
