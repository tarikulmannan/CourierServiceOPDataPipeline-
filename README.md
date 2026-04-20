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