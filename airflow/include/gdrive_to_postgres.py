import io
import os
import logging
from sqlalchemy import create_engine, text
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd

# ─────────────────────────────────────────────────────────────────────
# Use Airflow's logger instead of print().
# This means all output appears correctly in the Airflow task logs UI
# rather than being lost in container stdout.
# ─────────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Constants
# FOLDER_ID: the Google Drive folder that contains your Excel files.
# SCOPES: read-only access is all we need — principle of least privilege.
# ─────────────────────────────────────────────────────────────────────
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = '1suEcgCiBkOeBKTqrj5g-XpOfmTiNBCpE'
MIME_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# ─────────────────────────────────────────────────────────────────────
# These are the exact table names your sanity check expects.
# If a file lands in raw.* but isn't in this list, it's still loaded —
# the check only validates these four critical tables.
# ─────────────────────────────────────────────────────────────────────
EXPECTED_TABLES = ['orders', 'order_logs', 'delivery_men', 'customers']


def get_db_engine():
    """
    Builds a SQLAlchemy engine from environment variables.

    All variables are injected by Docker via the env_file + environment
    blocks in docker-compose.yaml. Nothing is hardcoded here so the
    same script works in any environment (local, staging, production)
    just by changing the .env file.

    DB_HOST = 'postgres' (the service name in docker-compose.yaml)
    DB_NAME = 'courier_db' (your data warehouse, not Airflow's internal db)
    """
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_HOST = os.getenv("DB_HOST", "postgres")   # 'postgres' matches the service name
    DB_PORT = os.getenv("DB_PORT", "5432")

    missing = [k for k, v in {
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASS,
        "DB_NAME": DB_NAME,
        "DB_HOST": DB_HOST,
    }.items() if not v]

    if missing:
        raise ValueError(
            f"[ETL] Missing required environment variables: {missing}\n"
            "Check your .env file and the environment block in docker-compose.yaml."
        )

    db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    log.info(f"[ETL] Connecting to '{DB_NAME}' at {DB_HOST}:{DB_PORT} as '{DB_USER}'")

    return create_engine(
        db_url,
        # Keep a small pool — Airflow tasks are short-lived,
        # we don't need many persistent connections.
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,   # Test connection health before using it
    )


def get_drive_service():
    """
    Authenticates with Google Drive using the service account credentials file.

    The path comes from GOOGLE_APPLICATION_CREDENTIALS, which is set in
    docker-compose.yaml to /opt/airflow/include/credentials.json —
    the file you copied into airflow/include/.
    """
    cred_path = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/opt/airflow/include/credentials.json"   # fallback to known container path
    )

    if not os.path.exists(cred_path):
        raise FileNotFoundError(
            f"[ETL] credentials.json not found at: {cred_path}\n"
            "Make sure you copied credentials.json into airflow/include/"
        )

    log.info(f"[ETL] Loading Google credentials from: {cred_path}")
    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)


def _clean_table_name(filename: str) -> str:
    """
    Converts a filename like 'Order Logs.xlsx' into a clean
    PostgreSQL table name like 'order_logs'.

    Rules:
    - Strip the .xlsx extension
    - Lowercase everything
    - Replace spaces and hyphens with underscores
    - Strip any leading/trailing whitespace
    """
    return (
        filename
        .replace('.xlsx', '')
        .strip()
        .lower()
        .replace(' ', '_')
        .replace('-', '_')
    )


