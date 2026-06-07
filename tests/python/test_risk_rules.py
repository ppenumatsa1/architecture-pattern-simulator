from shared.python.risk_rules import evaluate_risk


def test_evaluate_risk_returns_low_for_empty_payload() -> None:
    result = evaluate_risk({"id": "sub-1", "payload": {}})

    assert result.submission_id == "sub-1"
    assert result.score == 0
    assert result.risk_level == "LOW"
    assert result.reasons == []


def test_evaluate_risk_returns_medium_at_boundary_score() -> None:
    result = evaluate_risk(
        {
            "id": "sub-2",
            "payload": {
                "amount": 20_000,
                "debtToIncome": 0.40,
            },
        }
    )

    assert result.score == 25
    assert result.risk_level == "MEDIUM"
    assert result.reasons == ["medium-amount", "elevated-debt-to-income"]


def test_evaluate_risk_accumulates_high_risk_reasons() -> None:
    result = evaluate_risk(
        {
            "id": "sub-3",
            "payload": {
                "amount": 60_000,
                "creditScore": 540,
                "debtToIncome": 0.52,
                "latePaymentsLast12Months": 4,
                "hasBankruptcy": True,
                "fraudFlag": True,
            },
        }
    )

    assert result.score == 165
    assert result.risk_level == "HIGH"
    assert result.reasons == [
        "high-amount",
        "very-low-credit-score",
        "high-debt-to-income",
        "multiple-late-payments",
        "bankruptcy-history",
        "fraud-flag",
    ]
