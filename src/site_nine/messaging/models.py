from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Self

import pendulum

from site_nine.core.utils import parse_timestamp

ConversationType = Literal["conversation", "discussion"]
ConversationStatus = Literal["open", "closed"]
MessagePriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
ScopeType = Literal["role", "epic", "all"]


@dataclass
class Conversation:
    """
    A conversation or discussion between missions.

    Conversations are 1-on-1 between two missions with flat message structure.
    Discussions are scoped to role/epic/all with threaded messages.

    Attributes:
        id: Conversation identifier (CONV-[NNNN] format)
        subject: Conversation subject
        type: 'conversation' (1-on-1) or 'discussion' (scoped group)
        status: 'open' or 'closed'
        participant_1_id: First participant mission ID (NULL for discussions)
        participant_2_id: Second participant mission ID (NULL for discussions)
        scope_type: 'role', 'epic', or 'all' (NULL for conversations)
        scope_role: Role name if scope_type='role'
        scope_epic_id: Epic ID if scope_type='epic'
        task_id: Optional related task
        epic_id: Optional related epic
        created_at: Creation timestamp
        updated_at: Last update timestamp
        closed_at: Close timestamp (NULL if open)
    """

    id: str
    subject: str
    type: ConversationType
    status: ConversationStatus
    participant_1_id: int | None
    participant_2_id: int | None
    scope_type: ScopeType | None
    scope_role: str | None
    scope_epic_id: str | None
    task_id: str | None
    epic_id: str | None
    created_at: pendulum.DateTime
    updated_at: pendulum.DateTime
    closed_at: pendulum.DateTime | None

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Conversation from database row."""
        created_at = parse_timestamp(row["created_at"])
        updated_at = parse_timestamp(row["updated_at"])
        closed_at = parse_timestamp(row["closed_at"]) if row.get("closed_at") else None

        return cls(
            id=row["id"],
            subject=row["subject"],
            type=row["type"],
            status=row["status"],
            participant_1_id=row.get("participant_1_id"),
            participant_2_id=row.get("participant_2_id"),
            scope_type=row.get("scope_type"),
            scope_role=row.get("scope_role"),
            scope_epic_id=row.get("scope_epic_id"),
            task_id=row.get("task_id"),
            epic_id=row.get("epic_id"),
            created_at=created_at,
            updated_at=updated_at,
            closed_at=closed_at,
        )

    def is_conversation(self) -> bool:
        """Check if this is a 1-on-1 conversation."""
        return self.type == "conversation"

    def is_discussion(self) -> bool:
        """Check if this is a scoped discussion."""
        return self.type == "discussion"

    def is_participant(self, mission_id: int) -> bool:
        """Check if a mission is a participant in this conversation."""
        if self.is_conversation():
            return mission_id in (self.participant_1_id, self.participant_2_id)
        return False  # Discussions use dynamic scoping


@dataclass
class Message:
    """
    A message in a conversation or discussion.

    Attributes:
        id: Message identifier (MSG-[P]-[NNNN] format, P = priority)
        conversation_id: Parent conversation/discussion ID
        from_mission_id: Sender mission ID
        subject: Message subject
        body: Markdown-formatted body
        priority: CRITICAL, HIGH, MEDIUM, or LOW
        parent_message_id: Parent message for threading (NULL = root)
        thread_root_id: Root of thread tree (NULL = root or conversation)
        task_id: Optional related task
        epic_id: Optional related epic
        artifact_path: Optional related file/artifact
        created_at: Creation timestamp
        expires_at: Optional expiration timestamp
    """

    id: str
    conversation_id: str
    from_mission_id: int
    subject: str
    body: str
    priority: MessagePriority
    parent_message_id: str | None
    thread_root_id: str | None
    task_id: str | None
    epic_id: str | None
    artifact_path: str | None
    created_at: pendulum.DateTime
    expires_at: pendulum.DateTime | None

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Message from database row."""
        created_at = parse_timestamp(row["created_at"])
        expires_at = parse_timestamp(row["expires_at"]) if row.get("expires_at") else None

        return cls(
            id=row["id"],
            conversation_id=row["conversation_id"],
            from_mission_id=row["from_mission_id"],
            subject=row["subject"],
            body=row["body"],
            priority=row["priority"],
            parent_message_id=row.get("parent_message_id"),
            thread_root_id=row.get("thread_root_id"),
            task_id=row.get("task_id"),
            epic_id=row.get("epic_id"),
            artifact_path=row.get("artifact_path"),
            created_at=created_at,
            expires_at=expires_at,
        )

    def is_root_message(self) -> bool:
        """Check if this is a root message (not a reply)."""
        return self.parent_message_id is None

    def is_threaded_reply(self) -> bool:
        """Check if this is a threaded reply."""
        return self.parent_message_id is not None


@dataclass
class ConversationView:
    """
    Tracks when a mission last viewed a conversation.

    Attributes:
        conversation_id: Conversation/discussion ID
        mission_id: Mission ID
        last_viewed_at: Last view timestamp
    """

    conversation_id: str
    mission_id: int
    last_viewed_at: pendulum.DateTime

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create ConversationView from database row."""
        last_viewed_at = parse_timestamp(row["last_viewed_at"])

        return cls(
            conversation_id=row["conversation_id"],
            mission_id=row["mission_id"],
            last_viewed_at=last_viewed_at,
        )


@dataclass
class MessageAcknowledgement:
    """
    Tracks when a mission acknowledges/processes a specific message.

    Attributes:
        message_id: Message identifier
        mission_id: Mission ID that acknowledged the message
        acknowledged_at: Acknowledgement timestamp
    """

    message_id: str
    mission_id: int
    acknowledged_at: pendulum.DateTime

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create MessageAcknowledgement from database row."""
        acknowledged_at = parse_timestamp(row["acknowledged_at"])

        return cls(
            message_id=row["message_id"],
            mission_id=row["mission_id"],
            acknowledged_at=acknowledged_at,
        )
