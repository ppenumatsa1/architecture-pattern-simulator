from __future__ import annotations

from typing import Any

from .models import RiskResult, Submission


def evaluate_risk(submission: Submission | dict[str, Any]) -> RiskResult:
    """Deterministic POC risk scoring with simple additive rules."""
    parsed = submission if isinstance(submission, Submission) else _parse_submission(submission)
    payload = parsed.payload

    score = 0
    reasons: list[str] = []

    amount = _to_float(payload.get("amount"))
    if amount >= 50_000:
        score += 30
        reasons.append("high-amount")
    elif amount >= 20_000:
        score += 15
        reasons.append("medium-amount")

    credit_score = _to_int(payload.get("creditScore"), default=700)
    if credit_score < 580:
        score += 30
        reasons.append("very-low-credit-score")
    elif credit_score < 670:
        score += 15
        reasons.append("low-credit-score")

    debt_to_income = _to_float(payload.get("debtToIncome"))
    if debt_to_income >= 0.5:
        score += 20
        reasons.append("high-debt-to-income")
    elif debt_to_income >= 0.35:
        score += 10
        reasons.append("elevated-debt-to-income")

    late_payments = _to_int(payload.get("latePaymentsLast12Months"), default=0)
    if late_payments >= 3:
        score += 20
        reasons.append("multiple-late-payments")
    elif late_payments > 0:
        score += 10
        reasons.append("recent-late-payments")

    if _to_bool(payload.get("hasBankruptcy")):
        score += 25
        reasons.append("bankruptcy-history")

    if _to_bool(payload.get("fraudFlag")):
        score += 40
        reasons.append("fraud-flag")

    risk_level = "HIGH" if score >= 60 else "MEDIUM" if score >= 25 else "LOW"
    return RiskResult(
        submission_id=parsed.id,
        score=score,
        risk_level=risk_level,
        reasons=reasons,
    )


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _parse_submission(submission: dict[str, Any]) -> Submission:
    if hasattr(Submission, "model_validate"):
        return Submission.model_validate(submission)
    return Submission.parse_obj(submission)
