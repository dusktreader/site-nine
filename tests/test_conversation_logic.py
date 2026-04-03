"""
Tests for conversation logic (1-on-1 messaging with auto-creation).

Tests cover:
- Auto-creation of conversations on first message
- Prevention of duplicate conversations
- Subject extraction from message text
- Closed conversation handling (create new)
- Conversation view tracking
"""

import pytest

from site_nine.core.database import Database
from site_nine.messaging.exceptions import InvalidParticipantError
from site_nine.messaging.manager import MessageManager


@pytest.fixture
def message_manager(test_db: Database) -> MessageManager:
    """Create MessageManager with test database."""
    return MessageManager(test_db)


@pytest.fixture
def test_missions(test_db: Database) -> dict[str, int]:
    """Create test possessions for conversation testing."""
    # Seed daemons first
    test_db.execute_update(
        """
        INSERT INTO daemons (name, role, incarnations)
        VALUES 
            ('test-persona-1', 'Operator', 0),
            ('test-persona-2', 'Engineer', 0),
            ('test-persona-3', 'Architect', 0)
        """
    )

    # Create test possessions
    mission_1_id = test_db.execute_insert(
        """
        INSERT INTO possessions (daemon_name, role, possession_log, created_at, updated_at)
        VALUES (
            'test-persona-1', 'Operator',
            '.opencode/work/possessions/test-1.md',
            datetime('now'), datetime('now')
        )
        """
    )

    mission_2_id = test_db.execute_insert(
        """
        INSERT INTO possessions (daemon_name, role, possession_log, created_at, updated_at)
        VALUES (
            'test-persona-2', 'Engineer',
            '.opencode/work/possessions/test-2.md',
            datetime('now'), datetime('now')
        )
        """
    )

    mission_3_id = test_db.execute_insert(
        """
        INSERT INTO possessions (daemon_name, role, possession_log, created_at, updated_at)
        VALUES (
            'test-persona-3', 'Architect',
            '.opencode/work/possessions/test-3.md',
            datetime('now'), datetime('now')
        )
        """
    )

    return {
        "mission_1": mission_1_id,
        "mission_2": mission_2_id,
        "mission_3": mission_3_id,
    }


class TestSubjectExtraction:
    """Tests for _extract_subject_from_text helper."""

    def test_extract_subject_from_simple_text(self, message_manager: MessageManager):
        """Test subject extraction from simple text."""
        text = "Quick question about task ARC-H-0057"
        subject = message_manager._extract_subject_from_text(text)
        assert subject == "Quick question about task ARC-H-0057"

    def test_extract_subject_from_multiline(self, message_manager: MessageManager):
        """Test subject extraction takes only first line."""
        text = "First line here\nSecond line\nThird line"
        subject = message_manager._extract_subject_from_text(text)
        assert subject == "First line here"

    def test_extract_subject_removes_markdown(self, message_manager: MessageManager):
        """Test markdown formatting is removed from subject."""
        text = "## Heading with **bold** and *italic* text"
        subject = message_manager._extract_subject_from_text(text)
        assert subject == "Heading with bold and italic text"

    def test_extract_subject_truncates_long_text(self, message_manager: MessageManager):
        """Test long subjects are truncated with ellipsis."""
        text = "This is a very long message that exceeds the maximum length and should be truncated"
        subject = message_manager._extract_subject_from_text(text, max_length=30)
        assert len(subject) == 30
        assert subject.endswith("...")

    def test_extract_subject_from_empty_text(self, message_manager: MessageManager):
        """Test empty text returns default subject."""
        subject = message_manager._extract_subject_from_text("")
        assert subject == "No subject"

    def test_extract_subject_from_whitespace(self, message_manager: MessageManager):
        """Test whitespace-only text returns default subject."""
        subject = message_manager._extract_subject_from_text("   \n\n  ")
        assert subject == "No subject"


class TestConversationAutoCreation:
    """Tests for conversation auto-creation logic."""

    def test_auto_create_conversation_on_first_message(self, message_manager: MessageManager, test_missions: dict):
        """Test conversation is auto-created when sending first message."""
        conversation, message = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Hey, can you help with this task?",
        )

        # Verify conversation created
        assert conversation is not None
        assert conversation.type == "conversation"
        assert conversation.status == "open"
        assert conversation.subject == "Hey, can you help with this task?"

        # Verify participants (normalized order)
        assert {conversation.participant_1_id, conversation.participant_2_id} == {
            test_missions["mission_1"],
            test_missions["mission_2"],
        }

        # Verify message created
        assert message is not None
        assert message.conversation_id == conversation.id
        assert message.from_possession_id == test_missions["mission_1"]
        assert message.body == "Hey, can you help with this task?"
        assert message.parent_message_id is None  # No threading in conversations

    def test_reuse_existing_conversation(self, message_manager: MessageManager, test_missions: dict):
        """Test existing open conversation is reused for subsequent messages."""
        # Send first message
        conv1, msg1 = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="First message",
        )

        # Send second message
        conv2, msg2 = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Second message",
        )

        # Should reuse same conversation
        assert conv1.id == conv2.id

        # Messages should be different
        assert msg1.id != msg2.id

        # Both messages in same conversation
        assert msg1.conversation_id == msg2.conversation_id

    def test_prevent_duplicate_conversations(self, message_manager: MessageManager, test_missions: dict):
        """Test only one open conversation exists between two missions."""
        # Send from mission 1 to mission 2
        conv1, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Message 1",
        )

        # Send from mission 2 to mission 1 (reverse direction)
        conv2, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_2"],
            to_possession_id=test_missions["mission_1"],
            body="Message 2",
        )

        # Should be same conversation regardless of direction
        assert conv1.id == conv2.id

    def test_separate_conversations_for_different_pairs(self, message_manager: MessageManager, test_missions: dict):
        """Test different mission pairs get separate conversations."""
        # Mission 1 -> Mission 2
        conv_1_2, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Message to mission 2",
        )

        # Mission 1 -> Mission 3
        conv_1_3, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_3"],
            body="Message to mission 3",
        )

        # Should be different conversations
        assert conv_1_2.id != conv_1_3.id


