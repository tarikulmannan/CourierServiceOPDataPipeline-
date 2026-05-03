#!/bin/bash
# docs/create_courier_db.sh
# This runs inside the Postgres container on first startup.
# It creates your courier_db alongside Airflow's own database.

set -e  # Exit immediately if any command fails

echo "Creating courier_db..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    -- Create the database only if it doesn't already exist
    SELECT 'CREATE DATABASE courier_db'
    WHERE NOT EXISTS (
        SELECT FROM pg_database WHERE datname = 'courier_db'
    )\gexec

    -- Connect to courier_db and create your schemas
    \c courier_db

    CREATE SCHEMA IF NOT EXISTS raw;
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE SCHEMA IF NOT EXISTS core;
    CREATE SCHEMA IF NOT EXISTS marts;

  

EOSQL

# ← bash echo OUTSIDE the SQL block — correct
echo "courier_db and all schemas created successfully."
echo "Done."