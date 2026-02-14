from __future__ import annotations

from buzz import enforce_defined, require_condition
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.roles import Role
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
from site_nine.messaging.message_ids import format_message_id, get_next_message_number
from site_nine.messaging.models import Conversation, ConversationView, Message


class MessageManager:
    """
    Manages messaging operations for agent-to-agent communication.

    This manager handles:
    - Conversation (1-on-1) and Discussion (scoped group) CRUD
    - Message creation and retrieval
    - Conversation auto-creation logic
    - Conversation close/reopen logic
    - Conversation view tracking
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def _get_next_conversation_id(self) -> str:
        """
        Get next conversation ID.

        Conversation IDs follow format: CONV-[NNNN]
        Sequential numbering from 0001 to 9999.

        Returns:
            Next conversation ID
        """
        result = self.db.execute_query(
            """
            SELECT MAX(CAST(SUBSTR(id, 6) AS INTEGER)) as max_num
            FROM conversations
            """
        )

        max_num = result[0]["max_num"]
        next_num = 1 if max_num is None else max_num + 1

        return f"CONV-{next_num:04d}"

    def _get_next_message_id(self, priority: str) -> str:
        """
        Get next message ID with priority code.

        Message IDs follow format: MSG-[P]-[NNNN]
        where P is priority code (C/H/M/L).

        Args:
            priority: Message priority (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            Next message ID
        """
        next_num = get_next_message_number(self.db)
        return format_message_id(priority, next_num)

    # ============================================================================
    # Conversation CRUD
    # ============================================================================

    def create_conversation(
        self,
        subject: str,
        participant_1_id: int,
        participant_2_id: int,
        task_id: str | None = None,
        epic_id: str | None = None,
    ) -> Conversation:
        """
        Create a new 1-on-1 conversation.

        Args:
            subject: Conversation subject
            participant_1_id: First participant mission ID
            participant_2_id: Second participant mission ID
            task_id: Optional related task
            epic_id: Optional related epic

        Returns:
            Created conversation

        Raises:
            InvalidParticipantError: If participant IDs are invalid or the same
        """
        require_condition(
            participant_1_id != participant_2_id,
            "Participants must be different missions",
            raise_exc_class=InvalidParticipantError,
        )

        conversation_id = self._get_next_conversation_id()

        logger.debug(
            "creating_conversation",
            conversation_id=conversation_id,
            participant_1_id=participant_1_id,
            participant_2_id=participant_2_id,
        )

        self.db.execute_update(
            """
            INSERT INTO conversations (
                id, subject, type, status,
                participant_1_id, participant_2_id,
                scope_type, scope_role, scope_epic_id,
                task_id, epic_id
            ) VALUES (
                :id, :subject, 'conversation', 'open',
                :participant_1_id, :participant_2_id,
                NULL, NULL, NULL,
                :task_id, :epic_id
            )
            """,
            {
                "id": conversation_id,
                "subject": subject,
                "participant_1_id": participant_1_id,
                "participant_2_id": participant_2_id,
                "task_id": task_id,
                "epic_id": epic_id,
            },
        )

        conversation = self.get_conversation(conversation_id)
        return enforce_defined(conversation, "Failed to create conversation")

    def create_discussion(
        self,
        subject: str,
        scope_type: str,
        scope_role: str | None = None,
        scope_epic_id: str | None = None,
        task_id: str | None = None,
        epic_id: str | None = None,
    ) -> Conversation:
        """
        Create a new scoped discussion.

        Args:
            subject: Discussion subject
            scope_type: 'role', 'epic', or 'all'
            scope_role: Role name if scope_type='role'
            scope_epic_id: Epic ID if scope_type='epic'
            task_id: Optional related task
            epic_id: Optional related epic

        Returns:
            Created discussion

        Raises:
            InvalidScopeError: If scope configuration is invalid
        """
        # Validate scope configuration
        if scope_type == "role":
            require_condition(
                scope_role is not None,
                "scope_role required when scope_type='role'",
                raise_exc_class=InvalidScopeError,
            )
            # Type narrowing: scope_role is guaranteed to be str here
            assert scope_role is not None
            try:
                Role.from_string(scope_role)
            except ValueError as e:
                raise InvalidScopeError(f"Invalid role: {scope_role}") from e
        elif scope_type == "epic":
            require_condition(
                scope_epic_id is not None,
                "scope_epic_id required when scope_type='epic'",
                raise_exc_class=InvalidScopeError,
            )
        elif scope_type != "all":
            raise InvalidScopeError(f"Invalid scope_type: {scope_type}")

        conversation_id = self._get_next_conversation_id()

        logger.debug(
            "creating_discussion",
            conversation_id=conversation_id,
            scope_type=scope_type,
            scope_role=scope_role,
            scope_epic_id=scope_epic_id,
        )

        self.db.execute_update(
            """
            INSERT INTO conversations (
                id, subject, type, status,
                participant_1_id, participant_2_id,
                scope_type, scope_role, scope_epic_id,
                task_id, epic_id
            ) VALUES (
                :id, :subject, 'discussion', 'open',
                NULL, NULL,
                :scope_type, :scope_role, :scope_epic_id,
                :task_id, :epic_id
            )
            """,
            {
                "id": conversation_id,
                "subject": subject,
                "scope_type": scope_type,
                "scope_role": scope_role,
                "scope_epic_id": scope_epic_id,
                "task_id": task_id,
                "epic_id": epic_id,
            },
        )

        conversation = self.get_conversation(conversation_id)
        return enforce_defined(conversation, "Failed to create discussion")

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation or None if not found
        """
        rows = self.db.execute_query(
            "SELECT * FROM conversations WHERE id = :id",
            {"id": conversation_id},
        )
        return Conversation.from_db_row(rows[0]) if rows else None

    def get_or_create_conversation(
        self,
        participant_1_id: int,
        participant_2_id: int,
        subject: str,
        task_id: str | None = None,
        epic_id: str | None = None,
    ) -> Conversation:
        """
        Get existing open conversation between two missions, or create new one.

        This implements the auto-creation logic from ADR-008:
        1. Check if open conversation exists between the two missions
        2. If closed conversation exists, create NEW conversation (fresh start)
        3. If no conversation exists, create new conversation

        Args:
            participant_1_id: First participant mission ID
            participant_2_id: Second participant mission ID
            subject: Conversation subject (used if creating new)
            task_id: Optional related task
            epic_id: Optional related epic

        Returns:
            Existing or newly created conversation
        """
        # Normalize participant order (lower ID first) for consistent lookups
        p1, p2 = sorted([participant_1_id, participant_2_id])

        # Check for existing open conversation
        rows = self.db.execute_query(
            """
            SELECT * FROM conversations
            WHERE type = 'conversation'
            AND status = 'open'
            AND (
                (participant_1_id = :p1 AND participant_2_id = :p2)
                OR (participant_1_id = :p2 AND participant_2_id = :p1)
            )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"p1": p1, "p2": p2},
        )

        if rows:
            logger.debug(
                "found_existing_conversation",
                conversation_id=rows[0]["id"],
                participant_1_id=p1,
                participant_2_id=p2,
            )
            return Conversation.from_db_row(rows[0])

        # No open conversation exists, create new one
        logger.debug(
            "auto_creating_conversation",
            participant_1_id=p1,
            participant_2_id=p2,
        )
        return self.create_conversation(
            subject=subject,
            participant_1_id=p1,
            participant_2_id=p2,
            task_id=task_id,
            epic_id=epic_id,
        )

    def list_conversations(
        self,
        conversation_type: str | None = None,
        status: str | None = None,
        mission_id: int | None = None,
    ) -> list[Conversation]:
        """
        List conversations/discussions with optional filtering.

        Args:
            conversation_type: Filter by 'conversation' or 'discussion'
            status: Filter by 'open' or 'closed'
            mission_id: Filter by participant mission (conversations only)

        Returns:
            List of matching conversations
        """
        query = "SELECT * FROM conversations WHERE 1=1"
        params: dict = {}

        if conversation_type:
            query += " AND type = :type"
            params["type"] = conversation_type

        if status:
            query += " AND status = :status"
            params["status"] = status

        if mission_id:
            query += """
                AND (
                    participant_1_id = :mission_id 
                    OR participant_2_id = :mission_id
                )
            """
            params["mission_id"] = mission_id

        query += " ORDER BY updated_at DESC"

        rows = self.db.execute_query(query, params)
        return [Conversation.from_db_row(row) for row in rows]

    def close_conversation(self, conversation_id: str) -> Conversation:
        """
        Close a conversation/discussion.

        Args:
            conversation_id: Conversation ID

        Returns:
            Updated conversation

        Raises:
            ConversationNotFoundError: If conversation not found
            ConversationClosedError: If already closed
        """
        conversation = self.get_conversation(conversation_id)
        conversation = enforce_defined(
            conversation,
            f"Conversation {conversation_id} not found",
            raise_exc_class=ConversationNotFoundError,
        )

        require_condition(
            conversation.status == "open",
            f"Conversation {conversation_id} is already closed",
            raise_exc_class=ConversationClosedError,
        )

        logger.debug("closing_conversation", conversation_id=conversation_id)

        self.db.execute_update(
            """
            UPDATE conversations
            SET status = 'closed', closed_at = datetime('now')
            WHERE id = :id
            """,
            {"id": conversation_id},
        )

        updated = self.get_conversation(conversation_id)
        return enforce_defined(updated, "Failed to close conversation")

    def reopen_conversation(self, conversation_id: str) -> Conversation:
        """
        Reopen a closed conversation/discussion.

        Args:
            conversation_id: Conversation ID

        Returns:
            Updated conversation

        Raises:
            ConversationNotFoundError: If conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        conversation = enforce_defined(
            conversation,
            f"Conversation {conversation_id} not found",
            raise_exc_class=ConversationNotFoundError,
        )

        require_condition(
            conversation.status == "closed",
            f"Conversation {conversation_id} is not closed",
            raise_exc_class=MessagingError,
        )

        logger.debug("reopening_conversation", conversation_id=conversation_id)

        self.db.execute_update(
            """
            UPDATE conversations
            SET status = 'open', closed_at = NULL
            WHERE id = :id
            """,
            {"id": conversation_id},
        )

        updated = self.get_conversation(conversation_id)
        return enforce_defined(updated, "Failed to reopen conversation")

    # ============================================================================
    # Message CRUD
    # ============================================================================

    def create_message(
        self,
        conversation_id: str,
        from_mission_id: int,
        subject: str,
        body: str,
        priority: str = "MEDIUM",
        parent_message_id: str | None = None,
        task_id: str | None = None,
        epic_id: str | None = None,
        artifact_path: str | None = None,
    ) -> Message:
        """
        Create a new message in a conversation or discussion.

        Args:
            conversation_id: Parent conversation/discussion ID
            from_mission_id: Sender mission ID
            subject: Message subject
            body: Markdown-formatted message body
            priority: CRITICAL, HIGH, MEDIUM, or LOW
            parent_message_id: Parent message for threading (NULL = root)
            task_id: Optional related task
            epic_id: Optional related epic
            artifact_path: Optional related file/artifact

        Returns:
            Created message

        Raises:
            ConversationNotFoundError: If conversation not found
            ConversationClosedError: If conversation is closed
            InvalidThreadingError: If threading is invalid
        """
        # Validate conversation exists and is open
        conversation = self.get_conversation(conversation_id)
        conversation = enforce_defined(
            conversation,
            f"Conversation {conversation_id} not found",
            raise_exc_class=ConversationNotFoundError,
        )

        require_condition(
            conversation.status == "open",
            f"Cannot send message to closed conversation {conversation_id}",
            raise_exc_class=ConversationClosedError,
        )

        # Validate threading rules
        if parent_message_id:
            # Threading only allowed in discussions
            require_condition(
                conversation.is_discussion(),
                "Threading not allowed in conversations (type='conversation')",
                raise_exc_class=InvalidThreadingError,
            )

            # Parent message must exist
            parent = self.get_message(parent_message_id)
            parent = enforce_defined(
                parent,
                f"Parent message {parent_message_id} not found",
                raise_exc_class=MessageNotFoundError,
            )

            # Parent must be in same conversation
            require_condition(
                parent.conversation_id == conversation_id,
                f"Parent message not in conversation {conversation_id}",
                raise_exc_class=InvalidThreadingError,
            )

            # Determine thread root
            thread_root_id = parent.thread_root_id or parent.id
        else:
            thread_root_id = None

        message_id = self._get_next_message_id(priority)

        logger.debug(
            "creating_message",
            message_id=message_id,
            conversation_id=conversation_id,
            from_mission_id=from_mission_id,
            parent_message_id=parent_message_id,
        )

        self.db.execute_update(
            """
            INSERT INTO messages (
                id, conversation_id, from_mission_id,
                subject, body, priority,
                parent_message_id, thread_root_id,
                task_id, epic_id, artifact_path
            ) VALUES (
                :id, :conversation_id, :from_mission_id,
                :subject, :body, :priority,
                :parent_message_id, :thread_root_id,
                :task_id, :epic_id, :artifact_path
            )
            """,
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "from_mission_id": from_mission_id,
                "subject": subject,
                "body": body,
                "priority": priority,
                "parent_message_id": parent_message_id,
                "thread_root_id": thread_root_id,
                "task_id": task_id,
                "epic_id": epic_id,
                "artifact_path": artifact_path,
            },
        )

        message = self.get_message(message_id)
        return enforce_defined(message, "Failed to create message")

    def get_message(self, message_id: str) -> Message | None:
        """
        Get message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message or None if not found
        """
        rows = self.db.execute_query(
            "SELECT * FROM messages WHERE id = :id",
            {"id": message_id},
        )
        return Message.from_db_row(rows[0]) if rows else None

    def list_messages(
        self,
        conversation_id: str | None = None,
        from_mission_id: int | None = None,
        priority: str | None = None,
    ) -> list[Message]:
        """
        List messages with optional filtering.

        Args:
            conversation_id: Filter by conversation
            from_mission_id: Filter by sender
            priority: Filter by priority level

        Returns:
            List of matching messages ordered by created_at
        """
        query = "SELECT * FROM messages WHERE 1=1"
        params: dict = {}

        if conversation_id:
            query += " AND conversation_id = :conversation_id"
            params["conversation_id"] = conversation_id

        if from_mission_id:
            query += " AND from_mission_id = :from_mission_id"
            params["from_mission_id"] = from_mission_id

        if priority:
            query += " AND priority = :priority"
            params["priority"] = priority

        query += " ORDER BY created_at ASC"

        rows = self.db.execute_query(query, params)
        return [Message.from_db_row(row) for row in rows]

    def get_message_thread(self, thread_root_id: str) -> list[Message]:
        """
        Get all messages in a thread.

        Args:
            thread_root_id: Root message ID of the thread

        Returns:
            List of messages in the thread (root first, then by created_at)
        """
        # Get root message
        root = self.get_message(thread_root_id)
        if not root:
            return []

        # Get all replies
        rows = self.db.execute_query(
            """
            SELECT * FROM messages
            WHERE thread_root_id = :root_id
            ORDER BY created_at ASC
            """,
            {"root_id": thread_root_id},
        )

        replies = [Message.from_db_row(row) for row in rows]
        return [root] + replies

    # ============================================================================
    # Conversation View Tracking
    # ============================================================================

    def update_conversation_view(self, conversation_id: str, mission_id: int) -> ConversationView:
        """
        Update last viewed timestamp for a conversation.

        Args:
            conversation_id: Conversation ID
            mission_id: Mission ID

        Returns:
            Updated conversation view
        """
        logger.debug(
            "updating_conversation_view",
            conversation_id=conversation_id,
            mission_id=mission_id,
        )

        self.db.execute_update(
            """
            INSERT INTO conversation_views (conversation_id, mission_id, last_viewed_at)
            VALUES (:conversation_id, :mission_id, datetime('now'))
            ON CONFLICT(conversation_id, mission_id)
            DO UPDATE SET last_viewed_at = datetime('now')
            """,
            {"conversation_id": conversation_id, "mission_id": mission_id},
        )

        view = self.get_conversation_view(conversation_id, mission_id)
        return enforce_defined(view, "Failed to update conversation view")

    def get_conversation_view(self, conversation_id: str, mission_id: int) -> ConversationView | None:
        """
        Get conversation view record.

        Args:
            conversation_id: Conversation ID
            mission_id: Mission ID

        Returns:
            ConversationView or None if never viewed
        """
        rows = self.db.execute_query(
            """
            SELECT * FROM conversation_views
            WHERE conversation_id = :conversation_id
            AND mission_id = :mission_id
            """,
            {"conversation_id": conversation_id, "mission_id": mission_id},
        )
        return ConversationView.from_db_row(rows[0]) if rows else None

    def get_unread_conversations(self, mission_id: int) -> list[Conversation]:
        """
        Get conversations with unread messages for a mission.

        A conversation has unread messages if:
        - It has messages
        - The mission has never viewed it, OR
        - The last message is newer than the last view timestamp

        Args:
            mission_id: Mission ID

        Returns:
            List of conversations with unread messages
        """
        rows = self.db.execute_query(
            """
            SELECT DISTINCT c.*
            FROM conversations c
            JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN conversation_views cv ON (
                c.id = cv.conversation_id 
                AND cv.mission_id = :mission_id
            )
            WHERE c.status = 'open'
            AND (
                -- Never viewed
                cv.last_viewed_at IS NULL
                OR
                -- Has messages newer than last view
                EXISTS (
                    SELECT 1 FROM messages m2
                    WHERE m2.conversation_id = c.id
                    AND m2.created_at > cv.last_viewed_at
                )
            )
            AND (
                -- For conversations: mission is a participant
                (c.type = 'conversation' AND (
                    c.participant_1_id = :mission_id 
                    OR c.participant_2_id = :mission_id
                ))
                OR
                -- For discussions: mission is in scope (TODO: implement scope check)
                (c.type = 'discussion')
            )
            ORDER BY c.updated_at DESC
            """,
            {"mission_id": mission_id},
        )
        return [Conversation.from_db_row(row) for row in rows]
