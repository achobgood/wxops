"""Pattern converter: CUCM route pattern -> Webex dial plan pattern.

Converts CUCM dial pattern syntax to Webex-compatible E.164 format patterns.
Used by routing_mapper and css_mapper for pattern syntax conversion.

(from 03b-transform-mappers.md §6, Pattern Syntax Conversion table)
(from 03b-transform-mappers.md §13, Pattern Converter shared utility)

Conversion rules:
    - Strip access code prefix (everything before '.')
    - Prepend country code prefix (e.g., "+1") to the remaining pattern
    - Preserve wildcards: X, !, [ranges]
    - Strip '.' separator entirely
    - International access code (e.g., "011") is stripped when followed by wildcard
    - '@' macro requires expansion (not handled here — see migration config)
"""

from __future__ import annotations


def cucm_to_webex_pattern(
    cucm_pattern: str,
    country_code: str = "+1",
    outside_dial_digit: str = "9",
) -> str:
    """Convert a CUCM route pattern to a Webex dial plan pattern.

    (from 03b-transform-mappers.md §13: Pattern Converter)

    Args:
        cucm_pattern: CUCM route pattern (e.g., "9.1[2-9]XXXXXXXXX", "9.011!")
        country_code: E.164 country prefix including '+' (e.g., "+1", "+44")
        outside_dial_digit: The CUCM outside access digit (e.g., "9")

    Returns:
        Webex-format dial plan pattern (e.g., "+1[2-9]XXXXXXXXX", "+!")

    Examples:
        >>> cucm_to_webex_pattern("9.1[2-9]XXXXXXXXX", "+1", "9")
        '+1[2-9]XXXXXXXXX'
        >>> cucm_to_webex_pattern("9.011!", "+1", "9")
        '+!'
        >>> cucm_to_webex_pattern("1XXX", "+1", "9")
        '+11XXX'
        >>> cucm_to_webex_pattern("\\\\+1XXXXXXXXXX", "+1", "9")
        '+1XXXXXXXXXX'
    """
    if not cucm_pattern:
        return cucm_pattern

    # Coerce outside_dial_digit to str (config may supply it as int, e.g. 9)
    outside_dial_digit = str(outside_dial_digit)

    # Strip leading backslash-escaped '+' (CUCM uses \+ for literal plus)
    # (CUCM route patterns sometimes escape + as \\+)
    working = cucm_pattern.replace("\\+", "+")

    # If pattern already starts with '+', it's already E.164 format
    if working.startswith("+"):
        return working

    # Track whether we stripped an access code. When an access code is present,
    # the remainder typically starts with the national prefix (e.g., "1" for US).
    # Without an access code, the pattern is a direct route pattern where digits
    # should NOT be interpreted as embedded country codes.
    access_code_stripped = False

    # Strip access code prefix: everything before '.' (the dot separator)
    # (from 03b-transform-mappers.md §6: "Strips access code prefix (before '.')")
    if "." in working:
        _prefix, remainder = working.split(".", 1)
        working = remainder
        access_code_stripped = True
    # If no dot but starts with outside_dial_digit followed by known patterns,
    # strip the leading access code
    elif working.startswith(outside_dial_digit) and len(working) > 1:
        next_char = working[len(outside_dial_digit):]
        if next_char and (next_char[0].isdigit() or next_char[0] in "X[!"):
            working = working[len(outside_dial_digit):]
            access_code_stripped = True

    # Handle international access code patterns (e.g., "011!")
    # (from 03b-transform-mappers.md §6: "9.011!" -> "+!")
    # Common international access codes: 011 (US/CA), 00 (many countries)
    intl_prefixes = ["011", "00"]
    for intl in intl_prefixes:
        if working.startswith(intl):
            remainder_after_intl = working[len(intl):]
            if remainder_after_intl:
                return f"+{remainder_after_intl}"
            else:
                return f"+{working}"

    # If we stripped an access code, the remainder starts with the national
    # prefix digits (e.g., "1" for "+1"). Just prepend "+".
    # (from 03b-transform-mappers.md §6: "Strip access code prefix, prepend + and country code")
    # Example: "9.1[2-9]XXXXXXXXX" -> strip "9." -> "1[2-9]XXXXXXXXX" -> "+1[2-9]XXXXXXXXX"
    if access_code_stripped:
        bare_cc = country_code.lstrip("+")
        if bare_cc and working.startswith(bare_cc):
            return f"+{working}"

    # Prepend full country code prefix for patterns without embedded national prefix
    # (from 03b-transform-mappers.md §6: "prepend + and country code")
    # country_code already includes '+' (e.g., "+1")
    return f"{country_code}{working}"
