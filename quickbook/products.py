from whatsapp_agent.quickbook.base import QuickBookBase
from typing import Optional, Dict, Any, List

class QuickBookItem(QuickBookBase):
    def __init__(self):
        super().__init__()

    def _run_query(self, query: str) -> Optional[Dict[str, Any]]:
        url = self._get_url("query")
        params = {"query": query, "minorversion": self.API_VERSION}
        return self._request("GET", url, params=params)

    def fetch_all_items(self, limit=50) -> List[Dict[str, Any]]:
        """Get all items from QBO (up to `limit`)"""
        query = f"SELECT * FROM Item MAXRESULTS {limit}"
        data = self._run_query(query)
        return data.get("QueryResponse", {}).get("Item", []) if data else []

    def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch specific fields of item by its name"""
        query = f"""
            SELECT Name, Sku, UnitPrice, QtyOnHand, Type, Id 
            FROM Item 
            WHERE Name = '{name}'
        """
        data = self._run_query(query)
        items = data.get("QueryResponse", {}).get("Item", []) if data else []
        return items[0] if items else None

    def search_item_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Search item by SKU"""
        query = f"SELECT * FROM Item WHERE Sku = '{sku}'"
        data = self._run_query(query)
        items = data.get("QueryResponse", {}).get("Item", []) if data else []
        return items[0] if items else None
