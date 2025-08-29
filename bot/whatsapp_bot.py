# Import agents for handling different conversation flows
from whatsapp_agent.agents.b2b_business_support_agent.agent import B2BBusinessSupportAgent
from whatsapp_agent.agents.d2c_customer_support_agent.agent import D2CCustomerSupportAgent
from whatsapp_agent.agents.conversation_intent_router.agent import ConversationIntentRouter
from whatsapp_agent.agents.customer_greeting_agent.agent import CustomerGreetingAgent
# Import QuickBooks integration and MCP server
from whatsapp_agent.quickbook.customers import QuickBookCustomer
from whatsapp_agent.mcp.boost_mcp import get_boost_mcp_server

# Shopify base for GraphQL Admin API
from whatsapp_agent.shopify.base import ShopifyBase

# Import database handlers
from whatsapp_agent.database.chat_history import ChatHistoryDataBase
from whatsapp_agent.database.customer import CustomerDataBase

# Import schemas for chat history and customers
from whatsapp_agent.schema.chat_history import MessageSchema
from whatsapp_agent.schema.customer_schema import CustomerSchema, PersonalInfoSchema

# Import utilities for message handling, timestamps, and WebSocket communication
from whatsapp_agent.utils.whatsapp_message_handler import WhatsAppMessageHandler
from whatsapp_agent.utils.referrals_handler import ReferralHandler
from whatsapp_agent.utils.current_time import _get_current_karachi_time_str
from whatsapp_agent.utils.websocket import websocket_manager

# Import context schema and formatting helpers for system prompt construction
from whatsapp_agent.context.user_context import CustomerContextSchema
from whatsapp_agent.context._formatter import customer_context_to_prompt, chat_history_to_prompt
from whatsapp_agent.context.global_context import GlobalContext, CustomerContextSchemaExtra, MessageSchemaExtra
from typing import List, Literal

from whatsapp_agent._debug import Logger

# Default constants for new customer creation
DEFAULT_CUSTOMER_TYPE = "D2C"
DEFAULT_TOTAL_SPEND = 0

# Initialize database and integration instances
chat_history_db = ChatHistoryDataBase()
customer_db = CustomerDataBase()
quickbook_customer = QuickBookCustomer()
referral_handler = ReferralHandler()
whatsapp_handler = WhatsAppMessageHandler()

