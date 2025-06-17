# Relevant business types from Google Places API
BUSINESS_TYPES = [
    "electronics_store",
    "computer_store",
    "office_supply_store",
    "furniture_store",
    "hardware_store",
    "shopping_mall",
    "department_store",
    "university",
    "school",
    "real_estate_agency",
    "accounting",
    "lawyer",
    "car_dealer",
    "travel_agency",
    "convenience_store",
    "grocery_or_supermarket"
]

# Australian states with key cities/regions to crawl
AU_REGIONS = {
    "New South Wales": ["Sydney", "Newcastle", "Wollongong"],
    "Victoria": ["Melbourne", "Geelong", "Ballarat"],
    "Queensland": ["Brisbane", "Gold Coast", "Cairns", "Townsville"],
    "Western Australia": ["Perth", "Fremantle", "Bunbury"],
    "South Australia": ["Adelaide", "Mount Gambier"],
    "Tasmania": ["Hobart", "Launceston"],
    "Australian Capital Territory": ["Canberra"],
    "Northern Territory": ["Darwin", "Alice Springs"]
}


# Mapping of region names to lat,lng coordinates (used for Google Maps API)
REGION_COORDINATES = {
    "Sydney": "-33.8688,151.2093",
    "Newcastle": "-32.9283,151.7817",
    "Wollongong": "-34.4278,150.8931",
    "Melbourne": "-37.8136,144.9631",
    "Geelong": "-38.1499,144.3617",
    "Ballarat": "-37.5622,143.8503",
    "Brisbane": "-27.4698,153.0251",
    "Gold Coast": "-28.0167,153.4000",
    "Cairns": "-16.9186,145.7781",
    "Townsville": "-19.2589,146.8169",
    "Perth": "-31.9505,115.8605",
    "Fremantle": "-32.0569,115.7439",
    "Bunbury": "-33.3271,115.6414",
    "Adelaide": "-34.9285,138.6007",
    "Mount Gambier": "-37.8318,140.7790",
    "Hobart": "-42.8821,147.3272",
    "Launceston": "-41.4388,147.1347",
    "Canberra": "-35.2809,149.1300",
    "Darwin": "-12.4634,130.8456",
    "Alice Springs": "-23.6980,133.8807"
}



# Google Places API endpoints
GOOGLE_PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
