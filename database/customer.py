from typing import Optional, List, Dict, Any, cast
from whatsapp_agent._debug import Logger
from whatsapp_agent.database.base import DataBase 
from whatsapp_agent.schema.customer_schema import CustomerSchema

class CustomerDataBase(DataBase):
    TABLE_NAME = "customers"  # Make sure your Supabase table is named this

    def __init__(self):
        super().__init__()  # Calls DataBase constructor to connect

    def add_customer(self, customer: CustomerSchema) -> CustomerSchema:
        """Insert a new customer record."""
        data = customer.dict()
        response = self.supabase.table(self.TABLE_NAME).insert(data).execute()
        Logger.debug(f"Created new customer: {response.data[0]}")
        return cast(CustomerSchema, response.data[0])

    def get_customer_by_phone(self, phone_number: str) -> Optional[CustomerSchema]:
        """Fetch a customer by phone number."""
        response = self.supabase.table(self.TABLE_NAME) \
            .select("*") \
            .eq("phone_number", phone_number) \
            .limit(1) \
            .execute()
        
        if response.data:
            Logger.debug(f"Fetched customer by phone: {response.data}")
            return CustomerSchema.model_validate(response.data[0])
        return None

    def update_customer(self, phone_number: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer details."""
        # Validate and clean the updates
        clean_updates = {
            k: v for k, v in updates.items()
            if v not in (None, [], "")
        }
        # Remove escalation_status if it is not provided
        clean_updates.pop('escalation_status', None)
        response = self.supabase.table(self.TABLE_NAME) \
            .update(clean_updates) \
            .eq("phone_number", phone_number) \
            .execute()
        Logger.info(f"Updated customer details for phone: {phone_number}")
        return response.data

    def delete_customer(self, phone_number: str) -> Dict[str, Any]:
        """Delete a customer by phone number."""
        response = self.supabase.table(self.TABLE_NAME) \
            .delete() \
            .eq("phone_number", phone_number) \
            .execute()
        Logger.info(f"Deleted customer {phone_number}")
        return response.data

    def list_customers(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List customers with optional limit."""
        response = self.supabase.table(self.TABLE_NAME) \
            .select("*") \
            .limit(limit) \
            .execute()
        Logger.info(f"Listed customers with limit {limit}")
        return response.data

    def is_escalated(self, phone_number: str) -> bool:
        """Check if a customer has escalation_status=True."""
        response = self.supabase.table(self.TABLE_NAME) \
            .select("escalation_status") \
            .eq("phone_number", phone_number) \
            .limit(1) \
            .execute()
        
        if not response.data:
            Logger.warning(f"No escalation status found for customer: {phone_number}")
            return False  # Customer not found, treat as not escalated

        Logger.info(f"Fetched escalation status for customer: {phone_number}")
        return bool(response.data[0].get("escalation_status"))

    def update_escalation_status(self, phone_number: str, status: bool) -> bool:
        """
        Update a customer's escalation_status.
        Returns True if update was successful, False if customer not found.
        """
        response = self.supabase.table(self.TABLE_NAME) \
            .update({"escalation_status": status}) \
            .eq("phone_number", phone_number) \
            .execute()

        return bool(response.data)  # True if something was updated
