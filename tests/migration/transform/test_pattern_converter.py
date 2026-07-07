"""Tests for pattern_converter: CUCM route pattern -> Webex dial plan pattern.

Tests the cucm_to_webex_pattern() function with various CUCM pattern formats.
"""

from __future__ import annotations

import pytest

from wxcli.migration.transform.pattern_converter import cucm_to_webex_pattern


class TestPatternConverterAccessCodeStripping:
    """Access code prefix (before '.') is stripped."""

    def test_basic_access_code_stripped(self):
        """9.1[2-9]XXXXXXXXX -> +1[2-9]XXXXXXXXX"""
        result = cucm_to_webex_pattern("9.1[2-9]XXXXXXXXX", "+1", "9")
        assert result == "+1[2-9]XXXXXXXXX"

    def test_access_code_with_national_number(self):
        """9.1XXXXXXXXXX -> +1XXXXXXXXXX (the '1' is the national prefix, already embedded)."""
        result = cucm_to_webex_pattern("9.1XXXXXXXXXX", "+1", "9")
        assert result == "+1XXXXXXXXXX"

    def test_different_access_code(self):
        """8.1[2-9]XXXXXXXXX with access code 8 -> +1[2-9]XXXXXXXXX"""
        result = cucm_to_webex_pattern("8.1[2-9]XXXXXXXXX", "+1", "8")
        assert result == "+1[2-9]XXXXXXXXX"


class TestPatternConverterInternational:
    """International access code patterns (011, 00)."""

    def test_us_international_pattern(self):
        """9.011! -> +!"""
        result = cucm_to_webex_pattern("9.011!", "+1", "9")
        assert result == "+!"

    def test_european_international_pattern(self):
        """0.00! -> +!"""
        result = cucm_to_webex_pattern("0.00!", "+44", "0")
        assert result == "+!"

    def test_intl_with_country_code(self):
        """9.01144! -> +44!"""
        result = cucm_to_webex_pattern("9.01144!", "+1", "9")
        assert result == "+44!"


class TestPatternConverterWildcards:
    """Wildcards X, !, and ranges are preserved."""

    def test_x_wildcard_preserved(self):
        result = cucm_to_webex_pattern("9.1XXXXXXXXXX", "+1", "9")
        assert "X" in result

    def test_bang_wildcard_preserved(self):
        result = cucm_to_webex_pattern("9.011!", "+1", "9")
        assert result.endswith("!")

    def test_range_preserved(self):
        result = cucm_to_webex_pattern("9.1[2-9]XX", "+1", "9")
        assert "[2-9]" in result


class TestPatternConverterNoAccessCode:
    """Patterns without access code separator '.'."""

    def test_no_dot_with_leading_access_digit(self):
        """Pattern starting with outside dial digit but no dot.
        91XXXXXXXXXX -> strip '9' -> 1XXXXXXXXXX -> +1XXXXXXXXXX."""
        result = cucm_to_webex_pattern("91XXXXXXXXXX", "+1", "9")
        assert result == "+1XXXXXXXXXX"

    def test_no_dot_no_access_digit(self):
        """Pattern without access code or dot -> prepend country code."""
        result = cucm_to_webex_pattern("1XXX", "+1", "9")
        assert result == "+11XXX"


class TestPatternConverterEscapedPlus:
    """CUCM \\+ escape for literal plus."""

    def test_escaped_plus_pattern(self):
        """\\+1XXXXXXXXXX -> +1XXXXXXXXXX"""
        result = cucm_to_webex_pattern("\\+1XXXXXXXXXX", "+1", "9")
        assert result == "+1XXXXXXXXXX"

    def test_already_e164(self):
        """Pattern already in E.164 format (starts with +) is returned as-is."""
        result = cucm_to_webex_pattern("+15551234567", "+1", "9")
        assert result == "+15551234567"


class TestPatternConverterEdgeCases:
    """Empty patterns, unusual formats."""

    def test_empty_pattern(self):
        result = cucm_to_webex_pattern("", "+1", "9")
        assert result == ""

    def test_dot_at_start(self):
        """.1XXX -> access code is empty, remainder 1XXX starts with country '1' -> +1XXX."""
        result = cucm_to_webex_pattern(".1XXX", "+1", "9")
        assert result == "+1XXX"

    def test_pattern_with_only_wildcards(self):
        """9.! -> +!"""
        # After stripping "9.", we have "!" which isn't an intl prefix
        result = cucm_to_webex_pattern("9.!", "+1", "9")
        assert result == "+1!"
