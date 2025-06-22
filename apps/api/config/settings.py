from dotenv import load_dotenv
import os

# Load .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

# DB & API Settings
MONGODB_URI = os.getenv("MONGO_DB_URI")
MONGODB_NAME = os.getenv("MONGO_DB_NAME", "leads_db")

GOOGLE_API_KEYS = [key.strip() for key in os.getenv("GOOGLE_API_KEYS", "").split(",") if key.strip()]
API_REQUEST_CAP = int(os.getenv("API_REQUEST_CAP", "9500"))

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
