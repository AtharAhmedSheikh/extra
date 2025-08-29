from datetime import datetime
from typing import Dict, Any, Optional, List, cast
from whatsapp_agent.database.base import DataBase
from whatsapp_agent.schema.chat_history import ChatHistorySchema, MessageSchema
from whatsapp_agent._debug import Logger

class ChatHistoryDataBase(DataBase):
    TABLE_NAME = "chat_history"

    def __init__(self):
        super().__init__()

    def _convert_dt(self, obj):
        """Recursively convert datetime objects in nested structures to ISO strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, list):
            return [self._convert_dt(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self._convert_dt(v) for k, v in obj.items()}
        return obj

    def _create_chat_history(self, chat: ChatHistorySchema) -> Dict[str, Any]:
        """Insert a new chat history record."""
        data = self._convert_dt(chat.dict())
        response = self.supabase.table(self.TABLE_NAME).insert(data).execute()
        Logger.info("Created new chat history")
        return response.data

    def _get_chat_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Fetch chat history by phone number."""
        response = self.supabase.table(self.TABLE_NAME) \
            .select("*") \
            .eq("phone_number", phone_number) \
            .limit(1) \
            .execute()
        
        Logger.info("Fetched chat by phone")
        return response.data[0] if response.data else None

    def add_message(self, phone_number: str, message: MessageSchema) -> bool:
        """Append a message to the existing chat history for a customer."""
        existing_chat = self._get_chat_by_phone(phone_number)
        if not existing_chat:
            Logger.warning(f"No existing chat found for phone: {phone_number}")
            return False

        messages = existing_chat.get("messages", [])
        messages.append(message.dict())
        messages = self._convert_dt(messages)

        response = self.supabase.table(self.TABLE_NAME) \
            .update({"messages": messages}) \
            .eq("phone_number", phone_number) \
            .execute()

        Logger.info("Updated chat history with new message")
        return bool(response.data)

    def delete_chat(self, phone_number: str) -> bool:
        """Delete a chat history by phone number."""
        response = self.supabase.table(self.TABLE_NAME) \
            .delete() \
            .eq("phone_number", phone_number) \
            .execute()
        
        Logger.info(f"Deleted chat history of {phone_number}")
        return bool(response.data)

    def add_or_create_message(self, phone_number: str, message: MessageSchema) -> bool:
        """Add message to existing chat history or create a new record."""
        existing_chat = self._get_chat_by_phone(phone_number)

        if existing_chat:
            messages = existing_chat.get("messages", [])
            messages.append(message.dict())
            messages = self._convert_dt(messages)

            response = self.supabase.table(self.TABLE_NAME) \
                .update({"messages": messages}) \
                .eq("phone_number", phone_number) \
                .execute()
            Logger.info("Added message to existing chat history")
            return bool(response.data)
        else:
            new_chat = ChatHistorySchema(
                phone_number=phone_number,
                messages=[message]
            )
            self._create_chat_history(new_chat)
            return True


    def get_recent_chat_history_by_phone(self, phone_number: str, limit: int = 10) -> List[MessageSchema]:
        """
        Retrieve the most recent messages for a given phone number.
        Args:
            phone_number: The phone number to search for.
            limit: Number of recent messages to return.
        Returns:
            A list of message dictionaries sorted by datetime (newest last).
        """
        chat = self._get_chat_by_phone(phone_number)
        if not chat or "messages" not in chat:
            Logger.warning(f"No chat history found for phone {phone_number}")
            return []

        # Sort messages by their timestamp
        messages = chat["messages"]
        messages.sort(key=lambda m: m.get("time_stamp"))

        # # Cast messages to the expected type

        messages = [MessageSchema.model_validate(message) for message in messages]
        Logger.info(f"Fetched recent chat history for phone {phone_number}")
        # Return the last `limit` messages
        return messages[-limit:]
