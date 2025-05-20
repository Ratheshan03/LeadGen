from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    GOOGLE_API_URL = os.getenv("GOOGLE_API_URL")
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "leadgen")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "businesses")

settings = Settings()
