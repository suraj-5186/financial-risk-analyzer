from decimal import Decimal, ROUND_HALF_UP

def to_decimal(val: float | int | str | Decimal) -> Decimal:
    """Safely convert numeric values to Decimal with 2 decimal places."""
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def round_currency(val: float | int | Decimal) -> float:
    """Centralized rounding to 2 decimal places returning float."""
    if val is None:
        return 0.0
    d = to_decimal(val)
    return float(d)

def is_currency_equal(val1: float | Decimal, val2: float | Decimal, epsilon: float = 0.01) -> bool:
    """Decimal-safe comparison for monetary equality."""
    d1 = to_decimal(val1)
    d2 = to_decimal(val2)
    return abs(d1 - d2) <= Decimal(str(epsilon))
