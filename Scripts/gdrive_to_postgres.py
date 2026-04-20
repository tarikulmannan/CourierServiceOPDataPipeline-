import io
import os
from sqlalchemy import create_engine
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd

# 1. Setup
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = '1suEcgCiBkOeBKTqrj5g-XpOfmTiNBCpE'

# Get credentials from .env via Docker
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
db_host = "db"  # Hardcode this as 'db' to match the YAML service name
db_port = "5432"

# 2. DEBUG: This will show in 'docker logs' if values are missing
print(f"Connecting to: {db_host} as {DB_USER}...")

if not all([DB_USER, DB_PASS, DB_NAME]):
    raise ValueError("ERROR: One or more DB environment variables are MISSING!")

# 3. Use the EXPLICIT driver format
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{db_host}:{db_port}/{DB_NAME}"

def get_drive_service():
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def process_files():
    service = get_drive_service()
    engine = create_engine(DB_URL)

    # 2. List all .xlsx files in the folder
    query = f"'{FOLDER_ID}' in parents and mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if not files:
        print("No Excel files found.")
        return

    for file in files:
        print(f"Processing: {file['name']}...")
        
        # 3. Download
        request = service.files().get_media(fileId=file['id'])
        file_content = io.BytesIO(request.execute())
        
        # 4. Read with Pandas
        df = pd.read_excel(file_content, engine='openpyxl')
        
        # 5. Load to Postgres
        # We use the filename (minus .xlsx) as the table name, or one master table
        table_name = file['name'].replace('.xlsx', '').lower().replace(' ', '_')
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        print(f"Successfully loaded {file['name']} into table '{table_name}'")

if __name__ == "__main__":
    process_files()