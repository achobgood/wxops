"""E.164 normalization for CUCM Directory Numbers.

Classifies DNs as EXTENSION / NATIONAL / E164 / AMBIGUOUS and normalizes
to E.164 format using Google's phonenumbers library (libphonenumber).

Used by line_mapper during normalization pass 2 to produce CanonicalLine
objects with both bare extension and E.164 phone number fields.

(from 02-normalization-architecture.md, E.164 normalization section)
(from 03b-transform-mappers.md, line_mapper E.164 normalization algorithm)
"""

from __future__ import annotations

from dataclasses import dataclass

import phonenumbers


@dataclass
class E164Result:
    """Result of E.164 normalization for a single DN.

    Fields match what line_mapper in 03b-transform-mappers.md expects:
    - e164: normalized E.164 string (e.g., "+14155551234") or None
    - extension: bare extension digits (e.g., "1001") or None
    - raw: the original input DN string
    - classification: one of EXTENSION, NATIONAL, E164, AMBIGUOUS
    """

    e164: str | None
    extension: str | None
    raw: str
    classification: str  # EXTENSION | NATIONAL | E164 | AMBIGUOUS


# Maximum digits for a DN to be classified as an extension.
# (from 02-normalization-architecture.md: "if len(stripped) <= 6")
# Extended to handle CUCM extensions up to 10 digits, but phonenumbers
# is tried first — only numbers that fail phonenumbers parsing fall back
# to extension classification.
_MAX_EXTENSION_DIGITS = 6


def apply_prefix_rules(dn: str, rules: list[dict]) -> str:
    """Strip a site-specific prefix from a DN.

    Rules are applied in order; the first matching rule is used.
    Each rule is a dict with "prefix" (str) and optionally "description".

    (from 02-normalization-architecture.md: "Step 1: Strip site prefix")
    (from 03b-transform-mappers.md, line_mapper field table: site prefix rules)
    """
    for rule in rules:
        prefix = rule["prefix"]
        if dn.startswith(prefix) and len(dn) > len(prefix):
            return dn[len(prefix) :]
    return dn


def normalize_dn(
    dn: str,
    country_code: str,
    site_prefix_rules: list[dict],
) -> E164Result:
    """Normalize a CUCM DN to E.164 using libphonenumber.

    (from 02-normalization-architecture.md, normalize_dn function)
    (from 03b-transform-mappers.md, line_mapper E.164 normalization algorithm)

    Args:
        dn: Raw directory number string from CUCM.
        country_code: ISO 3166-1 alpha-2 code (e.g., "US", "GB", "DE").
            Comes from the DN's resolved location.
        site_prefix_rules: List of prefix stripping rules from migration config.

    Returns:
        E164Result with classification and normalized values.
        Invalid numbers produce AMBIGUOUS, never exceptions.
    """
    # Guard: empty or whitespace-only DN
    if not dn or not dn.strip():
        return E164Result(
            e164=None,
            extension=None,
            raw=dn or "",
            classification="AMBIGUOUS",
        )

    # Guard: non-digit characters that aren't '+' indicate special codes
    if not dn[0].isdigit() and dn[0] != "+":
        return E164Result(
            e164=None,
            extension=None,
            raw=dn,
            classification="AMBIGUOUS",
        )

    # Step 1: Strip site prefix (from 02-normalization-architecture.md)
    stripped = apply_prefix_rules(dn, site_prefix_rules)

    # Step 2: Try to parse as a phone number using phonenumbers
    # (from 02-normalization-architecture.md: phonenumbers library usage)
    try:
        parsed = phonenumbers.parse(stripped, country_code)
        if phonenumbers.is_valid_number(parsed):
            e164 = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            # Classify: already had '+' → E164, otherwise NATIONAL.
            # Design doc (02-normalization-architecture.md:162) uses
            # len(stripped) <= 10 heuristic; we use '+' prefix detection
            # instead, which is more accurate for 11-digit national numbers
            # like "14155551234" that shouldn't be classified as E164.
            if stripped.startswith("+"):
                classification = "E164"
            else:
                classification = "NATIONAL"
            return E164Result(
                e164=e164,
                extension=None,
                raw=dn,
                classification=classification,
            )
    except phonenumbers.NumberParseException:
        pass

    # Step 3: Short number = extension
    # (from 02-normalization-architecture.md: "if len(stripped) <= 6")
    digits_only = stripped.replace("+", "")
    if digits_only.isdigit() and len(digits_only) <= _MAX_EXTENSION_DIGITS:
        return E164Result(
            e164=None,
            extension=stripped,
            raw=dn,
            classification="EXTENSION",
        )

    # Step 4: Can't classify
    return E164Result(
        e164=None,
        extension=None,
        raw=dn,
        classification="AMBIGUOUS",
    )
