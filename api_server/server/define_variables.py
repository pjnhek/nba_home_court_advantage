import os

from dotenv import load_dotenv

load_dotenv()

project_id = os.getenv('PROJECT_ID')
bucket_name = os.getenv('GCP_BUCKET_NAME')
service_account_file_path = os.getenv('GCP_SERVICE_ACCOUNT_KEY')
api_server_url = os.getenv('API_SERVICE_URL')
client_id = os.getenv("SEATGEEK_CLIENT_ID")
secret_id = os.getenv("SECRET_ID")