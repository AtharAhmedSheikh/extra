from typing import List
from whatsapp_agent.context.user_context import CustomerContextSchema
from whatsapp_agent.schema.chat_history import MessageSchema
from pydantic import BaseModel
    
class CustomerContextSchemaExtra(CustomerContextSchema):
    formatted_context: str

class MessageSchemaExtra(BaseModel):
    formatted_message: str
    messages: List[MessageSchema]

class GlobalContext(BaseModel):
    customer_context: CustomerContextSchemaExtra
    messages: MessageSchemaExtra
