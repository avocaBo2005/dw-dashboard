# Evaluation checklist

## Correctness

- Reconcile row counts and KPI totals with the DW validation script.
- Confirm the complete-data delayed-delivery rate is approximately 6.77%.
- Confirm empty filters and zero denominators do not cause errors.
- Confirm seller order counts use distinct orders.

## Performance

- Record page load time for Overview, Sales, Delivery, and Decision Support.
- Use `EXPLAIN (ANALYZE, BUFFERS)` for the slowest queries.
- Add materialized aggregates only if the measured response time requires them.

## Decision usefulness

- Demonstrate one monthly sales drill-down.
- Demonstrate one high-delay customer-state segment.
- Compare review scores for delayed and non-delayed eligible orders.
- Explain that rule-based alerts prioritize investigation and do not prove causality.

## Known limitations

- Full-refresh ETL and snapshot order status.
- No payment or geolocation facts in the current warehouse.
- No seller-level delivery attribution.
- No seller history or incremental loading.

