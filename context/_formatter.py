from typing import List

from whatsapp_agent.schema.chat_history import MessageSchema
from whatsapp_agent.context.user_context import CustomerContextSchema


def customer_context_to_prompt(context: CustomerContextSchema) -> str:
    """
    Convert CustomerContextSchema into a clean system prompt block.
    Only non-empty fields are included.
    """
    # Get dict with None values removed
    data = context.dict(exclude_none=True)

    # Map field names to readable labels
    labels = {
        "phone_number": "Phone Number",
        "customer_type": "Customer Type",
        "customer_name": "Customer Name",
        "email": "Email",
        "address": "Address",
        "customer_quickbook_id": "QuickBook ID"
    }

    # Build lines only for fields that exist
    lines = [f"{labels[key]}: {value}" for key, value in data.items() if key in labels]

    if not lines:
        return ""  # No context to add

    # Format in a clear block for system prompt
    prompt_block = (
        "## Customer Context\n"
        + "\n".join(lines) +
        "\n---\n"
    )
    return prompt_block

def chat_history_to_prompt(messages: List[MessageSchema]) -> str:
    """
    Convert chat history into a readable block for system prompt.
    """
    if not messages:
        return ""

    lines = []
    for msg in messages:
        # Format time
        time_str = msg.time_stamp.strftime("%Y-%m-%d %H:%M")
        
        # Show content differently if not text
        if msg.message_type == "text":
            content_display = msg.content
        else:
            content_display = f"[{msg.message_type.upper()}] {msg.content}"

        # Capitalize sender
        sender_name = msg.sender.capitalize()

        lines.append(f"[{time_str}] {sender_name}: {content_display}")

    return "## Chat History\n" + "\n".join(lines) + "\n---\n"

