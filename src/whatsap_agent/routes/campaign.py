from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any

from whatsapp_agent.utils.campaign_handler import CampaignHandler
from whatsapp_agent.schema.campaign import CampaignSchema


campaign_router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

campaign_handler = CampaignHandler()

@campaign_router.post("/")
def create_campaign(
    data: Dict[str, Any] = Body(
        ...,
        examples=[{
            "name": "Summer Giveaway",
            "start_date": "2025-08-01",
            "end_date": "2025-08-15",
            "status": True,
            "created_by": "admin_user",
            "description": "A fun summer campaign with cool prizes",
            "prizes": ["iPhone 15", "MacBook Air", "Amazon Gift Card"]
        }],
    )
):
    """
    Create a new campaign.
    Accepts raw JSON body from frontend.
    """
    try:
        campaign = campaign_handler.create_campaign(
            name=data.get("name"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            status=data.get("status", False),
            created_by=data.get("created_by", "representative"),
            description=data.get("description"),
            prizes=data.get("prizes"),
        )
        if not campaign:
            raise HTTPException(status_code=400, detail="Failed to create campaign")
        return campaign
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@campaign_router.get("/", response_model=List[CampaignSchema])
def get_all_campaigns():
    return campaign_handler.get_all_campaigns()

@campaign_router.get("/{campaign_id}", response_model=CampaignSchema)
def get_campaign_by_id(campaign_id: str):
    campaign = campaign_handler.db.get_campaign_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@campaign_router.get("/user/{user_id}", response_model=List[CampaignSchema])
def get_campaigns_by_user(user_id: str):
    return campaign_handler.get_campaigns_by_user(user_id)


@campaign_router.get("/{campaign_id}/status")
def check_campaign_status(campaign_id: str):
    is_active = campaign_handler.check_campaign_status(campaign_id)
    return {"campaign_id": campaign_id, "active": is_active}

@campaign_router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str):
    success = campaign_handler.delete_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete campaign")
    return {"message": "Campaign deleted successfully", "campaign_id": campaign_id}
