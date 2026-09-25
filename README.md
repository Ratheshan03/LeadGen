# LeadGen — Australian Business Lead Generation Platform

A full-stack, geospatial-aware business lead generation system that systematically crawls Google Places API across Australian regions, stores leads in MongoDB, and surfaces them through a Streamlit web dashboard.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running the Project (Local / No Docker)](#running-the-project-local--no-docker)
- [Running with Docker](#running-with-docker)
- [How Crawling Works](#how-crawling-works)
- [Running a Custom Crawl (NSW LGAs)](#running-a-custom-crawl-nsw-lgas)
- [NSW LGA Reference List](#nsw-lga-reference-list)
- [API Endpoints](#api-endpoints)
- [Business Categories & Types](#business-categories--types)
- [Data Model](#data-model)
- [Quota Management](#quota-management)
- [Utility Scripts](#utility-scripts)

---

## Overview

LeadGen automates the discovery of Australian businesses by:

1. Generating a grid of geospatial **tiles** over any Australian region (LGA, SA2 Region, GCCSA)
2. Crawling each tile via **Google Places Text Search API** with configurable business type queries
3. Geo-filtering results to ensure they fall inside the actual region boundary (using Shapely)
4. **Deduplicating** by `place_id` and **upserting** into MongoDB
5. Exporting results to **Excel** for outreach workflows

The platform supports **dry-run simulation** (no API calls, no DB writes) to estimate scope before committing quota.

---

## Architecture

```
┌─────────────────────┐         HTTP          ┌──────────────────────────┐
│  Streamlit Frontend │ ────────────────────► │  FastAPI Backend         │
│  (Port 3000)        │                       │  (Port 8000)             │
│                     │                       │                          │
│  pages/             │                       │  routes/business.py      │
│  ├── Nearby Crawler │                       │  services/               │
│  ├── Text Crawler   │                       │  ├── google_maps.py      │
│  ├── View Leads     │                       │  └── business_manager.py │
│  └── Summary        │                       │  utils/                  │
└─────────────────────┘                       │  ├── helpers.py (tiles)  │
                                              │  ├── api_key_manager.py  │
                                              │  └── quota_manager.py    │
                                              │          │               │
                                              │     MongoDB Atlas        │
                                              │     (leads collection)   │
                                              └──────────────────────────┘
```

---

## Project Structure

```
LeadGen/
├── docker-compose.yml              # Docker: api + web + mongo
├── README.md
└── apps/
    ├── .env                        # Active environment variables
    ├── .env_template               # Template for setting up .env
    │
    ├── api/                        # FastAPI backend (port 8000)
    │   ├── main.py                 # App entry point, CORS, startup
    │   ├── requirements.txt        # Python dependencies
    │   ├── api_quota_usage.json    # Monthly API usage tracker
    │   │
    │   ├── config/
    │   │   ├── constants.py        # Business types, AU regions, tile sizes
    │   │   └── settings.py         # Env var loading (MONGO_DB_URI, API keys, etc.)
    │   │
    │   ├── db/
    │   │   ├── mongo.py            # Motor async MongoDB client + index setup
    │   │   ├── models/lead_model.py   # Pydantic Lead model
    │   │   ├── schemas/lead_schema.py # LeadBase / LeadCreate / LeadInDB / LeadPublic
    │   │   └── queries.py          # CRUD: insert, upsert, batch, filter, Excel export
    │   │
    │   ├── routes/
    │   │   └── business.py         # All API endpoints
    │   │
    │   ├── services/
    │   │   ├── google_maps.py      # Google Places API: nearby search, text search, details
    │   │   └── business_manager.py # Crawl orchestration: tile crawl, save, export
    │   │
    │   ├── utils/
    │   │   ├── helpers.py          # Tile generation, coordinate transforms, result normalisation
    │   │   ├── api_key_manager.py  # Round-robin API key rotation
    │   │   ├── quota_manager.py    # Monthly quota tracking (resets automatically)
    │   │   ├── visualization.py    # Folium map: tiles + polygons → HTML
    │   │   ├── test_custom_crawl.py   # ✅ Run a custom region crawl (edit this to change target)
    │   │   ├── test_full_crawl.py     # Run a dry-run of full Australia crawl
    │   │   └── migrate_business_types.py  # One-time schema migration script
    │   │
    │   └── data/
    │       └── geojson/
    │           ├── gccsa.geojson           # Greater Capital City Statistical Areas
    │           ├── lga.geojson             # Local Government Areas (all states)
    │           ├── regions.geojson         # SA2 Statistical Regions
    │           ├── state_to_lgas_map.json
    │           └── state_to_regions_map.json
    │
    └── web/                        # Streamlit frontend (port 3000)
        ├── main.py                 # Landing page
        ├── requirements.txt
        ├── pages/
        │   ├── 1_Nearby_Search_Crawler.py
        │   ├── 2_Text_Search_Crawler.py
        │   ├── 3_View_Leads.py
        │   └── 4_Business_Summary.py
        └── utils/api.py            # HTTP client functions calling backend
```

---

## Prerequisites

- **Python 3.10+**
- **MongoDB Atlas** account (or local MongoDB instance)
- **Google Cloud** project with **Places API (New)** enabled
- At least one **Google Maps API key** with Places API access

---

## Environment Setup

### 1. Copy and fill the environment file

The `.env` file lives at `apps/.env` (one level above `api/` and `web/`).

```bash
# From the repo root
cp apps/.env_template apps/.env
```

Edit `apps/.env`:

```env
# Google Places API — comma-separate multiple keys for rotation
GOOGLE_API_KEYS=AIzaSy...yourkey1,AIzaSy...yourkey2

# Google Places Text Search endpoint (do not change)
GOOGLE_API_URL=https://places.googleapis.com/v1/places:searchText

# MongoDB connection string (Atlas or local)
MONGO_DB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority

# Database name
MONGO_DB_NAME=leadgen

# Collection name
COLLECTION_NAME=leads

# Monthly API request cap (Google free tier = ~200 per key, raise for paid)
API_REQUEST_CAP=900

# Backend URL used by the web frontend and utility scripts
BACKEND_API_URL=http://localhost:8000
```

### 2. Create and activate the Python virtual environment

```powershell
# From the repo root — the venv already exists at apps/.venv
# To activate it in PowerShell:
cd apps
.\.venv\Scripts\Activate.ps1
```

If the venv does not exist yet:

```powershell
cd apps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```powershell
# With venv activated, from apps/api/
pip install -r api/requirements.txt
```

### 4. Install frontend dependencies (optional — only if running the web UI)

```powershell
pip install -r web/requirements.txt
```

---

## Running the Project (Local / No Docker)

Open **two separate PowerShell terminals** with the venv activated.

### Terminal 1 — Start the FastAPI backend

```powershell
cd apps\api
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
App started and DB indexes checked.
```

API docs available at: `http://localhost:8000/docs`

### Terminal 2 — Start the Streamlit frontend (optional)

```powershell
cd apps\web
streamlit run main.py --server.port 3000
```

Frontend available at: `http://localhost:3000`

---

## Running with Docker

```powershell
# From the repo root
docker-compose up --build
```

Services:
| Service | URL |
|---------|-----|
| FastAPI backend | http://localhost:8000 |
| Streamlit frontend | http://localhost:3000 |
| MongoDB | mongodb://localhost:27017 |

---

## How Crawling Works

### Tile Generation

The system loads the relevant GeoJSON file (`lga.geojson`, `regions.geojson`, or `gccsa.geojson`), extracts the polygon for the requested region, and subdivides it into a grid of rectangular **tiles**.

- Tile size is determined by region area (small urban LGAs → 5 km tiles; large rural LGAs → 50–150 km tiles)
- Shapely is used to filter results to only those physically inside the region boundary
- Each tile becomes a `locationBias` rectangle in the Google Places Text Search request

### Text Search Crawl Flow

```
Region selected (e.g. "Sydney" LGA in NSW)
    ↓
generate_tiles_for_australia() → list of tile bounds
    ↓
For each tile:
    GoogleMapsService.text_search_places(query, tile_bounds)
        → up to 3 pages × 20 results = 60 results per tile
    ↓
Geo-filter: keep only results inside tile polygon
    ↓
upsert_lead_with_business_type() → MongoDB (deduplication by place_id)
    ↓
Export all results → output_maps/<region>_<timestamp>.xlsx
```

### Dry Run

Pass `dry_run=true` to any crawl endpoint or script to simulate the full run without making API calls or writing to the database. Returns tile count and estimated API requests.

---

## Running a Custom Crawl (NSW LGAs)

### Step 1 — Ensure the API is running

```powershell
cd apps\api
uvicorn main:app --reload --port 8000
```

### Step 2 — Edit the custom crawl script

Open [apps/api/utils/test_custom_crawl.py](apps/api/utils/test_custom_crawl.py) and update the parameters near the bottom of the file:

```python
# Line ~70 — update these fields:
region_name = "Sydney"          # ← NSW LGA name (see full list below)
geojson_type = "lga"            # ← always "lga" for LGA-level crawl
state_name = "New South Wales"  # ← always this for NSW
business_query = "All"          # ← "All" to crawl every business type, or e.g. "restaurant"
dry_run = True                  # ← set False to actually crawl + save to DB
```

### Step 3 — Run the custom crawl script

```powershell
# With venv activated, from apps/api/
cd apps\api
python utils/test_custom_crawl.py
```

Output will show:
- Tile map saved to `output_maps/<region>_tiles_<timestamp>.html` (open in browser)
- Polygon map saved to `output_maps/<region>_polygon_<timestamp>.html`
- Crawl summary: total saved, tiles scanned, API requests used, failures

### Step 4 — Iterate through NSW LGAs

To crawl NSW LGA by LGA, update `region_name` for each run. Recommended order (start with major urban, then regional):

```
Sydney → Parramatta → Blacktown → Newcastle → Wollongong → Central Coast (NSW)
→ Lake Macquarie → Penrith → Liverpool → Campbelltown (NSW) → ...
```

> **Tip**: Use `dry_run = True` first to check tile count and estimated API usage before committing quota.

---

## API Endpoints

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/business/crawl` | Manual nearby search for a single region |
| GET | `/api/business/crawl/all` | Full automated crawl of all AU regions |
| GET | `/api/business/crawl/textsearch/custom` | **Custom region text search crawl** |
| GET | `/api/business/crawl/textsearch/full` | Full Australia-wide text search crawl |
| GET | `/api/business/leads` | Get leads with optional filters |
| GET | `/api/business/leads/summary` | Aggregated summary by state/type |
| GET | `/api/business/leads/crawl/textsearch/coverage` | Check crawl coverage for a region |

### Key query params for `/api/business/crawl/textsearch/custom`

| Param | Type | Example | Description |
|-------|------|---------|-------------|
| `query` | string | `restaurant` or `All` | Business type to search (All = all types) |
| `state` | string | `New South Wales` | Australian state name |
| `region` | string | `Sydney` | LGA / Region / GCCSA name |
| `geojson_type` | string | `lga` | Source: `lga`, `regions`, or `gccsa` |
| `dry_run` | bool | `true` | Simulate without API calls or DB writes |

Full interactive API docs: `http://localhost:8000/docs`

---

## Business Categories & Types

The system uses 15 categories covering 100+ Google Place types:

| Category | Example Types |
|----------|---------------|
| Automotive | car_dealer, car_repair, gas_station |
| Business | corporate_office, real_estate_agency, lawyer |
| Education | university, school, preschool |
| Food and Drink | restaurant, cafe, bar, bakery |
| Health and Wellness | pharmacy, doctor, dentist, hospital |
| Services | electrician, plumber, beauty_salon, barber_shop |
| Shopping | shopping_mall, supermarket, electronics_store |
| Sports | fitness_center, gym, golf_course |
| Transportation | train_station, airport, ferry_terminal |
| ...and more | Entertainment, Finance, Lodging, Government, etc. |

When `query = "All"`, the crawl iterates through every type in every category automatically.

---

## Data Model

Each lead stored in MongoDB contains:

```json
{
  "place_id": "ChIJ...",
  "name": "Business Name",
  "address": "123 Main St, Sydney NSW 2000",
  "phone": "+61 2 xxxx xxxx",
  "website": "https://example.com.au",
  "location": { "lat": -33.8688, "lng": 151.2093 },
  "types": ["restaurant", "food"],
  "rating": 4.5,
  "total_reviews": 120,
  "opening_hours": ["Mon: 9:00 AM – 5:00 PM", "..."],
  "state": "New South Wales",
  "region": "Sydney",
  "category": "Food and Drink",
  "business_types": ["restaurant"],
  "retrieved_at": "2025-03-15T10:30:00Z",
  "contacted": false,
  "email_sent": false,
  "sms_sent": false,
  "cold_called": false,
  "tags": ["restaurant"]
}
```

Deduplication is enforced via a unique index on `place_id`.

---

## Quota Management

API usage is tracked in `apps/api/api_quota_usage.json` and resets automatically each calendar month.

- Default cap: `API_REQUEST_CAP=900` (configurable in `.env`)
- Each tile × business type = 1–3 API requests (depending on result pages)
- Use `dry_run=True` to estimate total requests before running

To check current usage:

```powershell
cat apps/api/api_quota_usage.json
```

---

## Utility Scripts

All scripts run from `apps/api/` with the venv activated.

### Custom Crawl (primary use)

```powershell
python utils/test_custom_crawl.py
```

Edit region, state, query, and dry_run at the bottom of the file before running.

### Full Australia Dry Run

```powershell
python utils/test_full_crawl.py
```

Simulates a full Australia crawl and generates tile coverage maps.

### Schema Migration

If you have old leads with a single `business_type` field and need to migrate to the new `business_types` array:

```powershell
python utils/migrate_business_types.py
```

---

## Output Files

- Crawl results: `apps/api/output_maps/<region>_<timestamp>.xlsx`
- Tile visualisation maps: `apps/api/output_maps/<region>_tiles_<timestamp>.html`
- Polygon maps: `apps/api/output_maps/<region>_polygon_<timestamp>.html`

Open the `.html` files directly in a browser to inspect tile coverage.