def ingest_gdrive_to_postgres():
    """
    Main ingestion function — this is what the Airflow DAG calls.

    Flow:
    1. Authenticate with Google Drive
    2. List all .xlsx files in FOLDER_ID
    3. Download each file into memory (no disk writes needed)
    4. Read into a Pandas DataFrame
    5. Load into raw.<table_name> in courier_db
       - if_exists='replace' drops and recreates the table each run
         giving you a clean, idempotent load every time
    """
    service = get_drive_service()
    engine = get_db_engine()

    # List all Excel files in the target folder
    query = f"'{FOLDER_ID}' in parents and mimeType = '{MIME_XLSX}'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if not files:
        # Log a warning but don't fail — the Drive folder might legitimately
        # be empty during a test run. The sanity check will catch missing tables.
        log.warning(
            f"[ETL] No Excel files found in Drive folder: {FOLDER_ID}\n"
            "If this is unexpected, check the folder ID and service account permissions."
        )
        return

    log.info(f"[ETL] Found {len(files)} file(s) to process.")
    loaded_tables = []

    for file in files:
        file_name = file['name']
        file_id = file['id']
        table_name = _clean_table_name(file_name)

        log.info(f"[ETL] Processing: '{file_name}' → raw.{table_name}")

        try:
            # Download file content directly into memory as a byte stream.
            # We never write to disk — cleaner and faster.
            request = service.files().get_media(fileId=file_id)
            file_content = io.BytesIO(request.execute())

            # Read into DataFrame
            df = pd.read_excel(file_content, engine='openpyxl')
            row_count = len(df)

            if df.empty:
                log.warning(f"[ETL] '{file_name}' is empty — skipping load.")
                continue

            # Load into PostgreSQL raw schema
            # if_exists='replace' makes this idempotent —
            # safe to re-run without creating duplicate data
            df.to_sql(
                name=table_name,
                con=engine,
                schema='raw',
                if_exists='replace',
                index=False,          # Don't write the DataFrame index as a column
                chunksize=1000,       # Write in batches — handles large files safely
                method='multi',       # Faster bulk insert
            )

            log.info(f"[ETL] ✓ Loaded {row_count} rows → raw.{table_name}")
            loaded_tables.append(table_name)

        except Exception as e:
            # Log the error with full context but re-raise so Airflow
            # marks this task as FAILED and triggers the retry policy
            log.error(f"[ETL] ✗ Failed to process '{file_name}': {e}")
            raise

    log.info(
        f"[ETL] Ingestion complete. "
        f"{len(loaded_tables)}/{len(files)} file(s) loaded successfully: {loaded_tables}"
    )


def run_sanity_check():
    """
    Validates that all expected tables exist and contain data.
    This is what the second Airflow task calls — after ingestion succeeds.

    Raises ValueError if any table is empty, which causes Airflow to
    mark the task as FAILED so you get alerted immediately.
    """
    engine = get_db_engine()

    # Build the UNION query dynamically from EXPECTED_TABLES
    # so adding a new table only requires updating the list above,
    # not editing SQL here.
    union_parts = "\n        UNION ALL\n        ".join(
        f"SELECT '{tbl}' AS table_name, COUNT(*) AS row_count FROM raw.{tbl}"
        for tbl in EXPECTED_TABLES
    )
    query = text(f"SELECT table_name, row_count FROM ({union_parts}) AS counts")

    log.info("[ETL] Running sanity check on raw schema tables...")

    with engine.connect() as conn:
        df_check = pd.read_sql(query, conn)

        # Format nicely for Airflow task logs
        log.info("\n" + "─" * 40)
        log.info("  SANITY CHECK RESULTS")
        log.info("─" * 40)
        for _, row in df_check.iterrows():
            status = "✓" if row['row_count'] > 0 else "✗ EMPTY"
            log.info(f"  raw.{row['table_name']:<20} {row['row_count']:>8} rows  {status}")
        log.info("─" * 40)

        # Find any empty tables
        empty_tables = df_check[df_check['row_count'] == 0]['table_name'].tolist()

        if empty_tables:
            # Raise — this causes Airflow to mark the task FAILED
            raise ValueError(
                f"[ETL] Sanity check FAILED. Empty tables detected: {empty_tables}\n"
                "Check the ingestion task logs for errors."
            )

        log.info("[ETL] Sanity check PASSED. All tables have data. ✓")