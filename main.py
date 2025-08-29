from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from whatsapp_agent.routes.webhook import webhook_router
from whatsapp_agent.routes.callback import callback
from whatsapp_agent.routes.chats import chat_router
from whatsapp_agent.routes.customers import customer_router
from whatsapp_agent.routes.analytics import analytics_router
from whatsapp_agent.routes.websocket_chat import chat_ws_router
from whatsapp_agent.routes.campaign import campaign_router
from whatsapp_agent.routes.persona import persona_router
from whatsapp_agent.routes.upload import upload_router
from whatsapp_agent.routes.secrets import secrets_router
from whatsapp_agent._debug import enable_verbose_logging
from whatsapp_agent.utils.config import Config

# Load environment variables
load_dotenv()
enable_verbose_logging()

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
def get_api_key(api_key: str = Security(api_key_header)):
    expected_key = Config.get('FRONTEND_API_KEY')
    if not api_key or api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


app = FastAPI(
    title="WhatsApp AI Agent API",
    description="""
    This is a WhatsApp AI Agent API that processes incoming WhatsApp messages and responds using AI.
    
    ## Workflow
    1. User sends message on WhatsApp
    2. Meta WhatsApp Cloud API receives message
    3. Webhook receives request
    4. Message is processed
    5. AI Agent generates reply
    6. Reply is sent back to WhatsApp
    
    ## Setup Required
    - Meta WhatsApp Business API credentials
    - OpenAI API key
    - Ngrok for local development
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/ping", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify if the API is running.
    """
    return {
        "status": "healthy",
        "message": "WhatsApp Agent is running",
        "version": "1.0.0"
    }

# Include routers
app.include_router(webhook_router, tags=["Webhook"])
app.include_router(callback, tags=["Callback"])
app.include_router(chat_router, dependencies=[Depends(get_api_key)])
app.include_router(customer_router, dependencies=[Depends(get_api_key)])
app.include_router(analytics_router, dependencies=[Depends(get_api_key)])
app.include_router(chat_ws_router, tags=["WebSocket Chats"])
app.include_router(campaign_router, dependencies=[Depends(get_api_key)])
app.include_router(persona_router, dependencies=[Depends(get_api_key)], tags=["Persona Management"])
app.include_router(upload_router, tags=["Document Upload"], dependencies=[Depends(get_api_key)])
app.include_router(secrets_router, tags=["Secrets"], dependencies=[Depends(get_api_key)])

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="WhatsApp AI Agent API",
        version="1.0.0",
        description="API for WhatsApp AI Agent with detailed workflow",
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000) # set """reload = True""" for hot relod in development