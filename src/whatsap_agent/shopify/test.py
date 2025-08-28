from whatsapp_agent.shopify.base import ShopifyBase
from rich import print

def main():

    shopify = ShopifyBase()

    if shopify.test_connection():
        print("✅ Connected to Shopify!")
        
    customer = shopify.find_customer_by_phone("923365312712")
    # print(customer)

    tracking = shopify.track_latest_order_by_phone("923362")
    # print(tracking)

    product = shopify.get_product_by_id("9223480541425")
    # print(product)

    order = shopify.get_order_by_id("6434523152625")
    # print(order)

if __name__ == "__main__":
    main()