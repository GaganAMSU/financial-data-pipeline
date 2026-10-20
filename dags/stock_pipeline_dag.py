"""Daily pipeline: pull stock prices, then run dbt to build staging + mart models.

DAG = the dependency graph of tasks. Airflow's scheduler evaluates the cron
schedule below and, each time it fires, creates one "DAG run" that executes
the tasks in dependency order (ingest_prices -> dbt_run -> dbt_test).
"""
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

DBT_PROJECT_DIR = "/opt/airflow/dbt/financial_pipeline"
DBT_PROFILES_DIR = "/opt/airflow/dbt"
DBT_BIN = "/opt/dbt_venv/bin/dbt"


def _run_ingestion():
    from ingestion.fetch_prices import main

    main()


with DAG(
    dag_id="stock_price_pipeline",
    description="Ingest daily stock prices and build dbt models on top of them",
    schedule="0 22 * * 1-5",  # 22:00 UTC, weekdays — after US markets close
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finance", "learning-project"],
) as dag:
    ingest_prices = PythonOperator(
        task_id="ingest_prices",
        python_callable=_run_ingestion,
    )

    dbt_opts = f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{DBT_BIN} run {dbt_opts}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{DBT_BIN} test {dbt_opts}",
    )

    ingest_prices >> dbt_run >> dbt_test
