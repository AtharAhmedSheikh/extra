# exceptions.py
"""
Custom exception classes for the WhatsApp Support & QuickBooks Agent workflow.
These exceptions make error handling more descriptive and maintainable.
"""

class WorkflowBaseError(Exception):
    """Base class for all custom workflow exceptions."""
    pass

# =============================
# 1. Input & Validation Errors
# =============================
class InvalidPhoneNumberError(WorkflowBaseError):
    """Raised when the provided phone number format is invalid."""
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        super().__init__(f"Invalid phone number: {phone_number}")


class MissingRequiredFieldError(WorkflowBaseError):
    """Raised when a required field is missing in request data."""
    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(f"Missing required field: {field_name}")


class UnsupportedMessageTypeError(WorkflowBaseError):
    """Raised when the message type is not supported by the agent."""
    def __init__(self, message_type: str):
        self.message_type = message_type
        super().__init__(f"Unsupported message type: {message_type}")


# =============================
# 2. Database & Data Access Errors
# =============================
class CustomerNotFoundError(WorkflowBaseError):
    """Raised when customer details are not found in the database."""
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        super().__init__(f"No customer found for phone number: {phone_number}")


class ChatHistoryNotFoundError(WorkflowBaseError):
    """Raised when chat history is not found for the given customer."""
    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        super().__init__(f"No chat history found for phone number: {phone_number}")


class DatabaseConnectionError(WorkflowBaseError):
    """Raised when the database connection fails."""
    pass


# =============================
# 3. Agent & Processing Errors
# =============================
class AgentProcessingError(WorkflowBaseError):
    """Raised when an agent fails to process the request."""
    def __init__(self, agent_name: str, reason: str):
        self.agent_name = agent_name
        self.reason = reason
        super().__init__(f"Agent '{agent_name}' failed to process request: {reason}")


class InvalidIntentError(WorkflowBaseError):
    """Raised when intent routing returns an unsupported intent."""
    def __init__(self, intent: str):
        self.intent = intent
        super().__init__(f"Invalid or unsupported intent: {intent}")


# =============================
# 4. External API & Integration Errors
# =============================
class QuickBooksAPIError(WorkflowBaseError):
    """Raised when QuickBooks API request fails."""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(f"QuickBooks API Error: {message} (Status: {status_code})")


class WhatsAppAPIError(WorkflowBaseError):
    """Raised when sending or receiving WhatsApp messages fails."""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(f"WhatsApp API Error: {message} (Status: {status_code})")


# =============================
# 5. Security & Permission Errors
# =============================
class UnauthorizedAccessError(WorkflowBaseError):
    """Raised when an API key or credentials are invalid."""
    pass


class ForbiddenActionError(WorkflowBaseError):
    """Raised when an action is not allowed for the current user/role."""
    pass
