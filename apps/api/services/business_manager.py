from db.mongo import db
from db.queries import is_duplicate, insert_lead
from utils.helpers import transform_place_result


class BusinessManager:
    def __init__(self):
        pass

    async def filter_and_save_results(self, results: list, state: str, region: str):
        count = 0
        for result in results:
            place_id = result.get("place_id") or result.get("id")
            # print("Checking place_id:", place_id)

            if not place_id or await is_duplicate(db, place_id):
                # print("Skipping duplicate or missing:", place_id)
                continue

            business_data = transform_place_result(result)
            business_data["state"] = state
            business_data["region"] = region

            await insert_lead(db, business_data)
            count += 1
        return count