class TestClosedConversationHandling:
    """Tests for closed conversation handling (create new per ADR-008)."""

    def test_create_new_conversation_after_close(self, message_manager: MessageManager, test_missions: dict):
        """Test new conversation created when previous one is closed."""
        # Create first conversation
        conv1, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="First conversation",
        )

        # Close the conversation
        message_manager.close_conversation(conv1.id)

        # Send new message (should create new conversation)
        conv2, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="New conversation after close",
        )

        # Should be different conversation
        assert conv1.id != conv2.id
        assert conv2.status == "open"

    def test_closed_conversation_stays_closed(self, message_manager: MessageManager, test_missions: dict):
        """Test closed conversation is not reopened when new one is created."""
        # Create and close first conversation
        conv1, _ = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="First conversation",
        )
        message_manager.close_conversation(conv1.id)

        # Create new conversation
        message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="New conversation",
        )

        # Verify first conversation still closed
        conv1_after = message_manager.get_conversation(conv1.id)
        assert conv1_after is not None
        assert conv1_after.status == "closed"


class TestConversationViewTracking:
    """Tests for conversation view tracking."""

    def test_update_conversation_view_on_send(self, message_manager: MessageManager, test_missions: dict):
        """Test conversation view is updated when sending message."""
        conversation, message = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Test message",
        )

        # Verify conversation view created for sender
        view = message_manager.get_conversation_view(conversation.id, test_missions["mission_1"])
        assert view is not None
        assert view.conversation_id == conversation.id
        assert view.possession_id == test_missions["mission_1"]
        assert view.last_viewed_at is not None


class TestValidation:
    """Tests for validation and error handling."""

    def test_cannot_send_message_to_self(self, message_manager: MessageManager, test_missions: dict):
        """Test cannot send conversation message to yourself."""
        with pytest.raises(InvalidParticipantError):
            message_manager.send_conversation_message(
                from_possession_id=test_missions["mission_1"],
                to_possession_id=test_missions["mission_1"],  # Same as sender
                body="Message to myself",
            )

    def test_conversation_with_task_context(
        self, message_manager: MessageManager, test_missions: dict, test_db: Database
    ):
        """Test conversation can include task context."""
        # Create a test task
        test_db.execute_update(
            """
            INSERT INTO tasks (
                id, title, status, priority, role, file_path
            ) VALUES (
                'TST-H-0001', 'Test task', 'TODO', 'HIGH', 'Tester',
                '.opencode/work/tasks/TST-H-0001.md'
            )
            """
        )

        conversation, message = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Question about TST-H-0001",
            task_id="TST-H-0001",
        )

        # Verify task context
        assert conversation.task_id == "TST-H-0001"
        assert message.task_id == "TST-H-0001"


class TestIntegrationScenarios:
    """Integration tests for realistic conversation workflows."""

    def test_complete_conversation_workflow(self, message_manager: MessageManager, test_missions: dict):
        """Test complete conversation workflow: create, exchange messages, close."""
        # Mission 1 starts conversation
        conv1, msg1 = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Can you review my code?",
        )
        assert conv1.status == "open"

        # Mission 2 replies
        conv2, msg2 = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_2"],
            to_possession_id=test_missions["mission_1"],
            body="Sure, send me the PR link",
        )
        assert conv2.id == conv1.id  # Same conversation

        # Mission 1 responds
        conv3, msg3 = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="Here's the link: github.com/...",
        )
        assert conv3.id == conv1.id

        # Close conversation after resolution
        closed = message_manager.close_conversation(conv1.id)
        assert closed.status == "closed"

        # New message creates fresh conversation
        conv4, msg4 = message_manager.send_conversation_message(
            from_possession_id=test_missions["mission_1"],
            to_possession_id=test_missions["mission_2"],
            body="New question about different task",
        )
        assert conv4.id != conv1.id  # Different conversation
        assert conv4.status == "open"
