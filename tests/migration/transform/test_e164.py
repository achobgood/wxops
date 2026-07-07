"""Tests for E.164 normalization module.

Test cases derived from 02-normalization-architecture.md and 03b-transform-mappers.md.
TDD: these tests are written BEFORE the implementation.
"""

import pytest

from wxcli.migration.transform.e164 import (
    E164Result,
    apply_prefix_rules,
    normalize_dn,
)


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestShortExtension:
    """Short numbers (2-6 digits) → EXTENSION."""

    def test_4_digit(self):
        result = normalize_dn("1001", country_code="US", site_prefix_rules=[])
        assert result.classification == "EXTENSION"
        assert result.extension == "1001"
        assert result.e164 is None

    def test_3_digit(self):
        result = normalize_dn("100", country_code="US", site_prefix_rules=[])
        assert result.classification == "EXTENSION"
        assert result.extension == "100"

    def test_2_digit(self):
        result = normalize_dn("10", country_code="US", site_prefix_rules=[])
        assert result.classification == "EXTENSION"
        assert result.extension == "10"


class TestNational10Digit:
    """10-digit US number → NATIONAL, gets +1 prefix."""

    def test_us_10_digit(self):
        result = normalize_dn("4155551234", country_code="US", site_prefix_rules=[])
        assert result.classification == "NATIONAL"
        assert result.e164 == "+14155551234"

    def test_us_10_digit_different_area(self):
        result = normalize_dn("2125551234", country_code="US", site_prefix_rules=[])
        assert result.classification == "NATIONAL"
        assert result.e164 == "+12125551234"


class TestAlreadyE164:
    """Number starting with '+' and valid → E164, pass through."""

    def test_us_e164(self):
        result = normalize_dn("+14155551234", country_code="US", site_prefix_rules=[])
        assert result.classification == "E164"
        assert result.e164 == "+14155551234"

    def test_uk_e164(self):
        result = normalize_dn("+442071234567", country_code="GB", site_prefix_rules=[])
        assert result.classification == "E164"
        assert result.e164 == "+442071234567"


class TestAmbiguous7Digit:
    """7-digit number without clear country context → depends on phonenumbers parsing."""

    def test_7_digit_us(self):
        # 7-digit numbers are not valid standalone US numbers per E.164
        # phonenumbers may reject or accept depending on area code context
        result = normalize_dn("5551234", country_code="US", site_prefix_rules=[])
        # Without area code, 7 digits in US is ambiguous
        assert result.classification in ("EXTENSION", "AMBIGUOUS")


# ---------------------------------------------------------------------------
# Site prefix stripping tests
# ---------------------------------------------------------------------------

class TestStripOutsideLine9:
    """'91234567890' with rule 'strip leading 9' → '1234567890'."""

    def test_strip_leading_9(self):
        rules = [{"prefix": "9", "description": "outside line access code"}]
        result = normalize_dn("914155551234", country_code="US", site_prefix_rules=rules)
        # After stripping '9', we have '14155551234' — 11-digit US number
        assert result.e164 == "+14155551234"

    def test_no_strip_when_no_match(self):
        rules = [{"prefix": "9", "description": "outside line access code"}]
        result = normalize_dn("1001", country_code="US", site_prefix_rules=rules)
        # '1001' doesn't start with '9', so no stripping
        assert result.classification == "EXTENSION"
        assert result.extension == "1001"


class TestStripMultipleRules:
    """Multiple prefix rules applied in order."""

    def test_first_matching_rule_applied(self):
        rules = [
            {"prefix": "9", "description": "outside line"},
            {"prefix": "8", "description": "tie line"},
        ]
        result = normalize_dn("914155551234", country_code="US", site_prefix_rules=rules)
        assert result.e164 == "+14155551234"

    def test_second_rule_matches(self):
        rules = [
            {"prefix": "9", "description": "outside line"},
            {"prefix": "8", "description": "tie line"},
        ]
        result = normalize_dn("814155551234", country_code="US", site_prefix_rules=rules)
        assert result.e164 == "+14155551234"


class TestNoMatchPrefix:
    """DN doesn't match any prefix rule → unchanged."""

    def test_no_prefix_match(self):
        rules = [{"prefix": "9", "description": "outside line"}]
        stripped = apply_prefix_rules("1001", rules)
        assert stripped == "1001"


# ---------------------------------------------------------------------------
# International format tests
# ---------------------------------------------------------------------------

class TestUKNational:
    """'02071234567' with country 'GB' → '+442071234567'."""

    def test_uk_national(self):
        result = normalize_dn("02071234567", country_code="GB", site_prefix_rules=[])
        assert result.classification in ("NATIONAL", "E164")
        assert result.e164 == "+442071234567"


