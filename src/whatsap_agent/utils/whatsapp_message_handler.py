from openai import OpenAI
from whatsapp_agent.utils.config import Config
from whatsapp_agent.utils.voice.audio import AudioProcessor
from whatsapp_agent.utils.supabase_storage import SupabaseStorageManager
from whatsapp_agent._debug import Logger

import aiohttp
import os
from pywa_async.types import Image, Video, Document, Audio
import tempfile
import mimetypes
from pywa_async import WhatsApp


class WhatsAppMessageHandler(WhatsApp):
    def __init__(self):
        # Initialize OpenAI client
        super().__init__(phone_id=Config.get("WHATSAPP_PHONE_NO_ID"), token=Config.get("WHATSAPP_ACCESS_TOKEN"))
        self.client = OpenAI(api_key=Config.get("OPENAI_API_KEY"))
        self.audio_processor = AudioProcessor(self.client)
        # Initialize configuration
        self.storage_manager = SupabaseStorageManager()

    async def receive_whatsapp_message(self, data, is_voice=False):
        """Process incoming WhatsApp messages and send replies"""
        try:
            # Extract message data
            message_data = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [{}])[0]
            sender = message_data.get("from")

            if not sender:
                Logger.warning("No sender found in message")
                return

            if is_voice:
                message_data = await self._convert_to_text(message_data, sender)

            # Handle different message types
            message_type = message_data.get("type")
            
            if message_type == "text":
                text = message_data["text"]["body"]
                Logger.info(f"New text message from {sender}: {text}")
                return {'text': text, 'sender': sender, 'message_data': message_data}
            
            elif message_type in ["image", "document", "audio", "video"]:
                # Handle media messages
                media_content = await self._process_media_message(message_data, sender, message_type)
                return {'text': media_content, 'sender': sender, 'message_data': message_data}
            
            else:
                # Handle unknown message types
                Logger.warning(f"Unknown message type {message_type} from {sender}")
                return {'text': f"[{message_type.upper()} MESSAGE]", 'sender': sender, 'message_data': message_data}

        except Exception as e:
            Logger.error(f"Error processing message or sending reply: {e}")
            Logger.error(f"Full error details: {e}")
            import traceback
            Logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def _convert_to_text(self, message_data, sender):
        """Handle incoming voice messages"""
        if message_data.get("type") in ["audio", "voice"]:
            audio_id = message_data["audio"]["id"]

            Logger.info(f"Processing voice message from {sender}")
            Logger.info(f"Audio ID: {audio_id}")

            # Get media URL from Meta API
            media_url = f"https://graph.facebook.com/v17.0/{audio_id}"
            Logger.info(f"Fetching media from: {media_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(media_url, headers=Config.get_whatsapp_headers()) as response:
                    if response.status == 200:
                        media_data = await response.json()
                        audio_url = media_data.get("url")

                        if not audio_url:
                            Logger.error("No audio URL in media data")
                            return

                        # Download and process audio
                        audio_file = await self.audio_processor.download_audio(audio_url, Config.get("WHATSAPP_ACCESS_TOKEN"))
                        if not audio_file:
                            Logger.error("Failed to download audio")
                            return

                        # Convert to text
                        text = await self.audio_processor.convert_to_text(audio_file)
                        if not text:
                            Logger.error("Failed to convert audio to text")
                            return

                        os.unlink(audio_file)
                        del message_data['audio']
                        message_data['type'] = 'text'
                        message_data['text'] = {'body': text}
                        return message_data

                    else:
                        Logger.error(f"Failed to get media URL: {response.status}")
                        Logger.error("Response:", await response.text())
    
    async def _process_media_message(self, message_data, sender, message_type):
        """Handle incoming media messages by downloading and storing them in Supabase"""
        try:
            # Extract media data based on type
            media_info = message_data[message_type]
            media_id = media_info["id"]
            caption = media_info.get("caption", "")
            
            Logger.info(f"Processing {message_type} message from {sender}, media ID: {media_id}")
            
            # Create appropriate media object based on type
            if message_type == "image":
                media_obj = Image(id=media_id, sha256="", mime_type="", _client=self)
            elif message_type == "video":
                media_obj = Video(id=media_id, sha256="", mime_type="", _client=self)
            elif message_type == "document":
                media_obj = Document(id=media_id, sha256="", mime_type="", filename=media_info.get("filename", ""), _client=self)
            elif message_type == "audio":
                media_obj = Audio(id=media_id, sha256="", mime_type="", voice=media_info.get("voice", False), _client=self)
            else:
                Logger.error(f"Unsupported media type: {message_type}")
                return f"[{message_type.upper()} MESSAGE]"
            
            # Create a temporary file for downloading
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Download media using pywa_async directly to the temporary file
                # First, get the media URL
                media_url = await media_obj.get_media_url()
                
                # Download the media content
                async with aiohttp.ClientSession() as session:
                    async with session.get(media_url, headers=Config.get_whatsapp_headers()) as response:
                        if response.status == 200:
                            # Write the content to our temporary file
                            with open(temp_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(1024):
                                    f.write(chunk)
                            
                            Logger.info(f"Downloaded media to: {temp_path}")
                            
                            # Get the actual mime type and file extension
                            mime_type = media_info.get("mime_type", "")
                            if not mime_type:
                                mime_type = response.headers.get("content-type", "application/octet-stream")
                            
                            # Generate a filename for storage
                            storage_filename = media_info.get("filename", "")
                            if not storage_filename:
                                file_extension = mimetypes.guess_extension(mime_type) or f".{message_type}"
                                storage_filename = f"{message_type}_{media_id}{file_extension}"
                            
                            # Upload to Supabase storage
                            file_url = self.storage_manager.upload_file(temp_path, storage_filename, mime_type)
                            
                            if not file_url:
                                Logger.error("Failed to upload media to Supabase storage")
                                return f"[{message_type.upper()} MESSAGE - Upload Failed]"
                            
                            # Clean up temporary file
                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                            
                            # Create markdown link based on media type
                            if message_type == "image":
                                link_text = caption or "Image"
                                return f"![{link_text}]({file_url})"
                            elif message_type == "audio":
                                return f"[Audio Message]({file_url})"
                            else:  # document or video
                                link_text = caption or storage_filename
                                return f"[{link_text}]({file_url})"
                        else:
                            Logger.error(f"Failed to download media: {response.status}")
                            return f"[{message_type.upper()} MESSAGE - Download Failed]"
                    
            except Exception as e:
                Logger.error(f"Error downloading media: {e}")
                # Clean up temporary file if it exists
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return f"[{message_type.upper()} MESSAGE - Download Failed]"
                
        except Exception as e:
            Logger.error(f"Error processing {message_type} message: {e}")
            import traceback
            Logger.error(f"Traceback: {traceback.format_exc()}")
            return f"[{message_type.upper()} MESSAGE - Processing Error]"