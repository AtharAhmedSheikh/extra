import requests
from typing import Dict, Any, Optional, List
from whatsapp_agent._debug import Logger

from whatsapp_agent.utils.config import Config


class ShopifyBase:
    """
    Base class for Shopify API interactions using the REST Admin API.
    Provides simple REST endpoints for common operations.
    """
    
    def __init__(self):
        self.shop_domain = Config.get("SHOPIFY_SHOP_DOMAIN")
        self.access_token = Config.get("SHOPIFY_ACCESS_TOKEN")
        self.api_version = Config.get("SHOPIFY_API_VERSION", "2025-01")
        
        if not self.shop_domain or not self.access_token:
            raise ValueError("Shopify credentials not configured. Set SHOPIFY_SHOP_DOMAIN and SHOPIFY_ACCESS_TOKEN")
        
        # REST Admin API base URL
        self.base_url = f"https://{self.shop_domain}/admin/api/{self.api_version}"
        
        # Headers for all requests
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make a request to the Shopify REST API.
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            Logger.debug(f"Making {method} request to: {url}")
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204:  # No content
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                Logger.error(f"❌ Shopify REST endpoint not found. Check API version {self.api_version} and shop domain {self.shop_domain}")
                Logger.error(f"❌ Supported API versions: 2024-10, 2025-01, 2025-04, unstable")
                raise Exception(f"Shopify REST endpoint not found. API version {self.api_version} may not exist or shop domain {self.shop_domain} is incorrect.")
            Logger.error(f"❌ Shopify REST HTTP error: {e}")
            raise Exception(f"Shopify REST HTTP error: {str(e)}")
        except requests.exceptions.RequestException as e:
            Logger.error(f"❌ Shopify REST request failed: {e}")
            raise Exception(f"Shopify REST request failed: {str(e)}")
        except ValueError as e:
            Logger.error(f"❌ Invalid JSON response from Shopify REST API: {e}")
            raise Exception(f"Invalid JSON response from Shopify REST API: {str(e)}")
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get product information by ID using REST API.
        """
        try:
            endpoint = f"/products/{product_id}.json"
            data = self._make_request("GET", endpoint)
            return data.get("product")
        except Exception as e:
            Logger.error(f"❌ Error getting product {product_id}: {e}")
            return None
    
    def get_products_by_ids(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple products by IDs using REST API.
        """
        if not product_ids:
            return []
        
        products: List[Dict[str, Any]] = []
        for pid in product_ids:
            product = self.get_product_by_id(pid)
            if product:
                products.append(product)
        return products
    
    def get_shop_info(self) -> Optional[Dict[str, Any]]:
        """
        Get basic shop information via REST API.
        """
        try:
            endpoint = "/shop.json"
            data = self._make_request("GET", endpoint)
            return data.get("shop")
        except Exception as e:
            Logger.error(f"❌ Error getting shop info: {e}")
            return None
    
    def find_customer_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Find a Shopify customer by phone using REST API.
        Returns customer details if found.
        """
        try:
            # Search for customers by phone number
            endpoint = f"/customers/search.json?query=phone:{phone_number}"
            data = self._make_request("GET", endpoint)
            customers = data.get("customers", [])
            
            if customers:
                customer = customers[0]
                Logger.info(f"✅ Found Shopify customer by phone: {phone_number}")
                return {
                    "id": customer.get("id"),
                    "displayName": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                    "defaultEmailAddress": {"email": customer.get("email")},
                    "defaultPhoneNumber": {"phoneNumber": customer.get("phone")},
                    "defaultAddress": {
                        "address1": customer.get("default_address", {}).get("address1"),
                        "city": customer.get("default_address", {}).get("city"),
                        "province": customer.get("default_address", {}).get("province"),
                        "country": customer.get("default_address", {}).get("country"),
                        "zip": customer.get("default_address", {}).get("zip")
                    },
                    "totalSpent": customer.get("total_spent", 0)
                }
            
            Logger.info(f"ℹ️ No Shopify customer found for phone: {phone_number}")
            return None
            
        except Exception as e:
            Logger.error(f"❌ Error finding customer by phone in Shopify: {e}")
            return None
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order information by ID using REST API.
        """
        try:
            endpoint = f"/orders/{order_id}.json"
            data = self._make_request("GET", endpoint)
            return data.get("order")
        except Exception as e:
            Logger.error(f"❌ Error getting order {order_id}: {e}")
            return None
    
    def get_order_fulfillments(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get fulfillments for an order using REST API.
        """
        try:
            endpoint = f"/orders/{order_id}/fulfillments.json"
            data = self._make_request("GET", endpoint)
            return data.get("fulfillments", [])
        except Exception as e:
            Logger.error(f"❌ Error getting fulfillments for order {order_id}: {e}")
            return []
        
    def get_customer_orders(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get orders for a customer using REST API.
        """
        try:
            endpoint = f"/customers/{customer_id}/orders.json?limit={limit}&status=any"
            data = self._make_request("GET", endpoint)
            return data.get("orders", [])
        except Exception as e:
            Logger.error(f"❌ Error getting orders for customer {customer_id}: {e}")
            return []
    
    def track_latest_order_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest order for a customer by phone number.
        Returns order details if found.
        """
        try:
            # Find customer by phone
            customer = self.find_customer_by_phone(phone_number)
            if not customer:
                Logger.info(f"ℹ️ No customer found for phone number: {phone_number}")
                return None

            customer_id = customer.get("id")
            if not customer_id:
                Logger.error(f"❌ Customer found but no ID available for phone number: {phone_number}")
                return None

            # Get customer's latest order
            orders = self.get_customer_orders(customer_id, limit=1)
            if not orders:
                Logger.info(f"ℹ️ No orders found for customer with phone number: {phone_number}")
                return None

            latest_order = orders[0]
            Logger.info(f"✅ Found latest order for customer {phone_number}: {latest_order.get('name')}")
            return latest_order
            
        except Exception as e:
            Logger.error(f"❌ Error tracking latest order for {phone_number}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the Shopify API connection using REST API.
        """
        try:
            shop_info = self.get_shop_info()
            if shop_info:
                Logger.info(f"✅ Shopify connection successful: {shop_info.get('name')}")
                return True
            return False
        except Exception as e:
            Logger.error(f"❌ Shopify connection test failed: {e}")
            return False
    
    def close(self):
        """Close the requests session."""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
