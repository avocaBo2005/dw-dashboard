import pytest

from src.delivery_buffer import curve_frame, segments_frame, summary_frame, tradeoff_frame


def overview_payload():
    evaluation = {
        "k": 3,
        "late_rate_test": 0.04,
        "status": "met",
        "ci_low": 0.03,
        "ci_high": 0.05,
    }
    return {
        "data": {
            "summary": {
                "current_k0": {
                    "policy": "current_k0",
                    "late_rate": 0.07,
                    "promised_days_avg": 25,
                    "n_segments_scored": 14,
                    "n_segments_met": 2,
                    "pct_orders_in_met": 0.52,
                    "worst_segment": "PA",
                    "worst_late_rate": 0.18,
                }
            },
            "segments": [
                {
                    "segment": "SP",
                    "n_test": 100,
                    "fallback": False,
                    "current_k0": evaluation,
                    "global_k": evaluation,
                    "state_k": evaluation,
                }
            ],
        }
    }


def test_summary_and_segments_convert_ratios_to_percent():
    summary = summary_frame(overview_payload())
    segments = segments_frame(overview_payload())

    assert summary.loc[0, "Tỷ lệ trễ (%)"] == pytest.approx(7)
    assert summary.loc[0, "Tỷ lệ đơn thuộc bang đạt (%)"] == pytest.approx(52)
    assert segments.loc[0, "Buffer theo bang · tỷ lệ trễ (%)"] == pytest.approx(4)
    assert segments.loc[0, "Buffer theo bang · CI cao (%)"] == pytest.approx(5)


def test_curve_and_tradeoff_convert_ratios_to_percent():
    curve = curve_frame(
        {"data": {"curve": [{"k": 1, "late_rate_train": 0.05, "late_rate_test": 0.06}]}}
    )
    tradeoff = tradeoff_frame(
        {"data": [{"safety_margin": 0.005, "late_rate": 0.04, "pct_orders_in_met": 0.8}]}
    )

    assert curve.loc[0, "late_rate_test_pct"] == pytest.approx(6)
    assert tradeoff.loc[0, "safety_margin_pct"] == pytest.approx(0.5)
    assert tradeoff.loc[0, "pct_orders_in_met_pct"] == pytest.approx(80)
