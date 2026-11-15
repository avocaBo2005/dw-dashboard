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
        "Pivot metadata": {
            "data": {
                "sales": {"axes": [{"key": "year"}], "measures": [{"key": "total_price"}]},
                "delivery": {"axes": [{"key": "year"}], "measures": [{"key": "late_rate"}]},
            }
        },
        "Sales pivot": {
            "row_headers": [{"key": "2017"}],
            "col_headers": [{"key": "health"}],
            "matrix": [[100.0]],
        },
        "Delivery pivot": {
            "row_headers": [{"key": "2017"}],
            "col_headers": [{"key": "SP"}],
            "matrix": [[0.05]],
        },
        "Delivery buffer": {
            "data": {
                "summary": {
                    "current_k0": {"late_rate": 0.07},
                    "global_k": {"late_rate": 0.05},
                    "state_k": {"late_rate": 0.052},
                },
                "segments": [{"segment": "SP"}],
            }
        },
        "Delivery buffer tradeoff": {
            "data": [
                {
                    "late_rate": 0.05,
                    "promised_days_avg": 28,
                    "n_segments_scored": 14,
                    "n_segments_met": 8,
                }
            ]
        },
    }


def test_evaluate_payloads_all_pass():
    checks, metrics = evaluate_payloads(payloads())
    assert all(check.passed for check in checks)
    assert metrics == {
        "eligible": 96_470,
        "late": 6_534,
        "late_rate": 6.77,
        "passed": 17,
        "total": 17,
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


def test_evaluate_payloads_detects_invalid_pivot_shape_and_buffer_rate():
    data = payloads()
    data["Sales pivot"]["matrix"] = []
    data["Delivery buffer"]["data"]["summary"]["state_k"]["late_rate"] = 1.5

    checks, _ = evaluate_payloads(data)
    result = {check.name: check.passed for check in checks}
    assert result["Sales matrix đúng kích thước"] is False
    assert result["Tỷ lệ chính sách hợp lệ"] is False