class WhatsappBot:
    """Handles WhatsApp incoming messages, routes them to the correct agent, and replies."""

    @classmethod
    async def execute_workflow(cls, data, is_voice: bool = False):
        """
        Main entry point to process incoming WhatsApp messages.
        1. Receive message from WhatsApp
        2. Store message in history
        3. Retrieve or create customer
        4. Route message to appropriate agent based on intent
        5. Send agent's response back to WhatsApp and dashboard
        """
        try:
            # Receive and process the incoming message
            message_data = await cls.receive_whatsapp_message(data, is_voice)

            # Extract raw message content and sender phone number
            raw_message = message_data.get("text")
            phone_number = message_data.get("sender")

            # Fetch recent chat history for context
            chat_history = chat_history_db.get_recent_chat_history_by_phone(phone_number)

            Logger.info("Fetched chat history for customer")

            # Log the incoming message from customer
            cls._log_customer_message(phone_number, raw_message, is_voice)

            # Send message to dashboard WebSocket for live view
            Logger.info(f"Streaming customer message to dashboard for phone: {phone_number}")
            await cls.stream_to_web_socket(phone_number, raw_message, "customer")

            # Get or create the customer record
            customer = cls._get_or_create_customer(phone_number)

            # If the conversation is not escalated, handle with AI agent
            if not customer_db.is_escalated(phone_number):
                # Format messages and customer context for the system prompt
                messages_context = cls._format_message(chat_history)
                customer_context = await cls._format_customer_context(customer)

                # Combine contexts into global context for agent
                global_context = GlobalContext(
                    customer_context=customer_context,
                    messages=messages_context
                )
                if referral_handler._extract_codes(raw_message)[0] is not None:
                    response = await referral_handler.referral_workflow(raw_message, phone_number, global_context)
                else:
                    # Route to the appropriate AI agent based on intent
                    response = await cls._route_to_agent(phone_number, raw_message, global_context)

                Logger.info(f"Response from agent: {response}")
                # Log the agent's response in chat history
                cls._log_agent_message(phone_number, response)
                # Send the agent's message to the dashboard in real-time

                Logger.info(f"Streaming agent response to dashboard for phone: {phone_number}")
                await cls.stream_to_web_socket(phone_number, response, "agent")

                # Debug print of the response
                Logger.info(f"Response sent to {phone_number}: {response}")

                # Send to WhatsApp
                await cls.send_whatsapp_message(phone_number, response)
            else:
                # TODO: Future implementation to notify dashboard about escalation
                Logger.info(f"Customer {phone_number} is escalated, skipping AI routing.")
                pass

        except Exception as e:
            Logger.error(f"{__name__}: execute_workflow -> Error processing message for {phone_number}: {e}")

    @staticmethod
    def _log_customer_message(phone_number: str, raw_message: str, is_voice: bool):
        """Stores the customer's incoming message in chat history."""
        # Determine message type based on content and is_voice flag
        if is_voice:
            message_type = "audio"
        elif raw_message.startswith("![") and "](" in raw_message and raw_message.endswith(")"):
            # Image markdown format: ![caption](url)
            message_type = "image"
        elif raw_message.startswith("[") and "](" in raw_message and raw_message.endswith(")") and "Audio Message" in raw_message:
            # Audio markdown format: [Audio Message](url)
            message_type = "audio"
        elif raw_message.startswith("[") and "](" in raw_message and raw_message.endswith(")"):
            # Document/Video markdown format: [caption](url)
            message_type = "document"
        else:
            # Default to text for regular messages
            message_type = "text"
            
        message = MessageSchema(
            time_stamp=_get_current_karachi_time_str(),
            content=raw_message,
            message_type=message_type,
            sender="customer",
        )
        Logger.info(f"Adding customer message to chat history: {message.content} (type: {message_type})")
        chat_history_db.add_or_create_message(phone_number, message)
        
    @staticmethod
    def _log_agent_message(phone_number: str, response: str):
        """Stores the agent's outgoing message in chat history."""
        message = MessageSchema(
            time_stamp=_get_current_karachi_time_str(),
            content=response,
            message_type="text",
            sender="agent"
        )
        Logger.info(f"Adding agent message to chat history: {message.content}")
        chat_history_db.add_or_create_message(phone_number, message)

    @staticmethod
    def _get_or_create_customer(phone_number: str):
        """
        Retrieve customer by phone number or create a new one.
        Also attempts to sync with QuickBooks if data is missing.
        Before creating an empty record, checks Shopify customers by phone.
        """
        customer_details = customer_db.get_customer_by_phone(phone_number)

        # If no record or incomplete data, try fetching from QuickBooks
        if (not customer_details or (
            not customer_details.customer_name or
            not customer_details.email or
            not customer_details.customer_quickbook_id or
            not customer_details.customer_type or
            not customer_details.company_name or
            not customer_details.is_active or
            not customer_details.phone_number
        )):
            customer = quickbook_customer.get_customer_with_type_by_phone(phone_number)

            # Update existing record with QuickBooks data
            if customer and customer_details:
                Logger.info(f"Updating existing customer {phone_number} with QuickBooks data")
                customer_details = customer_db.update_customer(phone_number, customer.dict())

            # Add new record from QuickBooks
            elif customer and not customer_details:
                Logger.info(f"Creating new customer {phone_number} from QuickBooks data")
                new_customer = CustomerSchema(
                    customer_name=customer.customer_name,
                    email=customer.email,
                    customer_quickbook_id=customer.customer_quickbook_id,
                    customer_type=customer.customer_type,
                    company_name=customer.company_name,
                    is_active=customer.is_active,
                    phone_number=phone_number,
                )
                customer_details = customer_db.add_customer(new_customer)

            # Create new record without QuickBooks data
            elif not customer and not customer_details:
                # BEFORE creating an empty customer, try Shopify lookup by phone
                try:
                    shopify = ShopifyBase()
                    shopify_customer = shopify.find_customer_by_phone(phone_number)
                    if shopify_customer:
                        email_obj = shopify_customer.get("defaultEmailAddress") or {}
                        addr = shopify_customer.get("defaultAddress") or {}
                        new_customer = CustomerSchema(
                            phone_number=phone_number,
                            is_active=True,
                            escalation_status=False,
                            customer_type=DEFAULT_CUSTOMER_TYPE,
                            total_spend=shopify_customer.get("totalSpent") or DEFAULT_TOTAL_SPEND,
                            customer_name=shopify_customer.get("displayName"),
                            email=email_obj.get("email"),
                            address=", ".join([
                                part for part in [addr.get("address1"), addr.get("city"), addr.get("province"), addr.get("country"), addr.get("zip")] if part
                            ]) or None,
                        )
                        Logger.info(f"Creating new customer {phone_number} from Shopify customer data")
                        customer_details = customer_db.add_customer(new_customer)
                    else:
                        Logger.info(f"Creating new customer {phone_number} without QuickBooks/Shopify data")
                        new_customer = CustomerSchema(
                            phone_number=phone_number,
                            is_active=True,
                            escalation_status=False,
                            customer_type=DEFAULT_CUSTOMER_TYPE,
                            total_spend=DEFAULT_TOTAL_SPEND
                        )
                        customer_details = customer_db.add_customer(new_customer)
                except Exception as e:
                    Logger.error(f"Shopify lookup failed for {phone_number}: {e}")
                    new_customer = CustomerSchema(
                        phone_number=phone_number,
                        is_active=True,
                        escalation_status=False,
                        customer_type=DEFAULT_CUSTOMER_TYPE,
                        total_spend=DEFAULT_TOTAL_SPEND
                    )
                    customer_details = customer_db.add_customer(new_customer)

            # If no QuickBooks data but customer exists, leave as is
            elif not customer and customer_details:
                pass
            else:
                raise ValueError("Unexpected state")
    
        # Validate and return customer schema
        customer = CustomerSchema.model_validate(customer_details)
        return customer

    @staticmethod
    async def _route_to_agent(phone_number: str, raw_message: str, global_context: GlobalContext) -> str:
        """
        Determine which agent should handle the message based on intent,
        and get the AI-generated response.
        """
        # Use the conversation intent router to decide the next agent
        Logger.info("Routing message to appropriate agent based on intent")
        router_agent = ConversationIntentRouter()
        sentiment = await router_agent.run(raw_message, global_context)

        if (
            sentiment.name or 
            sentiment.email or 
            sentiment.address or 
            sentiment.socials or 
            sentiment.interest_groups
        ):
            personal_info = PersonalInfoSchema(
                customer_name=sentiment.name,
                email=sentiment.email,
                address=sentiment.address,
                socials=sentiment.socials,
                interest_groups=sentiment.interest_groups
            )
            Logger.info(f"Personal info extracted: {personal_info}")
            try:
                customer_db.update_customer(phone_number, personal_info.dict())
                Logger.debug(f"Updated customer {phone_number} with personal info: {personal_info}")
            except Exception as e:
                Logger.error(f"{__name__}: _route_to_agent -> Failed to update customer info: {e}")
        Logger.debug(f"Routing sentiment: {sentiment}")
        Logger.info(f"Routing to agent: {sentiment.next_agent}")

        # Route to the appropriate agent
        if sentiment.next_agent == "CustomerGreetingAgent":
            agent = CustomerGreetingAgent()
            return await agent.run(raw_message, global_context)

        if sentiment.next_agent == "D2CCustomerSupportAgent":
            boost_mcp_server = await get_boost_mcp_server()
            agent = D2CCustomerSupportAgent(boost_mcp_server)
            return await agent.run(raw_message, global_context)

        if sentiment.next_agent == "B2BBusinessSupportAgent":
            boost_mcp_server = await get_boost_mcp_server(
                allowed_tool_names=["search_shop_catalog"]
            )
            agent = B2BBusinessSupportAgent(boost_mcp_server)
            return await agent.run(raw_message, global_context)

        # If no match, raise an error
        Logger.error(f"{__name__}: _route_to_agent -> Unknown agent: {sentiment.next_agent}")
        raise ValueError(f"Unknown agent: {sentiment.next_agent}")

    @staticmethod
    async def _format_customer_context(customer: CustomerSchema) -> CustomerContextSchemaExtra:
        """
        Format the customer context for the system prompt
        by converting it to the prompt-ready format.
        """
        # Convert CustomerSchema to CustomerContextSchema
        context_data = CustomerContextSchema(
            phone_number=customer.phone_number,
            customer_type=customer.customer_type,
            customer_name=customer.customer_name,
            email=customer.email,
            address=customer.address,
            customer_quickbook_id=customer.customer_quickbook_id
        )
        # Format for prompt injection
        formatted = {
            'formatted_context': customer_context_to_prompt(context_data),
            **context_data.dict()
        }
        formatted_context = CustomerContextSchemaExtra.model_validate(formatted)
        Logger.debug(f"Formatted customer context: {formatted_context}")
        return formatted_context

    @staticmethod
    def _format_message(messages: List[MessageSchema]) -> MessageSchemaExtra:
        """
        Format chat messages for the system prompt.
        Converts message history to a string and wraps it in the schema.
        """
        formatted_message = chat_history_to_prompt(messages)
        formatted = {
            'formatted_message': formatted_message,
            'messages': messages
        }
        Logger.debug(f"Formatted message: {formatted}")
        return MessageSchemaExtra.model_validate(formatted)

    @staticmethod
    async def receive_whatsapp_message(data, is_voice=False):
        """Receive and normalize an incoming WhatsApp message via handler."""
        return await whatsapp_handler.receive_whatsapp_message(data, is_voice=is_voice)

    @staticmethod
    async def send_whatsapp_message(to: str, message: str):
        """Send a WhatsApp text message."""
        await whatsapp_handler.send_message(to, message, preview_url=True)

    @staticmethod
    async def stream_to_web_socket(phone_number: str, message: str, sender: Literal["customer", "agent"]):
        """
        Stream message in real-time to the dashboard via WebSocket.
        This allows live updates in the representative's chat view.
        """
        # Determine message type based on content for customer messages
        if sender == "customer":
            if message.startswith("![") and "](" in message and message.endswith(")"):
                # Image markdown format: ![caption](url)
                message_type = "image"
            elif message.startswith("[") and "](" in message and message.endswith(")") and "Audio Message" in message:
                # Audio markdown format: [Audio Message](url)
                message_type = "audio"
            elif message.startswith("[") and "](" in message and message.endswith(")"):
                # Document/Video markdown format: [caption](url)
                message_type = "document"
            else:
                # Default to text for regular messages
                message_type = "text"
        else:
            # Agent messages are always text
            message_type = "text"
            
        await websocket_manager.send_to_phone(phone_number, MessageSchema(
            content=message,
            sender=sender,
            message_type=message_type,
            time_stamp=_get_current_karachi_time_str()
        ))

    async def _save_personal_info(self, phone_number: str, personal_info: PersonalInfoSchema):
        """
        Save personal information for a user.
        """
        
        # await database.save_user_info(phone_number, user_info