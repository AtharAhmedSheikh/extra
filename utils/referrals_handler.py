import re
import random
import string
from pydantic import ValidationError
from typing import Optional
from whatsapp_agent.database.referral import ReferralDataBase
from whatsapp_agent.schema.referrals import ReferralSchema, ReferredUserSchema
from whatsapp_agent.context.global_context import GlobalContext
from whatsapp_agent.utils.whatsapp_message_handler import WhatsAppMessageHandler
from whatsapp_agent.utils.current_time import _get_current_karachi_time_str
from whatsapp_agent.utils.campaign_handler import CampaignHandler
from whatsapp_agent._debug import Logger

DEFAULT_PHONE_NUMBER ="15551304374"

referral_db = ReferralDataBase()

class ReferralHandler:
    @staticmethod
    def _extract_codes(message: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts campaign code and referral code from a message.
        Expected format: (Referral code: _ABCD-ABCDEF_)
        Returns (campaign_code, referral_code) or (None, None).
        """
        try:
            pattern = r"\(Referral code:\s*_([A-Z]{4})-([A-Z]{6})_\)"
            match = re.search(pattern, message)
            if match:
                return match.group(1), match.group(2)
            return None, None
        except Exception as e:
            Logger.error(f"{__name__}: _extract_codes -> Failed to extract codes: {e}")
            return None, None

    def _check_existing_referral(self, phone_number: str, referral_code: str) -> bool:
        """
        Checks if the phone number already exists in referred_users
        for the given referral code.
        """
        try:
            referral = referral_db.get_referral_by_code(referral_code)
            Logger.info(f"_check_existing_referral: referral data: {referral}")

            if not referral:
                return True  # Possibly treat as already existing or invalid code

            for user in referral.get('referred_users', []):
                if user.get('phone_number', None) == phone_number:
                    return True
            return False

        except ValidationError as e:
            Logger.error(f"{__name__}: _check_existing_referral -> Referral data invalid in DB: {e.json()}")
            return True
        except Exception as e:
            Logger.error(f"{__name__}: _check_existing_referral -> Unexpected error: {e}")
            return True

    @staticmethod
    def _generate_referral_code(length: int = 6) -> str:
        """Generates a random uppercase referral code."""
        try:
            return ''.join(random.choice(string.ascii_uppercase) for _ in range(length))
        except Exception as e:
            Logger.error(f"{__name__}: _generate_referral_code -> Error generating code: {e}")
            return "ERROR"

    def _add_user_to_referral(self, phone_number: str, referral_code: str):
        """
        Adds a user to the referral list.
        """
        try:
            referral_db.add_referred_user(referral_code, ReferredUserSchema(
                phone_number=phone_number,
                time_stamp=_get_current_karachi_time_str()
            ))
            Logger.info(f"User {phone_number} added to referral {referral_code}")
        except ValidationError as e:
            Logger.error(f"{__name__}: _add_user_to_referral -> Validation error adding referred user: {e.json()}")
        except Exception as e:
            Logger.error(f"{__name__}: _add_user_to_referral -> Error adding user to referral: {e}")

    async def _increment_referral_count(self, referral_code: str, phone_number: str, send_message: bool = False) -> None:
        """
        Increments the referral count for a given referral code.
        """
        try:
            self._add_user_to_referral(phone_number, referral_code)
            referral = referral_db.get_referral_by_code(referral_code)

            if not referral:
                Logger.error(f"{__name__}: _increment_referral_count -> Referral not found for code {referral_code}")
                return

            referral["total_points"] = referral.get("total_points", 0) + 1
            referral_db.update_referral(referral_code)  # Should pass updated referral object if required

            if send_message and referral.get("referrer_phone"):
                whatsapp_handler = WhatsAppMessageHandler()
                await whatsapp_handler.send_message(
                    referral["referrer_phone"],
                    "✅ Your referral count has been incremented!"
                )
        except Exception as e:
            Logger.error(f"{__name__}: _increment_referral_count -> Error incrementing referral count: {e}")

    @staticmethod
    def _check_campaign_status(campaign_code: str) -> bool:
        """
        Checks if a campaign exists.
        """
        try:
            campaign = CampaignHandler()
            return campaign.check_campaign_status(campaign_code)
        except Exception as e:
            Logger.error(f"{__name__}: _check_campaign_status -> Error checking campaign status: {e}")
            return False

    async def referral_workflow(self, user_message: str, phone_number: str, global_context: Optional[GlobalContext] = None):
        """
        Main workflow for handling referrals.
        """
        try:
            campaign_code, referral_code = self._extract_codes(user_message)
            Logger.info(f"Extracted campaign code: {campaign_code}, referral code: {referral_code}")

            if not campaign_code:
                Logger.warning("Invalid or missing campaign code.")

            if not self._check_campaign_status(campaign_code):
                Logger.warning("Campaign not active or invalid.")
                
            if not referral_code:
                Logger.warning("Invalid or missing referral code.")

            if self._check_existing_referral(phone_number, referral_code):
                Logger.warning("This user has already been referred with this code.")
            else:
                # Increment referral count for the referrer
                await self._increment_referral_count(referral_code, phone_number, send_message=True)

            # Check if referral exists for the phone number
            referral = referral_db.get_referral_by_phone_number(phone_number)
            if not referral:
                # Generate new referral code for this user
                new_referral_code = self._generate_referral_code()
                if new_referral_code == "ERROR":
                    Logger.error(f"{__name__}: referral_workflow -> Error generating referral code, please try again later.")

                try:
                    new_referral = ReferralSchema(
                        total_points=0,
                        referrer_id=phone_number,
                        referrer_name=global_context.customer_context.customer_name if global_context else "",
                        referrer_email=global_context.customer_context.email if global_context else "",
                        referrer_phone=phone_number,
                        referral_code=new_referral_code,
                        referred_users=[],
                        campaign_id=campaign_code,
                    )
                except ValidationError as e:
                    Logger.error(f"{__name__}: referral_workflow -> New referral data invalid: {e.json()}")

                # Save to DB
                try:
                    referral_db.add_referral(new_referral)
                except Exception as e:
                    Logger.error(f"{__name__}: referral_workflow -> Failed to add new referral: {e}")

                return self._static_message(new_referral_code)

            return self._static_message(referral['referral_code'])

        except Exception as e:
            Logger.error(f"{__name__}: referral_workflow -> Unexpected error: {e}")

    def _static_message(self, referral_code: str, campaign_code: str = "QTMR") -> str:
        """
        Generates a friendly and engaging static message for the referral.
        """
        referral_link = self._generate_referral_link(
            "👋 Hi! I'm inviting you to try *Boost Buddy WhatsApp Bot* 🚀 "
            "It's super useful and easy to use.  \n"
            f"Here's your referral code: (Referral code: _{campaign_code}-{referral_code}_) 🎉  \n"
            "👉 Just send this code to get started!"
        )
        return (
            f"🎉 Thank you for being part of Boost Buddy! 🎉\n\n"
            f"Share this exclusive referral code with your friends and family:\n\n"
            f"🔑 {referral_link}\n\n"
            f"Every time they shop using your code, you both get amazing rewards! 🛍️✨\n"
            f"Start sharing now and enjoy great savings together! 💸"
        )
        

    @staticmethod
    def _generate_referral_link(message: str, phone_number: str = DEFAULT_PHONE_NUMBER) -> str:
        import urllib.parse
        """
        Generates a WhatsApp referral link
        """
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{phone_number}/?text={encoded_message}"
