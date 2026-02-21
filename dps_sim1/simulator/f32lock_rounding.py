from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Number = Union[int, float]


def round_half_up(value: Number, ndigits: int = 0) -> Union[int, float]:
    """Round with ROUND_HALF_UP semantics (no banker's rounding).

    - ndigits == 0: returns int (compatible with round(x) one-arg style)
    - ndigits != 0: returns float
    """
    n = int(ndigits)
    quant = Decimal("1").scaleb(-n)
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    if n == 0:
        return int(rounded)
    return float(rounded)
