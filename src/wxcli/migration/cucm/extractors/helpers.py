"""Zeep dict navigation helpers for AXL response parsing.

AXL reference fields consistently use the ``{'_value_1': value, 'uuid': uuid}``
pattern. List fields may be a bare dict (single item) or a list.

Sources:
- 02b-cucm-extraction.md §3 (zeep dict navigation helpers)
- 02-normalization-architecture.md pass 1 example (reference field pattern)
"""

from __future__ import annotations

from typing import Any


def ref_value(field: dict[str, Any] | str | None) -> str | None:
    """Extract the display value from a zeep reference field.

    Zeep reference pattern: ``{'_value_1': 'DP-HQ', 'uuid': '{...}'}``
    Returns ``'DP-HQ'``. Also handles plain strings and None.
    (from 02b §3)
    """
    if field is None:
        return None
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        return field.get("_value_1")
    return None


def ref_uuid(field: dict[str, Any] | None) -> str | None:
    """Extract the UUID from a zeep reference field.

    (from 02b §3)
    """
    if isinstance(field, dict):
        return field.get("uuid")
    return None


def to_list(field: dict[str, Any] | list[Any] | None, key: str) -> list[Any]:
    """Normalize a zeep list field to a Python list.

    Zeep list pattern:
        ``{'line': [item1, item2, ...]}``  — multiple items
        ``{'line': item1}``                — single item (not wrapped in list)
        ``None``                           — empty

    (from 02b §3)
    """
    if field is None:
        return []
    if isinstance(field, dict):
        inner = field.get(key)
        if inner is None:
            return []
        if isinstance(inner, list):
            return inner
        return [inner]
    if isinstance(field, list):
        return field
    return []


def str_to_bool(value: str | None) -> bool | None:
    """Convert AXL string boolean to Python bool.

    (from 02b §3)
    """
    if value is None:
        return None
    return str(value).lower() == "true"
