"""Tests for CUCM digit pattern compiler and overlap detection.

Test cases derived from 04-css-decomposition.md and 03b-transform-mappers.md.
TDD: these tests are written BEFORE the implementation.
"""

import random
import re

import pytest

from wxcli.migration.transform.cucm_pattern import (
    classify_block_pattern,
    compile_cucm_pattern,
    cucm_pattern_to_regex,
    cucm_patterns_overlap,
    generate_representative_strings,
)


# ---------------------------------------------------------------------------
# Pattern compilation tests
# ---------------------------------------------------------------------------

class TestCompileSimpleDigits:
    """'9.1234' → exact match on '91234'."""

    def test_matches_exact(self):
        pat = compile_cucm_pattern("9.1234")
        assert pat.fullmatch("91234")

    def test_rejects_extra_digit(self):
        pat = compile_cucm_pattern("9.1234")
        assert pat.fullmatch("912345") is None

    def test_rejects_fewer_digits(self):
        pat = compile_cucm_pattern("9.123")
        assert pat.fullmatch("91234") is None


class TestCompileXWildcard:
    """'X' matches exactly one digit 0-9."""

    def test_single_x(self):
        pat = compile_cucm_pattern("9.1XXXXXXXXXX")
        assert pat.fullmatch("912345678901")

    def test_x_matches_zero(self):
        pat = compile_cucm_pattern("X")
        assert pat.fullmatch("0")

    def test_x_matches_nine(self):
        pat = compile_cucm_pattern("X")
        assert pat.fullmatch("9")

    def test_x_rejects_non_digit(self):
        pat = compile_cucm_pattern("X")
        assert pat.fullmatch("A") is None

    def test_x_rejects_two_digits(self):
        pat = compile_cucm_pattern("X")
        assert pat.fullmatch("12") is None


class TestCompileBangWildcard:
    """'!' matches one or more digits (greedy)."""

    def test_bang_matches_one_digit(self):
        pat = compile_cucm_pattern("9.011!")
        assert pat.fullmatch("90111")

    def test_bang_matches_many_digits(self):
        pat = compile_cucm_pattern("9.011!")
        assert pat.fullmatch("9011442071234567")

    def test_bang_rejects_zero_trailing(self):
        """'!' requires at least one digit after the prefix."""
        pat = compile_cucm_pattern("9.011!")
        assert pat.fullmatch("9011") is None


class TestCompileDigitRange:
    """'[2-9]' matches digits 2 through 9."""

    def test_range_match(self):
        pat = compile_cucm_pattern("9.1[2-9]XX")
        assert pat.fullmatch("91345")

    def test_range_lower_bound(self):
        pat = compile_cucm_pattern("9.1[2-9]XX")
        assert pat.fullmatch("91200")

    def test_range_upper_bound(self):
        pat = compile_cucm_pattern("9.1[2-9]XX")
        assert pat.fullmatch("91999")

    def test_range_rejects_below(self):
        pat = compile_cucm_pattern("9.1[2-9]XX")
        assert pat.fullmatch("91100") is None

    def test_range_rejects_above(self):
        """Digit range [2-9] rejects digits outside that range."""
        pat = compile_cucm_pattern("[2-9]")
        assert pat.fullmatch("1") is None


class TestCompileNegatedDigit:
    """'[^0]' matches any digit except 0."""

    def test_negated_allows_nonzero(self):
        pat = compile_cucm_pattern("[^0]XXX")
        assert pat.fullmatch("1234")

    def test_negated_rejects_zero(self):
        pat = compile_cucm_pattern("[^0]XXX")
        assert pat.fullmatch("0123") is None

    def test_negated_allows_nine(self):
        pat = compile_cucm_pattern("[^0]XXX")
        assert pat.fullmatch("9000")


