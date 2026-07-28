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
    #: Subset of ``errors`` meaning "this schema cannot answer that" rather
    #: than "the query failed". Every entry is also in ``errors``, so the
    #: human-facing consumers that predate this field are unchanged.
    unsupported: list[str] = field(default_factory=list)
    #: AXL method name -> returnedTags the schema rejected, which the
    #: connection dropped so the rest of the call could succeed. A non-empty
    #: entry means these objects were collected WITHOUT those fields.
    dropped_tags: dict[str, list[str]] = field(default_factory=dict)

    @property
    def success_count(self) -> int:
        return self.total - self.failed

    def record_unsupported(self, note: str) -> None:
        """Record work this CUCM/AXL schema does not support.

        Appends to ``errors`` (what humans read) and to ``unsupported`` (what
        ``status`` classifies on). Deliberately does not touch ``failed`` —
        work that was never possible is not a failed attempt.
        """
        self.errors.append(note)
        self.unsupported.append(note)

    @property
    def status(self) -> str:
        """``ok`` | ``partial`` | ``failed`` | ``unsupported``.

        A ``total`` of 0 has four possible meanings and they are not
        interchangeable: the cluster genuinely has none of these (``ok``), no
        call succeeded (``failed``), or nothing was askable on this schema
        (``unsupported``). ``partial`` means data arrived but something was
        lost — a failed sub-query, a skipped one, or a dropped field.
        """
        skipped = set(self.unsupported)
        hard_errors = [e for e in self.errors if e not in skipped]
        if hard_errors or self.failed:
            return "failed" if self.total == 0 else "partial"
        if self.unsupported:
            return "unsupported" if self.total == 0 else "partial"
        if self.dropped_tags:
            return "partial"
        return "ok"

    def to_status(self) -> dict[str, Any]:
        """Machine-readable collection status, for persisting into raw_data.json."""
        return {
            "name": self.extractor,
            "total": self.total,
            "failed": self.failed,
            "status": self.status,
            "errors": list(self.errors),
            "unsupported": list(self.unsupported),
            "dropped_tags": {m: list(t) for m, t in self.dropped_tags.items()},
        }


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
