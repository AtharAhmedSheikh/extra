from agents.mcp import MCPServerStreamableHttp, create_static_tool_filter
from whatsapp_agent._debug import Logger
from typing import List

from whatsapp_agent.utils.config import Config


async def get_boost_mcp_server(allowed_tool_names: List[str] | None = None):
    SHOPIFY_STORE_URL = Config.get("SHOPIFY_SHOP_DOMAIN")
    def tool_filter(allowed_tool_names: List[str]):
        if allowed_tool_names:
            return create_static_tool_filter(allowed_tool_names)
        return None
    try:
        boost_shopify_mcp = MCPServerStreamableHttp(
            name="Boost MCP Server",
            params={
                "url": f"https://{SHOPIFY_STORE_URL}/api/mcp",
                "terminate_on_close": True,
            },
            cache_tools_list=True,
            tool_filter=tool_filter(allowed_tool_names)
        )
        await boost_shopify_mcp.connect()
        Logger.info("Successfully connected to Boost MCP Server")

        # Test if tools are working
        if not await _test_mcp_tools(boost_shopify_mcp):
            Logger.warning("Problem in MCP tools, but connection is established")

        return boost_shopify_mcp

    except Exception as e:
        Logger.error(f"{__name__}: get_boost_mcp_server -> Failed to connect to MCP server: {e}")
        if boost_shopify_mcp:
            try:
                await boost_shopify_mcp.cleanup()
                Logger.info("MCP server cleaned up after connection failure")
            except Exception as cleanup_error:
                Logger.error(f"{__name__}: get_boost_mcp_server -> Error during cleanup after connection failure: {cleanup_error}")
        raise  # Re-raise the exception to be handled by caller


async def _test_mcp_tools(mcp_server:MCPServerStreamableHttp):
    """Test if MCP is working properly"""
    try:
        tools = await mcp_server.list_tools()
        Logger.info(f"Available MCP tools: {len(tools) if tools else 0}")
        Logger.info(f"Tool Names: {[t.name for t in tools]}")
        if tools:
            return True
        else:
            Logger.warning("No tools available from MCP server")
            return False
    except Exception as e:
        Logger.error(f"{__name__}: _test_mcp_tools -> Error testing MCP: {e}")
        return False