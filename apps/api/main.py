from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import sys
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from routes import business
from db.mongo import init_db_indexes

load_dotenv()

app = FastAPI(
    title="Business Crawler API",
    description="Fetch businesses using Google Places API",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(business.router, prefix="/api/business", tags=["Business"])

# Run Mongo index setup at startup
@app.on_event("startup")
async def startup_event():
    await init_db_indexes()
    print("App started and DB indexes checked.")
