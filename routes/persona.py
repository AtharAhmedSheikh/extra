from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from whatsapp_agent.database.boost_buddy_persona import PersonaDB

persona_router = APIRouter(prefix="/persona")

class PersonaUpdateRequest(BaseModel):
    agent_name: str
    new_persona: str

db = PersonaDB()


@persona_router.get("/get_all")
async def get_personas():
    response = db.supabase.table("boost_buddy_persona").select("agent_name,persona").execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="No personas found.")
    personas = {row["agent_name"]: row["persona"] for row in response.data}
    return personas

@persona_router.patch("/")
async def update_persona(request: PersonaUpdateRequest):
    success = db.update_persona(request.agent_name, request.new_persona)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update persona.")
    return {"message": "Persona updated successfully."}