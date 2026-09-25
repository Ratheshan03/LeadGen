"""python -m backend  ->  start the LeadGen API server."""
import uvicorn

from backend.config import settings

if __name__ == "__main__":
    print(f"LeadGen backend starting on http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}  (Ctrl+C to stop)")
    uvicorn.run("backend.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, log_level="warning")
