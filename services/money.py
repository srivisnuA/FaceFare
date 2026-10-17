"""Exact two-decimal wallet arithmetic with a bounded prototype balance."""
from decimal import Decimal, InvalidOperation

MAX_CENTS = 100_000_000_000


def to_cents(value, *, allow_negative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Amount must be numeric")
    try:
        decimal = Decimal(str(value))
        if not decimal.is_finite() or abs(decimal) > Decimal(MAX_CENTS) / 100:
            raise ValueError("Amount must be finite and at most 1,000,000,000")
        cents = decimal * 100
        if cents != cents.to_integral_value():
            raise ValueError("Amount must have at most two decimal places")
        if not allow_negative and cents < 0:
            raise ValueError("Amount cannot be negative")
        return int(cents)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc


def from_cents(cents):
    return cents / 100
