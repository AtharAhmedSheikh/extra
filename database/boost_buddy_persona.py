from whatsapp_agent.database.base import DataBase

class PersonaDB(DataBase):
    def get_persona(self, agent_name: str) -> str:
        response = self.supabase.table("boost_buddy_persona").select("persona").eq("agent_name", agent_name).single().execute()
        return response.data["persona"] if response.data else ""

    def update_persona(self, agent_name: str, new_persona: str) -> bool:
        response = self.supabase.table("boost_buddy_persona").update({"persona": new_persona}).eq("agent_name", agent_name).execute()
        return bool(response.data)