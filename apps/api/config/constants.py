import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# === BUSINESS CATEGORIES (Google Place Types) ===
BUSINESS_CATEGORIES = {
    "Automotive": [
        "car_dealer",
        "car_repair",
        "car_rental",
        "gas_station",
        "parking",
        "electric_vehicle_charging_station",
    ],
    "Business": [
        "corporate_office",
        "real_estate_agency",
        "consultant",
        "insurance_agency",
        "lawyer",
        "accounting",
    ],
    "Culture": [
        "museum",
        "art_gallery",
        "cultural_center",
        "historical_place",
    ],
    "Education": [
        "university",
        "school",
        "library",
        "preschool",
        "primary_school",
        "secondary_school",
    ],
    "Entertainment and Recreation": [
        "amusement_park",
        "zoo",
        "movie_theater",
        "night_club",
        "bowling_alley",
        "tourist_attraction",
        "aquarium",
        "casino",
        "event_venue",
        "park",
    ],
    "Facilities": [
        "public_bathroom",
        "stable",
    ],
    "Finance": [
        "bank",
        "atm",
        "accounting",
    ],
    "Food and Drink": [
        "restaurant",
        "cafe",
        "bar",
        "meal_delivery",
        "meal_takeaway",
        "bakery",
        "fast_food_restaurant",
        "pub",
        "coffee_shop",
    ],
    "Geographical Areas": [
        # Not useful for crawling actual businesses
    ],
    "Government": [
        "city_hall",
        "police",
        "fire_station",
        "embassy",
        "courthouse",
        "post_office",
    ],
    "Health and Wellness": [
        "pharmacy",
        "doctor",
        "dentist",
        "hospital",
        "veterinary_care",
        "spa",
        "chiropractor",
        "physiotherapist",
    ],
    "Housing": [
        "apartment_complex",
        "housing_complex",
    ],
    "Lodging": [
        "hotel",
        "motel",
        "hostel",
        "campground",
        "resort_hotel",
    ],
    "Natural Features": [
        "beach",
        "national_park",
    ],
    "Places of Worship": [
        "church",
        "mosque",
        "hindu_temple",
        "synagogue",
    ],
    "Services": [
        "electrician",
        "plumber",
        "courier_service",
        "laundry",
        "tailor",
        "barber_shop",
        "beauty_salon",
        "locksmith",
        "funeral_home",
        "hair_salon",
        "child_care_agency",
        "travel_agency",
    ],
    "Shopping": [
        "shopping_mall",
        "grocery_store",
        "convenience_store",
        "supermarket",
        "hardware_store",
        "clothing_store",
        "electronics_store",
        "furniture_store",
        "liquor_store",
        "pet_store",
        "book_store",
        "department_store",
        "jewelry_store",
        "shoe_store",
    ],
    "Sports": [
        "fitness_center",
        "gym",
        "stadium",
        "golf_course",
        "swimming_pool",
        "sports_complex",
    ],
    "Transportation": [
        "train_station",
        "bus_station",
        "taxi_stand",
        "subway_station",
        "airport",
        "ferry_terminal",
    ]
}


# Flattened list of all types used in BUSINESS_CATEGORIES
ALL_BUSINESS_TYPES = sorted(
    {ptype for types in BUSINESS_CATEGORIES.values() for ptype in types}
)

# Mapping type -> category
BUSINESS_TYPE_TO_CATEGORY = {
    ptype: category for category, types in BUSINESS_CATEGORIES.items() for ptype in types
}



# === AUSTRALIAN REGION INFO ===

# Australian states with key cities/regions to crawl
AU_REGIONS = {
    "New South Wales": [
        "Sydney", "Newcastle", "Wollongong", "Albury", "Maitland", "Wagga Wagga", "Port Macquarie", "Tamworth", "Coffs Harbour"
    ],
    "Victoria": [
        "Melbourne", "Geelong", "Ballarat", "Bendigo", "Shepparton", "Mildura", "Warrnambool", "Traralgon"
    ],
    "Queensland": [
        "Brisbane", "Gold Coast", "Cairns", "Townsville", "Toowoomba", "Rockhampton", "Mackay", "Bundaberg", "Hervey Bay"
    ],
    "Western Australia": [
        "Perth", "Fremantle", "Bunbury", "Albany", "Geraldton", "Kalgoorlie", "Broome"
    ],
    "South Australia": [
        "Adelaide", "Mount Gambier", "Whyalla", "Gawler", "Port Lincoln", "Port Pirie", "Murray Bridge"
    ],
    "Tasmania": [
        "Hobart", "Launceston", "Devonport", "Burnie"
    ],
    "Australian Capital Territory": [
        "Canberra", "Belconnen", "Gungahlin", "Tuggeranong"
    ],
    "Northern Territory": [
        "Darwin", "Alice Springs", "Palmerston", "Katherine"
    ]
}

