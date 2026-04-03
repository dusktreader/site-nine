"""
Comprehensive tests for the messaging system (TST-H-0090).

Covers gaps not addressed by existing test files:
- Discussion CRUD and scope validation
- Discussion participant computation
- Message CRUD (create, get, list)
- Threading (discussion threading, conversation rejection)
- Conversation CRUD (create, get, list, close, reopen)
- View tracking (upsert, viewers, active viewers)
- Edge cases (closed convos, invalid threading, error paths)
"""

import pytest

from site_nine.core.database import Database
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
from site_nine.messaging.models import Conversation, ConversationView, Message


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr(test_db: Database) -> MessageManager:
    """Create MessageManager with test database."""
    return MessageManager(test_db)


@pytest.fixture
def missions(test_db: Database) -> dict[str, int]:
    """Create test missions with proper personas and roles."""
    test_db.execute_update(
        """
        INSERT INTO daemons (name, role, incarnations)
        VALUES
            ('alpha', 'Operator', 0),
            ('beta', 'Operator', 0),
            ('gamma', 'Architect', 0),
            ('delta', 'Tester', 0)
        """
    )

    ids: dict[str, int] = {}
    for name, role in [("alpha", "Operator"), ("beta", "Operator"), ("gamma", "Architect"), ("delta", "Tester")]:
        mid = test_db.execute_insert(
            """
            INSERT INTO possessions (daemon_name, role, possession_log, start_time, created_at, updated_at)
            VALUES (
                :name, :role, :log, datetime('now'), datetime('now'), datetime('now')
            )
            """,
            {
                "name": name,
                "role": role,
                "log": f".opencode/work/possessions/{name}.md",
            },
        )
        ids[name] = mid

    return ids


@pytest.fixture
def epic(test_db: Database) -> str:
    """Create a test epic and return its ID."""
    test_db.execute_update(
        """
        INSERT INTO epics (id, title, priority, description, file_path)
        VALUES ('EPC-H-0099', 'Test Epic', 'HIGH', 'A test epic', '.opencode/work/epics/EPC-H-0099.md')
        """
    )
    return "EPC-H-0099"


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------


class TestCreateConversation:
    """Tests for MessageManager.create_conversation."""

    def test_create_basic_conversation(self, mgr: MessageManager, missions: dict):
        """Create a conversation and verify all fields are set."""
        conv = mgr.create_conversation(
            subject="Test conversation",
            participant_1_id=missions["alpha"],
            participant_2_id=missions["beta"],
        )

        assert conv.id.startswith("CONV-")
        assert conv.subject == "Test conversation"
        assert conv.type == "conversation"
        assert conv.status == "open"
        assert conv.participant_1_id == missions["alpha"]
        assert conv.participant_2_id == missions["beta"]
        assert conv.scope_type is None
        assert conv.scope_role is None
        assert conv.scope_epic_id is None
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.closed_at is None

    def test_create_conversation_with_task_and_epic_context(
        self, mgr: MessageManager, missions: dict, test_db: Database, epic: str
    ):
        """Create a conversation with optional task and epic context."""
        test_db.execute_update(
            """
            INSERT INTO tasks (id, title, status, priority, role, file_path)
            VALUES ('TST-H-0099', 'Context task', 'TODO', 'HIGH', 'Tester', '.opencode/work/tasks/TST-H-0099.md')
            """
        )

        conv = mgr.create_conversation(
            subject="Context conversation",
            participant_1_id=missions["alpha"],
            participant_2_id=missions["gamma"],
            task_id="TST-H-0099",
            epic_id=epic,
        )

        assert conv.task_id == "TST-H-0099"
        assert conv.epic_id == epic

    def test_create_conversation_same_participants_raises(self, mgr: MessageManager, missions: dict):
        """Cannot create a conversation where both participants are the same."""
        with pytest.raises(InvalidParticipantError):
            mgr.create_conversation(
                subject="Self-talk",
                participant_1_id=missions["alpha"],
                participant_2_id=missions["alpha"],
            )

    def test_conversation_ids_increment(self, mgr: MessageManager, missions: dict):
        """Conversation IDs increment sequentially."""
        conv1 = mgr.create_conversation("First", missions["alpha"], missions["beta"])
        conv2 = mgr.create_conversation("Second", missions["alpha"], missions["gamma"])

        num1 = int(conv1.id.split("-")[1])
        num2 = int(conv2.id.split("-")[1])
        assert num2 == num1 + 1


