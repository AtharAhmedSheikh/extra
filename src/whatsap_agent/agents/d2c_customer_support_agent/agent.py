from whatsapp_agent._debug import Logger
from whatsapp_agent.agents.d2c_customer_support_agent.instructions import dynamic_instructions
from whatsapp_agent.context.global_context import GlobalContext
from agents import Agent, Runner

# Customer support tools
from whatsapp_agent.tools.customer_support.company_knowledge import search_company_knowledgebase_tool
from whatsapp_agent.tools.customer_support.escalate_to_human import escalate_to_human_support_tool
from whatsapp_agent.tools.customer_support.order_tracking import track_customer_order_tool

class D2CCustomerSupportAgent(Agent):
    def __init__(self, mcp_server): 
        self.boost_mcp_server = mcp_server
        super().__init__(
            name="D2C Customer Support Agent",
            instructions=dynamic_instructions,
            model="gpt-4.1",
            mcp_servers=[self.boost_mcp_server],
            tools=[
                track_customer_order_tool,
                escalate_to_human_support_tool,
                search_company_knowledgebase_tool,
            ]
        )

    async def run(self, input_text: str, global_context: GlobalContext):
        response = await self._run_agent(input_text, global_context)
        Logger.info(f"D2C Customer Support Agent response: {response.final_output_as(str)}")
        await self._cleanup()
        return response.final_output_as(str)

    async def _run_agent(self, input_text: str, global_context: GlobalContext):
        return await Runner.run(
            starting_agent=self,
            input=input_text,
            context=global_context,
        )

    async def _cleanup(self):
        if self.boost_mcp_server:
            Logger.info("Cleaning up D2C Customer Support Agent resources (MCP).")
            await self.boost_mcp_server.cleanup()

