# Use the specific Python version you are working with
FROM python:3.13-slim

# Install system dependencies required for psycopg2 (Postgres driver)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files
COPY . .

# Run the script
CMD ["python", "Scripts/gdrive_to_postgres.py"]