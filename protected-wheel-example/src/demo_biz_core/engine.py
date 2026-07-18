"""The "commercial secret" — a toy bid-scoring engine.

This module is compiled by Cython into a native extension; the .py source
never enters the wheel. Anything here (weights, thresholds, algorithms) is
what the compilation protects.
"""

from __future__ import annotations

# Pretend these calibrated weights are the trade secret.
_PRICE_WEIGHT = 0.42
_TECH_WEIGHT = 0.35
_CREDIT_WEIGHT = 0.23
_LOWBALL_FLOOR = 0.78  # bids below 78% of base price get penalized


def _price_score(bid_amount: float, base_price: float) -> float:
    if base_price <= 0:
        raise ValueError("base_price must be positive")
    ratio = bid_amount / base_price
    if ratio < _LOWBALL_FLOOR:
        # Suspiciously cheap: linear penalty below the floor.
        return max(0.0, 100.0 * ratio / _LOWBALL_FLOOR * 0.6)
    if ratio > 1.0:
        return max(0.0, 100.0 - (ratio - 1.0) * 250.0)
    return 100.0 - (1.0 - ratio) * 40.0


def evaluate_bid(bid_amount: float, base_price: float, tech_score: float, credit_score: float) -> dict:
    """Score one bid. All the interesting numbers live in compiled code."""
    price = _price_score(bid_amount, base_price)
    total = price * _PRICE_WEIGHT + tech_score * _TECH_WEIGHT + credit_score * _CREDIT_WEIGHT
    return {
        "price_score": round(price, 2),
        "total_score": round(total, 2),
        "flagged_lowball": bid_amount / base_price < _LOWBALL_FLOOR,
    }


def engine_info() -> dict:
    """Prove at runtime that the compiled module is the one answering."""
    import sys

    return {
        "module_file": __file__,  # ends in .so/.pyd when compiled
        "compiled": not __file__.endswith(".py"),
        "python": sys.version.split()[0],
    }
