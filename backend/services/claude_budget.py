"""In-memory monthly Claude spend tracker.

Resets at the start of each calendar month (UTC). The tracker is purely in-memory
so it resets when the backend restarts — acceptable for the MVP. Persist to a
Supabase table later if drift becomes a problem.
"""
from datetime import datetime, timezone

# Monthly cap, in USD. Tune by editing this constant.
MONTHLY_BUDGET_USD = 20.0

# Haiku 4.5 pricing per million tokens (Oct 2025 pricing).
HAIKU_INPUT_PER_1M = 1.0
HAIKU_OUTPUT_PER_1M = 5.0

_state: dict = {"month": "", "spend": 0.0}


def _reset_if_new_month() -> None:
    current = datetime.now(timezone.utc).strftime("%Y-%m")
    if _state["month"] != current:
        _state["month"] = current
        _state["spend"] = 0.0


def record_usage(input_tokens: int, output_tokens: int) -> None:
    """Record one Claude call against the monthly budget."""
    _reset_if_new_month()
    cost = (input_tokens / 1_000_000) * HAIKU_INPUT_PER_1M
    cost += (output_tokens / 1_000_000) * HAIKU_OUTPUT_PER_1M
    _state["spend"] += cost


def within_budget() -> bool:
    _reset_if_new_month()
    return _state["spend"] < MONTHLY_BUDGET_USD


def remaining_usd() -> float:
    _reset_if_new_month()
    return max(0.0, MONTHLY_BUDGET_USD - _state["spend"])


def current_spend_usd() -> float:
    _reset_if_new_month()
    return _state["spend"]