class TestGermanNational:
    """'08912345678' with country 'DE' → '+498912345678'."""

    def test_german_national(self):
        result = normalize_dn("08912345678", country_code="DE", site_prefix_rules=[])
        assert result.classification in ("NATIONAL", "E164")
        assert result.e164 == "+498912345678"


class TestInvalidNumber:
    """'999' with country 'US' → phonenumbers rejects → EXTENSION (3 digits)."""

    def test_invalid_short(self):
        result = normalize_dn("999", country_code="US", site_prefix_rules=[])
        # 3 digits = short extension
        assert result.classification == "EXTENSION"
        assert result.extension == "999"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestDNWithLeadingPlus:
    """'+1...' → already E164."""

    def test_leading_plus(self):
        result = normalize_dn("+14155551234", country_code="US", site_prefix_rules=[])
        assert result.classification == "E164"
        assert result.e164 == "+14155551234"


class TestEmptyDN:
    """Empty or whitespace DN → AMBIGUOUS with clear early return."""

    def test_empty_string(self):
        result = normalize_dn("", country_code="US", site_prefix_rules=[])
        assert result.classification == "AMBIGUOUS"
        assert result.raw == ""

    def test_whitespace_only(self):
        result = normalize_dn("   ", country_code="US", site_prefix_rules=[])
        assert result.classification == "AMBIGUOUS"


class TestDNAllZeros:
    """'0000' → EXTENSION (4 digits)."""

    def test_all_zeros(self):
        result = normalize_dn("0000", country_code="US", site_prefix_rules=[])
        assert result.classification == "EXTENSION"
        assert result.extension == "0000"


class TestDNStarCode:
    """'*67' → not a phone number, handle gracefully."""

    def test_star_code(self):
        result = normalize_dn("*67", country_code="US", site_prefix_rules=[])
        # Should not raise, should return AMBIGUOUS or EXTENSION
        assert result.classification in ("AMBIGUOUS", "EXTENSION")
        assert result.raw == "*67" or result.extension == "*67"


class TestDNHashCode:
    """'#' prefixed codes should be handled gracefully."""

    def test_hash_code(self):
        result = normalize_dn("#72", country_code="US", site_prefix_rules=[])
        assert result.classification in ("AMBIGUOUS", "EXTENSION")


# ---------------------------------------------------------------------------
# E164Result dataclass tests
# ---------------------------------------------------------------------------

class TestE164ResultDataclass:
    """E164Result should have: e164, extension, raw, classification."""

    def test_has_required_fields(self):
        r = E164Result(e164="+14155551234", extension=None, raw="4155551234", classification="NATIONAL")
        assert r.e164 == "+14155551234"
        assert r.extension is None
        assert r.raw == "4155551234"
        assert r.classification == "NATIONAL"

    def test_extension_result(self):
        r = E164Result(e164=None, extension="1001", raw="1001", classification="EXTENSION")
        assert r.e164 is None
        assert r.extension == "1001"
        assert r.classification == "EXTENSION"


# ---------------------------------------------------------------------------
# apply_prefix_rules direct tests
# ---------------------------------------------------------------------------

class TestApplyPrefixRules:
    def test_empty_rules(self):
        assert apply_prefix_rules("91234", []) == "91234"

    def test_strip_single_digit(self):
        rules = [{"prefix": "9", "description": "outside line"}]
        assert apply_prefix_rules("91234", rules) == "1234"

    def test_strip_multi_digit_prefix(self):
        rules = [{"prefix": "90", "description": "international prefix"}]
        assert apply_prefix_rules("901234", rules) == "1234"

    def test_no_match_returns_original(self):
        rules = [{"prefix": "9", "description": "outside line"}]
        assert apply_prefix_rules("1234", rules) == "1234"

    def test_only_first_match_applied(self):
        """Only the first matching rule should be applied (not chained)."""
        rules = [
            {"prefix": "9", "description": "outside line"},
            {"prefix": "1", "description": "ld prefix"},
        ]
        # '9' matches, strips to '1234' — should NOT then strip the '1'
        assert apply_prefix_rules("91234", rules) == "1234"

    def test_prefix_must_match_start(self):
        rules = [{"prefix": "9", "description": "outside line"}]
        assert apply_prefix_rules("1239", rules) == "1239"


# ---------------------------------------------------------------------------
# Webex extension length validation
# ---------------------------------------------------------------------------

class TestExtensionLengthBounds:
    """Webex allows extensions 2-10 chars. DNs outside this range
    should still work but may generate decisions downstream."""

    def test_1_digit_still_classifies(self):
        result = normalize_dn("5", country_code="US", site_prefix_rules=[])
        # Single digit — too short for Webex but should still classify
        assert result.classification in ("EXTENSION", "AMBIGUOUS")

    def test_6_digit_extension(self):
        result = normalize_dn("100123", country_code="US", site_prefix_rules=[])
        assert result.classification in ("EXTENSION", "AMBIGUOUS")
