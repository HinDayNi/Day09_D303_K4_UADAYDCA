"""Deterministic timestamp parsing and hour-variance helpers for Delivery Agent.

Toàn bộ timestamp được parse dạng naive (không đổi timezone), giữ đúng định
dạng CSV `YYYY-MM-DD HH:MM:SS`. Số giờ chênh lệch được tính từ tổng số giây
chia cho 3600 bằng `Decimal`, làm tròn 2 chữ số theo `ROUND_HALF_UP`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
_SECONDS_PER_HOUR = Decimal("3600")
_TWO_PLACES = Decimal("0.01")


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse a CSV timestamp string into a naive datetime, or None."""
    if value is None or value == "":
        return None
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def round2(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def hours_between(later: Optional[str], earlier: Optional[str]) -> Optional[float]:
    """Return (later - earlier) in hours, rounded to 2 decimals, or None.

    Returns None whenever either timestamp is missing, so upstream
    agents never have to fabricate a variance from absent data.
    """
    later_dt = parse_timestamp(later)
    earlier_dt = parse_timestamp(earlier)
    if later_dt is None or earlier_dt is None:
        return None
    delta_seconds = Decimal(str((later_dt - earlier_dt).total_seconds()))
    variance = round2(delta_seconds / _SECONDS_PER_HOUR)
    return float(variance)
