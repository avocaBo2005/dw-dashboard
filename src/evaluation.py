from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.transform import grand_total


EXPECTED_ELIGIBLE = 96_470
EXPECTED_LATE = 6_534
EXPECTED_LATE_RATE = 6.77


@dataclass(frozen=True)
class CheckResult:
    category: str
    name: str
    passed: bool
    actual: str
    expected: str

    def as_row(self) -> dict[str, Any]:
        row = asdict(self)
        return {
            "Nhóm": row["category"],
            "Kiểm tra": row["name"],
            "Kết quả": "PASS" if row["passed"] else "FAIL",
            "Thực tế": row["actual"],
            "Kỳ vọng": row["expected"],
        }


def response_rating(elapsed_ms: float) -> str:
    if elapsed_ms <= 500:
        return "Tốt"
    if elapsed_ms <= 1_500:
        return "Chấp nhận"
    return "Cần tối ưu"


def _valid_pivot_matrix(payload: dict[str, Any]) -> bool:
    row_headers = payload.get("row_headers")
    col_headers = payload.get("col_headers")
    matrix = payload.get("matrix")
    if not isinstance(row_headers, list) or not isinstance(col_headers, list):
        return False
    if not isinstance(matrix, list) or len(matrix) != len(row_headers):
        return False
    return all(isinstance(row, list) and len(row) == len(col_headers) for row in matrix)


def _rates_in_unit_interval(values: list[object]) -> bool:
    try:
        return bool(values) and all(0 <= float(value) <= 1 for value in values)
    except (TypeError, ValueError):
        return False


