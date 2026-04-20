# Courier ETL Pipeline

This project automates the extraction of courier data from Excel files and loads it into a PostgreSQL database using Docker and Python.

## 🚀 Getting Started

Follow these steps to set up the environment and run the pipeline on your machine.

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [pgAdmin 4](https://www.pgadmin.org/download/) installed for database visualization.

# 🛠️ Google Service Account Setup Guide

To run the ETL pipeline without manual browser authentication, we use a **Service Account**. This acts as a "Robot User" that has its own identity.

### Step 1: Create the Service Account
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project from the top dropdown.
3. Navigate to **IAM & Admin** > **Service Accounts**.
4. Click **+ CREATE SERVICE ACCOUNT** at the top.
5. **Details:** - Name: `courier-etl-robot`
   - Click **Create and Continue**.
6. **Grant Access:** (Optional) You can skip the role assignment and just click **Done**.

### Step 2: Generate the JSON Key
1. In the Service Accounts list, click on the **Email** of the account you just created.
2. Click on the **Keys** tab.
3. Click **Add Key** > **Create new key**.
4. Select **JSON** and click **Create**.
5. A file will download to your computer. **Rename this file to `credentials.json`**.



### Step 3: Share the Google Drive Folder
Because the Service Account is like a separate person, it has no access to your files until you share them. In this case you will share the created service account email with me.
I will grant access.
1. Open the downloaded `credentials.json` and find the `"client_email"` (it looks like `courier-etl-robot@your-project.iam.gserviceaccount.com`).
2. Go to the **Google Drive Folder** containing the Excel files.
3. Click **Share**.
4. Paste the Service Account email address.
5. Set the permission to **Editor** (or Viewer if you only need to read).
6. Uncheck "Notify people" and click **Share**.



### Step 4: Final Integration
1. Place the `credentials.json` file into the root folder of the project.
2. Ensure your `.env` file is set up.
3. Run the pipeline:
   ```bash
   docker-compose up --build
   ```
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

1. Place your `.xlsx` files into the `/gdrive` folder.

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