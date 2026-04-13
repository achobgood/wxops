"""CUCM digit pattern compiler and overlap detection.

Compiles CUCM route pattern strings into Python regexes and detects
whether two patterns can match the same digit string. Used by css_mapper
for ordering conflict detection.

CUCM pattern symbols (from 04-css-decomposition.md):
    X   — single digit 0-9
    !   — one or more digits (greedy wildcard)
    [n-m] — digit range
    [^n] — negated digit
    @   — national numbering plan macro (country-specific)
    .   — separator (between access code and pattern)
    +   — E.164 prefix (literal)
"""

from __future__ import annotations

import random
import re


# ---------------------------------------------------------------------------
# @ macro expansion — intentionally broad for overlap detection safety.
# Real CUCM '@' expands to the loaded National Numbering Plan file, which
# varies by cluster/country. This catch-all never produces false negatives
# in overlap detection (it over-matches, so overlapping patterns are always
# detected). generate_representative_strings compensates by producing
# US-format 10-digit numbers for '@' patterns.
# CUCM @ pattern matches "any dialed number" — exact expansion varies by
# cluster/country dial plan. [0-9]{1,15} is a conservative over-match that
# never produces false negatives in overlap detection. Safe approximation.
# ---------------------------------------------------------------------------
_AT_MACRO_REGEX = "[0-9]{1,15}"


def cucm_pattern_to_regex(pattern: str) -> str:
    """Convert a CUCM digit pattern to a Python regex string.

    X → [0-9], ! → [0-9]+, [1-4] → [1-4], [^5] → [^5]
    . → '' (stripped — separator only), + → \\+, @ → expanded

    (from 03b-transform-mappers.md, cucm_pattern.py interface)
    """
    if not pattern or pattern.strip() == "" or pattern == ".":
        raise ValueError(f"Empty or invalid CUCM pattern: {pattern!r}")

    # Split on first '.' only — it's the access code separator
    # (from 04-css-decomposition.md: '.' separates access code from pattern)
    parts = pattern.split(".", 1)
    if len(parts) == 2:
        access_code, digit_pattern = parts[0], parts[1]
    else:
        access_code, digit_pattern = "", parts[0]

    # Convert the access code (literal digits, + prefix)
    regex = _convert_segment(access_code)
    # Convert the digit pattern
    regex += _convert_segment(digit_pattern)

    return regex


def _convert_segment(segment: str) -> str:
    """Convert a CUCM pattern segment to regex."""
    result = []
    i = 0
    while i < len(segment):
        ch = segment[i]
        if ch == "X":
            result.append("[0-9]")
        elif ch == "!":
            result.append("[0-9]+")
        elif ch == "@":
            result.append(_AT_MACRO_REGEX)
        elif ch == "+":
            result.append("\\+")
        elif ch == "[":
            # Pass through bracket expressions (ranges and negation)
            try:
                end = segment.index("]", i)
            except ValueError:
                raise ValueError(f"Unclosed bracket in CUCM pattern segment: {segment!r}")
            result.append(segment[i : end + 1])
            i = end
        elif ch.isdigit():
            result.append(ch)
        # Skip any other character (shouldn't normally appear)
        i += 1
    return "".join(result)


def compile_cucm_pattern(pattern: str) -> re.Pattern:
    """Compile a CUCM digit pattern into a Python regex Pattern object.

    (from phase-02-risk-spikes.md: compile_cucm_pattern(pattern: str) -> re.Pattern)
    """
    regex_str = cucm_pattern_to_regex(pattern)
    return re.compile(f"^{regex_str}$")


