from whatsapp_agent.database.campaign import CampaignDataBase
from whatsapp_agent.schema.campaign import CampaignSchema
from whatsapp_agent._debug import Logger
from typing import List, Optional


class CampaignHandler:
    def __init__(self):
        self.db = CampaignDataBase()

    @staticmethod
    def _generate_campaign_id(length: int = 4) -> str:
        """Generates a random uppercase campaign ID."""
        import random
        import string
        try:
            return ''.join(random.choice(string.ascii_uppercase) for _ in range(length))
        except Exception as e:
            Logger.error(f"{__name__}: _generate_campaign_id -> Error generating ID: {e}")
            return "ERROR"

    def create_campaign(self, name: str, end_date: str, start_date: str, status: bool, description: Optional[str] = None, prizes: Optional[List[str]] = None, created_by: str = "representative") -> dict:
        """Create a new campaign"""
        campaign = CampaignSchema(
            created_by=created_by,
            description=description if description else "",
            end_date=end_date,
            start_date=start_date,
            id=self._generate_campaign_id(),
            name=name,
            prizes=prizes if prizes else [],
            status=status
        )

        saved_campaign = self.db.create_campaign(campaign)
        return CampaignSchema(**saved_campaign)

    def check_campaign_status(self, campaign_code: str) -> bool:
        """Check if a campaign is active"""
        campaign = self.db.get_campaign_by_id(campaign_code)
        if campaign:
            return campaign.status
        return False

    def get_all_campaigns(self) -> List[CampaignSchema]:
        """List all campaigns"""
        campaigns = self.db.list_campaigns()
        return campaigns

    def get_campaigns_by_user(self, user_id: str) -> List[CampaignSchema]:
        """List all campaigns created by a specific user"""
        campaigns = self.db.list_campaigns_by_user(user_id)
        return campaigns

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign"""
        try:
            self.db.delete_campaign(campaign_id)
            return True
        except Exception as e:
            Logger.error(f"{__name__}: delete_campaign -> Error deleting campaign: {e}")
            return False