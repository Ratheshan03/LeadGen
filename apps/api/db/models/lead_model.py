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
    state: Optional[str]  # Added for state tracking
    region: Optional[str]  # Specific area or sub-region if available
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional metadata for marketing flow
    contacted: bool = False
    email_sent: bool = False
    sms_sent: bool = False
    cold_called: bool = False
    tags: List[str] = Field(default_factory=list)

    class Config:
        orm_mode = True
