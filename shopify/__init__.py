"""
Shopify Integration Package

This package provides Shopify API integration using the REST Admin API.

Modules:
- base: Core Shopify API client with REST support
- products: Product-specific operations and inventory management
"""

from .base import ShopifyBase
from .products import ShopifyProducts

__all__ = [
    "ShopifyBase",
    "ShopifyProducts"
]
