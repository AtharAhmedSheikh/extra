from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from whatsapp_agent._debug import Logger
from whatsapp_agent.utils.websocket import websocket_manager
from whatsapp_agent.utils.whatsapp_message_handler import WhatsAppMessageHandler
from whatsapp_agent.schema.chat_history import MessageSchema
from whatsapp_agent.utils.current_time import _get_current_karachi_time_str
from whatsapp_agent.database.chat_history import ChatHistoryDataBase

chat_ws_router = APIRouter(prefix="/ws")
    
chat_history_db = ChatHistoryDataBase()
message_handler = WhatsAppMessageHandler()

@chat_ws_router.websocket("/{phone_number}")
async def chat_websocket_endpoint(websocket: WebSocket, phone_number: str):
    await websocket_manager.connect(phone_number, websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            Logger.info(f"Frontend says (for {phone_number}): {msg}")

            msg_schema = MessageSchema(
                content=msg,
                message_type="text",
                sender="representative",
                time_stamp=_get_current_karachi_time_str(),
            )

            chat_history_db.add_or_create_message(phone_number, msg_schema)

            # send to WhatsApp API
            await message_handler.send_message(phone_number, msg)

    except WebSocketDisconnect:
        websocket_manager.disconnect(phone_number, websocket)
