# Olist Data Warehouse Dashboard

Separate Streamlit UI and OLAP contract for the CO4031 Olist data warehouse.
The dashboard consumes PostgreSQL data produced by the DW/ETL repository; it
does not read source CSV files directly.

## Features

- Executive overview with sales, delivery, and review KPIs.
- Sales analysis by time, product category, seller, and seller state.
- Delivery and review analysis by purchase time and customer state.
- Rule-based decision-support page for prioritizing risky segments.
- PostgreSQL OLAP examples using roll-up, cube, slice, dice, and pivot-like
  conditional aggregation.

## Prerequisites

- PostgreSQL DW running on port `5432`.
- The DW ETL has completed successfully.
- Python 3.11 or newer, or Docker Desktop.

## Database setup

Apply the analytics views after loading the warehouse:

```bash
psql -h localhost -p 5432 -U dw_user -d olist_dw \
  -v ON_ERROR_STOP=1 -f sql/001_create_analytics_views.sql
```

The expected grains and KPI rules are documented in
[`docs/data_contract.md`](docs/data_contract.md).

## Run locally

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>.

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Run with Docker

Copy `.env.example` to `.env`, set the database password, then run:

```bash
docker compose up --build
```

The Compose configuration uses `host.docker.internal` to reach the PostgreSQL
container exposed by the separate DW repository.

## Tests

```bash
pytest
```

The evaluation and demonstration checklist is in
[`docs/evaluation.md`](docs/evaluation.md).

## Metric interpretation

- `item_value` is source item price, not profit or net revenue.
- Seller order counts use `COUNT(DISTINCT order_id)`.
- Delivery rates use only eligible delivered orders in the denominator.
- Delivery delays are not attributed to individual sellers.
- Review facts are aggregated before joining to order-grain analytical data.

