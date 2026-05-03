# airflow/Dockerfile

# Always pin the exact version so your team gets identical environments
FROM apache/airflow:2.10.5

# Switch to root temporarily to install any OS-level packages
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to the airflow user (security best practice —
# never run Airflow as root in production)
USER airflow

# Install your Python dependencies
# These are the libraries your gdrive_to_postgres.py needs

#RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    pandas \
    openpyxl \
    sqlalchemy \
    psycopg2-binary \
    google-api-python-client \
    google-auth \
    google-auth-httplib2 \
    google-auth-oauthlib \
    apache-airflow-providers-postgres \
    apache-airflow-providers-google