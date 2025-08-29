from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from whatsapp_agent.bot.whatsapp_bot import WhatsappBot
from whatsapp_agent._debug import Logger
from whatsapp_agent.utils.config import Config

webhook_router = APIRouter(tags=["Webhook"])

def _get_verify_token():
    return Config.get("WHATSAPP_VERIFY_TOKEN")

@webhook_router.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    Logger.info("verifying hook")
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == _get_verify_token():
        challenge = params.get("hub.challenge")
        return PlainTextResponse(content=challenge)
    return "Invalid verification"


@webhook_router.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    # Check if the message is a voice message
    try:
        entry = data.get("entry", [])[0]
        if "changes" in entry and len(entry["changes"]) > 0:
            change = entry["changes"][0]
            if "value" in change and "messages" in change["value"]:
                message = change["value"]["messages"][0]
                
                # Check message type
                message_type = message.get("type")
                if message_type in ["audio", "voice"]:
                    Logger.info("Received voice message")
                    # Handle voice message
                    await WhatsappBot.execute_workflow(data, is_voice=True)
                elif message_type in ["image", "document", "video"]:
                    Logger.info(f"Received {message_type} message")
                    # Handle media message
                    await WhatsappBot.execute_workflow(data, is_voice=False)
                else:
                    # Handle text message
                    await WhatsappBot.execute_workflow(data, is_voice=False)
    except Exception as e:
        Logger.error(f"{__name__}: receive_message -> Error processing message: {e}")
        # await WhatsappBot.execute_workflow(data, is_voice=False)

    return "EVENT_RECEIVED"
