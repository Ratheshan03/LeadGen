# Boundary data

LeadGen crawls an area by covering its official boundary with search tiles.
The boundaries come from each country's statistics agency, processed into a
compact format by the scripts in `scripts/`.

```
data/
├── australia/
│   ├── boundaries/          lga, sa2, gccsa  (.geojson.gz, used by the app)
│   ├── lookups/             state_to_<level>.json  (area lists for the pickers)
│   └── source/              raw ABS shapefiles (not in git, only needed to rebuild)
```

## Levels

| Country | Level | What it is | Areas |
|---|---|---|---|
| Australia | `lga` | Local Government Area (council) | 547 |
| Australia | `sa2` | Statistical Area Level 2 (suburb sized) | 2,454 |
| Australia | `gccsa` | Greater Capital City / Rest of State | 16 |

Non-geographic entries in the official files ("No usual address",
"Migratory - Offshore - Shipping", "Outside Australia") have no boundary and
are left out.

## Processing

* Geometry is simplified with a ~1 m tolerance and coordinates are rounded to
  6 decimals. This keeps boundaries accurate to about a metre while cutting
  the files from ~500 MB to ~40 MB.
* Each area has the same properties in every country: `name`, `code`,
  `state` (state / region), `area_km2`, plus optional parents.
* `tests/test_tiling.py` checks the crawl tiles produced from this data against
  the tiles the original crawler produced from the full-resolution files.

## Sources and licences

**Australia** - Australian Bureau of Statistics, *Australian Statistical
Geography Standard (ASGS) Edition 3*, digital boundary files (GDA2020):
LGA 2024, SA2 2021, GCCSA 2021. Licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
<https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files>

## Rebuilding (e.g. when a new edition is released)

1. Download the shapefile zips from the source above and extract them into
   `data/australia/source/lga/`, `.../sa2/` and `.../gccsa/`.
2. From the project root run:
   ```
   python scripts/build_australia_data.py
   ```
3. Run `python -m pytest` to confirm everything still works. If the new
   edition changes boundaries, the tiling regression test will report the
   areas whose tiles moved; that is expected after a real boundary change.
