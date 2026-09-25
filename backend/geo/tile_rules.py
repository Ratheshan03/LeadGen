"""
Tile-sizing rules, per country.

A crawl covers an area with rectangular "tiles"; each tile is one Google Text
Search location restriction. These rules pick the tile size for an area from
its size and name. The Australian rules are the ones LeadGen has always used.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# (min_area_km2, max_area_km2, tile_size_km): bigger areas get bigger tiles.
DEFAULT_SIZE_BUCKETS: tuple[tuple[float, float, float], ...] = (
    (0, 3, 5),                    # tiny regions        -> 5 km tiles
    (3, 50, 10),                  # small towns         -> 10 km
    (50, 100, 15),                # suburban / mid-size -> 15 km
    (100, 500, 20),               # small rural / mixed -> 20 km
    (500, 1000, 25),              # larger rural        -> 25 km
    (1000, 2000, 50),             # very large rural    -> 50 km
    (2000, 5000, 70),             # huge districts      -> 70 km
    (5000, 10000, 100),           # vast territories    -> 100 km
    (10000, float("inf"), 150),   # outback scale       -> 150 km
)

# Words in an area's name suggesting sparse business density -> largest tiles.
_NATURE_AND_REMOTE_KEYWORDS = (
    # offshore / external
    "offshore", "island", "islands", "external territory", "cocos", "keeling",
    "norfolk", "christmas island", "torres strait", "ashmore", "cartier",
    # address / population unknown
    "no usual address", "outside", "unknown", "undefined",
    # natural reserves & protected
    "desert", "national park", "forest", "reserve", "state park", "wilderness",
    "nature refuge", "conservation area", "biosphere", "heritage area",
    "protected area", "marine park", "wildlife sanctuary", "botanic garden",
    # rural descriptors
    "pastoral", "grazing", "agricultural", "rural", "farm", "station",
    "bushland", "scrub", "grassland", "vineyard", "orchard",
    # water / coastal
    "lake", "river", "wetland", "swamp", "lagoon", "coastal", "mangrove", "shoal", "reef",
)
_ADMIN_SPARSE_KEYWORDS = ("unincorporated", "shire", "county", "region", "district")
_MILITARY_KEYWORDS = (
    "military", "training area", "weapons range", "bombing range", "air force base",
    "naval base", "army base",
)

# Genuinely remote / sparsely populated Australian LGAs (lower-case names).
# Together with SPARSE_GIANT_AREA_KM2 these collapse to one bounding-box tile.
AU_LOW_DENSITY_AREAS = frozenset({
    # Western Australia - Pilbara / Kimberley / Goldfields / Gascoyne / Murchison
    "east pilbara", "halls creek", "wyndham-east kimberley", "derby-west kimberley",
    "meekatharra", "wiluna", "laverton", "menzies", "ngaanyatjarraku", "ashburton",
    "upper gascoyne", "shark bay", "sandstone", "cue", "yalgoo", "murchison",
    "mount magnet", "leonora", "dundas", "exmouth", "carnarvon",
    # South Australia
    "unincorporated sa", "anangu pitjantjatjara yankunytjatjara", "maralinga tjarutja",
    "coober pedy", "roxby downs", "flinders ranges", "ceduna",
    # Northern Territory
    "barkly", "central desert", "macdonnell", "roper gulf", "victoria daly",
    "west arnhem", "east arnhem", "west daly", "tiwi islands",
    # Queensland - Gulf / Channel Country / Cape York
    "cook", "carpentaria", "burke", "diamantina", "boulia", "bulloo", "barcoo",
    "quilpie", "winton", "mckinlay", "cloncurry", "etheridge", "croydon",
    "flinders (qld)", "richmond", "aurukun", "pormpuraaw", "kowanyama", "doomadgee",
    "mornington", "northern peninsula area", "torres", "torres strait island",
    # NSW far west
    "central darling", "unincorporated nsw", "brewarrina", "bourke", "cobar",
})


@dataclass(frozen=True)
class TileRules:
    size_buckets: tuple[tuple[float, float, float], ...] = DEFAULT_SIZE_BUCKETS
    low_density_keywords: tuple[str, ...] = ()
    low_density_areas: frozenset[str] = field(default_factory=frozenset)
    # An area collapses to ONE bounding-box tile only if it is at least this
    # big AND listed in low_density_areas (e.g. East Pilbara, ~372,000 km²).
    sparse_giant_area_km2: float = 20000
    # Areas inside these capital-city regions (lower-case GCCSA names) get fine
    # tiles: 5 km, or 10 km if the area is 5,000 km² or larger.
    fine_tile_regions: frozenset[str] = field(default_factory=frozenset)
    # Dense-city mode: sub-areas smaller than this get a single tight tile.
    dense_small_area_km2: float = 50
    dense_tile_buffer_m: float = 100

    @property
    def max_tile_km(self) -> float:
        return max(size for _, _, size in self.size_buckets)


AU_TILE_RULES = TileRules(
    low_density_keywords=_NATURE_AND_REMOTE_KEYWORDS + _ADMIN_SPARSE_KEYWORDS + _MILITARY_KEYWORDS,
    low_density_areas=AU_LOW_DENSITY_AREAS,
    # Canberra (ACT) and the Other Territories have always been crawled with
    # fine tiles at the SA2 / GCCSA levels; kept as-is.
    fine_tile_regions=frozenset({"australian capital territory", "other territories"}),
)

# NZ council names all end in "District" / "City", so the administrative
# keywords would wrongly mark every council as sparse; they are left out.
NZ_TILE_RULES = TileRules(
    low_density_keywords=_NATURE_AND_REMOTE_KEYWORDS + _MILITARY_KEYWORDS,
    low_density_areas=frozenset({"chatham islands territory"}),
)
