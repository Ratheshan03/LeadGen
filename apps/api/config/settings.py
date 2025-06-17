from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

MONGODB_URI = os.getenv("MONGO_DB_URI")
GOOGLE_API_KEYS = os.getenv("GOOGLE_API_KEYS", "").split(",")
API_REQUEST_CAP = int(os.getenv("API_REQUEST_CAP", "9500"))


DEBUG = os.getenv("DEBUG", "False").lower() == "true"