class TestCompileE164Prefix:
    """'+' is a literal E.164 prefix."""

    def test_plus_prefix(self):
        pat = compile_cucm_pattern("+1XXXXXXXXXX")
        assert pat.fullmatch("+12125551234")

    def test_plus_rejects_without_plus(self):
        pat = compile_cucm_pattern("+1XXXXXXXXXX")
        assert pat.fullmatch("12125551234") is None


class TestCompileDotSeparator:
    """'.' is a separator (between access code and pattern), stripped in matching."""

    def test_dot_stripped(self):
        pat = compile_cucm_pattern("9.1234")
        # The '.' is just a separator — the matched string is "91234"
        assert pat.fullmatch("91234")

    def test_no_dot_still_works(self):
        pat = compile_cucm_pattern("1234")
        assert pat.fullmatch("1234")


# ---------------------------------------------------------------------------
# cucm_pattern_to_regex tests
# ---------------------------------------------------------------------------

class TestPatternToRegex:
    """cucm_pattern_to_regex returns a regex string."""

    def test_returns_string(self):
        result = cucm_pattern_to_regex("9.1XXX")
        assert isinstance(result, str)

    def test_compiles_to_valid_regex(self):
        regex_str = cucm_pattern_to_regex("9.1[2-9]XXXXXXXXX")
        re.compile(regex_str)  # should not raise

    def test_x_becomes_digit_class(self):
        regex_str = cucm_pattern_to_regex("XX")
        assert "[0-9]" in regex_str

    def test_bang_becomes_one_or_more(self):
        regex_str = cucm_pattern_to_regex("!")
        assert "[0-9]+" in regex_str

    def test_plus_escaped(self):
        regex_str = cucm_pattern_to_regex("+1XXX")
        assert "\\+" in regex_str


# ---------------------------------------------------------------------------
# Overlap detection tests (from 04-css-decomposition.md)
# ---------------------------------------------------------------------------

class TestOverlapBroadVsSpecific:
    """'9.!' vs '9.011!' → overlapping (broad catches international too)."""

    def test_overlap(self):
        assert cucm_patterns_overlap("9.!", "9.011!") is True


class TestOverlapRanges:
    """'9.1[2-9]XXXXXXXXX' vs '9.1900XXXXXXX' → overlapping (900 is in [2-9]XX range)."""

    def test_overlap(self):
        assert cucm_patterns_overlap("9.1[2-9]XXXXXXXXX", "9.1900XXXXXXX") is True


class TestNoOverlapDomesticVsIntl:
    """'9.1[2-9]XXXXXXXXX' vs '9.011!' → non-overlapping."""

    def test_no_overlap(self):
        assert cucm_patterns_overlap("9.1[2-9]XXXXXXXXX", "9.011!") is False


class TestNoOverlapLocalVsLd:
    """'9.[2-9]XXXXXX' (7-digit local) vs '9.1[2-9]XXXXXXXXX' (11-digit LD) → non-overlapping."""

    def test_no_overlap(self):
        assert cucm_patterns_overlap("9.[2-9]XXXXXX", "9.1[2-9]XXXXXXXXX") is False


class TestOverlapIdenticalPatterns:
    """Same pattern → overlapping."""

    def test_identical(self):
        assert cucm_patterns_overlap("9.1[2-9]XXXXXXXXX", "9.1[2-9]XXXXXXXXX") is True

    def test_identical_simple(self):
        assert cucm_patterns_overlap("1234", "1234") is True


class TestOverlapSymmetry:
    """Overlap detection should be symmetric: overlap(a,b) == overlap(b,a)."""

    def test_symmetric_overlapping(self):
        a, b = "9.!", "9.011!"
        assert cucm_patterns_overlap(a, b) == cucm_patterns_overlap(b, a)

    def test_symmetric_non_overlapping(self):
        a, b = "9.1[2-9]XXXXXXXXX", "9.011!"
        assert cucm_patterns_overlap(a, b) == cucm_patterns_overlap(b, a)


# ---------------------------------------------------------------------------
# generate_representative_strings tests
# ---------------------------------------------------------------------------

