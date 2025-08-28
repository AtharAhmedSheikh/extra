from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel

class CustomerSchema(BaseModel):
    phone_number: str
    is_active: bool
    escalation_status: Optional[bool] = False
    customer_type: Literal["B2B", "D2C"]
    total_spend: Optional[int] = 0
    customer_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    cart_id: Optional[str] = None
    order_history: Optional[List[str]] = None
    socials: Optional[List[str]] = None
    interest_groups: Optional[List[str]] = None
    customer_quickbook_id: Optional[str] = None
    tags: List[str] = []
    company_name: Optional[str] = None

class PersonalInfoSchema(BaseModel):
    customer_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    socials: Optional[List[str]] = None
    interest_groups: Optional[List[str]] = None