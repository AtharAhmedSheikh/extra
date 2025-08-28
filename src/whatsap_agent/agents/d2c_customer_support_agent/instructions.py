from agents import RunContextWrapper, Agent
from whatsapp_agent.context.global_context import GlobalContext
from whatsapp_agent.database.boost_buddy_persona import PersonaDB

BASE_INSTRUCTIONS = """
{persona}

## Context Provided
```
<<<CHAT_HISTORY>>>
{messages}
<<<END_CHAT_HISTORY>>>
```

```
<<<CUSTOMER_CONTEXT>>>
{customer_context}
<<<END_CUSTOMER_CONTEXT>>>
```
"""


async def dynamic_instructions(wrapper: RunContextWrapper[GlobalContext], agent: Agent) -> str:
   db = PersonaDB()
   persona = db.get_persona("d2c_customer_support_agent")
   return BASE_INSTRUCTIONS.format(
      persona=persona,
      messages=wrapper.context.messages.formatted_message,
      customer_context=wrapper.context.customer_context.formatted_context
   )