def _valid_tradeoff_row(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    try:
        promised_days = float(row["promised_days_avg"])
        segments_scored = int(row["n_segments_scored"])
        segments_met = int(row["n_segments_met"])
    except (KeyError, TypeError, ValueError):
        return False
    return promised_days >= 0 and 0 <= segments_met <= segments_scored


def evaluate_payloads(payloads: dict[str, dict[str, Any]]) -> tuple[list[CheckResult], dict[str, Any]]:
    api_ok = payloads.get("API health", {}).get("data", {}).get("status") == "ok"
    db_ok = payloads.get("Database health", {}).get("status") == "ok"
    sales_total = grand_total(payloads.get("Sales OLAP", {}))
    delivery_total = grand_total(payloads.get("Delivery OLAP", {}))
    distribution = payloads.get("Delivery distribution", {})
    summary = distribution.get("summary", {})
    eligible = int(delivery_total.get("eligible_orders") or 0)
    distributed_total = int(distribution.get("meta", {}).get("total") or -1)
    late = int(summary.get("late_orders") or 0)
    late_rate = float(summary.get("late_rate") or 0)
    review_groups = {
        row.get("group")
        for row in payloads.get("Review by delay", {}).get("data", [])
    }
    dss_rows = payloads.get("DSS scorecard", {}).get("data", [])
    dss_weights = payloads.get("DSS config", {}).get("data", {}).get("weights", [])
    weight_sum = sum(float(item.get("weight") or 0) for item in dss_weights)
    pivot_metadata = payloads.get("Pivot metadata", {}).get("data", {})
    pivot_metadata_ok = all(
        isinstance(pivot_metadata.get(cube, {}).get("axes"), list)
        and bool(pivot_metadata.get(cube, {}).get("axes"))
        and isinstance(pivot_metadata.get(cube, {}).get("measures"), list)
        and bool(pivot_metadata.get(cube, {}).get("measures"))
        for cube in ("sales", "delivery")
    )
    sales_pivot_ok = _valid_pivot_matrix(payloads.get("Sales pivot", {}))
    delivery_pivot_ok = _valid_pivot_matrix(payloads.get("Delivery pivot", {}))
    buffer_data = payloads.get("Delivery buffer", {}).get("data", {})
    buffer_summary = buffer_data.get("summary", {})
    expected_policies = {"current_k0", "global_k", "state_k"}
    buffer_policies_ok = (
        isinstance(buffer_summary, dict)
        and expected_policies.issubset(buffer_summary)
    )
    buffer_rates = [
        buffer_summary.get(policy, {}).get("late_rate")
        for policy in expected_policies
        if isinstance(buffer_summary.get(policy), dict)
    ]
    buffer_rates_ok = _rates_in_unit_interval(buffer_rates) and len(buffer_rates) == 3
    buffer_segments = buffer_data.get("segments", [])
    buffer_segments_ok = isinstance(buffer_segments, list) and len(buffer_segments) > 0
    tradeoff_rows = payloads.get("Delivery buffer tradeoff", {}).get("data", [])
    tradeoff_rates = [
        row.get("late_rate") for row in tradeoff_rows if isinstance(row, dict)
    ] if isinstance(tradeoff_rows, list) else []
    tradeoff_ok = (
        isinstance(tradeoff_rows, list)
        and len(tradeoff_rows) > 0
        and len(tradeoff_rates) == len(tradeoff_rows)
        and _rates_in_unit_interval(tradeoff_rates)
        and all(_valid_tradeoff_row(row) for row in tradeoff_rows)
    )

    checks = [
        CheckResult("Sẵn sàng", "API hoạt động", api_ok, str(api_ok), "True"),
        CheckResult("Sẵn sàng", "Database kết nối", db_ok, str(db_ok), "True"),
        CheckResult(
            "Dữ liệu", "Sales có dữ liệu", int(sales_total.get("n_orders") or 0) > 0,
            f"{int(sales_total.get('n_orders') or 0):,} đơn", "> 0 đơn",
        ),
        CheckResult(
            "Nhất quán", "Delivery khớp distribution", eligible == distributed_total,
            f"{eligible:,} / {distributed_total:,}", "Hai tổng bằng nhau",
        ),
        CheckResult(
            "Đối soát ETL", "Eligible orders", eligible == EXPECTED_ELIGIBLE,
            f"{eligible:,}", f"{EXPECTED_ELIGIBLE:,}",
        ),
        CheckResult(
            "Đối soát ETL", "Late orders", late == EXPECTED_LATE,
            f"{late:,}", f"{EXPECTED_LATE:,}",
        ),
        CheckResult(
            "Đối soát ETL", "Late rate", abs(late_rate - EXPECTED_LATE_RATE) <= 0.01,
            f"{late_rate:.2f}%", f"{EXPECTED_LATE_RATE:.2f}% ± 0.01",
        ),
        CheckResult(
            "Nhất quán", "Review đủ hai nhóm",
            review_groups == {"late", "not_late"},
            ", ".join(sorted(str(item) for item in review_groups)), "late, not_late",
        ),
        CheckResult(
            "DSS", "Scorecard trả kết quả", len(dss_rows) > 0,
            f"{len(dss_rows):,} dòng", "> 0 dòng",
        ),
        CheckResult(
            "DSS", "Tổng trọng số hợp lệ", bool(dss_weights) and weight_sum > 0,
            f"{weight_sum:.2f}", "> 0",
        ),
        CheckResult(
            "Pivot", "Metadata đủ hai cube", pivot_metadata_ok,
            ", ".join(sorted(pivot_metadata)) if isinstance(pivot_metadata, dict) else "Không hợp lệ",
            "sales, delivery",
        ),
        CheckResult(
            "Pivot", "Sales matrix đúng kích thước", sales_pivot_ok,
            str(sales_pivot_ok), "True",
        ),
        CheckResult(
            "Pivot", "Delivery matrix đúng kích thước", delivery_pivot_ok,
            str(delivery_pivot_ok), "True",
        ),
        CheckResult(
            "Delivery Buffer", "Đủ ba chính sách", buffer_policies_ok,
            ", ".join(sorted(buffer_summary)) if isinstance(buffer_summary, dict) else "Không hợp lệ",
            "current_k0, global_k, state_k",
        ),
        CheckResult(
            "Delivery Buffer", "Tỷ lệ chính sách hợp lệ", buffer_rates_ok,
            ", ".join(str(value) for value in buffer_rates),
            "Ba tỷ lệ trong [0, 1]",
        ),
        CheckResult(
            "Delivery Buffer", "Có đánh giá theo bang", buffer_segments_ok,
            f"{len(buffer_segments) if isinstance(buffer_segments, list) else 0} bang", "> 0 bang",
        ),
        CheckResult(
            "Delivery Buffer", "Trade-off hợp lệ", tradeoff_ok,
            f"{len(tradeoff_rows) if isinstance(tradeoff_rows, list) else 0} dòng",
            "> 0 dòng, tỷ lệ và số ngày hợp lệ",
        ),
    ]
    metrics = {
        "eligible": eligible,
        "late": late,
        "late_rate": late_rate,
        "passed": sum(check.passed for check in checks),
        "total": len(checks),
    }
    return checks, metrics