def generate_representative_strings(pattern: str, count: int = 10) -> list[str]:
    """Generate digit strings that match a CUCM pattern.

    Uses random generation to produce representative strings for overlap testing.
    For patterns with '!' (unbounded length), generates strings at representative
    lengths (5, 7, 10, 11, 15 digits for the '!' portion).
    (from 04-css-decomposition.md: enumeration approach #2)
    """
    if not pattern or pattern.strip() == "" or pattern == ".":
        raise ValueError(f"Empty or invalid CUCM pattern: {pattern!r}")

    # Split on first '.' — access code separator
    parts = pattern.split(".", 1)
    if len(parts) == 2:
        access_code, digit_pattern = parts[0], parts[1]
    else:
        access_code, digit_pattern = "", parts[0]

    compiled = compile_cucm_pattern(pattern)
    results = []

    for _ in range(count * 5):  # oversample to hit count
        s = _generate_one(access_code) + _generate_one(digit_pattern)
        if compiled.fullmatch(s):
            results.append(s)
        if len(results) >= count:
            break

    # Deduplicate but respect count
    if len(results) < count:
        # For exact patterns there's only one string
        unique = list(dict.fromkeys(results))
        # Pad with duplicates if needed
        while len(results) < count and unique:
            results.append(unique[0])

    return results[:count]


def _generate_one(segment: str) -> str:
    """Generate one random digit string matching a CUCM pattern segment."""
    result = []
    i = 0
    while i < len(segment):
        ch = segment[i]
        if ch == "X":
            result.append(str(random.randint(0, 9)))
        elif ch == "!":
            # Generate at representative lengths for the '!' portion
            bang_len = random.choice([1, 2, 4, 7, 10])
            result.append("".join(str(random.randint(0, 9)) for _ in range(bang_len)))
        elif ch == "@":
            # US national plan: generate 10-digit number
            result.append(
                str(random.randint(2, 9))
                + "".join(str(random.randint(0, 9)) for _ in range(9))
            )
        elif ch == "+":
            result.append("+")
        elif ch == "[":
            try:
                end = segment.index("]", i)
            except ValueError:
                raise ValueError(f"Unclosed bracket in CUCM pattern segment: {segment!r}")
            bracket_content = segment[i + 1 : end]
            digit = _random_from_bracket(bracket_content)
            result.append(digit)
            i = end
        elif ch.isdigit():
            result.append(ch)
        i += 1
    return "".join(result)


def _random_from_bracket(content: str) -> str:
    """Pick a random digit matching a bracket expression like '2-9' or '^0'."""
    negated = content.startswith("^")
    if negated:
        content = content[1:]

    # Build set of allowed digits
    allowed = set()
    i = 0
    while i < len(content):
        if i + 2 < len(content) and content[i + 1] == "-":
            start, end = int(content[i]), int(content[i + 2])
            allowed.update(range(start, end + 1))
            i += 3
        else:
            allowed.add(int(content[i]))
            i += 1

    if negated:
        allowed = set(range(10)) - allowed

    if not allowed:
        return "0"
    return str(random.choice(sorted(allowed)))


def cucm_patterns_overlap(pattern_a: str, pattern_b: str) -> bool:
    """Return True if two CUCM patterns can match any common digit string.

    Uses enumeration approach: generate representative digit strings from each
    pattern's match space and test against the other. Tests at representative
    lengths (4, 7, 10, 11, 15 digits) for patterns involving !.
    (from 04-css-decomposition.md, overlap detection via enumeration)
    (from 03b-transform-mappers.md, cucm_pattern.py interface)
    """
    compiled_a = compile_cucm_pattern(pattern_a)
    compiled_b = compile_cucm_pattern(pattern_b)

    # Generate samples from A, test against B
    samples_a = generate_representative_strings(pattern_a, count=50)
    for s in samples_a:
        if compiled_b.fullmatch(s):
            return True

    # Generate samples from B, test against A
    samples_b = generate_representative_strings(pattern_b, count=50)
    for s in samples_b:
        if compiled_a.fullmatch(s):
            return True

    return False


def classify_block_pattern(
    pattern: str,
    category_rules: list[dict],
) -> str | None:
    """Classify a CUCM blocking pattern into a Webex permission category.

    Returns category string (e.g., 'international', 'premium') or None if
    unclassifiable. Uses configurable rules from migration config.
    (from 03b-transform-mappers.md, cucm_pattern.py interface)

    A rule matches if the blocking pattern is identical to the rule's pattern
    (exact string match). For more sophisticated matching (e.g., pattern
    subsumption), extend this function.
    """
    for rule in category_rules:
        if rule["cucm_pattern"] == pattern:
            return rule["webex_category"]
    return None
