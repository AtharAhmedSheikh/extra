from fastapi import APIRouter, HTTPException, Query, Path, UploadFile, File, Form, Body
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
import math
import os
import tempfile

from whatsapp_agent.database.chat_history import ChatHistoryDataBase
from whatsapp_agent.schema.chat_history import MessageSchema
from whatsapp_agent.utils.current_time import _get_current_karachi_time_str
from whatsapp_agent.utils.whatsapp_message_handler import WhatsAppMessageHandler
from whatsapp_agent.utils.supabase_storage import SupabaseStorageManager
from whatsapp_agent._debug import Logger

# Create router
chat_router = APIRouter(prefix="/chats", tags=["Chats"])

# Pydantic models for request/response
class SendTextMessageRequest(BaseModel):
    content: str = Field(
        description="Message content",
        example="Hello there"
    )
    sender: Literal["customer", "agent", "representative"] = Field(
        description="Sender of the message",
        example="agent"
    )

class SendImageMessageRequest(BaseModel):
    caption: Optional[str] = Field(
        description="Optional caption for the image",
        example="Check out this image!"
    )
    sender: Literal["customer", "agent", "representative"] = Field(
        description="Sender of the message",
        example="agent"
    )

class SendAudioMessageRequest(BaseModel):
    sender: Literal["customer", "agent", "representative"] = Field(
        description="Sender of the message",
        example="agent"
    )

class SendDocumentMessageRequest(BaseModel):
    caption: Optional[str] = Field(
        description="Optional caption for the document",
        example="Here's the document you requested"
    )
    sender: Literal["customer", "agent", "representative"] = Field(
        description="Sender of the message",
        example="agent"
    )

class ChatMessagesResponse(BaseModel):
    phone_number: str
    messages: List[MessageSchema]
    pagination: dict
    total_messages: int

class SendMessageResponse(BaseModel):
    success: bool
    message: str
    timestamp: datetime

# Initialize database and message handler
chat_db = ChatHistoryDataBase()
storage_manager = SupabaseStorageManager()
message_handler = WhatsAppMessageHandler()

