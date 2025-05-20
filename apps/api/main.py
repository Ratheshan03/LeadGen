from fastapi import FastAPI
from app.api.routes import business
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Optional CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # or ["*"] to allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(business.router, prefix="/api")
