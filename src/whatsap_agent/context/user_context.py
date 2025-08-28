from typing import Literal, Optional
from pydantic import BaseModel

class CustomerContextSchema(BaseModel):
    phone_number: str
    customer_type: Literal["B2B", "D2C"]
    customer_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    customer_quickbook_id: Optional[str] = None