class TestGenerateRepresentativeStrings:
    """Generate digit strings that match a pattern."""

    def test_returns_list(self):
        result = generate_representative_strings("9.1XXX", count=5)
        assert isinstance(result, list)

    def test_all_match_pattern(self):
        pat = compile_cucm_pattern("9.1[2-9]XXXXXXXXX")
        strings = generate_representative_strings("9.1[2-9]XXXXXXXXX", count=10)
        for s in strings:
            assert pat.fullmatch(s), f"Generated string '{s}' doesn't match pattern"

    def test_bang_generates_varying_lengths(self):
        strings = generate_representative_strings("9.011!", count=20)
        lengths = {len(s) for s in strings}
        # '!' allows varying lengths, so we expect more than 1 distinct length
        assert len(lengths) > 1

    def test_count_respected(self):
        strings = generate_representative_strings("9.1XXXXXXXXXX", count=5)
        assert len(strings) == 5

    def test_exact_pattern_returns_one_string(self):
        strings = generate_representative_strings("91234", count=5)
        # An exact pattern can only produce one unique string
        assert len(set(strings)) == 1
        assert strings[0] == "91234"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_pattern_raises(self):
        with pytest.raises((ValueError, re.error)):
            compile_cucm_pattern("")

    def test_at_symbol_national_plan(self):
        """'@' is a country-specific macro. Should compile without error.
        The exact expansion is country-dependent — at minimum it should
        match some digit strings."""
        pat = compile_cucm_pattern("@")
        # Should match some US national number format
        strings = generate_representative_strings("@", count=5)
        assert len(strings) > 0

    def test_pattern_with_only_dot(self):
        """A lone '.' should be treated as empty/invalid."""
        with pytest.raises((ValueError, re.error)):
            compile_cucm_pattern(".")

    def test_multiple_dots(self):
        """Only the first '.' is the access code separator.
        Second '.' in the pattern portion is silently skipped."""
        pat = compile_cucm_pattern("9.1.234")
        # Access code "9", pattern "1.234" — the inner '.' is skipped
        assert pat.fullmatch("91234")

    def test_compile_returns_regex_pattern(self):
        result = compile_cucm_pattern("9.1XXX")
        assert isinstance(result, re.Pattern)


# ---------------------------------------------------------------------------
# classify_block_pattern tests (from 03b-transform-mappers.md interface)
# ---------------------------------------------------------------------------

US_CATEGORY_RULES = [
    {"cucm_pattern": "9.011!", "webex_category": "international"},
    {"cucm_pattern": "9.1900XXXXXXX", "webex_category": "premium"},
    {"cucm_pattern": "9.1976XXXXXXX", "webex_category": "premium"},
    {"cucm_pattern": "9.0!", "webex_category": "operator"},
    {"cucm_pattern": "9.1[2-9]XX555XXXX", "webex_category": "directory_assistance"},
    {"cucm_pattern": "9.1900!", "webex_category": "premium"},
]


class TestClassifyBlockPattern:
    def test_international(self):
        assert classify_block_pattern("9.011!", US_CATEGORY_RULES) == "international"

    def test_premium_900(self):
        assert classify_block_pattern("9.1900XXXXXXX", US_CATEGORY_RULES) == "premium"

    def test_premium_976(self):
        assert classify_block_pattern("9.1976XXXXXXX", US_CATEGORY_RULES) == "premium"

    def test_operator(self):
        assert classify_block_pattern("9.0!", US_CATEGORY_RULES) == "operator"

    def test_unclassifiable_returns_none(self):
        assert classify_block_pattern("9.1408XXXXXXX", US_CATEGORY_RULES) is None

    def test_directory_assistance(self):
        assert classify_block_pattern("9.1[2-9]XX555XXXX", US_CATEGORY_RULES) == "directory_assistance"

    def test_exact_match_required(self):
        """A pattern that doesn't exactly match any rule returns None."""
        assert classify_block_pattern("9.1234", US_CATEGORY_RULES) is None
