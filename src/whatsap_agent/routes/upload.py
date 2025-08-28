from fastapi import UploadFile, Form, APIRouter
from openai import OpenAI
from PyPDF2 import PdfReader
import docx

from whatsapp_agent.database.base import DataBase
from whatsapp_agent.utils.config import Config

OPENAI_KEY = Config.get("OPENAI_API_KEY")

supabase = DataBase().supabase
client = OpenAI(api_key=OPENAI_KEY)

upload_router = APIRouter()

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


@upload_router.post("/upload")
async def upload_document(file: UploadFile, title: str = Form(...)):
    """
    Upload document (txt, pdf, docx), generate embedding, and save to Supabase.
    """
    try:
        # Step 1: Extract text
        content = await extract_text(file)

        if not content.strip():
            return {"status": "error", "message": "No readable text extracted."}

        # Step 2: Create embedding
        response = client.embeddings.create(
            input=content,
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding

        # Step 3: Insert into Supabase
        supabase.table("documents").insert({
            "content": content,
            "embedding": embedding
        }).execute()

        return {"status": "success", "title": title, "length": len(content)}

    except Exception as e:
        return {"status": "error", "message": str(e)}
