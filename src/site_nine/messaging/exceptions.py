from site_nine.exceptions import SiteNineError


class MessagingError(SiteNineError):
    """Base messaging operation error."""


class ConversationNotFoundError(MessagingError):
    """Conversation not found."""


class MessageNotFoundError(MessagingError):
    """Message not found."""


class InvalidConversationTypeError(MessagingError):
    """Invalid conversation type."""


class ConversationClosedError(MessagingError):
    """Conversation is closed."""


class InvalidThreadingError(MessagingError):
    """Invalid message threading."""


class InvalidParticipantError(MessagingError):
    """Invalid conversation participant."""


class InvalidScopeError(MessagingError):
    """Invalid discussion scope."""
