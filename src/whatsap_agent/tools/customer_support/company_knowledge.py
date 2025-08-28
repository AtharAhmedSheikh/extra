from agents import function_tool
from supabase import create_client
from openai import OpenAI

from whatsapp_agent.database.base import DataBase
from whatsapp_agent.utils.config import Config



OPENAI_KEY = Config.get("OPENAI_API_KEY")

supabase = DataBase().supabase
client = OpenAI(api_key=OPENAI_KEY)

@function_tool
def search_company_knowledgebase_tool(query: str, top_k: int = 3) -> str:
    """
    Search the company knowledgebase stored in Supabase and return the most relevant answers.

    Args:
        query (str): The natural language query from user.
        top_k (int): Number of top results to return.

    Returns:
        str: Concatenated top documents with similarity scores.
    """
    # Step 1: Get embedding for query
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # Step 2: Call Supabase RPC
    response = supabase.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_threshold": 0.3,
        "match_count": top_k
    }).execute()

    results = response.data or []

    if not results:
        return "No relevant documents found."

    # Step 3: Format answer
    answer = "\n\n".join(
        [f"🔹 {r['content']} (score: {round(r['similarity'], 2)})" for r in results]
    )
    return answer
