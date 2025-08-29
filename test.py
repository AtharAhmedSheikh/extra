# from rich import print
# import asyncio
# from whatsapp_agent.bot.whatsapp_bot import WhatsappBot
# from whatsapp_agent.utils.websocket import websocket_manager
# from whatsapp_agent.database.customer import CustomerDataBase
# async def test_escalation():
#     db=CustomerDataBase()
#     db.update_escalation_status("923102137075", False)
#     # await websocket_manager.send_to_dashboard({
#     #     "event": "escalation_triggered",
#     #     "phone_number": "923102137075",
#     #     "chat_history": [{"message": "Hello"}]
#     # })
#     # return {"status": "message sent"}

# asyncio.run(test_escalation())


# # async def main():
# #     bot = WhatsappBot()
# #     user_message = "hi"
# #     await bot.execute_workflow({"text": user_message, "sender": "03092328094"}, test=True)

# # from whatsapp_agent.database.chat_history import ChatHistoryDataBase

# # chat_history_db = ChatHistoryDataBase()

# # data = chat_history_db.get_recent_chat_history_by_phone("923102137075")
# # print(data)

# import asyncio
# from whatsapp_agent.utils.referrals_handler import ReferralHandler
# from whatsapp_agent._debug import Logger, enable_verbose_logging

# enable_verbose_logging()
# referral_handler = ReferralHandler()

# # random message containing referral code in it
# message = """
# Hello, I would like to refer you to our service.
# (Referral code: _ABCD-MAOZTT_)

# """
# async def main():
#     print(await referral_handler.referral_workflow(message ,"923102320751"))

# asyncio.run(main())
# from agents import function_tool, Agent, Runner
# from supabase import create_client
# from openai import OpenAI
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Setup clients
# SUPABASE_URL = os.environ["SUPABASE_URL"]
# SUPABASE_KEY = os.environ["SUPABASE_API_KEY"]
# OPENAI_KEY = os.environ["OPENAI_API_KEY"]

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# client = OpenAI(api_key=OPENAI_KEY)

# @function_tool
# def search_company_knowledgebase_tool(query: str, top_k: int = 3) -> str:
#     """
#     Search the company knowledgebase stored in Supabase and return the most relevant answers.

#     Args:
#         query (str): The natural language query from user.
#         top_k (int): Number of top results to return.

#     Returns:
#         str: Concatenated top documents with similarity scores.
#     """
#     # Step 1: Get embedding for query
#     response = client.embeddings.create(
#         input=query,
#         model="text-embedding-3-small"
#     )
#     query_embedding = response.data[0].embedding
#     # Step 2: Call Supabase RPC
#     response = supabase.rpc("match_documents", {
#         "query_embedding": query_embedding,
#         "match_threshold": 0.2,
#         "match_count": top_k
#     }).execute()

#     results = response.data or []

#     if not results:
#         return "No relevant documents found."

#     # Step 3: Format answer
#     answer = "\n\n".join(
#         [f"🔹 {r['content']} (score: {round(r['similarity'], 2)})" for r in results]
#     )
#     return answer


# agent= Agent(
#     name="Assistant",
#     instructions="You are a helpful assistant that helps users find information from the company knowledgebase.",
#     tools=[
#         search_company_knowledgebase_tool
#     ]
# )

# result = Runner.run_sync(
#     agent,
#     "Which colors are available in Synergy Chair?"
# )

# print(result.final_output)


from whatsapp_agent.agents.d2c_customer_support_agent.agent import D2CCustomerSupportAgent
from whatsapp_agent.mcp.boost_mcp import get_boost_mcp_server
from whatsapp_agent.context.global_context import GlobalContext

async def main():
    boost_mcp_server = await get_boost_mcp_server()
    customer_support_agent = D2CCustomerSupportAgent(mcp_server=boost_mcp_server)
    response = await customer_support_agent.run("Show me the watches", GlobalContext())
    print(response)

import asyncio
asyncio.run(main())