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
        "bed_and_breakfast",
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


REGION_TILE_CONFIGS = {
    # === Major Cities ===
    "Melbourne": {
        "tile_km": 5,
        "width_km": 70,
        "height_km": 90,
        "bbox_override": {
            "lat_min": -38.30,
            "lat_max": -37.55,
            "lon_min": 144.65,
            "lon_max": 145.40
        }
    },
    "Sydney": {
        "tile_km": 5,
        "width_km": 70,
        "height_km": 90,
        "bbox_override": {
            "lat_min": -34.10,
            "lat_max": -33.60,
            "lon_min": 150.80,
            "lon_max": 151.35
        }
    },
    "Brisbane": {
        "tile_km": 5,
        "width_km": 60,
        "height_km": 80,
        "bbox_override": {
            "lat_min": -27.70,
            "lat_max": -27.30,
            "lon_min": 152.90,
            "lon_max": 153.20
        }
    },
    "Perth": {
        "tile_km": 5,
        "width_km": 60,
        "height_km": 80,
        "bbox_override": {
            "lat_min": -32.20,
            "lat_max": -31.70,
            "lon_min": 115.70,
            "lon_max": 116.10
        }
    },
    "Adelaide": {
        "tile_km": 5,
        "width_km": 60,
        "height_km": 80,
        "bbox_override": {
            "lat_min": -35.10,
            "lat_max": -34.70,
            "lon_min": 138.40,
            "lon_max": 138.75
        }
    },

    # === Mid-Sized Cities ===
    "Gold Coast": {
        "tile_km": 5,
        "width_km": 40,
        "height_km": 50,
        "bbox_override": {
            "lat_min": -28.10,
            "lat_max": -27.80,
            "lon_min": 153.30,
            "lon_max": 153.60
        }
    },
    "Canberra": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 35,
        "bbox_override": {
            "lat_min": -35.45,
            "lat_max": -35.10,
            "lon_min": 148.90,
            "lon_max": 149.30
        }
    },
    "Hobart": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 30,
        "bbox_override": {
            "lat_min": -43.10,
            "lat_max": -42.75,
            "lon_min": 147.10,
            "lon_max": 147.50
        }
    },
    "Newcastle": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 30,
        "bbox_override": {
            "lat_min": -32.95,
            "lat_max": -32.75,
            "lon_min": 151.70,
            "lon_max": 151.90
        }
    },
    "Wollongong": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 30,
        "bbox_override": {
            "lat_min": -34.60,
            "lat_max": -34.30,
            "lon_min": 150.80,
            "lon_max": 151.00
        }
    },
    "Geelong": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 30,
        "bbox_override": {
            "lat_min": -38.20,
            "lat_max": -37.90,
            "lon_min": 144.25,
            "lon_max": 144.45
        }
    },
    "Townsville": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 30,
        "bbox_override": {
            "lat_min": -19.35,
            "lat_max": -19.20,
            "lon_min": 146.75,
            "lon_max": 146.90
        }
    },
    "Cairns": {
        "tile_km": 5,
        "width_km": 30,
        "height_km": 30,
        "bbox_override": {
            "lat_min": -17.05,
            "lat_max": -16.85,
            "lon_min": 145.60,
            "lon_max": 145.90
        }
    },
    "Toowoomba": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -27.62,
            "lat_max": -27.48,
            "lon_min": 151.85,
            "lon_max": 152.03
        }
    },
    "Launceston": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -41.48,
            "lat_max": -41.35,
            "lon_min": 147.05,
            "lon_max": 147.20
        }
    },
    "Ballarat": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -37.60,
            "lat_max": -37.50,
            "lon_min": 143.80,
            "lon_max": 143.95
        }
    },
    "Bendigo": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -36.82,
            "lat_max": -36.70,
            "lon_min": 144.23,
            "lon_max": 144.35
        }
    },
    "Rockhampton": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -23.42,
            "lat_max": -23.30,
            "lon_min": 150.48,
            "lon_max": 150.60
        }
    },
    "Mackay": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -21.20,
            "lat_max": -21.05,
            "lon_min": 149.15,
            "lon_max": 149.30
        }
    },
    "Shepparton": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -36.42,
            "lat_max": -36.30,
            "lon_min": 145.38,
            "lon_max": 145.50
        }
    },
    "Mildura": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -34.35,
            "lat_max": -34.15,
            "lon_min": 142.00,
            "lon_max": 142.30
        }
    },
    "Wagga Wagga": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -35.25,
            "lat_max": -35.05,
            "lon_min": 147.22,
            "lon_max": 147.45
        }
    },

    # === Small & Remote Towns ===
    "Albany": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -35.05,
            "lat_max": -34.85,
            "lon_min": 117.82,
            "lon_max": 118.05
        }
    },
    "Broome": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -17.99,
            "lat_max": -17.85,
            "lon_min": 122.15,
            "lon_max": 122.30
        }
    },
    "Burnie": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -41.20,
            "lat_max": -41.00,
            "lon_min": 145.85,
            "lon_max": 146.10
        }
    },
    "Bundaberg": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -24.95,
            "lat_max": -24.75,
            "lon_min": 152.28,
            "lon_max": 152.55
        }
    },
    "Hervey Bay": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -25.40,
            "lat_max": -25.20,
            "lon_min": 152.75,
            "lon_max": 153.00
        }
    },
    "Mount Gambier": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -37.85,
            "lat_max": -37.60,
            "lon_min": 140.75,
            "lon_max": 141.00
        }
    },
    "Whyalla": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -33.07,
            "lat_max": -32.90,
            "lon_min": 137.50,
            "lon_max": 137.75
        }
    },
    "Port Lincoln": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -34.75,
            "lat_max": -34.55,
            "lon_min": 135.85,
            "lon_max": 136.10
        }
    },
    "Port Pirie": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -33.25,
            "lat_max": -33.05,
            "lon_min": 138.05,
            "lon_max": 138.30
        }
    },
    "Murray Bridge": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -35.25,
            "lat_max": -35.05,
            "lon_min": 139.20,
            "lon_max": 139.45
        }
    },
    "Gawler": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -34.63,
            "lat_max": -34.52,
            "lon_min": 138.70,
            "lon_max": 138.85
        }
    },
    "Devonport": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -41.18,
            "lat_max": -41.00,
            "lon_min": 146.35,
            "lon_max": 146.60
        }
    },
    "Albury": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -36.13,
            "lat_max": -36.00,
            "lon_min": 146.85,
            "lon_max": 147.00
        }
    },
    "Maitland": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -32.78,
            "lat_max": -32.68,
            "lon_min": 151.50,
            "lon_max": 151.65
        }
    },
    "Tamworth": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -31.12,
            "lat_max": -31.00,
            "lon_min": 150.83,
            "lon_max": 150.99
        }
    },
    "Port Macquarie": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -31.45,
            "lat_max": -31.25,
            "lon_min": 152.80,
            "lon_max": 153.05
        }
    },
    "Coffs Harbour": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -30.32,
            "lat_max": -30.18,
            "lon_min": 153.05,
            "lon_max": 153.20
        }
    },
    "Kalgoorlie": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -30.82,
            "lat_max": -30.65,
            "lon_min": 121.40,
            "lon_max": 121.60
        }
    },
    "Geraldton": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -28.85,
            "lat_max": -28.65,
            "lon_min": 114.55,
            "lon_max": 114.75
        }
    },
    "Fremantle": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -32.10,
            "lat_max": -31.90,
            "lon_min": 115.68,
            "lon_max": 115.88
        }
    },
    "Alice Springs": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -23.75,
            "lat_max": -23.60,
            "lon_min": 133.80,
            "lon_max": 133.95
        }
    },
    "Darwin": {
        "tile_km": 5,
        "width_km": 25,
        "height_km": 25,
        "bbox_override": {
            "lat_min": -12.60,
            "lat_max": -12.30,
            "lon_min": 130.75,
            "lon_max": 131.10
        }
    },
    "Palmerston": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -12.52,
            "lat_max": -12.40,
            "lon_min": 130.95,
            "lon_max": 131.12
        }
    },
    "Katherine": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -14.55,
            "lat_max": -14.35,
            "lon_min": 132.20,
            "lon_max": 132.45
        }
    },
    "Belconnen": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -35.30,
            "lat_max": -35.20,
            "lon_min": 149.02,
            "lon_max": 149.10
        }
    },
    "Gungahlin": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -35.22,
            "lat_max": -35.14,
            "lon_min": 149.10,
            "lon_max": 149.18
        }
    },
    "Tuggeranong": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20,
        "bbox_override": {
            "lat_min": -35.45,
            "lat_max": -35.30,
            "lon_min": 149.02,
            "lon_max": 149.15
        }
    },
    "Warrnambool": {
    "tile_km": 5,
    "width_km": 25,
    "height_km": 20,
    "bbox_override": {
        "lat_min": -38.4600,
        "lat_max": -38.3300,
        "lon_min": 142.4200,
        "lon_max": 142.6700
        }
    },
    "Traralgon": {
    "tile_km": 5,
    "width_km": 20,
    "height_km": 15,
    "bbox_override": {
        "lat_min": -38.2400,
        "lat_max": -38.1200,
        "lon_min": 146.4700,
        "lon_max": 146.6100
        }
    },
    "Bunbury": {
    "tile_km": 5,
    "width_km": 20,
    "height_km": 30,
    "bbox_override": {
        "lat_min": -33.4400,
        "lat_max": -33.2500,
        "lon_min": 115.5700,
        "lon_max": 115.7200
        }
    },

    # === Fallback ===
    "default": {
        "tile_km": 5,
        "width_km": 20,
        "height_km": 20
    }
}


# Google Places API endpoints
GOOGLE_PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
