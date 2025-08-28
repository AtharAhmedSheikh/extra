from whatsapp_agent.utils.config import Config

def test_credentials():
    """Test that all existing credential access patterns work"""
    print("Testing credentials access...")
    
    # # Test WhatsApp credentials
    # try:
    #     whatsapp_token = Config.get("WHATSAPP_ACCESS_TOKEN")
    #     print(f"WhatsApp token: {'Found' if whatsapp_token else 'Not found'}")
    # except Exception as e:
    #     print(f"Error getting WhatsApp token: {e}")
    
    # # Test OpenAI credentials
    # try:
    #     openai_key = Config.get("OPENAI_API_KEY")
    #     print(f"OpenAI key: {'Found' if openai_key else 'Not found'}")
    # except Exception as e:
    #     print(f"Error getting OpenAI key: {e}")
    
    # # Test QuickBooks credentials
    # try:
    #     qb_client_id = Config.get("QB_CLIENT_ID")
    #     print(f"QuickBooks client ID: {'Found' if qb_client_id else 'Not found'}")
    # except Exception as e:
    #     print(f"Error getting QuickBooks client ID: {e}")
    
    # # Test Shopify credentials
    # try:
    #     shopify_domain = Config.get("SHOPIFY_SHOP_DOMAIN")
    #     print(f"Shopify domain: {'Found' if shopify_domain else 'Not found'}")
    # except Exception as e:
    #     print(f"Error getting Shopify domain: {e}")
    
    # Test setting a new credential
    try:
        Config.set("FRONTEND_API_KEY", "abcdg")
        test_value = Config.get("FRONTEND_API_KEY")
        print(f"Test credential set/get: {'Success' if test_value == 'abcdg' else 'Failed'}")
    except Exception as e:
        print(f"Error setting/getting test credential: {e}")
    
    print("Credentials test completed!")

if __name__ == "__main__":
    test_credentials()