from datetime import datetime, timezone
from unittest.mock import patch
import services.claude_budget as budget


def _reset():
    budget._state["month"] = ""
    budget._state["spend"] = 0.0


def test_within_budget_when_no_spend():
    _reset()
    assert budget.within_budget()
    assert budget.remaining_usd() == budget.MONTHLY_BUDGET_USD


def test_record_usage_accumulates_cost():
    _reset()
    # 1M input + 1M output = $1 + $5 = $6
    budget.record_usage(1_000_000, 1_000_000)
    assert abs(budget.current_spend_usd() - 6.0) < 0.001


def test_within_budget_false_when_cap_exceeded():
    _reset()
    # Push past the cap (20M output tokens = $100)
    budget.record_usage(0, 20_000_000)
    assert not budget.within_budget()
    assert budget.remaining_usd() == 0.0


def test_resets_on_new_month():
    _reset()
    budget.record_usage(0, 20_000_000)
    assert not budget.within_budget()

    # Simulate next month by mutating the stored month string
    budget._state["month"] = "1999-01"
    # Now the next call will detect a "new" month (current UTC) and reset
    assert budget.within_budget()
    assert budget.current_spend_usd() == 0.0


def test_remaining_clamps_to_zero_when_over():
    _reset()
    budget.record_usage(0, 20_000_000)
    assert budget.remaining_usd() == 0.0