class TestGetConversation:
    """Tests for MessageManager.get_conversation."""

    def test_get_existing_conversation(self, mgr: MessageManager, missions: dict):
        """Retrieve a conversation by ID."""
        created = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        fetched = mgr.get_conversation(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.subject == "Test"

    def test_get_nonexistent_conversation_returns_none(self, mgr: MessageManager):
        """Return None for a nonexistent conversation ID."""
        assert mgr.get_conversation("CONV-9999") is None


class TestListConversations:
    """Tests for MessageManager.list_conversations."""

    def test_list_all_conversations(self, mgr: MessageManager, missions: dict):
        """List all conversations without filters."""
        mgr.create_conversation("Conv 1", missions["alpha"], missions["beta"])
        mgr.create_conversation("Conv 2", missions["alpha"], missions["gamma"])

        convs = mgr.list_conversations()
        assert len(convs) == 2

    def test_list_filter_by_type(self, mgr: MessageManager, missions: dict):
        """Filter conversations by type."""
        mgr.create_conversation("Conv", missions["alpha"], missions["beta"])
        mgr.create_discussion("Disc", scope_type="all")

        convs = mgr.list_conversations(conversation_type="conversation")
        disc = mgr.list_conversations(conversation_type="discussion")

        assert len(convs) == 1
        assert convs[0].type == "conversation"
        assert len(disc) == 1
        assert disc[0].type == "discussion"

    def test_list_filter_by_status(self, mgr: MessageManager, missions: dict):
        """Filter conversations by status."""
        conv = mgr.create_conversation("Conv", missions["alpha"], missions["beta"])
        mgr.create_conversation("Conv 2", missions["alpha"], missions["gamma"])
        mgr.close_conversation(conv.id)

        open_convs = mgr.list_conversations(status="open")
        closed_convs = mgr.list_conversations(status="closed")

        assert len(open_convs) == 1
        assert len(closed_convs) == 1
        assert closed_convs[0].id == conv.id

    def test_list_filter_by_mission(self, mgr: MessageManager, missions: dict):
        """Filter conversations by participant mission."""
        mgr.create_conversation("A-B", missions["alpha"], missions["beta"])
        mgr.create_conversation("A-G", missions["alpha"], missions["gamma"])
        mgr.create_conversation("B-G", missions["beta"], missions["gamma"])

        alpha_convs = mgr.list_conversations(possession_id=missions["alpha"])
        gamma_convs = mgr.list_conversations(possession_id=missions["gamma"])

        assert len(alpha_convs) == 2
        assert len(gamma_convs) == 2


class TestCloseConversation:
    """Tests for MessageManager.close_conversation."""

    def test_close_open_conversation(self, mgr: MessageManager, missions: dict):
        """Close an open conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        closed = mgr.close_conversation(conv.id)

        assert closed.status == "closed"
        assert closed.closed_at is not None

    def test_close_nonexistent_raises(self, mgr: MessageManager):
        """Closing a nonexistent conversation raises ConversationNotFoundError."""
        with pytest.raises(ConversationNotFoundError):
            mgr.close_conversation("CONV-9999")

    def test_close_already_closed_raises(self, mgr: MessageManager, missions: dict):
        """Closing an already-closed conversation raises ConversationClosedError."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.close_conversation(conv.id)

        with pytest.raises(ConversationClosedError):
            mgr.close_conversation(conv.id)


class TestReopenConversation:
    """Tests for MessageManager.reopen_conversation."""

    def test_reopen_closed_conversation(self, mgr: MessageManager, missions: dict):
        """Reopen a closed conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.close_conversation(conv.id)

        reopened = mgr.reopen_conversation(conv.id)
        assert reopened.status == "open"
        assert reopened.closed_at is None

    def test_reopen_nonexistent_raises(self, mgr: MessageManager):
        """Reopening a nonexistent conversation raises ConversationNotFoundError."""
        with pytest.raises(ConversationNotFoundError):
            mgr.reopen_conversation("CONV-9999")

    def test_reopen_already_open_raises(self, mgr: MessageManager, missions: dict):
        """Reopening an already-open conversation raises MessagingError."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])

        with pytest.raises(MessagingError):
            mgr.reopen_conversation(conv.id)


# ---------------------------------------------------------------------------
# Discussion CRUD and Scope Validation
# ---------------------------------------------------------------------------


class TestCreateDiscussion:
    """Tests for MessageManager.create_discussion."""

    def test_create_role_scoped_discussion(self, mgr: MessageManager):
        """Create a role-scoped discussion."""
        disc = mgr.create_discussion(
            subject="Operator chat",
            scope_type="role",
            scope_role="Operator",
        )

        assert disc.id.startswith("CONV-")
        assert disc.type == "discussion"
        assert disc.status == "open"
        assert disc.scope_type == "role"
        assert disc.scope_role == "Operator"
        assert disc.participant_1_id is None
        assert disc.participant_2_id is None

    def test_create_epic_scoped_discussion(self, mgr: MessageManager, epic: str):
        """Create an epic-scoped discussion."""
        disc = mgr.create_discussion(
            subject="Epic discussion",
            scope_type="epic",
            scope_epic_id=epic,
        )

        assert disc.scope_type == "epic"
        assert disc.scope_epic_id == epic

    def test_create_all_scoped_discussion(self, mgr: MessageManager):
        """Create an all-missions-scoped discussion."""
        disc = mgr.create_discussion(
            subject="All hands",
            scope_type="all",
        )

        assert disc.scope_type == "all"

    def test_role_scope_without_role_raises(self, mgr: MessageManager):
        """Role scope without scope_role raises InvalidScopeError."""
        with pytest.raises(InvalidScopeError):
            mgr.create_discussion(
                subject="No role",
                scope_type="role",
                scope_role=None,
            )

    def test_role_scope_with_invalid_role_raises(self, mgr: MessageManager):
        """Role scope with invalid role name raises InvalidScopeError."""
        with pytest.raises(InvalidScopeError):
            mgr.create_discussion(
                subject="Bad role",
                scope_type="role",
                scope_role="InvalidRoleName",
            )

    def test_epic_scope_without_epic_raises(self, mgr: MessageManager):
        """Epic scope without scope_epic_id raises InvalidScopeError."""
        with pytest.raises(InvalidScopeError):
            mgr.create_discussion(
                subject="No epic",
                scope_type="epic",
                scope_epic_id=None,
            )

    def test_invalid_scope_type_raises(self, mgr: MessageManager):
        """Invalid scope_type raises InvalidScopeError."""
        with pytest.raises(InvalidScopeError):
            mgr.create_discussion(
                subject="Bad scope",
                scope_type="invalid",
            )

    def test_discussion_with_task_and_epic_context(self, mgr: MessageManager, test_db: Database, epic: str):
        """Discussion can include task and epic context."""
        test_db.execute_update(
            """
            INSERT INTO tasks (id, title, status, priority, role, file_path)
            VALUES ('TST-H-0098', 'Discussion task', 'TODO', 'HIGH', 'Tester', '.opencode/work/tasks/TST-H-0098.md')
            """
        )

        disc = mgr.create_discussion(
            subject="Task discussion",
            scope_type="all",
            task_id="TST-H-0098",
            epic_id=epic,
        )

        assert disc.task_id == "TST-H-0098"
        assert disc.epic_id == epic


# ---------------------------------------------------------------------------
# Discussion Participant Computation
# ---------------------------------------------------------------------------


class TestDiscussionParticipants:
    """Tests for MessageManager.get_discussion_participants and is_mission_in_discussion_scope."""

    def test_role_scope_returns_matching_missions(self, mgr: MessageManager, missions: dict):
        """Role-scoped discussion returns missions with matching role."""
        disc = mgr.create_discussion("Operator chat", scope_type="role", scope_role="Operator")
        participants = mgr.get_discussion_participants(disc.id)

        # alpha and beta are Operators
        assert missions["alpha"] in participants
        assert missions["beta"] in participants
        # gamma is Architect, delta is Tester
        assert missions["gamma"] not in participants
        assert missions["delta"] not in participants

    def test_epic_scope_returns_missions_with_tasks(
        self, mgr: MessageManager, missions: dict, test_db: Database, epic: str
    ):
        """Epic-scoped discussion returns missions that have tasks in that epic."""
        # Create a task in the epic assigned to alpha's mission
        test_db.execute_update(
            """
            INSERT INTO tasks (id, title, status, priority, role, file_path, epic_id, current_possession_id)
            VALUES ('OPR-H-0098', 'Epic task', 'UNDERWAY', 'HIGH', 'Operator',
                    '.opencode/work/tasks/OPR-H-0098.md', :epic, :mission)
            """,
            {"epic": epic, "mission": missions["alpha"]},
        )

        disc = mgr.create_discussion("Epic discussion", scope_type="epic", scope_epic_id=epic)
        participants = mgr.get_discussion_participants(disc.id)

        assert missions["alpha"] in participants
        assert missions["beta"] not in participants

    def test_all_scope_returns_all_active_missions(self, mgr: MessageManager, missions: dict):
        """All-scoped discussion returns all active missions."""
        disc = mgr.create_discussion("All hands", scope_type="all")
        participants = mgr.get_discussion_participants(disc.id)

        for mid in missions.values():
            assert mid in participants

    def test_ended_mission_excluded_from_scope(self, mgr: MessageManager, missions: dict, test_db: Database):
        """Ended missions are excluded from discussion scope."""
        # Exorcise alpha's possession
        test_db.execute_update(
            "UPDATE possessions SET status = 'EXORCISED' WHERE id = :id",
            {"id": missions["alpha"]},
        )

        disc = mgr.create_discussion("All hands", scope_type="all")
        participants = mgr.get_discussion_participants(disc.id)

        assert missions["alpha"] not in participants
        assert missions["beta"] in participants

    def test_is_mission_in_discussion_scope_true(self, mgr: MessageManager, missions: dict):
        """is_mission_in_discussion_scope returns True for in-scope mission."""
        disc = mgr.create_discussion("Operator chat", scope_type="role", scope_role="Operator")
        assert mgr.is_possession_in_discussion_scope(disc.id, missions["alpha"]) is True

    def test_is_mission_in_discussion_scope_false(self, mgr: MessageManager, missions: dict):
        """is_possession_in_discussion_scope returns False for out-of-scope mission."""
        disc = mgr.create_discussion("Operator chat", scope_type="role", scope_role="Operator")
        assert mgr.is_possession_in_discussion_scope(disc.id, missions["gamma"]) is False

    def test_participants_for_conversation_raises(self, mgr: MessageManager, missions: dict):
        """Getting participants for a 1-on-1 conversation raises InvalidConversationTypeError."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])

        with pytest.raises(InvalidConversationTypeError):
            mgr.get_discussion_participants(conv.id)

    def test_participants_for_nonexistent_raises(self, mgr: MessageManager):
        """Getting participants for a nonexistent conversation raises ConversationNotFoundError."""
        with pytest.raises(ConversationNotFoundError):
            mgr.get_discussion_participants("CONV-9999")


# ---------------------------------------------------------------------------
# Message CRUD
# ---------------------------------------------------------------------------


class TestCreateMessage:
    """Tests for MessageManager.create_message."""

    def test_create_message_in_conversation(self, mgr: MessageManager, missions: dict):
        """Create a message in a conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        msg = mgr.create_message(
            conversation_id=conv.id,
            from_possession_id=missions["alpha"],
            subject="Hello",
            body="Hello, world!",
            priority="MEDIUM",
        )

        assert msg.id.startswith("MSG-M-")
        assert msg.conversation_id == conv.id
        assert msg.from_possession_id == missions["alpha"]
        assert msg.subject == "Hello"
        assert msg.body == "Hello, world!"
        assert msg.priority == "MEDIUM"
        assert msg.parent_message_id is None
        assert msg.thread_root_id is None
        assert msg.created_at is not None

    def test_create_message_with_different_priorities(self, mgr: MessageManager, missions: dict):
        """Messages get correct priority codes in their IDs."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])

        for priority, code in [("CRITICAL", "C"), ("HIGH", "H"), ("MEDIUM", "M"), ("LOW", "L")]:
            msg = mgr.create_message(
                conversation_id=conv.id,
                from_possession_id=missions["alpha"],
                subject=f"{priority} message",
                body=f"Body for {priority}",
                priority=priority,
            )
            assert f"MSG-{code}-" in msg.id

    def test_create_message_with_optional_fields(
        self, mgr: MessageManager, missions: dict, test_db: Database, epic: str
    ):
        """Message can include task, epic, and artifact context."""
        test_db.execute_update(
            """
            INSERT INTO tasks (id, title, status, priority, role, file_path)
            VALUES ('TST-H-0097', 'Msg task', 'TODO', 'HIGH', 'Tester', '.opencode/work/tasks/TST-H-0097.md')
            """
        )

        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        msg = mgr.create_message(
            conversation_id=conv.id,
            from_possession_id=missions["alpha"],
            subject="With context",
            body="Context body",
            task_id="TST-H-0097",
            epic_id=epic,
            artifact_path="src/site_nine/messaging/manager.py",
        )

        assert msg.task_id == "TST-H-0097"
        assert msg.epic_id == epic
        assert msg.artifact_path == "src/site_nine/messaging/manager.py"

    def test_create_message_in_closed_conversation_raises(self, mgr: MessageManager, missions: dict):
        """Cannot create a message in a closed conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.close_conversation(conv.id)

        with pytest.raises(ConversationClosedError):
            mgr.create_message(
                conversation_id=conv.id,
                from_possession_id=missions["alpha"],
                subject="Too late",
                body="Too late body",
            )

    def test_create_message_in_nonexistent_conversation_raises(self, mgr: MessageManager, missions: dict):
        """Cannot create a message in a nonexistent conversation."""
        with pytest.raises(ConversationNotFoundError):
            mgr.create_message(
                conversation_id="CONV-9999",
                from_possession_id=missions["alpha"],
                subject="Nowhere",
                body="Nowhere body",
            )

    def test_message_ids_increment_globally(self, mgr: MessageManager, missions: dict):
        """Message IDs increment globally across all priorities."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        msg1 = mgr.create_message(conv.id, missions["alpha"], "S1", "B1", priority="HIGH")
        msg2 = mgr.create_message(conv.id, missions["alpha"], "S2", "B2", priority="LOW")

        # Extract number portion
        num1 = int(msg1.id.split("-")[2])
        num2 = int(msg2.id.split("-")[2])
        assert num2 == num1 + 1


class TestGetMessage:
    """Tests for MessageManager.get_message."""

    def test_get_existing_message(self, mgr: MessageManager, missions: dict):
        """Retrieve a message by ID."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        created = mgr.create_message(conv.id, missions["alpha"], "Hello", "Body")
        fetched = mgr.get_message(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.subject == "Hello"

    def test_get_nonexistent_message_returns_none(self, mgr: MessageManager):
        """Return None for a nonexistent message ID."""
        assert mgr.get_message("MSG-M-9999") is None


class TestListMessages:
    """Tests for MessageManager.list_messages."""

    def test_list_messages_in_conversation(self, mgr: MessageManager, missions: dict):
        """List all messages in a specific conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.create_message(conv.id, missions["alpha"], "S1", "B1")
        mgr.create_message(conv.id, missions["beta"], "S2", "B2")

        msgs = mgr.list_messages(conversation_id=conv.id)
        assert len(msgs) == 2

    def test_list_messages_filter_by_sender(self, mgr: MessageManager, missions: dict):
        """Filter messages by sender mission."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.create_message(conv.id, missions["alpha"], "From alpha", "B1")
        mgr.create_message(conv.id, missions["beta"], "From beta", "B2")

        alpha_msgs = mgr.list_messages(from_possession_id=missions["alpha"])
        assert len(alpha_msgs) == 1
        assert alpha_msgs[0].subject == "From alpha"

    def test_list_messages_filter_by_priority(self, mgr: MessageManager, missions: dict):
        """Filter messages by priority level."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.create_message(conv.id, missions["alpha"], "Critical", "B", priority="CRITICAL")
        mgr.create_message(conv.id, missions["alpha"], "Low", "B", priority="LOW")

        critical = mgr.list_messages(priority="CRITICAL")
        assert len(critical) == 1
        assert critical[0].subject == "Critical"

    def test_list_messages_ordered_chronologically(self, mgr: MessageManager, missions: dict):
        """Messages are returned in chronological order."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        msg1 = mgr.create_message(conv.id, missions["alpha"], "First", "B1")
        msg2 = mgr.create_message(conv.id, missions["alpha"], "Second", "B2")
        msg3 = mgr.create_message(conv.id, missions["alpha"], "Third", "B3")

        msgs = mgr.list_messages(conversation_id=conv.id)
        assert [m.id for m in msgs] == [msg1.id, msg2.id, msg3.id]

    def test_list_messages_empty(self, mgr: MessageManager):
        """Listing messages with no matches returns empty list."""
        msgs = mgr.list_messages(conversation_id="CONV-9999")
        assert msgs == []


# ---------------------------------------------------------------------------
# Threading
# ---------------------------------------------------------------------------


class TestThreading:
    """Tests for message threading in discussions."""

    def test_threaded_reply_in_discussion(self, mgr: MessageManager, missions: dict):
        """Create a threaded reply in a discussion."""
        disc = mgr.create_discussion("Discussion", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Root body")

        reply = mgr.create_message(
            conversation_id=disc.id,
            from_possession_id=missions["beta"],
            subject="Reply",
            body="Reply body",
            parent_message_id=root.id,
        )

        assert reply.parent_message_id == root.id
        assert reply.thread_root_id == root.id

    def test_nested_reply_uses_original_root(self, mgr: MessageManager, missions: dict):
        """Replying to a reply sets thread_root_id to the original root."""
        disc = mgr.create_discussion("Discussion", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Root body")
        reply1 = mgr.create_message(
            disc.id,
            missions["beta"],
            "Reply 1",
            "Reply 1 body",
            parent_message_id=root.id,
        )
        reply2 = mgr.create_message(
            disc.id,
            missions["gamma"],
            "Reply 2",
            "Reply 2 body",
            parent_message_id=reply1.id,
        )

        assert reply2.parent_message_id == reply1.id
        assert reply2.thread_root_id == root.id

    def test_threading_rejected_in_conversation(self, mgr: MessageManager, missions: dict):
        """Threading is not allowed in 1-on-1 conversations."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        root = mgr.create_message(conv.id, missions["alpha"], "Root", "Root body")

        with pytest.raises(InvalidThreadingError):
            mgr.create_message(
                conversation_id=conv.id,
                from_possession_id=missions["beta"],
                subject="Reply",
                body="Reply body",
                parent_message_id=root.id,
            )

    def test_threading_with_nonexistent_parent_raises(self, mgr: MessageManager, missions: dict):
        """Threading with a nonexistent parent message raises error."""
        disc = mgr.create_discussion("Discussion", scope_type="all")

        with pytest.raises(MessageNotFoundError):
            mgr.create_message(
                conversation_id=disc.id,
                from_possession_id=missions["alpha"],
                subject="Reply",
                body="Reply body",
                parent_message_id="MSG-M-9999",
            )

    def test_threading_parent_in_wrong_conversation_raises(self, mgr: MessageManager, missions: dict):
        """Threading with a parent from a different conversation raises error."""
        disc1 = mgr.create_discussion("Discussion 1", scope_type="all")
        disc2 = mgr.create_discussion("Discussion 2", scope_type="all")

        root = mgr.create_message(disc1.id, missions["alpha"], "Root", "Root body")

        with pytest.raises(InvalidThreadingError):
            mgr.create_message(
                conversation_id=disc2.id,
                from_possession_id=missions["alpha"],
                subject="Reply",
                body="Reply body",
                parent_message_id=root.id,
            )


class TestGetMessageThread:
    """Tests for MessageManager.get_message_thread."""

    def test_get_thread_returns_root_and_replies(self, mgr: MessageManager, missions: dict):
        """get_message_thread returns root message followed by all replies."""
        disc = mgr.create_discussion("Discussion", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Root body")
        reply1 = mgr.create_message(
            disc.id,
            missions["beta"],
            "Reply 1",
            "Reply 1 body",
            parent_message_id=root.id,
        )
        reply2 = mgr.create_message(
            disc.id,
            missions["gamma"],
            "Reply 2",
            "Reply 2 body",
            parent_message_id=root.id,
        )

        thread = mgr.get_message_thread(root.id)
        assert len(thread) == 3
        assert thread[0].id == root.id
        assert thread[1].id == reply1.id
        assert thread[2].id == reply2.id

    def test_get_thread_for_nonexistent_root_returns_empty(self, mgr: MessageManager):
        """get_message_thread returns empty list for nonexistent root."""
        assert mgr.get_message_thread("MSG-M-9999") == []

    def test_get_thread_for_root_only_returns_single(self, mgr: MessageManager, missions: dict):
        """Thread with no replies returns just the root message."""
        disc = mgr.create_discussion("Discussion", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Root body")

        thread = mgr.get_message_thread(root.id)
        assert len(thread) == 1
        assert thread[0].id == root.id

    def test_nested_replies_in_thread(self, mgr: MessageManager, missions: dict):
        """Nested replies are all returned under the same thread root."""
        disc = mgr.create_discussion("Discussion", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Root body")
        reply1 = mgr.create_message(
            disc.id,
            missions["beta"],
            "Reply 1",
            "Reply 1 body",
            parent_message_id=root.id,
        )
        # Reply to reply1 (nested) - thread_root_id should still be root
        reply2 = mgr.create_message(
            disc.id,
            missions["gamma"],
            "Reply 2",
            "Reply 2 body",
            parent_message_id=reply1.id,
        )

        thread = mgr.get_message_thread(root.id)
        assert len(thread) == 3
        # All should share the same thread root
        for msg in thread[1:]:
            assert msg.thread_root_id == root.id


# ---------------------------------------------------------------------------
# View Tracking
# ---------------------------------------------------------------------------


class TestViewTracking:
    """Tests for conversation view tracking operations."""

    def test_update_view_creates_record(self, mgr: MessageManager, missions: dict):
        """Updating a view creates a new record if none exists."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        view = mgr.update_conversation_view(conv.id, missions["alpha"])

        assert view.conversation_id == conv.id
        assert view.possession_id == missions["alpha"]
        assert view.last_viewed_at is not None

    def test_update_view_upserts_timestamp(self, mgr: MessageManager, missions: dict):
        """Updating a view overwrites the previous timestamp."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        view1 = mgr.update_conversation_view(conv.id, missions["alpha"])

        # Small delay is unnecessary - the upsert itself is the test
        view2 = mgr.update_conversation_view(conv.id, missions["alpha"])

        assert view2.conversation_id == view1.conversation_id
        assert view2.possession_id == view1.possession_id
        # Timestamp should be >= previous (may be equal if fast)
        assert view2.last_viewed_at >= view1.last_viewed_at

    def test_get_view_returns_none_when_never_viewed(self, mgr: MessageManager, missions: dict):
        """get_conversation_view returns None if mission never viewed the conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        assert mgr.get_conversation_view(conv.id, missions["alpha"]) is None

    def test_get_conversation_viewers(self, mgr: MessageManager, missions: dict):
        """get_conversation_viewers returns all missions that have viewed."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.update_conversation_view(conv.id, missions["alpha"])
        mgr.update_conversation_view(conv.id, missions["beta"])

        viewers = mgr.get_conversation_viewers(conv.id)
        assert len(viewers) == 2
        viewer_ids = {v["possession_id"] for v in viewers}
        assert missions["alpha"] in viewer_ids
        assert missions["beta"] in viewer_ids
        # Verify viewer dict has expected keys
        for v in viewers:
            assert "daemon_name" in v
            assert "role" in v
            assert "last_viewed_at" in v

    def test_get_conversation_viewers_empty(self, mgr: MessageManager, missions: dict):
        """get_conversation_viewers returns empty list when no one has viewed."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        viewers = mgr.get_conversation_viewers(conv.id)
        assert viewers == []

    def test_get_active_viewers(self, mgr: MessageManager, missions: dict):
        """get_active_conversation_viewers returns missions that recently viewed."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        # View right now - should be active
        mgr.update_conversation_view(conv.id, missions["alpha"])

        active = mgr.get_active_conversation_viewers(conv.id, within_minutes=5)
        assert len(active) == 1
        assert active[0]["possession_id"] == missions["alpha"]

    def test_get_active_viewers_excludes_ended_missions(self, mgr: MessageManager, missions: dict, test_db: Database):
        """get_active_conversation_viewers excludes ended missions."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.update_conversation_view(conv.id, missions["alpha"])
        mgr.update_conversation_view(conv.id, missions["beta"])

        # Exorcise alpha's possession
        test_db.execute_update(
            "UPDATE possessions SET status = 'EXORCISED' WHERE id = :id",
            {"id": missions["alpha"]},
        )

        active = mgr.get_active_conversation_viewers(conv.id, within_minutes=5)
        active_ids = {v["possession_id"] for v in active}
        assert missions["alpha"] not in active_ids
        assert missions["beta"] in active_ids


# ---------------------------------------------------------------------------
# Unread Messages and Conversations (extending existing coverage)
# ---------------------------------------------------------------------------


class TestUnreadConversationsDiscussions:
    """Tests for get_unread_conversations with discussions."""

    def test_unread_discussion_for_in_scope_mission(self, mgr: MessageManager, missions: dict):
        """Discussion with unread messages shows for in-scope mission."""
        disc = mgr.create_discussion("Operator chat", scope_type="role", scope_role="Operator")
        mgr.create_message(disc.id, missions["alpha"], "Hello", "Hello body")

        # Beta is also an Operator, should see unread
        convs = mgr.get_unread_conversations(missions["beta"])
        assert len(convs) == 1
        assert convs[0].id == disc.id

    def test_unread_discussion_hidden_for_out_of_scope_mission(self, mgr: MessageManager, missions: dict):
        """Discussion with unread messages hidden for out-of-scope mission."""
        disc = mgr.create_discussion("Operator chat", scope_type="role", scope_role="Operator")
        mgr.create_message(disc.id, missions["alpha"], "Hello", "Hello body")

        # Gamma is Architect, should NOT see Operator discussion
        convs = mgr.get_unread_conversations(missions["gamma"])
        assert len(convs) == 0

    def test_unread_all_scope_discussion(self, mgr: MessageManager, missions: dict):
        """All-scope discussion shows for all active missions."""
        disc = mgr.create_discussion("All hands", scope_type="all")
        mgr.create_message(disc.id, missions["alpha"], "Announcement", "Body")

        for name, mid in missions.items():
            if name == "alpha":
                continue  # Sender - view was not auto-updated by create_message alone
            convs = mgr.get_unread_conversations(mid)
            conv_ids = [c.id for c in convs]
            assert disc.id in conv_ids, f"Mission {name} should see all-scope discussion"

    def test_closed_conversation_not_in_unread(self, mgr: MessageManager, missions: dict):
        """Closed conversations do not appear in unread list."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.create_message(conv.id, missions["alpha"], "Hello", "Body")
        mgr.close_conversation(conv.id)

        convs = mgr.get_unread_conversations(missions["beta"])
        assert len(convs) == 0


class TestUnreadMessageCount:
    """Tests for get_unread_message_count."""

    def test_count_matches_messages(self, mgr: MessageManager, missions: dict):
        """Unread count matches the number of unread messages returned."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.create_message(conv.id, missions["alpha"], "S1", "B1")
        mgr.create_message(conv.id, missions["alpha"], "S2", "B2")

        count = mgr.get_unread_message_count(conv.id, missions["beta"])
        messages = mgr.get_unread_messages(conv.id, missions["beta"])

        assert count == len(messages)
        assert count == 2

    def test_count_zero_after_viewing(self, mgr: MessageManager, missions: dict):
        """Unread count is zero after viewing the conversation."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.create_message(conv.id, missions["alpha"], "Hello", "Body")
        mgr.update_conversation_view(conv.id, missions["beta"])

        assert mgr.get_unread_message_count(conv.id, missions["beta"]) == 0

    def test_count_for_empty_conversation(self, mgr: MessageManager, missions: dict):
        """Unread count is zero for conversation with no messages."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        assert mgr.get_unread_message_count(conv.id, missions["beta"]) == 0


# ---------------------------------------------------------------------------
# Model methods
# ---------------------------------------------------------------------------


class TestConversationModel:
    """Tests for Conversation model methods."""

    def test_is_conversation(self, mgr: MessageManager, missions: dict):
        """is_conversation returns True for 1-on-1 conversations."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        assert conv.is_conversation() is True
        assert conv.is_discussion() is False

    def test_is_discussion(self, mgr: MessageManager):
        """is_discussion returns True for discussions."""
        disc = mgr.create_discussion("Disc", scope_type="all")
        assert disc.is_discussion() is True
        assert disc.is_conversation() is False

    def test_is_participant_for_conversation(self, mgr: MessageManager, missions: dict):
        """is_participant works for 1-on-1 conversations."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        assert conv.is_participant(missions["alpha"]) is True
        assert conv.is_participant(missions["beta"]) is True
        assert conv.is_participant(missions["gamma"]) is False

    def test_is_participant_for_discussion_returns_false(self, mgr: MessageManager, missions: dict):
        """is_participant always returns False for discussions (uses dynamic scoping)."""
        disc = mgr.create_discussion("Disc", scope_type="all")
        assert disc.is_participant(missions["alpha"]) is False


class TestMessageModel:
    """Tests for Message model methods."""

    def test_is_root_message(self, mgr: MessageManager, missions: dict):
        """is_root_message for root and non-root messages."""
        disc = mgr.create_discussion("Disc", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Body")
        reply = mgr.create_message(
            disc.id,
            missions["beta"],
            "Reply",
            "Reply body",
            parent_message_id=root.id,
        )

        assert root.is_root_message() is True
        assert reply.is_root_message() is False

    def test_is_threaded_reply(self, mgr: MessageManager, missions: dict):
        """is_threaded_reply for root and reply messages."""
        disc = mgr.create_discussion("Disc", scope_type="all")
        root = mgr.create_message(disc.id, missions["alpha"], "Root", "Body")
        reply = mgr.create_message(
            disc.id,
            missions["beta"],
            "Reply",
            "Reply body",
            parent_message_id=root.id,
        )

        assert root.is_threaded_reply() is False
        assert reply.is_threaded_reply() is True


# ---------------------------------------------------------------------------
# Edge Cases and Error Paths
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and error path tests."""

    def test_send_conversation_message_to_closed_creates_new(self, mgr: MessageManager, missions: dict):
        """Sending via send_conversation_message after close creates a new conversation."""
        conv1, _ = mgr.send_conversation_message(
            from_possession_id=missions["alpha"],
            to_possession_id=missions["beta"],
            body="First conversation",
        )
        mgr.close_conversation(conv1.id)

        conv2, msg2 = mgr.send_conversation_message(
            from_possession_id=missions["alpha"],
            to_possession_id=missions["beta"],
            body="New conversation after close",
        )

        assert conv2.id != conv1.id
        assert conv2.status == "open"
        assert msg2.conversation_id == conv2.id

    def test_send_conversation_message_updates_sender_view(self, mgr: MessageManager, missions: dict):
        """send_conversation_message updates the sender's view timestamp."""
        conv, msg = mgr.send_conversation_message(
            from_possession_id=missions["alpha"],
            to_possession_id=missions["beta"],
            body="Test message",
        )

        view = mgr.get_conversation_view(conv.id, missions["alpha"])
        assert view is not None
        assert view.last_viewed_at >= msg.created_at

    def test_multiple_conversations_between_different_pairs(self, mgr: MessageManager, missions: dict):
        """Each pair of missions gets their own conversation."""
        conv_ab, _ = mgr.send_conversation_message(missions["alpha"], missions["beta"], body="A to B")
        conv_ag, _ = mgr.send_conversation_message(missions["alpha"], missions["gamma"], body="A to G")
        conv_bg, _ = mgr.send_conversation_message(missions["beta"], missions["gamma"], body="B to G")

        assert conv_ab.id != conv_ag.id
        assert conv_ab.id != conv_bg.id
        assert conv_ag.id != conv_bg.id

    def test_conversation_reuse_normalizes_participant_order(self, mgr: MessageManager, missions: dict):
        """Conversation lookup normalizes participant order (lower ID first)."""
        conv1, _ = mgr.send_conversation_message(
            from_possession_id=missions["beta"],
            to_possession_id=missions["alpha"],
            body="B to A",
        )
        conv2, _ = mgr.send_conversation_message(
            from_possession_id=missions["alpha"],
            to_possession_id=missions["beta"],
            body="A to B",
        )

        assert conv1.id == conv2.id

    def test_close_and_reopen_cycle(self, mgr: MessageManager, missions: dict):
        """Close then reopen a conversation, then send messages again."""
        conv = mgr.create_conversation("Test", missions["alpha"], missions["beta"])
        mgr.close_conversation(conv.id)
        reopened = mgr.reopen_conversation(conv.id)

        assert reopened.status == "open"

        # Can send messages again
        msg = mgr.create_message(
            reopened.id,
            missions["alpha"],
            "After reopen",
            "Body",
        )
        assert msg.conversation_id == reopened.id

    def test_discussion_close_and_reopen(self, mgr: MessageManager, missions: dict):
        """Close and reopen a discussion."""
        disc = mgr.create_discussion("Discussion", scope_type="all")
        closed = mgr.close_conversation(disc.id)
        assert closed.status == "closed"

        reopened = mgr.reopen_conversation(disc.id)
        assert reopened.status == "open"

    def test_send_conversation_message_with_priority(self, mgr: MessageManager, missions: dict):
        """send_conversation_message respects the priority parameter."""
        _, msg = mgr.send_conversation_message(
            from_possession_id=missions["alpha"],
            to_possession_id=missions["beta"],
            body="Urgent!",
            priority="CRITICAL",
        )

        assert msg.priority == "CRITICAL"
        assert "MSG-C-" in msg.id

    def test_unread_messages_exclude_sender_own_messages(self, mgr: MessageManager, missions: dict):
        """Sender's own messages are not counted as unread for themselves (via view tracking)."""
        conv, msg = mgr.send_conversation_message(
            from_possession_id=missions["alpha"],
            to_possession_id=missions["beta"],
            body="Hello",
        )

        # Sender has a view timestamp set by send_conversation_message
        unread = mgr.get_unread_messages(conv.id, missions["alpha"])
        assert len(unread) == 0

    def test_discussion_messages_from_multiple_senders(self, mgr: MessageManager, missions: dict):
        """Discussion with messages from multiple senders tracks correctly."""
        disc = mgr.create_discussion("All hands", scope_type="role", scope_role="Operator")

        # Both Operators send messages
        msg1 = mgr.create_message(disc.id, missions["alpha"], "From alpha", "Body 1")
        msg2 = mgr.create_message(disc.id, missions["beta"], "From beta", "Body 2")

        msgs = mgr.list_messages(conversation_id=disc.id)
        assert len(msgs) == 2
        senders = {m.from_possession_id for m in msgs}
        assert senders == {missions["alpha"], missions["beta"]}
