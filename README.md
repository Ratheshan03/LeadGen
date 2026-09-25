# LeadGen

LeadGen collects business leads (name, phone, website, address, rating, opening
hours...) from Google Places for any council area in **Australia** and **New
Zealand**, and saves them as tidy Excel files with a map.

It covers each area with a grid of search tiles cut to the official council
boundary, searches every business type you choose, automatically digs deeper
where Google's 60-results-per-search limit is hit, removes duplicates, and
labels every business with the council and suburb area it is actually in.

- **Custom crawl** - one council, or every council in a state one by one (resumable)
- **Full crawl** - a whole country, spread over as many months of quota as you like
- **Nearby Search** - a quick sample around a city centre
- **Dashboard** - browse, filter and download everything collected
- Leads are stored locally (SQLite) - nothing to install or pay for. MongoDB is optional.

---

## 1. Setup (once)

You need **Windows 10/11** with **Python 3.12** (3.10-3.13 also work) and a
**Google Cloud API key**.

1. **Install Python 3.12** from <https://www.python.org/downloads/> - tick
   *"Add python.exe to PATH"* during installation.
2. **Get a Google API key**
   1. Open <https://console.cloud.google.com/>, create a project and turn on billing.
   2. *APIs & Services -> Library* -> enable **Places API (New)**.
   3. *APIs & Services -> Credentials -> Create credentials -> API key*.
      (Recommended: restrict the key to the Places API.)
3. **Double-click `setup.bat`** in this folder. It creates a private Python
   environment and installs everything (a few minutes the first time).
4. **Open `.env`** (created by setup) in Notepad and paste your key after
   `GOOGLE_API_KEYS=`. Adjust `API_REQUEST_CAP` (your monthly request limit) if
   you like. Save.
5. Done.

> Mac / Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`,
> then use the `python ...` commands shown below instead of the `.bat` files.

---

## 2. Everyday use

**Always start the backend first** and keep its window open:

| Windows (double-click) | Command line | What it does |
|---|---|---|
| `start_backend.bat` | `python -m backend` | Runs the crawler engine (keep open) |
| `custom_crawl.bat` | `python custom_crawl.py` | Guided crawl of one area or a whole state |
| `full_crawl.bat` | `python full_crawl.py` | Crawl an entire country |
| `start_dashboard.bat` | `python -m streamlit run dashboard/Home.py` | Web dashboard at http://127.0.0.1:8501 |

### Custom crawl (the usual way)

Double-click `custom_crawl.bat` and answer the questions:

```
What would you like to do?
    1) Crawl one area (council / suburb area)
    2) Crawl every area in a state or region, one by one (resumable)
    3) Nearby Search around a city centre
    4) Export leads from the database to Excel
    5) Show recent crawls
```

Before anything is spent you see the plan - number of tiles, Google requests
and estimated cost - and must confirm. While it runs you get a live log, one
line per business type:

```
  [12/93] cafe                                  57 found     41 new     4 requests
```

You can also run it directly with options, for example:

```
python custom_crawl.py --state "South Australia" --area Walkerville
python custom_crawl.py --state Tasmania --all-areas                 every council in Tasmania
python custom_crawl.py --state Queensland --area Brisbane --dense   big city, neighbourhood by neighbourhood
python custom_crawl.py --country NZ --state Canterbury --area "Christchurch City"
python custom_crawl.py --state Victoria --area Melbourne --estimate cost estimate only
python custom_crawl.py --help                                       all options
```

Press **Ctrl+C** during a crawl to stop it (or leave it running in the backend).

### Output

Every crawl writes an Excel file and a map to the `output` folder:

```
output/
└── Australia/
    └── South Australia/
        └── Walkerville/
            ├── Walkerville_ALL_2026-09-26_1030.xlsx
            └── Walkerville_ALL_2026-09-26_1030_map.html