# Use these for coordinate-based lookups
REGION_COORDINATES = {
    "Sydney": "-33.8688,151.2093",
    "Newcastle": "-32.9283,151.7817",
    "Wollongong": "-34.4278,150.8931",
    "Albury": "-36.0737,146.9135",
    "Maitland": "-32.7335,151.5570",
    "Wagga Wagga": "-35.1180,147.3598",
    "Port Macquarie": "-31.4300,152.9080",
    "Tamworth": "-31.0833,150.9333",
    "Coffs Harbour": "-30.2963,153.1135",

    "Melbourne": "-37.8142,144.9631",
    "Geelong": "-38.1499,144.3617",
    "Ballarat": "-37.5622,143.8503",
    "Bendigo": "-36.7570,144.2794",
    "Shepparton": "-36.3805,145.3989",
    "Mildura": "-34.2052,142.1367",
    "Warrnambool": "-38.3818,142.4875",
    "Traralgon": "-38.1950,146.5408",

    "Brisbane": "-27.4698,153.0251",
    "Gold Coast": "-28.0167,153.4000",
    "Cairns": "-16.9186,145.7781",
    "Townsville": "-19.2589,146.8169",
    "Toowoomba": "-27.5606,151.9539",
    "Rockhampton": "-23.3783,150.5100",
    "Mackay": "-21.1411,149.1860",
    "Bundaberg": "-24.8667,152.3500",
    "Hervey Bay": "-25.2880,152.8206",

    "Perth": "-31.9505,115.8605",
    "Fremantle": "-32.0569,115.7439",
    "Bunbury": "-33.3271,115.6414",
    "Albany": "-35.0269,117.8831",
    "Geraldton": "-28.7742,114.6140",
    "Kalgoorlie": "-30.7489,121.4655",
    "Broome": "-17.9614,122.2359",

    "Adelaide": "-34.9285,138.6007",
    "Mount Gambier": "-37.8318,140.7790",
    "Whyalla": "-33.0328,137.5610",
    "Gawler": "-34.5967,138.7458",
    "Port Lincoln": "-34.7208,135.8589",
    "Port Pirie": "-33.1775,138.0086",
    "Murray Bridge": "-35.1199,139.2734",

    "Hobart": "-42.8821,147.3272",
    "Launceston": "-41.4388,147.1347",
    "Devonport": "-41.1762,146.3513",
    "Burnie": "-41.0558,145.9036",

    "Canberra": "-35.2809,149.1300",
    "Belconnen": "-35.2369,149.0686",
    "Gungahlin": "-35.1850,149.1333",
    "Tuggeranong": "-35.4154,149.0626",

    "Darwin": "-12.4634,130.8456",
    "Alice Springs": "-23.6980,133.8807",
    "Palmerston": "-12.4861,130.9830",
    "Katherine": "-14.4656,132.2635"
}


# --- GEOJSON FILE PATHS ---
GCCSA_PATH = "data/geojson/gccsa.geojson"
LGA_PATH = "data/geojson/lga.geojson"
REGIONS_PATH = "data/geojson/regions.geojson"
STATES_PATH = "data/geojson/states.geojson"


# GeoJSON mapping files used for frontend crawling logic
GEOJSON_MAP_PATHS = {
    "state_to_lgas": os.path.join(BASE_DIR, "data", "geojson", "state_to_lgas_map.json"),
    "state_to_regions": os.path.join(BASE_DIR, "data", "geojson", "state_to_regions_map.json"),
}


# --- STATE CODES ---
AUSTRALIAN_STATES = [
    "New South Wales",
    "Victoria",
    "Queensland",
    "South Australia",
    "Western Australia",
    "Tasmania",
    "Northern Territory",
    "Australian Capital Territory",
]

# --- GEOJSON PROPERTY KEYS ---
GEO_KEY_REGION_NAME = "SA2_NAME21"
GEO_KEY_REGION_CODE = "SA2_CODE21"
GEO_KEY_SQKM = "AREASQKM"

# --- TILE SIZE RULES ---
DEFAULT_TILE_SIZE_KM = 10
MINIMUM_TILE_SIZE_KM = 5

# GCCSA regions used for larger area crawls
# These are larger metropolitan areas that can be crawled as single units

GCCSA_REGIONS = {
    "New South Wales": [
        "Greater Sydney",
        "Rest of NSW"
    ],
    "Victoria": [
        "Greater Melbourne",
        "Rest of Vic."
    ],
    "Queensland": [
        "Greater Brisbane",
        "Rest of Qld"
    ],
    "South Australia": [
        "Greater Adelaide",
        "Rest of SA"
    ],
    "Western Australia": [
        "Greater Perth",
        "Rest of WA"
    ],
    "Tasmania": [
        "Greater Hobart",
        "Rest of Tas."
    ],
    "Northern Territory": [
        "Greater Darwin",
        "Rest of NT"
    ],
    "Australian Capital Territory": [
        "Australian Capital Territory"
    ],
    "Other Territories": [
        "Other Territories"
    ]
}


# Tile sizing strategy based on area in square kilometers
# Ensures very small cities get full coverage with 5km tiles
# General urban/suburban: 10km, Larger rural: 20-30km
TILE_SIZE_OVERRIDES = [
    (0, 3, 5),        # Very small areas — single 5 km tile covers entire region
    (3, 1000, 10),    # Typical towns, suburbs, GCCSA urban areas
    (1000, 5000, 20), # Large rural or regional zones
    (5000, float("inf"), 30)  # Outback/very large unstructured areas
]

# Region descriptors used to influence tile sizing (NOT to exclude)
# These suggest sparse population/business density — use larger tiles
LOW_DENSITY_REGION_KEYWORDS = [
    "offshore", "no usual address", "outside", "unknown",
    "desert", "national park", "forest", "reserve", "unincorporated",
    "military", "training area", "wilderness", "nature refuge",
    "conservation area", "indigenous protected area", "biosphere"
]

# --- DEFAULT TILE CONFIGURATION FOR REGION CRAWLER ---
# Main crawling will use regions.geojson for full coverage of all populated locations
PRIMARY_GEOJSON_SOURCE = REGIONS_PATH



# Google Places API endpoints
GOOGLE_PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
