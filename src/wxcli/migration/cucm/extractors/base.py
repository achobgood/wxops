"""Base extractor class and ExtractionResult.

All AXL extractors (§2.1-2.6 of 02b) inherit from BaseExtractor.

Sources:
- 02b-cucm-extraction.md §3 (base extractor class, ExtractionResult)
- 02b-cucm-extraction.md §1 (error handling strategy)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Summary of one extractor's run.

    (from 02b §3)
    """

    extractor: str
    total: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return self.total - self.failed


class ExtractionError(Exception):
    """Raised when an extractor encounters an unrecoverable error.

    (from 02b §1: error handling)
    """

    def __init__(self, extractor: str, method: str, message: str) -> None:
        self.extractor = extractor
        self.method = method
        super().__init__(f"[{extractor}] {method}: {message}")


class BaseExtractor(ABC):
    """Base class for all CUCM AXL extractors.

    (from 02b §3)
    """

    name: str = ""
    page_size: int = 200  # Default AXL page size (from cucm-wxc-migration.md line 307)

    def __init__(self, connection: AXLConnection) -> None:
        self.conn = connection

    @abstractmethod
    def extract(self) -> ExtractionResult:
        """Run extraction. Returns count of objects extracted and any errors."""
        ...

    def paginated_list(
        self,
        method_name: str,
        search_criteria: dict[str, str],
        returned_tags: dict[str, str],
        page_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generic paginated AXL list operation.

        Uses first/skip pagination (from cucm-wxc-migration.md line 307).
        (from 02b §3)
        """
        effective_page_size = page_size or self.page_size
        return self.conn.paginated_list(
            method_name, search_criteria, returned_tags, effective_page_size
        )

    def get_detail(self, method_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Single-object get operation (e.g. getPhone by name or UUID).

        (from 02b §3)
        """
        return self.conn.get_detail(method_name, **kwargs)
