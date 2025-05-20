from app.db.mongo import leads_collection
from app.models.lead import LeadDB
from pymongo.errors import DuplicateKeyError

# Add unique index
leads_collection.create_index(
    [("name", 1), ("address", 1)],
    unique=True
)

def insert_leads(leads: list):
    saved = []
    for lead in leads:
        lead_data = LeadDB(**lead).dict()
        try:
            result = leads_collection.insert_one(lead_data)
            lead_data["_id"] = str(result.inserted_id)
            saved.append(lead_data)
        except DuplicateKeyError:
            continue
        except Exception as e:
            print(f"Error saving lead: {e}")
    return saved

def get_all_leads():
    leads = []
    for lead in leads_collection.find():
        lead['_id'] = str(lead['_id'])  # Convert ObjectId to string
        leads.append(lead)
    return leads

