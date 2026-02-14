"""Messaging module for agent-to-agent communication"""

from site_nine.messaging.exceptions import (
    ConversationClosedError,
    ConversationNotFoundError,
    InvalidConversationTypeError,
    InvalidParticipantError,
    InvalidScopeError,
    InvalidThreadingError,
    MessageNotFoundError,
    MessagingError,
)
from site_nine.messaging.manager import MessageManager
from site_nine.messaging.message_ids import (
    format_message_id,
    get_next_message_number,
    parse_message_id,
    sort_message_ids,
    validate_message_id,
)
from site_nine.messaging.models import Conversation, ConversationView, Message

__all__ = [
    # Manager
    "MessageManager",
    # Models
    "Conversation",
    "ConversationView",
    "Message",
    # Exceptions
    "MessagingError",
    "ConversationNotFoundError",
    "MessageNotFoundError",
    "InvalidConversationTypeError",
    "ConversationClosedError",
    "InvalidThreadingError",
    "InvalidParticipantError",
    "InvalidScopeError",
    # Message ID utilities
    "format_message_id",
    "get_next_message_number",
    "parse_message_id",
    "sort_message_ids",
    "validate_message_id",
]
