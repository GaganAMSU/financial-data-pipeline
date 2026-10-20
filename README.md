# Financial Data Pipeline

A daily stock-price pipeline built to learn the tools that show up constantly
in data engineering job postings: **Airflow** (orchestration), **dbt**
(SQL transformation + testing), **Postgres** (storage), **Docker Compose**
(reproducible infra), and **GitHub Actions** (CI).

## What it does

```
yfinance API --(ingestion/fetch_prices.py)--> raw.stock_prices (Postgres)
                                                      |
                                              dbt run (Airflow DAG)
                                                      v
                                    staging.stg_prices (cleaned/cast)
                                                      |
                              +-----------------------+-----------------------+
                              v                                               v
              marts.fct_daily_returns                        marts.fct_moving_averages
              (day-over-day % return)                         (20-day / 50-day SMA)
```

Every weekday at 22:00 UTC (after US markets close), an Airflow DAG:
1. Pulls the last ~10 days of OHLCV data for a configurable ticker list from
   Yahoo Finance and upserts it into `raw.stock_prices` (idempotent — re-runs
   don't create duplicates).
2. Runs `dbt run` to rebuild the staging view and the two mart tables.
3. Runs `dbt test` to check the data actually looks right before calling the
   run successful.

## Why these tools

| Tool | Role | Why it's here |
|---|---|---|
| **Airflow** | Scheduling & dependency graph between tasks | The de facto standard orchestrator; DAGs/operators/schedules are vocabulary used everywhere in DE job descriptions |
| **dbt** | SQL transformations, testing, lineage | Separates "move data" (Airflow/Python) from "model data" (SQL you can test and document) — the standard modern analytics-engineering split |
| **Postgres** | Storage for both Airflow's metadata and our actual data | Free, ubiquitous, good enough to learn every concept here |
| **Docker Compose** | Reproducible multi-service local environment | How real data stacks get run locally and in CI |
| **GitHub Actions** | CI on every push | Lint + unit tests + dbt project validation, so broken code never reaches `main` unnoticed |

## Running it

This runs inside Docker, which lives in WSL2 on this machine. The project
folder is on the Windows filesystem, so Docker Compose commands run from a
WSL shell pointed at the `/mnt/c/...` path.

```bash
# from a WSL terminal (or `wsl` from PowerShell/Windows Terminal)
cd /mnt/c/Users/gagan/projects/financial-data-pipeline

cp .env.example .env   # then edit .env if you want different tickers/password

docker compose build
docker compose up -d
```

First build takes a few minutes (pulls Airflow + Postgres images, installs
dbt into its own virtualenv). Once it's up:

- Airflow UI: http://localhost:8080 (login `admin` / `admin`)
- Un-pause the `stock_price_pipeline` DAG and trigger it manually to run
  immediately instead of waiting for the schedule.

Check the results directly in Postgres:

```bash
docker compose exec postgres psql -U postgres -d findata \
  -c "select * from marts.fct_daily_returns order by price_date desc limit 10;"
```

Tear down:

```bash
docker compose down        # stop containers, keep data
docker compose down -v     # also wipe the Postgres volume (fresh start)
```

## Project layout

```
dags/                   Airflow DAG definitions
ingestion/               Python ingestion script (yfinance -> raw.stock_prices)
dbt/financial_pipeline/  dbt project: staging views, mart tables, tests
sql/init.sql             One-time Postgres bootstrap (creates findata db + raw schema)
docker/                  Custom Airflow image + its Python dependencies
tests/                   pytest unit tests for the ingestion logic
.github/workflows/ci.yml Lint, unit tests, dbt project validation
```

## Local dev (without Docker)

For editing/testing the ingestion code or dbt models without spinning up the
full stack:

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

dbt needs its own virtualenv even locally — its pinned dependencies (protobuf, click, jinja2)
conflict with pandas/pytest/ruff's, the same reason it gets a separate venv inside the
Airflow image:

```bash
py -m venv .venv-dbt
.venv-dbt\Scripts\activate
pip install -r requirements-dbt.txt
dbt parse --project-dir dbt/financial_pipeline --profiles-dir dbt   # set POSTGRES_PASSWORD first
```

## Concepts worth understanding from this project

- **Idempotent loads**: `ingestion/fetch_prices.py` uses `INSERT ... ON
  CONFLICT DO UPDATE` keyed on `(ticker, price_date)`, so re-running the DAG
  for a day that already loaded just overwrites it instead of duplicating
  rows. Pipelines that get re-run (backfills, retries) need this.
- **staging vs. marts**: `stg_prices` only renames/casts columns — it never
  does business logic. The marts (`fct_daily_returns`, `fct_moving_averages`)
  are where the actual analysis happens. This separation means a source
  schema change only needs a fix in one staging model, not every mart.
- **dbt `ref()` and `source()`**: `ref('stg_prices')` instead of a hardcoded
  table name is what lets dbt compute the build order automatically and draw
  the lineage graph (`dbt docs generate`).
- **dbt tests**: schema tests (`not_null` in `schema.yml`) catch column-level
  problems; the singular test (`tests/assert_no_duplicate_ticker_dates.sql`)
  catches a grain violation that a generic test can't express as easily.
- **Environment isolation**: dbt lives in its own virtualenv inside the
  Airflow image (see `docker/Dockerfile.airflow`) because dbt and Airflow pin
  conflicting versions of shared dependencies (click, jinja2). This is the
  same problem tools like `astronomer-cosmos` exist to solve more elegantly.

## Possible next steps

- Add a volatility or Sharpe-ratio mart on top of `fct_daily_returns`.
- Add `dbt_utils` for richer generic tests (e.g. composite uniqueness).
- Point a BI tool (Metabase, Looker Studio) at the `marts` schema.
- Swap the hand-rolled dbt-in-a-venv trick for `astronomer-cosmos`.
- Add Slack/email alerting on DAG failure.
