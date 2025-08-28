from typing import List, Optional
from whatsapp_agent.database.base import DataBase

from whatsapp_agent.schema.referrals import ReferralSchema, ReferredUserSchema

class ReferralDataBase(DataBase):
    def __init__(self):
        super().__init__()  # initialize supabase connection

    def add_referral(self, referral: ReferralSchema):
        """Insert a referral record into Supabase"""
        data = referral.dict()  # convert Pydantic model to dict
        response = self.supabase.table("referrals").insert(data).execute()
        return response

    def get_referral_by_code(self, referral_code: str):
        """Fetch referral details from Supabase"""
        response = (
            self.supabase.table("referrals")
            .select("*")
            .eq("referral_code", referral_code)
            .execute()
        )

        return response.data[0] if response.data else None

    def get_referral_by_phone_number(self, phone_number: str):
        """Fetch referral details from Supabase by phone number"""
        response = (
            self.supabase.table("referrals")
            .select("*")
            .eq("referrer_phone", phone_number)
            .execute()
        )
        return response.data[0] if response.data else None

    def add_referred_user(self, referral_code: str, referred_user: ReferredUserSchema):
        """Add a referred user to an existing referral"""
        referral = self.get_referral_by_code(referral_code)
        referral.get("referred_users", []).append(referred_user.dict())
        response = (
            self.supabase.table("referrals")
            .update({"referred_users": referral.get("referred_users", [])})
            .eq("referral_code", referral_code)
            .execute()
        )
        return response
    
    def update_referral(self, referral_code: str):
        """Update an existing referral"""
        referral = self.get_referral_by_code(referral_code)
        response = (
            self.supabase.table("referrals")
            .update({"total_points": referral['total_points'] + 1})
            .eq("referral_code", referral_code)
            .execute()
        )
        return response
    
    