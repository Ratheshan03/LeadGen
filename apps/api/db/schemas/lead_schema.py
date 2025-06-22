from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class LeadBase(BaseModel):
    name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    location: Optional[dict]  # {"lat": ..., "lng": ...}
    place_id: str
    types: Optional[List[str]] = Field(default_factory=list)
    state: Optional[str]
    region: Optional[str]
    
    # Added for better categorization
    category: Optional[str]
    business_type: Optional[str]


class LeadCreate(LeadBase):
    pass


class LeadInDB(LeadBase):
    id: str
    retrieved_at: datetime
    contacted: bool = False
    email_sent: bool = False
    sms_sent: bool = False
    cold_called: bool = False
    tags: List[str] = Field(default_factory=list)


class LeadPublic(BaseModel):
    id: str
    name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    location: Optional[dict]
    types: Optional[List[str]] = Field(default_factory=list)
    state: Optional[str]
    region: Optional[str]
    category: Optional[str]
    business_type: Optional[str]
    tags: List[str] = Field(default_factory=list)
