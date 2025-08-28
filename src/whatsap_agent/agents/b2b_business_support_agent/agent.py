from whatsapp_agent._debug import Logger
from whatsapp_agent.agents.b2b_business_support_agent.instructions import dynamic_instructions
from whatsapp_agent.context.global_context import GlobalContext
from agents import Agent, Runner

from whatsapp_agent.tools.customer_support.company_knowledge import search_company_knowledgebase_tool
from whatsapp_agent.tools.customer_support.escalate_to_human import escalate_to_human_support_tool

from whatsapp_agent.tools.quickbook_tools.invoices import (
    check_invoice_status_tool,
    create_invoice_tool,
    get_invoices_by_customer_tool,
    get_last_invoice_by_customer_tool,
    get_unpaid_invoices_by_customer_tool,
    get_due_date_tool,
    get_invoice_tool,
)

class B2BBusinessSupportAgent(Agent):
    def __init__(self, mcp_server):
        self.boost_mcp_server = mcp_server
        super().__init__(
            name="B2BBusinessSupportAgent",
            instructions=dynamic_instructions,
            model="gpt-4.1",
            mcp_servers=[self.boost_mcp_server],
            tools=[
                    search_company_knowledgebase_tool,
                    escalate_to_human_support_tool,
                    check_invoice_status_tool,
                    create_invoice_tool,
                    get_invoices_by_customer_tool,
                    get_last_invoice_by_customer_tool,
                    get_unpaid_invoices_by_customer_tool,
                    get_due_date_tool,
                    get_invoice_tool,
            ]
        )
   
    async def run(self, input_text: str, global_context: GlobalContext):
        # This method would handle the input text and interact with QuickBook services
        response = await self._run_agent(input_text, global_context)
        Logger.info(f"B2B Business Support Agent response: {response.final_output}")
        await self._cleanup()
        return response.final_output_as(str)

    async def _run_agent(self, input_text: str, global_context: GlobalContext):
        # This method would process the input text and return a response
        return await Runner.run(
            starting_agent=self,
            input=input_text,
            context=global_context,
        )

    async def _cleanup(self):
        if self.boost_mcp_server:
            Logger.info("Cleaning up B2B Business Support Agent resources.")
            await self.boost_mcp_server.cleanup()