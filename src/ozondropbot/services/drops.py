from __future__ import annotations


def drop_percent(old_price: float, new_price: float) -> float:
    if old_price <= 0:
        return 0.0
    return ((old_price - new_price) / old_price) * 100
