# Courier ETL Pipeline

This project automates the extraction of courier data from Excel files and loads it into a PostgreSQL database using Docker and Python.

## 🚀 Getting Started

Follow these steps to set up the environment and run the pipeline on your machine.

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [pgAdmin 4](https://www.pgadmin.org/download/) installed for database visualization.

### 2. Environment Setup
The project uses environment variables to manage database credentials. 

1. Create a file named `.env` in the root directory.
2. Copy the following template and fill in your preferred credentials:

```text
DB_HOST=db
DB_USER=project_admin
DB_PASSWORD=YourSecurePassword123
DB_NAME=courier_db
```

**Note:** If you use special characters (like `@`) in your password, the Python script is configured to handle the encoding automatically using `urllib.parse`.

---

### 3. How to Run the Pipeline

1. Place your `.xlsx` files into the `/Scripts` folder.

2. Open your terminal in the project root and run:

```bash
docker-compose up --build
```

**What this does:**

- **Initializes Database:** Starts the PostgreSQL container.
- **Builds ETL:** Compiles the latest Python code into a Docker image.
- **Automated Load:** Scans the folder, processes every `.xlsx` file, and creates a matching table in PostgreSQL.


### 4. Viewing the Data in pgAdmin

To connect to the database from your host machine (laptop), use these settings in pgAdmin:

- **Host:** `localhost` (or `127.0.0.1`)
- **Port:** `5432`
- **Maintenance DB:** `courier_db`
- **Username:** (Matches your `.env` `DB_USER`)
- **Password:** (Matches your `.env` `DB_PASSWORD`)

---

## ⚠️ Troubleshooting

### Authentication Failed?

If you change your password in the `.env` file after running the containers once, the database
will still be locked to the **old** password because of Docker volume persistence. To force a refresh:

```bash
# This wipes the old database volume and resets the password
docker-compose down -v
docker-compose up --build
```