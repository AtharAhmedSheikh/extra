from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class SentimentAnalysisResult(BaseModel):
    """
    Represents the structured output from the **Conversation Intent Router** (Sentiment Agent).

    This model:
    - Stores the user's message.
    - Determines the next conversational agent.
    - Optionally holds user profile information for personalization.
    - Explains routing decisions for debugging or auditing.
    """

    user_message: str
    """The exact text message sent by the user. Downstream agents rely on this to maintain context."""

    next_agent: Literal[
        "CustomerGreetingAgent",
        "D2CCustomerSupportAgent",
        "B2BBusinessSupportAgent",
    ]
    """
    Specifies the next agent that should handle the conversation.

    Possible values:
    - `"CustomerGreetingAgent"` → For friendly, casual, or non-business conversations.
    - `"D2CCustomerSupportAgent"` → For Direct-to-Consumer product inquiries or support.
    - `"B2BBusinessSupportAgent"` → For Business-to-Business queries, partnerships, or bulk orders.
    """

    routing_reasoning: Optional[str] = None
    """Brief explanation for the chosen sentiment, intent, and next agent. Useful for debugging or audit logs."""

    name: Optional[str] = None
    """The user's name, if available. Useful for personalizing responses."""

    email: Optional[str] = None
    """The user's email address, if available. Useful for follow-up communications."""

    address: Optional[str] = None
    """The user's physical address, if available. Useful for location-based services."""

    socials: Optional[List[str]] = None
    """List of the user's social media profile URLs or usernames, if available."""

    interest_groups: List[Literal[
        "Bluetooth Headphones",
        "Bluetooth Speakers",
        "Wireless Earbuds",
        "Gaming Chairs",
        "Smart Watches",
        "Enclosure",
        "Power Supply",
        "Office Mouse",
        "CPU Coolers",
        "Computer Accessories",
        "Power Banks",
        "Gaming Mouse",
        "Gaming Monitors",
        "Combo",
        "Core"
    ]] = Field(default_factory=list)
    """
    List of interest groups the user belongs to.

    - May be empty or contain one/more allowed items.
    - Each item must exactly match one of the predefined values.
    """