```

- **Excel, "Leads" sheet:** one row per business - name, business types,
  category, address, phone, website and Google Maps links, rating, reviews,
  open/closed status, opening hours, council, suburb area (SA2),
  state/region, coordinates, Google types, place ID, first found / last updated.
- **Excel, "Summary" sheet:** what was crawled, when, requests used, estimated cost
  and counts per business type.
- **Map:** open the `.html` file in a browser - boundary, search tiles and every
  business (click a pin for details).

Only businesses **inside** the chosen area go into its Excel file. Businesses
found just across the border are still saved (under their own council) and
appear when you crawl or export that council.

All leads are also kept in the local database (`storage/leadgen.db`), so you
can re-export any combination later from the dashboard (*Leads* page) or with
`python custom_crawl.py --export --state "South Australia"`.

### Area types

| Country | Area type | Examples |
|---|---|---|
| Australia | **LGA** - council (default) | Walkerville, Brisbane, Sydney |
| Australia | SA2 - suburb-sized statistical area | North Adelaide, Brisbane City |
| Australia | GCCSA - capital city / rest of state | Greater Sydney, Rest of NSW |
| New Zealand | **TA** - district / city council (default) | Christchurch City, Queenstown-Lakes District |
| New Zealand | SA2 - suburb-sized statistical area | |
| New Zealand | Region - regional council area | Canterbury, Otago |

### Dense-city mode

Google returns at most 60 results per search. In big city centres (Brisbane,
Sydney, Auckland...) one search tile can have hundreds of cafes, so a normal
crawl misses many. **Dense-city mode** crawls the council neighbourhood by
neighbourhood (its SA2 areas) instead - much more complete, but it costs a lot
more (e.g. Brisbane with all types: ~$440+ instead of ~$3+). Always check the
estimate first.

---

## 3. Costs and the monthly cap

- Google charges about **USD 35 per 1,000 requests** for the data LeadGen
  collects (Text Search "Enterprise" rate; check your Google Cloud billing for
  current prices and any free monthly allowance).
- Each area needs at least **1 request per business type per tile**; busy areas
  need extra pages and splits (typically up to ~4x the minimum). A small council
  with all 93 types is roughly **$3-13**.
- `API_REQUEST_CAP` in `.env` is a hard monthly limit. When it is reached the
  crawl stops cleanly and keeps everything found so far. State and full crawls
  are **resumable** - run the same command next month and finished areas are
  skipped.

---

## 4. Settings

| What | Where |
|---|---|
| Google key(s), monthly cap, storage type, output folder | `.env` (see comments in `.env.example`) |
| Which business types to crawl | `config/business_types.yaml` - remove lines to skip types, add any [Google place type](https://developers.google.com/maps/documentation/places/web-service/place-types) |
| Council boundary data | `data/` - see [data/README.md](data/README.md) |

**Using MongoDB instead of the local database:** set `STORAGE=mongodb`,
`MONGO_DB_URI=...` and `MONGO_DB_NAME=...` in `.env` and restart the backend.
Everything else works the same.

---

## 5. Troubleshooting

| Message | Fix |
|---|---|
| *Cannot reach the LeadGen backend* | Start `start_backend.bat` and keep it open. |
| *No Google API key configured* | Put your key after `GOOGLE_API_KEYS=` in `.env`, restart the backend. |
| *Google rejected the API key* | Check the key, that **Places API (New)** is enabled and billing is on. |
| *Monthly request cap reached* | Wait for next month or raise `API_REQUEST_CAP` in `.env` (restart the backend). |
| *No LGA called '...'. Did you mean ...?* | Use the suggested spelling, or search: `python custom_crawl.py --search walker`. |
| Something else | See `logs/leadgen.log` (a new file each day). |

---

## For developers

```
backend/            FastAPI app, crawl engine, storage, geo engine
  geo/              boundary loading, point-in-area lookup, tiling rules
  crawler/          Google Places client, crawl engine, planner, Excel/map export
  storage/          SQLite (default) and MongoDB stores
  api.py, jobs.py   HTTP API and background crawl jobs
cli/                shared code for the crawl tools
dashboard/          Streamlit dashboard
config/             business_types.yaml
data/               processed boundary data (build scripts in scripts/)
tests/              pytest suite (fake Google API - no cost)
custom_crawl.py     crawl tool
full_crawl.py       whole-country crawl tool
```

- Run the tests: `python -m pytest` (about a minute; no network, no cost). The
  tiling tests compare every area's tiles with the output of the original
  LeadGen crawler.
- API docs while the backend runs: <http://127.0.0.1:8000/docs>
- Rebuild boundary data: see [data/README.md](data/README.md).

Boundary data: Australian Bureau of Statistics and Stats NZ, licensed CC BY 4.0.