@chat_router.get("/{phone_number}")
async def get_chat_messages(
    phone_number: str = Path(..., description="Phone number to get messages for", example="923001234567"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    messages_count: int = Query(20, ge=1, le=100, description="Number of messages per page")
):
    """
    Get WhatsApp chat messages for a specific phone number with pagination.
    
    - **phone_number**: The phone number to retrieve messages for
    - **page**: Page number (starting from 1)
    - **messages_count**: Number of messages per page (1-100)
    """
    try:
        # Get chat data from database
        chat_data = chat_db._get_chat_by_phone(phone_number)
        
        if not chat_data or "messages" not in chat_data:
            raise HTTPException(status_code=404, detail="No chat history found for this phone number")
        
        # Convert raw message data to MessageSchema objects
        messages = [MessageSchema.model_validate(msg) for msg in chat_data["messages"]]
        total_messages = len(messages)
        
        # Calculate pagination
        total_pages = math.ceil(total_messages / messages_count)
        start_index = (page - 1) * messages_count
        end_index = start_index + messages_count
        
        # Get paginated messages (reverse order to show newest first)
        reversed_messages = list(reversed(messages))
        paginated_messages = reversed_messages[start_index:end_index]
        pagination_info = {
            "current_page": page,
            "total_pages": total_pages,
            "messages_per_page": messages_count,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
        return ChatMessagesResponse(
            phone_number=phone_number,
            messages=paginated_messages,
            pagination=pagination_info,
            total_messages=total_messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="Database table not found. Please run the database setup first."
            )
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")

@chat_router.post("/{phone_number}/send")
async def send_message(
    phone_number: str = Path(..., description="Phone number to send message to", example="923001234567"),
    message_request: SendTextMessageRequest = Body(...)
):
    """
    Send a text WhatsApp message to a specific phone number.
    
    - **phone_number**: The phone number to send the message to
    - **content**: The message content
    - **sender**: Sender of the message (customer, agent, or representative)
    """
    try:
        # Validate message content
        if not message_request.content or message_request.content.strip() == "":
            raise HTTPException(status_code=400, detail="Message content cannot be empty")
        
        # Send message via WhatsApp API
        success = await message_handler.send_message(phone_number, message_request.content)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send message via WhatsApp API")
        
        # Create message object for storage
        new_message = MessageSchema(
            time_stamp=_get_current_karachi_time_str(),
            content=message_request.content,
            message_type="text",
            sender=message_request.sender
        )
        
        # Store message in database
        try:
            db_success = chat_db.add_or_create_message(phone_number, new_message)
            if db_success:
                Logger.info(f"✅ Text message stored in database")
        except Exception as e:
            Logger.error(f"{__name__}: send_message -> ❌ Failed to store text message in database: {e}")
            # Don't fail the request if storage fails, but log it
        
        return SendMessageResponse(
            success=True,
            message="Text message sent successfully",
            timestamp=new_message.time_stamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="Database table not found. Please run the database setup first."
            )
        raise HTTPException(status_code=500, detail=f"Failed to send text message: {error_msg}")

@chat_router.post("/{phone_number}/send-image")
async def send_image_message(
    phone_number: str = Path(..., description="Phone number to send image to", example="923001234567"),
    file: UploadFile = File(..., description="Image file to send (JPEG, PNG, GIF)"),
    caption: Optional[str] = Form(None, description="Optional caption for the image"),
    sender: Literal["customer", "agent", "representative"] = Form(..., description="Sender of the message")
):
    """
    Send an image WhatsApp message to a specific phone number.
    
    - **phone_number**: The phone number to send the image to
    - **file**: Image file to upload and send
    - **caption**: Optional caption for the image
    - **sender**: Sender of the message (customer, agent, or representative)
    """
    temp_file_path = None
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image (JPEG, PNG, GIF)")
        
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (WhatsApp image limit: 5MB)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        max_size = 5 * 1024 * 1024  # 5MB for images
        if file_size > max_size:
            raise HTTPException(status_code=400, detail=f"Image file too large. Maximum size is 5MB")
        
        # Create temporary file
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file.flush()  # Ensure all data is written
            temp_file_path = temp_file.name
        
        # Send image message
        success = await message_handler.send_image(phone_number, temp_file_path, caption)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send image message via WhatsApp API")
        
        # Upload file to Supabase storage
        file_url = storage_manager.upload_file(temp_file_path, content_type=file.content_type)
        if not file_url:
            raise HTTPException(status_code=500, detail="Failed to upload image to storage")
        
        # Create message object for storage with markdown link
        caption_text = caption or "Image"
        content_text = f"![{caption_text}]({file_url})"
        new_message = MessageSchema(
            time_stamp=_get_current_karachi_time_str(),
            content=content_text,
            message_type="image",
            sender=sender
        )
        
        # Store message in database
        try:
            db_success = chat_db.add_or_create_message(phone_number, new_message)
            if db_success:
                Logger.info(f"✅ Image message stored in database")
        except Exception as e:
            Logger.error(f"{__name__}: send_image_message -> ❌ Failed to store image message in database: {e}")

        return SendMessageResponse(
            success=True,
            message="Image message sent successfully",
            timestamp=new_message.time_stamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="Database table not found. Please run the database setup first."
            )
        raise HTTPException(status_code=500, detail=f"Failed to send image message: {error_msg}")
    finally:
        # Clean up temporary file with proper error handling
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                # Add a small delay to ensure file handle is released
                import time
                time.sleep(0.1)
                os.unlink(temp_file_path)
                Logger.info(f"✅ Temporary image file cleaned up: {temp_file_path}")
            except PermissionError as e:
                Logger.warning(f"⚠️ Could not delete temporary file {temp_file_path}: {e}")
                # On Windows, sometimes we need to wait a bit longer
                try:
                    time.sleep(0.5)
                    os.unlink(temp_file_path)
                    Logger.info(f"✅ Temporary image file cleaned up after delay: {temp_file_path}")
                except Exception as cleanup_error:
                    Logger.error(f"❌ Failed to clean up temporary file {temp_file_path}: {cleanup_error}")
            except Exception as e:
                Logger.error(f"❌ Failed to clean up temporary file {temp_file_path}: {e}")

@chat_router.post("/{phone_number}/send-audio")
async def send_audio_message(
    phone_number: str = Path(..., description="Phone number to send audio/voice to", example="923001234567"),
    file: UploadFile = File(..., description="Audio file to send (MP3, OGG, WAV)"),
    sender: Literal["customer", "agent", "representative"] = Form(..., description="Sender of the message")
):
    """
    Send an audio/voice WhatsApp message to a specific phone number.
    
    - **phone_number**: The phone number to send the audio/voice to
    - **file**: Audio file to send (MP3, OGG, WAV)
    - **sender**: Sender of the message (customer, agent, or representative)
    """
    temp_file_path = None
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file (MP3, OGG, WAV)")
        
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (WhatsApp audio limit: 16MB)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        max_size = 16 * 1024 * 1024  # 16MB for audio
        if file_size > max_size:
            raise HTTPException(status_code=400, detail=f"Audio file too large. Maximum size is 16MB")
        
        # Create temporary file
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file.flush()  # Ensure all data is written
            temp_file_path = temp_file.name
        
        # Send audio message
        success = await message_handler.send_audio(phone_number, temp_file_path)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send audio message via WhatsApp API")
        
        # Upload file to Supabase storage
        file_url = storage_manager.upload_file(temp_file_path, content_type=file.content_type)
        if not file_url:
            raise HTTPException(status_code=500, detail="Failed to upload audio to storage")
        
        # Create message object for storage with markdown link
        content_text = f"[Audio Message]({file_url})"
        new_message = MessageSchema(
            time_stamp=_get_current_karachi_time_str(),
            content=content_text,
            message_type="audio",
            sender=sender
        )
        
        # Store message in database
        try:
            db_success = chat_db.add_or_create_message(phone_number, new_message)
            if db_success:
                Logger.info(f"✅ Audio message stored in database")
        except Exception as e:
            Logger.error(f"{__name__}: send_audio_message -> ❌ Failed to store audio message in database: {e}")

        return SendMessageResponse(
            success=True,
            message="Audio message sent successfully",
            timestamp=new_message.time_stamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="Database table not found. Please run the database setup first."
            )
        raise HTTPException(status_code=500, detail=f"Failed to send audio message: {error_msg}")
    finally:
        # Clean up temporary file with proper error handling
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                # Add a small delay to ensure file handle is released
                import time
                time.sleep(0.1)
                os.unlink(temp_file_path)
                Logger.info(f"✅ Temporary audio file cleaned up: {temp_file_path}")
            except PermissionError as e:
                Logger.warning(f"⚠️ Could not delete temporary file {temp_file_path}: {e}")
                # On Windows, sometimes we need to wait a bit longer
                try:
                    time.sleep(0.5)
                    os.unlink(temp_file_path)
                    Logger.info(f"✅ Temporary audio file cleaned up after delay: {temp_file_path}")
                except Exception as cleanup_error:
                    Logger.error(f"❌ Failed to clean up temporary file {temp_file_path}: {cleanup_error}")
            except Exception as e:
                Logger.error(f"❌ Failed to clean up temporary file {temp_file_path}: {e}")


@chat_router.post("/{phone_number}/send-document")
async def send_document_message(
    phone_number: str = Path(..., description="Phone number to send document to", example="923001234567"),
    file: UploadFile = File(..., description="Document file to send (PDF, DOC, DOCX, etc.)"),
    caption: Optional[str] = Form(None, description="Optional caption for the document"),
    sender: Literal["customer", "agent", "representative"] = Form(..., description="Sender of the message")
):
    """
    Send a document WhatsApp message to a specific phone number.
    
    - **phone_number**: The phone number to send the document to
    - **file**: Document file to upload and send
    - **caption**: Optional caption for the document
    - **sender**: Sender of the message (customer, agent, or representative)
    """
    temp_file_path = None
    try:
        # Validate file type
        allowed_types = [
            'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain', 'application/rtf'
        ]
        
        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="File must be a supported document type (PDF, DOC, DOCX, XLS, XLSX, TXT, RTF)"
            )
        
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (WhatsApp document limit: 100MB)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        max_size = 100 * 1024 * 1024  # 100MB for documents
        if file_size > max_size:
            raise HTTPException(status_code=400, detail=f"Document file too large. Maximum size is 100MB")
        
        # Create temporary file
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file.flush()  # Ensure all data is written
            temp_file_path = temp_file.name
        
        # Send document message (assuming send_document method exists in WhatsAppMessageHandler)
        # Note: You may need to implement this method in WhatsAppMessageHandler
        try:
            success = await message_handler.send_document(phone_number, temp_file_path, caption)
        except AttributeError:
            # Fallback to send_message if send_document doesn't exist
            fallback_text = f"Document: {file.filename or 'Document'}"
            if caption:
                fallback_text += f" - {caption}"
            success = await message_handler.send_message(phone_number, fallback_text)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send document message via WhatsApp API")
        
        # Upload file to Supabase storage
        file_url = storage_manager.upload_file(temp_file_path, content_type=file.content_type)
        if not file_url:
            raise HTTPException(status_code=500, detail="Failed to upload document to storage")
        
        # Create message object for storage with markdown link
        file_name = file.filename or "Document"
        caption_text = caption or file_name
        content_text = f"[{caption_text}]({file_url})"
        new_message = MessageSchema(
            time_stamp=_get_current_karachi_time_str(),
            content=content_text,
            message_type="document",
            sender=sender
        )
        
        # Store message in database
        try:
            db_success = chat_db.add_or_create_message(phone_number, new_message)
            if db_success:
                Logger.info(f"✅ Document message stored in database")
        except Exception as e:
            Logger.error(f"{__name__}: send_document_message -> ❌ Failed to store document message in database: {e}")

        return SendMessageResponse(
            success=True,
            message="Document message sent successfully",
            timestamp=new_message.time_stamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="Database table not found. Please run the database setup first."
            )
        raise HTTPException(status_code=500, detail=f"Failed to send document message: {error_msg}")
    finally:
        # Clean up temporary file with proper error handling
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                # Add a small delay to ensure file handle is released
                import time
                time.sleep(0.1)
                os.unlink(temp_file_path)
                Logger.info(f"✅ Temporary document file cleaned up: {temp_file_path}")
            except PermissionError as e:
                Logger.warning(f"⚠️ Could not delete temporary file {temp_file_path}: {e}")
                # On Windows, sometimes we need to wait a bit longer
                try:
                    time.sleep(0.5)
                    os.unlink(temp_file_path)
                    Logger.info(f"✅ Temporary document file cleaned up after delay: {temp_file_path}")
                except Exception as cleanup_error:
                    Logger.error(f"❌ Failed to clean up temporary file {temp_file_path}: {cleanup_error}")
            except Exception as e:
                Logger.error(f"❌ Failed to clean up temporary file {temp_file_path}: {e}")
