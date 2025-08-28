from agents import Agent, Runner
from whatsapp_agent.agents.customer_greeting_agent.instructions import dynamic_instructions
from whatsapp_agent._debug import Logger
from whatsapp_agent.context.global_context import GlobalContext

class CustomerGreetingAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Customer Greeting Agent",
            instructions=dynamic_instructions,
            model="gpt-4.1-nano"
        )

    async def run(self, input_text: str, global_context: GlobalContext):
        """
        Handles incoming friendly or neutral greeting messages from customers.
        Generates a warm, short, WhatsApp-friendly response.
        """
        response = await self._run_agent(input_text, global_context)
        Logger.info(f"CustomerGreetingAgent response: {response.final_output_as(str)}")
        return response.final_output_as(str)

    async def _run_agent(self, input_text: str, global_context: GlobalContext):
        """
        Processes the greeting and returns a polite, conversational response.
        """
        return await Runner.run(
            starting_agent=self,
            input=input_text,
            context=global_context
        )
