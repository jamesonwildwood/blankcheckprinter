"""Convert a dollar amount into the words written on the check's legal line.

Example: 1234.56 -> "One Thousand Two Hundred Thirty-Four and 56/100"
"""

from decimal import Decimal, ROUND_HALF_UP

_ONES = [
    "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
    "Sixteen", "Seventeen", "Eighteen", "Nineteen",
]
_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
    "Eighty", "Ninety",
]
# Enough scale for any check a small business will ever write.
_SCALES = ["", "Thousand", "Million", "Billion", "Trillion"]


def _under_thousand(n):
    """Words for 0..999 (no leading/trailing spaces)."""
    parts = []
    if n >= 100:
        parts.append(_ONES[n // 100])
        parts.append("Hundred")
        n %= 100
    if n >= 20:
        tens = _TENS[n // 10]
        ones = n % 10
        parts.append(f"{tens}-{_ONES[ones]}" if ones else tens)
    elif n > 0:
        parts.append(_ONES[n])
    return " ".join(parts)


def int_to_words(n):
    """Words for a non-negative integer dollar amount."""
    if n == 0:
        return "Zero"
    groups = []
    scale = 0
    while n > 0:
        chunk = n % 1000
        if chunk:
            words = _under_thousand(chunk)
            if _SCALES[scale]:
                words += " " + _SCALES[scale]
            groups.append(words)
        n //= 1000
        scale += 1
    return " ".join(reversed(groups))


def amount_to_words(amount):
    """Return the check legal-line text, e.g. 'One Thousand and 05/100'.

    Cents are shown as NN/100 per U.S. check convention. Raises ValueError on
    negative amounts.
    """
    amt = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amt < 0:
        raise ValueError("Check amount cannot be negative")
    dollars = int(amt)
    cents = int((amt - dollars) * 100)
    return f"{int_to_words(dollars)} and {cents:02d}/100"


if __name__ == "__main__":  # quick self-check
    for v in [0, 5, 19, 100, 1234.56, 1000, 1000000.07, 2500.00, 99.99]:
        print(f"{v:>12} -> {amount_to_words(v)}")
