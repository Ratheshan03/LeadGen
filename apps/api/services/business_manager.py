from db.mongo import db
from db.queries import is_duplicate, insert_lead, insert_leads_batch, export_to_excel, upsert_lead_with_business_type
from utils.helpers import transform_place_result, generate_tiles_for_australia, split_tile_longer_side
from services.google_maps import GoogleMapsService

class BusinessManager:
    def __init__(self):
        pass

    # Max depth of saturation subdivision. A tile that returns Google's hard max
    # of 60 results (3 pages) is split into 2 halves; a half that is STILL
    # saturated is split again (into quarters); after that we stop and accept
    # partial results. depth 0 = original tile, so splitting is allowed at
    # depths 0 and 1 → at most 2 rounds of division.
    MAX_SATURATION_DEPTH = 2

    # Minimum in-bounds results required to treat a tile as SATURATED and worth
    # splitting. Google Text Search returns up to 60 raw results (3 pages), but
    # many can fall outside the tile and get geo-filtered out. Fetching 3 pages
    # alone does NOT mean the tile is truncating leads — only when the tile hits
    # Google's hard 60-result cap in-bounds is there almost certainly more being
    # cut off. Set to 60 (the exact cap): a tile returning 55-59 in-bounds did
    # NOT hit the wall, so it likely already has all its results and splitting it
    # would waste requests for ~0 extra leads (measured: borderline 56-62 types
    # recovered 0-2 leads for ~5 requests each). Requiring the full 60 skips
    # those wasteful borderline splits while keeping every genuinely-truncated
    # tile (park, parking, school, etc. return a clean 60 with many more behind).
    SATURATION_MIN_RESULTS = 60

    def _crawl_tile_recursive(self, maps_service, query: str, tile: dict, depth: int):
        """
        Crawl one tile for one business type, recursively subdividing SATURATED
        tiles up to MAX_SATURATION_DEPTH levels.

        Google Text Search caps at 60 results (3 pages). If a tile returns all 3
        pages it likely truncated more businesses, so (while under the depth cap
        and quota permitting) we split it along its longer side into 2 and crawl
        each child. Splitting stops at MAX_SATURATION_DEPTH or when quota runs out.

        Returns: (results, requests_made, quota_exceeded, pages_fetched)
        - pages_fetched is for the tile at THIS level (used for reporting only).
        """
        location_bias = {"rectangle": {"low": tile.get("low"), "high": tile.get("high")}}
        result_data = maps_service.text_search_places(
            text_query=query, location_bias=location_bias, max_results=20
        )

        results = list(result_data.get("results", []))
        pages_fetched = result_data.get("pages_fetched", 0)
        requests_made = result_data.get("requests_made", 0)
        quota_exceeded = bool(result_data.get("quota_exceeded"))

        # A tile is truly SATURATED only if it fetched all 3 pages AND returned
        # near the 60-result cap of in-bounds places. Fetching 3 pages with few
        # usable (in-bounds) results means Google's raw results were mostly
        # outside the tile — nothing is being truncated, so splitting would just
        # waste requests. `results` here holds only THIS tile's in-bounds places.
        is_saturated = pages_fetched >= 3 and len(results) >= self.SATURATION_MIN_RESULTS

        # Subdivide if saturated, not out of quota, and still under the depth cap.
        if is_saturated and not quota_exceeded and depth < self.MAX_SATURATION_DEPTH:
            sub_tiles = split_tile_longer_side(tile)
            if sub_tiles:
                print(f"🔬 Tile saturated ({len(results)} in-bounds, 3/3 pages) at depth {depth} "
                      f"— splitting '{tile.get('tile_name')}' into {len(sub_tiles)} for '{query}'")
                for sub in sub_tiles:
                    sub_results, sub_reqs, sub_quota, _ = self._crawl_tile_recursive(
                        maps_service, query, sub, depth + 1
                    )
                    requests_made += sub_reqs
                    results.extend(sub_results)
                    if sub_quota:
                        quota_exceeded = True
                        break  # stop subdividing once quota is hit

        return results, requests_made, quota_exceeded, pages_fetched

    def _crawl_tile_with_saturation(self, maps_service, query: str, tile: dict):
        """
        Public entry point: crawl a tile with depth-limited saturation
        subdivision and return de-duplicated results.

        Returns: (results, requests_made, quota_exceeded, pages_fetched)
        - results: de-duplicated place dicts across the tile and all its splits
        - requests_made: total HTTP requests spent (tile + all subdivisions)
        - quota_exceeded: True if the quota cap was hit at any point
        - pages_fetched: pages fetched on the ORIGINAL tile (for reporting)
        """
        results, requests_made, quota_exceeded, pages_fetched = self._crawl_tile_recursive(
            maps_service, query, tile, depth=0
        )

        # De-dup merged results by place id (a business near a split seam can
        # appear in more than one child tile).
        seen_ids = set()
        deduped = []
        for r in results:
            rid = r.get("place_id") or r.get("id")
            if rid and rid in seen_ids:
                continue
            if rid:
                seen_ids.add(rid)
            deduped.append(r)

        return deduped, requests_made, quota_exceeded, pages_fetched

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
        saved_data = []          # accumulates all places for Excel export
        api_requests_total = 0   # sum of HTTP requests across tiles
        quota_exceeded = False

        for tile in tiles:
            try:
                print(f"\n📍 Tile: {tile.get('region')} ({tile.get('state')}), Query: '{search_query}'")

                results, requests_made, tile_quota_hit, pages_fetched = self._crawl_tile_with_saturation(
                    maps_service, search_query, tile
                )
                api_requests_total += requests_made
                if tile_quota_hit:
                    quota_exceeded = True
                count = 0
                updated_count = 0

                for result in results:
                    place_id = result.get("place_id") or result.get("id")
                    if not place_id:
                        continue

                    business_data = transform_place_result(result)
                    business_data.update({
                        "state": tile.get("state"),
                        "region": tile.get("region"),
                        "category": "TextSearch"
                    })

                    # Use upsert to handle multiple business_types per place
                    is_new, operation = await upsert_lead_with_business_type(
                        db, business_data, search_query.lower()
                    )

                    if is_new:
                        count += 1
                    elif operation == "updated":
                        updated_count += 1

                    # Always add to saved_data for Excel export (regardless of new/updated/no-change)
                    business_data["business_types"] = business_data.get("business_types", [search_query.lower()])
                    if search_query.lower() not in business_data["business_types"]:
                        business_data["business_types"].append(search_query.lower())
                    saved_data.append(business_data)

                total_results = len(results)
                if updated_count > 0:
                    print(f"✅ {count} new + {updated_count} updated ({total_results} total in Excel) from {pages_fetched} pages")
                else:
                    print(f"✅ {count} saved ({total_results} total in Excel) from {pages_fetched} pages")

                total_saved += count
                detailed_results.append({
                    "region": tile.get("region"),
                    "state": tile.get("state"),
                    "saved": count,
                    "pages": pages_fetched
                })

                # Halt remaining tiles once the monthly quota cap is reached.
                if quota_exceeded:
                    print("🛑 Quota cap reached — halting remaining tiles for this query.")
                    break

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
            "tiles_scanned": len(detailed_results),
            "failures": failures,
            "details": detailed_results,
            "saved_data": saved_data,
            "api_requests_total": api_requests_total,
            "quota_exceeded": quota_exceeded
        }

        
    async def crawl_custom_text_search(
        self,
        query: str,
        state: str,
        region: str,
        tiles: list,
        dry_run: bool = False
    ):
        maps_service = GoogleMapsService()

        if not tiles:
            return {"error": f"No tiles found for region {region}, state {state}"}

        if dry_run:
            dry_run_summary = [{
                "state": tile.get("state"),
                "region": tile.get("region"),
                "business_type": query,
                "tile_name": tile.get("tile_name"),
                "simulated_request": True
            } for tile in tiles]

            return {
                "message": f"✅ Dry run for {region}, {state} complete.",
                "total_saved": 0,
                "tiles_scanned": len(tiles),
                "failures": [],
                "details": dry_run_summary,
                "api_requests_total": 0  # ✅ explicit for clarity
            }

        total_saved = 0
        failures = []
        detailed_results = []
        saved_data = []
        api_requests_total = 0  # ✅ sum requests across all tiles
        quota_exceeded = False

        for tile in tiles:
            try:
                print(f"\n📍 Custom Tile: {tile.get('region')} ({tile.get('state')}), Query: '{query}'")

                results, requests_made, tile_quota_hit, pages_fetched = self._crawl_tile_with_saturation(
                    maps_service, query, tile
                )
                api_requests_total += requests_made
                if tile_quota_hit:
                    quota_exceeded = True

                count = 0
                updated_count = 0
                for result in results:
                    place_id = result.get("place_id") or result.get("id")
                    if not place_id:
                        continue

                    business_data = transform_place_result(result)
                    business_data.update({
                        "state": tile.get("state"),
                        "region": tile.get("region"),
                        "category": "TextSearch"
                    })

                    # Use upsert to handle multiple business_types per place
                    is_new, operation = await upsert_lead_with_business_type(
                        db, business_data, query.lower()
                    )

                    if is_new:
                        count += 1
                        business_data["business_types"] = [query.lower()]
                    elif operation == "updated":
                        updated_count += 1

                    # Always add to saved_data for Excel export (regardless of new/updated/no-change)
                    # Excel should show ALL places returned by Google for this region+business_type
                    business_data["business_types"] = business_data.get("business_types", [query.lower()])
                    if query.lower() not in business_data["business_types"]:
                        business_data["business_types"].append(query.lower())
                    saved_data.append(business_data)

                total_results = len(results)
                if updated_count > 0:
                    print(f"✅ {count} new + {updated_count} updated ({total_results} total in Excel) from {pages_fetched} pages ({requests_made} HTTP requests)")
                else:
                    print(f"✅ {count} saved ({total_results} total in Excel) from {pages_fetched} pages ({requests_made} HTTP requests)")

                detailed_results.append({
                    "region": tile.get("region"),
                    "state": tile.get("state"),
                    "saved": count,
                    "pages": pages_fetched,
                    "requests": requests_made  # ✅ per-tile visibility
                })
                total_saved += count

                # Halt remaining tiles for this business type once quota is hit.
                if quota_exceeded:
                    print("🛑 Quota cap reached — halting remaining tiles for this query.")
                    break

            except Exception as e:
                error_msg = f"❌ Error in tile [{tile.get('region')} - {tile.get('state')} - Query: {query}]: {str(e)}"
                print(error_msg)
                failures.append({
                    "region": tile.get("region"),
                    "state": tile.get("state"),
                    "business_type": query,
                    "error": str(e)
                })

        cleaned_samples = [
            {"_id": str(doc.get("_id")), **{k: v for k, v in doc.items() if k != "_id"}}
            for doc in saved_data[:10]
        ]

        return {
            "message": "✅ Custom crawl completed",
            "total_saved": total_saved,
            "tiles_scanned": len(detailed_results),
            "failures": failures,
            "details": detailed_results,
            "sample_results": cleaned_samples,
            "saved_data": saved_data,
            "api_requests_total": api_requests_total,  # ✅ aggregate
            "quota_exceeded": quota_exceeded
        }


