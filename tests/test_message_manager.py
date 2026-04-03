"""Tests for messaging.manager module — desk mode and inbox integration"""

import pytest

from site_nine.messaging.manager import MessageManager


def _create_missions(db, count=2):
    """Create test possessions for messaging tests."""
    for i in range(1, count + 1):
        db.execute_update(
            """
            INSERT INTO possessions (id, daemon_name, role, possession_log, created_at, updated_at)
            VALUES (:id, :daemon, :role, :log, datetime('now'), datetime('now'))
            """,
            {
                "id": i,
                "daemon": "test-persona",
                "role": "Engineer",
                "log": f".opencode/work/possessions/test-{i}.md",
            },
        )


def _create_conversation(db, conv_id, participant_1, participant_2, subject="Test conversation"):
    """Create a test conversation."""
    db.execute_update(
        """
        INSERT INTO conversations (id, subject, type, status, participant_1_id, participant_2_id)
        VALUES (:id, :subject, 'conversation', 'open', :p1, :p2)
        """,
        {
            "id": conv_id,
            "subject": subject,
            "p1": participant_1,
            "p2": participant_2,
        },
    )


def _create_message(db, msg_id, conv_id, from_possession, subject="Test message", body="Test body", priority="MEDIUM"):
    """Create a test message."""
    db.execute_update(
        """
        INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority)
        VALUES (:id, :conv_id, :from_possession, :subject, :body, :priority)
        """,
        {
            "id": msg_id,
            "conv_id": conv_id,
            "from_possession": from_possession,
            "subject": subject,
            "body": body,
            "priority": priority,
        },
    )


def _set_conversation_view(db, conv_id, possession_id, viewed_at=None):
    """Set a conversation view timestamp."""
    if viewed_at is None:
        viewed_at_sql = "strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')"
    else:
        viewed_at_sql = f"'{viewed_at}'"

    db.execute_update(
        f"""
        INSERT INTO conversation_views (conversation_id, possession_id, last_viewed_at)
        VALUES (:conv_id, :possession_id, {viewed_at_sql})
        ON CONFLICT(conversation_id, possession_id)
        DO UPDATE SET last_viewed_at = {viewed_at_sql}
        """,
        {"conv_id": conv_id, "possession_id": possession_id},
    )


class TestGetUnreadMessages:
    """Tests for MessageManager.get_unread_messages"""

    def test_all_messages_unread_when_never_viewed(self, test_db):
        """All messages are unread if mission has never viewed the conversation."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Hello")
        _create_message(test_db, "MSG-M-0002", "CONV-0001", 1, subject="Follow-up")

        mgr = MessageManager(test_db)
        unread = mgr.get_unread_messages("CONV-0001", 2)

        assert len(unread) == 2
        assert unread[0].id == "MSG-M-0001"
        assert unread[1].id == "MSG-M-0002"

    def test_no_unread_after_viewing(self, test_db):
        """No unread messages after mission views the conversation."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Hello")

        mgr = MessageManager(test_db)

        # Mission 2 views the conversation
        mgr.update_conversation_view("CONV-0001", 2)

        unread = mgr.get_unread_messages("CONV-0001", 2)
        assert len(unread) == 0

    def test_new_messages_after_viewing_are_unread(self, test_db):
        """Messages sent after viewing are unread."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)

        # First message with explicit early timestamp
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-M-0001', 'CONV-0001', 1, 'First', 'body', 'MEDIUM', '2026-02-14T10:00:00+00:00')
            """
        )

        mgr = MessageManager(test_db)

        # Mission 2 views the conversation at a known timestamp
        _set_conversation_view(test_db, "CONV-0001", 2, "2026-02-14T10:00:30+00:00")

        # New message arrives AFTER the view timestamp
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES ('MSG-M-0002', 'CONV-0001', 1, 'Second', 'body', 'MEDIUM', '2026-02-14T10:01:00+00:00')
            """
        )

        unread = mgr.get_unread_messages("CONV-0001", 2)
        assert len(unread) == 1
        assert unread[0].id == "MSG-M-0002"
        assert unread[0].subject == "Second"

    def test_empty_conversation_has_no_unread(self, test_db):
        """Conversation with no messages has no unread messages."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)

        mgr = MessageManager(test_db)
        unread = mgr.get_unread_messages("CONV-0001", 2)
        assert len(unread) == 0

    def test_unread_preserves_message_attributes(self, test_db):
        """Unread messages have correct attributes for inbox display."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(
            test_db,
            "MSG-H-0001",
            "CONV-0001",
            1,
            subject="Urgent question",
            body="Need help with design",
            priority="HIGH",
        )

        mgr = MessageManager(test_db)
        unread = mgr.get_unread_messages("CONV-0001", 2)

        assert len(unread) == 1
        msg = unread[0]
        assert msg.id == "MSG-H-0001"
        assert msg.from_possession_id == 1
        assert msg.subject == "Urgent question"
        assert msg.priority == "HIGH"
        assert msg.body == "Need help with design"

    def test_unread_messages_ordered_by_created_at(self, test_db):
        """Unread messages are returned in chronological order."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)

        # Insert with explicit timestamps to ensure order
        test_db.execute_update(
            """
            INSERT INTO messages (id, conversation_id, from_possession_id, subject, body, priority, created_at)
            VALUES
                ('MSG-M-0003', 'CONV-0001', 1, 'Third', 'body', 'MEDIUM', '2026-02-14T10:03:00+00:00'),
                ('MSG-M-0001', 'CONV-0001', 1, 'First', 'body', 'MEDIUM', '2026-02-14T10:01:00+00:00'),
                ('MSG-M-0002', 'CONV-0001', 1, 'Second', 'body', 'MEDIUM', '2026-02-14T10:02:00+00:00')
            """
        )

        mgr = MessageManager(test_db)
        unread = mgr.get_unread_messages("CONV-0001", 2)

        assert len(unread) == 3
        assert unread[0].id == "MSG-M-0001"
        assert unread[1].id == "MSG-M-0002"
        assert unread[2].id == "MSG-M-0003"


