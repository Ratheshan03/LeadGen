from db.mongo import db
from db.queries import is_duplicate, insert_lead, insert_leads_batch
from utils.helpers import transform_place_result
from services.google_maps import GoogleMapsService

class BusinessManager:
    def __init__(self):
        pass

    async def filter_and_save_results(self, results: list, state: str, region: str):
        """
        Manual insert version (called by the user during testing).
        Processes one place at a time, filtering duplicates and inserting individually.
        """
        count = 0
        for result in results:
            place_id = result.get("place_id") or result.get("id")

            if not place_id or await is_duplicate(db, place_id):
                continue
            
            print(result)
            business_data = transform_place_result(result)
            business_data["state"] = state
            business_data["region"] = region

            await insert_lead(db, business_data)
            count += 1
        return count

    async def save_crawled_batch(self, places: list, state: str, region: str, category: str, business_type: str):
        """
        For automated batch insertion from crawler. Uses batch insert with deduplication.
        """
        processed = []
        for place in places:
            # print(place.get("displayName", {}).get("text"), "|", place.get("types"))
            place_id = place.get("place_id") or place.get("id")
            if not place_id:
                continue

            business_data = transform_place_result(place)
            business_data["state"] = state
            business_data["region"] = region
            business_data["category"] = category
            business_data["business_type"] = business_type

            processed.append(business_data)

        inserted_count = await insert_leads_batch(db, processed)
        return inserted_count


    async def crawl_using_text_search(self, search_query: str, tiles: list, dry_run: bool = False):
        total_saved = 0
        failures = []
        detailed_results = []
        dry_run_summary = []

        if dry_run:
            for tile in tiles:
                dry_run_summary.append({
                    "region": tile.get("region"),
                    "state": tile.get("state"),
                    "business_type": search_query,
                    "tile_name": tile.get("tile_name"),
                    "simulated_request": True
                })
            return {
                "message": "✅ Dry run simulation complete",
                "total_saved": 0,
                "tiles_scanned": len(tiles),
                "failures": [],
                "details": dry_run_summary
            }

        maps_service = GoogleMapsService()

        for tile in tiles:
            location_bias = {
                "rectangle": {
                    "low": tile.get("low"),
                    "high": tile.get("high")
                }
            }

            try:
                print(f"\n📍 Tile: {tile.get('region')} ({tile.get('state')}), Query: '{search_query}'")

                result_data = maps_service.text_search_places(
                    text_query=search_query,
                    location_bias=location_bias,
                    max_results=20
                )

                results = result_data.get("results", [])
                pages_fetched = result_data.get("pages_fetched", 0)
                count = 0

                for result in results:
                    place_id = result.get("place_id") or result.get("id")
                    if not place_id or await is_duplicate(db, place_id):
                        continue

                    business_data = transform_place_result(result)
                    business_data.update({
                        "state": tile.get("state"),
                        "region": tile.get("region"),
                        "category": "TextSearch",
                        "business_type": search_query.lower()
                    })

                    await insert_lead(db, business_data)
                    count += 1

                print(f"✅ {count} saved from {pages_fetched} pages")

                total_saved += count
                detailed_results.append({
                    "region": tile.get("region"),
                    "state": tile.get("state"),
                    "saved": count,
                    "pages": pages_fetched
                })

            except Exception as e:
                error_msg = f"❌ Error during tile crawl [{tile.get('region')} - {tile.get('state')} - Query: {search_query}]: {str(e)}"
                print(error_msg)
                failures.append({
                    "region": tile.get("region"),
                    "state": tile.get("state"),
                    "business_type": search_query,
                    "error": str(e)
                })

        return {
            "message": "✅ Full crawl completed",
            "total_saved": total_saved,
            "tiles_scanned": len(tiles),
            "failures": failures,
            "details": detailed_results
        }

        

    # async def crawl_custom_text_search(self, query: str, state: str, region: str, dry_run: bool = False):
    #     maps_service = GoogleMapsService()
    #     tiles = generate_tiles_for_region_unified(state, region)

    #     if not tiles:
    #         return {"error": f"No tiles found for region {region}"}
        
    #     if dry_run:
    #         return {
    #             "message": f"✅ DRY RUN for {region}, {state}",
    #             "total_tiles": len(tiles),
    #             "expected_requests": len(tiles),
    #             "details": [
    #                 {
    #                     "state": state,
    #                     "region": region,
    #                     "business_type": query,
    #                     "tile_count": len(tiles),
    #                 }
    #             ]
    #         }


    #     total_saved = 0
    #     duplicates = 0
    #     failures = []
    #     saved_data = []

    #     for tile in tiles:
    #         location_bias = {
    #             "rectangle": {
    #                 "low": tile["low"],
    #                 "high": tile["high"]
    #             }
    #         }

    #         try:
    #             print(f"Searching {query} in {region}, {state}")
    #             result_data = maps_service.text_search_places(query, location_bias)
    #             results = result_data["results"]

    #             for result in results:
    #                 place_id = result.get("place_id") or result.get("id")
    #                 if not place_id or await is_duplicate(db, place_id):
    #                     duplicates += 1
    #                     continue

    #                 business_data = transform_place_result(result)
    #                 business_data["state"] = state
    #                 business_data["region"] = region
    #                 business_data["category"] = "TextSearch"
    #                 business_data["business_type"] = query.lower()

    #                 await insert_lead(db, business_data)
    #                 total_saved += 1
    #                 saved_data.append(business_data)

    #         except Exception as e:
    #             failures.append({"region": region, "state": state, "error": str(e)})

    #     cleaned_samples = [
    #         {"_id": str(doc.get("_id")), **{k: v for k, v in doc.items() if k != "_id"}}
    #         for doc in saved_data[:10]
    #     ]

    #     return {
    #         "message": "✅ Custom crawl done.",
    #         "total_saved": total_saved,
    #         "duplicates_skipped": duplicates,
    #         "tiles_scanned": len(tiles),
    #         "failures": failures,
    #         "details": [
    #             {
    #                 "state": state,
    #                 "region": region,
    #                 "saved": total_saved
    #             }
    #         ],
    #         "sample_results": cleaned_samples
    #     }



