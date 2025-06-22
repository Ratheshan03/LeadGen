# === BUSINESS CATEGORIES (Google Place Types) ===
BUSINESS_CATEGORIES = {
    "Professional Offices": [
        "corporate_office",
        "lawyer",
        "accounting",
        "consultant",
        "insurance_agency",
        "real_estate_agency",
        "travel_agency",
    ],
    "Education & Institutions": [
        "university",
        "school",
    ],
    "Retail & Suppliers": [
        "electronics_store",
        "hardware_store", 
        "department_store",
        "furniture_store",
        "shopping_mall",
        "clothing_store",
        "grocery_store",
        "supermarket", 
        "convenience_store",
        "liquor_store",
    ],
    "Health & Wellness": [
        "pharmacy", 
        "veterinary_care", 
        "dentist",  
        "doctor", 
        "dental_clinic",  
        "spa",
    ],
    "Security & Vehicles": [
        "car_dealer", 
        "storage", 
        "car_repair",
        "electrician",
    ],
    "Logistics & B2B": [
        "courier_service", 
        "moving_company",  
        "laundry",  
        "painter",  
        "tailor",    
        "barber_shop",   
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

    "Melbourne": "-37.8136,144.9631",
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



# Google Places API endpoints
GOOGLE_PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"





# TEXT_SEARCH_TILES = [
#     {
#         "region": "Sydney",
#         "tile_name": "Sydney_tile_11",
#         "locationBias": {
#             "rectangle": {
#                 "low": {"latitude": -34.0688, "longitude": 151.0093},
#                 "high": {"latitude": -33.8688, "longitude": 151.2093}
#             }
#         }
#     },
#     {
#         "region": "Sydney",
#         "tile_name": "Sydney_tile_12",
#         "locationBias": {
#             "rectangle": {
#                 "low": {"latitude": -34.0688, "longitude": 151.2093},
#                 "high": {"latitude": -33.8688, "longitude": 151.4093}
#             }
#         }
#     },
#     ...
# ]
