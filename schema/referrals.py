from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ReferredUserSchema(BaseModel):
    phone_number: str
    time_stamp: str


class ReferralSchema(BaseModel):
    total_points: int = 0
    referrer_id: Optional[str] = None
    referrer_name: Optional[str] = None
    referrer_email: Optional[str] = None
    referrer_phone: Optional[str] = None
    referral_code: Optional[str] = None
    referred_users: List[ReferredUserSchema] = Field(default_factory=list)
    campaign_id: Optional[str] = None
