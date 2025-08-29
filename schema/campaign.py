from typing import List, Optional
from pydantic import BaseModel

class CampaignSchema(BaseModel):
    id: str
    name: str
    prizes: List[str]
    description: Optional[str] = None
    start_date: str
    end_date: str
    status: bool
    created_by: str