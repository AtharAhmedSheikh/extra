from whatsapp_agent.quickbook.base import QuickBookBase
from whatsapp_agent.quickbook.products import QuickBookItem
from whatsapp_agent._debug import Logger
from typing import Optional, Dict, Any, List

class QuickBookInvoice(QuickBookBase):
    def __init__(self):
        super().__init__()

    def _create_invoice(self, customer_id: str, item_list) -> Optional[Dict[str, Any]]:
        """Creates a basic invoice for a specific customer and item."""
        payload = {
            "CustomerRef": {"value": customer_id},
            "Line": [
                {
                    "Amount": item['amount'],
                    "DetailType": "SalesItemLineDetail",
                    "SalesItemLineDetail": {
                        "ItemRef": {"value": item['id'], "name": item['name']},
                        "Qty": item['quantity']
                    }
                } for item in item_list
            ]
        }
        url = self._get_url("invoice")
        return self._request("POST", url, json=payload)

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific invoice by ID."""
        url = self._get_url(f"invoice/{invoice_id}")
        res = self._request("GET", url)
        return res.get("Invoice") if res else None
        
    def get_invoices_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all invoices related to a customer."""
        query = f"SELECT * FROM Invoice WHERE CustomerRef = '{customer_id}'"
        url = self._get_url("query")
        params = {"query": query, "minorversion": self.API_VERSION}
        res = self._request("GET", url, params=params)
        return res.get("QueryResponse", {}).get("Invoice", []) if res else []

    def get_last_invoice_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get the last invoice related to a customer."""
        invoices = self.get_invoices_by_customer(customer_id)
        return invoices[-1] if invoices else None
    
    def check_invoice_status(self, invoice_id: str) -> Optional[str]:
        """Check the status of a specific invoice."""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            Logger.warning(f"[❌] Invoice with ID {invoice_id} not found.")
            return None
        return "Unpaid" if (invoice.get("Balance", 0) > 0) else "Paid"

    def get_unpaid_invoices_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all unpaid invoices related to a customer by fetching all and filtering."""
        query = f"SELECT * FROM Invoice WHERE CustomerRef = '{customer_id}'"
        url = self._get_url("query")
        params = {
            "query": query,
            "minorversion": self.API_VERSION
        }
        res = self._request("GET", url, params=params)
        invoices = res.get("QueryResponse", {}).get("Invoice", []) if res else []
        # Filter unpaid invoices (Balance > 0) in Python
        unpaid_invoices = [inv for inv in invoices if inv.get("Balance", 0) > 0]
        return unpaid_invoices

    def get_due_date(self, invoice_id: str) -> Optional[str]:
        """Get the due date of a specific invoice."""
        invoice = self.get_invoice(invoice_id)
        return invoice.get("DueDate") if invoice else None
       
    def create_invoice(self, customer_id: str, invoice_items):
        qb_items = QuickBookItem()
        item_list = []

        for item in invoice_items:
            item_name = item.name
            quantity = item.quantity

            qb_item = qb_items.get_item_by_name(item_name)

            if not qb_item:
                Logger.warning(f"Item not found in QuickBooks: {item_name}")
                continue 
            
            if qb_item.get('QtyOnHand') and (int(qb_item['QtyOnHand']) < int(quantity)):
                return f"Only {quantity} left in stock."

            unit_price = qb_item["UnitPrice"]
            amount = unit_price

            item_data = {
                "id": qb_item["Id"],
                "name": qb_item["Name"],
                "quantity": quantity,
                "amount": amount,
            }

            item_list.append(item_data)

        if not item_list:
            Logger.warning("No valid items found to create invoice.")
            return None

        return self._create_invoice(customer_id, item_list)


