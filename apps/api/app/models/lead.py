from pydantic import BaseModel, Field
from typing import Optional, List

class LeadCreate(BaseModel):
    name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    status: Optional[str]
    rating: Optional[float]
    total_reviews: Optional[int]
    opening_hours: Optional[List[str]] = []

class LeadDB(LeadCreate):
    contacted: bool = False
    email_sent: bool = False
    sms_sent: bool = False
    cold_called: bool = False
    tags: Optional[List[str]] = Field(default_factory=list)

