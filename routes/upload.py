from fastapi import UploadFile, Form, APIRouter, HTTPException
from openai import OpenAI
from PyPDF2 import PdfReader
import docx
from typing import List
from pydantic import BaseModel
import re

from whatsapp_agent.database.base import DataBase
from whatsapp_agent.utils.config import Config
from whatsapp_agent._debug import Logger

supabase = DataBase().supabase

def _get_openai_client():
    return OpenAI(api_key=Config.get("OPENAI_API_KEY"))

upload_router = APIRouter(prefix="/upload", tags=["Document Upload"])

class FAQRequest(BaseModel):
    question: str
    answer: str
    category: str = "general"
    keywords: List[str] = []

class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    keywords: List[str]

# --- Helper: Extract text based on file type ---
async def extract_text(file: UploadFile) -> str:
    filename = file.filename.lower()

    # Case 1: TXT
    if filename.endswith(".txt"):
        content = (await file.read()).decode("utf-8", errors="ignore")
        return content

    # Case 2: PDF
    elif filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    # Case 3: DOCX
    elif filename.endswith(".docx"):
        doc = docx.Document(file.file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    # Default: Try as text
    else:
        return (await file.read()).decode("utf-8", errors="ignore")

def chunk_by_sentences(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Chunk text by sentences with overlap for better context preservation"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed max size, save current chunk
        if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            
            # Start new chunk with overlap from previous chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + " " + sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def chunk_by_paragraphs(text: str, max_chunk_size: int = 1500, overlap: int = 150) -> List[str]:
    """Chunk text by paragraphs with semantic awareness"""
    paragraphs = text.split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed max size, save current chunk
        if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_words = words[-overlap//5:] if len(words) > overlap//5 else words
            current_chunk = " ".join(overlap_words) + "\n\n" + paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def chunk_by_headers(text: str, max_chunk_size: int = 2000) -> List[str]:
    """Chunk text by headers and sections for structured documents"""
    # Look for common header patterns
    header_pattern = r'^(#{1,6}\s+.+|[A-Z][^.!?]*:$|\d+\.\s+[A-Z][^.!?]*$)'
    lines = text.split('\n')
    
    chunks = []
    current_chunk = ""
    current_header = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            current_chunk += "\n"
            continue
            
        # Check if this line is a header
        if re.match(header_pattern, line, re.MULTILINE):
            # If we have a current chunk and it's not empty, save it
            if current_chunk.strip() and len(current_chunk) > 50:
                chunks.append(f"{current_header}\n{current_chunk}".strip())
            
            current_header = line
            current_chunk = ""
        else:
            current_chunk += line + "\n"
            
            # If chunk gets too large, split it
            if len(current_chunk) > max_chunk_size:
                chunks.append(f"{current_header}\n{current_chunk}".strip())
                current_chunk = ""
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(f"{current_header}\n{current_chunk}".strip())
    
    return chunks

def intelligent_chunking(text: str, document_type: str = "auto") -> List[str]:
    """Apply intelligent chunking based on document structure"""
    text = text.strip()
    
    if not text:
        return []
    
    # Determine document type if auto
    if document_type == "auto":
        if re.search(r'^#{1,6}\s+', text, re.MULTILINE):
            document_type = "markdown"
        elif re.search(r'^[A-Z][^.!?]*:$', text, re.MULTILINE):
            document_type = "structured"
        elif len(text.split('\n\n')) > 3:
            document_type = "paragraphs"
        else:
            document_type = "sentences"
    
    # Apply appropriate chunking strategy
    if document_type == "structured":
        chunks = chunk_by_headers(text)
    elif document_type == "paragraphs":
        chunks = chunk_by_paragraphs(text)
    else:
        chunks = chunk_by_sentences(text)
    
    # Filter out very small chunks
    chunks = [chunk for chunk in chunks if len(chunk.strip()) > 20]
    
    return chunks

async def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Create embeddings for multiple texts efficiently"""
    try:
        client = _get_openai_client()
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        Logger.error(f"Error creating embeddings: {e}")
        raise

@upload_router.post("/document")
async def upload_document(
    file: UploadFile, 
    title: str = Form(...),
    document_type: str = Form("auto"),
    category: str = Form("general"),
    max_chunk_size: int = Form(1500)
):
    """
    Upload document with intelligent chunking and store in vector_store with metadata in company_knowledgebase.
    """
    try:
        Logger.info(f"Starting document upload: {title}")
        
        # Step 1: Extract text
        content = await extract_text(file)

        if not content.strip():
            raise HTTPException(status_code=400, detail="No readable text extracted from file")

        Logger.info(f"Extracted {len(content)} characters from document")

        # Step 2: Apply intelligent chunking
        chunks = intelligent_chunking(content, document_type)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No valid chunks could be created from the document")
        
        Logger.info(f"Created {len(chunks)} chunks from document")

        # Step 3: Create embeddings for all chunks
        embeddings = await create_embeddings_batch(chunks)

        # Step 4: Store document metadata in company_knowledgebase
        kb_result = supabase.table("company_knowledgebase").insert({
            "title": title,
            "content_type": "document",
            "category": category,
            "filename": file.filename,
            "document_type": document_type,
            "total_chunks": len(chunks),
            "original_content_length": len(content),
            "metadata": {
                "max_chunk_size": max_chunk_size
            }
        }).execute()
        
        kb_id = kb_result.data[0]["id"]
        Logger.info(f"Stored document metadata with ID: {kb_id}")

        # Step 5: Store chunks in vector_store
        vector_records = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_records.append({
                "content": chunk,
                "embedding": embedding,
                "content_type": "document_chunk",
                "reference_id": kb_id,
                "metadata": {
                    "chunk_index": i,
                    "chunk_size": len(chunk)
                }
            })

        # Batch insert all chunks
        vector_result = supabase.table("vector_store").insert(vector_records).execute()
        
        Logger.info(f"Successfully stored {len(vector_records)} chunks in vector_store")

        return {
            "status": "success", 
            "title": title,
            "filename": file.filename,
            "kb_id": kb_id,
            "total_length": len(content),
            "chunks_created": len(chunks),
            "document_type": document_type,
            "vector_ids": [record["id"] for record in vector_result.data]
        }

    except HTTPException:
        raise
    except Exception as e:
        Logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@upload_router.post("/faq", response_model=FAQResponse)
async def create_faq(faq: FAQRequest):
    """
    Create a new FAQ entry and store directly in both company_knowledgebase and vector_store.
    """
    try:
        Logger.info(f"Creating FAQ: {faq.question[:50]}...")
        
        # Step 1: Store FAQ metadata in company_knowledgebase
        kb_result = supabase.table("company_knowledgebase").insert({
            "title": f"FAQ: {faq.question[:100]}",
            "content_type": "faq",
            "category": faq.category,
            "question": faq.question,
            "answer": faq.answer,
            "keywords": faq.keywords,
            "metadata": {}
        }).execute()
        
        kb_id = kb_result.data[0]["id"]
        
        # Step 2: Combine question and answer for embedding
        combined_text = f"Question: {faq.question}\nAnswer: {faq.answer}"
        
        # Step 3: Create embedding
        client = _get_openai_client()
        response = client.embeddings.create(
            input=combined_text,
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding

        # Step 4: Store in vector_store
        vector_result = supabase.table("vector_store").insert({
            "content": combined_text,
            "embedding": embedding,
            "content_type": "faq",
            "reference_id": kb_id,
            "metadata": {
                "category": faq.category,
                "keywords": faq.keywords
            }
        }).execute()

        Logger.info(f"Successfully created FAQ with KB ID: {kb_id}, Vector ID: {vector_result.data[0]['id']}")

        return FAQResponse(
            id=kb_id,
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            keywords=faq.keywords
        )

    except Exception as e:
        Logger.error(f"Error creating FAQ: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create FAQ: {str(e)}")

@upload_router.get("/faqs")
async def get_faqs(category: str = None, limit: int = 50):
    """
    Retrieve stored FAQs from company_knowledgebase.
    """
    try:
        query = supabase.table("company_knowledgebase").select("*").eq("content_type", "faq").eq("is_active", True)
        
        if category:
            query = query.eq("category", category)
        
        result = query.limit(limit).execute()
        
        faqs = []
        for item in result.data:
            faqs.append({
                "id": item["id"],
                "question": item["question"],
                "answer": item["answer"],
                "category": item["category"],
                "keywords": item["keywords"] or []
            })

        return {"faqs": faqs, "total": len(faqs)}

    except Exception as e:
        Logger.error(f"Error retrieving FAQs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve FAQs: {str(e)}")

@upload_router.get("/documents")
async def get_documents(limit: int = 20, offset: int = 0):
    """
    Retrieve uploaded documents metadata from company_knowledgebase.
    """
    try:
        result = supabase.table("company_knowledgebase").select("*").eq("content_type", "document").eq("is_active", True).range(offset, offset + limit - 1).execute()
        
        documents = []
        for item in result.data:
            documents.append({
                "id": item["id"],
                "title": item["title"],
                "filename": item["filename"],
                "category": item["category"],
                "document_type": item["document_type"],
                "total_chunks": item["total_chunks"],
                "original_content_length": item["original_content_length"],
                "created_at": item["created_at"]
            })

        return {"documents": documents, "limit": limit, "offset": offset}

    except Exception as e:
        Logger.error(f"Error retrieving documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")

@upload_router.get("/knowledge-stats")
async def get_knowledge_stats():
    """
    Get statistics about the knowledge base.
    """
    try:
        # Get document stats
        doc_stats = supabase.table("company_knowledgebase").select("content_type", {"count": "exact"}).eq("is_active", True).execute()
        
        # Get vector store stats
        vector_stats = supabase.table("vector_store").select("content_type", {"count": "exact"}).execute()
        
        # Count by content type
        doc_count = 0
        faq_count = 0
        chunk_count = 0
        faq_vector_count = 0
        
        # Process company_knowledgebase stats
        for stat in doc_stats.data:
            if stat["content_type"] == "document":
                doc_count += 1
            elif stat["content_type"] == "faq":
                faq_count += 1
        
        # Process vector_store stats
        for stat in vector_stats.data:
            if stat["content_type"] == "document_chunk":
                chunk_count += 1
            elif stat["content_type"] == "faq":
                faq_vector_count += 1

        return {
            "total_documents": doc_count,
            "total_faqs": faq_count,
            "total_document_chunks": chunk_count,
            "total_faq_vectors": faq_vector_count,
            "total_vectors": chunk_count + faq_vector_count
        }

    except Exception as e:
        Logger.error(f"Error retrieving knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve knowledge stats: {str(e)}")
