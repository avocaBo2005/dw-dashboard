from src.evaluation import evaluate_payloads, response_rating


def payloads():
    return {
        "API health": {"data": {"status": "ok"}},
        "Database health": {"status": "ok"},
        "Sales OLAP": {"data": [{"level": 0, "measures": {"n_orders": 1}}]},
        "Delivery OLAP": {
            "data": [{"level": 0, "measures": {"eligible_orders": 96_470}}]
        },
        "Delivery distribution": {
            "meta": {"total": 96_470},
            "summary": {"late_orders": 6_534, "late_rate": 6.77},
        },
        "Review by delay": {"data": [{"group": "late"}, {"group": "not_late"}]},
        "DSS scorecard": {"data": [{"seller_id": "abc"}]},
        "DSS config": {"data": {"weights": [{"criterion": "gmv", "weight": 0.4}]}},
    }


def test_evaluate_payloads_all_pass():
    checks, metrics = evaluate_payloads(payloads())
    assert all(check.passed for check in checks)
    assert metrics == {
        "eligible": 96_470,
        "late": 6_534,
        "late_rate": 6.77,
        "passed": 10,
        "total": 10,
    }


def test_evaluate_payloads_detects_reconciliation_error():
    data = payloads()
    data["Delivery distribution"]["meta"]["total"] = 1
    checks, _ = evaluate_payloads(data)
    result = {check.name: check.passed for check in checks}
    assert result["Delivery khớp distribution"] is False


def test_response_rating_boundaries():
    assert response_rating(500) == "Tốt"
    assert response_rating(501) == "Chấp nhận"
    assert response_rating(1_501) == "Cần tối ưu"
