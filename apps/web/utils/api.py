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


def get_leads(state=None, type_=None, category=None, business_type=None):
    """Fetch saved businesses with optional filters."""
    try:
        params = {}
        if state:
            params["state"] = state
        if type_:
            params["type"] = type_
        if category:
            params["category"] = category
        if business_type:
            params["business_type"] = business_type

        response = requests.get(f"{BASE_URL}/api/business/leads", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Lead fetch failed: {str(e)}"}



def get_summary_data(state=None, business_type=None):
    try:
        params = {}
        if state:
            params["state"] = state
        if business_type:
            params["business_type"] = business_type
        response = requests.get(f"{BASE_URL}/api/business/leads/summary", params=params)
        response.raise_for_status()
        return response.json()
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


def crawl_entire_state_or_all(dry_run=True):
    """Triggers full crawl for all regions/types. If dry_run=True, simulates it without saving."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl/all",
            params={"dry_run": str(dry_run).lower()}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Automated crawl failed: {str(e)}"}
    

def crawl_custom_text_search(query: str, state: str, region: str, dry_run=False):
    """Call custom scoped text search API."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl/textsearch/custom",
            params={
                "query": query,
                "state": state,
                "region": region,
                "dry_run": str(dry_run).lower()
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Custom text search crawl failed: {str(e)}"}




def crawl_text_search_full(dry_run=True):
    """Trigger full AU-wide text search crawl using pre-configured types and cities."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl/textsearch/full",
            params={"dry_run": str(dry_run).lower()}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Full text search crawl failed: {str(e)}"}


def crawl_text_search_trial(limit_tiles: int = 20):
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl/textsearch/full?limit_tiles={limit_tiles}&dry_run=false"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_region_coverage(state=None, region=None):
    try:
        params = {}
        if state:
            params["state"] = state
        if region:
            params["region"] = region

        response = requests.get(f"{BASE_URL}/api/business/leads/crawl/textsearch/coverage", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
