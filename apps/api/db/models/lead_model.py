from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class LeadModel(BaseModel):
    name: str
    address: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    location: dict  # Contains lat/lng
    place_id: str
    types: List[str] = Field(default_factory=list)

    # Location metadata
    state: Optional[str]
    region: Optional[str]  # City
    category: Optional[str]  # e.g. "Retail & Suppliers"
    business_type: Optional[str]  # e.g. "office_supply_store"

    # Timestamp for crawl tracking
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional marketing metadata
    contacted: bool = False
    email_sent: bool = False
    sms_sent: bool = False
    cold_called: bool = False
    tags: List[str] = Field(default_factory=list)

    class Config:
        orm_mode = True
