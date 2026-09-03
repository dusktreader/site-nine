from __future__ import annotations

from buzz import enforce_defined, require_condition
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.core.utils import utc_now
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
from site_nine.messaging.models import Conversation, ConversationView, Message, MessageAcknowledgement


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
            participant_1_id: First participant possession ID
            participant_2_id: Second participant possession ID
            task_id: Optional related task
            epic_id: Optional related epic

        Returns:
            Created conversation

        Raises:
            InvalidParticipantError: If participant IDs are invalid or the same
        """
        require_condition(
            participant_1_id != participant_2_id,
            "Participants must be different possessions",
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
        Get existing open conversation between two possessions, or create new one.

        This implements the auto-creation logic from ADR-008:
        1. Check if open conversation exists between the two possessions
        2. If closed conversation exists, create NEW conversation (fresh start)
        3. If no conversation exists, create new conversation

        Args:
            participant_1_id: First participant possession ID
            participant_2_id: Second participant possession ID
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
        possession_id: int | None = None,
    ) -> list[Conversation]:
        """
        List conversations/discussions with optional filtering.

        Args:
            conversation_type: Filter by 'conversation' or 'discussion'
            status: Filter by 'open' or 'closed'
            possession_id: Filter by participant possession (conversations only)

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

        if possession_id:
            query += """
                AND (
                    participant_1_id = :possession_id 
                    OR participant_2_id = :possession_id
                )
            """
            params["possession_id"] = possession_id

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
            SET status = 'closed', closed_at = :now
            WHERE id = :id
            """,
            {"id": conversation_id, "now": utc_now()},
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
        from_possession_id: int,
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
            from_possession_id: Sender possession ID
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
            from_possession_id=from_possession_id,
            parent_message_id=parent_message_id,
        )

        self.db.execute_update(
            """
            INSERT INTO messages (
                id, conversation_id, from_possession_id,
                subject, body, priority,
                parent_message_id, thread_root_id,
                task_id, epic_id, artifact_path
            ) VALUES (
                :id, :conversation_id, :from_possession_id,
                :subject, :body, :priority,
                :parent_message_id, :thread_root_id,
                :task_id, :epic_id, :artifact_path
            )
            """,
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "from_possession_id": from_possession_id,
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
        from_possession_id: int | None = None,
        priority: str | None = None,
    ) -> list[Message]:
        """
        List messages with optional filtering.

        Args:
            conversation_id: Filter by conversation
            from_possession_id: Filter by sender
            priority: Filter by priority level

        Returns:
            List of matching messages ordered by created_at
        """
        query = "SELECT * FROM messages WHERE 1=1"
        params: dict = {}

        if conversation_id:
            query += " AND conversation_id = :conversation_id"
            params["conversation_id"] = conversation_id

        if from_possession_id:
            query += " AND from_possession_id = :from_possession_id"
            params["from_possession_id"] = from_possession_id

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

    def update_conversation_view(
        self,
        conversation_id: str,
        possession_id: int,
        viewed_at: str | None = None,
    ) -> ConversationView:
        """
        Update last viewed timestamp for a conversation.

        Args:
            conversation_id: Conversation ID
            possession_id: Possession ID
            viewed_at: Optional explicit timestamp (defaults to utc_now())

        Returns:
            Updated conversation view
        """
        logger.debug(
            "updating_conversation_view",
            conversation_id=conversation_id,
            possession_id=possession_id,
        )

        now = viewed_at if viewed_at is not None else utc_now()
        self.db.execute_update(
            """
            INSERT INTO conversation_views (conversation_id, possession_id, last_viewed_at)
            VALUES (:conversation_id, :possession_id, :now)
            ON CONFLICT(conversation_id, possession_id)
            DO UPDATE SET last_viewed_at = :now
            """,
            {"conversation_id": conversation_id, "possession_id": possession_id, "now": now},
        )

        view = self.get_conversation_view(conversation_id, possession_id)
        return enforce_defined(view, "Failed to update conversation view")

    def get_conversation_view(self, conversation_id: str, possession_id: int) -> ConversationView | None:
        """
        Get conversation view record.

        Args:
            conversation_id: Conversation ID
            possession_id: Possession ID

        Returns:
            ConversationView or None if never viewed
        """
        rows = self.db.execute_query(
            """
            SELECT * FROM conversation_views
            WHERE conversation_id = :conversation_id
            AND possession_id = :possession_id
            """,
            {"conversation_id": conversation_id, "possession_id": possession_id},
        )
        return ConversationView.from_db_row(rows[0]) if rows else None

    def get_unread_conversations(self, possession_id: int) -> list[Conversation]:
        """
        Get conversations with unread messages for a possession.

        A conversation has unread messages if:
        - It has messages
        - The possession has never viewed it, OR
        - The last message is newer than the last view timestamp

        For discussions, properly checks if possession is in scope.

        Args:
            possession_id: Possession ID

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
                AND cv.possession_id = :possession_id
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
                    AND datetime(m2.created_at) > datetime(cv.last_viewed_at)
                )
            )
            AND (
                -- For conversations: possession is a participant
                (c.type = 'conversation' AND (
                    c.participant_1_id = :possession_id 
                    OR c.participant_2_id = :possession_id
                ))
                OR
                -- For discussions: check scope dynamically
                (c.type = 'discussion' AND (
                    -- Role scope
                    (c.scope_type = 'role' AND EXISTS (
                        SELECT 1 FROM possessions p
                        WHERE p.id = :possession_id
                        AND p.role = c.scope_role
                        AND p.status != 'EXORCISED'
                        AND p.start_time <= c.created_at
                    ))
                    OR
                    -- Epic scope
                    (c.scope_type = 'epic' AND EXISTS (
                        SELECT 1 FROM possessions p
                        JOIN tasks t ON t.current_possession_id = p.id
                        WHERE p.id = :possession_id
                        AND t.epic_id = c.scope_epic_id
                        AND p.status != 'EXORCISED'
                        AND p.start_time <= c.created_at
                    ))
                    OR
                    -- All possessions scope
                    (c.scope_type = 'all' AND EXISTS (
                        SELECT 1 FROM possessions p
                        WHERE p.id = :possession_id
                        AND p.status != 'EXORCISED'
                        AND p.start_time <= c.created_at
                    ))
                ))
            )
            ORDER BY c.updated_at DESC
            """,
            {"possession_id": possession_id},
        )
        return [Conversation.from_db_row(row) for row in rows]

    def get_unread_messages(self, conversation_id: str, possession_id: int) -> list[Message]:
        """
        Get unread messages in a conversation for a possession.

        Messages are unread if:
        - Possession has never viewed the conversation, OR
        - Message was created after possession's last_viewed_at timestamp

        Args:
            conversation_id: Conversation ID
            possession_id: Possession ID

        Returns:
            List of unread messages ordered by created_at
        """
        rows = self.db.execute_query(
            """
            SELECT m.*
            FROM messages m
            LEFT JOIN conversation_views cv ON (
                cv.conversation_id = :conversation_id
                AND cv.possession_id = :possession_id
            )
            WHERE m.conversation_id = :conversation_id
            AND (
                cv.last_viewed_at IS NULL
                OR datetime(m.created_at) > datetime(cv.last_viewed_at)
            )
            ORDER BY m.created_at ASC
            """,
            {"conversation_id": conversation_id, "possession_id": possession_id},
        )
        return [Message.from_db_row(row) for row in rows]

    def get_unread_message_count(self, conversation_id: str, possession_id: int) -> int:
        """
        Get count of unread messages in a conversation for a possession.

        Args:
            conversation_id: Conversation ID
            possession_id: Possession ID

        Returns:
            Count of unread messages
        """
        rows = self.db.execute_query(
            """
            SELECT COUNT(*) as count
            FROM messages m
            LEFT JOIN conversation_views cv ON (
                cv.conversation_id = :conversation_id
                AND cv.possession_id = :possession_id
            )
            WHERE m.conversation_id = :conversation_id
            AND (
                cv.last_viewed_at IS NULL
                OR datetime(m.created_at) > datetime(cv.last_viewed_at)
            )
            """,
            {"conversation_id": conversation_id, "possession_id": possession_id},
        )
        return rows[0]["count"] if rows else 0

    def get_conversation_viewers(self, conversation_id: str) -> list[dict]:
        """
        Get list of possessions that have viewed a conversation with their last view times.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of dicts with possession_id, daemon_name, role, and last_viewed_at
        """
        rows = self.db.execute_query(
            """
            SELECT cv.possession_id, cv.last_viewed_at, p.daemon_name, p.role
            FROM conversation_views cv
            JOIN possessions p ON p.id = cv.possession_id
            WHERE cv.conversation_id = :conversation_id
            ORDER BY cv.last_viewed_at DESC
            """,
            {"conversation_id": conversation_id},
        )
        return [
            {
                "possession_id": row["possession_id"],
                "daemon_name": row["daemon_name"],
                "role": row["role"],
                "last_viewed_at": row["last_viewed_at"],
            }
            for row in rows
        ]

    def get_active_conversation_viewers(self, conversation_id: str, within_minutes: int = 5) -> list[dict]:
        """
        Get possessions actively viewing a conversation (viewed within time window).

        Args:
            conversation_id: Conversation ID
            within_minutes: Consider active if viewed within this many minutes (default 5)

        Returns:
            List of dicts with possession_id, daemon_name, role, last_viewed_at
        """
        import pendulum

        cutoff = pendulum.now("UTC").subtract(minutes=within_minutes).to_iso8601_string()

        rows = self.db.execute_query(
            """
            SELECT cv.possession_id, cv.last_viewed_at, p.daemon_name, p.role
            FROM conversation_views cv
            JOIN possessions p ON p.id = cv.possession_id
            WHERE cv.conversation_id = :conversation_id
            AND p.status != 'EXORCISED'
            AND cv.last_viewed_at >= :cutoff
            ORDER BY cv.last_viewed_at DESC
            """,
            {
                "conversation_id": conversation_id,
                "cutoff": cutoff,
            },
        )
        return [
            {
                "possession_id": row["possession_id"],
                "daemon_name": row["daemon_name"],
                "role": row["role"],
                "last_viewed_at": row["last_viewed_at"],
            }
            for row in rows
        ]

    # ============================================================================
    # Message Acknowledgement Tracking
    # ============================================================================

    def acknowledge_message(self, message_id: str, possession_id: int) -> None:
        """
        Acknowledge/mark a message as processed by a possession.

        Args:
            message_id: Message ID to acknowledge
            possession_id: Possession ID acknowledging the message

        Raises:
            MessageNotFoundError: If message not found
        """
        # Verify message exists
        message = self.get_message(message_id)
        enforce_defined(
            message,
            f"Message {message_id} not found",
            raise_exc_class=MessageNotFoundError,
        )

        logger.debug(
            "acknowledging_message",
            message_id=message_id,
            possession_id=possession_id,
        )

        self.db.execute_update(
            """
            INSERT INTO message_acknowledgements (message_id, possession_id, acknowledged_at)
            VALUES (:message_id, :possession_id, :now)
            ON CONFLICT(message_id, possession_id)
            DO UPDATE SET acknowledged_at = :now
            """,
            {"message_id": message_id, "possession_id": possession_id, "now": utc_now()},
        )

    def get_message_acknowledgements(self, message_id: str) -> list[dict]:
        """
        Get all acknowledgements for a message.

        Args:
            message_id: Message ID

        Returns:
            List of dicts with possession_id, daemon_name, role, acknowledged_at
        """
        rows = self.db.execute_query(
            """
            SELECT ma.*, p.daemon_name, p.role
            FROM message_acknowledgements ma
            JOIN possessions p ON p.id = ma.possession_id
            WHERE ma.message_id = :message_id
            ORDER BY ma.acknowledged_at DESC
            """,
            {"message_id": message_id},
        )
        return [
            {
                "possession_id": row["possession_id"],
                "daemon_name": row["daemon_name"],
                "role": row["role"],
                "acknowledged_at": row["acknowledged_at"],
            }
            for row in rows
        ]

    def is_message_acknowledged_by(self, message_id: str, possession_id: int) -> bool:
        """
        Check if a message has been acknowledged by a specific possession.

        Args:
            message_id: Message ID
            possession_id: Possession ID

        Returns:
            True if acknowledged, False otherwise
        """
        rows = self.db.execute_query(
            """
            SELECT 1 FROM message_acknowledgements
            WHERE message_id = :message_id
            AND possession_id = :possession_id
            """,
            {"message_id": message_id, "possession_id": possession_id},
        )
        return len(rows) > 0

    def get_unacknowledged_messages(self, possession_id: int) -> list[Message]:
        """
        Get messages sent to a possession that have not been acknowledged.

        Returns messages in open conversations where:
        - The possession is a recipient (not the sender)
        - The possession has not acknowledged the message

        Args:
            possession_id: Possession ID

        Returns:
            List of unacknowledged messages
        """
        rows = self.db.execute_query(
            """
            SELECT DISTINCT m.*
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.status = 'open'
            AND m.from_possession_id != :possession_id
            AND NOT EXISTS (
                SELECT 1 FROM message_acknowledgements ma
                WHERE ma.message_id = m.id
                AND ma.possession_id = :possession_id
            )
            AND (
                -- For conversations: possession is a participant
                (c.type = 'conversation' AND (
                    c.participant_1_id = :possession_id OR c.participant_2_id = :possession_id
                ))
                OR
                -- For discussions: possession is in scope (check dynamically)
                (c.type = 'discussion' AND (
                    (c.scope_type = 'all') OR
                    (c.scope_type = 'role' AND EXISTS (
                        SELECT 1 FROM possessions pos
                        WHERE pos.id = :possession_id
                        AND pos.role = c.scope_role
                        AND pos.status != 'EXORCISED'
                    )) OR
                    (c.scope_type = 'epic' AND EXISTS (
                        SELECT 1 FROM tasks t
                        WHERE t.epic_id = c.scope_epic_id
                        AND t.current_possession_id = :possession_id
                    ))
                ))
            )
            ORDER BY m.created_at ASC
            """,
            {"possession_id": possession_id},
        )
        return [Message.from_db_row(row) for row in rows]

    # ============================================================================
    # Discussion Participant Computation
    # ============================================================================

    def get_discussion_participants(self, conversation_id: str) -> list[int]:
        """
        Get dynamic participant list for a discussion based on scope.

        Computes who can see a discussion based on its scope configuration:
        - role: All active possessions with matching role
        - epic: All active possessions working on tasks in that epic
        - all: All active possessions

        Args:
            conversation_id: Discussion ID

        Returns:
            List of possession IDs that are participants in this discussion

        Raises:
            ConversationNotFoundError: If conversation not found
            InvalidConversationTypeError: If not a discussion
        """
        conversation = self.get_conversation(conversation_id)
        conversation = enforce_defined(
            conversation,
            f"Conversation {conversation_id} not found",
            raise_exc_class=ConversationNotFoundError,
        )

        require_condition(
            conversation.is_discussion(),
            f"Cannot get participants for conversation type '{conversation.type}'",
            raise_exc_class=InvalidConversationTypeError,
        )

        # Build dynamic query based on scope type
        # Convert pendulum DateTime to string for SQLite
        created_at_str = conversation.created_at.to_iso8601_string()

        if conversation.scope_type == "role":
            rows = self.db.execute_query(
                """
                SELECT id
                FROM possessions
                WHERE status != 'EXORCISED'
                AND role = :role
                AND start_time <= :created_at
                ORDER BY id
                """,
                {"role": conversation.scope_role, "created_at": created_at_str},
            )
        elif conversation.scope_type == "epic":
            rows = self.db.execute_query(
                """
                SELECT DISTINCT p.id
                FROM possessions p
                JOIN tasks t ON t.current_possession_id = p.id
                WHERE p.status != 'EXORCISED'
                AND t.epic_id = :epic_id
                AND p.start_time <= :created_at
                ORDER BY p.id
                """,
                {"epic_id": conversation.scope_epic_id, "created_at": created_at_str},
            )
        else:  # scope_type == "all"
            rows = self.db.execute_query(
                """
                SELECT id
                FROM possessions
                WHERE status != 'EXORCISED'
                AND start_time <= :created_at
                ORDER BY id
                """,
                {"created_at": created_at_str},
            )

        return [row["id"] for row in rows]

    def is_possession_in_discussion_scope(self, conversation_id: str, possession_id: int) -> bool:
        """
        Check if a possession is in the scope of a discussion.

        Args:
            conversation_id: Discussion ID
            possession_id: Possession ID to check

        Returns:
            True if possession is in scope, False otherwise

        Raises:
            ConversationNotFoundError: If conversation not found
            InvalidConversationTypeError: If not a discussion
        """
        participants = self.get_discussion_participants(conversation_id)
        return possession_id in participants

    # ============================================================================
    # High-Level Workflow Methods
    # ============================================================================

    def _extract_subject_from_text(self, text: str, max_length: int = 60) -> str:
        """
        Extract a subject line from message text.

        Takes the first line or first sentence (up to max_length characters).
        Strips markdown formatting and whitespace.

        Args:
            text: Message text to extract subject from
            max_length: Maximum subject length (default 60)

        Returns:
            Extracted subject line
        """
        # Take first line
        first_line = text.split("\n")[0].strip()

        # Remove common markdown formatting
        subject = first_line.replace("#", "").replace("*", "").replace("_", "").strip()

        # Truncate if too long, adding ellipsis
        if len(subject) > max_length:
            subject = subject[: max_length - 3].strip() + "..."

        return subject if subject else "No subject"

    def send_conversation_message(
        self,
        from_possession_id: int,
        to_possession_id: int,
        body: str,
        priority: str = "MEDIUM",
        task_id: str | None = None,
        epic_id: str | None = None,
        artifact_path: str | None = None,
    ) -> tuple[Conversation, Message]:
        """
        Send a message in a 1-on-1 conversation with auto-creation logic.

        This implements the conversation workflow from ADR-008:
        1. Check if open conversation exists between the two possessions
        2. If closed conversation exists, create NEW conversation (fresh start)
        3. If no conversation exists, create new conversation
        4. Extract subject from message text (first line/sentence)
        5. Add message to conversation
        6. Update conversation_views for sender

        Args:
            from_possession_id: Sender possession ID
            to_possession_id: Recipient possession ID
            body: Markdown-formatted message body
            priority: Message priority (CRITICAL, HIGH, MEDIUM, LOW)
            task_id: Optional related task
            epic_id: Optional related epic
            artifact_path: Optional related file/artifact

        Returns:
            Tuple of (conversation, message)

        Raises:
            InvalidParticipantError: If possession IDs are invalid or the same
        """
        require_condition(
            from_possession_id != to_possession_id,
            "Cannot send message to yourself",
            raise_exc_class=InvalidParticipantError,
        )

        # Extract subject from message body
        subject = self._extract_subject_from_text(body)

        logger.debug(
            "sending_conversation_message",
            from_possession_id=from_possession_id,
            to_possession_id=to_possession_id,
            subject=subject,
        )

        # Get or create conversation (handles closed conversation logic)
        conversation = self.get_or_create_conversation(
            participant_1_id=from_possession_id,
            participant_2_id=to_possession_id,
            subject=subject,
            task_id=task_id,
            epic_id=epic_id,
        )

        # Create message in conversation
        message = self.create_message(
            conversation_id=conversation.id,
            from_possession_id=from_possession_id,
            subject=subject,
            body=body,
            priority=priority,
            parent_message_id=None,  # No threading in conversations
            task_id=task_id,
            epic_id=epic_id,
            artifact_path=artifact_path,
        )

        # Update conversation view for sender
        self.update_conversation_view(conversation.id, from_possession_id)

        logger.info(
            "conversation_message_sent",
            conversation_id=conversation.id,
            message_id=message.id,
            from_possession_id=from_possession_id,
            to_possession_id=to_possession_id,
        )

        return conversation, message
