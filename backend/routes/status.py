from fastapi import APIRouter
import services.claude_budget as claude_budget

router = APIRouter()


@router.get("/status")
def status():
    """Public health/degraded-state endpoint. Frontend reads this to show a
    warm banner when the monthly Claude budget is out."""
    within = claude_budget.within_budget()
    return {
        "degraded": not within,
        "claude_budget": {
            "remaining_usd": round(claude_budget.remaining_usd(), 2),
            "resets_on": claude_budget.reset_date_iso(),
        },
    }