class TestGetUnreadConversations:
    """Tests for get_unread_conversations used by desk mode."""

    def test_unread_conversations_returned(self, test_db):
        """Conversations with unread messages are returned."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2, subject="Design question")
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Hello")

        mgr = MessageManager(test_db)
        convs = mgr.get_unread_conversations(2)

        assert len(convs) == 1
        assert convs[0].id == "CONV-0001"

    def test_no_unread_after_viewing(self, test_db):
        """Viewed conversations are not returned."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Hello")

        mgr = MessageManager(test_db)
        mgr.update_conversation_view("CONV-0001", 2)

        convs = mgr.get_unread_conversations(2)
        assert len(convs) == 0


class TestDeskModeInboxIntegration:
    """Tests for desk mode + inbox integration logic."""

    def test_desk_mode_collects_all_unread_across_conversations(self, test_db):
        """Desk mode should show all unread messages across all conversations."""
        _create_missions(test_db, 3)
        _create_conversation(test_db, "CONV-0001", 1, 2, subject="Design question")
        _create_conversation(test_db, "CONV-0002", 3, 2, subject="Test plan")
        _create_message(test_db, "MSG-H-0001", "CONV-0001", 1, subject="Question about design", priority="HIGH")
        _create_message(test_db, "MSG-M-0002", "CONV-0002", 3, subject="Need clarification", priority="MEDIUM")

        mgr = MessageManager(test_db)

        # Simulate desk mode: get unread conversations, then messages
        conversations = mgr.get_unread_conversations(2)
        all_unread = []
        for conv in conversations:
            unread_msgs = mgr.get_unread_messages(conv.id, 2)
            for msg in unread_msgs:
                all_unread.append((conv.id, msg))

        assert len(all_unread) == 2
        # Verify message attributes are available for display
        msg_ids = {msg.id for _, msg in all_unread}
        assert "MSG-H-0001" in msg_ids
        assert "MSG-M-0002" in msg_ids

        # Verify display-relevant attributes
        for conv_id, msg in all_unread:
            assert msg.from_possession_id in (1, 3)
            assert msg.subject in ("Question about design", "Need clarification")

    def test_desk_mode_shows_nothing_when_all_read(self, test_db):
        """Desk mode shows no messages when all are read."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Hello")

        mgr = MessageManager(test_db)
        mgr.update_conversation_view("CONV-0001", 2)

        conversations = mgr.get_unread_conversations(2)
        assert len(conversations) == 0

    def test_inbox_and_desk_use_consistent_logic(self, test_db):
        """Inbox and desk mode should use the same underlying data."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2, subject="Question")
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Help needed")

        mgr = MessageManager(test_db)

        # Both inbox (get_unread_conversations) and desk polling use same method
        inbox_convs = mgr.get_unread_conversations(2)
        desk_convs = mgr.get_unread_conversations(2)

        assert len(inbox_convs) == len(desk_convs)
        assert inbox_convs[0].id == desk_convs[0].id

        # Both should get same unread messages
        inbox_msgs = mgr.get_unread_messages("CONV-0001", 2)
        desk_msgs = mgr.get_unread_messages("CONV-0001", 2)

        assert len(inbox_msgs) == len(desk_msgs)
        assert inbox_msgs[0].id == desk_msgs[0].id

    def test_unread_count_matches_unread_messages(self, test_db):
        """get_unread_message_count and get_unread_messages return consistent results."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1)
        _create_message(test_db, "MSG-M-0002", "CONV-0001", 1)
        _create_message(test_db, "MSG-M-0003", "CONV-0001", 1)

        mgr = MessageManager(test_db)

        count = mgr.get_unread_message_count("CONV-0001", 2)
        messages = mgr.get_unread_messages("CONV-0001", 2)

        assert count == len(messages)
        assert count == 3


class TestMessageAcknowledgement:
    """Tests for message acknowledgement tracking."""

    def test_acknowledge_message(self, test_db):
        """Test acknowledging a message."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Test")

        mgr = MessageManager(test_db)
        mgr.acknowledge_message("MSG-M-0001", 2)

        # Verify acknowledgement was recorded
        assert mgr.is_message_acknowledged_by("MSG-M-0001", 2) is True

    def test_acknowledge_message_idempotent(self, test_db):
        """Test acknowledging a message multiple times is idempotent."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Test")

        mgr = MessageManager(test_db)

        # Acknowledge twice
        mgr.acknowledge_message("MSG-M-0001", 2)
        mgr.acknowledge_message("MSG-M-0001", 2)

        # Should still be acknowledged
        assert mgr.is_message_acknowledged_by("MSG-M-0001", 2) is True

        # Should have only one acknowledgement record
        acks = mgr.get_message_acknowledgements("MSG-M-0001")
        assert len(acks) == 1

    def test_get_message_acknowledgements(self, test_db):
        """Test getting all acknowledgements for a message."""
        _create_missions(test_db, 3)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Test")

        mgr = MessageManager(test_db)

        # Multiple missions acknowledge the same message
        mgr.acknowledge_message("MSG-M-0001", 2)
        mgr.acknowledge_message("MSG-M-0001", 3)

        acks = mgr.get_message_acknowledgements("MSG-M-0001")
        assert len(acks) == 2

        possession_ids = {ack["possession_id"] for ack in acks}
        assert possession_ids == {2, 3}

    def test_is_message_acknowledged_by(self, test_db):
        """Test checking if specific mission acknowledged a message."""
        _create_missions(test_db, 3)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Test")

        mgr = MessageManager(test_db)

        # Mission 2 acknowledges, mission 3 does not
        mgr.acknowledge_message("MSG-M-0001", 2)

        assert mgr.is_message_acknowledged_by("MSG-M-0001", 2) is True
        assert mgr.is_message_acknowledged_by("MSG-M-0001", 3) is False

    def test_get_unacknowledged_messages(self, test_db):
        """Test getting unacknowledged messages for a mission."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Message 1")
        _create_message(test_db, "MSG-M-0002", "CONV-0001", 1, subject="Message 2")
        _create_message(test_db, "MSG-M-0003", "CONV-0001", 1, subject="Message 3")

        mgr = MessageManager(test_db)

        # Mission 2 acknowledges one message
        mgr.acknowledge_message("MSG-M-0001", 2)

        # Mission 2 should have 2 unacknowledged messages
        unacked = mgr.get_unacknowledged_messages(2)
        assert len(unacked) == 2

        unacked_ids = {msg.id for msg in unacked}
        assert unacked_ids == {"MSG-M-0002", "MSG-M-0003"}

    def test_get_unacknowledged_messages_excludes_own_messages(self, test_db):
        """Test that missions don't see their own messages as unacknowledged."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="From mission 1")
        _create_message(test_db, "MSG-M-0002", "CONV-0001", 2, subject="From mission 2")

        mgr = MessageManager(test_db)

        # Mission 1 should only see message from mission 2
        unacked = mgr.get_unacknowledged_messages(1)
        assert len(unacked) == 1
        assert unacked[0].id == "MSG-M-0002"

        # Mission 2 should only see message from mission 1
        unacked = mgr.get_unacknowledged_messages(2)
        assert len(unacked) == 1
        assert unacked[0].id == "MSG-M-0001"

    def test_get_unacknowledged_messages_excludes_closed_conversations(self, test_db):
        """Test that closed conversations are excluded from unacknowledged messages."""
        _create_missions(test_db, 2)
        _create_conversation(test_db, "CONV-0001", 1, 2)
        _create_message(test_db, "MSG-M-0001", "CONV-0001", 1, subject="Test")

        # Close the conversation
        test_db.execute_update("UPDATE conversations SET status = 'closed' WHERE id = 'CONV-0001'")

        mgr = MessageManager(test_db)
        unacked = mgr.get_unacknowledged_messages(2)

        # Should not see messages from closed conversation
        assert len(unacked) == 0

    def test_acknowledge_nonexistent_message_raises_error(self, test_db):
        """Test that acknowledging a non-existent message raises an error."""
        _create_missions(test_db, 1)

        mgr = MessageManager(test_db)

        with pytest.raises(Exception):  # MessageNotFoundError
            mgr.acknowledge_message("MSG-M-9999", 1)
