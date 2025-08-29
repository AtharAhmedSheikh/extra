import os
from typing import Dict, Any, Optional, List
from whatsapp_agent._debug import Logger
from .base import ShopifyBase

class ShopifyProducts(ShopifyBase):
    """
    Shopify Products API client using REST Admin API.
    Handles product-related operations.
    """
    
    def get_product_inventory(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get inventory information for a specific product.
        """
        try:
            endpoint = f"/products/{product_id}.json"
            data = self._make_request("GET", endpoint)
            product = data.get("product")
            
            if not product:
                return None
                
            # Get inventory levels for all variants
            inventory_data = []
            for variant in product.get("variants", []):
                variant_id = variant.get("id")
                if variant_id:
                    inventory_levels = self.get_variant_inventory_levels(variant_id)
                    inventory_data.append({
                        "variant_id": variant_id,
                        "variant_title": variant.get("title"),
                        "sku": variant.get("sku"),
                        "inventory_quantity": variant.get("inventory_quantity", 0),
                        "inventory_levels": inventory_levels
                    })
            
            return {
                "product_id": product_id,
                "product_title": product.get("title"),
                "variants": inventory_data
            }
            
        except Exception as e:
            Logger.error(f"❌ Error getting product inventory for {product_id}: {e}")
            return None
    
    def get_variant_inventory_levels(self, variant_id: str) -> List[Dict[str, Any]]:
        """
        Get inventory levels for a specific variant across all locations.
        """
        try:
            endpoint = f"/inventory_levels.json?inventory_item_ids={variant_id}"
            data = self._make_request("GET", endpoint)
            return data.get("inventory_levels", [])
        except Exception as e:
            Logger.error(f"❌ Error getting inventory levels for variant {variant_id}: {e}")
            return []
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Get products with low stock (below threshold).
        """
        try:
            endpoint = "/products.json?limit=250"
            data = self._make_request("GET", endpoint)
            products = data.get("products", [])
            
            low_stock_products = []
            for product in products:
                for variant in product.get("variants", []):
                    inventory_quantity = variant.get("inventory_quantity", 0)
                    if inventory_quantity <= threshold and inventory_quantity > 0:
                        low_stock_products.append({
                            "product_id": product.get("id"),
                            "product_title": product.get("title"),
                            "variant_id": variant.get("id"),
                            "variant_title": variant.get("title"),
                            "sku": variant.get("sku"),
                            "inventory_quantity": inventory_quantity,
                            "threshold": threshold
                        })
            
            return low_stock_products
            
        except Exception as e:
            Logger.error(f"❌ Error getting low stock products: {e}")
            return []
    
    def get_out_of_stock_products(self) -> List[Dict[str, Any]]:
        """
        Get products that are out of stock.
        """
        try:
            endpoint = "/products.json?limit=250"
            data = self._make_request("GET", endpoint)
            products = data.get("products", [])
            
            out_of_stock_products = []
            for product in products:
                for variant in product.get("variants", []):
                    inventory_quantity = variant.get("inventory_quantity", 0)
                    if inventory_quantity <= 0:
                        out_of_stock_products.append({
                            "product_id": product.get("id"),
                            "product_title": product.get("title"),
                            "variant_id": variant.get("id"),
                            "variant_title": variant.get("title"),
                            "sku": variant.get("sku"),
                            "inventory_quantity": inventory_quantity
                        })
            
            return out_of_stock_products
            
        except Exception as e:
            Logger.error(f"❌ Error getting out of stock products: {e}")
            return []
    
    def check_product_availability(self, product_id: str, variant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check availability of a product or specific variant.
        """
        try:
            endpoint = f"/products/{product_id}.json"
            data = self._make_request("GET", endpoint)
            product = data.get("product")
            
            if not product:
                return {"available": False, "error": "Product not found"}
            
            if variant_id:
                # Check specific variant
                for variant in product.get("variants", []):
                    if str(variant.get("id")) == str(variant_id):
                        inventory_quantity = variant.get("inventory_quantity", 0)
                        return {
                            "available": inventory_quantity > 0,
                            "product_id": product_id,
                            "variant_id": variant_id,
                            "inventory_quantity": inventory_quantity,
                            "variant_title": variant.get("title")
                        }
                return {"available": False, "error": "Variant not found"}
            else:
                # Check overall product availability
                total_inventory = sum(variant.get("inventory_quantity", 0) for variant in product.get("variants", []))
                return {
                    "available": total_inventory > 0,
                    "product_id": product_id,
                    "total_inventory": total_inventory,
                    "product_title": product.get("title")
                }
                
        except Exception as e:
            Logger.error(f"❌ Error checking product availability for {product_id}: {e}")
            return {"available": False, "error": str(e)}
    
    def get_product_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Get product by its handle (URL slug).
        """
        try:
            endpoint = f"/products.json?handle={handle}"
            data = self._make_request("GET", endpoint)
            products = data.get("products", [])
            return products[0] if products else None
        except Exception as e:
            Logger.error(f"❌ Error getting product by handle {handle}: {e}")
            return None
    
    def search_products(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search products by query string.
        """
        try:
            endpoint = f"/products/search.json?query={query}&limit={limit}"
            data = self._make_request("GET", endpoint)
            return data.get("products", [])
        except Exception as e:
            Logger.error(f"❌ Error searching products with query '{query}': {e}")
            return []
    
    def get_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Get all variants for a specific product.
        """
        try:
            endpoint = f"/products/{product_id}/variants.json"
            data = self._make_request("GET", endpoint)
            return data.get("variants", [])
        except Exception as e:
            Logger.error(f"❌ Error getting variants for product {product_id}: {e}")
            return []
    
    def get_inventory_count(self, location_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get inventory count across all products or for a specific location.
        """
        try:
            if location_id:
                endpoint = f"/inventory_levels.json?location_ids={location_id}"
            else:
                endpoint = "/inventory_levels.json"
            
            data = self._make_request("GET", endpoint)
            inventory_levels = data.get("inventory_levels", [])
            
            total_items = sum(level.get("available", 0) for level in inventory_levels)
            total_locations = len(set(level.get("location_id") for level in inventory_levels))
            
            return {
                "total_items": total_items,
                "total_locations": total_locations,
                "inventory_levels": inventory_levels
            }
            
        except Exception as e:
            Logger.error(f"❌ Error getting inventory count: {e}")
            return {"total_items": 0, "total_locations": 0, "inventory_levels": []}
