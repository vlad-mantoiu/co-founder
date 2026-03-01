"""Budget management package for the autonomous agent.

Provides BudgetService for daily allowance calculation, per-call cost tracking,
and circuit breaker enforcement (BDGT-01, BDGT-06, BDGT-07).
"""

from app.agent.budget.service import MODEL_COST_WEIGHTS, BudgetExceededError, BudgetService

__all__ = ["BudgetService", "BudgetExceededError", "MODEL_COST_WEIGHTS"]
