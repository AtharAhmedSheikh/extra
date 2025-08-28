from typing import List, Optional
from whatsapp_agent.database.base import DataBase
from whatsapp_agent.schema.campaign import CampaignSchema

class CampaignDataBase(DataBase):
    TABLE_NAME = "campaigns"

    def __init__(self):
        super().__init__()

    def create_campaign(self, campaign: CampaignSchema) -> dict:
        """Insert a new campaign"""
        response = self.supabase.table(self.TABLE_NAME).insert(campaign.model_dump()).execute()
        return response.data[0] if response.data else {}

    def get_campaign_by_id(self, campaign_id: str) -> Optional[CampaignSchema]:
        """Fetch a campaign by its ID"""
        response = (
            self.supabase.table(self.TABLE_NAME)
            .select("*")
            .eq("id", campaign_id)
            .execute()
        )
        if response.data:
            return CampaignSchema(**response.data[0])
        return None

    def list_campaigns(self) -> List[CampaignSchema]:
        """List all campaigns"""
        response = self.supabase.table(self.TABLE_NAME).select("*").execute()
        return [CampaignSchema(**row) for row in response.data]

    def list_campaigns_by_user(self, user_id: str) -> List[CampaignSchema]:
        """Fetch campaigns created by a specific user"""
        response = (
            self.supabase.table(self.TABLE_NAME)
            .select("*")
            .eq("created_by", user_id)
            .execute()
        )
        return [CampaignSchema(**row) for row in response.data]

    def update_campaign(self, campaign_id: str, updates: dict) -> dict:
        """Update a campaign"""
        response = (
            self.supabase.table(self.TABLE_NAME)
            .update(updates)
            .eq("id", campaign_id)
            .execute()
        )
        return response.data

    def delete_campaign(self, campaign_id: str) -> dict:
        """Delete a campaign"""
        response = (
            self.supabase.table(self.TABLE_NAME)
            .delete()
            .eq("id", campaign_id)
            .execute()
        )
        return response.data
