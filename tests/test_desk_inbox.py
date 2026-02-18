"""
Tests for desk mode inbox display integration (OPR-M-0103).

Tests cover:
- _format_desk_inbox_summary helper function
- Inbox-style message formatting per ADR-009 lines 160-171
- Filtering of own messages from desk mode display
- Desk command JSON output with inbox data
"""

import pytest

from site_nine.cli.comms import _format_desk_inbox_summary
from site_nine.core.database import Database
from site_nine.messaging.manager import MessageManager


@pytest.fixture
def message_manager(test_db: Database) -> MessageManager:
    """Create MessageManager with test database."""
    return MessageManager(test_db)


@pytest.fixture
def test_missions(test_db: Database) -> dict[str, int]:
    """Create test missions for desk mode testing."""
    test_db.execute_update(
        """
        INSERT INTO personas (name, role, mythology, description)
        VALUES
            ('desk-persona-1', 'Operator', 'Test', 'Desk test persona 1'),
            ('desk-persona-2', 'Engineer', 'Test', 'Desk test persona 2'),
            ('desk-persona-3', 'Architect', 'Test', 'Desk test persona 3')
        """
    )

    mission_1_id = test_db.execute_insert(
        """
        INSERT INTO missions (
            persona_name, role, codename, mission_file,
            start_date, start_time, objective
        )
        VALUES (
            'desk-persona-1', 'Operator', 'desk-one',
            '.opencode/work/missions/desk-1.md',
            '2026-02-14', '10:00:00', 'Desk test mission 1'
        )
        """
    )

    mission_2_id = test_db.execute_insert(
        """
        INSERT INTO missions (
            persona_name, role, codename, mission_file,
            start_date, start_time, objective
        )
        VALUES (
            'desk-persona-2', 'Engineer', 'desk-two',
            '.opencode/work/missions/desk-2.md',
            '2026-02-14', '10:00:00', 'Desk test mission 2'
        )
        """
    )

    mission_3_id = test_db.execute_insert(
        """
        INSERT INTO missions (
            persona_name, role, codename, mission_file,
            start_date, start_time, objective
        )
        VALUES (
            'desk-persona-3', 'Architect', 'desk-three',
            '.opencode/work/missions/desk-3.md',
            '2026-02-14', '10:00:00', 'Desk test mission 3'
        )
        """
    )

    return {
        "mission_1": mission_1_id,
        "mission_2": mission_2_id,
        "mission_3": mission_3_id,
    }


class TestFormatDeskInboxSummary:
    """Tests for _format_desk_inbox_summary helper."""

    def test_no_unread_messages_returns_empty(self, message_manager: MessageManager, test_missions: dict):
        """When there are no unread conversations, returns empty list."""
        conversations = message_manager.get_unread_conversations(test_missions["mission_1"])
        result = _format_desk_inbox_summary(message_manager, conversations, test_missions["mission_1"])
        assert result == []

    def test_single_unread_message_format(self, message_manager: MessageManager, test_missions: dict):
        """A single unread message from another mission formats correctly."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]

        # Mission 2 sends a message to Mission 1
        _conv, msg = message_manager.send_conversation_message(
            from_mission_id=mid2,
            to_mission_id=mid1,
            body="Question about design",
        )

        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)

        assert len(result) == 4  # header, message line, blank, reply hint
        assert "1 new message(s)!" in result[0]
        assert msg.id in result[1]
        assert f"Mission #{mid2}" in result[1]
        assert '"Question about design"' in result[1]
        assert "s9 comms reply" in result[3]

    def test_multiple_unread_messages_from_different_missions(
        self, message_manager: MessageManager, test_missions: dict
    ):
        """Multiple unread messages from different missions are all listed."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]
        mid3 = test_missions["mission_3"]

        # Mission 2 sends a message to Mission 1
        _conv2, msg2 = message_manager.send_conversation_message(
            from_mission_id=mid2,
            to_mission_id=mid1,
            body="Question about design",
        )

        # Mission 3 sends a message to Mission 1
        _conv3, msg3 = message_manager.send_conversation_message(
            from_mission_id=mid3,
            to_mission_id=mid1,
            body="Need clarification",
        )

        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)

        assert len(result) == 5  # header, 2 message lines, blank, reply hint
        assert "2 new message(s)!" in result[0]
        # Both messages should be listed
        msg_lines = result[1:3]
        msg_ids_in_output = [line for line in msg_lines if msg2.id in line or msg3.id in line]
        assert len(msg_ids_in_output) == 2

    def test_own_messages_excluded(self, message_manager: MessageManager, test_missions: dict):
        """Own messages are not shown in desk mode display."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]

        # Mission 1 sends a message to Mission 2
        message_manager.send_conversation_message(
            from_mission_id=mid1,
            to_mission_id=mid2,
            body="Hello from mission 1",
        )

        # Mission 1 checks its own desk — should NOT see its own outgoing message
        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)
        assert result == []

    def test_message_line_matches_adr_format(self, message_manager: MessageManager, test_missions: dict):
        """Message lines match ADR-009 format: '- MSG-X-NNNN from Mission #N: "subject"'."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]

        _conv, msg = message_manager.send_conversation_message(
            from_mission_id=mid2,
            to_mission_id=mid1,
            body="Question about design",
        )

        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)

        # Message line should start with "- " (not indented)
        msg_line = result[1]
        assert msg_line.startswith("- ")
        assert msg_line == f'- {msg.id} from Mission #{mid2}: "Question about design"'

    def test_reply_hint_present(self, message_manager: MessageManager, test_missions: dict):
        """Reply hint is shown when there are unread messages."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]

        message_manager.send_conversation_message(
            from_mission_id=mid2,
            to_mission_id=mid1,
            body="Need help with implementation",
        )

        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)

        # Last line should be the reply hint
        assert "s9 comms reply" in result[-1]
        assert "MSG_ID" in result[-1]

    def test_empty_conversations_list(self, message_manager: MessageManager, test_missions: dict):
        """Empty conversations list returns empty result."""
        result = _format_desk_inbox_summary(message_manager, [], test_missions["mission_1"])
        assert result == []

    def test_conversation_with_only_own_messages_returns_empty(
        self, message_manager: MessageManager, test_missions: dict
    ):
        """If all unread messages are from self, returns empty list."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]

        # Mission 1 sends to Mission 2, then Mission 2 views it
        _conv, _msg = message_manager.send_conversation_message(
            from_mission_id=mid1,
            to_mission_id=mid2,
            body="Hello",
        )

        # From mission 1's perspective, check unread — should be empty
        # because send_conversation_message marks the view for the sender
        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)
        assert result == []

    def test_multiple_messages_in_same_conversation(self, message_manager: MessageManager, test_missions: dict):
        """Multiple unread messages in the same conversation are all listed."""
        mid1 = test_missions["mission_1"]
        mid2 = test_missions["mission_2"]

        # Mission 2 sends two messages to Mission 1
        _conv, msg1 = message_manager.send_conversation_message(
            from_mission_id=mid2,
            to_mission_id=mid1,
            body="First question",
        )

        # Send another message in the same conversation
        msg2 = message_manager.create_message(
            conversation_id=_conv.id,
            from_mission_id=mid2,
            subject="Follow-up question",
            body="Follow-up question about the first topic",
            priority="MEDIUM",
        )

        conversations = message_manager.get_unread_conversations(mid1)
        result = _format_desk_inbox_summary(message_manager, conversations, mid1)

        assert "2 new message(s)!" in result[0]
        all_lines = "\n".join(result)
        assert msg1.id in all_lines
        assert msg2.id in all_lines
