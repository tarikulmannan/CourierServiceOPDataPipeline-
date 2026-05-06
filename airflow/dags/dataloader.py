# ─────────────────────────────────────────────────────────────────────────────
# courier_ingestion_dag_decorator.py
# METHOD: Decorator style (@dag, @task) — the modern Airflow 2.x way
#
# Place this file in: airflow/dags/courier_ingestion_dag.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import logging
from datetime import datetime, timedelta

# Add include/ to Python path so we can import our ETL functions
sys.path.insert(0, '/opt/airflow/include')

# Airflow decorator imports
from airflow.decorators import dag, task

# Import your ETL functions from airflow/include/gdrive_to_postgres.py
from gdrive_to_postgres import ingest_gdrive_to_postgres, run_sanity_check

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# @dag decorator turns this function into a DAG.
# Everything INSIDE the function is the DAG's structure.
# ─────────────────────────────────────────────────────────────────────────────
@dag(
    dag_id='courier_data_ingestion',

    description='Ingest Excel files from Google Drive into PostgreSQL raw schema',

    # Cron schedule: runs every day at 2:00 AM UTC
    # ┌─ minute (0)
    # │ ┌─ hour (2)
    # │ │ ┌─ day of month (*)  = every day
    # │ │ │ ┌─ month (*)       = every month
    # │ │ │ │ ┌─ weekday (*)   = any day of week
    # │ │ │ │ │
    #schedule='0 2 * * *',
    schedule=None,
    start_date=datetime(2025, 1, 1),

    # catchup=False means: don't backfill all the missed runs
    # between start_date and today. Just run going forward.
    catchup=False,

    # If a DAG run is still going when the next schedule fires,
    # don't start a new one — wait for the current one to finish.
    max_active_runs=1,

    # Applied to every task inside this DAG
    default_args={
        'owner': 'courier_team',
        'retries': 1,                        # Retry once on failure
        'retry_delay': timedelta(minutes=5), # Wait 5 mins before retrying
        'email_on_failure': False,           # Set True when you add email config
        'email_on_retry': False,
    },

    tags=['ingestion', 'gdrive', 'postgres', 'raw'],
)
def courier_ingestion():
    """
    ### Courier Data Ingestion Pipeline

    This DAG loads Excel files from a Google Drive folder into the
    PostgreSQL `raw` schema in `courier_db`.

    **Tasks (in order):**
    1. `ingest_gdrive_to_postgres` — downloads each .xlsx file from Drive
       and loads it into `raw.<table_name>`
    2. `run_sanity_check` — validates that all expected tables exist
       and contain data. Fails loudly if any table is empty.

    **Schedule:** Daily at 02:00 UTC

    **On failure:** The failed task retries once after 5 minutes.
    Check the task logs in the Airflow UI for details.
    """

    # ─────────────────────────────────────────────────────────────────
    # @task decorator turns this function into an Airflow Task.
    # Airflow handles all the scheduling, retries, and logging for it.
    #
    # Notice: we're wrapping our imported functions in @task so that
    # Airflow can treat them as first-class tasks with their own
    # log output, retry logic, and state tracking in the UI.
    # ─────────────────────────────────────────────────────────────────

    @task(task_id='ingest_gdrive_to_postgres')
    def task_ingest():
        """
        Downloads all .xlsx files from the Google Drive folder
        and loads them into the raw schema in courier_db.
        """
        log.info("[DAG] Starting Google Drive ingestion task...")
        ingest_gdrive_to_postgres()
        log.info("[DAG] Ingestion task completed.")

    @task(task_id='run_sanity_check')
    def task_sanity_check():
        """
        Validates row counts across all expected raw tables.
        Raises an error if any table is empty — causing Airflow
        to mark this task as FAILED so you get notified.
        """
        log.info("[DAG] Starting sanity check task...")
        run_sanity_check()
        log.info("[DAG] Sanity check task completed.")

    # ─────────────────────────────────────────────────────────────────
    # Task dependency — the >> operator means:
    # "run task_ingest first, then run task_sanity_check"
    #
    # If task_ingest fails → task_sanity_check is skipped automatically
    # ─────────────────────────────────────────────────────────────────
    task_ingest() >> task_sanity_check()


# ─────────────────────────────────────────────────────────────────────────────
# This line is REQUIRED with the decorator pattern.
# It actually instantiates the DAG by calling the function.
# Without this line, Airflow cannot discover the DAG.
# ─────────────────────────────────────────────────────────────────────────────
courier_ingestion()