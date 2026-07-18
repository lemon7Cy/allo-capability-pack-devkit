"""demo-biz-core: protected business logic, compiled to a native extension.

This file is the ONLY python source shipped in the wheel. Keep it a trivial
re-export — never put business logic here.
"""

from .engine import evaluate_bid, engine_info

__all__ = ["evaluate_bid", "engine_info"]
