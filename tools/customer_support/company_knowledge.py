# from agents import function_tool
# from supabase import create_client
# from openai import OpenAI

# from whatsapp_agent.database.base import DataBase
# from whatsapp_agent.utils.config import Config



# OPENAI_KEY = Config.get("OPENAI_API_KEY")

# supabase = DataBase().supabase
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
#         "match_threshold": 0.3,
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



from agents import function_tool
from openai import OpenAI
from typing import Optional

from whatsapp_agent.database.base import DataBase
from whatsapp_agent.utils.config import Config
from whatsapp_agent._debug import Logger

supabase = DataBase().supabase

def _get_openai_client():
    return OpenAI(api_key=Config.get("OPENAI_API_KEY"))

@function_tool
def search_company_knowledgebase_tool(
    query: str, 
    top_k: int = 5, 
    content_type_filter: Optional[str] = None,
    match_threshold: float = 0.3
) -> str:
    """
    Search the unified company knowledgebase (documents and FAQs) using semantic similarity.

    Args:
        query (str): The natural language query from user.
        top_k (int): Number of top results to return (default: 5).
        content_type_filter (str, optional): Filter by content type ('document_chunk' or 'faq').
        match_threshold (float): Minimum similarity threshold (default: 0.3).

    Returns:
        str: Formatted search results with similarity scores and metadata.
    """
    try:
        Logger.info(f"Searching knowledgebase for: '{query}' with filter: {content_type_filter}")
        
        # Step 1: Get embedding for query
        client = _get_openai_client()
        response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding

        # Step 2: Search vectors using the new function
        search_result = supabase.rpc("match_vectors", {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "match_threshold": match_threshold,
            "content_type_filter": content_type_filter
        }).execute()

        results = search_result.data or []

        if not results:
            return "No relevant documents found in the company knowledgebase."

        # Step 3: Get additional metadata for results with references
        enriched_results = []
        reference_ids = [r['reference_id'] for r in results if r['reference_id']]
        
        if reference_ids:
            # Fetch metadata from company_knowledgebase
            kb_result = supabase.table("company_knowledgebase").select("id, title, category, question, answer").in_("id", reference_ids).execute()
            kb_data = {item['id']: item for item in kb_result.data}
            
            for result in results:
                enriched_result = result.copy()
                if result['reference_id'] and result['reference_id'] in kb_data:
                    kb_info = kb_data[result['reference_id']]
                    enriched_result['title'] = kb_info.get('title', 'N/A')
                    enriched_result['category'] = kb_info.get('category', 'general')
                    
                    # For FAQs, include structured question/answer
                    if result['content_type'] == 'faq':
                        enriched_result['question'] = kb_info.get('question', '')
                        enriched_result['answer'] = kb_info.get('answer', '')
                
                enriched_results.append(enriched_result)
        else:
            enriched_results = results

        # Step 4: Format response
        formatted_results = []
        for i, result in enumerate(enriched_results, 1):
            content_type = result['content_type']
            similarity = round(result['similarity'], 3)
            category = result.get('category', 'general')
            
            if content_type == 'faq':
                # Format FAQ results
                question = result.get('question', 'N/A')
                answer = result.get('answer', result['content'])
                formatted_results.append(
                    f"🔹 **FAQ #{i}** (Category: {category}, Score: {similarity})\n"
                    f"**Q:** {question}\n"
                    f"**A:** {answer}"
                )
            else:
                # Format document chunk results
                title = result.get('title', 'Document')
                content = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
                formatted_results.append(
                    f"🔹 **Document #{i}:** {title} (Category: {category}, Score: {similarity})\n"
                    f"{content}"
                )

        Logger.info(f"Found {len(results)} relevant results")
        return "\n\n".join(formatted_results)

    except Exception as e:
        Logger.error(f"Error searching knowledgebase: {e}")
        return f"Error occurred while searching the knowledgebase: {str(e)}"