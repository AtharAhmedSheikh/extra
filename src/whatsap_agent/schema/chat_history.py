from datetime import datetime
from typing import Literal, List, Optional
from pydantic import BaseModel

class MessageSchema(BaseModel):
    time_stamp: datetime
    content: str
    message_type: Literal["audio", "text", "image", "document"]
    sender: Literal["customer", "agent", "representative"]

class ChatHistorySchema(BaseModel):
    phone_number: str  # We'll make this the primary key reference to customer
    messages: List[MessageSchema] = []  # Stores full conversation

class EscalationEventSchema(BaseModel):
    event: Literal["escalation_triggered"]
    phone_number: str
    chat_history: List[MessageSchema]

class EndEscalationSchema(BaseModel):
    phone_number: str
    reason: Optional[str] = None

class HumanMessageSchema(BaseModel):
    phone_number: str
    text: str
    representative_id: Optional[str] = None  # tracking ke liye
