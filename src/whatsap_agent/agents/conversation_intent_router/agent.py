from agents import Agent, Runner, ModelBehaviorError
from whatsapp_agent.agents.conversation_intent_router.instructions import dynamic_instructions
from whatsapp_agent.agents.conversation_intent_router.output_type import SentimentAnalysisResult
from whatsapp_agent._debug import Logger
from whatsapp_agent.context.global_context import GlobalContext

class ConversationIntentRouter(Agent):
    def __init__(self):
        super().__init__(
            name="ConversationIntentRouter",
            instructions=dynamic_instructions,
            model="gpt-4o",
            output_type=SentimentAnalysisResult
        )

    async def run(self, input_text: str, global_context: GlobalContext):
        """Handle the input text, decide routing, and return the next agent name."""
        response = await self._run_agent(input_text, global_context)
        Logger.debug(f"Conversation Intent Router response: {response.final_output}")
        try:
            sentiment = response.final_output_as(SentimentAnalysisResult)
            return sentiment
        except Exception as e:
            Logger.error(f"{__name__}: {self.run.__name__} -> Error processing response in Conversation Intent Router: {e}")
            raise ModelBehaviorError(f"Got unexpected response format: {e}")
            

    async def _run_agent(self, input_text: str, global_context: GlobalContext):
        """Process the input text and return routing decision."""
        return await Runner.run(
            starting_agent=self,
            input=input_text,
            context=global_context
        )

