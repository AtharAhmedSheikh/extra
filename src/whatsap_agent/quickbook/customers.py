from whatsapp_agent.quickbook.base import QuickBookBase
from whatsapp_agent._debug import Logger
from typing import Optional, Dict, Any
import re

from whatsapp_agent.schema.customer_schema import CustomerSchema

class QuickBookCustomer(QuickBookBase):
    def __init__(self):
        super().__init__()

    def _run_query(self, query: str) -> Optional[Dict[str, Any]]:
        url = self._get_url("query")
        params = {"query": query, "minorversion": self.API_VERSION}
        return self._request("GET", url, params=params)

    def _normalize_phone(self, phone: str) -> str:
        return re.sub(r"[^\d]", "", phone)[-10:]

    def fetch_customers_paginated(self, target_phone: str, max_pages: int = 10) -> Optional[Dict[str, Any]]:
        """Fetch paginated customers and match phone."""
        start = 1
        limit = 100
        normalized_target = self._normalize_phone(target_phone)

        for _ in range(max_pages):
            query = f"SELECT * FROM Customer STARTPOSITION {start} MAXRESULTS {limit}"
            data = self._run_query(query)
            customers = data.get("QueryResponse", {}).get("Customer", []) if data else []

            for customer in customers:
                phones = [
                    self._normalize_phone(customer.get("PrimaryPhone", {}).get("FreeFormNumber", "")),
                    self._normalize_phone(customer.get("Mobile", {}).get("FreeFormNumber", ""))
                ]
                if normalized_target in phones:
                    Logger.debug(f"Fetched customer by phone in quickbook: {customer}")
                    return customer

            if len(customers) < limit:
                break  # No more pages
            start += limit
        Logger.warning(f"No customer found by phone in quickbook: {target_phone}")
        return None

    def fetch_customer_type_by_id(self, customer_id: str) -> Optional[str]:
        url = self._get_url(f"customer/{customer_id}?include=enhancedAllCustomFields")
        params = {"minorversion": self.API_VERSION}
        data = self._request("GET", url, params=params)

        if not data or "Customer" not in data:
            Logger.warning(f"No customer found by ID in quickbook: {customer_id}")
            return None

        custom_fields = data["Customer"].get("CustomField", [])
        type_field = next((cf for cf in custom_fields if cf.get("DefinitionId") == "1000000001"), None)

        if type_field and type_field.get("StringValue"):
            index = int(type_field["StringValue"])
            Logger.info(f"Fetched customer type by ID in quickbook: {customer_id}")
            return ["B2B", "D2C", "walking"][index - 1]
        
        return "D2C"
    
    def fetch_customer_by_phone_safe(self, target_phone: str, max_results: int = 50) -> Optional[Dict[str, Any]]:
        """Fetch customer by matching phone number (PrimaryPhone or Mobile)"""
        normalized_target = self._normalize_phone(target_phone)
        query = (
            "SELECT Active, BalanceWithJobs, Id, SyncToken, FullyQualifiedName, CompanyName, "
            "PrimaryPhone, PrimaryEmailAddr FROM Customer MAXRESULTS {max_results}"
        ).format(max_results=max_results)
        data = self._run_query(query)

        customers = data.get("QueryResponse", {}).get("Customer", []) if data else []

        for customer in customers:
            phones = [
                self._normalize_phone(customer.get("PrimaryPhone", {}).get("FreeFormNumber", "")),
                self._normalize_phone(customer.get("Mobile", {}).get("FreeFormNumber", ""))
            ]
            if normalized_target in phones:
                Logger.debug(f"Fetched customer by phone in quickbook: {customer}")
                return customer

        return None
    
    def get_customer_with_type_by_phone(
        self, phone: str, customer_id: str | None = None
    ) -> Optional[CustomerSchema]:
        """
        Retrieve a full customer object by phone (or ID) and include the inferred customer type.
        """
        # Fetch customer if only phone is provided
        customer = None
        if not customer_id:
            customer = self.fetch_customer_by_phone_safe(phone)
            if not customer:
                Logger.warning(f"No customer found by phone in quickbook: {phone}")
                return None
            customer_id = customer.get("Id")

        # Add inferred type
        customer_type = self.fetch_customer_type_by_id(customer_id)
        customer["CustomerType"] = customer_type
        customer_schema = self._convert_customer_to_schema(customer)
        Logger.info(f"Fetched customer with type by phone in quickbook: {phone}")
        return customer_schema

    def _convert_customer_to_schema(self, customer: Dict[str, Any]) -> CustomerSchema:
        """
        Convert a customer dictionary to a CustomerSchema instance.
        """
        return CustomerSchema(
            customer_name=customer.get("FullyQualifiedName"),
            email=customer.get("PrimaryEmailAddr", {}).get("Address"),
            customer_quickbook_id=customer.get("Id"),
            customer_type=customer.get("CustomerType"),
            company_name=customer.get("CompanyName") if customer.get("CompanyName") else None,
            is_active=customer.get("Active", False),
            phone_number=customer.get("PrimaryPhone", {}).get("FreeFormNumber", "")[-10:],
        )


