import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


def crawl_businesses(state, region, types):
    """Triggers a crawl from the backend using provided state, region, and types."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl",
            params={"state": state, "region": region, "types": types},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Crawl failed: {str(e)}"}


def get_leads(state=None, type_=None):
    """Fetch saved businesses with optional filters."""
    try:
        params = {}
        if state:
            params["state"] = state
        if type_:
            params["type_"] = type_
        response = requests.get(f"{BASE_URL}/api/business/leads", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Lead fetch failed: {str(e)}"}


def get_summary_data():
    """Returns summary data: business counts grouped by state and type."""
    try:
        response = requests.get(f"{BASE_URL}/api/business/leads/summary")
        response.raise_for_status()
        data = response.json()
        # print("Summary API Response:", data)
        return data
    except Exception as e:
        return {"error": f"Summary fetch failed: {str(e)}"}


def health_check():
    """Optional: Check backend health, useful on landing or settings page."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "details": response.text}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}
