from agents import function_tool
from whatsapp_agent.database.customer import CustomerDataBase

customer_db = CustomerDataBase()

@function_tool
def escalate_to_human_support_tool(phone_number: str):
    is_updated = customer_db.update_escalation_status(phone_number, True)
    return {"status": "escalated"} if is_updated else {"status": "Sorry, we couldn't escalate your issue."}